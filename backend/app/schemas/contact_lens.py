from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    DispensingOrderStatus,
    ExamSectionState,
    FollowUpInterval,
    FollowUpReminderState,
    FollowUpStatus,
    FollowUpType,
)
from app.schemas.dispensing_order import OrderStatusEventRead


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class _OptionalTextModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def normalize_blank_text(cls, value: object) -> object:
        return _blank_to_none(value)


class ContactLensIndication(_OptionalTextModel):
    type: Literal["cosmetic", "refractive", "keratoconus", "sports", "therapeutic", "other"] | None = None
    other: str | None = Field(default=None, max_length=255)


class ContactLensAssessmentEye(_OptionalTextModel):
    k_reading: str | None = Field(default=None, max_length=100)
    hvid_mm: str | None = Field(default=None, max_length=32)
    tear_film: str | None = Field(default=None, max_length=255)
    tbut_seconds: str | None = Field(default=None, max_length=32)


class ContactLensAssessment(_OptionalTextModel):
    right: ContactLensAssessmentEye = Field(default_factory=ContactLensAssessmentEye)
    left: ContactLensAssessmentEye = Field(default_factory=ContactLensAssessmentEye)
    clinical_notes: str | None = Field(default=None, max_length=4000)


class ContactLensEyePrescription(_OptionalTextModel):
    power: str | None = Field(default=None, max_length=32)
    base_curve_mm: str | None = Field(default=None, max_length=32)
    diameter_mm: str | None = Field(default=None, max_length=32)


class ContactLensPrescription(BaseModel):
    right: ContactLensEyePrescription = Field(default_factory=ContactLensEyePrescription)
    left: ContactLensEyePrescription = Field(default_factory=ContactLensEyePrescription)


class ContactLensDetails(_OptionalTextModel):
    brand: str | None = Field(default=None, max_length=255)
    material: str | None = Field(default=None, max_length=255)
    replacement_schedule: str | None = Field(default=None, max_length=255)
    wearing_schedule: str | None = Field(default=None, max_length=255)


class ContactLensTrialTraining(_OptionalTextModel):
    trial_lens_dispensed: bool = False
    training_status: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)


class ContactLensWorkupUpdate(BaseModel):
    state: ExamSectionState = ExamSectionState.INCOMPLETE
    indication: ContactLensIndication = Field(default_factory=ContactLensIndication)
    assessment: ContactLensAssessment = Field(default_factory=ContactLensAssessment)
    prescription: ContactLensPrescription = Field(default_factory=ContactLensPrescription)
    lens_details: ContactLensDetails = Field(default_factory=ContactLensDetails)
    trial_training: ContactLensTrialTraining = Field(default_factory=ContactLensTrialTraining)


class ContactLensWorkupRead(ContactLensWorkupUpdate):
    saved_at: datetime | None = None
    saved_by: int | None = None


class ContactLensOrderUpdate(BaseModel):
    vendor_id: int | None = Field(default=None, ge=1)
    lens_details: ContactLensDetails = Field(default_factory=ContactLensDetails)
    order_notes: str | None = Field(default=None, max_length=4000)
    expected_delivery_date: date | None = None

    @field_validator("order_notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        return _blank_to_none(value)


class ContactLensOrderStatusUpdate(BaseModel):
    status: DispensingOrderStatus
    notes: str | None = Field(default=None, max_length=4000)


class ContactLensOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    customer_id: int
    vendor_id: int | None
    vendor_name: str | None = None
    order_reference: str
    status: DispensingOrderStatus
    workup_snapshot: dict
    lens_details: ContactLensDetails
    order_notes: str | None
    expected_delivery_date: date | None
    delivered_by: int | None
    delivered_at: datetime | None
    is_delayed: bool
    events: list[OrderStatusEventRead]
    created_by: int | None
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


class ContactLensFollowUpSchedule(BaseModel):
    interval: FollowUpInterval
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def validate_custom_due_date(self):
        if self.interval == FollowUpInterval.CUSTOM and self.due_date is None:
            raise ValueError("A due date is required for a custom follow-up")
        return self


class ContactLensFollowUpStatusUpdate(BaseModel):
    status: FollowUpStatus
    completion_notes: str | None = Field(default=None, max_length=4000)


class FollowUpCreate(BaseModel):
    task_type: FollowUpType
    due_date: date
    assigned_staff_id: int | None = Field(default=None, gt=0)
    reminder_state: FollowUpReminderState = FollowUpReminderState.NOT_SCHEDULED
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_create_notes(cls, value: object) -> object:
        return _blank_to_none(value)


class FollowUpStatusUpdate(BaseModel):
    status: FollowUpStatus
    completion_notes: str | None = Field(default=None, max_length=4000)

    @field_validator("completion_notes", mode="before")
    @classmethod
    def normalize_completion_notes(cls, value: object) -> object:
        return _blank_to_none(value)


class ContactLensFollowUpRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    visit_id: int
    contact_lens_order_id: int | None
    task_type: FollowUpType
    interval: FollowUpInterval | None
    due_date: date
    status: FollowUpStatus
    assigned_staff_id: int | None
    reminder_state: FollowUpReminderState
    notes: str | None
    completion_notes: str | None
    completed_by: int | None
    completed_at: datetime | None
    created_by: int | None
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


class FollowUpListResponse(BaseModel):
    visit_id: int
    items: list[ContactLensFollowUpRead]
    total: int


class ContactLensContext(BaseModel):
    visit_id: int
    is_activated: bool
    workup: ContactLensWorkupRead | None
    order: ContactLensOrderRead | None
    follow_up: ContactLensFollowUpRead | None
    active_bill_id: int | None = None
