"""Sales opportunity pipeline rules and configuration."""

from __future__ import annotations

from investhome_api.models.sales import CLOSED_OPPORTUNITY_STAGES, OpportunityStage

ALLOWED_STAGE_TRANSITIONS: dict[OpportunityStage, frozenset[OpportunityStage]] = {
    OpportunityStage.NEW: frozenset(
        {
            OpportunityStage.QUALIFIED,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.QUALIFIED: frozenset(
        {
            OpportunityStage.MEETING_SCHEDULED,
            OpportunityStage.INVENTORY_MATCHING,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.MEETING_SCHEDULED: frozenset(
        {
            OpportunityStage.MEETING_COMPLETED,
            OpportunityStage.QUALIFIED,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.MEETING_COMPLETED: frozenset(
        {
            OpportunityStage.INVENTORY_MATCHING,
            OpportunityStage.PROPOSAL_PREPARATION,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.INVENTORY_MATCHING: frozenset(
        {
            OpportunityStage.PROPOSAL_PREPARATION,
            OpportunityStage.SOFT_HOLD,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.PROPOSAL_PREPARATION: frozenset(
        {
            OpportunityStage.PROPOSAL_SENT,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.PROPOSAL_SENT: frozenset(
        {
            OpportunityStage.NEGOTIATION,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.NEGOTIATION: frozenset(
        {
            OpportunityStage.SOFT_HOLD,
            OpportunityStage.RESERVATION,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.SOFT_HOLD: frozenset(
        {
            OpportunityStage.RESERVATION,
            OpportunityStage.INVENTORY_MATCHING,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.RESERVATION: frozenset(
        {
            OpportunityStage.DEPOSIT_PENDING,
            OpportunityStage.CONTRACT,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.DEPOSIT_PENDING: frozenset(
        {
            OpportunityStage.CONTRACT,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.CONTRACT: frozenset(
        {
            OpportunityStage.CLOSING_HANDOFF,
            OpportunityStage.WON,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.CLOSING_HANDOFF: frozenset(
        {
            OpportunityStage.WON,
            OpportunityStage.LOST,
            OpportunityStage.DORMANT,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.DORMANT: frozenset(
        {
            OpportunityStage.NEW,
            OpportunityStage.QUALIFIED,
            OpportunityStage.CANCELLED,
        }
    ),
    OpportunityStage.WON: frozenset(),
    OpportunityStage.LOST: frozenset(),
    OpportunityStage.CANCELLED: frozenset(),
}

CONTRACT_PATH_STAGES = frozenset(
    {
        OpportunityStage.CONTRACT,
        OpportunityStage.CLOSING_HANDOFF,
    }
)

OPPORTUNITY_ACTIVITY_FIELDS = [
    "opportunity_code",
    "stage",
    "probability",
    "expected_revenue",
    "expected_close_date",
    "assigned_sales_user_id",
    "next_action",
    "next_action_date",
    "reservation_id",
    "loss_reason",
    "dormant_review_date",
    "cancelled_reason",
]
