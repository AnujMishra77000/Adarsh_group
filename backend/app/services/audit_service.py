from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        actor_user_id: int | None,
        action: str,
        entity_type: str,
        entity_id: str,
        old_values: dict | None = None,
        new_values: dict | None = None,
        metadata_json: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        audit = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            metadata_json=metadata_json,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit)
        self.db.flush()
        return audit
