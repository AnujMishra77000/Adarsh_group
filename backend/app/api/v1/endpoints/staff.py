from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.staff import StaffCreateRequest, StaffListResponse, StaffLoginActivityListResponse, StaffRead
from app.services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=StaffListResponse)
def list_staff(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> StaffListResponse:
    _ = current_user
    service = StaffService(db, shop_key=shop_key)
    return service.list_staff(page=page, page_size=page_size, search=search, is_active=is_active)


@router.post("", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> StaffRead:
    service = StaffService(db, shop_key=shop_key)
    return service.create_staff(
        payload=payload,
        actor=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.delete("/{staff_user_id}", response_model=MessageResponse)
def delete_staff(
    staff_user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    service = StaffService(db, shop_key=shop_key)
    return service.delete_staff(
        staff_user_id=staff_user_id,
        actor=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/login-activities", response_model=StaffLoginActivityListResponse)
def staff_login_activities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    staff_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> StaffLoginActivityListResponse:
    _ = current_user
    service = StaffService(db, shop_key=shop_key)
    return service.list_login_activities(page=page, page_size=page_size, staff_user_id=staff_user_id)
