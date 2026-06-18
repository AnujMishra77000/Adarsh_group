from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Shop(Base, TimestampMixin):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    center_type: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    users = relationship("User", back_populates="shop")
    customers = relationship("Customer", back_populates="shop")
    prescriptions = relationship("Prescription", back_populates="shop")
    bills = relationship("Bill", back_populates="shop")
    vendors = relationship("Vendor", back_populates="shop")
    campaigns = relationship("Campaign", back_populates="shop")
    campaign_logs = relationship("CampaignLog", back_populates="shop")
    whatsapp_logs = relationship("WhatsAppLog", back_populates="shop")
    audit_logs = relationship("AuditLog", back_populates="shop")
    chat_messages = relationship("ChatMessage", back_populates="shop")
    visits = relationship("Visit", back_populates="shop")
    visit_exam_sections = relationship("VisitExamSection", back_populates="shop")
    visit_prescriptions = relationship("VisitPrescription", back_populates="shop")
    dispensing_orders = relationship("DispensingOrder", back_populates="shop")
    contact_lens_orders = relationship("ContactLensOrder", back_populates="shop")
    follow_up_tasks = relationship("FollowUpTask", back_populates="shop")
