from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.vendor import VendorCreate, VendorListResponse, VendorRead, VendorUpdate
from app.services.vendor_service import VendorService

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=VendorListResponse)
def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VendorListResponse:
    _ = current_user
    service = VendorService(db)
    return service.list_vendors(page=page, page_size=page_size, search=search, is_active=is_active)


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> VendorRead:
    service = VendorService(db)
    return service.create_vendor(payload=payload, actor=current_user)


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VendorRead:
    _ = current_user
    service = VendorService(db)
    return service.get_vendor(vendor_id=vendor_id)


@router.put("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> VendorRead:
    service = VendorService(db)
    return service.update_vendor(vendor_id=vendor_id, payload=payload, actor=current_user)


@router.delete("/{vendor_id}", response_model=MessageResponse)
def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    service = VendorService(db)
    service.delete_vendor(vendor_id=vendor_id, actor=current_user)
    return MessageResponse(message="Vendor deactivated successfully")
