"""Department management business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.branch import Branch
from investhome_api.models.company import Company
from investhome_api.models.department import (
    AssignmentStatus,
    CompanyDepartment as Department,
    DepartmentBudget,
    DepartmentEmployeeAssignment,
    DepartmentKPI,
    DepartmentProjectLink,
    DepartmentResponsibility,
    DepartmentStatus,
    KPIStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.department import (
    AssignEmployeesRequest,
    DepartmentCreate,
    DepartmentDashboardMetrics,
    DepartmentDetailResponse,
    DepartmentEmployeeResponse,
    DepartmentKPIResponse,
    DepartmentSummaryResponse,
    DepartmentTreeNode,
    DepartmentUpdate,
    EmployeeAssignmentItem,
    MoveDepartmentRequest,
)


SORTABLE_FIELDS = {
    "department_code": Department.department_code,
    "department_name": Department.department_name,
    "department_type": Department.department_type,
    "status": Department.status,
    "employee_count": Department.employee_count,
    "team_count": Department.team_count,
    "created_at": Department.created_at,
    "updated_at": Department.updated_at,
}


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def paginate_total_pages(total: int, page_size: int) -> int:
    return max(1, ceil(total / page_size))


def _get_user_name(db: Session, user_id: UUID | None) -> str | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user.full_name if user else None


def _serialize_summary(
    dept: Department,
    *,
    company_name: str | None = None,
    branch_name: str | None = None,
    head_name: str | None = None,
) -> DepartmentSummaryResponse:
    return DepartmentSummaryResponse(
        id=dept.id,
        department_code=dept.department_code,
        department_name=dept.department_name,
        company_id=dept.company_id,
        company_name=company_name,
        branch_id=dept.branch_id,
        branch_name=branch_name,
        department_type=dept.department_type,
        parent_department_id=dept.parent_department_id,
        department_head_user_id=dept.department_head_user_id,
        head_name=head_name,
        cost_center=dept.cost_center,
        status=dept.status,
        employee_count=dept.employee_count,
        team_count=dept.team_count,
        open_positions=dept.open_positions,
        annual_budget=dept.annual_budget,
        currency=dept.currency,
        fiscal_year=dept.fiscal_year,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


def serialize_department_detail(db: Session, dept: Department) -> DepartmentDetailResponse:
    company = db.get(Company, dept.company_id)
    branch_name = None
    if dept.branch_id:
        branch = db.get(Branch, dept.branch_id)
        branch_name = branch.branch_name if branch else None
    child_count = db.scalar(
        select(func.count()).where(
            Department.parent_department_id == dept.id,
            Department.archived_at.is_(None),
        )
    ) or 0
    summary = _serialize_summary(
        dept,
        company_name=company.company_name if company else None,
        branch_name=branch_name,
        head_name=_get_user_name(db, dept.department_head_user_id),
    )
    return DepartmentDetailResponse(
        **summary.model_dump(),
        description=dept.description,
        start_date=dept.start_date,
        end_date=dept.end_date,
        merged_into_department_id=dept.merged_into_department_id,
        notes=dept.notes,
        archived_at=dept.archived_at,
        child_count=child_count,
    )


def get_department_or_none(db: Session, department_id: UUID) -> Department | None:
    return db.get(Department, department_id)


def _validate_parent(db: Session, dept: Department, parent_id: UUID | None) -> None:
    if parent_id is None:
        return
    if parent_id == dept.id:
        raise ValueError("department.errors.circular_parent")
    parent = db.get(Department, parent_id)
    if parent is None or parent.archived_at is not None:
        raise ValueError("department.errors.parent_not_found")
    if parent.company_id != dept.company_id:
        raise ValueError("department.errors.parent_company_mismatch")
    # Walk up the tree to detect cycles
    current_id = parent.parent_department_id
    visited = {parent_id, dept.id}
    while current_id:
        if current_id in visited:
            raise ValueError("department.errors.circular_parent")
        visited.add(current_id)
        ancestor = db.get(Department, current_id)
        if ancestor is None:
            break
        current_id = ancestor.parent_department_id


def _check_duplicate_code(db: Session, company_id: UUID, code: str, exclude_id: UUID | None = None) -> None:
    query = select(Department.id).where(
        Department.company_id == company_id,
        Department.department_code == code,
        Department.archived_at.is_(None),
    )
    if exclude_id:
        query = query.where(Department.id != exclude_id)
    if db.scalar(query):
        raise ValueError("department.errors.duplicate_code")


def list_departments(
    db: Session,
    *,
    search: str | None = None,
    company_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_type: str | None = None,
    status: str | None = None,
    parent_department_id: UUID | None = None,
    head_user_id: UUID | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[DepartmentSummaryResponse], int]:
    query = (
        select(Department, Company.company_name, Branch.branch_name, User.full_name)
        .join(Company, Department.company_id == Company.id)
        .outerjoin(Branch, Department.branch_id == Branch.id)
        .outerjoin(User, Department.department_head_user_id == User.id)
    )

    if not include_archived:
        query = query.where(Department.archived_at.is_(None))
    if company_id:
        query = query.where(Department.company_id == company_id)
    if branch_id:
        query = query.where(Department.branch_id == branch_id)
    if department_type:
        query = query.where(Department.department_type == department_type)
    if status:
        query = query.where(Department.status == status)
    if parent_department_id:
        query = query.where(Department.parent_department_id == parent_department_id)
    if head_user_id:
        query = query.where(Department.department_head_user_id == head_user_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Department.department_name.ilike(pattern),
                Department.department_code.ilike(pattern),
                Department.cost_center.ilike(pattern),
                Company.company_name.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    sort_column = SORTABLE_FIELDS.get(sort_by, Department.updated_at)
    order = desc(sort_column) if sort_dir.lower() == "desc" else asc(sort_column)
    query = query.order_by(order).offset((page - 1) * page_size).limit(page_size)

    items: list[DepartmentSummaryResponse] = []
    for dept, company_name, branch_name, head_name in db.execute(query).all():
        items.append(_serialize_summary(dept, company_name=company_name, branch_name=branch_name, head_name=head_name))
    return items, total


def build_department_tree(db: Session, company_id: UUID) -> tuple[list[DepartmentTreeNode], int]:
    depts = db.scalars(
        select(Department)
        .where(Department.company_id == company_id, Department.archived_at.is_(None))
        .order_by(Department.department_name)
    ).all()

    nodes: dict[UUID, DepartmentTreeNode] = {}
    for dept in depts:
        nodes[dept.id] = DepartmentTreeNode(
            id=dept.id,
            department_code=dept.department_code,
            department_name=dept.department_name,
            department_type=dept.department_type,
            status=dept.status,
            parent_department_id=dept.parent_department_id,
            department_head_user_id=dept.department_head_user_id,
            head_name=_get_user_name(db, dept.department_head_user_id),
            employee_count=dept.employee_count,
            team_count=dept.team_count,
            children=[],
        )

    roots: list[DepartmentTreeNode] = []
    for dept in depts:
        node = nodes[dept.id]
        if dept.parent_department_id and dept.parent_department_id in nodes:
            nodes[dept.parent_department_id].children.append(node)
        else:
            roots.append(node)

    return roots, len(depts)


def create_department(db: Session, payload: DepartmentCreate) -> Department:
    company = db.get(Company, payload.company_id)
    if company is None:
        raise ValueError("department.errors.company_not_found")

    if payload.branch_id:
        branch = db.get(Branch, payload.branch_id)
        if branch is None or branch.company_id != payload.company_id:
            raise ValueError("department.errors.branch_not_found")

    code = _normalize_code(payload.department_code)
    _check_duplicate_code(db, payload.company_id, code)

    data = payload.model_dump()
    data["department_code"] = code
    dept = Department(**data)
    db.add(dept)
    db.flush()

    _validate_parent(db, dept, payload.parent_department_id)
    return dept


def update_department(db: Session, dept: Department, payload: DepartmentUpdate) -> Department:
    data = payload.model_dump(exclude_unset=True)
    if "department_code" in data:
        data["department_code"] = _normalize_code(data["department_code"])
        _check_duplicate_code(db, dept.company_id, data["department_code"], exclude_id=dept.id)
    if "branch_id" in data and data["branch_id"]:
        branch = db.get(Branch, data["branch_id"])
        if branch is None or branch.company_id != dept.company_id:
            raise ValueError("department.errors.branch_not_found")
    if "parent_department_id" in data:
        _validate_parent(db, dept, data["parent_department_id"])

    for key, value in data.items():
        setattr(dept, key, value)
    return dept


def _count_active_assignments(db: Session, department_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count()).where(
                DepartmentEmployeeAssignment.department_id == department_id,
                DepartmentEmployeeAssignment.status == AssignmentStatus.ACTIVE.value,
            )
        )
        or 0
    )


def _count_children(db: Session, department_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count()).where(
                Department.parent_department_id == department_id,
                Department.archived_at.is_(None),
            )
        )
        or 0
    )


def _count_active_budgets(db: Session, department_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count()).where(
                DepartmentBudget.department_id == department_id,
                DepartmentBudget.approval_status.in_(["approved", "pending"]),
            )
        )
        or 0
    )


def check_delete_allowed(db: Session, dept: Department) -> list[str]:
    blockers: list[str] = []
    if _count_active_assignments(db, dept.id) > 0:
        blockers.append("department.errors.has_active_employees")
    if _count_children(db, dept.id) > 0:
        blockers.append("department.errors.has_child_departments")
    if dept.team_count > 0:
        blockers.append("department.errors.has_active_teams")
    if (
        db.scalar(
            select(func.count()).where(
                DepartmentProjectLink.department_id == dept.id,
            )
        )
        or 0
    ) > 0:
        blockers.append("department.errors.has_active_projects")
    if _count_active_budgets(db, dept.id) > 0:
        blockers.append("department.errors.has_active_budgets")
    return blockers


def delete_department(db: Session, dept: Department) -> None:
    blockers = check_delete_allowed(db, dept)
    if blockers:
        raise ValueError(blockers[0])
    db.delete(dept)


def archive_department(db: Session, dept: Department) -> Department:
    dept.status = DepartmentStatus.ARCHIVED.value
    dept.archived_at = datetime.now(UTC)
    return dept


def assign_head(db: Session, dept: Department, user_id: UUID) -> Department:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("department.errors.user_not_found")
    dept.department_head_user_id = user_id
    return dept


def _validate_allocation(db: Session, user_id: UUID, new_pct: int, exclude_dept_id: UUID | None = None) -> None:
    query = select(func.coalesce(func.sum(DepartmentEmployeeAssignment.allocation_percentage), 0)).where(
        DepartmentEmployeeAssignment.user_id == user_id,
        DepartmentEmployeeAssignment.status == AssignmentStatus.ACTIVE.value,
    )
    if exclude_dept_id:
        query = query.where(DepartmentEmployeeAssignment.department_id != exclude_dept_id)
    current = db.scalar(query) or 0
    if current + new_pct > 100:
        raise ValueError("department.errors.allocation_exceeds_100")


def assign_employees(db: Session, dept: Department, payload: AssignEmployeesRequest) -> list[DepartmentEmployeeAssignment]:
    results: list[DepartmentEmployeeAssignment] = []
    for item in payload.assignments:
        _validate_allocation(db, item.user_id, item.allocation_percentage)
        user = db.get(User, item.user_id)
        if user is None:
            raise ValueError("department.errors.user_not_found")

        existing = db.scalar(
            select(DepartmentEmployeeAssignment).where(
                DepartmentEmployeeAssignment.department_id == dept.id,
                DepartmentEmployeeAssignment.user_id == item.user_id,
            )
        )
        if existing:
            existing.allocation_percentage = item.allocation_percentage
            existing.is_primary = item.is_primary
            existing.effective_date = item.effective_date
            existing.end_date = item.end_date
            existing.status = AssignmentStatus.ACTIVE.value
            results.append(existing)
        else:
            assignment = DepartmentEmployeeAssignment(
                department_id=dept.id,
                user_id=item.user_id,
                allocation_percentage=item.allocation_percentage,
                is_primary=item.is_primary,
                effective_date=item.effective_date,
                end_date=item.end_date,
            )
            db.add(assignment)
            results.append(assignment)

    dept.employee_count = _count_active_assignments(db, dept.id)
    return results


def transfer_employees(
    db: Session,
    source: Department,
    target_id: UUID,
    user_ids: list[UUID],
    end_date=None,
) -> tuple[Department, Department]:
    target = db.get(Department, target_id)
    if target is None or target.archived_at is not None:
        raise ValueError("department.errors.target_not_found")
    if target.company_id != source.company_id:
        raise ValueError("department.errors.target_company_mismatch")

    for user_id in user_ids:
        assignment = db.scalar(
            select(DepartmentEmployeeAssignment).where(
                DepartmentEmployeeAssignment.department_id == source.id,
                DepartmentEmployeeAssignment.user_id == user_id,
                DepartmentEmployeeAssignment.status == AssignmentStatus.ACTIVE.value,
            )
        )
        if assignment:
            assignment.status = AssignmentStatus.ENDED.value
            assignment.end_date = end_date

        _validate_allocation(db, user_id, assignment.allocation_percentage if assignment else 100)
        new_assignment = DepartmentEmployeeAssignment(
            department_id=target.id,
            user_id=user_id,
            allocation_percentage=assignment.allocation_percentage if assignment else 100,
            is_primary=assignment.is_primary if assignment else False,
            effective_date=end_date,
        )
        db.add(new_assignment)

    source.employee_count = _count_active_assignments(db, source.id)
    target.employee_count = _count_active_assignments(db, target.id)
    return source, target


def move_department(db: Session, dept: Department, payload: MoveDepartmentRequest) -> Department:
    if payload.company_id and payload.company_id != dept.company_id:
        company = db.get(Company, payload.company_id)
        if company is None:
            raise ValueError("department.errors.company_not_found")
        if _count_children(db, dept.id) > 0:
            raise ValueError("department.errors.move_has_children")
        dept.company_id = payload.company_id

    if payload.branch_id is not None:
        if payload.branch_id:
            branch = db.get(Branch, payload.branch_id)
            if branch is None or branch.company_id != dept.company_id:
                raise ValueError("department.errors.branch_not_found")
        dept.branch_id = payload.branch_id

    if "parent_department_id" in payload.model_dump(exclude_unset=True):
        _validate_parent(db, dept, payload.parent_department_id)
        dept.parent_department_id = payload.parent_department_id

    return dept


def merge_departments(db: Session, source: Department, target_id: UUID, notes: str | None = None) -> tuple[Department, Department]:
    if source.id == target_id:
        raise ValueError("department.errors.cannot_merge_self")
    target = db.get(Department, target_id)
    if target is None or target.archived_at is not None:
        raise ValueError("department.errors.target_not_found")
    if target.company_id != source.company_id:
        raise ValueError("department.errors.target_company_mismatch")

    # Transfer employee assignments
    assignments = db.scalars(
        select(DepartmentEmployeeAssignment).where(
            DepartmentEmployeeAssignment.department_id == source.id,
            DepartmentEmployeeAssignment.status == AssignmentStatus.ACTIVE.value,
        )
    ).all()
    for assignment in assignments:
        existing = db.scalar(
            select(DepartmentEmployeeAssignment).where(
                DepartmentEmployeeAssignment.department_id == target.id,
                DepartmentEmployeeAssignment.user_id == assignment.user_id,
            )
        )
        if existing:
            existing.status = AssignmentStatus.ENDED.value
        assignment.department_id = target.id

    # Transfer KPIs
    for kpi in db.scalars(select(DepartmentKPI).where(DepartmentKPI.department_id == source.id)).all():
        kpi.department_id = target.id

    # Transfer responsibilities
    for resp in db.scalars(
        select(DepartmentResponsibility).where(DepartmentResponsibility.department_id == source.id)
    ).all():
        resp.department_id = target.id

    # Transfer budgets
    for budget in db.scalars(select(DepartmentBudget).where(DepartmentBudget.department_id == source.id)).all():
        budget.department_id = target.id

    # Transfer project links
    for link in db.scalars(
        select(DepartmentProjectLink).where(DepartmentProjectLink.department_id == source.id)
    ).all():
        link.department_id = target.id

    # Reparent child departments
    for child in db.scalars(
        select(Department).where(Department.parent_department_id == source.id)
    ).all():
        child.parent_department_id = target.id

    source.status = DepartmentStatus.MERGED.value
    source.merged_into_department_id = target.id
    if notes:
        source.notes = (source.notes or "") + f"\n[Merged] {notes}"

    target.employee_count = _count_active_assignments(db, target.id)
    target.team_count = source.team_count + target.team_count
    return source, target


def list_department_employees(db: Session, department_id: UUID) -> list[DepartmentEmployeeResponse]:
    rows = db.scalars(
        select(DepartmentEmployeeAssignment)
        .where(DepartmentEmployeeAssignment.department_id == department_id)
        .order_by(DepartmentEmployeeAssignment.is_primary.desc())
    ).all()
    items: list[DepartmentEmployeeResponse] = []
    for row in rows:
        items.append(
            DepartmentEmployeeResponse(
                id=row.id,
                user_id=row.user_id,
                user_name=_get_user_name(db, row.user_id),
                allocation_percentage=row.allocation_percentage,
                is_primary=row.is_primary,
                effective_date=row.effective_date,
                end_date=row.end_date,
                status=row.status,
            )
        )
    return items


def list_department_kpis(db: Session, department_id: UUID) -> list[DepartmentKPIResponse]:
    rows = db.scalars(select(DepartmentKPI).where(DepartmentKPI.department_id == department_id)).all()
    return [DepartmentKPIResponse.model_validate(row) for row in rows]


def compute_dashboard_metrics(db: Session, company_id: UUID | None = None) -> DepartmentDashboardMetrics:
    base = select(Department).where(Department.archived_at.is_(None))
    if company_id:
        base = base.where(Department.company_id == company_id)

    depts = db.scalars(base).all()
    total = len(depts)
    active = sum(1 for d in depts if d.status == DepartmentStatus.ACTIVE.value)
    without_head = sum(1 for d in depts if d.department_head_user_id is None and d.status == DepartmentStatus.ACTIVE.value)
    total_employees = sum(d.employee_count for d in depts)
    open_positions = sum(d.open_positions for d in depts)

    over_budget = 0
    for dept in depts:
        budgets = db.scalars(
            select(DepartmentBudget).where(
                DepartmentBudget.department_id == dept.id,
                DepartmentBudget.approval_status == "approved",
            )
        ).all()
        for b in budgets:
            if b.approved_budget and b.used_budget and b.used_budget > b.approved_budget:
                over_budget += 1
                break

    below_kpi = db.scalar(
        select(func.count()).where(
            DepartmentKPI.status.in_([KPIStatus.BEHIND.value, KPIStatus.AT_RISK.value]),
            DepartmentKPI.department_id.in_([d.id for d in depts] or [None]),
        )
    ) or 0

    return DepartmentDashboardMetrics(
        total_departments=total,
        active_departments=active,
        without_head=without_head,
        total_employees=total_employees,
        open_positions=open_positions,
        over_budget=over_budget,
        below_kpi_target=below_kpi,
        recent_org_changes=0,
    )
