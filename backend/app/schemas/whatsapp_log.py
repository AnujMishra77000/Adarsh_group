from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import WhatsAppMessageType, WhatsAppModuleType, WhatsAppStatus


class WhatsAppLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_type: WhatsAppModuleType
    reference_id: int
    customer_id: int | None
    vendor_id: int | None
    recipient_no: str
    message_type: WhatsAppMessageType
    template_name: str | None
    media_id: str | None
    provider_message_id: str | None
    status: WhatsAppStatus
    error_message: str | None
    payload_json: dict
    created_at: datetime
    updated_at: datetime
