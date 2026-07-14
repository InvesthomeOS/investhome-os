from datetime import UTC, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.project import (
    ACTIVE_PROJECT_STATUSES,
    DevelopmentType,
    Project,
    ProjectStatus,
    ProjectType,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
    ProjectUpdate,
)

from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity

router = APIRouter(prefix="/projects", tags=["projects"])

PROJECT_ACTIVITY_FIELDS = [
    "project_code",
    "project_name",
    "city",
    "project_type",
    "project_status",
    "total_development_cost",
    "current_project_value",
    "equity_required",
    "equity_raised",
]

SORTABLE_FIELDS = {
    "project_code": Project.project_code,
    "project_name": Project.project_name,
    "city": Project.city,
    "project_type": Project.project_type,
    "project_status": Project.project_status,
    "total_units": Project.total_units,
    "total_development_cost": Project.total_development_cost,
    "current_project_value": Project.current_project_value,
    "equity_required": Project.equity_required,
    "equity_raised": Project.equity_raised,
    "target_completion_date": Project.target_completion_date,
    "assigned_project_manager": Project.assigned_project_manager,
    "updated_at": Project.updated_at,
    "created_at": Project.created_at,
}


def _get_project_or_404(
    project_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> Project:
    project = db.get(Project, project_id)
    if project is None or (project.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _apply_filters(
    query,
    *,
    search: str | None,
    status_filter: ProjectStatus | None,
    project_type: ProjectType | None,
    development_type: DevelopmentType | None,
    city: str | None,
    assigned_project_manager: str | None,
    include_archived: bool,
):
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))

    if status_filter is not None:
        query = query.where(Project.project_status == status_filter)

    if project_type is not None:
        query = query.where(Project.project_type == project_type)

    if development_type is not None:
        query = query.where(Project.development_type == development_type)

    if city:
        query = query.where(Project.city.ilike(f"%{city.strip()}%"))

    if assigned_project_manager:
        pattern = f"%{assigned_project_manager.strip()}%"
        query = query.where(Project.assigned_project_manager.ilike(pattern))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Project.project_code.ilike(pattern),
                Project.project_name.ilike(pattern),
                Project.address.ilike(pattern),
                Project.city.ilike(pattern),
                Project.ownership_entity.ilike(pattern),
                Project.description.ilike(pattern),
                Project.assigned_project_manager.ilike(pattern),
            )
        )

    return query


@router.get("/stats", response_model=ProjectStatsResponse)
def get_project_stats(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view")),
) -> ProjectStatsResponse:
    projects = db.scalars(select(Project).where(Project.archived_at.is_(None))).all()

    active_projects = [p for p in projects if p.project_status in ACTIVE_PROJECT_STATUSES]

    return ProjectStatsResponse(
        total=len(projects),
        active=len(active_projects),
        units_under_development=sum(
            (p.total_units or 0) for p in active_projects
        ),
        total_development_cost=sum(
            (p.total_development_cost or Decimal("0")) for p in projects
        ),
        current_portfolio_value=sum(
            (p.current_project_value or Decimal("0")) for p in projects
        ),
        equity_raised=sum((p.equity_raised or Decimal("0")) for p in projects),
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: str | None = Query(default=None, max_length=255),
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    project_type: ProjectType | None = None,
    development_type: DevelopmentType | None = None,
    city: str | None = Query(default=None, max_length=100),
    assigned_project_manager: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view")),
) -> ProjectListResponse:
    sort_column = SORTABLE_FIELDS.get(sort_by, Project.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(Project)
    query = _apply_filters(
        query,
        search=search,
        status_filter=status_filter,
        project_type=project_type,
        development_type=development_type,
        city=city,
        assigned_project_manager=assigned_project_manager,
        include_archived=include_archived,
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    query = query.order_by(order_fn(sort_column))
    offset = (page - 1) * page_size
    projects = db.scalars(query.offset(offset).limit(page_size)).all()

    pages = ceil(total / page_size) if total else 0

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(project) for project in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view")),
) -> ProjectResponse:
    project = _get_project_or_404(project_id, db)
    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "create")),
) -> ProjectResponse:
    project = Project(**payload.model_dump())
    db.add(project)
    try:
        db.flush()
        log_entity_created(
            db,
            entity_type=ActivityEntityType.PROJECT,
            entity_id=project.id,
            description_key="activity.project.created",
            actor=actor,
            metadata={"name": project.project_name},
            request=request,
            is_demo=project.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project code already exists",
        ) from exc
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "update")),
) -> ProjectResponse:
    project = _get_project_or_404(project_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    before = snapshot_entity(project, PROJECT_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(project, field, value)

    project.updated_at = datetime.now(UTC)
    financial_fields = {
        "total_development_cost",
        "current_project_value",
        "equity_required",
        "equity_raised",
    }
    changed = {field for field in updates if before.get(field) != getattr(project, field)}
    description_key = (
        "activity.project.financial_updated"
        if changed & financial_fields
        else "activity.project.updated"
    )
    try:
        db.flush()
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.PROJECT,
            entity_id=project.id,
            description_key=description_key,
            actor=actor,
            before=before,
            after=snapshot_entity(project, PROJECT_ACTIVITY_FIELDS),
            metadata={"name": project.project_name},
            request=request,
            is_demo=project.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project code already exists",
        ) from exc
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=ProjectResponse)
def archive_project(
    project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "archive")),
) -> ProjectResponse:
    project = _get_project_or_404(project_id, db)

    if project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is already archived",
        )

    project.archived_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.PROJECT,
        entity_id=project.id,
        description_key="activity.project.archived",
        actor=actor,
        metadata={"name": project.project_name},
        request=request,
        is_demo=project.is_demo,
    )
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)
