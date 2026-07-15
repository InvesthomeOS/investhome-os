"""Centralized activity logging and query service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.config.activity_config import (
    ENTITY_RESOURCE_MAP,
    SECURITY_ENTITY_TYPES,
    SENSITIVE_FIELD_NAMES,
    SENSITIVE_PARTIAL_MATCH,
)
from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivityLog,
    ActivitySource,
)
from investhome_api.models.user_auth import User
from investhome_api.services.permission_service import is_super_admin, user_has_permission

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActivityRequestContext:
    source: ActivitySource = ActivitySource.WEB
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_serialize_value(item) for item in value]
    return value


def _is_sensitive_field(field_name: str) -> bool:
    normalized = field_name.lower()
    if normalized in SENSITIVE_FIELD_NAMES:
        return True
    return any(token in normalized for token in SENSITIVE_PARTIAL_MATCH)


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if _is_sensitive_field(key):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = _serialize_value(value)
    return sanitized


def compute_field_changes(
    before: dict[str, Any],
    after: dict[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    changed_fields: list[str] = []
    previous_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for field in sorted(set(before.keys()) | set(after.keys())):
        old_raw = before.get(field)
        new_raw = after.get(field)
        old_val = _serialize_value(old_raw)
        new_val = _serialize_value(new_raw)
        if old_val != new_val:
            changed_fields.append(field)
            if not _is_sensitive_field(field):
                previous_values[field] = old_val
                new_values[field] = new_val
            else:
                previous_values[field] = "[REDACTED]"
                new_values[field] = "[REDACTED]"

    return changed_fields, previous_values, new_values


def snapshot_entity(entity: Any, fields: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in fields:
        if hasattr(entity, field):
            data[field] = getattr(entity, field)
    return data


def build_event_type(entity_type: ActivityEntityType, action: ActivityAction) -> str:
    return f"{entity_type.value}.{action.value}"


def log_activity(
    db: Session,
    *,
    action: ActivityAction,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    description_key: str,
    actor_user: User | None = None,
    actor_type: ActivityActorType | None = None,
    actor_name: str | None = None,
    source: ActivitySource = ActivitySource.WEB,
    metadata: dict[str, Any] | None = None,
    changed_fields: list[str] | None = None,
    previous_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    request_context: ActivityRequestContext | None = None,
    is_demo: bool = False,
    created_at: datetime | None = None,
    commit: bool = False,
) -> ActivityLog | None:
    """Record activity after a successful business operation. Failures are logged, not raised."""
    resolved_actor_type = actor_type or (
        ActivityActorType.USER if actor_user is not None else ActivityActorType.SYSTEM
    )
    resolved_actor_name = actor_name or (actor_user.full_name if actor_user is not None else None)
    ctx = request_context or ActivityRequestContext()

    try:
        entry = ActivityLog(
            event_type=build_event_type(entity_type, action),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=resolved_actor_type,
            actor_user_id=actor_user.id if actor_user is not None else None,
            actor_name=resolved_actor_name,
            source=ctx.source if request_context else source,
            description_key=description_key,
            metadata_json=sanitize_payload(metadata),
            changed_fields=changed_fields,
            previous_values=sanitize_payload(previous_values),
            new_values=sanitize_payload(new_values),
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
            is_demo=is_demo,
        )
        if created_at is not None:
            entry.created_at = created_at
        db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry
    except Exception:
        logger.exception(
            "Failed to record activity for %s/%s action=%s",
            entity_type.value,
            entity_id,
            action.value,
        )
        return None


def user_can_view_entity_type_events(user: User, entity_type: ActivityEntityType) -> bool:
    if is_super_admin(user):
        return True
    if entity_type in SECURITY_ENTITY_TYPES:
        return user_has_permission(user, "users", "view") or user_has_permission(user, "roles", "view")
    resource = ENTITY_RESOURCE_MAP.get(entity_type)
    if resource is None:
        return False
    return user_has_permission(user, resource, "view")


def user_can_view_entity_activity(user: User, entity_type: ActivityEntityType) -> bool:
    if is_super_admin(user):
        return True
    if not user_has_permission(user, "activity", "view"):
        return False
    return user_can_view_entity_type_events(user, entity_type)


def user_can_view_activity_entry(user: User, entry: ActivityLog, db: Session | None = None) -> bool:
    if not user_can_view_entity_activity(user, entry.entity_type):
        return False
    if entry.entity_type == ActivityEntityType.DOCUMENT:
        if db is None:
            return False
        from investhome_api.models.document import Document
        from investhome_api.services.document_service import user_can_view_document

        document = db.get(Document, entry.entity_id)
        if document is None:
            return False
        return user_can_view_document(user, document)
    return True


def list_activities(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    entity_type: ActivityEntityType | None = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    action: ActivityAction | None = None,
    source: ActivitySource | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ActivityLog], int]:
    query = select(ActivityLog)

    if entity_type is not None:
        query = query.where(ActivityLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(ActivityLog.entity_id == entity_id)
    if actor_user_id is not None:
        query = query.where(ActivityLog.actor_user_id == actor_user_id)
    if action is not None:
        query = query.where(ActivityLog.action == action)
    if source is not None:
        query = query.where(ActivityLog.source == source)
    if date_from is not None:
        query = query.where(ActivityLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(ActivityLog.created_at <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ActivityLog.actor_name.ilike(pattern),
                ActivityLog.description_key.ilike(pattern),
            )
        )

    allowed_types = [
        entity
        for entity in ActivityEntityType
        if user_can_view_entity_activity(user, entity)
    ]
    if not allowed_types:
        return [], 0
    query = query.where(ActivityLog.entity_type.in_(allowed_types))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order_fn = desc if sort_order == "desc" else asc
    offset = (page - 1) * page_size
    items = list(
        db.scalars(query.order_by(order_fn(ActivityLog.created_at)).offset(offset).limit(page_size)).all()
    )
    return items, total


def get_activity_entry(db: Session, user: User, activity_id: UUID) -> ActivityLog | None:
    entry = db.get(ActivityLog, activity_id)
    if entry is None:
        return None
    if not user_can_view_activity_entry(user, entry, db):
        return None
    return entry


def list_entity_activity(
    db: Session,
    user: User,
    *,
    entity_type: ActivityEntityType,
    entity_id: UUID,
    limit: int = 20,
) -> list[ActivityLog]:
    if not user_can_view_entity_type_events(user, entity_type):
        return []
    if entity_type == ActivityEntityType.DOCUMENT:
        from investhome_api.models.document import Document
        from investhome_api.services.document_service import user_can_view_document

        document = db.get(Document, entity_id)
        if document is None or not user_can_view_document(user, document):
            return []
    return list(
        db.scalars(
            select(ActivityLog)
            .where(
                ActivityLog.entity_type == entity_type,
                ActivityLog.entity_id == entity_id,
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
        ).all()
    )


def list_recent_activity(
    db: Session,
    user: User | None = None,
    *,
    limit: int = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[ActivityLog]:
    query = select(ActivityLog)
    if date_from is not None:
        query = query.where(ActivityLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(ActivityLog.created_at <= date_to)
    query = query.order_by(desc(ActivityLog.created_at)).limit(limit)
    entries = list(db.scalars(query).all())
    if user is None:
        return entries
    return [entry for entry in entries if user_can_view_activity_entry(user, entry, db)]


def pagination_meta(total: int, page: int, page_size: int) -> dict[str, int]:
    pages = ceil(total / page_size) if total else 0
    return {"total": total, "page": page, "page_size": page_size, "pages": pages}


ENTITY_LINK_MODULES: dict[ActivityEntityType, str] = {
    ActivityEntityType.LEAD: "leads",
    ActivityEntityType.INVESTOR: "investors",
    ActivityEntityType.PROJECT: "projects",
    ActivityEntityType.TRANSACTION: "finance",
    ActivityEntityType.FINANCIAL_ACCOUNT: "finance",
    ActivityEntityType.PROJECT_BUDGET: "finance",
    ActivityEntityType.FUNDING_COMMITMENT: "finance",
    ActivityEntityType.PAYMENT_OBLIGATION: "finance",
    ActivityEntityType.USER: "admin/users",
    ActivityEntityType.ROLE: "admin/roles",
    ActivityEntityType.DOCUMENT: "documents",
}


def resolve_entity_label(metadata: dict[str, object] | None) -> str | None:
    if not metadata:
        return None
    for key in ("title", "name", "full_name", "project_name", "description", "email"):
        value = metadata.get(key)
        if value:
            return str(value)
    return None
