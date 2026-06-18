from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentStatus


class VisitBillLinkRequest(BaseModel):
    bill_id: int = Field(ge=1)
    dispensing_order_id: int | None = Field(default=None, ge=1)
    contact_lens_order_id: int | None = Field(default=None, ge=1)


class VisitBillSummary(BaseModel):
    id: int
    bill_number: str
    visit_id: int | None
    dispensing_order_id: int | None
    contact_lens_order_id: int | None
    grand_total: Decimal
    paid_total: Decimal
    balance_amount: Decimal
    payment_status: PaymentStatus
    has_invoice: bool


class VisitBillingContext(BaseModel):
    visit_id: int
    customer_id: int
    dispensing_order_id: int | None
    contact_lens_order_id: int | None
    order_bill: VisitBillSummary | None
    contact_lens_order_bill: VisitBillSummary | None
    visit_bills: list[VisitBillSummary]
