"""Centralized project critical-alert rules (derived, not persisted)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.project import Project, ProjectStatus
from investhome_api.models.project_cost import (
    COMMITTED_COST_STATUSES,
    ProjectCommitment,
    ProjectCommitmentLine,
    ProjectCommitmentStatus,
    ProjectVendorBill,
    VendorBillStatus,
)
from investhome_api.models.project_budget import ProjectBudgetLine
from investhome_api.models.project_team import ProjectTeamMember, ProjectTeamMemberStatus
from investhome_api.schemas.project_dashboard import (
    AlertCategory,
    AlertSeverity,
    ProjectAlertItem,
    ProjectRiskLevel,
)

BUDGET_UTILIZATION_WARN = Decimal("90")


def compute_project_risk(
    project: Project,
    *,
    today: date,
    team_count: int,
    budget_utilization: Decimal | None,
) -> ProjectRiskLevel:
    score = 0
    if project.project_manager_user_id is None and not project.assigned_project_manager:
        score += 2
    if team_count == 0:
        score += 1
    if project.completion_percentage is None and project.project_status in {
        ProjectStatus.CONSTRUCTION,
        ProjectStatus.PRE_DEVELOPMENT,
        ProjectStatus.PERMITTING,
    }:
        score += 2
    if project.target_completion_date and project.target_completion_date < today:
        if project.project_status not in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}:
            score += 3
    if project.start_date and project.target_completion_date:
        if project.target_completion_date < project.start_date:
            score += 2
    if budget_utilization is not None and budget_utilization >= BUDGET_UTILIZATION_WARN:
        score += 2
    if project.project_status == ProjectStatus.ON_HOLD:
        score += 1

    if score >= 6:
        return ProjectRiskLevel.CRITICAL
    if score >= 4:
        return ProjectRiskLevel.HIGH
    if score >= 2:
        return ProjectRiskLevel.MEDIUM
    return ProjectRiskLevel.LOW


def _alert(
    *,
    project: Project,
    rule: str,
    severity: AlertSeverity,
    category: AlertCategory,
    title: str,
    message: str,
    recommended_action: str | None = None,
    due_date: date | None = None,
    today: date,
) -> ProjectAlertItem:
    days_remaining = None
    if due_date is not None:
        days_remaining = (due_date - today).days
    return ProjectAlertItem(
        id=f"{project.id}:{rule}",
        project_id=project.id,
        project_name=project.project_name,
        severity=severity,
        category=category,
        title=title,
        message=message,
        action_required=severity in {AlertSeverity.HIGH, AlertSeverity.CRITICAL},
        recommended_action=recommended_action,
        created_at=datetime.now(UTC),
        due_date=due_date,
        days_remaining=days_remaining,
        source=rule,
        action_url=f"/dashboard/projects?id={project.id}",
    )


def _cost_alerts_for_project(
    db: Session,
    project: Project,
    *,
    today: date,
) -> list[ProjectAlertItem]:
    """Deterministic cost alerts: overdue bills, pending approvals, over-budget commitments."""
    alerts: list[ProjectAlertItem] = []
    bills = db.scalars(
        select(ProjectVendorBill).where(ProjectVendorBill.project_id == project.id)
    ).all()
    for bill in bills:
        if bill.due_date is None:
            continue
        if bill.status in {VendorBillStatus.PAID, VendorBillStatus.VOID, VendorBillStatus.ARCHIVED}:
            continue
        if bill.due_date < today and Decimal(str(bill.balance_due or 0)) > 0:
            alerts.append(
                _alert(
                    project=project,
                    rule=f"bill_overdue:{bill.id}",
                    severity=AlertSeverity.HIGH,
                    category=AlertCategory.BUDGET,
                    title="Vendor bill overdue",
                    message=f"Bill {bill.bill_number} is past due ({bill.due_date.isoformat()}).",
                    recommended_action="Pay or renegotiate the overdue vendor bill.",
                    due_date=bill.due_date,
                    today=today,
                )
            )

    pending = db.scalars(
        select(ProjectCommitment).where(
            ProjectCommitment.project_id == project.id,
            ProjectCommitment.status == ProjectCommitmentStatus.IN_REVIEW,
        )
    ).all()
    for commitment in pending:
        alerts.append(
            _alert(
                project=project,
                rule=f"commitment_pending_approval:{commitment.id}",
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.BUDGET,
                title="Commitment pending approval",
                message=f"Commitment {commitment.commitment_number} awaits approval.",
                recommended_action="Review and approve or reject the commitment.",
                today=today,
            )
        )

    committed_lines = db.execute(
        select(
            ProjectCommitmentLine.budget_line_id,
            ProjectBudgetLine.current_budget,
            ProjectBudgetLine.line_number,
        )
        .join(ProjectCommitment, ProjectCommitment.id == ProjectCommitmentLine.commitment_id)
        .join(ProjectBudgetLine, ProjectBudgetLine.id == ProjectCommitmentLine.budget_line_id)
        .where(
            ProjectCommitment.project_id == project.id,
            ProjectCommitment.status.in_(list(COMMITTED_COST_STATUSES)),
            ProjectCommitmentLine.is_active.is_(True),
        )
    ).all()
    # Aggregate committed per budget line
    committed_map: dict[UUID, Decimal] = {}
    line_meta: dict[UUID, tuple[Decimal, str]] = {}
    for budget_line_id, current_budget, line_number in committed_lines:
        line_meta[budget_line_id] = (Decimal(str(current_budget or 0)), line_number)
    amounts = db.execute(
        select(
            ProjectCommitmentLine.budget_line_id,
            ProjectCommitmentLine.current_amount,
        )
        .join(ProjectCommitment, ProjectCommitment.id == ProjectCommitmentLine.commitment_id)
        .where(
            ProjectCommitment.project_id == project.id,
            ProjectCommitment.status.in_(list(COMMITTED_COST_STATUSES)),
            ProjectCommitmentLine.is_active.is_(True),
        )
    ).all()
    for budget_line_id, amount in amounts:
        committed_map[budget_line_id] = committed_map.get(budget_line_id, Decimal("0")) + Decimal(
            str(amount or 0)
        )
    for budget_line_id, committed in committed_map.items():
        current_budget, line_number = line_meta.get(budget_line_id, (Decimal("0"), "?"))
        if committed > current_budget:
            alerts.append(
                _alert(
                    project=project,
                    rule=f"commitment_over_budget:{budget_line_id}",
                    severity=AlertSeverity.HIGH,
                    category=AlertCategory.BUDGET,
                    title="Commitments exceed budget line",
                    message=(
                        f"Budget line {line_number} committed {committed} "
                        f"exceeds current budget {current_budget}."
                    ),
                    recommended_action="Approve a revision or reduce commitments.",
                    today=today,
                )
            )
    return alerts


def generate_alerts_for_project(
    project: Project,
    *,
    today: date,
    team_members: list[ProjectTeamMember],
    budget_spent: Decimal | None,
    budget_total: Decimal | None,
    db: Session | None = None,
    include_operational_cost_alerts: bool = False,
) -> list[ProjectAlertItem]:
    if project.archived_at is not None:
        return []

    alerts: list[ProjectAlertItem] = []
    active_team = [
        member
        for member in team_members
        if member.status == ProjectTeamMemberStatus.ACTIVE
    ]

    utilization: Decimal | None = None
    if budget_total is not None and budget_total > 0 and budget_spent is not None:
        utilization = (budget_spent / budget_total) * Decimal("100")

    if project.target_completion_date and project.target_completion_date < today:
        if project.project_status not in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}:
            alerts.append(
                _alert(
                    project=project,
                    rule="schedule_overdue",
                    severity=AlertSeverity.CRITICAL,
                    category=AlertCategory.SCHEDULE,
                    title="Project past estimated completion",
                    message=(
                        f"Estimated completion {project.target_completion_date.isoformat()} "
                        "has passed while the project remains active."
                    ),
                    recommended_action="Update schedule or mark the project completed.",
                    due_date=project.target_completion_date,
                    today=today,
                )
            )

    if (
        project.completion_percentage is None
        and project.project_status == ProjectStatus.CONSTRUCTION
    ):
        alerts.append(
            _alert(
                project=project,
                rule="missing_completion",
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.CONSTRUCTION,
                title="Completion percentage missing",
                message="Construction project has no completion percentage recorded.",
                recommended_action="Enter the latest completion percentage.",
                today=today,
            )
        )

    if project.project_manager_user_id is None and not (project.assigned_project_manager or "").strip():
        alerts.append(
            _alert(
                project=project,
                rule="missing_manager",
                severity=AlertSeverity.HIGH,
                category=AlertCategory.TEAM,
                title="No project manager assigned",
                message="Assign a project manager to keep ownership clear.",
                recommended_action="Set project manager on the project.",
                today=today,
            )
        )

    if not active_team:
        alerts.append(
            _alert(
                project=project,
                rule="missing_team",
                severity=AlertSeverity.LOW,
                category=AlertCategory.TEAM,
                title="No project team members",
                message="This project has no active team assignments.",
                recommended_action="Add at least one team member.",
                today=today,
            )
        )

    if project.start_date and project.target_completion_date:
        if project.target_completion_date < project.start_date:
            alerts.append(
                _alert(
                    project=project,
                    rule="inconsistent_schedule",
                    severity=AlertSeverity.HIGH,
                    category=AlertCategory.DATA_QUALITY,
                    title="Inconsistent schedule dates",
                    message="Target completion is before the estimated start date.",
                    recommended_action="Correct start or completion dates.",
                    today=today,
                )
            )

    if utilization is not None and utilization >= BUDGET_UTILIZATION_WARN:
        severity = (
            AlertSeverity.CRITICAL if utilization >= Decimal("100") else AlertSeverity.HIGH
        )
        alerts.append(
            _alert(
                project=project,
                rule="budget_utilization",
                severity=severity,
                category=AlertCategory.BUDGET,
                title="High budget utilization",
                message=f"Budget utilization is {utilization.quantize(Decimal('0.01'))}%.",
                recommended_action="Review spend and revise budget if needed.",
                today=today,
            )
        )

    if (
        project.construction_budget is None
        and project.total_development_cost is None
        and project.project_status
        in {ProjectStatus.CONSTRUCTION, ProjectStatus.PRE_DEVELOPMENT}
    ):
        alerts.append(
            _alert(
                project=project,
                rule="missing_budget",
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.BUDGET,
                title="Budget data missing",
                message="Active development project has no construction or total budget.",
                recommended_action="Enter construction budget or total development cost.",
                today=today,
            )
        )

    # Operational ERP cost alerts (overdue bills, pending commitment approvals)
    # stay out of the primary executive alert surface (Sprint 10A4C). Pass
    # include_operational_cost_alerts=True for Advanced Budget / construction ops.
    if db is not None and include_operational_cost_alerts:
        alerts.extend(_cost_alerts_for_project(db, project, today=today))

    return alerts


def generate_portfolio_alerts(
    projects: list[Project],
    *,
    today: date | None = None,
    team_by_project: dict[UUID, list[ProjectTeamMember]],
    budget_spent_by_project: dict[UUID, Decimal],
    budget_total_by_project: dict[UUID, Decimal],
    limit: int = 50,
    db: Session | None = None,
    include_operational_cost_alerts: bool = False,
) -> list[ProjectAlertItem]:
    today = today or date.today()
    alerts: list[ProjectAlertItem] = []
    seen: set[str] = set()
    for project in projects:
        project_alerts = generate_alerts_for_project(
            project,
            today=today,
            team_members=team_by_project.get(project.id, []),
            budget_spent=budget_spent_by_project.get(project.id),
            budget_total=budget_total_by_project.get(project.id),
            db=db,
            include_operational_cost_alerts=include_operational_cost_alerts,
        )
        for alert in project_alerts:
            if alert.id in seen:
                continue
            seen.add(alert.id)
            alerts.append(alert)

    severity_rank = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.HIGH: 1,
        AlertSeverity.MEDIUM: 2,
        AlertSeverity.LOW: 3,
        AlertSeverity.INFO: 4,
    }
    alerts.sort(key=lambda item: (severity_rank[item.severity], item.project_name))
    return alerts[:limit]
