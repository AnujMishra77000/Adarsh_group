"""add shared chat messages table

Revision ID: 0004_add_shared_chat_messages
Revises: 0003_add_shop_key_isolation
Create Date: 2026-04-18 10:20:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_add_shared_chat_messages"
down_revision: str | None = "0003_add_shop_key_isolation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sender_name", sa.String(length=255), nullable=False),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("sender_shop_key", sa.String(length=64), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("attachment_original_name", sa.String(length=255), nullable=True),
        sa.Column("attachment_storage_name", sa.String(length=255), nullable=True),
        sa.Column("attachment_content_type", sa.String(length=255), nullable=True),
        sa.Column("attachment_size_bytes", sa.Integer(), nullable=True),
        sa.Column("attachment_stored_bytes", sa.Integer(), nullable=True),
        sa.Column("attachment_sha256", sa.String(length=64), nullable=True),
        sa.Column("is_attachment_compressed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_index("ix_chat_messages_sender_user_id", "chat_messages", ["sender_user_id"], unique=False)
    op.create_index("ix_chat_messages_sender_role", "chat_messages", ["sender_role"], unique=False)
    op.create_index("ix_chat_messages_sender_shop_key", "chat_messages", ["sender_shop_key"], unique=False)
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"], unique=False)
    op.create_index("ix_chat_messages_attachment_storage_name", "chat_messages", ["attachment_storage_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_chat_messages_attachment_storage_name", table_name="chat_messages")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_shop_key", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_role", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_user_id", table_name="chat_messages")
    op.drop_table("chat_messages")
