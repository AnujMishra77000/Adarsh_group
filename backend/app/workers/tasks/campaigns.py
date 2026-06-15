from __future__ import annotations

import structlog

from app.db.tenant import tenant_db_manager
from app.services.campaign_service import CampaignService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="campaign.execute", bind=True)
def execute_campaign_task(self, campaign_id: int, shop_code: str) -> dict[str, str | int]:
    logger.info("campaign.task.started", campaign_id=campaign_id, shop_code=shop_code, task_id=self.request.id)

    with tenant_db_manager.session_scope(shop_code) as db:
        service = CampaignService(db)
        service.execute_campaign_with_recovery(campaign_id)

    logger.info("campaign.task.completed", campaign_id=campaign_id, shop_code=shop_code, task_id=self.request.id)
    return {"status": "completed", "campaign_id": campaign_id, "shop_code": shop_code}
