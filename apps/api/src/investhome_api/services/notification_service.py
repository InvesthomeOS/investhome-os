"""Centralized notification service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.config.notification_config import ENTITY_RESOURCE_MAP, SECURITY_ENTITY_TYPES
from investhome_api.models.notification import (
    Notification,
    NotificationPriority,
    NotificationSource,
    NotificationStatus,
    NotificationType,
)
from investhome_api.models.user_auth import User
from investhome_api.services.permission_service import is_super_admin, user_has_permission

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {
    NotificationPriority.CRITICAL: 0,
    NotificationPriority.HIGH: 1,
    NotificationPriority.MEDIUM: 2,
    NotificationPriority.LOW: 3,
    NotificationPriority.INFO: 4,
}

ENTITY_LINK_MODULES: dict[str, str] = {
    "lead": "leads",
    "investor": "investors",
    "project": "projects",
    "transaction": "finance",
    "financial_account": "finance",
    "project_budget": "finance",
    "funding_commitment": "finance",
    "payment_obligation": "finance",
    "inventory_reservation": "inventory",
    "user": "admin/users",
    "role": "admin/roles",
}


@dataclass(frozen=True)
class NotificationCandidate:
    rule_key: str
    type: NotificationType
    priority: NotificationPriority
    title_key: str
    message_key: str
    metadata: dict[str, Any]
    related_entity_type: str
    related_entity_id: UUID
    source: NotificationSource = NotificationSource.AUTOMATION
    created_by: UUID | None = None
    expires_at: datetime | None = None
    is_demo: bool = False
    link_module: str | None = None
    link_query: dict[str, str] | None = None
    related_label: str | None = None


def _dedupe_key(rule_key: str, entity_type: str, entity_id: UUID) -> str:
    return f"{rule_key}:{entity_type}:{entity_id}"


def user_can_view_notification(user: User, notification: Notification) -> bool:
    if notification.recipient_user_id != user.id and not is_super_admin(user):
        return False
    if is_super_admin(user):
        return True
    if not notification.related_entity_type:
        return True
    entity_type = notification.related_entity_type
    if entity_type in SECURITY_ENTITY_TYPES:
        return user_has_permission(user, "users", "view") or user_has_permission(user, "roles", "view")
    resource = ENTITY_RESOURCE_MAP.get(entity_type)
    if resource is None:
        return False
    return user_has_permission(user, resource, "view")


def create_notification(
    db: Session,
    *,
    recipient_user_id: UUID,
    type: NotificationType,
    priority: NotificationPriority,
    title_key: str,
    message_key: str,
    rule_key: str,
    related_entity_type: str,
    related_entity_id: UUID,
    metadata: dict[str, Any] | None = None,
    source: NotificationSource = NotificationSource.AUTOMATION,
    created_by: UUID | None = None,
    expires_at: datetime | None = None,
    is_demo: bool = False,
    commit: bool = False,
) -> Notification | None:
    """Create or refresh a notification idempotently. Failures are logged, not raised."""
    dedupe = _dedupe_key(rule_key, related_entity_type, related_entity_id)
    enriched = dict(metadata or {})
    try:
        existing = db.scalar(
            select(Notification).where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.dedupe_key == dedupe,
            )
        )
        if existing is not None:
            if existing.status == NotificationStatus.DISMISSED:
                return existing
            existing.priority = priority
            existing.title_key = title_key
            existing.message_key = message_key
            existing.metadata_json = enriched
            existing.expires_at = expires_at
            if commit:
                db.commit()
                db.refresh(existing)
            else:
                db.flush()
            return existing

        notification = Notification(
            type=type,
            priority=priority,
            title_key=title_key,
            message_key=message_key,
            metadata_json=enriched,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            recipient_user_id=recipient_user_id,
            created_by=created_by,
            source=source,
            status=NotificationStatus.UNREAD,
            dedupe_key=dedupe,
            expires_at=expires_at,
            is_demo=is_demo,
        )
        db.add(notification)
        if commit:
            db.commit()
            db.refresh(notification)
        else:
            db.flush()
        return notification
    except Exception:
        logger.exception(
            "Failed to create notification rule=%s entity=%s/%s",
            rule_key,
            related_entity_type,
            related_entity_id,
        )
        return None


def upsert_candidate(
    db: Session,
    user_id: UUID,
    candidate: NotificationCandidate,
) -> Notification | None:
    metadata = dict(candidate.metadata)
    if candidate.link_module:
        metadata["link_module"] = candidate.link_module
    if candidate.link_query:
        metadata["link_query"] = candidate.link_query
    if candidate.related_label:
        metadata["related_label"] = candidate.related_label
    return create_notification(
        db,
        recipient_user_id=user_id,
        type=candidate.type,
        priority=candidate.priority,
        title_key=candidate.title_key,
        message_key=candidate.message_key,
        rule_key=candidate.rule_key,
        related_entity_type=candidate.related_entity_type,
        related_entity_id=candidate.related_entity_id,
        metadata=metadata,
        source=candidate.source,
        created_by=candidate.created_by,
        expires_at=candidate.expires_at,
        is_demo=candidate.is_demo,
    )


def dismiss_stale_automation(
    db: Session,
    user_id: UUID,
    active_dedupe_keys: set[str],
) -> int:
    """Dismiss automation notifications whose conditions no longer apply."""
    now = datetime.now(UTC)
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == user_id,
                Notification.source == NotificationSource.AUTOMATION,
                Notification.status != NotificationStatus.DISMISSED,
            )
        ).all()
    )
    count = 0
    for notification in notifications:
        if notification.dedupe_key not in active_dedupe_keys:
            notification.status = NotificationStatus.DISMISSED
            notification.dismissed_at = now
            count += 1
    return count


def enrich_notification(notification: Notification) -> dict[str, Any]:
    from investhome_api.schemas.notification import NotificationResponse

    metadata = notification.metadata_json or {}
    link_module = metadata.get("link_module") or ENTITY_LINK_MODULES.get(
        notification.related_entity_type or ""
    )
    link_query = metadata.get("link_query")
    related_label = metadata.get("related_label")
    base = NotificationResponse.model_validate(notification).model_dump()
    base["link_module"] = str(link_module) if link_module else None
    base["link_query"] = link_query if isinstance(link_query, dict) else None
    base["related_label"] = str(related_label) if related_label else None
    return base


def list_notifications(
    db: Session,
    user: User,
    *,
    status: NotificationStatus | None = None,
    priority: NotificationPriority | None = None,
    page: int = 1,
    page_size: int = 25,
    include_dismissed: bool = False,
) -> tuple[list[Notification], int, int]:
    query = select(Notification).where(Notification.recipient_user_id == user.id)

    if status is not None:
        query = query.where(Notification.status == status)
    elif not include_dismissed:
        query = query.where(Notification.status != NotificationStatus.DISMISSED)

    if priority is not None:
        query = query.where(Notification.priority == priority)

    if not is_super_admin(user):
        allowed_types = [
            entity
            for entity, resource in ENTITY_RESOURCE_MAP.items()
            if user_has_permission(user, resource, "view")
        ]
        security_ok = user_has_permission(user, "users", "view") or user_has_permission(
            user, "roles", "view"
        )
        conditions = [Notification.related_entity_type.is_(None)]
        if allowed_types:
            conditions.append(Notification.related_entity_type.in_(allowed_types))
        if security_ok:
            conditions.append(Notification.related_entity_type.in_(SECURITY_ENTITY_TYPES))
        query = query.where(or_(*conditions))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.recipient_user_id == user.id,
            Notification.status == NotificationStatus.UNREAD,
        )
    ) or 0

    offset = (page - 1) * page_size
    items = list(
        db.scalars(
            query.order_by(desc(Notification.created_at)).offset(offset).limit(page_size)
        ).all()
    )
    items = [item for item in items if user_can_view_notification(user, item)]
    return items, total, unread


def get_unread_count(db: Session, user: User) -> tuple[int, NotificationPriority | None]:
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == user.id,
                Notification.status == NotificationStatus.UNREAD,
            )
        ).all()
    )
    visible = [n for n in notifications if user_can_view_notification(user, n)]
    if not visible:
        return 0, None
    highest = min(visible, key=lambda n: PRIORITY_ORDER[n.priority]).priority
    return len(visible), highest


def get_notification_summary(db: Session, user: User) -> dict[str, int]:
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == user.id,
                Notification.status == NotificationStatus.UNREAD,
            )
        ).all()
    )
    visible = [n for n in notifications if user_can_view_notification(user, n)]
    return {
        "critical": sum(1 for n in visible if n.priority == NotificationPriority.CRITICAL),
        "high": sum(1 for n in visible if n.priority == NotificationPriority.HIGH),
        "medium": sum(1 for n in visible if n.priority == NotificationPriority.MEDIUM),
        "unread": len(visible),
    }


def get_notification(db: Session, user: User, notification_id: UUID) -> Notification | None:
    notification = db.get(Notification, notification_id)
    if notification is None:
        return None
    if not user_can_view_notification(user, notification):
        return None
    return notification


def mark_read(db: Session, user: User, notification_id: UUID) -> Notification | None:
    notification = get_notification(db, user, notification_id)
    if notification is None:
        return None
    if notification.status == NotificationStatus.UNREAD:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(UTC)
    db.flush()
    return notification


def mark_all_read(db: Session, user: User) -> int:
    now = datetime.now(UTC)
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == user.id,
                Notification.status == NotificationStatus.UNREAD,
            )
        ).all()
    )
    count = 0
    for notification in notifications:
        if user_can_view_notification(user, notification):
            notification.status = NotificationStatus.READ
            notification.read_at = now
            count += 1
    db.flush()
    return count


def dismiss_notification(db: Session, user: User, notification_id: UUID) -> Notification | None:
    notification = get_notification(db, user, notification_id)
    if notification is None:
        return None
    notification.status = NotificationStatus.DISMISSED
    notification.dismissed_at = datetime.now(UTC)
    db.flush()
    return notification


def pagination_meta(total: int, page: int, page_size: int) -> dict[str, int]:
    pages = ceil(total / page_size) if total else 0
    return {"total": total, "page": page, "page_size": page_size, "pages": pages}
