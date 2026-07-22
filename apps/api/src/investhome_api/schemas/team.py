"""Team management API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.team import (
    TeamCapacityStatus,
    TeamGoalStatus,
    TeamKpiStatus,
    TeamLeadRole,
    TeamLeadStatus,
    TeamMemberStatus,
    TeamMembershipType,
    TeamProjectLinkStatus,
    TeamStatus,
    TeamTaskPriority,
    TeamTaskStatus,
    TeamType,
)


class TeamBase(BaseModel):
    team_code: str = Field(min_length=1, max_length=50)
    team_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    company_id: UUID
    branch_id: UUID | None = None
    department_id: UUID | None = None
    team_type: TeamType = TeamType.FUNCTIONAL
    parent_team_id: UUID | None = None
    cost_center: str | None = Field(default=None, max_length=50)
    status: TeamStatus = TeamStatus.DRAFT
    start_date: date | None = None
    end_date: date | None = None
    total_available_hours: Decimal = Field(default=Decimal("0"), ge=0)


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    team_code: str | None = Field(default=None, min_length=1, max_length=50)
    team_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    team_type: TeamType | None = None
    parent_team_id: UUID | None = None
    cost_center: str | None = Field(default=None, max_length=50)
    status: TeamStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    total_available_hours: Decimal | None = Field(default=None, ge=0)


class TeamSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_code: str
    team_name: str
    company_id: UUID
    company_name: str | None = None
    branch_id: UUID | None = None
    branch_name: str | None = None
    department_id: UUID | None = None
    team_type: str
    parent_team_id: UUID | None = None
    cost_center: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    total_available_hours: Decimal
    allocated_hours: Decimal
    member_count: int
    active_projects_count: int
    open_tasks_count: int
    health_score: int = 0
    primary_lead_user_id: UUID | None = None
    primary_lead_name: str | None = None
    created_at: datetime
    updated_at: datetime


class TeamDetailResponse(TeamSummaryResponse):
    description: str | None = None
    merged_into_team_id: UUID | None = None
    disband_reason: str | None = None
    disband_effective_date: date | None = None
    archived_at: datetime | None = None
    child_team_count: int = 0
    allocation_warnings: list[str] = Field(default_factory=list)


class TeamListResponse(BaseModel):
    items: list[TeamSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TeamTreeNode(BaseModel):
    id: UUID
    team_code: str
    team_name: str
    status: str
    member_count: int
    health_score: int
    children: list[TeamTreeNode] = Field(default_factory=list)


class TeamTreeResponse(BaseModel):
    items: list[TeamTreeNode]


class TeamDashboardMetrics(BaseModel):
    total_teams: int
    active_teams: int
    forming_teams: int
    total_members: int
    avg_health_score: int
    over_allocated_members: int
    open_tasks: int
    active_projects: int


class TeamLeadAssignRequest(BaseModel):
    user_id: UUID
    lead_role: TeamLeadRole = TeamLeadRole.PRIMARY
    start_date: date | None = None
    end_date: date | None = None
    is_temporary: bool = False


class TeamLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: UUID
    user_name: str | None = None
    lead_role: str
    start_date: date | None = None
    end_date: date | None = None
    is_temporary: bool
    status: str
    created_at: datetime
    updated_at: datetime


class TeamMemberCreate(BaseModel):
    user_id: UUID
    role_in_team: str | None = Field(default=None, max_length=120)
    membership_type: TeamMembershipType = TeamMembershipType.PRIMARY
    allocation_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    start_date: date | None = None
    end_date: date | None = None
    workload_hours: Decimal = Field(default=Decimal("0"), ge=0)
    status: TeamMemberStatus = TeamMemberStatus.ACTIVE


class TeamMemberUpdate(BaseModel):
    role_in_team: str | None = Field(default=None, max_length=120)
    membership_type: TeamMembershipType | None = None
    allocation_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    start_date: date | None = None
    end_date: date | None = None
    workload_hours: Decimal | None = Field(default=None, ge=0)
    status: TeamMemberStatus | None = None


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: UUID
    user_name: str | None = None
    role_in_team: str | None = None
    membership_type: str
    allocation_percentage: Decimal
    start_date: date | None = None
    end_date: date | None = None
    workload_hours: Decimal
    status: str
    total_allocation_across_teams: Decimal = Decimal("0")
    allocation_warning: str | None = None
    created_at: datetime
    updated_at: datetime


class TeamMemberTransferRequest(BaseModel):
    user_id: UUID
    target_team_id: UUID
    allocation_percentage: Decimal | None = Field(default=None, ge=0, le=100)


class TeamProjectAssignRequest(BaseModel):
    project_id: UUID | None = None
    project_stub_name: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    allocation_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    budget: Decimal | None = Field(default=None, ge=0)


class TeamProjectLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    project_id: UUID | None = None
    project_name: str | None = None
    project_stub_name: str | None = None
    role: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    allocation_percentage: Decimal
    budget: Decimal | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class TeamTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    assigned_user_id: UUID | None = None
    priority: TeamTaskPriority = TeamTaskPriority.MEDIUM
    due_date: date | None = None
    status: TeamTaskStatus = TeamTaskStatus.OPEN
    estimated_hours: Decimal = Field(default=Decimal("0"), ge=0)
    actual_hours: Decimal = Field(default=Decimal("0"), ge=0)
    project_id: UUID | None = None
    work_item_id: UUID | None = None


class TeamTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    assigned_user_id: UUID | None = None
    priority: TeamTaskPriority | None = None
    due_date: date | None = None
    status: TeamTaskStatus | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    actual_hours: Decimal | None = Field(default=None, ge=0)
    project_id: UUID | None = None
    work_item_id: UUID | None = None


class TeamTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    assigned_user_id: UUID | None = None
    assigned_user_name: str | None = None
    work_item_id: UUID | None = None
    title: str
    priority: str
    due_date: date | None = None
    status: str
    estimated_hours: Decimal
    actual_hours: Decimal
    project_id: UUID | None = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime


class TeamGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    target_value: Decimal | None = None
    current_value: Decimal = Field(default=Decimal("0"), ge=0)
    unit: str | None = Field(default=None, max_length=50)
    due_date: date | None = None
    status: TeamGoalStatus = TeamGoalStatus.DRAFT


class TeamGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    title: str
    description: str | None = None
    target_value: Decimal | None = None
    current_value: Decimal
    unit: str | None = None
    due_date: date | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class TeamKpiCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    target_value: Decimal = Field(default=Decimal("0"), ge=0)
    current_value: Decimal = Field(default=Decimal("0"), ge=0)
    unit: str | None = Field(default=None, max_length=50)
    period: str | None = Field(default=None, max_length=30)
    status: TeamKpiStatus = TeamKpiStatus.ON_TRACK


class TeamKpiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    name: str
    description: str | None = None
    target_value: Decimal
    current_value: Decimal
    unit: str | None = None
    period: str | None = None
    status: str
    achievement_percentage: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime


class TeamCapacitySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    period: str
    period_start: date | None = None
    period_end: date | None = None
    available_hours: Decimal
    allocated_hours: Decimal
    remaining_hours: Decimal
    utilization_percentage: Decimal
    status: str
    created_at: datetime


class TeamMoveRequest(BaseModel):
    company_id: UUID | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    parent_team_id: UUID | None = None


class TeamMergeRequest(BaseModel):
    source_team_id: UUID
    target_team_id: UUID
    reason: str | None = None


class TeamDisbandRequest(BaseModel):
    reason: str = Field(min_length=1)
    effective_date: date
    transfer_members_to_team_id: UUID | None = None
    reassign_tasks_to_user_id: UUID | None = None
    close_goals: bool = True


class TeamDisbandChecklistResponse(BaseModel):
    can_disband: bool
    blockers: list[str]
    active_members: int
    active_projects: int
    open_tasks: int
    active_goals: int
    child_teams: int


class TeamPerformanceResponse(BaseModel):
    health_score: int
    task_completion_rate: Decimal
    overdue_ratio: Decimal
    capacity_balance: Decimal
    kpi_achievement: Decimal
    member_stability: Decimal
    project_delivery: Decimal


class TeamMutationResponse(BaseModel):
    team: TeamDetailResponse
    warnings: list[str] = Field(default_factory=list)


class TeamWorkloadMember(BaseModel):
    user_id: UUID
    user_name: str
    total_allocation: Decimal
    total_hours: Decimal
    teams: list[str]
    heat_level: int


class TeamWorkloadResponse(BaseModel):
    period: str
    members: list[TeamWorkloadMember]
    team_id: UUID | None = None
