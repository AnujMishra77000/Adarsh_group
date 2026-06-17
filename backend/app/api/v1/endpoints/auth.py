from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_key
from app.core.security import TokenDecodeError, decode_jwt_token
from app.core.config import settings
from app.db.session import get_db, resolve_shop_code
from app.models.user import User
from app.schemas.auth import (
    AdminRegisterRequest,
    AuthPublicConfigResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthPublicConfigResponse)
def auth_config() -> AuthPublicConfigResponse:
    return AuthPublicConfigResponse(admin_registration_enabled=settings.admin_registration_enabled)


@router.post("/admin/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_admin(
    payload: AdminRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    shop_key = resolve_shop_code(request=request, explicit_shop_code=payload.shop_code, required=True)
    service = AuthService(db)
    return service.register_admin(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        shop_key=shop_key,
    )


@router.post("/login", response_model=TokenPairResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    shop_key = resolve_shop_code(request=request, explicit_shop_code=payload.shop_code, required=True)
    service = AuthService(db)
    return service.login(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        shop_key=shop_key,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    inferred_shop = payload.shop_code
    if not inferred_shop:
        try:
            inferred_shop = str(decode_jwt_token(payload.refresh_token).get("shop_code") or "").strip() or None
        except TokenDecodeError:
            inferred_shop = None

    shop_key = resolve_shop_code(request=request, explicit_shop_code=inferred_shop, required=False)
    if not shop_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    service = AuthService(db)
    return service.refresh_tokens(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        shop_key=shop_key,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    inferred_shop = payload.shop_code
    if not inferred_shop:
        try:
            inferred_shop = str(decode_jwt_token(payload.refresh_token).get("shop_code") or "").strip() or None
        except TokenDecodeError:
            inferred_shop = None

    shop_key = resolve_shop_code(request=request, explicit_shop_code=inferred_shop, required=False)
    if not shop_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    service = AuthService(db)
    return service.logout(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        shop_key=shop_key,
    )


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user), shop_key: str = Depends(get_shop_key)) -> User:
    if current_user.shop_key != shop_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid shop access")
    return current_user
