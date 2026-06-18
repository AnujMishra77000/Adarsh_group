from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.enums import UserRole
from app.models.user import User
from app.models.visit import Visit
from app.repositories.customer_repository import CustomerRepository
from app.repositories.user_repository import UserRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.visit import VisitCreate, VisitListResponse, VisitRead
from app.services.audit_service import AuditService


class VisitService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = VisitRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)

    def _serialize(self, visit: Visit) -> VisitRead:
        customer = visit.customer
        examiner = visit.assigned_examiner
        return VisitRead(
            id=visit.id,
            shop_key=visit.shop_key,
            customer_id=visit.customer_id,
            customer_name=customer.name if customer else None,
            customer_business_id=customer.customer_id if customer else None,
            customer_contact_no=customer.contact_no if customer else None,
            visit_date=visit.visit_date,
            reason_for_visit=visit.reason_for_visit,
            referred_by=visit.referred_by,
            assigned_examiner_id=visit.assigned_examiner_id,
            assigned_examiner_name=(examiner.full_name or examiner.email) if examiner else None,
            visit_notes=visit.visit_notes,
            contact_lens_workup_requested=visit.contact_lens_workup_requested,
            status=visit.status,
            created_at=visit.created_at,
            updated_at=visit.updated_at,
            created_by=visit.created_by,
            updated_by=visit.updated_by,
        )

    def _resolve_examiner_id(self, requested_examiner_id: int | None, actor: User) -> int:
        examiner_id = requested_examiner_id or actor.id
        if actor.role != UserRole.ADMIN and examiner_id != actor.id:
            raise AppException(
                status_code=403,
                code="examiner_assignment_forbidden",
                message="Staff can only assign visits to themselves",
            )

        examiner = self.user_repo.get_by_id(examiner_id)
        if not examiner or not examiner.is_active or examiner.shop_key != self.shop_key:
            raise AppException(status_code=404, code="examiner_not_found", message="Assigned examiner not found")

        return examiner.id

    @staticmethod
    def _normalize_key(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def start_visit(self, payload: VisitCreate, actor: User) -> VisitRead:
        idempotency_key = self._normalize_key(payload.idempotency_key)
        if idempotency_key:
            existing_visit = self.repo.get_by_idempotency_key(idempotency_key, shop_key=self.shop_key)
            if existing_visit:
                if existing_visit.customer_id != payload.customer_id:
                    raise AppException(
                        status_code=409,
                        code="visit_idempotency_customer_mismatch",
                        message="This visit request was already used for another patient",
                    )
                return self._serialize(existing_visit)

        customer = self.customer_repo.get_by_id(payload.customer_id, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        examiner_id = self._resolve_examiner_id(payload.assigned_examiner_id, actor)
        visit = Visit(
            shop_key=self.shop_key,
            customer_id=customer.id,
            visit_date=payload.visit_date or datetime.now(UTC),
            reason_for_visit=payload.reason_for_visit.strip(),
            referred_by=payload.referred_by.strip() if payload.referred_by else None,
            assigned_examiner_id=examiner_id,
            visit_notes=payload.visit_notes.strip() if payload.visit_notes else None,
            contact_lens_workup_requested=payload.contact_lens_workup_requested,
            status=payload.status,
            idempotency_key=idempotency_key,
            created_by=actor.id,
            updated_by=actor.id,
        )

        try:
            self.repo.create(visit)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="visit.create",
                entity_type="visit",
                entity_id=str(visit.id),
                new_values={
                    "customer_id": visit.customer_id,
                    "visit_date": visit.visit_date.isoformat(),
                    "reason_for_visit": visit.reason_for_visit,
                    "status": visit.status.value,
                    "assigned_examiner_id": visit.assigned_examiner_id,
                    "contact_lens_workup_requested": visit.contact_lens_workup_requested,
                },
            )
            self.db.commit()
            self.db.refresh(visit)
        except IntegrityError as exc:
            self.db.rollback()
            if idempotency_key:
                existing_visit = self.repo.get_by_idempotency_key(idempotency_key, shop_key=self.shop_key)
                if existing_visit:
                    return self._serialize(existing_visit)
            raise AppException(status_code=409, code="visit_create_conflict", message="Unable to start visit") from exc

        persisted = self.repo.get_by_id(visit.id, shop_key=self.shop_key)
        assert persisted is not None
        return self._serialize(persisted)

    def get_visit(self, visit_id: int, actor: User) -> VisitRead:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")

        visit = self.repo.get_by_id(visit_id, shop_key=self.shop_key)
        if not visit:
            raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
        return self._serialize(visit)

    def list_customer_visits(self, customer_id: int) -> VisitListResponse:
        customer = self.customer_repo.get_by_id(customer_id, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        visits = self.repo.list_for_customer(customer_id, shop_key=self.shop_key)
        return VisitListResponse(items=[self._serialize(visit) for visit in visits], total=len(visits))
