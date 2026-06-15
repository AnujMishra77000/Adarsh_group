from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionBase(BaseModel):
    customer_id: int
    prescription_date: date
    right_sph: Decimal | None = None
    right_cyl: Decimal | None = None
    right_axis: int | None = Field(default=None, ge=0, le=180)
    right_vn: str | None = Field(default=None, max_length=20)
    left_sph: Decimal | None = None
    left_cyl: Decimal | None = None
    left_axis: int | None = Field(default=None, ge=0, le=180)
    left_vn: str | None = Field(default=None, max_length=20)
    fh: str | None = Field(default=None, max_length=32)
    add_power: Decimal | None = None
    pd: Decimal | None = None
    notes: str | None = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionUpdate(BaseModel):
    prescription_date: date | None = None
    right_sph: Decimal | None = None
    right_cyl: Decimal | None = None
    right_axis: int | None = Field(default=None, ge=0, le=180)
    right_vn: str | None = Field(default=None, max_length=20)
    left_sph: Decimal | None = None
    left_cyl: Decimal | None = None
    left_axis: int | None = Field(default=None, ge=0, le=180)
    left_vn: str | None = Field(default=None, max_length=20)
    fh: str | None = Field(default=None, max_length=32)
    add_power: Decimal | None = None
    pd: Decimal | None = None
    notes: str | None = None


class PrescriptionRead(PrescriptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    created_by: int | None
    updated_by: int | None
    is_deleted: bool
    customer_name: str | None = None
    customer_business_id: str | None = None
    customer_contact_no: str | None = None


class PrescriptionListResponse(BaseModel):
    items: list[PrescriptionRead]
    total: int
    page: int
    page_size: int


class PrescriptionPdfResponse(BaseModel):
    prescription_id: int
    pdf_url: str


class PrescriptionSendVendorRequest(BaseModel):
    vendor_id: int = Field(ge=1)
    caption: str | None = Field(default=None, max_length=500)


class PrescriptionSendVendorResponse(BaseModel):
    message: str
    whatsapp_log_id: int | None = None
    provider_message_id: str | None = None
