"""single database shop foundation

Revision ID: 0006_single_db_shop_foundation
Revises: 0005_add_private_document_file_paths
Create Date: 2026-06-16 18:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_single_db_shop_foundation"
down_revision: str | None = "0005_add_private_document_file_paths"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SHOP_ROWS = (
    {
        "code": "adarsh-optical-centre",
        "display_name": "Adarsh Optical Centre",
        "location_label": "",
        "center_type": "Optical centre",
        "is_active": True,
    },
    {
        "code": "adarsh-optometric-clinic",
        "display_name": "Adarsh Optometric Clinic",
        "location_label": "Khadakpada, Kalyan West",
        "center_type": "Optometric clinic",
        "is_active": True,
    },
    {
        "code": "adarsh-opticals-muxar",
        "display_name": "Adarsh Opticals",
        "location_label": "Near Muxar Hospital",
        "center_type": "Optical centre",
        "is_active": True,
    },
    {
        "code": "adarsh-eye-boutique",
        "display_name": "Adarsh Eye Boutique",
        "location_label": "",
        "center_type": "Eye boutique",
        "is_active": True,
    },
)

LEGACY_TO_CANONICAL = {
    "aadarsh-eye-boutique-center": "adarsh-eye-boutique",
    "adarsh-optometric-center": "adarsh-optometric-clinic",
    "adarsh-optical-center": "adarsh-optical-centre",
}

SHOP_ID_TABLES = (
    "users",
    "customers",
    "prescriptions",
    "bills",
    "vendors",
    "campaigns",
    "campaign_logs",
    "whatsapp_logs",
    "audit_logs",
    "chat_messages",
)


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


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _has_index(table_name, index_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_present(index_name: str, table_name: str) -> None:
    if _has_index(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _create_shops_table() -> None:
    if _has_table("shops"):
        return

    op.create_table(
        "shops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("location_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("center_type", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_shops_code", "shops", ["code"], unique=True)
    op.create_index("ix_shops_is_active", "shops", ["is_active"], unique=False)


def _seed_shops() -> None:
    bind = op.get_bind()
    for shop in SHOP_ROWS:
        bind.execute(
            sa.text(
                """
                INSERT INTO shops (code, display_name, location_label, center_type, is_active)
                SELECT :code, :display_name, :location_label, :center_type, :is_active
                WHERE NOT EXISTS (SELECT 1 FROM shops WHERE code = :code)
                """
            ),
            shop,
        )


def _add_shop_id_column(table_name: str) -> None:
    if not _has_table(table_name) or _has_column(table_name, "shop_id"):
        return

    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.add_column(sa.Column("shop_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_shop_id_shops",
            "shops",
            ["shop_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    _create_index_if_missing(f"ix_{table_name}_shop_id", table_name, ["shop_id"])


def _canonical_case_expression(column_name: str) -> str:
    cases = " ".join(
        f"WHEN {column_name} = '{legacy}' THEN '{canonical}'"
        for legacy, canonical in LEGACY_TO_CANONICAL.items()
    )
    return f"CASE {cases} ELSE {column_name} END"


def _backfill_from_shop_key(table_name: str, column_name: str = "shop_key") -> None:
    if not (_has_table(table_name) and _has_column(table_name, "shop_id") and _has_column(table_name, column_name)):
        return

    canonical_expr = _canonical_case_expression(column_name)
    op.get_bind().execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET shop_id = (
                SELECT shops.id
                FROM shops
                WHERE shops.code = {canonical_expr}
            )
            WHERE shop_id IS NULL
            """
        )
    )


def _backfill_from_parent(child_table: str, parent_table: str, fk_column: str) -> None:
    if not (_has_table(child_table) and _has_table(parent_table) and _has_column(child_table, "shop_id")):
        return

    op.get_bind().execute(
        sa.text(
            f"""
            UPDATE {child_table}
            SET shop_id = (
                SELECT {parent_table}.shop_id
                FROM {parent_table}
                WHERE {parent_table}.id = {child_table}.{fk_column}
            )
            WHERE shop_id IS NULL
            """
        )
    )


def _backfill_whatsapp_logs() -> None:
    if not (_has_table("whatsapp_logs") and _has_column("whatsapp_logs", "shop_id")):
        return

    op.get_bind().execute(
        sa.text(
            """
            UPDATE whatsapp_logs
            SET shop_id = COALESCE(
                (SELECT customers.shop_id FROM customers WHERE customers.id = whatsapp_logs.customer_id),
                (SELECT vendors.shop_id FROM vendors WHERE vendors.id = whatsapp_logs.vendor_id)
            )
            WHERE shop_id IS NULL
            """
        )
    )


def _backfill_audit_logs() -> None:
    if not (_has_table("audit_logs") and _has_column("audit_logs", "shop_id")):
        return

    op.get_bind().execute(
        sa.text(
            """
            UPDATE audit_logs
            SET shop_id = (
                SELECT users.shop_id
                FROM users
                WHERE users.id = audit_logs.actor_user_id
            )
            WHERE shop_id IS NULL
            """
        )
    )


def upgrade() -> None:
    _create_shops_table()
    _seed_shops()

    for table_name in SHOP_ID_TABLES:
        _add_shop_id_column(table_name)

    _backfill_from_shop_key("users")
    _backfill_from_shop_key("customers")
    _backfill_from_shop_key("campaigns")
    _backfill_from_shop_key("chat_messages", column_name="sender_shop_key")
    _backfill_from_parent("prescriptions", "customers", "customer_id")
    _backfill_from_parent("bills", "customers", "customer_id")
    _backfill_from_parent("campaign_logs", "campaigns", "campaign_id")
    _backfill_whatsapp_logs()
    _backfill_audit_logs()

    _drop_index_if_present("ix_customers_customer_id", "customers")
    _drop_index_if_present("ix_bills_bill_number", "bills")
    _create_index_if_missing("ix_customers_shop_id_customer_id", "customers", ["shop_id", "customer_id"], unique=True)
    _create_index_if_missing("ix_bills_shop_id_bill_number", "bills", ["shop_id", "bill_number"], unique=True)
    _create_index_if_missing("ix_campaign_logs_shop_id_campaign_id", "campaign_logs", ["shop_id", "campaign_id"])
    _create_index_if_missing("ix_whatsapp_logs_shop_id_created_at", "whatsapp_logs", ["shop_id", "created_at"])
    _create_index_if_missing("ix_audit_logs_shop_id_created_at", "audit_logs", ["shop_id", "created_at"])
    _create_index_if_missing("ix_chat_messages_shop_id_created_at", "chat_messages", ["shop_id", "created_at"])


def downgrade() -> None:
    _drop_index_if_present("ix_chat_messages_shop_id_created_at", "chat_messages")
    _drop_index_if_present("ix_audit_logs_shop_id_created_at", "audit_logs")
    _drop_index_if_present("ix_whatsapp_logs_shop_id_created_at", "whatsapp_logs")
    _drop_index_if_present("ix_campaign_logs_shop_id_campaign_id", "campaign_logs")
    _drop_index_if_present("ix_bills_shop_id_bill_number", "bills")
    _drop_index_if_present("ix_customers_shop_id_customer_id", "customers")
    _create_index_if_missing("ix_bills_bill_number", "bills", ["bill_number"], unique=True)
    _create_index_if_missing("ix_customers_customer_id", "customers", ["customer_id"], unique=True)

    for table_name in reversed(SHOP_ID_TABLES):
        if not _has_column(table_name, "shop_id"):
            continue
        _drop_index_if_present(f"ix_{table_name}_shop_id", table_name)
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_constraint(f"fk_{table_name}_shop_id_shops", type_="foreignkey")
            batch_op.drop_column("shop_id")

    if _has_table("shops"):
        _drop_index_if_present("ix_shops_is_active", "shops")
        _drop_index_if_present("ix_shops_code", "shops")
        op.drop_table("shops")
