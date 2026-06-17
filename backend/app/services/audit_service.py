from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.shop_scope import assign_shop_scope
from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session, shop_key: str | None = None):
        self.db = db
        self.shop_key = shop_key

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
        shop_key: str | None = None,
    ) -> AuditLog:
        resolved_shop_key = shop_key or self.shop_key
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
        if resolved_shop_key:
            assign_shop_scope(audit, self.db, resolved_shop_key, legacy_attr="unused")
        self.db.add(audit)
        self.db.flush()
        return audit
