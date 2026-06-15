from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.customer import CustomerCreate, CustomerDetailRead, CustomerListResponse, CustomerRead, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CustomerListResponse:
    _ = current_user
    service = CustomerService(db, shop_key=shop_key)
    return service.list_customers(page=page, page_size=page_size, search=search)


@router.get("/search", response_model=CustomerListResponse)
def search_customers(
    q: str = Query(default="", min_length=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CustomerListResponse:
    _ = current_user
    service = CustomerService(db, shop_key=shop_key)
    return service.list_customers(page=page, page_size=page_size, search=q)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CustomerRead:
    service = CustomerService(db, shop_key=shop_key)
    return service.create_customer(payload=payload, actor=current_user)


@router.get("/{customer_id}", response_model=CustomerDetailRead)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CustomerDetailRead:
    _ = current_user
    service = CustomerService(db, shop_key=shop_key)
    return service.get_customer(customer_pk=customer_id)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> CustomerRead:
    service = CustomerService(db, shop_key=shop_key)
    return service.update_customer(customer_pk=customer_id, payload=payload, actor=current_user)


@router.delete("/{customer_id}", response_model=MessageResponse)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    service = CustomerService(db, shop_key=shop_key)
    service.delete_customer(customer_pk=customer_id, actor=current_user)
    return MessageResponse(message="Customer deleted successfully")
