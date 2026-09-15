"""Sales opportunity API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.sales import OpportunityStage
from investhome_api.models.user_auth import User
from investhome_api.schemas.sales_opportunity import (
    DashboardMetricsResponse,
    ExecutiveSalesSummaryResponse,
    LinkInventoryRequest,
    LinkProjectRequest,
    NextActionRequest,
    OpportunityInventoryResponse,
    OpportunityProjectResponse,
    OpportunityTimelineResponse,
    PipelineStageGroup,
    PipelineSummaryResponse,
    ProbabilityChangeRequest,
    SalesOpportunityCreate,
    SalesOpportunityListResponse,
    SalesOpportunityResponse,
    SalesOpportunityUpdate,
    StageChangeRequest,
)
from investhome_api.services.sales import opportunity_service as svc

router = APIRouter(prefix="/sales/opportunities", tags=["sales-opportunities"])


def _handle_opportunity_error(exc: svc.OpportunityError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


@router.get("", response_model=SalesOpportunityListResponse)
def list_opportunities(
    search: str | None = Query(default=None, max_length=255),
    stage: OpportunityStage | None = Query(default=None),
    assigned_sales_user_id: UUID | None = Query(default=None),
    party_id: UUID | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at", max_length=50),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view")),
) -> SalesOpportunityListResponse:
    items, total = svc.list_opportunities(
        db,
        search=search,
        stage=stage,
        assigned_sales_user_id=assigned_sales_user_id,
        party_id=party_id,
        lead_id=lead_id,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        offset=offset,
        limit=limit,
    )
    return SalesOpportunityListResponse(
        items=[svc.serialize_opportunity(db, item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view")),
) -> DashboardMetricsResponse:
    return DashboardMetricsResponse(**svc.build_dashboard_metrics(db))


@router.get("/pipeline", response_model=PipelineSummaryResponse)
def get_pipeline(
    include_details: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view_pipeline")),
) -> PipelineSummaryResponse:
    summary = svc.build_pipeline_summary(db, include_archived=include_archived)
    groups = None
    if include_details:
        groups = []
        for stage in OpportunityStage:
            items, _ = svc.list_opportunities(
                db,
                stage=stage,
                include_archived=include_archived,
                limit=200,
            )
            if items:
                groups.append(
                    PipelineStageGroup(
                        stage=stage.value,
                        count=len(items),
                        opportunities=[svc.serialize_opportunity(db, o) for o in items],
                    )
                )
    return PipelineSummaryResponse(stages=summary["stages"], total=summary["total"], groups=groups)


@router.get("/executive-summary", response_model=ExecutiveSalesSummaryResponse)
def get_executive_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("executive", "view")),
) -> ExecutiveSalesSummaryResponse:
    return ExecutiveSalesSummaryResponse(**svc.build_executive_summary(db))


@router.get("/{opportunity_id}", response_model=SalesOpportunityResponse)
def get_opportunity(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
    except svc.OpportunityError as exc:
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.post("", response_model=SalesOpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    payload: SalesOpportunityCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "create")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.create_opportunity(
            db,
            data=payload.model_dump(),
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.patch("/{opportunity_id}", response_model=SalesOpportunityResponse)
def update_opportunity(
    opportunity_id: UUID,
    payload: SalesOpportunityUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        opportunity = svc.update_opportunity(
            db,
            opportunity,
            updates=payload.model_dump(exclude_unset=True),
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.delete("/{opportunity_id}", response_model=SalesOpportunityResponse)
def archive_opportunity(
    opportunity_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "archive")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        opportunity = svc.archive_opportunity(db, opportunity, actor=actor, request=request)
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.post("/{opportunity_id}/restore", response_model=SalesOpportunityResponse)
def restore_opportunity(
    opportunity_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "restore")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id, include_archived=True)
        opportunity = svc.restore_opportunity(db, opportunity, actor=actor, request=request)
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.post("/{opportunity_id}/stage", response_model=SalesOpportunityResponse)
def change_stage(
    opportunity_id: UUID,
    payload: StageChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "change_stage")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        opportunity = svc.change_stage(
            db,
            opportunity,
            new_stage=payload.stage,
            actor=actor,
            request=request,
            notes=payload.notes,
            loss_reason=payload.loss_reason,
            loss_notes=payload.loss_notes,
            dormant_review_date=payload.dormant_review_date,
            cancelled_reason=payload.cancelled_reason,
        )
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.post("/{opportunity_id}/probability", response_model=SalesOpportunityResponse)
def change_probability(
    opportunity_id: UUID,
    payload: ProbabilityChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "change_probability")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        opportunity = svc.change_probability(
            db,
            opportunity,
            new_probability=payload.probability,
            actor=actor,
            reason=payload.reason,
            request=request,
        )
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.post("/{opportunity_id}/next-action", response_model=SalesOpportunityResponse)
def update_next_action(
    opportunity_id: UUID,
    payload: NextActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update")),
) -> SalesOpportunityResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        opportunity = svc.update_next_action(
            db,
            opportunity,
            next_action=payload.next_action,
            next_action_date=payload.next_action_date,
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(opportunity)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return svc.serialize_opportunity(db, opportunity)


@router.post("/{opportunity_id}/inventory", response_model=OpportunityInventoryResponse, status_code=status.HTTP_201_CREATED)
def link_inventory(
    opportunity_id: UUID,
    payload: LinkInventoryRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update")),
) -> OpportunityInventoryResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        link = svc.link_inventory(
            db,
            opportunity,
            inventory_asset_id=payload.inventory_asset_id,
            actor=actor,
            match_reason=payload.match_reason,
            is_favorite=payload.is_favorite,
            notes=payload.notes,
            request=request,
        )
        db.commit()
        db.refresh(link)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return OpportunityInventoryResponse.model_validate(link)


@router.delete("/{opportunity_id}/inventory/{inventory_asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_inventory(
    opportunity_id: UUID,
    inventory_asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update")),
) -> None:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        svc.unlink_inventory(
            db,
            opportunity,
            inventory_asset_id=inventory_asset_id,
            actor=actor,
            request=request,
        )
        db.commit()
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc


@router.post("/{opportunity_id}/projects", response_model=OpportunityProjectResponse, status_code=status.HTTP_201_CREATED)
def link_project(
    opportunity_id: UUID,
    payload: LinkProjectRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update")),
) -> OpportunityProjectResponse:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        link = svc.link_project(
            db,
            opportunity,
            project_id=payload.project_id,
            actor=actor,
            request=request,
        )
        db.commit()
        db.refresh(link)
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc
    return OpportunityProjectResponse.model_validate(link)


@router.delete("/{opportunity_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_project(
    opportunity_id: UUID,
    project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("sales", "update")),
) -> None:
    try:
        opportunity = svc.get_opportunity_or_raise(db, opportunity_id)
        svc.unlink_project(
            db,
            opportunity,
            project_id=project_id,
            actor=actor,
            request=request,
        )
        db.commit()
    except svc.OpportunityError as exc:
        db.rollback()
        raise _handle_opportunity_error(exc) from exc


@router.get("/{opportunity_id}/timeline", response_model=list[OpportunityTimelineResponse])
def get_timeline(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("sales", "view")),
) -> list[OpportunityTimelineResponse]:
    try:
        svc.get_opportunity_or_raise(db, opportunity_id)
    except svc.OpportunityError as exc:
        raise _handle_opportunity_error(exc) from exc
    entries = svc.get_timeline(db, opportunity_id)
    return [OpportunityTimelineResponse.model_validate(entry) for entry in entries]
