from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMode, PaymentStatus


class BillBase(BaseModel):
    customer_id: int = Field(ge=1)
    product_name: str = Field(min_length=1, max_length=255)
    frame_name: str | None = Field(default=None, max_length=255)
    whole_price: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    payment_mode: PaymentMode
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)


class BillCreate(BillBase):
    pass


class BillUpdate(BaseModel):
    customer_id: int | None = Field(default=None, ge=1)
    product_name: str | None = Field(default=None, min_length=1, max_length=255)
    frame_name: str | None = Field(default=None, max_length=255)
    whole_price: Decimal | None = Field(default=None, ge=0)
    discount: Decimal | None = Field(default=None, ge=0)
    paid_amount: Decimal | None = Field(default=None, ge=0)
    payment_mode: PaymentMode | None = None
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)


class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bill_number: str
    customer_id: int
    customer_name_snapshot: str

    product_name: str
    frame_name: str | None

    whole_price: Decimal
    discount: Decimal
    final_price: Decimal
    paid_amount: Decimal
    balance_amount: Decimal

    payment_mode: PaymentMode
    payment_status: PaymentStatus

    delivery_date: date | None
    notes: str | None
    pdf_url: str | None

    created_at: datetime
    updated_at: datetime
    created_by: int | None
    updated_by: int | None
    is_deleted: bool

    customer_name: str | None = None
    customer_business_id: str | None = None
    customer_contact_no: str | None = None


class BillListResponse(BaseModel):
    items: list[BillRead]
    total: int
    page: int
    page_size: int
