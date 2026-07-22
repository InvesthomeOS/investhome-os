"""Project detail workspace schemas (Sprint 10A3)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.schemas.project import ProjectResponse, ProjectTeamMemberResponse
from investhome_api.schemas.project_dashboard import (
    MetricValue,
    ProjectActivityItem,
    ProjectAlertItem,
    ProjectMilestoneItem,
    ProjectRiskLevel,
)


class ProjectDetailPermissions(BaseModel):
    can_edit: bool = False
    can_archive: bool = False
    can_restore: bool = False
    can_manage_status: bool = False
    can_view_financial: bool = False
    can_edit_financial: bool = False
    can_view_team: bool = False
    can_manage_team: bool = False
    can_export: bool = False


class ProjectDetailNavigationItem(BaseModel):
    key: str
    href: str
    visible: bool = True


class ProjectDetailShell(BaseModel):
    project: ProjectResponse
    permissions: ProjectDetailPermissions
    navigation: list[ProjectDetailNavigationItem]
    risk: ProjectRiskLevel
    financial_access: bool
    alerts_count: int = 0
    milestones_count: int = 0
    team_count: int = 0
    documents_count: int = 0
    units_count: int = 0
    data_completeness: dict[str, str] = Field(default_factory=dict)


class ProjectOverviewResponse(BaseModel):
    shell: ProjectDetailShell
    snapshot: dict[str, Any]
    schedule: dict[str, Any]
    financial_snapshot: dict[str, MetricValue] | None
    construction_snapshot: dict[str, Any]
    sales_leasing_snapshot: dict[str, MetricValue]
    team: list[ProjectTeamMemberResponse]
    milestones: list[ProjectMilestoneItem]
    alerts: list[ProjectAlertItem]
    activity: list[ProjectActivityItem]
    key_documents: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)


class ProjectFinancialsResponse(BaseModel):
    financial_access: bool
    summary: dict[str, MetricValue] | None = None
    budgets: list[dict[str, Any]] = Field(default_factory=list)
    capital: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProjectScheduleResponse(BaseModel):
    key_dates: dict[str, date | None]
    days_remaining: int | None
    days_delayed: int | None
    is_delayed: bool
    missing_dates: list[str]
    milestones: list[ProjectMilestoneItem]
    risks: list[str] = Field(default_factory=list)


class ProjectConstructionResponse(BaseModel):
    completion_percentage: Decimal | None
    development_stage: str | None
    status: str
    is_delayed: bool
    days_remaining: int | None
    budget_utilization: MetricValue
    risk: ProjectRiskLevel
    alerts: list[ProjectAlertItem]
    warnings: list[str] = Field(default_factory=list)


class ProjectUnitsResponse(BaseModel):
    summary: dict[str, MetricValue]
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    pages: int
    warnings: list[str] = Field(default_factory=list)


class ProjectSalesResponse(BaseModel):
    summary: dict[str, MetricValue]
    opportunities: list[dict[str, Any]]
    total_opportunities: int
    by_status: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ProjectLeasingResponse(BaseModel):
    summary: dict[str, MetricValue]
    by_status: dict[str, int] = Field(default_factory=dict)
    items: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProjectInvestorsResponse(BaseModel):
    financial_access: bool
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    warnings: list[str] = Field(default_factory=list)


class ProjectDocumentsResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    warnings: list[str] = Field(default_factory=list)


class ProjectDirectoryUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    job_title: str | None = None
    status: str


class ProjectDirectoryUserListResponse(BaseModel):
    items: list[ProjectDirectoryUser]
    total: int


