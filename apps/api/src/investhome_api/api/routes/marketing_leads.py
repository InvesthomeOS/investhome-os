"""Marketing lead context API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_audience_segment import (
    HandoffReadinessResponse,
    HandoffResponse,
    MarketingLeadDetailResponse,
    MarketingLeadSummary,
    MarketingLeadSummaryStats,
)
from investhome_api.services.activity_recorder import log_entity_updated
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.marketing_lead_service import (
    get_handoff_readiness,
    get_marketing_lead_detail,
    get_marketing_lead_summary,
    hand_marketing_lead_to_sales,
    list_marketing_leads,
    suppress_marketing_lead,
    update_marketing_lead_scores,
    verify_marketing_lead,
)

router = APIRouter(prefix="/marketing/leads", tags=["marketing-leads"])


@router.get("/summary", response_model=MarketingLeadSummaryStats)
def leads_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_leads")),
) -> MarketingLeadSummaryStats:
    return MarketingLeadSummaryStats(**get_marketing_lead_summary(db))


@router.get("")
def list_leads(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_leads")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    campaign_id: UUID | None = None,
    source_id: UUID | None = None,
    handoff_status: str | None = None,
) -> dict:
    rows, total = list_marketing_leads(
        db, page=page, page_size=page_size,
        campaign_id=campaign_id, source_id=source_id, handoff_status=handoff_status,
    )
    items = [
        MarketingLeadSummary(
            id=r.id,
            lead_id=r.lead_id,
            contact_id=r.contact_id,
            company_id=r.company_id,
            campaign_id=r.campaign_id,
            source_id=r.source_id,
            channel_id=r.channel_id,
            utm_data_json=r.utm_data_json,
            marketing_status=r.marketing_status,
            verification_status=r.verification_status,
            handoff_status=r.handoff_status.value,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.get("/{context_id}", response_model=MarketingLeadDetailResponse)
def get_lead_detail(
    context_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_leads")),
) -> MarketingLeadDetailResponse:
    data = get_marketing_lead_detail(db, context_id)
    ctx = data["context"]
    return MarketingLeadDetailResponse(
        id=ctx.id,
        lead_id=ctx.lead_id,
        contact_id=ctx.contact_id,
        company_id=ctx.company_id,
        campaign_id=ctx.campaign_id,
        source_id=ctx.source_id,
        attribution_json=ctx.attribution_json,
        utm_data_json=ctx.utm_data_json,
        scores_json=data["scores"],
        consent_status=data["consent_status"],
        marketing_status=ctx.marketing_status,
        verification_status=ctx.verification_status,
        handoff_status=ctx.handoff_status.value,
    )


@router.get("/{context_id}/handoff-readiness", response_model=HandoffReadinessResponse)
def handoff_readiness(
    context_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_leads")),
) -> HandoffReadinessResponse:
    return HandoffReadinessResponse(**get_handoff_readiness(db, context_id))


@router.post("/{context_id}/handoff", response_model=HandoffResponse)
def handoff_to_sales(
    context_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "hand_to_sales")),
) -> HandoffResponse:
    result = hand_marketing_lead_to_sales(db, context_id, user)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_LEAD_CONTEXT,
        entity_id=context_id,
        description_key="marketing.lead_context.handed_off",
        actor=user,
        before={},
        after=result,
        request=request,
    )
    db.commit()
    return HandoffResponse(**result)


@router.post("/{context_id}/verify")
def verify_lead(
    context_id: UUID,
    status: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "verify")),
) -> dict:
    ctx = verify_marketing_lead(db, context_id, status)
    db.commit()
    return {"id": str(ctx.id), "verification_status": ctx.verification_status}


@router.post("/{context_id}/scores")
def update_scores(
    context_id: UUID,
    scores: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_scores")),
) -> dict:
    ctx = update_marketing_lead_scores(db, context_id, scores)
    db.commit()
    return {"id": str(ctx.id), "scores_json": ctx.scores_json}


@router.post("/{context_id}/suppress")
def suppress_lead(
    context_id: UUID,
    reason: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_suppression")),
) -> dict:
    ctx = suppress_marketing_lead(db, context_id, reason)
    db.commit()
    return {"id": str(ctx.id), "handoff_status": ctx.handoff_status.value}
