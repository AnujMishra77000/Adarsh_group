from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import VisitStatus


class VisitBase(BaseModel):
    visit_date: datetime | None = None
    reason_for_visit: str = Field(min_length=2, max_length=255)
    referred_by: str | None = Field(default=None, max_length=255)
    assigned_examiner_id: int | None = Field(default=None, ge=1)
    visit_notes: str | None = Field(default=None, max_length=4000)
    contact_lens_workup_requested: bool = False
    status: VisitStatus = VisitStatus.DRAFT

    @field_validator("visit_date")
    @classmethod
    def normalize_visit_date(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @field_validator("status")
    @classmethod
    def validate_start_status(cls, value: VisitStatus) -> VisitStatus:
        if value not in {VisitStatus.DRAFT, VisitStatus.IN_PROGRESS}:
            raise ValueError("New visits can only start as draft or in progress")
        return value


class VisitCreate(VisitBase):
    customer_id: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_key: str
    customer_id: int
    customer_name: str | None = None
    customer_business_id: str | None = None
    customer_contact_no: str | None = None
    visit_date: datetime
    reason_for_visit: str
    referred_by: str | None
    assigned_examiner_id: int | None
    assigned_examiner_name: str | None = None
    visit_notes: str | None
    contact_lens_workup_requested: bool
    status: VisitStatus
    created_at: datetime
    updated_at: datetime
    created_by: int | None
    updated_by: int | None


class VisitListResponse(BaseModel):
    items: list[VisitRead]
    total: int
