"""order completion, delivery, and follow-ups

Revision ID: 0014_order_completion_followups
Revises: 0013_contact_lens_workflow
Create Date: 2026-06-18 16:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_order_completion_followups"
down_revision: str | None = "0013_contact_lens_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


reminder_state_enum = sa.Enum(
    "not_scheduled",
    "scheduled",
    "sent",
    "failed",
    name="follow_up_reminder_state",
)


def upgrade() -> None:
    reminder_state_enum.create(op.get_bind(), checkfirst=True)

    for table_name in ("dispensing_orders", "contact_lens_orders"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("expected_delivery_date", sa.Date(), nullable=True))
            batch_op.add_column(sa.Column("delivered_by", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table_name}_delivered_by",
                "users",
                ["delivered_by"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index(f"ix_{table_name}_expected_delivery_date", ["expected_delivery_date"])

    op.create_table(
        "order_status_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("shop_key", sa.String(length=64), nullable=False),
        sa.Column(
            "dispensing_order_id",
            sa.Integer(),
            sa.ForeignKey("dispensing_orders.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "contact_lens_order_id",
            sa.Integer(),
            sa.ForeignKey("contact_lens_orders.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("previous_status", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "(dispensing_order_id IS NOT NULL AND contact_lens_order_id IS NULL) OR "
            "(dispensing_order_id IS NULL AND contact_lens_order_id IS NOT NULL)",
            name="ck_order_status_events_single_order",
        ),
    )
    for index_name, columns in (
        ("ix_order_status_events_shop_id", ["shop_id"]),
        ("ix_order_status_events_shop_key", ["shop_key"]),
        ("ix_order_status_events_dispensing_order_id", ["dispensing_order_id"]),
        ("ix_order_status_events_contact_lens_order_id", ["contact_lens_order_id"]),
        ("ix_order_status_events_event", ["event"]),
        ("ix_order_status_events_occurred_at", ["occurred_at"]),
    ):
        op.create_index(index_name, "order_status_events", columns, unique=False)

    with op.batch_alter_table("follow_up_tasks") as batch_op:
        batch_op.drop_constraint("uq_follow_up_tasks_contact_lens_order_id", type_="unique")
        batch_op.alter_column("contact_lens_order_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("interval", existing_type=sa.String(length=32), nullable=True)
        batch_op.add_column(sa.Column("assigned_staff_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "reminder_state",
                reminder_state_enum,
                nullable=False,
                server_default="not_scheduled",
            )
        )
        batch_op.add_column(sa.Column("completion_notes", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_follow_up_tasks_assigned_staff_id",
            "users",
            ["assigned_staff_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_follow_up_tasks_task_type", ["task_type"])
        batch_op.create_index("ix_follow_up_tasks_assigned_staff_id", ["assigned_staff_id"])
        batch_op.create_index("ix_follow_up_tasks_reminder_state", ["reminder_state"])

    op.execute(sa.text("UPDATE follow_up_tasks SET task_type = 'contact_lens' WHERE task_type = 'contact_lens_review'"))


def downgrade() -> None:
    with op.batch_alter_table("follow_up_tasks") as batch_op:
        batch_op.drop_index("ix_follow_up_tasks_reminder_state")
        batch_op.drop_index("ix_follow_up_tasks_assigned_staff_id")
        batch_op.drop_index("ix_follow_up_tasks_task_type")
        batch_op.drop_constraint("fk_follow_up_tasks_assigned_staff_id", type_="foreignkey")
        batch_op.drop_column("completion_notes")
        batch_op.drop_column("reminder_state")
        batch_op.drop_column("assigned_staff_id")
        batch_op.alter_column("interval", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column("contact_lens_order_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint(
            "uq_follow_up_tasks_contact_lens_order_id",
            ["contact_lens_order_id"],
        )

    op.drop_table("order_status_events")

    for table_name in ("contact_lens_orders", "dispensing_orders"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_expected_delivery_date")
            batch_op.drop_constraint(f"fk_{table_name}_delivered_by", type_="foreignkey")
            batch_op.drop_column("delivered_at")
            batch_op.drop_column("delivered_by")
            batch_op.drop_column("expected_delivery_date")

    reminder_state_enum.drop(op.get_bind(), checkfirst=True)
