"""patient visit foundation

Revision ID: 0008_patient_visit_foundation
Revises: 0007_multi_item_billing
Create Date: 2026-06-17 14:20:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008_patient_visit_foundation"
down_revision: str | None = "0007_multi_item_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


visit_status_enum = sa.Enum("draft", "in_progress", "completed", "cancelled", name="visit_status")


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


def _add_customer_patient_columns() -> None:
    additions = (
        ("occupation", sa.String(length=255)),
        ("guardian_name", sa.String(length=255)),
        ("guardian_contact_no", sa.String(length=20)),
        ("registration_idempotency_key", sa.String(length=120)),
    )
    for column_name, column_type in additions:
        if _has_column("customers", column_name):
            continue
        with op.batch_alter_table("customers", schema=None) as batch_op:
            batch_op.add_column(sa.Column(column_name, column_type, nullable=True))

    _create_index_if_missing(
        "ix_customers_registration_idempotency_key",
        "customers",
        ["registration_idempotency_key"],
    )
    _create_index_if_missing(
        "uq_customers_shop_key_registration_idempotency_key",
        "customers",
        ["shop_key", "registration_idempotency_key"],
        unique=True,
    )


def _create_visits_table() -> None:
    if _has_table("visits"):
        return

    visit_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("shop_key", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason_for_visit", sa.String(length=255), nullable=False),
        sa.Column("referred_by", sa.String(length=255), nullable=True),
        sa.Column("assigned_examiner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("visit_notes", sa.Text(), nullable=True),
        sa.Column("status", visit_status_enum, nullable=False, server_default="draft"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    _create_index_if_missing("ix_visits_shop_id", "visits", ["shop_id"])
    _create_index_if_missing("ix_visits_shop_key", "visits", ["shop_key"])
    _create_index_if_missing("ix_visits_customer_id", "visits", ["customer_id"])
    _create_index_if_missing("ix_visits_visit_date", "visits", ["visit_date"])
    _create_index_if_missing("ix_visits_status", "visits", ["status"])
    _create_index_if_missing("ix_visits_assigned_examiner_id", "visits", ["assigned_examiner_id"])
    _create_index_if_missing("ix_visits_idempotency_key", "visits", ["idempotency_key"])
    _create_index_if_missing(
        "uq_visits_shop_key_idempotency_key",
        "visits",
        ["shop_key", "idempotency_key"],
        unique=True,
    )


def upgrade() -> None:
    _add_customer_patient_columns()
    _create_visits_table()


def downgrade() -> None:
    if _has_table("visits"):
        op.drop_table("visits")
    visit_status_enum.drop(op.get_bind(), checkfirst=True)

    _drop_index_if_present("uq_customers_shop_key_registration_idempotency_key", "customers")
    _drop_index_if_present("ix_customers_registration_idempotency_key", "customers")
    with op.batch_alter_table("customers", schema=None) as batch_op:
        for column_name in (
            "registration_idempotency_key",
            "guardian_contact_no",
            "guardian_name",
            "occupation",
        ):
            if _has_column("customers", column_name):
                batch_op.drop_column(column_name)
