from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.bill import Bill
from app.models.enums import BillItemType, PaymentMode, PaymentStatus
from app.schemas.bill import BillCreate
from app.services.bill_service import BillService
from app.services.dispensing_order_service import DispensingOrderService
from app.schemas.customer import CustomerCreate
from app.services.customer_service import CustomerService
from app.schemas.visit_billing import VisitBillLinkRequest
from app.services.visit_billing_service import VisitBillingService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO
from tests.test_dispensing_orders import _create_finalized_visit, _order_payload


def _create_order(db_session: Session, make_user):
    actor, patient, visit, _prescription = _create_finalized_visit(db_session, make_user)
    order = DispensingOrderService(db_session, TEST_SHOP_ONE).save_draft(visit.id, _order_payload(), actor)
    return actor, patient, visit, order


def _bill_payload(customer_id: int, visit_id: int | None = None, order_id: int | None = None) -> BillCreate:
    return BillCreate(
        customer_id=customer_id,
        visit_id=visit_id,
        dispensing_order_id=order_id,
        tax_total=Decimal("180.00"),
        items=[
            {
                "item_type": BillItemType.FRAME,
                "item_name": "Ray-Ban RX-5228",
                "quantity": Decimal("1"),
                "unit_price": Decimal("3000.00"),
                "discount": Decimal("200.00"),
            },
            {
                "item_type": BillItemType.LENS,
                "item_name": "Progressive lens pair",
                "quantity": Decimal("1"),
                "unit_price": Decimal("4200.00"),
                "discount": Decimal("0.00"),
            },
        ],
        payments=[
            {"mode": PaymentMode.UPI, "amount": Decimal("3000.00"), "reference_no": "UPI-PHASE8"}
        ],
    )


def test_bill_model_has_context_links_and_active_order_uniqueness() -> None:
    assert Bill.__table__.columns.get("visit_id") is not None
    assert Bill.__table__.columns.get("dispensing_order_id") is not None
    index = next(index for index in Bill.__table__.indexes if index.name == "uq_bills_active_dispensing_order")
    assert index.unique is True
    assert index.dialect_options["postgresql"]["where"] is not None
    assert index.dialect_options["sqlite"]["where"] is not None


def test_contextual_bill_reuses_existing_items_payments_and_totals(db_session: Session, make_user) -> None:
    actor, patient, visit, order = _create_order(db_session, make_user)

    bill = BillService(db_session, TEST_SHOP_ONE).create_bill(
        _bill_payload(patient.id, visit.id, order.id),
        actor,
    )

    assert bill.visit_id == visit.id
    assert bill.dispensing_order_id == order.id
    assert bill.subtotal == Decimal("7200.00")
    assert bill.discount_total == Decimal("200.00")
    assert bill.tax_total == Decimal("180.00")
    assert bill.grand_total == Decimal("7180.00")
    assert bill.paid_total == Decimal("3000.00")
    assert bill.balance_amount == Decimal("4180.00")
    assert bill.payment_status == PaymentStatus.PARTIAL


def test_legacy_bill_without_workflow_context_remains_supported(db_session: Session, make_user) -> None:
    actor, patient, _visit, _order = _create_order(db_session, make_user)

    bill = BillService(db_session, TEST_SHOP_ONE).create_bill(_bill_payload(patient.id), actor)

    assert bill.visit_id is None
    assert bill.dispensing_order_id is None


def test_one_active_bill_per_order_and_cancelled_bill_allows_replacement(db_session: Session, make_user) -> None:
    actor, patient, visit, order = _create_order(db_session, make_user)
    service = BillService(db_session, TEST_SHOP_ONE)
    first = service.create_bill(_bill_payload(patient.id, visit.id, order.id), actor)

    with pytest.raises(AppException) as duplicate:
        service.create_bill(_bill_payload(patient.id, visit.id, order.id), actor)
    assert duplicate.value.status_code == 409
    assert duplicate.value.code == "dispensing_order_already_billed"

    service.delete_bill(first.id, actor)
    replacement = service.create_bill(_bill_payload(patient.id, visit.id, order.id), actor)
    assert replacement.dispensing_order_id == order.id


def test_bill_context_rejects_customer_or_visit_mismatch(db_session: Session, make_user) -> None:
    actor, _patient, visit, order = _create_order(db_session, make_user)
    other_patient = CustomerService(db_session, TEST_SHOP_ONE).create_customer(
        CustomerCreate(name="Different Patient", contact_no="9876500888"),
        actor,
    )
    service = BillService(db_session, TEST_SHOP_ONE)

    with pytest.raises(AppException) as mismatch:
        service.create_bill(_bill_payload(other_patient.id, visit.id, order.id), actor)
    assert mismatch.value.status_code == 422
    assert mismatch.value.code == "bill_context_customer_mismatch"


def test_existing_bill_can_be_linked_without_changing_financial_records(db_session: Session, make_user) -> None:
    actor, patient, visit, order = _create_order(db_session, make_user)
    bill_service = BillService(db_session, TEST_SHOP_ONE)
    existing = bill_service.create_bill(_bill_payload(patient.id), actor)
    before = {
        "subtotal": existing.subtotal,
        "discount_total": existing.discount_total,
        "tax_total": existing.tax_total,
        "grand_total": existing.grand_total,
        "paid_total": existing.paid_total,
        "balance_amount": existing.balance_amount,
        "items": [(item.item_type, item.item_name, item.line_total) for item in existing.items],
        "payments": [(payment.mode, payment.amount, payment.reference_no) for payment in existing.payments],
    }

    linked = VisitBillingService(db_session, TEST_SHOP_ONE).link_existing_bill(
        visit.id,
        VisitBillLinkRequest(bill_id=existing.id, dispensing_order_id=order.id),
        actor,
    )
    after = bill_service.get_bill(existing.id)

    assert linked.visit_id == visit.id
    assert linked.dispensing_order_id == order.id
    assert after.subtotal == before["subtotal"]
    assert after.discount_total == before["discount_total"]
    assert after.tax_total == before["tax_total"]
    assert after.grand_total == before["grand_total"]
    assert after.paid_total == before["paid_total"]
    assert after.balance_amount == before["balance_amount"]
    assert [(item.item_type, item.item_name, item.line_total) for item in after.items] == before["items"]
    assert [(payment.mode, payment.amount, payment.reference_no) for payment in after.payments] == before["payments"]


def test_repeated_visit_link_does_not_clear_existing_order_context(db_session: Session, make_user) -> None:
    actor, patient, visit, order = _create_order(db_session, make_user)
    bill = BillService(db_session, TEST_SHOP_ONE).create_bill(
        _bill_payload(patient.id, visit.id, order.id),
        actor,
    )

    linked = VisitBillingService(db_session, TEST_SHOP_ONE).link_existing_bill(
        visit.id,
        VisitBillLinkRequest(bill_id=bill.id),
        actor,
    )

    assert linked.visit_id == visit.id
    assert linked.dispensing_order_id == order.id


def test_visit_billing_context_returns_official_bill_totals(db_session: Session, make_user) -> None:
    actor, patient, visit, order = _create_order(db_session, make_user)
    bill = BillService(db_session, TEST_SHOP_ONE).create_bill(
        _bill_payload(patient.id, visit.id, order.id),
        actor,
    )

    context = VisitBillingService(db_session, TEST_SHOP_ONE).get_context(visit.id, actor)

    assert context.dispensing_order_id == order.id
    assert context.order_bill is not None
    assert context.order_bill.id == bill.id
    assert context.order_bill.grand_total == bill.grand_total
    assert context.order_bill.paid_total == bill.paid_total
    assert context.order_bill.balance_amount == bill.balance_amount
    assert [item.id for item in context.visit_bills] == [bill.id]


def test_visit_billing_context_is_hidden_from_another_shop(db_session: Session, make_user) -> None:
    _actor, _patient, visit, _order = _create_order(db_session, make_user)
    other_shop_actor = make_user("other-shop-admin@example.com", shop_key=TEST_SHOP_TWO)

    with pytest.raises(AppException) as hidden:
        VisitBillingService(db_session, TEST_SHOP_TWO).get_context(visit.id, other_shop_actor)

    assert hidden.value.status_code == 404
    assert hidden.value.code == "visit_not_found"
