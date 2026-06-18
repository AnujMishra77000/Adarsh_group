from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PrescriptionVersionStatus, VisitStatus


class PrescriptionEyeValues(BaseModel):
    sph: str | None = Field(default=None, max_length=16)
    cyl: str | None = Field(default=None, max_length=16)
    axis: str | None = Field(default=None, max_length=3)
    add: str | None = Field(default=None, max_length=16)
    va: str | None = Field(default=None, max_length=20)

    @field_validator("sph", "cyl", "axis", "add", "va")
    @classmethod
    def normalize_optional_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PrescriptionEyePair(BaseModel):
    right: PrescriptionEyeValues = Field(default_factory=PrescriptionEyeValues)
    left: PrescriptionEyeValues = Field(default_factory=PrescriptionEyeValues)


class FinalPrescriptionData(BaseModel):
    distance: PrescriptionEyePair = Field(default_factory=PrescriptionEyePair)
    near: PrescriptionEyePair = Field(default_factory=PrescriptionEyePair)
    pd: str | None = Field(default=None, max_length=32)
    fitting_height: str | None = Field(default=None, max_length=32)

    @field_validator("pd", "fitting_height")
    @classmethod
    def normalize_measurement(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class VisitPrescriptionDraftUpdate(BaseModel):
    data: FinalPrescriptionData = Field(default_factory=FinalPrescriptionData)
    patient_instructions: str | None = Field(default=None, max_length=4000)

    @field_validator("patient_instructions")
    @classmethod
    def normalize_instructions(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PrescriptionFinalizeRequest(BaseModel):
    confirmed: bool = False


class VisitCompletionRequest(BaseModel):
    confirmed: bool = False


class VisitPrescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    customer_id: int
    version_number: int
    status: PrescriptionVersionStatus
    is_current: bool
    data: FinalPrescriptionData
    patient_instructions: str | None
    amends_prescription_id: int | None
    finalized_by: int | None
    finalized_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: int | None
    updated_by: int | None
    has_pdf: bool = False


class VisitPrescriptionSummary(BaseModel):
    visit_id: int
    current_version_id: int | None
    draft_version_id: int | None
    versions: list[VisitPrescriptionRead]


class PrescriptionReviewPatient(BaseModel):
    id: int
    business_id: str
    name: str


class PrescriptionReviewVisit(BaseModel):
    id: int
    visit_date: datetime
    reason_for_visit: str
    status: VisitStatus
    shop_key: str
    branch_name: str
    branch_location: str


class PrescriptionReviewExaminer(BaseModel):
    id: int
    name: str


class VisitPrescriptionReview(BaseModel):
    prescription: VisitPrescriptionRead
    patient: PrescriptionReviewPatient
    visit: PrescriptionReviewVisit
    examiner: PrescriptionReviewExaminer
    core_examination_summary: dict[str, dict]
    referral_summary: dict | None
    patient_instructions: str | None
    warnings: list[str]


class VisitPrescriptionPdfResponse(BaseModel):
    visit_id: int
    prescription_id: int
    version_number: int
    pdf_url: str
