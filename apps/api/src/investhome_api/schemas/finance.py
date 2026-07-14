from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    BudgetCategory,
    CommitmentStatus,
    CommitmentType,
    ObligationPriority,
    ObligationStatus,
    ObligationType,
    PaymentMethod,
    TransactionStatus,
    TransactionType,
)


class CurrencyTotals(BaseModel):
    """Amounts grouped by currency code."""

    totals: dict[str, Decimal] = Field(default_factory=dict)


class FinanceStatsResponse(BaseModel):
    total_cash: dict[str, Decimal]
    available_cash: dict[str, Decimal]
    pending_receivables: dict[str, Decimal]
    upcoming_payments: dict[str, Decimal]
    overdue_payments: dict[str, Decimal]
    total_project_budget: dict[str, Decimal]
    total_paid: dict[str, Decimal]
    remaining_funding_need: dict[str, Decimal]


class FinanceSummaryResponse(FinanceStatsResponse):
    project_count: int
    active_investors: int
    equity_committed: dict[str, Decimal]
    equity_funded: dict[str, Decimal]
    project_budget_variance: dict[str, Decimal]


# --- Financial Account ---


class FinancialAccountBase(BaseModel):
    account_name: str = Field(min_length=1, max_length=255)
    account_type: AccountType = AccountType.OPERATING
    institution_name: str | None = Field(default=None, max_length=255)
    ownership_entity: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    current_balance: Decimal | None = Field(default=None)
    available_balance: Decimal | None = Field(default=None)
    account_reference: str | None = Field(default=None, max_length=100)
    status: AccountStatus = AccountStatus.ACTIVE
    notes: str | None = None


class FinancialAccountCreate(FinancialAccountBase):
    pass


class FinancialAccountUpdate(BaseModel):
    account_name: str | None = Field(default=None, min_length=1, max_length=255)
    account_type: AccountType | None = None
    institution_name: str | None = Field(default=None, max_length=255)
    ownership_entity: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    current_balance: Decimal | None = None
    available_balance: Decimal | None = None
    account_reference: str | None = Field(default=None, max_length=100)
    status: AccountStatus | None = None
    notes: str | None = None


class FinancialAccountResponse(FinancialAccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FinancialAccountListResponse(BaseModel):
    items: list[FinancialAccountResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Transaction ---


class FinanceTransactionBase(BaseModel):
    transaction_date: date
    transaction_type: TransactionType
    category: str | None = Field(default=None, max_length=100)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=500)
    account_id: UUID
    project_id: UUID | None = None
    investor_id: UUID | None = None
    counterparty: str | None = Field(default=None, max_length=255)
    reference_number: str | None = Field(default=None, max_length=100)
    payment_method: PaymentMethod | None = None
    status: TransactionStatus = TransactionStatus.PENDING
    due_date: date | None = None
    paid_date: date | None = None
    notes: str | None = None


class FinanceTransactionCreate(FinanceTransactionBase):
    pass


class FinanceTransactionUpdate(BaseModel):
    transaction_date: date | None = None
    transaction_type: TransactionType | None = None
    category: str | None = Field(default=None, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=500)
    account_id: UUID | None = None
    project_id: UUID | None = None
    investor_id: UUID | None = None
    counterparty: str | None = Field(default=None, max_length=255)
    reference_number: str | None = Field(default=None, max_length=100)
    payment_method: PaymentMethod | None = None
    status: TransactionStatus | None = None
    due_date: date | None = None
    paid_date: date | None = None
    notes: str | None = None


class FinanceTransactionResponse(FinanceTransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    investor_name: str | None = None
    account_name: str | None = None


class FinanceTransactionListResponse(BaseModel):
    items: list[FinanceTransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Project Budget ---


class ProjectBudgetBase(BaseModel):
    project_id: UUID
    budget_name: str = Field(min_length=1, max_length=255)
    category: BudgetCategory
    original_budget: Decimal | None = Field(default=None, ge=0)
    revised_budget: Decimal | None = Field(default=None, ge=0)
    committed_amount: Decimal | None = Field(default=None, ge=0)
    paid_amount: Decimal | None = Field(default=None, ge=0)
    forecast_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    notes: str | None = None


class ProjectBudgetCreate(ProjectBudgetBase):
    pass


class ProjectBudgetUpdate(BaseModel):
    project_id: UUID | None = None
    budget_name: str | None = Field(default=None, min_length=1, max_length=255)
    category: BudgetCategory | None = None
    original_budget: Decimal | None = Field(default=None, ge=0)
    revised_budget: Decimal | None = Field(default=None, ge=0)
    committed_amount: Decimal | None = Field(default=None, ge=0)
    paid_amount: Decimal | None = Field(default=None, ge=0)
    forecast_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    notes: str | None = None


class ProjectBudgetResponse(ProjectBudgetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    remaining: Decimal | None = None
    variance: Decimal | None = None


class ProjectBudgetListResponse(BaseModel):
    items: list[ProjectBudgetResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Funding Commitment ---


class FundingCommitmentBase(BaseModel):
    project_id: UUID
    investor_id: UUID
    commitment_type: CommitmentType
    committed_amount: Decimal = Field(gt=0)
    funded_amount: Decimal | None = Field(default=None, ge=0)
    remaining_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    commitment_date: date | None = None
    target_funding_date: date | None = None
    actual_funding_date: date | None = None
    status: CommitmentStatus = CommitmentStatus.PROPOSED
    notes: str | None = None

    @model_validator(mode="after")
    def sync_remaining(self) -> "FundingCommitmentBase":
        if self.remaining_amount is None and self.committed_amount is not None:
            funded = self.funded_amount or Decimal("0")
            self.remaining_amount = self.committed_amount - funded
        return self


class FundingCommitmentCreate(FundingCommitmentBase):
    pass


class FundingCommitmentUpdate(BaseModel):
    project_id: UUID | None = None
    investor_id: UUID | None = None
    commitment_type: CommitmentType | None = None
    committed_amount: Decimal | None = Field(default=None, gt=0)
    funded_amount: Decimal | None = Field(default=None, ge=0)
    remaining_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    commitment_date: date | None = None
    target_funding_date: date | None = None
    actual_funding_date: date | None = None
    status: CommitmentStatus | None = None
    notes: str | None = None


class FundingCommitmentResponse(FundingCommitmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    investor_name: str | None = None


class FundingCommitmentListResponse(BaseModel):
    items: list[FundingCommitmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Payment Obligation ---


class PaymentObligationBase(BaseModel):
    project_id: UUID | None = None
    investor_id: UUID | None = None
    obligation_type: ObligationType
    payee: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    due_date: date | None = None
    paid_date: date | None = None
    status: ObligationStatus = ObligationStatus.UPCOMING
    priority: ObligationPriority = ObligationPriority.NORMAL
    notes: str | None = None


class PaymentObligationCreate(PaymentObligationBase):
    pass


class PaymentObligationUpdate(BaseModel):
    project_id: UUID | None = None
    investor_id: UUID | None = None
    obligation_type: ObligationType | None = None
    payee: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    due_date: date | None = None
    paid_date: date | None = None
    status: ObligationStatus | None = None
    priority: ObligationPriority | None = None
    notes: str | None = None


class PaymentObligationResponse(PaymentObligationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    investor_name: str | None = None


class PaymentObligationListResponse(BaseModel):
    items: list[PaymentObligationResponse]
    total: int
    page: int
    page_size: int
    pages: int
