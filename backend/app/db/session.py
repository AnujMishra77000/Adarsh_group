from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import TokenDecodeError, decode_jwt_token
from app.db.tenant import tenant_db_manager


def _extract_shop_code_from_host(host_header: str | None) -> str | None:
    if not host_header:
        return None

    host_value = host_header.strip().lower()
    if ":" in host_value:
        host_value = host_value.split(":", 1)[0]
    if not host_value:
        return None

    if host_value in tenant_db_manager.shop_codes:
        return host_value

    segments = host_value.split(".")
    if not segments:
        return None

    candidate = segments[0].strip().lower()
    if candidate in tenant_db_manager.shop_codes:
        return candidate
    return None


def _extract_shop_code_from_authorization(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None

    prefix = "bearer "
    raw = authorization_header.strip()
    if len(raw) <= len(prefix) or raw[: len(prefix)].lower() != prefix:
        return None

    token = raw[len(prefix) :].strip()
    if not token:
        return None

    try:
        decoded = decode_jwt_token(token)
    except TokenDecodeError:
        return None

    shop_code = decoded.get("shop_code")
    if isinstance(shop_code, str) and shop_code.strip():
        return shop_code.strip().lower()
    return None


def resolve_shop_code(request: Request, explicit_shop_code: str | None = None, *, required: bool = True) -> str | None:
    if explicit_shop_code and explicit_shop_code.strip():
        shop_code = explicit_shop_code.strip().lower()
    else:
        header_shop = request.headers.get("x-shop-code") or request.headers.get("x-shop-key")
        token_shop = _extract_shop_code_from_authorization(request.headers.get("authorization"))
        host_shop = _extract_shop_code_from_host(request.headers.get("host"))
        shop_code = header_shop or token_shop or host_shop

    if not shop_code:
        if required:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shop context is required")
        return None

    try:
        validated = tenant_db_manager.validate_shop_code(shop_code)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    request.state.shop_code = validated
    return validated


def get_current_shop(request: Request) -> str:
    existing = getattr(request.state, "shop_code", None)
    if isinstance(existing, str) and existing.strip():
        return tenant_db_manager.validate_shop_code(existing)
    resolved = resolve_shop_code(request=request, required=True)
    assert resolved is not None
    return resolved


def get_tenant_db(shop_code: str) -> Session:
    validated_shop = tenant_db_manager.validate_shop_code(shop_code)
    return tenant_db_manager.get_session(validated_shop)


def get_db(request: Request, shop_code: str = Depends(get_current_shop)) -> Generator[Session, None, None]:
    db = get_tenant_db(shop_code)
    request.state.db_session = db
    try:
        yield db
    finally:
        request.state.db_session = None
        db.close()
