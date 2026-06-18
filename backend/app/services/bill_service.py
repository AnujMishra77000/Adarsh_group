from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_name
from app.models.bill import Bill, BillItem, Payment
from app.models.customer import Customer
from app.models.enums import BillItemType, PaymentMode, PaymentStatus, WhatsAppModuleType, WhatsAppStatus
from app.models.user import User
from app.repositories.bill_repository import BillRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.contact_lens_repository import ContactLensRepository
from app.repositories.dispensing_order_repository import DispensingOrderRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.bill import BillCreate, BillItemCreate, BillListResponse, BillPaymentCreate, BillRead, BillUpdate
from app.services.audit_service import AuditService
from app.services.document_file_service import build_media_file_reference, resolve_media_file_reference
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
        self.contact_lens_repo = ContactLensRepository(db)
        self.dispensing_order_repo = DispensingOrderRepository(db)
        self.visit_repo = VisitRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)
        self.invoice_pdf_service = InvoicePdfService()
        self.email_service = EmailService()
        self.whatsapp_service = WhatsAppService(db, shop_key=shop_key)

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

    @staticmethod
    def _payload_has_field(payload: BillCreate | BillUpdate, field_name: str) -> bool:
        return field_name in payload.model_fields_set

    def _to_quantity(self, value: Decimal | int | float | str) -> Decimal:
        quantity = self._to_money(value)
        if quantity <= Decimal("0.00"):
            raise AppException(status_code=422, code="invalid_quantity", message="Quantity must be greater than zero")
        return quantity

    def _build_item_data(self, item: BillItemCreate) -> dict[str, Decimal | BillItemType | str]:
        quantity = self._to_quantity(item.quantity)
        unit_price = self._to_money(item.unit_price)
        discount = self._to_money(item.discount)
        gross_total = (quantity * unit_price).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

        if discount > gross_total:
            raise AppException(
                status_code=422,
                code="line_discount_exceeds_price",
                message="Line item discount cannot be greater than line price",
            )

        line_total = (gross_total - discount).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        return {
            "item_type": item.item_type,
            "item_name": item.item_name.strip(),
            "quantity": quantity,
            "unit_price": unit_price,
            "discount": discount,
            "line_total": line_total,
        }

    def _legacy_item_from_values(
        self,
        *,
        product_name: str | None,
        frame_name: str | None,
        whole_price: Decimal | None,
        discount: Decimal | None,
    ) -> BillItemCreate:
        if product_name is None or not product_name.strip() or whole_price is None:
            raise AppException(
                status_code=422,
                code="bill_items_required",
                message="Provide at least one bill item",
            )

        return BillItemCreate(
            item_type=BillItemType.FRAME if frame_name else BillItemType.OTHER,
            item_name=product_name.strip(),
            quantity=Decimal("1.00"),
            unit_price=whole_price,
            discount=discount or Decimal("0.00"),
        )

    def _existing_items_as_create(self, bill: Bill) -> list[BillItemCreate]:
        if bill.items:
            return [
                BillItemCreate(
                    item_type=item.item_type,
                    item_name=item.item_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                )
                for item in bill.items
            ]

        return [
            self._legacy_item_from_values(
                product_name=bill.product_name,
                frame_name=bill.frame_name,
                whole_price=bill.whole_price,
                discount=bill.discount,
            )
        ]

    def _resolve_items_for_create(self, payload: BillCreate) -> list[dict[str, Decimal | BillItemType | str]]:
        source_items = payload.items or [
            self._legacy_item_from_values(
                product_name=payload.product_name,
                frame_name=payload.frame_name,
                whole_price=payload.whole_price,
                discount=payload.discount,
            )
        ]
        return [self._build_item_data(item) for item in source_items]

    def _resolve_items_for_update(
        self,
        *,
        bill: Bill,
        payload: BillUpdate,
        update_data: dict,
    ) -> list[dict[str, Decimal | BillItemType | str]]:
        legacy_item_fields = {"product_name", "frame_name", "whole_price", "discount"}
        if self._payload_has_field(payload, "items"):
            if not payload.items:
                raise AppException(
                    status_code=422,
                    code="bill_items_required",
                    message="Provide at least one bill item",
                )
            source_items = payload.items
        elif legacy_item_fields.intersection(update_data):
            source_items = [
                self._legacy_item_from_values(
                    product_name=update_data.get("product_name", bill.product_name),
                    frame_name=update_data.get("frame_name", bill.frame_name),
                    whole_price=update_data.get("whole_price", bill.whole_price),
                    discount=update_data.get("discount", bill.discount),
                )
            ]
        else:
            source_items = self._existing_items_as_create(bill)

        return [self._build_item_data(item) for item in source_items]

    def _build_payment_data(self, payment: BillPaymentCreate) -> dict[str, Decimal | PaymentMode | datetime | str | None]:
        return {
            "mode": payment.mode,
            "amount": self._to_money(payment.amount),
            "paid_at": payment.paid_at or datetime.now(UTC),
            "reference_no": payment.reference_no.strip() if payment.reference_no else None,
        }

    def _legacy_payments_from_values(
        self,
        *,
        paid_amount: Decimal | None,
        payment_mode: PaymentMode | None,
    ) -> list[BillPaymentCreate]:
        paid_total = self._to_money(paid_amount or Decimal("0.00"))
        if paid_total <= Decimal("0.00"):
            return []

        return [
            BillPaymentCreate(
                mode=payment_mode or PaymentMode.CASH,
                amount=paid_total,
            )
        ]

    def _existing_payments_as_create(self, bill: Bill) -> list[BillPaymentCreate]:
        if bill.payments:
            return [
                BillPaymentCreate(
                    mode=payment.mode,
                    amount=payment.amount,
                    paid_at=payment.paid_at,
                    reference_no=payment.reference_no,
                )
                for payment in bill.payments
            ]

        return self._legacy_payments_from_values(paid_amount=bill.paid_amount, payment_mode=bill.payment_mode)

    def _resolve_payments_for_create(self, payload: BillCreate) -> list[dict[str, Decimal | PaymentMode | datetime | str | None]]:
        source_payments = payload.payments or self._legacy_payments_from_values(
            paid_amount=payload.paid_amount,
            payment_mode=payload.payment_mode,
        )
        return [self._build_payment_data(payment) for payment in source_payments]

    def _resolve_payments_for_update(
        self,
        *,
        bill: Bill,
        payload: BillUpdate,
        update_data: dict,
    ) -> list[dict[str, Decimal | PaymentMode | datetime | str | None]]:
        legacy_payment_fields = {"paid_amount", "payment_mode"}
        if self._payload_has_field(payload, "payments"):
            source_payments = payload.payments or []
        elif legacy_payment_fields.intersection(update_data):
            source_payments = self._legacy_payments_from_values(
                paid_amount=update_data.get("paid_amount", bill.paid_amount),
                payment_mode=update_data.get("payment_mode", bill.payment_mode),
            )
        else:
            source_payments = self._existing_payments_as_create(bill)

        return [self._build_payment_data(payment) for payment in source_payments]

    def _calculate_bill_totals(
        self,
        *,
        items_data: list[dict[str, Decimal | BillItemType | str]],
        payments_data: list[dict[str, Decimal | PaymentMode | datetime | str | None]],
        tax_total: Decimal,
    ) -> dict[str, Decimal | PaymentStatus]:
        subtotal = sum(
            (Decimal(item["quantity"]) * Decimal(item["unit_price"])).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
            for item in items_data
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        discount_total = sum(Decimal(item["discount"]) for item in items_data).quantize(
            MONEY_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )
        item_total = sum(Decimal(item["line_total"]) for item in items_data).quantize(
            MONEY_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )
        grand_total = (item_total + tax_total).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        paid_total = sum(Decimal(payment["amount"]) for payment in payments_data).quantize(
            MONEY_QUANTIZER,
            rounding=ROUND_HALF_UP,
        )

        if paid_total > grand_total:
            raise AppException(
                status_code=422,
                code="paid_exceeds_grand_total",
                message="Paid total cannot be greater than bill grand total",
            )

        balance_amount = (grand_total - paid_total).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        if balance_amount <= Decimal("0.00"):
            payment_status = PaymentStatus.PAID
        elif paid_total > Decimal("0.00"):
            payment_status = PaymentStatus.PARTIAL
        else:
            payment_status = PaymentStatus.PENDING

        return {
            "subtotal": subtotal,
            "discount_total": discount_total,
            "tax_total": tax_total,
            "grand_total": grand_total,
            "paid_total": paid_total,
            "balance_amount": balance_amount,
            "payment_status": payment_status,
        }

    @staticmethod
    def _frame_snapshot(items_data: list[dict[str, Decimal | BillItemType | str]], fallback: str | None = None) -> str | None:
        for item in items_data:
            if item["item_type"] == BillItemType.FRAME:
                return str(item["item_name"])
        return fallback

    def _apply_bill_components(
        self,
        *,
        bill: Bill,
        items_data: list[dict[str, Decimal | BillItemType | str]],
        payments_data: list[dict[str, Decimal | PaymentMode | datetime | str | None]],
        tax_total: Decimal,
        frame_name: str | None,
    ) -> None:
        totals = self._calculate_bill_totals(items_data=items_data, payments_data=payments_data, tax_total=tax_total)
        first_item = items_data[0]

        bill.product_name = str(first_item["item_name"])
        bill.frame_name = self._frame_snapshot(items_data, fallback=frame_name)
        bill.whole_price = Decimal(totals["subtotal"])
        bill.discount = Decimal(totals["discount_total"])
        bill.final_price = Decimal(totals["grand_total"])
        bill.paid_amount = Decimal(totals["paid_total"])
        bill.subtotal = Decimal(totals["subtotal"])
        bill.discount_total = Decimal(totals["discount_total"])
        bill.tax_total = Decimal(totals["tax_total"])
        bill.grand_total = Decimal(totals["grand_total"])
        bill.paid_total = Decimal(totals["paid_total"])
        bill.balance_amount = Decimal(totals["balance_amount"])
        bill.payment_status = totals["payment_status"]
        bill.payment_mode = (
            payments_data[0]["mode"]
            if payments_data
            else bill.payment_mode or PaymentMode.CASH
        )
        bill.items = [
            BillItem(
                shop_id=bill.shop_id,
                item_type=item["item_type"],
                item_name=str(item["item_name"]),
                quantity=Decimal(item["quantity"]),
                unit_price=Decimal(item["unit_price"]),
                discount=Decimal(item["discount"]),
                line_total=Decimal(item["line_total"]),
            )
            for item in items_data
        ]
        bill.payments = [
            Payment(
                shop_id=bill.shop_id,
                mode=payment["mode"],
                amount=Decimal(payment["amount"]),
                paid_at=payment["paid_at"],
                reference_no=payment["reference_no"],
            )
            for payment in payments_data
        ]

    @staticmethod
    def _sync_child_shop_ids(bill: Bill) -> None:
        for item in bill.items:
            item.shop_id = bill.shop_id
        for payment in bill.payments:
            payment.shop_id = bill.shop_id

    def _serialize(self, bill: Bill) -> BillRead:
        customer = bill.customer
        return BillRead(
            id=bill.id,
            bill_number=bill.bill_number,
            customer_id=bill.customer_id,
            visit_id=bill.visit_id,
            dispensing_order_id=bill.dispensing_order_id,
            contact_lens_order_id=bill.contact_lens_order_id,
            customer_name_snapshot=bill.customer_name_snapshot,
            product_name=bill.product_name,
            frame_name=bill.frame_name,
            whole_price=bill.whole_price,
            discount=bill.discount,
            final_price=bill.final_price,
            paid_amount=bill.paid_amount,
            subtotal=bill.subtotal,
            discount_total=bill.discount_total,
            tax_total=bill.tax_total,
            grand_total=bill.grand_total,
            paid_total=bill.paid_total,
            balance_amount=bill.balance_amount,
            payment_mode=bill.payment_mode,
            payment_status=bill.payment_status,
            items=list(bill.items),
            payments=list(bill.payments),
            delivery_date=bill.delivery_date,
            notes=bill.notes,
            pdf_url=self._bill_pdf_download_url(bill.id) if self._has_pdf_reference(bill) else None,
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
            if not self.repo.get_by_bill_number(candidate, shop_key=self.shop_key):
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

    @staticmethod
    def _bill_pdf_download_url(bill_id: int) -> str:
        return f"{settings.api_v1_prefix}/bills/{bill_id}/pdf/download"

    @staticmethod
    def _has_pdf_reference(bill: Bill) -> bool:
        return bool((bill.pdf_file_path and bill.pdf_file_path.strip()) or (bill.pdf_url and bill.pdf_url.strip()))

    def _resolve_bill_pdf_file(self, bill: Bill) -> Path:
        return resolve_media_file_reference(
            bill.pdf_file_path or bill.pdf_url,
            allowed_dir=settings.invoice_media_dir,
            invalid_code="invalid_bill_pdf_file_reference",
            missing_code="bill_pdf_not_found",
            missing_message="Bill PDF file not found on server",
        )

    def _set_bill_pdf_file(self, bill: Bill, file_path: Path) -> str:
        file_reference = build_media_file_reference(file_path)
        bill.pdf_file_path = file_reference
        bill.pdf_url = self._bill_pdf_download_url(bill.id)
        return file_reference

    def _send_bill_whatsapp_document(
        self,
        *,
        bill: Bill,
        customer: Customer,
        actor: User,
        raise_on_error: bool,
    ) -> WhatsAppSendResult:
        if not self._has_pdf_reference(bill):
            raise AppException(status_code=422, code="bill_pdf_missing", message="Bill PDF has not been generated")

        pdf_file = self._resolve_bill_pdf_file(bill)
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
        if not self._has_pdf_reference(bill):
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

        pdf_file = self._resolve_bill_pdf_file(bill)
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
            generated = self.invoice_pdf_service.generate_invoice_pdf(
                bill=bill,
                staff_name=actor.full_name or actor.email,
            )
            pdf_reference = self._set_bill_pdf_file(bill, generated.file_path)
            bill.updated_by = actor.id
            self.repo.save(bill)
            self.audit_service.log(
                actor_user_id=actor.id,
                action=action,
                entity_type="bill",
                entity_id=str(bill.id),
                new_values={"pdf_file_path": pdf_reference, "pdf_url": bill.pdf_url},
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

    def get_pdf_file_for_download(self, bill_id: int, actor: User) -> Path:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")

        bill = self.repo.get_by_id(bill_id, shop_key=self.shop_key)
        if not bill:
            raise AppException(status_code=404, code="bill_not_found", message="Bill not found")

        if not self._has_pdf_reference(bill):
            raise AppException(status_code=422, code="bill_pdf_missing", message="Bill PDF has not been generated")

        return self._resolve_bill_pdf_file(bill)

    def _resolve_workflow_context(
        self,
        *,
        customer_id: int,
        visit_id: int | None,
        dispensing_order_id: int | None,
        contact_lens_order_id: int | None,
    ) -> tuple[int | None, int | None, int | None]:
        visit = None
        if visit_id is not None:
            visit = self.visit_repo.get_by_id(visit_id, shop_key=self.shop_key)
            if not visit:
                raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
            if visit.customer_id != customer_id:
                raise AppException(
                    status_code=422,
                    code="bill_context_customer_mismatch",
                    message="The selected visit belongs to a different patient",
                )

        if dispensing_order_id is not None and contact_lens_order_id is not None:
            raise AppException(
                status_code=422,
                code="bill_multiple_order_contexts",
                message="A bill can belong to either a spectacle order or a contact lens order",
            )

        if dispensing_order_id is None and contact_lens_order_id is None:
            return visit_id, None, None

        if contact_lens_order_id is not None:
            order = self.contact_lens_repo.get_order_by_id(contact_lens_order_id, shop_key=self.shop_key)
            if not order:
                raise AppException(
                    status_code=404,
                    code="contact_lens_order_not_found",
                    message="Contact lens order not found",
                )
            if order.customer_id != customer_id:
                raise AppException(
                    status_code=422,
                    code="bill_context_customer_mismatch",
                    message="The contact lens order belongs to a different patient",
                )
            if visit is not None and order.visit_id != visit.id:
                raise AppException(
                    status_code=422,
                    code="bill_context_visit_mismatch",
                    message="The contact lens order belongs to a different visit",
                )
            if self.repo.get_active_by_contact_lens_order(order.id, shop_key=self.shop_key):
                raise AppException(
                    status_code=409,
                    code="contact_lens_order_already_billed",
                    message="This contact lens order already has an active bill",
                )
            return order.visit_id, None, order.id

        assert dispensing_order_id is not None
        order = self.dispensing_order_repo.get_by_id(dispensing_order_id, shop_key=self.shop_key)
        if not order:
            raise AppException(
                status_code=404,
                code="dispensing_order_not_found",
                message="Dispensing order not found",
            )
        if order.customer_id != customer_id:
            raise AppException(
                status_code=422,
                code="bill_context_customer_mismatch",
                message="The dispensing order belongs to a different patient",
            )
        if visit is not None and order.visit_id != visit.id:
            raise AppException(
                status_code=422,
                code="bill_context_visit_mismatch",
                message="The dispensing order belongs to a different visit",
            )
        if self.repo.get_active_by_dispensing_order(order.id, shop_key=self.shop_key):
            raise AppException(
                status_code=409,
                code="dispensing_order_already_billed",
                message="This dispensing order already has an active bill",
            )
        return order.visit_id, order.id, None

    def create_bill(self, payload: BillCreate, actor: User) -> BillRead:
        customer = self.customer_repo.get_by_id(payload.customer_id, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        visit_id, dispensing_order_id, contact_lens_order_id = self._resolve_workflow_context(
            customer_id=customer.id,
            visit_id=payload.visit_id,
            dispensing_order_id=payload.dispensing_order_id,
            contact_lens_order_id=payload.contact_lens_order_id,
        )

        items_data = self._resolve_items_for_create(payload)
        payments_data = self._resolve_payments_for_create(payload)
        tax_total = self._to_money(payload.tax_total)

        bill: Bill | None = None

        for _ in range(5):
            bill_number = self._generate_bill_number()
            bill = Bill(
                bill_number=bill_number,
                customer_id=customer.id,
                visit_id=visit_id,
                dispensing_order_id=dispensing_order_id,
                contact_lens_order_id=contact_lens_order_id,
                customer_name_snapshot=customer.name,
                product_name="",
                frame_name=None,
                whole_price=Decimal("0.00"),
                discount=Decimal("0.00"),
                final_price=Decimal("0.00"),
                paid_amount=Decimal("0.00"),
                balance_amount=Decimal("0.00"),
                subtotal=Decimal("0.00"),
                discount_total=Decimal("0.00"),
                tax_total=Decimal("0.00"),
                grand_total=Decimal("0.00"),
                paid_total=Decimal("0.00"),
                payment_mode=payload.payment_mode or PaymentMode.CASH,
                payment_status=PaymentStatus.PENDING,
                delivery_date=payload.delivery_date,
                notes=payload.notes,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self._apply_bill_components(
                bill=bill,
                items_data=items_data,
                payments_data=payments_data,
                tax_total=tax_total,
                frame_name=payload.frame_name,
            )

            try:
                self.repo.create(bill)
                self._sync_child_shop_ids(bill)
                self.audit_service.log(
                    actor_user_id=actor.id,
                    action="bill.create",
                    entity_type="bill",
                    entity_id=str(bill.id),
                    new_values={
                        "bill_number": bill.bill_number,
                        "customer_id": bill.customer_id,
                        "visit_id": bill.visit_id,
                        "dispensing_order_id": bill.dispensing_order_id,
                        "contact_lens_order_id": bill.contact_lens_order_id,
                        "grand_total": str(bill.grand_total),
                        "paid_total": str(bill.paid_total),
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
                if "dispensing_order" in str(exc).lower():
                    raise AppException(
                        status_code=409,
                        code="dispensing_order_already_billed",
                        message="This dispensing order already has an active bill",
                    ) from exc
                if "contact_lens_order" in str(exc).lower():
                    raise AppException(
                        status_code=409,
                        code="contact_lens_order_already_billed",
                        message="This contact lens order already has an active bill",
                    ) from exc
                raise AppException(status_code=409, code="bill_create_conflict", message="Unable to create bill") from exc

        if bill is None or bill.id is None:
            raise AppException(status_code=500, code="bill_create_failed", message="Unable to create bill")

        self._try_auto_generate_pdf(bill=bill, actor=actor, action="bill.generate_pdf.auto")

        persisted_bill = self.repo.get_by_id(bill.id, shop_key=self.shop_key)
        if persisted_bill and self._has_pdf_reference(persisted_bill):
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
            "subtotal": str(bill.subtotal),
            "discount_total": str(bill.discount_total),
            "tax_total": str(bill.tax_total),
            "grand_total": str(bill.grand_total),
            "paid_amount": str(bill.paid_amount),
            "paid_total": str(bill.paid_total),
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

        items_data = self._resolve_items_for_update(bill=bill, payload=payload, update_data=update_data)
        payments_data = self._resolve_payments_for_update(bill=bill, payload=payload, update_data=update_data)
        tax_total = self._to_money(update_data.get("tax_total", bill.tax_total))

        bill.payment_mode = update_data.get("payment_mode", bill.payment_mode)
        self._apply_bill_components(
            bill=bill,
            items_data=items_data,
            payments_data=payments_data,
            tax_total=tax_total,
            frame_name=update_data.get("frame_name", bill.frame_name),
        )
        bill.delivery_date = update_data.get("delivery_date", bill.delivery_date)
        bill.notes = update_data.get("notes", bill.notes)
        bill.updated_by = actor.id

        try:
            self.repo.save(bill)
            self._sync_child_shop_ids(bill)
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
                    "subtotal": str(bill.subtotal),
                    "discount_total": str(bill.discount_total),
                    "tax_total": str(bill.tax_total),
                    "grand_total": str(bill.grand_total),
                    "paid_total": str(bill.paid_total),
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

        generated = self.invoice_pdf_service.generate_invoice_pdf(
            bill=bill,
            staff_name=actor.full_name or actor.email,
        )

        pdf_reference = self._set_bill_pdf_file(bill, generated.file_path)
        bill.updated_by = actor.id

        try:
            self.repo.save(bill)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="bill.generate_pdf",
                entity_type="bill",
                entity_id=str(bill.id),
                new_values={"pdf_file_path": pdf_reference, "pdf_url": bill.pdf_url},
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

        if not self._has_pdf_reference(bill):
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

        if not self._has_pdf_reference(bill):
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
