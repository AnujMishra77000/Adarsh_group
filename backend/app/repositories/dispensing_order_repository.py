from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.dispensing_order import DispensingOrder


class DispensingOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _load_options():
        return (
            joinedload(DispensingOrder.prescription),
            joinedload(DispensingOrder.vendor),
            joinedload(DispensingOrder.visit),
            joinedload(DispensingOrder.shop),
        )

    def get_by_visit(self, visit_id: int, shop_key: str) -> DispensingOrder | None:
        return (
            self.db.query(DispensingOrder)
            .options(*self._load_options())
            .filter(
                DispensingOrder.visit_id == visit_id,
                shop_filter(self.db, DispensingOrder, shop_key),
            )
            .first()
        )

    def get_by_id(self, order_id: int, shop_key: str) -> DispensingOrder | None:
        return (
            self.db.query(DispensingOrder)
            .options(*self._load_options())
            .filter(
                DispensingOrder.id == order_id,
                shop_filter(self.db, DispensingOrder, shop_key),
            )
            .first()
        )

    def create(self, order: DispensingOrder) -> DispensingOrder:
        assign_shop_scope(order, self.db, order.shop_key)
        self.db.add(order)
        self.db.flush()
        return order

    def save(self, order: DispensingOrder) -> DispensingOrder:
        assign_shop_scope(order, self.db, order.shop_key)
        self.db.add(order)
        self.db.flush()
        return order
