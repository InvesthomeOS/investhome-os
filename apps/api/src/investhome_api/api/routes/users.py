"""User management routes."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.api.deps.auth import require_manage_users, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.schemas.auth import (
    InviteDeliveryResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRolesUpdate,
    UserUpdate,
)
from investhome_api.services.audit_service import record_auth_event
from investhome_api.services import session_service
from investhome_api.services.permission_service import (
    ensure_not_privilege_escalation,
    load_user_with_roles,
)
from investhome_api.services.user_invitation import (
    InvitationError,
    active_invitation_for_user,
    invalidate_outstanding_invitations,
    issue_invitation,
    unguessable_password_hash,
)
from investhome_api.services.user_service import serialize_user

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_or_404(user_id: UUID, db: Session) -> User:
    user = load_user_with_roles(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("", response_model=UserListResponse)
def list_users(
    search: str | None = Query(default=None, max_length=255),
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("users", "view")),
) -> UserListResponse:
    query = select(User).options(selectinload(User.roles))

    if not include_archived:
        query = query.where(User.archived_at.is_(None))

    if status_filter is not None:
        query = query.where(User.status == status_filter)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.job_title.ilike(pattern),
                User.department.ilike(pattern),
            )
        )

    query = query.order_by(User.full_name.asc())
    users = db.scalars(query).unique().all()
    return UserListResponse(
        items=[serialize_user(user) for user in users],
        total=len(users),
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("users", "view")),
) -> UserResponse:
    return serialize_user(_get_user_or_404(user_id, db))


@router.post("", response_model=InviteDeliveryResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> InviteDeliveryResponse:
    email = payload.email.lower()
    existing = db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    roles = db.scalars(select(Role).where(Role.id.in_(payload.role_ids))).all()
    if len(roles) != len(set(payload.role_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role selection")

    ensure_not_privilege_escalation(actor, [role.code for role in roles])

    user = User(
        full_name=payload.full_name,
        email=email,
        phone=payload.phone,
        job_title=payload.job_title,
        department=payload.department,
        status=UserStatus.INVITED,
        preferred_language=payload.preferred_language,
        timezone=payload.timezone,
        avatar_url=payload.avatar_url,
        hashed_password=unguessable_password_hash(),
    )
    db.add(user)
    db.flush()

    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    issued = issue_invitation(db, user=user, invited_by_user_id=actor.id)
    record_auth_event(
        "users.created",
        db=db,
        actor=actor,
        target_id=user.id,
        metadata={"email": user.email, "delivery_status": issued.delivery_status},
        request=request,
    )
    record_auth_event(
        "user.invited",
        db=db,
        actor=actor,
        target_id=user.id,
        metadata={"delivery_status": issued.delivery_status},
        request=request,
    )
    db.commit()
    return InviteDeliveryResponse(
        user=serialize_user(_get_user_or_404(user.id, db)),
        delivery_status=issued.delivery_status,
    )


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> UserResponse:
    user = _get_user_or_404(user_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    if "email" in updates:
        email = str(updates["email"]).lower()
        conflict = db.scalar(select(User.id).where(User.email == email, User.id != user.id))
        if conflict is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        updates["email"] = email

    if "status" in updates and updates["status"] in {UserStatus.INACTIVE, UserStatus.SUSPENDED}:
        if actor.id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )
        session_service.revoke_user_sessions(db, user.id, reason="status_changed")
        invalidate_outstanding_invitations(db, user.id)

    for field, value in updates.items():
        setattr(user, field, value)

    user.updated_at = datetime.now(UTC)
    db.commit()
    record_auth_event(
        "users.updated",
        db=db,
        actor=actor,
        target_id=user.id,
        request=request,
    )
    return serialize_user(_get_user_or_404(user.id, db))


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> UserResponse:
    user = _get_user_or_404(user_id, db)

    if actor.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.status = UserStatus.INACTIVE
    user.updated_at = datetime.now(UTC)
    session_service.revoke_user_sessions(db, user.id, reason="deactivated")
    invalidate_outstanding_invitations(db, user.id)
    record_auth_event(
        "user.deactivated",
        db=db,
        actor=actor,
        target_id=user.id,
        request=request,
    )
    db.commit()
    return serialize_user(_get_user_or_404(user.id, db))


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> UserResponse:
    user = _get_user_or_404(user_id, db)
    if user.status == UserStatus.INVITED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invited users must accept their invitation",
        )
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspended users cannot be activated from this action",
        )
    user.status = UserStatus.ACTIVE
    user.updated_at = datetime.now(UTC)
    record_auth_event(
        "user.activated",
        db=db,
        actor=actor,
        target_id=user.id,
        request=request,
    )
    db.commit()
    return serialize_user(_get_user_or_404(user.id, db))


def _invite_user(
    *,
    user_id: UUID,
    request: Request,
    db: Session,
    actor: User,
    resend: bool,
) -> InviteDeliveryResponse:
    user = _get_user_or_404(user_id, db)
    if user.status != UserStatus.INVITED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not awaiting invitation",
        )
    active = active_invitation_for_user(db, user.id)
    if active is not None and not resend:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active invitation already exists",
        )
    try:
        issued = issue_invitation(
            db,
            user=user,
            invited_by_user_id=actor.id,
            invalidate_existing=True,
        )
    except InvitationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    event = "user.invite_resent" if resend else "user.invited"
    record_auth_event(
        event,
        db=db,
        actor=actor,
        target_id=user.id,
        metadata={"delivery_status": issued.delivery_status},
        request=request,
    )
    db.commit()
    return InviteDeliveryResponse(
        user=serialize_user(_get_user_or_404(user.id, db)),
        delivery_status=issued.delivery_status,
    )


@router.post("/{user_id}/invite", response_model=InviteDeliveryResponse)
def invite_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> InviteDeliveryResponse:
    return _invite_user(user_id=user_id, request=request, db=db, actor=actor, resend=False)


@router.post("/{user_id}/invite/resend", response_model=InviteDeliveryResponse)
def resend_user_invite(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> InviteDeliveryResponse:
    return _invite_user(user_id=user_id, request=request, db=db, actor=actor, resend=True)


@router.put("/{user_id}/roles", response_model=UserResponse)
def assign_user_roles(
    user_id: UUID,
    payload: UserRolesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users()),
) -> UserResponse:
    user = _get_user_or_404(user_id, db)
    roles = db.scalars(select(Role).where(Role.id.in_(payload.role_ids))).all()

    if len(roles) != len(set(payload.role_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role selection")

    ensure_not_privilege_escalation(actor, [role.code for role in roles])

    db.query(UserRole).filter(UserRole.user_id == user.id).delete(synchronize_session=False)
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    user.updated_at = datetime.now(UTC)
    db.commit()
    record_auth_event(
        "users.roles_assigned",
        db=db,
        actor=actor,
        target_id=user.id,
        metadata={"role_ids": [str(role.id) for role in roles]},
        request=request,
    )
    return serialize_user(_get_user_or_404(user.id, db))
