from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import create_access_token, decode_jwt_token, get_password_hash, hash_token
from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AdminRegisterRequest, LoginRequest, LogoutRequest, RefreshTokenRequest
from app.services import auth_service as auth_service_module
from app.services.auth_rate_limiter import login_rate_limiter
from app.services.auth_service import AuthService


SHOP_KEY = "adarsh-eye-boutique"


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db: Session = self.SessionLocal()
        self.addCleanup(self.db.close)

        login_rate_limiter._redis_unavailable = True
        login_rate_limiter.reset()
        self.addCleanup(login_rate_limiter.reset)

        self.setting_patchers = [
            patch.object(settings, "access_token_expire_minutes", 30),
            patch.object(settings, "refresh_token_expire_days", 14),
            patch.object(settings, "auth_login_rate_limit_attempts", 10),
            patch.object(settings, "auth_login_rate_limit_window_seconds", 60),
            patch.object(settings, "auth_login_lockout_failed_attempts", 2),
            patch.object(settings, "auth_login_lockout_seconds", 300),
            patch.object(settings, "environment", "development"),
            patch.object(settings, "allow_admin_registration", False),
        ]
        for patcher in self.setting_patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def create_admin(self, email: str = "Admin@Example.com", password: str = "secure-pass-123") -> User:
        user = UserRepository(self.db).create(
            email=email,
            full_name="Admin User",
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            shop_key=SHOP_KEY,
            is_active=True,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def auth_service(self) -> AuthService:
        return AuthService(self.db)

    def audit_actions(self) -> list[str]:
        return [row.action for row in self.db.query(AuditLog).order_by(AuditLog.id).all()]

    @patch.object(auth_service_module, "find_shop_with_email", return_value=None)
    def test_invalid_login_is_rejected_and_audited(self, _: object) -> None:
        self.create_admin()

        with self.assertRaises(AppException) as raised:
            self.auth_service().login(
                payload=LoginRequest(email=" ADMIN@example.com ", password="wrong-pass-123"),
                ip_address="127.0.0.1",
                user_agent="test",
                shop_key=SHOP_KEY,
            )

        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("auth.login.failed", self.audit_actions())

    @patch.object(auth_service_module, "find_shop_with_email", return_value=None)
    def test_successful_login_returns_expiring_tokens_and_resets_failures(self, _: object) -> None:
        user = self.create_admin()

        tokens = self.auth_service().login(
            payload=LoginRequest(email=" admin@example.com ", password="secure-pass-123"),
            ip_address="127.0.0.1",
            user_agent="test",
            shop_key=SHOP_KEY,
        )

        access_payload = decode_jwt_token(tokens.access_token)
        self.assertEqual(access_payload["sub"], str(user.id))
        self.assertEqual(access_payload["type"], "access")
        self.assertEqual(access_payload["shop_code"], SHOP_KEY)
        self.assertIn("exp", access_payload)
        self.assertIsNotNone(RefreshTokenRepository(self.db).get_by_hash(hash_token(tokens.refresh_token)))

    @patch.object(auth_service_module, "find_shop_with_email", return_value=None)
    def test_refresh_rotation_revokes_old_refresh_token(self, _: object) -> None:
        self.create_admin()
        service = self.auth_service()
        tokens = service.login(
            payload=LoginRequest(email="admin@example.com", password="secure-pass-123"),
            ip_address="127.0.0.1",
            user_agent="test",
            shop_key=SHOP_KEY,
        )

        rotated = service.refresh_tokens(
            payload=RefreshTokenRequest(refresh_token=tokens.refresh_token),
            ip_address="127.0.0.1",
            user_agent="test",
            shop_key=SHOP_KEY,
        )

        old_record = RefreshTokenRepository(self.db).get_by_hash(hash_token(tokens.refresh_token))
        self.assertIsNotNone(old_record.revoked_at)
        self.assertNotEqual(tokens.refresh_token, rotated.refresh_token)
        with self.assertRaises(AppException):
            service.refresh_tokens(
                payload=RefreshTokenRequest(refresh_token=tokens.refresh_token),
                ip_address="127.0.0.1",
                user_agent="test",
                shop_key=SHOP_KEY,
            )

    @patch.object(auth_service_module, "find_shop_with_email", return_value=None)
    def test_logout_revokes_active_refresh_token(self, _: object) -> None:
        self.create_admin()
        tokens = self.auth_service().login(
            payload=LoginRequest(email="admin@example.com", password="secure-pass-123"),
            ip_address="127.0.0.1",
            user_agent="test",
            shop_key=SHOP_KEY,
        )

        self.auth_service().logout(
            payload=LogoutRequest(refresh_token=tokens.refresh_token),
            ip_address="127.0.0.1",
            user_agent="test",
            shop_key=SHOP_KEY,
        )

        token_record = RefreshTokenRepository(self.db).get_by_hash(hash_token(tokens.refresh_token))
        self.assertIsNotNone(token_record.revoked_at)
        self.assertIn("auth.logout", self.audit_actions())

    def test_admin_registration_is_disabled_in_production_by_default(self) -> None:
        with patch.object(settings, "environment", "production"), patch.object(
            settings, "allow_admin_registration", False
        ):
            with self.assertRaises(AppException) as raised:
                self.auth_service().register_admin(
                    payload=AdminRegisterRequest(
                        email="owner@example.com",
                        full_name="Owner",
                        password="secure-pass-123",
                        master_password=settings.admin_master_password,
                    ),
                    ip_address="127.0.0.1",
                    user_agent="test",
                    shop_key=SHOP_KEY,
                )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.code, "admin_registration_disabled")
        self.assertIn("auth.admin.register.blocked", self.audit_actions())

    @patch.object(auth_service_module, "find_shop_with_email", return_value=None)
    def test_repeated_failed_login_attempts_trigger_lockout(self, _: object) -> None:
        self.create_admin()
        service = self.auth_service()

        for _attempt in range(2):
            with self.assertRaises(AppException):
                service.login(
                    payload=LoginRequest(email="admin@example.com", password="wrong-pass-123"),
                    ip_address="127.0.0.1",
                    user_agent="test",
                    shop_key=SHOP_KEY,
                )

        with self.assertRaises(AppException) as raised:
            service.login(
                payload=LoginRequest(email="admin@example.com", password="secure-pass-123"),
                ip_address="127.0.0.1",
                user_agent="test",
                shop_key=SHOP_KEY,
            )

        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("auth.login.locked", self.audit_actions())

    @patch.object(auth_service_module, "find_shop_with_email", return_value=None)
    def test_login_attempts_are_rate_limited_by_ip_shop_and_identifier(self, _: object) -> None:
        self.create_admin()
        service = self.auth_service()

        with patch.object(settings, "auth_login_rate_limit_attempts", 1):
            with self.assertRaises(AppException) as first_failure:
                service.login(
                    payload=LoginRequest(email="admin@example.com", password="wrong-pass-123"),
                    ip_address="127.0.0.1",
                    user_agent="test",
                    shop_key=SHOP_KEY,
                )

            with self.assertRaises(AppException) as throttled:
                service.login(
                    payload=LoginRequest(email="admin@example.com", password="secure-pass-123"),
                    ip_address="127.0.0.1",
                    user_agent="test",
                    shop_key=SHOP_KEY,
                )

        self.assertEqual(first_failure.exception.status_code, 401)
        self.assertEqual(throttled.exception.status_code, 429)
        self.assertEqual(throttled.exception.code, "login_rate_limited")
        self.assertIn("auth.login.rate_limited", self.audit_actions())

    def test_shop_mismatch_token_is_rejected(self) -> None:
        user = self.create_admin()
        token = create_access_token(subject=str(user.id), role=user.role.value, shop_code=SHOP_KEY)

        with self.assertRaises(HTTPException) as raised:
            get_current_user(db=self.db, token=token, shop_key="adarsh-opticals-muxar")

        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
