from __future__ import annotations

from datetime import UTC, datetime
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.db.base import Base
from app.models.bill import Bill
from app.models.enums import BillItemType, ExamSectionState, PaymentMode
from app.schemas.bill import BillCreate
from app.models.visit import Visit
from app.schemas.customer import CustomerCreate
from app.schemas.visit import VisitCreate
from app.schemas.visit_exam_section import VisitExamSectionUpdate
from app.services.customer_service import CustomerService
from app.services.bill_service import BillService
from app.services.visit_exam_section_service import VisitExamSectionService
from app.services.visit_service import VisitService
from tests.conftest import TEST_SHOP_ONE


def _create_visit(
    db_session: Session,
    make_user,
    *,
    reason: str,
    request_contact_lens: bool = False,
):
    actor = make_user("phase-nine@example.com", TEST_SHOP_ONE)
    patient = CustomerService(db_session, TEST_SHOP_ONE).create_customer(
        CustomerCreate(name="Contact Lens Patient", contact_no="9876500991"),
        actor,
    )
    visit = VisitService(db_session, TEST_SHOP_ONE).start_visit(
        VisitCreate(
            customer_id=patient.id,
            visit_date=datetime(2026, 6, 18, 12, 0, tzinfo=UTC),
            reason_for_visit=reason,
            contact_lens_workup_requested=request_contact_lens,
            idempotency_key=f"phase-nine-{reason}-{request_contact_lens}",
        ),
        actor,
    )
    return actor, patient, visit


def _contact_lens_section(db_session: Session, visit_id: int, actor):
    sections = VisitExamSectionService(db_session, TEST_SHOP_ONE).list_sections(visit_id, actor)
    return next(section for section in sections.sections if section.key == "contact_lens")


def test_contact_lens_section_is_hidden_for_ordinary_spectacle_visit(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Routine spectacle check",
    )

    section = _contact_lens_section(db_session, visit.id, actor)

    assert section.is_visible is False
    assert section.is_optional is True
    assert section.is_required is False


def test_contact_lens_section_is_visible_for_reason_or_explicit_request(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact-lens fitting and trial",
        request_contact_lens=True,
    )

    section = _contact_lens_section(db_session, visit.id, actor)

    assert visit.contact_lens_workup_requested is True
    assert section.is_visible is True
    assert section.is_optional is True


def test_contact_lens_models_are_additive_and_order_billing_is_unique() -> None:
    assert Visit.__table__.columns.get("contact_lens_workup_requested") is not None
    assert "contact_lens_orders" in Base.metadata.tables
    assert "follow_up_tasks" in Base.metadata.tables
    assert Bill.__table__.columns.get("contact_lens_order_id") is not None
    index = next(index for index in Bill.__table__.indexes if index.name == "uq_bills_active_contact_lens_order")
    assert index.unique is True
    assert index.dialect_options["postgresql"]["where"] is not None
    assert index.dialect_options["sqlite"]["where"] is not None


def _workup_payload() -> dict:
    return {
        "indication": {"type": "refractive", "other": None},
        "assessment": {
            "right": {"k_reading": "43.25 / 44.00", "hvid_mm": "11.8", "tear_film": "Normal", "tbut_seconds": "9"},
            "left": {"k_reading": "43.50 / 44.25", "hvid_mm": "11.7", "tear_film": "Mild dryness", "tbut_seconds": "8"},
            "clinical_notes": "Good initial candidate",
        },
        "prescription": {
            "right": {"power": "-2.00", "base_curve_mm": "8.6", "diameter_mm": "14.2"},
            "left": {"power": "-1.75", "base_curve_mm": "8.6", "diameter_mm": "14.2"},
        },
        "lens_details": {
            "brand": "Acuvue Oasys",
            "material": "Senofilcon A",
            "replacement_schedule": "Fortnightly",
            "wearing_schedule": "Daily wear",
        },
        "trial_training": {
            "trial_lens_dispensed": True,
            "training_status": "completed",
            "notes": "Patient can insert and remove independently",
        },
    }


def test_contact_lens_draft_preserves_distinct_right_and_left_values(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact lens fitting",
        request_contact_lens=True,
    )
    payload = _workup_payload()

    saved = VisitExamSectionService(db_session, TEST_SHOP_ONE).save_section(
        visit.id,
        "contact_lens",
        VisitExamSectionUpdate(state=ExamSectionState.INCOMPLETE, payload=payload),
        actor,
    )

    assert saved.payload["prescription"]["right"]["power"] == "-2.00"
    assert saved.payload["prescription"]["left"]["power"] == "-1.75"
    assert saved.payload["assessment"]["right"]["tbut_seconds"] == "9"
    assert saved.payload["assessment"]["left"]["tbut_seconds"] == "8"


def test_completed_contact_lens_workup_requires_custom_other_indication(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact lens fitting",
        request_contact_lens=True,
    )
    payload = _workup_payload()
    payload["indication"] = {"type": "other", "other": ""}

    with pytest.raises(AppException) as invalid:
        VisitExamSectionService(db_session, TEST_SHOP_ONE).save_section(
            visit.id,
            "contact_lens",
            VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload=payload),
            actor,
        )

    assert invalid.value.code == "exam_section_validation_failed"
    assert "custom indication" in invalid.value.message.lower()


def test_completed_contact_lens_workup_requires_each_eye_prescription(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact lens fitting",
        request_contact_lens=True,
    )
    payload = _workup_payload()
    payload["prescription"]["left"]["diameter_mm"] = ""

    with pytest.raises(AppException) as invalid:
        VisitExamSectionService(db_session, TEST_SHOP_ONE).save_section(
            visit.id,
            "contact_lens",
            VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload=payload),
            actor,
        )

    assert invalid.value.code == "exam_section_validation_failed"
    assert "left eye diameter" in invalid.value.message.lower()


def _save_workup(db_session: Session, visit_id: int, actor) -> None:
    VisitExamSectionService(db_session, TEST_SHOP_ONE).save_section(
        visit_id,
        "contact_lens",
        VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload=_workup_payload()),
        actor,
    )


def _create_contact_lens_order(db_session: Session, make_user):
    from app.schemas.contact_lens import ContactLensOrderUpdate
    from app.services.contact_lens_service import ContactLensService

    actor, patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact lens fitting",
        request_contact_lens=True,
    )
    _save_workup(db_session, visit.id, actor)
    order = ContactLensService(db_session, TEST_SHOP_ONE).save_order(
        visit.id,
        ContactLensOrderUpdate(lens_details=_workup_payload()["lens_details"]),
        actor,
    )
    return actor, patient, visit, order


def test_contact_lens_order_uses_saved_workup_and_has_controlled_status(db_session: Session, make_user) -> None:
    from app.models.enums import DispensingOrderStatus
    from app.schemas.contact_lens import ContactLensOrderStatusUpdate, ContactLensOrderUpdate
    from app.services.contact_lens_service import ContactLensService

    actor, patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact lens fitting",
        request_contact_lens=True,
    )
    _save_workup(db_session, visit.id, actor)
    service = ContactLensService(db_session, TEST_SHOP_ONE)

    order = service.save_order(
        visit.id,
        ContactLensOrderUpdate(
            vendor_id=None,
            lens_details=_workup_payload()["lens_details"],
            order_notes="Supply two boxes per eye",
        ),
        actor,
    )
    ready = service.change_order_status(
        visit.id,
        ContactLensOrderStatusUpdate(status=DispensingOrderStatus.READY_FOR_VENDOR),
        actor,
    )

    assert order.customer_id == patient.id
    assert order.workup_snapshot["prescription"]["right"]["power"] == "-2.00"
    assert order.workup_snapshot["prescription"]["left"]["power"] == "-1.75"
    assert order.status == DispensingOrderStatus.DRAFT
    assert ready.status == DispensingOrderStatus.READY_FOR_VENDOR

    with pytest.raises(AppException) as invalid:
        service.change_order_status(
            visit.id,
            ContactLensOrderStatusUpdate(status=DispensingOrderStatus.DELIVERED),
            actor,
        )
    assert invalid.value.code == "contact_lens_order_invalid_status_transition"


def test_contact_lens_follow_up_is_idempotent_and_preserves_completion(db_session: Session, make_user) -> None:
    from app.models.enums import FollowUpInterval, FollowUpStatus
    from app.schemas.contact_lens import ContactLensFollowUpSchedule, ContactLensOrderUpdate
    from app.services.contact_lens_service import ContactLensService

    actor, _patient, visit = _create_visit(
        db_session,
        make_user,
        reason="Contact lens fitting",
        request_contact_lens=True,
    )
    _save_workup(db_session, visit.id, actor)
    service = ContactLensService(db_session, TEST_SHOP_ONE)
    service.save_order(
        visit.id,
        ContactLensOrderUpdate(lens_details=_workup_payload()["lens_details"]),
        actor,
    )

    first = service.schedule_follow_up(
        visit.id,
        ContactLensFollowUpSchedule(interval=FollowUpInterval.ONE_WEEK, notes="Initial review"),
        actor,
    )
    repeated = service.schedule_follow_up(
        visit.id,
        ContactLensFollowUpSchedule(interval=FollowUpInterval.FIFTEEN_DAYS, notes="Adjusted review"),
        actor,
    )

    assert repeated.id == first.id
    assert repeated.due_date == date.today() + timedelta(days=15)
    assert repeated.notes == "Adjusted review"

    completed = service.change_follow_up_status(visit.id, FollowUpStatus.COMPLETED, actor)
    assert completed.status == FollowUpStatus.COMPLETED
    assert completed.completed_by == actor.id
    assert completed.completed_at is not None

    with pytest.raises(AppException) as preserved:
        service.schedule_follow_up(
            visit.id,
            ContactLensFollowUpSchedule(interval=FollowUpInterval.ONE_MONTH),
            actor,
        )
    assert preserved.value.code == "contact_lens_follow_up_read_only"


def test_contact_lens_order_bill_reuses_official_totals_and_allows_replacement_after_delete(
    db_session: Session,
    make_user,
) -> None:
    actor, patient, visit, order = _create_contact_lens_order(db_session, make_user)
    service = BillService(db_session, TEST_SHOP_ONE)
    payload = BillCreate(
        customer_id=patient.id,
        visit_id=visit.id,
        contact_lens_order_id=order.id,
        tax_total=Decimal("90.00"),
        items=[
            {
                "item_type": BillItemType.CONTACT_LENS,
                "item_name": "Acuvue Oasys fortnightly lenses",
                "quantity": Decimal("2"),
                "unit_price": Decimal("1200.00"),
                "discount": Decimal("100.00"),
            }
        ],
        payments=[{"mode": PaymentMode.UPI, "amount": Decimal("1000.00"), "reference_no": "CL-UPI"}],
    )

    with patch.object(BillService, "_try_auto_generate_pdf", return_value=None):
        first = service.create_bill(payload, actor)
        assert first.contact_lens_order_id == order.id
        assert first.subtotal == Decimal("2400.00")
        assert first.discount_total == Decimal("100.00")
        assert first.grand_total == Decimal("2390.00")
        assert first.paid_total == Decimal("1000.00")
        assert first.balance_amount == Decimal("1390.00")

        with pytest.raises(AppException) as duplicate:
            service.create_bill(payload, actor)
        assert duplicate.value.code == "contact_lens_order_already_billed"

        service.delete_bill(first.id, actor)
        replacement = service.create_bill(payload, actor)
        assert replacement.contact_lens_order_id == order.id


def test_contact_lens_history_contains_order_and_follow_up_without_cross_shop_access(
    db_session: Session,
    make_user,
) -> None:
    from app.models.enums import FollowUpInterval
    from app.schemas.contact_lens import ContactLensFollowUpSchedule
    from app.services.contact_lens_service import ContactLensService
    from tests.conftest import TEST_SHOP_TWO

    actor, patient, visit, order = _create_contact_lens_order(db_session, make_user)
    follow_up = ContactLensService(db_session, TEST_SHOP_ONE).schedule_follow_up(
        visit.id,
        ContactLensFollowUpSchedule(interval=FollowUpInterval.ONE_WEEK, notes="Check comfort"),
        actor,
    )

    detail = CustomerService(db_session, TEST_SHOP_ONE).get_customer(patient.id)

    assert len(detail.contact_lens_orders) == 1
    assert detail.contact_lens_orders[0].id == order.id
    assert detail.contact_lens_orders[0].visit_id == visit.id
    assert detail.contact_lens_orders[0].order_reference == order.order_reference
    assert len(detail.follow_up_tasks) == 1
    assert detail.follow_up_tasks[0].id == follow_up.id
    assert detail.follow_up_tasks[0].due_date == follow_up.due_date

    with pytest.raises(AppException) as hidden:
        CustomerService(db_session, TEST_SHOP_TWO).get_customer(patient.id)
    assert hidden.value.code == "customer_not_found"
