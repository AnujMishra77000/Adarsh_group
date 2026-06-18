from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.contact_lens_order import ContactLensOrder, FollowUpTask


class ContactLensRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_order_by_visit(self, visit_id: int, shop_key: str) -> ContactLensOrder | None:
        return (
            self.db.query(ContactLensOrder)
            .options(
                joinedload(ContactLensOrder.vendor),
                joinedload(ContactLensOrder.follow_up_task),
                joinedload(ContactLensOrder.bills),
            )
            .filter(
                ContactLensOrder.visit_id == visit_id,
                shop_filter(self.db, ContactLensOrder, shop_key),
            )
            .first()
        )

    def get_order_by_id(self, order_id: int, shop_key: str) -> ContactLensOrder | None:
        return (
            self.db.query(ContactLensOrder)
            .options(joinedload(ContactLensOrder.vendor), joinedload(ContactLensOrder.follow_up_task))
            .filter(
                ContactLensOrder.id == order_id,
                shop_filter(self.db, ContactLensOrder, shop_key),
            )
            .first()
        )

    def create_order(self, order: ContactLensOrder) -> ContactLensOrder:
        assign_shop_scope(order, self.db, order.shop_key)
        self.db.add(order)
        self.db.flush()
        return order

    def save_order(self, order: ContactLensOrder) -> ContactLensOrder:
        assign_shop_scope(order, self.db, order.shop_key)
        self.db.add(order)
        self.db.flush()
        return order

    def get_follow_up_by_visit(self, visit_id: int, shop_key: str) -> FollowUpTask | None:
        return (
            self.db.query(FollowUpTask)
            .filter(
                FollowUpTask.visit_id == visit_id,
                shop_filter(self.db, FollowUpTask, shop_key),
            )
            .first()
        )

    def create_follow_up(self, task: FollowUpTask) -> FollowUpTask:
        assign_shop_scope(task, self.db, task.shop_key)
        self.db.add(task)
        self.db.flush()
        return task

    def save_follow_up(self, task: FollowUpTask) -> FollowUpTask:
        assign_shop_scope(task, self.db, task.shop_key)
        self.db.add(task)
        self.db.flush()
        return task
