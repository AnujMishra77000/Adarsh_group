from __future__ import annotations

from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import ExamSectionState, enum_values
from app.models.mixins import TimestampMixin, UserTrackingMixin


class VisitExamSection(Base, TimestampMixin, UserTrackingMixin):
    __tablename__ = "visit_exam_sections"
    __table_args__ = (
        UniqueConstraint("visit_id", "section_key", name="uq_visit_exam_sections_visit_section"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    state: Mapped[ExamSectionState] = mapped_column(
        Enum(ExamSectionState, name="exam_section_state", values_callable=enum_values),
        nullable=False,
        default=ExamSectionState.INCOMPLETE,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    shop = relationship("Shop", back_populates="visit_exam_sections")
    visit = relationship("Visit", back_populates="exam_sections")
