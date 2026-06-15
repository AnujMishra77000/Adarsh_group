"""add shop_key isolation columns

Revision ID: 0003_add_shop_key_isolation
Revises: 0002_add_customer_email
Create Date: 2026-04-17 16:25:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_add_shop_key_isolation"
down_revision: str | None = "0002_add_customer_email"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_SHOP_KEY = "aadarsh-eye-boutique-center"


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _add_shop_key_column_if_missing(table_name: str) -> None:
    if _has_column(table_name, "shop_key"):
        return

    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "shop_key",
                sa.String(length=64),
                nullable=False,
                server_default=DEFAULT_SHOP_KEY,
            )
        )


def _create_shop_key_index_if_missing(table_name: str, index_name: str) -> None:
    if _has_index(table_name, index_name):
        return
    op.create_index(index_name, table_name, ["shop_key"], unique=False)


def _backfill_shop_key(table_name: str) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(f"UPDATE {table_name} SET shop_key = :shop_key WHERE shop_key IS NULL"),
        {"shop_key": DEFAULT_SHOP_KEY},
    )


def upgrade() -> None:
    _add_shop_key_column_if_missing("users")
    _add_shop_key_column_if_missing("customers")
    _add_shop_key_column_if_missing("campaigns")

    _backfill_shop_key("users")
    _backfill_shop_key("customers")
    _backfill_shop_key("campaigns")

    _create_shop_key_index_if_missing("users", "ix_users_shop_key")
    _create_shop_key_index_if_missing("customers", "ix_customers_shop_key")
    _create_shop_key_index_if_missing("campaigns", "ix_campaigns_shop_key")


def downgrade() -> None:
    if _has_index("campaigns", "ix_campaigns_shop_key"):
        op.drop_index("ix_campaigns_shop_key", table_name="campaigns")
    if _has_index("customers", "ix_customers_shop_key"):
        op.drop_index("ix_customers_shop_key", table_name="customers")
    if _has_index("users", "ix_users_shop_key"):
        op.drop_index("ix_users_shop_key", table_name="users")

    if _has_column("campaigns", "shop_key"):
        with op.batch_alter_table("campaigns", schema=None) as batch_op:
            batch_op.drop_column("shop_key")

    if _has_column("customers", "shop_key"):
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.drop_column("shop_key")

    if _has_column("users", "shop_key"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.drop_column("shop_key")
