from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.vendor_repository import VendorRepository
from app.schemas.vendor import VendorCreate, VendorListResponse, VendorRead, VendorUpdate
from app.services.audit_service import AuditService


class VendorService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VendorRepository(db)
        self.audit_service = AuditService(db)

    def list_vendors(
        self,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
    ) -> VendorListResponse:
        items, total = self.repo.list(page=page, page_size=page_size, search=search, is_active=is_active)
        return VendorListResponse(
            items=[VendorRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_vendor(self, payload: VendorCreate, actor: User) -> VendorRead:
        vendor = Vendor(
            vendor_name=payload.vendor_name,
            contact_person=payload.contact_person,
            whatsapp_no=payload.whatsapp_no,
            address=payload.address,
            is_active=payload.is_active,
        )

        try:
            self.repo.create(vendor)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="vendor.create",
                entity_type="vendor",
                entity_id=str(vendor.id),
                new_values={
                    "vendor_name": vendor.vendor_name,
                    "whatsapp_no": vendor.whatsapp_no,
                    "is_active": vendor.is_active,
                },
            )
            self.db.commit()
            self.db.refresh(vendor)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="vendor_create_conflict", message="Unable to create vendor") from exc

        return VendorRead.model_validate(vendor)

    def get_vendor(self, vendor_id: int) -> VendorRead:
        vendor = self.repo.get_by_id(vendor_id)
        if not vendor:
            raise AppException(status_code=404, code="vendor_not_found", message="Vendor not found")
        return VendorRead.model_validate(vendor)

    def update_vendor(self, vendor_id: int, payload: VendorUpdate, actor: User) -> VendorRead:
        vendor = self.repo.get_by_id(vendor_id)
        if not vendor:
            raise AppException(status_code=404, code="vendor_not_found", message="Vendor not found")

        old_values = {
            "vendor_name": vendor.vendor_name,
            "contact_person": vendor.contact_person,
            "whatsapp_no": vendor.whatsapp_no,
            "address": vendor.address,
            "is_active": vendor.is_active,
        }

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vendor, field, value)

        try:
            self.repo.save(vendor)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="vendor.update",
                entity_type="vendor",
                entity_id=str(vendor.id),
                old_values=old_values,
                new_values=update_data,
            )
            self.db.commit()
            self.db.refresh(vendor)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="vendor_update_conflict", message="Unable to update vendor") from exc

        return VendorRead.model_validate(vendor)

    def delete_vendor(self, vendor_id: int, actor: User) -> None:
        vendor = self.repo.get_by_id(vendor_id)
        if not vendor:
            raise AppException(status_code=404, code="vendor_not_found", message="Vendor not found")

        if not vendor.is_active:
            return

        vendor.is_active = False
        self.repo.save(vendor)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="vendor.deactivate",
            entity_type="vendor",
            entity_id=str(vendor.id),
            old_values={"is_active": True},
            new_values={"is_active": False},
        )
        self.db.commit()
