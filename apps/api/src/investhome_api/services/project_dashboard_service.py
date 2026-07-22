"""Projects portfolio dashboard aggregation (Sprint 10A2)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.finance import ProjectBudget
from investhome_api.models.inventory import (
    AvailabilityStatus,
    InventoryAsset,
    InventorySalesStatus,
    LeasingStatus,
    ReservationStatus,
)
from investhome_api.models.project import (
    ACTIVE_PROJECT_STATUSES,
    DevelopmentStage,
    Project,
    ProjectPriority,
    ProjectStatus,
    ProjectType,
)
from investhome_api.models.project_team import ProjectTeamMember, ProjectTeamMemberStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_dashboard import (
    ConstructionProjectRow,
    ConstructionSummary,
    DashboardFiltersApplied,
    DashboardMeta,
    FinancialSummary,
    LeasingSummary,
    PortfolioSummary,
    ProjectActivityItem,
    ProjectActivityListResponse,
    ProjectAlertListResponse,
    ProjectDashboardResponse,
    ProjectMilestoneListResponse,
    ProjectRiskLevel,
    SalesSummary,
    metric,
    unavailable,
)
from investhome_api.services.activity_service import list_activities
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_alerts import compute_project_risk, generate_portfolio_alerts
from investhome_api.services.project_milestones import derive_upcoming_milestones

ZERO = Decimal("0")


def _can_view_financial(user: User | None) -> bool:
    if user is None:
        return True
    return user_has_permission(user, "projects", "view_financial") or user_has_permission(
        user, "projects", "edit_financial"
    )


def _apply_project_filters(
    query,
    *,
    search: str | None,
    status: ProjectStatus | None,
    project_type: ProjectType | None,
    priority: ProjectPriority | None,
    development_stage: DevelopmentStage | None,
    project_manager_user_id: UUID | None,
    city: str | None,
    state: str | None,
    country: str | None,
    completion_year: int | None,
    include_archived: bool,
):
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    if status is not None:
        query = query.where(Project.project_status == status)
    if project_type is not None:
        query = query.where(Project.project_type == project_type)
    if priority is not None:
        query = query.where(Project.priority == priority)
    if development_stage is not None:
        query = query.where(Project.development_stage == development_stage)
    if project_manager_user_id is not None:
        query = query.where(Project.project_manager_user_id == project_manager_user_id)
    if city:
        query = query.where(Project.city.ilike(f"%{city.strip()}%"))
    if state:
        query = query.where(Project.state.ilike(f"%{state.strip()}%"))
    if country:
        query = query.where(Project.country.ilike(f"%{country.strip()}%"))
    if completion_year is not None:
        query = query.where(func.extract("year", Project.target_completion_date) == completion_year)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Project.project_code.ilike(pattern),
                Project.project_name.ilike(pattern),
                Project.city.ilike(pattern),
                Project.address.ilike(pattern),
            )
        )
    return query


def _load_filtered_projects(
    db: Session,
    *,
    search: str | None = None,
    status: ProjectStatus | None = None,
    project_type: ProjectType | None = None,
    priority: ProjectPriority | None = None,
    development_stage: DevelopmentStage | None = None,
    project_manager_user_id: UUID | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    completion_year: int | None = None,
    include_archived: bool = False,
) -> list[Project]:
    query = select(Project)
    query = _apply_project_filters(
        query,
        search=search,
        status=status,
        project_type=project_type,
        priority=priority,
        development_stage=development_stage,
        project_manager_user_id=project_manager_user_id,
        city=city,
        state=state,
        country=country,
        completion_year=completion_year,
        include_archived=include_archived,
    )
    return list(db.scalars(query.order_by(Project.updated_at.desc())).all())


def _budget_maps(
    db: Session, project_ids: list[UUID]
) -> tuple[dict[UUID, Decimal], dict[UUID, Decimal]]:
    """Budget spent/total maps for dashboard utilization.

    Source precedence (never sum both):
      1. NORMALIZED — when posted bills or approved commitments exist for a project,
         spent = actual cost (posted bill net+tax), total = current approved budget lines.
      2. LEGACY — otherwise use ProjectBudget.paid_amount / revised_budget.
    """
    spent: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    totals: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    if not project_ids:
        return spent, totals

    from investhome_api.models.project_budget import (
        BudgetVersionStatus,
        ProjectBudgetLine,
        ProjectBudgetVersion,
    )
    from investhome_api.services.project_cost_service import (
        project_cost_totals,
        project_has_normalized_cost_data,
    )

    normalized_ids: set[UUID] = set()
    for project_id in project_ids:
        if project_has_normalized_cost_data(db, project_id):
            cost = project_cost_totals(db, project_id)
            spent[project_id] = cost["actual_cost"]
            version = db.scalars(
                select(ProjectBudgetVersion).where(
                    ProjectBudgetVersion.project_id == project_id,
                    ProjectBudgetVersion.is_current.is_(True),
                    ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
                )
            ).first()
            if version is not None:
                totals[project_id] = Decimal(
                    str(
                        db.scalar(
                            select(func.coalesce(func.sum(ProjectBudgetLine.current_budget), 0)).where(
                                ProjectBudgetLine.budget_version_id == version.id,
                                ProjectBudgetLine.is_active.is_(True),
                                ProjectBudgetLine.is_summary.is_(False),
                            )
                        )
                        or 0
                    )
                )
            normalized_ids.add(project_id)

    legacy_ids = [project_id for project_id in project_ids if project_id not in normalized_ids]
    if legacy_ids:
        rows = db.execute(
            select(
                ProjectBudget.project_id,
                func.coalesce(func.sum(ProjectBudget.paid_amount), 0),
                func.coalesce(
                    func.sum(
                        func.coalesce(ProjectBudget.revised_budget, ProjectBudget.original_budget)
                    ),
                    0,
                ),
            )
            .where(ProjectBudget.project_id.in_(legacy_ids))
            .group_by(ProjectBudget.project_id)
        ).all()
        for project_id, paid, budget in rows:
            spent[project_id] = Decimal(str(paid))
            totals[project_id] = Decimal(str(budget))
    return spent, totals


def _team_map(db: Session, project_ids: list[UUID]) -> dict[UUID, list[ProjectTeamMember]]:
    mapping: dict[UUID, list[ProjectTeamMember]] = defaultdict(list)
    if not project_ids:
        return mapping
    members = db.scalars(
        select(ProjectTeamMember).where(ProjectTeamMember.project_id.in_(project_ids))
    ).all()
    for member in members:
        mapping[member.project_id].append(member)
    return mapping


def _inventory_counts(
    db: Session, project_ids: list[UUID]
) -> dict[str, int]:
    empty = {
        "available": 0,
        "reserved": 0,
        "under_contract": 0,
        "sold": 0,
        "leased": 0,
        "vacant": 0,
        "total_assets": 0,
    }
    if not project_ids:
        return empty

    row = db.execute(
        select(
            func.count(InventoryAsset.id),
            func.sum(
                case(
                    (InventoryAsset.availability_status == AvailabilityStatus.AVAILABLE, 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (
                        InventoryAsset.reservation_status.in_(
                            [ReservationStatus.SOFT_HOLD, ReservationStatus.CONFIRMED]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (InventoryAsset.sales_status == InventorySalesStatus.UNDER_CONTRACT, 1),
                    else_=0,
                )
            ),
            func.sum(
                case((InventoryAsset.sales_status == InventorySalesStatus.SOLD, 1), else_=0)
            ),
            func.sum(
                case((InventoryAsset.leasing_status == LeasingStatus.LEASED, 1), else_=0)
            ),
            func.sum(
                case((InventoryAsset.leasing_status == LeasingStatus.VACANT, 1), else_=0)
            ),
        ).where(
            InventoryAsset.project_id.in_(project_ids),
            InventoryAsset.archived_at.is_(None),
        )
    ).one()
    return {
        "total_assets": int(row[0] or 0),
        "available": int(row[1] or 0),
        "reserved": int(row[2] or 0),
        "under_contract": int(row[3] or 0),
        "sold": int(row[4] or 0),
        "leased": int(row[5] or 0),
        "vacant": int(row[6] or 0),
    }


def _completion_bucket(value: Decimal | None) -> str:
    if value is None:
        return "unknown"
    amount = float(value)
    if amount < 25:
        return "0-24"
    if amount < 50:
        return "25-49"
    if amount < 75:
        return "50-74"
    if amount < 100:
        return "75-99"
    return "100"


def build_dashboard(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    status: ProjectStatus | None = None,
    project_type: ProjectType | None = None,
    priority: ProjectPriority | None = None,
    development_stage: DevelopmentStage | None = None,
    project_manager_user_id: UUID | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    completion_year: int | None = None,
    include_archived: bool = False,
    milestone_days: int = 30,
    activity_limit: int = 20,
    alert_limit: int = 50,
) -> ProjectDashboardResponse:
    today = date.today()
    financial_access = _can_view_financial(user)
    projects = _load_filtered_projects(
        db,
        search=search,
        status=status,
        project_type=project_type,
        priority=priority,
        development_stage=development_stage,
        project_manager_user_id=project_manager_user_id,
        city=city,
        state=state,
        country=country,
        completion_year=completion_year,
        include_archived=include_archived,
    )
    project_ids = [project.id for project in projects]
    warnings: list[str] = []
    completeness: dict[str, str] = {}

    inventory = _inventory_counts(db, project_ids)
    if inventory["total_assets"] == 0:
        warnings.append("No linked inventory assets for the filtered projects.")
        completeness["inventory"] = "missing"
    else:
        completeness["inventory"] = "partial"

    budget_spent_map, budget_total_map = _budget_maps(db, project_ids)
    team_map = _team_map(db, project_ids)

    status_distribution: dict[str, int] = defaultdict(int)
    stage_distribution: dict[str, int] = defaultdict(int)
    priority_distribution: dict[str, int] = defaultdict(int)
    completion_distribution: dict[str, int] = defaultdict(int)

    total_units = 0
    residential_units = 0
    commercial_units = 0
    completion_values: list[Decimal] = []
    delayed = 0
    at_risk = 0
    without_schedule = 0
    without_progress = 0
    on_schedule = 0
    days_remaining_values: list[int] = []
    construction_rows: list[ConstructionProjectRow] = []

    portfolio_value = ZERO
    total_dev_cost = ZERO
    construction_budget = ZERO
    soft_cost = ZERO
    land_cost = ZERO
    equity_raised = ZERO
    equity_required = ZERO
    debt = ZERO
    expected_revenue = ZERO
    expected_profit = ZERO
    budget_spent_total = ZERO
    budget_total_from_lines = ZERO

    for project in projects:
        status_distribution[project.project_status.value] += 1
        if project.development_stage is not None:
            stage_distribution[project.development_stage.value] += 1
        priority_distribution[project.priority.value] += 1
        completion_distribution[_completion_bucket(project.completion_percentage)] += 1

        total_units += project.total_units or 0
        residential_units += project.residential_units or 0
        commercial_units += project.commercial_units or 0

        if project.completion_percentage is not None:
            completion_values.append(project.completion_percentage)
        else:
            without_progress += 1

        spent = budget_spent_map.get(project.id, ZERO)
        line_budget = budget_total_map.get(project.id, ZERO)
        project_budget = (
            project.construction_budget
            or project.total_development_cost
            or (line_budget if line_budget > 0 else None)
        )
        utilization = None
        if project_budget and project_budget > 0:
            utilization = (spent / project_budget) * Decimal("100")

        team_count = len(
            [
                member
                for member in team_map.get(project.id, [])
                if member.status == ProjectTeamMemberStatus.ACTIVE
            ]
        )
        risk = compute_project_risk(
            project,
            today=today,
            team_count=team_count,
            budget_utilization=utilization,
        )
        if risk in {ProjectRiskLevel.HIGH, ProjectRiskLevel.CRITICAL}:
            at_risk += 1

        is_delayed = False
        days_delayed = None
        days_remaining = None
        if project.target_completion_date is None:
            without_schedule += 1
        else:
            days_remaining = (project.target_completion_date - today).days
            days_remaining_values.append(days_remaining)
            if (
                days_remaining < 0
                and project.project_status
                not in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}
            ):
                is_delayed = True
                delayed += 1
                days_delayed = abs(days_remaining)
            elif days_remaining >= 0:
                on_schedule += 1

        if project.project_status in ACTIVE_PROJECT_STATUSES or project.project_status == ProjectStatus.CONSTRUCTION:
            construction_rows.append(
                ConstructionProjectRow(
                    project_id=project.id,
                    project_name=project.project_name,
                    status=project.project_status.value,
                    development_stage=(
                        project.development_stage.value if project.development_stage else None
                    ),
                    completion_percentage=project.completion_percentage,
                    estimated_start_date=project.start_date,
                    actual_start_date=project.actual_start_date,
                    estimated_completion_date=project.target_completion_date,
                    actual_completion_date=project.actual_completion_date,
                    days_remaining=days_remaining,
                    days_delayed=days_delayed,
                    is_delayed=is_delayed,
                    risk=risk,
                    next_milestone=(
                        f"Complete by {project.target_completion_date.isoformat()}"
                        if project.target_completion_date
                        else None
                    ),
                )
            )

        if financial_access:
            portfolio_value += project.current_project_value or ZERO
            total_dev_cost += project.total_development_cost or ZERO
            construction_budget += project.construction_budget or ZERO
            soft_cost += project.soft_cost_budget or ZERO
            land_cost += project.land_cost or ZERO
            equity_raised += project.equity_raised or ZERO
            equity_required += project.equity_required or ZERO
            debt += project.debt_amount or ZERO
            expected_revenue += project.projected_revenue or ZERO
            expected_profit += project.projected_profit or ZERO
            budget_spent_total += spent
            budget_total_from_lines += line_budget

    construction_rows.sort(
        key=lambda row: (
            0 if row.is_delayed else 1,
            -(float(row.completion_percentage) if row.completion_percentage is not None else -1),
        )
    )

    avg_completion = (
        sum(completion_values, ZERO) / Decimal(len(completion_values))
        if completion_values
        else None
    )
    avg_days_remaining = (
        Decimal(sum(days_remaining_values)) / Decimal(len(days_remaining_values))
        if days_remaining_values
        else None
    )

    def inventory_metric(key: str):
        if inventory["total_assets"] == 0:
            return unavailable("No linked inventory assets")
        return metric(inventory[key])

    budget_remaining = None
    budget_utilization = None
    effective_budget = construction_budget if construction_budget > 0 else total_dev_cost
    if financial_access and effective_budget > 0:
        budget_remaining = effective_budget - budget_spent_total
        budget_utilization = (budget_spent_total / effective_budget) * Decimal("100")
    elif financial_access and budget_total_from_lines > 0:
        budget_remaining = budget_total_from_lines - budget_spent_total
        budget_utilization = (budget_spent_total / budget_total_from_lines) * Decimal("100")

    planning_statuses = {
        ProjectStatus.PIPELINE,
        ProjectStatus.DUE_DILIGENCE,
        ProjectStatus.ACQUISITION,
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.PERMITTING,
    }

    portfolio = PortfolioSummary(
        total_projects=len([p for p in projects if p.archived_at is None]),
        active_projects=sum(1 for p in projects if p.project_status in ACTIVE_PROJECT_STATUSES),
        planning_projects=sum(1 for p in projects if p.project_status in planning_statuses),
        under_construction_projects=sum(
            1 for p in projects if p.project_status == ProjectStatus.CONSTRUCTION
        ),
        completed_projects=sum(1 for p in projects if p.project_status == ProjectStatus.COMPLETED),
        on_hold_projects=sum(1 for p in projects if p.project_status == ProjectStatus.ON_HOLD),
        cancelled_projects=sum(1 for p in projects if p.project_status == ProjectStatus.CANCELLED),
        archived_projects=sum(1 for p in projects if p.archived_at is not None),
        total_units=total_units,
        residential_units=residential_units,
        commercial_units=commercial_units,
        available_units=inventory_metric("available"),
        reserved_units=inventory_metric("reserved"),
        under_contract_units=inventory_metric("under_contract"),
        sold_units=inventory_metric("sold"),
        occupied_units=inventory_metric("leased"),
        vacant_units=inventory_metric("vacant"),
        portfolio_value=metric(portfolio_value) if financial_access else unavailable("Restricted"),
        total_development_budget=metric(total_dev_cost)
        if financial_access
        else unavailable("Restricted"),
        construction_budget=metric(construction_budget)
        if financial_access
        else unavailable("Restricted"),
        budget_spent=metric(budget_spent_total) if financial_access else unavailable("Restricted"),
        budget_remaining=metric(budget_remaining)
        if financial_access and budget_remaining is not None
        else unavailable("Restricted" if not financial_access else "No budget baseline"),
        budget_utilization_percentage=metric(budget_utilization)
        if financial_access and budget_utilization is not None
        else unavailable("Restricted" if not financial_access else "No budget baseline"),
        average_project_completion=metric(avg_completion)
        if avg_completion is not None
        else unavailable("No completion percentages recorded"),
        projects_delayed=delayed,
        projects_at_risk=at_risk,
        status_distribution=dict(status_distribution),
        stage_distribution=dict(stage_distribution),
        priority_distribution=dict(priority_distribution),
    )

    financials = None
    if financial_access:
        margin = None
        if expected_revenue > 0:
            margin = (expected_profit / expected_revenue) * Decimal("100")
        from investhome_api.services.project_executive_finance_service import (
            build_portfolio_executive_rollup,
        )

        attention_items, upcoming_cash, ai_finance, exec_rollup = build_portfolio_executive_rollup(
            db, projects, today=today
        )

        financials = FinancialSummary(
            expected_revenue=exec_rollup["expected_revenue"]
            if exec_rollup["expected_revenue"].available
            else metric(expected_revenue),
            expected_profit=exec_rollup["expected_profit"]
            if exec_rollup["expected_profit"].available
            else metric(expected_profit),
            current_portfolio_value=metric(portfolio_value),
            total_development_cost=metric(total_dev_cost),
            construction_budget=metric(construction_budget),
            soft_cost_budget=metric(soft_cost),
            land_cost=metric(land_cost),
            equity_raised=metric(equity_raised),
            equity_required=metric(equity_required),
            debt_outstanding=metric(debt),
            budget_spent=metric(budget_spent_total),
            budget_remaining=metric(budget_remaining)
            if budget_remaining is not None
            else unavailable("No budget baseline"),
            budget_utilization_percentage=metric(budget_utilization)
            if budget_utilization is not None
            else unavailable("No budget baseline"),
            realized_revenue=unavailable("No linked closed-sale cash ledger"),
            remaining_revenue=unavailable("No linked closed-sale cash ledger"),
            realized_profit=unavailable("No linked closed-sale cash ledger"),
            roi=unavailable("Insufficient cash-flow history"),
            irr=unavailable("Insufficient cash-flow history"),
            equity_multiple=unavailable("Insufficient cash-flow history"),
            average_profit_margin=metric(margin)
            if margin is not None
            else unavailable("Expected revenue not set"),
            funding_gap=exec_rollup["funding_gap"],
            cash_position=exec_rollup["cash_position"],
            forecast_cost=exec_rollup["forecast_cost"],
            need_30_days=exec_rollup["need_30_days"],
            need_60_days=exec_rollup["need_60_days"],
            need_90_days=exec_rollup["need_90_days"],
            projects_requiring_attention=[
                item.model_dump(mode="json") for item in attention_items
            ],
            upcoming_large_cash_events=[item.model_dump(mode="json") for item in upcoming_cash],
            ai_finance_summary=ai_finance.model_dump(mode="json"),
        )
        completeness["financials"] = "executive_rollup"
    else:
        completeness["financials"] = "restricted"

    sold = inventory["sold"]
    available = inventory["available"]
    under_contract = inventory["under_contract"]
    reserved = inventory["reserved"]
    sales_den = sold + available + under_contract + reserved
    sales_rate = (
        Decimal(sold) / Decimal(sales_den) * Decimal("100") if sales_den > 0 else None
    )
    sales = SalesSummary(
        available_units=inventory_metric("available"),
        reserved_units=inventory_metric("reserved"),
        under_contract_units=inventory_metric("under_contract"),
        sold_units=inventory_metric("sold"),
        cancelled_units=unavailable("Inventory sales cancelled status not tracked as units"),
        sales_rate=metric(sales_rate)
        if sales_rate is not None
        else unavailable("No linked inventory assets"),
        gross_sales_volume=unavailable("Unit sale prices not aggregated in this endpoint"),
        by_status={
            "available": available,
            "reserved": reserved,
            "under_contract": under_contract,
            "sold": sold,
        }
        if inventory["total_assets"] > 0
        else {},
    )
    completeness["sales"] = "inventory_status" if inventory["total_assets"] else "missing"

    leased = inventory["leased"]
    vacant = inventory["vacant"]
    lease_den = leased + vacant
    occupancy = (
        Decimal(leased) / Decimal(lease_den) * Decimal("100") if lease_den > 0 else None
    )
    leasing = LeasingSummary(
        occupied_units=inventory_metric("leased"),
        vacant_units=inventory_metric("vacant"),
        occupancy_rate=metric(occupancy)
        if occupancy is not None
        else unavailable("No linked leaseable inventory"),
        leases_expiring_30_days=unavailable("No lease contract entity"),
        leases_expiring_60_days=unavailable("No lease contract entity"),
        leases_expiring_90_days=unavailable("No lease contract entity"),
        monthly_rental_income=unavailable("No lease contract entity"),
        by_status={"leased": leased, "vacant": vacant} if inventory["total_assets"] else {},
    )
    completeness["leasing"] = "inventory_proxy" if inventory["total_assets"] else "missing"
    warnings.append("Leasing occupancy uses inventory leasing_status (no lease contracts).")

    construction = ConstructionSummary(
        average_completion_percentage=metric(avg_completion)
        if avg_completion is not None
        else unavailable("No completion percentages recorded"),
        projects_on_schedule=on_schedule,
        projects_delayed=delayed,
        projects_without_schedule=without_schedule,
        projects_without_progress=without_progress,
        average_days_remaining=metric(avg_days_remaining)
        if avg_days_remaining is not None
        else unavailable("No estimated completion dates"),
        completion_distribution=dict(completion_distribution),
        stage_distribution=dict(stage_distribution),
        projects=construction_rows[:25],
    )

    milestones = derive_upcoming_milestones(projects, today=today, days=milestone_days)
    alert_budget_totals: dict[UUID, Decimal] = {}
    for project in projects:
        alert_budget_totals[project.id] = (
            project.construction_budget
            or project.total_development_cost
            or budget_total_map.get(project.id, ZERO)
            or ZERO
        )
    alerts = generate_portfolio_alerts(
        projects,
        today=today,
        team_by_project=team_map,
        budget_spent_by_project=budget_spent_map,
        budget_total_by_project=alert_budget_totals,
        limit=alert_limit,
        db=db,
    )

    activity_items, _ = list_activities(
        db,
        user,
        entity_type=ActivityEntityType.PROJECT,
        page=1,
        page_size=activity_limit,
    )
    project_name_by_id = {project.id: project.project_name for project in projects}
    # Also load names for activity on projects outside filter set
    missing_ids = [
        entry.entity_id
        for entry in activity_items
        if entry.entity_id and entry.entity_id not in project_name_by_id
    ]
    if missing_ids:
        for project in db.scalars(select(Project).where(Project.id.in_(missing_ids))).all():
            project_name_by_id[project.id] = project.project_name

    activity = [
        ProjectActivityItem(
            id=entry.id,
            project_id=entry.entity_id,
            project_name=project_name_by_id.get(entry.entity_id) if entry.entity_id else None,
            type=entry.action.value if entry.action else "updated",
            title=entry.description_key,
            description=None,
            actor=entry.actor_name,
            created_at=entry.created_at,
            metadata=entry.metadata_json or {},
            action_url=(
                f"/dashboard/projects?id={entry.entity_id}" if entry.entity_id else None
            ),
        )
        for entry in activity_items
    ]

    # When filters are applied, keep activity scoped to filtered projects when possible
    if any(
        [
            search,
            status,
            project_type,
            priority,
            development_stage,
            project_manager_user_id,
            city,
            state,
            country,
            completion_year,
        ]
    ):
        filtered_ids = set(project_ids)
        activity = [
            item for item in activity if item.project_id is None or item.project_id in filtered_ids
        ]

    meta = DashboardMeta(
        generated_at=datetime.now(UTC),
        currency_mode="project_native",
        financial_access=financial_access,
        applied_filters=DashboardFiltersApplied(
            status=status.value if status else None,
            project_type=project_type.value if project_type else None,
            priority=priority.value if priority else None,
            development_stage=development_stage.value if development_stage else None,
            project_manager_user_id=project_manager_user_id,
            city=city,
            state=state,
            country=country,
            completion_year=completion_year,
            include_archived=include_archived,
            search=search,
        ),
        data_completeness=completeness,
        partial_data_warnings=warnings,
    )

    return ProjectDashboardResponse(
        portfolio=portfolio,
        financials=financials,
        construction=construction,
        sales=sales,
        leasing=leasing,
        milestones=milestones,
        alerts=alerts,
        activity=activity,
        meta=meta,
    )


def list_milestones(
    db: Session,
    *,
    days: int = 30,
    project_id: UUID | None = None,
    include_archived: bool = False,
) -> ProjectMilestoneListResponse:
    projects = _load_filtered_projects(db, include_archived=include_archived)
    items = derive_upcoming_milestones(projects, days=days, project_id=project_id)
    return ProjectMilestoneListResponse(items=items, total=len(items))


def list_critical_items(
    db: Session,
    user: User,
    *,
    include_archived: bool = False,
    limit: int = 50,
) -> ProjectAlertListResponse:
    projects = _load_filtered_projects(db, include_archived=include_archived)
    project_ids = [project.id for project in projects]
    spent, totals = _budget_maps(db, project_ids)
    team_map = _team_map(db, project_ids)
    budget_totals = {}
    for project in projects:
        budget_totals[project.id] = (
            project.construction_budget
            or project.total_development_cost
            or totals.get(project.id, ZERO)
            or ZERO
        )
    items = generate_portfolio_alerts(
        projects,
        team_by_project=team_map,
        budget_spent_by_project=spent,
        budget_total_by_project=budget_totals,
        limit=limit,
        db=db,
    )
    if not _can_view_financial(user):
        items = [item for item in items if item.category.value != "budget"]
    return ProjectAlertListResponse(items=items, total=len(items))


def list_recent_activity(
    db: Session,
    user: User,
    *,
    limit: int = 20,
) -> ProjectActivityListResponse:
    entries, total = list_activities(
        db,
        user,
        entity_type=ActivityEntityType.PROJECT,
        page=1,
        page_size=limit,
    )
    project_ids = [entry.entity_id for entry in entries if entry.entity_id]
    names: dict[UUID, str] = {}
    if project_ids:
        for project in db.scalars(select(Project).where(Project.id.in_(project_ids))).all():
            names[project.id] = project.project_name
    items = [
        ProjectActivityItem(
            id=entry.id,
            project_id=entry.entity_id,
            project_name=names.get(entry.entity_id) if entry.entity_id else None,
            type=entry.action.value if entry.action else "updated",
            title=entry.description_key,
            actor=entry.actor_name,
            created_at=entry.created_at,
            metadata=entry.metadata_json or {},
            action_url=(
                f"/dashboard/projects?id={entry.entity_id}" if entry.entity_id else None
            ),
        )
        for entry in entries
    ]
    return ProjectActivityListResponse(items=items, total=total)
