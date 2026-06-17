from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.campaign import Campaign
from app.models.campaign_log import CampaignLog
from app.models.enums import CampaignStatus, WhatsAppModuleType, WhatsAppStatus
from app.models.user import User
from app.repositories.campaign_log_repository import CampaignLogRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignRead,
    CampaignScheduleResponse,
    CampaignUpdate,
)
from app.schemas.campaign_log import CampaignLogListResponse, CampaignLogRead
from app.services.audit_service import AuditService
from app.services.whatsapp_service import WhatsAppService

logger = structlog.get_logger(__name__)


class CampaignService:
    def __init__(self, db: Session, shop_key: str | None = None):
        self.db = db
        self.shop_key = shop_key
        self.repo = CampaignRepository(db)
        self.log_repo = CampaignLogRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.audit_service = AuditService(db, shop_key=shop_key)
        self.whatsapp_service = WhatsAppService(db, shop_key=shop_key)

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _serialize_campaign(campaign: Campaign) -> CampaignRead:
        return CampaignRead.model_validate(campaign)

    @staticmethod
    def _serialize_log(log_row: CampaignLog) -> CampaignLogRead:
        return CampaignLogRead.model_validate(log_row)

    def _require_shop_key(self) -> str:
        if not self.shop_key:
            raise AppException(status_code=400, code="missing_shop_context", message="Missing shop context")
        return self.shop_key

    def list_campaigns(
        self,
        *,
        page: int,
        page_size: int,
        status: CampaignStatus | None,
        search: str | None,
    ) -> CampaignListResponse:
        shop_key = self._require_shop_key()
        items, total = self.repo.list(page=page, page_size=page_size, shop_key=shop_key, status=status, search=search)
        return CampaignListResponse(
            items=[self._serialize_campaign(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_campaign(self, campaign_id: int) -> CampaignRead:
        campaign = self.repo.get_by_id(campaign_id, shop_key=self._require_shop_key())
        if not campaign:
            raise AppException(status_code=404, code="campaign_not_found", message="Campaign not found")
        return self._serialize_campaign(campaign)

    def create_campaign(self, payload: CampaignCreate, actor: User) -> CampaignRead:
        shop_key = self._require_shop_key()
        campaign = Campaign(
            shop_key=shop_key,
            title=payload.title.strip(),
            message_body=payload.message_body.strip(),
            scheduled_at=self._to_utc(payload.scheduled_at),
            status=CampaignStatus.DRAFT,
            total_customers_targeted=0,
            total_sent=0,
            total_failed=0,
            created_by=actor.id,
            updated_by=actor.id,
        )

        try:
            self.repo.create(campaign)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="campaign.create",
                entity_type="campaign",
                entity_id=str(campaign.id),
                new_values={
                    "title": campaign.title,
                    "scheduled_at": campaign.scheduled_at.isoformat(),
                    "status": campaign.status.value,
                },
            )
            self.db.commit()
            self.db.refresh(campaign)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="campaign_create_conflict", message="Unable to create campaign") from exc

        return self._serialize_campaign(campaign)

    def update_campaign(self, campaign_id: int, payload: CampaignUpdate, actor: User) -> CampaignRead:
        campaign = self.repo.get_by_id(campaign_id, shop_key=self._require_shop_key())
        if not campaign:
            raise AppException(status_code=404, code="campaign_not_found", message="Campaign not found")

        if campaign.status == CampaignStatus.RUNNING:
            raise AppException(
                status_code=409,
                code="campaign_running",
                message="Running campaigns cannot be updated",
            )

        old_values = {
            "title": campaign.title,
            "message_body": campaign.message_body,
            "scheduled_at": campaign.scheduled_at.isoformat(),
            "status": campaign.status.value,
        }

        updates = payload.model_dump(exclude_unset=True)
        if "title" in updates and updates["title"] is not None:
            campaign.title = updates["title"].strip()
        if "message_body" in updates and updates["message_body"] is not None:
            campaign.message_body = updates["message_body"].strip()
        if "scheduled_at" in updates and updates["scheduled_at"] is not None:
            campaign.scheduled_at = self._to_utc(updates["scheduled_at"])
        if "status" in updates and updates["status"] is not None:
            campaign.status = updates["status"]

        campaign.updated_by = actor.id

        try:
            self.repo.save(campaign)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="campaign.update",
                entity_type="campaign",
                entity_id=str(campaign.id),
                old_values=old_values,
                new_values={
                    "title": campaign.title,
                    "message_body": campaign.message_body,
                    "scheduled_at": campaign.scheduled_at.isoformat(),
                    "status": campaign.status.value,
                },
            )
            self.db.commit()
            self.db.refresh(campaign)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="campaign_update_conflict", message="Unable to update campaign") from exc

        return self._serialize_campaign(campaign)

    def delete_campaign(self, campaign_id: int, actor: User) -> None:
        campaign = self.repo.get_by_id(campaign_id, shop_key=self._require_shop_key())
        if not campaign:
            raise AppException(status_code=404, code="campaign_not_found", message="Campaign not found")

        if campaign.is_deleted:
            return

        campaign.is_deleted = True
        campaign.status = CampaignStatus.CANCELLED
        campaign.updated_by = actor.id

        self.repo.save(campaign)
        self.audit_service.log(
            actor_user_id=actor.id,
            action="campaign.delete",
            entity_type="campaign",
            entity_id=str(campaign.id),
            old_values={"is_deleted": False},
            new_values={"is_deleted": True, "status": campaign.status.value},
        )
        self.db.commit()

    def schedule_campaign(self, campaign_id: int, actor: User) -> CampaignScheduleResponse:
        shop_key = self._require_shop_key()
        campaign = self.repo.get_by_id(campaign_id, shop_key=shop_key)
        if not campaign:
            raise AppException(status_code=404, code="campaign_not_found", message="Campaign not found")

        if campaign.status == CampaignStatus.RUNNING:
            raise AppException(
                status_code=409,
                code="campaign_running",
                message="Campaign is already running",
            )

        if campaign.status == CampaignStatus.COMPLETED:
            raise AppException(
                status_code=409,
                code="campaign_completed",
                message="Completed campaign cannot be scheduled again",
            )

        target_count = self.customer_repo.count_whatsapp_eligible(shop_key=shop_key)
        campaign.total_customers_targeted = target_count
        campaign.total_sent = 0
        campaign.total_failed = 0
        campaign.status = CampaignStatus.SCHEDULED
        campaign.updated_by = actor.id
        self.repo.save(campaign)

        self.audit_service.log(
            actor_user_id=actor.id,
            action="campaign.schedule",
            entity_type="campaign",
            entity_id=str(campaign.id),
            new_values={
                "scheduled_at": campaign.scheduled_at.isoformat(),
                "status": campaign.status.value,
                "total_customers_targeted": target_count,
            },
        )

        try:
            self.db.commit()
            self.db.refresh(campaign)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(status_code=409, code="campaign_schedule_conflict", message="Unable to schedule campaign") from exc

        try:
            from app.workers.tasks.campaigns import execute_campaign_task

            # SQLite may return naive datetimes even when timezone=True is declared.
            # Normalize before scheduling to avoid offset-aware comparison errors.
            eta = self._to_utc(campaign.scheduled_at)
            if eta <= datetime.now(UTC):
                execute_campaign_task.delay(campaign.id, campaign.shop_key)
            else:
                execute_campaign_task.apply_async(args=[campaign.id, campaign.shop_key], eta=eta)
        except Exception as exc:  # pragma: no cover - broker/runtime dependent
            logger.error("campaign.task_dispatch_failed", campaign_id=campaign.id, error=str(exc))
            campaign.status = CampaignStatus.FAILED
            campaign.updated_by = actor.id
            self.repo.save(campaign)
            self.audit_service.log(
                actor_user_id=actor.id,
                action="campaign.schedule.dispatch_failed",
                entity_type="campaign",
                entity_id=str(campaign.id),
                metadata_json={"error": str(exc)},
                new_values={"status": campaign.status.value},
            )
            self.db.commit()
            raise AppException(
                status_code=500,
                code="campaign_dispatch_failed",
                message="Campaign saved but scheduling dispatch failed",
            ) from exc

        return CampaignScheduleResponse(message="Campaign scheduled successfully", campaign=self._serialize_campaign(campaign))

    def list_logs(self, campaign_id: int, page: int, page_size: int) -> CampaignLogListResponse:
        campaign = self.repo.get_by_id(campaign_id, shop_key=self._require_shop_key())
        if not campaign:
            raise AppException(status_code=404, code="campaign_not_found", message="Campaign not found")

        items, total = self.log_repo.list_for_campaign(campaign_id=campaign_id, page=page, page_size=page_size)
        return CampaignLogListResponse(
            items=[self._serialize_log(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def execute_campaign(self, campaign_id: int) -> None:
        campaign = self.repo.get_by_id(campaign_id)
        if not campaign:
            logger.warning("campaign.execute.not_found", campaign_id=campaign_id)
            return

        if campaign.status not in {CampaignStatus.SCHEDULED, CampaignStatus.RUNNING}:
            logger.info(
                "campaign.execute.skip_status",
                campaign_id=campaign_id,
                status=campaign.status.value,
            )
            return

        self.audit_service.shop_key = campaign.shop_key
        self.whatsapp_service.shop_key = campaign.shop_key

        campaign.status = CampaignStatus.RUNNING
        self.repo.save(campaign)
        self.db.commit()

        customers = self.customer_repo.list_whatsapp_eligible(shop_key=campaign.shop_key)
        campaign.total_customers_targeted = len(customers)

        sent_count = 0
        failed_count = 0

        for customer in customers:
            recipient = customer.whatsapp_no or ""
            result = self.whatsapp_service.send_text_message(
                module_type=WhatsAppModuleType.CAMPAIGN,
                reference_id=campaign.id,
                recipient_no=recipient,
                customer_id=customer.id,
                message_body=campaign.message_body,
                raise_on_error=False,
            )

            send_status = "sent" if result.status == WhatsAppStatus.SENT else "failed"
            if result.status == WhatsAppStatus.SENT:
                sent_count += 1
            else:
                failed_count += 1

            self.log_repo.create(
                CampaignLog(
                    campaign_id=campaign.id,
                    customer_id=customer.id,
                    recipient_whatsapp_no=recipient,
                    send_status=send_status,
                    provider_message_id=result.provider_message_id,
                    error_message=result.error_message,
                )
            )
            self.db.commit()

        campaign.total_sent = sent_count
        campaign.total_failed = failed_count
        campaign.status = CampaignStatus.FAILED if sent_count == 0 and failed_count > 0 else CampaignStatus.COMPLETED

        self.repo.save(campaign)
        self.audit_service.log(
            actor_user_id=campaign.updated_by or campaign.created_by,
            action="campaign.execute",
            entity_type="campaign",
            entity_id=str(campaign.id),
            new_values={
                "status": campaign.status.value,
                "total_customers_targeted": campaign.total_customers_targeted,
                "total_sent": campaign.total_sent,
                "total_failed": campaign.total_failed,
            },
        )
        self.db.commit()

        logger.info(
            "campaign.execute.completed",
            campaign_id=campaign.id,
            total_customers_targeted=campaign.total_customers_targeted,
            total_sent=campaign.total_sent,
            total_failed=campaign.total_failed,
            status=campaign.status.value,
        )

    def execute_campaign_with_recovery(self, campaign_id: int) -> None:
        try:
            self.execute_campaign(campaign_id)
        except Exception as exc:  # pragma: no cover - defensive safety
            logger.exception("campaign.execute.failed", campaign_id=campaign_id, error=str(exc))
            self.db.rollback()

            campaign = self.repo.get_by_id(campaign_id)
            if campaign:
                campaign.status = CampaignStatus.FAILED
                self.repo.save(campaign)
                self.audit_service.log(
                    actor_user_id=campaign.updated_by or campaign.created_by,
                    action="campaign.execute.failed",
                    entity_type="campaign",
                    entity_id=str(campaign.id),
                    metadata_json={"error": str(exc)},
                    new_values={"status": campaign.status.value},
                )
                self.db.commit()
