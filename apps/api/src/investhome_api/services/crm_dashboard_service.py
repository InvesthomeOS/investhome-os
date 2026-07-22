"""CRM workspace dashboard aggregation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import ACTIVE_WORK_ITEM_STATUSES, WorkItem, WorkItemType
from investhome_api.schemas.crm import (
    CrmActivitySummary,
    CrmCommunicationSummary,
    CrmDashboardResponse,
    CrmMeetingSummary,
    CrmPinnedCompanySummary,
    CrmRelationshipAlert,
    CrmTaskSummary,
)
from investhome_api.services.activity_service import list_activities
from investhome_api.services.crm_contact_service import (
    count_active_contacts,
    count_contacts_with_email,
    count_contacts_with_phone,
    count_favorite_contacts,
    fetch_favorite_contacts,
    fetch_pinned_companies,
    fetch_recent_contacts,
    fetch_recently_updated_contacts,
)

CRM_ACTIVITY_ENTITY_TYPES = (
    ActivityEntityType.CRM_CONTACT,
    ActivityEntityType.LEAD,
    ActivityEntityType.INVESTOR,
)


def _serialize_activity(entry) -> CrmActivitySummary:
    return CrmActivitySummary(
        id=entry.id,
        action=entry.action.value,
        entity_type=entry.entity_type.value,
        entity_id=entry.entity_id,
        description_key=entry.description_key,
        actor_name=entry.actor_name,
        created_at=entry.created_at,
    )


def _fetch_upcoming_tasks(db: Session, *, limit: int = 10) -> list[CrmTaskSummary]:
    now = datetime.now(tz=UTC)
    rows = db.scalars(
        select(WorkItem)
        .where(
            WorkItem.archived_at.is_(None),
            WorkItem.status.in_(ACTIVE_WORK_ITEM_STATUSES),
            WorkItem.due_at.is_not(None),
            WorkItem.due_at >= now,
        )
        .order_by(WorkItem.due_at.asc())
        .limit(limit)
    ).all()
    return [
        CrmTaskSummary(
            id=item.id,
            title=item.title,
            status=item.status.value,
            due_at=item.due_at,
            priority=item.priority.value,
        )
        for item in rows
    ]


def _fetch_todays_meetings(db: Session, *, limit: int = 10) -> list[CrmMeetingSummary]:
    """Meetings integration hook — work items typed as meetings due today."""
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    rows = db.scalars(
        select(WorkItem)
        .where(
            WorkItem.archived_at.is_(None),
            WorkItem.work_item_type == WorkItemType.MEETING,
            WorkItem.start_at.is_not(None),
            WorkItem.start_at >= today_start,
            WorkItem.start_at < today_end,
        )
        .order_by(WorkItem.start_at.asc())
        .limit(limit)
    ).all()
    return [
        CrmMeetingSummary(
            id=item.id,
            title=item.title,
            start_at=item.start_at,
            status=item.status.value,
        )
        for item in rows
    ]


def _build_relationship_alerts(db: Session, *, limit: int = 10) -> list[CrmRelationshipAlert]:
    stale_cutoff = datetime.now(tz=UTC) - timedelta(days=90)
    rows = db.scalars(
        select(CrmContact)
        .where(
            CrmContact.archived_at.is_(None),
            CrmContact.status == CrmContactStatus.ACTIVE,
            CrmContact.updated_at < stale_cutoff,
        )
        .order_by(CrmContact.updated_at.asc())
        .limit(limit)
    ).all()
    return [
        CrmRelationshipAlert(
            contact_id=contact.id,
            display_name=contact.display_name,
            alert_type="stale_relationship",
            message_key="crm.alerts.staleRelationship",
            severity="warning",
        )
        for contact in rows
    ]


def build_crm_dashboard(db: Session, user: User) -> CrmDashboardResponse:
    recent_activities: list[CrmActivitySummary] = []
    for entity_type in CRM_ACTIVITY_ENTITY_TYPES:
        entries, _ = list_activities(
            db,
            user,
            entity_type=entity_type,
            page=1,
            page_size=5,
        )
        recent_activities.extend(_serialize_activity(entry) for entry in entries)
    recent_activities.sort(key=lambda item: item.created_at, reverse=True)
    recent_activities = recent_activities[:10]

    pinned = [
        CrmPinnedCompanySummary(
            contact_id=contact.id,
            display_name=contact.display_name,
            organization_name=contact.organization_name,
            contact_type=contact.contact_type,
        )
        for contact in fetch_pinned_companies(db, limit=10)
    ]

    return CrmDashboardResponse(
        recent_contacts=fetch_recent_contacts(db, limit=10),
        recent_activities=recent_activities,
        upcoming_tasks=_fetch_upcoming_tasks(db, limit=10),
        todays_meetings=_fetch_todays_meetings(db, limit=10),
        recently_updated=fetch_recently_updated_contacts(db, limit=10),
        relationship_alerts=_build_relationship_alerts(db, limit=10),
        favorite_contacts=fetch_favorite_contacts(db, limit=10),
        pinned_companies=pinned,
        communication_summary=CrmCommunicationSummary(
            total_contacts=count_active_contacts(db),
            contacts_with_email=count_contacts_with_email(db),
            contacts_with_phone=count_contacts_with_phone(db),
            favorites_count=count_favorite_contacts(db),
            recent_interactions_count=len(recent_activities),
        ),
    )
