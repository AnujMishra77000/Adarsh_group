from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import Gender, enum_values
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UserTrackingMixin


class Customer(Base, TimestampMixin, UserTrackingMixin, SoftDeleteMixin):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("shop_id", "customer_id", name="uq_customers_shop_id_customer_id"),
        UniqueConstraint("shop_key", "registration_idempotency_key", name="uq_customers_shop_key_registration_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True, index=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    customer_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contact_no: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    whatsapp_no: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, name="gender_enum", values_callable=enum_values), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_contact_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose_of_visit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registration_idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    shop = relationship("Shop", back_populates="customers")
    prescriptions = relationship("Prescription", back_populates="customer")
    bills = relationship("Bill", back_populates="customer")
    visits = relationship("Visit", back_populates="customer")
    visit_prescriptions = relationship("VisitPrescription", back_populates="customer")
    dispensing_orders = relationship("DispensingOrder", back_populates="customer")
    contact_lens_orders = relationship("ContactLensOrder", back_populates="customer")
    follow_up_tasks = relationship("FollowUpTask", back_populates="customer")
