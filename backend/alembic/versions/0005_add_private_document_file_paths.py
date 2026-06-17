"""add private document file paths

Revision ID: 0005_add_private_document_file_paths
Revises: 0004_add_shared_chat_messages
Create Date: 2026-06-15 14:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_add_private_document_file_paths"
down_revision: str | None = "0004_add_shared_chat_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("bills", "pdf_file_path"):
        with op.batch_alter_table("bills", schema=None) as batch_op:
            batch_op.add_column(sa.Column("pdf_file_path", sa.Text(), nullable=True))

    if not _has_column("prescriptions", "pdf_file_path"):
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.add_column(sa.Column("pdf_file_path", sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_column("prescriptions", "pdf_file_path"):
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.drop_column("pdf_file_path")

    if _has_column("bills", "pdf_file_path"):
        with op.batch_alter_table("bills", schema=None) as batch_op:
            batch_op.drop_column("pdf_file_path")
