from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_name
from app.models.bill import Bill
from app.models.customer import Customer
from app.models.enums import PaymentStatus, WhatsAppModuleType, WhatsAppStatus
from app.models.user import User
from app.repositories.bill_repository import BillRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.bill import BillCreate, BillListResponse, BillRead, BillUpdate
from app.services.audit_service import AuditService
from app.services.invoice_pdf_service import InvoicePdfService
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppSendResult, WhatsAppService

logger = structlog.get_logger(__name__)

MONEY_QUANTIZER = Decimal("0.01")


class BillService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = BillRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.audit_service = AuditService(db)
        self.invoice_pdf_service = InvoicePdfService()
        self.email_service = EmailService()
        self.whatsapp_service = WhatsAppService(db)

    @staticmethod
    def _to_money(value: Decimal | int | float | str) -> Decimal:
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise AppException(status_code=422, code="invalid_money_value", message="Invalid monetary value") from exc

        if parsed.is_nan() or parsed.is_infinite():
            raise AppException(status_code=422, code="invalid_money_value", message="Invalid monetary value")

        parsed = parsed.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        if parsed < Decimal("0.00"):
            raise AppException(status_code=422, code="invalid_money_value", message="Monetary value cannot be negative")

        return parsed

    def _calculate_amounts(self, whole_price: Decimal, discount: Decimal, paid_amount: Decimal) -> tuple[Decimal, Decimal, PaymentStatus]:
        if discount > whole_price:
            raise AppException(
                status_code=422,
                code="discount_exceeds_whole_price",
                message="Discount cannot be greater than whole price",
            )

        final_price = (whole_price - discount).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        if paid_amount > final_price:
            raise AppException(
                status_code=422,
                code="paid_exceeds_final_price",
                message="Paid amount cannot be greater than final price",
            )

        balance_amount = (final_price - paid_amount).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        if balance_amount <= Decimal("0.00"):
            payment_status = PaymentStatus.PAID
        elif paid_amount > Decimal("0.00"):
            payment_status = PaymentStatus.PARTIAL
        else:
            payment_status = PaymentStatus.PENDING

        return final_price, balance_amount, payment_status

    def _serialize(self, bill: Bill) -> BillRead:
        customer = bill.customer
        return BillRead(
            id=bill.id,
            bill_number=bill.bill_number,
            customer_id=bill.customer_id,
            customer_name_snapshot=bill.customer_name_snapshot,
            product_name=bill.product_name,
            frame_name=bill.frame_name,
            whole_price=bill.whole_price,
            discount=bill.discount,
            final_price=bill.final_price,
            paid_amount=bill.paid_amount,
            balance_amount=bill.balance_amount,
            payment_mode=bill.payment_mode,
            payment_status=bill.payment_status,
            delivery_date=bill.delivery_date,
            notes=bill.notes,
            pdf_url=bill.pdf_url,
            created_at=bill.created_at,
            updated_at=bill.updated_at,
            created_by=bill.created_by,
            updated_by=bill.updated_by,
            is_deleted=bill.is_deleted,
            customer_name=customer.name if customer else None,
            customer_business_id=customer.customer_id if customer else None,
            customer_contact_no=customer.contact_no if customer else None,
        )

    def _generate_bill_number(self) -> str:
        today = datetime.now(UTC).date()
        existing_count = self.repo.count_created_for_day(today, shop_key=self.shop_key)

        for offset in range(1, 500):
            sequence = existing_count + offset
            candidate = f"BILL-{today:%Y%m%d}-{sequence:04d}"
            if not self.repo.get_by_bill_number(candidate):
                return candidate

        raise AppException(status_code=500, code="bill_number_generation_failed", message="Unable to generate bill number")

    @staticmethod
    def _is_customer_whatsapp_eligible(customer: Customer) -> bool:
        return bool(
            customer.whatsapp_opt_in
            and customer.whatsapp_no
            and customer.whatsapp_no.strip()
            and not customer.is_deleted
        )

    
    @staticmethod
    def _is_customer_email_eligible(customer: Customer) -> bool:
        return bool(
            customer.email
            and customer.email.strip()
            and not customer.is_deleted
        )

    @staticmethod
    def _format_money(value: Decimal) -> str:
        return f"{Decimal(value):,.2f}"

    def _resolve_media_file_from_public_url(self, media_url: str) -> Path:
        parsed = urlparse(media_url)
        path_value = parsed.path if parsed.scheme else media_url

        if not path_value.startswith(settings.media_url_prefix):
            raise AppException(status_code=422, code="invalid_media_url", message="Bill PDF URL is invalid")

        relative_part = path_value[len(settings.media_url_prefix) :].lstrip("/")
        absolute_path = settings.media_root_path / relative_part

        if not absolute_path.exists() or not absolute_path.is_file():
            raise AppException(status_code=404, code="bill_pdf_not_found", message="Bill PDF file not found on server")

        return absolute_path

    def _send_bill_whatsapp_document(
        self,
        *,
        bill: Bill,
        customer: Customer,
        actor: User,
        raise_on_error: bool,
    ) -> WhatsAppSendResult:
        if not bill.pdf_url:
            raise AppException(status_code=422, code="bill_pdf_missing", message="Bill PDF has not been generated")

        pdf_file = self._resolve_media_file_from_public_url(bill.pdf_url)
        media_id = self.whatsapp_service.upload_media(pdf_file)

        caption = (
            f"Invoice {bill.bill_number} from {get_shop_name(self.shop_key)}. "
            f"Final: INR {self._format_money(bill.final_price)}, "
            f"Balance: INR {self._format_money(bill.balance_amount)}"
        )

        return self.whatsapp_service.send_document_message(
            module_type=WhatsAppModuleType.BILL,
            reference_id=bill.id,
            customer_id=customer.id,
            recipient_no=customer.whatsapp_no or "",
            media_id=media_id,
            document_name=pdf_file.name,
            caption=caption,
            raise_on_error=raise_on_error,
        )

    def _send_bill_email_document(
        self,
        *,
        bill: Bill,
        customer: Customer,
        raise_on_error: bool,
    ) -> bool:
        if not bill.pdf_url:
            raise AppException(status_code=422, code="bill_pdf_missing", message="Bill PDF has not been generated")

        if not self.email_service.is_configured():
            raise AppException(
                status_code=422,
                code="email_provider_not_configured",
                message="Gmail SMTP is not configured",
            )

        if not customer.email or not customer.email.strip():
            raise AppException(
                status_code=422,
                code="customer_email_missing",
                message="Customer email is not available",
            )

        pdf_file = self._resolve_media_file_from_public_url(bill.pdf_url)
        sent = self.email_service.send_bill_invoice_email(customer=customer, bill=bill, invoice_pdf_path=pdf_file)

        if not sent and raise_on_error:
            raise AppException(
                status_code=502,
                code="bill_email_send_failed",
                message="Unable to send bill on email",
            )

        return sent

    def _try_auto_generate_pdf(self, bill: Bill, actor: User, action: str) -> None:
        try:
            pdf_url = self.invoice_pdf_service.generate_invoice_pdf(
                bill=bill,
                staff_name=actor.full_name or actor.email,
            )
            bill.pdf_url = pdf_url
            bill.updated_by = actor.id
            self.repo.save(bill)
            self.audit_service.log(
                actor_user_id=actor.id,
                action=action,
                entity_type="bill",
                entity_id=str(bill.id),
                new_values={"pdf_url": pdf_url},
            )
            self.db.commit()
            self.db.refresh(bill)
        except AppException as exc:
            self.db.rollback()
            logger.warning("bill.auto_pdf_generation_failed", bill_id=bill.id, code=exc.code, message=exc.message)
        except Exception as exc:  # pragma: no cover - defensive safety
            self.db.rollback()
            logger.warning("bill.auto_pdf_generation_failed_unknown", bill_id=bill.id, error=str(exc))

    def _try_auto_send_whatsapp(self, bill: Bill, customer: Customer, actor: User) -> None:
        try:
            result = self._send_bill_whatsapp_document(bill=bill, customer=customer, actor=actor, raise_on_error=False)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="bill.send_whatsapp.auto",
                entity_type="bill",
                entity_id=str(bill.id),
                metadata_json={
                    "status": result.status.value,
                    "whatsapp_log_id": result.whatsapp_log_id,
                    "provider_message_id": result.provider_message_id,
                    "error_message": result.error_message,
                },
            )
            self.db.commit()

            if result.status != WhatsAppStatus.SENT:
                logger.warning(
                    "bill.auto_whatsapp_send_failed",
                    bill_id=bill.id,
                    whatsapp_log_id=result.whatsapp_log_id,
                    error=result.error_message,
                )
        except AppException as exc:
            self.db.rollback()
            logger.warning(
                "bill.auto_whatsapp_send_failed",
                bill_id=bill.id,
                code=exc.code,
                message=exc.message,
            )
        except Exception as exc:  # pragma: no cover - defensive safety
            self.db.rollback()
            logger.warning("bill.auto_whatsapp_send_failed_unknown", bill_id=bill.id, error=str(exc))

    def _try_auto_send_email(self, bill: Bill, customer: Customer, actor: User) -> None:
        if not self.email_service.is_configured():
            return

        try:
            sent = self._send_bill_email_document(bill=bill, customer=customer, raise_on_error=False)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="bill.send_email.auto",
                entity_type="bill",
                entity_id=str(bill.id),
                metadata_json={"status": "sent" if sent else "failed", "customer_email": customer.email},
            )
            self.db.commit()

            if not sent:
                logger.warning("bill.auto_email_send_failed", bill_id=bill.id, customer_id=customer.id)
        except AppException as exc:
            self.db.rollback()
            logger.warning(
                "bill.auto_email_send_failed",
                bill_id=bill.id,
                code=exc.code,
                message=exc.message,
            )
        except Exception as exc:  # pragma: no cover - defensive safety
            self.db.rollback()
            logger.warning("bill.auto_email_send_failed_unknown", bill_id=bill.id, error=str(exc))

    def list_bills(self, page: int, page_size: int, search: str | None, customer_pk: int | None) -> BillListResponse:
        items, total = self.repo.list(
            page=page,
            page_size=page_size,
            shop_key=self.shop_key,
            search=search,
            customer_pk=customer_pk,
        )
        return BillListResponse(
            items=[self._serialize(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_bill(self, bill_id: int) -> BillRead:
        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")
        return self._serialize(bill)

    def create_bill(self, payload: BillCreate, actor: User) -> BillRead:
        customer = self.customer_repo.get_by_id(payload.customer_id, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        whole_price = self._to_money(payload.whole_price)
        discount = self._to_money(payload.discount)
        paid_amount = self._to_money(payload.paid_amount)
        final_price, balance_amount, payment_status = self._calculate_amounts(
            whole_price=whole_price,
            discount=discount,
            paid_amount=paid_amount,
        )

        bill: Bill | None = None

        for _ in range(5):
            bill_number = self._generate_bill_number()
            bill = Bill(
                bill_number=bill_number,
                customer_id=customer.id,
                customer_name_snapshot=customer.name,
                product_name=payload.product_name,
                frame_name=payload.frame_name,
                whole_price=whole_price,
                discount=discount,
                final_price=final_price,
                paid_amount=paid_amount,
                balance_amount=balance_amount,
                payment_mode=payload.payment_mode,
                payment_status=payment_status,
                delivery_date=payload.delivery_date,
                notes=payload.notes,
                created_by=actor.id,
                updated_by=actor.id,
            )

            try:
                self.repo.create(bill)
                self.audit_service.log(
                    actor_user_id=actor.id,
                    action="bill.create",
                    entity_type="bill",
                    entity_id=str(bill.id),
                    new_values={
                        "bill_number": bill.bill_number,
                        "customer_id": bill.customer_id,
                        "final_price": str(bill.final_price),
                        "paid_amount": str(bill.paid_amount),
                        "balance_amount": str(bill.balance_amount),
                    },
                )
                self.db.commit()
                self.db.refresh(bill)
                break
            except IntegrityError as exc:
                self.db.rollback()
                if "bill_number" in str(exc).lower():
                    continue
                raise AppException(status_code=409, code="bill_create_conflict", message="Unable to create bill") from exc

        if bill is None or bill.id is None:
            raise AppException(status_code=500, code="bill_create_failed", message="Unable to create bill")

        self._try_auto_generate_pdf(bill=bill, actor=actor, action="bill.generate_pdf.auto")

        persisted_bill = self.repo.get_by_id(bill.id, shop_key=self.shop_key)
        if persisted_bill and persisted_bill.pdf_url:
            if self._is_customer_email_eligible(customer):
                self._try_auto_send_email(bill=persisted_bill, customer=customer, actor=actor)

            if self._is_customer_whatsapp_eligible(customer):
                self._try_auto_send_whatsapp(bill=persisted_bill, customer=customer, actor=actor)

        return self.get_bill(bill.id)

    def update_bill(self, bill_id: int, payload: BillUpdate, actor: User) -> BillRead:
        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        old_values = {
            "customer_id": bill.customer_id,
            "product_name": bill.product_name,
            "frame_name": bill.frame_name,
            "whole_price": str(bill.whole_price),
            "discount": str(bill.discount),
            "paid_amount": str(bill.paid_amount),
            "payment_mode": bill.payment_mode.value,
            "payment_status": bill.payment_status.value,
            "delivery_date": str(bill.delivery_date) if bill.delivery_date else None,
            "notes": bill.notes,
        }

        update_data = payload.model_dump(exclude_unset=True)

        if payload.customer_id is not None and payload.customer_id != bill.customer_id:
            customer = self.customer_repo.get_by_id(payload.customer_id, shop_key=self.shop_key)
            if not customer:
                raise AppException(status_code=404, code="customer_not_found", message="Customer not found")
            bill.customer_id = customer.id
            bill.customer_name_snapshot = customer.name

        whole_price = self._to_money(update_data.get("whole_price", bill.whole_price))
        discount = self._to_money(update_data.get("discount", bill.discount))
        paid_amount = self._to_money(update_data.get("paid_amount", bill.paid_amount))

        final_price, balance_amount, payment_status = self._calculate_amounts(
            whole_price=whole_price,
            discount=discount,
            paid_amount=paid_amount,
        )

        bill.product_name = update_data.get("product_name", bill.product_name)
        bill.frame_name = update_data.get("frame_name", bill.frame_name)
        bill.whole_price = whole_price
        bill.discount = discount
        bill.final_price = final_price
        bill.paid_amount = paid_amount
        bill.balance_amount = balance_amount
        bill.payment_mode = update_data.get("payment_mode", bill.payment_mode)
        bill.payment_status = payment_status
        bill.delivery_date = update_data.get("delivery_date", bill.delivery_date)
        bill.notes = update_data.get("notes", bill.notes)
        bill.updated_by = actor.id

        try:
            self.repo.save(bill)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="bill.update",
                entity_type="bill",
                entity_id=str(bill.id),
                old_values=old_values,
                new_values={
                    "customer_id": bill.customer_id,
                    "product_name": bill.product_name,
                    "frame_name": bill.frame_name,
                    "whole_price": str(bill.whole_price),
                    "discount": str(bill.discount),
                    "final_price": str(bill.final_price),
                    "paid_amount": str(bill.paid_amount),
                    "balance_amount": str(bill.balance_amount),
                    "payment_mode": bill.payment_mode.value,
                    "payment_status": bill.payment_status.value,
                    "delivery_date": str(bill.delivery_date) if bill.delivery_date else None,
                    "notes": bill.notes,
                },
            )
            self.db.commit()
            self.db.refresh(bill)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="bill_update_conflict", message="Unable to update bill") from exc

        self._try_auto_generate_pdf(bill=bill, actor=actor, action="bill.generate_pdf.refresh")
        return self.get_bill(bill.id)

    def delete_bill(self, bill_id: int, actor: User) -> None:
        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        if bill.is_deleted:
            return

        bill.is_deleted = True
        bill.updated_by = actor.id

        self.repo.save(bill)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="bill.delete",
            entity_type="bill",
            entity_id=str(bill.id),
            old_values={"is_deleted": False},
            new_values={"is_deleted": True},
        )
        self.db.commit()

    def generate_pdf(self, bill_id: int, actor: User) -> BillRead:
        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        pdf_url = self.invoice_pdf_service.generate_invoice_pdf(
            bill=bill,
            staff_name=actor.full_name or actor.email,
        )

        bill.pdf_url = pdf_url
        bill.updated_by = actor.id

        try:
            self.repo.save(bill)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="bill.generate_pdf",
                entity_type="bill",
                entity_id=str(bill.id),
                new_values={"pdf_url": pdf_url},
            )
            self.db.commit()
            self.db.refresh(bill)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=500, code="bill_pdf_persist_failed", message="Unable to save PDF URL") from exc

        return self._serialize(bill)

    def send_email(self, bill_id: int, actor: User) -> str:
        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        customer = bill.customer
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Bill customer not found")

        if not self._is_customer_email_eligible(customer):
            raise AppException(
                status_code=422,
                code="customer_email_not_eligible",
                message="Customer email is not available",
            )

        if not bill.pdf_url:
            self.generate_pdf(bill_id=bill.id, actor=actor)
            bill = self.repo.get_by_id(bill.id, shop_key=self.shop_key)
            if not bill:
                raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        sent = self._send_bill_email_document(bill=bill, customer=customer, raise_on_error=True)

        self.audit_service.log(
            actor_user_id=actor.id,
            action="bill.send_email",
            entity_type="bill",
            entity_id=str(bill.id),
            metadata_json={
                "status": "sent" if sent else "failed",
                "customer_email": customer.email,
            },
        )
        self.db.commit()

        return "Bill sent to customer email successfully"

    def send_whatsapp(self, bill_id: int, actor: User) -> str:
        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        customer = bill.customer
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Bill customer not found")

        if not self._is_customer_whatsapp_eligible(customer):
            raise AppException(
                status_code=422,
                code="customer_whatsapp_not_eligible",
                message="Customer is not eligible for business-initiated WhatsApp messages",
            )

        if not bill.pdf_url:
            self.generate_pdf(bill_id=bill.id, actor=actor)
            bill = self.repo.get_by_id(bill.id, shop_key=self.shop_key)
            if not bill:
                raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        result = self._send_bill_whatsapp_document(bill=bill, customer=customer, actor=actor, raise_on_error=False)

        self.audit_service.log(
            actor_user_id=actor.id,
            action="bill.send_whatsapp",
            entity_type="bill",
            entity_id=str(bill.id),
            metadata_json={
                "status": result.status.value,
                "whatsapp_log_id": result.whatsapp_log_id,
                "provider_message_id": result.provider_message_id,
                "error_message": result.error_message,
            },
        )
        self.db.commit()

        if result.status != WhatsAppStatus.SENT:
            raise AppException(
                status_code=502,
                code="bill_whatsapp_send_failed",
                message=result.error_message or "Unable to send bill on WhatsApp",
            )

        return "Bill sent to customer on WhatsApp successfully"
