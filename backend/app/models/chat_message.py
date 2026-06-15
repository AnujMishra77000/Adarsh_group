from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sender_shop_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    attachment_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_storage_name: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    attachment_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_stored_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_attachment_compressed: Mapped[bool] = mapped_column(default=False, nullable=False)
