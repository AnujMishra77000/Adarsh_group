from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.prescription import Prescription
from app.models.user import User
from app.models.enums import WhatsAppModuleType, WhatsAppStatus
from app.repositories.customer_repository import CustomerRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionListResponse,
    PrescriptionPdfResponse,
    PrescriptionRead,
    PrescriptionSendVendorRequest,
    PrescriptionSendVendorResponse,
    PrescriptionUpdate,
)
from app.services.audit_service import AuditService
from app.services.prescription_pdf_service import PrescriptionPdfService
from app.services.whatsapp_service import WhatsAppService


class PrescriptionService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.repo = PrescriptionRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.vendor_repo = VendorRepository(db)
        self.audit_service = AuditService(db)
        self.pdf_service = PrescriptionPdfService()
        self.whatsapp_service = WhatsAppService(db)

    def _serialize(self, prescription: Prescription) -> PrescriptionRead:
        customer = prescription.customer
        return PrescriptionRead(
            id=prescription.id,
            customer_id=prescription.customer_id,
            prescription_date=prescription.prescription_date,
            right_sph=prescription.right_sph,
            right_cyl=prescription.right_cyl,
            right_axis=prescription.right_axis,
            right_vn=prescription.right_vn,
            left_sph=prescription.left_sph,
            left_cyl=prescription.left_cyl,
            left_axis=prescription.left_axis,
            left_vn=prescription.left_vn,
            fh=prescription.fh,
            add_power=prescription.add_power,
            pd=prescription.pd,
            notes=prescription.notes,
            created_at=prescription.created_at,
            updated_at=prescription.updated_at,
            created_by=prescription.created_by,
            updated_by=prescription.updated_by,
            is_deleted=prescription.is_deleted,
            customer_name=customer.name if customer else None,
            customer_business_id=customer.customer_id if customer else None,
            customer_contact_no=customer.contact_no if customer else None,
        )

    def _get_prescription_or_404(self, prescription_id: int) -> Prescription:
        prescription = self.repo.get_by_id(prescription_id, shop_key=self.shop_key)
        if not prescription:
            raise AppException(status_code=404, code="prescription_not_found", message="Prescription not found")
        return prescription

    def list_prescriptions(
        self,
        page: int,
        page_size: int,
        customer_pk: int | None,
        customer_business_id: str | None,
        contact_no: str | None,
    ) -> PrescriptionListResponse:
        items, total = self.repo.list(
            page=page,
            page_size=page_size,
            shop_key=self.shop_key,
            customer_pk=customer_pk,
            customer_business_id=customer_business_id,
            contact_no=contact_no,
        )
        return PrescriptionListResponse(
            items=[self._serialize(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_by_customer(self, customer_pk: int) -> list[PrescriptionRead]:
        if not self.customer_repo.get_by_id(customer_pk, shop_key=self.shop_key):
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")
        prescriptions = self.repo.list_for_customer(customer_pk, shop_key=self.shop_key)
        return [self._serialize(item) for item in prescriptions]

    def get_prescription(self, prescription_id: int) -> PrescriptionRead:
        prescription = self._get_prescription_or_404(prescription_id)
        return self._serialize(prescription)

    def create_prescription(self, payload: PrescriptionCreate, actor: User) -> PrescriptionRead:
        customer = self.customer_repo.get_by_id(payload.customer_id, shop_key=self.shop_key)
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        prescription = Prescription(
            customer_id=payload.customer_id,
            prescription_date=payload.prescription_date,
            right_sph=payload.right_sph,
            right_cyl=payload.right_cyl,
            right_axis=payload.right_axis,
            right_vn=payload.right_vn,
            left_sph=payload.left_sph,
            left_cyl=payload.left_cyl,
            left_axis=payload.left_axis,
            left_vn=payload.left_vn,
            fh=payload.fh,
            add_power=payload.add_power,
            pd=payload.pd,
            notes=payload.notes,
            created_by=actor.id,
            updated_by=actor.id,
        )

        try:
            self.repo.create(prescription)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="prescription.create",
                entity_type="prescription",
                entity_id=str(prescription.id),
                new_values={
                    "customer_id": prescription.customer_id,
                    "prescription_date": str(prescription.prescription_date),
                },
            )
            self.db.commit()
            self.db.refresh(prescription)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="prescription_create_conflict",
                message="Unable to create prescription",
            ) from exc

        return self.get_prescription(prescription.id)

    def update_prescription(self, prescription_id: int, payload: PrescriptionUpdate, actor: User) -> PrescriptionRead:
        prescription = self._get_prescription_or_404(prescription_id)

        old_values = {
            "prescription_date": str(prescription.prescription_date),
            "notes": prescription.notes,
        }

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(prescription, field, value)
        prescription.updated_by = actor.id

        try:
            self.repo.save(prescription)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="prescription.update",
                entity_type="prescription",
                entity_id=str(prescription.id),
                old_values=old_values,
                new_values={k: str(v) for k, v in update_data.items()},
            )
            self.db.commit()
            self.db.refresh(prescription)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="prescription_update_conflict",
                message="Unable to update prescription",
            ) from exc

        return self.get_prescription(prescription.id)

    def delete_prescription(self, prescription_id: int, actor: User) -> None:
        prescription = self._get_prescription_or_404(prescription_id)

        if prescription.is_deleted:
            return

        prescription.is_deleted = True
        prescription.updated_by = actor.id
        self.repo.save(prescription)

        self.audit_service.log(
            actor_user_id=actor.id,
            action="prescription.delete",
            entity_type="prescription",
            entity_id=str(prescription.id),
            old_values={"is_deleted": False},
            new_values={"is_deleted": True},
        )
        self.db.commit()

    def generate_pdf(self, prescription_id: int, actor: User) -> PrescriptionPdfResponse:
        prescription = self._get_prescription_or_404(prescription_id)
        customer = prescription.customer
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        generated = self.pdf_service.generate_prescription_pdf(
            prescription=prescription,
            customer=customer,
            staff_name=actor.full_name or actor.email,
        )

        self.audit_service.log(
            actor_user_id=actor.id,
            action="prescription.generate_pdf",
            entity_type="prescription",
            entity_id=str(prescription.id),
            new_values={"pdf_url": generated.public_url},
        )
        self.db.commit()

        return PrescriptionPdfResponse(prescription_id=prescription.id, pdf_url=generated.public_url)

    def send_to_vendor(
        self,
        prescription_id: int,
        payload: PrescriptionSendVendorRequest,
        actor: User,
    ) -> PrescriptionSendVendorResponse:
        prescription = self._get_prescription_or_404(prescription_id)
        customer = prescription.customer
        if not customer:
            raise AppException(status_code=404, code="customer_not_found", message="Customer not found")

        vendor = self.vendor_repo.get_by_id(payload.vendor_id)
        if not vendor:
            raise AppException(status_code=404, code="vendor_not_found", message="Vendor not found")
        if not vendor.is_active:
            raise AppException(status_code=422, code="vendor_inactive", message="Vendor is not active")

        generated = self.pdf_service.generate_prescription_pdf(
            prescription=prescription,
            customer=customer,
            staff_name=actor.full_name or actor.email,
        )

        media_id = self.whatsapp_service.upload_media(generated.file_path)
        caption = payload.caption or (
            f"Prescription for {customer.name} ({customer.customer_id}) - "
            f"{prescription.prescription_date.strftime('%d %b %Y')}"
        )

        result = self.whatsapp_service.send_document_message(
            module_type=WhatsAppModuleType.PRESCRIPTION,
            reference_id=prescription.id,
            customer_id=customer.id,
            vendor_id=vendor.id,
            recipient_no=vendor.whatsapp_no,
            media_id=media_id,
            document_name=generated.file_path.name,
            caption=caption,
            raise_on_error=False,
        )

        self.audit_service.log(
            actor_user_id=actor.id,
            action="prescription.send_vendor_whatsapp",
            entity_type="prescription",
            entity_id=str(prescription.id),
            metadata_json={
                "vendor_id": vendor.id,
                "whatsapp_log_id": result.whatsapp_log_id,
                "provider_message_id": result.provider_message_id,
                "status": result.status.value,
                "error_message": result.error_message,
            },
        )
        self.db.commit()

        if result.status != WhatsAppStatus.SENT:
            raise AppException(
                status_code=502,
                code="prescription_vendor_send_failed",
                message=result.error_message or "Failed to send prescription to vendor",
            )

        return PrescriptionSendVendorResponse(
            message="Prescription sent to vendor on WhatsApp",
            whatsapp_log_id=result.whatsapp_log_id,
            provider_message_id=result.provider_message_id,
        )
