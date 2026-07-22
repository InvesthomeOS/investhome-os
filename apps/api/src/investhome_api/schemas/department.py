"""Department management API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.department import (
    AssignmentStatus,
    BudgetApprovalStatus,
    DepartmentStatus,
    DepartmentType,
    KPIStatus,
    ResponsibilityStatus,
)


class DepartmentBase(BaseModel):
    department_code: str = Field(min_length=1, max_length=50)
    department_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    company_id: UUID
    branch_id: UUID | None = None
    department_type: DepartmentType = DepartmentType.OTHER
    parent_department_id: UUID | None = None
    department_head_user_id: UUID | None = None
    cost_center: str | None = Field(default=None, max_length=50)
    status: DepartmentStatus = DepartmentStatus.DRAFT
    start_date: date | None = None
    end_date: date | None = None
    annual_budget: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    fiscal_year: int | None = None
    notes: str | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    department_code: str | None = Field(default=None, min_length=1, max_length=50)
    department_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    branch_id: UUID | None = None
    department_type: DepartmentType | None = None
    parent_department_id: UUID | None = None
    department_head_user_id: UUID | None = None
    cost_center: str | None = Field(default=None, max_length=50)
    status: DepartmentStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    annual_budget: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    fiscal_year: int | None = None
    notes: str | None = None


class DepartmentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_code: str
    department_name: str
    company_id: UUID
    company_name: str | None = None
    branch_id: UUID | None = None
    branch_name: str | None = None
    department_type: str
    parent_department_id: UUID | None = None
    department_head_user_id: UUID | None = None
    head_name: str | None = None
    cost_center: str | None = None
    status: str
    employee_count: int
    team_count: int
    open_positions: int
    annual_budget: Decimal | None = None
    currency: str | None = None
    fiscal_year: int | None = None
    created_at: datetime
    updated_at: datetime


class DepartmentDetailResponse(DepartmentSummaryResponse):
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    merged_into_department_id: UUID | None = None
    notes: str | None = None
    archived_at: datetime | None = None
    child_count: int = 0


class DepartmentListResponse(BaseModel):
    items: list[DepartmentSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DepartmentMutationResponse(BaseModel):
    department: DepartmentDetailResponse
    warnings: list[str] = Field(default_factory=list)


class DepartmentTreeNode(BaseModel):
    id: UUID
    department_code: str
    department_name: str
    department_type: str
    status: str
    parent_department_id: UUID | None = None
    department_head_user_id: UUID | None = None
    head_name: str | None = None
    employee_count: int
    team_count: int
    children: list[DepartmentTreeNode] = Field(default_factory=list)


class DepartmentTreeResponse(BaseModel):
    items: list[DepartmentTreeNode]
    total: int


class DepartmentDashboardMetrics(BaseModel):
    total_departments: int
    active_departments: int
    without_head: int
    total_employees: int
    open_positions: int
    over_budget: int
    below_kpi_target: int
    recent_org_changes: int


class AssignHeadRequest(BaseModel):
    user_id: UUID


class EmployeeAssignmentItem(BaseModel):
    user_id: UUID
    allocation_percentage: int = Field(default=100, ge=0, le=100)
    is_primary: bool = False
    effective_date: date | None = None
    end_date: date | None = None


class AssignEmployeesRequest(BaseModel):
    assignments: list[EmployeeAssignmentItem]


class TransferEmployeesRequest(BaseModel):
    target_department_id: UUID
    user_ids: list[UUID]
    end_date: date | None = None


class MoveDepartmentRequest(BaseModel):
    company_id: UUID | None = None
    branch_id: UUID | None = None
    parent_department_id: UUID | None = None


class MergeDepartmentRequest(BaseModel):
    target_department_id: UUID
    notes: str | None = None


class DepartmentEmployeeResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str | None = None
    allocation_percentage: int
    is_primary: bool
    effective_date: date | None = None
    end_date: date | None = None
    status: str


class DepartmentEmployeesResponse(BaseModel):
    items: list[DepartmentEmployeeResponse]
    total: int


class DepartmentTeamsResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
    total: int
    stub: bool = True


class DepartmentProjectsResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
    total: int
    stub: bool = True


class DepartmentKPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    target: Decimal | None = None
    current_value: Decimal | None = None
    unit: str | None = None
    period: str | None = None
    owner_id: UUID | None = None
    progress: Decimal | None = None
    status: str


class DepartmentKPIsResponse(BaseModel):
    items: list[DepartmentKPIResponse]
    total: int


class DepartmentKPICreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    target: Decimal | None = None
    current_value: Decimal | None = None
    unit: str | None = Field(default=None, max_length=50)
    period: str | None = Field(default=None, max_length=50)
    owner_id: UUID | None = None
    status: KPIStatus = KPIStatus.ON_TRACK


class DepartmentBudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fiscal_year: int
    approved_budget: Decimal | None = None
    used_budget: Decimal | None = None
    currency: str | None = None
    cost_center: str | None = None
    owner_id: UUID | None = None
    approval_status: str


class DepartmentBudgetCreate(BaseModel):
    fiscal_year: int
    approved_budget: Decimal | None = None
    used_budget: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    cost_center: str | None = Field(default=None, max_length=50)
    owner_id: UUID | None = None
    approval_status: BudgetApprovalStatus = BudgetApprovalStatus.DRAFT
