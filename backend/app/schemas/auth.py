from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, model_validator


class AdminRegisterRequest(BaseModel):
    shop_code: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    master_password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    shop_code: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None
    login_id: str | None = Field(default=None, min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @model_validator(mode="after")
    def ensure_login_identifier(self) -> "LoginRequest":
        if not self.email and not self.login_id:
            raise ValueError("Either email or login_id is required")
        return self


class RefreshTokenRequest(BaseModel):
    shop_code: str | None = Field(default=None, min_length=3, max_length=64)
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    shop_code: str | None = Field(default=None, min_length=3, max_length=64)
    refresh_token: str = Field(min_length=20)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthPublicConfigResponse(BaseModel):
    admin_registration_enabled: bool
