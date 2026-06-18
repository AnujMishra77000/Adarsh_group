"""contact lens workflow

Revision ID: 0013_contact_lens_workflow
Revises: 0012_visit_billing_integration
Create Date: 2026-06-18 13:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0013_contact_lens_workflow"
down_revision: str | None = "0012_visit_billing_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


follow_up_status_enum = sa.Enum("pending", "completed", "cancelled", name="follow_up_status")
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


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if not _has_column("visits", "contact_lens_workup_requested"):
        with op.batch_alter_table("visits") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "contact_lens_workup_requested",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )

    if not _has_table("contact_lens_orders"):
        op.create_table(
            "contact_lens_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("shop_key", sa.String(length=64), nullable=False),
            sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("order_reference", sa.String(length=64), nullable=False),
            sa.Column("status", dispensing_order_status_enum, nullable=False, server_default="draft"),
            sa.Column("workup_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("lens_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("order_notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("visit_id", name="uq_contact_lens_orders_visit_id"),
            sa.UniqueConstraint("shop_id", "order_reference", name="uq_contact_lens_orders_shop_reference"),
        )
        for index_name, columns in (
            ("ix_contact_lens_orders_shop_id", ["shop_id"]),
            ("ix_contact_lens_orders_shop_key", ["shop_key"]),
            ("ix_contact_lens_orders_visit_id", ["visit_id"]),
            ("ix_contact_lens_orders_customer_id", ["customer_id"]),
            ("ix_contact_lens_orders_vendor_id", ["vendor_id"]),
            ("ix_contact_lens_orders_order_reference", ["order_reference"]),
            ("ix_contact_lens_orders_status", ["status"]),
        ):
            op.create_index(index_name, "contact_lens_orders", columns, unique=False)

    if not _has_table("follow_up_tasks"):
        follow_up_status_enum.create(op.get_bind(), checkfirst=True)
        op.create_table(
            "follow_up_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("shop_key", sa.String(length=64), nullable=False),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("contact_lens_order_id", sa.Integer(), sa.ForeignKey("contact_lens_orders.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("task_type", sa.String(length=64), nullable=False, server_default="contact_lens_review"),
            sa.Column("interval", sa.String(length=32), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("status", follow_up_status_enum, nullable=False, server_default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("completed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("contact_lens_order_id", name="uq_follow_up_tasks_contact_lens_order_id"),
        )
        for index_name, columns in (
            ("ix_follow_up_tasks_shop_id", ["shop_id"]),
            ("ix_follow_up_tasks_shop_key", ["shop_key"]),
            ("ix_follow_up_tasks_customer_id", ["customer_id"]),
            ("ix_follow_up_tasks_visit_id", ["visit_id"]),
            ("ix_follow_up_tasks_contact_lens_order_id", ["contact_lens_order_id"]),
            ("ix_follow_up_tasks_due_date", ["due_date"]),
            ("ix_follow_up_tasks_status", ["status"]),
        ):
            op.create_index(index_name, "follow_up_tasks", columns, unique=False)

    if not _has_column("bills", "contact_lens_order_id"):
        with op.batch_alter_table("bills") as batch_op:
            batch_op.add_column(sa.Column("contact_lens_order_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_bills_contact_lens_order_id",
                "contact_lens_orders",
                ["contact_lens_order_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    if not _has_index("bills", "ix_bills_contact_lens_order_id"):
        op.create_index("ix_bills_contact_lens_order_id", "bills", ["contact_lens_order_id"], unique=False)
    if not _has_index("bills", "uq_bills_active_contact_lens_order"):
        op.create_index(
            "uq_bills_active_contact_lens_order",
            "bills",
            ["contact_lens_order_id"],
            unique=True,
            postgresql_where=sa.text("contact_lens_order_id IS NOT NULL AND NOT is_deleted"),
            sqlite_where=sa.text("contact_lens_order_id IS NOT NULL AND is_deleted = 0"),
        )


def downgrade() -> None:
    if _has_index("bills", "uq_bills_active_contact_lens_order"):
        op.drop_index("uq_bills_active_contact_lens_order", table_name="bills")
    if _has_index("bills", "ix_bills_contact_lens_order_id"):
        op.drop_index("ix_bills_contact_lens_order_id", table_name="bills")
    if _has_column("bills", "contact_lens_order_id"):
        with op.batch_alter_table("bills") as batch_op:
            batch_op.drop_constraint("fk_bills_contact_lens_order_id", type_="foreignkey")
            batch_op.drop_column("contact_lens_order_id")
    if _has_table("follow_up_tasks"):
        op.drop_table("follow_up_tasks")
    follow_up_status_enum.drop(op.get_bind(), checkfirst=True)
    if _has_table("contact_lens_orders"):
        op.drop_table("contact_lens_orders")
    if _has_column("visits", "contact_lens_workup_requested"):
        with op.batch_alter_table("visits") as batch_op:
            batch_op.drop_column("contact_lens_workup_requested")
