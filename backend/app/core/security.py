from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


class TokenDecodeError(ValueError):
    """Raised when a JWT cannot be decoded or validated."""


def _normalize_secret_for_bcrypt(secret: str) -> bytes:
    """Normalize password/secret bytes for bcrypt compatibility.

    bcrypt only accepts up to 72 input bytes. For longer secrets, hash first with
    SHA-256 and use the hex digest bytes.
    """
    encoded = secret.encode("utf-8")
    if len(encoded) <= 72:
        return encoded
    return hashlib.sha256(encoded).hexdigest().encode("utf-8")


def get_password_hash(password: str) -> str:
    normalized_password = _normalize_secret_for_bcrypt(password)
    hashed = bcrypt.hashpw(normalized_password, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    normalized_password = _normalize_secret_for_bcrypt(plain_password)
    try:
        return bcrypt.checkpw(normalized_password, hashed_password.encode("utf-8"))
    except ValueError:
        return False


def _build_token(subject: str, role: str, token_type: str, expires_delta: timedelta | None, shop_code: str) -> str:
    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "shop_code": shop_code,
        "type": token_type,
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }

    if expires_delta is not None:
        expire = now + expires_delta
        payload["exp"] = int(expire.timestamp())

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str, shop_code: str) -> str:
    expires_delta = None
    if settings.access_token_expire_minutes > 0:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    return _build_token(
        subject=subject,
        role=role,
        shop_code=shop_code,
        token_type="access",
        expires_delta=expires_delta,
    )


def create_refresh_token(subject: str, role: str, shop_code: str) -> str:
    return _build_token(
        subject=subject,
        role=role,
        shop_code=shop_code,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_jwt_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenDecodeError("Invalid or expired token") from exc


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
