"""Lead qualification business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.lead_qualification import (
    FollowUpStatus,
    LeadFollowUp,
    LeadInventoryInterest,
    LeadQualification,
    LeadTimeline,
    QualificationStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.leads.config import (
    QUALIFICATION_ACTIVITY_FIELDS,
    QUALIFICATION_STATUS_TRANSITIONS,
)
from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.services.notification_hooks import notify_users_with_permission


class QualificationError(ValueError):
    def __init__(self, error_key: str, *, status_code: int = 422) -> None:
        self.error_key = error_key
        self.status_code = status_code
        super().__init__(error_key)


def _now() -> datetime:
    return datetime.now(UTC)


def _get_lead_or_raise(db: Session, lead_id: UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None:
        raise QualificationError("leads.errors.not_found", status_code=404)
    return lead


def _append_timeline(
    db: Session,
    lead_id: UUID,
    *,
    event_type: str,
    actor: User | None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LeadTimeline:
    entry = LeadTimeline(
        lead_id=lead_id,
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        notes=notes,
        metadata_json=metadata,
    )
    db.add(entry)
    db.flush()
    return entry


def get_or_create_qualification(db: Session, lead_id: UUID) -> LeadQualification:
    _get_lead_or_raise(db, lead_id)
    existing = db.scalar(select(LeadQualification).where(LeadQualification.lead_id == lead_id))
    if existing:
        return existing
    qual = LeadQualification(lead_id=lead_id)
    db.add(qual)
    db.flush()
    return qual


def get_qualification(db: Session, lead_id: UUID) -> LeadQualification | None:
    _get_lead_or_raise(db, lead_id)
    return db.scalar(select(LeadQualification).where(LeadQualification.lead_id == lead_id))


def update_qualification(
    db: Session,
    lead_id: UUID,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> LeadQualification:
    lead = _get_lead_or_raise(db, lead_id)
    qual = get_or_create_qualification(db, lead_id)
    before = snapshot_entity(qual, QUALIFICATION_ACTIVITY_FIELDS)

    for field, value in data.items():
        if field in QUALIFICATION_ACTIVITY_FIELDS and hasattr(qual, field):
            setattr(qual, field, value)

    qual.updated_at = _now()
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.LEAD_QUALIFICATION,
        entity_id=qual.id,
        description_key="activity.lead_qualification.updated",
        actor=actor,
        before=before,
        after=snapshot_entity(qual, QUALIFICATION_ACTIVITY_FIELDS),
        metadata={"lead_id": str(lead_id), "lead_name": lead.full_name},
        request=request,
        is_demo=lead.is_demo,
    )
    _append_timeline(
        db,
        lead_id,
        event_type="sales.lead.qualification_updated",
        actor=actor,
        metadata={"qualification_id": str(qual.id)},
    )
    return qual


def change_qualification_status(
    db: Session,
    lead_id: UUID,
    new_status: QualificationStatus,
    *,
    actor: User,
    notes: str | None = None,
    request: Request | None = None,
) -> LeadQualification:
    lead = _get_lead_or_raise(db, lead_id)
    qual = get_or_create_qualification(db, lead_id)
    current = qual.qualification_status.value
    allowed = QUALIFICATION_STATUS_TRANSITIONS.get(current, set())
    if new_status.value not in allowed and current != new_status.value:
        raise QualificationError("leads.errors.invalid_qualification_transition")

    if new_status == QualificationStatus.QUALIFIED:
        qual.qualified_at = _now()
        qual.qualified_by_id = actor.id
        if lead.status in (LeadStatus.NEW, LeadStatus.CONTACTED):
            lead.status = LeadStatus.QUALIFIED
            lead.updated_at = _now()
    elif new_status == QualificationStatus.UNQUALIFIED:
        qual.qualified_at = None
        qual.qualified_by_id = actor.id

    before_status = qual.qualification_status
    qual.qualification_status = new_status
    qual.updated_at = _now()
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.LEAD_QUALIFICATION,
        entity_id=qual.id,
        description_key="activity.lead_qualification.status_changed",
        actor=actor,
        before={"qualification_status": before_status.value},
        after={"qualification_status": new_status.value},
        metadata={"lead_id": str(lead_id), "lead_name": lead.full_name},
        request=request,
        is_demo=lead.is_demo,
    )

    event_type = "sales.lead.qualified" if new_status == QualificationStatus.QUALIFIED else "sales.lead.qualification_updated"
    _append_timeline(
        db,
        lead_id,
        event_type=event_type,
        actor=actor,
        notes=notes,
        metadata={"from_status": current, "to_status": new_status.value},
    )

    if new_status == QualificationStatus.QUALIFIED:
        notify_users_with_permission(
            db,
            resource="sales",
            action="view_lead",
            type=NotificationType.APPROVAL,
            priority=NotificationPriority.MEDIUM,
            title_key="notifications.lead.qualified.title",
            message_key="notifications.lead.qualified.message",
            rule_key="lead.qualified",
            related_entity_type="lead",
            related_entity_id=lead_id,
            metadata={"lead_name": lead.full_name},
            created_by=actor.id,
        )
    return qual


def list_inventory_interests(db: Session, lead_id: UUID) -> list[LeadInventoryInterest]:
    _get_lead_or_raise(db, lead_id)
    return list(
        db.scalars(
            select(LeadInventoryInterest)
            .where(LeadInventoryInterest.lead_id == lead_id)
            .order_by(LeadInventoryInterest.created_at.desc())
        ).all()
    )


def add_inventory_interest(
    db: Session,
    lead_id: UUID,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> LeadInventoryInterest:
    lead = _get_lead_or_raise(db, lead_id)
    interest = LeadInventoryInterest(lead_id=lead_id, **data)
    db.add(interest)
    db.flush()

    log_entity_created(
        db,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead_id,
        description_key="activity.lead.inventory_linked",
        actor=actor,
        metadata={"interest_type": interest.interest_type.value, "asset_id": str(interest.inventory_asset_id)},
        request=request,
        is_demo=lead.is_demo,
    )
    _append_timeline(
        db,
        lead_id,
        event_type="sales.lead.inventory_matched",
        actor=actor,
        metadata={"interest_id": str(interest.id), "asset_id": str(interest.inventory_asset_id)},
    )
    return interest


def remove_inventory_interest(db: Session, lead_id: UUID, interest_id: UUID) -> None:
    _get_lead_or_raise(db, lead_id)
    interest = db.get(LeadInventoryInterest, interest_id)
    if interest is None or interest.lead_id != lead_id:
        raise QualificationError("leads.errors.interest_not_found", status_code=404)
    db.delete(interest)
    db.flush()


def list_follow_ups(db: Session, lead_id: UUID) -> list[LeadFollowUp]:
    _get_lead_or_raise(db, lead_id)
    return list(
        db.scalars(
            select(LeadFollowUp)
            .where(LeadFollowUp.lead_id == lead_id)
            .order_by(LeadFollowUp.due_at.asc())
        ).all()
    )


def create_follow_up(
    db: Session,
    lead_id: UUID,
    data: dict[str, Any],
    *,
    actor: User,
    request: Request | None = None,
) -> LeadFollowUp:
    lead = _get_lead_or_raise(db, lead_id)
    follow_up = LeadFollowUp(lead_id=lead_id, **data)
    db.add(follow_up)
    db.flush()

    log_entity_created(
        db,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead_id,
        description_key="activity.lead.follow_up_created",
        actor=actor,
        metadata={"follow_up_type": follow_up.follow_up_type.value, "due_at": follow_up.due_at.isoformat()},
        request=request,
        is_demo=lead.is_demo,
    )
    _append_timeline(
        db,
        lead_id,
        event_type="sales.lead.followup_due",
        actor=actor,
        metadata={"follow_up_id": str(follow_up.id), "due_at": follow_up.due_at.isoformat()},
    )
    return follow_up


def complete_follow_up(
    db: Session,
    lead_id: UUID,
    follow_up_id: UUID,
    *,
    actor: User,
    request: Request | None = None,
) -> LeadFollowUp:
    lead = _get_lead_or_raise(db, lead_id)
    follow_up = db.get(LeadFollowUp, follow_up_id)
    if follow_up is None or follow_up.lead_id != lead_id:
        raise QualificationError("leads.errors.follow_up_not_found", status_code=404)

    follow_up.status = FollowUpStatus.COMPLETED
    follow_up.completed_at = _now()
    follow_up.updated_at = _now()
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead_id,
        description_key="activity.lead.follow_up_completed",
        actor=actor,
        before={"status": "pending"},
        after={"status": "completed"},
        metadata={"follow_up_id": str(follow_up_id)},
        request=request,
        is_demo=lead.is_demo,
    )
    return follow_up


def build_lead_timeline(db: Session, lead_id: UUID, *, limit: int = 100) -> list[dict[str, Any]]:
    """Merge domain timeline + activity logs chronologically."""
    from investhome_api.models.activity import ActivityLog

    _get_lead_or_raise(db, lead_id)

    domain_entries = db.scalars(
        select(LeadTimeline)
        .where(LeadTimeline.lead_id == lead_id)
        .order_by(LeadTimeline.created_at.desc())
        .limit(limit)
    ).all()

    activity_entries = db.scalars(
        select(ActivityLog)
        .where(
            ActivityLog.entity_id == lead_id,
            ActivityLog.entity_type.in_([ActivityEntityType.LEAD, ActivityEntityType.LEAD_QUALIFICATION]),
        )
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    ).all()

    merged: list[dict[str, Any]] = []
    for entry in domain_entries:
        merged.append(
            {
                "source": "timeline",
                "event_type": entry.event_type,
                "actor_user_id": str(entry.actor_user_id) if entry.actor_user_id else None,
                "notes": entry.notes,
                "metadata": entry.metadata_json,
                "created_at": entry.created_at.isoformat(),
            }
        )
    for entry in activity_entries:
        merged.append(
            {
                "source": "activity",
                "event_type": entry.event_type,
                "actor_user_id": str(entry.actor_user_id) if entry.actor_user_id else None,
                "notes": entry.description_key,
                "metadata": entry.metadata_json,
                "created_at": entry.created_at.isoformat(),
            }
        )

    merged.sort(key=lambda x: x["created_at"], reverse=True)
    return merged[:limit]


def build_executive_qualification_summary(db: Session) -> dict[str, Any]:
    from sqlalchemy import func

    from investhome_api.models.lead_qualification import LeadScore

    qualified = db.scalar(
        select(func.count())
        .select_from(LeadQualification)
        .where(LeadQualification.qualification_status == QualificationStatus.QUALIFIED)
    ) or 0
    unqualified = db.scalar(
        select(func.count())
        .select_from(LeadQualification)
        .where(LeadQualification.qualification_status == QualificationStatus.UNQUALIFIED)
    ) or 0
    awaiting_review = db.scalar(
        select(func.count())
        .select_from(LeadQualification)
        .where(LeadQualification.qualification_status == QualificationStatus.IN_REVIEW)
    ) or 0
    avg_score = db.scalar(select(func.avg(LeadScore.total_score)).select_from(LeadScore)) or 0

    # Leads without pending follow-ups
    leads_with_pending = select(LeadFollowUp.lead_id).where(
        LeadFollowUp.status == FollowUpStatus.PENDING
    )
    active_leads = select(Lead.id).where(Lead.archived_at.is_(None))
    without_follow_up = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(Lead.id.in_(active_leads), Lead.id.notin_(leads_with_pending))
    ) or 0

    ready_for_opportunity = db.scalar(
        select(func.count())
        .select_from(LeadQualification)
        .where(
            LeadQualification.qualification_status == QualificationStatus.QUALIFIED,
        )
    ) or 0

    return {
        "qualified_count": qualified,
        "unqualified_count": unqualified,
        "awaiting_review_count": awaiting_review,
        "avg_lead_score": round(float(avg_score), 1),
        "without_follow_up_count": without_follow_up,
        "ready_for_opportunity_count": ready_for_opportunity,
    }
