from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY_VALUES = {
    "change-this-to-a-long-random-secret",
    "replace-with-a-long-random-secret",
    "changeme",
    "change-me",
    "secret",
    "supersecret",
    "your-secret-key",
}
DEFAULT_ADMIN_MASTER_PASSWORD_VALUES = {
    "adarsh@1234",
    "admin",
    "admin123",
    "password",
    "password123",
    "change-this-admin-master-password",
}
LOCAL_DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = Field(default="Adarsh Optical Group CRM", alias="PROJECT_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    secret_key: str = Field(alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    allow_long_refresh_tokens_in_production: bool = Field(
        default=False, alias="ALLOW_LONG_REFRESH_TOKENS_IN_PRODUCTION"
    )
    allow_admin_registration: bool = Field(default=False, alias="ALLOW_ADMIN_REGISTRATION")
    auth_login_rate_limit_attempts: int = Field(default=10, alias="AUTH_LOGIN_RATE_LIMIT_ATTEMPTS")
    auth_login_rate_limit_window_seconds: int = Field(default=60, alias="AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS")
    auth_login_lockout_failed_attempts: int = Field(default=5, alias="AUTH_LOGIN_LOCKOUT_FAILED_ATTEMPTS")
    auth_login_lockout_seconds: int = Field(default=300, alias="AUTH_LOGIN_LOCKOUT_SECONDS")
    admin_master_password: str = Field(alias="ADMIN_MASTER_PASSWORD")
    auth_enforce_global_email_uniqueness: bool = Field(
        default=True, alias="AUTH_ENFORCE_GLOBAL_EMAIL_UNIQUENESS"
    )

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    shop_databases: dict[str, str] = Field(default_factory=dict, alias="SHOP_DATABASES")
    shop_identifier_mappings: dict[str, str] = Field(default_factory=dict, alias="SHOP_IDENTIFIER_MAPPINGS")

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
    smtp_from_name: str = Field(default="Adarsh Optical Group", alias="SMTP_FROM_NAME")
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

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return str(value).strip().lower()

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

    @field_validator("shop_identifier_mappings", mode="before")
    @classmethod
    def parse_shop_identifier_mappings(cls, value: str | dict[str, str] | None) -> dict[str, str]:
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
                raise ValueError("SHOP_IDENTIFIER_MAPPINGS must be valid JSON object") from exc
            if not isinstance(loaded, dict):
                raise ValueError("SHOP_IDENTIFIER_MAPPINGS must map identifier/mobile values to shop codes")
            parsed = {str(identifier): str(shop_code) for identifier, shop_code in loaded.items()}
        else:
            raise ValueError("SHOP_IDENTIFIER_MAPPINGS must be a dictionary or JSON string")

        cleaned: dict[str, str] = {}
        for identifier, shop_code in parsed.items():
            normalized_identifier = identifier.strip().lower()
            normalized_shop_code = shop_code.strip().lower()
            if not normalized_identifier or not normalized_shop_code:
                continue
            cleaned[normalized_identifier] = normalized_shop_code
        return cleaned

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if not self.is_production:
            return self

        errors: list[str] = []
        secret_key = self.secret_key.strip()
        admin_master_password = self.admin_master_password.strip()

        if secret_key.lower() in DEFAULT_SECRET_KEY_VALUES or len(secret_key) < 32:
            errors.append(
                "SECRET_KEY must be a unique high-entropy value of at least 32 characters in production"
            )

        if (
            admin_master_password.lower() in DEFAULT_ADMIN_MASTER_PASSWORD_VALUES
            or len(admin_master_password) < 12
        ):
            errors.append(
                "ADMIN_MASTER_PASSWORD must be changed from the default and be at least 12 characters in production"
            )

        if self.access_token_expire_minutes <= 0:
            errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0 in production")

        if self.refresh_token_expire_days > 30 and not self.allow_long_refresh_tokens_in_production:
            errors.append(
                "REFRESH_TOKEN_EXPIRE_DAYS must be 30 or less in production unless "
                "ALLOW_LONG_REFRESH_TOKENS_IN_PRODUCTION=true is explicitly set"
            )

        if "backend_cors_origins" not in self.model_fields_set or not self.backend_cors_origins:
            errors.append("BACKEND_CORS_ORIGINS must be explicitly set in production")
        elif any("*" in origin.strip() for origin in self.backend_cors_origins):
            errors.append("BACKEND_CORS_ORIGINS must not include '*' in production")

        if errors:
            joined_errors = "; ".join(errors)
            raise ValueError(f"Unsafe production configuration: {joined_errors}")

        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def admin_registration_enabled(self) -> bool:
        return self.is_development or self.allow_admin_registration

    @property
    def effective_backend_cors_origins(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.backend_cors_origins if origin.strip()]
        if not self.is_production:
            origins.extend(LOCAL_DEVELOPMENT_CORS_ORIGINS)
        return list(dict.fromkeys(origins))

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
    def vendor_order_media_dir(self) -> Path:
        return self.media_root_path / "vendor_orders"

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
