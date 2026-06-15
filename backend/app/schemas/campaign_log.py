from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CampaignLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    customer_id: int | None
    recipient_whatsapp_no: str
    send_status: str
    provider_message_id: str | None
    error_message: str | None
    attempted_at: datetime


class CampaignLogListResponse(BaseModel):
    items: list[CampaignLogRead]
    total: int
    page: int
    page_size: int
