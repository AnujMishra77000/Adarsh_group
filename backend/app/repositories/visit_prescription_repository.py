from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.enums import PrescriptionVersionStatus
from app.models.visit import Visit
from app.models.visit_prescription import VisitPrescription


class VisitPrescriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _load_options():
        return (
            joinedload(VisitPrescription.customer),
            joinedload(VisitPrescription.visit).joinedload(Visit.customer),
            joinedload(VisitPrescription.visit).joinedload(Visit.assigned_examiner),
            joinedload(VisitPrescription.visit).joinedload(Visit.shop),
        )

    def list_for_visit(self, visit_id: int, shop_key: str) -> list[VisitPrescription]:
        return (
            self.db.query(VisitPrescription)
            .options(*self._load_options())
            .filter(VisitPrescription.visit_id == visit_id, shop_filter(self.db, VisitPrescription, shop_key))
            .order_by(VisitPrescription.version_number.desc())
            .all()
        )

    def get_by_id(self, prescription_id: int, visit_id: int, shop_key: str) -> VisitPrescription | None:
        return (
            self.db.query(VisitPrescription)
            .options(*self._load_options())
            .filter(
                VisitPrescription.id == prescription_id,
                VisitPrescription.visit_id == visit_id,
                shop_filter(self.db, VisitPrescription, shop_key),
            )
            .first()
        )

    def get_draft(self, visit_id: int, shop_key: str) -> VisitPrescription | None:
        return (
            self.db.query(VisitPrescription)
            .options(*self._load_options())
            .filter(
                VisitPrescription.visit_id == visit_id,
                VisitPrescription.status == PrescriptionVersionStatus.DRAFT,
                shop_filter(self.db, VisitPrescription, shop_key),
            )
            .order_by(VisitPrescription.version_number.desc())
            .first()
        )

    def get_current(self, visit_id: int, shop_key: str) -> VisitPrescription | None:
        return (
            self.db.query(VisitPrescription)
            .options(*self._load_options())
            .filter(
                VisitPrescription.visit_id == visit_id,
                VisitPrescription.is_current.is_(True),
                VisitPrescription.status == PrescriptionVersionStatus.FINALIZED,
                shop_filter(self.db, VisitPrescription, shop_key),
            )
            .first()
        )

    def next_version_number(self, visit_id: int, shop_key: str) -> int:
        highest = (
            self.db.query(func.max(VisitPrescription.version_number))
            .filter(VisitPrescription.visit_id == visit_id, shop_filter(self.db, VisitPrescription, shop_key))
            .scalar()
        )
        return int(highest or 0) + 1

    def create(self, prescription: VisitPrescription) -> VisitPrescription:
        assign_shop_scope(prescription, self.db, prescription.shop_key)
        self.db.add(prescription)
        self.db.flush()
        return prescription

    def save(self, prescription: VisitPrescription) -> VisitPrescription:
        assign_shop_scope(prescription, self.db, prescription.shop_key)
        self.db.add(prescription)
        self.db.flush()
        return prescription
