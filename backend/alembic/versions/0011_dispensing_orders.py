"""spectacle dispensing orders

Revision ID: 0011_dispensing_orders
Revises: 0010_visit_prescription_versions
Create Date: 2026-06-18 11:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011_dispensing_orders"
down_revision: str | None = "0010_visit_prescription_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


dispensing_order_status_enum = sa.Enum(
    "draft",
    "ready_for_vendor",
    "sent_to_vendor",
    "in_production",
    "ready_for_delivery",
    "delivered",
    "cancelled",
    name="dispensing_order_status",
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE whatsapp_module_type ADD VALUE IF NOT EXISTS 'dispensing_order'")

    if _has_table("dispensing_orders"):
        return

    dispensing_order_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "dispensing_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("shop_key", sa.String(length=64), nullable=False),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "prescription_id",
            sa.Integer(),
            sa.ForeignKey("visit_prescriptions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("order_reference", sa.String(length=64), nullable=False),
        sa.Column("status", dispensing_order_status_enum, nullable=False, server_default="draft"),
        sa.Column("frame_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("measurement_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("lens_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("manufacturing_instructions", sa.Text(), nullable=True),
        sa.Column("vendor_document_file_path", sa.Text(), nullable=True),
        sa.Column("sent_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("visit_id", name="uq_dispensing_orders_visit_id"),
        sa.UniqueConstraint("shop_id", "order_reference", name="uq_dispensing_orders_shop_reference"),
    )
    for index_name, columns in (
        ("ix_dispensing_orders_shop_id", ["shop_id"]),
        ("ix_dispensing_orders_shop_key", ["shop_key"]),
        ("ix_dispensing_orders_visit_id", ["visit_id"]),
        ("ix_dispensing_orders_customer_id", ["customer_id"]),
        ("ix_dispensing_orders_prescription_id", ["prescription_id"]),
        ("ix_dispensing_orders_vendor_id", ["vendor_id"]),
        ("ix_dispensing_orders_order_reference", ["order_reference"]),
        ("ix_dispensing_orders_status", ["status"]),
    ):
        _create_index_if_missing(index_name, "dispensing_orders", columns)


def downgrade() -> None:
    if _has_table("dispensing_orders"):
        op.drop_table("dispensing_orders")
    dispensing_order_status_enum.drop(op.get_bind(), checkfirst=True)

