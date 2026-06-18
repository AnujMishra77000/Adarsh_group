from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exam_sections import EXAM_SECTION_BY_KEY
from app.core.exceptions import AppException
from app.core.shops import get_shop_definition
from app.models.enums import ExamSectionState, PrescriptionVersionStatus, VisitStatus
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_exam_section import VisitExamSection
from app.models.visit_prescription import VisitPrescription
from app.repositories.visit_exam_section_repository import VisitExamSectionRepository
from app.repositories.visit_prescription_repository import VisitPrescriptionRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.visit import VisitRead
from app.schemas.visit_prescription import (
    FinalPrescriptionData,
    PrescriptionFinalizeRequest,
    PrescriptionReviewExaminer,
    PrescriptionReviewPatient,
    PrescriptionReviewVisit,
    VisitCompletionRequest,
    VisitPrescriptionDraftUpdate,
    VisitPrescriptionPdfResponse,
    VisitPrescriptionRead,
    VisitPrescriptionReview,
    VisitPrescriptionSummary,
)
from app.services.audit_service import AuditService
from app.services.document_file_service import build_media_file_reference, resolve_media_file_reference
from app.services.visit_prescription_pdf_service import VisitPrescriptionPdfService
from app.services.visit_service import VisitService


class VisitPrescriptionService:
    CORE_REVIEW_SECTION_KEYS = ("visual_acuity", "objective_refraction", "subjective_refraction", "potential_vision")
    REQUIRED_REVIEW_SECTION_KEYS = ("visual_acuity", "objective_refraction", "subjective_refraction")
    OPTICAL_POWER_RE = re.compile(r"^[+-]?\d{1,2}(?:\.\d{1,2})?$")

    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = VisitPrescriptionRepository(db)
        self.visit_repo = VisitRepository(db)
        self.section_repo = VisitExamSectionRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)
        self.pdf_service = VisitPrescriptionPdfService()

    def _ensure_visit(self, visit_id: int, actor: User) -> Visit:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")
        visit = self.visit_repo.get_by_id(visit_id, shop_key=self.shop_key)
        if not visit:
            raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
        return visit

    @staticmethod
    def _serialize(prescription: VisitPrescription) -> VisitPrescriptionRead:
        return VisitPrescriptionRead(
            id=prescription.id,
            visit_id=prescription.visit_id,
            customer_id=prescription.customer_id,
            version_number=prescription.version_number,
            status=prescription.status,
            is_current=prescription.is_current,
            data=FinalPrescriptionData.model_validate(prescription.data or {}),
            patient_instructions=prescription.patient_instructions,
            amends_prescription_id=prescription.amends_prescription_id,
            finalized_by=prescription.finalized_by,
            finalized_at=prescription.finalized_at,
            created_at=prescription.created_at,
            updated_at=prescription.updated_at,
            created_by=prescription.created_by,
            updated_by=prescription.updated_by,
            has_pdf=bool(prescription.pdf_file_path),
        )

    @classmethod
    def _power_error(cls, value: str | None, label: str, errors: list[str]) -> None:
        if value is None or value.lower() == "plano":
            return
        if not cls.OPTICAL_POWER_RE.match(value):
            errors.append(f"{label} must be Plano or a signed optical power")

    @staticmethod
    def _cylinder_needs_axis(value: str | None) -> bool:
        if value is None or value.lower() == "plano":
            return False
        try:
            return float(value) != 0
        except ValueError:
            return True

    @staticmethod
    def _axis_error(value: str | None, label: str, errors: list[str]) -> None:
        if value is None:
            errors.append(f"{label} is required when cylinder is entered")
            return
        try:
            axis = int(value)
        except ValueError:
            errors.append(f"{label} must be a whole number between 0 and 180")
            return
        if axis < 0 or axis > 180:
            errors.append(f"{label} must be between 0 and 180")

    @classmethod
    def _finalization_errors(cls, data: FinalPrescriptionData) -> list[str]:
        errors: list[str] = []
        has_prescription_value = False
        for section_name, pair in (("distance", data.distance), ("near", data.near)):
            for eye_name, values in (("right", pair.right), ("left", pair.left)):
                label = f"{eye_name.title()} eye {section_name}"
                for field_name, value in (("sphere", values.sph), ("cylinder", values.cyl), ("add", values.add)):
                    if value is not None:
                        has_prescription_value = True
                        cls._power_error(value, f"{label} {field_name}", errors)
                if values.va is not None:
                    has_prescription_value = True
                if cls._cylinder_needs_axis(values.cyl):
                    cls._axis_error(values.axis, f"{label} axis", errors)
        if not has_prescription_value:
            errors.append("At least one final prescription value is required")
        return errors

    def get_summary(self, visit_id: int, actor: User) -> VisitPrescriptionSummary:
        self._ensure_visit(visit_id, actor)
        versions = self.repo.list_for_visit(visit_id, shop_key=self.shop_key)
        current = next((item for item in versions if item.is_current and item.status == PrescriptionVersionStatus.FINALIZED), None)
        draft = next((item for item in versions if item.status == PrescriptionVersionStatus.DRAFT), None)
        return VisitPrescriptionSummary(
            visit_id=visit_id,
            current_version_id=current.id if current else None,
            draft_version_id=draft.id if draft else None,
            versions=[self._serialize(item) for item in versions],
        )

    def save_draft(
        self,
        visit_id: int,
        payload: VisitPrescriptionDraftUpdate,
        actor: User,
    ) -> VisitPrescriptionRead:
        visit = self._ensure_visit(visit_id, actor)
        if visit.status == VisitStatus.CANCELLED:
            raise AppException(status_code=409, code="visit_cancelled", message="Cancelled visits are read-only")

        draft = self.repo.get_draft(visit_id, shop_key=self.shop_key)
        if draft is None:
            current = self.repo.get_current(visit_id, shop_key=self.shop_key)
            if current is not None:
                raise AppException(
                    status_code=409,
                    code="prescription_amendment_required",
                    message="Start an amendment to correct a finalized prescription",
                )
            draft = VisitPrescription(
                shop_key=self.shop_key,
                visit_id=visit.id,
                customer_id=visit.customer_id,
                version_number=self.repo.next_version_number(visit.id, shop_key=self.shop_key),
                status=PrescriptionVersionStatus.DRAFT,
                is_current=False,
                data=payload.data.model_dump(mode="json"),
                patient_instructions=payload.patient_instructions,
                created_by=actor.id,
                updated_by=actor.id,
            )
            action = "visit_prescription.draft_create"
        else:
            draft.data = payload.data.model_dump(mode="json")
            draft.patient_instructions = payload.patient_instructions
            draft.updated_by = actor.id
            action = "visit_prescription.draft_update"

        try:
            if draft.id is None:
                self.repo.create(draft)
            else:
                self.repo.save(draft)
            self.audit_service.log(
                actor_user_id=actor.id,
                action=action,
                entity_type="visit_prescription",
                entity_id=str(draft.id),
                new_values={"visit_id": visit.id, "version_number": draft.version_number},
            )
            self.db.commit()
            self.db.refresh(draft)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="prescription_draft_conflict",
                message="Unable to save prescription draft",
            ) from exc
        return self._serialize(draft)

    def get_review(self, visit_id: int, prescription_id: int, actor: User) -> VisitPrescriptionReview:
        visit = self._ensure_visit(visit_id, actor)
        prescription = self.repo.get_by_id(prescription_id, visit_id, shop_key=self.shop_key)
        if not prescription:
            raise AppException(status_code=404, code="visit_prescription_not_found", message="Prescription version not found")

        records = {record.section_key: record for record in self.section_repo.list_for_visit(visit_id, self.shop_key)}
        core_summary: dict[str, dict] = {}
        warnings: list[str] = []
        for key in self.CORE_REVIEW_SECTION_KEYS:
            record = records.get(key)
            if record:
                core_summary[key] = {"state": record.state.value, "payload": record.payload}
            if key in self.REQUIRED_REVIEW_SECTION_KEYS and (not record or record.state != ExamSectionState.COMPLETE):
                warnings.append(f"{EXAM_SECTION_BY_KEY[key].title} is incomplete")

        referral_record = records.get("referral")
        referral_summary = None
        if referral_record and referral_record.payload.get("referral_required") is True:
            referral_summary = referral_record.payload

        warnings.extend(self._finalization_errors(FinalPrescriptionData.model_validate(prescription.data or {})))
        shop = get_shop_definition(visit.shop_key)
        examiner = visit.assigned_examiner
        return VisitPrescriptionReview(
            prescription=self._serialize(prescription),
            patient=PrescriptionReviewPatient(
                id=visit.customer.id,
                business_id=visit.customer.customer_id,
                name=visit.customer.name,
            ),
            visit=PrescriptionReviewVisit(
                id=visit.id,
                visit_date=visit.visit_date,
                reason_for_visit=visit.reason_for_visit,
                status=visit.status,
                shop_key=visit.shop_key,
                branch_name=shop.display_name if shop else visit.shop_key,
                branch_location=shop.location_label if shop else "",
            ),
            examiner=PrescriptionReviewExaminer(
                id=examiner.id if examiner else actor.id,
                name=(examiner.full_name or examiner.email) if examiner else (actor.full_name or actor.email),
            ),
            core_examination_summary=core_summary,
            referral_summary=referral_summary,
            patient_instructions=prescription.patient_instructions,
            warnings=warnings,
        )

    def _sync_final_section(self, visit_id: int, prescription: VisitPrescription, actor: User) -> None:
        section = self.section_repo.get_for_visit(visit_id, "final_prescription", shop_key=self.shop_key)
        payload = {
            "data": prescription.data,
            "patient_instructions": prescription.patient_instructions,
            "version_id": prescription.id,
            "version_number": prescription.version_number,
        }
        if section:
            section.state = ExamSectionState.COMPLETE
            section.payload = payload
            section.updated_by = actor.id
            self.section_repo.save(section)
            return
        self.section_repo.create(
            VisitExamSection(
                shop_key=self.shop_key,
                visit_id=visit_id,
                section_key="final_prescription",
                state=ExamSectionState.COMPLETE,
                payload=payload,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )

    def finalize(
        self,
        visit_id: int,
        prescription_id: int,
        payload: PrescriptionFinalizeRequest,
        actor: User,
    ) -> VisitPrescriptionRead:
        visit = self._ensure_visit(visit_id, actor)
        if not payload.confirmed:
            raise AppException(
                status_code=400,
                code="prescription_finalization_confirmation_required",
                message="Confirm finalization before continuing",
            )
        if visit.status == VisitStatus.CANCELLED:
            raise AppException(status_code=409, code="visit_cancelled", message="Cancelled visits are read-only")

        prescription = self.repo.get_by_id(prescription_id, visit_id, shop_key=self.shop_key)
        if not prescription:
            raise AppException(status_code=404, code="visit_prescription_not_found", message="Prescription version not found")
        if prescription.status != PrescriptionVersionStatus.DRAFT:
            raise AppException(status_code=409, code="prescription_read_only", message="Finalized prescriptions are read-only")

        errors = self._finalization_errors(FinalPrescriptionData.model_validate(prescription.data or {}))
        if errors:
            raise AppException(status_code=422, code="prescription_validation_failed", message="; ".join(errors))

        previous_current = self.repo.get_current(visit_id, shop_key=self.shop_key)
        if previous_current:
            previous_current.status = PrescriptionVersionStatus.SUPERSEDED
            previous_current.is_current = False
            previous_current.updated_by = actor.id
            self.repo.save(previous_current)

        now = datetime.now(UTC)
        prescription.status = PrescriptionVersionStatus.FINALIZED
        prescription.is_current = True
        prescription.finalized_by = actor.id
        prescription.finalized_at = now
        prescription.pdf_file_path = None
        prescription.updated_by = actor.id
        self.repo.save(prescription)
        self._sync_final_section(visit_id, prescription, actor)
        if visit.status == VisitStatus.DRAFT:
            visit.status = VisitStatus.IN_PROGRESS
            visit.updated_by = actor.id
            self.visit_repo.save(visit)

        self.audit_service.log(
            actor_user_id=actor.id,
            action="visit_prescription.finalize",
            entity_type="visit_prescription",
            entity_id=str(prescription.id),
            new_values={
                "visit_id": visit_id,
                "version_number": prescription.version_number,
                "finalized_at": now.isoformat(),
                "supersedes_id": previous_current.id if previous_current else None,
            },
        )
        self.db.commit()
        self.db.refresh(prescription)
        return self._serialize(prescription)

    def create_amendment(self, visit_id: int, prescription_id: int, actor: User) -> VisitPrescriptionRead:
        visit = self._ensure_visit(visit_id, actor)
        if visit.status == VisitStatus.CANCELLED:
            raise AppException(status_code=409, code="visit_cancelled", message="Cancelled visits are read-only")
        current = self.repo.get_current(visit_id, shop_key=self.shop_key)
        if not current or current.id != prescription_id:
            raise AppException(
                status_code=409,
                code="current_prescription_required",
                message="Only the current finalized prescription can be amended",
            )
        existing_draft = self.repo.get_draft(visit_id, shop_key=self.shop_key)
        if existing_draft:
            raise AppException(status_code=409, code="prescription_draft_exists", message="An amendment draft already exists")

        amendment = VisitPrescription(
            shop_key=self.shop_key,
            visit_id=visit.id,
            customer_id=visit.customer_id,
            version_number=self.repo.next_version_number(visit.id, shop_key=self.shop_key),
            status=PrescriptionVersionStatus.DRAFT,
            is_current=False,
            data=deepcopy(current.data),
            patient_instructions=current.patient_instructions,
            amends_prescription_id=current.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        try:
            self.repo.create(amendment)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="visit_prescription.amendment_create",
                entity_type="visit_prescription",
                entity_id=str(amendment.id),
                old_values={"current_prescription_id": current.id, "version_number": current.version_number},
                new_values={"version_number": amendment.version_number},
            )
            self.db.commit()
            self.db.refresh(amendment)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="prescription_amendment_conflict",
                message="Unable to create prescription amendment",
            ) from exc
        return self._serialize(amendment)

    def complete_visit(self, visit_id: int, payload: VisitCompletionRequest, actor: User) -> VisitRead:
        visit = self._ensure_visit(visit_id, actor)
        if not payload.confirmed:
            raise AppException(
                status_code=400,
                code="visit_completion_confirmation_required",
                message="Confirm visit completion before continuing",
            )
        if not self.repo.get_current(visit_id, shop_key=self.shop_key):
            raise AppException(
                status_code=422,
                code="finalized_prescription_required",
                message="Finalize the current prescription before completing the visit",
            )
        if visit.status == VisitStatus.CANCELLED:
            raise AppException(status_code=409, code="visit_cancelled", message="Cancelled visits cannot be completed")

        visit.status = VisitStatus.COMPLETED
        visit.updated_by = actor.id
        self.visit_repo.save(visit)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="visit.complete",
            entity_type="visit",
            entity_id=str(visit.id),
            old_values={"status": VisitStatus.IN_PROGRESS.value},
            new_values={"status": VisitStatus.COMPLETED.value},
        )
        self.db.commit()
        return VisitService(self.db, shop_key=self.shop_key).get_visit(visit_id, actor)

    @staticmethod
    def _pdf_download_url(visit_id: int) -> str:
        return f"{settings.api_v1_prefix}/visits/{visit_id}/prescription/pdf/download"

    def _resolve_pdf_file(self, prescription: VisitPrescription) -> Path:
        return resolve_media_file_reference(
            prescription.pdf_file_path,
            allowed_dir=settings.prescription_media_dir,
            invalid_code="invalid_prescription_pdf_file_reference",
            missing_code="prescription_pdf_missing",
            missing_message="Current prescription PDF has not been generated",
        )

    @staticmethod
    def _set_pdf_file(prescription: VisitPrescription, file_path: Path) -> str:
        reference = build_media_file_reference(file_path)
        prescription.pdf_file_path = reference
        return reference

    def generate_pdf(self, visit_id: int, actor: User) -> VisitPrescriptionPdfResponse:
        visit = self._ensure_visit(visit_id, actor)
        prescription = self.repo.get_current(visit_id, shop_key=self.shop_key)
        if not prescription:
            raise AppException(
                status_code=422,
                code="finalized_prescription_required",
                message="Finalize the current prescription before generating its PDF",
            )
        examiner = visit.assigned_examiner
        examiner_name = (examiner.full_name or examiner.email) if examiner else (actor.full_name or actor.email)
        generated = self.pdf_service.generate_visit_prescription_pdf(
            prescription=prescription,
            examiner_name=examiner_name,
        )
        reference = self._set_pdf_file(prescription, generated.file_path)
        prescription.updated_by = actor.id
        self.repo.save(prescription)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="visit_prescription.generate_pdf",
            entity_type="visit_prescription",
            entity_id=str(prescription.id),
            new_values={"version_number": prescription.version_number, "pdf_file_path": reference},
        )
        self.db.commit()
        return VisitPrescriptionPdfResponse(
            visit_id=visit_id,
            prescription_id=prescription.id,
            version_number=prescription.version_number,
            pdf_url=self._pdf_download_url(visit_id),
        )

    def get_pdf_file_for_download(self, visit_id: int, actor: User) -> Path:
        self._ensure_visit(visit_id, actor)
        prescription = self.repo.get_current(visit_id, shop_key=self.shop_key)
        if not prescription:
            raise AppException(
                status_code=422,
                code="finalized_prescription_required",
                message="No current finalized prescription is available",
            )
        return self._resolve_pdf_file(prescription)
