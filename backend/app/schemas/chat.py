from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageCreate(BaseModel):
    message_text: str = Field(min_length=1, max_length=4000)


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_user_id: int | None
    sender_name: str
    sender_role: str
    sender_shop_key: str
    sender_shop_name: str
    message_text: str | None
    attachment_original_name: str | None
    attachment_content_type: str | None
    attachment_size_bytes: int | None
    attachment_stored_bytes: int | None
    is_attachment_compressed: bool
    has_attachment: bool
    created_at: datetime
    updated_at: datetime


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageRead]
    has_more: bool


class ChatSocketEvent(BaseModel):
    event: str
    data: ChatMessageRead
