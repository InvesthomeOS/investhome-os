"""Pydantic schemas for project cost tracking (Sprint 10A4B)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.project_cost import (
    ChangeOrderStatus,
    ProjectCommitmentStatus,
    ProjectCommitmentType,
    ProjectPaymentMethod,
    ProjectPaymentStatus,
    ProjectVendorStatus,
    RetainageReleaseStatus,
    VendorBillStatus,
    VendorStatus,
    VendorType,
)
from investhome_api.schemas.project_dashboard import MetricValue


class CostPermissions(BaseModel):
    can_view: bool = False
    can_manage_vendors: bool = False
    can_manage_commitments: bool = False
    can_approve_commitments: bool = False
    can_manage_bills: bool = False
    can_approve_bills: bool = False
    can_post_bills: bool = False
    can_manage_payments: bool = False
    can_post_payments: bool = False
    can_manage_retainage: bool = False
    can_approve_retainage: bool = False
    can_override_budget_control: bool = False
    can_export: bool = False


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------


class VendorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    vendor_code: str | None = Field(default=None, max_length=50)
    tax_id_last4: str | None = Field(default=None, max_length=4)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    website: str | None = Field(default=None, max_length=255)
    vendor_type: VendorType = VendorType.OTHER
    status: VendorStatus = VendorStatus.ACTIVE
    payment_terms: str | None = Field(default=None, max_length=100)
    default_currency: str = Field(default="USD", min_length=3, max_length=3)
    insurance_expiration_date: date | None = None
    license_number: str | None = Field(default=None, max_length=100)
    license_expiration_date: date | None = None
    notes: str | None = None
    company_id: UUID | None = None


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = None
    tax_id_last4: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    vendor_type: VendorType | None = None
    status: VendorStatus | None = None
    payment_terms: str | None = None
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    insurance_expiration_date: date | None = None
    license_number: str | None = None
    license_expiration_date: date | None = None
    notes: str | None = None


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    name: str
    legal_name: str | None
    vendor_code: str
    tax_id_last4: str | None
    email: str | None
    phone: str | None
    address: str | None
    website: str | None
    vendor_type: VendorType
    status: VendorStatus
    payment_terms: str | None
    default_currency: str
    insurance_expiration_date: date | None
    license_number: str | None
    license_expiration_date: date | None
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectVendorCreate(BaseModel):
    vendor_id: UUID
    role: str = Field(default="vendor", min_length=1, max_length=100)
    status: ProjectVendorStatus = ProjectVendorStatus.ACTIVE
    primary_contact_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class ProjectVendorUpdate(BaseModel):
    role: str | None = Field(default=None, min_length=1, max_length=100)
    status: ProjectVendorStatus | None = None
    primary_contact_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class ProjectVendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    project_id: UUID
    vendor_id: UUID
    role: str
    status: ProjectVendorStatus
    primary_contact_id: UUID | None
    start_date: date | None
    end_date: date | None
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    vendor_name: str | None = None
    vendor_code: str | None = None
    vendor_status: VendorStatus | None = None


# ---------------------------------------------------------------------------
# Commitments
# ---------------------------------------------------------------------------


class CommitmentLineCreate(BaseModel):
    budget_line_id: UUID
    category_id: UUID | None = None
    cost_code_id: UUID | None = None
    line_number: str | None = Field(default=None, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal | None = None
    unit: str | None = Field(default=None, max_length=50)
    unit_price: Decimal | None = None
    original_amount: Decimal = Field(default=Decimal("0"))
    tax_amount: Decimal | None = None
    notes: str | None = None
    sort_order: int = 0


class CommitmentLineUpdate(BaseModel):
    budget_line_id: UUID | None = None
    category_id: UUID | None = None
    cost_code_id: UUID | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    original_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    notes: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CommitmentLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    commitment_id: UUID
    budget_line_id: UUID
    category_id: UUID
    cost_code_id: UUID | None
    line_number: str
    description: str
    quantity: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    original_amount: Decimal
    approved_change_orders: Decimal
    current_amount: Decimal
    invoiced_amount: Decimal
    paid_amount: Decimal
    retained_amount: Decimal
    remaining_amount: Decimal
    tax_amount: Decimal | None
    notes: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CommitmentLineBulkCreateRequest(BaseModel):
    lines: list[CommitmentLineCreate] = Field(min_length=1, max_length=500)


class CommitmentCreate(BaseModel):
    vendor_id: UUID
    budget_version_id: UUID | None = None
    commitment_type: ProjectCommitmentType
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    executed_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    payment_terms: str | None = Field(default=None, max_length=100)
    retainage_percentage: Decimal | None = None
    document_id: UUID | None = None
    lines: list[CommitmentLineCreate] = Field(default_factory=list)


class CommitmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    budget_version_id: UUID | None = None
    executed_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    payment_terms: str | None = None
    retainage_percentage: Decimal | None = None
    document_id: UUID | None = None


class CommitmentApproveRequest(BaseModel):
    override_reason: str | None = None


class CommitmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    project_id: UUID
    vendor_id: UUID
    budget_version_id: UUID | None
    commitment_number: str
    commitment_type: ProjectCommitmentType
    title: str
    description: str | None
    status: ProjectCommitmentStatus
    currency: str
    original_amount: Decimal
    approved_change_orders: Decimal
    current_committed_amount: Decimal
    invoiced_amount: Decimal
    paid_amount: Decimal
    retained_amount: Decimal
    remaining_commitment: Decimal
    executed_date: date | None
    start_date: date | None
    end_date: date | None
    payment_terms: str | None
    retainage_percentage: Decimal | None
    document_id: UUID | None
    budget_override_reason: str | None
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    closed_at: datetime | None
    cancelled_at: datetime | None
    version_number: int
    created_at: datetime
    updated_at: datetime
    vendor_name: str | None = None
    budget_warnings: list[str] = Field(default_factory=list)
    lines: list[CommitmentLineResponse] = Field(default_factory=list)


class CommitmentListResponse(BaseModel):
    items: list[CommitmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Change orders
# ---------------------------------------------------------------------------


class ChangeOrderLineInput(BaseModel):
    commitment_line_id: UUID
    budget_line_id: UUID | None = None
    description: str | None = None
    amount: Decimal
    notes: str | None = None


class ChangeOrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    reason: str | None = None
    effective_date: date | None = None
    lines: list[ChangeOrderLineInput] = Field(min_length=1)


class ChangeOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    reason: str | None = None
    effective_date: date | None = None
    lines: list[ChangeOrderLineInput] | None = None


class ChangeOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    change_order_id: UUID
    commitment_line_id: UUID
    budget_line_id: UUID
    description: str | None
    amount: Decimal
    notes: str | None


class ChangeOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    commitment_id: UUID
    change_order_number: str
    title: str
    description: str | None
    status: ChangeOrderStatus
    reason: str | None
    requested_amount: Decimal
    approved_amount: Decimal | None
    effective_date: date | None
    applied_at: datetime | None
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[ChangeOrderLineResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Vendor bills
# ---------------------------------------------------------------------------


class VendorBillLineCreate(BaseModel):
    budget_line_id: UUID
    category_id: UUID | None = None
    cost_code_id: UUID | None = None
    commitment_id: UUID | None = None
    commitment_line_id: UUID | None = None
    line_number: str | None = Field(default=None, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal = Field(default=Decimal("0"))
    retainage_amount: Decimal = Field(default=Decimal("0"))
    tax_amount: Decimal | None = None
    previously_billed_amount: Decimal = Field(default=Decimal("0"))
    stored_materials_amount: Decimal | None = None
    notes: str | None = None
    sort_order: int = 0


class VendorBillLineUpdate(BaseModel):
    budget_line_id: UUID | None = None
    category_id: UUID | None = None
    cost_code_id: UUID | None = None
    commitment_line_id: UUID | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal | None = None
    retainage_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    previously_billed_amount: Decimal | None = None
    stored_materials_amount: Decimal | None = None
    notes: str | None = None
    sort_order: int | None = None


class VendorBillLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    vendor_bill_id: UUID
    commitment_id: UUID | None
    commitment_line_id: UUID | None
    budget_line_id: UUID
    category_id: UUID
    cost_code_id: UUID | None
    line_number: str
    description: str
    quantity: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    gross_amount: Decimal
    retainage_amount: Decimal
    net_amount: Decimal
    tax_amount: Decimal | None
    previously_billed_amount: Decimal
    current_billed_amount: Decimal
    stored_materials_amount: Decimal | None
    notes: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class VendorBillLineBulkCreateRequest(BaseModel):
    lines: list[VendorBillLineCreate] = Field(min_length=1, max_length=500)


class VendorBillCreate(BaseModel):
    vendor_id: UUID
    commitment_id: UUID | None = None
    vendor_invoice_number: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    invoice_date: date
    received_date: date | None = None
    due_date: date | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    payment_terms: str | None = None
    description: str | None = None
    document_id: UUID | None = None
    lines: list[VendorBillLineCreate] = Field(default_factory=list)


class VendorBillUpdate(BaseModel):
    vendor_invoice_number: str | None = Field(default=None, min_length=1, max_length=100)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    invoice_date: date | None = None
    received_date: date | None = None
    due_date: date | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    payment_terms: str | None = None
    description: str | None = None
    document_id: UUID | None = None
    commitment_id: UUID | None = None


class VendorBillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    project_id: UUID
    vendor_id: UUID
    commitment_id: UUID | None
    bill_number: str
    vendor_invoice_number: str
    status: VendorBillStatus
    currency: str
    invoice_date: date
    received_date: date | None
    due_date: date | None
    billing_period_start: date | None
    billing_period_end: date | None
    subtotal: Decimal
    tax_amount: Decimal
    retainage_amount: Decimal
    total_amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    payment_terms: str | None
    description: str | None
    document_id: UUID | None
    is_overdue: bool = False
    submitted_at: datetime | None
    approved_at: datetime | None
    posted_at: datetime | None
    voided_at: datetime | None
    version_number: int
    created_at: datetime
    updated_at: datetime
    vendor_name: str | None = None
    lines: list[VendorBillLineResponse] = Field(default_factory=list)


class VendorBillListResponse(BaseModel):
    items: list[VendorBillResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class PaymentAllocationCreate(BaseModel):
    vendor_bill_id: UUID
    allocated_amount: Decimal
    retainage_release_amount: Decimal = Field(default=Decimal("0"))
    discount_amount: Decimal | None = None


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    vendor_bill_id: UUID
    project_id: UUID
    allocated_amount: Decimal
    retainage_release_amount: Decimal
    discount_amount: Decimal | None
    created_at: datetime


class PaymentCreate(BaseModel):
    vendor_id: UUID
    payment_date: date
    payment_method: ProjectPaymentMethod = ProjectPaymentMethod.OTHER
    currency: str = Field(default="USD", min_length=3, max_length=3)
    gross_amount: Decimal
    reference_number: str | None = None
    memo: str | None = None
    document_id: UUID | None = None
    allocations: list[PaymentAllocationCreate] = Field(default_factory=list)


class PaymentUpdate(BaseModel):
    payment_date: date | None = None
    payment_method: ProjectPaymentMethod | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    gross_amount: Decimal | None = None
    reference_number: str | None = None
    memo: str | None = None
    document_id: UUID | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    project_id: UUID
    vendor_id: UUID
    payment_number: str
    payment_date: date
    status: ProjectPaymentStatus
    payment_method: ProjectPaymentMethod
    currency: str
    gross_amount: Decimal
    reference_number: str | None
    memo: str | None
    document_id: UUID | None
    posted_at: datetime | None
    voided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    vendor_name: str | None = None
    allocated_amount: Decimal = Decimal("0")
    unallocated_amount: Decimal = Decimal("0")
    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Retainage
# ---------------------------------------------------------------------------


class RetainageReleaseCreate(BaseModel):
    vendor_id: UUID
    commitment_id: UUID
    vendor_bill_id: UUID | None = None
    release_date: date
    amount: Decimal
    description: str | None = None
    document_id: UUID | None = None


class RetainageReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    vendor_id: UUID
    commitment_id: UUID
    vendor_bill_id: UUID | None
    release_number: str
    status: RetainageReleaseStatus
    release_date: date
    amount: Decimal
    description: str | None
    document_id: UUID | None
    submitted_at: datetime | None
    approved_at: datetime | None
    posted_at: datetime | None
    voided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RetainageSummaryResponse(BaseModel):
    total_retained: MetricValue
    total_released: MetricValue
    outstanding_retainage: MetricValue
    by_vendor: list[dict[str, Any]] = Field(default_factory=list)
    by_commitment: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Cost summaries / rollups
# ---------------------------------------------------------------------------


class CostByBudgetLineRow(BaseModel):
    budget_line_id: UUID
    line_number: str
    name: str
    category_id: UUID
    current_budget: Decimal
    committed_cost: Decimal
    pending_commitments: Decimal
    actual_cost: Decimal
    paid_cost: Decimal
    retained_cost: Decimal
    remaining_budget: Decimal
    available_to_commit: Decimal
    basic_forecast_at_completion: Decimal
    projected_variance: Decimal


class CostByCategoryRow(BaseModel):
    category_id: UUID
    category_code: str
    category_name: str
    current_budget: Decimal
    committed_cost: Decimal
    actual_cost: Decimal
    paid_cost: Decimal
    retained_cost: Decimal
    remaining_budget: Decimal
    available_to_commit: Decimal


class CostByVendorRow(BaseModel):
    vendor_id: UUID
    vendor_name: str
    committed_cost: Decimal
    actual_cost: Decimal
    paid_cost: Decimal
    retained_cost: Decimal
    open_bills_balance: Decimal


class CostSummaryResponse(BaseModel):
    source: str
    totals: dict[str, MetricValue]
    permissions: CostPermissions
    warnings: list[str] = Field(default_factory=list)
    data_completeness: dict[str, str] = Field(default_factory=dict)
