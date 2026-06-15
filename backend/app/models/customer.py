from __future__ import annotations

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shops import DEFAULT_SHOP_KEY
from app.db.base_class import Base
from app.models.enums import Gender
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UserTrackingMixin


class Customer(Base, TimestampMixin, UserTrackingMixin, SoftDeleteMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_key: Mapped[str] = mapped_column(String(64), nullable=False, default=DEFAULT_SHOP_KEY, index=True)
    customer_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contact_no: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    whatsapp_no: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, name="gender_enum"), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose_of_visit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    prescriptions = relationship("Prescription", back_populates="customer")
    bills = relationship("Bill", back_populates="customer")
