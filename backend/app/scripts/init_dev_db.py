from __future__ import annotations

from app.db.base import Base
from app.db.tenant import tenant_db_manager
from app.scripts.seed import seed_users


def main() -> None:
    if not tenant_db_manager.shop_codes:
        raise SystemExit("SHOP_DATABASES is empty. Configure tenant database mapping before init.")

    for shop_code in sorted(tenant_db_manager.shop_codes):
        engine = tenant_db_manager.get_engine(shop_code)
        Base.metadata.create_all(bind=engine)

        with tenant_db_manager.session_scope(shop_code) as db:
            # Local development initializer: keep it deterministic and simple.
            seed_users(db, shop_code=shop_code)
            db.commit()


if __name__ == "__main__":
    main()
