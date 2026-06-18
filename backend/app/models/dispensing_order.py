from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import DispensingOrderStatus, enum_values
from app.models.mixins import TimestampMixin, UserTrackingMixin


class DispensingOrder(Base, TimestampMixin, UserTrackingMixin):
    __tablename__ = "dispensing_orders"
    __table_args__ = (
        UniqueConstraint("visit_id", name="uq_dispensing_orders_visit_id"),
        UniqueConstraint("shop_id", "order_reference", name="uq_dispensing_orders_shop_reference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("visit_prescriptions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=True, index=True)
    order_reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[DispensingOrderStatus] = mapped_column(
        Enum(DispensingOrderStatus, name="dispensing_order_status", values_callable=enum_values),
        nullable=False,
        default=DispensingOrderStatus.DRAFT,
        index=True,
    )
    frame_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    measurement_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lens_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    manufacturing_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor_document_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shop = relationship("Shop", back_populates="dispensing_orders")
    visit = relationship("Visit", back_populates="dispensing_order")
    customer = relationship("Customer", back_populates="dispensing_orders")
    prescription = relationship("VisitPrescription", back_populates="dispensing_orders")
    vendor = relationship("Vendor", back_populates="dispensing_orders")
    bills = relationship("Bill", back_populates="dispensing_order")
