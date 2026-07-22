"""Centralized lead status mapping for campaign performance reporting."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.sales import CLOSED_OPPORTUNITY_STAGES, OpportunityStage, SalesOpportunity


class AttributionLeadStatus:
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    OPPORTUNITY = "opportunity"
    CONVERTED = "converted"
    LOST = "lost"


_LEAD_STATUS_MAP: dict[LeadStatus, str] = {
    LeadStatus.NEW: AttributionLeadStatus.NEW,
    LeadStatus.CONTACTED: AttributionLeadStatus.CONTACTED,
    LeadStatus.QUALIFIED: AttributionLeadStatus.QUALIFIED,
    LeadStatus.MEETING_SCHEDULED: AttributionLeadStatus.OPPORTUNITY,
    LeadStatus.PROPOSAL_SENT: AttributionLeadStatus.OPPORTUNITY,
    LeadStatus.NEGOTIATION: AttributionLeadStatus.OPPORTUNITY,
    LeadStatus.WON: AttributionLeadStatus.CONVERTED,
    LeadStatus.LOST: AttributionLeadStatus.LOST,
}

_OPPORTUNITY_STAGE_MAP: dict[OpportunityStage, str] = {
    OpportunityStage.NEW: AttributionLeadStatus.NEW,
    OpportunityStage.QUALIFIED: AttributionLeadStatus.QUALIFIED,
    OpportunityStage.MEETING_SCHEDULED: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.MEETING_COMPLETED: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.INVENTORY_MATCHING: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.PROPOSAL_PREPARATION: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.PROPOSAL_SENT: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.NEGOTIATION: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.SOFT_HOLD: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.RESERVATION: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.DEPOSIT_PENDING: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.CONTRACT: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.CLOSING_HANDOFF: AttributionLeadStatus.OPPORTUNITY,
    OpportunityStage.WON: AttributionLeadStatus.CONVERTED,
    OpportunityStage.LOST: AttributionLeadStatus.LOST,
    OpportunityStage.DORMANT: AttributionLeadStatus.LOST,
    OpportunityStage.CANCELLED: AttributionLeadStatus.LOST,
}

_STATUS_RANK = {
    AttributionLeadStatus.NEW: 0,
    AttributionLeadStatus.CONTACTED: 1,
    AttributionLeadStatus.QUALIFIED: 2,
    AttributionLeadStatus.OPPORTUNITY: 3,
    AttributionLeadStatus.CONVERTED: 4,
    AttributionLeadStatus.LOST: 5,
}


def map_lead_status(status: LeadStatus) -> str:
    return _LEAD_STATUS_MAP.get(status, AttributionLeadStatus.NEW)


def map_opportunity_stage(stage: OpportunityStage) -> str:
    return _OPPORTUNITY_STAGE_MAP.get(stage, AttributionLeadStatus.OPPORTUNITY)


def resolve_lead_attribution_status(db: Session, lead_id: UUID) -> str:
    """Return the highest-progress attribution status for a lead."""
    lead = db.get(Lead, lead_id)
    if lead is None:
        return AttributionLeadStatus.NEW

    lead_status = map_lead_status(lead.status)
    best = lead_status

    opportunities = db.scalars(
        select(SalesOpportunity).where(
            SalesOpportunity.lead_id == lead_id,
            SalesOpportunity.archived_at.is_(None),
        )
    ).all()

    for opp in opportunities:
        opp_status = map_opportunity_stage(opp.stage)
        if _STATUS_RANK.get(opp_status, 0) > _STATUS_RANK.get(best, 0):
            best = opp_status
        if opp.stage == OpportunityStage.WON:
            return AttributionLeadStatus.CONVERTED

    if lead.status == LeadStatus.WON:
        return AttributionLeadStatus.CONVERTED
    if lead.status == LeadStatus.LOST and not opportunities:
        return AttributionLeadStatus.LOST

    return best


def is_converted_status(status: str) -> bool:
    return status == AttributionLeadStatus.CONVERTED


def is_qualified_status(status: str) -> bool:
    return status in {
        AttributionLeadStatus.QUALIFIED,
        AttributionLeadStatus.OPPORTUNITY,
        AttributionLeadStatus.CONVERTED,
    }


def is_open_opportunity(db: Session, lead_id: UUID) -> bool:
    opp = db.scalars(
        select(SalesOpportunity).where(
            SalesOpportunity.lead_id == lead_id,
            SalesOpportunity.archived_at.is_(None),
            SalesOpportunity.stage.not_in(CLOSED_OPPORTUNITY_STAGES),
        )
    ).first()
    return opp is not None
