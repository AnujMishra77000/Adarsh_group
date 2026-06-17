from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.enums import WhatsAppStatus
from app.models.whatsapp_log import WhatsAppLog


class WhatsAppLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, log: WhatsAppLog, shop_key: str | None = None) -> WhatsAppLog:
        if shop_key:
            assign_shop_scope(log, self.db, shop_key, legacy_attr="unused")
        self.db.add(log)
        self.db.flush()
        return log

    def failed_count(self, since: datetime | None = None, shop_key: str | None = None) -> int:
        query = self.db.query(WhatsAppLog.id).filter(WhatsAppLog.status == WhatsAppStatus.FAILED)
        if shop_key is not None:
            query = query.filter(shop_filter(self.db, WhatsAppLog, shop_key, legacy_attr=None))
        if since is not None:
            query = query.filter(WhatsAppLog.created_at >= since)
        return query.count()
