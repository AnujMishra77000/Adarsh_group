from __future__ import annotations

from app.core.config import settings
from app.db.tenant import tenant_db_manager
from app.repositories.user_repository import UserRepository


def find_shop_with_email(email: str, exclude_shop_key: str | None = None) -> str | None:
    """
    Returns the first shop key where the email already exists, excluding current shop.
    This enforces shop-level credential isolation even with multiple tenant databases.
    """
    if not settings.auth_enforce_global_email_uniqueness:
        return None

    normalized_email = email.strip().lower()
    normalized_exclude = exclude_shop_key.strip().lower() if exclude_shop_key else None

    for shop_code in sorted(tenant_db_manager.shop_codes):
        if normalized_exclude and shop_code == normalized_exclude:
            continue

        with tenant_db_manager.session_scope(shop_code) as db:
            repo = UserRepository(db)
            if repo.get_by_email(normalized_email):
                return shop_code

    return None
