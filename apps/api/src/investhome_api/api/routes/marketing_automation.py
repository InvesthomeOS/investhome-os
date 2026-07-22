"""Marketing automation workflow API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_automation import (
    AutomationLogEntry,
    AutomationLogListResponse,
    AutomationMetricsResponse,
    ExecutionListResponse,
    ExecutionSummary,
    WorkflowCreate,
    WorkflowDetail,
    WorkflowListResponse,
    WorkflowSummary,
    WorkflowUpdate,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_created,
    log_entity_deleted,
    log_entity_updated,
)
from investhome_api.services.marketing.automation_service import (
    activate_workflow,
    archive_workflow,
    compute_pages,
    create_workflow,
    delete_workflow,
    duplicate_workflow,
    execution_to_log_entry,
    execution_to_summary,
    get_workflow_metrics,
    list_executions,
    list_workflows,
    pause_workflow,
    update_workflow,
    workflow_to_detail,
    workflow_to_summary,
    _get_workflow_or_404,
)

router = APIRouter(prefix="/marketing/automations", tags=["marketing-automations"])


@router.get("", response_model=WorkflowListResponse)
def list_automations_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    is_journey: bool | None = None,
    include_archived: bool = False,
) -> WorkflowListResponse:
    rows, total = list_workflows(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        is_journey=is_journey,
        include_archived=include_archived,
    )
    return WorkflowListResponse(
        items=[WorkflowSummary(**workflow_to_summary(row)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=compute_pages(total, page_size),
    )


@router.post("", response_model=WorkflowDetail, status_code=status.HTTP_201_CREATED)
def create_automation_route(
    body: WorkflowCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    workflow = create_workflow(db, user, body)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=workflow.id,
        description_key="activity.marketing.automation.created",
        actor=user,
        metadata={"name": workflow.name, "status": workflow.status.value},
        request=request,
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.get("/{automation_id}", response_model=WorkflowDetail)
def get_automation_route(
    automation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    workflow = _get_workflow_or_404(db, automation_id)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.patch("/{automation_id}", response_model=WorkflowDetail)
def update_automation_route(
    automation_id: UUID,
    body: WorkflowUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    before = workflow_to_detail(_get_workflow_or_404(db, automation_id))
    workflow = update_workflow(db, automation_id, user, body)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=workflow.id,
        description_key="activity.marketing.automation.updated",
        actor=user,
        before={"name": before["name"], "version": before["version"]},
        after={"name": workflow.name, "version": workflow.version},
        request=request,
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_automation_route(
    automation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> None:
    workflow = _get_workflow_or_404(db, automation_id)
    name = workflow.name
    delete_workflow(db, automation_id)
    log_entity_deleted(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=automation_id,
        description_key="activity.marketing.automation.deleted",
        actor=user,
        metadata={"name": name},
        request=request,
    )
    db.commit()


@router.post("/{automation_id}/activate", response_model=WorkflowDetail)
def activate_automation_route(
    automation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    before_status = _get_workflow_or_404(db, automation_id).status.value
    workflow = activate_workflow(db, automation_id, user)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=workflow.id,
        description_key="activity.marketing.automation.activated",
        actor=user,
        before={"status": before_status},
        after={"status": workflow.status.value},
        request=request,
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.post("/{automation_id}/pause", response_model=WorkflowDetail)
def pause_automation_route(
    automation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    before_status = _get_workflow_or_404(db, automation_id).status.value
    workflow = pause_workflow(db, automation_id)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=workflow.id,
        description_key="activity.marketing.automation.paused",
        actor=user,
        before={"status": before_status},
        after={"status": workflow.status.value},
        request=request,
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.post("/{automation_id}/archive", response_model=WorkflowDetail)
def archive_automation_route(
    automation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    before_status = _get_workflow_or_404(db, automation_id).status.value
    workflow = archive_workflow(db, automation_id)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=workflow.id,
        description_key="activity.marketing.automation.archived",
        actor=user,
        before={"status": before_status},
        after={"status": workflow.status.value},
        request=request,
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.post("/{automation_id}/duplicate", response_model=WorkflowDetail, status_code=status.HTTP_201_CREATED)
def duplicate_automation_route(
    automation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> WorkflowDetail:
    workflow = duplicate_workflow(db, automation_id, user)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_AUTOMATION,
        entity_id=workflow.id,
        description_key="activity.marketing.automation.duplicated",
        actor=user,
        metadata={"source_id": str(automation_id), "name": workflow.name},
        request=request,
    )
    db.commit()
    db.refresh(workflow)
    return WorkflowDetail(**workflow_to_detail(workflow))


@router.get("/{automation_id}/executions", response_model=ExecutionListResponse)
def list_automation_executions_route(
    automation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> ExecutionListResponse:
    rows, total = list_executions(db, automation_id, page=page, page_size=page_size, status_filter=status_filter)
    return ExecutionListResponse(
        items=[ExecutionSummary(**execution_to_summary(row)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=compute_pages(total, page_size),
    )


@router.get("/{automation_id}/logs", response_model=AutomationLogListResponse)
def list_automation_logs_route(
    automation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> AutomationLogListResponse:
    rows, total = list_executions(db, automation_id, page=page, page_size=page_size)

    return AutomationLogListResponse(
        items=[AutomationLogEntry(**execution_to_log_entry(row)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=compute_pages(total, page_size),
    )


@router.get("/{automation_id}/metrics", response_model=AutomationMetricsResponse)
def get_automation_metrics_route(
    automation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_automations")),
) -> AutomationMetricsResponse:
    return AutomationMetricsResponse(**get_workflow_metrics(db, automation_id))
