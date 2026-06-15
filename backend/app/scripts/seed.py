from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.tenant import tenant_db_manager
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository


def _shop_specific_email(prefix: str, shop_code: str) -> str:
    return f"{prefix}+{shop_code}@aadarsh-eye.com"


def seed_users(db: Session, shop_code: str) -> None:
    user_repo = UserRepository(db)
    admin_email = _shop_specific_email("admin", shop_code)
    staff_email = _shop_specific_email("staff", shop_code)

    if not user_repo.get_by_email(admin_email):
        user_repo.create(
            email=admin_email,
            full_name="Aadarsh Admin",
            password_hash=get_password_hash("Admin@12345"),
            role=UserRole.ADMIN,
            shop_key=shop_code,
        )

    if not user_repo.get_by_email(staff_email):
        user_repo.create(
            email=staff_email,
            full_name="Aadarsh Staff",
            password_hash=get_password_hash("Staff@12345"),
            role=UserRole.STAFF,
            shop_key=shop_code,
        )


def main() -> None:
    if not tenant_db_manager.shop_codes:
        raise SystemExit("SHOP_DATABASES is empty. Configure tenant database mapping before seeding.")

    for shop_code in sorted(tenant_db_manager.shop_codes):
        with tenant_db_manager.session_scope(shop_code) as db:
            seed_users(db, shop_code=shop_code)
            db.commit()


if __name__ == "__main__":
    main()
