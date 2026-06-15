from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.enums import WhatsAppStatus
from app.models.whatsapp_log import WhatsAppLog


class WhatsAppLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, log: WhatsAppLog) -> WhatsAppLog:
        self.db.add(log)
        self.db.flush()
        return log

    def failed_count(self, since: datetime | None = None) -> int:
        query = self.db.query(WhatsAppLog.id).filter(WhatsAppLog.status == WhatsAppStatus.FAILED)
        if since is not None:
            query = query.filter(WhatsAppLog.created_at >= since)
        return query.count()
