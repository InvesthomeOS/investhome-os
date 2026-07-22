"""Project workspace service — CRUD, status, team, financial RBAC."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import asc, desc, extract, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.project import (
    ACTIVE_PROJECT_STATUSES,
    DevelopmentStage,
    DevelopmentType,
    Project,
    ProjectPriority,
    ProjectStatus,
    ProjectType,
)
from investhome_api.models.project_team import (
    ProjectTeamMember,
    ProjectTeamMemberStatus,
    ProjectTeamRole,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.project import (
    FINANCIAL_FIELDS,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
    ProjectStatusTransitionResponse,
    ProjectTeamListResponse,
    ProjectTeamMemberCreate,
    ProjectTeamMemberResponse,
    ProjectTeamMemberUpdate,
    ProjectUpdate,
    ProjectUserSummary,
)
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_status import get_allowed_transitions, validate_status_transition

PROJECT_ACTIVITY_FIELDS = [
    "project_code",
    "project_name",
    "city",
    "project_type",
    "project_status",
    "priority",
    "development_stage",
    "total_development_cost",
    "current_project_value",
    "equity_required",
    "equity_raised",
    "construction_budget",
    "land_cost",
    "completion_percentage",
    "project_manager_user_id",
    "address",
    "start_date",
    "target_completion_date",
]

SORTABLE_FIELDS = {
    "project_code": Project.project_code,
    "project_name": Project.project_name,
    "city": Project.city,
    "project_type": Project.project_type,
    "project_status": Project.project_status,
    "priority": Project.priority,
    "development_stage": Project.development_stage,
    "total_units": Project.total_units,
    "total_development_cost": Project.total_development_cost,
    "construction_budget": Project.construction_budget,
    "projected_revenue": Project.projected_revenue,
    "current_project_value": Project.current_project_value,
    "equity_required": Project.equity_required,
    "equity_raised": Project.equity_raised,
    "completion_percentage": Project.completion_percentage,
    "target_completion_date": Project.target_completion_date,
    "assigned_project_manager": Project.assigned_project_manager,
    "updated_at": Project.updated_at,
    "created_at": Project.created_at,
}

# Aliases accepted by list/sort API for sprint-friendly names
SORT_ALIASES = {
    "name": "project_name",
    "code": "project_code",
    "status": "project_status",
    "expected_revenue": "projected_revenue",
    "estimated_completion_date": "target_completion_date",
}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:280] or "project"


def _can_view_financial(user: User | None) -> bool:
    if user is None:
        return True
    return user_has_permission(user, "projects", "view_financial") or user_has_permission(
        user, "projects", "edit_financial"
    )


def _can_edit_financial(user: User | None) -> bool:
    if user is None:
        return True
    return user_has_permission(user, "projects", "edit_financial")


def _reject_unauthorized_financial_writes(updates: dict, user: User | None) -> dict:
    financial_updates = FINANCIAL_FIELDS.intersection(updates)
    if financial_updates and not _can_edit_financial(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to edit project financial fields",
        )
    return updates


def _load_user_summary(db: Session, user_id: UUID | None) -> ProjectUserSummary | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None:
        return None
    return ProjectUserSummary(id=user.id, full_name=user.full_name, email=user.email)


def to_team_member_response(db: Session, member: ProjectTeamMember) -> ProjectTeamMemberResponse:
    base = ProjectTeamMemberResponse.model_validate(member)
    return base.model_copy(update={"user": _load_user_summary(db, member.user_id)})


def to_project_response(
    db: Session,
    project: Project,
    *,
    user: User | None,
    include_team: bool = False,
) -> ProjectResponse:
    data = ProjectResponse.model_validate(project)
    updates: dict = {
        "project_manager": _load_user_summary(db, project.project_manager_user_id),
    }
    if include_team:
        members = list_team_members(db, project.id)
        updates["team_summary"] = members.items
    else:
        updates["team_summary"] = []

    response = data.model_copy(update=updates)
    if not _can_view_financial(user):
        redact = {field: None for field in FINANCIAL_FIELDS}
        response = response.model_copy(update=redact)
    return response


def get_project_or_404(
    db: Session,
    project_id: UUID,
    *,
    include_archived: bool = False,
) -> Project:
    project = db.get(Project, project_id)
    if project is None or (project.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_project_by_slug(db: Session, slug: str, *, include_archived: bool = False) -> Project:
    query = select(Project).where(Project.slug == slug)
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    project = db.scalars(query).first()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _ensure_unique_slug(db: Session, slug: str, *, exclude_id: UUID | None = None) -> str:
    base = _slugify(slug)
    candidate = base
    suffix = 2
    while True:
        query = select(Project.id).where(Project.slug == candidate)
        if exclude_id is not None:
            query = query.where(Project.id != exclude_id)
        existing = db.scalar(query)
        if existing is None:
            return candidate
        candidate = f"{base}-{suffix}"[:280]
        suffix += 1


def _apply_filters(
    query,
    *,
    search: str | None,
    status_filter: ProjectStatus | None,
    project_type: ProjectType | None,
    development_type: DevelopmentType | None,
    priority: ProjectPriority | None,
    development_stage: DevelopmentStage | None,
    city: str | None,
    state: str | None,
    country: str | None,
    assigned_project_manager: str | None,
    project_manager_user_id: UUID | None,
    completion_year: int | None,
    start_date_from: date | None,
    start_date_to: date | None,
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
    if priority is not None:
        query = query.where(Project.priority == priority)
    if development_stage is not None:
        query = query.where(Project.development_stage == development_stage)
    if city:
        query = query.where(Project.city.ilike(f"%{city.strip()}%"))
    if state:
        query = query.where(Project.state.ilike(f"%{state.strip()}%"))
    if country:
        query = query.where(Project.country.ilike(f"%{country.strip()}%"))
    if assigned_project_manager:
        pattern = f"%{assigned_project_manager.strip()}%"
        query = query.where(Project.assigned_project_manager.ilike(pattern))
    if project_manager_user_id is not None:
        query = query.where(Project.project_manager_user_id == project_manager_user_id)
    if completion_year is not None:
        query = query.where(extract("year", Project.target_completion_date) == completion_year)
    if start_date_from is not None:
        query = query.where(Project.start_date >= start_date_from)
    if start_date_to is not None:
        query = query.where(Project.start_date <= start_date_to)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Project.project_code.ilike(pattern),
                Project.project_name.ilike(pattern),
                Project.address.ilike(pattern),
                Project.address_line2.ilike(pattern),
                Project.city.ilike(pattern),
                Project.state.ilike(pattern),
                Project.postal_code.ilike(pattern),
                Project.ownership_entity.ilike(pattern),
                Project.description.ilike(pattern),
                Project.assigned_project_manager.ilike(pattern),
                Project.slug.ilike(pattern),
            )
        )
    return query


def get_project_stats(db: Session, *, user: User | None) -> ProjectStatsResponse:
    projects = list(db.scalars(select(Project).where(Project.archived_at.is_(None))).all())
    active_projects = [p for p in projects if p.project_status in ACTIVE_PROJECT_STATUSES]
    under_construction = sum(1 for p in projects if p.project_status == ProjectStatus.CONSTRUCTION)
    completed = sum(1 for p in projects if p.project_status == ProjectStatus.COMPLETED)

    stats = ProjectStatsResponse(
        total=len(projects),
        active=len(active_projects),
        under_construction=under_construction,
        completed=completed,
        units_under_development=sum((p.total_units or 0) for p in active_projects),
        total_units=sum((p.total_units or 0) for p in projects),
        total_development_cost=sum((p.total_development_cost or Decimal("0")) for p in projects),
        current_portfolio_value=sum((p.current_project_value or Decimal("0")) for p in projects),
        equity_raised=sum((p.equity_raised or Decimal("0")) for p in projects),
    )
    if not _can_view_financial(user):
        stats = stats.model_copy(
            update={
                "total_development_cost": Decimal("0"),
                "current_portfolio_value": Decimal("0"),
                "equity_raised": Decimal("0"),
            }
        )
    return stats


def list_projects(
    db: Session,
    *,
    user: User | None,
    search: str | None = None,
    status_filter: ProjectStatus | None = None,
    project_type: ProjectType | None = None,
    development_type: DevelopmentType | None = None,
    priority: ProjectPriority | None = None,
    development_stage: DevelopmentStage | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    assigned_project_manager: str | None = None,
    project_manager_user_id: UUID | None = None,
    completion_year: int | None = None,
    start_date_from: date | None = None,
    start_date_to: date | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> ProjectListResponse:
    resolved_sort = SORT_ALIASES.get(sort_by, sort_by)
    sort_column = SORTABLE_FIELDS.get(resolved_sort, Project.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(Project)
    query = _apply_filters(
        query,
        search=search,
        status_filter=status_filter,
        project_type=project_type,
        development_type=development_type,
        priority=priority,
        development_stage=development_stage,
        city=city,
        state=state,
        country=country,
        assigned_project_manager=assigned_project_manager,
        project_manager_user_id=project_manager_user_id,
        completion_year=completion_year,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        include_archived=include_archived,
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    projects = list(
        db.scalars(query.order_by(order_fn(sort_column)).offset((page - 1) * page_size).limit(page_size)).all()
    )
    pages = ceil(total / page_size) if total else 0
    return ProjectListResponse(
        items=[to_project_response(db, project, user=user) for project in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def create_project(
    db: Session,
    payload: ProjectCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> Project:
    data = _reject_unauthorized_financial_writes(payload.model_dump(), actor)
    slug_source = data.get("slug") or data["project_code"] or data["project_name"]
    data["slug"] = _ensure_unique_slug(db, slug_source)
    data["created_by_user_id"] = actor.id
    data["updated_by_user_id"] = actor.id

    project = Project(**data)
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
    return project


def update_project(
    db: Session,
    project_id: UUID,
    payload: ProjectUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> Project:
    project = get_project_or_404(db, project_id)
    if project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archived projects cannot be edited; restore the project first",
        )

    updates = _reject_unauthorized_financial_writes(payload.model_dump(exclude_unset=True), actor)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    if "project_status" in updates and updates["project_status"] != project.project_status:
        validate_status_transition(project.project_status, updates["project_status"])

    if "slug" in updates and updates["slug"]:
        updates["slug"] = _ensure_unique_slug(db, updates["slug"], exclude_id=project.id)

    before = snapshot_entity(project, PROJECT_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(project, field, value)
    project.updated_by_user_id = actor.id
    project.updated_at = datetime.now(UTC)

    financial_changed = FINANCIAL_FIELDS.intersection(updates)
    schedule_fields = {
        "start_date",
        "actual_start_date",
        "target_completion_date",
        "actual_completion_date",
        "estimated_closing_date",
        "acquisition_date",
    }
    address_fields = {"address", "address_line2", "city", "state", "postal_code", "country", "latitude", "longitude"}
    description_key = "activity.project.updated"
    if financial_changed:
        description_key = "activity.project.financial_updated"
    elif schedule_fields.intersection(updates):
        description_key = "activity.project.schedule_updated"
    elif address_fields.intersection(updates):
        description_key = "activity.project.address_updated"
    elif "project_manager_user_id" in updates:
        description_key = "activity.project.manager_changed"

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
    return project


def archive_project(
    db: Session,
    project_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> Project:
    project = get_project_or_404(db, project_id)
    if project.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is already archived")

    project.archived_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    project.updated_by_user_id = actor.id
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
    return project


def restore_project(
    db: Session,
    project_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> Project:
    project = get_project_or_404(db, project_id, include_archived=True)
    if project.archived_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not archived")

    project.archived_at = None
    project.updated_at = datetime.now(UTC)
    project.updated_by_user_id = actor.id
    db.flush()
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.PROJECT,
        entity_id=project.id,
        description_key="activity.project.restored",
        actor=actor,
        metadata={"name": project.project_name},
        request=request,
        is_demo=project.is_demo,
    )
    db.commit()
    db.refresh(project)
    return project


def change_project_status(
    db: Session,
    project_id: UUID,
    target_status: ProjectStatus,
    *,
    actor: User,
    request: Request | None = None,
    note: str | None = None,
) -> Project:
    project = get_project_or_404(db, project_id)
    validate_status_transition(project.project_status, target_status)
    before = snapshot_entity(project, PROJECT_ACTIVITY_FIELDS)
    project.project_status = target_status
    project.updated_at = datetime.now(UTC)
    project.updated_by_user_id = actor.id
    db.flush()
    metadata = {"name": project.project_name, "status": target_status.value}
    if note:
        metadata["note"] = note
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT,
        entity_id=project.id,
        description_key="activity.project.status_changed",
        actor=actor,
        before=before,
        after=snapshot_entity(project, PROJECT_ACTIVITY_FIELDS),
        metadata=metadata,
        request=request,
        is_demo=project.is_demo,
    )
    db.commit()
    db.refresh(project)
    return project


def get_status_transitions(db: Session, project_id: UUID) -> ProjectStatusTransitionResponse:
    project = get_project_or_404(db, project_id)
    return ProjectStatusTransitionResponse(
        current_status=project.project_status,
        allowed=get_allowed_transitions(project.project_status),
    )


def list_team_members(db: Session, project_id: UUID) -> ProjectTeamListResponse:
    get_project_or_404(db, project_id, include_archived=True)
    members = list(
        db.scalars(
            select(ProjectTeamMember)
            .where(ProjectTeamMember.project_id == project_id)
            .order_by(ProjectTeamMember.created_at.asc())
        ).all()
    )
    items = [to_team_member_response(db, member) for member in members]
    return ProjectTeamListResponse(items=items, total=len(items))


def assign_team_member(
    db: Session,
    project_id: UUID,
    payload: ProjectTeamMemberCreate,
    *,
    actor: User,
    request: Request | None = None,
) -> ProjectTeamMember:
    project = get_project_or_404(db, project_id)
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = db.scalars(
        select(ProjectTeamMember).where(
            ProjectTeamMember.project_id == project_id,
            ProjectTeamMember.user_id == payload.user_id,
            ProjectTeamMember.role == payload.role,
        )
    ).first()
    if existing is not None and existing.status == ProjectTeamMemberStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active team assignment already exists for this user and role",
        )

    if payload.is_primary:
        _clear_primary_flags(db, project_id)

    if existing is not None:
        member = existing
        for field, value in payload.model_dump().items():
            setattr(member, field, value)
        member.status = ProjectTeamMemberStatus.ACTIVE
        member.updated_at = datetime.now(UTC)
    else:
        member = ProjectTeamMember(project_id=project_id, **payload.model_dump())
        db.add(member)

    if payload.role == ProjectTeamRole.PROJECT_MANAGER and payload.is_primary:
        project.project_manager_user_id = payload.user_id
        if not project.assigned_project_manager:
            project.assigned_project_manager = user.full_name

    try:
        db.flush()
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.PROJECT,
            entity_id=project.id,
            description_key="activity.project.team_member_added",
            actor=actor,
            before={},
            after={"user_id": str(payload.user_id), "role": payload.role.value},
            metadata={"name": project.project_name},
            request=request,
            is_demo=project.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team assignment conflict",
        ) from exc
    db.refresh(member)
    return member


def update_team_member(
    db: Session,
    project_id: UUID,
    member_id: UUID,
    payload: ProjectTeamMemberUpdate,
    *,
    actor: User,
    request: Request | None = None,
) -> ProjectTeamMember:
    project = get_project_or_404(db, project_id)
    member = db.get(ProjectTeamMember, member_id)
    if member is None or member.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_primary"):
        _clear_primary_flags(db, project_id, exclude_id=member.id)

    before = {"role": member.role.value, "status": member.status.value, "is_primary": member.is_primary}
    for field, value in updates.items():
        setattr(member, field, value)
    member.updated_at = datetime.now(UTC)

    if member.role == ProjectTeamRole.PROJECT_MANAGER and member.is_primary:
        project.project_manager_user_id = member.user_id

    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT,
        entity_id=project.id,
        description_key="activity.project.team_member_updated",
        actor=actor,
        before=before,
        after={"role": member.role.value, "status": member.status.value, "is_primary": member.is_primary},
        metadata={"name": project.project_name},
        request=request,
        is_demo=project.is_demo,
    )
    db.commit()
    db.refresh(member)
    return member


def remove_team_member(
    db: Session,
    project_id: UUID,
    member_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> None:
    project = get_project_or_404(db, project_id)
    member = db.get(ProjectTeamMember, member_id)
    if member is None or member.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    if project.project_manager_user_id == member.user_id and member.role == ProjectTeamRole.PROJECT_MANAGER:
        project.project_manager_user_id = None

    db.delete(member)
    db.flush()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.PROJECT,
        entity_id=project.id,
        description_key="activity.project.team_member_removed",
        actor=actor,
        before={"member_id": str(member_id)},
        after={},
        metadata={"name": project.project_name},
        request=request,
        is_demo=project.is_demo,
    )
    db.commit()


def _clear_primary_flags(db: Session, project_id: UUID, *, exclude_id: UUID | None = None) -> None:
    members = db.scalars(
        select(ProjectTeamMember).where(
            ProjectTeamMember.project_id == project_id,
            ProjectTeamMember.is_primary.is_(True),
        )
    ).all()
    for member in members:
        if exclude_id is not None and member.id == exclude_id:
            continue
        member.is_primary = False
