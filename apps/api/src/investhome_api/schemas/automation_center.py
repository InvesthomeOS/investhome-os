"""Schemas for the Automation Center control-tower API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

WorkflowCategory = Literal[
    "crm",
    "marketing",
    "investor",
    "finance",
    "projects",
    "website",
    "ai",
    "notifications",
    "administration",
]

WorkflowSource = Literal["marketing_automation", "arq_cron", "catalog_placeholder"]

ScheduleCadence = Literal["hourly", "daily", "weekly", "monthly", "manual", "webhook", "custom"]

IntegrationStatus = Literal["connected", "configured", "unavailable", "disabled", "unknown"]

ExecutionStatus = Literal["running", "queued", "completed", "failed", "cancelled", "skipped", "not_connected"]

ErrorSeverity = Literal["info", "warning", "error", "critical"]


class SystemHealthSummary(BaseModel):
    running_count: int = 0
    failed_count: int = 0
    queued_count: int = 0
    completed_count: int = 0
    average_runtime_ms: int | None = None
    queue_size: int | None = None
    queue_available: bool = False
    last_execution_at: datetime | None = None
    availability: Literal["available", "degraded", "unavailable"] = "unavailable"
    execution_engine_available: bool = False
    execution_engine_message: str = ""
    workflow_total: int = 0
    workflow_active: int = 0


class AutomationOverviewResponse(BaseModel):
    health: SystemHealthSummary
    workflow_status: list[dict[str, Any]] = Field(default_factory=list)
    recent_failures: list["AutomationErrorItem"] = Field(default_factory=list)
    recent_executions: list["AutomationExecutionItem"] = Field(default_factory=list)
    scheduled_jobs: list["AutomationScheduleItem"] = Field(default_factory=list)
    ai_workflows: list["AutomationWorkflowSummary"] = Field(default_factory=list)
    integrations: list["AutomationIntegrationItem"] = Field(default_factory=list)
    queue_health: "QueueHealthResponse"


class AutomationWorkflowSummary(BaseModel):
    id: str
    name: str
    category: WorkflowCategory
    source: WorkflowSource
    status: str
    trigger: str | None = None
    trigger_label: str | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    next_run_label: str | None = None
    success_rate: float | None = None
    success_rate_available: bool = False
    execution_count: int = 0
    description: str | None = None
    manage_href: str | None = None
    is_placeholder: bool = False


class AutomationWorkflowListResponse(BaseModel):
    items: list[AutomationWorkflowSummary]
    total: int
    page: int
    page_size: int
    pages: int
    categories: list[WorkflowCategory]


class AutomationWorkflowStep(BaseModel):
    id: str
    type: str
    label: str
    config: dict[str, Any] = Field(default_factory=dict)


class AutomationWorkflowDetail(AutomationWorkflowSummary):
    timezone: str | None = None
    steps: list[AutomationWorkflowStep] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    trigger_config: dict[str, Any] | None = None
    history: list["AutomationExecutionItem"] = Field(default_factory=list)
    logs: list["AutomationLogItem"] = Field(default_factory=list)
    execution_engine_available: bool = False
    execution_engine_message: str = ""
    can_retry: bool = False
    can_pause: bool = False
    can_resume: bool = False


class AutomationExecutionItem(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str | None = None
    status: str
    trigger_type: str | None = None
    retry_count: int = 0
    duration_ms: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    category: WorkflowCategory | None = None


class AutomationExecutionListResponse(BaseModel):
    items: list[AutomationExecutionItem]
    total: int
    page: int
    page_size: int
    pages: int
    status_counts: dict[str, int] = Field(default_factory=dict)


class AutomationErrorItem(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str | None = None
    time: datetime | None = None
    severity: ErrorSeverity = "error"
    message: str
    retry_count: int = 0
    can_retry: bool = False
    status: str = "failed"
    category: WorkflowCategory | None = None


class AutomationErrorListResponse(BaseModel):
    items: list[AutomationErrorItem]
    total: int
    page: int
    page_size: int
    pages: int


class AutomationScheduleItem(BaseModel):
    id: str
    name: str
    category: WorkflowCategory
    cadence: ScheduleCadence
    cadence_label: str
    cron_expression: str | None = None
    next_run_label: str | None = None
    last_run_at: datetime | None = None
    status: str
    source: WorkflowSource
    description: str | None = None


class AutomationScheduleListResponse(BaseModel):
    items: list[AutomationScheduleItem]
    total: int


class AutomationIntegrationItem(BaseModel):
    id: str
    name: str
    status: IntegrationStatus
    status_label: str
    configured: bool = False
    feature_flag: str | None = None
    env_keys: list[str] = Field(default_factory=list)
    notes: str | None = None
    href: str | None = None


class AutomationIntegrationListResponse(BaseModel):
    items: list[AutomationIntegrationItem]
    total: int


class AutomationAuditItem(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None = None
    entity_label: str | None = None
    description_key: str | None = None
    actor_name: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutomationAuditListResponse(BaseModel):
    items: list[AutomationAuditItem]
    total: int
    page: int
    page_size: int
    pages: int


class AutomationLogItem(BaseModel):
    id: str
    level: ErrorSeverity | Literal["info", "warning", "error"]
    message: str
    created_at: datetime | None = None
    retry_count: int = 0


class QueueHealthResponse(BaseModel):
    available: bool = False
    redis_connected: bool = False
    queue_size: int | None = None
    worker_registered: bool = True
    message: str = ""
    jobs: list[dict[str, Any]] = Field(default_factory=list)


class AutomationRetryResponse(BaseModel):
    accepted: bool = False
    message: str
