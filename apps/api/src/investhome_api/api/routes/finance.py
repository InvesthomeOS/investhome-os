from datetime import UTC, date, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    BudgetCategory,
    CommitmentStatus,
    CommitmentType,
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    ObligationPriority,
    ObligationStatus,
    ObligationType,
    PaymentMethod,
    PaymentObligation,
    ProjectBudget,
    TransactionStatus,
    TransactionType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.user_auth import User
from investhome_api.models.project import Project
from investhome_api.schemas.finance import (
    FinanceStatsResponse,
    FinanceSummaryResponse,
    FinanceTransactionCreate,
    FinanceTransactionListResponse,
    FinanceTransactionResponse,
    FinanceTransactionUpdate,
    FinancialAccountCreate,
    FinancialAccountListResponse,
    FinancialAccountResponse,
    FinancialAccountUpdate,
    FundingCommitmentCreate,
    FundingCommitmentListResponse,
    FundingCommitmentResponse,
    FundingCommitmentUpdate,
    PaymentObligationCreate,
    PaymentObligationListResponse,
    PaymentObligationResponse,
    PaymentObligationUpdate,
    ProjectBudgetCreate,
    ProjectBudgetListResponse,
    ProjectBudgetResponse,
    ProjectBudgetUpdate,
)
from investhome_api.services.finance_service import (
    compute_executive_summary,
    compute_finance_stats,
)

router = APIRouter(prefix="/finance", tags=["finance"])

_finance_view = Depends(require_permission("finance", "view"))
_finance_create = Depends(require_permission("finance", "create"))
_finance_update = Depends(require_permission("finance", "update"))
_finance_archive = Depends(require_permission("finance", "archive"))
_finance_delete = Depends(require_permission("finance", "delete"))

accounts_router = APIRouter(prefix="/accounts", tags=["finance"])
transactions_router = APIRouter(prefix="/transactions", tags=["finance"])
budgets_router = APIRouter(prefix="/project-budgets", tags=["finance"])
commitments_router = APIRouter(prefix="/funding-commitments", tags=["finance"])
obligations_router = APIRouter(prefix="/payment-obligations", tags=["finance"])

ACCOUNT_SORTABLE_FIELDS = {
    "account_name": FinancialAccount.account_name,
    "account_type": FinancialAccount.account_type,
    "status": FinancialAccount.status,
    "currency": FinancialAccount.currency,
    "current_balance": FinancialAccount.current_balance,
    "updated_at": FinancialAccount.updated_at,
    "created_at": FinancialAccount.created_at,
}

TRANSACTION_SORTABLE_FIELDS = {
    "transaction_date": FinanceTransaction.transaction_date,
    "transaction_type": FinanceTransaction.transaction_type,
    "amount": FinanceTransaction.amount,
    "status": FinanceTransaction.status,
    "currency": FinanceTransaction.currency,
    "updated_at": FinanceTransaction.updated_at,
    "created_at": FinanceTransaction.created_at,
}

BUDGET_SORTABLE_FIELDS = {
    "budget_name": ProjectBudget.budget_name,
    "category": ProjectBudget.category,
    "original_budget": ProjectBudget.original_budget,
    "revised_budget": ProjectBudget.revised_budget,
    "paid_amount": ProjectBudget.paid_amount,
    "updated_at": ProjectBudget.updated_at,
    "created_at": ProjectBudget.created_at,
}

COMMITMENT_SORTABLE_FIELDS = {
    "committed_amount": FundingCommitment.committed_amount,
    "funded_amount": FundingCommitment.funded_amount,
    "status": FundingCommitment.status,
    "commitment_date": FundingCommitment.commitment_date,
    "updated_at": FundingCommitment.updated_at,
    "created_at": FundingCommitment.created_at,
}

OBLIGATION_SORTABLE_FIELDS = {
    "due_date": PaymentObligation.due_date,
    "amount": PaymentObligation.amount,
    "status": PaymentObligation.status,
    "priority": PaymentObligation.priority,
    "updated_at": PaymentObligation.updated_at,
    "created_at": PaymentObligation.created_at,
}


def _ensure_project_exists(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _ensure_investor_exists(investor_id: UUID, db: Session) -> Investor:
    investor = db.get(Investor, investor_id)
    if investor is None or investor.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investor not found")
    return investor


def _ensure_account_exists(account_id: UUID, db: Session) -> FinancialAccount:
    account = db.get(FinancialAccount, account_id)
    if account is None or account.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _get_account_or_404(
    account_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> FinancialAccount:
    account = db.get(FinancialAccount, account_id)
    if account is None or (account.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _get_transaction_or_404(
    transaction_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> FinanceTransaction:
    transaction = db.get(FinanceTransaction, transaction_id)
    if transaction is None or (transaction.archived_at is not None and not include_archived):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


def _get_budget_or_404(budget_id: UUID, db: Session) -> ProjectBudget:
    budget = db.get(ProjectBudget, budget_id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


def _get_commitment_or_404(commitment_id: UUID, db: Session) -> FundingCommitment:
    commitment = db.get(FundingCommitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funding commitment not found",
        )
    return commitment


def _get_obligation_or_404(
    obligation_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> PaymentObligation:
    obligation = db.get(PaymentObligation, obligation_id)
    if obligation is None or (obligation.archived_at is not None and not include_archived):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment obligation not found",
        )
    return obligation


def _budget_remaining(budget: ProjectBudget) -> Decimal | None:
    revised = budget.revised_budget or budget.original_budget
    if revised is None:
        return None
    paid = budget.paid_amount or Decimal("0")
    return revised - paid


def _budget_variance(budget: ProjectBudget) -> Decimal | None:
    revised = budget.revised_budget or budget.original_budget
    if revised is None:
        return None
    forecast = budget.forecast_amount or revised
    return forecast - revised


def _enrich_transaction(
    transaction: FinanceTransaction,
    db: Session,
) -> FinanceTransactionResponse:
    data = FinanceTransactionResponse.model_validate(transaction)
    if transaction.project_id:
        project = db.get(Project, transaction.project_id)
        if project:
            data.project_name = project.project_name
    if transaction.investor_id:
        investor = db.get(Investor, transaction.investor_id)
        if investor:
            data.investor_name = investor.full_name
    account = db.get(FinancialAccount, transaction.account_id)
    if account:
        data.account_name = account.account_name
    return data


def _enrich_budget(budget: ProjectBudget, db: Session) -> ProjectBudgetResponse:
    data = ProjectBudgetResponse.model_validate(budget)
    project = db.get(Project, budget.project_id)
    if project:
        data.project_name = project.project_name
    data.remaining = _budget_remaining(budget)
    data.variance = _budget_variance(budget)
    return data


def _enrich_commitment(commitment: FundingCommitment, db: Session) -> FundingCommitmentResponse:
    data = FundingCommitmentResponse.model_validate(commitment)
    project = db.get(Project, commitment.project_id)
    if project:
        data.project_name = project.project_name
    investor = db.get(Investor, commitment.investor_id)
    if investor:
        data.investor_name = investor.full_name
    return data


def _enrich_obligation(obligation: PaymentObligation, db: Session) -> PaymentObligationResponse:
    data = PaymentObligationResponse.model_validate(obligation)
    if obligation.project_id:
        project = db.get(Project, obligation.project_id)
        if project:
            data.project_name = project.project_name
    if obligation.investor_id:
        investor = db.get(Investor, obligation.investor_id)
        if investor:
            data.investor_name = investor.full_name
    return data


def _validate_transaction_fks(
    db: Session,
    *,
    account_id: UUID | None = None,
    project_id: UUID | None = None,
    investor_id: UUID | None = None,
) -> None:
    if account_id is not None:
        _ensure_account_exists(account_id, db)
    if project_id is not None:
        _ensure_project_exists(project_id, db)
    if investor_id is not None:
        _ensure_investor_exists(investor_id, db)


@router.get("/stats", response_model=FinanceStatsResponse)
def get_finance_stats(
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FinanceStatsResponse:
    return FinanceStatsResponse(**compute_finance_stats(db))


@router.get("/summary", response_model=FinanceSummaryResponse)
def get_finance_summary(
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FinanceSummaryResponse:
    return FinanceSummaryResponse(**compute_executive_summary(db))


# --- Financial Accounts ---


@accounts_router.get("", response_model=FinancialAccountListResponse)
def list_accounts(
    search: str | None = Query(default=None, max_length=255),
    status_filter: AccountStatus | None = Query(default=None, alias="status"),
    account_type: AccountType | None = None,
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FinancialAccountListResponse:
    sort_column = ACCOUNT_SORTABLE_FIELDS.get(sort_by, FinancialAccount.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(FinancialAccount)
    if not include_archived:
        query = query.where(FinancialAccount.archived_at.is_(None))
    if status_filter is not None:
        query = query.where(FinancialAccount.status == status_filter)
    if account_type is not None:
        query = query.where(FinancialAccount.account_type == account_type)
    if currency:
        query = query.where(FinancialAccount.currency == currency.upper())
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                FinancialAccount.account_name.ilike(pattern),
                FinancialAccount.institution_name.ilike(pattern),
                FinancialAccount.ownership_entity.ilike(pattern),
                FinancialAccount.account_reference.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    accounts = db.scalars(
        query.order_by(order_fn(sort_column)).offset(offset).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0

    return FinancialAccountListResponse(
        items=[FinancialAccountResponse.model_validate(a) for a in accounts],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@accounts_router.get("/{account_id}", response_model=FinancialAccountResponse)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FinancialAccountResponse:
    account = _get_account_or_404(account_id, db)
    return FinancialAccountResponse.model_validate(account)


@accounts_router.post("", response_model=FinancialAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: FinancialAccountCreate,
    db: Session = Depends(get_db),
    _user: User = _finance_create,
) -> FinancialAccountResponse:
    account = FinancialAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return FinancialAccountResponse.model_validate(account)


@accounts_router.patch("/{account_id}", response_model=FinancialAccountResponse)
def update_account(
    account_id: UUID,
    payload: FinancialAccountUpdate,
    db: Session = Depends(get_db),
    _user: User = _finance_update,
) -> FinancialAccountResponse:
    account = _get_account_or_404(account_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    for field, value in updates.items():
        setattr(account, field, value)
    account.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(account)
    return FinancialAccountResponse.model_validate(account)


@accounts_router.delete("/{account_id}", response_model=FinancialAccountResponse)
def archive_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_archive,
) -> FinancialAccountResponse:
    account = _get_account_or_404(account_id, db)
    if account.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already archived",
        )
    account.archived_at = datetime.now(UTC)
    account.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(account)
    return FinancialAccountResponse.model_validate(account)


# --- Transactions ---


@transactions_router.get("", response_model=FinanceTransactionListResponse)
def list_transactions(
    search: str | None = Query(default=None, max_length=255),
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: UUID | None = None,
    investor_id: UUID | None = None,
    account_id: UUID | None = None,
    transaction_type: TransactionType | None = None,
    status_filter: TransactionStatus | None = Query(default=None, alias="status"),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="transaction_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FinanceTransactionListResponse:
    sort_column = TRANSACTION_SORTABLE_FIELDS.get(sort_by, FinanceTransaction.transaction_date)
    order_fn = asc if sort_order == "asc" else desc

    query = select(FinanceTransaction)
    if not include_archived:
        query = query.where(FinanceTransaction.archived_at.is_(None))
    if date_from is not None:
        query = query.where(FinanceTransaction.transaction_date >= date_from)
    if date_to is not None:
        query = query.where(FinanceTransaction.transaction_date <= date_to)
    if project_id is not None:
        query = query.where(FinanceTransaction.project_id == project_id)
    if investor_id is not None:
        query = query.where(FinanceTransaction.investor_id == investor_id)
    if account_id is not None:
        query = query.where(FinanceTransaction.account_id == account_id)
    if transaction_type is not None:
        query = query.where(FinanceTransaction.transaction_type == transaction_type)
    if status_filter is not None:
        query = query.where(FinanceTransaction.status == status_filter)
    if currency:
        query = query.where(FinanceTransaction.currency == currency.upper())
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                FinanceTransaction.description.ilike(pattern),
                FinanceTransaction.category.ilike(pattern),
                FinanceTransaction.counterparty.ilike(pattern),
                FinanceTransaction.reference_number.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    transactions = db.scalars(
        query.order_by(order_fn(sort_column)).offset(offset).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0

    return FinanceTransactionListResponse(
        items=[_enrich_transaction(t, db) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@transactions_router.get("/{transaction_id}", response_model=FinanceTransactionResponse)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FinanceTransactionResponse:
    transaction = _get_transaction_or_404(transaction_id, db)
    return _enrich_transaction(transaction, db)


@transactions_router.post(
    "",
    response_model=FinanceTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: FinanceTransactionCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _finance_create,
) -> FinanceTransactionResponse:
    _validate_transaction_fks(
        db,
        account_id=payload.account_id,
        project_id=payload.project_id,
        investor_id=payload.investor_id,
    )
    transaction = FinanceTransaction(**payload.model_dump())
    db.add(transaction)
    db.flush()
    from investhome_api.services.activity_recorder import log_finance_transaction_event

    log_finance_transaction_event(
        db,
        transaction=transaction,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(transaction)
    return _enrich_transaction(transaction, db)


@transactions_router.patch("/{transaction_id}", response_model=FinanceTransactionResponse)
def update_transaction(
    transaction_id: UUID,
    payload: FinanceTransactionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _finance_update,
) -> FinanceTransactionResponse:
    transaction = _get_transaction_or_404(transaction_id, db)
    previous_status = transaction.status
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    _validate_transaction_fks(
        db,
        account_id=updates.get("account_id"),
        project_id=updates.get("project_id"),
        investor_id=updates.get("investor_id"),
    )
    for field, value in updates.items():
        setattr(transaction, field, value)
    transaction.updated_at = datetime.now(UTC)
    db.flush()
    from investhome_api.services.activity_recorder import log_finance_transaction_event

    log_finance_transaction_event(
        db,
        transaction=transaction,
        actor=actor,
        request=request,
        previous_status=previous_status,
    )
    db.commit()
    db.refresh(transaction)
    return _enrich_transaction(transaction, db)


@transactions_router.delete("/{transaction_id}", response_model=FinanceTransactionResponse)
def archive_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_archive,
) -> FinanceTransactionResponse:
    transaction = _get_transaction_or_404(transaction_id, db)
    if transaction.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction is already archived",
        )
    transaction.archived_at = datetime.now(UTC)
    transaction.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(transaction)
    return _enrich_transaction(transaction, db)


# --- Project Budgets ---


@budgets_router.get("", response_model=ProjectBudgetListResponse)
def list_budgets(
    project_id: UUID | None = None,
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> ProjectBudgetListResponse:
    sort_column = BUDGET_SORTABLE_FIELDS.get(sort_by, ProjectBudget.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(ProjectBudget)
    if project_id is not None:
        query = query.where(ProjectBudget.project_id == project_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    budgets = db.scalars(
        query.order_by(order_fn(sort_column)).offset(offset).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0

    return ProjectBudgetListResponse(
        items=[_enrich_budget(b, db) for b in budgets],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@budgets_router.get("/{budget_id}", response_model=ProjectBudgetResponse)
def get_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> ProjectBudgetResponse:
    budget = _get_budget_or_404(budget_id, db)
    return _enrich_budget(budget, db)


@budgets_router.post("", response_model=ProjectBudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: ProjectBudgetCreate,
    db: Session = Depends(get_db),
    _user: User = _finance_create,
) -> ProjectBudgetResponse:
    _ensure_project_exists(payload.project_id, db)
    budget = ProjectBudget(**payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return _enrich_budget(budget, db)


@budgets_router.patch("/{budget_id}", response_model=ProjectBudgetResponse)
def update_budget(
    budget_id: UUID,
    payload: ProjectBudgetUpdate,
    db: Session = Depends(get_db),
    _user: User = _finance_update,
) -> ProjectBudgetResponse:
    budget = _get_budget_or_404(budget_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    if "project_id" in updates and updates["project_id"] is not None:
        _ensure_project_exists(updates["project_id"], db)
    for field, value in updates.items():
        setattr(budget, field, value)
    budget.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(budget)
    return _enrich_budget(budget, db)


@budgets_router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_delete,
) -> None:
    budget = _get_budget_or_404(budget_id, db)
    db.delete(budget)
    db.commit()


# --- Funding Commitments ---


@commitments_router.get("", response_model=FundingCommitmentListResponse)
def list_commitments(
    project_id: UUID | None = None,
    investor_id: UUID | None = None,
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FundingCommitmentListResponse:
    sort_column = COMMITMENT_SORTABLE_FIELDS.get(sort_by, FundingCommitment.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(FundingCommitment)
    if project_id is not None:
        query = query.where(FundingCommitment.project_id == project_id)
    if investor_id is not None:
        query = query.where(FundingCommitment.investor_id == investor_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    commitments = db.scalars(
        query.order_by(order_fn(sort_column)).offset(offset).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0

    return FundingCommitmentListResponse(
        items=[_enrich_commitment(c, db) for c in commitments],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@commitments_router.get("/{commitment_id}", response_model=FundingCommitmentResponse)
def get_commitment(
    commitment_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> FundingCommitmentResponse:
    commitment = _get_commitment_or_404(commitment_id, db)
    return _enrich_commitment(commitment, db)


@commitments_router.post(
    "",
    response_model=FundingCommitmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commitment(
    payload: FundingCommitmentCreate,
    db: Session = Depends(get_db),
    _user: User = _finance_create,
) -> FundingCommitmentResponse:
    _ensure_project_exists(payload.project_id, db)
    _ensure_investor_exists(payload.investor_id, db)
    commitment = FundingCommitment(**payload.model_dump())
    db.add(commitment)
    db.commit()
    db.refresh(commitment)
    return _enrich_commitment(commitment, db)


@commitments_router.patch("/{commitment_id}", response_model=FundingCommitmentResponse)
def update_commitment(
    commitment_id: UUID,
    payload: FundingCommitmentUpdate,
    db: Session = Depends(get_db),
    _user: User = _finance_update,
) -> FundingCommitmentResponse:
    commitment = _get_commitment_or_404(commitment_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    if "project_id" in updates and updates["project_id"] is not None:
        _ensure_project_exists(updates["project_id"], db)
    if "investor_id" in updates and updates["investor_id"] is not None:
        _ensure_investor_exists(updates["investor_id"], db)
    for field, value in updates.items():
        setattr(commitment, field, value)
    commitment.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(commitment)
    return _enrich_commitment(commitment, db)


@commitments_router.delete("/{commitment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_commitment(
    commitment_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_delete,
) -> None:
    commitment = _get_commitment_or_404(commitment_id, db)
    db.delete(commitment)
    db.commit()


# --- Payment Obligations ---


@obligations_router.get("", response_model=PaymentObligationListResponse)
def list_obligations(
    project_id: UUID | None = None,
    status_filter: ObligationStatus | None = Query(default=None, alias="status"),
    priority: ObligationPriority | None = None,
    due_date_from: date | None = None,
    due_date_to: date | None = None,
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="due_date"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> PaymentObligationListResponse:
    sort_column = OBLIGATION_SORTABLE_FIELDS.get(sort_by, PaymentObligation.due_date)
    order_fn = asc if sort_order == "asc" else desc

    query = select(PaymentObligation)
    if not include_archived:
        query = query.where(PaymentObligation.archived_at.is_(None))
    if project_id is not None:
        query = query.where(PaymentObligation.project_id == project_id)
    if status_filter is not None:
        query = query.where(PaymentObligation.status == status_filter)
    if priority is not None:
        query = query.where(PaymentObligation.priority == priority)
    if due_date_from is not None:
        query = query.where(PaymentObligation.due_date >= due_date_from)
    if due_date_to is not None:
        query = query.where(PaymentObligation.due_date <= due_date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    obligations = db.scalars(
        query.order_by(order_fn(sort_column)).offset(offset).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0

    return PaymentObligationListResponse(
        items=[_enrich_obligation(o, db) for o in obligations],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@obligations_router.get("/{obligation_id}", response_model=PaymentObligationResponse)
def get_obligation(
    obligation_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_view,
) -> PaymentObligationResponse:
    obligation = _get_obligation_or_404(obligation_id, db)
    return _enrich_obligation(obligation, db)


@obligations_router.post(
    "",
    response_model=PaymentObligationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_obligation(
    payload: PaymentObligationCreate,
    db: Session = Depends(get_db),
    _user: User = _finance_create,
) -> PaymentObligationResponse:
    if payload.project_id is not None:
        _ensure_project_exists(payload.project_id, db)
    if payload.investor_id is not None:
        _ensure_investor_exists(payload.investor_id, db)
    obligation = PaymentObligation(**payload.model_dump())
    db.add(obligation)
    db.commit()
    db.refresh(obligation)
    return _enrich_obligation(obligation, db)


@obligations_router.patch("/{obligation_id}", response_model=PaymentObligationResponse)
def update_obligation(
    obligation_id: UUID,
    payload: PaymentObligationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _finance_update,
) -> PaymentObligationResponse:
    obligation = _get_obligation_or_404(obligation_id, db)
    previous_status = obligation.status
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    if "project_id" in updates and updates["project_id"] is not None:
        _ensure_project_exists(updates["project_id"], db)
    if "investor_id" in updates and updates["investor_id"] is not None:
        _ensure_investor_exists(updates["investor_id"], db)
    for field, value in updates.items():
        setattr(obligation, field, value)
    obligation.updated_at = datetime.now(UTC)
    db.flush()
    from investhome_api.services.activity_recorder import log_payment_obligation_event

    log_payment_obligation_event(
        db,
        obligation=obligation,
        actor=actor,
        request=request,
        previous_status=previous_status,
    )
    db.commit()
    db.refresh(obligation)
    return _enrich_obligation(obligation, db)


@obligations_router.delete("/{obligation_id}", response_model=PaymentObligationResponse)
def archive_obligation(
    obligation_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _finance_archive,
) -> PaymentObligationResponse:
    obligation = _get_obligation_or_404(obligation_id, db)
    if obligation.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment obligation is already archived",
        )
    obligation.archived_at = datetime.now(UTC)
    obligation.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(obligation)
    return _enrich_obligation(obligation, db)


router.include_router(accounts_router)
router.include_router(transactions_router)
router.include_router(budgets_router)
router.include_router(commitments_router)
router.include_router(obligations_router)
