from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        page: int,
        page_size: int,
        shop_key: str,
        status: CampaignStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Campaign], int]:
        query = self.db.query(Campaign).filter(Campaign.is_deleted.is_(False), Campaign.shop_key == shop_key)

        if status is not None:
            query = query.filter(Campaign.status == status)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(Campaign.title.ilike(pattern))

        total = query.count()
        items = (
            query.order_by(Campaign.scheduled_at.desc(), Campaign.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, campaign_id: int, shop_key: str | None = None, include_deleted: bool = False) -> Campaign | None:
        query = self.db.query(Campaign)
        if not include_deleted:
            query = query.filter(Campaign.is_deleted.is_(False))
        if shop_key is not None:
            query = query.filter(Campaign.shop_key == shop_key)
        return query.filter(Campaign.id == campaign_id).first()

    def list_due_scheduled(self, now: datetime, limit: int = 100) -> list[Campaign]:
        return (
            self.db.query(Campaign)
            .filter(
                Campaign.is_deleted.is_(False),
                Campaign.status == CampaignStatus.SCHEDULED,
                Campaign.scheduled_at <= now,
            )
            .order_by(Campaign.scheduled_at.asc())
            .limit(limit)
            .all()
        )

    def create(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def save(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        self.db.flush()
        return campaign
