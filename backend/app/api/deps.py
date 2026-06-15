from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenDecodeError, decode_jwt_token
from app.db.session import get_current_shop, get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_shop_key(shop_code: str = Depends(get_current_shop)) -> str:
    return shop_code


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    shop_key: str = Depends(get_current_shop),
) -> User:
    try:
        payload = decode_jwt_token(token)
    except TokenDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token payload")

    token_shop_code = str(payload.get("shop_code") or "").strip().lower()
    if not token_shop_code or token_shop_code != shop_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token shop context")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token subject") from exc

    user = UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not active")
    if user.shop_key != shop_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token shop context")

    token_role = str(payload.get("role") or "").strip().lower()
    if token_role and user.role.value != token_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role context")

    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    role_values = {role.value for role in roles}

    def _dependency(current_user: User = Depends(get_current_user), shop_key: str = Depends(get_shop_key)) -> User:
        if current_user.role.value not in role_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        if current_user.shop_key != shop_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid shop access")

        return current_user

    return _dependency
