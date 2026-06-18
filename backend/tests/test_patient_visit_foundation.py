from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.enums import ExamSectionState, UserRole, VisitStatus
from app.schemas.customer import CustomerCreate
from app.schemas.visit import VisitCreate
from app.schemas.visit_exam_section import VisitExamSectionUpdate
from app.services.customer_service import CustomerService
from app.services.visit_exam_section_service import VisitExamSectionService
from app.services.visit_service import VisitService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO


def test_patient_registration_idempotency_prevents_duplicate_customers(db_session: Session, make_user) -> None:
    actor = make_user("patient-idempotency@example.com", TEST_SHOP_ONE)
    service = CustomerService(db_session, shop_key=TEST_SHOP_ONE)

    payload = CustomerCreate(
        name="Riya Shah",
        age=29,
        contact_no="9876500001",
        occupation="Teacher",
        guardian_name="",
        guardian_contact_no="",
        whatsapp_opt_in=False,
        registration_idempotency_key="register-riya-001",
    )

    first = service.create_customer(payload=payload, actor=actor)
    second = service.create_customer(payload=payload, actor=actor)

    assert first.id == second.id
    assert service.list_customers(page=1, page_size=10, search="9876500001").total == 1


def test_start_visit_for_existing_patient_is_idempotent_and_shop_scoped(db_session: Session, make_user) -> None:
    actor_one = make_user("visit-admin-one@example.com", TEST_SHOP_ONE)
    actor_two = make_user("visit-admin-two@example.com", TEST_SHOP_TWO)

    patient = CustomerService(db_session, shop_key=TEST_SHOP_ONE).create_customer(
        payload=CustomerCreate(
            name="Amit Visit",
            contact_no="9876500002",
            whatsapp_opt_in=False,
        ),
        actor=actor_one,
    )

    visit_service = VisitService(db_session, shop_key=TEST_SHOP_ONE)
    payload = VisitCreate(
        customer_id=patient.id,
        visit_date=datetime(2026, 6, 17, 10, 30, tzinfo=UTC),
        reason_for_visit="Blurred distance vision",
        referred_by="Walk-in",
        assigned_examiner_id=actor_one.id,
        visit_notes="First visit in new workflow",
        idempotency_key="visit-amit-001",
    )

    first = visit_service.start_visit(payload=payload, actor=actor_one)
    second = visit_service.start_visit(payload=payload, actor=actor_one)

    assert first.id == second.id
    assert first.status == VisitStatus.DRAFT
    assert first.customer_id == patient.id
    assert visit_service.list_customer_visits(patient.id).total == 1

    with pytest.raises(AppException) as cross_shop_read:
        VisitService(db_session, shop_key=TEST_SHOP_TWO).get_visit(first.id, actor=actor_two)
    assert cross_shop_read.value.status_code == 404


def test_customer_history_includes_visits_without_losing_legacy_history(db_session: Session, make_user) -> None:
    actor = make_user("history-admin@example.com", TEST_SHOP_ONE)
    customer_service = CustomerService(db_session, shop_key=TEST_SHOP_ONE)
    patient = customer_service.create_customer(
        payload=CustomerCreate(name="Visit History Patient", contact_no="9876500003", whatsapp_opt_in=False),
        actor=actor,
    )

    visit = VisitService(db_session, shop_key=TEST_SHOP_ONE).start_visit(
        payload=VisitCreate(
            customer_id=patient.id,
            reason_for_visit="Annual eye check",
            referred_by="Family",
            idempotency_key="visit-history-001",
        ),
        actor=actor,
    )

    detail = customer_service.get_customer(patient.id)

    assert [item.id for item in detail.visits] == [visit.id]
    assert detail.visits[0].reason_for_visit == "Annual eye check"
    assert detail.prescriptions == []
    assert detail.bills == []


def test_customer_history_includes_visit_referral_summary(db_session: Session, make_user) -> None:
    actor = make_user("history-referral-admin@example.com", TEST_SHOP_ONE)
    customer_service = CustomerService(db_session, shop_key=TEST_SHOP_ONE)
    patient = customer_service.create_customer(
        payload=CustomerCreate(name="Referral History Patient", contact_no="9876500013", whatsapp_opt_in=False),
        actor=actor,
    )
    visit = VisitService(db_session, shop_key=TEST_SHOP_ONE).start_visit(
        payload=VisitCreate(
            customer_id=patient.id,
            reason_for_visit="Retina review needed",
            referred_by="Optometrist",
            idempotency_key="visit-referral-history-001",
        ),
        actor=actor,
    )
    VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE).save_section(
        visit_id=visit.id,
        section_key="referral",
        payload=VisitExamSectionUpdate(
            state=ExamSectionState.COMPLETE,
            payload={
                "referral_required": True,
                "specialist_type": "retina_specialist",
                "referral_status": "pending",
                "notes": "Refer for dilated retina evaluation",
                "follow_up": "Call patient after specialist visit",
            },
        ),
        actor=actor,
    )

    detail = customer_service.get_customer(patient.id)

    assert len(detail.referrals) == 1
    assert detail.referrals[0].visit_id == visit.id
    assert detail.referrals[0].specialist_type == "retina_specialist"
    assert detail.referrals[0].referral_status == "pending"
    assert detail.referrals[0].notes == "Refer for dilated retina evaluation"
    assert detail.referrals[0].follow_up == "Call patient after specialist visit"


def test_staff_cannot_assign_visit_to_another_examiner(db_session: Session, make_user) -> None:
    staff = make_user("visit-staff@example.com", TEST_SHOP_ONE, role=UserRole.STAFF)
    other_staff = make_user("visit-other-staff@example.com", TEST_SHOP_ONE, role=UserRole.STAFF)
    patient = CustomerService(db_session, shop_key=TEST_SHOP_ONE).create_customer(
        payload=CustomerCreate(name="Staff Assign Patient", contact_no="9876500004", whatsapp_opt_in=False),
        actor=staff,
    )

    with pytest.raises(AppException) as raised:
        VisitService(db_session, shop_key=TEST_SHOP_ONE).start_visit(
            payload=VisitCreate(
                customer_id=patient.id,
                reason_for_visit="Headache with near work",
                assigned_examiner_id=other_staff.id,
            ),
            actor=staff,
        )

    assert raised.value.status_code == 403
