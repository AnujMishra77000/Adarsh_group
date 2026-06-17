from __future__ import annotations

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.db.shop_scope import assign_shop_scope, resolve_shop_id, shop_filter
from app.models.customer import Customer
from app.models.prescription import Prescription


class PrescriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def _shop_clause(self, shop_key: str):
        shop_id = resolve_shop_id(self.db, shop_key)
        customer_scope = shop_filter(self.db, Customer, shop_key)
        if shop_id is None:
            return customer_scope
        return or_(Prescription.shop_id == shop_id, and_(Prescription.shop_id.is_(None), customer_scope))

    def list(
        self,
        page: int,
        page_size: int,
        shop_key: str,
        customer_pk: int | None = None,
        customer_business_id: str | None = None,
        contact_no: str | None = None,
    ) -> tuple[list[Prescription], int]:
        query = (
            self.db.query(Prescription)
            .join(Customer, Customer.id == Prescription.customer_id)
            .options(joinedload(Prescription.customer))
            .filter(Prescription.is_deleted.is_(False), Customer.is_deleted.is_(False), self._shop_clause(shop_key))
        )

        if customer_pk is not None:
            query = query.filter(Prescription.customer_id == customer_pk)

        if customer_business_id:
            query = query.filter(Customer.customer_id.ilike(f"%{customer_business_id.strip()}%"))

        if contact_no:
            query = query.filter(Customer.contact_no.ilike(f"%{contact_no.strip()}%"))

        total = query.count()
        items = (
            query.order_by(Prescription.prescription_date.desc(), Prescription.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def list_for_customer(self, customer_pk: int, shop_key: str) -> list[Prescription]:
        return (
            self.db.query(Prescription)
            .join(Customer, Customer.id == Prescription.customer_id)
            .options(joinedload(Prescription.customer))
            .filter(
                Prescription.customer_id == customer_pk,
                Prescription.is_deleted.is_(False),
                self._shop_clause(shop_key),
                Customer.is_deleted.is_(False),
            )
            .order_by(Prescription.prescription_date.desc(), Prescription.created_at.desc())
            .all()
        )

    def get_by_id(self, prescription_id: int, shop_key: str) -> Prescription | None:
        return (
            self.db.query(Prescription)
            .join(Customer, Customer.id == Prescription.customer_id)
            .options(joinedload(Prescription.customer))
            .filter(
                Prescription.id == prescription_id,
                Prescription.is_deleted.is_(False),
                self._shop_clause(shop_key),
                Customer.is_deleted.is_(False),
            )
            .first()
        )

    def create(self, prescription: Prescription) -> Prescription:
        customer = prescription.customer or self.db.get(Customer, prescription.customer_id)
        if customer is not None:
            assign_shop_scope(prescription, self.db, customer.shop_key, legacy_attr="unused")
        self.db.add(prescription)
        self.db.flush()
        return prescription

    def save(self, prescription: Prescription) -> Prescription:
        if prescription.shop_id is None and prescription.customer_id is not None:
            customer = prescription.customer or self.db.get(Customer, prescription.customer_id)
            if customer is not None:
                assign_shop_scope(prescription, self.db, customer.shop_key, legacy_attr="unused")
        self.db.add(prescription)
        self.db.flush()
        return prescription
