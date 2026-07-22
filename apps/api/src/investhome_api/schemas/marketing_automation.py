"""Pydantic schemas for marketing automation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from investhome_api.models.marketing_automation import (
    MarketingAutomationActionType,
    MarketingAutomationConditionOperator,
    MarketingAutomationDelayUnit,
    MarketingAutomationExecutionStatus,
    MarketingAutomationTemplateCategory,
    MarketingAutomationTriggerType,
    MarketingAutomationWorkflowStatus,
)

# --- Reference enums for API consumers ---

TRIGGER_TYPES = [t.value for t in MarketingAutomationTriggerType]
CONDITION_OPERATORS = [c.value for c in MarketingAutomationConditionOperator]
ACTION_TYPES = [a.value for a in MarketingAutomationActionType]
DELAY_UNITS = [d.value for d in MarketingAutomationDelayUnit]
WORKFLOW_STATUSES = [s.value for s in MarketingAutomationWorkflowStatus]
TEMPLATE_CATEGORIES = [c.value for c in MarketingAutomationTemplateCategory]
JOURNEY_NODE_TYPES = ["trigger", "condition", "delay", "action", "decision", "end"]


class AutomationTriggerSchema(BaseModel):
    type: str
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_trigger_type(cls, v: str) -> str:
        if v not in TRIGGER_TYPES:
            raise ValueError(f"Invalid trigger type: {v}. Must be one of {TRIGGER_TYPES}")
        return v


class AutomationConditionSchema(BaseModel):
    field: str
    operator: str
    value: Any = None
    value_to: Any = None

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in CONDITION_OPERATORS:
            raise ValueError(f"Invalid condition operator: {v}")
        return v


class AutomationActionSchema(BaseModel):
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None

    @field_validator("type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in ACTION_TYPES:
            raise ValueError(f"Invalid action type: {v}")
        return v


class AutomationDelaySchema(BaseModel):
    unit: str
    amount: int | None = None
    specific_date: datetime | None = None
    timezone: str = "UTC"

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v not in DELAY_UNITS:
            raise ValueError(f"Invalid delay unit: {v}")
        return v


class AutomationBranchSchema(BaseModel):
    branch_type: Literal["if", "else_if", "else", "switch"] = "if"
    conditions: list[AutomationConditionSchema] = Field(default_factory=list)
    branches: list[dict[str, Any]] = Field(default_factory=list)


class JourneyNodeSchema(BaseModel):
    id: str
    type: str
    label: str
    x: float = 0
    y: float = 0
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        if v not in JOURNEY_NODE_TYPES:
            raise ValueError(f"Invalid journey node type: {v}")
        return v


class JourneyEdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class JourneyGraphSchema(BaseModel):
    nodes: list[JourneyNodeSchema] = Field(default_factory=list)
    edges: list[JourneyEdgeSchema] = Field(default_factory=list)

    @field_validator("nodes")
    @classmethod
    def validate_graph_has_trigger_and_end(cls, nodes: list[JourneyNodeSchema]) -> list[JourneyNodeSchema]:
        if nodes:
            types = {n.type for n in nodes}
            if "trigger" not in types:
                raise ValueError("Journey graph must contain at least one trigger node")
            if "end" not in types:
                raise ValueError("Journey graph must contain at least one end node")
        return nodes


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    status: str = "draft"
    trigger: AutomationTriggerSchema | None = None
    conditions: list[AutomationConditionSchema] = Field(default_factory=list)
    actions: list[AutomationActionSchema] = Field(default_factory=list)
    journey_graph: JourneyGraphSchema | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    timezone: str = "UTC"
    is_journey: bool = False

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in WORKFLOW_STATUSES:
            raise ValueError(f"Invalid workflow status: {v}")
        return v

    @model_validator(mode="after")
    def validate_definition(self) -> WorkflowCreate:
        if not self.is_journey:
            if not self.trigger:
                raise ValueError("Automation requires a trigger")
            if not self.actions:
                raise ValueError("Automation requires at least one action")
        return self


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    status: str | None = None
    trigger: AutomationTriggerSchema | None = None
    conditions: list[AutomationConditionSchema] | None = None
    actions: list[AutomationActionSchema] | None = None
    journey_graph: JourneyGraphSchema | None = None
    owner_user_id: UUID | None = None
    team_id: UUID | None = None
    timezone: str | None = None
    is_journey: bool | None = None
    change_summary: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in WORKFLOW_STATUSES:
            raise ValueError(f"Invalid workflow status: {v}")
        return v


class WorkflowSummary(BaseModel):
    id: UUID
    name: str
    code: str | None
    description: str | None
    status: str
    version: int
    is_journey: bool
    owner_user_id: UUID | None
    created_by_user_id: UUID | None = None
    team_id: UUID | None
    activated_at: datetime | None = None
    last_run_at: datetime | None = None
    execution_count: int = 0
    execution_engine_available: bool = False
    created_at: datetime
    updated_at: datetime


class WorkflowDetail(WorkflowSummary):
    trigger: dict[str, Any] | None
    conditions: list[dict[str, Any]] | None
    actions: list[dict[str, Any]] | None
    journey_graph: dict[str, Any] | None
    timezone: str


class WorkflowListResponse(BaseModel):
    items: list[WorkflowSummary]
    total: int
    page: int
    page_size: int
    pages: int


class ExecutionSummary(BaseModel):
    id: UUID
    workflow_id: UUID
    workflow_version: int
    status: str
    trigger_type: str | None
    error_message: str | None
    duration_ms: int | None
    retry_count: int = 0
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ExecutionDetail(ExecutionSummary):
    trigger_context: dict[str, Any] | None
    actions_executed: list[dict[str, Any]] | None
    actions_skipped: list[dict[str, Any]] | None


class ExecutionListResponse(BaseModel):
    items: list[ExecutionSummary]
    total: int
    page: int
    page_size: int
    pages: int


class AutomationLogEntry(BaseModel):
    id: UUID
    execution_id: UUID
    level: Literal["info", "warning", "error"]
    message: str
    trigger_type: str | None = None
    actions_attempted: int = 0
    actions_completed: int = 0
    failure_reason: str | None = None
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    created_at: datetime


class AutomationLogListResponse(BaseModel):
    items: list[AutomationLogEntry]
    total: int
    page: int
    page_size: int
    pages: int


class AutomationMetricsResponse(BaseModel):
    workflow_id: UUID
    status: str
    execution_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    not_connected_count: int
    average_duration_ms: int | None
    last_run_at: datetime | None
    activated_at: datetime | None
    execution_engine_available: bool
    execution_engine_message: str


class TemplateSummary(BaseModel):
    id: UUID
    name: str
    code: str
    description: str | None
    category: str
    is_journey: bool
    is_active: bool
    created_at: datetime


class TemplateDetail(TemplateSummary):
    trigger: dict[str, Any] | None
    conditions: list[dict[str, Any]] | None
    actions: list[dict[str, Any]] | None
    journey_graph: dict[str, Any] | None


class TemplateListResponse(BaseModel):
    items: list[TemplateSummary]
    total: int


class CreateFromTemplateRequest(BaseModel):
    template_id: UUID
    name: str = Field(min_length=1, max_length=255)
    code: str | None = None


class VersionSummary(BaseModel):
    id: UUID
    workflow_id: UUID
    version_number: int
    change_summary: str | None
    created_by_user_id: UUID | None
    created_at: datetime


class VersionDetail(VersionSummary):
    snapshot: dict[str, Any]


class VersionCompareResponse(BaseModel):
    version_a: int
    version_b: int
    diff: dict[str, Any]


class VersionRestoreRequest(BaseModel):
    version_number: int
    change_summary: str | None = None


class ExecuteWorkflowRequest(BaseModel):
    trigger_context: dict[str, Any] = Field(default_factory=dict)


class ExecuteWorkflowResponse(BaseModel):
    execution_id: UUID
    status: str
    message: str


class DashboardMetric(BaseModel):
    key: str
    label: str
    value: int | str | None
    state: Literal["ready", "unknown", "warning", "error"] = "unknown"


class DashboardExecutionItem(BaseModel):
    id: UUID
    workflow_id: UUID
    workflow_name: str | None
    status: str
    trigger_type: str | None
    error_message: str | None
    created_at: datetime


class AutomationDashboardResponse(BaseModel):
    metrics: list[DashboardMetric]
    recent_executions: list[DashboardExecutionItem]
    recent_errors: list[DashboardExecutionItem]
    recommendations: list[str]


class AutomationHealthResponse(BaseModel):
    overall_status: Literal["healthy", "warning", "critical", "unknown"]
    workflow_errors: DashboardMetric
    failed_executions: DashboardMetric
    queue_length: DashboardMetric
    average_runtime_ms: DashboardMetric
    retry_count: DashboardMetric
    journey_health: DashboardMetric
    automation_health: DashboardMetric


class TriggerReferenceItem(BaseModel):
    type: str
    label: str
    description: str


class ActionReferenceItem(BaseModel):
    type: str
    label: str
    description: str
    connection_status: Literal["connected", "not_connected", "unknown"] = "unknown"


class TriggersReferenceResponse(BaseModel):
    triggers: list[TriggerReferenceItem]


class ActionsReferenceResponse(BaseModel):
    actions: list[ActionReferenceItem]
