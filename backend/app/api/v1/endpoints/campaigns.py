from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import CampaignStatus, UserRole
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignListResponse, CampaignRead, CampaignScheduleResponse, CampaignUpdate
from app.schemas.campaign_log import CampaignLogListResponse
from app.schemas.common import MessageResponse
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: CampaignStatus | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CampaignListResponse:
    _ = current_user
    service = CampaignService(db, shop_key=shop_key)
    return service.list_campaigns(page=page, page_size=page_size, status=status, search=search)


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> CampaignRead:
    service = CampaignService(db, shop_key=shop_key)
    return service.create_campaign(payload=payload, actor=current_user)


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CampaignRead:
    _ = current_user
    service = CampaignService(db, shop_key=shop_key)
    return service.get_campaign(campaign_id=campaign_id)


@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> CampaignRead:
    service = CampaignService(db, shop_key=shop_key)
    return service.update_campaign(campaign_id=campaign_id, payload=payload, actor=current_user)


@router.delete("/{campaign_id}", response_model=MessageResponse)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    service = CampaignService(db, shop_key=shop_key)
    service.delete_campaign(campaign_id=campaign_id, actor=current_user)
    return MessageResponse(message="Campaign deleted successfully")


@router.post("/{campaign_id}/schedule", response_model=CampaignScheduleResponse)
def schedule_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> CampaignScheduleResponse:
    service = CampaignService(db, shop_key=shop_key)
    return service.schedule_campaign(campaign_id=campaign_id, actor=current_user)


@router.get("/{campaign_id}/logs", response_model=CampaignLogListResponse)
def campaign_logs(
    campaign_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> CampaignLogListResponse:
    _ = current_user
    service = CampaignService(db, shop_key=shop_key)
    return service.list_logs(campaign_id=campaign_id, page=page, page_size=page_size)
