"""Rule-based lead scoring — human-reviewed, not ML."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.lead import Lead
from investhome_api.models.lead_qualification import (
    FollowUpStatus,
    FollowUpType,
    LeadFollowUp,
    LeadInventoryInterest,
    LeadQualification,
    LeadScore,
    LeadScoreComponent,
    LeadTimeline,
    QualificationStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import log_entity_updated
from investhome_api.services.leads.config import LEAD_SCORE_COMPONENT_KEYS, LEAD_SCORE_WEIGHTS
from investhome_api.services.leads.qualification_service import QualificationError, _append_timeline, _get_lead_or_raise
from investhome_api.models.notification import NotificationPriority, NotificationType
from investhome_api.services.notification_hooks import notify_users_with_permission


def _now() -> datetime:
    return datetime.now(UTC)


def _score_budget_readiness(qual: LeadQualification | None) -> int:
    if qual is None:
        return 0
    if qual.budget_min and qual.budget_max:
        return 100
    if qual.budget_min or qual.budget_max:
        return 70
    return 20


def _score_timeline(qual: LeadQualification | None) -> int:
    if qual is None or qual.expected_purchase_timeline is None:
        return 10
    mapping = {
        "immediate": 100,
        "3_months": 85,
        "6_months": 60,
        "12_plus": 40,
        "unknown": 15,
    }
    return mapping.get(qual.expected_purchase_timeline.value, 15)


def _score_investment_capacity(qual: LeadQualification | None) -> int:
    if qual is None or not qual.investment_capacity:
        return 10
    capacity = qual.investment_capacity.lower()
    if any(k in capacity for k in ("high", "large", "1m", "million")):
        return 90
    if any(k in capacity for k in ("medium", "mid")):
        return 60
    return 40


def _score_engagement(db: Session, lead_id: UUID) -> int:
    follow_ups = db.scalars(
        select(LeadFollowUp).where(LeadFollowUp.lead_id == lead_id)
    ).all()
    if not follow_ups:
        return 20
    completed = sum(1 for f in follow_ups if f.status == FollowUpStatus.COMPLETED)
    ratio = completed / len(follow_ups)
    return min(100, int(30 + ratio * 70))


def _score_meeting_completion(db: Session, lead_id: UUID) -> int:
    meetings = db.scalars(
        select(LeadFollowUp).where(
            LeadFollowUp.lead_id == lead_id,
            LeadFollowUp.follow_up_type == FollowUpType.MEETING,
        )
    ).all()
    if not meetings:
        return 0
    completed = sum(1 for m in meetings if m.status == FollowUpStatus.COMPLETED)
    return min(100, int(completed / len(meetings) * 100))


def _score_document_readiness(qual: LeadQualification | None) -> int:
    if qual is None or not qual.required_documents:
        return 30
    doc_count = len(qual.required_documents)
    if doc_count == 0:
        return 50
    return min(100, 40 + doc_count * 10)


def _score_inventory_match(db: Session, lead_id: UUID) -> int:
    interests = db.scalars(
        select(LeadInventoryInterest).where(LeadInventoryInterest.lead_id == lead_id)
    ).all()
    if not interests:
        return 0
    positive = sum(1 for i in interests if i.interest_type.value in ("matched", "shortlisted", "favorite"))
    return min(100, int(positive / len(interests) * 100))


def _score_sales_confidence(qual: LeadQualification | None) -> int:
    if qual is None:
        return 0
    mapping = {
        QualificationStatus.QUALIFIED: 100,
        QualificationStatus.IN_REVIEW: 60,
        QualificationStatus.REQUIRES_MORE_INFORMATION: 40,
        QualificationStatus.NEW: 20,
        QualificationStatus.UNQUALIFIED: 0,
    }
    return mapping.get(qual.qualification_status, 0)


def compute_component_scores(db: Session, lead_id: UUID) -> dict[str, int]:
    qual = db.scalar(select(LeadQualification).where(LeadQualification.lead_id == lead_id))
    return {
        "budget_readiness": _score_budget_readiness(qual),
        "timeline": _score_timeline(qual),
        "investment_capacity": _score_investment_capacity(qual),
        "engagement": _score_engagement(db, lead_id),
        "meeting_completion": _score_meeting_completion(db, lead_id),
        "document_readiness": _score_document_readiness(qual),
        "inventory_match_quality": _score_inventory_match(db, lead_id),
        "sales_confidence": _score_sales_confidence(qual),
    }


def calculate_total_score(component_scores: dict[str, int]) -> int:
    total = Decimal("0")
    for key, weight in LEAD_SCORE_WEIGHTS.items():
        score = component_scores.get(key, 0)
        total += Decimal(str(score)) * weight
    return max(0, min(100, int(total)))


def get_lead_score(db: Session, lead_id: UUID) -> LeadScore | None:
    _get_lead_or_raise(db, lead_id)
    return db.scalar(select(LeadScore).where(LeadScore.lead_id == lead_id))


def recalculate_lead_score(
    db: Session,
    lead_id: UUID,
    *,
    actor: User,
    manual_override: int | None = None,
    request: Request | None = None,
) -> tuple[LeadScore, list[LeadScoreComponent]]:
    lead = _get_lead_or_raise(db, lead_id)
    component_scores = compute_component_scores(db, lead_id)
    total = manual_override if manual_override is not None else calculate_total_score(component_scores)

    existing = db.scalar(select(LeadScore).where(LeadScore.lead_id == lead_id))
    if existing:
        db.execute(
            LeadScoreComponent.__table__.delete().where(
                LeadScoreComponent.lead_score_id == existing.id
            )
        )
        existing.total_score = total
        existing.computed_at = _now()
        existing.computed_by_id = actor.id
        existing.is_manual_override = manual_override is not None
        existing.updated_at = _now()
        lead_score = existing
    else:
        lead_score = LeadScore(
            lead_id=lead_id,
            total_score=total,
            computed_by_id=actor.id,
            is_manual_override=manual_override is not None,
        )
        db.add(lead_score)
        db.flush()

    components: list[LeadScoreComponent] = []
    for key in LEAD_SCORE_COMPONENT_KEYS:
        comp = LeadScoreComponent(
            lead_score_id=lead_score.id,
            component_key=key,
            score=component_scores.get(key, 0),
            weight=LEAD_SCORE_WEIGHTS[key],
        )
        db.add(comp)
        components.append(comp)

    lead.cached_lead_score = total
    lead.updated_at = _now()
    db.flush()

    log_entity_updated(
        db,
        entity_type=ActivityEntityType.LEAD_QUALIFICATION,
        entity_id=lead_score.id,
        description_key="activity.lead_score.updated",
        actor=actor,
        before={},
        after={"total_score": total},
        metadata={"lead_id": str(lead_id), "lead_name": lead.full_name},
        request=request,
        is_demo=lead.is_demo,
    )
    _append_timeline(
        db,
        lead_id,
        event_type="sales.lead.score_updated",
        actor=actor,
        metadata={"total_score": total, "manual_override": manual_override is not None},
    )
    notify_users_with_permission(
        db,
        resource="sales",
        action="view_lead",
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.LOW,
        title_key="notifications.lead.score_updated.title",
        message_key="notifications.lead.score_updated.message",
        rule_key="lead.score_updated",
        related_entity_type="lead",
        related_entity_id=lead_id,
        metadata={"lead_name": lead.full_name, "score": total},
        created_by=actor.id,
    )
    return lead_score, components
