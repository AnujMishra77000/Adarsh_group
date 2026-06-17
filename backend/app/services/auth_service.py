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
from app.services.auth_rate_limiter import login_rate_limiter
from app.services.shop_identity_service import find_shop_with_email

logger = structlog.get_logger(__name__)


def _normalize_login_identifier(value: str | None) -> str:
    return str(value or "").strip().lower()


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.audit_service = AuditService(db)

    def _log_auth_event(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata_json: dict | None,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str | None = None,
    ) -> None:
        try:
            self.audit_service.log(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_json=metadata_json,
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning("auth.audit_log_failed", action=action, error=str(exc))

    def _reject_failed_login(
        self,
        *,
        limit_key: str,
        user: User | None,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str,
        status_code: int = 401,
        code: str = "invalid_credentials",
        message: str = "Invalid login credentials",
    ) -> None:
        failure_status = login_rate_limiter.record_failed_attempt(limit_key)
        metadata = {
            "reason": reason,
            "shop_key": shop_key,
            "login_key": limit_key,
        }
        self._log_auth_event(
            actor_user_id=user.id if user else None,
            action="auth.login.failed",
            entity_type="user" if user else "auth_login",
            entity_id=str(user.id) if user else limit_key,
            metadata_json=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            shop_key=shop_key,
        )

        if not failure_status.allowed:
            self._log_auth_event(
                actor_user_id=user.id if user else None,
                action="auth.login.locked",
                entity_type="user" if user else "auth_login",
                entity_id=str(user.id) if user else limit_key,
                metadata_json={
                    **metadata,
                    "retry_after_seconds": failure_status.retry_after_seconds,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(
                status_code=429,
                code="login_locked",
                message="Too many failed login attempts. Please try again later.",
            )

        raise AppException(status_code=status_code, code=code, message=message)

    def register_admin(
        self,
        payload: AdminRegisterRequest,
        ip_address: str | None,
        user_agent: str | None,
        shop_key: str,
    ) -> User:
        normalized_email = _normalize_login_identifier(str(payload.email))
        self._log_auth_event(
            actor_user_id=None,
            action="auth.admin.register.attempt",
            entity_type="auth_admin_registration",
            entity_id=normalized_email,
            metadata_json={"shop_key": shop_key},
            ip_address=ip_address,
            user_agent=user_agent,
            shop_key=shop_key,
        )

        if not settings.admin_registration_enabled:
            self._log_auth_event(
                actor_user_id=None,
                action="auth.admin.register.blocked",
                entity_type="auth_admin_registration",
                entity_id=normalized_email,
                metadata_json={"reason": "disabled", "shop_key": shop_key},
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(
                status_code=403,
                code="admin_registration_disabled",
                message="Admin registration is disabled.",
            )

        if payload.master_password != settings.admin_master_password:
            self._log_auth_event(
                actor_user_id=None,
                action="auth.admin.register.failed",
                entity_type="auth_admin_registration",
                entity_id=normalized_email,
                metadata_json={"reason": "invalid_master_password", "shop_key": shop_key},
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(status_code=403, code="invalid_master_password", message="Invalid admin master password")

        if self.user_repo.get_by_email(normalized_email, shop_key=shop_key):
            self._log_auth_event(
                actor_user_id=None,
                action="auth.admin.register.failed",
                entity_type="auth_admin_registration",
                entity_id=normalized_email,
                metadata_json={"reason": "email_exists", "shop_key": shop_key},
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(status_code=409, code="email_exists", message="Email is already registered")

        conflicting_shop = find_shop_with_email(normalized_email, exclude_shop_key=shop_key, db=self.db)
        if conflicting_shop:
            self._log_auth_event(
                actor_user_id=None,
                action="auth.admin.register.failed",
                entity_type="auth_admin_registration",
                entity_id=normalized_email,
                metadata_json={"reason": "email_exists_other_shop", "shop_key": shop_key},
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(
                status_code=409,
                code="email_exists_other_shop",
                message="Email is already registered in another shop. Use a shop-specific email.",
            )

        try:
            user = self.user_repo.create(
                email=normalized_email,
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
                shop_key=shop_key,
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
        login_identifier = _normalize_login_identifier(str(payload.email or payload.login_id or ""))
        limit_key = login_rate_limiter.build_key(ip_address=ip_address, shop_key=shop_key, login_identifier=login_identifier)

        lockout_status = login_rate_limiter.check_lockout(limit_key)
        if not lockout_status.allowed:
            self._log_auth_event(
                actor_user_id=None,
                action="auth.login.locked",
                entity_type="auth_login",
                entity_id=limit_key,
                metadata_json={
                    "shop_key": shop_key,
                    "login_key": limit_key,
                    "retry_after_seconds": lockout_status.retry_after_seconds,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(
                status_code=429,
                code="login_locked",
                message="Too many failed login attempts. Please try again later.",
            )

        rate_status = login_rate_limiter.check_rate_limit(limit_key)
        if not rate_status.allowed:
            self._log_auth_event(
                actor_user_id=None,
                action="auth.login.rate_limited",
                entity_type="auth_login",
                entity_id=limit_key,
                metadata_json={
                    "shop_key": shop_key,
                    "login_key": limit_key,
                    "retry_after_seconds": rate_status.retry_after_seconds,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            raise AppException(
                status_code=429,
                code="login_rate_limited",
                message="Too many login attempts. Please try again later.",
            )

        user = self.user_repo.get_by_email(login_identifier, shop_key=shop_key)
        if not user or not verify_password(payload.password, user.password_hash):
            self._reject_failed_login(
                limit_key=limit_key,
                user=user,
                reason="invalid_credentials",
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )

        conflicting_shop = find_shop_with_email(login_identifier, exclude_shop_key=shop_key, db=self.db)
        if conflicting_shop:
            self._reject_failed_login(
                limit_key=limit_key,
                user=user,
                reason="cross_shop_identity_blocked",
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
                status_code=403,
                code="cross_shop_identity_blocked",
                message="This login id is already linked to another shop. Use shop-specific credentials.",
            )

        if not user.is_active:
            self._reject_failed_login(
                limit_key=limit_key,
                user=user,
                reason="user_inactive",
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
                status_code=403,
                code="user_inactive",
                message="User account is inactive",
            )

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
                shop_key=shop_key,
            )
            self.db.commit()
            login_rate_limiter.record_success(limit_key)
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
        if token_record.revoked_at is not None or _as_aware_utc(token_record.expires_at) <= now:
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
                shop_key=shop_key,
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

        if not token_record or token_record.revoked_at is not None:
            self._log_auth_event(
                actor_user_id=token_record.user_id if token_record else None,
                action="auth.logout",
                entity_type="refresh_token",
                entity_id=token_hash[:32],
                metadata_json={"result": "not_found_or_already_revoked", "shop_key": shop_key},
                ip_address=ip_address,
                user_agent=user_agent,
                shop_key=shop_key,
            )
            return MessageResponse(message="Logged out successfully")

        if token_record.revoked_at is None:
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
                shop_key=shop_key,
            )
            self.db.commit()

        return MessageResponse(message="Logged out successfully")
