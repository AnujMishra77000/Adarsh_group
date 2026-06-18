from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import (
    DispensingOrderStatus,
    FollowUpReminderState,
    FollowUpStatus,
    FollowUpType,
    enum_values,
)
from app.models.mixins import TimestampMixin, UserTrackingMixin


class ContactLensOrder(Base, TimestampMixin, UserTrackingMixin):
    __tablename__ = "contact_lens_orders"
    __table_args__ = (
        UniqueConstraint("visit_id", name="uq_contact_lens_orders_visit_id"),
        UniqueConstraint("shop_id", "order_reference", name="uq_contact_lens_orders_shop_reference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=True, index=True)
    order_reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[DispensingOrderStatus] = mapped_column(
        Enum(DispensingOrderStatus, name="dispensing_order_status", values_callable=enum_values),
        nullable=False,
        default=DispensingOrderStatus.DRAFT,
        index=True,
    )
    workup_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lens_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    order_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    delivered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shop = relationship("Shop", back_populates="contact_lens_orders")
    visit = relationship("Visit", back_populates="contact_lens_order")
    customer = relationship("Customer", back_populates="contact_lens_orders")
    vendor = relationship("Vendor", back_populates="contact_lens_orders")
    bills = relationship("Bill", back_populates="contact_lens_order")
    follow_up_tasks = relationship("FollowUpTask", back_populates="contact_lens_order")
    status_events = relationship(
        "OrderStatusEvent",
        back_populates="contact_lens_order",
        order_by="OrderStatusEvent.occurred_at",
        cascade="all, delete-orphan",
    )


class FollowUpTask(Base, TimestampMixin, UserTrackingMixin):
    __tablename__ = "follow_up_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False, index=True)
    contact_lens_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("contact_lens_orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default=FollowUpType.CONTACT_LENS.value, index=True
    )
    interval: Mapped[str | None] = mapped_column(String(32), nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status", values_callable=enum_values),
        nullable=False,
        default=FollowUpStatus.PENDING,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_staff_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reminder_state: Mapped[FollowUpReminderState] = mapped_column(
        Enum(FollowUpReminderState, name="follow_up_reminder_state", values_callable=enum_values),
        nullable=False,
        default=FollowUpReminderState.NOT_SCHEDULED,
        index=True,
    )
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shop = relationship("Shop", back_populates="follow_up_tasks")
    customer = relationship("Customer", back_populates="follow_up_tasks")
    visit = relationship("Visit", back_populates="follow_up_tasks")
    contact_lens_order = relationship("ContactLensOrder", back_populates="follow_up_tasks")
