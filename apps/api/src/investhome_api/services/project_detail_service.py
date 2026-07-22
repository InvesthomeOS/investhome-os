"""Project detail workspace aggregation (Sprint 10A3)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.finance import FundingCommitment, ProjectBudget
from investhome_api.models.inventory import InventoryAsset
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
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_alerts import compute_project_risk, generate_alerts_for_project
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


def get_financials(db: Session, user: User, project_id: UUID) -> ProjectFinancialsResponse:
    if not _can_view_financial(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view project financials",
        )
    project = _load_project(db, project_id)
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
        db.scalars(select(ProjectBudget).where(ProjectBudget.project_id == project.id)).all()
    )
    commitments = list(
        db.scalars(
            select(FundingCommitment).where(FundingCommitment.project_id == project.id)
        ).all()
    )
    warnings: list[str] = []
    if not budgets:
        warnings.append("No linked project budget lines.")
    if not commitments:
        warnings.append("No linked funding commitments.")

    return ProjectFinancialsResponse(
        financial_access=True,
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
            "realized_revenue": unavailable("Realized revenue ledger is not available"),
            "realized_profit": unavailable("Realized profit ledger is not available"),
            "roi": unavailable("ROI requires cash-flow history"),
            "irr": unavailable("IRR requires cash-flow history"),
            "equity_multiple": unavailable("Equity multiple requires distribution history"),
        },
        budgets=[
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


def get_units(
    db: Session,
    user: User,
    project_id: UUID,
    *,
    search: str | None = None,
    availability_status: str | None = None,
    sales_status: str | None = None,
    leasing_status: str | None = None,
    asset_type: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "display_id",
    sort_order: str = "asc",
) -> ProjectUnitsResponse:
    project = _load_project(db, project_id)
    financial_access = _can_view_financial(user)
    inventory = _inventory_counts(db, [project.id])

    query = select(InventoryAsset).where(
        InventoryAsset.project_id == project.id,
        InventoryAsset.archived_at.is_(None),
    )
    count_query = (
        select(func.count())
        .select_from(InventoryAsset)
        .where(
            InventoryAsset.project_id == project.id,
            InventoryAsset.archived_at.is_(None),
        )
    )

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
    pages = max(1, ceil(total / page_size)) if total else 1
    offset = (page - 1) * page_size
    assets = list(db.scalars(query.offset(offset).limit(page_size)).all())

    def inv_metric(key: str):
        if inventory["total_assets"] == 0:
            return unavailable("No linked inventory assets")
        return metric(inventory[key])

    items = []
    for asset in assets:
        items.append(
            {
                "id": str(asset.id),
                "unit": asset.display_id,
                "unit_code": asset.system_code,
                "type": asset.asset_type.value if asset.asset_type else None,
                "bedrooms": asset.bedrooms,
                "bathrooms": asset.bathrooms,
                "floor_id": str(asset.floor_id) if asset.floor_id else None,
                "square_feet": asset.total_area_sqft or asset.interior_area_sqft,
                "availability_status": asset.availability_status.value,
                "sales_status": asset.sales_status.value,
                "leasing_status": asset.leasing_status.value,
                "reservation_status": asset.reservation_status.value,
                "price": asset.list_price if financial_access else None,
                "price_available": financial_access and asset.list_price is not None,
                "rent": None,
                "rent_available": False,
                "rent_reason": "Unit rent is not stored on inventory assets",
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
            "available": inv_metric("available"),
            "reserved": inv_metric("reserved"),
            "under_contract": inv_metric("under_contract"),
            "sold": inv_metric("sold"),
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


def get_investors(db: Session, user: User, project_id: UUID) -> ProjectInvestorsResponse:
    project = _load_project(db, project_id)
    financial_access = _can_view_financial(user)
    rows = db.execute(
        select(FundingCommitment, Investor)
        .join(Investor, Investor.id == FundingCommitment.investor_id)
        .where(FundingCommitment.project_id == project.id)
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
        warnings.append("No investors linked via funding commitments.")
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
