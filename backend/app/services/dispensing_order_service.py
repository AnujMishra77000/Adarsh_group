from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_definition
from app.db.shop_scope import assign_shop_scope
from app.models.dispensing_order import DispensingOrder, OrderStatusEvent
from app.models.enums import DispensingOrderStatus, PrescriptionVersionStatus, WhatsAppModuleType, WhatsAppStatus
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_prescription import VisitPrescription
from app.repositories.dispensing_order_repository import DispensingOrderRepository
from app.repositories.vendor_repository import VendorRepository
from app.repositories.visit_prescription_repository import VisitPrescriptionRepository
from app.repositories.visit_repository import VisitRepository
from app.schemas.dispensing_order import (
    DispensingMeasurements,
    DispensingOrderContext,
    DispensingOrderDocumentResponse,
    DispensingOrderDraftUpdate,
    DispensingOrderRead,
    DispensingOrderSendVendorRequest,
    DispensingOrderSendVendorResponse,
    DispensingOrderStatusUpdate,
    FrameSelection,
    LensSpecification,
)
from app.services.audit_service import AuditService
from app.services.dispensing_order_pdf_service import DispensingOrderPdfService
from app.services.document_file_service import build_media_file_reference, resolve_media_file_reference
from app.services.whatsapp_service import WhatsAppService


class DispensingOrderService:
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
        DispensingOrderStatus.READY_FOR_VENDOR: {DispensingOrderStatus.DRAFT, DispensingOrderStatus.CANCELLED},
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
        self.repo = DispensingOrderRepository(db)
        self.visit_repo = VisitRepository(db)
        self.prescription_repo = VisitPrescriptionRepository(db)
        self.vendor_repo = VendorRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)
        self.pdf_service = DispensingOrderPdfService()
        self.whatsapp_service = WhatsAppService(db, shop_key=shop_key)

    def _ensure_visit(self, visit_id: int, actor: User) -> Visit:
        if actor.shop_key != self.shop_key:
            raise AppException(status_code=403, code="invalid_shop_access", message="Invalid shop access")
        visit = self.visit_repo.get_by_id(visit_id, shop_key=self.shop_key)
        if not visit:
            raise AppException(status_code=404, code="visit_not_found", message="Visit not found")
        return visit

    def _current_prescription(self, visit_id: int) -> VisitPrescription | None:
        return self.prescription_repo.get_current(visit_id, shop_key=self.shop_key)

    @staticmethod
    def _order_reference() -> str:
        return f"DO-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"

    @staticmethod
    def _serialize(order: DispensingOrder) -> DispensingOrderRead:
        is_delayed = bool(
            order.expected_delivery_date
            and order.expected_delivery_date < date.today()
            and order.status not in {DispensingOrderStatus.DELIVERED, DispensingOrderStatus.CANCELLED}
        )
        return DispensingOrderRead(
            id=order.id,
            visit_id=order.visit_id,
            customer_id=order.customer_id,
            prescription_id=order.prescription_id,
            prescription_version_number=order.prescription.version_number,
            vendor_id=order.vendor_id,
            vendor_name=order.vendor.vendor_name if order.vendor else None,
            order_reference=order.order_reference,
            status=order.status,
            frame=FrameSelection.model_validate(order.frame_data or {}),
            measurements=DispensingMeasurements.model_validate(order.measurement_data or {}),
            lens=LensSpecification.model_validate(order.lens_data or {}),
            manufacturing_instructions=order.manufacturing_instructions,
            has_vendor_document=bool(order.vendor_document_file_path),
            sent_by=order.sent_by,
            sent_at=order.sent_at,
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

    def _record_status_event(
        self,
        order: DispensingOrder,
        *,
        event: str,
        status: DispensingOrderStatus,
        actor: User,
        previous_status: DispensingOrderStatus | None = None,
        notes: str | None = None,
    ) -> None:
        item = OrderStatusEvent(
            shop_key=self.shop_key,
            dispensing_order_id=order.id,
            event=event,
            previous_status=previous_status.value if previous_status else None,
            status=status.value,
            user_id=actor.id,
            notes=notes,
        )
        assign_shop_scope(item, self.db, self.shop_key)
        self.db.add(item)
        self.db.flush()

    def _get_order(self, visit_id: int) -> DispensingOrder:
        order = self.repo.get_by_visit(visit_id, self.shop_key)
        if not order:
            raise AppException(
                status_code=404,
                code="dispensing_order_not_found",
                message="Dispensing order not found",
            )
        return order

    def _validate_vendor(self, vendor_id: int | None):
        if vendor_id is None:
            return None
        vendor = self.vendor_repo.get_by_id(vendor_id, shop_key=self.shop_key)
        if not vendor:
            raise AppException(status_code=404, code="vendor_not_found", message="Vendor not found")
        if not vendor.is_active:
            raise AppException(status_code=422, code="vendor_inactive", message="Vendor is not active")
        return vendor

    def _require_current_link(self, order: DispensingOrder) -> VisitPrescription:
        current = self._current_prescription(order.visit_id)
        if not current:
            raise AppException(
                status_code=422,
                code="finalized_prescription_required",
                message="A finalized prescription is required for this spectacle order",
            )
        if order.prescription_id != current.id or order.prescription.status != PrescriptionVersionStatus.FINALIZED:
            raise AppException(
                status_code=409,
                code="dispensing_order_prescription_stale",
                message="The order uses an older prescription version. Relink it explicitly before continuing.",
            )
        return current

    def get_context(self, visit_id: int, actor: User) -> DispensingOrderContext:
        self._ensure_visit(visit_id, actor)
        current = self._current_prescription(visit_id)
        order = self.repo.get_by_visit(visit_id, self.shop_key)
        return DispensingOrderContext(
            visit_id=visit_id,
            current_prescription_id=current.id if current else None,
            current_prescription_version_number=current.version_number if current else None,
            order=self._serialize(order) if order else None,
            is_prescription_stale=bool(order and (not current or order.prescription_id != current.id)),
        )

    def save_draft(self, visit_id: int, payload: DispensingOrderDraftUpdate, actor: User) -> DispensingOrderRead:
        visit = self._ensure_visit(visit_id, actor)
        vendor = self._validate_vendor(payload.vendor_id)
        order = self.repo.get_by_visit(visit_id, self.shop_key)
        if order is None:
            current = self._current_prescription(visit_id)
            if not current:
                raise AppException(
                    status_code=422,
                    code="finalized_prescription_required",
                    message="Finalize a prescription before creating the spectacle order",
                )
            order = DispensingOrder(
                shop_key=self.shop_key,
                visit_id=visit.id,
                customer_id=visit.customer_id,
                prescription_id=current.id,
                vendor_id=vendor.id if vendor else None,
                order_reference=self._order_reference(),
                status=DispensingOrderStatus.DRAFT,
                created_by=actor.id,
                updated_by=actor.id,
                expected_delivery_date=payload.expected_delivery_date,
            )
            action = "dispensing_order.create"
        else:
            if order.status not in self.EDITABLE_STATUSES:
                raise AppException(
                    status_code=409,
                    code="dispensing_order_read_only",
                    message="This order can no longer be edited",
                )
            order.vendor_id = vendor.id if vendor else None
            order.updated_by = actor.id
            action = "dispensing_order.update"

        order.frame_data = payload.frame.model_dump(mode="json", exclude_none=True)
        order.measurement_data = payload.measurements.model_dump(mode="json", exclude_none=True)
        order.lens_data = payload.lens.model_dump(mode="json", exclude_none=True)
        order.manufacturing_instructions = payload.manufacturing_instructions
        order.expected_delivery_date = payload.expected_delivery_date
        order.vendor_document_file_path = None

        try:
            is_new = order.id is None
            if is_new:
                self.repo.create(order)
                self._record_status_event(
                    order,
                    event="spectacle_ordered",
                    status=DispensingOrderStatus.DRAFT,
                    actor=actor,
                    notes="Spectacle order created",
                )
            else:
                self.repo.save(order)
            self.audit_service.log(
                actor_user_id=actor.id,
                action=action,
                entity_type="dispensing_order",
                entity_id=str(order.id),
                new_values={
                    "visit_id": visit.id,
                    "prescription_id": order.prescription_id,
                    "vendor_id": order.vendor_id,
                    "status": order.status.value,
                },
            )
            self.db.commit()
            order = self._get_order(visit_id)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="dispensing_order_conflict",
                message="Unable to save the dispensing order",
            ) from exc
        return self._serialize(order)

    def relink_current_prescription(self, visit_id: int, actor: User) -> DispensingOrderRead:
        self._ensure_visit(visit_id, actor)
        order = self._get_order(visit_id)
        if order.status not in self.EDITABLE_STATUSES:
            raise AppException(
                status_code=409,
                code="dispensing_order_relink_not_allowed",
                message="Only draft or ready orders can be relinked",
            )
        current = self._current_prescription(visit_id)
        if not current:
            raise AppException(
                status_code=422,
                code="finalized_prescription_required",
                message="No current finalized prescription is available",
            )
        previous_id = order.prescription_id
        order.prescription_id = current.id
        order.vendor_document_file_path = None
        order.updated_by = actor.id
        self.repo.save(order)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="dispensing_order.relink_prescription",
            entity_type="dispensing_order",
            entity_id=str(order.id),
            old_values={"prescription_id": previous_id},
            new_values={"prescription_id": current.id, "version_number": current.version_number},
        )
        self.db.commit()
        return self._serialize(self._get_order(visit_id))

    def change_status(
        self,
        visit_id: int,
        payload: DispensingOrderStatusUpdate,
        actor: User,
    ) -> DispensingOrderRead:
        self._ensure_visit(visit_id, actor)
        order = self._get_order(visit_id)
        if payload.status == order.status:
            return self._serialize(order)
        if payload.status not in self.STATUS_TRANSITIONS[order.status]:
            raise AppException(
                status_code=409,
                code="dispensing_order_invalid_status_transition",
                message=f"Cannot change order from {order.status.value} to {payload.status.value}",
            )
        if payload.status == DispensingOrderStatus.READY_FOR_VENDOR:
            self._require_current_link(order)
            if not order.lens_data.get("lens_type"):
                raise AppException(
                    status_code=422,
                    code="dispensing_order_lens_type_required",
                    message="Select a lens type before marking the order ready",
                )
        previous = order.status
        order.status = payload.status
        order.updated_by = actor.id
        if payload.status == DispensingOrderStatus.DELIVERED:
            order.delivered_by = actor.id
            order.delivered_at = datetime.now(UTC)
        self.repo.save(order)
        self._record_status_event(
            order,
            event=self.STATUS_EVENTS[payload.status],
            previous_status=previous,
            status=payload.status,
            actor=actor,
            notes=payload.notes,
        )
        self.audit_service.log(
            actor_user_id=actor.id,
            action="dispensing_order.status_change",
            entity_type="dispensing_order",
            entity_id=str(order.id),
            old_values={"status": previous.value},
            new_values={"status": order.status.value},
        )
        self.db.commit()
        return self._serialize(self._get_order(visit_id))

    def _generate_document(self, order: DispensingOrder, actor: User) -> Path:
        self._require_current_link(order)
        shop = get_shop_definition(self.shop_key)
        generated = self.pdf_service.generate_vendor_order_pdf(
            order=order,
            branch_name=shop.display_name if shop else self.shop_key,
        )
        order.vendor_document_file_path = build_media_file_reference(generated.file_path)
        order.updated_by = actor.id
        self.repo.save(order)
        return generated.file_path

    @staticmethod
    def _document_download_url(visit_id: int) -> str:
        return f"/api/v1/visits/{visit_id}/dispensing-order/vendor-document/download"

    def generate_vendor_document(self, visit_id: int, actor: User) -> DispensingOrderDocumentResponse:
        self._ensure_visit(visit_id, actor)
        order = self._get_order(visit_id)
        file_path = self._generate_document(order, actor)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="dispensing_order.generate_vendor_document",
            entity_type="dispensing_order",
            entity_id=str(order.id),
            new_values={"file_path": build_media_file_reference(file_path)},
        )
        self.db.commit()
        return DispensingOrderDocumentResponse(
            order_id=order.id,
            download_url=self._document_download_url(visit_id),
        )

    def get_vendor_document_for_download(self, visit_id: int, actor: User) -> Path:
        self._ensure_visit(visit_id, actor)
        order = self._get_order(visit_id)
        self._require_current_link(order)
        return resolve_media_file_reference(
            order.vendor_document_file_path,
            allowed_dir=settings.vendor_order_media_dir,
            invalid_code="invalid_dispensing_order_document_reference",
            missing_code="dispensing_order_document_missing",
            missing_message="Vendor order document has not been generated",
        )

    def send_to_vendor(
        self,
        visit_id: int,
        payload: DispensingOrderSendVendorRequest,
        actor: User,
    ) -> DispensingOrderSendVendorResponse:
        self._ensure_visit(visit_id, actor)
        order = self._get_order(visit_id)
        self._require_current_link(order)
        if order.status != DispensingOrderStatus.READY_FOR_VENDOR:
            raise AppException(
                status_code=409,
                code="dispensing_order_not_ready",
                message="Mark the order ready for vendor before sending",
            )
        vendor = self._validate_vendor(order.vendor_id)
        if vendor is None:
            raise AppException(
                status_code=422,
                code="dispensing_order_vendor_required",
                message="Select a vendor before sending",
            )
        if not order.lens_data.get("lens_type"):
            raise AppException(
                status_code=422,
                code="dispensing_order_lens_type_required",
                message="Select a lens type before sending",
            )

        file_path = self._generate_document(order, actor)
        media_id = self.whatsapp_service.upload_media(file_path)
        result = self.whatsapp_service.send_document_message(
            module_type=WhatsAppModuleType.DISPENSING_ORDER,
            reference_id=order.id,
            customer_id=None,
            vendor_id=vendor.id,
            recipient_no=vendor.whatsapp_no,
            media_id=media_id,
            document_name=file_path.name,
            caption=payload.caption or f"Spectacle order {order.order_reference}",
            raise_on_error=False,
        )
        self.audit_service.log(
            actor_user_id=actor.id,
            action="dispensing_order.send_vendor_whatsapp",
            entity_type="dispensing_order",
            entity_id=str(order.id),
            metadata_json={
                "vendor_id": vendor.id,
                "whatsapp_log_id": result.whatsapp_log_id,
                "provider_message_id": result.provider_message_id,
                "status": result.status.value,
                "error_message": result.error_message,
            },
        )
        if result.status != WhatsAppStatus.SENT:
            self.db.commit()
            raise AppException(
                status_code=502,
                code="dispensing_order_vendor_send_failed",
                message=result.error_message or "Failed to send spectacle order to vendor",
            )

        order.status = DispensingOrderStatus.SENT_TO_VENDOR
        order.sent_by = actor.id
        order.sent_at = datetime.now(UTC)
        order.updated_by = actor.id
        self.repo.save(order)
        self._record_status_event(
            order,
            event="vendor_order_sent",
            previous_status=DispensingOrderStatus.READY_FOR_VENDOR,
            status=DispensingOrderStatus.SENT_TO_VENDOR,
            actor=actor,
            notes=payload.caption,
        )
        self.db.commit()
        return DispensingOrderSendVendorResponse(
            message="Spectacle order sent to vendor on WhatsApp",
            whatsapp_log_id=result.whatsapp_log_id,
            provider_message_id=result.provider_message_id,
        )
