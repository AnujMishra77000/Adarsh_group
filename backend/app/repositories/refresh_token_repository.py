from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, token_hash: str, expires_at: datetime, created_ip: str | None) -> RefreshToken:
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_ip=created_ip,
        )
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def revoke(self, refresh_token: RefreshToken, revoked_at: datetime) -> None:
        refresh_token.revoked_at = revoked_at
        self.db.add(refresh_token)

    def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> int:
        tokens = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .all()
        )
        for token in tokens:
            token.revoked_at = revoked_at
            self.db.add(token)
        return len(tokens)
