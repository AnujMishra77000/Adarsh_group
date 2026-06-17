from __future__ import annotations

import importlib
import inspect
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.shops import SHOP_DEFINITIONS
from app.db import session as db_session_module
from app.models.bill import Bill
from app.models.campaign import Campaign
from app.models.campaign_log import CampaignLog
from app.models.chat_message import ChatMessage
from app.models.customer import Customer
from app.models.enums import CampaignStatus, PaymentMode, PaymentStatus
from app.models.prescription import Prescription
from app.models.user import User
from app.models.vendor import Vendor
from app.models.whatsapp_log import WhatsAppLog
from app.schemas.vendor import VendorCreate
from app.services.vendor_service import VendorService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO


TENANT_OWNED_MODELS = (
    User,
    Customer,
    Prescription,
    Bill,
    Vendor,
    Campaign,
    CampaignLog,
    WhatsAppLog,
    ChatMessage,
)


def _shop_model():
    try:
        return importlib.import_module("app.models.shop").Shop
    except ModuleNotFoundError as exc:  # pragma: no cover - red phase clarity
        pytest.fail(f"Shop model is required for single-db multi-shop tenancy: {exc}")


def _seed_shops(db: Session) -> dict[str, object]:
    Shop = _shop_model()
    shops: dict[str, object] = {}
    for definition in SHOP_DEFINITIONS:
        shop = Shop(
            code=definition.code,
            display_name=definition.display_name,
            location_label=definition.location_label,
            center_type=definition.center_type,
            is_active=definition.is_active,
        )
        db.add(shop)
        shops[definition.code] = shop
    db.commit()
    for shop in shops.values():
        db.refresh(shop)
    return shops


def test_normal_db_session_dependency_no_longer_requires_tenant_database_selection() -> None:
    signature = inspect.signature(db_session_module.get_db)

    assert "shop_code" not in signature.parameters


def test_shop_model_is_registered_with_all_four_canonical_shops(db_session: Session) -> None:
    shops = _seed_shops(db_session)

    assert set(shops) == {definition.code for definition in SHOP_DEFINITIONS}
    assert {getattr(shop, "display_name") for shop in shops.values()} >= {
        "Adarsh Optical Centre",
        "Adarsh Optometric Clinic",
        "Adarsh Opticals",
        "Adarsh Eye Boutique",
    }


@pytest.mark.parametrize("model", TENANT_OWNED_MODELS)
def test_tenant_owned_models_have_shop_id_foreign_key(model: type) -> None:
    column = model.__table__.columns.get("shop_id")

    assert column is not None, f"{model.__name__} must have a shop_id column"
    assert any(foreign_key.column.table.name == "shops" for foreign_key in column.foreign_keys)


def test_customer_business_id_is_unique_per_shop_not_global(db_session: Session) -> None:
    shops = _seed_shops(db_session)
    shop_one = shops[TEST_SHOP_ONE]
    shop_two = shops[TEST_SHOP_TWO]

    db_session.add_all(
        [
            Customer(
                shop_id=getattr(shop_one, "id"),
                shop_key=TEST_SHOP_ONE,
                customer_id="CUST-SHARED",
                name="Shop One Customer",
                contact_no="9999999991",
            ),
            Customer(
                shop_id=getattr(shop_two, "id"),
                shop_key=TEST_SHOP_TWO,
                customer_id="CUST-SHARED",
                name="Shop Two Customer",
                contact_no="9999999992",
            ),
        ]
    )

    try:
        db_session.commit()
    except IntegrityError as exc:
        pytest.fail(f"customer_id should be unique per shop, not globally: {exc}")


def test_bill_number_is_unique_per_shop_not_global(db_session: Session) -> None:
    shops = _seed_shops(db_session)
    shop_one = shops[TEST_SHOP_ONE]
    shop_two = shops[TEST_SHOP_TWO]

    customer_one = Customer(
        shop_id=getattr(shop_one, "id"),
        shop_key=TEST_SHOP_ONE,
        customer_id="CUST-BILL-1",
        name="Shop One Customer",
        contact_no="9999999991",
    )
    customer_two = Customer(
        shop_id=getattr(shop_two, "id"),
        shop_key=TEST_SHOP_TWO,
        customer_id="CUST-BILL-2",
        name="Shop Two Customer",
        contact_no="9999999992",
    )
    db_session.add_all([customer_one, customer_two])
    db_session.flush()

    db_session.add_all(
        [
            Bill(
                shop_id=getattr(shop_one, "id"),
                bill_number="BILL-SHARED",
                customer_id=customer_one.id,
                customer_name_snapshot=customer_one.name,
                product_name="Frame",
                whole_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                final_price=Decimal("100.00"),
                paid_amount=Decimal("100.00"),
                balance_amount=Decimal("0.00"),
                payment_mode=PaymentMode.CASH,
                payment_status=PaymentStatus.PAID,
            ),
            Bill(
                shop_id=getattr(shop_two, "id"),
                bill_number="BILL-SHARED",
                customer_id=customer_two.id,
                customer_name_snapshot=customer_two.name,
                product_name="Lens",
                whole_price=Decimal("200.00"),
                discount=Decimal("0.00"),
                final_price=Decimal("200.00"),
                paid_amount=Decimal("200.00"),
                balance_amount=Decimal("0.00"),
                payment_mode=PaymentMode.UPI,
                payment_status=PaymentStatus.PAID,
            ),
        ]
    )

    try:
        db_session.commit()
    except IntegrityError as exc:
        pytest.fail(f"bill_number should be unique per shop, not globally: {exc}")


def test_vendor_crud_is_scoped_to_current_shop(db_session: Session, make_user) -> None:
    _seed_shops(db_session)
    actor_one = make_user("vendor-one@example.com", TEST_SHOP_ONE)
    actor_two = make_user("vendor-two@example.com", TEST_SHOP_TWO)

    shop_one_service = VendorService(db_session, shop_key=TEST_SHOP_ONE)
    shop_two_service = VendorService(db_session, shop_key=TEST_SHOP_TWO)

    vendor_one = shop_one_service.create_vendor(
        payload=VendorCreate(vendor_name="Shop One Vendor", whatsapp_no="9999999991"),
        actor=actor_one,
    )
    vendor_two = shop_two_service.create_vendor(
        payload=VendorCreate(vendor_name="Shop Two Vendor", whatsapp_no="9999999992"),
        actor=actor_two,
    )

    assert shop_one_service.list_vendors(page=1, page_size=10, search=None, is_active=None).total == 1
    assert shop_two_service.list_vendors(page=1, page_size=10, search=None, is_active=None).total == 1
    assert shop_one_service.get_vendor(vendor_one.id).vendor_name == "Shop One Vendor"

    with pytest.raises(AppException) as cross_shop_read:
        shop_one_service.get_vendor(vendor_two.id)
    assert cross_shop_read.value.status_code == 404


def test_campaign_logs_are_tied_to_their_campaign_shop(db_session: Session) -> None:
    shops = _seed_shops(db_session)
    shop_one = shops[TEST_SHOP_ONE]
    shop_two = shops[TEST_SHOP_TWO]

    campaign_one = Campaign(
        shop_id=getattr(shop_one, "id"),
        shop_key=TEST_SHOP_ONE,
        title="Shop One Campaign",
        message_body="Hello",
        scheduled_at=datetime.now(UTC),
        status=CampaignStatus.DRAFT,
    )
    campaign_two = Campaign(
        shop_id=getattr(shop_two, "id"),
        shop_key=TEST_SHOP_TWO,
        title="Shop Two Campaign",
        message_body="Hello",
        scheduled_at=datetime.now(UTC),
        status=CampaignStatus.DRAFT,
    )
    db_session.add_all([campaign_one, campaign_two])
    db_session.flush()

    log_one = CampaignLog(
        shop_id=getattr(shop_one, "id"),
        campaign_id=campaign_one.id,
        recipient_whatsapp_no="9999999991",
        send_status="sent",
    )
    log_two = CampaignLog(
        shop_id=getattr(shop_two, "id"),
        campaign_id=campaign_two.id,
        recipient_whatsapp_no="9999999992",
        send_status="sent",
    )
    db_session.add_all([log_one, log_two])
    db_session.commit()

    assert {log.shop_id for log in campaign_one.logs} == {getattr(shop_one, "id")}
    assert {log.shop_id for log in campaign_two.logs} == {getattr(shop_two, "id")}
