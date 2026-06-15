from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.enums import WhatsAppMessageType, WhatsAppModuleType, WhatsAppStatus
from app.models.mixins import TimestampMixin


class WhatsAppLog(Base, TimestampMixin):
    __tablename__ = "whatsapp_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_type: Mapped[WhatsAppModuleType] = mapped_column(
        Enum(WhatsAppModuleType, name="whatsapp_module_type"),
        nullable=False,
    )
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_no: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[WhatsAppMessageType] = mapped_column(
        Enum(WhatsAppMessageType, name="whatsapp_message_type"),
        nullable=False,
    )
    template_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[WhatsAppStatus] = mapped_column(Enum(WhatsAppStatus, name="whatsapp_status"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
