"""Department management API routes."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.department import CompanyDepartment as Department, DepartmentBudget, DepartmentKPI
from investhome_api.models.user_auth import User
from investhome_api.schemas.department import (
    AssignEmployeesRequest,
    AssignHeadRequest,
    DepartmentBudgetCreate,
    DepartmentBudgetResponse,
    DepartmentCreate,
    DepartmentDashboardMetrics,
    DepartmentDetailResponse,
    DepartmentEmployeesResponse,
    DepartmentKPICreate,
    DepartmentKPIResponse,
    DepartmentKPIsResponse,
    DepartmentListResponse,
    DepartmentMutationResponse,
    DepartmentProjectsResponse,
    DepartmentTeamsResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
    MergeDepartmentRequest,
    MoveDepartmentRequest,
    TransferEmployeesRequest,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_created,
    log_entity_deleted,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity, snapshot_entity
from investhome_api.services.company_notifications import notify_department_head_assigned
from investhome_api.services.department_service import (
    archive_department,
    assign_employees,
    assign_head,
    build_department_tree,
    compute_dashboard_metrics,
    create_department,
    delete_department,
    get_department_or_none,
    list_department_employees,
    list_department_kpis,
    list_departments,
    merge_departments,
    move_department,
    paginate_total_pages,
    serialize_department_detail,
    transfer_employees,
    update_department,
)

router = APIRouter(prefix="/departments", tags=["departments"])

DEPARTMENT_ACTIVITY_FIELDS = [
    "department_code",
    "department_name",
    "company_id",
    "branch_id",
    "department_type",
    "status",
    "parent_department_id",
    "department_head_user_id",
]


def _get_department_or_404(db: Session, department_id: UUID) -> Department:
    dept = get_department_or_none(db, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="department.errors.not_found")
    return dept


def _value_error_http(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/dashboard", response_model=DepartmentDashboardMetrics)
def department_dashboard_metrics(
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentDashboardMetrics:
    del user
    return compute_dashboard_metrics(db, company_id)


@router.get("/tree", response_model=DepartmentTreeResponse)
def get_department_tree(
    company_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentTreeResponse:
    del user
    items, total = build_department_tree(db, company_id)
    return DepartmentTreeResponse(items=items, total=total)


@router.get("", response_model=DepartmentListResponse)
def list_department_records(
    search: str | None = Query(default=None, max_length=255),
    company_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_type: str | None = Query(default=None, max_length=40),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    parent_department_id: UUID | None = None,
    head_user_id: UUID | None = None,
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at", max_length=40),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentListResponse:
    del user
    items, total = list_departments(
        db,
        search=search,
        company_id=company_id,
        branch_id=branch_id,
        department_type=department_type,
        status=status_filter,
        parent_department_id=parent_department_id,
        head_user_id=head_user_id,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return DepartmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=paginate_total_pages(total, page_size),
    )


@router.get("/export")
def export_departments(
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "export")),
) -> Response:
    del user
    items, _ = list_departments(db, company_id=company_id, page_size=10000)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "department_code",
            "department_name",
            "company_id",
            "branch_id",
            "department_type",
            "status",
            "employee_count",
            "team_count",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.department_code,
                item.department_name,
                str(item.company_id),
                str(item.branch_id) if item.branch_id else "",
                item.department_type,
                item.status,
                item.employee_count,
                item.team_count,
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="departments.csv"'},
    )


@router.post("", response_model=DepartmentMutationResponse, status_code=status.HTTP_201_CREATED)
def create_department_record(
    body: DepartmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "create")),
) -> DepartmentMutationResponse:
    try:
        dept = create_department(db, body)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_entity_created(
        db,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.entity_created",
        actor=user,
        metadata={"department_code": dept.department_code, "department_name": dept.department_name},
        request=request,
    )
    db.commit()
    db.refresh(dept)
    return DepartmentMutationResponse(department=serialize_department_detail(db, dept))


@router.get("/{department_id}", response_model=DepartmentDetailResponse)
def get_department_record(
    department_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentDetailResponse:
    del user
    dept = _get_department_or_404(db, department_id)
    return serialize_department_detail(db, dept)


@router.put("/{department_id}", response_model=DepartmentMutationResponse)
def update_department_record(
    department_id: UUID,
    body: DepartmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "update")),
) -> DepartmentMutationResponse:
    dept = _get_department_or_404(db, department_id)
    before = snapshot_entity(dept, DEPARTMENT_ACTIVITY_FIELDS)
    try:
        update_department(db, dept, body)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.entity_updated",
        actor=user,
        before=before,
        after=snapshot_entity(dept, DEPARTMENT_ACTIVITY_FIELDS),
        request=request,
    )
    db.commit()
    db.refresh(dept)
    return DepartmentMutationResponse(department=serialize_department_detail(db, dept))


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department_record(
    department_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "delete")),
) -> None:
    dept = _get_department_or_404(db, department_id)
    try:
        delete_department(db, dept)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_entity_deleted(
        db,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.entity_deleted",
        actor=user,
        metadata={"department_code": dept.department_code},
        request=request,
    )
    db.commit()


@router.post("/{department_id}/archive", response_model=DepartmentMutationResponse)
def archive_department_record(
    department_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "archive")),
) -> DepartmentMutationResponse:
    dept = _get_department_or_404(db, department_id)
    archive_department(db, dept)
    log_activity(
        db,
        action=ActivityAction.ARCHIVED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.entity_archived",
        actor_user=user,
        metadata={"department_code": dept.department_code},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    db.refresh(dept)
    return DepartmentMutationResponse(department=serialize_department_detail(db, dept))


@router.post("/{department_id}/assign-head", response_model=DepartmentMutationResponse)
def assign_department_head(
    department_id: UUID,
    body: AssignHeadRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "assign_head")),
) -> DepartmentMutationResponse:
    dept = _get_department_or_404(db, department_id)
    try:
        assign_head(db, dept, body.user_id)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.head_assigned",
        actor_user=user,
        metadata={"head_user_id": str(body.user_id)},
        request_context=activity_context_from_request(request),
    )
    notify_department_head_assigned(
        db,
        head_user_id=body.user_id,
        department_id=dept.id,
        department_name=dept.department_name,
        actor=user,
    )
    db.commit()
    db.refresh(dept)
    return DepartmentMutationResponse(department=serialize_department_detail(db, dept))


@router.post("/{department_id}/assign-employees", response_model=DepartmentEmployeesResponse)
def assign_department_employees(
    department_id: UUID,
    body: AssignEmployeesRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "assign_employee")),
) -> DepartmentEmployeesResponse:
    dept = _get_department_or_404(db, department_id)
    try:
        assign_employees(db, dept, body)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.employees_assigned",
        actor_user=user,
        metadata={"count": len(body.assignments)},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    items = list_department_employees(db, department_id)
    return DepartmentEmployeesResponse(items=items, total=len(items))


@router.post("/{department_id}/transfer-employees", response_model=DepartmentMutationResponse)
def transfer_department_employees(
    department_id: UUID,
    body: TransferEmployeesRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "transfer_employee")),
) -> DepartmentMutationResponse:
    dept = _get_department_or_404(db, department_id)
    try:
        transfer_employees(db, dept, body.target_department_id, body.user_ids, body.end_date)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.employees_transferred",
        actor_user=user,
        metadata={"target_id": str(body.target_department_id), "count": len(body.user_ids)},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    db.refresh(dept)
    return DepartmentMutationResponse(department=serialize_department_detail(db, dept))


@router.post("/{department_id}/move", response_model=DepartmentMutationResponse)
def move_department_record(
    department_id: UUID,
    body: MoveDepartmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "move")),
) -> DepartmentMutationResponse:
    dept = _get_department_or_404(db, department_id)
    try:
        move_department(db, dept, body)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.moved",
        actor_user=user,
        metadata=body.model_dump(exclude_none=True),
        request_context=activity_context_from_request(request),
    )
    db.commit()
    db.refresh(dept)
    return DepartmentMutationResponse(department=serialize_department_detail(db, dept))


@router.post("/{department_id}/merge", response_model=DepartmentMutationResponse)
def merge_department_record(
    department_id: UUID,
    body: MergeDepartmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "merge")),
) -> DepartmentMutationResponse:
    dept = _get_department_or_404(db, department_id)
    try:
        source, target = merge_departments(db, dept, body.target_department_id, body.notes)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=source.id,
        description_key="activity.department.merged",
        actor_user=user,
        metadata={"target_id": str(body.target_department_id)},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    db.refresh(target)
    return DepartmentMutationResponse(department=serialize_department_detail(db, target))


@router.get("/{department_id}/employees", response_model=DepartmentEmployeesResponse)
def get_department_employees(
    department_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentEmployeesResponse:
    del user
    _get_department_or_404(db, department_id)
    items = list_department_employees(db, department_id)
    return DepartmentEmployeesResponse(items=items, total=len(items))


@router.get("/{department_id}/teams", response_model=DepartmentTeamsResponse)
def get_department_teams(
    department_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentTeamsResponse:
    del user
    _get_department_or_404(db, department_id)
    return DepartmentTeamsResponse(items=[], total=0, stub=True)


@router.get("/{department_id}/projects", response_model=DepartmentProjectsResponse)
def get_department_projects(
    department_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentProjectsResponse:
    del user
    _get_department_or_404(db, department_id)
    return DepartmentProjectsResponse(items=[], total=0, stub=True)


@router.get("/{department_id}/kpis", response_model=DepartmentKPIsResponse)
def get_department_kpis(
    department_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "read")),
) -> DepartmentKPIsResponse:
    del user
    _get_department_or_404(db, department_id)
    items = list_department_kpis(db, department_id)
    return DepartmentKPIsResponse(items=items, total=len(items))


@router.post("/{department_id}/kpis", response_model=DepartmentKPIResponse, status_code=status.HTTP_201_CREATED)
def create_department_kpi(
    department_id: UUID,
    body: DepartmentKPICreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "manage_kpi")),
) -> DepartmentKPIResponse:
    dept = _get_department_or_404(db, department_id)
    kpi = DepartmentKPI(department_id=dept.id, **body.model_dump())
    db.add(kpi)
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.kpi_created",
        actor_user=user,
        metadata={"kpi_name": body.name},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    db.refresh(kpi)
    return DepartmentKPIResponse.model_validate(kpi)


@router.post("/{department_id}/budgets", response_model=DepartmentBudgetResponse, status_code=status.HTTP_201_CREATED)
def create_department_budget(
    department_id: UUID,
    body: DepartmentBudgetCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("department", "manage_budget")),
) -> DepartmentBudgetResponse:
    dept = _get_department_or_404(db, department_id)
    budget = DepartmentBudget(department_id=dept.id, **body.model_dump())
    db.add(budget)
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DEPARTMENT,
        entity_id=dept.id,
        description_key="activity.department.budget_created",
        actor_user=user,
        metadata={"fiscal_year": body.fiscal_year},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    db.refresh(budget)
    return DepartmentBudgetResponse.model_validate(budget)
