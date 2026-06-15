from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.campaign_log import CampaignLog


class CampaignLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_campaign(self, campaign_id: int, page: int, page_size: int) -> tuple[list[CampaignLog], int]:
        query = self.db.query(CampaignLog).filter(CampaignLog.campaign_id == campaign_id)
        total = query.count()
        items = (
            query.order_by(CampaignLog.attempted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, campaign_log: CampaignLog) -> CampaignLog:
        self.db.add(campaign_log)
        self.db.flush()
        return campaign_log
