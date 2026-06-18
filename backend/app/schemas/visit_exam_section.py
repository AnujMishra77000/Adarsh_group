from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ExamSectionState


class VisitExamSectionUpdate(BaseModel):
    state: ExamSectionState
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("state")
    @classmethod
    def reject_future_save_state(cls, value: ExamSectionState) -> ExamSectionState:
        if value == ExamSectionState.FUTURE:
            raise ValueError("Future sections cannot be saved")
        return value


class VisitExamSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    title: str
    description: str
    state: ExamSectionState
    is_required: bool
    is_optional: bool
    is_disabled: bool
    is_visible: bool
    payload: dict[str, Any]
    saved_at: datetime | None = None
    saved_by: int | None = None


class VisitExamSectionListResponse(BaseModel):
    visit_id: int
    sections: list[VisitExamSectionRead]
    total: int


class VisitExamSectionHistoryItem(BaseModel):
    visit_id: int
    visit_date: datetime
    section_key: str
    title: str
    state: ExamSectionState
    payload: dict[str, Any]
    saved_at: datetime | None = None
    saved_by: int | None = None


class VisitExamSectionHistoryResponse(BaseModel):
    visit_id: int
    items: list[VisitExamSectionHistoryItem]
    total: int
