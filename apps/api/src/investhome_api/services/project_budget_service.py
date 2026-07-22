"""Project budget foundation service (Sprint 10A4A)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from math import ceil
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.finance import ProjectBudget
from investhome_api.models.project import Project
from investhome_api.models.project_budget import (
    BudgetCategoryType,
    BudgetRevisionStatus,
    BudgetVersionStatus,
    ProjectBudgetCategory,
    ProjectBudgetLine,
    ProjectBudgetRevision,
    ProjectBudgetRevisionLine,
    ProjectBudgetVersion,
    ProjectCostCode,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_budget_foundation import (
    BudgetCategoryCreate,
    BudgetCategoryResponse,
    BudgetCategoryUpdate,
    BudgetImportConfirmRequest,
    BudgetImportPreviewResponse,
    BudgetImportPreviewRow,
    BudgetImportResultResponse,
    BudgetLineBulkCreateRequest,
    BudgetLineCreate,
    BudgetLineListResponse,
    BudgetLineReorderRequest,
    BudgetLineResponse,
    BudgetLineUpdate,
    BudgetPermissions,
    BudgetRevisionCreate,
    BudgetRevisionLineResponse,
    BudgetRevisionListResponse,
    BudgetRevisionResponse,
    BudgetRevisionUpdate,
    BudgetSummaryResponse,
    BudgetVersionCreate,
    BudgetVersionListResponse,
    BudgetVersionResponse,
    BudgetVersionUpdate,
    CategoryTotal,
    CostCodeCreate,
    CostCodeResponse,
    CostCodeUpdate,
    RevisionLineInput,
)
from investhome_api.schemas.project_dashboard import metric, unavailable
from investhome_api.services.activity_recorder import (
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_budget_status import (
    assert_version_editable,
    validate_revision_transition,
    validate_version_transition,
)
from investhome_api.services import project_service as project_svc

ZERO = Decimal("0")


def _perm(user: User, action: str) -> bool:
    return user_has_permission(user, "projects", action)


def budget_permissions(user: User) -> BudgetPermissions:
    view = _perm(user, "view_financial") or _perm(user, "edit_financial")
    return BudgetPermissions(
        can_view=view,
        can_edit=_perm(user, "edit_financial") or _perm(user, "manage_budget"),
        can_manage=_perm(user, "manage_budget") or _perm(user, "edit_financial"),
        can_approve=_perm(user, "approve_budget") or _perm(user, "edit_financial"),
        can_export=_perm(user, "export") or view,
        can_manage_cost_codes=_perm(user, "manage_cost_codes") or _perm(user, "edit_financial"),
    )


def require_view(user: User) -> None:
    if not budget_permissions(user).can_view:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Financial access required")


def require_edit(user: User) -> None:
    if not budget_permissions(user).can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget edit access required")


def require_manage(user: User) -> None:
    if not budget_permissions(user).can_manage:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget manage access required")


def require_approve(user: User) -> None:
    if not budget_permissions(user).can_approve:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget approve access required")


def require_cost_codes(user: User) -> None:
    if not budget_permissions(user).can_manage_cost_codes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cost code manage access required")


def _load_project(db: Session, project_id: UUID) -> Project:
    return project_svc.get_project_or_404(db, project_id, include_archived=True)


def _load_version(db: Session, project_id: UUID, budget_id: UUID) -> ProjectBudgetVersion:
    version = db.get(ProjectBudgetVersion, budget_id)
    if version is None or version.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget version not found")
    return version


def _money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return ZERO
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid monetary value",
        ) from exc
    return amount.quantize(Decimal("0.01"))


def _recalc_line(line: ProjectBudgetLine) -> None:
    line.current_budget = _money(line.original_budget) + _money(line.approved_revisions)
    if line.forecast_at_completion is not None:
        line.variance = _money(line.forecast_at_completion) - line.current_budget


def _version_totals(db: Session, version_id: UUID) -> tuple[Decimal, Decimal, Decimal]:
    row = db.execute(
        select(
            func.coalesce(func.sum(ProjectBudgetLine.original_budget), 0),
            func.coalesce(func.sum(ProjectBudgetLine.approved_revisions), 0),
            func.coalesce(func.sum(ProjectBudgetLine.current_budget), 0),
        ).where(
            ProjectBudgetLine.budget_version_id == version_id,
            ProjectBudgetLine.is_active.is_(True),
            ProjectBudgetLine.is_summary.is_(False),
        )
    ).one()
    return _money(row[0]), _money(row[1]), _money(row[2])


def _to_version_response(db: Session, version: ProjectBudgetVersion) -> BudgetVersionResponse:
    original, _revisions, current = _version_totals(db, version.id)
    data = BudgetVersionResponse.model_validate(version)
    return data.model_copy(
        update={"original_budget_total": original, "current_budget_total": current}
    )


def _to_line_response(
    line: ProjectBudgetLine,
    *,
    categories: dict[UUID, ProjectBudgetCategory],
    codes: dict[UUID, ProjectCostCode],
) -> BudgetLineResponse:
    category = categories.get(line.category_id)
    code = codes.get(line.cost_code_id) if line.cost_code_id else None
    base = BudgetLineResponse.model_validate(line)
    return base.model_copy(
        update={
            "category_code": category.code if category else None,
            "category_name": category.name if category else None,
            "cost_code": code.code if code else None,
            "cost_code_name": code.name if code else None,
        }
    )


def _load_categories_map(db: Session, ids: set[UUID]) -> dict[UUID, ProjectBudgetCategory]:
    if not ids:
        return {}
    rows = db.scalars(select(ProjectBudgetCategory).where(ProjectBudgetCategory.id.in_(ids))).all()
    return {row.id: row for row in rows}


def _load_codes_map(db: Session, ids: set[UUID]) -> dict[UUID, ProjectCostCode]:
    if not ids:
        return {}
    rows = db.scalars(select(ProjectCostCode).where(ProjectCostCode.id.in_(ids))).all()
    return {row.id: row for row in rows}


def _validate_category(db: Session, category_id: UUID) -> ProjectBudgetCategory:
    category = db.get(ProjectBudgetCategory, category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")
    return category


def _validate_cost_code(
    db: Session, cost_code_id: UUID | None, category_id: UUID
) -> ProjectCostCode | None:
    if cost_code_id is None:
        return None
    code = db.get(ProjectCostCode, cost_code_id)
    if code is None or not code.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid cost code")
    if code.category_id != category_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cost code does not belong to the selected category",
        )
    return code


def _assert_no_cycle(db: Session, line_id: UUID, parent_line_id: UUID | None) -> None:
    if parent_line_id is None:
        return
    if parent_line_id == line_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Budget line cannot be its own parent",
        )
    seen = {line_id}
    current = parent_line_id
    while current is not None:
        if current in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Circular budget line hierarchy is not allowed",
            )
        seen.add(current)
        parent = db.get(ProjectBudgetLine, current)
        current = parent.parent_line_id if parent else None


def _next_version_number(db: Session, project_id: UUID) -> int:
    current = db.scalar(
        select(func.max(ProjectBudgetVersion.version_number)).where(
            ProjectBudgetVersion.project_id == project_id
        )
    )
    return int(current or 0) + 1


def _log(
    db: Session,
    *,
    action_key: str,
    entity_id: UUID,
    actor: User | None,
    request: Request | None,
    metadata: dict | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    if before is not None and after is not None:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.PROJECT_BUDGET,
            entity_id=entity_id,
            description_key=action_key,
            actor=actor,
            before=before,
            after=after,
            metadata=metadata,
            request=request,
        )
    else:
        log_entity_created(
            db,
            entity_type=ActivityEntityType.PROJECT_BUDGET,
            entity_id=entity_id,
            description_key=action_key,
            actor=actor,
            metadata=metadata,
            request=request,
        )


# ---------------------------------------------------------------------------
# System taxonomy seed (for test DB / fresh installs without migration seed)
# ---------------------------------------------------------------------------

_SYSTEM_CATEGORIES = [
    ("LAND", "Land", BudgetCategoryType.LAND, 10),
    ("ACQ", "Acquisition", BudgetCategoryType.ACQUISITION, 20),
    ("HARD", "Hard Costs", BudgetCategoryType.HARD_COST, 30),
    ("SOFT", "Soft Costs", BudgetCategoryType.SOFT_COST, 40),
    ("FIN", "Financing", BudgetCategoryType.FINANCING, 50),
    ("MKT", "Marketing", BudgetCategoryType.MARKETING, 60),
    ("SALES", "Sales", BudgetCategoryType.SALES, 70),
    ("LEASE", "Leasing", BudgetCategoryType.LEASING, 80),
    ("OPS", "Operating", BudgetCategoryType.OPERATING, 90),
    ("CONT", "Contingency", BudgetCategoryType.CONTINGENCY, 100),
    ("TAX", "Tax", BudgetCategoryType.TAX, 110),
    ("INS", "Insurance", BudgetCategoryType.INSURANCE, 120),
    ("PROF", "Professional Fees", BudgetCategoryType.PROFESSIONAL_FEES, 130),
    ("DEVFEE", "Developer Fee", BudgetCategoryType.DEVELOPER_FEE, 140),
    ("OTHER", "Other", BudgetCategoryType.OTHER, 150),
]

_SYSTEM_COST_CODES = [
    ("01-000", "General Requirements", "HARD", 10),
    ("03-000", "Concrete", "HARD", 30),
    ("09-000", "Finishes", "HARD", 90),
    ("22-000", "Plumbing", "HARD", 110),
    ("23-000", "HVAC", "HARD", 120),
    ("26-000", "Electrical", "HARD", 130),
    ("A-100", "Architecture", "SOFT", 160),
    ("E-100", "Engineering", "SOFT", 170),
    ("L-100", "Legal", "SOFT", 180),
    ("C-100", "Contingency Allowance", "CONT", 200),
]


def ensure_system_taxonomy(db: Session) -> None:
    existing = db.scalar(
        select(func.count()).select_from(ProjectBudgetCategory).where(
            ProjectBudgetCategory.is_system.is_(True)
        )
    )
    if existing:
        return
    category_ids: dict[str, UUID] = {}
    for code, name, category_type, sort_order in _SYSTEM_CATEGORIES:
        row = ProjectBudgetCategory(
            company_id=None,
            code=code,
            name=name,
            category_type=category_type,
            sort_order=sort_order,
            is_active=True,
            is_system=True,
        )
        db.add(row)
        db.flush()
        category_ids[code] = row.id
    for code, name, category_code, sort_order in _SYSTEM_COST_CODES:
        db.add(
            ProjectCostCode(
                company_id=None,
                code=code,
                name=name,
                category_id=category_ids[category_code],
                level=1,
                sort_order=sort_order,
                is_active=True,
                is_system=True,
            )
        )
    db.commit()


# ---------------------------------------------------------------------------
# Categories / cost codes
# ---------------------------------------------------------------------------


def list_categories(
    db: Session,
    *,
    search: str | None = None,
    active_only: bool = True,
    company_id: UUID | None = None,
) -> list[BudgetCategoryResponse]:
    ensure_system_taxonomy(db)
    query = select(ProjectBudgetCategory)
    if active_only:
        query = query.where(ProjectBudgetCategory.is_active.is_(True))
    if company_id is not None:
        query = query.where(
            or_(
                ProjectBudgetCategory.company_id.is_(None),
                ProjectBudgetCategory.company_id == company_id,
            )
        )
    else:
        query = query.where(ProjectBudgetCategory.company_id.is_(None))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ProjectBudgetCategory.code.ilike(pattern),
                ProjectBudgetCategory.name.ilike(pattern),
            )
        )
    rows = db.scalars(query.order_by(ProjectBudgetCategory.sort_order.asc())).all()
    return [BudgetCategoryResponse.model_validate(row) for row in rows]


def create_category(
    db: Session, payload: BudgetCategoryCreate, *, actor: User
) -> BudgetCategoryResponse:
    require_cost_codes(actor)
    row = ProjectBudgetCategory(
        company_id=payload.company_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        description=payload.description,
        category_type=payload.category_type,
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
        is_active=True,
        is_system=False,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Category code already exists",
        ) from exc
    db.refresh(row)
    return BudgetCategoryResponse.model_validate(row)


def update_category(
    db: Session, category_id: UUID, payload: BudgetCategoryUpdate, *, actor: User
) -> BudgetCategoryResponse:
    require_cost_codes(actor)
    row = db.get(ProjectBudgetCategory, category_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if row.is_system and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="System categories cannot be deactivated via delete path",
        )
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return BudgetCategoryResponse.model_validate(row)


def delete_category(db: Session, category_id: UUID, *, actor: User) -> None:
    require_cost_codes(actor)
    row = db.get(ProjectBudgetCategory, category_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if row.is_system:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="System categories cannot be deleted",
        )
    in_use = db.scalar(
        select(func.count()).select_from(ProjectBudgetLine).where(
            ProjectBudgetLine.category_id == category_id
        )
    )
    if in_use:
        row.is_active = False
        db.commit()
        return
    db.delete(row)
    db.commit()


def list_cost_codes(
    db: Session,
    *,
    search: str | None = None,
    category_id: UUID | None = None,
    active_only: bool = True,
    company_id: UUID | None = None,
) -> list[CostCodeResponse]:
    ensure_system_taxonomy(db)
    query = select(ProjectCostCode)
    if active_only:
        query = query.where(ProjectCostCode.is_active.is_(True))
    if category_id is not None:
        query = query.where(ProjectCostCode.category_id == category_id)
    if company_id is not None:
        query = query.where(
            or_(ProjectCostCode.company_id.is_(None), ProjectCostCode.company_id == company_id)
        )
    else:
        query = query.where(ProjectCostCode.company_id.is_(None))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(ProjectCostCode.code.ilike(pattern), ProjectCostCode.name.ilike(pattern))
        )
    rows = db.scalars(query.order_by(ProjectCostCode.sort_order.asc())).all()
    return [CostCodeResponse.model_validate(row) for row in rows]


def create_cost_code(db: Session, payload: CostCodeCreate, *, actor: User) -> CostCodeResponse:
    require_cost_codes(actor)
    _validate_category(db, payload.category_id)
    row = ProjectCostCode(
        company_id=payload.company_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        description=payload.description,
        category_id=payload.category_id,
        parent_id=payload.parent_id,
        level=payload.level,
        sort_order=payload.sort_order,
        is_active=True,
        is_system=False,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cost code already exists",
        ) from exc
    db.refresh(row)
    return CostCodeResponse.model_validate(row)


def update_cost_code(
    db: Session, cost_code_id: UUID, payload: CostCodeUpdate, *, actor: User
) -> CostCodeResponse:
    require_cost_codes(actor)
    row = db.get(ProjectCostCode, cost_code_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost code not found")
    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates and updates["category_id"] is not None:
        _validate_category(db, updates["category_id"])
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return CostCodeResponse.model_validate(row)


def delete_cost_code(db: Session, cost_code_id: UUID, *, actor: User) -> None:
    require_cost_codes(actor)
    row = db.get(ProjectCostCode, cost_code_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost code not found")
    if row.is_system:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="System cost codes cannot be deleted",
        )
    in_use = db.scalar(
        select(func.count()).select_from(ProjectBudgetLine).where(
            ProjectBudgetLine.cost_code_id == cost_code_id
        )
    )
    if in_use:
        row.is_active = False
        db.commit()
        return
    db.delete(row)
    db.commit()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def list_versions(db: Session, user: User, project_id: UUID) -> BudgetVersionListResponse:
    require_view(user)
    _load_project(db, project_id)
    rows = list(
        db.scalars(
            select(ProjectBudgetVersion)
            .where(ProjectBudgetVersion.project_id == project_id)
            .order_by(ProjectBudgetVersion.version_number.desc())
        ).all()
    )
    return BudgetVersionListResponse(
        items=[_to_version_response(db, row) for row in rows],
        total=len(rows),
    )


def create_version(
    db: Session,
    user: User,
    project_id: UUID,
    payload: BudgetVersionCreate,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_manage(user)
    ensure_system_taxonomy(db)
    project = _load_project(db, project_id)
    version = ProjectBudgetVersion(
        company_id=project.company_id,
        project_id=project.id,
        name=payload.name.strip(),
        version_number=_next_version_number(db, project.id),
        status=BudgetVersionStatus.DRAFT,
        description=payload.description,
        currency=(payload.currency or project.currency or "USD").upper(),
        effective_date=payload.effective_date,
        is_current=False,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(version)
    db.flush()
    _log(
        db,
        action_key="activity.project_budget.created",
        entity_id=version.id,
        actor=user,
        request=request,
        metadata={"project_id": str(project.id), "version_number": version.version_number},
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def get_version(db: Session, user: User, project_id: UUID, budget_id: UUID) -> BudgetVersionResponse:
    require_view(user)
    version = _load_version(db, project_id, budget_id)
    return _to_version_response(db, version)


def update_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetVersionUpdate,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    before = snapshot_entity(version, ["name", "description", "effective_date", "status"])
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(version, key, value)
    version.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.updated",
        entity_id=version.id,
        actor=user,
        request=request,
        before=before,
        after=snapshot_entity(version, ["name", "description", "effective_date", "status"]),
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def archive_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_manage(user)
    version = _load_version(db, project_id, budget_id)
    validate_version_transition(version.status, BudgetVersionStatus.ARCHIVED)
    if version.is_current:
        version.is_current = False
    version.status = BudgetVersionStatus.ARCHIVED
    version.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.archived",
        entity_id=version.id,
        actor=user,
        request=request,
        metadata={"status": version.status.value},
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def submit_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_manage(user)
    version = _load_version(db, project_id, budget_id)
    validate_version_transition(version.status, BudgetVersionStatus.IN_REVIEW)
    active_lines = db.scalar(
        select(func.count()).select_from(ProjectBudgetLine).where(
            ProjectBudgetLine.budget_version_id == version.id,
            ProjectBudgetLine.is_active.is_(True),
        )
    )
    if not active_lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Budget must contain at least one active line before submission",
        )
    project = _load_project(db, project_id)
    if version.currency.upper() != (project.currency or "USD").upper():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Budget currency must match project currency",
        )
    version.status = BudgetVersionStatus.IN_REVIEW
    version.submitted_at = datetime.now(UTC)
    version.submitted_by_user_id = user.id
    version.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.submitted",
        entity_id=version.id,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def approve_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_approve(user)
    version = _load_version(db, project_id, budget_id)
    validate_version_transition(version.status, BudgetVersionStatus.APPROVED)
    if version.submitted_by_user_id and version.submitted_by_user_id == user.id:
        # Soft separation of duties — allow if user also has manage, but prefer distinct actors
        if not _perm(user, "manage_budget") and not user_has_permission(user, "finance", "approve"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Submitter cannot approve the same budget",
            )

    current_versions = list(
        db.scalars(
            select(ProjectBudgetVersion).where(
                ProjectBudgetVersion.project_id == project_id,
                ProjectBudgetVersion.is_current.is_(True),
                ProjectBudgetVersion.id != version.id,
            )
        ).all()
    )
    for other in current_versions:
        if other.status == BudgetVersionStatus.APPROVED:
            validate_version_transition(other.status, BudgetVersionStatus.SUPERSEDED)
            other.status = BudgetVersionStatus.SUPERSEDED
        other.is_current = False

    now = datetime.now(UTC)
    version.status = BudgetVersionStatus.APPROVED
    version.approved_at = now
    version.approved_by_user_id = user.id
    version.locked_at = now
    version.locked_by_user_id = user.id
    version.is_current = True
    version.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.approved",
        entity_id=version.id,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def reject_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_approve(user)
    version = _load_version(db, project_id, budget_id)
    validate_version_transition(version.status, BudgetVersionStatus.REJECTED)
    version.status = BudgetVersionStatus.REJECTED
    version.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.rejected",
        entity_id=version.id,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def set_current_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_manage(user)
    version = _load_version(db, project_id, budget_id)
    if version.status != BudgetVersionStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only approved budgets can be set as current",
        )
    others = list(
        db.scalars(
            select(ProjectBudgetVersion).where(
                ProjectBudgetVersion.project_id == project_id,
                ProjectBudgetVersion.is_current.is_(True),
                ProjectBudgetVersion.id != version.id,
            )
        ).all()
    )
    for other in others:
        other.is_current = False
        if other.status == BudgetVersionStatus.APPROVED:
            other.status = BudgetVersionStatus.SUPERSEDED
    version.is_current = True
    version.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.set_current",
        entity_id=version.id,
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(version)
    return _to_version_response(db, version)


def clone_version(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetVersionResponse:
    require_manage(user)
    source = _load_version(db, project_id, budget_id)
    project = _load_project(db, project_id)
    clone = ProjectBudgetVersion(
        company_id=project.company_id,
        project_id=project.id,
        name=f"{source.name} (Copy)",
        version_number=_next_version_number(db, project.id),
        status=BudgetVersionStatus.DRAFT,
        description=source.description,
        currency=source.currency,
        effective_date=None,
        is_current=False,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(clone)
    db.flush()

    lines = list(
        db.scalars(
            select(ProjectBudgetLine).where(ProjectBudgetLine.budget_version_id == source.id)
        ).all()
    )
    id_map: dict[UUID, UUID] = {}
    # First pass without parents
    for line in sorted(lines, key=lambda item: item.sort_order):
        new_line = ProjectBudgetLine(
            company_id=project.company_id,
            project_id=project.id,
            budget_version_id=clone.id,
            category_id=line.category_id,
            cost_code_id=line.cost_code_id,
            parent_line_id=None,
            line_number=line.line_number,
            name=line.name,
            description=line.description,
            quantity=line.quantity,
            unit=line.unit,
            unit_cost=line.unit_cost,
            original_budget=line.original_budget,
            approved_revisions=ZERO,
            current_budget=line.original_budget,
            committed_cost=None,
            actual_cost=None,
            forecast_to_complete=None,
            forecast_at_completion=None,
            variance=None,
            currency=line.currency,
            notes=line.notes,
            sort_order=line.sort_order,
            is_summary=line.is_summary,
            is_active=line.is_active,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        db.add(new_line)
        db.flush()
        id_map[line.id] = new_line.id

    for line in lines:
        if line.parent_line_id and line.parent_line_id in id_map:
            cloned = db.get(ProjectBudgetLine, id_map[line.id])
            if cloned is not None:
                cloned.parent_line_id = id_map[line.parent_line_id]

    _log(
        db,
        action_key="activity.project_budget.cloned",
        entity_id=clone.id,
        actor=user,
        request=request,
        metadata={"source_budget_id": str(source.id)},
    )
    db.commit()
    db.refresh(clone)
    return _to_version_response(db, clone)


# ---------------------------------------------------------------------------
# Lines
# ---------------------------------------------------------------------------


def list_lines(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    *,
    search: str | None = None,
    category_id: UUID | None = None,
    cost_code_id: UUID | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 100,
) -> BudgetLineListResponse:
    require_view(user)
    _load_version(db, project_id, budget_id)
    query = select(ProjectBudgetLine).where(ProjectBudgetLine.budget_version_id == budget_id)
    count_query = (
        select(func.count())
        .select_from(ProjectBudgetLine)
        .where(ProjectBudgetLine.budget_version_id == budget_id)
    )
    if active_only:
        query = query.where(ProjectBudgetLine.is_active.is_(True))
        count_query = count_query.where(ProjectBudgetLine.is_active.is_(True))
    if category_id is not None:
        query = query.where(ProjectBudgetLine.category_id == category_id)
        count_query = count_query.where(ProjectBudgetLine.category_id == category_id)
    if cost_code_id is not None:
        query = query.where(ProjectBudgetLine.cost_code_id == cost_code_id)
        count_query = count_query.where(ProjectBudgetLine.cost_code_id == cost_code_id)
    if search:
        pattern = f"%{search.strip()}%"
        cond = or_(
            ProjectBudgetLine.name.ilike(pattern),
            ProjectBudgetLine.line_number.ilike(pattern),
            ProjectBudgetLine.description.ilike(pattern),
        )
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = int(db.scalar(count_query) or 0)
    pages = max(1, ceil(total / page_size)) if total else 1
    rows = list(
        db.scalars(
            query.order_by(ProjectBudgetLine.sort_order.asc(), ProjectBudgetLine.line_number.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    categories = _load_categories_map(db, {row.category_id for row in rows})
    codes = _load_codes_map(db, {row.cost_code_id for row in rows if row.cost_code_id})
    return BudgetLineListResponse(
        items=[_to_line_response(row, categories=categories, codes=codes) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def create_line(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetLineCreate,
    *,
    request: Request | None = None,
    commit: bool = True,
) -> BudgetLineResponse:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    project = _load_project(db, project_id)
    _validate_category(db, payload.category_id)
    _validate_cost_code(db, payload.cost_code_id, payload.category_id)
    if payload.parent_line_id:
        parent = db.get(ProjectBudgetLine, payload.parent_line_id)
        if parent is None or parent.budget_version_id != version.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parent line must belong to the same budget",
            )
    original = _money(payload.original_budget)
    if original < ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Original budget cannot be negative",
        )
    line = ProjectBudgetLine(
        company_id=project.company_id,
        project_id=project.id,
        budget_version_id=version.id,
        category_id=payload.category_id,
        cost_code_id=payload.cost_code_id,
        parent_line_id=payload.parent_line_id,
        line_number=payload.line_number.strip(),
        name=payload.name.strip(),
        description=payload.description,
        quantity=payload.quantity,
        unit=payload.unit,
        unit_cost=_money(payload.unit_cost) if payload.unit_cost is not None else None,
        original_budget=original,
        approved_revisions=ZERO,
        current_budget=original,
        currency=version.currency,
        notes=payload.notes,
        sort_order=payload.sort_order,
        is_summary=payload.is_summary,
        is_active=True,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(line)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Duplicate line number for this budget version",
        ) from exc
    _log(
        db,
        action_key="activity.project_budget.line_created",
        entity_id=version.id,
        actor=user,
        request=request,
        metadata={"line_id": str(line.id), "line_number": line.line_number},
    )
    if commit:
        db.commit()
        db.refresh(line)
    categories = _load_categories_map(db, {line.category_id})
    codes = _load_codes_map(db, {line.cost_code_id} if line.cost_code_id else set())
    return _to_line_response(line, categories=categories, codes=codes)


def update_line(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    line_id: UUID,
    payload: BudgetLineUpdate,
    *,
    request: Request | None = None,
) -> BudgetLineResponse:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    line = db.get(ProjectBudgetLine, line_id)
    if line is None or line.budget_version_id != version.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget line not found")
    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates and updates["category_id"] is not None:
        _validate_category(db, updates["category_id"])
    category_id = updates.get("category_id", line.category_id)
    if "cost_code_id" in updates:
        _validate_cost_code(db, updates["cost_code_id"], category_id)
    if "parent_line_id" in updates:
        _assert_no_cycle(db, line.id, updates["parent_line_id"])
    if "original_budget" in updates and updates["original_budget"] is not None:
        updates["original_budget"] = _money(updates["original_budget"])
        if updates["original_budget"] < ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Original budget cannot be negative",
            )
    before = snapshot_entity(line, ["name", "original_budget", "category_id", "cost_code_id"])
    for key, value in updates.items():
        setattr(line, key, value)
    _recalc_line(line)
    line.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.line_updated",
        entity_id=version.id,
        actor=user,
        request=request,
        before=before,
        after=snapshot_entity(line, ["name", "original_budget", "category_id", "cost_code_id"]),
        metadata={"line_id": str(line.id)},
    )
    db.commit()
    db.refresh(line)
    categories = _load_categories_map(db, {line.category_id})
    codes = _load_codes_map(db, {line.cost_code_id} if line.cost_code_id else set())
    return _to_line_response(line, categories=categories, codes=codes)


def delete_line(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    line_id: UUID,
    *,
    request: Request | None = None,
) -> None:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    line = db.get(ProjectBudgetLine, line_id)
    if line is None or line.budget_version_id != version.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget line not found")
    children = db.scalar(
        select(func.count()).select_from(ProjectBudgetLine).where(
            ProjectBudgetLine.parent_line_id == line.id
        )
    )
    if children:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Remove child lines before deleting a parent line",
        )
    db.delete(line)
    _log(
        db,
        action_key="activity.project_budget.line_deleted",
        entity_id=version.id,
        actor=user,
        request=request,
        metadata={"line_id": str(line_id)},
    )
    db.commit()


def reorder_lines(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetLineReorderRequest,
    *,
    request: Request | None = None,
) -> BudgetLineListResponse:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    for index, line_id in enumerate(payload.line_ids, start=1):
        line = db.get(ProjectBudgetLine, line_id)
        if line is None or line.budget_version_id != version.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget line not found")
        line.sort_order = index
        line.updated_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.lines_reordered",
        entity_id=version.id,
        actor=user,
        request=request,
    )
    db.commit()
    return list_lines(db, user, project_id, budget_id)


def bulk_create_lines(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetLineBulkCreateRequest,
    *,
    request: Request | None = None,
) -> BudgetLineListResponse:
    require_edit(user)
    for line_payload in payload.lines:
        create_line(db, user, project_id, budget_id, line_payload, request=request)
    return list_lines(db, user, project_id, budget_id)


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


def _to_revision_response(db: Session, revision: ProjectBudgetRevision) -> BudgetRevisionResponse:
    lines = list(
        db.scalars(
            select(ProjectBudgetRevisionLine).where(
                ProjectBudgetRevisionLine.revision_id == revision.id
            )
        ).all()
    )
    data = BudgetRevisionResponse.model_validate(revision)
    return data.model_copy(
        update={
            "lines": [BudgetRevisionLineResponse.model_validate(line) for line in lines]
        }
    )


def list_revisions(
    db: Session, user: User, project_id: UUID, budget_id: UUID
) -> BudgetRevisionListResponse:
    require_view(user)
    _load_version(db, project_id, budget_id)
    rows = list(
        db.scalars(
            select(ProjectBudgetRevision)
            .where(ProjectBudgetRevision.budget_version_id == budget_id)
            .order_by(ProjectBudgetRevision.revision_number.desc())
        ).all()
    )
    return BudgetRevisionListResponse(
        items=[_to_revision_response(db, row) for row in rows],
        total=len(rows),
    )


def create_revision(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetRevisionCreate,
    *,
    request: Request | None = None,
) -> BudgetRevisionResponse:
    require_manage(user)
    version = _load_version(db, project_id, budget_id)
    if version.status != BudgetVersionStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Revisions can only be created against approved budgets",
        )
    next_number = int(
        db.scalar(
            select(func.max(ProjectBudgetRevision.revision_number)).where(
                ProjectBudgetRevision.budget_version_id == version.id
            )
        )
        or 0
    ) + 1
    amount = ZERO
    for item in payload.lines:
        line = db.get(ProjectBudgetLine, item.budget_line_id)
        if line is None or line.budget_version_id != version.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Revision line must reference a line in this budget",
            )
        amount += _money(item.amount)

    revision = ProjectBudgetRevision(
        company_id=version.company_id,
        project_id=project_id,
        budget_version_id=version.id,
        revision_number=next_number,
        title=payload.title.strip(),
        description=payload.description,
        status=BudgetRevisionStatus.DRAFT,
        effective_date=payload.effective_date,
        amount=amount,
    )
    db.add(revision)
    db.flush()
    for item in payload.lines:
        db.add(
            ProjectBudgetRevisionLine(
                revision_id=revision.id,
                budget_line_id=item.budget_line_id,
                amount=_money(item.amount),
                description=item.description,
            )
        )
    _log(
        db,
        action_key="activity.project_budget.revision_created",
        entity_id=version.id,
        actor=user,
        request=request,
        metadata={"revision_id": str(revision.id)},
    )
    db.commit()
    db.refresh(revision)
    return _to_revision_response(db, revision)


def _load_revision(
    db: Session, project_id: UUID, budget_id: UUID, revision_id: UUID
) -> ProjectBudgetRevision:
    revision = db.get(ProjectBudgetRevision, revision_id)
    if (
        revision is None
        or revision.project_id != project_id
        or revision.budget_version_id != budget_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    return revision


def update_revision(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    payload: BudgetRevisionUpdate,
    *,
    request: Request | None = None,
) -> BudgetRevisionResponse:
    require_manage(user)
    revision = _load_revision(db, project_id, budget_id, revision_id)
    if revision.status not in {BudgetRevisionStatus.DRAFT, BudgetRevisionStatus.REJECTED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Revision is locked")
    updates = payload.model_dump(exclude_unset=True)
    lines = updates.pop("lines", None)
    for key, value in updates.items():
        setattr(revision, key, value)
    if lines is not None:
        for existing in list(
            db.scalars(
                select(ProjectBudgetRevisionLine).where(
                    ProjectBudgetRevisionLine.revision_id == revision.id
                )
            ).all()
        ):
            db.delete(existing)
        amount = ZERO
        for item_data in lines:
            item = RevisionLineInput.model_validate(item_data)
            amount += _money(item.amount)
            db.add(
                ProjectBudgetRevisionLine(
                    revision_id=revision.id,
                    budget_line_id=item.budget_line_id,
                    amount=_money(item.amount),
                    description=item.description,
                )
            )
        revision.amount = amount
    _log(
        db,
        action_key="activity.project_budget.revision_updated",
        entity_id=budget_id,
        actor=user,
        request=request,
        metadata={"revision_id": str(revision.id)},
    )
    db.commit()
    db.refresh(revision)
    return _to_revision_response(db, revision)


def submit_revision(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetRevisionResponse:
    require_manage(user)
    revision = _load_revision(db, project_id, budget_id, revision_id)
    validate_revision_transition(revision.status, BudgetRevisionStatus.IN_REVIEW)
    revision.status = BudgetRevisionStatus.IN_REVIEW
    revision.submitted_at = datetime.now(UTC)
    revision.submitted_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.revision_submitted",
        entity_id=budget_id,
        actor=user,
        request=request,
        metadata={"revision_id": str(revision.id)},
    )
    db.commit()
    db.refresh(revision)
    return _to_revision_response(db, revision)


def approve_revision(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetRevisionResponse:
    require_approve(user)
    revision = _load_revision(db, project_id, budget_id, revision_id)
    validate_revision_transition(revision.status, BudgetRevisionStatus.APPROVED)
    version = _load_version(db, project_id, budget_id)
    if version.status != BudgetVersionStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Target budget must be approved",
        )

    lines = list(
        db.scalars(
            select(ProjectBudgetRevisionLine).where(
                ProjectBudgetRevisionLine.revision_id == revision.id
            )
        ).all()
    )
    for item in lines:
        budget_line = db.get(ProjectBudgetLine, item.budget_line_id)
        if budget_line is None:
            continue
        # Never mutate original_budget
        budget_line.approved_revisions = _money(budget_line.approved_revisions) + _money(item.amount)
        _recalc_line(budget_line)
        budget_line.updated_by_user_id = user.id

    revision.status = BudgetRevisionStatus.APPROVED
    revision.approved_at = datetime.now(UTC)
    revision.approved_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.revision_approved",
        entity_id=budget_id,
        actor=user,
        request=request,
        metadata={"revision_id": str(revision.id), "amount": str(revision.amount)},
    )
    db.commit()
    db.refresh(revision)
    return _to_revision_response(db, revision)


def reject_revision(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetRevisionResponse:
    require_approve(user)
    revision = _load_revision(db, project_id, budget_id, revision_id)
    validate_revision_transition(revision.status, BudgetRevisionStatus.REJECTED)
    revision.status = BudgetRevisionStatus.REJECTED
    revision.rejected_at = datetime.now(UTC)
    revision.rejected_by_user_id = user.id
    _log(
        db,
        action_key="activity.project_budget.revision_rejected",
        entity_id=budget_id,
        actor=user,
        request=request,
        metadata={"revision_id": str(revision.id)},
    )
    db.commit()
    db.refresh(revision)
    return _to_revision_response(db, revision)


def cancel_revision(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    *,
    request: Request | None = None,
) -> BudgetRevisionResponse:
    require_manage(user)
    revision = _load_revision(db, project_id, budget_id, revision_id)
    validate_revision_transition(revision.status, BudgetRevisionStatus.CANCELLED)
    revision.status = BudgetRevisionStatus.CANCELLED
    _log(
        db,
        action_key="activity.project_budget.revision_cancelled",
        entity_id=budget_id,
        actor=user,
        request=request,
        metadata={"revision_id": str(revision.id)},
    )
    db.commit()
    db.refresh(revision)
    return _to_revision_response(db, revision)


# ---------------------------------------------------------------------------
# Summary / import / export
# ---------------------------------------------------------------------------


def get_revision(
    db: Session, user: User, project_id: UUID, budget_id: UUID, revision_id: UUID
) -> BudgetRevisionResponse:
    require_view(user)
    revision = _load_revision(db, project_id, budget_id, revision_id)
    return _to_revision_response(db, revision)


def get_budget_summary(db: Session, user: User, project_id: UUID) -> BudgetSummaryResponse:
    require_view(user)
    ensure_system_taxonomy(db)
    project = _load_project(db, project_id)
    permissions = budget_permissions(user)
    warnings: list[str] = []
    completeness: dict[str, str] = {}

    current = db.scalars(
        select(ProjectBudgetVersion).where(
            ProjectBudgetVersion.project_id == project_id,
            ProjectBudgetVersion.is_current.is_(True),
            ProjectBudgetVersion.status == BudgetVersionStatus.APPROVED,
        )
    ).first()
    if current is None:
        current = db.scalars(
            select(ProjectBudgetVersion)
            .where(ProjectBudgetVersion.project_id == project_id)
            .order_by(ProjectBudgetVersion.version_number.desc())
        ).first()

    legacy = list(
        db.scalars(select(ProjectBudget).where(ProjectBudget.project_id == project_id)).all()
    )
    legacy_payload = [
        {
            "id": str(item.id),
            "budget_name": item.budget_name,
            "category": item.category.value if item.category else None,
            "original_budget": item.original_budget,
            "revised_budget": item.revised_budget,
            "paid_amount": item.paid_amount,
            "committed_amount": item.committed_amount,
            "currency": item.currency,
        }
        for item in legacy
    ]

    if current is None:
        completeness["budget"] = "missing"
        warnings.append("No budget versions exist for this project.")
        return BudgetSummaryResponse(
            budget_version=None,
            totals={
                "original_budget": unavailable("No approved budget exists"),
                "approved_revisions": unavailable("No approved budget exists"),
                "current_budget": unavailable("No approved budget exists"),
                "committed_cost": unavailable("Committed cost unavailable — no approved budget exists"),
                "actual_cost": unavailable("Actual cost unavailable — no approved budget exists"),
                "paid_cost": unavailable("Paid cost unavailable — no approved budget exists"),
                "retained_cost": unavailable("Retained cost unavailable — no approved budget exists"),
                "remaining_budget": unavailable("No approved budget exists"),
                "available_to_commit": unavailable("No approved budget exists"),
                "forecast_at_completion": unavailable("Forecasting is not implemented"),
                "basic_forecast_at_completion": unavailable("No approved budget exists"),
                "projected_variance": unavailable("Forecasting is not implemented"),
                "contingency_budget": unavailable("No contingency lines"),
                "contingency_used": unavailable("Actual cost unavailable — no approved budget exists"),
                "contingency_remaining": unavailable("No contingency lines"),
                "budget_utilization_percentage": unavailable("No approved budget exists"),
            },
            categories=[],
            data_completeness=completeness,
            permissions=permissions,
            warnings=warnings,
            legacy_budgets=legacy_payload,
        )

    lines = list(
        db.scalars(
            select(ProjectBudgetLine).where(
                ProjectBudgetLine.budget_version_id == current.id,
                ProjectBudgetLine.is_active.is_(True),
                ProjectBudgetLine.is_summary.is_(False),
            )
        ).all()
    )
    original = sum((_money(line.original_budget) for line in lines), ZERO)
    revisions = sum((_money(line.approved_revisions) for line in lines), ZERO)
    current_total = sum((_money(line.current_budget) for line in lines), ZERO)

    categories_map = _load_categories_map(db, {line.category_id for line in lines})
    by_category: dict[UUID, CategoryTotal] = {}
    for line in lines:
        category = categories_map.get(line.category_id)
        if category is None:
            continue
        bucket = by_category.get(category.id)
        if bucket is None:
            bucket = CategoryTotal(
                category_id=category.id,
                category_code=category.code,
                category_name=category.name,
                category_type=category.category_type.value,
                original_budget=ZERO,
                approved_revisions=ZERO,
                current_budget=ZERO,
                line_count=0,
            )
            by_category[category.id] = bucket
        bucket.original_budget += _money(line.original_budget)
        bucket.approved_revisions += _money(line.approved_revisions)
        bucket.current_budget += _money(line.current_budget)
        bucket.line_count += 1

    contingency = sum(
        (
            _money(line.current_budget)
            for line in lines
            if categories_map.get(line.category_id)
            and categories_map[line.category_id].category_type == BudgetCategoryType.CONTINGENCY
        ),
        ZERO,
    )

    completeness["budget"] = (
        "approved" if current.status == BudgetVersionStatus.APPROVED and current.is_current else "draft"
    )
    completeness["lines"] = "present" if lines else "missing"
    if not lines:
        warnings.append("Budget has no active lines.")

    # Normalized cost rollups (10A4B). Do not mix with legacy ProjectBudget.paid_amount.
    from investhome_api.services.project_cost_service import (
        project_cost_totals,
        project_has_normalized_cost_data,
    )

    cost_totals = project_cost_totals(db, project_id)
    committed_cost = cost_totals["committed_cost"]
    pending_commitments = cost_totals["pending_commitments"]
    actual_cost = cost_totals["actual_cost"]
    paid_cost = cost_totals["paid_cost"]
    retained_cost = cost_totals["retained_cost"]
    has_normalized = project_has_normalized_cost_data(db, project_id)
    remaining_budget = current_total - actual_cost
    available_to_commit = current_total - committed_cost
    commitment_remaining = max(committed_cost - actual_cost, ZERO)
    basic_forecast = actual_cost + commitment_remaining
    projected_variance = current_total - basic_forecast
    utilization = (
        (actual_cost / current_total) * Decimal("100") if current_total > ZERO else None
    )

    completeness["actual_cost"] = "normalized" if has_normalized else "zero"
    completeness["committed_cost"] = "normalized" if has_normalized else "zero"
    completeness["forecast"] = "basic_commitment_based"
    warnings.append(
        "basic_forecast_at_completion is a commitment-based estimate, not a full forecasting engine"
    )

    return BudgetSummaryResponse(
        budget_version=_to_version_response(db, current),
        totals={
            "original_budget": metric(original),
            "approved_revisions": metric(revisions),
            "current_budget": metric(current_total),
            "committed_cost": metric(committed_cost),
            "pending_commitments": metric(pending_commitments),
            "actual_cost": metric(actual_cost),
            "paid_cost": metric(paid_cost),
            "retained_cost": metric(retained_cost),
            "remaining_budget": metric(remaining_budget),
            "available_to_commit": metric(available_to_commit),
            "forecast_at_completion": unavailable(
                "Full forecasting engine is not implemented; see basic_forecast_at_completion"
            ),
            "basic_forecast_at_completion": metric(basic_forecast),
            "projected_variance": metric(projected_variance),
            "contingency_budget": metric(contingency) if contingency > ZERO else unavailable("No contingency lines"),
            "contingency_used": unavailable("Contingency usage tracking is not implemented"),
            "contingency_remaining": (
                metric(contingency) if contingency > ZERO else unavailable("No contingency lines")
            ),
            "budget_utilization_percentage": (
                metric(utilization.quantize(Decimal("0.01")))
                if utilization is not None
                else unavailable("No budget baseline")
            ),
        },
        categories=sorted(by_category.values(), key=lambda item: item.category_code),
        data_completeness=completeness,
        permissions=permissions,
        warnings=warnings,
        legacy_budgets=legacy_payload,
    )


def preview_import_csv(
    db: Session, user: User, project_id: UUID, budget_id: UUID, content: str
) -> BudgetImportPreviewResponse:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV has no headers")

    categories = {
        row.code.upper(): row
        for row in db.scalars(select(ProjectBudgetCategory).where(ProjectBudgetCategory.is_active.is_(True))).all()
    }
    codes = {
        row.code: row
        for row in db.scalars(select(ProjectCostCode).where(ProjectCostCode.is_active.is_(True))).all()
    }
    existing_numbers = {
        row.line_number
        for row in db.scalars(
            select(ProjectBudgetLine).where(ProjectBudgetLine.budget_version_id == version.id)
        ).all()
    }
    seen_numbers: set[str] = set()
    rows: list[BudgetImportPreviewRow] = []
    for index, raw in enumerate(reader, start=2):
        errors: list[str] = []
        category_code = (raw.get("category_code") or "").strip().upper()
        cost_code = (raw.get("cost_code") or "").strip()
        line_number = (raw.get("line_number") or "").strip()
        name = (raw.get("name") or "").strip()
        if not category_code or category_code not in categories:
            errors.append("Unknown or missing category_code")
        if cost_code and cost_code not in codes:
            errors.append("Unknown cost_code")
        if cost_code and category_code in categories:
            code_row = codes.get(cost_code)
            if code_row and code_row.category_id != categories[category_code].id:
                errors.append("cost_code does not belong to category_code")
        if not line_number:
            errors.append("Missing line_number")
        elif line_number in existing_numbers or line_number in seen_numbers:
            errors.append("Duplicate line_number")
        if not name:
            errors.append("Missing name")
        try:
            original = _money(raw.get("original_budget") or "0")
            if original < ZERO:
                errors.append("original_budget cannot be negative")
        except HTTPException:
            errors.append("Invalid original_budget")
            original = ZERO
        seen_numbers.add(line_number)
        rows.append(
            BudgetImportPreviewRow(
                row_number=index,
                valid=len(errors) == 0,
                errors=errors,
                data={
                    "category_code": category_code,
                    "cost_code": cost_code or None,
                    "line_number": line_number,
                    "name": name,
                    "description": (raw.get("description") or None),
                    "original_budget": str(original),
                    "quantity": raw.get("quantity") or None,
                    "unit": raw.get("unit") or None,
                    "unit_cost": raw.get("unit_cost") or None,
                    "notes": raw.get("notes") or None,
                },
            )
        )

    valid_rows = sum(1 for row in rows if row.valid)
    return BudgetImportPreviewResponse(
        valid=valid_rows == len(rows) and len(rows) > 0,
        total_rows=len(rows),
        valid_rows=valid_rows,
        invalid_rows=len(rows) - valid_rows,
        rows=rows,
    )


def confirm_import_csv(
    db: Session,
    user: User,
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetImportConfirmRequest,
    *,
    request: Request | None = None,
) -> BudgetImportResultResponse:
    require_edit(user)
    version = _load_version(db, project_id, budget_id)
    assert_version_editable(version.status)
    categories = {
        row.code.upper(): row
        for row in db.scalars(select(ProjectBudgetCategory).where(ProjectBudgetCategory.is_active.is_(True))).all()
    }
    codes = {
        row.code: row
        for row in db.scalars(select(ProjectCostCode).where(ProjectCostCode.is_active.is_(True))).all()
    }

    # Transactional: validate all first
    prepared: list[BudgetLineCreate] = []
    errors: list[str] = []
    for index, raw in enumerate(payload.rows, start=1):
        category_code = str(raw.get("category_code") or "").upper()
        cost_code = raw.get("cost_code")
        if category_code not in categories:
            errors.append(f"Row {index}: unknown category")
            continue
        cost_code_id = None
        if cost_code:
            code_row = codes.get(str(cost_code))
            if code_row is None:
                errors.append(f"Row {index}: unknown cost code")
                continue
            cost_code_id = code_row.id
        prepared.append(
            BudgetLineCreate(
                category_id=categories[category_code].id,
                cost_code_id=cost_code_id,
                line_number=str(raw.get("line_number") or ""),
                name=str(raw.get("name") or ""),
                description=raw.get("description"),
                original_budget=_money(raw.get("original_budget")),
                quantity=Decimal(str(raw["quantity"])) if raw.get("quantity") not in (None, "") else None,
                unit=raw.get("unit"),
                unit_cost=_money(raw.get("unit_cost")) if raw.get("unit_cost") not in (None, "") else None,
                notes=raw.get("notes"),
                sort_order=index,
            )
        )
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors})

    try:
        for line_payload in prepared:
            create_line(
                db, user, project_id, budget_id, line_payload, request=request, commit=False
            )
        _log(
            db,
            action_key="activity.project_budget.csv_imported",
            entity_id=budget_id,
            actor=user,
            request=request,
            metadata={"imported": len(prepared)},
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Import transaction failed",
        ) from exc
    return BudgetImportResultResponse(imported=len(prepared), skipped=0, errors=[])


def export_lines_csv(db: Session, user: User, project_id: UUID, budget_id: UUID) -> str:
    require_view(user)
    if not budget_permissions(user).can_export:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Export permission required")
    version = _load_version(db, project_id, budget_id)
    project = _load_project(db, project_id)
    lines = list_lines(db, user, project_id, budget_id, page=1, page_size=5000).items
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "project_code",
            "project_name",
            "budget_name",
            "budget_version",
            "status",
            "currency",
            "line_number",
            "category_code",
            "cost_code",
            "name",
            "original_budget",
            "approved_revisions",
            "current_budget",
            "notes",
        ]
    )
    for line in lines:
        writer.writerow(
            [
                project.project_code,
                project.project_name,
                version.name,
                version.version_number,
                version.status.value,
                version.currency,
                line.line_number,
                line.category_code,
                line.cost_code,
                line.name,
                line.original_budget,
                line.approved_revisions,
                line.current_budget,
                line.notes or "",
            ]
        )
    return buffer.getvalue()
