from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.shop_scope import assign_shop_scope, resolve_shop_id
from app.models.campaign import Campaign
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
        campaign = self.db.get(Campaign, campaign_log.campaign_id)
        if campaign is not None and campaign_log.shop_id is None:
            if campaign.shop_id is not None:
                campaign_log.shop_id = campaign.shop_id
            else:
                campaign_log.shop_id = resolve_shop_id(self.db, campaign.shop_key)
            if campaign.shop_key:
                assign_shop_scope(campaign_log, self.db, campaign.shop_key, legacy_attr="unused")
        self.db.add(campaign_log)
        self.db.flush()
        return campaign_log
