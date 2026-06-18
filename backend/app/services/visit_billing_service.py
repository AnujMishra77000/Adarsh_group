from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.bill import Bill
from app.models.user import User
from app.models.visit import Visit
from app.repositories.bill_repository import BillRepository
from app.repositories.contact_lens_repository import ContactLensRepository
from app.repositories.dispensing_order_repository import DispensingOrderRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.bill import BillRead
from app.schemas.visit_billing import VisitBillLinkRequest, VisitBillSummary, VisitBillingContext
from app.services.audit_service import AuditService
from app.services.bill_service import BillService


class VisitBillingService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.bill_repo = BillRepository(db)
        self.contact_lens_repo = ContactLensRepository(db)
        self.visit_repo = VisitRepository(db)
        self.order_repo = DispensingOrderRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)
        self.bill_service = BillService(db, shop_key=shop_key)

    def _ensure_visit(self, visit_id: int, actor: User) -> Visit:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")
        visit = self.visit_repo.get_by_id(visit_id, shop_key=self.shop_key)
        if not visit:
            raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
        return visit

    @staticmethod
    def _summary(bill: Bill) -> VisitBillSummary:
        return VisitBillSummary(
            id=bill.id,
            bill_number=bill.bill_number,
            visit_id=bill.visit_id,
            dispensing_order_id=bill.dispensing_order_id,
            contact_lens_order_id=bill.contact_lens_order_id,
            grand_total=bill.grand_total,
            paid_total=bill.paid_total,
            balance_amount=bill.balance_amount,
            payment_status=bill.payment_status,
            has_invoice=bool(bill.pdf_file_path or bill.pdf_url),
        )

    def get_context(self, visit_id: int, actor: User) -> VisitBillingContext:
        visit = self._ensure_visit(visit_id, actor)
        order = self.order_repo.get_by_visit(visit_id, shop_key=self.shop_key)
        order_bill = self.bill_repo.get_active_by_dispensing_order(order.id, self.shop_key) if order else None
        contact_lens_order = self.contact_lens_repo.get_order_by_visit(visit_id, shop_key=self.shop_key)
        contact_lens_order_bill = (
            self.bill_repo.get_active_by_contact_lens_order(contact_lens_order.id, self.shop_key)
            if contact_lens_order
            else None
        )
        bills = self.bill_repo.list_active_for_visit(visit_id, self.shop_key)
        return VisitBillingContext(
            visit_id=visit.id,
            customer_id=visit.customer_id,
            dispensing_order_id=order.id if order else None,
            contact_lens_order_id=contact_lens_order.id if contact_lens_order else None,
            order_bill=self._summary(order_bill) if order_bill else None,
            contact_lens_order_bill=self._summary(contact_lens_order_bill) if contact_lens_order_bill else None,
            visit_bills=[self._summary(bill) for bill in bills],
        )

    def link_existing_bill(
        self,
        visit_id: int,
        payload: VisitBillLinkRequest,
        actor: User,
    ) -> BillRead:
        visit = self._ensure_visit(visit_id, actor)
        bill = self.bill_repo.get_by_id(payload.bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")
        if bill.customer_id != visit.customer_id:
            raise AppException(
                status_code=422,
                code="bill_context_customer_mismatch",
                message="The bill belongs to a different patient",
            )
        if bill.visit_id is not None and bill.visit_id != visit.id:
            raise AppException(
                status_code=409,
                code="bill_already_linked_to_visit",
                message="The bill is already linked to another visit",
            )

        order = None
        contact_lens_order = None
        if payload.dispensing_order_id is not None and payload.contact_lens_order_id is not None:
            raise AppException(
                status_code=422,
                code="bill_multiple_order_contexts",
                message="A bill can belong to either a spectacle order or a contact lens order",
            )
        requested_order_id = payload.dispensing_order_id or bill.dispensing_order_id
        if requested_order_id is not None:
            order = self.order_repo.get_by_id(requested_order_id, shop_key=self.shop_key)
            if not order:
                raise AppException(
                    status_code=404,
                    code="dispensing_order_not_found",
                    message="Dispensing order not found",
                )
            if order.visit_id != visit.id or order.customer_id != visit.customer_id:
                raise AppException(
                    status_code=422,
                    code="bill_context_visit_mismatch",
                    message="The dispensing order does not belong to this patient visit",
                )
            active_bill = self.bill_repo.get_active_by_dispensing_order(order.id, self.shop_key)
            if active_bill and active_bill.id != bill.id:
                raise AppException(
                    status_code=409,
                    code="dispensing_order_already_billed",
                    message="This dispensing order already has an active bill",
                )
            if bill.dispensing_order_id is not None and bill.dispensing_order_id != order.id:
                raise AppException(
                    status_code=409,
                    code="bill_already_linked_to_order",
                    message="The bill is already linked to another dispensing order",
                )

        requested_contact_lens_order_id = payload.contact_lens_order_id or bill.contact_lens_order_id
        if requested_contact_lens_order_id is not None:
            contact_lens_order = self.contact_lens_repo.get_order_by_id(
                requested_contact_lens_order_id,
                shop_key=self.shop_key,
            )
            if not contact_lens_order:
                raise AppException(
                    status_code=404,
                    code="contact_lens_order_not_found",
                    message="Contact lens order not found",
                )
            if contact_lens_order.visit_id != visit.id or contact_lens_order.customer_id != visit.customer_id:
                raise AppException(
                    status_code=422,
                    code="bill_context_visit_mismatch",
                    message="The contact lens order does not belong to this patient visit",
                )
            active_bill = self.bill_repo.get_active_by_contact_lens_order(contact_lens_order.id, self.shop_key)
            if active_bill and active_bill.id != bill.id:
                raise AppException(
                    status_code=409,
                    code="contact_lens_order_already_billed",
                    message="This contact lens order already has an active bill",
                )
            if bill.contact_lens_order_id is not None and bill.contact_lens_order_id != contact_lens_order.id:
                raise AppException(
                    status_code=409,
                    code="bill_already_linked_to_order",
                    message="The bill is already linked to another contact lens order",
                )

        old_values = {
            "visit_id": bill.visit_id,
            "dispensing_order_id": bill.dispensing_order_id,
            "contact_lens_order_id": bill.contact_lens_order_id,
        }
        bill.visit_id = visit.id
        bill.dispensing_order_id = order.id if order else None
        bill.contact_lens_order_id = contact_lens_order.id if contact_lens_order else None
        bill.updated_by = actor.id
        try:
            self.bill_repo.save(bill)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="bill.link_workflow_context",
                entity_type="bill",
                entity_id=str(bill.id),
                old_values=old_values,
                new_values={
                    "visit_id": bill.visit_id,
                    "dispensing_order_id": bill.dispensing_order_id,
                    "contact_lens_order_id": bill.contact_lens_order_id,
                },
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code=(
                    "contact_lens_order_already_billed"
                    if contact_lens_order is not None
                    else "dispensing_order_already_billed"
                ),
                message=(
                    "This contact lens order already has an active bill"
                    if contact_lens_order is not None
                    else "This dispensing order already has an active bill"
                ),
            ) from exc
        return self.bill_service.get_bill(bill.id)
