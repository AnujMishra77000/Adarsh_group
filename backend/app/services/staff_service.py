from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.staff import (
    StaffCreateRequest,
    StaffListResponse,
    StaffLoginActivityListResponse,
    StaffLoginActivityRead,
    StaffRead,
)
from app.services.audit_service import AuditService
from app.services.shop_identity_service import find_shop_with_email


class StaffService:
    def __init__(self, db: Session, shop_key: str):
        self.db = db
        self.shop_key = shop_key
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)

    def list_staff(
        self,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
    ) -> StaffListResponse:
        items, total = self.user_repo.list_staff(
            page=page,
            page_size=page_size,
            shop_key=self.shop_key,
            search=search,
            is_active=is_active,
        )

        return StaffListResponse(
            items=[StaffRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_staff(
        self,
        payload: StaffCreateRequest,
        actor: User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> StaffRead:
        if self.user_repo.get_by_email(payload.email, shop_key=self.shop_key):
            raise AppException(status_code=409, code="email_exists", message="Email is already registered")

        conflicting_shop = find_shop_with_email(payload.email, exclude_shop_key=self.shop_key)
        if conflicting_shop:
            raise AppException(
                status_code=409,
                code="email_exists_other_shop",
                message="Email is already registered in another shop. Use a shop-specific email.",
            )

        try:
            staff = self.user_repo.create(
                email=payload.email,
                full_name=payload.full_name,
                password_hash=get_password_hash(payload.password),
                role=UserRole.STAFF,
                shop_key=self.shop_key,
                is_active=True,
            )
            self.audit_service.log(
                actor_user_id=actor.id,
                action="staff.create",
                entity_type="user",
                entity_id=str(staff.id),
                new_values={
                    "email": staff.email,
                    "role": staff.role.value,
                    "is_active": staff.is_active,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.commit()
            self.db.refresh(staff)
            return StaffRead.model_validate(staff)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="staff_create_conflict", message="Unable to create staff user") from exc

    def delete_staff(
        self,
        staff_user_id: int,
        actor: User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> MessageResponse:
        staff = self.user_repo.get_staff_by_id(staff_user_id, shop_key=self.shop_key)
        if not staff:
            raise AppException(status_code=404, code="staff_not_found", message="Staff user not found")

        if staff.id == actor.id:
            raise AppException(status_code=400, code="self_deactivate_blocked", message="You cannot deactivate your own account")

        if not staff.is_active:
            return MessageResponse(message="Staff user already inactive")

        staff.is_active = False
        self.user_repo.save(staff)

        self.audit_service.log(
            actor_user_id=actor.id,
            action="staff.deactivate",
            entity_type="user",
            entity_id=str(staff.id),
            old_values={"is_active": True},
            new_values={"is_active": False},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.commit()

        return MessageResponse(message="Staff user deactivated successfully")

    def list_login_activities(
        self,
        page: int,
        page_size: int,
        staff_user_id: int | None,
    ) -> StaffLoginActivityListResponse:
        query = (
            self.db.query(AuditLog, User)
            .join(User, User.id == AuditLog.actor_user_id)
            .filter(
                AuditLog.action == "auth.login",
                User.role == UserRole.STAFF,
                User.shop_key == self.shop_key,
            )
        )

        if staff_user_id is not None:
            query = query.filter(User.id == staff_user_id)

        total = query.count()
        rows = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            StaffLoginActivityRead(
                id=audit.id,
                staff_user_id=user.id,
                staff_email=user.email,
                staff_full_name=user.full_name,
                attempted_at=audit.created_at,
                ip_address=audit.ip_address,
                user_agent=audit.user_agent,
            )
            for audit, user in rows
        ]

        return StaffLoginActivityListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
