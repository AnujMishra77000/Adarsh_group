from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShopResolveRequest(BaseModel):
    mobile: str | None = Field(default=None, min_length=3, max_length=80)
    identifier: str | None = Field(default=None, min_length=3, max_length=80)

    @model_validator(mode="after")
    def ensure_identifier(self) -> "ShopResolveRequest":
        if not (self.mobile or self.identifier):
            raise ValueError("Either mobile or identifier is required")
        return self


class ShopPublicRead(BaseModel):
    code: str
    display_name: str
    location_label: str
    center_type: str


class ShopBase(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=255)
    location_label: str = Field(default="", max_length=255)
    center_type: str = Field(min_length=2, max_length=80)
    is_active: bool = True


class ShopCreate(ShopBase):
    pass


class ShopUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=255)
    location_label: str | None = Field(default=None, max_length=255)
    center_type: str | None = Field(default=None, min_length=2, max_length=80)
    is_active: bool | None = None


class ShopRead(ShopBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
