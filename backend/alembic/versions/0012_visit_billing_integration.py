"""visit billing integration

Revision ID: 0012_visit_billing_integration
Revises: 0011_dispensing_orders
Create Date: 2026-06-18 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0012_visit_billing_integration"
down_revision: str | None = "0011_dispensing_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    add_visit_id = not _has_column("bills", "visit_id")
    add_dispensing_order_id = not _has_column("bills", "dispensing_order_id")
    if add_visit_id or add_dispensing_order_id:
        with op.batch_alter_table("bills") as batch_op:
            if add_visit_id:
                batch_op.add_column(sa.Column("visit_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_bills_visit_id",
                    "visits",
                    ["visit_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
            if add_dispensing_order_id:
                batch_op.add_column(sa.Column("dispensing_order_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_bills_dispensing_order_id",
                    "dispensing_orders",
                    ["dispensing_order_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
    if not _has_index("bills", "ix_bills_visit_id"):
        op.create_index("ix_bills_visit_id", "bills", ["visit_id"], unique=False)
    if not _has_index("bills", "ix_bills_dispensing_order_id"):
        op.create_index("ix_bills_dispensing_order_id", "bills", ["dispensing_order_id"], unique=False)
    if not _has_index("bills", "uq_bills_active_dispensing_order"):
        op.create_index(
            "uq_bills_active_dispensing_order",
            "bills",
            ["dispensing_order_id"],
            unique=True,
            postgresql_where=sa.text("dispensing_order_id IS NOT NULL AND NOT is_deleted"),
            sqlite_where=sa.text("dispensing_order_id IS NOT NULL AND is_deleted = 0"),
        )


def downgrade() -> None:
    if _has_index("bills", "uq_bills_active_dispensing_order"):
        op.drop_index("uq_bills_active_dispensing_order", table_name="bills")
    if _has_index("bills", "ix_bills_dispensing_order_id"):
        op.drop_index("ix_bills_dispensing_order_id", table_name="bills")
    if _has_index("bills", "ix_bills_visit_id"):
        op.drop_index("ix_bills_visit_id", table_name="bills")
    drop_dispensing_order_id = _has_column("bills", "dispensing_order_id")
    drop_visit_id = _has_column("bills", "visit_id")
    if drop_dispensing_order_id or drop_visit_id:
        with op.batch_alter_table("bills") as batch_op:
            if drop_dispensing_order_id:
                batch_op.drop_constraint("fk_bills_dispensing_order_id", type_="foreignkey")
                batch_op.drop_column("dispensing_order_id")
            if drop_visit_id:
                batch_op.drop_constraint("fk_bills_visit_id", type_="foreignkey")
                batch_op.drop_column("visit_id")
