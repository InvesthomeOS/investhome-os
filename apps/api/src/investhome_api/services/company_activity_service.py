"""Company workspace recent activity timeline."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.user_auth import User
from investhome_api.services.activity_service import ENTITY_LINK_MODULES, resolve_entity_label

COMPANY_ACTIVITY_ENTITY_TYPES = (
    ActivityEntityType.COMPANY,
    ActivityEntityType.BRANCH,
    ActivityEntityType.OFFICE,
    ActivityEntityType.DEPARTMENT,
    ActivityEntityType.TEAM,
    ActivityEntityType.BRAND,
    ActivityEntityType.USER,
    ActivityEntityType.DOCUMENT,
    ActivityEntityType.ROLE,
)


def list_recent_company_activity(
    db: Session,
    user: User,
    *,
    limit: int = 20,
) -> tuple[list[ActivityLog], int]:
    del user  # Permission enforced at route layer; entries are company-scoped audit events.
    base = select(ActivityLog).where(ActivityLog.entity_type.in_(COMPANY_ACTIVITY_ENTITY_TYPES))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(db.scalars(base.order_by(ActivityLog.created_at.desc()).limit(limit)).all())
    return items, total


def serialize_activity_entry(entry: ActivityLog) -> dict:
    metadata = entry.metadata_json or {}
    return {
        **{column.key: getattr(entry, column.key) for column in entry.__table__.columns},
        "entity_label": resolve_entity_label(metadata),
        "link_module": ENTITY_LINK_MODULES.get(entry.entity_type),
    }
