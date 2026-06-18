"""visit prescription versions

Revision ID: 0010_visit_prescription_versions
Revises: 0009_visit_exam_sections
Create Date: 2026-06-18 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010_visit_prescription_versions"
down_revision: str | None = "0009_visit_exam_sections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


prescription_version_status_enum = sa.Enum(
    "draft",
    "finalized",
    "superseded",
    "cancelled",
    name="prescription_version_status",
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
    if _has_table("visit_prescriptions"):
        return

    prescription_version_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "visit_prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("shop_key", sa.String(length=64), nullable=False),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", prescription_version_status_enum, nullable=False, server_default="draft"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("patient_instructions", sa.Text(), nullable=True),
        sa.Column(
            "amends_prescription_id",
            sa.Integer(),
            sa.ForeignKey("visit_prescriptions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("finalized_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_file_path", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("visit_id", "version_number", name="uq_visit_prescriptions_visit_version"),
    )
    for index_name, columns in (
        ("ix_visit_prescriptions_shop_id", ["shop_id"]),
        ("ix_visit_prescriptions_shop_key", ["shop_key"]),
        ("ix_visit_prescriptions_visit_id", ["visit_id"]),
        ("ix_visit_prescriptions_customer_id", ["customer_id"]),
        ("ix_visit_prescriptions_status", ["status"]),
        ("ix_visit_prescriptions_is_current", ["is_current"]),
        ("ix_visit_prescriptions_amends_prescription_id", ["amends_prescription_id"]),
    ):
        _create_index_if_missing(index_name, "visit_prescriptions", columns)
    op.create_index(
        "uq_visit_prescriptions_current_per_visit",
        "visit_prescriptions",
        ["visit_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
        sqlite_where=sa.text("is_current = 1"),
    )
    op.create_index(
        "uq_visit_prescriptions_draft_per_visit",
        "visit_prescriptions",
        ["visit_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
        sqlite_where=sa.text("status = 'draft'"),
    )


def downgrade() -> None:
    if _has_table("visit_prescriptions"):
        op.drop_table("visit_prescriptions")
    prescription_version_status_enum.drop(op.get_bind(), checkfirst=True)
