from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.enums import ExamSectionState, PrescriptionVersionStatus, VisitStatus
from app.models.visit_prescription import VisitPrescription
from app.schemas.customer import CustomerCreate
from app.schemas.visit import VisitCreate
from app.schemas.visit_exam_section import VisitExamSectionUpdate
from app.schemas.visit_prescription import (
    PrescriptionFinalizeRequest,
    VisitCompletionRequest,
    VisitPrescriptionDraftUpdate,
)
from app.services.customer_service import CustomerService
from app.services.visit_exam_section_service import VisitExamSectionService
from app.services.visit_prescription_service import VisitPrescriptionService
from app.services.visit_service import VisitService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO


def _create_visit(db_session: Session, make_user, shop_key: str = TEST_SHOP_ONE):
    actor = make_user(f"phase-six-{shop_key}@example.com", shop_key)
    patient = CustomerService(db_session, shop_key=shop_key).create_customer(
        payload=CustomerCreate(name=f"Phase Six Patient {shop_key}", contact_no="9876500111", whatsapp_opt_in=False),
        actor=actor,
    )
    visit = VisitService(db_session, shop_key=shop_key).start_visit(
        payload=VisitCreate(
            customer_id=patient.id,
            visit_date=datetime(2026, 6, 18, 9, 30, tzinfo=UTC),
            reason_for_visit="Final prescription review",
            idempotency_key=f"phase-six-{shop_key}",
        ),
        actor=actor,
    )
    return actor, patient, visit


def _valid_draft() -> VisitPrescriptionDraftUpdate:
    return VisitPrescriptionDraftUpdate(
        data={
            "distance": {
                "right": {"sph": "-1.00", "cyl": "-0.50", "axis": "90", "va": "6/6"},
                "left": {"sph": "-0.75", "cyl": "-0.25", "axis": "80", "va": "6/6"},
            },
            "near": {
                "right": {"sph": "+0.50", "cyl": "", "axis": "", "add": "+1.50", "va": "N6"},
                "left": {"sph": "+0.50", "cyl": "", "axis": "", "add": "+1.50", "va": "N6"},
            },
            "pd": "62",
            "fitting_height": "18",
        },
        patient_instructions="Use for distance and reading. Review after 12 months.",
    )


def test_visit_prescription_table_enforces_one_current_and_one_draft_per_visit() -> None:
    index_names = {index.name for index in VisitPrescription.__table__.indexes}

    assert "uq_visit_prescriptions_current_per_visit" in index_names
    assert "uq_visit_prescriptions_draft_per_visit" in index_names


def test_prescription_draft_is_saved_and_updated_as_version_one(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)

    created = service.save_draft(visit.id, _valid_draft(), actor)
    updated_payload = _valid_draft().model_copy(update={"patient_instructions": "Updated patient instructions"})
    updated = service.save_draft(visit.id, updated_payload, actor)
    summary = service.get_summary(visit.id, actor)

    assert created.id == updated.id
    assert created.version_number == 1
    assert updated.status == PrescriptionVersionStatus.DRAFT
    assert updated.patient_instructions == "Updated patient instructions"
    assert summary.draft_version_id == created.id
    assert summary.current_version_id is None
    assert len(summary.versions) == 1


def test_review_contains_context_clinical_summary_referral_and_warnings(db_session: Session, make_user) -> None:
    actor, patient, visit = _create_visit(db_session, make_user)
    sections = VisitExamSectionService(db_session, shop_key=TEST_SHOP_ONE)
    sections.save_section(
        visit.id,
        "subjective_refraction",
        VisitExamSectionUpdate(
            state=ExamSectionState.COMPLETE,
            payload={"eye_values": {"right": {"sph": "-1.00"}, "left": {"sph": "-0.75"}}},
        ),
        actor,
    )
    sections.save_section(
        visit.id,
        "referral",
        VisitExamSectionUpdate(
            state=ExamSectionState.COMPLETE,
            payload={
                "referral_required": True,
                "specialist_type": "Ophthalmologist",
                "referral_status": "Pending",
                "notes": "Review cataract",
            },
        ),
        actor,
    )
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    draft = service.save_draft(visit.id, _valid_draft(), actor)

    review = service.get_review(visit.id, draft.id, actor)

    assert review.patient.id == patient.id
    assert review.visit.id == visit.id
    assert review.examiner.id == actor.id
    assert review.core_examination_summary["subjective_refraction"]["state"] == "complete"
    assert review.referral_summary["specialist_type"] == "Ophthalmologist"
    assert review.patient_instructions.startswith("Use for distance")
    assert any("Visual Acuity" in warning for warning in review.warnings)


def test_finalization_is_explicit_strict_and_makes_version_read_only(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    draft = service.save_draft(visit.id, _valid_draft(), actor)

    with pytest.raises(AppException) as confirmation_error:
        service.finalize(visit.id, draft.id, PrescriptionFinalizeRequest(confirmed=False), actor)
    assert confirmation_error.value.status_code == 400
    assert confirmation_error.value.code == "prescription_finalization_confirmation_required"

    invalid = _valid_draft()
    invalid.data.distance.right.axis = None
    draft = service.save_draft(visit.id, invalid, actor)
    with pytest.raises(AppException) as validation_error:
        service.finalize(visit.id, draft.id, PrescriptionFinalizeRequest(confirmed=True), actor)
    assert validation_error.value.status_code == 422
    assert "Right eye distance axis" in validation_error.value.message

    draft = service.save_draft(visit.id, _valid_draft(), actor)
    finalized = service.finalize(visit.id, draft.id, PrescriptionFinalizeRequest(confirmed=True), actor)

    assert finalized.status == PrescriptionVersionStatus.FINALIZED
    assert finalized.is_current is True
    assert finalized.finalized_by == actor.id
    assert finalized.finalized_at is not None

    with pytest.raises(AppException) as edit_error:
        service.save_draft(visit.id, _valid_draft(), actor)
    assert edit_error.value.status_code == 409
    assert edit_error.value.code == "prescription_amendment_required"


def test_amendment_preserves_history_and_changes_current_only_when_finalized(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    first_draft = service.save_draft(visit.id, _valid_draft(), actor)
    first = service.finalize(visit.id, first_draft.id, PrescriptionFinalizeRequest(confirmed=True), actor)

    amendment = service.create_amendment(visit.id, first.id, actor)
    before_finalizing = service.get_summary(visit.id, actor)

    assert amendment.version_number == 2
    assert amendment.amends_prescription_id == first.id
    assert amendment.status == PrescriptionVersionStatus.DRAFT
    assert before_finalizing.current_version_id == first.id
    assert before_finalizing.draft_version_id == amendment.id

    changed = _valid_draft()
    changed.data.distance.right.sph = "-1.25"
    service.save_draft(visit.id, changed, actor)
    second = service.finalize(visit.id, amendment.id, PrescriptionFinalizeRequest(confirmed=True), actor)
    history = service.get_summary(visit.id, actor)

    first_history = next(version for version in history.versions if version.id == first.id)
    assert first_history.status == PrescriptionVersionStatus.SUPERSEDED
    assert first_history.is_current is False
    assert second.version_number == 2
    assert second.is_current is True
    assert history.current_version_id == second.id
    assert len(history.versions) == 2


def test_visit_completion_requires_current_finalized_prescription_and_confirmation(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)

    with pytest.raises(AppException) as missing:
        service.complete_visit(visit.id, VisitCompletionRequest(confirmed=True), actor)
    assert missing.value.code == "finalized_prescription_required"

    draft = service.save_draft(visit.id, _valid_draft(), actor)
    service.finalize(visit.id, draft.id, PrescriptionFinalizeRequest(confirmed=True), actor)

    with pytest.raises(AppException) as confirmation:
        service.complete_visit(visit.id, VisitCompletionRequest(confirmed=False), actor)
    assert confirmation.value.code == "visit_completion_confirmation_required"

    completed = service.complete_visit(visit.id, VisitCompletionRequest(confirmed=True), actor)
    assert completed.status == VisitStatus.COMPLETED


def test_completed_visit_allows_versioned_prescription_amendment_without_reopening_exam(
    db_session: Session,
    make_user,
) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    draft = service.save_draft(visit.id, _valid_draft(), actor)
    first = service.finalize(visit.id, draft.id, PrescriptionFinalizeRequest(confirmed=True), actor)
    service.complete_visit(visit.id, VisitCompletionRequest(confirmed=True), actor)

    amendment = service.create_amendment(visit.id, first.id, actor)
    corrected = _valid_draft()
    corrected.data.distance.right.sph = "-1.25"
    service.save_draft(visit.id, corrected, actor)
    second = service.finalize(visit.id, amendment.id, PrescriptionFinalizeRequest(confirmed=True), actor)
    completed_visit = VisitService(db_session, shop_key=TEST_SHOP_ONE).get_visit(visit.id, actor)

    assert second.version_number == 2
    assert second.is_current is True
    assert completed_visit.status == VisitStatus.COMPLETED


def test_cross_shop_cannot_access_visit_prescriptions(db_session: Session, make_user) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    service.save_draft(visit.id, _valid_draft(), actor)
    other_actor = make_user("phase-six-other@example.com", TEST_SHOP_TWO)

    with pytest.raises(AppException) as raised:
        VisitPrescriptionService(db_session, shop_key=TEST_SHOP_TWO).get_summary(visit.id, other_actor)
    assert raised.value.status_code == 404


def test_pdf_download_resolves_only_the_current_finalized_version(
    db_session: Session,
    make_user,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor, _patient, visit = _create_visit(db_session, make_user)
    service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    first_draft = service.save_draft(visit.id, _valid_draft(), actor)

    with pytest.raises(AppException) as draft_error:
        service.generate_pdf(visit.id, actor)
    assert draft_error.value.code == "finalized_prescription_required"

    first = service.finalize(visit.id, first_draft.id, PrescriptionFinalizeRequest(confirmed=True), actor)
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    settings.prescription_media_dir.mkdir(parents=True, exist_ok=True)
    first_file = settings.prescription_media_dir / "visit-prescription-v1.pdf"
    first_file.write_bytes(b"version-one")
    monkeypatch.setattr(
        service.pdf_service,
        "generate_visit_prescription_pdf",
        lambda **_kwargs: SimpleNamespace(file_path=first_file),
    )
    service.generate_pdf(visit.id, actor)
    assert service.get_pdf_file_for_download(visit.id, actor) == first_file

    amendment = service.create_amendment(visit.id, first.id, actor)
    changed = _valid_draft()
    changed.data.distance.left.sph = "-1.00"
    service.save_draft(visit.id, changed, actor)
    service.finalize(visit.id, amendment.id, PrescriptionFinalizeRequest(confirmed=True), actor)

    with pytest.raises(AppException) as stale_error:
        service.get_pdf_file_for_download(visit.id, actor)
    assert stale_error.value.code == "prescription_pdf_missing"

    second_file = settings.prescription_media_dir / "visit-prescription-v2.pdf"
    second_file.write_bytes(b"version-two")
    monkeypatch.setattr(
        service.pdf_service,
        "generate_visit_prescription_pdf",
        lambda **_kwargs: SimpleNamespace(file_path=second_file),
    )
    service.generate_pdf(visit.id, actor)
    assert service.get_pdf_file_for_download(visit.id, actor).read_bytes() == b"version-two"
