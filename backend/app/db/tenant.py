from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import AppException


def _build_engine_kwargs(database_uri: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
    }

    if database_uri.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


class TenantDBManager:
    def __init__(self, shop_databases: dict[str, str]):
        self._shop_databases = {key.strip().lower(): value for key, value in shop_databases.items()}
        self._engines: dict[str, Engine] = {}
        self._sessionmakers: dict[str, sessionmaker[Session]] = {}
        self._lock = Lock()

    @property
    def shop_codes(self) -> set[str]:
        return set(self._shop_databases.keys())

    def validate_shop_code(self, shop_code: str) -> str:
        if not self._shop_databases:
            raise AppException(
                status_code=500,
                code="shop_database_mapping_missing",
                message="SHOP_DATABASES configuration is missing",
            )

        normalized = shop_code.strip().lower()
        if not normalized:
            raise AppException(status_code=400, code="missing_shop_code", message="Shop context is required")
        if normalized not in self._shop_databases:
            raise AppException(status_code=400, code="invalid_shop_code", message="Invalid shop context")
        return normalized

    def _ensure_sessionmaker(self, shop_code: str) -> sessionmaker[Session]:
        validated_shop = self.validate_shop_code(shop_code)

        existing = self._sessionmakers.get(validated_shop)
        if existing is not None:
            return existing

        with self._lock:
            existing = self._sessionmakers.get(validated_shop)
            if existing is not None:
                return existing

            database_uri = self._shop_databases[validated_shop]
            engine = create_engine(database_uri, **_build_engine_kwargs(database_uri))
            local_sessionmaker = sessionmaker(
                bind=engine,
                autoflush=False,
                autocommit=False,
                future=True,
            )
            self._engines[validated_shop] = engine
            self._sessionmakers[validated_shop] = local_sessionmaker
            return local_sessionmaker

    def get_engine(self, shop_code: str) -> Engine:
        validated_shop = self.validate_shop_code(shop_code)
        self._ensure_sessionmaker(validated_shop)
        return self._engines[validated_shop]

    def get_session(self, shop_code: str) -> Session:
        maker = self._ensure_sessionmaker(shop_code)
        return maker()

    @contextmanager
    def session_scope(self, shop_code: str) -> Generator[Session, None, None]:
        db = self.get_session(shop_code)
        try:
            yield db
        finally:
            db.close()


tenant_db_manager = TenantDBManager(settings.shop_databases)
