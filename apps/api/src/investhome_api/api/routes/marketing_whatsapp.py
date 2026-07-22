"""Marketing WhatsApp channel API routes."""

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
    WhatsAppCampaignCreate,
    WhatsAppCampaignListResponse,
    WhatsAppCampaignResponse,
    WhatsAppCampaignUpdate,
    WhatsAppConversationResponse,
    WhatsAppDashboardResponse,
    WhatsAppSenderResponse,
    WhatsAppTemplateCreate,
    WhatsAppTemplateResponse,
)
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.whatsapp_service import (
    calculate_whatsapp_readiness,
    create_whatsapp_campaign,
    create_whatsapp_template,
    get_whatsapp_campaign,
    get_whatsapp_dashboard,
    list_whatsapp_campaigns,
    list_whatsapp_conversations,
    list_whatsapp_senders,
    list_whatsapp_templates,
    schedule_whatsapp_campaign,
    submit_whatsapp_template,
    update_whatsapp_campaign,
)
from investhome_api.services.marketing.providers.whatsapp_marketing import get_whatsapp_marketing_provider

router = APIRouter(prefix="/marketing/whatsapp", tags=["marketing-whatsapp"])


@router.get("/dashboard", response_model=WhatsAppDashboardResponse)
def whatsapp_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view_dashboard")),
) -> dict:
    return get_whatsapp_dashboard(db)


@router.get("/campaigns", response_model=WhatsAppCampaignListResponse)
def get_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> dict:
    items, total = list_whatsapp_campaigns(db, page=page, page_size=page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": compute_pages(total, page_size),
    }


@router.post("/campaigns", response_model=WhatsAppCampaignResponse, status_code=status.HTTP_201_CREATED)
def post_campaign(
    payload: WhatsAppCampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> object:
    campaign = create_whatsapp_campaign(db, user, payload.model_dump())
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=WhatsAppCampaignResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> object:
    return get_whatsapp_campaign(db, campaign_id)


@router.patch("/campaigns/{campaign_id}", response_model=WhatsAppCampaignResponse)
def patch_campaign(
    campaign_id: UUID,
    payload: WhatsAppCampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> object:
    campaign = update_whatsapp_campaign(db, user, campaign_id, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/readiness", response_model=ReadinessResponse)
def post_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> dict:
    return calculate_whatsapp_readiness(db, campaign_id)


@router.post("/campaigns/{campaign_id}/schedule", response_model=SendOperationResponse)
def post_schedule(
    campaign_id: UUID,
    payload: IdempotentSendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> dict:
    result = schedule_whatsapp_campaign(
        db, user, campaign_id,
        idempotency_key=payload.idempotency_key,
        scheduled_at=payload.scheduled_at,
    )
    db.commit()
    return result


@router.get("/templates", response_model=list[WhatsAppTemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> list:
    return list_whatsapp_templates(db)


@router.post("/templates", response_model=WhatsAppTemplateResponse, status_code=status.HTTP_201_CREATED)
def post_template(
    payload: WhatsAppTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> object:
    template = create_whatsapp_template(db, user, payload.model_dump())
    db.commit()
    db.refresh(template)
    return template


@router.post("/templates/{template_id}/submit")
def post_submit_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> dict:
    result = submit_whatsapp_template(db, template_id)
    db.commit()
    return result


@router.get("/templates/provider")
def get_provider_templates(
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> dict:
    return get_whatsapp_marketing_provider().get_templates()


@router.get("/senders", response_model=list[WhatsAppSenderResponse])
def get_senders(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> list:
    return list_whatsapp_senders(db)


@router.get("/conversations", response_model=list[WhatsAppConversationResponse])
def get_conversations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> list:
    return list_whatsapp_conversations(db)
