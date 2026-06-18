from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DispensingOrderStatus, LensType


class _OptionalTextModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class FrameSelection(_OptionalTextModel):
    brand: str | None = Field(default=None, max_length=120)
    model_number: str | None = Field(default=None, max_length=120)
    colour_code: str | None = Field(default=None, max_length=80)
    frame_type: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    a_size_mm: Decimal | None = Field(default=None, gt=0, le=100)
    b_size_mm: Decimal | None = Field(default=None, gt=0, le=100)
    dbl_mm: Decimal | None = Field(default=None, gt=0, le=50)
    temple_length_mm: Decimal | None = Field(default=None, gt=0, le=250)
    effective_diameter_mm: Decimal | None = Field(default=None, gt=0, le=120)


class DispensingMeasurements(_OptionalTextModel):
    right_monocular_pd_mm: Decimal | None = Field(default=None, gt=0, le=60)
    left_monocular_pd_mm: Decimal | None = Field(default=None, gt=0, le=60)
    total_pd_mm: Decimal | None = Field(default=None, gt=0, le=100)
    right_fitting_height_mm: Decimal | None = Field(default=None, gt=0, le=80)
    left_fitting_height_mm: Decimal | None = Field(default=None, gt=0, le=80)
    right_segment_height_mm: Decimal | None = Field(default=None, gt=0, le=80)
    left_segment_height_mm: Decimal | None = Field(default=None, gt=0, le=80)
    pantoscopic_tilt_degrees: Decimal | None = Field(default=None, ge=-30, le=30)
    vertex_distance_mm: Decimal | None = Field(default=None, gt=0, le=50)
    measured_by: str | None = Field(default=None, max_length=255)
    measurement_notes: str | None = Field(default=None, max_length=2000)


class LensSpecification(_OptionalTextModel):
    lens_type: LensType | None = None
    brand: str | None = Field(default=None, max_length=120)
    material: str | None = Field(default=None, max_length=120)
    index: str | None = Field(default=None, max_length=40)
    design: str | None = Field(default=None, max_length=160)
    coating: str | None = Field(default=None, max_length=160)
    tint_or_photochromic: str | None = Field(default=None, max_length=160)


class DispensingOrderDraftUpdate(_OptionalTextModel):
    frame: FrameSelection = Field(default_factory=FrameSelection)
    measurements: DispensingMeasurements = Field(default_factory=DispensingMeasurements)
    lens: LensSpecification = Field(default_factory=LensSpecification)
    vendor_id: int | None = Field(default=None, gt=0)
    manufacturing_instructions: str | None = Field(default=None, max_length=4000)
    expected_delivery_date: date | None = None


class DispensingOrderStatusUpdate(BaseModel):
    status: DispensingOrderStatus
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class OrderStatusEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event: str
    previous_status: DispensingOrderStatus | None
    status: DispensingOrderStatus
    user_id: int | None
    notes: str | None
    occurred_at: datetime


class DispensingOrderSendVendorRequest(_OptionalTextModel):
    caption: str | None = Field(default=None, max_length=1024)


class DispensingOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    customer_id: int
    prescription_id: int
    prescription_version_number: int
    vendor_id: int | None
    vendor_name: str | None
    order_reference: str
    status: DispensingOrderStatus
    frame: FrameSelection
    measurements: DispensingMeasurements
    lens: LensSpecification
    manufacturing_instructions: str | None
    has_vendor_document: bool
    sent_by: int | None
    sent_at: datetime | None
    expected_delivery_date: date | None
    delivered_by: int | None
    delivered_at: datetime | None
    is_delayed: bool
    events: list[OrderStatusEventRead]
    created_by: int | None
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


class DispensingOrderContext(BaseModel):
    visit_id: int
    current_prescription_id: int | None
    current_prescription_version_number: int | None
    order: DispensingOrderRead | None
    is_prescription_stale: bool


class DispensingOrderDocumentResponse(BaseModel):
    order_id: int
    download_url: str


class DispensingOrderSendVendorResponse(BaseModel):
    message: str
    whatsapp_log_id: int | None = None
    provider_message_id: str | None = None
