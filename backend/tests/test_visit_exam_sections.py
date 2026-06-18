from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.exam_sections import EXAM_SECTION_DEFINITIONS
from app.models.enums import ExamSectionState
from app.schemas.customer import CustomerCreate
from app.schemas.visit import VisitCreate
from app.schemas.visit_exam_section import VisitExamSectionUpdate
from app.services.customer_service import CustomerService
from app.services.visit_exam_section_service import VisitExamSectionService
from app.services.visit_service import VisitService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO


def _create_visit(db_session: Session, make_user, shop_key: str = TEST_SHOP_ONE):
    actor = make_user(f"exam-{shop_key}@example.com", shop_key)
    patient = CustomerService(db_session, shop_key=shop_key).create_customer(
        payload=CustomerCreate(name=f"Exam Patient {shop_key}", contact_no="9876500100", whatsapp_opt_in=False),
        actor=actor,
    )
    visit = VisitService(db_session, shop_key=shop_key).start_visit(
        payload=VisitCreate(
            customer_id=patient.id,
            visit_date=datetime(2026, 6, 17, 11, 30, tzinfo=UTC),
            reason_for_visit="Comprehensive eye examination",
            idempotency_key=f"exam-visit-{shop_key}",
        ),
        actor=actor,
    )
    return actor, patient, visit


def _create_visit_for_patient(db_session: Session, actor, patient_id: int, idempotency_key: str):
    return VisitService(db_session, shop_key=actor.shop_key).start_visit(
        payload=VisitCreate(
            customer_id=patient_id,
            visit_date=datetime(2026, 6, 17, 12, 30, tzinfo=UTC),
            reason_for_visit="Follow-up refraction",
            idempotency_key=idempotency_key,
        ),
        actor=actor,
    )


def test_exam_section_registry_contains_phase_three_sections() -> None:
    section_keys = [section.key for section in EXAM_SECTION_DEFINITIONS]

    assert section_keys == [
        "patient_visit",
        "visual_acuity",
        "objective_refraction",
        "subjective_refraction",
        "binocular_vision",
        "cycloplegic_refraction",
        "final_prescription",
        "potential_vision",
        "torch_light_evaluation",
        "slit_lamp_evaluation",
        "referral",
        "frame_dispensing",
        "lens_order",
        "contact_lens",
        "billing",
        "completion_follow_up",
        "iop_future",
    ]
    iop = next(section for section in EXAM_SECTION_DEFINITIONS if section.key == "iop_future")
    assert iop.is_disabled is True
    assert iop.state == ExamSectionState.FUTURE


def test_exam_sections_can_be_saved_and_reopened(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)

    saved = service.save_section(
        visit_id=visit.id,
        section_key="visual_acuity",
        payload=VisitExamSectionUpdate(
            state=ExamSectionState.COMPLETE,
            payload={
                "distance": {
                    "right": {"unaided": "6/9", "pinhole": "6/6"},
                    "left": {"unaided": "6/12", "pinhole": "6/9"},
                },
                "notes": "Saved from section draft",
            },
        ),
        actor=actor,
    )

    reopened = service.list_sections(visit_id=visit.id, actor=actor)
    visual_acuity = next(section for section in reopened.sections if section.key == "visual_acuity")

    assert saved.state == ExamSectionState.COMPLETE
    assert visual_acuity.payload["distance"]["right"]["unaided"] == "6/9"
    assert visual_acuity.saved_at == saved.saved_at


def test_cross_shop_cannot_read_or_write_exam_sections(db_session: Session, make_user) -> None:
    actor_one, _patient, visit = _create_visit(db_session, make_user, TEST_SHOP_ONE)
    actor_two = make_user("exam-cross-shop@example.com", TEST_SHOP_TWO)
    _ = actor_one

    with pytest.raises(AppException) as raised:
        VisitExamSectionService(db_session, shop_key=TEST_SHOP_TWO).list_sections(visit_id=visit.id, actor=actor_two)
    assert raised.value.status_code == 404

    with pytest.raises(AppException) as write_raised:
        VisitExamSectionService(db_session, shop_key=TEST_SHOP_TWO).save_section(
            visit_id=visit.id,
            section_key="subjective_refraction",
            payload=VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload={"notes": "wrong branch"}),
            actor=actor_two,
        )
    assert write_raised.value.status_code == 404


def test_invalid_or_disabled_sections_are_rejected(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)

    with pytest.raises(AppException) as invalid:
        service.save_section(
            visit_id=visit.id,
            section_key="unknown_section",
            payload=VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload={}),
            actor=actor,
        )
    assert invalid.value.status_code == 404

    with pytest.raises(AppException) as disabled:
        service.save_section(
            visit_id=visit.id,
            section_key="iop_future",
            payload=VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload={"iop": "18"}),
            actor=actor,
        )
    assert disabled.value.status_code == 400


def test_completed_refraction_validates_axis_and_optical_values_but_draft_can_remain_incomplete(
    db_session: Session,
    make_user,
) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)
    invalid_payload = {
        "eye_values": {
            "right": {"sph": "banana", "cyl": "-1.00", "axis": "220", "va": "6/9"},
            "left": {"sph": "+0.50", "cyl": "-0.50", "axis": "", "va": "6/6"},
        },
        "method": "autorefractometer",
    }

    draft = service.save_section(
        visit_id=visit.id,
        section_key="objective_refraction",
        payload=VisitExamSectionUpdate(state=ExamSectionState.INCOMPLETE, payload=invalid_payload),
        actor=actor,
    )
    assert draft.payload["eye_values"]["right"]["axis"] == "220"

    with pytest.raises(AppException) as raised:
        service.save_section(
            visit_id=visit.id,
            section_key="objective_refraction",
            payload=VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload=invalid_payload),
            actor=actor,
        )

    assert raised.value.status_code == 422
    assert "Right eye SPH must be Plano or a signed optical power" in raised.value.message
    assert "Right eye axis must be between 0 and 180" in raised.value.message
    assert "Left eye axis is required when cylinder is entered" in raised.value.message


def test_previous_core_exam_values_are_viewable_without_overwriting_current_visit(
    db_session: Session,
    make_user,
) -> None:
    actor, patient, first_visit = _create_visit(db_session, make_user)
    second_visit = _create_visit_for_patient(db_session, actor, patient.id, "exam-second-visit")
    service = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)

    service.save_section(
        visit_id=first_visit.id,
        section_key="visual_acuity",
        payload=VisitExamSectionUpdate(
            state=ExamSectionState.COMPLETE,
            payload={
                "distance": {
                    "right": {"unaided": "6/9"},
                    "left": {"unaided": "6/12"},
                    "both": {"unaided": "6/9"},
                },
                "near": {"both": {"unaided": "N6"}},
            },
        ),
        actor=actor,
    )

    history = service.list_previous_core_sections(visit_id=second_visit.id, actor=actor)
    current = service.list_sections(visit_id=second_visit.id, actor=actor)
    visual_acuity = next(section for section in current.sections if section.key == "visual_acuity")

    assert len(history.items) == 1
    assert history.items[0].visit_id == first_visit.id
    assert history.items[0].section_key == "visual_acuity"
    assert history.items[0].payload["distance"]["right"]["unaided"] == "6/9"
    assert visual_acuity.payload == {}


def test_completed_cycloplegic_refraction_validates_only_when_performed(
    db_session: Session,
    make_user,
) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)

    not_done = service.save_section(
        visit_id=visit.id,
        section_key="cycloplegic_refraction",
        payload=VisitExamSectionUpdate(
            state=ExamSectionState.COMPLETE,
            payload={"not_done": True, "performed": False, "notes": "Deferred today"},
        ),
        actor=actor,
    )
    assert not_done.payload["not_done"] is True

    with pytest.raises(AppException) as raised:
        service.save_section(
            visit_id=visit.id,
            section_key="cycloplegic_refraction",
            payload=VisitExamSectionUpdate(
                state=ExamSectionState.COMPLETE,
                payload={
                    "performed": True,
                    "drug_used": "",
                    "time_instilled": "",
                    "eye_values": {
                        "right": {"sph": "+1.00", "cyl": "-1.00", "axis": "190"},
                        "left": {"sph": "+0.50", "cyl": "-0.50", "axis": ""},
                    },
                },
            ),
            actor=actor,
        )

    assert raised.value.status_code == 422
    assert "Cycloplegic drug used is required when performed" in raised.value.message
    assert "Cycloplegic instillation time is required when performed" in raised.value.message
    assert "Right eye axis must be between 0 and 180" in raised.value.message
    assert "Left eye axis is required when cylinder is entered" in raised.value.message


def test_completed_torch_and_slit_lamp_reject_silent_normal_abnormal_conflicts(
    db_session: Session,
    make_user,
) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)
    conflicting_torch_payload = {
        "findings": {
            "lids": {"normal": True, "abnormal_findings": ["Swelling"], "notes": ""},
            "conjunctiva": {"normal": True, "abnormal_findings": [], "notes": ""},
        }
    }

    draft = service.save_section(
        visit_id=visit.id,
        section_key="torch_light_evaluation",
        payload=VisitExamSectionUpdate(state=ExamSectionState.INCOMPLETE, payload=conflicting_torch_payload),
        actor=actor,
    )
    assert draft.payload["findings"]["lids"]["abnormal_findings"] == ["Swelling"]

    with pytest.raises(AppException) as torch_raised:
        service.save_section(
            visit_id=visit.id,
            section_key="torch_light_evaluation",
            payload=VisitExamSectionUpdate(state=ExamSectionState.COMPLETE, payload=conflicting_torch_payload),
            actor=actor,
        )
    assert torch_raised.value.status_code == 422
    assert "Lids cannot be marked normal with abnormal findings" in torch_raised.value.message

    with pytest.raises(AppException) as slit_raised:
        service.save_section(
            visit_id=visit.id,
            section_key="slit_lamp_evaluation",
            payload=VisitExamSectionUpdate(
                state=ExamSectionState.COMPLETE,
                payload={
                    "eyes": {
                        "right": {
                            "lens": {
                                "normal": True,
                                "findings": ["Cataract"],
                                "cataract_grade": "Grade 2",
                                "notes": "",
                            }
                        },
                        "left": {
                            "cornea": {
                                "normal": True,
                                "findings": [],
                                "notes": "Corneal scar",
                            }
                        },
                    }
                },
            ),
            actor=actor,
        )
    assert slit_raised.value.status_code == 422
    assert "Right eye lens cannot be marked normal with abnormal findings" in slit_raised.value.message
    assert "Left eye cornea cannot be marked normal with abnormal findings" in slit_raised.value.message
