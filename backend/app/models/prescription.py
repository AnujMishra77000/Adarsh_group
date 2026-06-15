from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UserTrackingMixin


class Prescription(Base, TimestampMixin, UserTrackingMixin, SoftDeleteMixin):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    prescription_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    right_sph: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    right_cyl: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    right_axis: Mapped[int | None] = mapped_column(Integer, nullable=True)
    right_vn: Mapped[str | None] = mapped_column(String(20), nullable=True)

    left_sph: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    left_cyl: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    left_axis: Mapped[int | None] = mapped_column(Integer, nullable=True)
    left_vn: Mapped[str | None] = mapped_column(String(20), nullable=True)

    fh: Mapped[str | None] = mapped_column(String(32), nullable=True)
    add_power: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    pd: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="prescriptions")
