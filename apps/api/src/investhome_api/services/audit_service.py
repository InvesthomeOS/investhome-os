"""Audit event bridge to centralized activity logging."""

from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import log_security_event

SYSTEM_ENTITY_ID = UUID("00000000-0000-0000-0000-000000000000")


def record_auth_event(
    event_type: str,
    *,
    db: Session | None = None,
    actor_id: UUID | None = None,
    actor: User | None = None,
    target_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
    request: Request | None = None,
    commit: bool = False,
) -> None:
    if db is None:
        return

    action_map = {
        "auth.login": (ActivityAction.LOGIN, "activity.user.login"),
        "auth.logout": (ActivityAction.LOGOUT, "activity.user.logout"),
        "auth.password_changed": (ActivityAction.PASSWORD_CHANGED, "activity.user.password_changed"),
        "users.created": (ActivityAction.INVITED, "activity.user.invited"),
        "users.updated": (ActivityAction.UPDATED, "activity.user.updated"),
        "users.deactivated": (ActivityAction.DEACTIVATED, "activity.user.deactivated"),
        "users.roles_assigned": (ActivityAction.ROLE_ASSIGNED, "activity.user.role_assigned"),
        "roles.created": (ActivityAction.CREATED, "activity.role.created"),
        "roles.updated": (ActivityAction.UPDATED, "activity.role.updated"),
        "roles.permissions_assigned": (
            ActivityAction.PERMISSION_CHANGED,
            "activity.role.permission_changed",
        ),
    }
    mapped = action_map.get(event_type)
    if mapped is None:
        return

    action, description_key = mapped
    entity_id = target_id or actor_id or SYSTEM_ENTITY_ID
    entity_type = (
        ActivityEntityType.ROLE
        if event_type.startswith("roles.")
        else ActivityEntityType.USER
    )

    log_security_event(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=description_key,
        actor=actor,
        metadata=metadata,
        request=request,
        commit=commit,
    )


def record_login_failed(
    db: Session,
    *,
    email: str,
    user: User | None = None,
    request: Request | None = None,
) -> None:
    log_security_event(
        db,
        action=ActivityAction.LOGIN_FAILED,
        entity_type=ActivityEntityType.USER,
        entity_id=user.id if user is not None else SYSTEM_ENTITY_ID,
        description_key="activity.user.login_failed",
        actor_name=email,
        actor_type=ActivityActorType.SYSTEM if user is None else ActivityActorType.USER,
        metadata={"email": email},
        request=request,
        commit=True,
    )
