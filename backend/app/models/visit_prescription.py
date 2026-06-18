from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import PrescriptionVersionStatus, enum_values
from app.models.mixins import TimestampMixin, UserTrackingMixin


class VisitPrescription(Base, TimestampMixin, UserTrackingMixin):
    __tablename__ = "visit_prescriptions"
    __table_args__ = (
        UniqueConstraint("visit_id", "version_number", name="uq_visit_prescriptions_visit_version"),
        Index(
            "uq_visit_prescriptions_current_per_visit",
            "visit_id",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current = 1"),
        ),
        Index(
            "uq_visit_prescriptions_draft_per_visit",
            "visit_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
            sqlite_where=text("status = 'draft'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PrescriptionVersionStatus] = mapped_column(
        Enum(PrescriptionVersionStatus, name="prescription_version_status", values_callable=enum_values),
        nullable=False,
        default=PrescriptionVersionStatus.DRAFT,
        index=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    patient_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    amends_prescription_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit_prescriptions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    finalized_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop = relationship("Shop", back_populates="visit_prescriptions")
    customer = relationship("Customer", back_populates="visit_prescriptions")
    visit = relationship("Visit", back_populates="prescription_versions")
    amends_prescription = relationship("VisitPrescription", remote_side=[id], foreign_keys=[amends_prescription_id])
    dispensing_orders = relationship("DispensingOrder", back_populates="prescription")
