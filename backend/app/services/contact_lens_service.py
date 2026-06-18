from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.db.shop_scope import assign_shop_scope
from app.models.contact_lens_order import ContactLensOrder, FollowUpTask
from app.models.dispensing_order import DispensingOrder, OrderStatusEvent
from app.models.enums import (
    DispensingOrderStatus,
    FollowUpInterval,
    FollowUpReminderState,
    FollowUpStatus,
    FollowUpType,
    VisitStatus,
)
from app.models.user import User
from app.models.visit import Visit
from app.repositories.contact_lens_repository import ContactLensRepository
from app.repositories.vendor_repository import VendorRepository
from app.repositories.visit_exam_section_repository import VisitExamSectionRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.contact_lens import (
    ContactLensContext,
    ContactLensFollowUpRead,
    ContactLensFollowUpSchedule,
    ContactLensOrderRead,
    ContactLensOrderStatusUpdate,
    ContactLensOrderUpdate,
    ContactLensWorkupRead,
    ContactLensWorkupUpdate,
    FollowUpCreate,
    FollowUpListResponse,
    FollowUpStatusUpdate,
)
from app.schemas.visit_exam_section import VisitExamSectionUpdate
from app.services.audit_service import AuditService
from app.services.visit_exam_section_service import VisitExamSectionService


class ContactLensService:
    STATUS_EVENTS = {
        DispensingOrderStatus.READY_FOR_VENDOR: "ready_for_vendor",
        DispensingOrderStatus.SENT_TO_VENDOR: "vendor_order_sent",
        DispensingOrderStatus.IN_PRODUCTION: "order_in_production",
        DispensingOrderStatus.READY_FOR_DELIVERY: "ready_for_delivery",
        DispensingOrderStatus.DELIVERED: "delivered",
        DispensingOrderStatus.CANCELLED: "cancelled",
        DispensingOrderStatus.DRAFT: "returned_to_draft",
    }
    STATUS_TRANSITIONS = {
        DispensingOrderStatus.DRAFT: {DispensingOrderStatus.READY_FOR_VENDOR, DispensingOrderStatus.CANCELLED},
        DispensingOrderStatus.READY_FOR_VENDOR: {
            DispensingOrderStatus.DRAFT,
            DispensingOrderStatus.SENT_TO_VENDOR,
            DispensingOrderStatus.CANCELLED,
        },
        DispensingOrderStatus.SENT_TO_VENDOR: {
            DispensingOrderStatus.IN_PRODUCTION,
            DispensingOrderStatus.CANCELLED,
        },
        DispensingOrderStatus.IN_PRODUCTION: {
            DispensingOrderStatus.READY_FOR_DELIVERY,
            DispensingOrderStatus.CANCELLED,
        },
        DispensingOrderStatus.READY_FOR_DELIVERY: {
            DispensingOrderStatus.DELIVERED,
            DispensingOrderStatus.CANCELLED,
        },
        DispensingOrderStatus.DELIVERED: set(),
        DispensingOrderStatus.CANCELLED: set(),
    }
    EDITABLE_STATUSES = {DispensingOrderStatus.DRAFT, DispensingOrderStatus.READY_FOR_VENDOR}

    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = ContactLensRepository(db)
        self.visit_repo = VisitRepository(db)
        self.section_repo = VisitExamSectionRepository(db)
        self.vendor_repo = VendorRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)

    def _ensure_visit(self, visit_id: int, actor: User, *, editable: bool = False) -> Visit:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")
        visit = self.visit_repo.get_by_id(visit_id, shop_key=self.shop_key)
        if not visit:
            raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
        if editable and visit.status in {VisitStatus.COMPLETED, VisitStatus.CANCELLED}:
            raise AppException(status_code=409, code="visit_read_only", message="Completed or cancelled visits are read-only")
        return visit

    @staticmethod
    def _order_reference() -> str:
        return f"CL-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"

    @staticmethod
    def _serialize_order(order: ContactLensOrder) -> ContactLensOrderRead:
        is_delayed = bool(
            order.expected_delivery_date
            and order.expected_delivery_date < date.today()
            and order.status not in {DispensingOrderStatus.DELIVERED, DispensingOrderStatus.CANCELLED}
        )
        return ContactLensOrderRead(
            id=order.id,
            visit_id=order.visit_id,
            customer_id=order.customer_id,
            vendor_id=order.vendor_id,
            vendor_name=order.vendor.vendor_name if order.vendor else None,
            order_reference=order.order_reference,
            status=order.status,
            workup_snapshot=order.workup_snapshot or {},
            lens_details=order.lens_data or {},
            order_notes=order.order_notes,
            expected_delivery_date=order.expected_delivery_date,
            delivered_by=order.delivered_by,
            delivered_at=order.delivered_at,
            is_delayed=is_delayed,
            events=list(order.status_events),
            created_by=order.created_by,
            updated_by=order.updated_by,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def _record_order_event(
        self,
        order: ContactLensOrder,
        *,
        event: str,
        status: DispensingOrderStatus,
        actor: User,
        previous_status: DispensingOrderStatus | None = None,
        notes: str | None = None,
    ) -> None:
        item = OrderStatusEvent(
            shop_key=self.shop_key,
            contact_lens_order_id=order.id,
            event=event,
            previous_status=previous_status.value if previous_status else None,
            status=status.value,
            user_id=actor.id,
            notes=notes,
        )
        assign_shop_scope(item, self.db, self.shop_key)
        self.db.add(item)
        self.db.flush()

    @staticmethod
    def _serialize_follow_up(task: FollowUpTask) -> ContactLensFollowUpRead:
        return ContactLensFollowUpRead.model_validate(task)

    def _get_order(self, visit_id: int) -> ContactLensOrder:
        order = self.repo.get_order_by_visit(visit_id, self.shop_key)
        if not order:
            raise AppException(status_code=404, code="contact_lens_order_not_found", message="Contact lens order not found")
        return order

    def _validate_vendor(self, vendor_id: int | None) -> int | None:
        if vendor_id is None:
            return None
        vendor = self.vendor_repo.get_by_id(vendor_id, shop_key=self.shop_key)
        if not vendor:
            raise AppException(status_code=404, code="vendor_not_found", message="Vendor not found")
        if not vendor.is_active:
            raise AppException(status_code=422, code="vendor_inactive", message="Vendor is not active")
        return vendor.id

    @staticmethod
    def _validate_order_values(workup: dict, lens_data: dict) -> None:
        errors: list[str] = []
        prescription = workup.get("prescription") if isinstance(workup, dict) else None
        for eye_key, eye_label in (("right", "Right eye"), ("left", "Left eye")):
            eye = prescription.get(eye_key) if isinstance(prescription, dict) else None
            for key, label in (("power", "power"), ("base_curve_mm", "base curve"), ("diameter_mm", "diameter")):
                if not isinstance(eye, dict) or not str(eye.get(key) or "").strip():
                    errors.append(f"{eye_label} {label} is required")
        for key, label in (
            ("brand", "Brand"),
            ("material", "Material"),
            ("replacement_schedule", "Replacement schedule"),
            ("wearing_schedule", "Wearing schedule"),
        ):
            if not str(lens_data.get(key) or "").strip():
                errors.append(f"{label} is required")
        if errors:
            raise AppException(status_code=422, code="contact_lens_order_validation_failed", message="; ".join(errors))

    def get_context(self, visit_id: int, actor: User) -> ContactLensContext:
        visit = self._ensure_visit(visit_id, actor)
        section = self.section_repo.get_for_visit(visit_id, "contact_lens", shop_key=self.shop_key)
        order = self.repo.get_order_by_visit(visit_id, self.shop_key)
        follow_up = self.repo.get_follow_up_by_visit(visit_id, self.shop_key, FollowUpType.CONTACT_LENS.value)
        workup = None
        if section:
            workup = ContactLensWorkupRead(
                state=section.state,
                **(section.payload or {}),
                saved_at=section.updated_at,
                saved_by=section.updated_by,
            )
        active_bill_id = None
        if order:
            active_bill = next((bill for bill in order.bills if not bill.is_deleted), None)
            active_bill_id = active_bill.id if active_bill else None
        return ContactLensContext(
            visit_id=visit.id,
            is_activated=bool(visit.contact_lens_workup_requested or section or order),
            workup=workup,
            order=self._serialize_order(order) if order else None,
            follow_up=self._serialize_follow_up(follow_up) if follow_up else None,
            active_bill_id=active_bill_id,
        )

    def activate(self, visit_id: int, actor: User) -> ContactLensContext:
        visit = self._ensure_visit(visit_id, actor, editable=True)
        if not visit.contact_lens_workup_requested:
            visit.contact_lens_workup_requested = True
            visit.updated_by = actor.id
            self.visit_repo.save(visit)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="contact_lens.activate",
                entity_type="visit",
                entity_id=str(visit.id),
                new_values={"contact_lens_workup_requested": True},
            )
            self.db.commit()
        return self.get_context(visit_id, actor)

    def save_workup(self, visit_id: int, payload: ContactLensWorkupUpdate, actor: User) -> ContactLensWorkupRead:
        visit = self._ensure_visit(visit_id, actor, editable=True)
        section = VisitExamSectionService(self.db, self.shop_key).save_section(
            visit_id,
            "contact_lens",
            VisitExamSectionUpdate(
                state=payload.state,
                payload=payload.model_dump(mode="json", exclude={"state"}),
            ),
            actor,
        )
        if not visit.contact_lens_workup_requested:
            visit.contact_lens_workup_requested = True
            visit.updated_by = actor.id
            self.visit_repo.save(visit)
            self.db.commit()
        return ContactLensWorkupRead(
            state=section.state,
            **section.payload,
            saved_at=section.saved_at,
            saved_by=section.saved_by,
        )

    def save_order(self, visit_id: int, payload: ContactLensOrderUpdate, actor: User) -> ContactLensOrderRead:
        visit = self._ensure_visit(visit_id, actor, editable=True)
        vendor_id = self._validate_vendor(payload.vendor_id)
        section = self.section_repo.get_for_visit(visit_id, "contact_lens", shop_key=self.shop_key)
        if not section:
            raise AppException(status_code=422, code="contact_lens_workup_required", message="Save the contact lens work-up first")
        lens_data = payload.lens_details.model_dump(mode="json", exclude_none=True)
        self._validate_order_values(section.payload or {}, lens_data)
        order = self.repo.get_order_by_visit(visit_id, self.shop_key)
        if order is None:
            order = ContactLensOrder(
                shop_key=self.shop_key,
                visit_id=visit.id,
                customer_id=visit.customer_id,
                vendor_id=vendor_id,
                order_reference=self._order_reference(),
                status=DispensingOrderStatus.DRAFT,
                workup_snapshot=deepcopy(section.payload or {}),
                lens_data=lens_data,
                order_notes=payload.order_notes,
                expected_delivery_date=payload.expected_delivery_date,
                created_by=actor.id,
                updated_by=actor.id,
            )
            action = "contact_lens_order.create"
        else:
            if order.status not in self.EDITABLE_STATUSES:
                raise AppException(status_code=409, code="contact_lens_order_read_only", message="This order can no longer be edited")
            order.vendor_id = vendor_id
            order.lens_data = lens_data
            order.order_notes = payload.order_notes
            order.expected_delivery_date = payload.expected_delivery_date
            order.updated_by = actor.id
            action = "contact_lens_order.update"
        visit.contact_lens_workup_requested = True
        visit.updated_by = actor.id
        try:
            is_new = order.id is None
            if is_new:
                self.repo.create_order(order)
                self._record_order_event(
                    order,
                    event="contact_lens_ordered",
                    status=DispensingOrderStatus.DRAFT,
                    actor=actor,
                    notes=payload.order_notes,
                )
            else:
                self.repo.save_order(order)
            self.visit_repo.save(visit)
            self.audit_service.log(
                actor_user_id=actor.id,
                action=action,
                entity_type="contact_lens_order",
                entity_id=str(order.id),
                new_values={"visit_id": visit.id, "vendor_id": order.vendor_id, "status": order.status.value},
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="contact_lens_order_conflict", message="Unable to save contact lens order") from exc
        return self._serialize_order(self._get_order(visit_id))

    def change_order_status(
        self,
        visit_id: int,
        payload: ContactLensOrderStatusUpdate,
        actor: User,
    ) -> ContactLensOrderRead:
        self._ensure_visit(visit_id, actor)
        order = self._get_order(visit_id)
        if payload.status == order.status:
            return self._serialize_order(order)
        if payload.status not in self.STATUS_TRANSITIONS[order.status]:
            raise AppException(
                status_code=409,
                code="contact_lens_order_invalid_status_transition",
                message=f"Cannot change order from {order.status.value} to {payload.status.value}",
            )
        previous = order.status
        order.status = payload.status
        order.updated_by = actor.id
        if payload.status == DispensingOrderStatus.DELIVERED:
            order.delivered_by = actor.id
            order.delivered_at = datetime.now(UTC)
        self.repo.save_order(order)
        self._record_order_event(
            order,
            event=self.STATUS_EVENTS[payload.status],
            previous_status=previous,
            status=payload.status,
            actor=actor,
            notes=payload.notes,
        )
        self.audit_service.log(
            actor_user_id=actor.id,
            action="contact_lens_order.status_change",
            entity_type="contact_lens_order",
            entity_id=str(order.id),
            old_values={"status": previous.value},
            new_values={"status": order.status.value},
        )
        self.db.commit()
        return self._serialize_order(self._get_order(visit_id))

    @staticmethod
    def _due_date(payload: ContactLensFollowUpSchedule) -> date:
        today = date.today()
        if payload.interval == FollowUpInterval.ONE_WEEK:
            return today + timedelta(days=7)
        if payload.interval == FollowUpInterval.FIFTEEN_DAYS:
            return today + timedelta(days=15)
        if payload.interval == FollowUpInterval.ONE_MONTH:
            return today + timedelta(days=30)
        assert payload.due_date is not None
        if payload.due_date < today:
            raise AppException(status_code=422, code="contact_lens_follow_up_due_date_invalid", message="Due date cannot be in the past")
        return payload.due_date

    def schedule_follow_up(
        self,
        visit_id: int,
        payload: ContactLensFollowUpSchedule,
        actor: User,
    ) -> ContactLensFollowUpRead:
        visit = self._ensure_visit(visit_id, actor)
        if visit.status == VisitStatus.CANCELLED:
            raise AppException(status_code=409, code="visit_cancelled", message="Cancelled visits cannot receive follow-ups")
        order = self._get_order(visit_id)
        task = self.repo.get_follow_up_by_visit(visit_id, self.shop_key, FollowUpType.CONTACT_LENS.value)
        if task and task.status != FollowUpStatus.PENDING:
            raise AppException(
                status_code=409,
                code="contact_lens_follow_up_read_only",
                message="Completed or cancelled follow-ups cannot be changed",
            )
        due_date = self._due_date(payload)
        if task is None:
            task = FollowUpTask(
                shop_key=self.shop_key,
                customer_id=visit.customer_id,
                visit_id=visit.id,
                contact_lens_order_id=order.id,
                task_type=FollowUpType.CONTACT_LENS.value,
                interval=payload.interval.value,
                due_date=due_date,
                status=FollowUpStatus.PENDING,
                notes=payload.notes,
                reminder_state=FollowUpReminderState.NOT_SCHEDULED,
                created_by=actor.id,
                updated_by=actor.id,
            )
            action = "contact_lens_follow_up.create"
            self.repo.create_follow_up(task)
        else:
            task.interval = payload.interval.value
            task.due_date = due_date
            task.notes = payload.notes
            task.updated_by = actor.id
            action = "contact_lens_follow_up.update"
            self.repo.save_follow_up(task)
        self.audit_service.log(
            actor_user_id=actor.id,
            action=action,
            entity_type="follow_up_task",
            entity_id=str(task.id),
            new_values={"visit_id": visit.id, "due_date": task.due_date.isoformat(), "status": task.status.value},
        )
        self.db.commit()
        return self._serialize_follow_up(
            self.repo.get_follow_up_by_visit(visit_id, self.shop_key, FollowUpType.CONTACT_LENS.value)
        )

    def change_follow_up_status(self, visit_id: int, status: FollowUpStatus, actor: User) -> ContactLensFollowUpRead:
        self._ensure_visit(visit_id, actor)
        task = self.repo.get_follow_up_by_visit(visit_id, self.shop_key, FollowUpType.CONTACT_LENS.value)
        if not task:
            raise AppException(status_code=404, code="contact_lens_follow_up_not_found", message="Follow-up not found")
        if status == task.status:
            return self._serialize_follow_up(task)
        if task.status != FollowUpStatus.PENDING or status == FollowUpStatus.PENDING:
            raise AppException(
                status_code=409,
                code="contact_lens_follow_up_invalid_status_transition",
                message=f"Cannot change follow-up from {task.status.value} to {status.value}",
            )
        return self.change_follow_up_status_by_id(
            visit_id,
            task.id,
            FollowUpStatusUpdate(status=status),
            actor,
            error_code="contact_lens_follow_up_invalid_status_transition",
        )

    def list_follow_ups(self, visit_id: int, actor: User) -> FollowUpListResponse:
        self._ensure_visit(visit_id, actor)
        items = self.repo.list_follow_ups_by_visit(visit_id, self.shop_key)
        return FollowUpListResponse(
            visit_id=visit_id,
            items=[self._serialize_follow_up(item) for item in items],
            total=len(items),
        )

    def _validate_follow_up_context(self, visit_id: int, task_type: FollowUpType) -> int | None:
        if task_type == FollowUpType.CONTACT_LENS:
            order = self.repo.get_order_by_visit(visit_id, self.shop_key)
            if not order:
                raise AppException(
                    status_code=422,
                    code="contact_lens_order_required",
                    message="Create the contact lens order before scheduling this follow-up",
                )
            return order.id
        if task_type == FollowUpType.PROGRESSIVE_ADAPTATION:
            order = (
                self.db.query(DispensingOrder)
                .filter(DispensingOrder.visit_id == visit_id, DispensingOrder.shop_key == self.shop_key)
                .first()
            )
            if not order or order.lens_data.get("lens_type") != "progressive":
                raise AppException(
                    status_code=422,
                    code="progressive_order_required",
                    message="A progressive spectacle order is required for this follow-up",
                )
        return None

    def create_follow_up(self, visit_id: int, payload: FollowUpCreate, actor: User) -> ContactLensFollowUpRead:
        visit = self._ensure_visit(visit_id, actor)
        if visit.status == VisitStatus.CANCELLED:
            raise AppException(status_code=409, code="visit_cancelled", message="Cancelled visits cannot receive follow-ups")
        if payload.due_date < date.today():
            raise AppException(status_code=422, code="follow_up_due_date_invalid", message="Due date cannot be in the past")
        if payload.assigned_staff_id is not None:
            assignee = (
                self.db.query(User)
                .filter(User.id == payload.assigned_staff_id, User.shop_key == self.shop_key)
                .first()
            )
            if assignee is None:
                raise AppException(status_code=404, code="follow_up_assignee_not_found", message="Assigned staff not found")
        contact_lens_order_id = self._validate_follow_up_context(visit_id, payload.task_type)
        task = FollowUpTask(
            shop_key=self.shop_key,
            customer_id=visit.customer_id,
            visit_id=visit.id,
            contact_lens_order_id=contact_lens_order_id,
            task_type=payload.task_type.value,
            due_date=payload.due_date,
            status=FollowUpStatus.PENDING,
            assigned_staff_id=payload.assigned_staff_id,
            reminder_state=payload.reminder_state,
            notes=payload.notes,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repo.create_follow_up(task)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="follow_up.create",
            entity_type="follow_up_task",
            entity_id=str(task.id),
            new_values={
                "visit_id": visit.id,
                "task_type": task.task_type,
                "due_date": task.due_date.isoformat(),
                "assigned_staff_id": task.assigned_staff_id,
                "reminder_state": task.reminder_state.value,
            },
        )
        self.db.commit()
        return self._serialize_follow_up(self.repo.get_follow_up_by_id(task.id, visit.id, self.shop_key))

    def change_follow_up_status_by_id(
        self,
        visit_id: int,
        task_id: int,
        payload: FollowUpStatusUpdate,
        actor: User,
        *,
        error_code: str = "follow_up_invalid_status_transition",
    ) -> ContactLensFollowUpRead:
        self._ensure_visit(visit_id, actor)
        task = self.repo.get_follow_up_by_id(task_id, visit_id, self.shop_key)
        if not task:
            raise AppException(status_code=404, code="follow_up_not_found", message="Follow-up not found")
        if payload.status == task.status:
            return self._serialize_follow_up(task)
        if task.status != FollowUpStatus.PENDING or payload.status == FollowUpStatus.PENDING:
            raise AppException(
                status_code=409,
                code=error_code,
                message=f"Cannot change follow-up from {task.status.value} to {payload.status.value}",
            )
        previous = task.status
        task.status = payload.status
        task.updated_by = actor.id
        if payload.status == FollowUpStatus.COMPLETED:
            task.completed_by = actor.id
            task.completed_at = datetime.now(UTC)
            task.completion_notes = payload.completion_notes
        self.repo.save_follow_up(task)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="follow_up.status_change",
            entity_type="follow_up_task",
            entity_id=str(task.id),
            old_values={"status": previous.value},
            new_values={"status": task.status.value, "completion_notes": task.completion_notes},
        )
        self.db.commit()
        return self._serialize_follow_up(self.repo.get_follow_up_by_id(task.id, visit_id, self.shop_key))
