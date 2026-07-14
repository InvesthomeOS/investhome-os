"""Finance summary and stats calculations."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.finance import (
    AccountStatus,
    CommitmentStatus,
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    INCOME_TRANSACTION_TYPES,
    ObligationStatus,
    PaymentObligation,
    ProjectBudget,
    TransactionStatus,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project


def _sum_by_currency(rows: list[tuple[str, Decimal | None]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for currency, amount in rows:
        if amount is None:
            continue
        key = currency or "USD"
        totals[key] = totals.get(key, Decimal("0")) + amount
    return totals


def compute_finance_stats(db: Session) -> dict[str, object]:
    today = date.today()

    accounts = db.scalars(
        select(FinancialAccount).where(
            FinancialAccount.archived_at.is_(None),
            FinancialAccount.status == AccountStatus.ACTIVE,
        )
    ).all()

    total_cash = _sum_by_currency(
        [(a.currency, a.current_balance or Decimal("0")) for a in accounts]
    )
    available_cash = _sum_by_currency(
        [(a.currency, a.available_balance or Decimal("0")) for a in accounts]
    )

    receivable_txns = db.scalars(
        select(FinanceTransaction).where(
            FinanceTransaction.archived_at.is_(None),
            FinanceTransaction.transaction_type.in_(INCOME_TRANSACTION_TYPES),
            FinanceTransaction.status.in_(
                [TransactionStatus.PENDING, TransactionStatus.SCHEDULED]
            ),
        )
    ).all()
    pending_receivables = _sum_by_currency(
        [(t.currency, t.amount) for t in receivable_txns]
    )

    upcoming_obligations = db.scalars(
        select(PaymentObligation).where(
            PaymentObligation.archived_at.is_(None),
            PaymentObligation.status.in_(
                [ObligationStatus.UPCOMING, ObligationStatus.DUE]
            ),
        )
    ).all()
    upcoming_payments = _sum_by_currency(
        [(o.currency, o.amount) for o in upcoming_obligations]
    )

    overdue_obligations = db.scalars(
        select(PaymentObligation).where(
            PaymentObligation.archived_at.is_(None),
            PaymentObligation.status == ObligationStatus.OVERDUE,
        )
    ).all()
    overdue_payments = _sum_by_currency(
        [(o.currency, o.amount) for o in overdue_obligations]
    )

    budgets = db.scalars(select(ProjectBudget)).all()
    total_project_budget = _sum_by_currency(
        [
            (
                b.currency,
                b.revised_budget if b.revised_budget is not None else b.original_budget,
            )
            for b in budgets
        ]
    )
    total_paid = _sum_by_currency([(b.currency, b.paid_amount) for b in budgets])

    commitments = db.scalars(
        select(FundingCommitment).where(
            FundingCommitment.status.not_in(
                [CommitmentStatus.CANCELLED, CommitmentStatus.FULLY_FUNDED]
            )
        )
    ).all()
    remaining_funding_need = _sum_by_currency(
        [
            (
                c.currency,
                (c.remaining_amount or Decimal("0"))
                if c.remaining_amount is not None
                else (c.committed_amount - (c.funded_amount or Decimal("0"))),
            )
            for c in commitments
        ]
    )

    return {
        "total_cash": total_cash,
        "available_cash": available_cash,
        "pending_receivables": pending_receivables,
        "upcoming_payments": upcoming_payments,
        "overdue_payments": overdue_payments,
        "total_project_budget": total_project_budget,
        "total_paid": total_paid,
        "remaining_funding_need": remaining_funding_need,
    }


def compute_executive_summary(db: Session) -> dict[str, object]:
    stats = compute_finance_stats(db)
    project_count = db.scalar(
        select(func.count()).select_from(Project).where(Project.archived_at.is_(None))
    ) or 0
    active_investors = db.scalar(
        select(func.count())
        .select_from(Investor)
        .where(Investor.archived_at.is_(None))
    ) or 0

    commitments = db.scalars(select(FundingCommitment)).all()
    equity_committed = _sum_by_currency(
        [(c.currency, c.committed_amount) for c in commitments]
    )
    equity_funded = _sum_by_currency(
        [(c.currency, c.funded_amount) for c in commitments]
    )

    budgets = db.scalars(select(ProjectBudget)).all()
    budget_variance: dict[str, Decimal] = {}
    for budget in budgets:
        revised = budget.revised_budget or budget.original_budget or Decimal("0")
        paid = budget.paid_amount or Decimal("0")
        forecast = budget.forecast_amount or revised
        variance = forecast - revised
        key = budget.currency or "USD"
        budget_variance[key] = budget_variance.get(key, Decimal("0")) + variance

    return {
        **stats,
        "project_count": project_count,
        "active_investors": active_investors,
        "equity_committed": equity_committed,
        "equity_funded": equity_funded,
        "project_budget_variance": budget_variance,
    }
