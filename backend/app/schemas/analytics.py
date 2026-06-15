from __future__ import annotations

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_customers: int
    today_customers: int
    total_prescriptions: int
    bills_generated_today: int
    revenue_today: float
    scheduled_campaigns: int
    failed_whatsapp_jobs: int


class RevenueSummaryResponse(BaseModel):
    range_key: str
    total_revenue: float
    total_bills: int
    average_bill_value: float


class RevenueTimeseriesPoint(BaseModel):
    label: str
    value: float


class RevenueTimeseriesResponse(BaseModel):
    range_key: str
    points: list[RevenueTimeseriesPoint]
