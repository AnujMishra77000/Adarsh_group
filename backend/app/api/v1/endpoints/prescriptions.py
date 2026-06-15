from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionListResponse,
    PrescriptionPdfResponse,
    PrescriptionRead,
    PrescriptionSendVendorRequest,
    PrescriptionSendVendorResponse,
    PrescriptionUpdate,
)
from app.services.prescription_service import PrescriptionService

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.get("", response_model=PrescriptionListResponse)
def list_prescriptions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    customer_id: int | None = Query(default=None),
    customer_business_id: str | None = Query(default=None),
    contact_no: str | None = Query(default=None),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> PrescriptionListResponse:
    _ = current_user
    service = PrescriptionService(db, shop_key=shop_key)
    return service.list_prescriptions(
        page=page,
        page_size=page_size,
        customer_pk=customer_id,
        customer_business_id=customer_business_id,
        contact_no=contact_no,
    )


@router.post("", response_model=PrescriptionRead, status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> PrescriptionRead:
    service = PrescriptionService(db, shop_key=shop_key)
    return service.create_prescription(payload=payload, actor=current_user)


@router.get("/customer/{customer_id}", response_model=list[PrescriptionRead])
def list_customer_prescriptions(
    customer_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> list[PrescriptionRead]:
    _ = current_user
    service = PrescriptionService(db, shop_key=shop_key)
    return service.list_by_customer(customer_pk=customer_id)


@router.get("/{prescription_id}", response_model=PrescriptionRead)
def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> PrescriptionRead:
    _ = current_user
    service = PrescriptionService(db, shop_key=shop_key)
    return service.get_prescription(prescription_id=prescription_id)


@router.put("/{prescription_id}", response_model=PrescriptionRead)
def update_prescription(
    prescription_id: int,
    payload: PrescriptionUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> PrescriptionRead:
    service = PrescriptionService(db, shop_key=shop_key)
    return service.update_prescription(prescription_id=prescription_id, payload=payload, actor=current_user)


@router.delete("/{prescription_id}", response_model=MessageResponse)
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    service = PrescriptionService(db, shop_key=shop_key)
    service.delete_prescription(prescription_id=prescription_id, actor=current_user)
    return MessageResponse(message="Prescription deleted successfully")


@router.post("/{prescription_id}/pdf", response_model=PrescriptionPdfResponse)
def generate_prescription_pdf(
    prescription_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> PrescriptionPdfResponse:
    service = PrescriptionService(db, shop_key=shop_key)
    return service.generate_pdf(prescription_id=prescription_id, actor=current_user)


@router.post("/{prescription_id}/send-vendor", response_model=PrescriptionSendVendorResponse)
def send_prescription_to_vendor(
    prescription_id: int,
    payload: PrescriptionSendVendorRequest,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> PrescriptionSendVendorResponse:
    service = PrescriptionService(db, shop_key=shop_key)
    return service.send_to_vendor(prescription_id=prescription_id, payload=payload, actor=current_user)
