from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = Field(default="Aadarsh Eye Boutique Care Centre CRM", alias="PROJECT_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    secret_key: str = Field(alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=0, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=36500, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    admin_master_password: str = Field(default="adarsh@1234", alias="ADMIN_MASTER_PASSWORD")
    auth_enforce_global_email_uniqueness: bool = Field(
        default=True, alias="AUTH_ENFORCE_GLOBAL_EMAIL_UNIQUENESS"
    )

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    shop_databases: dict[str, str] = Field(default_factory=dict, alias="SHOP_DATABASES")

    postgres_server: str = Field(default="localhost", alias="POSTGRES_SERVER")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="eye_boutique", alias="POSTGRES_DB")
    postgres_user: str = Field(default="eye_admin", alias="POSTGRES_USER")
    postgres_password: str = Field(default="eye_password", alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"], alias="BACKEND_CORS_ORIGINS"
    )

    backend_public_url: str = Field(default="http://localhost:8000", alias="BACKEND_PUBLIC_URL")
    media_root: str = Field(default="storage", alias="MEDIA_ROOT")
    media_url_prefix: str = Field(default="/media", alias="MEDIA_URL_PREFIX")
    chat_storage_root: str = Field(default="private_storage/chat", alias="CHAT_STORAGE_ROOT")
    chat_max_file_size_mb: int = Field(default=12, alias="CHAT_MAX_FILE_SIZE_MB")
    chat_redis_channel: str = Field(default="eye_boutique:shared_chat", alias="CHAT_REDIS_CHANNEL")

    # SMTP / Gmail settings for automatic customer welcome email
    customer_welcome_email_enabled: bool = Field(default=False, alias="CUSTOMER_WELCOME_EMAIL_ENABLED")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Aadarsh Eye Boutique Care Centre", alias="SMTP_FROM_NAME")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    smtp_timeout_seconds: int = Field(default=30, alias="SMTP_TIMEOUT_SECONDS")

    whatsapp_api_base_url: str = Field(default="https://graph.facebook.com", alias="WHATSAPP_API_BASE_URL")
    whatsapp_api_version: str = Field(default="v20.0", alias="WHATSAPP_API_VERSION")
    whatsapp_phone_number_id: str | None = Field(default=None, alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_access_token: str | None = Field(default=None, alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_business_account_id: str | None = Field(default=None, alias="WHATSAPP_BUSINESS_ACCOUNT_ID")
    whatsapp_default_country_code: str = Field(default="91", alias="WHATSAPP_DEFAULT_COUNTRY_CODE")
    whatsapp_request_timeout_seconds: int = Field(default=25, alias="WHATSAPP_REQUEST_TIMEOUT_SECONDS")
    whatsapp_retry_attempts: int = Field(default=3, alias="WHATSAPP_RETRY_ATTEMPTS")

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if value.startswith("["):
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError("BACKEND_CORS_ORIGINS JSON value must be a list")
            return [str(origin) for origin in parsed]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("backend_public_url", mode="before")
    @classmethod
    def normalize_backend_public_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("media_url_prefix", mode="before")
    @classmethod
    def normalize_media_url_prefix(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            cleaned = f"/{cleaned}"
        if cleaned != "/":
            cleaned = cleaned.rstrip("/")
        return cleaned

    @field_validator("shop_databases", mode="before")
    @classmethod
    def parse_shop_databases(cls, value: str | dict[str, str] | None) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            parsed = value
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return {}
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("SHOP_DATABASES must be valid JSON object") from exc
            if not isinstance(loaded, dict):
                raise ValueError("SHOP_DATABASES must be a JSON object mapping shop_code to database url")
            parsed = {str(key): str(url) for key, url in loaded.items()}
        else:
            raise ValueError("SHOP_DATABASES must be a dictionary or JSON string")

        cleaned: dict[str, str] = {}
        for shop_code, database_uri in parsed.items():
            normalized_shop = shop_code.strip().lower()
            normalized_uri = database_uri.strip()
            if not normalized_shop or not normalized_uri:
                continue
            cleaned[normalized_shop] = normalized_uri
        return cleaned

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        if self.shop_databases:
            return next(iter(self.shop_databases.values()))
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    @property
    def backend_root_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def media_root_path(self) -> Path:
        root = Path(self.media_root)
        if root.is_absolute():
            return root
        return self.backend_root_dir / root

    @property
    def invoice_media_dir(self) -> Path:
        return self.media_root_path / "invoices"

    @property
    def prescription_media_dir(self) -> Path:
        return self.media_root_path / "prescriptions"

    @property
    def chat_storage_root_path(self) -> Path:
        root = Path(self.chat_storage_root)
        if root.is_absolute():
            return root
        return self.backend_root_dir / root


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
