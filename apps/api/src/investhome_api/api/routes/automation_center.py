"""Automation Center control-tower API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.automation_center import (
    AutomationAuditItem,
    AutomationAuditListResponse,
    AutomationErrorItem,
    AutomationErrorListResponse,
    AutomationExecutionItem,
    AutomationExecutionListResponse,
    AutomationIntegrationItem,
    AutomationIntegrationListResponse,
    AutomationOverviewResponse,
    AutomationRetryResponse,
    AutomationScheduleItem,
    AutomationScheduleListResponse,
    AutomationWorkflowDetail,
    AutomationWorkflowListResponse,
    AutomationWorkflowSummary,
    QueueHealthResponse,
    SystemHealthSummary,
)
from investhome_api.services import automation_center_service as service

router = APIRouter(prefix="/automation", tags=["automation-center"])


@router.get("/overview", response_model=AutomationOverviewResponse)
def automation_overview(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
) -> AutomationOverviewResponse:
    data = service.get_overview(db)
    return AutomationOverviewResponse(
        health=SystemHealthSummary(**data["health"]),
        workflow_status=data["workflow_status"],
        recent_failures=[AutomationErrorItem(**item) for item in data["recent_failures"]],
        recent_executions=[AutomationExecutionItem(**item) for item in data["recent_executions"]],
        scheduled_jobs=[AutomationScheduleItem(**item) for item in data["scheduled_jobs"]],
        ai_workflows=[AutomationWorkflowSummary(**item) for item in data["ai_workflows"]],
        integrations=[AutomationIntegrationItem(**item) for item in data["integrations"]],
        queue_health=QueueHealthResponse(**data["queue_health"]),
    )


@router.get("/health", response_model=SystemHealthSummary)
def automation_health(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
) -> SystemHealthSummary:
    return SystemHealthSummary(**service.get_system_health(db))


@router.get("/queue-health", response_model=QueueHealthResponse)
def automation_queue_health(
    _user: User = Depends(require_permission("automation", "view")),
) -> QueueHealthResponse:
    return QueueHealthResponse(**service.get_queue_health())


@router.get("/workflows", response_model=AutomationWorkflowListResponse)
def list_automation_workflows(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: str | None = None,
    search: str | None = None,
    include_placeholders: bool = True,
) -> AutomationWorkflowListResponse:
    items, total = service.list_workflows(
        db,
        page=page,
        page_size=page_size,
        category=category,
        search=search,
        include_placeholders=include_placeholders,
    )
    return AutomationWorkflowListResponse(
        items=[AutomationWorkflowSummary(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=service.compute_pages(total, page_size),
        categories=list(service.CATEGORIES),  # type: ignore[arg-type]
    )


@router.get("/workflows/{workflow_id}", response_model=AutomationWorkflowDetail)
def get_automation_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
) -> AutomationWorkflowDetail:
    detail = service.get_workflow_detail(db, workflow_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return AutomationWorkflowDetail(**detail)


@router.get("/executions", response_model=AutomationExecutionListResponse)
def list_automation_executions(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> AutomationExecutionListResponse:
    items, total, status_counts = service.list_executions(
        db, page=page, page_size=page_size, status_filter=status_filter
    )
    return AutomationExecutionListResponse(
        items=[AutomationExecutionItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=service.compute_pages(total, page_size),
        status_counts=status_counts,
    )


@router.get("/errors", response_model=AutomationErrorListResponse)
def list_automation_errors(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> AutomationErrorListResponse:
    items, total = service.list_errors(db, page=page, page_size=page_size)
    return AutomationErrorListResponse(
        items=[AutomationErrorItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=service.compute_pages(total, page_size),
    )


@router.get("/schedules", response_model=AutomationScheduleListResponse)
def list_automation_schedules(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
) -> AutomationScheduleListResponse:
    items = service.list_schedules(db)
    return AutomationScheduleListResponse(
        items=[AutomationScheduleItem(**item) for item in items],
        total=len(items),
    )


@router.get("/integrations", response_model=AutomationIntegrationListResponse)
def list_automation_integrations(
    _user: User = Depends(require_permission("automation", "view")),
) -> AutomationIntegrationListResponse:
    items = service.list_integrations()
    return AutomationIntegrationListResponse(
        items=[AutomationIntegrationItem(**item) for item in items],
        total=len(items),
    )


@router.get("/audit", response_model=AutomationAuditListResponse)
def list_automation_audit(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("automation", "view")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> AutomationAuditListResponse:
    items, total = service.list_audit(db, page=page, page_size=page_size)
    return AutomationAuditListResponse(
        items=[AutomationAuditItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=service.compute_pages(total, page_size),
    )


@router.post("/workflows/{workflow_id}/retry", response_model=AutomationRetryResponse)
def retry_automation_workflow(
    workflow_id: str,
    _user: User = Depends(require_permission("automation", "manage")),
) -> AutomationRetryResponse:
    return AutomationRetryResponse(
        accepted=False,
        message=(
            f"Retry is not available for workflow {workflow_id}. "
            "Marketing automation execution engine is not connected; ARQ jobs have no manual retry API."
        ),
    )


@router.post("/errors/{execution_id}/retry", response_model=AutomationRetryResponse)
def retry_automation_error(
    execution_id: str,
    _user: User = Depends(require_permission("automation", "manage")),
) -> AutomationRetryResponse:
    return AutomationRetryResponse(
        accepted=False,
        message=(
            f"Retry is not available for execution {execution_id}. "
            "No execution requeue endpoint is registered yet."
        ),
    )
