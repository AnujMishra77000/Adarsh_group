from __future__ import annotations

from app.core.config import Settings


def test_production_effective_cors_origins_do_not_include_development_ports() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        SECRET_KEY="production-secret-key-with-more-than-32-characters",
        ADMIN_MASTER_PASSWORD="production-admin-password",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=14,
        BACKEND_CORS_ORIGINS=["https://crm.adarsh.example"],
    )

    assert settings.effective_backend_cors_origins == ["https://crm.adarsh.example"]
