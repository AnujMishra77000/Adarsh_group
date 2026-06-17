from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.db.shop_scope import assign_shop_scope, resolve_shop_id, shop_filter
from app.models.bill import Bill
from app.models.customer import Customer


class BillRepository:
    def __init__(self, db: Session):
        self.db = db

    def _shop_clause(self, shop_key: str):
        shop_id = resolve_shop_id(self.db, shop_key)
        customer_scope = shop_filter(self.db, Customer, shop_key)
        if shop_id is None:
            return customer_scope
        return or_(Bill.shop_id == shop_id, and_(Bill.shop_id.is_(None), customer_scope))

    def list(
        self,
        page: int,
        page_size: int,
        shop_key: str,
        search: str | None = None,
        customer_pk: int | None = None,
    ) -> tuple[list[Bill], int]:
        query = (
            self.db.query(Bill)
            .join(Customer, Customer.id == Bill.customer_id)
            .options(joinedload(Bill.customer), joinedload(Bill.items), joinedload(Bill.payments))
            .filter(Bill.is_deleted.is_(False), Customer.is_deleted.is_(False), self._shop_clause(shop_key))
        )

        if customer_pk is not None:
            query = query.filter(Bill.customer_id == customer_pk)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Bill.bill_number.ilike(pattern),
                    Bill.customer_name_snapshot.ilike(pattern),
                    Bill.product_name.ilike(pattern),
                    Bill.frame_name.ilike(pattern),
                    Customer.customer_id.ilike(pattern),
                    Customer.name.ilike(pattern),
                    Customer.contact_no.ilike(pattern),
                    Customer.whatsapp_no.ilike(pattern),
                )
            )

        total = query.count()
        items = (
            query.order_by(Bill.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, bill_id: int, shop_key: str, include_deleted: bool = False) -> Bill | None:
        query = (
            self.db.query(Bill)
            .join(Customer, Customer.id == Bill.customer_id)
            .options(joinedload(Bill.customer), joinedload(Bill.items), joinedload(Bill.payments))
        )
        if not include_deleted:
            query = query.filter(Bill.is_deleted.is_(False))
        return query.filter(Bill.id == bill_id, self._shop_clause(shop_key), Customer.is_deleted.is_(False)).first()

    def get_by_bill_number(self, bill_number: str, shop_key: str | None = None) -> Bill | None:
        query = self.db.query(Bill)
        if shop_key is not None:
            query = query.join(Customer, Customer.id == Bill.customer_id).filter(self._shop_clause(shop_key))
        return query.filter(Bill.bill_number == bill_number).first()

    def count_created_for_day(self, target_date: date, shop_key: str) -> int:
        start = datetime.combine(target_date, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        return (
            self.db.query(Bill.id)
            .join(Customer, Customer.id == Bill.customer_id)
            .filter(Bill.created_at >= start, Bill.created_at < end, self._shop_clause(shop_key))
            .count()
        )

    def create(self, bill: Bill) -> Bill:
        customer = bill.customer or self.db.get(Customer, bill.customer_id)
        if customer is not None:
            assign_shop_scope(bill, self.db, customer.shop_key, legacy_attr="unused")
        self.db.add(bill)
        self.db.flush()
        return bill

    def save(self, bill: Bill) -> Bill:
        if bill.shop_id is None and bill.customer_id is not None:
            customer = bill.customer or self.db.get(Customer, bill.customer_id)
            if customer is not None:
                assign_shop_scope(bill, self.db, customer.shop_key, legacy_attr="unused")
        self.db.add(bill)
        self.db.flush()
        return bill
