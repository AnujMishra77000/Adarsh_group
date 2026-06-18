from __future__ import annotations

import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exam_sections import ExamSectionDefinition, EXAM_SECTION_DEFINITIONS, get_exam_section_definition
from app.core.exceptions import AppException
from app.models.enums import ExamSectionState, VisitStatus
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_exam_section import VisitExamSection
from app.repositories.visit_exam_section_repository import VisitExamSectionRepository
from app.repositories.visit_prescription_repository import VisitPrescriptionRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.visit_exam_section import (
    VisitExamSectionHistoryItem,
    VisitExamSectionHistoryResponse,
    VisitExamSectionListResponse,
    VisitExamSectionRead,
    VisitExamSectionUpdate,
)
from app.services.audit_service import AuditService


class VisitExamSectionService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = VisitExamSectionRepository(db)
        self.visit_repo = VisitRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)

    CORE_HISTORY_SECTION_KEYS = {
        "visual_acuity",
        "objective_refraction",
        "subjective_refraction",
        "potential_vision",
    }
    REFRACTION_SECTION_KEYS = {
        "objective_refraction",
        "subjective_refraction",
        "final_prescription",
        "cycloplegic_refraction",
    }
    OBJECTIVE_METHODS = {
        "autorefractometer",
        "retinoscopy",
        "mohindra_retinoscopy",
        "dynamic_retinoscopy",
    }
    OPTICAL_POWER_RE = re.compile(r"^[+-]?\d{1,2}(?:\.\d{1,2})?$")

    def _ensure_visit_in_shop(self, visit_id: int, actor: User) -> Visit:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")

        visit = self.visit_repo.get_by_id(visit_id, shop_key=self.shop_key)
        if not visit:
            raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
        return visit

    @staticmethod
    def _serialize(
        definition: ExamSectionDefinition,
        record: VisitExamSection | None = None,
        *,
        is_visible: bool | None = None,
    ) -> VisitExamSectionRead:
        return VisitExamSectionRead(
            key=definition.key,
            title=definition.title,
            description=definition.description,
            state=record.state if record else definition.state,
            is_required=definition.is_required,
            is_optional=definition.is_optional,
            is_disabled=definition.is_disabled,
            is_visible=definition.is_visible if is_visible is None else is_visible,
            payload=record.payload if record else {},
            saved_at=record.updated_at if record else None,
            saved_by=record.updated_by if record else None,
        )

    def list_sections(self, visit_id: int, actor: User) -> VisitExamSectionListResponse:
        visit = self._ensure_visit_in_shop(visit_id, actor)
        records = {record.section_key: record for record in self.repo.list_for_visit(visit_id, shop_key=self.shop_key)}
        sections = [
            self._serialize(
                definition,
                records.get(definition.key),
                is_visible=(
                    self._contact_lens_visible(visit, records.get(definition.key))
                    if definition.key == "contact_lens"
                    else None
                ),
            )
            for definition in EXAM_SECTION_DEFINITIONS
        ]
        return VisitExamSectionListResponse(visit_id=visit_id, sections=sections, total=len(sections))

    @staticmethod
    def _contact_lens_visible(visit: Visit, record: VisitExamSection | None) -> bool:
        normalized_reason = visit.reason_for_visit.lower().replace("-", " ")
        return "contact lens" in normalized_reason or visit.contact_lens_workup_requested or record is not None

    @classmethod
    def _is_blank(cls, value: object) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    @classmethod
    def _validate_optical_power(cls, value: object, label: str, errors: list[str]) -> None:
        if cls._is_blank(value):
            return
        normalized = str(value).strip()
        if normalized.lower() == "plano":
            return
        if not cls.OPTICAL_POWER_RE.match(normalized):
            errors.append(f"{label} must be Plano or a signed optical power")

    @classmethod
    def _cylinder_requires_axis(cls, value: object) -> bool:
        if cls._is_blank(value):
            return False
        normalized = str(value).strip()
        if normalized.lower() == "plano":
            return False
        try:
            return float(normalized) != 0
        except ValueError:
            return True

    @classmethod
    def _validate_axis(cls, value: object, label: str, errors: list[str]) -> None:
        if cls._is_blank(value):
            errors.append(f"{label} is required when cylinder is entered")
            return
        try:
            axis = int(str(value).strip())
        except ValueError:
            errors.append(f"{label} must be a whole number between 0 and 180")
            return
        if axis < 0 or axis > 180:
            errors.append(f"{label} must be between 0 and 180")

    @classmethod
    def _validate_refraction_payload(cls, section_key: str, payload: dict) -> list[str]:
        errors: list[str] = []
        eye_values = payload.get("eye_values")
        if not isinstance(eye_values, dict):
            return errors

        method = str(payload.get("method") or "").strip()
        if section_key == "objective_refraction" and method and method not in cls.OBJECTIVE_METHODS:
            errors.append("Objective refraction method is not supported")

        for eye_key, eye_label in (("right", "Right eye"), ("left", "Left eye")):
            eye_payload = eye_values.get(eye_key)
            if not isinstance(eye_payload, dict):
                continue

            cls._validate_optical_power(eye_payload.get("sph"), f"{eye_label} SPH", errors)
            cls._validate_optical_power(eye_payload.get("cyl"), f"{eye_label} CYL", errors)
            if cls._cylinder_requires_axis(eye_payload.get("cyl")):
                cls._validate_axis(eye_payload.get("axis"), f"{eye_label} axis", errors)

        return errors

    @staticmethod
    def _has_abnormal_details(value: object, keys: tuple[str, ...]) -> bool:
        if not isinstance(value, dict):
            return False
        for key in keys:
            detail = value.get(key)
            if isinstance(detail, list) and len([item for item in detail if str(item).strip()]) > 0:
                return True
            if isinstance(detail, str) and detail.strip():
                return True
            if detail not in (None, "", [], False):
                return True
        return False

    @staticmethod
    def _humanize_key(value: str) -> str:
        return value.replace("_", " ").capitalize()

    @classmethod
    def _validate_torch_light_payload(cls, payload: dict) -> list[str]:
        errors: list[str] = []
        findings = payload.get("findings")
        if not isinstance(findings, dict):
            return errors

        for structure_key, structure_payload in findings.items():
            if not isinstance(structure_payload, dict):
                continue
            if structure_payload.get("normal") is True and cls._has_abnormal_details(
                structure_payload,
                ("abnormal_findings", "finding", "other_finding", "custom_notes", "notes"),
            ):
                errors.append(f"{cls._humanize_key(str(structure_key))} cannot be marked normal with abnormal findings")
        return errors

    @classmethod
    def _validate_slit_lamp_payload(cls, payload: dict) -> list[str]:
        errors: list[str] = []
        eyes = payload.get("eyes")
        if not isinstance(eyes, dict):
            return errors

        for eye_key, eye_payload in eyes.items():
            if not isinstance(eye_payload, dict):
                continue
            eye_label = f"{cls._humanize_key(str(eye_key))} eye"
            for structure_key, structure_payload in eye_payload.items():
                if not isinstance(structure_payload, dict):
                    continue
                if structure_payload.get("normal") is True and cls._has_abnormal_details(
                    structure_payload,
                    ("findings", "finding", "other_finding", "custom_notes", "notes", "cataract_grade", "grade"),
                ):
                    errors.append(
                        f"{eye_label} {str(structure_key).replace('_', ' ')} cannot be marked normal with abnormal findings"
                    )
        return errors

    @classmethod
    def _validate_cycloplegic_payload(cls, payload: dict) -> list[str]:
        if payload.get("not_done") is True or payload.get("performed") is not True:
            return []

        errors: list[str] = []
        if cls._is_blank(payload.get("drug_used")):
            errors.append("Cycloplegic drug used is required when performed")
        if cls._is_blank(payload.get("time_instilled")):
            errors.append("Cycloplegic instillation time is required when performed")
        errors.extend(cls._validate_refraction_payload("cycloplegic_refraction", payload))
        return errors

    @classmethod
    def _validate_contact_lens_payload(cls, payload: dict) -> list[str]:
        errors: list[str] = []
        indication = payload.get("indication")
        indication_type = indication.get("type") if isinstance(indication, dict) else None
        allowed_indications = {"cosmetic", "refractive", "keratoconus", "sports", "therapeutic", "other"}
        if cls._is_blank(indication_type):
            errors.append("Contact lens indication is required")
        elif indication_type not in allowed_indications:
            errors.append("Contact lens indication is not supported")
        elif indication_type == "other" and cls._is_blank(indication.get("other")):
            errors.append("A custom indication is required when Other is selected")

        prescription = payload.get("prescription")
        for eye_key, eye_label in (("right", "Right eye"), ("left", "Left eye")):
            eye = prescription.get(eye_key) if isinstance(prescription, dict) else None
            if not isinstance(eye, dict):
                errors.append(f"{eye_label} contact lens prescription is required")
                continue
            for field, label in (
                ("power", "power"),
                ("base_curve_mm", "base curve"),
                ("diameter_mm", "diameter"),
            ):
                if cls._is_blank(eye.get(field)):
                    errors.append(f"{eye_label} {label} is required")
            cls._validate_optical_power(eye.get("power"), f"{eye_label} power", errors)

        return errors

    def _validate_completed_section(self, section_key: str, payload: VisitExamSectionUpdate) -> None:
        if payload.state != ExamSectionState.COMPLETE:
            return

        errors: list[str] = []
        if section_key == "cycloplegic_refraction":
            errors = self._validate_cycloplegic_payload(payload.payload)
        elif section_key in self.REFRACTION_SECTION_KEYS:
            errors = self._validate_refraction_payload(section_key, payload.payload)
        elif section_key == "torch_light_evaluation":
            errors = self._validate_torch_light_payload(payload.payload)
        elif section_key == "slit_lamp_evaluation":
            errors = self._validate_slit_lamp_payload(payload.payload)
        elif section_key == "contact_lens":
            errors = self._validate_contact_lens_payload(payload.payload)

        if errors:
            raise AppException(
                status_code=422,
                code="exam_section_validation_failed",
                message="; ".join(errors),
            )

    def list_previous_core_sections(self, visit_id: int, actor: User) -> VisitExamSectionHistoryResponse:
        visit = self._ensure_visit_in_shop(visit_id, actor)
        records = self.repo.list_previous_for_customer(
            customer_id=visit.customer_id,
            current_visit_id=visit_id,
            section_keys=self.CORE_HISTORY_SECTION_KEYS,
            shop_key=self.shop_key,
        )
        items = []
        for record in records:
            definition = get_exam_section_definition(record.section_key)
            if definition is None or record.visit is None:
                continue
            items.append(
                VisitExamSectionHistoryItem(
                    visit_id=record.visit_id,
                    visit_date=record.visit.visit_date,
                    section_key=record.section_key,
                    title=definition.title,
                    state=record.state,
                    payload=record.payload,
                    saved_at=record.updated_at,
                    saved_by=record.updated_by,
                )
            )
        return VisitExamSectionHistoryResponse(visit_id=visit_id, items=items, total=len(items))

    def save_section(
        self,
        visit_id: int,
        section_key: str,
        payload: VisitExamSectionUpdate,
        actor: User,
    ) -> VisitExamSectionRead:
        definition = get_exam_section_definition(section_key)
        if definition is None:
            raise AppException(status_code=404, code="exam_section_not_found", message="Examination section not found")
        if definition.is_disabled:
            raise AppException(
                status_code=400,
                code="exam_section_disabled",
                message="This examination section is not available yet",
            )

        normalized_key = definition.key
        visit = self._ensure_visit_in_shop(visit_id, actor)
        if visit.status in {VisitStatus.COMPLETED, VisitStatus.CANCELLED}:
            raise AppException(status_code=409, code="visit_read_only", message="Completed or cancelled visits are read-only")
        if normalized_key == "final_prescription" and VisitPrescriptionRepository(self.db).get_current(
            visit_id,
            shop_key=self.shop_key,
        ):
            raise AppException(
                status_code=409,
                code="prescription_amendment_required",
                message="Start an amendment to correct a finalized prescription",
            )
        self._validate_completed_section(normalized_key, payload)
        existing = self.repo.get_for_visit(visit_id, normalized_key, shop_key=self.shop_key)
        old_values = None

        if existing:
            old_values = {"state": existing.state.value, "payload": existing.payload}
            existing.state = payload.state
            existing.payload = payload.payload
            existing.updated_by = actor.id
            record = existing
        else:
            record = VisitExamSection(
                shop_key=self.shop_key,
                visit_id=visit_id,
                section_key=normalized_key,
                state=payload.state,
                payload=payload.payload,
                created_by=actor.id,
                updated_by=actor.id,
            )

        try:
            if existing:
                self.repo.save(record)
            else:
                self.repo.create(record)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="visit_exam_section.save",
                entity_type="visit_exam_section",
                entity_id=f"{visit_id}:{normalized_key}",
                old_values=old_values,
                new_values={"state": record.state.value, "payload": record.payload},
            )
            self.db.commit()
            self.db.refresh(record)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="exam_section_save_conflict",
                message="Unable to save examination section",
            ) from exc

        return self._serialize(definition, record)
