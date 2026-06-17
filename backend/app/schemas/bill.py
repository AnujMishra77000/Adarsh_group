from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BillItemType, PaymentMode, PaymentStatus


class BillItemBase(BaseModel):
    item_type: BillItemType = BillItemType.OTHER
    item_name: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)


class BillItemCreate(BillItemBase):
    pass


class BillItemRead(BillItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bill_id: int
    line_total: Decimal


class BillPaymentBase(BaseModel):
    mode: PaymentMode
    amount: Decimal = Field(gt=0)
    paid_at: datetime | None = None
    reference_no: str | None = Field(default=None, max_length=255)


class BillPaymentCreate(BillPaymentBase):
    pass


class BillPaymentRead(BillPaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bill_id: int
    paid_at: datetime


class BillBase(BaseModel):
    customer_id: int = Field(ge=1)
    product_name: str | None = Field(default=None, min_length=1, max_length=255)
    frame_name: str | None = Field(default=None, max_length=255)
    whole_price: Decimal | None = Field(default=None, ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    payment_mode: PaymentMode | None = None
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    tax_total: Decimal = Field(default=Decimal("0.00"), ge=0)
    items: list[BillItemCreate] = Field(default_factory=list)
    payments: list[BillPaymentCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_items_or_legacy_product(self) -> Self:
        if self.items:
            return self

        if not self.product_name or self.whole_price is None:
            raise ValueError("Provide either bill items or legacy product_name and whole_price")

        return self


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
    tax_total: Decimal | None = Field(default=None, ge=0)
    items: list[BillItemCreate] | None = None
    payments: list[BillPaymentCreate] | None = None


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
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    paid_total: Decimal
    balance_amount: Decimal

    payment_mode: PaymentMode
    payment_status: PaymentStatus
    items: list[BillItemRead] = Field(default_factory=list)
    payments: list[BillPaymentRead] = Field(default_factory=list)

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
