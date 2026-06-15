from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.bill import BillCreate, BillListResponse, BillRead, BillUpdate
from app.schemas.common import MessageResponse
from app.services.bill_service import BillService

router = APIRouter(prefix="/bills", tags=["bills"])


@router.get("", response_model=BillListResponse)
def list_bills(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> BillListResponse:
    _ = current_user
    service = BillService(db, shop_key=shop_key)
    return service.list_bills(page=page, page_size=page_size, search=search, customer_pk=customer_id)


@router.post("", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> BillRead:
    service = BillService(db, shop_key=shop_key)
    return service.create_bill(payload=payload, actor=current_user)


@router.get("/{bill_id}", response_model=BillRead)
def get_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> BillRead:
    _ = current_user
    service = BillService(db, shop_key=shop_key)
    return service.get_bill(bill_id=bill_id)


@router.put("/{bill_id}", response_model=BillRead)
def update_bill(
    bill_id: int,
    payload: BillUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> BillRead:
    service = BillService(db, shop_key=shop_key)
    return service.update_bill(bill_id=bill_id, payload=payload, actor=current_user)


@router.delete("/{bill_id}", response_model=MessageResponse)
def delete_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    service = BillService(db, shop_key=shop_key)
    service.delete_bill(bill_id=bill_id, actor=current_user)
    return MessageResponse(message="Bill deleted successfully")


@router.post("/{bill_id}/generate-pdf", response_model=BillRead)
def generate_bill_pdf(
    bill_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> BillRead:
    service = BillService(db, shop_key=shop_key)
    return service.generate_pdf(bill_id=bill_id, actor=current_user)


@router.post("/{bill_id}/send-email", response_model=MessageResponse)
def send_bill_email(
    bill_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> MessageResponse:
    service = BillService(db, shop_key=shop_key)
    message = service.send_email(bill_id=bill_id, actor=current_user)
    return MessageResponse(message=message)


@router.post("/{bill_id}/send-whatsapp", response_model=MessageResponse)
def send_bill_whatsapp(
    bill_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> MessageResponse:
    service = BillService(db, shop_key=shop_key)
    message = service.send_whatsapp(bill_id=bill_id, actor=current_user)
    return MessageResponse(message=message)
