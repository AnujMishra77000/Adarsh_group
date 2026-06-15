from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import (
    TokenDecodeError,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AdminRegisterRequest, LoginRequest, LogoutRequest, RefreshTokenRequest, TokenPairResponse
from app.schemas.common import MessageResponse
from app.services.audit_service import AuditService
from app.services.shop_identity_service import find_shop_with_email

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.audit_service = AuditService(db)

    def register_admin(
        self,
        payload: AdminRegisterRequest,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str,
    ) -> User:
        if payload.master_password != settings.admin_master_password:
            raise AppException(status_code=403, code="invalid_master_password", message="Invalid admin master password")

        if self.user_repo.get_by_email(payload.email, shop_key=shop_key):
            raise AppException(status_code=409, code="email_exists", message="Email is already registered")

        conflicting_shop = find_shop_with_email(payload.email, exclude_shop_key=shop_key)
        if conflicting_shop:
            raise AppException(
                status_code=409,
                code="email_exists_other_shop",
                message="Email is already registered in another shop. Use a shop-specific email.",
            )

        try:
            user = self.user_repo.create(
                email=payload.email,
                full_name=payload.full_name,
                password_hash=get_password_hash(payload.password),
                role=UserRole.ADMIN,
                shop_key=shop_key,
                is_active=True,
            )
            self.audit_service.log(
                actor_user_id=user.id,
                action="auth.admin.register",
                entity_type="user",
                entity_id=str(user.id),
                new_values={"email": user.email, "role": user.role.value},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="integrity_error", message="Unable to create admin user") from exc

    def login(
        self,
        payload: LoginRequest,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str,
    ) -> TokenPairResponse:
        login_identifier = payload.email or payload.login_id or ""
        user = self.user_repo.get_by_email(login_identifier, shop_key=shop_key)
        if not user or not verify_password(payload.password, user.password_hash):
            raise AppException(status_code=401, code="invalid_credentials", message="Invalid login credentials")

        conflicting_shop = find_shop_with_email(login_identifier, exclude_shop_key=shop_key)
        if conflicting_shop:
            raise AppException(
                status_code=403,
                code="cross_shop_identity_blocked",
                message="This login id is already linked to another shop. Use shop-specific credentials.",
            )

        if not user.is_active:
            raise AppException(status_code=403, code="user_inactive", message="User account is inactive")

        access_token = create_access_token(subject=str(user.id), role=user.role.value, shop_code=shop_key)
        refresh_token = create_refresh_token(subject=str(user.id), role=user.role.value, shop_code=shop_key)
        refresh_payload = decode_jwt_token(refresh_token)

        try:
            self.refresh_repo.create(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.fromtimestamp(int(refresh_payload["exp"]), tz=UTC),
                created_ip=ip_address,
            )
            user.last_login_at = datetime.now(UTC)
            self.db.add(user)

            self.audit_service.log(
                actor_user_id=user.id,
                action="auth.login",
                entity_type="user",
                entity_id=str(user.id),
                metadata_json={"ip_address": ip_address},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            logger.error("auth.login.persistence_failed", user_id=user.id, error=str(exc))
            raise AppException(status_code=500, code="auth_persist_failed", message="Unable to complete login") from exc

        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)

    def refresh_tokens(
        self,
        payload: RefreshTokenRequest,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str,
    ) -> TokenPairResponse:
        try:
            decoded = decode_jwt_token(payload.refresh_token)
        except TokenDecodeError as exc:
            raise AppException(status_code=401, code="invalid_refresh_token", message="Invalid refresh token") from exc

        if decoded.get("type") != "refresh":
            raise AppException(status_code=401, code="invalid_refresh_token", message="Invalid refresh token type")

        token_hash = hash_token(payload.refresh_token)
        token_record = self.refresh_repo.get_by_hash(token_hash)
        if not token_record:
            raise AppException(status_code=401, code="refresh_not_found", message="Refresh token not recognized")

        now = datetime.now(UTC)
        if token_record.revoked_at is not None or token_record.expires_at <= now:
            raise AppException(status_code=401, code="refresh_expired", message="Refresh token expired or revoked")

        user = self.user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise AppException(status_code=401, code="user_invalid", message="User no longer active")
        if user.shop_key != shop_key:
            raise AppException(status_code=401, code="refresh_shop_mismatch", message="Invalid refresh context")

        if str(user.id) != str(decoded.get("sub")):
            raise AppException(status_code=401, code="refresh_subject_mismatch", message="Refresh token mismatch")
        if str(decoded.get("shop_code", "")).strip().lower() != shop_key:
            raise AppException(status_code=401, code="refresh_shop_mismatch", message="Invalid refresh context")

        new_access_token = create_access_token(subject=str(user.id), role=user.role.value, shop_code=shop_key)
        new_refresh_token = create_refresh_token(subject=str(user.id), role=user.role.value, shop_code=shop_key)
        new_refresh_payload = decode_jwt_token(new_refresh_token)

        try:
            self.refresh_repo.revoke(token_record, revoked_at=now)
            self.refresh_repo.create(
                user_id=user.id,
                token_hash=hash_token(new_refresh_token),
                expires_at=datetime.fromtimestamp(int(new_refresh_payload["exp"]), tz=UTC),
                created_ip=ip_address,
            )

            self.audit_service.log(
                actor_user_id=user.id,
                action="auth.refresh",
                entity_type="user",
                entity_id=str(user.id),
                metadata_json={"rotated": True},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            logger.error("auth.refresh.persistence_failed", user_id=user.id, error=str(exc))
            raise AppException(status_code=500, code="refresh_failed", message="Unable to rotate refresh token") from exc

        return TokenPairResponse(access_token=new_access_token, refresh_token=new_refresh_token)

    def logout(
        self,
        payload: LogoutRequest,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str,
    ) -> MessageResponse:
        try:
            decoded = decode_jwt_token(payload.refresh_token)
        except TokenDecodeError as exc:
            raise AppException(status_code=401, code="invalid_refresh_token", message="Invalid refresh token") from exc

        if decoded.get("type") != "refresh":
            raise AppException(status_code=401, code="invalid_refresh_token", message="Invalid refresh token type")
        if str(decoded.get("shop_code", "")).strip().lower() != shop_key:
            raise AppException(status_code=401, code="logout_shop_mismatch", message="Invalid logout context")

        token_hash = hash_token(payload.refresh_token)
        token_record = self.refresh_repo.get_by_hash(token_hash)

        if token_record and token_record.revoked_at is None:
            user = self.user_repo.get_by_id(token_record.user_id)
            if not user or user.shop_key != shop_key:
                raise AppException(status_code=401, code="logout_shop_mismatch", message="Invalid logout context")

            now = datetime.now(UTC)
            self.refresh_repo.revoke(token_record, revoked_at=now)
            self.audit_service.log(
                actor_user_id=token_record.user_id,
                action="auth.logout",
                entity_type="user",
                entity_id=str(token_record.user_id),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.commit()

        return MessageResponse(message="Logged out successfully")
