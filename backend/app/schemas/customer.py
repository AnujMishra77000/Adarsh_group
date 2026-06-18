from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DispensingOrderStatus, FollowUpStatus, Gender, PaymentStatus

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class CustomerBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    age: int | None = Field(default=None, ge=0, le=130)
    contact_no: str = Field(min_length=8, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    whatsapp_no: str | None = Field(default=None, min_length=8, max_length=20)
    gender: Gender | None = None
    occupation: str | None = Field(default=None, max_length=255)
    guardian_name: str | None = Field(default=None, max_length=255)
    guardian_contact_no: str | None = Field(default=None, min_length=8, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    purpose_of_visit: str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool = False

    @field_validator("whatsapp_no", "occupation", "guardian_name", "guardian_contact_no", "address", "purpose_of_visit", mode="before")
    @classmethod
    def normalize_blank_optional_strings(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not EMAIL_REGEX.match(normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class CustomerCreate(CustomerBase):
    registration_idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    age: int | None = Field(default=None, ge=0, le=130)
    contact_no: str | None = Field(default=None, min_length=8, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    whatsapp_no: str | None = Field(default=None, min_length=8, max_length=20)
    gender: Gender | None = None
    occupation: str | None = Field(default=None, max_length=255)
    guardian_name: str | None = Field(default=None, max_length=255)
    guardian_contact_no: str | None = Field(default=None, min_length=8, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    purpose_of_visit: str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool | None = None

    @field_validator("whatsapp_no", "occupation", "guardian_name", "guardian_contact_no", "address", "purpose_of_visit", mode="before")
    @classmethod
    def normalize_blank_optional_strings(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not EMAIL_REGEX.match(normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: str
    created_at: datetime
    updated_at: datetime
    created_by: int | None
    updated_by: int | None
    is_deleted: bool


class CustomerPrescriptionSummary(BaseModel):
    id: int
    prescription_date: date
    notes: str | None


class CustomerBillSummary(BaseModel):
    id: int
    bill_number: str
    final_price: Decimal
    balance_amount: Decimal
    payment_status: PaymentStatus
    created_at: datetime


class CustomerVisitSummary(BaseModel):
    id: int
    visit_date: datetime
    reason_for_visit: str
    referred_by: str | None
    status: str
    assigned_examiner_id: int | None
    visit_notes: str | None
    created_at: datetime


class CustomerReferralSummary(BaseModel):
    visit_id: int
    visit_date: datetime
    specialist_type: str | None
    referral_status: str | None
    notes: str | None
    follow_up: str | None


class CustomerContactLensOrderSummary(BaseModel):
    id: int
    visit_id: int
    order_reference: str
    status: DispensingOrderStatus
    vendor_id: int | None
    created_at: datetime


class CustomerFollowUpTaskSummary(BaseModel):
    id: int
    visit_id: int
    contact_lens_order_id: int
    task_type: str
    due_date: date
    status: FollowUpStatus
    notes: str | None
    completed_at: datetime | None


class CustomerDetailRead(CustomerRead):
    visits: list[CustomerVisitSummary]
    referrals: list[CustomerReferralSummary]
    prescriptions: list[CustomerPrescriptionSummary]
    bills: list[CustomerBillSummary]
    contact_lens_orders: list[CustomerContactLensOrderSummary]
    follow_up_tasks: list[CustomerFollowUpTaskSummary]


class CustomerListResponse(BaseModel):
    items: list[CustomerRead]
    total: int
    page: int
    page_size: int
