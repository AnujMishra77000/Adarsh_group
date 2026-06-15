from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, page: int, page_size: int, shop_key: str, search: str | None = None) -> tuple[list[Customer], int]:
        query = self.db.query(Customer).filter(Customer.is_deleted.is_(False), Customer.shop_key == shop_key)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.customer_id.ilike(pattern),
                    Customer.name.ilike(pattern),
                    Customer.contact_no.ilike(pattern),
                    Customer.email.ilike(pattern),
                    Customer.whatsapp_no.ilike(pattern),
                )
            )

        total = query.count()
        items = (
            query.order_by(Customer.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, customer_pk: int, shop_key: str, include_deleted: bool = False) -> Customer | None:
        query = self.db.query(Customer)
        if not include_deleted:
            query = query.filter(Customer.is_deleted.is_(False))
        return query.filter(Customer.id == customer_pk, Customer.shop_key == shop_key).first()

    def get_detail(self, customer_pk: int, shop_key: str) -> Customer | None:
        return (
            self.db.query(Customer)
            .options(
                joinedload(Customer.prescriptions),
                joinedload(Customer.bills),
            )
            .filter(Customer.id == customer_pk, Customer.is_deleted.is_(False), Customer.shop_key == shop_key)
            .first()
        )

    def get_by_business_id(self, customer_business_id: str, shop_key: str) -> Customer | None:
        return self.db.query(Customer).filter(
            Customer.customer_id == customer_business_id,
            Customer.is_deleted.is_(False),
            Customer.shop_key == shop_key,
        ).first()

    def exists_business_id(self, customer_business_id: str, shop_key: str | None = None) -> bool:
        query = self.db.query(Customer.id).filter(Customer.customer_id == customer_business_id)
        if shop_key is not None:
            query = query.filter(Customer.shop_key == shop_key)
        return query.first() is not None

    def list_whatsapp_eligible(self, shop_key: str) -> list[Customer]:
        return (
            self.db.query(Customer)
            .filter(
                Customer.is_deleted.is_(False),
                Customer.shop_key == shop_key,
                Customer.whatsapp_opt_in.is_(True),
                Customer.whatsapp_no.is_not(None),
                func.length(func.trim(Customer.whatsapp_no)) > 0,
            )
            .order_by(Customer.id.asc())
            .all()
        )

    def count_whatsapp_eligible(self, shop_key: str) -> int:
        return (
            self.db.query(Customer.id)
            .filter(
                Customer.is_deleted.is_(False),
                Customer.shop_key == shop_key,
                Customer.whatsapp_opt_in.is_(True),
                Customer.whatsapp_no.is_not(None),
                func.length(func.trim(Customer.whatsapp_no)) > 0,
            )
            .count()
        )

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

    def save(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer
