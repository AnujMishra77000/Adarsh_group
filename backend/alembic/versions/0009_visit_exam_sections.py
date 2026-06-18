"""visit exam sections

Revision ID: 0009_visit_exam_sections
Revises: 0008_patient_visit_foundation
Create Date: 2026-06-17 16:55:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_visit_exam_sections"
down_revision: str | None = "0008_patient_visit_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


exam_section_state_enum = sa.Enum(
    "incomplete",
    "complete",
    "optional",
    "not_applicable",
    "future",
    name="exam_section_state",
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if _has_index(table_name, index_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    if _has_table("visit_exam_sections"):
        return

    exam_section_state_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "visit_exam_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), sa.ForeignKey("shops.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("shop_key", sa.String(length=64), nullable=False),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_key", sa.String(length=80), nullable=False),
        sa.Column("state", exam_section_state_enum, nullable=False, server_default="incomplete"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("visit_id", "section_key", name="uq_visit_exam_sections_visit_section"),
    )
    _create_index_if_missing("ix_visit_exam_sections_shop_id", "visit_exam_sections", ["shop_id"])
    _create_index_if_missing("ix_visit_exam_sections_shop_key", "visit_exam_sections", ["shop_key"])
    _create_index_if_missing("ix_visit_exam_sections_visit_id", "visit_exam_sections", ["visit_id"])
    _create_index_if_missing("ix_visit_exam_sections_section_key", "visit_exam_sections", ["section_key"])
    _create_index_if_missing("ix_visit_exam_sections_state", "visit_exam_sections", ["state"])


def downgrade() -> None:
    if _has_table("visit_exam_sections"):
        op.drop_table("visit_exam_sections")
    exam_section_state_enum.drop(op.get_bind(), checkfirst=True)
