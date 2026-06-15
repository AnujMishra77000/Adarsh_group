from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VendorBase(BaseModel):
    vendor_name: str = Field(min_length=2, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    whatsapp_no: str = Field(min_length=8, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    vendor_name: str | None = Field(default=None, min_length=2, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    whatsapp_no: str | None = Field(default=None, min_length=8, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class VendorRead(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class VendorListResponse(BaseModel):
    items: list[VendorRead]
    total: int
    page: int
    page_size: int
