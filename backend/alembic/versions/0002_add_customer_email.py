"""add customer email for welcome mail

Revision ID: 0002_add_customer_email
Revises: 0001_initial_schema
Create Date: 2026-04-05 18:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_customer_email"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.create_index("ix_customers_email", ["email"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.drop_index("ix_customers_email")
        batch_op.drop_column("email")
