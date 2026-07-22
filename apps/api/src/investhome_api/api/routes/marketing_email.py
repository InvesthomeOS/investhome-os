"""Marketing email channel API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_channel_communications import (
    EmailCampaignCreate,
    EmailCampaignListResponse,
    EmailCampaignResponse,
    EmailCampaignUpdate,
    EmailDashboardResponse,
    EmailDomainCreate,
    EmailDomainResponse,
    EmailSenderResponse,
    EmailSequenceResponse,
    EmailSequenceStepResponse,
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTestSendRequest,
    IdempotentSendRequest,
    ReadinessResponse,
    SendOperationResponse,
)
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.email_service import (
    calculate_email_readiness,
    create_email_campaign,
    create_email_domain,
    create_email_template,
    get_email_campaign,
    get_email_dashboard,
    get_email_sequence,
    list_email_campaigns,
    list_email_domains,
    list_email_senders,
    list_email_sequences,
    list_email_templates,
    list_sequence_steps,
    schedule_email_campaign,
    send_test_email,
    update_email_campaign,
)
from investhome_api.services.marketing.providers.email_marketing import get_email_marketing_provider

router = APIRouter(prefix="/marketing/email", tags=["marketing-email"])


@router.get("/dashboard", response_model=EmailDashboardResponse)
def email_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view_dashboard")),
) -> dict:
    return get_email_dashboard(db)


@router.get("/campaigns", response_model=EmailCampaignListResponse)
def get_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> dict:
    items, total = list_email_campaigns(db, page=page, page_size=page_size, status_filter=status_filter)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": compute_pages(total, page_size),
    }


@router.post("/campaigns", response_model=EmailCampaignResponse, status_code=status.HTTP_201_CREATED)
def post_campaign(
    payload: EmailCampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_email")),
) -> object:
    campaign = create_email_campaign(db, user, payload.model_dump())
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=EmailCampaignResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> object:
    return get_email_campaign(db, campaign_id)


@router.patch("/campaigns/{campaign_id}", response_model=EmailCampaignResponse)
def patch_campaign(
    campaign_id: UUID,
    payload: EmailCampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_email")),
) -> object:
    campaign = update_email_campaign(db, user, campaign_id, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/readiness", response_model=ReadinessResponse)
def post_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> dict:
    return calculate_email_readiness(db, campaign_id)


@router.post("/campaigns/{campaign_id}/schedule", response_model=SendOperationResponse)
def post_schedule(
    campaign_id: UUID,
    payload: IdempotentSendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_email")),
) -> dict:
    result = schedule_email_campaign(
        db, user, campaign_id,
        idempotency_key=payload.idempotency_key,
        scheduled_at=payload.scheduled_at,
    )
    db.commit()
    return result


@router.post("/campaigns/{campaign_id}/test-send")
def post_test_send(
    campaign_id: UUID,
    payload: EmailTestSendRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> dict:
    return send_test_email(db, None, campaign_id, recipient_email=payload.recipient_email)


@router.get("/templates", response_model=list[EmailTemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> list:
    return list_email_templates(db)


@router.post("/templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def post_template(
    payload: EmailTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "send_email")),
) -> object:
    template = create_email_template(db, user, payload.model_dump())
    db.commit()
    db.refresh(template)
    return template


@router.get("/senders", response_model=list[EmailSenderResponse])
def get_senders(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> list:
    return list_email_senders(db)


@router.get("/domains", response_model=list[EmailDomainResponse])
def get_domains(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> list:
    return list_email_domains(db)


@router.post("/domains", response_model=EmailDomainResponse, status_code=status.HTTP_201_CREATED)
def post_domain(
    payload: EmailDomainCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "manage_settings")),
) -> object:
    domain = create_email_domain(db, payload.model_dump())
    db.commit()
    db.refresh(domain)
    return domain


@router.get("/sequences", response_model=list[EmailSequenceResponse])
def get_sequences(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> list:
    return list_email_sequences(db)


@router.get("/sequences/{sequence_id}", response_model=EmailSequenceResponse)
def get_sequence(
    sequence_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> object:
    return get_email_sequence(db, sequence_id)


@router.get("/sequences/{sequence_id}/steps", response_model=list[EmailSequenceStepResponse])
def get_sequence_steps(
    sequence_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> list:
    return list_sequence_steps(db, sequence_id)


@router.get("/suppression")
def get_suppression(
    _: User = Depends(require_permission("marketing", "manage_suppression")),
) -> dict:
    return get_email_marketing_provider().get_suppression()
