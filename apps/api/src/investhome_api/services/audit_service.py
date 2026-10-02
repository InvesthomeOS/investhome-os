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
        "user.invited": (ActivityAction.INVITED, "activity.user.invited"),
        "user.invite_resent": (ActivityAction.INVITED, "activity.user.invite_resent"),
        "user.invite_accepted": (ActivityAction.ACTIVATED, "activity.user.invite_accepted"),
        "user.activated": (ActivityAction.ACTIVATED, "activity.user.activated"),
        "user.deactivated": (ActivityAction.DEACTIVATED, "activity.user.deactivated"),
        "users.updated": (ActivityAction.UPDATED, "activity.user.updated"),
        "users.deactivated": (ActivityAction.DEACTIVATED, "activity.user.deactivated"),
        "users.roles_assigned": (ActivityAction.ROLE_ASSIGNED, "activity.user.role_assigned"),
        "roles.created": (ActivityAction.CREATED, "activity.role.created"),
        "roles.updated": (ActivityAction.UPDATED, "activity.role.updated"),
        "roles.permissions_assigned": (
            ActivityAction.PERMISSION_CHANGED,
            "activity.role.permission_changed",
        ),
        "security.session_terminated": (ActivityAction.OTHER, "activity.security.session_terminated"),
        "security.sessions_terminated": (ActivityAction.OTHER, "activity.security.sessions_terminated"),
        "security.api_key_created": (ActivityAction.CREATED, "activity.security.api_key_created"),
        "security.api_key_rotated": (ActivityAction.UPDATED, "activity.security.api_key_rotated"),
        "security.api_key_revoked": (ActivityAction.DELETED, "activity.security.api_key_revoked"),
        "security.temp_grant_created": (
            ActivityAction.PERMISSION_CHANGED,
            "activity.security.temp_grant_created",
        ),
        "security.temp_grant_revoked": (
            ActivityAction.PERMISSION_CHANGED,
            "activity.security.temp_grant_revoked",
        ),
        "security.feature_flag_updated": (ActivityAction.UPDATED, "activity.security.feature_flag_updated"),
        "security.incident_created": (ActivityAction.CREATED, "activity.security.incident_created"),
        "security.audit_exported": (ActivityAction.EXPORTED, "activity.security.audit_exported"),
        "security.force_logout": (ActivityAction.OTHER, "activity.security.force_logout"),
        "security.password_reset": (ActivityAction.PASSWORD_CHANGED, "activity.security.password_reset"),
        "security.user_suspended": (ActivityAction.DEACTIVATED, "activity.security.user_suspended"),
        "security.mfa_reset": (ActivityAction.OTHER, "activity.security.mfa_reset"),
        "platform.module_updated": (ActivityAction.UPDATED, "activity.platform.module_updated"),
        "platform.feature_flag_updated": (ActivityAction.UPDATED, "activity.platform.feature_flag_updated"),
        "platform.api_client_created": (ActivityAction.CREATED, "activity.platform.api_client_created"),
        "platform.webhook_enqueued": (ActivityAction.CREATED, "activity.platform.webhook_enqueued"),
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
    if event_type in {"security.mfa_reset", "security.session_terminated", "security.sessions_terminated", "security.force_logout"}:
        try:
            from investhome_api.services.login_rate_limit import resolve_client_ip
            from investhome_api.services.security_monitoring import SecurityEventKind, observe_security_event

            kind = (
                SecurityEventKind.ADMIN_MFA_RESET
                if event_type == "security.mfa_reset"
                else SecurityEventKind.SESSION_REVOKED
            )
            observe_security_event(
                kind,
                ip=resolve_client_ip(request) if request is not None else None,
                identity=str(actor.id) if actor is not None else None,
            )
        except Exception:
            pass
    _emit_notification_for_auth_event(
        event_type,
        db=db,
        actor=actor,
        target_id=target_id,
        metadata=metadata,
    )


def _emit_notification_for_auth_event(
    event_type: str,
    *,
    db: Session,
    actor: User | None,
    target_id: UUID | None,
    metadata: dict[str, object] | None,
) -> None:
    from investhome_api.services.notification_hooks import (
        notify_password_changed,
        notify_user_deactivated,
        notify_user_invited,
        notify_users_with_permission,
    )
    from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType

    actor_id = actor.id if actor is not None else None
    if event_type in {"users.created", "user.invited"} and target_id is not None:
        if event_type == "users.created":
            notify_user_invited(
                db,
                recipient_user_id=target_id,
                actor_user_id=actor_id,
                metadata=metadata,
            )
    elif event_type in {"users.deactivated", "user.deactivated"} and target_id is not None:
        notify_user_deactivated(db, recipient_user_id=target_id, actor_user_id=actor_id)
    elif event_type == "auth.password_changed" and actor is not None:
        notify_password_changed(db, recipient_user_id=actor.id)
    elif event_type == "roles.permissions_assigned" and target_id is not None:
        notify_users_with_permission(
            db,
            resource="roles",
            action="view",
            type=NotificationType.SYSTEM,
            priority=NotificationPriority.CRITICAL,
            title_key="notifications.activity.permission_changed.title",
            message_key="notifications.activity.permission_changed.message",
            rule_key="activity.permission_changed",
            related_entity_type="role",
            related_entity_id=target_id,
            metadata=metadata,
            source=NotificationSource.ACTIVITY,
            created_by=actor_id,
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
