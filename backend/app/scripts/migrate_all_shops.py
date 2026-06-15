from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings


def main() -> None:
    if not settings.shop_databases:
        raise SystemExit("SHOP_DATABASES is empty. Configure shop database mapping first.")

    backend_dir = Path(__file__).resolve().parents[2]
    alembic_ini = backend_dir / "alembic.ini"

    for shop_code, database_uri in sorted(settings.shop_databases.items()):
        config = Config(str(alembic_ini))
        config.set_main_option("sqlalchemy.url", database_uri)
        print(f"Running migrations for {shop_code} ...")
        command.upgrade(config, "head")

    print("All shop databases migrated successfully.")


if __name__ == "__main__":
    main()
