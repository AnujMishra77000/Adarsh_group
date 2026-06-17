from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import VALID_SHOP_CODES, VALID_SHOP_KEYS, get_canonical_shop_code, get_shop_aliases, normalize_shop_code


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
        self._shop_databases: dict[str, str] = {}
        self._canonical_to_database_key: dict[str, str] = {}
        self._accepted_shop_codes: set[str] = set()

        for raw_shop_code, database_uri in shop_databases.items():
            database_key = normalize_shop_code(raw_shop_code)
            if not database_key:
                continue

            self._shop_databases[database_key] = database_uri

            canonical_code = get_canonical_shop_code(database_key) or database_key
            existing_database_key = self._canonical_to_database_key.get(canonical_code)
            if existing_database_key is not None and existing_database_key != database_key:
                raise ValueError(
                    "SHOP_DATABASES contains multiple entries for the same shop: "
                    f"{existing_database_key!r} and {database_key!r}"
                )

            self._canonical_to_database_key[canonical_code] = database_key
            self._accepted_shop_codes.update(get_shop_aliases(canonical_code))
            self._accepted_shop_codes.add(database_key)

        self._engines: dict[str, Engine] = {}
        self._sessionmakers: dict[str, sessionmaker[Session]] = {}
        self._lock = Lock()

    @property
    def shop_codes(self) -> set[str]:
        if not self._shop_databases:
            return set(VALID_SHOP_KEYS)
        return set(self._accepted_shop_codes)

    @property
    def database_shop_codes(self) -> set[str]:
        if not self._shop_databases:
            return set(VALID_SHOP_CODES)
        return set(self._shop_databases.keys())

    def validate_shop_code(self, shop_code: str) -> str:
        normalized = normalize_shop_code(shop_code)
        if not normalized:
            raise AppException(status_code=400, code="missing_shop_code", message="Shop context is required")

        if not self._shop_databases:
            canonical_code = get_canonical_shop_code(normalized)
            if canonical_code is None:
                raise AppException(status_code=400, code="invalid_shop_code", message="Invalid shop context")
            return canonical_code

        if normalized in self._shop_databases:
            return normalized

        canonical_code = get_canonical_shop_code(normalized) or normalized
        database_key = self._canonical_to_database_key.get(canonical_code)
        if database_key is None:
            raise AppException(status_code=400, code="invalid_shop_code", message="Invalid shop context")
        return database_key

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
        if not self._shop_databases:
            from app.db.session import engine

            return engine
        self._ensure_sessionmaker(validated_shop)
        return self._engines[validated_shop]

    def get_session(self, shop_code: str) -> Session:
        if not self._shop_databases:
            self.validate_shop_code(shop_code)
            from app.db.session import SessionLocal

            return SessionLocal()
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
