from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CampaignStatus


class CampaignBase(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    message_body: str = Field(min_length=1, max_length=5000)
    scheduled_at: datetime


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    message_body: str | None = Field(default=None, min_length=1, max_length=5000)
    scheduled_at: datetime | None = None
    status: CampaignStatus | None = None


class CampaignRead(CampaignBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CampaignStatus
    total_customers_targeted: int
    total_sent: int
    total_failed: int
    created_by: int | None
    updated_by: int | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    items: list[CampaignRead]
    total: int
    page: int
    page_size: int


class CampaignScheduleResponse(BaseModel):
    message: str
    campaign: CampaignRead
