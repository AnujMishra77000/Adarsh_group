from __future__ import annotations

import os
from collections.abc import Callable, Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-enough-length-for-local-and-ci")
os.environ.setdefault("ADMIN_MASTER_PASSWORD", "test-admin-master-password")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("BACKEND_CORS_ORIGINS", '["http://localhost:5173"]')

from app.db.base import Base  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402

TEST_SHOP_ONE = "adarsh-optical-centre"
TEST_SHOP_TWO = "adarsh-eye-boutique"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def make_user(db_session: Session) -> Callable[..., User]:
    def _make_user(
        email: str,
        shop_key: str = TEST_SHOP_ONE,
        role: UserRole = UserRole.ADMIN,
    ) -> User:
        user = User(
            email=email.lower(),
            full_name=email.split("@")[0],
            password_hash="not-used-in-service-tests",
            role=role,
            shop_key=shop_key,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make_user
