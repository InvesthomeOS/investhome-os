"""Shared marketing channel API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_channel_communications import (
    DeliveryEventListResponse,
    DeliveryEventResponse,
    FrequencyPolicyCreate,
    FrequencyPolicyResponse,
    OptOutRequest,
    OptOutResponse,
    PersonalizationPreviewRequest,
    PersonalizationPreviewResponse,
    ProviderStatusResponse,
    ReadinessResponse,
    RecipientCalculationResponse,
)
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.channel_calendar_service import list_channel_calendar_items
from investhome_api.services.marketing.channel_shared_service import (
    calculate_recipients,
    check_readiness,
    create_frequency_policy,
    list_channel_provider_statuses,
    list_delivery_events,
    list_frequency_policies,
    preview_personalization,
    process_opt_out,
)
from investhome_api.services.marketing.email_service import calculate_email_readiness
from investhome_api.services.marketing.sms_service import calculate_sms_readiness
from investhome_api.services.marketing.social_service import calculate_social_readiness
from investhome_api.services.marketing.whatsapp_service import calculate_whatsapp_readiness

router = APIRouter(prefix="/marketing/channel", tags=["marketing-channel"])


@router.get("/calendar")
def get_channel_calendar(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view")),
) -> dict:
    return {"items": list_channel_calendar_items(db)}


@router.get("/provider-status", response_model=list[ProviderStatusResponse])
def get_provider_statuses(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view")),
) -> list[dict]:
    return list_channel_provider_statuses(db)


@router.get("/eligibility/{audience_id}", response_model=RecipientCalculationResponse)
def get_audience_eligibility(
    audience_id: UUID,
    channel: str = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view_audience_consent")),
) -> dict:
    return calculate_recipients(db, audience_id, channel)


@router.post("/readiness/email/{campaign_id}", response_model=ReadinessResponse)
def email_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_email")),
) -> dict:
    return calculate_email_readiness(db, campaign_id)


@router.post("/readiness/whatsapp/{campaign_id}", response_model=ReadinessResponse)
def whatsapp_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_whatsapp")),
) -> dict:
    return calculate_whatsapp_readiness(db, campaign_id)


@router.post("/readiness/sms/{campaign_id}", response_model=ReadinessResponse)
def sms_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "send_sms")),
) -> dict:
    return calculate_sms_readiness(db, campaign_id)


@router.post("/readiness/social/{post_id}", response_model=ReadinessResponse)
def social_readiness(
    post_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    return calculate_social_readiness(db, post_id)


@router.get("/frequency-policies", response_model=list[FrequencyPolicyResponse])
def get_frequency_policies(
    channel: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "view")),
) -> list:
    return list_frequency_policies(db, channel)


@router.post("/frequency-policies", response_model=FrequencyPolicyResponse, status_code=201)
def post_frequency_policy(
    payload: FrequencyPolicyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "manage_settings")),
) -> object:
    policy = create_frequency_policy(db, payload.model_dump())
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/personalization/preview", response_model=PersonalizationPreviewResponse)
def personalization_preview(
    payload: PersonalizationPreviewRequest,
    _: User = Depends(require_permission("marketing", "view")),
) -> dict:
    return preview_personalization(payload.config, payload.sample_contact)


@router.get("/delivery-events", response_model=DeliveryEventListResponse)
def get_delivery_events(
    channel: str | None = None,
    campaign_type: str | None = None,
    campaign_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "export_analytics")),
) -> dict:
    items, total = list_delivery_events(
        db, channel=channel, campaign_type=campaign_type, campaign_id=campaign_id,
        page=page, page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": compute_pages(total, page_size),
    }


@router.post("/opt-out", response_model=OptOutResponse)
def post_opt_out(
    payload: OptOutRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("marketing", "manage_suppression")),
) -> dict:
    result = process_opt_out(
        db,
        contact_id=payload.contact_id,
        company_id=payload.company_id,
        channel=payload.channel,
    )
    db.commit()
    return result
