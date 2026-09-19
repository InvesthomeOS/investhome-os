"""Relationship score engine — weighted factors from interaction data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.crm_relationship import (
    CrmRelationship,
    CrmRelationshipScoreSnapshot,
    CrmRelationshipStrength,
)
from investhome_api.schemas.crm_relationships import CrmRelationshipScoreBreakdown

STRENGTH_WEIGHTS = {
    CrmRelationshipStrength.WEAK: 0.4,
    CrmRelationshipStrength.MODERATE: 0.6,
    CrmRelationshipStrength.STRONG: 0.8,
    CrmRelationshipStrength.STRATEGIC: 1.0,
}

SCORE_WEIGHTS = {
    "engagement": 0.25,
    "influence": 0.20,
    "trust": 0.20,
    "business_value": 0.25,
    "risk_penalty": 0.10,
}


def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _days_since(dt: datetime | None) -> int | None:
    if not dt:
        return None
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (now - dt).days


def _entity_engagement_hint(db: Session, relationship: CrmRelationship) -> int:
    """Derive engagement from linked contact/company last_contact when available."""
    scores: list[int] = []
    for entity_type, entity_id in (
        (relationship.source_entity_type.value, relationship.source_entity_id),
        (relationship.target_entity_type.value, relationship.target_entity_id),
    ):
        if entity_type == "contact":
            contact = db.get(CrmContact, entity_id)
            if contact:
                days = _days_since(contact.last_contact_at)
                if days is None:
                    scores.append(30)
                elif days <= 7:
                    scores.append(90)
                elif days <= 30:
                    scores.append(70)
                elif days <= 90:
                    scores.append(45)
                else:
                    scores.append(20)
    if not scores:
        days = _days_since(relationship.last_interaction_at)
        if days is None:
            return 35
        if days <= 14:
            return 75
        if days <= 60:
            return 50
        return 25
    return _clamp(sum(scores) / len(scores))


def calculate_relationship_scores(
    db: Session,
    relationship: CrmRelationship,
) -> CrmRelationshipScoreBreakdown:
    strength_factor = STRENGTH_WEIGHTS.get(relationship.strength, 0.5)
    engagement = _entity_engagement_hint(db, relationship)
    influence = _clamp(50 + (30 * strength_factor) + (10 if relationship.is_verified else 0))
    trust = _clamp(40 + (35 * strength_factor) + (15 if relationship.is_verified else 0))
    business_value = _clamp(35 + (40 * strength_factor))
    risk = _clamp(60 - engagement * 0.4 - trust * 0.3)
    if relationship.is_confidential:
        trust = _clamp(trust + 5)

    relationship_score = _clamp(
        engagement * SCORE_WEIGHTS["engagement"]
        + influence * SCORE_WEIGHTS["influence"]
        + trust * SCORE_WEIGHTS["trust"]
        + business_value * SCORE_WEIGHTS["business_value"]
        - risk * SCORE_WEIGHTS["risk_penalty"]
    )

    factors = {
        "strength_factor": strength_factor,
        "engagement_source": "entity_last_contact" if engagement != 35 else "relationship_or_default",
        "verified_boost": relationship.is_verified,
        "confidential_adjustment": relationship.is_confidential,
        "weights": SCORE_WEIGHTS,
    }

    return CrmRelationshipScoreBreakdown(
        relationship_score=relationship_score,
        engagement_score=engagement,
        influence_score=influence,
        trust_score=trust,
        business_value_score=business_value,
        risk_score=risk,
        factors=factors,
    )


def apply_scores_to_relationship(
    db: Session,
    relationship: CrmRelationship,
    breakdown: CrmRelationshipScoreBreakdown,
) -> None:
    relationship.relationship_score = breakdown.relationship_score
    relationship.engagement_score = breakdown.engagement_score
    relationship.influence_score = breakdown.influence_score
    relationship.trust_score = breakdown.trust_score
    relationship.business_value_score = breakdown.business_value_score
    relationship.risk_score = breakdown.risk_score

    snapshot = CrmRelationshipScoreSnapshot(
        relationship_id=relationship.id,
        relationship_score=breakdown.relationship_score,
        engagement_score=breakdown.engagement_score,
        influence_score=breakdown.influence_score,
        trust_score=breakdown.trust_score,
        business_value_score=breakdown.business_value_score,
        risk_score=breakdown.risk_score,
        factors=breakdown.factors,
    )
    db.add(snapshot)


def recalculate_scores(
    db: Session,
    *,
    relationship_ids: list[UUID] | None = None,
    recalculate_all: bool = False,
) -> tuple[int, list[CrmRelationshipScoreBreakdown]]:
    query = select(CrmRelationship).where(CrmRelationship.archived_at.is_(None))
    if relationship_ids:
        query = query.where(CrmRelationship.id.in_(relationship_ids))
    elif not recalculate_all:
        return 0, []

    relationships = db.scalars(query).all()
    results: list[CrmRelationshipScoreBreakdown] = []
    for rel in relationships:
        breakdown = calculate_relationship_scores(db, rel)
        apply_scores_to_relationship(db, rel, breakdown)
        results.append(breakdown)
    return len(results), results
