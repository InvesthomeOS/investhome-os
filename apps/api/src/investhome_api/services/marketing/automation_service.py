"""Marketing automation workflow service — CRUD, lifecycle, metrics, execution records."""

from __future__ import annotations

import copy
import math
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_automation import (
    MarketingAutomationExecution,
    MarketingAutomationExecutionStatus,
    MarketingAutomationVersion,
    MarketingAutomationWorkflow,
    MarketingAutomationWorkflowStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_automation import (
    AutomationActionSchema,
    AutomationConditionSchema,
    AutomationTriggerSchema,
    JourneyGraphSchema,
    WorkflowCreate,
    WorkflowUpdate,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    MarketingAutomationWorkflowStatus.DRAFT.value: {
        MarketingAutomationWorkflowStatus.ACTIVE.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
    },
    MarketingAutomationWorkflowStatus.ACTIVE.value: {
        MarketingAutomationWorkflowStatus.PAUSED.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
        MarketingAutomationWorkflowStatus.ERROR.value,
    },
    MarketingAutomationWorkflowStatus.PAUSED.value: {
        MarketingAutomationWorkflowStatus.ACTIVE.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
    },
    MarketingAutomationWorkflowStatus.ERROR.value: {
        MarketingAutomationWorkflowStatus.PAUSED.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
        MarketingAutomationWorkflowStatus.DRAFT.value,
    },
    MarketingAutomationWorkflowStatus.PENDING_APPROVAL.value: {
        MarketingAutomationWorkflowStatus.DRAFT.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
    },
    MarketingAutomationWorkflowStatus.APPROVED.value: {
        MarketingAutomationWorkflowStatus.ACTIVE.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
    },
    MarketingAutomationWorkflowStatus.DISABLED.value: {
        MarketingAutomationWorkflowStatus.DRAFT.value,
        MarketingAutomationWorkflowStatus.ARCHIVED.value,
    },
    MarketingAutomationWorkflowStatus.ARCHIVED.value: set(),
}

_SECRET_KEY_PATTERN = re.compile(r"(api[_-]?key|token|password|secret|authorization)", re.IGNORECASE)


def is_execution_engine_available() -> bool:
    """Automation execution worker is not registered yet."""
    return False


def execution_engine_message() -> str:
    return "Automation execution queue is not connected. Lifecycle and records are available; channel actions will not run."


def compute_pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return math.ceil(total / page_size)


def _get_workflow_or_404(db: Session, workflow_id: UUID) -> MarketingAutomationWorkflow:
    workflow = db.get(MarketingAutomationWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found")
    return workflow


def validate_status_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from '{current}' to '{target}'",
        )


def _validate_workflow_definition(
    *,
    trigger: dict[str, Any] | None,
    conditions: list[dict[str, Any]] | None,
    actions: list[dict[str, Any]] | None,
    journey_graph: dict[str, Any] | None,
    is_journey: bool,
) -> None:
    if is_journey:
        if not journey_graph or not journey_graph.get("nodes"):
            raise HTTPException(status_code=400, detail="Journey automations require a journey graph with nodes")
        JourneyGraphSchema.model_validate(journey_graph)
        return
    if not trigger:
        raise HTTPException(status_code=400, detail="Automation requires a trigger")
    AutomationTriggerSchema.model_validate(trigger)
    for condition in conditions or []:
        AutomationConditionSchema.model_validate(condition)
    if not actions:
        raise HTTPException(status_code=400, detail="Automation requires at least one action")
    for action in actions:
        AutomationActionSchema.model_validate(action)


def _serialize_trigger(trigger_json: dict[str, Any] | None) -> dict[str, Any] | None:
    return trigger_json


def _serialize_conditions(conditions_json: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    return conditions_json


def _serialize_actions(actions_json: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    return actions_json


def _workflow_snapshot(workflow: MarketingAutomationWorkflow) -> dict[str, Any]:
    return {
        "name": workflow.name,
        "code": workflow.code,
        "description": workflow.description,
        "status": workflow.status.value,
        "version": workflow.version,
        "trigger_json": workflow.trigger_json,
        "conditions_json": workflow.conditions_json,
        "actions_json": workflow.actions_json,
        "journey_graph_json": workflow.journey_graph_json,
        "owner_user_id": str(workflow.owner_user_id) if workflow.owner_user_id else None,
        "team_id": str(workflow.team_id) if workflow.team_id else None,
        "timezone": workflow.timezone,
        "is_journey": workflow.is_journey,
    }


def _save_version(db: Session, workflow: MarketingAutomationWorkflow, user: User, change_summary: str | None) -> None:
    db.add(
        MarketingAutomationVersion(
            workflow_id=workflow.id,
            version_number=workflow.version,
            snapshot_json=_workflow_snapshot(workflow),
            change_summary=change_summary,
            created_by_user_id=user.id,
        )
    )


def workflow_to_summary(workflow: MarketingAutomationWorkflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "code": workflow.code,
        "description": workflow.description,
        "status": workflow.status.value,
        "version": workflow.version,
        "is_journey": workflow.is_journey,
        "owner_user_id": workflow.owner_user_id,
        "created_by_user_id": workflow.created_by_user_id,
        "team_id": workflow.team_id,
        "activated_at": workflow.activated_at,
        "last_run_at": workflow.last_run_at,
        "execution_count": workflow.execution_count,
        "execution_engine_available": is_execution_engine_available(),
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
    }


def workflow_to_detail(workflow: MarketingAutomationWorkflow) -> dict[str, Any]:
    return {
        **workflow_to_summary(workflow),
        "trigger": _serialize_trigger(workflow.trigger_json),
        "conditions": _serialize_conditions(workflow.conditions_json),
        "actions": _serialize_actions(workflow.actions_json),
        "journey_graph": workflow.journey_graph_json,
        "timezone": workflow.timezone,
    }


def list_workflows(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status_filter: str | None = None,
    is_journey: bool | None = None,
    include_archived: bool = False,
) -> tuple[list[MarketingAutomationWorkflow], int]:
    query = select(MarketingAutomationWorkflow)
    if not include_archived:
        query = query.where(MarketingAutomationWorkflow.status != MarketingAutomationWorkflowStatus.ARCHIVED)
    if search:
        query = query.where(MarketingAutomationWorkflow.name.ilike(f"%{search}%"))
    if status_filter:
        query = query.where(MarketingAutomationWorkflow.status == MarketingAutomationWorkflowStatus(status_filter))
    if is_journey is not None:
        query = query.where(MarketingAutomationWorkflow.is_journey.is_(is_journey))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingAutomationWorkflow.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def create_workflow(db: Session, user: User, payload: WorkflowCreate) -> MarketingAutomationWorkflow:
    data = payload.model_dump()
    trigger = data.pop("trigger", None)
    conditions = data.pop("conditions", None)
    actions = data.pop("actions", None)
    journey_graph = data.pop("journey_graph", None)
    status_value = data.pop("status", "draft")
    if status_value != MarketingAutomationWorkflowStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="New automations must be created in draft status")

    _validate_workflow_definition(
        trigger=trigger,
        conditions=conditions,
        actions=actions,
        journey_graph=journey_graph,
        is_journey=data.get("is_journey", False),
    )

    workflow = MarketingAutomationWorkflow(
        name=data["name"],
        code=data.get("code"),
        description=data.get("description"),
        status=MarketingAutomationWorkflowStatus.DRAFT,
        trigger_json=trigger,
        conditions_json=conditions or [],
        actions_json=actions or [],
        journey_graph_json=journey_graph,
        owner_user_id=data.get("owner_user_id") or user.id,
        created_by_user_id=user.id,
        team_id=data.get("team_id"),
        timezone=data.get("timezone", "UTC"),
        is_journey=data.get("is_journey", False),
    )
    db.add(workflow)
    db.flush()
    _save_version(db, workflow, user, "Initial version")
    return workflow


def update_workflow(
    db: Session,
    workflow_id: UUID,
    user: User,
    payload: WorkflowUpdate,
) -> MarketingAutomationWorkflow:
    workflow = _get_workflow_or_404(db, workflow_id)
    if workflow.status == MarketingAutomationWorkflowStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived automations cannot be modified")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        raise HTTPException(status_code=400, detail="Use lifecycle endpoints to change automation status")

    trigger = data.pop("trigger", None)
    conditions = data.pop("conditions", None)
    actions = data.pop("actions", None)
    journey_graph = data.pop("journey_graph", None)
    change_summary = data.pop("change_summary", None)

    if trigger is not None:
        workflow.trigger_json = trigger
    if conditions is not None:
        workflow.conditions_json = conditions
    if actions is not None:
        workflow.actions_json = actions
    if journey_graph is not None:
        workflow.journey_graph_json = journey_graph

    for key in ("name", "code", "description", "owner_user_id", "team_id", "timezone", "is_journey"):
        if key in data:
            setattr(workflow, key, data[key])

    _validate_workflow_definition(
        trigger=workflow.trigger_json,
        conditions=workflow.conditions_json,
        actions=workflow.actions_json,
        journey_graph=workflow.journey_graph_json,
        is_journey=workflow.is_journey,
    )

    workflow.version += 1
    _save_version(db, workflow, user, change_summary or "Updated workflow")
    return workflow


def delete_workflow(db: Session, workflow_id: UUID) -> None:
    workflow = _get_workflow_or_404(db, workflow_id)
    if workflow.status == MarketingAutomationWorkflowStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Active automations must be paused or archived before deletion")
    db.delete(workflow)


def activate_workflow(db: Session, workflow_id: UUID, user: User) -> MarketingAutomationWorkflow:
    workflow = _get_workflow_or_404(db, workflow_id)
    validate_status_transition(workflow.status.value, MarketingAutomationWorkflowStatus.ACTIVE.value)
    _validate_workflow_definition(
        trigger=workflow.trigger_json,
        conditions=workflow.conditions_json,
        actions=workflow.actions_json,
        journey_graph=workflow.journey_graph_json,
        is_journey=workflow.is_journey,
    )
    workflow.status = MarketingAutomationWorkflowStatus.ACTIVE
    if workflow.activated_at is None:
        workflow.activated_at = datetime.now(UTC)
    record_execution_intent(db, workflow, user, note="Activation recorded; execution engine not connected")
    return workflow


def pause_workflow(db: Session, workflow_id: UUID) -> MarketingAutomationWorkflow:
    workflow = _get_workflow_or_404(db, workflow_id)
    validate_status_transition(workflow.status.value, MarketingAutomationWorkflowStatus.PAUSED.value)
    workflow.status = MarketingAutomationWorkflowStatus.PAUSED
    return workflow


def archive_workflow(db: Session, workflow_id: UUID) -> MarketingAutomationWorkflow:
    workflow = _get_workflow_or_404(db, workflow_id)
    validate_status_transition(workflow.status.value, MarketingAutomationWorkflowStatus.ARCHIVED.value)
    workflow.status = MarketingAutomationWorkflowStatus.ARCHIVED
    return workflow


def duplicate_workflow(db: Session, workflow_id: UUID, user: User) -> MarketingAutomationWorkflow:
    source = _get_workflow_or_404(db, workflow_id)
    copy_name = f"{source.name} (Copy)"
    suffix = 2
    while db.scalar(select(func.count()).where(MarketingAutomationWorkflow.name == copy_name)):
        copy_name = f"{source.name} (Copy {suffix})"
        suffix += 1

    duplicate = MarketingAutomationWorkflow(
        name=copy_name,
        code=None,
        description=source.description,
        status=MarketingAutomationWorkflowStatus.DRAFT,
        version=1,
        trigger_json=copy.deepcopy(source.trigger_json),
        conditions_json=copy.deepcopy(source.conditions_json),
        actions_json=copy.deepcopy(source.actions_json),
        journey_graph_json=copy.deepcopy(source.journey_graph_json),
        owner_user_id=user.id,
        created_by_user_id=user.id,
        team_id=source.team_id,
        timezone=source.timezone,
        is_journey=source.is_journey,
    )
    db.add(duplicate)
    db.flush()
    _save_version(db, duplicate, user, f"Duplicated from {source.id}")
    return duplicate


def record_execution_intent(
    db: Session,
    workflow: MarketingAutomationWorkflow,
    user: User,
    *,
    note: str,
    trigger_context: dict[str, Any] | None = None,
) -> MarketingAutomationExecution:
    """Record execution intent without claiming channel delivery."""
    now = datetime.now(UTC)
    action_types = [a.get("type") for a in (workflow.actions_json or []) if isinstance(a, dict)]
    execution = MarketingAutomationExecution(
        workflow_id=workflow.id,
        workflow_version=workflow.version,
        status=MarketingAutomationExecutionStatus.NOT_CONNECTED,
        trigger_type=(workflow.trigger_json or {}).get("type"),
        trigger_context_json=_sanitize_payload(trigger_context or {"intent": "lifecycle", "note": note}),
        actions_executed_json=[],
        actions_skipped_json=[{"type": t, "reason": "execution_engine_unavailable"} for t in action_types if t],
        error_message=execution_engine_message() if not is_execution_engine_available() else None,
        started_at=now,
        completed_at=now,
        duration_ms=0,
        retry_count=0,
    )
    db.add(execution)
    workflow.execution_count += 1
    workflow.last_run_at = now
    return execution


def list_executions(
    db: Session,
    workflow_id: UUID,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
) -> tuple[list[MarketingAutomationExecution], int]:
    _get_workflow_or_404(db, workflow_id)
    query = select(MarketingAutomationExecution).where(MarketingAutomationExecution.workflow_id == workflow_id)
    if status_filter:
        query = query.where(MarketingAutomationExecution.status == MarketingAutomationExecutionStatus(status_filter))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingAutomationExecution.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def execution_to_summary(execution: MarketingAutomationExecution) -> dict[str, Any]:
    return {
        "id": execution.id,
        "workflow_id": execution.workflow_id,
        "workflow_version": execution.workflow_version,
        "status": execution.status.value,
        "trigger_type": execution.trigger_type,
        "error_message": execution.error_message,
        "duration_ms": execution.duration_ms,
        "retry_count": execution.retry_count,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "created_at": execution.created_at,
    }


def execution_to_detail(execution: MarketingAutomationExecution) -> dict[str, Any]:
    return {
        **execution_to_summary(execution),
        "trigger_context": _sanitize_payload(execution.trigger_context_json),
        "actions_executed": execution.actions_executed_json,
        "actions_skipped": execution.actions_skipped_json,
    }


def execution_to_log_entry(execution: MarketingAutomationExecution) -> dict[str, Any]:
    attempted = len(execution.actions_executed_json or []) + len(execution.actions_skipped_json or [])
    completed = len(execution.actions_executed_json or [])
    level = "error" if execution.status == MarketingAutomationExecutionStatus.FAILED else "warning" if execution.status == MarketingAutomationExecutionStatus.NOT_CONNECTED else "info"
    return {
        "id": execution.id,
        "execution_id": execution.id,
        "level": level,
        "message": execution.error_message or f"Execution {execution.status.value}",
        "trigger_type": execution.trigger_type,
        "actions_attempted": attempted,
        "actions_completed": completed,
        "failure_reason": execution.error_message,
        "retry_count": execution.retry_count,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "duration_ms": execution.duration_ms,
        "created_at": execution.created_at,
    }


def get_workflow_metrics(db: Session, workflow_id: UUID) -> dict[str, Any]:
    workflow = _get_workflow_or_404(db, workflow_id)
    completed = db.scalar(
        select(func.count()).where(
            MarketingAutomationExecution.workflow_id == workflow_id,
            MarketingAutomationExecution.status == MarketingAutomationExecutionStatus.COMPLETED,
        )
    ) or 0
    failed = db.scalar(
        select(func.count()).where(
            MarketingAutomationExecution.workflow_id == workflow_id,
            MarketingAutomationExecution.status == MarketingAutomationExecutionStatus.FAILED,
        )
    ) or 0
    skipped = db.scalar(
        select(func.count()).where(
            MarketingAutomationExecution.workflow_id == workflow_id,
            MarketingAutomationExecution.status == MarketingAutomationExecutionStatus.SKIPPED,
        )
    ) or 0
    not_connected = db.scalar(
        select(func.count()).where(
            MarketingAutomationExecution.workflow_id == workflow_id,
            MarketingAutomationExecution.status == MarketingAutomationExecutionStatus.NOT_CONNECTED,
        )
    ) or 0
    avg_duration = db.scalar(
        select(func.avg(MarketingAutomationExecution.duration_ms)).where(
            MarketingAutomationExecution.workflow_id == workflow_id,
            MarketingAutomationExecution.duration_ms.is_not(None),
        )
    )
    return {
        "workflow_id": workflow.id,
        "status": workflow.status.value,
        "execution_count": workflow.execution_count,
        "completed_count": completed,
        "failed_count": failed,
        "skipped_count": skipped,
        "not_connected_count": not_connected,
        "average_duration_ms": int(avg_duration) if avg_duration is not None else None,
        "last_run_at": workflow.last_run_at,
        "activated_at": workflow.activated_at,
        "execution_engine_available": is_execution_engine_available(),
        "execution_engine_message": execution_engine_message(),
    }


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _SECRET_KEY_PATTERN.search(key):
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = _sanitize_payload(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    return value
