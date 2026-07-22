"""Marketing SMS channel API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_channel_communications import (
    IdempotentSendRequest,
    ReadinessResponse,
    SendOperationResponse,
    SmsCampaignCreate,
    SmsCampaignListResponse,
    SmsCampaignResponse,
    SmsCampaignUpdate,
    SmsDashboardResponse,
    SmsSenderResponse,
    SmsTemplateCreate,
    SmsTemplateResponse,
    SmsTestSendRequest,
    SmsValidationResponse,
)
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.sms_service import (
    calculate_sms_readiness,
    create_sms_campaign,
    create_sms_template,
    get_sms_campaign,
    get_sms_dashboard,
    list_sms_campaigns,
    list_sms_senders,
    list_sms_templates,
    schedule_sms_campaign,
    send_test_sms,
    update_sms_campaign,
    validate_sms_body,
)

router = APIRouter(prefix="/marketing/sms", tags=["marketing-sms"])


@router.get("/dashboard", response_model=SmsDashboardResponse)
def sms_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view_dashboard")),
) -> dict:
    return get_sms_dashboard(db)


@router.get("/campaigns", response_model=SmsCampaignListResponse)
def get_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> dict:
    items, total = list_sms_campaigns(db, page=page, page_size=page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": compute_pages(total, page_size),
    }


@router.post("/campaigns", response_model=SmsCampaignResponse, status_code=status.HTTP_201_CREATED)
def post_campaign(
    payload: SmsCampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_sms")),
) -> object:
    campaign = create_sms_campaign(db, user, payload.model_dump())
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=SmsCampaignResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> object:
    return get_sms_campaign(db, campaign_id)


@router.patch("/campaigns/{campaign_id}", response_model=SmsCampaignResponse)
def patch_campaign(
    campaign_id: UUID,
    payload: SmsCampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_sms")),
) -> object:
    campaign = update_sms_campaign(db, user, campaign_id, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/readiness", response_model=ReadinessResponse)
def post_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> dict:
    return calculate_sms_readiness(db, campaign_id)


@router.post("/campaigns/{campaign_id}/schedule", response_model=SendOperationResponse)
def post_schedule(
    campaign_id: UUID,
    payload: IdempotentSendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_sms")),
) -> dict:
    result = schedule_sms_campaign(
        db, user, campaign_id,
        idempotency_key=payload.idempotency_key,
        scheduled_at=payload.scheduled_at,
    )
    db.commit()
    return result


@router.post("/campaigns/{campaign_id}/test-send")
def post_test_send(
    campaign_id: UUID,
    payload: SmsTestSendRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> dict:
    return send_test_sms(db, campaign_id, phone_number=payload.phone_number)


@router.post("/validate", response_model=SmsValidationResponse)
def post_validate(
    body: str = Query(...),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> dict:
    return validate_sms_body(body)


@router.get("/templates", response_model=list[SmsTemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> list:
    return list_sms_templates(db)


@router.post("/templates", response_model=SmsTemplateResponse, status_code=status.HTTP_201_CREATED)
def post_template(
    payload: SmsTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_sms")),
) -> object:
    template = create_sms_template(db, user, payload.model_dump())
    db.commit()
    db.refresh(template)
    return template


@router.get("/senders", response_model=list[SmsSenderResponse])
def get_senders(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> list:
    return list_sms_senders(db)
