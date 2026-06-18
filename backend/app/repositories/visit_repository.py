from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.visit import Visit


class VisitRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_customer(self, customer_id: int, shop_key: str) -> list[Visit]:
        return (
            self.db.query(Visit)
            .options(joinedload(Visit.customer), joinedload(Visit.assigned_examiner))
            .filter(
                Visit.customer_id == customer_id,
                shop_filter(self.db, Visit, shop_key),
            )
            .order_by(Visit.visit_date.desc(), Visit.created_at.desc())
            .all()
        )

    def get_by_id(self, visit_id: int, shop_key: str) -> Visit | None:
        return (
            self.db.query(Visit)
            .options(joinedload(Visit.customer), joinedload(Visit.assigned_examiner))
            .filter(Visit.id == visit_id, shop_filter(self.db, Visit, shop_key))
            .first()
        )

    def get_by_idempotency_key(self, idempotency_key: str, shop_key: str) -> Visit | None:
        return (
            self.db.query(Visit)
            .options(joinedload(Visit.customer), joinedload(Visit.assigned_examiner))
            .filter(
                Visit.idempotency_key == idempotency_key,
                shop_filter(self.db, Visit, shop_key),
            )
            .first()
        )

    def create(self, visit: Visit) -> Visit:
        assign_shop_scope(visit, self.db, visit.shop_key)
        self.db.add(visit)
        self.db.flush()
        return visit

    def save(self, visit: Visit) -> Visit:
        assign_shop_scope(visit, self.db, visit.shop_key)
        self.db.add(visit)
        self.db.flush()
        return visit
