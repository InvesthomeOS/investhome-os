"""Branch management API routes."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.branch import Branch, BranchStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.branch import (
    AssignManagerRequest,
    BranchAssetResponse,
    BranchCreate,
    BranchDetailResponse,
    BranchEmployeesResponse,
    BranchImportRequest,
    BranchImportResponse,
    BranchListResponse,
    BranchMutationResponse,
    BranchUpdate,
    TransferEmployeesRequest,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity, snapshot_entity
from investhome_api.services.company_notifications import notify_branch_manager_assigned
from investhome_api.services.branch_service import (
    create_branch,
    duplicate_branch,
    get_branch_or_none,
    list_branches,
    paginate_total_pages,
    serialize_branch_detail,
    update_branch,
)

router = APIRouter(prefix="/branches", tags=["branches"])

BRANCH_ACTIVITY_FIELDS = [
    "branch_code",
    "branch_name",
    "company_id",
    "branch_type",
    "country",
    "city",
    "status",
    "manager_user_id",
]


def _get_branch_or_404(db: Session, branch_id: UUID) -> Branch:
    branch = get_branch_or_none(db, branch_id)
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="branch.errors.not_found")
    return branch


def _value_error_http(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=BranchListResponse)
def list_branch_records(
    search: str | None = Query(default=None, max_length=255),
    company_id: UUID | None = None,
    country: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    city: str | None = Query(default=None, max_length=100),
    branch_type: str | None = Query(default=None, max_length=40),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    manager_user_id: UUID | None = None,
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at", max_length=40),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "read")),
) -> BranchListResponse:
    del user
    items, total = list_branches(
        db,
        search=search,
        company_id=company_id,
        country=country,
        state=state,
        city=city,
        branch_type=branch_type,
        status=status_filter,
        manager_user_id=manager_user_id,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return BranchListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=paginate_total_pages(total, page_size),
    )


@router.get("/export")
def export_branches(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "export")),
) -> Response:
    del user
    items, _ = list_branches(db, page=1, page_size=10_000)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "branch_code",
            "branch_name",
            "company_name",
            "branch_type",
            "country",
            "state",
            "city",
            "status",
            "manager_name",
            "employee_count",
            "department_count",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.branch_code,
                item.branch_name,
                item.company_name or "",
                item.branch_type,
                item.country,
                item.state or "",
                item.city,
                item.status,
                item.manager_name or "",
                item.employee_count,
                item.department_count,
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="branches-export.csv"'},
    )


@router.post("/import", response_model=BranchImportResponse)
def import_branches(
    body: BranchImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "create")),
) -> BranchImportResponse:
    created = 0
    skipped = 0
    errors: list[str] = []
    for index, row in enumerate(body.rows, start=1):
        try:
            branch, _ = create_branch(db, BranchCreate(**row.model_dump()))
            log_entity_created(
                db,
                entity_type=ActivityEntityType.BRANCH,
                entity_id=branch.id,
                description_key="activity.branch.created",
                actor=user,
                metadata={"branch_code": branch.branch_code, "source": "import"},
                request=request,
            )
            created += 1
        except ValueError as exc:
            if str(exc) == "branch.errors.duplicate_code":
                skipped += 1
            else:
                errors.append(f"Row {index}: {exc}")
    db.commit()
    return BranchImportResponse(created=created, skipped=skipped, errors=errors)


@router.get("/{branch_id}", response_model=BranchDetailResponse)
def get_branch(
    branch_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "read")),
) -> BranchDetailResponse:
    branch = _get_branch_or_404(db, branch_id)
    return serialize_branch_detail(db, branch, user=user)


@router.post("", response_model=BranchMutationResponse, status_code=status.HTTP_201_CREATED)
def create_branch_record(
    body: BranchCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "create")),
) -> BranchMutationResponse:
    try:
        branch, warnings = create_branch(db, body)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    log_entity_created(
        db,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=branch.id,
        description_key="activity.branch.created",
        actor=user,
        metadata={"branch_code": branch.branch_code, "branch_name": branch.branch_name},
        request=request,
    )
    db.commit()
    db.refresh(branch)
    branch = _get_branch_or_404(db, branch.id)
    return BranchMutationResponse(branch=serialize_branch_detail(db, branch, warnings=warnings), warnings=warnings)


@router.put("/{branch_id}", response_model=BranchMutationResponse)
def update_branch_record(
    branch_id: UUID,
    body: BranchUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "update")),
) -> BranchMutationResponse:
    branch = _get_branch_or_404(db, branch_id)
    before = snapshot_entity(branch, BRANCH_ACTIVITY_FIELDS)
    old_status = branch.status
    try:
        branch, warnings = update_branch(db, branch, body)
    except ValueError as exc:
        raise _value_error_http(exc) from exc

    after = snapshot_entity(branch, BRANCH_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=branch.id,
        description_key="activity.branch.updated",
        actor=user,
        before=before,
        after=after,
        request=request,
    )
    if body.status is not None and branch.status != old_status:
        log_activity(
            db,
            action=ActivityAction.STATUS_CHANGED,
            entity_type=ActivityEntityType.BRANCH,
            entity_id=branch.id,
            description_key="activity.branch.status_changed",
            actor_user=user,
            metadata={"from_status": old_status, "to_status": branch.status},
            request_context=activity_context_from_request(request),
        )
    db.commit()
    branch = _get_branch_or_404(db, branch.id)
    return BranchMutationResponse(branch=serialize_branch_detail(db, branch, warnings=warnings), warnings=warnings)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch_record(
    branch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "delete")),
) -> None:
    branch = _get_branch_or_404(db, branch_id)
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=branch.id,
        description_key="activity.branch.deleted",
        actor_user=user,
        metadata={"branch_code": branch.branch_code},
        request_context=activity_context_from_request(request),
    )
    db.delete(branch)
    db.commit()


@router.post("/{branch_id}/archive", response_model=BranchDetailResponse)
def archive_branch(
    branch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "update")),
) -> BranchDetailResponse:
    branch = _get_branch_or_404(db, branch_id)
    branch.status = BranchStatus.ARCHIVED.value
    branch.archived_at = datetime.now(UTC)
    log_activity(
        db,
        action=ActivityAction.ARCHIVED,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=branch.id,
        description_key="activity.branch.archived",
        actor_user=user,
        metadata={"branch_code": branch.branch_code},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    branch = _get_branch_or_404(db, branch.id)
    return serialize_branch_detail(db, branch)


@router.post("/{branch_id}/deactivate", response_model=BranchDetailResponse)
def deactivate_branch(
    branch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "update")),
) -> BranchDetailResponse:
    branch = _get_branch_or_404(db, branch_id)
    old_status = branch.status
    branch.status = BranchStatus.INACTIVE.value
    log_activity(
        db,
        action=ActivityAction.STATUS_CHANGED,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=branch.id,
        description_key="activity.branch.status_changed",
        actor_user=user,
        metadata={"from_status": old_status, "to_status": branch.status},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    branch = _get_branch_or_404(db, branch.id)
    return serialize_branch_detail(db, branch)


@router.post("/{branch_id}/duplicate", response_model=BranchDetailResponse, status_code=status.HTTP_201_CREATED)
def duplicate_branch_record(
    branch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "create")),
) -> BranchDetailResponse:
    source = _get_branch_or_404(db, branch_id)
    clone = duplicate_branch(db, source)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=clone.id,
        description_key="activity.branch.created",
        actor=user,
        metadata={"branch_code": clone.branch_code, "duplicated_from": str(source.id)},
        request=request,
    )
    db.commit()
    clone = _get_branch_or_404(db, clone.id)
    return serialize_branch_detail(db, clone)


@router.get("/{branch_id}/employees", response_model=BranchEmployeesResponse)
def list_branch_employees(
    branch_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "read")),
) -> BranchEmployeesResponse:
    del db, user
    _get_branch_or_404(db, branch_id)
    return BranchEmployeesResponse(items=[], total=0, stub=True)


@router.get("/{branch_id}/assets")
def list_branch_assets(
    branch_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "read")),
) -> dict[str, list[BranchAssetResponse] | int]:
    del user
    branch = _get_branch_or_404(db, branch_id)
    items = [BranchAssetResponse.model_validate(asset) for asset in branch.assets]
    return {"items": items, "total": len(items)}


@router.post("/{branch_id}/assign-manager", response_model=BranchDetailResponse)
def assign_branch_manager(
    branch_id: UUID,
    body: AssignManagerRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "assign_manager")),
) -> BranchDetailResponse:
    branch = _get_branch_or_404(db, branch_id)
    if body.manager_user_id is not None and db.get(User, body.manager_user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="branch.errors.manager_not_found")
    branch.manager_user_id = body.manager_user_id
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=branch.id,
        description_key="activity.branch.manager_assigned",
        actor_user=user,
        metadata={"manager_user_id": str(body.manager_user_id) if body.manager_user_id else None},
        request_context=activity_context_from_request(request),
    )
    notify_branch_manager_assigned(
        db,
        manager_user_id=body.manager_user_id,
        branch_id=branch.id,
        branch_name=branch.branch_name,
        actor=user,
    )
    db.commit()
    branch = _get_branch_or_404(db, branch.id)
    return serialize_branch_detail(db, branch, user=user)


@router.post("/{branch_id}/transfer-employees", response_model=BranchEmployeesResponse)
def transfer_branch_employees(
    branch_id: UUID,
    body: TransferEmployeesRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("branch", "transfer_employee")),
) -> BranchEmployeesResponse:
    source = _get_branch_or_404(db, branch_id)
    target = _get_branch_or_404(db, body.target_branch_id)
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.BRANCH,
        entity_id=source.id,
        description_key="activity.branch.employees_transferred",
        actor_user=user,
        metadata={
            "target_branch_id": str(target.id),
            "employee_count": len(body.employee_user_ids),
            "stub": True,
        },
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return BranchEmployeesResponse(items=[], total=0, stub=True)
