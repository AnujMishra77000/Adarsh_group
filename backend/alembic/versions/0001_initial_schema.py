"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-05 09:50:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role_enum = sa.Enum("admin", "staff", name="user_role")
gender_enum = sa.Enum("male", "female", "other", name="gender_enum")
payment_mode_enum = sa.Enum("cash", "upi", name="payment_mode")
payment_status_enum = sa.Enum("pending", "partial", "paid", name="payment_status")
campaign_status_enum = sa.Enum(
    "draft",
    "scheduled",
    "running",
    "completed",
    "failed",
    "cancelled",
    name="campaign_status",
)
whatsapp_module_type_enum = sa.Enum("customer", "prescription", "bill", "campaign", name="whatsapp_module_type")
whatsapp_message_type_enum = sa.Enum("text", "template", "document", name="whatsapp_message_type")
whatsapp_status_enum = sa.Enum("pending", "sent", "failed", name="whatsapp_status")


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    gender_enum.create(bind, checkfirst=True)
    payment_mode_enum.create(bind, checkfirst=True)
    payment_status_enum.create(bind, checkfirst=True)
    campaign_status_enum.create(bind, checkfirst=True)
    whatsapp_module_type_enum.create(bind, checkfirst=True)
    whatsapp_message_type_enum.create(bind, checkfirst=True)
    whatsapp_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_name", sa.String(length=255), nullable=False),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("whatsapp_no", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_vendors_vendor_name", "vendors", ["vendor_name"], unique=False)
    op.create_index("ix_vendors_whatsapp_no", "vendors", ["whatsapp_no"], unique=False)
    op.create_index("ix_vendors_is_active", "vendors", ["is_active"], unique=False)

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("contact_no", sa.String(length=20), nullable=False),
        sa.Column("whatsapp_no", sa.String(length=20), nullable=True),
        sa.Column("gender", gender_enum, nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("purpose_of_visit", sa.String(length=255), nullable=True),
        sa.Column("whatsapp_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_customers_customer_id", "customers", ["customer_id"], unique=True)
    op.create_index("ix_customers_name", "customers", ["name"], unique=False)
    op.create_index("ix_customers_contact_no", "customers", ["contact_no"], unique=False)
    op.create_index("ix_customers_whatsapp_no", "customers", ["whatsapp_no"], unique=False)
    op.create_index("ix_customers_is_deleted", "customers", ["is_deleted"], unique=False)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message_body", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", campaign_status_enum, nullable=False, server_default="draft"),
        sa.Column("total_customers_targeted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_campaigns_scheduled_at", "campaigns", ["scheduled_at"], unique=False)
    op.create_index("ix_campaigns_status", "campaigns", ["status"], unique=False)
    op.create_index("ix_campaigns_is_deleted", "campaigns", ["is_deleted"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("prescription_date", sa.Date(), nullable=False),
        sa.Column("right_sph", sa.Numeric(5, 2), nullable=True),
        sa.Column("right_cyl", sa.Numeric(5, 2), nullable=True),
        sa.Column("right_axis", sa.Integer(), nullable=True),
        sa.Column("right_vn", sa.String(length=20), nullable=True),
        sa.Column("left_sph", sa.Numeric(5, 2), nullable=True),
        sa.Column("left_cyl", sa.Numeric(5, 2), nullable=True),
        sa.Column("left_axis", sa.Integer(), nullable=True),
        sa.Column("left_vn", sa.String(length=20), nullable=True),
        sa.Column("fh", sa.String(length=32), nullable=True),
        sa.Column("add_power", sa.Numeric(5, 2), nullable=True),
        sa.Column("pd", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_prescriptions_customer_id", "prescriptions", ["customer_id"], unique=False)
    op.create_index("ix_prescriptions_prescription_date", "prescriptions", ["prescription_date"], unique=False)
    op.create_index("ix_prescriptions_is_deleted", "prescriptions", ["is_deleted"], unique=False)

    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bill_number", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("frame_name", sa.String(length=255), nullable=True),
        sa.Column("whole_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("final_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("balance_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_mode", payment_mode_enum, nullable=False),
        sa.Column("payment_status", payment_status_enum, nullable=False, server_default="pending"),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_bills_bill_number", "bills", ["bill_number"], unique=True)
    op.create_index("ix_bills_customer_id", "bills", ["customer_id"], unique=False)
    op.create_index("ix_bills_is_deleted", "bills", ["is_deleted"], unique=False)

    op.create_table(
        "campaign_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_whatsapp_no", sa.String(length=20), nullable=False),
        sa.Column("send_status", sa.String(length=20), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_campaign_logs_campaign_id", "campaign_logs", ["campaign_id"], unique=False)
    op.create_index("ix_campaign_logs_customer_id", "campaign_logs", ["customer_id"], unique=False)
    op.create_index("ix_campaign_logs_send_status", "campaign_logs", ["send_status"], unique=False)

    op.create_table(
        "whatsapp_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_type", whatsapp_module_type_enum, nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_no", sa.String(length=20), nullable=False),
        sa.Column("message_type", whatsapp_message_type_enum, nullable=False),
        sa.Column("template_name", sa.String(length=255), nullable=True),
        sa.Column("media_id", sa.String(length=255), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("status", whatsapp_status_enum, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_whatsapp_logs_reference_id", "whatsapp_logs", ["reference_id"], unique=False)
    op.create_index("ix_whatsapp_logs_customer_id", "whatsapp_logs", ["customer_id"], unique=False)
    op.create_index("ix_whatsapp_logs_vendor_id", "whatsapp_logs", ["vendor_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_whatsapp_logs_vendor_id", table_name="whatsapp_logs")
    op.drop_index("ix_whatsapp_logs_customer_id", table_name="whatsapp_logs")
    op.drop_index("ix_whatsapp_logs_reference_id", table_name="whatsapp_logs")
    op.drop_table("whatsapp_logs")

    op.drop_index("ix_campaign_logs_send_status", table_name="campaign_logs")
    op.drop_index("ix_campaign_logs_customer_id", table_name="campaign_logs")
    op.drop_index("ix_campaign_logs_campaign_id", table_name="campaign_logs")
    op.drop_table("campaign_logs")

    op.drop_index("ix_bills_is_deleted", table_name="bills")
    op.drop_index("ix_bills_customer_id", table_name="bills")
    op.drop_index("ix_bills_bill_number", table_name="bills")
    op.drop_table("bills")

    op.drop_index("ix_prescriptions_is_deleted", table_name="prescriptions")
    op.drop_index("ix_prescriptions_prescription_date", table_name="prescriptions")
    op.drop_index("ix_prescriptions_customer_id", table_name="prescriptions")
    op.drop_table("prescriptions")

    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_campaigns_is_deleted", table_name="campaigns")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_scheduled_at", table_name="campaigns")
    op.drop_table("campaigns")

    op.drop_index("ix_customers_is_deleted", table_name="customers")
    op.drop_index("ix_customers_whatsapp_no", table_name="customers")
    op.drop_index("ix_customers_contact_no", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_index("ix_customers_customer_id", table_name="customers")
    op.drop_table("customers")

    op.drop_index("ix_vendors_is_active", table_name="vendors")
    op.drop_index("ix_vendors_whatsapp_no", table_name="vendors")
    op.drop_index("ix_vendors_vendor_name", table_name="vendors")
    op.drop_table("vendors")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    whatsapp_status_enum.drop(op.get_bind(), checkfirst=True)
    whatsapp_message_type_enum.drop(op.get_bind(), checkfirst=True)
    whatsapp_module_type_enum.drop(op.get_bind(), checkfirst=True)
    campaign_status_enum.drop(op.get_bind(), checkfirst=True)
    payment_status_enum.drop(op.get_bind(), checkfirst=True)
    payment_mode_enum.drop(op.get_bind(), checkfirst=True)
    gender_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
