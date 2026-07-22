"""Team management business logic."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from investhome_api.models.branch import Branch
from investhome_api.models.company import Company
from investhome_api.models.project import Project
from investhome_api.models.team import (
    CompanyTeam,
    TeamCapacitySnapshot,
    TeamCapacityStatus,
    TeamGoal,
    TeamGoalStatus,
    TeamKPI,
    TeamKpiStatus,
    TeamLeadAssignment,
    TeamLeadRole,
    TeamLeadStatus,
    TeamMember,
    TeamMemberStatus,
    TeamProjectLink,
    TeamProjectLinkStatus,
    TeamStatus,
    TeamTask,
    TeamTaskStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.team import (
    TeamCreate,
    TeamDashboardMetrics,
    TeamDetailResponse,
    TeamDisbandChecklistResponse,
    TeamGoalCreate,
    TeamKpiCreate,
    TeamLeadAssignRequest,
    TeamLeadResponse,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamMemberUpdate,
    TeamPerformanceResponse,
    TeamProjectAssignRequest,
    TeamProjectLinkResponse,
    TeamSummaryResponse,
    TeamTaskCreate,
    TeamTaskResponse,
    TeamTaskUpdate,
    TeamTreeNode,
    TeamUpdate,
    TeamWorkloadMember,
    TeamWorkloadResponse,
)

SORTABLE_FIELDS = {
    "team_code": CompanyTeam.team_code,
    "team_name": CompanyTeam.team_name,
    "status": CompanyTeam.status,
    "team_type": CompanyTeam.team_type,
    "member_count": CompanyTeam.member_count,
    "created_at": CompanyTeam.created_at,
    "updated_at": CompanyTeam.updated_at,
}

OPEN_TASK_STATUSES = {TeamTaskStatus.OPEN.value, TeamTaskStatus.IN_PROGRESS.value, TeamTaskStatus.BLOCKED.value}
ACTIVE_MEMBER_STATUSES = {TeamMemberStatus.ACTIVE.value, TeamMemberStatus.PENDING.value}
ACTIVE_GOAL_STATUSES = {TeamGoalStatus.DRAFT.value, TeamGoalStatus.ACTIVE.value}
ACTIVE_PROJECT_STATUSES = {TeamProjectLinkStatus.ACTIVE.value}


def paginate_total_pages(total: int, page_size: int) -> int:
    if total == 0:
        return 0
    return ceil(total / page_size)


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def get_team_or_none(db: Session, team_id: UUID) -> CompanyTeam | None:
    return db.scalar(
        select(CompanyTeam)
        .options(
            joinedload(CompanyTeam.lead_assignments),
            joinedload(CompanyTeam.members),
            joinedload(CompanyTeam.project_links),
            joinedload(CompanyTeam.tasks),
            joinedload(CompanyTeam.goals),
            joinedload(CompanyTeam.kpis),
        )
        .where(CompanyTeam.id == team_id)
    )


def _user_allocation_total(db: Session, user_id: UUID, *, exclude_team_id: UUID | None = None) -> Decimal:
    query = select(func.coalesce(func.sum(TeamMember.allocation_percentage), 0)).where(
        TeamMember.user_id == user_id,
        TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES)),
    )
    if exclude_team_id:
        query = query.where(TeamMember.team_id != exclude_team_id)
    return _decimal(db.scalar(query))


def validate_user_allocation(
    db: Session,
    user_id: UUID,
    allocation_percentage: Decimal,
    *,
    exclude_team_id: UUID | None = None,
) -> tuple[bool, list[str]]:
    existing = _user_allocation_total(db, user_id, exclude_team_id=exclude_team_id)
    total = existing + _decimal(allocation_percentage)
    warnings: list[str] = []
    if total > Decimal("100"):
        return False, ["team.errors.allocation_exceeds_100"]
    if total >= Decimal("80"):
        warnings.append("team.warnings.allocation_near_capacity")
    return True, warnings


def _would_create_cycle(db: Session, team_id: UUID, parent_team_id: UUID | None) -> bool:
    if parent_team_id is None or parent_team_id == team_id:
        return parent_team_id == team_id
    current = parent_team_id
    visited: set[UUID] = set()
    while current is not None:
        if current == team_id:
            return True
        if current in visited:
            return True
        visited.add(current)
        current = db.scalar(select(CompanyTeam.parent_team_id).where(CompanyTeam.id == current))
    return False


def _primary_lead(db: Session, team: CompanyTeam) -> TeamLeadAssignment | None:
    for assignment in team.lead_assignments:
        if (
            assignment.lead_role == TeamLeadRole.PRIMARY.value
            and assignment.status == TeamLeadStatus.ACTIVE.value
        ):
            return assignment
    return None


def compute_health_score(db: Session, team: CompanyTeam) -> TeamPerformanceResponse:
    tasks = team.tasks or db.scalars(select(TeamTask).where(TeamTask.team_id == team.id)).all()
    total_tasks = len(tasks)
    completed = sum(1 for task in tasks if task.status == TeamTaskStatus.COMPLETED.value)
    overdue = sum(
        1
        for task in tasks
        if task.due_date is not None
        and task.due_date < date.today()
        and task.status in OPEN_TASK_STATUSES
    )
    task_completion_rate = Decimal(completed / total_tasks) if total_tasks else Decimal("1")
    overdue_ratio = Decimal(overdue / total_tasks) if total_tasks else Decimal("0")

    available = _decimal(team.total_available_hours)
    allocated = _decimal(team.allocated_hours)
    if available > 0:
        utilization = allocated / available
        capacity_balance = max(Decimal("0"), Decimal("1") - abs(utilization - Decimal("0.85")))
    else:
        capacity_balance = Decimal("1") if allocated == 0 else Decimal("0.5")

    kpis = team.kpis or db.scalars(select(TeamKPI).where(TeamKPI.team_id == team.id)).all()
    if kpis:
        achievements = []
        for kpi in kpis:
            target = _decimal(kpi.target_value)
            if target > 0:
                achievements.append(min(_decimal(kpi.current_value) / target, Decimal("1")))
        kpi_achievement = sum(achievements) / Decimal(len(achievements)) if achievements else Decimal("1")
    else:
        kpi_achievement = Decimal("1")

    members = team.members or db.scalars(select(TeamMember).where(TeamMember.team_id == team.id)).all()
    active_members = [member for member in members if member.status in ACTIVE_MEMBER_STATUSES]
    ended = sum(1 for member in members if member.status == TeamMemberStatus.ENDED.value)
    member_stability = Decimal("1") - (Decimal(ended) / Decimal(len(members)) if members else Decimal("0"))

    project_links = team.project_links or db.scalars(
        select(TeamProjectLink).where(TeamProjectLink.team_id == team.id)
    ).all()
    if project_links:
        delivered = sum(1 for link in project_links if link.status == TeamProjectLinkStatus.COMPLETED.value)
        project_delivery = Decimal(delivered / len(project_links))
    else:
        project_delivery = Decimal("1")

    weighted = (
        task_completion_rate * Decimal("0.25")
        + (Decimal("1") - overdue_ratio) * Decimal("0.20")
        + capacity_balance * Decimal("0.20")
        + kpi_achievement * Decimal("0.15")
        + member_stability * Decimal("0.10")
        + project_delivery * Decimal("0.10")
    )
    health_score = int(max(0, min(100, round(float(weighted * 100)))))

    return TeamPerformanceResponse(
        health_score=health_score,
        task_completion_rate=task_completion_rate.quantize(Decimal("0.01")),
        overdue_ratio=overdue_ratio.quantize(Decimal("0.01")),
        capacity_balance=capacity_balance.quantize(Decimal("0.01")),
        kpi_achievement=kpi_achievement.quantize(Decimal("0.01")),
        member_stability=member_stability.quantize(Decimal("0.01")),
        project_delivery=project_delivery.quantize(Decimal("0.01")),
    )


def refresh_team_counters(db: Session, team: CompanyTeam) -> None:
    team.member_count = db.scalar(
        select(func.count())
        .select_from(TeamMember)
        .where(TeamMember.team_id == team.id, TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES)))
    ) or 0
    team.active_projects_count = db.scalar(
        select(func.count())
        .select_from(TeamProjectLink)
        .where(TeamProjectLink.team_id == team.id, TeamProjectLink.status.in_(list(ACTIVE_PROJECT_STATUSES)))
    ) or 0
    team.open_tasks_count = db.scalar(
        select(func.count())
        .select_from(TeamTask)
        .where(TeamTask.team_id == team.id, TeamTask.status.in_(list(OPEN_TASK_STATUSES)))
    ) or 0
    allocated = db.scalar(
        select(func.coalesce(func.sum(TeamMember.workload_hours), 0)).where(
            TeamMember.team_id == team.id,
            TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES)),
        )
    )
    team.allocated_hours = _decimal(allocated)


def _serialize_summary(db: Session, team: CompanyTeam) -> TeamSummaryResponse:
    company = db.get(Company, team.company_id)
    branch_name = None
    if team.branch_id:
        branch = db.get(Branch, team.branch_id)
        branch_name = branch.branch_name if branch else None
    lead = _primary_lead(db, team)
    lead_name = None
    if lead:
        user = db.get(User, lead.user_id)
        lead_name = user.full_name if user else None
    performance = compute_health_score(db, team)
    return TeamSummaryResponse(
        id=team.id,
        team_code=team.team_code,
        team_name=team.team_name,
        company_id=team.company_id,
        company_name=company.company_name if company else None,
        branch_id=team.branch_id,
        branch_name=branch_name,
        department_id=team.department_id,
        team_type=team.team_type,
        parent_team_id=team.parent_team_id,
        cost_center=team.cost_center,
        status=team.status,
        start_date=team.start_date,
        end_date=team.end_date,
        total_available_hours=_decimal(team.total_available_hours),
        allocated_hours=_decimal(team.allocated_hours),
        member_count=team.member_count,
        active_projects_count=team.active_projects_count,
        open_tasks_count=team.open_tasks_count,
        health_score=performance.health_score,
        primary_lead_user_id=lead.user_id if lead else None,
        primary_lead_name=lead_name,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


def serialize_team_detail(db: Session, team: CompanyTeam, *, warnings: list[str] | None = None) -> TeamDetailResponse:
    summary = _serialize_summary(db, team)
    child_count = db.scalar(
        select(func.count()).select_from(CompanyTeam).where(CompanyTeam.parent_team_id == team.id)
    ) or 0
    return TeamDetailResponse(
        **summary.model_dump(),
        description=team.description,
        merged_into_team_id=team.merged_into_team_id,
        disband_reason=team.disband_reason,
        disband_effective_date=team.disband_effective_date,
        archived_at=team.archived_at,
        child_team_count=child_count,
        allocation_warnings=warnings or [],
    )


def list_teams(
    db: Session,
    *,
    search: str | None = None,
    company_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    team_type: str | None = None,
    status: str | None = None,
    parent_team_id: UUID | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[TeamSummaryResponse], int]:
    query = select(CompanyTeam)
    if not include_archived:
        query = query.where(CompanyTeam.archived_at.is_(None))
    if company_id:
        query = query.where(CompanyTeam.company_id == company_id)
    if branch_id:
        query = query.where(CompanyTeam.branch_id == branch_id)
    if department_id:
        query = query.where(CompanyTeam.department_id == department_id)
    if team_type:
        query = query.where(CompanyTeam.team_type == team_type)
    if status:
        query = query.where(CompanyTeam.status == status)
    if parent_team_id:
        query = query.where(CompanyTeam.parent_team_id == parent_team_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                CompanyTeam.team_code.ilike(pattern),
                CompanyTeam.team_name.ilike(pattern),
                CompanyTeam.description.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_column = SORTABLE_FIELDS.get(sort_by, CompanyTeam.updated_at)
    order = desc(sort_column) if sort_dir == "desc" else asc(sort_column)
    teams = db.scalars(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return [_serialize_summary(db, team) for team in teams], total


def build_team_tree(db: Session, *, company_id: UUID | None = None) -> list[TeamTreeNode]:
    query = select(CompanyTeam).where(CompanyTeam.archived_at.is_(None))
    if company_id:
        query = query.where(CompanyTeam.company_id == company_id)
    teams = db.scalars(query).all()
    nodes: dict[UUID, TeamTreeNode] = {}
    for team in teams:
        performance = compute_health_score(db, team)
        nodes[team.id] = TeamTreeNode(
            id=team.id,
            team_code=team.team_code,
            team_name=team.team_name,
            status=team.status,
            member_count=team.member_count,
            health_score=performance.health_score,
            children=[],
        )
    roots: list[TeamTreeNode] = []
    for team in teams:
        node = nodes[team.id]
        if team.parent_team_id and team.parent_team_id in nodes:
            nodes[team.parent_team_id].children.append(node)
        else:
            roots.append(node)
    return roots


def build_dashboard_metrics(db: Session, *, company_id: UUID | None = None) -> TeamDashboardMetrics:
    base = select(CompanyTeam).where(CompanyTeam.archived_at.is_(None))
    if company_id:
        base = base.where(CompanyTeam.company_id == company_id)
    teams = db.scalars(base).all()
    total_teams = len(teams)
    active_teams = sum(1 for team in teams if team.status == TeamStatus.ACTIVE.value)
    forming_teams = sum(1 for team in teams if team.status == TeamStatus.FORMING.value)
    total_members = sum(team.member_count for team in teams)
    open_tasks = sum(team.open_tasks_count for team in teams)
    active_projects = sum(team.active_projects_count for team in teams)
    health_scores = [compute_health_score(db, team).health_score for team in teams]
    avg_health = int(sum(health_scores) / len(health_scores)) if health_scores else 0

    over_allocated = 0
    member_rows = db.scalars(
        select(TeamMember).where(TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES)))
    ).all()
    user_totals: dict[UUID, Decimal] = {}
    for row in member_rows:
        user_totals[row.user_id] = user_totals.get(row.user_id, Decimal("0")) + _decimal(row.allocation_percentage)
    over_allocated = sum(1 for total in user_totals.values() if total > Decimal("100"))

    return TeamDashboardMetrics(
        total_teams=total_teams,
        active_teams=active_teams,
        forming_teams=forming_teams,
        total_members=total_members,
        avg_health_score=avg_health,
        over_allocated_members=over_allocated,
        open_tasks=open_tasks,
        active_projects=active_projects,
    )


def _assert_company_exists(db: Session, company_id: UUID) -> None:
    if db.get(Company, company_id) is None:
        raise ValueError("team.errors.company_not_found")


def _assert_unique_code(db: Session, company_id: UUID, team_code: str, exclude_id: UUID | None = None) -> None:
    query = select(CompanyTeam.id).where(
        CompanyTeam.company_id == company_id,
        func.upper(CompanyTeam.team_code) == _normalize_code(team_code),
    )
    if exclude_id:
        query = query.where(CompanyTeam.id != exclude_id)
    if db.scalar(query):
        raise ValueError("team.errors.duplicate_code")


def create_team(db: Session, payload: TeamCreate) -> tuple[CompanyTeam, list[str]]:
    _assert_company_exists(db, payload.company_id)
    _assert_unique_code(db, payload.company_id, payload.team_code)
    if payload.parent_team_id:
        parent = get_team_or_none(db, payload.parent_team_id)
        if parent is None:
            raise ValueError("team.errors.parent_not_found")
        if parent.company_id != payload.company_id:
            raise ValueError("team.errors.parent_company_mismatch")

    team = CompanyTeam(
        team_code=_normalize_code(payload.team_code),
        team_name=payload.team_name.strip(),
        description=payload.description,
        company_id=payload.company_id,
        branch_id=payload.branch_id,
        department_id=payload.department_id,
        team_type=payload.team_type.value,
        parent_team_id=payload.parent_team_id,
        cost_center=payload.cost_center,
        status=payload.status.value,
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_available_hours=_decimal(payload.total_available_hours),
    )
    if payload.parent_team_id and _would_create_cycle(db, team.id, payload.parent_team_id):
        raise ValueError("team.errors.circular_parent")
    db.add(team)
    db.flush()
    refresh_team_counters(db, team)
    return team, []


def update_team(db: Session, team: CompanyTeam, payload: TeamUpdate) -> tuple[CompanyTeam, list[str]]:
    warnings: list[str] = []
    if payload.team_code is not None:
        _assert_unique_code(db, team.company_id, payload.team_code, exclude_id=team.id)
        team.team_code = _normalize_code(payload.team_code)
    if payload.team_name is not None:
        team.team_name = payload.team_name.strip()
    if payload.description is not None:
        team.description = payload.description
    if payload.branch_id is not None:
        team.branch_id = payload.branch_id
    if payload.department_id is not None:
        team.department_id = payload.department_id
    if payload.team_type is not None:
        team.team_type = payload.team_type.value
    if payload.parent_team_id is not None:
        if payload.parent_team_id == team.id or _would_create_cycle(db, team.id, payload.parent_team_id):
            raise ValueError("team.errors.circular_parent")
        team.parent_team_id = payload.parent_team_id
    if payload.cost_center is not None:
        team.cost_center = payload.cost_center
    if payload.status is not None:
        team.status = payload.status.value
    if payload.start_date is not None:
        team.start_date = payload.start_date
    if payload.end_date is not None:
        team.end_date = payload.end_date
    if payload.total_available_hours is not None:
        team.total_available_hours = _decimal(payload.total_available_hours)
    refresh_team_counters(db, team)
    return team, warnings


def get_delete_blockers(db: Session, team: CompanyTeam) -> list[str]:
    blockers: list[str] = []
    if team.member_count > 0:
        blockers.append("team.errors.has_active_members")
    if team.active_projects_count > 0:
        blockers.append("team.errors.has_active_projects")
    if team.open_tasks_count > 0:
        blockers.append("team.errors.has_open_tasks")
    active_goals = db.scalar(
        select(func.count())
        .select_from(TeamGoal)
        .where(TeamGoal.team_id == team.id, TeamGoal.status.in_(list(ACTIVE_GOAL_STATUSES)))
    ) or 0
    if active_goals:
        blockers.append("team.errors.has_active_goals")
    child_count = db.scalar(
        select(func.count()).select_from(CompanyTeam).where(CompanyTeam.parent_team_id == team.id)
    ) or 0
    if child_count:
        blockers.append("team.errors.has_child_teams")
    return blockers


def delete_team(db: Session, team: CompanyTeam) -> None:
    blockers = get_delete_blockers(db, team)
    if blockers:
        raise ValueError(blockers[0])
    db.delete(team)


def assign_lead(db: Session, team: CompanyTeam, payload: TeamLeadAssignRequest) -> TeamLeadAssignment:
    if db.get(User, payload.user_id) is None:
        raise ValueError("team.errors.user_not_found")
    if payload.lead_role == TeamLeadRole.PRIMARY:
        for assignment in team.lead_assignments:
            if assignment.lead_role == TeamLeadRole.PRIMARY.value and assignment.status == TeamLeadStatus.ACTIVE.value:
                assignment.status = TeamLeadStatus.ENDED.value
    assignment = TeamLeadAssignment(
        team_id=team.id,
        user_id=payload.user_id,
        lead_role=payload.lead_role.value,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_temporary=payload.is_temporary,
        status=TeamLeadStatus.ACTIVE.value,
    )
    db.add(assignment)
    db.flush()
    return assignment


def serialize_lead(db: Session, assignment: TeamLeadAssignment) -> TeamLeadResponse:
    user = db.get(User, assignment.user_id)
    return TeamLeadResponse(
        id=assignment.id,
        team_id=assignment.team_id,
        user_id=assignment.user_id,
        user_name=user.full_name if user else None,
        lead_role=assignment.lead_role,
        start_date=assignment.start_date,
        end_date=assignment.end_date,
        is_temporary=assignment.is_temporary,
        status=assignment.status,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


def add_member(db: Session, team: CompanyTeam, payload: TeamMemberCreate) -> tuple[TeamMember, list[str]]:
    if db.get(User, payload.user_id) is None:
        raise ValueError("team.errors.user_not_found")
    existing = db.scalar(
        select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == payload.user_id)
    )
    if existing and existing.status in ACTIVE_MEMBER_STATUSES:
        raise ValueError("team.errors.member_exists")
    ok, warnings = validate_user_allocation(
        db, payload.user_id, payload.allocation_percentage, exclude_team_id=team.id
    )
    if not ok:
        raise ValueError(warnings[0])
    member = TeamMember(
        team_id=team.id,
        user_id=payload.user_id,
        role_in_team=payload.role_in_team,
        membership_type=payload.membership_type.value,
        allocation_percentage=_decimal(payload.allocation_percentage),
        start_date=payload.start_date,
        end_date=payload.end_date,
        workload_hours=_decimal(payload.workload_hours),
        status=payload.status.value,
    )
    db.add(member)
    db.flush()
    refresh_team_counters(db, team)
    return member, warnings


def update_member(db: Session, member: TeamMember, payload: TeamMemberUpdate) -> tuple[TeamMember, list[str]]:
    allocation = payload.allocation_percentage if payload.allocation_percentage is not None else member.allocation_percentage
    ok, warnings = validate_user_allocation(
        db, member.user_id, _decimal(allocation), exclude_team_id=member.team_id
    )
    if not ok:
        raise ValueError(warnings[0])
    if payload.role_in_team is not None:
        member.role_in_team = payload.role_in_team
    if payload.membership_type is not None:
        member.membership_type = payload.membership_type.value
    if payload.allocation_percentage is not None:
        member.allocation_percentage = _decimal(payload.allocation_percentage)
    if payload.start_date is not None:
        member.start_date = payload.start_date
    if payload.end_date is not None:
        member.end_date = payload.end_date
    if payload.workload_hours is not None:
        member.workload_hours = _decimal(payload.workload_hours)
    if payload.status is not None:
        member.status = payload.status.value
    team = get_team_or_none(db, member.team_id)
    if team:
        refresh_team_counters(db, team)
    return member, warnings


def serialize_member(db: Session, member: TeamMember) -> TeamMemberResponse:
    user = db.get(User, member.user_id)
    total = _user_allocation_total(db, member.user_id)
    warning = None
    if total > Decimal("100"):
        warning = "team.warnings.allocation_exceeds_100"
    elif total >= Decimal("80"):
        warning = "team.warnings.allocation_near_capacity"
    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        user_id=member.user_id,
        user_name=user.full_name if user else None,
        role_in_team=member.role_in_team,
        membership_type=member.membership_type,
        allocation_percentage=_decimal(member.allocation_percentage),
        start_date=member.start_date,
        end_date=member.end_date,
        workload_hours=_decimal(member.workload_hours),
        status=member.status,
        total_allocation_across_teams=total,
        allocation_warning=warning,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


def remove_member(db: Session, member: TeamMember) -> None:
    team = get_team_or_none(db, member.team_id)
    member.status = TeamMemberStatus.ENDED.value
    if team:
        refresh_team_counters(db, team)


def transfer_member(
    db: Session,
    source_team: CompanyTeam,
    *,
    user_id: UUID,
    target_team_id: UUID,
    allocation_percentage: Decimal | None,
) -> TeamMember:
    target = get_team_or_none(db, target_team_id)
    if target is None:
        raise ValueError("team.errors.target_not_found")
    member = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == source_team.id,
            TeamMember.user_id == user_id,
            TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES)),
        )
    )
    if member is None:
        raise ValueError("team.errors.member_not_found")
    allocation = allocation_percentage if allocation_percentage is not None else member.allocation_percentage
    member.status = TeamMemberStatus.ENDED.value
    new_member, _ = add_member(
        db,
        target,
        TeamMemberCreate(
            user_id=user_id,
            role_in_team=member.role_in_team,
            membership_type=member.membership_type,  # type: ignore[arg-type]
            allocation_percentage=allocation,
            start_date=date.today(),
            workload_hours=member.workload_hours,
        ),
    )
    refresh_team_counters(db, source_team)
    return new_member


def assign_project(db: Session, team: CompanyTeam, payload: TeamProjectAssignRequest) -> TeamProjectLink:
    if payload.project_id is None and not payload.project_stub_name:
        raise ValueError("team.errors.project_required")
    if payload.project_id and db.get(Project, payload.project_id) is None:
        raise ValueError("team.errors.project_not_found")
    link = TeamProjectLink(
        team_id=team.id,
        project_id=payload.project_id,
        project_stub_name=payload.project_stub_name,
        role=payload.role,
        start_date=payload.start_date,
        end_date=payload.end_date,
        allocation_percentage=_decimal(payload.allocation_percentage),
        budget=payload.budget,
        status=TeamProjectLinkStatus.ACTIVE.value,
    )
    db.add(link)
    db.flush()
    refresh_team_counters(db, team)
    return link


def serialize_project_link(db: Session, link: TeamProjectLink) -> TeamProjectLinkResponse:
    project_name = None
    if link.project_id:
        project = db.get(Project, link.project_id)
        project_name = project.name if project else None
    return TeamProjectLinkResponse(
        id=link.id,
        team_id=link.team_id,
        project_id=link.project_id,
        project_name=project_name,
        project_stub_name=link.project_stub_name,
        role=link.role,
        start_date=link.start_date,
        end_date=link.end_date,
        allocation_percentage=_decimal(link.allocation_percentage),
        budget=_decimal(link.budget) if link.budget is not None else None,
        status=link.status,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def create_task(db: Session, team: CompanyTeam, payload: TeamTaskCreate) -> TeamTask:
    task = TeamTask(
        team_id=team.id,
        assigned_user_id=payload.assigned_user_id,
        work_item_id=payload.work_item_id,
        title=payload.title.strip(),
        priority=payload.priority.value,
        due_date=payload.due_date,
        status=payload.status.value,
        estimated_hours=_decimal(payload.estimated_hours),
        actual_hours=_decimal(payload.actual_hours),
        project_id=payload.project_id,
    )
    db.add(task)
    db.flush()
    refresh_team_counters(db, team)
    return task


def update_task(db: Session, task: TeamTask, payload: TeamTaskUpdate) -> TeamTask:
    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.assigned_user_id is not None:
        task.assigned_user_id = payload.assigned_user_id
    if payload.priority is not None:
        task.priority = payload.priority.value
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.status is not None:
        task.status = payload.status.value
    if payload.estimated_hours is not None:
        task.estimated_hours = _decimal(payload.estimated_hours)
    if payload.actual_hours is not None:
        task.actual_hours = _decimal(payload.actual_hours)
    if payload.project_id is not None:
        task.project_id = payload.project_id
    if payload.work_item_id is not None:
        task.work_item_id = payload.work_item_id
    team = get_team_or_none(db, task.team_id)
    if team:
        refresh_team_counters(db, team)
    return task


def serialize_task(db: Session, task: TeamTask) -> TeamTaskResponse:
    user_name = None
    if task.assigned_user_id:
        user = db.get(User, task.assigned_user_id)
        user_name = user.full_name if user else None
    is_overdue = (
        task.due_date is not None
        and task.due_date < date.today()
        and task.status in OPEN_TASK_STATUSES
    )
    return TeamTaskResponse(
        id=task.id,
        team_id=task.team_id,
        assigned_user_id=task.assigned_user_id,
        assigned_user_name=user_name,
        work_item_id=task.work_item_id,
        title=task.title,
        priority=task.priority,
        due_date=task.due_date,
        status=task.status,
        estimated_hours=_decimal(task.estimated_hours),
        actual_hours=_decimal(task.actual_hours),
        project_id=task.project_id,
        is_overdue=is_overdue,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def create_goal(db: Session, team: CompanyTeam, payload: TeamGoalCreate) -> TeamGoal:
    goal = TeamGoal(
        team_id=team.id,
        title=payload.title.strip(),
        description=payload.description,
        target_value=payload.target_value,
        current_value=_decimal(payload.current_value),
        unit=payload.unit,
        due_date=payload.due_date,
        status=payload.status.value,
    )
    db.add(goal)
    db.flush()
    return goal


def create_kpi(db: Session, team: CompanyTeam, payload: TeamKpiCreate) -> TeamKPI:
    kpi = TeamKPI(
        team_id=team.id,
        name=payload.name.strip(),
        description=payload.description,
        target_value=_decimal(payload.target_value),
        current_value=_decimal(payload.current_value),
        unit=payload.unit,
        period=payload.period,
        status=payload.status.value,
    )
    db.add(kpi)
    db.flush()
    return kpi


def move_team(
    db: Session,
    team: CompanyTeam,
    *,
    company_id: UUID | None,
    branch_id: UUID | None,
    department_id: UUID | None,
    parent_team_id: UUID | None,
) -> CompanyTeam:
    if company_id is not None:
        _assert_company_exists(db, company_id)
        team.company_id = company_id
    if branch_id is not None:
        team.branch_id = branch_id
    if department_id is not None:
        team.department_id = department_id
    if parent_team_id is not None:
        if parent_team_id == team.id or _would_create_cycle(db, team.id, parent_team_id):
            raise ValueError("team.errors.circular_parent")
        team.parent_team_id = parent_team_id
    return team


def merge_teams(db: Session, *, source: CompanyTeam, target: CompanyTeam, reason: str | None) -> CompanyTeam:
    if source.id == target.id:
        raise ValueError("team.errors.merge_same_team")
    if source.company_id != target.company_id:
        raise ValueError("team.errors.merge_company_mismatch")

    for member in list(source.members):
        if member.status not in ACTIVE_MEMBER_STATUSES:
            continue
        existing = db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == target.id,
                TeamMember.user_id == member.user_id,
                TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES)),
            )
        )
        if existing:
            member.status = TeamMemberStatus.ENDED.value
            continue
        member.team_id = target.id

    for link in list(source.project_links):
        link.team_id = target.id
    for task in list(source.tasks):
        task.team_id = target.id
    for goal in list(source.goals):
        goal.team_id = target.id
    for kpi in list(source.kpis):
        kpi.team_id = target.id
    for child in db.scalars(select(CompanyTeam).where(CompanyTeam.parent_team_id == source.id)).all():
        child.parent_team_id = target.id

    source.status = TeamStatus.MERGED.value
    source.merged_into_team_id = target.id
    source.disband_reason = reason
    refresh_team_counters(db, target)
    refresh_team_counters(db, source)
    return target


def disband_checklist(db: Session, team: CompanyTeam) -> TeamDisbandChecklistResponse:
    blockers = get_delete_blockers(db, team)
    active_goals = db.scalar(
        select(func.count())
        .select_from(TeamGoal)
        .where(TeamGoal.team_id == team.id, TeamGoal.status.in_(list(ACTIVE_GOAL_STATUSES)))
    ) or 0
    child_count = db.scalar(
        select(func.count()).select_from(CompanyTeam).where(CompanyTeam.parent_team_id == team.id)
    ) or 0
    return TeamDisbandChecklistResponse(
        can_disband=len(blockers) == 0,
        blockers=blockers,
        active_members=team.member_count,
        active_projects=team.active_projects_count,
        open_tasks=team.open_tasks_count,
        active_goals=active_goals,
        child_teams=child_count,
    )


def disband_team(
    db: Session,
    team: CompanyTeam,
    *,
    reason: str,
    effective_date: date,
    transfer_members_to_team_id: UUID | None,
    reassign_tasks_to_user_id: UUID | None,
    close_goals: bool,
) -> CompanyTeam:
    checklist = disband_checklist(db, team)
    if not checklist.can_disband:
        raise ValueError(checklist.blockers[0])

    if transfer_members_to_team_id:
        target = get_team_or_none(db, transfer_members_to_team_id)
        if target is None:
            raise ValueError("team.errors.target_not_found")
        for member in list(team.members):
            if member.status in ACTIVE_MEMBER_STATUSES:
                transfer_member(
                    db,
                    team,
                    user_id=member.user_id,
                    target_team_id=transfer_members_to_team_id,
                    allocation_percentage=member.allocation_percentage,
                )

    for task in team.tasks:
        if task.status in OPEN_TASK_STATUSES:
            if reassign_tasks_to_user_id:
                task.assigned_user_id = reassign_tasks_to_user_id
            task.status = TeamTaskStatus.CANCELLED.value

    for link in team.project_links:
        if link.status in ACTIVE_PROJECT_STATUSES:
            link.status = TeamProjectLinkStatus.CANCELLED.value

    if close_goals:
        for goal in team.goals:
            if goal.status in ACTIVE_GOAL_STATUSES:
                goal.status = TeamGoalStatus.CANCELLED.value

    team.status = TeamStatus.DISBANDED.value
    team.disband_reason = reason
    team.disband_effective_date = effective_date
    team.archived_at = datetime.now(UTC)
    refresh_team_counters(db, team)
    return team


def build_capacity_snapshot(db: Session, team: CompanyTeam, period: str) -> TeamCapacitySnapshot:
    available = _decimal(team.total_available_hours)
    allocated = _decimal(team.allocated_hours)
    remaining = max(Decimal("0"), available - allocated)
    utilization = (allocated / available * Decimal("100")) if available > 0 else Decimal("0")
    if utilization > Decimal("100"):
        status = TeamCapacityStatus.OVER_ALLOCATED.value
    elif utilization >= Decimal("85"):
        status = TeamCapacityStatus.NEAR_CAPACITY.value
    elif utilization >= Decimal("50"):
        status = TeamCapacityStatus.BALANCED.value
    else:
        status = TeamCapacityStatus.UNDER_UTILIZED.value
    snapshot = TeamCapacitySnapshot(
        team_id=team.id,
        period=period,
        available_hours=available,
        allocated_hours=allocated,
        remaining_hours=remaining,
        utilization_percentage=utilization.quantize(Decimal("0.01")),
        status=status,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def build_workload_view(db: Session, *, period: str, team_id: UUID | None = None) -> TeamWorkloadResponse:
    query = select(TeamMember, User.full_name, CompanyTeam.team_name).join(
        User, TeamMember.user_id == User.id
    ).join(CompanyTeam, TeamMember.team_id == CompanyTeam.id).where(
        TeamMember.status.in_(list(ACTIVE_MEMBER_STATUSES))
    )
    if team_id:
        query = query.where(TeamMember.team_id == team_id)
    rows = db.execute(query).all()
    grouped: dict[UUID, TeamWorkloadMember] = {}
    for member, full_name, team_name in rows:
        if member.user_id not in grouped:
            grouped[member.user_id] = TeamWorkloadMember(
                user_id=member.user_id,
                user_name=full_name,
                total_allocation=Decimal("0"),
                total_hours=Decimal("0"),
                teams=[],
                heat_level=0,
            )
        entry = grouped[member.user_id]
        entry.total_allocation += _decimal(member.allocation_percentage)
        entry.total_hours += _decimal(member.workload_hours)
        if team_name not in entry.teams:
            entry.teams.append(team_name)
    for entry in grouped.values():
        total = float(entry.total_allocation)
        if total >= 100:
            entry.heat_level = 4
        elif total >= 80:
            entry.heat_level = 3
        elif total >= 50:
            entry.heat_level = 2
        elif total > 0:
            entry.heat_level = 1
    return TeamWorkloadResponse(period=period, members=list(grouped.values()), team_id=team_id)
