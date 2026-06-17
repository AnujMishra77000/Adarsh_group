from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.shop_scope import require_same_shop
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository


def find_shop_with_email(email: str, exclude_shop_key: str | None = None, db: Session | None = None) -> str | None:
    """
    Returns the first shop key where the email already exists, excluding current shop.
    This enforces global credential uniqueness in the single shared database.
    """
    if not settings.auth_enforce_global_email_uniqueness:
        return None

    normalized_email = email.strip().lower()
    owns_session = db is None
    active_db = db or SessionLocal()
    try:
        user = UserRepository(active_db).get_by_email(normalized_email)
        if user is None:
            return None
        if exclude_shop_key and require_same_shop(user, active_db, exclude_shop_key):
            return None
        if user.shop_key:
            return user.shop_key
        return user.shop.code if user.shop else None
    finally:
        if owns_session:
            active_db.close()
