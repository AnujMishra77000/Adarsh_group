from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.campaign import Campaign
from app.models.customer import Customer
from app.models.enums import CampaignStatus, PaymentStatus, WhatsAppStatus
from app.models.prescription import Prescription
from app.models.whatsapp_log import WhatsAppLog
from app.schemas.analytics import (
    DashboardSummaryResponse,
    RevenueSummaryResponse,
    RevenueTimeseriesPoint,
    RevenueTimeseriesResponse,
)

RevenueRangeKey = Literal["today", "last_7_days", "last_30_days"]


@dataclass
class RangeWindow:
    start: datetime
    end: datetime
    labels: list[str]


class AnalyticsService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key

    @staticmethod
    def _day_bounds(target_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(target_date, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        return start, end

    def _build_window(self, range_key: RevenueRangeKey) -> RangeWindow:
        now = datetime.now(UTC)
        today = now.date()

        if range_key == "today":
            start, end = self._day_bounds(today)
            labels = [f"{hour:02d}:00" for hour in range(24)]
            return RangeWindow(start=start, end=end, labels=labels)

        if range_key == "last_7_days":
            start_date = today - timedelta(days=6)
            start, _ = self._day_bounds(start_date)
            _, end = self._day_bounds(today)
            labels = [(start_date + timedelta(days=offset)).strftime("%d %b") for offset in range(7)]
            return RangeWindow(start=start, end=end, labels=labels)

        start_date = today - timedelta(days=29)
        start, _ = self._day_bounds(start_date)
        _, end = self._day_bounds(today)
        labels = [(start_date + timedelta(days=offset)).strftime("%d %b") for offset in range(30)]
        return RangeWindow(start=start, end=end, labels=labels)

    def _confirmed_bill_query(self):
        return (
            self.db.query(Bill)
            .join(Customer, Customer.id == Bill.customer_id)
            .filter(
                Bill.is_deleted.is_(False),
                Customer.is_deleted.is_(False),
                Customer.shop_key == self.shop_key,
                Bill.payment_status.in_([PaymentStatus.PAID, PaymentStatus.PARTIAL]),
            )
        )

    def get_dashboard_summary(self, *, include_revenue: bool = True) -> DashboardSummaryResponse:
        now = datetime.now(UTC)
        today_start, today_end = self._day_bounds(now.date())

        total_customers = (
            self.db.query(Customer.id).filter(Customer.is_deleted.is_(False), Customer.shop_key == self.shop_key).count()
        )
        today_customers = (
            self.db.query(Customer.id)
            .filter(
                Customer.is_deleted.is_(False),
                Customer.shop_key == self.shop_key,
                Customer.created_at >= today_start,
                Customer.created_at < today_end,
            )
            .count()
        )

        total_prescriptions = (
            self.db.query(Prescription.id)
            .join(Customer, Customer.id == Prescription.customer_id)
            .filter(
                Prescription.is_deleted.is_(False),
                Customer.is_deleted.is_(False),
                Customer.shop_key == self.shop_key,
            )
            .count()
        )

        bills_generated_today = (
            self.db.query(Bill.id)
            .join(Customer, Customer.id == Bill.customer_id)
            .filter(
                Bill.is_deleted.is_(False),
                Customer.is_deleted.is_(False),
                Customer.shop_key == self.shop_key,
                Bill.created_at >= today_start,
                Bill.created_at < today_end,
            )
            .count()
        )

        revenue_today = 0.0
        if include_revenue:
            revenue_today_raw = (
                self._confirmed_bill_query()
                .with_entities(func.coalesce(func.sum(Bill.final_price), 0))
                .filter(Bill.created_at >= today_start, Bill.created_at < today_end)
                .scalar()
            )
            revenue_today = float(revenue_today_raw or 0)

        scheduled_campaigns = (
            self.db.query(Campaign.id)
            .filter(
                Campaign.is_deleted.is_(False),
                Campaign.shop_key == self.shop_key,
                Campaign.status == CampaignStatus.SCHEDULED,
            )
            .count()
        )

        failed_whatsapp_jobs = (
            self.db.query(WhatsAppLog.id)
            .join(Customer, Customer.id == WhatsAppLog.customer_id)
            .filter(
                WhatsAppLog.status == WhatsAppStatus.FAILED,
                Customer.shop_key == self.shop_key,
            )
            .count()
        )

        return DashboardSummaryResponse(
            total_customers=total_customers,
            today_customers=today_customers,
            total_prescriptions=total_prescriptions,
            bills_generated_today=bills_generated_today,
            revenue_today=revenue_today,
            scheduled_campaigns=scheduled_campaigns,
            failed_whatsapp_jobs=failed_whatsapp_jobs,
        )

    def get_revenue_summary(self, range_key: RevenueRangeKey) -> RevenueSummaryResponse:
        window = self._build_window(range_key)

        bills = (
            self._confirmed_bill_query()
            .filter(Bill.created_at >= window.start, Bill.created_at < window.end)
            .all()
        )

        total_revenue = Decimal("0.00")
        for bill in bills:
            total_revenue += Decimal(bill.final_price)

        total_bills = len(bills)
        average_bill_value = float(total_revenue / total_bills) if total_bills > 0 else 0.0

        return RevenueSummaryResponse(
            range_key=range_key,
            total_revenue=float(total_revenue),
            total_bills=total_bills,
            average_bill_value=average_bill_value,
        )

    def get_revenue_timeseries(self, range_key: RevenueRangeKey) -> RevenueTimeseriesResponse:
        window = self._build_window(range_key)

        bills = (
            self._confirmed_bill_query()
            .filter(Bill.created_at >= window.start, Bill.created_at < window.end)
            .all()
        )

        series: dict[str, float] = {label: 0.0 for label in window.labels}

        for bill in bills:
            created = bill.created_at.astimezone(UTC)
            if range_key == "today":
                key = f"{created.hour:02d}:00"
            else:
                key = created.strftime("%d %b")
            if key in series:
                series[key] += float(bill.final_price)

        points = [RevenueTimeseriesPoint(label=label, value=series[label]) for label in window.labels]
        return RevenueTimeseriesResponse(range_key=range_key, points=points)
