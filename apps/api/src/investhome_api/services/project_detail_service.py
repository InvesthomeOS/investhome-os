"""Project detail workspace aggregation (Sprint 10A3)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.finance import CommitmentStatus, FundingCommitment, ProjectBudget
from investhome_api.models.project_budget import (
    BudgetAudience,
    BudgetVersionStatus,
    ProjectBudgetLine,
    ProjectBudgetVersion,
)
from investhome_api.models.inventory import (
    AvailabilityStatus,
    Building,
    Floor,
    InventoryAsset,
    InventorySalesStatus,
    SalesMarket,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project, ProjectStatus
from investhome_api.models.project_team import ProjectTeamMember, ProjectTeamMemberStatus
from investhome_api.models.sales import OpportunityProject, SalesOpportunity
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.schemas.project import FINANCIAL_FIELDS
from investhome_api.schemas.project_dashboard import (
    ProjectActivityItem,
    ProjectActivityListResponse,
    ProjectAlertListResponse,
    ProjectMilestoneListResponse,
    metric,
    unavailable,
)
from investhome_api.schemas.project_detail import (
    ProjectConstructionResponse,
    ProjectDetailNavigationItem,
    ProjectDetailPermissions,
    ProjectDetailShell,
    ProjectDirectoryUser,
    ProjectDirectoryUserListResponse,
    ProjectDocumentsResponse,
    ProjectFinancialsResponse,
    ProjectInvestorsResponse,
    ProjectLeasingResponse,
    ProjectOverviewResponse,
    ProjectSalesResponse,
    ProjectScheduleResponse,
    ProjectUnitsResponse,
)
from investhome_api.services import project_service as project_svc
from investhome_api.services.activity_service import list_activities
from investhome_api.services.document_service import build_list_query, enrich_response
from investhome_api.services.operational_child_scope import operational_child_clause
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_alerts import compute_project_risk, generate_alerts_for_project
from investhome_api.services.inventory.phase_identity import operational_phase_id
from investhome_api.services.project_dashboard_service import _budget_maps, _inventory_counts
from investhome_api.services.project_milestones import derive_milestones_for_project

ZERO = Decimal("0")

TAB_KEYS = (
    "overview",
    "financials",
    "schedule",
    "construction",
    "units",
    "sales",
    "leasing",
    "investors",
    "documents",
    "team",
    "activity",
)


def _can_view_financial(user: User) -> bool:
    return user_has_permission(user, "projects", "view_financial") or user_has_permission(
        user, "projects", "edit_financial"
    )


def _perm(user: User, action: str) -> bool:
    return user_has_permission(user, "projects", action)


def _load_project(db: Session, project_id: UUID) -> Project:
    return project_svc.get_project_or_404(db, project_id, include_archived=True)


def _days_remaining(project: Project, today: date) -> int | None:
    if project.target_completion_date is None:
        return None
    return (project.target_completion_date - today).days


def _is_delayed(project: Project, today: date) -> bool:
    days = _days_remaining(project, today)
    if days is None:
        return False
    if project.project_status in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}:
        return False
    return days < 0


def _budget_utilization(
    project: Project, spent: Decimal, line_total: Decimal
) -> Decimal | None:
    baseline = project.construction_budget or project.total_development_cost
    if baseline is None or baseline <= 0:
        baseline = line_total if line_total > 0 else None
    if baseline is None or baseline <= 0:
        return None
    return (spent / baseline) * Decimal("100")


def _financial_metric(value: Decimal | None, *, access: bool, reason: str = "No data"):
    if not access:
        return unavailable("Restricted")
    if value is None:
        return unavailable(reason)
    return metric(value)


def build_shell(db: Session, user: User, project_id: UUID) -> ProjectDetailShell:
    project = _load_project(db, project_id)
    today = date.today()
    financial_access = _can_view_financial(user)
    project_response = project_svc.to_project_response(db, project, user=user, include_team=True)

    spent_map, total_map = _budget_maps(db, [project.id])
    spent = spent_map.get(project.id, ZERO)
    line_total = total_map.get(project.id, ZERO)
    utilization = _budget_utilization(project, spent, line_total)

    team_orm = list(
        db.scalars(
            select(ProjectTeamMember).where(ProjectTeamMember.project_id == project.id)
        ).all()
    )
    active_team = [m for m in team_orm if m.status == ProjectTeamMemberStatus.ACTIVE]
    risk = compute_project_risk(
        project,
        today=today,
        team_count=len(active_team),
        budget_utilization=utilization,
    )
    alerts = generate_alerts_for_project(
        project,
        today=today,
        team_members=team_orm,
        budget_spent=spent,
        budget_total=line_total
        if line_total > 0
        else (project.construction_budget or project.total_development_cost),
        db=db,
    )
    milestones = derive_milestones_for_project(project, today=today, window_days=90)
    inventory = _inventory_counts(db, [project.id])

    docs, doc_total = build_list_query(
        db, user, project_id=project.id, page=1, page_size=1
    )
    del docs

    can_view_team = _perm(user, "view_team") or _perm(user, "manage_team")
    can_view_docs = user_has_permission(user, "documents", "view")
    can_view_activity = user_has_permission(user, "activity", "view")
    can_view_inventory = user_has_permission(user, "inventory", "view") or _perm(user, "view")
    can_view_sales = user_has_permission(user, "sales", "view") or _perm(user, "view")
    can_view_investors = user_has_permission(user, "investors", "view") or _perm(user, "view")

    visibility = {
        "overview": True,
        "financials": financial_access,
        "schedule": True,
        "construction": True,
        "units": can_view_inventory,
        "sales": can_view_sales,
        "leasing": can_view_inventory,
        "investors": can_view_investors,
        "documents": can_view_docs,
        "team": can_view_team,
        "activity": can_view_activity,
    }

    navigation = [
        ProjectDetailNavigationItem(
            key=key,
            href=f"/dashboard/projects/{project.id}/{key}",
            visible=visibility[key],
        )
        for key in TAB_KEYS
    ]

    completeness: dict[str, str] = {
        "schedule": "present" if project.target_completion_date else "missing",
        "progress": "present" if project.completion_percentage is not None else "missing",
        "inventory": "present" if inventory["total_assets"] > 0 else "missing",
        "team": "present" if active_team else "missing",
        "documents": "present" if doc_total > 0 else "missing",
        "financials": "present"
        if financial_access
        and (
            project.total_development_cost is not None
            or project.construction_budget is not None
        )
        else ("restricted" if not financial_access else "missing"),
    }

    return ProjectDetailShell(
        project=project_response,
        permissions=ProjectDetailPermissions(
            can_edit=_perm(user, "update"),
            can_archive=_perm(user, "archive"),
            can_restore=_perm(user, "restore"),
            can_manage_status=_perm(user, "manage_status"),
            can_view_financial=financial_access,
            can_edit_financial=_perm(user, "edit_financial"),
            can_view_team=can_view_team,
            can_manage_team=_perm(user, "manage_team"),
            can_export=_perm(user, "export"),
        ),
        navigation=navigation,
        risk=risk,
        financial_access=financial_access,
        alerts_count=len(alerts),
        milestones_count=len(milestones),
        team_count=len(active_team),
        documents_count=doc_total,
        units_count=inventory["total_assets"],
        data_completeness=completeness,
    )


def get_overview(db: Session, user: User, project_id: UUID) -> ProjectOverviewResponse:
    shell = build_shell(db, user, project_id)
    project = _load_project(db, project_id)
    today = date.today()
    warnings: list[str] = []

    spent_map, total_map = _budget_maps(db, [project.id])
    spent = spent_map.get(project.id, ZERO)
    line_total = total_map.get(project.id, ZERO)
    utilization = _budget_utilization(project, spent, line_total)
    inventory = _inventory_counts(db, [project.id])
    if inventory["total_assets"] == 0:
        warnings.append("No inventory units linked to this project.")

    team = project_svc.list_team_members(db, project.id)
    milestones = derive_milestones_for_project(project, today=today, window_days=90)
    alerts = generate_alerts_for_project(
        project,
        today=today,
        team_members=list(
            db.scalars(
                select(ProjectTeamMember).where(ProjectTeamMember.project_id == project.id)
            ).all()
        ),
        budget_spent=spent,
        budget_total=line_total
        if line_total > 0
        else (project.construction_budget or project.total_development_cost),
        db=db,
    )

    activity = list_recent_activity(db, user, project_id, limit=10)
    docs_resp = get_documents(db, user, project_id, page=1, page_size=5)

    days_remaining = _days_remaining(project, today)
    delayed = _is_delayed(project, today)

    financial_snapshot = None
    if shell.financial_access:
        remaining = None
        baseline = project.construction_budget or project.total_development_cost
        if baseline is not None:
            remaining = baseline - spent
        financial_snapshot = {
            "total_development_budget": _financial_metric(
                project.total_development_cost, access=True
            ),
            "budget_used": metric(spent),
            "budget_remaining": _financial_metric(remaining, access=True, reason="No budget baseline"),
            "budget_utilization": _financial_metric(
                utilization, access=True, reason="No budget baseline"
            ),
            "expected_revenue": _financial_metric(project.projected_revenue, access=True),
            "expected_profit": _financial_metric(project.projected_profit, access=True),
            "current_value": _financial_metric(project.current_project_value, access=True),
        }

    def inv_metric(key: str):
        if inventory["total_assets"] == 0:
            return unavailable("No linked inventory assets")
        return metric(inventory[key])

    return ProjectOverviewResponse(
        shell=shell,
        snapshot={
            "project_type": project.project_type.value,
            "development_type": project.development_type.value,
            "development_stage": (
                project.development_stage.value if project.development_stage else None
            ),
            "priority": project.priority.value,
            "address": project.address,
            "city": project.city,
            "state": project.state,
            "country": project.country,
            "timezone": project.timezone,
            "gross_square_feet": project.gross_square_feet,
            "net_sellable_square_feet": project.net_sellable_square_feet,
            "lot_size": project.lot_size,
            "residential_units": project.residential_units,
            "commercial_units": project.commercial_units,
            "total_units": project.total_units,
            "ownership_entity": project.ownership_entity,
            "acquisition_date": project.acquisition_date,
            "start_date": project.start_date,
            "actual_start_date": project.actual_start_date,
            "target_completion_date": project.target_completion_date,
            "actual_completion_date": project.actual_completion_date,
            "estimated_closing_date": project.estimated_closing_date,
            "completion_percentage": project.completion_percentage,
            "status": project.project_status.value,
            "risk": shell.risk.value,
        },
        schedule={
            "days_remaining": days_remaining,
            "is_delayed": delayed,
            "days_delayed": abs(days_remaining) if delayed and days_remaining is not None else None,
            "estimated_completion": project.target_completion_date,
            "estimated_start": project.start_date,
            "actual_start": project.actual_start_date,
        },
        financial_snapshot=financial_snapshot,
        construction_snapshot={
            "completion_percentage": project.completion_percentage,
            "development_stage": (
                project.development_stage.value if project.development_stage else None
            ),
            "status": project.project_status.value,
            "is_delayed": delayed,
            "risk": shell.risk.value,
            "budget_utilization": (
                metric(utilization)
                if shell.financial_access and utilization is not None
                else unavailable(
                    "Restricted" if not shell.financial_access else "No budget baseline"
                )
            ),
            "linked_records_available": False,
            "linked_records_reason": (
                "Dedicated construction records (permits, inspections, change orders) "
                "are not linked in this workspace yet."
            ),
        },
        sales_leasing_snapshot={
            "available_units": inv_metric("available"),
            "reserved_units": inv_metric("reserved"),
            "under_contract_units": inv_metric("under_contract"),
            "sold_units": inv_metric("sold"),
            "occupied_units": inv_metric("leased"),
            "vacant_units": inv_metric("vacant"),
        },
        team=team.items if shell.permissions.can_view_team else [],
        milestones=milestones[:8],
        alerts=alerts[:8],
        activity=activity.items,
        key_documents=docs_resp.items,
        warnings=warnings,
    )


def _scoped_version_cost(
    db: Session,
    project_id: UUID,
    audience: BudgetAudience,
    phase_id: UUID | None = None,
) -> tuple[Decimal | None, Decimal | None]:
    """Cost from current approved versions.

    A selected phase uses only that phase. The whole project uses phase
    versions when any exist, and does not also add the project-level version.
    With no phase versions, the existing project-level version is used.
    """
    if phase_id is None:
        phased_exists = db.scalar(
            select(ProjectBudgetVersion.id)
            .where(
                ProjectBudgetVersion.project_id == project_id,
                ProjectBudgetVersion.audience == audience,
                ProjectBudgetVersion.is_current.is_(True),
                ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
                ProjectBudgetVersion.phase_id.is_not(None),
            )
            .limit(1)
        )
        if phased_exists is None:
            version = _current_version(db, project_id, audience)
            if version is None:
                return None, None
            return _active_line_total(db, version.id)
    versions = list(
        db.scalars(
            select(ProjectBudgetVersion).where(
                ProjectBudgetVersion.project_id == project_id,
                ProjectBudgetVersion.audience == audience,
                ProjectBudgetVersion.is_current.is_(True),
                ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
            )
        ).all()
    )
    if phase_id is not None:
        chosen = [version for version in versions if version.phase_id == phase_id]
    else:
        chosen = [version for version in versions if version.phase_id is not None]
    if not chosen:
        return None, None
    current = ZERO
    estimated = ZERO
    for version in chosen:
        line_current, line_estimated = _active_line_total(db, version.id)
        current += line_current
        estimated += line_estimated
    return current, estimated


def _current_version(
    db: Session, project_id: UUID, audience: BudgetAudience
) -> ProjectBudgetVersion | None:
    return db.scalars(
        select(ProjectBudgetVersion).where(
            ProjectBudgetVersion.project_id == project_id,
            ProjectBudgetVersion.audience == audience,
            ProjectBudgetVersion.is_current.is_(True),
            ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
        )
    ).first()


def _active_line_total(db: Session, version_id: UUID) -> tuple[Decimal, Decimal]:
    lines = list(
        db.scalars(
            select(ProjectBudgetLine).where(
                ProjectBudgetLine.budget_version_id == version_id,
                ProjectBudgetLine.is_active.is_(True),
                ProjectBudgetLine.is_summary.is_(False),
            )
        ).all()
    )
    current = sum((line.current_budget or ZERO for line in lines), ZERO)
    estimated = sum(
        (
            line.forecast_at_completion
            if line.forecast_at_completion is not None
            else (line.current_budget or ZERO)
            for line in lines
        ),
        ZERO,
    )
    return current, estimated


_CONTRACTED_STATUSES = (
    CommitmentStatus.COMMITTED,
    CommitmentStatus.PARTIALLY_FUNDED,
    CommitmentStatus.FULLY_FUNDED,
    CommitmentStatus.DELAYED,
)


def _investor_terms(
    db: Session, project_id: UUID, phase_id: UUID | None = None
) -> tuple[Decimal | None, Decimal | None, str]:
    """Capital and contracted profit for active commitments.

    Proposed and cancelled rows are excluded. A missing profit stays unknown.
    Mixed currencies are not added together. Investor profit is not a project cost.
    """
    rows = list(
        db.scalars(
            select(FundingCommitment).where(
                FundingCommitment.project_id == project_id,
                FundingCommitment.status.in_(_CONTRACTED_STATUSES),
                operational_child_clause(
                    FundingCommitment.is_demo, FundingCommitment.project_id
                ),
            )
        ).all()
    )
    if phase_id is not None:
        rows = [row for row in rows if row.phase_id == phase_id]
        if not rows:
            return None, None, "No funding commitment is recorded for this phase"
    if not rows:
        return ZERO, None, "No contracted funding commitment"
    currencies = {row.currency for row in rows}
    if len(currencies) != 1:
        return None, None, "Included commitments do not share one currency"
    capital = sum((row.committed_amount for row in rows), ZERO)
    if any(row.contracted_profit is None for row in rows):
        return capital, None, "Contracted profit is missing on a commitment"
    profit = sum((row.contracted_profit or ZERO for row in rows), ZERO)
    return capital, profit, ""


def _parse_money(raw: object) -> Decimal | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except Exception:
        return None


def _explicit_adjustment(meta: object) -> Decimal | None:
    if not isinstance(meta, dict):
        return ZERO
    total = ZERO
    for key in ("discount_amount", "adjustment_amount"):
        if key not in meta or meta[key] is None:
            continue
        parsed = _parse_money(meta[key])
        if parsed is None:
            return None
        total += parsed
    return total


def _active_sale_agreements(db: Session, project_id: UUID, phase_id: UUID | None):
    from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
    from investhome_api.services.crm.unit_change import (
        is_historical_unit_change,
        is_relationship_detached,
    )

    rows = list(
        db.scalars(
            select(CrmAgreement).where(
                CrmAgreement.project_id == project_id,
                CrmAgreement.status != CrmAgreementStatus.CANCELLED,
            )
        ).all()
    )
    if phase_id is not None:
        rows = [row for row in rows if row.phase_id == phase_id]
    return [
        row
        for row in rows
        if not is_historical_unit_change(row) and not is_relationship_detached(row)
    ]


def _net_verified_cash(db: Session, agreement_ids: set[UUID], currency: str) -> dict[UUID, Decimal | None]:
    """Completed receipts minus completed refunds. Unlinked or pending cash stays unknown."""
    from investhome_api.models.finance import FinanceTransaction, TransactionStatus, TransactionType

    if not agreement_ids:
        return {}
    movements = list(
        db.scalars(
            select(FinanceTransaction).where(
                FinanceTransaction.agreement_id.in_(agreement_ids),
                FinanceTransaction.archived_at.is_(None),
                FinanceTransaction.status == TransactionStatus.COMPLETED,
                operational_child_clause(
                    FinanceTransaction.is_demo, FinanceTransaction.project_id
                ),
            )
        ).all()
    )
    grouped: dict[UUID, list] = {agreement_id: [] for agreement_id in agreement_ids}
    for row in movements:
        if row.agreement_id is not None:
            grouped.setdefault(row.agreement_id, []).append(row)
    receipts = {TransactionType.SALE_PROCEEDS, TransactionType.INCOME}
    nets: dict[UUID, Decimal | None] = {}
    for agreement_id, rows in grouped.items():
        verified = [
            row
            for row in rows
            if row.transaction_type in receipts or row.transaction_type == TransactionType.REFUND
        ]
        if not verified or any((row.currency or "").upper() != currency for row in verified):
            nets[agreement_id] = None
            continue
        incoming = sum(
            (row.amount for row in verified if row.transaction_type in receipts),
            ZERO,
        )
        returned = sum(
            (row.amount for row in verified if row.transaction_type == TransactionType.REFUND),
            ZERO,
        )
        nets[agreement_id] = incoming - returned
    return nets


def _sale_position(
    db: Session, project_id: UUID, phase_id: UUID | None, currency: str
) -> tuple[Decimal | None, Decimal | None, Decimal | None, str]:
    """Contracted price, verified net cash, and remaining receivable.

    A missing collection link stays unknown. It is not treated as zero.
    Cash refunds reduce verified net cash once. Commission is not included.
    """
    rows = _active_sale_agreements(db, project_id, phase_id)
    if not rows:
        return None, None, None, "No contracted sale is recorded"
    cash = _net_verified_cash(db, {row.id for row in rows}, currency.upper())
    contracted = ZERO
    collected = ZERO
    remaining = ZERO
    cash_known = True
    for row in rows:
        sale = _parse_money(row.investment_amount)
        if sale is None:
            return None, None, None, "A contracted sale has no amount"
        adjustment = _explicit_adjustment(row.metadata_json)
        if adjustment is None:
            return None, None, None, "A sale adjustment is not numeric"
        contracted += sale
        net = cash.get(row.id)
        if net is None:
            cash_known = False
            continue
        collected += net
        remaining += sale - adjustment - net
    if not cash_known:
        return contracted, None, None, "Verified collection is not linked"
    return contracted, collected, remaining, ""


def _commission_position(
    db: Session, project_id: UUID, phase_id: UUID | None
) -> tuple[Decimal | None, Decimal | None, Decimal | None, str]:
    """Broker commission on the sale. It is not sale proceeds or a customer receipt."""
    from investhome_api.models.crm_agreement import CrmAgreementParticipant

    rows = _active_sale_agreements(db, project_id, phase_id)
    if not rows:
        return None, None, None, "No commission is recorded"
    by_id = {row.id: row for row in rows}
    participants = list(
        db.scalars(
            select(CrmAgreementParticipant).where(
                CrmAgreementParticipant.agreement_id.in_(by_id)
            )
        ).all()
    )
    agent_roles = {"broker", "realtor", "agent", "agency"}
    relevant = [
        row
        for row in participants
        if (row.role or "").casefold() in agent_roles
        or row.commission_amount is not None
        or row.commission_rate is not None
        or row.commission_paid is not None
    ]
    if not relevant:
        return None, None, None, "No commission is recorded"
    amount_total = ZERO
    paid_total = ZERO
    paid_known = True
    for row in relevant:
        amount = row.commission_amount
        sale = _parse_money(by_id[row.agreement_id].investment_amount)
        if amount is None and row.commission_rate is not None and sale is not None:
            amount = (row.commission_rate * sale).quantize(Decimal("0.01"))
        if amount is None:
            return None, None, None, "Commission amount is missing"
        amount_total += amount
        if row.commission_paid is None:
            paid_known = False
            continue
        paid_total += row.commission_paid
    if not paid_known:
        return amount_total, None, None, "Commission payment is missing"
    return amount_total, paid_total, amount_total - paid_total, ""


def _asset_sale_facts(
    db: Session, project_id: UUID, asset_ids: list[UUID], currency: str
) -> dict[UUID, dict[str, Decimal | str | None]]:
    wanted = set(asset_ids)
    rows = [
        row
        for row in _active_sale_agreements(db, project_id, None)
        if row.inventory_asset_id in wanted
    ]
    cash = _net_verified_cash(db, {row.id for row in rows}, currency.upper())
    facts: dict[UUID, dict[str, Decimal | None]] = {}
    for row in rows:
        asset_id = row.inventory_asset_id
        if asset_id is None:
            continue
        if asset_id in facts:
            facts[asset_id] = {"sale": None, "collected": None, "plan": None}
            continue
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        plan = meta.get("payment_plan")
        facts[asset_id] = {
            "sale": _parse_money(row.investment_amount),
            "collected": cash.get(row.id),
            "plan": plan.strip() if isinstance(plan, str) and plan.strip() else None,
        }
    return facts


_CUSTOMER_PROFIT_HIDDEN = unavailable("Not included in the customer proforma")


def get_financials(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    audience: BudgetAudience = BudgetAudience.INTERNAL,
    phase_id: UUID | None = None,
) -> ProjectFinancialsResponse:
    if not _can_view_financial(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view project financials",
        )
    project = _load_project(db, project_id)
    phase_id = operational_phase_id(uses_phases=project.uses_phases, phase_id=phase_id)
    spent_map, total_map = _budget_maps(db, [project.id])
    spent = spent_map.get(project.id, ZERO)
    line_total = total_map.get(project.id, ZERO)
    utilization = _budget_utilization(project, spent, line_total)
    baseline = project.construction_budget or project.total_development_cost
    remaining = (baseline - spent) if baseline is not None else None
    margin = None
    if project.projected_revenue and project.projected_profit is not None:
        if project.projected_revenue > 0:
            margin = (project.projected_profit / project.projected_revenue) * Decimal("100")

    budgets = list(
        db.scalars(
            select(ProjectBudget).where(
                ProjectBudget.project_id == project.id,
                operational_child_clause(ProjectBudget.is_demo, ProjectBudget.project_id),
            )
        ).all()
    )
    commitments = list(
        db.scalars(
            select(FundingCommitment).where(
                FundingCommitment.project_id == project.id,
                operational_child_clause(
                    FundingCommitment.is_demo, FundingCommitment.project_id
                ),
            )
        ).all()
    )
    if phase_id is not None:
        commitments = [row for row in commitments if row.phase_id == phase_id]
    warnings: list[str] = []
    if not budgets:
        warnings.append("No linked project budget lines.")
    if not commitments:
        warnings.append("No linked funding commitments.")

    line_cost, estimated_cost = _scoped_version_cost(
        db, project.id, BudgetAudience.INTERNAL, phase_id
    )
    legacy_revised = sum(
        ((item.revised_budget if item.revised_budget is not None else item.original_budget) or ZERO)
        for item in budgets
    )
    if phase_id is not None:
        total_project_cost = line_cost
    elif line_cost is not None:
        total_project_cost = line_cost
    elif budgets:
        total_project_cost = legacy_revised
    else:
        total_project_cost = project.total_development_cost
    if estimated_cost is None and phase_id is None:
        estimated_cost = total_project_cost
    actual_cost = None if phase_id is not None else spent
    remaining_budget = (
        (total_project_cost - actual_cost)
        if total_project_cost is not None and actual_cost is not None
        else None
    )
    revenue = None if phase_id is not None else project.projected_revenue
    total_profit = (
        (revenue - total_project_cost)
        if revenue is not None and total_project_cost is not None
        else None
    )
    committed_capital, contracted_profit, profit_reason = _investor_terms(
        db, project.id, phase_id
    )
    sale_currency = (project.currency or "USD").upper()
    contracted_sales, verified_cash, receivable, sales_reason = _sale_position(
        db, project.id, phase_id, sale_currency
    )
    commission_amount, commission_paid, commission_remaining, commission_reason = (
        _commission_position(db, project.id, phase_id)
    )
    investor_return = (
        committed_capital + contracted_profit
        if committed_capital is not None and contracted_profit is not None
        else None
    )
    investhome_profit = (
        total_profit - contracted_profit
        if total_profit is not None and contracted_profit is not None
        else None
    )
    capital_metric = (
        metric(committed_capital)
        if committed_capital is not None
        else unavailable(profit_reason)
    )
    profit_metric = _financial_metric(
        contracted_profit, access=True, reason=profit_reason or "Contracted profit is unknown"
    )
    return_metric = _financial_metric(
        investor_return, access=True, reason=profit_reason or "Contracted profit is unknown"
    )
    residual_metric = _financial_metric(
        investhome_profit,
        access=True,
        reason=profit_reason or "Revenue, cost, or contracted profit is unavailable",
    )

    if audience == BudgetAudience.CUSTOMER:
        published, _ignored = _scoped_version_cost(
            db, project.id, BudgetAudience.CUSTOMER, phase_id
        )
        return ProjectFinancialsResponse(
            financial_access=True,
            audience=BudgetAudience.CUSTOMER.value,
            summary={
                "published_budget": _financial_metric(
                    published, access=True, reason="No customer proforma"
                ),
                "contracted_sales_value": _financial_metric(
                    contracted_sales,
                    access=True,
                    reason=sales_reason or "No contracted sale is recorded",
                ),
                "financing": capital_metric,
                "investor_committed_capital": capital_metric,
                "investor_contracted_profit": _CUSTOMER_PROFIT_HIDDEN,
                "investor_total_return": _CUSTOMER_PROFIT_HIDDEN,
                "investhome_estimated_profit": _CUSTOMER_PROFIT_HIDDEN,
            },
            budgets=[],
            capital=[],
            warnings=["Customer view omits internal cost, profit, and cash movement."],
        )

    return ProjectFinancialsResponse(
        financial_access=True,
        audience=BudgetAudience.INTERNAL.value,
        summary={
            "purchase_price": _financial_metric(project.acquisition_price, access=True),
            "land_cost": _financial_metric(project.land_cost, access=True),
            "construction_budget": _financial_metric(project.construction_budget, access=True),
            "soft_cost_budget": _financial_metric(project.soft_cost_budget, access=True),
            "total_development_budget": _financial_metric(
                project.total_development_cost, access=True
            ),
            "budget_paid": metric(spent),
            "budget_remaining": _financial_metric(
                remaining, access=True, reason="No budget baseline"
            ),
            "budget_utilization": _financial_metric(
                utilization, access=True, reason="No budget baseline"
            ),
            "expected_revenue": _financial_metric(project.projected_revenue, access=True),
            "expected_profit": _financial_metric(project.projected_profit, access=True),
            "profit_margin": _financial_metric(margin, access=True, reason="Insufficient data"),
            "current_value": _financial_metric(project.current_project_value, access=True),
            "equity_required": _financial_metric(project.equity_required, access=True),
            "equity_raised": _financial_metric(project.equity_raised, access=True),
            "debt_outstanding": _financial_metric(project.debt_amount, access=True),
            "realized_revenue": _financial_metric(
                verified_cash, access=True, reason=sales_reason or "Verified collection is not linked"
            ),
            "verified_collections": _financial_metric(
                verified_cash, access=True, reason=sales_reason or "Verified collection is not linked"
            ),
            "remaining_receivable": _financial_metric(
                receivable, access=True, reason=sales_reason or "Verified collection is not linked"
            ),
            "commission_amount": _financial_metric(
                commission_amount, access=True, reason=commission_reason or "No commission is recorded"
            ),
            "commission_paid": _financial_metric(
                commission_paid, access=True, reason=commission_reason or "Commission payment is missing"
            ),
            "commission_remaining": _financial_metric(
                commission_remaining,
                access=True,
                reason=commission_reason or "Commission payment is missing",
            ),
            "realized_profit": unavailable("Realized profit ledger is not available"),
            "roi": unavailable("ROI requires cash-flow history"),
            "irr": unavailable("IRR requires cash-flow history"),
            "equity_multiple": unavailable("Equity multiple requires distribution history"),
            "total_project_cost": _financial_metric(
                total_project_cost, access=True, reason="No budget baseline"
            ),
            "estimated_cost": _financial_metric(
                estimated_cost, access=True, reason="No budget baseline"
            ),
            "estimated_sales_revenue": _financial_metric(revenue, access=True),
            "contracted_sales_value": _financial_metric(
                contracted_sales, access=True, reason=sales_reason or "No contracted sale is recorded"
            ),
            "actual_cost": (
                unavailable("Actual cost is not recorded by phase")
                if phase_id is not None
                else metric(actual_cost)
            ),
            "remaining_budget": _financial_metric(
                remaining_budget, access=True, reason="No budget baseline"
            ),
            "financing": capital_metric,
            "total_project_profit": _financial_metric(
                total_profit, access=True, reason="Revenue or cost is unavailable"
            ),
            "project_profitability": _financial_metric(
                total_profit, access=True, reason="Revenue or cost is unavailable"
            ),
            "investor_committed_capital": capital_metric,
            "investor_contracted_profit": profit_metric,
            "investor_total_return": return_metric,
            "investhome_estimated_profit": residual_metric,
        },
        budgets=[]
        if phase_id is not None
        else [
            {
                "id": str(b.id),
                "budget_name": b.budget_name,
                "category": b.category.value if b.category else None,
                "original_budget": b.original_budget,
                "revised_budget": b.revised_budget,
                "committed_amount": b.committed_amount,
                "paid_amount": b.paid_amount,
                "forecast_amount": b.forecast_amount,
                "currency": b.currency,
            }
            for b in budgets
        ],
        capital=[
            {
                "id": str(c.id),
                "investor_id": str(c.investor_id),
                "commitment_type": c.commitment_type.value if c.commitment_type else None,
                "committed_amount": c.committed_amount,
                "contracted_profit": c.contracted_profit,
                "funded_amount": c.funded_amount,
                "remaining_amount": c.remaining_amount,
                "status": c.status.value if c.status else None,
                "currency": c.currency,
                "commitment_date": c.commitment_date,
            }
            for c in commitments
        ],
        warnings=warnings,
    )


def get_schedule(db: Session, user: User, project_id: UUID) -> ProjectScheduleResponse:
    del user
    project = _load_project(db, project_id)
    today = date.today()
    days_remaining = _days_remaining(project, today)
    delayed = _is_delayed(project, today)
    missing: list[str] = []
    if project.acquisition_date is None:
        missing.append("acquisition_date")
    if project.start_date is None:
        missing.append("estimated_start")
    if project.target_completion_date is None:
        missing.append("estimated_completion")
    if project.estimated_closing_date is None:
        missing.append("estimated_closing")

    risks: list[str] = []
    if delayed:
        risks.append("Project is past estimated completion.")
    if project.start_date and project.target_completion_date:
        if project.target_completion_date < project.start_date:
            risks.append("Target completion is before estimated start.")
    if missing:
        risks.append("One or more key schedule dates are missing.")

    milestones = derive_milestones_for_project(project, today=today, window_days=365)
    return ProjectScheduleResponse(
        key_dates={
            "acquisition": project.acquisition_date,
            "estimated_start": project.start_date,
            "actual_start": project.actual_start_date,
            "estimated_completion": project.target_completion_date,
            "actual_completion": project.actual_completion_date,
            "estimated_closing": project.estimated_closing_date,
            "actual_closing": None,
        },
        days_remaining=days_remaining,
        days_delayed=abs(days_remaining) if delayed and days_remaining is not None else None,
        is_delayed=delayed,
        missing_dates=missing,
        milestones=milestones,
        risks=risks,
    )


def get_construction(db: Session, user: User, project_id: UUID) -> ProjectConstructionResponse:
    shell = build_shell(db, user, project_id)
    project = _load_project(db, project_id)
    today = date.today()
    spent_map, total_map = _budget_maps(db, [project.id])
    spent = spent_map.get(project.id, ZERO)
    line_total = total_map.get(project.id, ZERO)
    utilization = _budget_utilization(project, spent, line_total)
    alerts = generate_alerts_for_project(
        project,
        today=today,
        team_members=list(
            db.scalars(
                select(ProjectTeamMember).where(ProjectTeamMember.project_id == project.id)
            ).all()
        ),
        budget_spent=spent,
        budget_total=line_total
        if line_total > 0
        else (project.construction_budget or project.total_development_cost),
        db=db,
        include_operational_cost_alerts=True,
    )
    construction_alerts = [
        a
        for a in alerts
        if getattr(a.category, "value", str(a.category))
        in {"construction", "schedule", "budget"}
    ]
    return ProjectConstructionResponse(
        completion_percentage=project.completion_percentage,
        development_stage=(
            project.development_stage.value if project.development_stage else None
        ),
        status=project.project_status.value,
        is_delayed=_is_delayed(project, today),
        days_remaining=_days_remaining(project, today),
        budget_utilization=(
            metric(utilization)
            if shell.financial_access and utilization is not None
            else unavailable(
                "Restricted" if not shell.financial_access else "No budget baseline"
            )
        ),
        risk=shell.risk,
        alerts=construction_alerts,
        warnings=[
            "Dedicated construction records (permits, inspections, change orders, "
            "contractors) are not available in this workspace yet."
        ],
    )


def _sales_allocation_counts(db: Session, project_id: UUID) -> dict[str, int]:
    """Count real inventory rows. Sold and available use the sales pair, not closing."""
    row = db.execute(
        select(
            func.count(InventoryAsset.id),
            func.sum(case((InventoryAsset.sales_market == SalesMarket.TURKEY, 1), else_=0)),
            func.sum(case((InventoryAsset.sales_market == SalesMarket.USA, 1), else_=0)),
            func.sum(case((InventoryAsset.sales_status == InventorySalesStatus.SOLD, 1), else_=0)),
            func.sum(
                case(
                    (
                        and_(
                            InventoryAsset.sales_status == InventorySalesStatus.AVAILABLE_FOR_SALE,
                            InventoryAsset.availability_status == AvailabilityStatus.AVAILABLE,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
        ).where(
            InventoryAsset.project_id == project_id,
            InventoryAsset.archived_at.is_(None),
            operational_child_clause(InventoryAsset.is_demo, InventoryAsset.project_id),
        )
    ).one()
    return {
        "total_physical_units": int(row[0] or 0),
        "turkey_allocation": int(row[1] or 0),
        "usa_allocation": int(row[2] or 0),
        "sold_units": int(row[3] or 0),
        "available_for_sale": int(row[4] or 0),
    }


def get_units(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    search: str | None = None,
    phase_id: UUID | None = None,
    availability_status: str | None = None,
    sales_status: str | None = None,
    sales_market: str | None = None,
    leasing_status: str | None = None,
    asset_type: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "display_id",
    sort_order: str = "asc",
) -> ProjectUnitsResponse:
    project = _load_project(db, project_id)
    phase_id = operational_phase_id(uses_phases=project.uses_phases, phase_id=phase_id)
    financial_access = _can_view_financial(user)
    can_view_list_price = financial_access or user_has_permission(user, "inventory", "view_price")
    inventory = _inventory_counts(db, [project.id], phase_id)

    query = select(InventoryAsset).where(
        InventoryAsset.project_id == project.id,
        InventoryAsset.archived_at.is_(None),
        operational_child_clause(InventoryAsset.is_demo, InventoryAsset.project_id),
    )
    count_query = (
        select(func.count())
        .select_from(InventoryAsset)
        .where(
            InventoryAsset.project_id == project.id,
            InventoryAsset.archived_at.is_(None),
            operational_child_clause(InventoryAsset.is_demo, InventoryAsset.project_id),
        )
    )

    if phase_id is not None:
        query = query.where(InventoryAsset.phase_id == phase_id)
        count_query = count_query.where(InventoryAsset.phase_id == phase_id)
    if search:
        pattern = f"%{search.strip()}%"
        cond = or_(
            InventoryAsset.display_id.ilike(pattern),
            InventoryAsset.system_code.ilike(pattern),
            InventoryAsset.unit_subtype.ilike(pattern),
        )
        query = query.where(cond)
        count_query = count_query.where(cond)
    if availability_status:
        query = query.where(InventoryAsset.availability_status == availability_status)
        count_query = count_query.where(InventoryAsset.availability_status == availability_status)
    if sales_status:
        query = query.where(InventoryAsset.sales_status == sales_status)
        count_query = count_query.where(InventoryAsset.sales_status == sales_status)
    if sales_market:
        query = query.where(InventoryAsset.sales_market == sales_market)
        count_query = count_query.where(InventoryAsset.sales_market == sales_market)
    if leasing_status:
        query = query.where(InventoryAsset.leasing_status == leasing_status)
        count_query = count_query.where(InventoryAsset.leasing_status == leasing_status)
    if asset_type:
        query = query.where(InventoryAsset.asset_type == asset_type)
        count_query = count_query.where(InventoryAsset.asset_type == asset_type)

    sortable = {
        "display_id": InventoryAsset.display_id,
        "updated_at": InventoryAsset.updated_at,
        "list_price": InventoryAsset.list_price,
        "sales_status": InventoryAsset.sales_status,
        "leasing_status": InventoryAsset.leasing_status,
    }
    sort_col = sortable.get(sort_by, InventoryAsset.display_id)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    total = int(db.scalar(count_query) or 0)
    priced_count, priced_sum = db.execute(
        select(
            func.count(InventoryAsset.list_price),
            func.coalesce(func.sum(InventoryAsset.list_price), 0),
        ).where(count_query.whereclause)
    ).one()
    if not can_view_list_price:
        list_value = unavailable("Restricted")
    elif total == 0:
        list_value = unavailable("No linked inventory assets")
    elif int(priced_count or 0) != total:
        list_value = unavailable("List price is missing on a unit")
    else:
        list_value = metric(priced_sum)
    pages = max(1, ceil(total / page_size)) if total else 1
    offset = (page - 1) * page_size
    assets = list(db.scalars(query.offset(offset).limit(page_size)).all())
    floor_ids = {asset.floor_id for asset in assets if asset.floor_id is not None}
    floors_by_id: dict[UUID, Floor] = {}
    if floor_ids:
        floors_by_id = {
            floor.id: floor
            for floor in db.scalars(select(Floor).where(Floor.id.in_(floor_ids))).all()
        }
    building_ids = {asset.building_id for asset in assets if asset.building_id is not None}
    buildings_by_id: dict[UUID, Building] = {}
    if building_ids:
        buildings_by_id = {
            building.id: building
            for building in db.scalars(select(Building).where(Building.id.in_(building_ids))).all()
        }
    from investhome_api.models.inventory import ProjectPhase

    phase_ids = {asset.phase_id for asset in assets if getattr(asset, "phase_id", None) is not None}
    phases_by_id: dict[UUID, ProjectPhase] = {}
    if phase_ids:
        phases_by_id = {
            phase.id: phase
            for phase in db.scalars(select(ProjectPhase).where(ProjectPhase.id.in_(phase_ids))).all()
        }
    allocation = _sales_allocation_counts(db, project.id)

    def inv_metric(key: str):
        if inventory["total_assets"] == 0:
            return unavailable("No linked inventory assets")
        return metric(inventory[key])

    sale_facts = (
        _asset_sale_facts(db, project.id, [asset.id for asset in assets], project.currency or "USD")
        if financial_access
        else {}
    )
    items = []
    for asset in assets:
        floor = floors_by_id.get(asset.floor_id) if asset.floor_id else None
        building = buildings_by_id.get(asset.building_id) if asset.building_id else None
        building_label = building.name if building else None
        phase = phases_by_id.get(asset.phase_id) if getattr(asset, "phase_id", None) else None
        phase_name = phase.name if phase else None
        label_prefix = phase_name or building_label
        unit_label = (
            f"{label_prefix} · {asset.display_id}" if label_prefix else asset.display_id
        )
        market = asset.sales_market.value if asset.sales_market else None
        items.append(
            {
                "id": str(asset.id),
                "unit": asset.display_id,
                "unit_label": unit_label,
                "phase_id": str(asset.phase_id) if getattr(asset, "phase_id", None) else None,
                "phase_name": phase_name,
                "building_id": str(asset.building_id) if asset.building_id else None,
                "building_code": building.code if building else None,
                "building_label": building_label,
                "unit_code": asset.system_code,
                "type": asset.asset_type.value if asset.asset_type else None,
                "bedrooms": asset.bedrooms,
                "bathrooms": asset.bathrooms,
                "floor_id": str(asset.floor_id) if asset.floor_id else None,
                "floor_number": floor.floor_number if floor else None,
                "floor_label": (floor.display_name or str(floor.floor_number)) if floor else None,
                "square_feet": asset.total_area_sqft or asset.interior_area_sqft,
                "availability_status": asset.availability_status.value,
                "sales_status": asset.sales_status.value,
                "sales_market": market,
                "leasing_status": asset.leasing_status.value,
                "reservation_status": asset.reservation_status.value,
                "price": asset.list_price if can_view_list_price else None,
                "sale_amount": sale_facts.get(asset.id, {}).get("sale") if financial_access else None,
                "sale_amount_available": financial_access and sale_facts.get(asset.id, {}).get("sale") is not None,
                "collected_amount": (
                    sale_facts.get(asset.id, {}).get("collected") if financial_access else None
                ),
                "collected_available": financial_access
                and sale_facts.get(asset.id, {}).get("collected") is not None,
                "payment_plan": sale_facts.get(asset.id, {}).get("plan") if financial_access else None,
                "price_available": can_view_list_price and asset.list_price is not None,
                "rent": None,
                "rent_available": False,
                "rent_reason": "Monthly rent is stored as an estimated_rent price, not an asset column",
                "investor": None,
                "updated_at": asset.updated_at,
            }
        )

    warnings = []
    if inventory["total_assets"] == 0:
        warnings.append("No units linked to this project.")

    return ProjectUnitsResponse(
        summary={
            "total_units": metric(inventory["total_assets"]),
            "total_list_value": list_value,
            "total_physical_units": metric(allocation["total_physical_units"]),
            "turkey_allocation": metric(allocation["turkey_allocation"]),
            "usa_allocation": metric(allocation["usa_allocation"]),
            "available": inv_metric("available"),
            "available_for_sale": metric(allocation["available_for_sale"]),
            "reserved": inv_metric("reserved"),
            "under_contract": inv_metric("under_contract"),
            "sold": inv_metric("sold"),
            "sold_units": metric(allocation["sold_units"]),
            "occupied": inv_metric("leased"),
            "vacant": inv_metric("vacant"),
        },
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        warnings=warnings,
    )


def get_sales(db: Session, user: User, project_id: UUID) -> ProjectSalesResponse:
    project = _load_project(db, project_id)
    financial_access = _can_view_financial(user)
    inventory = _inventory_counts(db, [project.id])

    opp_ids = list(
        db.scalars(
            select(OpportunityProject.opportunity_id).where(
                OpportunityProject.project_id == project.id
            )
        ).all()
    )
    opportunities: list[SalesOpportunity] = []
    if opp_ids:
        opportunities = list(
            db.scalars(
                select(SalesOpportunity)
                .where(
                    SalesOpportunity.id.in_(opp_ids),
                    SalesOpportunity.archived_at.is_(None),
                )
                .order_by(SalesOpportunity.updated_at.desc())
                .limit(100)
            ).all()
        )

    by_status: dict[str, int] = {}
    revenue_values: list[Decimal] = []
    for opp in opportunities:
        key = opp.stage.value if opp.stage else "unknown"
        by_status[key] = by_status.get(key, 0) + 1
        if opp.expected_revenue is not None:
            revenue_values.append(opp.expected_revenue)

    avg_price = None
    volume = None
    if financial_access and revenue_values:
        volume = sum(revenue_values, ZERO)
        avg_price = volume / Decimal(len(revenue_values))

    sold = inventory["sold"]
    total_assets = inventory["total_assets"]
    sales_rate = None
    if total_assets > 0:
        sales_rate = (Decimal(sold) / Decimal(total_assets)) * Decimal("100")

    warnings: list[str] = []
    if total_assets == 0:
        warnings.append("Sales unit counts are unavailable until inventory is linked.")
    if not opportunities:
        warnings.append("No sales opportunities are linked to this project.")

    def inv_metric(key: str):
        if total_assets == 0:
            return unavailable("No linked inventory assets")
        return metric(inventory[key])

    return ProjectSalesResponse(
        summary={
            "available_units": inv_metric("available"),
            "reserved_units": inv_metric("reserved"),
            "under_contract_units": inv_metric("under_contract"),
            "sold_units": inv_metric("sold"),
            "sales_rate": (
                metric(sales_rate)
                if sales_rate is not None
                else unavailable("No linked inventory assets")
            ),
            "average_sales_price": (
                metric(avg_price)
                if financial_access and avg_price is not None
                else unavailable(
                    "Restricted"
                    if not financial_access
                    else "No opportunity expected revenue"
                )
            ),
            "sales_volume": (
                metric(volume)
                if financial_access and volume is not None
                else unavailable(
                    "Restricted"
                    if not financial_access
                    else "No opportunity expected revenue"
                )
            ),
            "linked_opportunities": metric(len(opportunities)),
        },
        opportunities=[
            {
                "id": str(o.id),
                "opportunity_code": o.opportunity_code,
                "display_id": o.display_id,
                "stage": o.stage.value if o.stage else None,
                "probability": o.probability,
                "expected_close_date": o.expected_close_date,
                "expected_revenue": o.expected_revenue if financial_access else None,
                "currency": o.currency,
                "priority": o.priority.value if o.priority else None,
                "href": f"/dashboard/sales/opportunities?id={o.id}",
                "updated_at": o.updated_at,
            }
            for o in opportunities
        ],
        total_opportunities=len(opportunities),
        by_status=by_status,
        warnings=warnings,
    )


def get_leasing(db: Session, user: User, project_id: UUID) -> ProjectLeasingResponse:
    del user
    project = _load_project(db, project_id)
    inventory = _inventory_counts(db, [project.id])
    total = inventory["total_assets"]
    occupied = inventory["leased"]
    vacant = inventory["vacant"]
    occupancy = None
    if total > 0:
        occupancy = (Decimal(occupied) / Decimal(total)) * Decimal("100")

    assets = list(
        db.scalars(
            select(InventoryAsset)
            .where(
                InventoryAsset.project_id == project.id,
                InventoryAsset.archived_at.is_(None),
                operational_child_clause(InventoryAsset.is_demo, InventoryAsset.project_id),
            )
            .order_by(InventoryAsset.display_id.asc())
            .limit(100)
        ).all()
    )
    by_status: dict[str, int] = {}
    for asset in assets:
        key = asset.leasing_status.value
        by_status[key] = by_status.get(key, 0) + 1

    def inv_metric(key: str):
        if total == 0:
            return unavailable("No linked inventory assets")
        return metric(inventory[key])

    return ProjectLeasingResponse(
        summary={
            "occupied_units": inv_metric("leased"),
            "vacant_units": inv_metric("vacant"),
            "occupancy_rate": (
                metric(occupancy) if occupancy is not None else unavailable("No linked inventory assets")
            ),
            "monthly_rent": unavailable("Unit rent is not stored on inventory assets"),
            "lease_expirations": unavailable("Lease contract data is not available"),
        },
        by_status=by_status,
        items=[
            {
                "id": str(a.id),
                "unit": a.display_id,
                "unit_code": a.system_code,
                "leasing_status": a.leasing_status.value,
                "availability_status": a.availability_status.value,
                "square_feet": a.total_area_sqft or a.interior_area_sqft,
                "updated_at": a.updated_at,
            }
            for a in assets
        ],
        warnings=[
            "Lease contract data is not available. Occupancy is derived from unit leasing status.",
        ],
    )


def get_investors(
    db: Session, user: User, project_id: UUID, phase_id: UUID | None = None
) -> ProjectInvestorsResponse:
    project = _load_project(db, project_id)
    phase_id = operational_phase_id(uses_phases=project.uses_phases, phase_id=phase_id)
    financial_access = _can_view_financial(user)
    rows = db.execute(
        select(FundingCommitment, Investor)
        .join(Investor, Investor.id == FundingCommitment.investor_id)
        .where(
            FundingCommitment.project_id == project.id,
            operational_child_clause(FundingCommitment.is_demo, FundingCommitment.project_id),
            *([FundingCommitment.phase_id == phase_id] if phase_id is not None else []),
        )
        .order_by(FundingCommitment.updated_at.desc())
    ).all()

    items = []
    for commitment, investor in rows:
        items.append(
            {
                "commitment_id": str(commitment.id),
                "investor_id": str(investor.id),
                "investor_name": investor.full_name,
                "entity": None,
                "commitment_type": (
                    commitment.commitment_type.value if commitment.commitment_type else None
                ),
                "committed_amount": commitment.committed_amount if financial_access else None,
                "contracted_profit": commitment.contracted_profit if financial_access else None,
                "funded_amount": commitment.funded_amount if financial_access else None,
                "remaining_amount": commitment.remaining_amount if financial_access else None,
                "ownership": None,
                "ownership_available": False,
                "units": None,
                "status": commitment.status.value if commitment.status else None,
                "contact": None,
                "last_activity": commitment.updated_at,
                "href": f"/dashboard/investors?id={investor.id}",
                "financial_access": financial_access,
            }
        )

    warnings = []
    if not items:
        warnings.append(
            "No funding commitments are recorded for this phase."
            if phase_id is not None
            else "No investors linked via funding commitments."
        )
    if not financial_access:
        warnings.append("Financial commitment amounts are restricted.")

    return ProjectInvestorsResponse(
        financial_access=financial_access,
        items=items,
        total=len(items),
        warnings=warnings,
    )


def get_documents(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> ProjectDocumentsResponse:
    project = _load_project(db, project_id)
    documents, total = build_list_query(
        db,
        user,
        search=search,
        category=category,
        status_filter=status_filter,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        page=page,
        page_size=page_size,
    )
    uploader_ids = {d.uploaded_by_user_id for d in documents if d.uploaded_by_user_id}
    uploaders: dict[UUID, str] = {}
    if uploader_ids:
        for u in db.scalars(select(User).where(User.id.in_(uploader_ids))).all():
            uploaders[u.id] = u.full_name

    items = [
        enrich_response(doc, uploader_name=uploaders.get(doc.uploaded_by_user_id))
        for doc in documents
    ]
    warnings = []
    if total == 0:
        warnings.append("No project documents.")
    return ProjectDocumentsResponse(items=items, total=total, warnings=warnings)


def list_project_alerts(
    db: Session, user: User, project_id: UUID
) -> ProjectAlertListResponse:
    project = _load_project(db, project_id)
    today = date.today()
    spent_map, total_map = _budget_maps(db, [project.id])
    spent = spent_map.get(project.id, ZERO)
    line_total = total_map.get(project.id, ZERO)
    members = list(
        db.scalars(
            select(ProjectTeamMember).where(ProjectTeamMember.project_id == project.id)
        ).all()
    )
    items = generate_alerts_for_project(
        project,
        today=today,
        team_members=members,
        budget_spent=spent,
        budget_total=line_total
        if line_total > 0
        else (project.construction_budget or project.total_development_cost),
        db=db,
    )
    # Prefer detail workspace deep links
    for item in items:
        item.action_url = f"/dashboard/projects/{project.id}/overview"
    return ProjectAlertListResponse(items=items, total=len(items))


def list_project_milestones(
    db: Session, user: User, project_id: UUID, *, days: int = 365
) -> ProjectMilestoneListResponse:
    del user
    project = _load_project(db, project_id)
    today = date.today()
    items = derive_milestones_for_project(project, today=today, window_days=days)
    for item in items:
        item.action_url = f"/dashboard/projects/{project.id}/schedule"
    return ProjectMilestoneListResponse(items=items, total=len(items))


def list_recent_activity(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    limit: int | None = None,
) -> ProjectActivityListResponse:
    project = _load_project(db, project_id)
    financial_access = _can_view_financial(user)
    size = limit or page_size
    entries, total = list_activities(
        db,
        user,
        entity_type=ActivityEntityType.PROJECT,
        entity_id=project.id,
        search=search,
        page=page,
        page_size=size,
    )
    items: list[ProjectActivityItem] = []
    for entry in entries:
        previous_values = dict(entry.previous_values or {})
        new_values = dict(entry.new_values or {})
        if not financial_access:
            for field in FINANCIAL_FIELDS:
                if field in previous_values:
                    previous_values[field] = "[restricted]"
                if field in new_values:
                    new_values[field] = "[restricted]"
        metadata = dict(entry.metadata_json or {})
        if previous_values or new_values:
            metadata["previous_values"] = previous_values
            metadata["new_values"] = new_values
            metadata["changed_fields"] = entry.changed_fields or []
        items.append(
            ProjectActivityItem(
                id=entry.id,
                project_id=project.id,
                project_name=project.project_name,
                type=entry.action.value if entry.action else "updated",
                title=entry.description_key,
                description=None,
                actor=entry.actor_name,
                created_at=entry.created_at,
                metadata=metadata,
                action_url=f"/dashboard/projects/{project.id}/activity",
            )
        )
    return ProjectActivityListResponse(items=items, total=total)


def search_directory_users(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    search: str | None = None,
    limit: int = 20,
) -> ProjectDirectoryUserListResponse:
    if not (_perm(user, "manage_team") or _perm(user, "view_team")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to search project directory users",
        )
    _load_project(db, project_id)
    query = select(User).where(User.archived_at.is_(None), User.status == UserStatus.ACTIVE)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.job_title.ilike(pattern),
            )
        )
    users = list(db.scalars(query.order_by(User.full_name.asc()).limit(limit)).all())
    return ProjectDirectoryUserListResponse(
        items=[
            ProjectDirectoryUser(
                id=u.id,
                full_name=u.full_name,
                email=u.email,
                job_title=u.job_title,
                status=u.status.value if hasattr(u.status, "value") else str(u.status),
            )
            for u in users
        ],
        total=len(users),
    )
