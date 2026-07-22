"""Marketing campaign management service — lifecycle, readiness, approvals."""

from __future__ import annotations

import csv
import io
import math
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing import (
    CampaignBrief,
    CampaignBudgetAllocation,
    CampaignChannelAssignment,
    CampaignMilestone,
    CampaignMilestoneStatus,
    CampaignMilestoneType,
    CampaignSavedView,
    CampaignTarget,
    CampaignTemplate,
    CampaignTracking,
    CampaignTrackingReadiness,
    MarketingApproval,
    MarketingApprovalStatus,
    MarketingApprovalType,
    MarketingBudget,
    MarketingCampaign,
    MarketingCampaignObjective,
    MarketingCampaignPrimaryChannel,
    MarketingCampaignPriority,
    MarketingCampaignStatus,
    MarketingCampaignType,
    MarketingLeadContext,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing import (
    MarketingCampaignCreate,
    MarketingCampaignDetail,
    MarketingCampaignSummary,
    MarketingCampaignUpdate,
    MarketingMetricValue,
    MarketingWorkspaceOverviewResponse,
)
from investhome_api.schemas.marketing_campaigns import (
    CampaignApprovalAction,
    CampaignBriefResponse,
    CampaignBriefUpdate,
    CampaignBudgetAllocationCreate,
    CampaignBudgetAllocationResponse,
    CampaignBudgetAllocationUpdate,
    CampaignBulkActionRequest,
    CampaignBulkActionResult,
    CampaignChannelAssignmentCreate,
    CampaignChannelAssignmentResponse,
    CampaignDuplicateRequest,
    CampaignLeadContextResponse,
    CampaignMilestoneCreate,
    CampaignMilestoneResponse,
    CampaignMilestoneUpdate,
    CampaignOverviewResponse,
    CampaignReadinessCheck,
    CampaignReadinessResponse,
    CampaignSavedViewCreate,
    CampaignSavedViewResponse,
    CampaignSavedViewUpdate,
    CampaignSpendAdjustment,
    CampaignStatusTransitionResponse,
    CampaignSummaryStats,
    CampaignTargetCreate,
    CampaignTargetResponse,
    CampaignTemplateCreate,
    CampaignTemplateResponse,
    CampaignTrackingResponse,
    CampaignTrackingUpdate,
)

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"planning", "pending_approval", "archived", "cancelled"},
    "planning": {"pending_approval", "draft", "archived", "cancelled"},
    "pending_approval": {"approved", "draft", "cancelled"},
    "approved": {"scheduled", "active", "cancelled"},
    "scheduled": {"active", "paused", "cancelled"},
    "active": {"paused", "completed", "cancelled"},
    "paused": {"active", "completed", "cancelled"},
    "completed": {"archived"},
    "cancelled": {"archived", "draft"},
    "archived": {"draft"},
}


def validate_status_transition(current: str, target: str) -> None:
    allowed = VALID_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed and current != target:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition campaign from '{current}' to '{target}'. Allowed: {', '.join(sorted(allowed)) or 'none'}",
        )


def get_allowed_transitions(current: str) -> list[str]:
    return sorted(VALID_STATUS_TRANSITIONS.get(current, set()))


SORTABLE_CAMPAIGN_COLUMNS = {
    "name": MarketingCampaign.name,
    "status": MarketingCampaign.status,
    "campaign_type": MarketingCampaign.campaign_type,
    "start_date": MarketingCampaign.start_date,
    "end_date": MarketingCampaign.end_date,
    "budget_amount": MarketingCampaign.budget_amount,
    "updated_at": MarketingCampaign.updated_at,
    "created_at": MarketingCampaign.created_at,
}


def _metric(value: Decimal | int | float | None) -> MarketingMetricValue:
    return MarketingMetricValue(value=value, available=True)


def _unavailable(reason: str) -> MarketingMetricValue:
    return MarketingMetricValue(value=None, available=False, reason=reason)


def _sync_project_ids(project_ids: list[str] | None, target_project_id: UUID | None) -> list[str] | None:
    if target_project_id is None:
        return project_ids
    target = str(target_project_id)
    merged = list(project_ids or [])
    if target not in merged:
        merged.append(target)
    return merged


def _campaign_spent_amount(db: Session, campaign_id: UUID) -> Decimal | None:
    total = db.scalar(
        select(func.coalesce(func.sum(CampaignBudgetAllocation.spent_amount), 0)).where(
            CampaignBudgetAllocation.campaign_id == campaign_id
        )
    )
    if total is None:
        return None
    amount = Decimal(str(total))
    has_rows = db.scalar(
        select(func.count()).select_from(CampaignBudgetAllocation).where(
            CampaignBudgetAllocation.campaign_id == campaign_id
        )
    )
    if not has_rows:
        return None
    return amount


def _campaign_lead_count(db: Session, campaign_id: UUID) -> int:
    from investhome_api.models.marketing_lead_attribution import MarketingLeadAttribution

    return (
        db.scalar(
            select(func.count()).select_from(MarketingLeadAttribution).where(
                MarketingLeadAttribution.campaign_id == campaign_id
            )
        )
        or 0
    )


def _estimated_leads_from_campaign(campaign: MarketingCampaign) -> Decimal | None:
    targets = campaign.targets_json or {}
    for key in ("estimated_leads", "leads", "target_leads"):
        raw = targets.get(key)
        if raw is None:
            continue
        try:
            return Decimal(str(raw))
        except Exception:
            continue
    return None


def _to_summary(
    campaign: MarketingCampaign,
    *,
    spent_amount: Decimal | None = None,
    actual_leads: int | None = None,
) -> MarketingCampaignSummary:
    primary = campaign.primary_channel.value if campaign.primary_channel else None
    return MarketingCampaignSummary(
        id=campaign.id,
        name=campaign.name,
        code=campaign.code,
        objective=campaign.objective.value,
        campaign_type=campaign.campaign_type.value,
        status=campaign.status.value,
        priority=campaign.priority.value,
        owner_user_id=campaign.owner_user_id,
        company_id=campaign.company_id,
        target_project_id=campaign.target_project_id,
        lead_source_id=campaign.lead_source_id,
        primary_channel=primary,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        budget_amount=campaign.budget_amount,
        budget_currency=campaign.budget_currency,
        spent_amount=spent_amount,
        actual_leads=actual_leads,
        tags=campaign.tags,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _to_detail(db: Session, campaign: MarketingCampaign) -> MarketingCampaignDetail:
    spent = _campaign_spent_amount(db, campaign.id)
    leads = _campaign_lead_count(db, campaign.id)
    summary = _to_summary(campaign, spent_amount=spent, actual_leads=leads)
    remaining = None
    if campaign.budget_amount is not None and spent is not None:
        remaining = campaign.budget_amount - spent
    elif campaign.budget_amount is not None:
        remaining = campaign.budget_amount
    return MarketingCampaignDetail(
        **summary.model_dump(),
        description=campaign.description,
        team_id=campaign.team_id,
        project_ids=campaign.project_ids,
        property_ids=campaign.property_ids,
        audience_ids=campaign.audience_ids,
        segment_ids=campaign.segment_ids,
        channel_ids=campaign.channel_ids,
        timezone=campaign.timezone,
        targets_json=campaign.targets_json,
        notes=campaign.notes,
        metadata_json=campaign.metadata_json,
        archived_at=campaign.archived_at,
        remaining_budget=remaining,
    )


def create_campaign(
    db: Session,
    *,
    payload: MarketingCampaignCreate,
    actor: User,
) -> MarketingCampaign:
    primary_channel = None
    if payload.primary_channel:
        primary_channel = MarketingCampaignPrimaryChannel(payload.primary_channel)
    project_ids = _sync_project_ids(payload.project_ids, payload.target_project_id)
    metadata = dict(payload.metadata_json or {})
    metadata.setdefault("ai_automation_hooks", {"enabled": False, "prepared_for": ["8A2"]})
    campaign = MarketingCampaign(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        objective=MarketingCampaignObjective(payload.objective),
        campaign_type=MarketingCampaignType(payload.campaign_type),
        status=MarketingCampaignStatus.DRAFT,
        priority=MarketingCampaignPriority(payload.priority),
        owner_user_id=payload.owner_user_id or actor.id,
        team_id=payload.team_id,
        company_id=payload.company_id,
        target_project_id=payload.target_project_id,
        lead_source_id=payload.lead_source_id,
        primary_channel=primary_channel,
        project_ids=project_ids,
        property_ids=payload.property_ids,
        audience_ids=payload.audience_ids,
        segment_ids=payload.segment_ids,
        channel_ids=payload.channel_ids,
        start_date=payload.start_date,
        end_date=payload.end_date,
        timezone=payload.timezone,
        budget_amount=payload.budget_amount,
        budget_currency=payload.budget_currency,
        targets_json=payload.targets_json,
        tags=payload.tags,
        notes=payload.notes,
        metadata_json=metadata,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(campaign)
    db.flush()
    return campaign


def get_campaign(db: Session, campaign_id: UUID, *, include_archived: bool = False) -> MarketingCampaign:
    campaign = db.get(MarketingCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not include_archived and campaign.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


def list_campaigns(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    campaign_type: str | None = None,
    objective: str | None = None,
    owner_user_id: UUID | None = None,
    project_id: UUID | None = None,
    primary_channel: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
    missing_owner: bool = False,
    missing_budget: bool = False,
    missing_tracking: bool = False,
    owner_only: UUID | None = None,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
) -> tuple[list[MarketingCampaignSummary], int]:
    query = select(MarketingCampaign)
    if not include_archived:
        query = query.where(MarketingCampaign.archived_at.is_(None))
    if status_filter:
        query = query.where(MarketingCampaign.status == MarketingCampaignStatus(status_filter))
    if campaign_type:
        query = query.where(MarketingCampaign.campaign_type == campaign_type)
    if objective:
        query = query.where(MarketingCampaign.objective == objective)
    if owner_user_id:
        query = query.where(MarketingCampaign.owner_user_id == owner_user_id)
    if owner_only:
        query = query.where(MarketingCampaign.owner_user_id == owner_only)
    if primary_channel:
        query = query.where(MarketingCampaign.primary_channel == MarketingCampaignPrimaryChannel(primary_channel))
    if project_id:
        project_token = str(project_id)
        query = query.where(
            or_(
                MarketingCampaign.target_project_id == project_id,
                cast(MarketingCampaign.project_ids, String).contains(project_token),
            )
        )
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                MarketingCampaign.name.ilike(pattern),
                MarketingCampaign.code.ilike(pattern),
                MarketingCampaign.description.ilike(pattern),
            )
        )
    if missing_owner:
        query = query.where(MarketingCampaign.owner_user_id.is_(None))
    if missing_budget:
        query = query.where(MarketingCampaign.budget_amount.is_(None))
    if missing_tracking:
        tracked_ids = db.scalars(select(CampaignTracking.campaign_id)).all()
        query = query.where(MarketingCampaign.id.notin_(tracked_ids) if tracked_ids else True)

    sort_column = SORTABLE_CAMPAIGN_COLUMNS.get(sort_by, MarketingCampaign.updated_at)
    order_clause = sort_column.asc() if sort_dir.lower() == "asc" else sort_column.desc()

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(order_clause).offset((page - 1) * page_size).limit(page_size)).all()
    summaries: list[MarketingCampaignSummary] = []
    for row in rows:
        summaries.append(
            _to_summary(
                row,
                spent_amount=_campaign_spent_amount(db, row.id),
                actual_leads=_campaign_lead_count(db, row.id),
            )
        )
    return summaries, total


def list_campaigns_for_project(
    db: Session,
    project_id: UUID,
    *,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[MarketingCampaignSummary], int]:
    return list_campaigns(db, page=page, page_size=page_size, project_id=project_id)


def export_campaigns_csv(
    db: Session,
    *,
    status_filter: str | None = None,
    campaign_type: str | None = None,
    owner_user_id: UUID | None = None,
    project_id: UUID | None = None,
    primary_channel: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> str:
    items, _ = list_campaigns(
        db,
        page=1,
        page_size=10_000,
        status_filter=status_filter,
        campaign_type=campaign_type,
        owner_user_id=owner_user_id,
        project_id=project_id,
        primary_channel=primary_channel,
        search=search,
        include_archived=include_archived,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "name",
            "code",
            "status",
            "campaign_type",
            "primary_channel",
            "objective",
            "owner_user_id",
            "target_project_id",
            "lead_source_id",
            "start_date",
            "end_date",
            "budget_amount",
            "budget_currency",
            "spent_amount",
            "actual_leads",
            "created_at",
            "updated_at",
        ]
    )
    for item in items:
        writer.writerow(
            [
                str(item.id),
                item.name,
                item.code or "",
                item.status,
                item.campaign_type,
                item.primary_channel or "",
                item.objective,
                str(item.owner_user_id) if item.owner_user_id else "",
                str(item.target_project_id) if item.target_project_id else "",
                str(item.lead_source_id) if item.lead_source_id else "",
                item.start_date.isoformat() if item.start_date else "",
                item.end_date.isoformat() if item.end_date else "",
                str(item.budget_amount) if item.budget_amount is not None else "",
                item.budget_currency or "",
                str(item.spent_amount) if item.spent_amount is not None else "",
                str(item.actual_leads) if item.actual_leads is not None else "",
                item.created_at.isoformat() if item.created_at else "",
                item.updated_at.isoformat() if item.updated_at else "",
            ]
        )
    return buffer.getvalue()


def _from_performance_metric(metric) -> MarketingMetricValue:
    from investhome_api.schemas.marketing_performance import PerformanceMetricValue

    if isinstance(metric, PerformanceMetricValue):
        return MarketingMetricValue(
            value=metric.value,
            available=metric.state == "ready",
            reason=metric.reason,
        )
    return metric


def get_workspace_overview(db: Session) -> MarketingWorkspaceOverviewResponse:
    from investhome_api.services.marketing.campaign_performance_service import build_performance_overview

    overview = build_performance_overview(db)
    base = select(MarketingCampaign).where(MarketingCampaign.archived_at.is_(None))
    campaigns = list(db.scalars(base).all())
    budget_values = [c.budget_amount for c in campaigns if c.budget_amount is not None]
    currencies = {c.budget_currency for c in campaigns if c.budget_currency}
    currency = next(iter(currencies)) if len(currencies) == 1 else (None if not currencies else "MIXED")

    now = datetime.now(UTC)
    upcoming_rows = [
        c
        for c in campaigns
        if c.start_date is not None and c.start_date > now and c.status != MarketingCampaignStatus.CANCELLED
    ]
    upcoming_rows.sort(key=lambda c: c.start_date or now)
    upcoming_summaries = [_to_summary(c) for c in upcoming_rows[:10]]

    estimated_leads_total = Decimal("0")
    estimated_leads_available = False
    for campaign in campaigns:
        estimated = _estimated_leads_from_campaign(campaign)
        if estimated is not None:
            estimated_leads_total += estimated
            estimated_leads_available = True

    return MarketingWorkspaceOverviewResponse(
        total_campaigns=_from_performance_metric(overview.total_campaigns),
        active_campaigns=_from_performance_metric(overview.active_campaigns),
        budget=_from_performance_metric(overview.total_budget),
        spend=_from_performance_metric(overview.total_spend),
        estimated_leads=(
            _metric(estimated_leads_total) if estimated_leads_available else _unavailable("no_estimated_leads")
        ),
        actual_leads=_from_performance_metric(overview.total_leads),
        estimated_roi=_unavailable("roi_requires_revenue_and_spend"),
        top_performing=_from_performance_metric(overview.avg_conversion_rate),
        upcoming=_metric(len(upcoming_rows)),
        currency=currency or overview.currency,
        upcoming_campaigns=upcoming_summaries,
        qualified_leads=_from_performance_metric(overview.qualified_leads),
        converted_leads=_from_performance_metric(overview.converted_leads),
        avg_cpl=_from_performance_metric(overview.avg_cpl),
        avg_conversion_rate=_from_performance_metric(overview.avg_conversion_rate),
        campaigns_requiring_attention=_from_performance_metric(overview.campaigns_requiring_attention),
    )


def get_campaign_summary_stats(db: Session, *, owner_only: UUID | None = None) -> CampaignSummaryStats:
    query = select(MarketingCampaign.status, func.count()).where(MarketingCampaign.archived_at.is_(None))
    if owner_only:
        query = query.where(MarketingCampaign.owner_user_id == owner_only)
    query = query.group_by(MarketingCampaign.status)
    counts = {row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in db.execute(query).all()}
    archived_count = db.scalar(
        select(func.count()).select_from(MarketingCampaign).where(MarketingCampaign.archived_at.is_not(None))
    ) or 0
    return CampaignSummaryStats(
        total=sum(counts.values()),
        draft=counts.get("draft", 0),
        planning=counts.get("planning", 0),
        pending_approval=counts.get("pending_approval", 0),
        approved=counts.get("approved", 0),
        scheduled=counts.get("scheduled", 0),
        active=counts.get("active", 0),
        paused=counts.get("paused", 0),
        completed=counts.get("completed", 0),
        cancelled=counts.get("cancelled", 0),
        archived=archived_count,
    )


def update_campaign(
    db: Session,
    *,
    campaign: MarketingCampaign,
    payload: MarketingCampaignUpdate,
    actor: User,
) -> MarketingCampaign:
    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] != campaign.status.value:
        validate_status_transition(campaign.status.value, update_data["status"])
    enum_fields = {
        "objective": MarketingCampaignObjective,
        "campaign_type": MarketingCampaignType,
        "status": MarketingCampaignStatus,
        "priority": MarketingCampaignPriority,
        "primary_channel": MarketingCampaignPrimaryChannel,
    }
    if "target_project_id" in update_data or "project_ids" in update_data:
        target = update_data.get("target_project_id", campaign.target_project_id)
        project_ids = update_data.get("project_ids", campaign.project_ids)
        update_data["project_ids"] = _sync_project_ids(project_ids, target)
    for field, value in update_data.items():
        if field in enum_fields and value is not None:
            setattr(campaign, field, enum_fields[field](value))
        elif field in enum_fields and value is None:
            setattr(campaign, field, None)
        else:
            setattr(campaign, field, value)
    campaign.updated_by_user_id = actor.id
    db.flush()
    return campaign


def _transition_status(
    db: Session,
    *,
    campaign: MarketingCampaign,
    target: MarketingCampaignStatus,
    actor: User,
) -> MarketingCampaign:
    validate_status_transition(campaign.status.value, target.value)
    campaign.status = target
    campaign.updated_by_user_id = actor.id
    db.flush()
    return campaign


def submit_for_approval(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.PENDING_APPROVAL, actor=actor)
    approval = MarketingApproval(
        entity_type="campaign",
        entity_id=campaign.id,
        approval_type=MarketingApprovalType.CAMPAIGN,
        status=MarketingApprovalStatus.PENDING,
        requested_by_user_id=actor.id,
    )
    db.add(approval)
    db.flush()
    return campaign


def approve_campaign(
    db: Session,
    *,
    campaign: MarketingCampaign,
    actor: User,
    notes: str | None = None,
) -> MarketingCampaign:
    if campaign.status != MarketingCampaignStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Campaign is not pending approval")
    _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.APPROVED, actor=actor)
    pending = db.scalars(
        select(MarketingApproval).where(
            MarketingApproval.entity_id == campaign.id,
            MarketingApproval.entity_type == "campaign",
            MarketingApproval.status == MarketingApprovalStatus.PENDING,
        )
    ).first()
    if pending:
        pending.status = MarketingApprovalStatus.APPROVED
        pending.approved_by_user_id = actor.id
        pending.notes = notes
    db.flush()
    return campaign


def reject_campaign(
    db: Session,
    *,
    campaign: MarketingCampaign,
    actor: User,
    notes: str | None = None,
) -> MarketingCampaign:
    if campaign.status != MarketingCampaignStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Campaign is not pending approval")
    _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.DRAFT, actor=actor)
    pending = db.scalars(
        select(MarketingApproval).where(
            MarketingApproval.entity_id == campaign.id,
            MarketingApproval.entity_type == "campaign",
            MarketingApproval.status == MarketingApprovalStatus.PENDING,
        )
    ).first()
    if pending:
        pending.status = MarketingApprovalStatus.REJECTED
        pending.approved_by_user_id = actor.id
        pending.notes = notes
    db.flush()
    return campaign


def schedule_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.SCHEDULED, actor=actor)


def activate_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    readiness = compute_readiness(db, campaign)
    if not readiness.can_activate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campaign cannot be activated: {', '.join(readiness.blockers)}",
        )
    if campaign.status == MarketingCampaignStatus.APPROVED:
        return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.ACTIVE, actor=actor)
    return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.ACTIVE, actor=actor)


def pause_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.PAUSED, actor=actor)


def resume_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.ACTIVE, actor=actor)


def complete_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.COMPLETED, actor=actor)


def cancel_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    return _transition_status(db, campaign=campaign, target=MarketingCampaignStatus.CANCELLED, actor=actor)


def archive_campaign(db: Session, *, campaign: MarketingCampaign, actor: User, reason: str | None = None) -> MarketingCampaign:
    campaign.status = MarketingCampaignStatus.ARCHIVED
    campaign.archived_at = datetime.now(tz=UTC)
    campaign.updated_by_user_id = actor.id
    if reason:
        meta = campaign.metadata_json or {}
        meta["archive_reason"] = reason
        campaign.metadata_json = meta
    db.flush()
    return campaign


def restore_campaign(db: Session, *, campaign: MarketingCampaign, actor: User) -> MarketingCampaign:
    if campaign.archived_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Campaign is not archived")
    campaign.archived_at = None
    campaign.status = MarketingCampaignStatus.DRAFT
    campaign.updated_by_user_id = actor.id
    db.flush()
    return campaign


def delete_campaign(db: Session, *, campaign: MarketingCampaign, actor: User, reason: str) -> None:
    if campaign.status not in (MarketingCampaignStatus.DRAFT, MarketingCampaignStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft or cancelled campaigns can be deleted",
        )
    db.delete(campaign)


def duplicate_campaign(
    db: Session,
    *,
    campaign: MarketingCampaign,
    actor: User,
    payload: CampaignDuplicateRequest,
) -> MarketingCampaign:
    new_name = payload.name or f"{campaign.name} (Copy)"
    clone = MarketingCampaign(
        name=new_name,
        code=None,
        description=campaign.description,
        objective=campaign.objective,
        campaign_type=campaign.campaign_type,
        status=MarketingCampaignStatus.DRAFT,
        priority=campaign.priority,
        owner_user_id=actor.id,
        team_id=campaign.team_id,
        project_ids=deepcopy(campaign.project_ids),
        property_ids=deepcopy(campaign.property_ids),
        audience_ids=deepcopy(campaign.audience_ids),
        segment_ids=deepcopy(campaign.segment_ids),
        channel_ids=deepcopy(campaign.channel_ids),
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        timezone=campaign.timezone,
        budget_amount=campaign.budget_amount if payload.include_budget else None,
        budget_currency=campaign.budget_currency if payload.include_budget else None,
        targets_json=deepcopy(campaign.targets_json),
        tags=deepcopy(campaign.tags),
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(clone)
    db.flush()

    brief = db.scalars(select(CampaignBrief).where(CampaignBrief.campaign_id == campaign.id)).first()
    if brief:
        db.add(
            CampaignBrief(
                campaign_id=clone.id,
                executive_summary=brief.executive_summary,
                objectives=brief.objectives,
                messaging=brief.messaging,
                strategies=brief.strategies,
                risks=brief.risks,
                competitive_context=brief.competitive_context,
                success_criteria=brief.success_criteria,
                created_by_user_id=actor.id,
                updated_by_user_id=actor.id,
            )
        )

    if payload.include_tracking:
        tracking = db.scalars(select(CampaignTracking).where(CampaignTracking.campaign_id == campaign.id)).first()
        if tracking:
            db.add(
                CampaignTracking(
                    campaign_id=clone.id,
                    utm_source=tracking.utm_source,
                    utm_medium=tracking.utm_medium,
                    utm_campaign=tracking.utm_campaign,
                    utm_term=tracking.utm_term,
                    utm_content=tracking.utm_content,
                    tracking_code=None,
                    landing_page_url=tracking.landing_page_url,
                    readiness_status=CampaignTrackingReadiness.INCOMPLETE,
                )
            )

    db.flush()
    return clone


def compute_readiness(db: Session, campaign: MarketingCampaign) -> CampaignReadinessResponse:
    checks: list[CampaignReadinessCheck] = []
    blockers: list[str] = []

    if campaign.owner_user_id:
        checks.append(CampaignReadinessCheck(key="owner", label_key="marketing.campaign.readiness.owner", state="ready"))
    else:
        checks.append(CampaignReadinessCheck(key="owner", label_key="marketing.campaign.readiness.owner", state="blocked", message="Owner required"))
        blockers.append("owner")

    if campaign.audience_ids or campaign.segment_ids:
        checks.append(CampaignReadinessCheck(key="audience", label_key="marketing.campaign.readiness.audience", state="ready"))
    else:
        checks.append(CampaignReadinessCheck(key="audience", label_key="marketing.campaign.readiness.audience", state="blocked", message="Audience or segment required"))
        blockers.append("audience")

    if campaign.channel_ids:
        checks.append(CampaignReadinessCheck(key="channels", label_key="marketing.campaign.readiness.channels", state="ready"))
    else:
        checks.append(CampaignReadinessCheck(key="channels", label_key="marketing.campaign.readiness.channels", state="blocked", message="At least one channel required"))
        blockers.append("channels")

    if campaign.budget_amount and campaign.budget_amount > 0:
        checks.append(CampaignReadinessCheck(key="budget", label_key="marketing.campaign.readiness.budget", state="ready"))
    else:
        checks.append(CampaignReadinessCheck(key="budget", label_key="marketing.campaign.readiness.budget", state="warning", message="No budget set"))
        blockers.append("budget")

    tracking = db.scalars(select(CampaignTracking).where(CampaignTracking.campaign_id == campaign.id)).first()
    if tracking and tracking.readiness_status == CampaignTrackingReadiness.READY:
        checks.append(CampaignReadinessCheck(key="tracking", label_key="marketing.campaign.readiness.tracking", state="ready"))
    elif tracking:
        checks.append(CampaignReadinessCheck(key="tracking", label_key="marketing.campaign.readiness.tracking", state="warning", message="Tracking incomplete"))
        blockers.append("tracking")
    else:
        checks.append(CampaignReadinessCheck(key="tracking", label_key="marketing.campaign.readiness.tracking", state="blocked", message="Tracking not configured"))
        blockers.append("tracking")

    pending_approval = db.scalar(
        select(func.count()).select_from(MarketingApproval).where(
            MarketingApproval.entity_id == campaign.id,
            MarketingApproval.entity_type == "campaign",
            MarketingApproval.status == MarketingApprovalStatus.PENDING,
        )
    )
    if campaign.status == MarketingCampaignStatus.APPROVED:
        checks.append(CampaignReadinessCheck(key="approvals", label_key="marketing.campaign.readiness.approvals", state="ready"))
    elif pending_approval:
        checks.append(CampaignReadinessCheck(key="approvals", label_key="marketing.campaign.readiness.approvals", state="blocked", message="Pending approval"))
        blockers.append("approvals")
    else:
        checks.append(CampaignReadinessCheck(key="approvals", label_key="marketing.campaign.readiness.approvals", state="warning", message="Not submitted for approval"))

    blocked_checks = [c for c in checks if c.state == "blocked"]
    warning_checks = [c for c in checks if c.state == "warning"]
    if blocked_checks:
        overall = "blocked"
    elif warning_checks:
        overall = "warning"
    else:
        overall = "ready"

    can_activate = campaign.status in (
        MarketingCampaignStatus.APPROVED,
        MarketingCampaignStatus.SCHEDULED,
        MarketingCampaignStatus.PAUSED,
    ) and "owner" not in blockers and "channels" not in blockers and "approvals" not in blockers

    return CampaignReadinessResponse(
        overall_state=overall,
        checks=checks,
        can_activate=can_activate,
        blockers=blockers,
    )


def get_campaign_overview(db: Session, campaign: MarketingCampaign) -> CampaignOverviewResponse:
    readiness = compute_readiness(db, campaign)
    lead_count = _campaign_lead_count(db, campaign.id)
    spent = _campaign_spent_amount(db, campaign.id)
    remaining = None
    if campaign.budget_amount is not None and spent is not None:
        remaining = campaign.budget_amount - spent
    elif campaign.budget_amount is not None:
        remaining = campaign.budget_amount
    approval = db.scalars(
        select(MarketingApproval)
        .where(MarketingApproval.entity_id == campaign.id, MarketingApproval.entity_type == "campaign")
        .order_by(MarketingApproval.created_at.desc())
    ).first()

    budget_state = "ready" if campaign.budget_amount is not None else "no_data"
    spend_state = "ready" if spent is not None else "no_data"

    return CampaignOverviewResponse(
        campaign_id=campaign.id,
        readiness=readiness,
        budget_summary={
            "planned": str(campaign.budget_amount) if campaign.budget_amount is not None else None,
            "currency": campaign.budget_currency,
            "spent": str(spent) if spent is not None else None,
            "remaining": str(remaining) if remaining is not None else None,
            "state": budget_state,
        },
        leads_summary={"count": lead_count, "state": "ready" if lead_count else "empty"},
        conversions_summary={"count": None, "state": "not_connected"},
        spend_summary={
            "amount": str(spent) if spent is not None else None,
            "state": spend_state,
        },
        approval_status=approval.status.value if approval else None,
        notes=campaign.notes,
        target_project_id=campaign.target_project_id,
        lead_source_id=campaign.lead_source_id,
        primary_channel=campaign.primary_channel.value if campaign.primary_channel else None,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        remaining_budget=remaining,
    )


def validate_status_transition_query(campaign: MarketingCampaign, target_status: str) -> CampaignStatusTransitionResponse:
    allowed = get_allowed_transitions(campaign.status.value)
    valid = target_status in allowed or target_status == campaign.status.value
    message = None if valid else f"Transition from '{campaign.status.value}' to '{target_status}' is not allowed"
    return CampaignStatusTransitionResponse(
        valid=valid,
        current_status=campaign.status.value,
        target_status=target_status,
        allowed_transitions=allowed,
        message=message,
    )


def get_or_create_brief(db: Session, campaign_id: UUID) -> CampaignBrief:
    brief = db.scalars(select(CampaignBrief).where(CampaignBrief.campaign_id == campaign_id)).first()
    if brief is None:
        brief = CampaignBrief(campaign_id=campaign_id)
        db.add(brief)
        db.flush()
    return brief


def update_brief(db: Session, *, campaign_id: UUID, payload: CampaignBriefUpdate, actor: User) -> CampaignBriefResponse:
    brief = get_or_create_brief(db, campaign_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(brief, field, value)
    brief.updated_by_user_id = actor.id
    db.flush()
    return CampaignBriefResponse.model_validate(brief)


def list_milestones(db: Session, campaign_id: UUID) -> list[CampaignMilestoneResponse]:
    rows = db.scalars(
        select(CampaignMilestone)
        .where(CampaignMilestone.campaign_id == campaign_id)
        .order_by(CampaignMilestone.sort_order, CampaignMilestone.created_at)
    ).all()
    return [CampaignMilestoneResponse.model_validate(r) for r in rows]


def create_milestone(
    db: Session, *, campaign_id: UUID, payload: CampaignMilestoneCreate, actor: User
) -> CampaignMilestoneResponse:
    milestone = CampaignMilestone(
        campaign_id=campaign_id,
        name=payload.name,
        milestone_type=CampaignMilestoneType(payload.milestone_type),
        status=CampaignMilestoneStatus(payload.status),
        due_date=payload.due_date,
        depends_on_ids=payload.depends_on_ids,
        notes=payload.notes,
        sort_order=payload.sort_order,
        created_by_user_id=actor.id,
    )
    db.add(milestone)
    db.flush()
    return CampaignMilestoneResponse.model_validate(milestone)


def update_milestone(
    db: Session, *, milestone: CampaignMilestone, payload: CampaignMilestoneUpdate, actor: User
) -> CampaignMilestoneResponse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "milestone_type" and value is not None:
            milestone.milestone_type = CampaignMilestoneType(value)
        elif field == "status" and value is not None:
            milestone.status = CampaignMilestoneStatus(value)
            if value == "completed":
                milestone.completed_at = datetime.now(tz=UTC)
        else:
            setattr(milestone, field, value)
    db.flush()
    return CampaignMilestoneResponse.model_validate(milestone)


def delete_milestone(db: Session, milestone: CampaignMilestone) -> None:
    db.delete(milestone)


def get_milestone(db: Session, milestone_id: UUID) -> CampaignMilestone:
    milestone = db.get(CampaignMilestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    return milestone


def assign_channel(
    db: Session, *, campaign_id: UUID, payload: CampaignChannelAssignmentCreate
) -> CampaignChannelAssignmentResponse:
    assignment = CampaignChannelAssignment(
        campaign_id=campaign_id,
        channel_id=payload.channel_id,
        provider=payload.provider,
        budget_amount=payload.budget_amount,
        budget_currency=payload.budget_currency,
        schedule_json=payload.schedule_json,
        tracking_json=payload.tracking_json,
    )
    db.add(assignment)
    db.flush()
    return CampaignChannelAssignmentResponse.model_validate(assignment)


def list_channel_assignments(db: Session, campaign_id: UUID) -> list[CampaignChannelAssignmentResponse]:
    rows = db.scalars(
        select(CampaignChannelAssignment).where(CampaignChannelAssignment.campaign_id == campaign_id)
    ).all()
    return [CampaignChannelAssignmentResponse.model_validate(r) for r in rows]


def unlink_channel(db: Session, assignment: CampaignChannelAssignment) -> None:
    db.delete(assignment)


def get_channel_assignment(db: Session, assignment_id: UUID) -> CampaignChannelAssignment:
    assignment = db.get(CampaignChannelAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel assignment not found")
    return assignment


def create_budget_allocation(
    db: Session, *, campaign_id: UUID, payload: CampaignBudgetAllocationCreate, actor: User
) -> CampaignBudgetAllocationResponse:
    allocation = CampaignBudgetAllocation(
        campaign_id=campaign_id,
        budget_id=payload.budget_id,
        channel_id=payload.channel_id,
        name=payload.name,
        currency=payload.currency,
        planned_amount=payload.planned_amount,
        committed_amount=payload.committed_amount,
        period_start=payload.period_start,
        period_end=payload.period_end,
        notes=payload.notes,
        created_by_user_id=actor.id,
    )
    db.add(allocation)
    db.flush()
    return CampaignBudgetAllocationResponse.model_validate(allocation)


def list_budget_allocations(db: Session, campaign_id: UUID) -> list[CampaignBudgetAllocationResponse]:
    rows = db.scalars(
        select(CampaignBudgetAllocation).where(CampaignBudgetAllocation.campaign_id == campaign_id)
    ).all()
    return [CampaignBudgetAllocationResponse.model_validate(r) for r in rows]


def update_budget_allocation(
    db: Session, *, allocation: CampaignBudgetAllocation, payload: CampaignBudgetAllocationUpdate
) -> CampaignBudgetAllocationResponse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(allocation, field, value)
    db.flush()
    return CampaignBudgetAllocationResponse.model_validate(allocation)


def adjust_spend(
    db: Session, *, campaign_id: UUID, payload: CampaignSpendAdjustment, actor: User
) -> CampaignBudgetAllocationResponse:
    if payload.allocation_id:
        allocation = db.get(CampaignBudgetAllocation, payload.allocation_id)
        if allocation is None or allocation.campaign_id != campaign_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    else:
        allocations = list_budget_allocations(db, campaign_id)
        if not allocations:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No budget allocations found")
        allocation = db.get(CampaignBudgetAllocation, allocations[0].id)
        assert allocation is not None

    current = allocation.spent_amount or Decimal("0")
    allocation.spent_amount = current + payload.amount
    meta = allocation.metadata_json or {}
    adjustments = meta.get("manual_adjustments", [])
    adjustments.append({
        "amount": str(payload.amount),
        "reason": payload.reason,
        "actor_id": str(actor.id),
        "at": datetime.now(tz=UTC).isoformat(),
    })
    meta["manual_adjustments"] = adjustments
    allocation.metadata_json = meta
    db.flush()
    return CampaignBudgetAllocationResponse.model_validate(allocation)


def get_or_create_tracking(db: Session, campaign_id: UUID) -> CampaignTracking:
    tracking = db.scalars(select(CampaignTracking).where(CampaignTracking.campaign_id == campaign_id)).first()
    if tracking is None:
        tracking = CampaignTracking(campaign_id=campaign_id)
        db.add(tracking)
        db.flush()
    return tracking


def _validate_tracking(tracking: CampaignTracking) -> list[str]:
    errors: list[str] = []
    if not tracking.utm_source:
        errors.append("utm_source is required")
    if not tracking.utm_medium:
        errors.append("utm_medium is required")
    if not tracking.utm_campaign:
        errors.append("utm_campaign is required")
    return errors


def _compute_tracking_readiness(tracking: CampaignTracking) -> CampaignTrackingReadiness:
    errors = _validate_tracking(tracking)
    if not any([tracking.utm_source, tracking.utm_medium, tracking.utm_campaign]):
        return CampaignTrackingReadiness.NOT_CONFIGURED
    if errors:
        tracking.validation_errors = errors
        return CampaignTrackingReadiness.INCOMPLETE
    tracking.validation_errors = None
    return CampaignTrackingReadiness.READY


def update_tracking(
    db: Session, *, campaign_id: UUID, payload: CampaignTrackingUpdate
) -> CampaignTrackingResponse:
    tracking = get_or_create_tracking(db, campaign_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tracking, field, value)
    tracking.readiness_status = _compute_tracking_readiness(tracking)
    db.flush()
    return CampaignTrackingResponse.model_validate(tracking)


def validate_tracking(db: Session, campaign_id: UUID) -> CampaignTrackingResponse:
    tracking = get_or_create_tracking(db, campaign_id)
    tracking.readiness_status = _compute_tracking_readiness(tracking)
    db.flush()
    return CampaignTrackingResponse.model_validate(tracking)


def list_targets(db: Session, campaign_id: UUID) -> list[CampaignTargetResponse]:
    rows = db.scalars(select(CampaignTarget).where(CampaignTarget.campaign_id == campaign_id)).all()
    return [CampaignTargetResponse.model_validate(r) for r in rows]


def create_target(db: Session, *, campaign_id: UUID, payload: CampaignTargetCreate) -> CampaignTargetResponse:
    target = CampaignTarget(
        campaign_id=campaign_id,
        metric_key=payload.metric_key,
        metric_label=payload.metric_label,
        target_value=payload.target_value,
        unit=payload.unit,
        period=payload.period,
    )
    db.add(target)
    db.flush()
    return CampaignTargetResponse.model_validate(target)


def list_campaign_leads(db: Session, campaign_id: UUID) -> list[CampaignLeadContextResponse]:
    from investhome_api.models.marketing_lead_attribution import MarketingLeadAttribution

    rows = db.scalars(
        select(MarketingLeadAttribution).where(MarketingLeadAttribution.campaign_id == campaign_id)
    ).all()
    return [
        CampaignLeadContextResponse(
            id=r.id,
            lead_id=r.lead_id,
            contact_id=None,
            company_id=r.company_id,
            campaign_id=r.campaign_id,
            source_id=None,
            channel_id=None,
            utm_data_json={
                k: v
                for k, v in {
                    "utm_source": r.utm_source,
                    "utm_medium": r.utm_medium,
                    "utm_campaign": r.utm_campaign,
                    "utm_term": r.utm_term,
                    "utm_content": r.utm_content,
                }.items()
                if v
            }
            or None,
            marketing_status=None,
            verification_status=None,
            handoff_status="not_ready",
            created_at=r.created_at,
        )
        for r in rows
    ]


def list_saved_views(db: Session, user_id: UUID) -> list[CampaignSavedViewResponse]:
    rows = db.scalars(
        select(CampaignSavedView).where(CampaignSavedView.user_id == user_id).order_by(CampaignSavedView.name)
    ).all()
    return [CampaignSavedViewResponse.model_validate(r) for r in rows]


def create_saved_view(
    db: Session, *, user_id: UUID, payload: CampaignSavedViewCreate
) -> CampaignSavedViewResponse:
    view = CampaignSavedView(
        user_id=user_id,
        name=payload.name,
        filters_json=payload.filters_json,
        is_default=payload.is_default,
        is_shared=payload.is_shared,
    )
    db.add(view)
    db.flush()
    return CampaignSavedViewResponse.model_validate(view)


def update_saved_view(
    db: Session, *, view: CampaignSavedView, payload: CampaignSavedViewUpdate
) -> CampaignSavedViewResponse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(view, field, value)
    db.flush()
    return CampaignSavedViewResponse.model_validate(view)


def delete_saved_view(db: Session, view: CampaignSavedView) -> None:
    db.delete(view)


def get_saved_view(db: Session, view_id: UUID) -> CampaignSavedView:
    view = db.get(CampaignSavedView, view_id)
    if view is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved view not found")
    return view


def list_templates(db: Session) -> list[CampaignTemplateResponse]:
    rows = db.scalars(
        select(CampaignTemplate).where(CampaignTemplate.is_active.is_(True)).order_by(CampaignTemplate.name)
    ).all()
    return [CampaignTemplateResponse.model_validate(r) for r in rows]


def create_template(
    db: Session, *, payload: CampaignTemplateCreate, actor: User
) -> CampaignTemplateResponse:
    template = CampaignTemplate(
        name=payload.name,
        description=payload.description,
        campaign_type=MarketingCampaignType(payload.campaign_type) if payload.campaign_type else None,
        objective=MarketingCampaignObjective(payload.objective) if payload.objective else None,
        template_json=payload.template_json,
        created_by_user_id=actor.id,
    )
    db.add(template)
    db.flush()
    return CampaignTemplateResponse.model_validate(template)


def bulk_action(
    db: Session, *, payload: CampaignBulkActionRequest, actor: User
) -> CampaignBulkActionResult:
    eligible_ids: list[UUID] = []
    ineligible: list[dict] = []

    for cid in payload.campaign_ids:
        try:
            campaign = get_campaign(db, cid)
            if payload.action == "archive":
                if campaign.status in (MarketingCampaignStatus.COMPLETED, MarketingCampaignStatus.CANCELLED, MarketingCampaignStatus.DRAFT):
                    eligible_ids.append(cid)
                else:
                    ineligible.append({"id": str(cid), "reason": f"Cannot archive campaign in {campaign.status.value} status"})
            elif payload.action == "activate":
                readiness = compute_readiness(db, campaign)
                if readiness.can_activate:
                    eligible_ids.append(cid)
                else:
                    ineligible.append({"id": str(cid), "reason": ", ".join(readiness.blockers)})
            elif payload.action == "pause":
                if campaign.status == MarketingCampaignStatus.ACTIVE:
                    eligible_ids.append(cid)
                else:
                    ineligible.append({"id": str(cid), "reason": "Only active campaigns can be paused"})
            elif payload.action == "submit_approval":
                if campaign.status in (MarketingCampaignStatus.DRAFT, MarketingCampaignStatus.PLANNING):
                    eligible_ids.append(cid)
                else:
                    ineligible.append({"id": str(cid), "reason": f"Cannot submit from {campaign.status.value}"})
            else:
                ineligible.append({"id": str(cid), "reason": f"Unknown action: {payload.action}"})
        except HTTPException:
            ineligible.append({"id": str(cid), "reason": "Campaign not found"})

    results: list[dict] = []
    for cid in eligible_ids:
        campaign = get_campaign(db, cid)
        if payload.action == "archive":
            archive_campaign(db, campaign=campaign, actor=actor)
            results.append({"id": str(cid), "status": "archived"})
        elif payload.action == "activate":
            activate_campaign(db, campaign=campaign, actor=actor)
            results.append({"id": str(cid), "status": "active"})
        elif payload.action == "pause":
            pause_campaign(db, campaign=campaign, actor=actor)
            results.append({"id": str(cid), "status": "paused"})
        elif payload.action == "submit_approval":
            submit_for_approval(db, campaign=campaign, actor=actor)
            results.append({"id": str(cid), "status": "pending_approval"})

    return CampaignBulkActionResult(
        eligible_count=len(eligible_ids),
        ineligible_count=len(ineligible),
        eligible_ids=eligible_ids,
        ineligible=ineligible,
        results=results,
    )


def campaign_to_detail(db: Session, campaign: MarketingCampaign) -> MarketingCampaignDetail:
    return _to_detail(db, campaign)


def compute_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total > 0 else 0
