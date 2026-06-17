"""multi item billing

Revision ID: 0007_multi_item_billing
Revises: 0006_single_db_shop_foundation
Create Date: 2026-06-16 21:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_multi_item_billing"
down_revision: str | None = "0006_single_db_shop_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


bill_item_type_enum = sa.Enum(
    "frame",
    "lens",
    "coating",
    "contact_lens",
    "eye_test",
    "repair",
    "accessory",
    "other",
    name="bill_item_type",
)
payment_mode_enum = sa.Enum("cash", "upi", "card", "bank_transfer", "other", name="payment_mode", create_type=False)


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _add_payment_mode_values() -> None:
    if _dialect_name() != "postgresql":
        return

    for value in ("card", "bank_transfer", "other"):
        op.execute(sa.text(f"ALTER TYPE payment_mode ADD VALUE IF NOT EXISTS '{value}'"))


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _has_index(table_name, index_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def _add_bill_total_columns() -> None:
    additions = (
        ("subtotal", "whole_price"),
        ("discount_total", "discount"),
        ("tax_total", None),
        ("grand_total", "final_price"),
        ("paid_total", "paid_amount"),
    )

    for column_name, source_column in additions:
        if not _has_column("bills", column_name):
            with op.batch_alter_table("bills", schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        column_name,
                        sa.Numeric(12, 2),
                        nullable=False,
                        server_default="0",
                    )
                )

        if source_column is not None:
            op.execute(
                sa.text(
                    f"""
                    UPDATE bills
                    SET {column_name} = COALESCE({source_column}, 0)
                    WHERE {column_name} = 0
                    """
                )
            )


def _create_bill_items_table() -> None:
    if _has_table("bill_items"):
        return

    bind = op.get_bind()
    bill_item_type_enum.create(bind, checkfirst=True)
    op.create_table(
        "bill_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("bill_id", sa.Integer(), sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", bill_item_type_enum, nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    _create_index_if_missing("ix_bill_items_shop_id", "bill_items", ["shop_id"])
    _create_index_if_missing("ix_bill_items_bill_id", "bill_items", ["bill_id"])


def _create_payments_table() -> None:
    if _has_table("payments"):
        return

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("bill_id", sa.Integer(), sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", payment_mode_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_no", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    _create_index_if_missing("ix_payments_shop_id", "payments", ["shop_id"])
    _create_index_if_missing("ix_payments_bill_id", "payments", ["bill_id"])


def _backfill_bill_items() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO bill_items (
                shop_id,
                bill_id,
                item_type,
                item_name,
                quantity,
                unit_price,
                discount,
                line_total,
                created_at,
                updated_at
            )
            SELECT
                bills.shop_id,
                bills.id,
                CASE WHEN bills.frame_name IS NOT NULL AND bills.frame_name != '' THEN 'frame' ELSE 'other' END,
                bills.product_name,
                1,
                bills.whole_price,
                bills.discount,
                bills.final_price,
                bills.created_at,
                bills.updated_at
            FROM bills
            WHERE NOT EXISTS (
                SELECT 1
                FROM bill_items
                WHERE bill_items.bill_id = bills.id
            )
            """
        )
    )


def _backfill_payments() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO payments (
                shop_id,
                bill_id,
                mode,
                amount,
                paid_at,
                created_at,
                updated_at
            )
            SELECT
                bills.shop_id,
                bills.id,
                bills.payment_mode,
                bills.paid_amount,
                COALESCE(bills.created_at, CURRENT_TIMESTAMP),
                bills.created_at,
                bills.updated_at
            FROM bills
            WHERE bills.paid_amount > 0
              AND NOT EXISTS (
                SELECT 1
                FROM payments
                WHERE payments.bill_id = bills.id
            )
            """
        )
    )


def upgrade() -> None:
    _add_payment_mode_values()
    _add_bill_total_columns()
    _create_bill_items_table()
    _create_payments_table()
    _backfill_bill_items()
    _backfill_payments()


def downgrade() -> None:
    if _has_table("payments"):
        op.drop_table("payments")

    if _has_table("bill_items"):
        op.drop_table("bill_items")

    with op.batch_alter_table("bills", schema=None) as batch_op:
        for column_name in ("paid_total", "grand_total", "tax_total", "discount_total", "subtotal"):
            if _has_column("bills", column_name):
                batch_op.drop_column(column_name)

    if _dialect_name() == "postgresql":
        bill_item_type_enum.drop(op.get_bind(), checkfirst=True)
