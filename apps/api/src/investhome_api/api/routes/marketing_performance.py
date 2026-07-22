"""Campaign performance and lead attribution API — Sprint 8A3."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.marketing_lead_attribution import MarketingLeadAttribution
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_performance import (
    CampaignLeadBreakdownResponse,
    CampaignPerformanceDetail,
    CampaignPerformanceListResponse,
    ChannelPerformanceResponse,
    LeadAttributionCreate,
    LeadAttributionListResponse,
    LeadAttributionResponse,
    LeadAttributionUpdate,
    MarketingPerformanceOverview,
    PerformanceFilters,
    ProjectPerformanceResponse,
)
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity
from investhome_api.services.marketing import campaign_performance_service as perf_svc
from investhome_api.services.marketing import lead_attribution_service as attrib_svc
from investhome_api.services.marketing.campaign_service import get_campaign

router = APIRouter(prefix="/marketing/performance", tags=["marketing-performance"])

_VIEW = require_any_permission(
    ("marketing", "view"),
    ("marketing", "view_dashboard"),
    ("marketing", "view_attribution"),
)
_EDIT_ATTRIB = require_any_permission(
    ("marketing", "manage_campaigns"),
    ("leads", "update"),
)
_EXPORT = require_any_permission(("marketing", "export"), ("marketing", "export_analytics"))
_VIEW_LEADS = require_any_permission(("marketing", "view_leads"), ("leads", "view"), ("crm", "read"))

_EXPORT_ENTITY_ID = UUID("00000000-0000-0000-0000-000000000053")


def _filters_from_query(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    campaign_id: UUID | None = None,
    project_id: UUID | None = None,
    campaign_type: str | None = None,
    owner_user_id: UUID | None = None,
    status_filter: str | None = None,
    company_id: UUID | None = None,
) -> PerformanceFilters:
    return PerformanceFilters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        project_id=project_id,
        campaign_type=campaign_type,
        owner_user_id=owner_user_id,
        status=status_filter,
        company_id=company_id,
    )


@router.get("/overview", response_model=MarketingPerformanceOverview)
def performance_overview(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    campaign_type: str | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW),
) -> MarketingPerformanceOverview:
    return perf_svc.get_performance_overview(
        db,
        filters=_filters_from_query(
            date_from, date_to, campaign_id, project_id, campaign_type, owner_user_id, status_filter, company_id
        ),
    )


@router.get("/campaigns", response_model=CampaignPerformanceListResponse)
def list_campaign_performance(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    campaign_type: str | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: UUID | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort_by: str | None = Query(default=None),
    sort_dir: str = Query(default="desc"),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW),
) -> CampaignPerformanceListResponse:
    return perf_svc.list_campaign_performance(
        db,
        filters=_filters_from_query(
            date_from, date_to, campaign_id, project_id, campaign_type, owner_user_id, status_filter, company_id
        ),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignPerformanceDetail)
def campaign_performance_detail(
    campaign_id: UUID,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW),
) -> CampaignPerformanceDetail:
    campaign = get_campaign(db, campaign_id)
    return perf_svc.get_campaign_performance_detail(db, campaign, date_from=date_from, date_to=date_to)


@router.get("/campaigns/{campaign_id}/leads", response_model=CampaignLeadBreakdownResponse)
def campaign_attributed_leads(
    campaign_id: UUID,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW_LEADS),
) -> CampaignLeadBreakdownResponse:
    get_campaign(db, campaign_id)
    return perf_svc.get_campaign_lead_breakdown(
        db, campaign_id, page=page, page_size=page_size, date_from=date_from, date_to=date_to
    )


@router.get("/channels", response_model=ChannelPerformanceResponse)
def channel_performance(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    campaign_type: str | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW),
) -> ChannelPerformanceResponse:
    return perf_svc.get_channel_performance(
        db,
        filters=_filters_from_query(
            date_from, date_to, campaign_id, project_id, campaign_type, owner_user_id, status_filter, company_id
        ),
    )


@router.get("/projects", response_model=ProjectPerformanceResponse)
def project_performance(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    campaign_type: str | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW),
) -> ProjectPerformanceResponse:
    return perf_svc.get_project_performance(
        db,
        filters=_filters_from_query(
            date_from, date_to, campaign_id, project_id, campaign_type, owner_user_id, status_filter, company_id
        ),
    )


@router.get("/export/{report_type}")
def export_performance(
    report_type: str,
    request: Request,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    campaign_type: str | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_EXPORT),
) -> Response:
    if report_type not in {"campaign", "campaigns", "channel", "project", "lead_attribution"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported report type")
    normalized = "campaign" if report_type == "campaigns" else report_type
    csv_text = perf_svc.export_performance_csv(
        db,
        report_type=normalized,
        filters=_filters_from_query(
            date_from, date_to, campaign_id, project_id, campaign_type, owner_user_id, status_filter, company_id
        ),
    )
    log_activity(
        db,
        action=ActivityAction.EXPORTED,
        entity_type=ActivityEntityType.MARKETING_ATTRIBUTION,
        entity_id=_EXPORT_ENTITY_ID,
        description_key="marketing.performance.exported",
        actor_user=user,
        metadata={"report_type": normalized},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    filename = f"marketing_{normalized}_performance.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/attributions", response_model=LeadAttributionListResponse)
def list_attributions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    campaign_id: UUID | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW),
) -> LeadAttributionListResponse:
    rows, total = attrib_svc.list_attributions(
        db, page=page, page_size=page_size, campaign_id=campaign_id, company_id=company_id, lead_id=lead_id
    )
    return LeadAttributionListResponse(
        items=[attrib_svc.attribution_to_response(db, row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/attributions/by-lead/{lead_id}", response_model=LeadAttributionResponse | None)
def get_attribution_for_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(_VIEW_LEADS),
) -> LeadAttributionResponse | None:
    row = attrib_svc.get_attribution_by_lead(db, lead_id)
    if row is None:
        return None
    return attrib_svc.attribution_to_response(db, row)


@router.post("/attributions", response_model=LeadAttributionResponse, status_code=status.HTTP_201_CREATED)
def create_attribution(
    payload: LeadAttributionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT_ATTRIB),
) -> LeadAttributionResponse:
    result = attrib_svc.create_attribution(db, payload, actor=user)
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.MARKETING_ATTRIBUTION,
        entity_id=result.id,
        description_key="marketing.attribution.attributed",
        actor_user=user,
        metadata={
            "lead_id": str(result.lead_id),
            "campaign_id": str(result.campaign_id) if result.campaign_id else None,
            "reason": payload.attribution_reason,
        },
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return result


@router.put("/attributions/{attribution_id}", response_model=LeadAttributionResponse)
@router.patch("/attributions/{attribution_id}", response_model=LeadAttributionResponse)
def update_attribution(
    attribution_id: UUID,
    payload: LeadAttributionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT_ATTRIB),
) -> LeadAttributionResponse:
    row = db.get(MarketingLeadAttribution, attribution_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribution not found")
    previous = row.campaign_id
    result = attrib_svc.update_attribution(db, row, payload, actor=user)
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.MARKETING_ATTRIBUTION,
        entity_id=result.id,
        description_key="marketing.attribution.changed",
        actor_user=user,
        metadata={
            "lead_id": str(result.lead_id),
            "previous_campaign_id": str(previous) if previous else None,
            "new_campaign_id": str(result.campaign_id) if result.campaign_id else None,
            "reason": payload.attribution_reason,
        },
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return result


@router.delete("/attributions/{attribution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attribution(
    attribution_id: UUID,
    request: Request,
    reason: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT_ATTRIB),
) -> Response:
    row = db.get(MarketingLeadAttribution, attribution_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribution not found")
    lead_id = row.lead_id
    previous = row.campaign_id
    attrib_svc.delete_attribution(db, row, actor=user, reason=reason)
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=ActivityEntityType.MARKETING_ATTRIBUTION,
        entity_id=attribution_id,
        description_key="marketing.attribution.removed",
        actor_user=user,
        metadata={
            "lead_id": str(lead_id),
            "previous_campaign_id": str(previous) if previous else None,
            "reason": reason,
        },
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
