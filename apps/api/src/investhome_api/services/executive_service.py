"""Executive dashboard aggregation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.executive_config import (
    BUDGET_VARIANCE_AT_RISK_RATIO,
    BUDGET_VARIANCE_ATTENTION_RATIO,
    COMPLETED_PROJECT_STATUSES,
    COMPLETION_APPROACHING_DAYS,
    FUNDING_GAP_AT_RISK,
    FUNDING_GAP_ATTENTION,
    LEAD_INACTIVITY_DAYS,
    LOW_AVAILABLE_BALANCE_RATIO,
)
from investhome_api.models.finance import (
    AccountStatus,
    CommitmentStatus,
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    INCOME_TRANSACTION_TYPES,
    ObligationPriority,
    ObligationStatus,
    PaymentObligation,
    ProjectBudget,
    TransactionStatus,
    TransactionType,
)
from investhome_api.models.investor import Investor, InvestorStatus
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import ACTIVE_PROJECT_STATUSES, Project, ProjectStatus
from investhome_api.schemas.executive import (
    AccountCashRow,
    ActivityItem,
    AttentionItem,
    CashFlowPoint,
    CurrencyMetricComparison,
    DeadlineItem,
    ExecutiveActivityResponse,
    ExecutiveAttentionResponse,
    ExecutiveDeadlinesResponse,
    ExecutiveFilters,
    ExecutiveFinancialOverviewResponse,
    ExecutiveInvestorOverviewResponse,
    ExecutiveLeadsPipelineResponse,
    ExecutiveProjectPortfolioResponse,
    ExecutiveSummaryResponse,
    InvestorCountryCount,
    InvestorModelCount,
    InvestorStatusCount,
    MetricComparison,
    PipelineStage,
    ProjectFundingGap,
    ProjectHealthRow,
    ProjectStatusCount,
    SummaryCard,
)
from investhome_api.services.activity_service import (
    ENTITY_LINK_MODULES,
    list_recent_activity,
    resolve_entity_label,
)
from investhome_api.services.finance_service import _sum_by_currency, compute_finance_stats

OUTFLOW_TRANSACTION_TYPES = frozenset(
    {
        TransactionType.EXPENSE,
        TransactionType.INVESTOR_DISTRIBUTION,
        TransactionType.LOAN_PAYMENT,
        TransactionType.ACQUISITION,
        TransactionType.CONSTRUCTION_COST,
        TransactionType.OPERATING_COST,
    }
)

LEAD_PIPELINE_STATUSES = [
    LeadStatus.NEW,
    LeadStatus.CONTACTED,
    LeadStatus.QUALIFIED,
    LeadStatus.MEETING_SCHEDULED,
    LeadStatus.PROPOSAL_SENT,
    LeadStatus.NEGOTIATION,
    LeadStatus.WON,
    LeadStatus.LOST,
]

QUALIFIED_STATUSES = frozenset(
    {
        LeadStatus.QUALIFIED,
        LeadStatus.MEETING_SCHEDULED,
        LeadStatus.PROPOSAL_SENT,
        LeadStatus.NEGOTIATION,
        LeadStatus.WON,
    }
)


@dataclass
class PeriodWindow:
    current_from: date
    current_to: date
    previous_from: date
    previous_to: date


def resolve_period_window(date_from: date, date_to: date) -> PeriodWindow:
    length = (date_to - date_from).days + 1
    previous_to = date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=length - 1)
    return PeriodWindow(date_from, date_to, previous_from, previous_to)


def _dt_start(value: date) -> datetime:
    return datetime.combine(value, datetime.min.time())


def _dt_end(value: date) -> datetime:
    return datetime.combine(value, datetime.max.time())


def _lead_query(db: Session, filters: ExecutiveFilters):
    query = select(Lead).where(Lead.archived_at.is_(None))
    if filters.assigned_to:
        query = query.where(Lead.assigned_to == filters.assigned_to)
    return query


def _investor_query(db: Session, filters: ExecutiveFilters):
    query = select(Investor).where(Investor.archived_at.is_(None))
    if filters.assigned_to:
        query = query.where(Investor.assigned_to == filters.assigned_to)
    return query


def _project_query(db: Session, filters: ExecutiveFilters):
    query = select(Project).where(Project.archived_at.is_(None))
    if filters.project_id:
        query = query.where(Project.id == filters.project_id)
    if filters.assigned_to:
        query = query.where(Project.assigned_project_manager == filters.assigned_to)
    return query


def _txn_query(db: Session, filters: ExecutiveFilters):
    query = select(FinanceTransaction).where(FinanceTransaction.archived_at.is_(None))
    if filters.project_id:
        query = query.where(FinanceTransaction.project_id == filters.project_id)
    if filters.currency:
        query = query.where(FinanceTransaction.currency == filters.currency.upper())
    return query


def _budget_variance_for_project(db: Session, project_id: UUID) -> Decimal:
    budgets = db.scalars(select(ProjectBudget).where(ProjectBudget.project_id == project_id)).all()
    total = Decimal("0")
    for budget in budgets:
        revised = budget.revised_budget or budget.original_budget or Decimal("0")
        forecast = budget.forecast_amount or revised
        total += forecast - revised
    return total


def _project_funding_gap(project: Project) -> Decimal:
    required = project.equity_required or Decimal("0")
    raised = project.equity_raised or Decimal("0")
    return max(required - raised, Decimal("0"))


def compute_project_health(
    db: Session,
    project: Project,
    *,
    today: date,
    has_critical_obligation: bool,
) -> str:
    status_value = project.project_status.value
    if status_value in COMPLETED_PROJECT_STATUSES:
        return "on_track"

    funding_gap = _project_funding_gap(project)
    budgets = db.scalars(
        select(ProjectBudget).where(ProjectBudget.project_id == project.id)
    ).all()
    max_variance_ratio = Decimal("0")
    for budget in budgets:
        revised = budget.revised_budget or budget.original_budget or Decimal("0")
        if revised <= 0:
            continue
        forecast = budget.forecast_amount or revised
        ratio = abs(forecast - revised) / revised
        max_variance_ratio = max(max_variance_ratio, ratio)

    overdue_completion = (
        project.target_completion_date is not None
        and project.target_completion_date < today
        and project.project_status != ProjectStatus.COMPLETED
    )
    approaching_completion = (
        project.target_completion_date is not None
        and today <= project.target_completion_date <= today + timedelta(days=COMPLETION_APPROACHING_DAYS)
        and project.project_status != ProjectStatus.COMPLETED
    )

    if (
        overdue_completion
        or has_critical_obligation
        or funding_gap >= FUNDING_GAP_AT_RISK
        or max_variance_ratio >= BUDGET_VARIANCE_AT_RISK_RATIO
    ):
        return "at_risk"

    if (
        approaching_completion
        or funding_gap >= FUNDING_GAP_ATTENTION
        or max_variance_ratio >= BUDGET_VARIANCE_ATTENTION_RATIO
    ):
        return "attention"

    return "on_track"


def build_executive_summary(db: Session, filters: ExecutiveFilters) -> ExecutiveSummaryResponse:
    window = resolve_period_window(filters.date_from, filters.date_to)
    today = date.today()

    leads = db.scalars(_lead_query(db, filters)).all()
    total_leads = len(leads)
    qualified_leads = sum(1 for lead in leads if lead.status in QUALIFIED_STATUSES)

    leads_created_current = sum(
        1 for lead in leads if window.current_from <= lead.created_at.date() <= window.current_to
    )
    leads_created_previous = sum(
        1 for lead in leads if window.previous_from <= lead.created_at.date() <= window.previous_to
    )

    investors = db.scalars(_investor_query(db, filters)).all()
    active_investors = sum(1 for inv in investors if inv.status == InvestorStatus.ACTIVE)
    investors_created_current = sum(
        1
        for inv in investors
        if window.current_from <= inv.created_at.date() <= window.current_to
    )
    investors_created_previous = sum(
        1
        for inv in investors
        if window.previous_from <= inv.created_at.date() <= window.previous_to
    )

    total_capacity = sum((inv.investment_capacity or Decimal("0")) for inv in investors)

    projects = db.scalars(_project_query(db, filters)).all()
    active_projects = sum(
        1 for project in projects if project.project_status in ACTIVE_PROJECT_STATUSES
    )
    portfolio_value = sum((p.current_project_value or Decimal("0")) for p in projects)

    finance_stats = compute_finance_stats(db)
    available_cash = finance_stats["available_cash"]
    if filters.currency:
        key = filters.currency.upper()
        available_cash = {key: available_cash.get(key, Decimal("0"))}

    remaining_funding = finance_stats["remaining_funding_need"]
    if filters.currency:
        key = filters.currency.upper()
        remaining_funding = {key: remaining_funding.get(key, Decimal("0"))}

    cards = [
        SummaryCard(
            key="total_leads",
            value=total_leads,
            comparison=MetricComparison(
                current=total_leads,
                previous=total_leads - leads_created_current + leads_created_previous,
                change=leads_created_current - leads_created_previous,
                change_available=True,
            ),
            link_module="leads",
        ),
        SummaryCard(
            key="qualified_leads",
            value=qualified_leads,
            comparison=MetricComparison(current=qualified_leads, change_available=False),
            link_module="leads",
            link_query={"status": LeadStatus.QUALIFIED.value},
        ),
        SummaryCard(
            key="active_investors",
            value=active_investors,
            comparison=MetricComparison(
                current=active_investors,
                change=investors_created_current - investors_created_previous,
                change_available=True,
            ),
            link_module="investors",
            link_query={"status": InvestorStatus.ACTIVE.value},
        ),
        SummaryCard(
            key="total_investment_capacity",
            value=total_capacity,
            comparison=MetricComparison(current=int(total_capacity), change_available=False),
            link_module="investors",
        ),
        SummaryCard(
            key="active_projects",
            value=active_projects,
            comparison=MetricComparison(current=active_projects, change_available=False),
            link_module="projects",
        ),
        SummaryCard(
            key="total_portfolio_value",
            value=portfolio_value,
            comparison=MetricComparison(current=int(portfolio_value), change_available=False),
            link_module="projects",
        ),
        SummaryCard(
            key="available_cash",
            value=None,
            currency_totals=available_cash,
            currency_comparison=CurrencyMetricComparison(totals=available_cash, change_available=False),
            link_module="finance",
        ),
        SummaryCard(
            key="remaining_funding_need",
            value=None,
            currency_totals=remaining_funding,
            currency_comparison=CurrencyMetricComparison(totals=remaining_funding, change_available=False),
            link_module="finance",
            link_query={"tab": "funding"},
        ),
    ]

    return ExecutiveSummaryResponse(cards=cards)


def build_attention_items(db: Session, filters: ExecutiveFilters) -> ExecutiveAttentionResponse:
    today = date.today()
    items: list[AttentionItem] = []

    obligation_query = select(PaymentObligation).where(PaymentObligation.archived_at.is_(None))
    if filters.project_id:
        obligation_query = obligation_query.where(PaymentObligation.project_id == filters.project_id)
    obligations = db.scalars(obligation_query).all()

    for obligation in obligations:
        if filters.currency and obligation.currency != filters.currency.upper():
            continue
        if obligation.status == ObligationStatus.OVERDUE:
            items.append(
                AttentionItem(
                    severity="critical",
                    title_key="executive.attention.overdue_payment.title",
                    description_key="executive.attention.overdue_payment.description",
                    metadata={
                        "payee": obligation.payee or "",
                        "amount": str(obligation.amount),
                        "currency": obligation.currency,
                    },
                    entity_type="payment_obligation",
                    entity_id=obligation.id,
                    related_label=obligation.payee,
                    due_date=obligation.due_date,
                    age_days=(today - obligation.due_date).days if obligation.due_date else None,
                    link_module="finance",
                    link_query={"tab": "payments"},
                )
            )
        elif (
            obligation.priority == ObligationPriority.CRITICAL
            and obligation.status not in {ObligationStatus.PAID, ObligationStatus.CANCELLED}
        ):
            items.append(
                AttentionItem(
                    severity="critical",
                    title_key="executive.attention.critical_obligation.title",
                    description_key="executive.attention.critical_obligation.description",
                    metadata={
                        "payee": obligation.payee or "",
                        "amount": str(obligation.amount),
                        "currency": obligation.currency,
                    },
                    entity_type="payment_obligation",
                    entity_id=obligation.id,
                    related_label=obligation.payee,
                    due_date=obligation.due_date,
                    link_module="finance",
                    link_query={"tab": "payments"},
                )
            )

    projects = db.scalars(_project_query(db, filters)).all()
    critical_project_ids = {
        o.project_id
        for o in obligations
        if o.priority == ObligationPriority.CRITICAL
        and o.status not in {ObligationStatus.PAID, ObligationStatus.CANCELLED}
        and o.project_id
    }

    for project in projects:
        if (
            project.target_completion_date
            and project.target_completion_date < today
            and project.project_status.value not in COMPLETED_PROJECT_STATUSES
        ):
            items.append(
                AttentionItem(
                    severity="warning",
                    title_key="executive.attention.project_overdue.title",
                    description_key="executive.attention.project_overdue.description",
                    metadata={"project": project.project_name},
                    entity_type="project",
                    entity_id=project.id,
                    related_label=project.project_name,
                    due_date=project.target_completion_date,
                    age_days=(today - project.target_completion_date).days,
                    link_module="projects",
                )
            )

        gap = _project_funding_gap(project)
        if gap >= FUNDING_GAP_ATTENTION:
            items.append(
                AttentionItem(
                    severity="critical" if gap >= FUNDING_GAP_AT_RISK else "warning",
                    title_key="executive.attention.funding_gap.title",
                    description_key="executive.attention.funding_gap.description",
                    metadata={"project": project.project_name, "gap": str(gap)},
                    entity_type="project",
                    entity_id=project.id,
                    related_label=project.project_name,
                    link_module="projects",
                )
            )

        health = compute_project_health(
            db,
            project,
            today=today,
            has_critical_obligation=project.id in critical_project_ids,
        )
        if health == "at_risk" and not any(
            item.entity_id == project.id and item.title_key.endswith("funding_gap.title")
            for item in items
        ):
            items.append(
                AttentionItem(
                    severity="critical",
                    title_key="executive.attention.project_at_risk.title",
                    description_key="executive.attention.project_at_risk.description",
                    metadata={"project": project.project_name},
                    entity_type="project",
                    entity_id=project.id,
                    related_label=project.project_name,
                    link_module="projects",
                )
            )

    investors = db.scalars(_investor_query(db, filters)).all()
    for investor in investors:
        if investor.next_follow_up_date and investor.next_follow_up_date < today:
            items.append(
                AttentionItem(
                    severity="warning",
                    title_key="executive.attention.investor_follow_up.title",
                    description_key="executive.attention.investor_follow_up.description",
                    metadata={"name": investor.full_name},
                    entity_type="investor",
                    entity_id=investor.id,
                    related_label=investor.full_name,
                    due_date=investor.next_follow_up_date,
                    age_days=(today - investor.next_follow_up_date).days,
                    link_module="investors",
                )
            )

    inactivity_cutoff = today - timedelta(days=LEAD_INACTIVITY_DAYS)
    leads = db.scalars(_lead_query(db, filters)).all()
    for lead in leads:
        if lead.status == LeadStatus.QUALIFIED and lead.updated_at.date() <= inactivity_cutoff:
            items.append(
                AttentionItem(
                    severity="information",
                    title_key="executive.attention.inactive_qualified_lead.title",
                    description_key="executive.attention.inactive_qualified_lead.description",
                    metadata={"name": lead.full_name},
                    entity_type="lead",
                    entity_id=lead.id,
                    related_label=lead.full_name,
                    age_days=(today - lead.updated_at.date()).days,
                    link_module="leads",
                    link_query={"status": LeadStatus.QUALIFIED.value},
                )
            )

    txns = db.scalars(_txn_query(db, filters)).all()
    for txn in txns:
        if (
            txn.due_date
            and txn.due_date < today
            and txn.status in {TransactionStatus.PENDING, TransactionStatus.OVERDUE, TransactionStatus.SCHEDULED}
        ):
            items.append(
                AttentionItem(
                    severity="warning",
                    title_key="executive.attention.transaction_overdue.title",
                    description_key="executive.attention.transaction_overdue.description",
                    metadata={
                        "description": txn.description or "",
                        "amount": str(txn.amount),
                        "currency": txn.currency,
                    },
                    entity_type="transaction",
                    entity_id=txn.id,
                    related_label=txn.description,
                    due_date=txn.due_date,
                    age_days=(today - txn.due_date).days,
                    link_module="finance",
                    link_query={"tab": "transactions"},
                )
            )

    accounts = db.scalars(
        select(FinancialAccount).where(
            FinancialAccount.archived_at.is_(None),
            FinancialAccount.status == AccountStatus.ACTIVE,
        )
    ).all()
    for account in accounts:
        if filters.currency and account.currency != filters.currency.upper():
            continue
        current = account.current_balance or Decimal("0")
        available = account.available_balance or Decimal("0")
        if current > 0 and available / current < LOW_AVAILABLE_BALANCE_RATIO:
            items.append(
                AttentionItem(
                    severity="warning",
                    title_key="executive.attention.low_balance.title",
                    description_key="executive.attention.low_balance.description",
                    metadata={"account": account.account_name, "currency": account.currency},
                    entity_type="account",
                    entity_id=account.id,
                    related_label=account.account_name,
                    link_module="finance",
                    link_query={"tab": "accounts"},
                )
            )

    severity_order = {"critical": 0, "warning": 1, "information": 2}
    items.sort(key=lambda item: (severity_order[item.severity], item.due_date or today))
    return ExecutiveAttentionResponse(items=items)


def build_leads_pipeline(db: Session, filters: ExecutiveFilters) -> ExecutiveLeadsPipelineResponse:
    window = resolve_period_window(filters.date_from, filters.date_to)
    leads = db.scalars(_lead_query(db, filters)).all()

    stages: list[PipelineStage] = []
    for status in LEAD_PIPELINE_STATUSES:
        stage_leads = [lead for lead in leads if lead.status == status]
        budget_total = sum((lead.estimated_budget or Decimal("0")) for lead in stage_leads)
        stages.append(
            PipelineStage(
                status=status.value,
                count=len(stage_leads),
                estimated_budget_total=budget_total,
            )
        )

    won_in_period = sum(
        1
        for lead in leads
        if lead.status == LeadStatus.WON
        and window.current_from <= lead.updated_at.date() <= window.current_to
    )
    lost_in_period = sum(
        1
        for lead in leads
        if lead.status == LeadStatus.LOST
        and window.current_from <= lead.updated_at.date() <= window.current_to
    )

    new_count = next((stage.count for stage in stages if stage.status == LeadStatus.NEW.value), 0)
    won_count = next((stage.count for stage in stages if stage.status == LeadStatus.WON.value), 0)
    conversion_rate = None
    if new_count + won_count > 0:
        conversion_rate = Decimal(won_count) / Decimal(new_count + won_count)

    total_budget = sum((lead.estimated_budget or Decimal("0")) for lead in leads)
    return ExecutiveLeadsPipelineResponse(
        stages=stages,
        conversion_rate=conversion_rate,
        won_in_period=won_in_period,
        lost_in_period=lost_in_period,
        total_estimated_budget=total_budget,
    )


def build_investor_overview(db: Session, filters: ExecutiveFilters) -> ExecutiveInvestorOverviewResponse:
    today = date.today()
    investors = db.scalars(_investor_query(db, filters)).all()

    status_counts: dict[str, int] = {}
    model_counts: dict[str, int] = {}
    country_counts: dict[str, int] = {}
    capacity_by_currency: dict[str, Decimal] = {"USD": Decimal("0")}

    for investor in investors:
        status_counts[investor.status.value] = status_counts.get(investor.status.value, 0) + 1
        if investor.preferred_investment_model:
            key = investor.preferred_investment_model.value
            model_counts[key] = model_counts.get(key, 0) + 1
        country = investor.country or "Unknown"
        country_counts[country] = country_counts.get(country, 0) + 1
        capacity_by_currency["USD"] += investor.investment_capacity or Decimal("0")

    commitment_query = select(FundingCommitment).join(
        Investor, FundingCommitment.investor_id == Investor.id
    ).where(Investor.archived_at.is_(None))
    if filters.project_id:
        commitment_query = commitment_query.where(FundingCommitment.project_id == filters.project_id)
    if filters.assigned_to:
        commitment_query = commitment_query.where(Investor.assigned_to == filters.assigned_to)
    commitments = db.scalars(commitment_query).all()

    total_committed = _sum_by_currency([(c.currency, c.committed_amount) for c in commitments])
    total_funded = _sum_by_currency([(c.currency, c.funded_amount) for c in commitments])
    remaining = _sum_by_currency(
        [
            (
                c.currency,
                c.remaining_amount
                if c.remaining_amount is not None
                else (c.committed_amount - (c.funded_amount or Decimal("0"))),
            )
            for c in commitments
            if c.status not in {CommitmentStatus.CANCELLED, CommitmentStatus.FULLY_FUNDED}
        ]
    )

    if filters.currency:
        key = filters.currency.upper()
        total_committed = {key: total_committed.get(key, Decimal("0"))}
        total_funded = {key: total_funded.get(key, Decimal("0"))}
        remaining = {key: remaining.get(key, Decimal("0"))}
        capacity_by_currency = {key: capacity_by_currency.get("USD", Decimal("0"))}

    follow_ups: list[AttentionItem] = []
    for investor in investors:
        if investor.next_follow_up_date and investor.next_follow_up_date >= today:
            follow_ups.append(
                AttentionItem(
                    severity="information",
                    title_key="executive.investors.upcoming_follow_up.title",
                    description_key="executive.investors.upcoming_follow_up.description",
                    metadata={"name": investor.full_name},
                    entity_type="investor",
                    entity_id=investor.id,
                    related_label=investor.full_name,
                    due_date=investor.next_follow_up_date,
                    link_module="investors",
                )
            )
    follow_ups.sort(key=lambda item: item.due_date or today)

    return ExecutiveInvestorOverviewResponse(
        by_status=[
            InvestorStatusCount(status=status, count=count)
            for status, count in sorted(status_counts.items())
        ],
        total_investment_capacity=capacity_by_currency,
        total_committed=total_committed,
        total_funded=total_funded,
        remaining_committed=remaining,
        upcoming_follow_ups=follow_ups[:10],
        by_investment_model=[
            InvestorModelCount(model=model, count=count)
            for model, count in sorted(model_counts.items())
        ],
        by_country=[
            InvestorCountryCount(country=country, count=count)
            for country, count in sorted(country_counts.items(), key=lambda item: -item[1])
        ],
    )


def build_project_portfolio(db: Session, filters: ExecutiveFilters) -> ExecutiveProjectPortfolioResponse:
    today = date.today()
    projects = db.scalars(_project_query(db, filters)).all()

    status_counts: dict[str, int] = {}
    total_units = 0
    units_under_development = 0
    total_dev_cost = Decimal("0")
    portfolio_value = Decimal("0")
    projected_sale = Decimal("0")
    equity_required = Decimal("0")
    equity_raised = Decimal("0")
    projected_profit = Decimal("0")

    critical_rows = db.scalars(
        select(PaymentObligation.project_id).where(
            PaymentObligation.priority == ObligationPriority.CRITICAL,
            PaymentObligation.status.not_in(
                [ObligationStatus.PAID, ObligationStatus.CANCELLED]
            ),
            PaymentObligation.project_id.is_not(None),
        )
    ).all()
    critical_project_ids = {row for row in critical_rows if row is not None}

    health_rows: list[ProjectHealthRow] = []
    for project in projects:
        status_counts[project.project_status.value] = (
            status_counts.get(project.project_status.value, 0) + 1
        )
        units = project.total_units or 0
        total_units += units
        if project.project_status in ACTIVE_PROJECT_STATUSES:
            units_under_development += units
        total_dev_cost += project.total_development_cost or Decimal("0")
        portfolio_value += project.current_project_value or Decimal("0")
        projected_sale += project.projected_sale_value or Decimal("0")
        equity_required += project.equity_required or Decimal("0")
        equity_raised += project.equity_raised or Decimal("0")
        projected_profit += project.projected_profit or Decimal("0")

        health_rows.append(
            ProjectHealthRow(
                project_id=project.id,
                project_name=project.project_name,
                status=project.project_status.value,
                units=project.total_units,
                completion_target=project.target_completion_date,
                development_cost=project.total_development_cost,
                current_value=project.current_project_value,
                equity_required=project.equity_required,
                equity_raised=project.equity_raised,
                funding_gap=_project_funding_gap(project),
                budget_variance=_budget_variance_for_project(db, project.id),
                health_status=compute_project_health(
                    db,
                    project,
                    today=today,
                    has_critical_obligation=project.id in critical_project_ids,
                ),
            )
        )

    return ExecutiveProjectPortfolioResponse(
        by_status=[
            ProjectStatusCount(status=status, count=count)
            for status, count in sorted(status_counts.items())
        ],
        total_units=total_units,
        units_under_development=units_under_development,
        total_development_cost=total_dev_cost,
        current_portfolio_value=portfolio_value,
        projected_sale_value=projected_sale,
        total_equity_required=equity_required,
        total_equity_raised=equity_raised,
        total_projected_profit=projected_profit,
        projects=health_rows,
    )


def _weekly_buckets(date_from: date, date_to: date) -> list[tuple[date, date]]:
    buckets: list[tuple[date, date]] = []
    cursor = date_from
    while cursor <= date_to:
        end = min(cursor + timedelta(days=6), date_to)
        buckets.append((cursor, end))
        cursor = end + timedelta(days=1)
    return buckets


def build_financial_overview(db: Session, filters: ExecutiveFilters) -> ExecutiveFinancialOverviewResponse:
    stats = compute_finance_stats(db)
    accounts = db.scalars(
        select(FinancialAccount).where(
            FinancialAccount.archived_at.is_(None),
            FinancialAccount.status == AccountStatus.ACTIVE,
        )
    ).all()

    cash_rows = [
        AccountCashRow(
            account_id=account.id,
            account_name=account.account_name,
            currency=account.currency,
            current_balance=account.current_balance,
            available_balance=account.available_balance,
        )
        for account in accounts
        if not filters.currency or account.currency == filters.currency.upper()
    ]

    txns = db.scalars(
        _txn_query(db, filters).where(
            FinanceTransaction.status == TransactionStatus.COMPLETED,
            FinanceTransaction.transaction_date >= filters.date_from,
            FinanceTransaction.transaction_date <= filters.date_to,
        )
    ).all()

    income = _sum_by_currency(
        [(t.currency, t.amount) for t in txns if t.transaction_type in INCOME_TRANSACTION_TYPES]
    )
    expenses = _sum_by_currency(
        [(t.currency, t.amount) for t in txns if t.transaction_type in OUTFLOW_TRANSACTION_TYPES]
    )
    investor_inflows = _sum_by_currency(
        [
            (t.currency, t.amount)
            for t in txns
            if t.transaction_type == TransactionType.INVESTMENT_INFLOW
        ]
    )
    loan_draws = _sum_by_currency(
        [(t.currency, t.amount) for t in txns if t.transaction_type == TransactionType.LOAN_DRAW]
    )
    loan_payments = _sum_by_currency(
        [(t.currency, t.amount) for t in txns if t.transaction_type == TransactionType.LOAN_PAYMENT]
    )

    if filters.currency:
        key = filters.currency.upper()
        for mapping in (
            income,
            expenses,
            investor_inflows,
            loan_draws,
            loan_payments,
            stats["available_cash"],
            stats["upcoming_payments"],
            stats["overdue_payments"],
            stats["total_project_budget"],
            stats["total_paid"],
        ):
            pass

    projects = db.scalars(_project_query(db, filters)).all()
    funding_gaps = [
        ProjectFundingGap(
            project_id=project.id,
            project_name=project.project_name,
            currency="USD",
            funding_gap=_project_funding_gap(project),
        )
        for project in projects
        if _project_funding_gap(project) > 0
    ]

    trend: list[CashFlowPoint] = []
    for start, end in _weekly_buckets(filters.date_from, filters.date_to):
        bucket_txns = [t for t in txns if start <= t.transaction_date <= end]
        inflows = _sum_by_currency(
            [(t.currency, t.amount) for t in bucket_txns if t.transaction_type in INCOME_TRANSACTION_TYPES]
        )
        outflows = _sum_by_currency(
            [(t.currency, t.amount) for t in bucket_txns if t.transaction_type in OUTFLOW_TRANSACTION_TYPES]
        )
        net: dict[str, Decimal] = {}
        currencies = set(inflows) | set(outflows)
        for currency in currencies:
            net[currency] = inflows.get(currency, Decimal("0")) - outflows.get(currency, Decimal("0"))
        trend.append(CashFlowPoint(period_start=start, period_end=end, inflows=inflows, outflows=outflows, net=net))

    available = stats["available_cash"]
    upcoming = stats["upcoming_payments"]
    overdue = stats["overdue_payments"]
    total_budget = stats["total_project_budget"]
    total_paid = stats["total_paid"]
    if filters.currency:
        key = filters.currency.upper()
        available = {key: available.get(key, Decimal("0"))}
        upcoming = {key: upcoming.get(key, Decimal("0"))}
        overdue = {key: overdue.get(key, Decimal("0"))}
        total_budget = {key: total_budget.get(key, Decimal("0"))}
        total_paid = {key: total_paid.get(key, Decimal("0"))}
        income = {key: income.get(key, Decimal("0"))}
        expenses = {key: expenses.get(key, Decimal("0"))}
        investor_inflows = {key: investor_inflows.get(key, Decimal("0"))}
        loan_draws = {key: loan_draws.get(key, Decimal("0"))}
        loan_payments = {key: loan_payments.get(key, Decimal("0"))}

    return ExecutiveFinancialOverviewResponse(
        cash_by_account=cash_rows,
        available_cash=available,
        income_in_period=income,
        expenses_in_period=expenses,
        investor_inflows=investor_inflows,
        loan_draws=loan_draws,
        loan_payments=loan_payments,
        upcoming_payments=upcoming,
        overdue_payments=overdue,
        total_project_budget=total_budget,
        total_paid=total_paid,
        funding_gap_by_project=funding_gaps,
        cash_flow_trend=trend,
    )


def _deadline_window(due: date, today: date) -> str:
    if due < today:
        return "overdue"
    if due <= today + timedelta(days=7):
        return "next_7_days"
    if due <= today + timedelta(days=30):
        return "next_30_days"
    return "later"


def build_deadlines(db: Session, filters: ExecutiveFilters) -> ExecutiveDeadlinesResponse:
    today = date.today()
    items: list[DeadlineItem] = []

    obligation_query = select(PaymentObligation).where(
        PaymentObligation.archived_at.is_(None),
        PaymentObligation.status.not_in([ObligationStatus.PAID, ObligationStatus.CANCELLED]),
    )
    if filters.project_id:
        obligation_query = obligation_query.where(PaymentObligation.project_id == filters.project_id)
    for obligation in db.scalars(obligation_query).all():
        if obligation.due_date is None:
            continue
        if filters.currency and obligation.currency != filters.currency.upper():
            continue
        items.append(
            DeadlineItem(
                deadline_type="payment_obligation",
                title=obligation.payee or obligation.description or "Payment",
                related_label=obligation.description,
                due_date=obligation.due_date,
                window=_deadline_window(obligation.due_date, today),
                entity_type="payment_obligation",
                entity_id=obligation.id,
                link_module="finance",
                link_query={"tab": "payments"},
            )
        )

    for investor in db.scalars(_investor_query(db, filters)).all():
        if investor.next_follow_up_date:
            items.append(
                DeadlineItem(
                    deadline_type="investor_follow_up",
                    title=investor.full_name,
                    related_label=investor.full_name,
                    due_date=investor.next_follow_up_date,
                    window=_deadline_window(investor.next_follow_up_date, today),
                    entity_type="investor",
                    entity_id=investor.id,
                    link_module="investors",
                )
            )

    for project in db.scalars(_project_query(db, filters)).all():
        if project.target_completion_date:
            items.append(
                DeadlineItem(
                    deadline_type="project_completion",
                    title=project.project_name,
                    related_label=project.project_name,
                    due_date=project.target_completion_date,
                    window=_deadline_window(project.target_completion_date, today),
                    entity_type="project",
                    entity_id=project.id,
                    link_module="projects",
                )
            )

    commitment_query = select(FundingCommitment)
    if filters.project_id:
        commitment_query = commitment_query.where(FundingCommitment.project_id == filters.project_id)
    for commitment in db.scalars(commitment_query).all():
        if commitment.target_funding_date:
            items.append(
                DeadlineItem(
                    deadline_type="funding_target",
                    title=str(commitment.committed_amount),
                    related_label=str(commitment.project_id),
                    due_date=commitment.target_funding_date,
                    window=_deadline_window(commitment.target_funding_date, today),
                    entity_type="funding_commitment",
                    entity_id=commitment.id,
                    link_module="finance",
                    link_query={"tab": "funding"},
                    metadata={"currency": commitment.currency},
                )
            )

    txn_query = _txn_query(db, filters).where(
        FinanceTransaction.status.in_(
            [TransactionStatus.PENDING, TransactionStatus.SCHEDULED, TransactionStatus.OVERDUE]
        ),
        FinanceTransaction.due_date.is_not(None),
    )
    for txn in db.scalars(txn_query).all():
        if txn.due_date is None:
            continue
        items.append(
            DeadlineItem(
                deadline_type="transaction_due",
                title=txn.description or txn.transaction_type.value,
                related_label=txn.description,
                due_date=txn.due_date,
                window=_deadline_window(txn.due_date, today),
                entity_type="transaction",
                entity_id=txn.id,
                link_module="finance",
                link_query={"tab": "transactions"},
            )
        )

    window_order = {"overdue": 0, "next_7_days": 1, "next_30_days": 2, "later": 3}
    items.sort(key=lambda item: (window_order[item.window], item.due_date))
    return ExecutiveDeadlinesResponse(items=items)


def build_activity_feed(
    db: Session,
    filters: ExecutiveFilters,
    user: "User | None" = None,
) -> ExecutiveActivityResponse:
    entries = list_recent_activity(
        db,
        user,
        limit=30,
        date_from=_dt_start(filters.date_from),
        date_to=_dt_end(filters.date_to),
    )
    items = [
        ActivityItem(
            id=entry.id,
            event_type=entry.event_type,
            action=entry.action.value,
            entity_type=entry.entity_type.value,
            entity_id=entry.entity_id,
            description_key=entry.description_key,
            metadata=entry.metadata_json,
            actor=entry.actor_name,
            actor_user_id=entry.actor_user_id,
            source=entry.source.value,
            entity_label=resolve_entity_label(entry.metadata_json),
            link_module=ENTITY_LINK_MODULES.get(entry.entity_type),
            is_demo=entry.is_demo,
            created_at=entry.created_at,
        )
        for entry in entries
    ]
    return ExecutiveActivityResponse(items=items)
