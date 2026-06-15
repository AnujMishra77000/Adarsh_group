from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.analytics import DashboardSummaryResponse, RevenueSummaryResponse, RevenueTimeseriesResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

RangeKey = Literal["today", "last_7_days", "last_30_days"]


@router.get("/dashboard", response_model=DashboardSummaryResponse)
def dashboard_summary(
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DashboardSummaryResponse:
    _ = current_user
    service = AnalyticsService(db, shop_key=shop_key)
    return service.get_dashboard_summary(include_revenue=current_user.role == UserRole.ADMIN)


@router.get("/revenue", response_model=RevenueSummaryResponse)
def revenue_summary(
    range_key: RangeKey = Query(default="last_7_days", alias="range"),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> RevenueSummaryResponse:
    _ = current_user
    service = AnalyticsService(db, shop_key=shop_key)
    return service.get_revenue_summary(range_key=range_key)


@router.get("/revenue/timeseries", response_model=RevenueTimeseriesResponse)
def revenue_timeseries(
    range_key: RangeKey = Query(default="last_7_days", alias="range"),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> RevenueTimeseriesResponse:
    _ = current_user
    service = AnalyticsService(db, shop_key=shop_key)
    return service.get_revenue_timeseries(range_key=range_key)
