from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StaffCreateRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=72)


class StaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    shop_key: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StaffListResponse(BaseModel):
    items: list[StaffRead]
    total: int
    page: int
    page_size: int


class StaffLoginActivityRead(BaseModel):
    id: int
    staff_user_id: int
    staff_email: EmailStr
    staff_full_name: str | None
    attempted_at: datetime
    ip_address: str | None
    user_agent: str | None


class StaffLoginActivityListResponse(BaseModel):
    items: list[StaffLoginActivityRead]
    total: int
    page: int
    page_size: int
