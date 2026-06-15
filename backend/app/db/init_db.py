from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.core.shops import DEFAULT_SHOP_KEY
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository


def init_db(db: Session) -> None:
    user_repo = UserRepository(db)
    bootstrap_email = "admin@aadarsh-eye.local"

    if user_repo.get_by_email(bootstrap_email):
        return

    user_repo.create(
        email=bootstrap_email,
        full_name="System Administrator",
        password_hash=get_password_hash(settings.admin_master_password),
        role=UserRole.ADMIN,
        shop_key=DEFAULT_SHOP_KEY,
        is_active=True,
    )
    db.commit()
