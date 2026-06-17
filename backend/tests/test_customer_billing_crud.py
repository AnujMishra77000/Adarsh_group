from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.enums import BillItemType, PaymentMode, PaymentStatus
from app.models.user import User
from app.schemas.bill import BillCreate, BillItemCreate, BillPaymentCreate, BillUpdate
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.bill_service import BillService
from app.services.customer_service import CustomerService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO


def test_customer_crud_is_scoped_to_active_shop(db_session: Session, make_user) -> None:
    actor_one: User = make_user("customer-admin-one@example.com", TEST_SHOP_ONE)
    make_user("customer-admin-two@example.com", TEST_SHOP_TWO)

    shop_one_service = CustomerService(db_session, shop_key=TEST_SHOP_ONE)
    customer = shop_one_service.create_customer(
        payload=CustomerCreate(
            name="Priya Sharma",
            contact_no="9876543210",
            email="PRIYA@example.com",
            whatsapp_opt_in=False,
        ),
        actor=actor_one,
    )

    assert customer.name == "Priya Sharma"
    assert customer.email == "priya@example.com"
    assert shop_one_service.list_customers(page=1, page_size=10, search=None).total == 1
    assert CustomerService(db_session, shop_key=TEST_SHOP_TWO).list_customers(page=1, page_size=10, search=None).total == 0

    with pytest.raises(AppException) as cross_shop_read:
        CustomerService(db_session, shop_key=TEST_SHOP_TWO).get_customer(customer_pk=customer.id)
    assert cross_shop_read.value.status_code == 404

    updated = shop_one_service.update_customer(
        customer_pk=customer.id,
        payload=CustomerUpdate(name="Priya S."),
        actor=actor_one,
    )
    assert updated.name == "Priya S."

    shop_one_service.delete_customer(customer_pk=customer.id, actor=actor_one)

    with pytest.raises(AppException) as deleted_read:
        shop_one_service.get_customer(customer_pk=customer.id)
    assert deleted_read.value.status_code == 404


def test_billing_crud_calculates_totals_and_is_scoped_to_shop(db_session: Session, make_user) -> None:
    actor_one: User = make_user("billing-admin-one@example.com", TEST_SHOP_ONE)
    make_user("billing-admin-two@example.com", TEST_SHOP_TWO)

    customer = CustomerService(db_session, shop_key=TEST_SHOP_ONE).create_customer(
        payload=CustomerCreate(
            name="Amit Patel",
            contact_no="9988776655",
            whatsapp_opt_in=False,
        ),
        actor=actor_one,
    )

    bill_service = BillService(db_session, shop_key=TEST_SHOP_ONE)

    with patch.object(BillService, "_try_auto_generate_pdf", return_value=None):
        bill = bill_service.create_bill(
            payload=BillCreate(
                customer_id=customer.id,
                product_name="Progressive Lens",
                frame_name="Titan",
                whole_price=Decimal("2500.00"),
                discount=Decimal("500.00"),
                paid_amount=Decimal("1000.00"),
                payment_mode=PaymentMode.UPI,
                notes="Initial order",
            ),
            actor=actor_one,
        )

        assert bill.final_price == Decimal("2000.00")
        assert bill.balance_amount == Decimal("1000.00")
        assert bill.payment_status == PaymentStatus.PARTIAL
        assert bill_service.list_bills(page=1, page_size=10, search=None, customer_pk=None).total == 1
        assert BillService(db_session, shop_key=TEST_SHOP_TWO).list_bills(page=1, page_size=10, search=None, customer_pk=None).total == 0

        with pytest.raises(AppException) as cross_shop_read:
            BillService(db_session, shop_key=TEST_SHOP_TWO).get_bill(bill_id=bill.id)
        assert cross_shop_read.value.status_code == 404

        updated = bill_service.update_bill(
            bill_id=bill.id,
            payload=BillUpdate(paid_amount=Decimal("2000.00")),
            actor=actor_one,
        )
        assert updated.balance_amount == Decimal("0.00")
        assert updated.payment_status == PaymentStatus.PAID

    bill_service.delete_bill(bill_id=bill.id, actor=actor_one)

    with pytest.raises(AppException) as deleted_read:
        bill_service.get_bill(bill_id=bill.id)
    assert deleted_read.value.status_code == 404


def test_multi_item_bill_supports_partial_payments_and_legacy_snapshots(db_session: Session, make_user) -> None:
    actor: User = make_user("multi-bill-admin@example.com", TEST_SHOP_ONE)
    customer = CustomerService(db_session, shop_key=TEST_SHOP_ONE).create_customer(
        payload=CustomerCreate(
            name="Neha Shah",
            contact_no="9000090000",
            whatsapp_opt_in=False,
        ),
        actor=actor,
    )

    bill_service = BillService(db_session, shop_key=TEST_SHOP_ONE)

    with patch.object(BillService, "_try_auto_generate_pdf", return_value=None):
        bill = bill_service.create_bill(
            payload=BillCreate(
                customer_id=customer.id,
                items=[
                    BillItemCreate(
                        item_type=BillItemType.FRAME,
                        item_name="Acetate Frame",
                        quantity=Decimal("1"),
                        unit_price=Decimal("3000.00"),
                        discount=Decimal("250.00"),
                    ),
                    BillItemCreate(
                        item_type=BillItemType.LENS,
                        item_name="Progressive Lenses",
                        quantity=Decimal("2"),
                        unit_price=Decimal("1800.00"),
                        discount=Decimal("100.00"),
                    ),
                ],
                payments=[
                    BillPaymentCreate(mode=PaymentMode.UPI, amount=Decimal("1500.00"), reference_no="UPI-1"),
                    BillPaymentCreate(mode=PaymentMode.CARD, amount=Decimal("1000.00"), reference_no="CARD-1"),
                ],
                notes="Multi-line optical order",
            ),
            actor=actor,
        )

    assert bill.subtotal == Decimal("6600.00")
    assert bill.discount_total == Decimal("350.00")
    assert bill.tax_total == Decimal("0.00")
    assert bill.grand_total == Decimal("6250.00")
    assert bill.paid_total == Decimal("2500.00")
    assert bill.balance_amount == Decimal("3750.00")
    assert bill.payment_status == PaymentStatus.PARTIAL
    assert [item.item_name for item in bill.items] == ["Acetate Frame", "Progressive Lenses"]
    assert [payment.mode for payment in bill.payments] == [PaymentMode.UPI, PaymentMode.CARD]

    assert bill.product_name == "Acetate Frame"
    assert bill.frame_name == "Acetate Frame"
    assert bill.whole_price == bill.subtotal
    assert bill.discount == bill.discount_total
    assert bill.final_price == bill.grand_total
    assert bill.paid_amount == bill.paid_total
