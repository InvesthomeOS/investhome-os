"""Role and permission management routes."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.api.deps.auth import get_current_user, require_manage_roles, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import Permission, Role, RolePermission, User
from investhome_api.schemas.auth import (
    PermissionListResponse,
    PermissionResponse,
    RoleCreate,
    RoleDetail,
    RoleListResponse,
    RolePermissionsUpdate,
    RoleSummary,
    RoleUpdate,
)
from investhome_api.services.audit_service import record_auth_event
from investhome_api.services.permission_service import (
    ensure_not_privilege_escalation,
    get_all_permissions,
)

router = APIRouter(prefix="/roles", tags=["roles"])
permissions_router = APIRouter(prefix="/permissions", tags=["permissions"])


def _serialize_role(role: Role, *, detailed: bool = False) -> RoleSummary | RoleDetail:
    if detailed:
        return RoleDetail.model_validate(role)
    return RoleSummary.model_validate(role)


def _get_role_or_404(role_id: UUID, db: Session) -> Role:
    role = db.scalar(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.permissions))
    )
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.get("", response_model=RoleListResponse)
def list_roles(
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("roles", "view")),
) -> RoleListResponse:
    roles = db.scalars(select(Role).order_by(Role.name.asc())).all()
    return RoleListResponse(
        items=[RoleSummary.model_validate(role) for role in roles],
        total=len(roles),
    )


@router.get("/{role_id}", response_model=RoleDetail)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("roles", "view")),
) -> RoleDetail:
    return RoleDetail.model_validate(_get_role_or_404(role_id, db))


@router.post("", response_model=RoleDetail, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_roles()),
) -> RoleDetail:
    code = payload.code.lower()
    existing = db.scalar(select(Role.id).where(Role.code == code))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role code already exists")

    role = Role(
        name=payload.name,
        code=code,
        description=payload.description,
        is_system_role=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    record_auth_event(
        "roles.created",
        db=db,
        actor=actor,
        target_id=role.id,
        request=request,
    )
    return RoleDetail.model_validate(role)


@router.patch("/{role_id}", response_model=RoleDetail)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_roles()),
) -> RoleDetail:
    role = _get_role_or_404(role_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    if role.is_system_role and "name" not in updates and "description" not in updates:
        pass

    for field, value in updates.items():
        setattr(role, field, value)

    role.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(role)
    record_auth_event(
        "roles.updated",
        db=db,
        actor=actor,
        target_id=role.id,
        request=request,
    )
    return RoleDetail.model_validate(_get_role_or_404(role.id, db))


@router.put("/{role_id}/permissions", response_model=RoleDetail)
def assign_role_permissions(
    role_id: UUID,
    payload: RolePermissionsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_roles()),
) -> RoleDetail:
    role = _get_role_or_404(role_id, db)
    permissions = db.scalars(
        select(Permission).where(Permission.id.in_(payload.permission_ids))
    ).all()

    if len(permissions) != len(set(payload.permission_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid permission selection",
        )

    ensure_not_privilege_escalation(
        actor,
        [],
        assigning_permissions=[(p.resource, p.action) for p in permissions],
    )

    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete(synchronize_session=False)
    for permission in permissions:
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    role.updated_at = datetime.now(UTC)
    db.commit()
    record_auth_event(
        "roles.permissions_assigned",
        db=db,
        actor=actor,
        target_id=role.id,
        request=request,
    )
    return RoleDetail.model_validate(_get_role_or_404(role.id, db))


@permissions_router.get("", response_model=PermissionListResponse)
def list_permissions(
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("roles", "view")),
) -> PermissionListResponse:
    permissions = get_all_permissions(db)
    return PermissionListResponse(
        items=[PermissionResponse.model_validate(permission) for permission in permissions],
        total=len(permissions),
    )
