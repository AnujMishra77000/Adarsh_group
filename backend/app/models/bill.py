from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import BillItemType, PaymentMode, PaymentStatus, enum_values
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UserTrackingMixin


class Bill(Base, TimestampMixin, UserTrackingMixin, SoftDeleteMixin):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("shop_id", "bill_number", name="uq_bills_shop_id_bill_number"),
        Index(
            "uq_bills_active_dispensing_order",
            "dispensing_order_id",
            unique=True,
            postgresql_where=text("dispensing_order_id IS NOT NULL AND NOT is_deleted"),
            sqlite_where=text("dispensing_order_id IS NOT NULL AND is_deleted = 0"),
        ),
        Index(
            "uq_bills_active_contact_lens_order",
            "contact_lens_order_id",
            unique=True,
            postgresql_where=text("contact_lens_order_id IS NOT NULL AND NOT is_deleted"),
            sqlite_where=text("contact_lens_order_id IS NOT NULL AND is_deleted = 0"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    bill_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id", ondelete="RESTRICT"), nullable=True, index=True)
    dispensing_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("dispensing_orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    contact_lens_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("contact_lens_orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    customer_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)

    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    frame_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    whole_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    final_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    paid_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    payment_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode", values_callable=enum_values),
        nullable=False,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=enum_values),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop = relationship("Shop", back_populates="bills")
    customer = relationship("Customer", back_populates="bills")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan", order_by="BillItem.id")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan", order_by="Payment.id")
    visit = relationship("Visit", back_populates="bills")
    dispensing_order = relationship("DispensingOrder", back_populates="bills")
    contact_lens_order = relationship("ContactLensOrder", back_populates="bills")


class BillItem(Base, TimestampMixin):
    __tablename__ = "bill_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type: Mapped[BillItemType] = mapped_column(
        Enum(BillItemType, name="bill_item_type", values_callable=enum_values),
        nullable=False,
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    bill = relationship("Bill", back_populates="items")
    shop = relationship("Shop")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode", values_callable=enum_values),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_no: Mapped[str | None] = mapped_column(String(255), nullable=True)

    bill = relationship("Bill", back_populates="payments")
    shop = relationship("Shop")
