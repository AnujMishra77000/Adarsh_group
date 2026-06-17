from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.bill import Bill, BillItem, Payment
from app.models.campaign import Campaign
from app.models.campaign_log import CampaignLog
from app.models.customer import Customer
from app.models.prescription import Prescription
from app.models.shop import Shop
from app.models.user import User
from app.models.vendor import Vendor
from app.models.whatsapp_log import WhatsAppLog
from tests.conftest import TEST_SHOP_ONE


def _sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path}"


def _legacy_metadata() -> MetaData:
    metadata = MetaData()

    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("email", String(255), nullable=False),
        Column("full_name", String(255)),
        Column("password_hash", String(255), nullable=False),
        Column("shop_key", String(64)),
        Column("role", String(20), nullable=False),
        Column("is_active", Boolean, nullable=False),
        Column("last_login_at", DateTime(timezone=True)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("shop_key", String(64)),
        Column("customer_id", String(32), nullable=False),
        Column("name", String(255), nullable=False),
        Column("age", Integer),
        Column("contact_no", String(20), nullable=False),
        Column("email", String(255)),
        Column("whatsapp_no", String(20)),
        Column("gender", String(20)),
        Column("address", Text),
        Column("purpose_of_visit", String(255)),
        Column("whatsapp_opt_in", Boolean, nullable=False),
        Column("created_by", Integer),
        Column("updated_by", Integer),
        Column("is_deleted", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "prescriptions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", Integer, nullable=False),
        Column("prescription_date", Date, nullable=False),
        Column("right_sph", Numeric(5, 2)),
        Column("right_cyl", Numeric(5, 2)),
        Column("right_axis", Integer),
        Column("right_vn", String(20)),
        Column("left_sph", Numeric(5, 2)),
        Column("left_cyl", Numeric(5, 2)),
        Column("left_axis", Integer),
        Column("left_vn", String(20)),
        Column("fh", String(32)),
        Column("add_power", Numeric(5, 2)),
        Column("pd", Numeric(5, 2)),
        Column("notes", Text),
        Column("pdf_file_path", Text),
        Column("created_by", Integer),
        Column("updated_by", Integer),
        Column("is_deleted", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "bills",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("bill_number", String(32), nullable=False),
        Column("customer_id", Integer, nullable=False),
        Column("customer_name_snapshot", String(255), nullable=False),
        Column("product_name", String(255), nullable=False),
        Column("frame_name", String(255)),
        Column("whole_price", Numeric(12, 2), nullable=False),
        Column("discount", Numeric(12, 2), nullable=False),
        Column("final_price", Numeric(12, 2), nullable=False),
        Column("paid_amount", Numeric(12, 2), nullable=False),
        Column("balance_amount", Numeric(12, 2), nullable=False),
        Column("payment_mode", String(20), nullable=False),
        Column("payment_status", String(20), nullable=False),
        Column("delivery_date", Date),
        Column("notes", Text),
        Column("pdf_url", Text),
        Column("pdf_file_path", Text),
        Column("created_by", Integer),
        Column("updated_by", Integer),
        Column("is_deleted", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "vendors",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("vendor_name", String(255), nullable=False),
        Column("contact_person", String(255)),
        Column("whatsapp_no", String(20), nullable=False),
        Column("address", Text),
        Column("is_active", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "campaigns",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("shop_key", String(64)),
        Column("title", String(255), nullable=False),
        Column("message_body", Text, nullable=False),
        Column("scheduled_at", DateTime(timezone=True), nullable=False),
        Column("status", String(20), nullable=False),
        Column("total_customers_targeted", Integer, nullable=False),
        Column("total_sent", Integer, nullable=False),
        Column("total_failed", Integer, nullable=False),
        Column("created_by", Integer),
        Column("updated_by", Integer),
        Column("is_deleted", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "campaign_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("campaign_id", Integer, nullable=False),
        Column("customer_id", Integer),
        Column("recipient_whatsapp_no", String(20), nullable=False),
        Column("send_status", String(20), nullable=False),
        Column("provider_message_id", String(255)),
        Column("error_message", Text),
        Column("attempted_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "whatsapp_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("module_type", String(20), nullable=False),
        Column("reference_id", Integer, nullable=False),
        Column("customer_id", Integer),
        Column("vendor_id", Integer),
        Column("recipient_no", String(20), nullable=False),
        Column("message_type", String(20), nullable=False),
        Column("template_name", String(255)),
        Column("media_id", String(255)),
        Column("provider_message_id", String(255)),
        Column("status", String(20), nullable=False),
        Column("error_message", Text),
        Column("payload_json", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "audit_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("actor_user_id", Integer),
        Column("action", String(80), nullable=False),
        Column("entity_type", String(80), nullable=False),
        Column("entity_id", String(80), nullable=False),
        Column("old_values", JSON),
        Column("new_values", JSON),
        Column("metadata_json", JSON),
        Column("ip_address", String(45)),
        Column("user_agent", String(255)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "chat_messages",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("sender_user_id", Integer),
        Column("sender_name", String(255), nullable=False),
        Column("sender_role", String(20), nullable=False),
        Column("sender_shop_key", String(64), nullable=False),
        Column("message_text", Text),
        Column("attachment_original_name", String(255)),
        Column("attachment_storage_name", String(255)),
        Column("attachment_content_type", String(255)),
        Column("attachment_size_bytes", Integer),
        Column("attachment_stored_bytes", Integer),
        Column("attachment_sha256", String(64)),
        Column("is_attachment_compressed", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    return metadata


def _create_source_db(source_url: str) -> None:
    engine = create_engine(source_url, future=True)
    metadata = _legacy_metadata()
    metadata.create_all(engine)
    now = datetime.now(UTC).replace(microsecond=0)
    today = now.date()

    with engine.begin() as conn:
        conn.execute(
            metadata.tables["users"].insert(),
            {
                "id": 7,
                "email": "legacy-admin@example.com",
                "full_name": "Legacy Admin",
                "password_hash": "hashed",
                "shop_key": TEST_SHOP_ONE,
                "role": "ADMIN",
                "is_active": True,
                "last_login_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["customers"].insert(),
            {
                "id": 11,
                "shop_key": TEST_SHOP_ONE,
                "customer_id": "CUST-001",
                "name": "Legacy Customer",
                "age": 32,
                "contact_no": "9999999999",
                "email": "customer@example.com",
                "whatsapp_no": "9999999999",
                "gender": "OTHER",
                "address": "Kalyan",
                "purpose_of_visit": "Eye test",
                "whatsapp_opt_in": True,
                "created_by": 7,
                "updated_by": 7,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["vendors"].insert(),
            {
                "id": 41,
                "vendor_name": "Legacy Vendor",
                "contact_person": "Vendor Person",
                "whatsapp_no": "9888888888",
                "address": "Mumbai",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["prescriptions"].insert(),
            {
                "id": 21,
                "customer_id": 11,
                "prescription_date": today,
                "right_sph": Decimal("1.25"),
                "right_cyl": None,
                "right_axis": None,
                "right_vn": None,
                "left_sph": Decimal("1.00"),
                "left_cyl": None,
                "left_axis": None,
                "left_vn": None,
                "fh": None,
                "add_power": None,
                "pd": None,
                "notes": "legacy prescription",
                "pdf_file_path": "prescriptions/legacy.pdf",
                "created_by": 7,
                "updated_by": 7,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["bills"].insert(),
            {
                "id": 31,
                "bill_number": "BILL-001",
                "customer_id": 11,
                "customer_name_snapshot": "Legacy Customer",
                "product_name": "Frame",
                "frame_name": "Classic",
                "whole_price": Decimal("1000.00"),
                "discount": Decimal("100.00"),
                "final_price": Decimal("900.00"),
                "paid_amount": Decimal("500.00"),
                "balance_amount": Decimal("400.00"),
                "payment_mode": "CASH",
                "payment_status": "PARTIAL",
                "delivery_date": today + timedelta(days=2),
                "notes": "legacy bill",
                "pdf_url": "/media/invoices/legacy.pdf",
                "pdf_file_path": "invoices/legacy.pdf",
                "created_by": 7,
                "updated_by": 7,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["campaigns"].insert(),
            {
                "id": 51,
                "shop_key": TEST_SHOP_ONE,
                "title": "Legacy Campaign",
                "message_body": "Hello",
                "scheduled_at": now,
                "status": "DRAFT",
                "total_customers_targeted": 1,
                "total_sent": 1,
                "total_failed": 0,
                "created_by": 7,
                "updated_by": 7,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["campaign_logs"].insert(),
            {
                "id": 61,
                "campaign_id": 51,
                "customer_id": 11,
                "recipient_whatsapp_no": "9999999999",
                "send_status": "sent",
                "provider_message_id": "wamid.1",
                "error_message": None,
                "attempted_at": now,
            },
        )
        conn.execute(
            metadata.tables["whatsapp_logs"].insert(),
            {
                "id": 71,
                "module_type": "BILL",
                "reference_id": 31,
                "customer_id": 11,
                "vendor_id": 41,
                "recipient_no": "9999999999",
                "message_type": "DOCUMENT",
                "template_name": None,
                "media_id": "media-1",
                "provider_message_id": "wamid.2",
                "status": "SENT",
                "error_message": None,
                "payload_json": {"source": "legacy"},
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["audit_logs"].insert(),
            {
                "id": 81,
                "actor_user_id": 7,
                "action": "customer.create",
                "entity_type": "customer",
                "entity_id": "11",
                "old_values": None,
                "new_values": {"name": "Legacy Customer"},
                "metadata_json": {"source": "legacy"},
                "ip_address": "127.0.0.1",
                "user_agent": "test",
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.execute(
            metadata.tables["chat_messages"].insert(),
            {
                "id": 91,
                "sender_user_id": 7,
                "sender_name": "Legacy Admin",
                "sender_role": "admin",
                "sender_shop_key": TEST_SHOP_ONE,
                "message_text": "legacy chat",
                "attachment_original_name": None,
                "attachment_storage_name": None,
                "attachment_content_type": None,
                "attachment_size_bytes": None,
                "attachment_stored_bytes": None,
                "attachment_sha256": None,
                "is_attachment_compressed": False,
                "created_at": now,
                "updated_at": now,
            },
        )


def _create_target_db(target_url: str) -> None:
    engine = create_engine(target_url, future=True)
    Base.metadata.create_all(engine)


def _target_session(target_url: str):
    engine = create_engine(target_url, future=True)
    session_local = sessionmaker(bind=engine)
    return engine, session_local()


def test_dry_run_reports_counts_without_writing_to_target(tmp_path: Path) -> None:
    from app.scripts.import_shop_databases_to_single_db import import_shop_databases

    source_url = _sqlite_url(tmp_path / "legacy_shop.db")
    target_url = _sqlite_url(tmp_path / "single.db")
    _create_source_db(source_url)
    _create_target_db(target_url)

    result = import_shop_databases(
        source_map={TEST_SHOP_ONE: source_url},
        target_db_url=target_url,
        dry_run=True,
    )

    assert result.dry_run is True
    assert result.shops[0].table_counts["customers"].source_count == 1
    assert result.shops[0].table_counts["customers"].would_insert == 1

    engine, db = _target_session(target_url)
    try:
        assert db.query(Shop).count() == 0
        assert db.query(Customer).count() == 0
        assert db.query(User).count() == 0
    finally:
        db.close()
        engine.dispose()


def test_import_maps_relationships_and_is_idempotent(tmp_path: Path) -> None:
    from app.scripts.import_shop_databases_to_single_db import import_shop_databases

    source_url = _sqlite_url(tmp_path / "legacy_shop.db")
    target_url = _sqlite_url(tmp_path / "single.db")
    _create_source_db(source_url)
    _create_target_db(target_url)

    first = import_shop_databases(source_map={TEST_SHOP_ONE: source_url}, target_db_url=target_url)
    second = import_shop_databases(source_map={TEST_SHOP_ONE: source_url}, target_db_url=target_url)

    assert first.shops[0].table_counts["customers"].inserted == 1
    assert second.shops[0].table_counts["customers"].skipped_existing == 1

    engine, db = _target_session(target_url)
    try:
        shop = db.query(Shop).filter(Shop.code == TEST_SHOP_ONE).one()
        user = db.query(User).filter(User.email == "legacy-admin@example.com").one()
        customer = db.query(Customer).filter(Customer.customer_id == "CUST-001").one()
        prescription = db.query(Prescription).one()
        bill = db.query(Bill).filter(Bill.bill_number == "BILL-001").one()
        bill_item = db.query(BillItem).filter(BillItem.bill_id == bill.id).one()
        payment = db.query(Payment).filter(Payment.bill_id == bill.id).one()
        vendor = db.query(Vendor).filter(Vendor.vendor_name == "Legacy Vendor").one()
        campaign = db.query(Campaign).filter(Campaign.title == "Legacy Campaign").one()
        campaign_log = db.query(CampaignLog).one()
        whatsapp_log = db.query(WhatsAppLog).one()

        assert customer.shop_id == shop.id
        assert customer.created_by == user.id
        assert prescription.shop_id == shop.id
        assert prescription.customer_id == customer.id
        assert bill.shop_id == shop.id
        assert bill.customer_id == customer.id
        assert bill.subtotal == Decimal("1000.00")
        assert bill.discount_total == Decimal("100.00")
        assert bill.grand_total == Decimal("900.00")
        assert bill.paid_total == Decimal("500.00")
        assert bill_item.shop_id == shop.id
        assert bill_item.item_name == "Frame"
        assert bill_item.line_total == Decimal("900.00")
        assert payment.shop_id == shop.id
        assert payment.amount == Decimal("500.00")
        assert vendor.shop_id == shop.id
        assert campaign.shop_id == shop.id
        assert campaign.created_by == user.id
        assert campaign_log.shop_id == shop.id
        assert campaign_log.campaign_id == campaign.id
        assert campaign_log.customer_id == customer.id
        assert whatsapp_log.shop_id == shop.id
        assert whatsapp_log.reference_id == bill.id
        assert whatsapp_log.customer_id == customer.id
        assert whatsapp_log.vendor_id == vendor.id

        assert db.query(Customer).count() == 1
        assert db.query(Bill).count() == 1
        assert db.query(BillItem).count() == 1
        assert db.query(Payment).count() == 1
        with engine.connect() as conn:
            mapping_count = conn.execute(select(func.count()).select_from(Table("shop_import_mappings", MetaData(), autoload_with=engine))).scalar_one()
        assert mapping_count >= 10
    finally:
        db.close()
        engine.dispose()
