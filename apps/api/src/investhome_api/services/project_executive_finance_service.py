"""Centralized executive project finance computations (Sprint 10A4C).

Reuses project financial fields, FundingCommitment, normalized budget summary,
legacy ProjectBudget, and 10A4B cost rollups — never double-counts legacy + normalized.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.finance import (
    CommitmentStatus,
    FundingCommitment,
    ObligationStatus,
    PaymentObligation,
    ProjectBudget,
)
from investhome_api.models.project import Project
from investhome_api.models.project_budget import (
    BudgetVersionStatus,
    ProjectBudgetLine,
    ProjectBudgetVersion,
)
from investhome_api.models.project_cost import (
    ProjectVendorBill,
    VendorBillStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_dashboard import MetricValue, metric, unavailable
from investhome_api.schemas.project_executive_finance import (
    CashFlowHorizonBucket,
    CashFlowUpcomingItem,
    ExecutiveAlertSeverity,
    ExecutiveFinanceAlert,
    FinancialHealthStatus,
    PortfolioAiFinanceSummaryPayload,
    PortfolioExecutiveAttentionItem,
    PortfolioUpcomingCashItem,
    ProjectAiFinanceSummaryPayload,
    ProjectCashFlowSummaryResponse,
    ProjectExecutiveFinanceResponse,
)
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_cost_service import (
    project_cost_totals,
    project_has_normalized_cost_data,
)
from investhome_api.services import project_service as project_svc

ZERO = Decimal("0")
LARGE_CASH_THRESHOLD = Decimal("50000")
FUNDING_GAP_WATCH = Decimal("100000")
FUNDING_GAP_AT_RISK = Decimal("500000")
FUNDING_GAP_CRITICAL = Decimal("1000000")
CANCELLED_COMMITMENT = CommitmentStatus.CANCELLED
OPEN_OBLIGATION_STATUSES = {
    ObligationStatus.UPCOMING,
    ObligationStatus.DUE,
    ObligationStatus.OVERDUE,
}
OPEN_BILL_STATUSES = {
    VendorBillStatus.DRAFT,
    VendorBillStatus.IN_REVIEW,
    VendorBillStatus.APPROVED,
    VendorBillStatus.POSTED,
    VendorBillStatus.PARTIALLY_PAID,
}


def _money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value))


def _can_view_financial(user: User) -> bool:
    return user_has_permission(user, "projects", "view_financial") or user_has_permission(
        user, "projects", "edit_financial"
    )


def _require_financial_view(user: User) -> None:
    if not _can_view_financial(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view project financials",
        )


def _optional_metric(value: Decimal | None, *, reason: str) -> MetricValue:
    if value is None:
        return unavailable(reason)
    return metric(value)


def _load_project(db: Session, project_id: UUID) -> Project:
    return project_svc.get_project_or_404(db, project_id, include_archived=True)


def _funding_totals(db: Session, project_id: UUID) -> dict[str, Decimal | None]:
    rows = list(
        db.scalars(
            select(FundingCommitment).where(
                FundingCommitment.project_id == project_id,
                FundingCommitment.status != CANCELLED_COMMITMENT,
            )
        ).all()
    )
    if not rows:
        return {
            "committed": None,
            "funded": None,
            "remaining": None,
            "count": 0,
        }
    committed = sum((_money(row.committed_amount) for row in rows), ZERO)
    funded = sum((_money(row.funded_amount) for row in rows), ZERO)
    remaining = sum(
        (
            _money(row.remaining_amount)
            if row.remaining_amount is not None
            else max(_money(row.committed_amount) - _money(row.funded_amount), ZERO)
            for row in rows
        ),
        ZERO,
    )
    return {
        "committed": committed,
        "funded": funded,
        "remaining": remaining,
        "count": len(rows),
    }


def _legacy_paid(db: Session, project_id: UUID) -> Decimal | None:
    rows = list(
        db.scalars(select(ProjectBudget).where(ProjectBudget.project_id == project_id)).all()
    )
    if not rows:
        return None
    return sum((_money(row.paid_amount) for row in rows), ZERO)


def _normalized_budget_total(db: Session, project_id: UUID) -> Decimal | None:
    version = db.scalars(
        select(ProjectBudgetVersion).where(
            ProjectBudgetVersion.project_id == project_id,
            ProjectBudgetVersion.is_current.is_(True),
            ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
        )
    ).first()
    if version is None:
        return None
    total = db.scalar(
        select(func.coalesce(func.sum(ProjectBudgetLine.current_budget), 0)).where(
            ProjectBudgetLine.budget_version_id == version.id,
            ProjectBudgetLine.is_active.is_(True),
            ProjectBudgetLine.is_summary.is_(False),
        )
    )
    return _money(total)


def _resolve_cost_metrics(
    db: Session, project_id: UUID, project: Project
) -> tuple[MetricValue, MetricValue, str, dict[str, str], list[str]]:
    """Return actual_cost, forecast_cost, cost_source, completeness, warnings."""
    completeness: dict[str, str] = {}
    warnings: list[str] = []
    has_normalized = project_has_normalized_cost_data(db, project_id)
    budget_total = _normalized_budget_total(db, project_id)

    if has_normalized:
        totals = project_cost_totals(db, project_id)
        actual = totals["actual_cost"]
        committed = totals["committed_cost"]
        commitment_remaining = max(committed - actual, ZERO)
        basic_forecast = actual + commitment_remaining
        if budget_total is not None and budget_total > ZERO and basic_forecast <= ZERO:
            forecast = budget_total
        else:
            forecast = basic_forecast if basic_forecast > ZERO else budget_total
        completeness["actual_cost"] = "normalized"
        completeness["forecast_cost"] = "commitment_based"
        warnings.append(
            "Forecast cost uses commitment-based estimate; full forecasting engine is not implemented."
        )
        if forecast is None:
            forecast_metric = unavailable("No forecast baseline")
        else:
            forecast_metric = metric(forecast)
        return metric(actual), forecast_metric, "normalized", completeness, warnings

    legacy_paid = _legacy_paid(db, project_id)
    if legacy_paid is not None:
        completeness["actual_cost"] = "legacy"
        actual_metric = metric(legacy_paid)
    else:
        completeness["actual_cost"] = "missing"
        actual_metric = unavailable("No actual cost recorded")

    forecast_candidates = [
        budget_total,
        project.total_development_cost,
        project.construction_budget,
    ]
    forecast_value = next((value for value in forecast_candidates if value is not None), None)
    if forecast_value is not None:
        completeness["forecast_cost"] = "project_or_budget"
        forecast_metric = metric(_money(forecast_value))
    else:
        completeness["forecast_cost"] = "missing"
        forecast_metric = unavailable("No forecast cost baseline")
        warnings.append("Forecast cost unavailable — set development budget or approve a budget.")

    return actual_metric, forecast_metric, "legacy" if legacy_paid is not None else "none", completeness, warnings


def _cash_events(
    db: Session, project_id: UUID, *, today: date
) -> list[CashFlowUpcomingItem]:
    events: list[CashFlowUpcomingItem] = []

    obligations = db.scalars(
        select(PaymentObligation).where(
            PaymentObligation.project_id == project_id,
            PaymentObligation.archived_at.is_(None),
            PaymentObligation.status.in_(list(OPEN_OBLIGATION_STATUSES)),
        )
    ).all()
    for obligation in obligations:
        events.append(
            CashFlowUpcomingItem(
                id=str(obligation.id),
                kind="payment_obligation",
                direction="outflow",
                label=obligation.description or obligation.payee or obligation.obligation_type.value,
                amount=_money(obligation.amount),
                currency=obligation.currency or "USD",
                expected_date=obligation.due_date,
                status=obligation.status.value if obligation.status else None,
                source="payment_obligations",
            )
        )

    bills = db.scalars(
        select(ProjectVendorBill).where(
            ProjectVendorBill.project_id == project_id,
            ProjectVendorBill.status.in_(list(OPEN_BILL_STATUSES)),
        )
    ).all()
    for bill in bills:
        balance = _money(bill.balance_due)
        if balance <= ZERO:
            continue
        events.append(
            CashFlowUpcomingItem(
                id=str(bill.id),
                kind="vendor_bill",
                direction="outflow",
                label=f"Bill {bill.bill_number}",
                amount=balance,
                currency=bill.currency or "USD",
                expected_date=bill.due_date,
                status=bill.status.value if bill.status else None,
                source="project_vendor_bills",
            )
        )

    commitments = db.scalars(
        select(FundingCommitment).where(
            FundingCommitment.project_id == project_id,
            FundingCommitment.status != CANCELLED_COMMITMENT,
        )
    ).all()
    for commitment in commitments:
        remaining = (
            _money(commitment.remaining_amount)
            if commitment.remaining_amount is not None
            else max(_money(commitment.committed_amount) - _money(commitment.funded_amount), ZERO)
        )
        if remaining <= ZERO:
            continue
        events.append(
            CashFlowUpcomingItem(
                id=str(commitment.id),
                kind="funding_commitment",
                direction="inflow",
                label=(
                    commitment.commitment_type.value
                    if commitment.commitment_type
                    else "Funding commitment"
                ),
                amount=remaining,
                currency=commitment.currency or "USD",
                expected_date=commitment.target_funding_date or commitment.commitment_date,
                status=commitment.status.value if commitment.status else None,
                source="funding_commitments",
            )
        )

    return events


def _horizon_bucket(
    events: list[CashFlowUpcomingItem], *, today: date, days: int
) -> CashFlowHorizonBucket:
    horizon = today + timedelta(days=days)
    in_window = [
        event
        for event in events
        if event.expected_date is not None and today <= event.expected_date <= horizon
    ]
    # Also include overdue outflows (past due) in every horizon — they are immediate needs.
    overdue = [
        event
        for event in events
        if event.direction == "outflow"
        and event.expected_date is not None
        and event.expected_date < today
    ]
    relevant = in_window + [event for event in overdue if event not in in_window]

    outflows = sum(
        (event.amount for event in relevant if event.direction == "outflow"),
        ZERO,
    )
    inflows = sum(
        (event.amount for event in relevant if event.direction == "inflow"),
        ZERO,
    )
    if not relevant and not events:
        return CashFlowHorizonBucket(
            days=days,
            outflows=unavailable("No dated cash events"),
            inflows=unavailable("No dated cash events"),
            net_need=unavailable("No dated cash events"),
            item_count=0,
        )
    if not relevant:
        return CashFlowHorizonBucket(
            days=days,
            outflows=metric(ZERO),
            inflows=metric(ZERO),
            net_need=metric(ZERO),
            item_count=0,
        )
    net_need = max(outflows - inflows, ZERO)
    return CashFlowHorizonBucket(
        days=days,
        outflows=metric(outflows),
        inflows=metric(inflows),
        net_need=metric(net_need),
        item_count=len(relevant),
    )


def build_cash_flow_summary(
    db: Session,
    project: Project,
    *,
    today: date | None = None,
) -> ProjectCashFlowSummaryResponse:
    today = today or date.today()
    events = _cash_events(db, project.id, today=today)
    dated = [event for event in events if event.expected_date is not None]
    undated = [event for event in events if event.expected_date is None]

    warnings: list[str] = []
    completeness: dict[str, str] = {
        "dated_events": "present" if dated else "missing",
        "undated_events": "present" if undated else "none",
    }
    if undated:
        warnings.append(
            f"{len(undated)} cash event(s) lack expected dates and are excluded from 30/60/90 horizons."
        )
    if not dated:
        warnings.append("No dated payment obligations, vendor bills, or funding events for cash-flow horizons.")

    large_payments = sorted(
        [
            event
            for event in dated
            if event.direction == "outflow" and event.amount >= LARGE_CASH_THRESHOLD
        ],
        key=lambda item: (item.expected_date or today, -item.amount),
    )[:10]
    large_receipts = sorted(
        [
            event
            for event in dated
            if event.direction == "inflow" and event.amount >= LARGE_CASH_THRESHOLD
        ],
        key=lambda item: (item.expected_date or today, -item.amount),
    )[:10]

    return ProjectCashFlowSummaryResponse(
        project_id=project.id,
        currency=project.currency or "USD",
        as_of=today,
        horizon_30=_horizon_bucket(dated, today=today, days=30),
        horizon_60=_horizon_bucket(dated, today=today, days=60),
        horizon_90=_horizon_bucket(dated, today=today, days=90),
        large_upcoming_payments=large_payments,
        large_upcoming_receipts=large_receipts,
        data_completeness=completeness,
        warnings=warnings,
    )


def _funding_gap(project: Project) -> MetricValue:
    if project.equity_required is None and project.equity_raised is None:
        return unavailable("Equity required/raised not set")
    required = _money(project.equity_required)
    raised = _money(project.equity_raised)
    return metric(max(required - raised, ZERO))


def _current_cash(
    *,
    equity_raised: Decimal | None,
    funded_amount: Decimal | None,
    actual_cost: MetricValue,
) -> MetricValue:
    inflow = equity_raised if equity_raised is not None else funded_amount
    if inflow is None:
        return unavailable("Cash position requires equity raised or funded commitments")
    if not actual_cost.available or actual_cost.value is None:
        return unavailable("Cash position requires actual cost")
    return metric(_money(inflow) - _money(actual_cost.value))


def compute_financial_health(
    *,
    expected_profit: MetricValue,
    current_cash: MetricValue,
    funding_gap: MetricValue,
    need_30: MetricValue,
    forecast_cost: MetricValue,
    data_completeness: dict[str, str],
) -> tuple[FinancialHealthStatus, list[str]]:
    reasons: list[str] = []
    missing_core = [
        key
        for key, value in data_completeness.items()
        if value in {"missing", "none"} and key in {"expected_revenue", "forecast_cost", "funding"}
    ]
    available_signals = sum(
        1
        for metric_value in (expected_profit, current_cash, funding_gap, forecast_cost)
        if metric_value.available
    )
    if available_signals == 0:
        return FinancialHealthStatus.UNAVAILABLE, ["Insufficient financial data for health scoring"]

    critical = False
    at_risk = False
    watch = False

    if expected_profit.available and expected_profit.value is not None:
        if _money(expected_profit.value) < ZERO:
            critical = True
            reasons.append("Expected profit is negative")
    else:
        watch = True
        reasons.append("Expected profit unavailable")

    gap_value = _money(funding_gap.value) if funding_gap.available and funding_gap.value is not None else None
    if gap_value is not None:
        if gap_value >= FUNDING_GAP_CRITICAL:
            critical = True
            reasons.append("Funding gap is critical")
        elif gap_value >= FUNDING_GAP_AT_RISK:
            at_risk = True
            reasons.append("Funding gap is significant")
        elif gap_value >= FUNDING_GAP_WATCH:
            watch = True
            reasons.append("Funding gap warrants attention")

    cash_value = (
        _money(current_cash.value) if current_cash.available and current_cash.value is not None else None
    )
    need_value = _money(need_30.value) if need_30.available and need_30.value is not None else None
    if cash_value is not None and cash_value < ZERO:
        at_risk = True
        reasons.append("Current cash position is negative")
    if cash_value is not None and need_value is not None and need_value > cash_value:
        if need_value - cash_value >= FUNDING_GAP_AT_RISK:
            critical = True
            reasons.append("30-day cash need far exceeds available cash")
        else:
            at_risk = True
            reasons.append("30-day funding need exceeds available cash")

    if not forecast_cost.available:
        watch = True
        reasons.append("Forecast completion cost incomplete")

    if missing_core:
        watch = True
        reasons.append("Missing core financial assumptions: " + ", ".join(missing_core))

    if critical:
        return FinancialHealthStatus.CRITICAL, reasons or ["Critical financial conditions detected"]
    if at_risk:
        return FinancialHealthStatus.AT_RISK, reasons or ["At-risk financial conditions detected"]
    if watch:
        return FinancialHealthStatus.WATCH, reasons or ["Conditions require monitoring"]
    return FinancialHealthStatus.HEALTHY, reasons or ["Key financial indicators are within range"]


def _build_executive_alerts(
    *,
    project: Project,
    funding_gap: MetricValue,
    expected_profit: MetricValue,
    need_30: MetricValue,
    current_cash: MetricValue,
    cash_flow: ProjectCashFlowSummaryResponse,
    data_completeness: dict[str, str],
    forecast_cost: MetricValue,
    actual_cost: MetricValue,
) -> list[ExecutiveFinanceAlert]:
    alerts: list[ExecutiveFinanceAlert] = []

    if (
        need_30.available
        and need_30.value is not None
        and _money(need_30.value) > ZERO
        and (
            not current_cash.available
            or current_cash.value is None
            or _money(need_30.value) > _money(current_cash.value)
        )
    ):
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:funding_gap_30d",
                code="funding_gap_30d",
                severity=ExecutiveAlertSeverity.HIGH,
                title="Funding gap within 30 days",
                message="Near-term cash need exceeds available cash or cash data is incomplete.",
                recommended_action="Secure short-term funding or defer large outflows.",
                related_metric="need_30_days",
            )
        )

    if expected_profit.available and expected_profit.value is not None and _money(expected_profit.value) < ZERO:
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:negative_projected_profit",
                code="negative_projected_profit",
                severity=ExecutiveAlertSeverity.CRITICAL,
                title="Negative projected profit",
                message="Expected profit is below zero based on current project assumptions.",
                recommended_action="Review revenue assumptions and forecast cost.",
                related_metric="expected_profit",
            )
        )

    missing = [
        key
        for key, value in data_completeness.items()
        if value in {"missing", "none"}
        and key in {"expected_revenue", "expected_profit", "forecast_cost", "funding"}
    ]
    if missing:
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:missing_assumptions",
                code="missing_assumptions",
                severity=ExecutiveAlertSeverity.MEDIUM,
                title="Missing financial assumptions",
                message="Key executive finance fields are incomplete: " + ", ".join(missing) + ".",
                recommended_action="Complete revenue, cost, and funding assumptions.",
                related_metric="data_completeness",
            )
        )

    for item in cash_flow.large_upcoming_payments[:3]:
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:large_payment:{item.id}",
                code="large_expected_payment",
                severity=ExecutiveAlertSeverity.MEDIUM,
                title="Large expected payment",
                message=f"{item.label} of {item.amount} is expected.",
                recommended_action="Confirm liquidity for the upcoming payment.",
                related_metric="need_30_days",
                due_date=item.expected_date,
            )
        )

    for item in cash_flow.large_upcoming_receipts[:3]:
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:large_receipt:{item.id}",
                code="large_expected_receipt",
                severity=ExecutiveAlertSeverity.LOW,
                title="Large expected receipt",
                message=f"{item.label} of {item.amount} is expected.",
                recommended_action="Track receipt timing against cash needs.",
                related_metric="current_cash",
                due_date=item.expected_date,
            )
        )

    if (
        forecast_cost.available
        and actual_cost.available
        and forecast_cost.value is not None
        and actual_cost.value is not None
        and _money(forecast_cost.value) > ZERO
        and _money(actual_cost.value) > _money(forecast_cost.value) * Decimal("0.9")
    ):
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:forecast_deterioration",
                code="forecast_deterioration",
                severity=ExecutiveAlertSeverity.HIGH,
                title="Forecast cost pressure",
                message="Actual cost is approaching or exceeding the forecast completion cost.",
                recommended_action="Revisit forecast assumptions and remaining commitments.",
                related_metric="forecast_cost",
            )
        )

    if funding_gap.available and funding_gap.value is not None and _money(funding_gap.value) >= FUNDING_GAP_WATCH:
        alerts.append(
            ExecutiveFinanceAlert(
                id=f"{project.id}:funding_gap",
                code="funding_gap",
                severity=(
                    ExecutiveAlertSeverity.CRITICAL
                    if _money(funding_gap.value) >= FUNDING_GAP_CRITICAL
                    else ExecutiveAlertSeverity.HIGH
                    if _money(funding_gap.value) >= FUNDING_GAP_AT_RISK
                    else ExecutiveAlertSeverity.MEDIUM
                ),
                title="Funding gap",
                message=f"Equity funding gap is {_money(funding_gap.value)}.",
                recommended_action="Raise remaining equity or revise capital plan.",
                related_metric="funding_gap",
            )
        )

    return alerts


def _ai_payload(
    *,
    project: Project,
    health: FinancialHealthStatus,
    expected_profit: MetricValue,
    funding_gap: MetricValue,
    need_30: MetricValue,
    current_cash: MetricValue,
    data_completeness: dict[str, str],
    cards: dict[str, MetricValue],
) -> ProjectAiFinanceSummaryPayload:
    missing_info = [
        key for key, value in data_completeness.items() if value in {"missing", "none"}
    ]
    needs_cash = False
    if need_30.available and need_30.value is not None and _money(need_30.value) > ZERO:
        if (
            not current_cash.available
            or current_cash.value is None
            or _money(need_30.value) > _money(current_cash.value)
        ):
            needs_cash = True
    if funding_gap.available and funding_gap.value is not None and _money(funding_gap.value) > ZERO:
        needs_cash = True

    is_profitable: bool | None = None
    if expected_profit.available and expected_profit.value is not None:
        is_profitable = _money(expected_profit.value) >= ZERO

    is_risky = health in {
        FinancialHealthStatus.AT_RISK,
        FinancialHealthStatus.CRITICAL,
    }

    highlights: list[str] = []
    if needs_cash:
        highlights.append("Project needs additional cash or funding coverage.")
    if is_profitable is True:
        highlights.append("Expected profit is non-negative.")
    elif is_profitable is False:
        highlights.append("Expected profit is negative.")
    if missing_info:
        highlights.append("Missing information: " + ", ".join(missing_info[:6]))

    return ProjectAiFinanceSummaryPayload(
        project_id=project.id,
        project_name=project.project_name,
        health=health,
        needs_cash=needs_cash,
        is_profitable=is_profitable,
        is_risky=is_risky,
        missing_info=missing_info,
        highlights=highlights,
        metrics=cards,
        generated_at=datetime.now(UTC),
    )


def get_executive_finance(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    today: date | None = None,
) -> ProjectExecutiveFinanceResponse:
    _require_financial_view(user)
    today = today or date.today()
    project = _load_project(db, project_id)
    warnings: list[str] = []
    completeness: dict[str, str] = {}

    actual_cost, forecast_cost, cost_source, cost_completeness, cost_warnings = _resolve_cost_metrics(
        db, project_id, project
    )
    completeness.update(cost_completeness)
    warnings.extend(cost_warnings)

    funding = _funding_totals(db, project_id)
    completeness["funding"] = "present" if funding["count"] else "missing"
    if project.equity_required is None and project.equity_raised is None and not funding["count"]:
        warnings.append("No funding assumptions or commitments recorded.")

    expected_revenue = _optional_metric(
        project.projected_revenue, reason="Expected revenue not set"
    )
    completeness["expected_revenue"] = "present" if project.projected_revenue is not None else "missing"

    expected_profit = _optional_metric(
        project.projected_profit, reason="Expected profit not set"
    )
    completeness["expected_profit"] = "present" if project.projected_profit is not None else "missing"

    received_revenue = (
        metric(_money(funding["funded"]))
        if funding["funded"] is not None
        else unavailable("No funded commitments recorded")
    )
    completeness["received_revenue"] = "funding_commitments" if funding["funded"] is not None else "missing"

    profit_margin: MetricValue
    if (
        project.projected_revenue is not None
        and project.projected_profit is not None
        and _money(project.projected_revenue) > ZERO
    ):
        profit_margin = metric(
            (_money(project.projected_profit) / _money(project.projected_revenue)) * Decimal("100")
        )
    else:
        profit_margin = unavailable("Insufficient data for profit margin")

    funding_gap = _funding_gap(project)
    completeness["funding_gap"] = "present" if funding_gap.available else "missing"

    current_cash = _current_cash(
        equity_raised=project.equity_raised,
        funded_amount=funding["funded"] if isinstance(funding["funded"], Decimal) else None,
        actual_cost=actual_cost,
    )
    completeness["current_cash"] = "present" if current_cash.available else "missing"

    cash_flow = build_cash_flow_summary(db, project, today=today)
    warnings.extend(cash_flow.warnings)
    completeness.update({f"cash_flow_{k}": v for k, v in cash_flow.data_completeness.items()})

    need_30 = cash_flow.horizon_30.net_need
    need_60 = cash_flow.horizon_60.net_need
    need_90 = cash_flow.horizon_90.net_need

    health, health_reasons = compute_financial_health(
        expected_profit=expected_profit,
        current_cash=current_cash,
        funding_gap=funding_gap,
        need_30=need_30,
        forecast_cost=forecast_cost,
        data_completeness=completeness,
    )

    cards = {
        "expected_revenue": expected_revenue,
        "received_revenue": received_revenue,
        "forecast_cost": forecast_cost,
        "actual_cost": actual_cost,
        "expected_profit": expected_profit,
        "profit_margin": profit_margin,
        "current_cash": current_cash,
        "funding_gap": funding_gap,
        "need_30_days": need_30,
        "need_60_days": need_60,
        "need_90_days": need_90,
    }

    alerts = _build_executive_alerts(
        project=project,
        funding_gap=funding_gap,
        expected_profit=expected_profit,
        need_30=need_30,
        current_cash=current_cash,
        cash_flow=cash_flow,
        data_completeness=completeness,
        forecast_cost=forecast_cost,
        actual_cost=actual_cost,
    )

    return ProjectExecutiveFinanceResponse(
        project_id=project.id,
        project_name=project.project_name,
        currency=project.currency or "USD",
        as_of=today,
        health=health,
        health_reasons=health_reasons,
        expected_revenue=expected_revenue,
        received_revenue=received_revenue,
        forecast_cost=forecast_cost,
        actual_cost=actual_cost,
        expected_profit=expected_profit,
        profit_margin=profit_margin,
        current_cash=current_cash,
        funding_gap=funding_gap,
        need_30_days=need_30,
        need_60_days=need_60,
        need_90_days=need_90,
        equity_required=_optional_metric(project.equity_required, reason="Equity required not set"),
        equity_raised=_optional_metric(project.equity_raised, reason="Equity raised not set"),
        committed_funding=(
            metric(_money(funding["committed"]))
            if funding["committed"] is not None
            else unavailable("No funding commitments")
        ),
        funded_amount=(
            metric(_money(funding["funded"]))
            if funding["funded"] is not None
            else unavailable("No funded commitments")
        ),
        remaining_funding=(
            metric(_money(funding["remaining"]))
            if funding["remaining"] is not None
            else unavailable("No remaining funding")
        ),
        cash_flow=cash_flow,
        alerts=alerts,
        ai_summary=_ai_payload(
            project=project,
            health=health,
            expected_profit=expected_profit,
            funding_gap=funding_gap,
            need_30=need_30,
            current_cash=current_cash,
            data_completeness=completeness,
            cards=cards,
        ),
        data_completeness=completeness,
        warnings=warnings,
        cost_source=cost_source,
    )


def get_cash_flow_summary(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    today: date | None = None,
) -> ProjectCashFlowSummaryResponse:
    _require_financial_view(user)
    project = _load_project(db, project_id)
    return build_cash_flow_summary(db, project, today=today or date.today())


def build_portfolio_executive_rollup(
    db: Session,
    projects: list[Project],
    *,
    today: date | None = None,
    limit_attention: int = 8,
    limit_upcoming: int = 8,
) -> tuple[
    list[PortfolioExecutiveAttentionItem],
    list[PortfolioUpcomingCashItem],
    PortfolioAiFinanceSummaryPayload,
    dict[str, MetricValue],
]:
    """Aggregate executive metrics across projects for the portfolio dashboard."""
    today = today or date.today()
    attention: list[PortfolioExecutiveAttentionItem] = []
    upcoming: list[PortfolioUpcomingCashItem] = []
    needing_cash: list[UUID] = []
    profitable: list[tuple[UUID, Decimal]] = []
    risky: list[UUID] = []
    missing: list[UUID] = []

    total_expected_revenue = ZERO
    total_forecast_cost = ZERO
    total_expected_profit = ZERO
    total_funding_gap = ZERO
    total_cash = ZERO
    total_need_30 = ZERO
    total_need_60 = ZERO
    total_need_90 = ZERO
    has_revenue = False
    has_forecast = False
    has_profit = False
    has_gap = False
    has_cash = False
    has_need_30 = False
    has_need_60 = False
    has_need_90 = False

    for project in projects:
        # Compute without permission gate — caller already authorized portfolio financials.
        actual_cost, forecast_cost, _source, completeness, _warnings = _resolve_cost_metrics(
            db, project.id, project
        )
        funding = _funding_totals(db, project.id)
        expected_revenue = _optional_metric(
            project.projected_revenue, reason="Expected revenue not set"
        )
        expected_profit = _optional_metric(
            project.projected_profit, reason="Expected profit not set"
        )
        funding_gap = _funding_gap(project)
        current_cash = _current_cash(
            equity_raised=project.equity_raised,
            funded_amount=funding["funded"] if isinstance(funding["funded"], Decimal) else None,
            actual_cost=actual_cost,
        )
        cash_flow = build_cash_flow_summary(db, project, today=today)
        need_30 = cash_flow.horizon_30.net_need
        need_60 = cash_flow.horizon_60.net_need
        need_90 = cash_flow.horizon_90.net_need
        completeness["expected_revenue"] = (
            "present" if project.projected_revenue is not None else "missing"
        )
        completeness["expected_profit"] = (
            "present" if project.projected_profit is not None else "missing"
        )
        completeness["funding"] = "present" if funding["count"] else "missing"
        health, health_reasons = compute_financial_health(
            expected_profit=expected_profit,
            current_cash=current_cash,
            funding_gap=funding_gap,
            need_30=need_30,
            forecast_cost=forecast_cost,
            data_completeness=completeness,
        )

        if expected_revenue.available and expected_revenue.value is not None:
            total_expected_revenue += _money(expected_revenue.value)
            has_revenue = True
        if forecast_cost.available and forecast_cost.value is not None:
            total_forecast_cost += _money(forecast_cost.value)
            has_forecast = True
        if expected_profit.available and expected_profit.value is not None:
            profit_value = _money(expected_profit.value)
            total_expected_profit += profit_value
            has_profit = True
            profitable.append((project.id, profit_value))
        if funding_gap.available and funding_gap.value is not None:
            total_funding_gap += _money(funding_gap.value)
            has_gap = True
        if current_cash.available and current_cash.value is not None:
            total_cash += _money(current_cash.value)
            has_cash = True
        if need_30.available and need_30.value is not None:
            total_need_30 += _money(need_30.value)
            has_need_30 = True
        if need_60.available and need_60.value is not None:
            total_need_60 += _money(need_60.value)
            has_need_60 = True
        if need_90.available and need_90.value is not None:
            total_need_90 += _money(need_90.value)
            has_need_90 = True

        ai = _ai_payload(
            project=project,
            health=health,
            expected_profit=expected_profit,
            funding_gap=funding_gap,
            need_30=need_30,
            current_cash=current_cash,
            data_completeness=completeness,
            cards={},
        )
        if ai.needs_cash:
            needing_cash.append(project.id)
        if ai.is_risky:
            risky.append(project.id)
        if ai.missing_info:
            missing.append(project.id)

        if health in {
            FinancialHealthStatus.WATCH,
            FinancialHealthStatus.AT_RISK,
            FinancialHealthStatus.CRITICAL,
        }:
            attention.append(
                PortfolioExecutiveAttentionItem(
                    project_id=project.id,
                    project_name=project.project_name,
                    health=health,
                    funding_gap=funding_gap,
                    expected_profit=expected_profit,
                    need_30_days=need_30,
                    reason=health_reasons[0] if health_reasons else health.value,
                )
            )

        for item in cash_flow.large_upcoming_payments[:2] + cash_flow.large_upcoming_receipts[:2]:
            upcoming.append(
                PortfolioUpcomingCashItem(
                    project_id=project.id,
                    project_name=project.project_name,
                    kind=item.kind,
                    direction=item.direction,
                    label=item.label,
                    amount=item.amount,
                    currency=item.currency,
                    expected_date=item.expected_date,
                )
            )

    health_rank = {
        FinancialHealthStatus.CRITICAL: 0,
        FinancialHealthStatus.AT_RISK: 1,
        FinancialHealthStatus.WATCH: 2,
        FinancialHealthStatus.HEALTHY: 3,
        FinancialHealthStatus.UNAVAILABLE: 4,
    }
    attention.sort(key=lambda item: (health_rank[item.health], item.project_name))
    upcoming.sort(key=lambda item: (item.expected_date or today, -item.amount))
    profitable.sort(key=lambda item: item[1], reverse=True)

    rollup = {
        "expected_revenue": metric(total_expected_revenue)
        if has_revenue
        else unavailable("No expected revenue"),
        "forecast_cost": metric(total_forecast_cost)
        if has_forecast
        else unavailable("No forecast cost"),
        "expected_profit": metric(total_expected_profit)
        if has_profit
        else unavailable("No expected profit"),
        "funding_gap": metric(total_funding_gap) if has_gap else unavailable("No funding gap data"),
        "cash_position": metric(total_cash) if has_cash else unavailable("No cash position data"),
        "need_30_days": metric(total_need_30)
        if has_need_30
        else unavailable("No dated cash events"),
        "need_60_days": metric(total_need_60)
        if has_need_60
        else unavailable("No dated cash events"),
        "need_90_days": metric(total_need_90)
        if has_need_90
        else unavailable("No dated cash events"),
    }
    ai_summary = PortfolioAiFinanceSummaryPayload(
        projects_needing_cash=needing_cash[:20],
        most_profitable_projects=[item[0] for item in profitable[:10]],
        riskiest_projects=risky[:10],
        projects_missing_info=missing[:20],
        generated_at=datetime.now(UTC),
    )
    return attention[:limit_attention], upcoming[:limit_upcoming], ai_summary, rollup
