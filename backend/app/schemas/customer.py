from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Gender, PaymentStatus

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomerBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    age: int | None = Field(default=None, ge=0, le=130)
    contact_no: str = Field(min_length=8, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    whatsapp_no: str | None = Field(default=None, min_length=8, max_length=20)
    gender: Gender | None = None
    address: str | None = Field(default=None, max_length=2000)
    purpose_of_visit: str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool = False

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
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    age: int | None = Field(default=None, ge=0, le=130)
    contact_no: str | None = Field(default=None, min_length=8, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    whatsapp_no: str | None = Field(default=None, min_length=8, max_length=20)
    gender: Gender | None = None
    address: str | None = Field(default=None, max_length=2000)
    purpose_of_visit: str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool | None = None

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


class CustomerDetailRead(CustomerRead):
    prescriptions: list[CustomerPrescriptionSummary]
    bills: list[CustomerBillSummary]


class CustomerListResponse(BaseModel):
    items: list[CustomerRead]
    total: int
    page: int
    page_size: int
