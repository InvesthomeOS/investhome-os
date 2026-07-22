"""Schemas for normalized project budget foundation (Sprint 10A4A)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.project_budget import (
    BudgetCategoryType,
    BudgetRevisionStatus,
    BudgetVersionStatus,
)
from investhome_api.schemas.project_dashboard import MetricValue


class BudgetPermissions(BaseModel):
    can_view: bool = False
    can_edit: bool = False
    can_manage: bool = False
    can_approve: bool = False
    can_export: bool = False
    can_manage_cost_codes: bool = False


class BudgetCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    code: str
    name: str
    description: str | None
    category_type: BudgetCategoryType
    parent_id: UUID | None
    sort_order: int
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime


class BudgetCategoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_type: BudgetCategoryType
    parent_id: UUID | None = None
    sort_order: int = 0
    company_id: UUID | None = None


class BudgetCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_type: BudgetCategoryType | None = None
    parent_id: UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CostCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    code: str
    name: str
    description: str | None
    category_id: UUID
    parent_id: UUID | None
    level: int
    is_active: bool
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CostCodeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: UUID
    parent_id: UUID | None = None
    level: int = 1
    sort_order: int = 0
    company_id: UUID | None = None


class CostCodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: UUID | None = None
    parent_id: UUID | None = None
    level: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class BudgetVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    effective_date: date | None = None


class BudgetVersionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    effective_date: date | None = None


class BudgetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    project_id: UUID
    name: str
    version_number: int
    status: BudgetVersionStatus
    description: str | None
    currency: str
    effective_date: date | None
    approved_at: datetime | None
    approved_by_user_id: UUID | None
    submitted_at: datetime | None
    submitted_by_user_id: UUID | None
    locked_at: datetime | None
    locked_by_user_id: UUID | None
    is_current: bool
    original_budget_total: Decimal | None = None
    current_budget_total: Decimal | None = None
    created_at: datetime
    created_by_user_id: UUID | None
    updated_at: datetime
    updated_by_user_id: UUID | None


class BudgetVersionListResponse(BaseModel):
    items: list[BudgetVersionResponse]
    total: int


class BudgetLineCreate(BaseModel):
    category_id: UUID
    cost_code_id: UUID | None = None
    parent_line_id: UUID | None = None
    line_number: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = Field(default=None, max_length=50)
    unit_cost: Decimal | None = None
    original_budget: Decimal = Field(default=Decimal("0"))
    notes: str | None = None
    sort_order: int = 0
    is_summary: bool = False


class BudgetLineUpdate(BaseModel):
    category_id: UUID | None = None
    cost_code_id: UUID | None = None
    parent_line_id: UUID | None = None
    line_number: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_cost: Decimal | None = None
    original_budget: Decimal | None = None
    notes: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    is_summary: bool | None = None


class BudgetLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    project_id: UUID
    budget_version_id: UUID
    category_id: UUID
    cost_code_id: UUID | None
    parent_line_id: UUID | None
    legacy_project_budget_id: UUID | None
    line_number: str
    name: str
    description: str | None
    quantity: Decimal | None
    unit: str | None
    unit_cost: Decimal | None
    original_budget: Decimal
    approved_revisions: Decimal
    current_budget: Decimal
    committed_cost: Decimal | None
    actual_cost: Decimal | None
    forecast_to_complete: Decimal | None
    forecast_at_completion: Decimal | None
    variance: Decimal | None
    currency: str
    notes: str | None
    sort_order: int
    is_summary: bool
    is_active: bool
    category_code: str | None = None
    category_name: str | None = None
    cost_code: str | None = None
    cost_code_name: str | None = None
    created_at: datetime
    updated_at: datetime


class BudgetLineListResponse(BaseModel):
    items: list[BudgetLineResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BudgetLineReorderRequest(BaseModel):
    line_ids: list[UUID] = Field(min_length=1)


class BudgetLineBulkCreateRequest(BaseModel):
    lines: list[BudgetLineCreate] = Field(min_length=1, max_length=500)


class RevisionLineInput(BaseModel):
    budget_line_id: UUID
    amount: Decimal
    description: str | None = None


class BudgetRevisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    effective_date: date | None = None
    lines: list[RevisionLineInput] = Field(min_length=1)


class BudgetRevisionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    effective_date: date | None = None
    lines: list[RevisionLineInput] | None = None


class BudgetRevisionLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision_id: UUID
    budget_line_id: UUID
    amount: Decimal
    description: str | None


class BudgetRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    budget_version_id: UUID
    revision_number: int
    title: str
    description: str | None
    status: BudgetRevisionStatus
    effective_date: date | None
    amount: Decimal
    submitted_at: datetime | None
    submitted_by_user_id: UUID | None
    approved_at: datetime | None
    approved_by_user_id: UUID | None
    rejected_at: datetime | None
    rejected_by_user_id: UUID | None
    lines: list[BudgetRevisionLineResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BudgetRevisionListResponse(BaseModel):
    items: list[BudgetRevisionResponse]
    total: int


class CategoryTotal(BaseModel):
    category_id: UUID
    category_code: str
    category_name: str
    category_type: str
    original_budget: Decimal
    approved_revisions: Decimal
    current_budget: Decimal
    line_count: int


class BudgetSummaryResponse(BaseModel):
    budget_version: BudgetVersionResponse | None
    totals: dict[str, MetricValue]
    categories: list[CategoryTotal]
    data_completeness: dict[str, str]
    permissions: BudgetPermissions
    warnings: list[str] = Field(default_factory=list)
    legacy_budgets: list[dict[str, Any]] = Field(default_factory=list)


class BudgetImportPreviewRow(BaseModel):
    row_number: int
    valid: bool
    errors: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class BudgetImportPreviewResponse(BaseModel):
    valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[BudgetImportPreviewRow]


class BudgetImportConfirmRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=2000)


class BudgetImportResultResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
