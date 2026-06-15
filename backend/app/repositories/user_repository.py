from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_staff_by_id(self, user_id: int, shop_key: str | None = None) -> User | None:
        query = self.db.query(User).filter(User.id == user_id, User.role == UserRole.STAFF)
        if shop_key is not None:
            query = query.filter(User.shop_key == shop_key)
        return query.first()

    def get_by_email(self, email: str, shop_key: str | None = None) -> User | None:
        query = self.db.query(User).filter(User.email == email.lower())
        if shop_key is not None:
            query = query.filter(User.shop_key == shop_key)
        return query.first()

    def exists_admin(self) -> bool:
        return self.db.query(User.id).filter(User.role == UserRole.ADMIN).first() is not None

    def list_staff(
        self,
        page: int,
        page_size: int,
        shop_key: str,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        query = self.db.query(User).filter(User.role == UserRole.STAFF, User.shop_key == shop_key)

        if is_active is not None:
            query = query.filter(User.is_active.is_(is_active))

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.email.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )

        total = query.count()
        items = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(
        self,
        email: str,
        full_name: str | None,
        password_hash: str,
        role: UserRole,
        shop_key: str,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            shop_key=shop_key,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
