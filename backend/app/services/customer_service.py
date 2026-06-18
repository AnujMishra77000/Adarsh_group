from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.contact_lens_order import ContactLensOrder
from app.models.customer import Customer
from app.models.dispensing_order import DispensingOrder
from app.models.enums import PrescriptionVersionStatus
from app.models.user import User
from app.models.visit_prescription import VisitPrescription
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import (
    CustomerBillSummary,
    CustomerContactLensOrderSummary,
    CustomerCreate,
    CustomerDetailRead,
    CustomerDispensingOrderSummary,
    CustomerListResponse,
    CustomerFollowUpTaskSummary,
    CustomerPrescriptionSummary,
    CustomerRead,
    CustomerReferralSummary,
    CustomerTimelineItem,
    CustomerUpdate,
    CustomerVisitSummary,
)
from app.services.audit_service import AuditService
from app.services.email_service import EmailService


class CustomerService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = CustomerRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)
        self.email_service = EmailService()

    def list_customers(self, page: int, page_size: int, search: str | None) -> CustomerListResponse:
        items, total = self.repo.list(page=page, page_size=page_size, shop_key=self.shop_key, search=search)
        return CustomerListResponse(
            items=[CustomerRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def _generate_customer_code(self) -> str:
        today_segment = datetime.utcnow().strftime("%Y%m%d")
        for _ in range(10):
            code = f"CUST-{today_segment}-{secrets.randbelow(1_000_000):06d}"
            if not self.repo.exists_business_id(code, shop_key=self.shop_key):
                return code
        raise AppException(status_code=500, code="customer_id_generation_failed", message="Unable to generate customer id")

    @staticmethod
    def _referral_value(payload: dict, key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def create_customer(self, payload: CustomerCreate, actor: User) -> CustomerRead:
        registration_idempotency_key = (
            payload.registration_idempotency_key.strip() if payload.registration_idempotency_key else None
        )
        if registration_idempotency_key:
            existing_customer = self.repo.get_by_registration_idempotency_key(
                registration_idempotency_key,
                shop_key=self.shop_key,
            )
            if existing_customer:
                return CustomerRead.model_validate(existing_customer)

        customer = Customer(
            shop_key=self.shop_key,
            customer_id=self._generate_customer_code(),
            name=payload.name,
            age=payload.age,
            contact_no=payload.contact_no,
            email=payload.email,
            whatsapp_no=payload.whatsapp_no,
            gender=payload.gender,
            occupation=payload.occupation,
            guardian_name=payload.guardian_name,
            guardian_contact_no=payload.guardian_contact_no,
            address=payload.address,
            purpose_of_visit=payload.purpose_of_visit,
            whatsapp_opt_in=payload.whatsapp_opt_in,
            registration_idempotency_key=registration_idempotency_key,
            created_by=actor.id,
            updated_by=actor.id,
        )

        try:
            self.repo.create(customer)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="customer.create",
                entity_type="customer",
                entity_id=str(customer.id),
                new_values={
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "contact_no": customer.contact_no,
                    "email": customer.email,
                },
            )
            self.db.commit()
            self.db.refresh(customer)
        except IntegrityError as exc:
            self.db.rollback()
            if registration_idempotency_key:
                existing_customer = self.repo.get_by_registration_idempotency_key(
                    registration_idempotency_key,
                    shop_key=self.shop_key,
                )
                if existing_customer:
                    return CustomerRead.model_validate(existing_customer)
            raise AppException(status_code=409, code="customer_create_conflict", message="Unable to create customer") from exc

        if customer.email:
            self.email_service.send_customer_welcome_email(customer)

        return CustomerRead.model_validate(customer)

    def get_customer(self, customer_pk: int) -> CustomerDetailRead:
        customer = self.repo.get_detail(customer_pk, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        prescriptions = sorted(
            [p for p in customer.prescriptions if not p.is_deleted],
            key=lambda item: (item.prescription_date, item.created_at),
            reverse=True,
        )
        bills = sorted(
            [b for b in customer.bills if not b.is_deleted],
            key=lambda item: item.created_at,
            reverse=True,
        )
        contact_lens_orders = sorted(
            self.db.query(ContactLensOrder)
            .filter(ContactLensOrder.customer_id == customer.id, ContactLensOrder.shop_key == self.shop_key)
            .all(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        dispensing_orders = sorted(
            self.db.query(DispensingOrder)
            .filter(DispensingOrder.customer_id == customer.id, DispensingOrder.shop_key == self.shop_key)
            .all(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        visit_prescriptions = (
            self.db.query(VisitPrescription)
            .filter(VisitPrescription.customer_id == customer.id, VisitPrescription.shop_key == self.shop_key)
            .order_by(VisitPrescription.created_at.desc())
            .all()
        )
        follow_up_tasks = sorted(
            list(customer.follow_up_tasks),
            key=lambda item: (item.due_date, item.created_at),
            reverse=True,
        )
        visits = sorted(
            list(customer.visits),
            key=lambda item: (item.visit_date, item.created_at),
            reverse=True,
        )
        referrals: list[CustomerReferralSummary] = []
        timeline: list[CustomerTimelineItem] = []
        for visit in visits:
            timeline.append(
                CustomerTimelineItem(
                    event="visit",
                    occurred_at=visit.visit_date,
                    label=f"Visit: {visit.reason_for_visit}",
                    visit_id=visit.id,
                    entity_type="visit",
                    entity_id=visit.id,
                    status=visit.status.value,
                    user_id=visit.created_by,
                    notes=visit.visit_notes,
                )
            )
            for section in visit.exam_sections:
                if section.section_key != "referral":
                    continue
                payload = section.payload if isinstance(section.payload, dict) else {}
                if payload.get("referral_required") is not True:
                    continue
                referrals.append(
                    CustomerReferralSummary(
                        visit_id=visit.id,
                        visit_date=visit.visit_date,
                        specialist_type=self._referral_value(payload, "specialist_type"),
                        referral_status=self._referral_value(payload, "referral_status"),
                        notes=self._referral_value(payload, "notes"),
                        follow_up=self._referral_value(payload, "follow_up"),
                    )
                )
                timeline.append(
                    CustomerTimelineItem(
                        event="referral",
                        occurred_at=section.updated_at,
                        label="Referral recorded",
                        visit_id=visit.id,
                        entity_type="visit_exam_section",
                        entity_id=section.id,
                        status=self._referral_value(payload, "referral_status"),
                        user_id=section.updated_by,
                        notes=self._referral_value(payload, "notes"),
                    )
                )

        for prescription in visit_prescriptions:
            if prescription.status not in {
                PrescriptionVersionStatus.FINALIZED,
                PrescriptionVersionStatus.SUPERSEDED,
            } or prescription.finalized_at is None:
                continue
            amended = prescription.amends_prescription_id is not None
            timeline.append(
                CustomerTimelineItem(
                    event="prescription_amended" if amended else "prescription_finalized",
                    occurred_at=prescription.finalized_at,
                    label=(
                        f"Prescription amendment v{prescription.version_number} finalized"
                        if amended
                        else f"Prescription v{prescription.version_number} finalized"
                    ),
                    visit_id=prescription.visit_id,
                    entity_type="visit_prescription",
                    entity_id=prescription.id,
                    status=prescription.status.value,
                    user_id=prescription.finalized_by,
                    notes=prescription.patient_instructions,
                )
            )
            if prescription.pdf_file_path:
                timeline.append(
                    CustomerTimelineItem(
                        event="prescription_card_generated",
                        occurred_at=prescription.updated_at,
                        label=f"Prescription card v{prescription.version_number} generated",
                        visit_id=prescription.visit_id,
                        entity_type="visit_prescription",
                        entity_id=prescription.id,
                        status=prescription.status.value,
                        user_id=prescription.updated_by,
                        notes=None,
                    )
                )

        for order in [*dispensing_orders, *contact_lens_orders]:
            order_type = "dispensing_order" if isinstance(order, DispensingOrder) else "contact_lens_order"
            fallback_event = "spectacle_ordered" if isinstance(order, DispensingOrder) else "contact_lens_ordered"
            if not order.status_events:
                timeline.append(
                    CustomerTimelineItem(
                        event=fallback_event,
                        occurred_at=order.created_at,
                        label=f"{order.order_reference}: {fallback_event.replace('_', ' ')}",
                        visit_id=order.visit_id,
                        entity_type=order_type,
                        entity_id=order.id,
                        status=order.status.value,
                        user_id=order.created_by,
                        notes=None,
                    )
                )
            for event in order.status_events:
                timeline.append(
                    CustomerTimelineItem(
                        event=event.event,
                        occurred_at=event.occurred_at,
                        label=f"{order.order_reference}: {event.event.replace('_', ' ')}",
                        visit_id=order.visit_id,
                        entity_type=order_type,
                        entity_id=order.id,
                        status=event.status,
                        user_id=event.user_id,
                        notes=event.notes,
                        previous_status=event.previous_status,
                    )
                )

        for bill in bills:
            has_invoice = bool(bill.pdf_file_path or bill.pdf_url)
            timeline.append(
                CustomerTimelineItem(
                    event="invoice_generated" if has_invoice else "invoice_created",
                    occurred_at=bill.updated_at if has_invoice else bill.created_at,
                    label=f"Invoice {bill.bill_number} {'generated' if has_invoice else 'created'}",
                    visit_id=bill.visit_id,
                    entity_type="bill",
                    entity_id=bill.id,
                    status=bill.payment_status.value,
                    user_id=bill.updated_by if has_invoice else bill.created_by,
                    notes=bill.notes,
                )
            )
            for payment in bill.payments:
                timeline.append(
                    CustomerTimelineItem(
                        event="payment_recorded",
                        occurred_at=payment.created_at,
                        label=f"Payment recorded for {bill.bill_number}",
                        visit_id=bill.visit_id,
                        entity_type="payment",
                        entity_id=payment.id,
                        status=payment.mode.value,
                        user_id=payment.created_by,
                        notes=payment.reference_no,
                    )
                )

        for task in follow_up_tasks:
            task_type = task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)
            timeline.append(
                CustomerTimelineItem(
                    event="follow_up_scheduled",
                    occurred_at=task.created_at,
                    label=f"{task_type.replace('_', ' ').title()} follow-up scheduled",
                    visit_id=task.visit_id,
                    entity_type="follow_up",
                    entity_id=task.id,
                    status=task.status.value,
                    user_id=task.created_by,
                    notes=task.notes,
                )
            )
            if task.completed_at:
                timeline.append(
                    CustomerTimelineItem(
                        event="follow_up_completed",
                        occurred_at=task.completed_at,
                        label=f"{task_type.replace('_', ' ').title()} follow-up completed",
                        visit_id=task.visit_id,
                        entity_type="follow_up",
                        entity_id=task.id,
                        status=task.status.value,
                        user_id=task.completed_by,
                        notes=task.completion_notes,
                        previous_status="pending",
                    )
                )
        timeline.sort(key=lambda item: item.occurred_at, reverse=True)

        return CustomerDetailRead(
            **CustomerRead.model_validate(customer).model_dump(),
            visits=[
                CustomerVisitSummary(
                    id=visit.id,
                    visit_date=visit.visit_date,
                    reason_for_visit=visit.reason_for_visit,
                    referred_by=visit.referred_by,
                    status=visit.status.value,
                    assigned_examiner_id=visit.assigned_examiner_id,
                    visit_notes=visit.visit_notes,
                    created_at=visit.created_at,
                )
                for visit in visits
            ],
            referrals=referrals,
            prescriptions=[
                CustomerPrescriptionSummary(
                    id=prescription.id,
                    prescription_date=prescription.prescription_date,
                    notes=prescription.notes,
                )
                for prescription in prescriptions
            ],
            bills=[
                CustomerBillSummary(
                    id=bill.id,
                    bill_number=bill.bill_number,
                    final_price=bill.final_price,
                    balance_amount=bill.balance_amount,
                    payment_status=bill.payment_status,
                    created_at=bill.created_at,
                )
                for bill in bills
            ],
            dispensing_orders=[
                CustomerDispensingOrderSummary(
                    id=order.id,
                    visit_id=order.visit_id,
                    order_reference=order.order_reference,
                    status=order.status,
                    vendor_id=order.vendor_id,
                    delivered_by=order.delivered_by,
                    delivered_at=order.delivered_at,
                    created_at=order.created_at,
                )
                for order in dispensing_orders
            ],
            contact_lens_orders=[
                CustomerContactLensOrderSummary(
                    id=order.id,
                    visit_id=order.visit_id,
                    order_reference=order.order_reference,
                    status=order.status,
                    vendor_id=order.vendor_id,
                    delivered_by=order.delivered_by,
                    delivered_at=order.delivered_at,
                    created_at=order.created_at,
                )
                for order in contact_lens_orders
            ],
            follow_up_tasks=[
                CustomerFollowUpTaskSummary(
                    id=task.id,
                    visit_id=task.visit_id,
                    contact_lens_order_id=task.contact_lens_order_id,
                    task_type=task.task_type,
                    due_date=task.due_date,
                    status=task.status,
                    notes=task.notes,
                    assigned_staff_id=task.assigned_staff_id,
                    reminder_state=task.reminder_state.value,
                    completion_notes=task.completion_notes,
                    completed_at=task.completed_at,
                )
                for task in follow_up_tasks
            ],
            timeline=timeline,
        )

    def update_customer(self, customer_pk: int, payload: CustomerUpdate, actor: User) -> CustomerRead:
        customer = self.repo.get_by_id(customer_pk, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        old_values = {
            "name": customer.name,
            "contact_no": customer.contact_no,
            "email": customer.email,
            "whatsapp_no": customer.whatsapp_no,
            "occupation": customer.occupation,
            "guardian_name": customer.guardian_name,
            "guardian_contact_no": customer.guardian_contact_no,
            "address": customer.address,
            "purpose_of_visit": customer.purpose_of_visit,
            "whatsapp_opt_in": customer.whatsapp_opt_in,
        }

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        customer.updated_by = actor.id

        try:
            self.repo.save(customer)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="customer.update",
                entity_type="customer",
                entity_id=str(customer.id),
                old_values=old_values,
                new_values=update_data,
            )
            self.db.commit()
            self.db.refresh(customer)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="customer_update_conflict", message="Unable to update customer") from exc

        return CustomerRead.model_validate(customer)

    def delete_customer(self, customer_pk: int, actor: User) -> None:
        customer = self.repo.get_by_id(customer_pk, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        if customer.is_deleted:
            return

        customer.is_deleted = True
        customer.updated_by = actor.id

        self.repo.save(customer)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="customer.delete",
            entity_type="customer",
            entity_id=str(customer.id),
            old_values={"is_deleted": False},
            new_values={"is_deleted": True},
        )
        self.db.commit()
