from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.customer import Customer
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import (
    CustomerBillSummary,
    CustomerCreate,
    CustomerDetailRead,
    CustomerListResponse,
    CustomerPrescriptionSummary,
    CustomerRead,
    CustomerUpdate,
)
from app.services.audit_service import AuditService
from app.services.email_service import EmailService


class CustomerService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = CustomerRepository(db)
        self.audit_service = AuditService(db)
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
            if not self.repo.exists_business_id(code):
                return code
        raise AppException(status_code=500, code="customer_id_generation_failed", message="Unable to generate customer id")

    def create_customer(self, payload: CustomerCreate, actor: User) -> CustomerRead:
        customer = Customer(
            shop_key=self.shop_key,
            customer_id=self._generate_customer_code(),
            name=payload.name,
            age=payload.age,
            contact_no=payload.contact_no,
            email=payload.email,
            whatsapp_no=payload.whatsapp_no,
            gender=payload.gender,
            address=payload.address,
            purpose_of_visit=payload.purpose_of_visit,
            whatsapp_opt_in=payload.whatsapp_opt_in,
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

        return CustomerDetailRead(
            **CustomerRead.model_validate(customer).model_dump(),
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
