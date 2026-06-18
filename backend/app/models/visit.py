from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import VisitStatus, enum_values
from app.models.mixins import TimestampMixin, UserTrackingMixin


class Visit(Base, TimestampMixin, UserTrackingMixin):
    __tablename__ = "visits"
    __table_args__ = (
        UniqueConstraint("shop_key", "idempotency_key", name="uq_visits_shop_key_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reason_for_visit: Mapped[str] = mapped_column(String(255), nullable=False)
    referred_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_examiner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    visit_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_lens_workup_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus, name="visit_status", values_callable=enum_values),
        nullable=False,
        default=VisitStatus.DRAFT,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    shop = relationship("Shop", back_populates="visits")
    customer = relationship("Customer", back_populates="visits")
    assigned_examiner = relationship("User", foreign_keys=[assigned_examiner_id])
    exam_sections = relationship("VisitExamSection", back_populates="visit", cascade="all, delete-orphan")
    prescription_versions = relationship("VisitPrescription", back_populates="visit")
    dispensing_order = relationship("DispensingOrder", back_populates="visit", uselist=False)
    contact_lens_order = relationship("ContactLensOrder", back_populates="visit", uselist=False)
    follow_up_tasks = relationship("FollowUpTask", back_populates="visit")
    bills = relationship("Bill", back_populates="visit")
