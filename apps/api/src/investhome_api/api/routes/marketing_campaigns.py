"""Marketing campaign management API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing import (
    MarketingCampaignCreate,
    MarketingCampaignCreateResponse,
    MarketingCampaignDetail,
    MarketingCampaignListResponse,
    MarketingCampaignUpdate,
    MarketingWorkspaceOverviewResponse,
)
from investhome_api.schemas.marketing_campaigns import (
    CampaignApprovalAction,
    CampaignArchiveRequest,
    CampaignBriefResponse,
    CampaignBriefUpdate,
    CampaignBudgetAllocationCreate,
    CampaignBudgetAllocationResponse,
    CampaignBudgetAllocationUpdate,
    CampaignBulkActionRequest,
    CampaignBulkActionResult,
    CampaignChannelAssignmentCreate,
    CampaignChannelAssignmentResponse,
    CampaignDeleteRequest,
    CampaignDuplicateRequest,
    CampaignLeadContextResponse,
    CampaignMilestoneCreate,
    CampaignMilestoneResponse,
    CampaignMilestoneUpdate,
    CampaignOverviewResponse,
    CampaignReadinessResponse,
    CampaignSavedViewCreate,
    CampaignSavedViewResponse,
    CampaignSavedViewUpdate,
    CampaignSpendAdjustment,
    CampaignStatusTransitionRequest,
    CampaignStatusTransitionResponse,
    CampaignSummaryStats,
    CampaignTargetCreate,
    CampaignTargetResponse,
    CampaignTemplateCreate,
    CampaignTemplateResponse,
    CampaignTrackingResponse,
    CampaignTrackingUpdate,
    CampaignAnalyticsShell,
    CampaignAttributionShell,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_created,
    log_entity_deleted,
    log_entity_updated,
)
from investhome_api.services.marketing.campaign_service import (
    activate_campaign,
    adjust_spend,
    approve_campaign,
    archive_campaign,
    assign_channel,
    bulk_action,
    cancel_campaign,
    complete_campaign,
    compute_pages,
    create_budget_allocation,
    create_campaign,
    create_milestone,
    create_saved_view,
    create_target,
    create_template,
    delete_campaign,
    delete_milestone,
    delete_saved_view,
    duplicate_campaign,
    export_campaigns_csv,
    get_campaign,
    get_campaign_overview,
    get_channel_assignment,
    get_milestone,
    get_saved_view,
    get_workspace_overview,
    list_budget_allocations,
    list_campaign_leads,
    list_campaigns,
    list_channel_assignments,
    list_milestones,
    list_saved_views,
    list_targets,
    list_templates,
    pause_campaign,
    reject_campaign,
    restore_campaign,
    resume_campaign,
    schedule_campaign,
    submit_for_approval,
    unlink_channel,
    update_brief,
    update_budget_allocation,
    update_campaign,
    update_milestone,
    update_saved_view,
    update_tracking,
    validate_status_transition_query,
    validate_tracking,
    campaign_to_detail,
    compute_readiness,
    get_campaign_summary_stats,
    get_or_create_brief,
)

router = APIRouter(prefix="/marketing/campaigns", tags=["marketing-campaigns"])

_campaign_read = require_any_permission(
    ("marketing", "view"),
    ("marketing", "manage_campaigns"),
    ("marketing", "view_dashboard"),
)
_campaign_write = require_any_permission(
    ("marketing", "manage_campaigns"),
    ("marketing", "create"),
    ("marketing", "update"),
)


def _log_campaign_status_change(
    db: Session,
    *,
    campaign_id: UUID,
    description_key: str,
    before_status: str,
    after_status: str,
    actor: User,
    request: Request,
    metadata: dict | None = None,
) -> None:
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
        entity_id=campaign_id,
        description_key=description_key,
        actor=actor,
        before={"status": before_status},
        after={"status": after_status},
        metadata=metadata,
        request=request,
    )


@router.get("", response_model=MarketingCampaignListResponse)
def list_campaigns_route(
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_read),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    campaign_type: str | None = Query(None),
    objective: str | None = Query(None),
    owner_user_id: UUID | None = Query(None),
    project_id: UUID | None = Query(None),
    primary_channel: str | None = Query(None),
    search: str | None = Query(None),
    include_archived: bool = Query(False),
    missing_owner: bool = Query(False),
    missing_budget: bool = Query(False),
    missing_tracking: bool = Query(False),
    my_campaigns: bool = Query(False),
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc"),
) -> MarketingCampaignListResponse:
    owner_only = user.id if my_campaigns else None
    items, total = list_campaigns(
        db,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        campaign_type=campaign_type,
        objective=objective,
        owner_user_id=owner_user_id,
        project_id=project_id,
        primary_channel=primary_channel,
        search=search,
        include_archived=include_archived,
        missing_owner=missing_owner,
        missing_budget=missing_budget,
        missing_tracking=missing_tracking,
        owner_only=owner_only,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return MarketingCampaignListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=compute_pages(total, page_size),
    )


@router.get("/overview", response_model=MarketingWorkspaceOverviewResponse)
def get_campaigns_workspace_overview(
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_read),
) -> MarketingWorkspaceOverviewResponse:
    return get_workspace_overview(db)


@router.get("/export")
def export_campaigns_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "export")),
    status_filter: str | None = Query(None, alias="status"),
    campaign_type: str | None = Query(None),
    owner_user_id: UUID | None = Query(None),
    project_id: UUID | None = Query(None),
    primary_channel: str | None = Query(None),
    search: str | None = Query(None),
    include_archived: bool = Query(False),
) -> Response:
    content = export_campaigns_csv(
        db,
        status_filter=status_filter,
        campaign_type=campaign_type,
        owner_user_id=owner_user_id,
        project_id=project_id,
        primary_channel=primary_channel,
        search=search,
        include_archived=include_archived,
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="marketing-campaigns-export.csv"'},
    )


@router.get("/summary", response_model=CampaignSummaryStats)
def get_campaigns_summary(
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_read),
    my_campaigns: bool = Query(False),
) -> CampaignSummaryStats:
    owner_only = user.id if my_campaigns else None
    return get_campaign_summary_stats(db, owner_only=owner_only)


@router.get("/saved-views", response_model=list[CampaignSavedViewResponse])
def get_campaign_saved_views(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> list[CampaignSavedViewResponse]:
    return list_saved_views(db, user.id)


@router.post("/saved-views", response_model=CampaignSavedViewResponse, status_code=status.HTTP_201_CREATED)
def post_campaign_saved_view(
    payload: CampaignSavedViewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignSavedViewResponse:
    view = create_saved_view(db, user_id=user.id, payload=payload)
    db.commit()
    return view


@router.put("/saved-views/{view_id}", response_model=CampaignSavedViewResponse)
def put_campaign_saved_view(
    view_id: UUID,
    payload: CampaignSavedViewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignSavedViewResponse:
    view = get_saved_view(db, view_id)
    if view.user_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your saved view")
    result = update_saved_view(db, view=view, payload=payload)
    db.commit()
    return result


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_saved_view(
    view_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> None:
    view = get_saved_view(db, view_id)
    if view.user_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your saved view")
    delete_saved_view(db, view)
    db.commit()


@router.get("/templates", response_model=list[CampaignTemplateResponse])
def get_campaign_templates(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> list[CampaignTemplateResponse]:
    return list_templates(db)


@router.post("/templates", response_model=CampaignTemplateResponse, status_code=status.HTTP_201_CREATED)
def post_campaign_template(
    payload: CampaignTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignTemplateResponse:
    result = create_template(db, payload=payload, actor=user)
    db.commit()
    return result


@router.post("/bulk", response_model=CampaignBulkActionResult)
def post_campaign_bulk_action(
    payload: CampaignBulkActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignBulkActionResult:
    result = bulk_action(db, payload=payload, actor=user)
    for item in result.results or []:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
            entity_id=UUID(item["id"]),
            description_key="marketing.campaign.bulk_action",
            actor=user,
            before={"status": "unknown"},
            after={"action": payload.action, "status": item.get("status", "unknown")},
            request=request,
        )
    db.commit()
    return result


@router.post("", response_model=MarketingCampaignCreateResponse, status_code=status.HTTP_201_CREATED)
def create_campaign_route(
    payload: MarketingCampaignCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_write),
) -> MarketingCampaignCreateResponse:
    campaign = create_campaign(db, payload=payload, actor=user)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
        entity_id=campaign.id,
        description_key="marketing.campaign.created",
        actor=user,
        request=request,
    )
    if campaign.target_project_id is not None:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
            entity_id=campaign.id,
            description_key="marketing.campaign.project_linked",
            actor=user,
            before={"target_project_id": None},
            after={"target_project_id": str(campaign.target_project_id)},
            request=request,
        )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.get("/{campaign_id}", response_model=MarketingCampaignDetail)
def get_campaign_route(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_read),
) -> MarketingCampaignDetail:
    return campaign_to_detail(db, get_campaign(db, campaign_id, include_archived=True))


@router.put("/{campaign_id}", response_model=MarketingCampaignCreateResponse)
def update_campaign_route(
    campaign_id: UUID,
    payload: MarketingCampaignUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_write),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before = {
        "status": campaign.status.value,
        "name": campaign.name,
        "budget_amount": str(campaign.budget_amount) if campaign.budget_amount is not None else None,
        "target_project_id": str(campaign.target_project_id) if campaign.target_project_id else None,
    }
    previous_project = campaign.target_project_id
    previous_budget = campaign.budget_amount
    campaign = update_campaign(db, campaign=campaign, payload=payload, actor=user)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
        entity_id=campaign.id,
        description_key="marketing.campaign.updated",
        actor=user,
        before=before,
        after={
            "status": campaign.status.value,
            "name": campaign.name,
            "budget_amount": str(campaign.budget_amount) if campaign.budget_amount is not None else None,
            "target_project_id": str(campaign.target_project_id) if campaign.target_project_id else None,
        },
        request=request,
    )
    if "budget_amount" in payload.model_dump(exclude_unset=True) and previous_budget != campaign.budget_amount:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
            entity_id=campaign.id,
            description_key="marketing.campaign.budget_updated",
            actor=user,
            before={"budget_amount": str(previous_budget) if previous_budget is not None else None},
            after={"budget_amount": str(campaign.budget_amount) if campaign.budget_amount is not None else None},
            request=request,
        )
    if (
        "target_project_id" in payload.model_dump(exclude_unset=True)
        and previous_project != campaign.target_project_id
        and campaign.target_project_id is not None
    ):
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
            entity_id=campaign.id,
            description_key="marketing.campaign.project_linked",
            actor=user,
            before={"target_project_id": str(previous_project) if previous_project else None},
            after={"target_project_id": str(campaign.target_project_id)},
            request=request,
        )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_route(
    campaign_id: UUID,
    payload: CampaignDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "delete")),
) -> None:
    campaign = get_campaign(db, campaign_id)
    log_entity_deleted(
        db,
        entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
        entity_id=campaign.id,
        description_key="marketing.campaign.deleted",
        actor=user,
        metadata={"reason": payload.reason},
        request=request,
    )
    delete_campaign(db, campaign=campaign, actor=user, reason=payload.reason)
    db.commit()


@router.post("/{campaign_id}/duplicate", response_model=MarketingCampaignCreateResponse, status_code=status.HTTP_201_CREATED)
def duplicate_campaign_route(
    campaign_id: UUID,
    payload: CampaignDuplicateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> MarketingCampaignCreateResponse:
    source = get_campaign(db, campaign_id, include_archived=True)
    clone = duplicate_campaign(db, campaign=source, actor=user, payload=payload)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_CAMPAIGN,
        entity_id=clone.id,
        description_key="marketing.campaign.duplicated",
        actor=user,
        metadata={"source_id": str(source.id)},
        request=request,
    )
    db.commit()
    db.refresh(clone)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, clone))


@router.get("/{campaign_id}/overview", response_model=CampaignOverviewResponse)
def get_campaign_overview_route(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_campaign_read),
) -> CampaignOverviewResponse:
    return get_campaign_overview(db, get_campaign(db, campaign_id))


@router.get("/{campaign_id}/readiness", response_model=CampaignReadinessResponse)
def get_campaign_readiness(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignReadinessResponse:
    return compute_readiness(db, get_campaign(db, campaign_id))


@router.post("/{campaign_id}/validate-transition", response_model=CampaignStatusTransitionResponse)
def validate_campaign_transition(
    campaign_id: UUID,
    payload: CampaignStatusTransitionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignStatusTransitionResponse:
    return validate_status_transition_query(get_campaign(db, campaign_id), payload.target_status)


@router.post("/{campaign_id}/submit-approval", response_model=MarketingCampaignCreateResponse)
def submit_campaign_approval(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = submit_for_approval(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db,
        campaign_id=campaign.id,
        description_key="marketing.campaign.submitted_for_approval",
        before_status=before_status,
        after_status=campaign.status.value,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/approve", response_model=MarketingCampaignCreateResponse)
def approve_campaign_route(
    campaign_id: UUID,
    payload: CampaignApprovalAction,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "approve_content")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = approve_campaign(db, campaign=campaign, actor=user, notes=payload.notes)
    _log_campaign_status_change(
        db,
        campaign_id=campaign.id,
        description_key="marketing.campaign.approved",
        before_status=before_status,
        after_status=campaign.status.value,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/reject", response_model=MarketingCampaignCreateResponse)
def reject_campaign_route(
    campaign_id: UUID,
    payload: CampaignApprovalAction,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "approve_content")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = reject_campaign(db, campaign=campaign, actor=user, notes=payload.notes)
    _log_campaign_status_change(
        db,
        campaign_id=campaign.id,
        description_key="marketing.campaign.rejected",
        before_status=before_status,
        after_status=campaign.status.value,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/schedule", response_model=MarketingCampaignCreateResponse)
def schedule_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = schedule_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.scheduled",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/activate", response_model=MarketingCampaignCreateResponse)
def activate_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "activate_campaign")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = activate_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.activated",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/pause", response_model=MarketingCampaignCreateResponse)
def pause_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "pause_campaign")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = pause_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.paused",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/resume", response_model=MarketingCampaignCreateResponse)
def resume_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "activate_campaign")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = resume_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.resumed",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/complete", response_model=MarketingCampaignCreateResponse)
def complete_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = complete_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.completed",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/cancel", response_model=MarketingCampaignCreateResponse)
def cancel_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = cancel_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.cancelled",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/archive", response_model=MarketingCampaignCreateResponse)
def archive_campaign_route(
    campaign_id: UUID,
    payload: CampaignArchiveRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "archive")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id)
    before_status = campaign.status.value
    campaign = archive_campaign(db, campaign=campaign, actor=user, reason=payload.reason)
    _log_campaign_status_change(
        db,
        campaign_id=campaign.id,
        description_key="marketing.campaign.archived",
        before_status=before_status,
        after_status=campaign.status.value,
        actor=user,
        request=request,
        metadata={"reason": payload.reason},
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.post("/{campaign_id}/restore", response_model=MarketingCampaignCreateResponse)
def restore_campaign_route(
    campaign_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "archive")),
) -> MarketingCampaignCreateResponse:
    campaign = get_campaign(db, campaign_id, include_archived=True)
    before_status = campaign.status.value
    campaign = restore_campaign(db, campaign=campaign, actor=user)
    _log_campaign_status_change(
        db, campaign_id=campaign.id, description_key="marketing.campaign.restored",
        before_status=before_status, after_status=campaign.status.value, actor=user, request=request,
    )
    db.commit()
    db.refresh(campaign)
    return MarketingCampaignCreateResponse(campaign=campaign_to_detail(db, campaign))


@router.get("/{campaign_id}/brief", response_model=CampaignBriefResponse)
def get_campaign_brief(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignBriefResponse:
    brief = get_or_create_brief(db, campaign_id)
    db.commit()
    return CampaignBriefResponse.model_validate(brief)


@router.put("/{campaign_id}/brief", response_model=CampaignBriefResponse)
def put_campaign_brief(
    campaign_id: UUID,
    payload: CampaignBriefUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignBriefResponse:
    get_campaign(db, campaign_id)
    result = update_brief(db, campaign_id=campaign_id, payload=payload, actor=user)
    db.commit()
    return result


@router.get("/{campaign_id}/milestones", response_model=list[CampaignMilestoneResponse])
def get_campaign_milestones(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> list[CampaignMilestoneResponse]:
    return list_milestones(db, campaign_id)


@router.post("/{campaign_id}/milestones", response_model=CampaignMilestoneResponse, status_code=status.HTTP_201_CREATED)
def post_campaign_milestone(
    campaign_id: UUID,
    payload: CampaignMilestoneCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignMilestoneResponse:
    get_campaign(db, campaign_id)
    result = create_milestone(db, campaign_id=campaign_id, payload=payload, actor=user)
    db.commit()
    return result


@router.put("/{campaign_id}/milestones/{milestone_id}", response_model=CampaignMilestoneResponse)
def put_campaign_milestone(
    campaign_id: UUID,
    milestone_id: UUID,
    payload: CampaignMilestoneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignMilestoneResponse:
    milestone = get_milestone(db, milestone_id)
    if milestone.campaign_id != campaign_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    result = update_milestone(db, milestone=milestone, payload=payload, actor=user)
    db.commit()
    return result


@router.delete("/{campaign_id}/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_milestone(
    campaign_id: UUID,
    milestone_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> None:
    milestone = get_milestone(db, milestone_id)
    if milestone.campaign_id != campaign_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    delete_milestone(db, milestone)
    db.commit()


@router.get("/{campaign_id}/channels", response_model=list[CampaignChannelAssignmentResponse])
def get_campaign_channels(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> list[CampaignChannelAssignmentResponse]:
    return list_channel_assignments(db, campaign_id)


@router.post("/{campaign_id}/channels", response_model=CampaignChannelAssignmentResponse, status_code=status.HTTP_201_CREATED)
def post_campaign_channel(
    campaign_id: UUID,
    payload: CampaignChannelAssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignChannelAssignmentResponse:
    get_campaign(db, campaign_id)
    result = assign_channel(db, campaign_id=campaign_id, payload=payload)
    db.commit()
    return result


@router.delete("/{campaign_id}/channels/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_channel(
    campaign_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> None:
    assignment = get_channel_assignment(db, assignment_id)
    if assignment.campaign_id != campaign_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    unlink_channel(db, assignment)
    db.commit()


@router.get("/{campaign_id}/budget", response_model=list[CampaignBudgetAllocationResponse])
def get_campaign_budget(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_budgets")),
) -> list[CampaignBudgetAllocationResponse]:
    return list_budget_allocations(db, campaign_id)


@router.post("/{campaign_id}/budget", response_model=CampaignBudgetAllocationResponse, status_code=status.HTTP_201_CREATED)
def post_campaign_budget(
    campaign_id: UUID,
    payload: CampaignBudgetAllocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_budgets")),
) -> CampaignBudgetAllocationResponse:
    get_campaign(db, campaign_id)
    result = create_budget_allocation(db, campaign_id=campaign_id, payload=payload, actor=user)
    db.commit()
    return result


@router.put("/{campaign_id}/budget/{allocation_id}", response_model=CampaignBudgetAllocationResponse)
def put_campaign_budget(
    campaign_id: UUID,
    allocation_id: UUID,
    payload: CampaignBudgetAllocationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_budgets")),
) -> CampaignBudgetAllocationResponse:
    from investhome_api.models.marketing import CampaignBudgetAllocation
    allocation = db.get(CampaignBudgetAllocation, allocation_id)
    if allocation is None or allocation.campaign_id != campaign_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    result = update_budget_allocation(db, allocation=allocation, payload=payload)
    db.commit()
    return result


@router.post("/{campaign_id}/budget/spend", response_model=CampaignBudgetAllocationResponse)
def post_campaign_spend_adjustment(
    campaign_id: UUID,
    payload: CampaignSpendAdjustment,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_spend")),
) -> CampaignBudgetAllocationResponse:
    result = adjust_spend(db, campaign_id=campaign_id, payload=payload, actor=user)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_BUDGET,
        entity_id=result.id,
        description_key="marketing.campaign.spend_adjusted",
        actor=user,
        before={"spent_amount": None},
        after={"spent_amount": str(result.spent_amount) if result.spent_amount is not None else None},
        metadata={"amount": str(payload.amount), "reason": payload.reason},
        request=request,
    )
    db.commit()
    return result


@router.get("/{campaign_id}/tracking", response_model=CampaignTrackingResponse)
def get_campaign_tracking(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignTrackingResponse:
    from investhome_api.services.marketing.campaign_service import get_or_create_tracking
    tracking = get_or_create_tracking(db, campaign_id)
    db.commit()
    return CampaignTrackingResponse.model_validate(tracking)


@router.put("/{campaign_id}/tracking", response_model=CampaignTrackingResponse)
def put_campaign_tracking(
    campaign_id: UUID,
    payload: CampaignTrackingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignTrackingResponse:
    get_campaign(db, campaign_id)
    result = update_tracking(db, campaign_id=campaign_id, payload=payload)
    db.commit()
    return result


@router.post("/{campaign_id}/tracking/validate", response_model=CampaignTrackingResponse)
def post_campaign_tracking_validate(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignTrackingResponse:
    result = validate_tracking(db, campaign_id)
    db.commit()
    return result


@router.get("/{campaign_id}/targets", response_model=list[CampaignTargetResponse])
def get_campaign_targets(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> list[CampaignTargetResponse]:
    return list_targets(db, campaign_id)


@router.post("/{campaign_id}/targets", response_model=CampaignTargetResponse, status_code=status.HTTP_201_CREATED)
def post_campaign_target(
    campaign_id: UUID,
    payload: CampaignTargetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_campaigns")),
) -> CampaignTargetResponse:
    get_campaign(db, campaign_id)
    result = create_target(db, campaign_id=campaign_id, payload=payload)
    db.commit()
    return result


@router.get("/{campaign_id}/leads", response_model=list[CampaignLeadContextResponse])
def get_campaign_leads(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_leads")),
) -> list[CampaignLeadContextResponse]:
    return list_campaign_leads(db, campaign_id)


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalyticsShell)
def get_campaign_analytics(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "export_analytics")),
) -> CampaignAnalyticsShell:
    from investhome_api.services.marketing.campaign_performance_service import get_campaign_performance_detail

    campaign = get_campaign(db, campaign_id)
    detail = get_campaign_performance_detail(db, campaign)
    metrics = detail.metrics.model_dump(mode="json")
    has_leads = (detail.metrics.total_leads.value or 0) > 0
    has_spend = detail.metrics.actual_spend.state == "ready"
    state = "ready" if has_leads or has_spend or detail.metrics.planned_budget.state == "ready" else "no_data"
    return CampaignAnalyticsShell(
        state=state,
        message_key=(
            "marketing.campaign.analytics.ready"
            if state == "ready"
            else "marketing.campaign.analytics.no_data"
        ),
        metrics={
            **metrics,
            "status_breakdown": detail.status_breakdown,
            "spend_vs_budget": detail.spend_vs_budget,
            "lead_trend": detail.lead_trend,
        },
    )


@router.get("/{campaign_id}/attribution", response_model=CampaignAttributionShell)
def get_campaign_attribution(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
) -> CampaignAttributionShell:
    from investhome_api.services.marketing.campaign_performance_service import get_campaign_performance_detail

    campaign = get_campaign(db, campaign_id)
    detail = get_campaign_performance_detail(db, campaign)
    has_data = bool(detail.recent_leads) or bool(detail.top_sources) or bool(detail.utm_breakdown)
    return CampaignAttributionShell(
        state="ready" if has_data else "no_data",
        message_key=(
            "marketing.campaign.attribution.ready"
            if has_data
            else "marketing.campaign.attribution.no_data"
        ),
        channels=[
            *[{"type": "source", **row} for row in detail.top_sources],
            *[{"type": "utm", **row} for row in detail.utm_breakdown],
            *[{"type": "lead", "lead_id": str(row.lead_id), "name": row.full_name} for row in detail.recent_leads],
        ],
    )
