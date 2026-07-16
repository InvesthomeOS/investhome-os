"""Notification business rules and thresholds."""

from decimal import Decimal

from investhome_api.config.executive_config import (
    BUDGET_VARIANCE_AT_RISK_RATIO,
    BUDGET_VARIANCE_ATTENTION_RATIO,
    COMPLETION_APPROACHING_DAYS,
    FUNDING_GAP_AT_RISK,
    FUNDING_GAP_ATTENTION,
    LEAD_INACTIVITY_DAYS,
    LOW_AVAILABLE_BALANCE_RATIO,
)

# Days without follow-up before lead reminder.
LEAD_NO_FOLLOWUP_DAYS: int = 7

# Days a qualified lead may wait before alert.
QUALIFIED_LEAD_WAITING_DAYS: int = 5

# Days before proposal expected after meeting scheduled.
PROPOSAL_NOT_SENT_DAYS: int = 7

# Entity type -> permission resource for visibility checks.
ENTITY_RESOURCE_MAP: dict[str, str] = {
    "lead": "leads",
    "investor": "investors",
    "project": "projects",
    "financial_account": "finance",
    "transaction": "finance",
    "project_budget": "finance",
    "funding_commitment": "finance",
    "payment_obligation": "finance",
    "user": "users",
    "role": "roles",
    "document": "documents",
    "inventory_reservation": "inventory",
    "price_change_request": "inventory",
    "inventory_price": "inventory",
}

SECURITY_ENTITY_TYPES = frozenset({"user", "role"})

EXECUTIVE_ONLY_RULES = frozenset(
    {
        "project.funding_gap",
        "project.budget_variance",
        "finance.low_cash_balance",
    }
)

# Re-export executive thresholds for generator use.
__all__ = [
    "LEAD_NO_FOLLOWUP_DAYS",
    "QUALIFIED_LEAD_WAITING_DAYS",
    "PROPOSAL_NOT_SENT_DAYS",
    "ENTITY_RESOURCE_MAP",
    "SECURITY_ENTITY_TYPES",
    "EXECUTIVE_ONLY_RULES",
    "FUNDING_GAP_ATTENTION",
    "FUNDING_GAP_AT_RISK",
    "BUDGET_VARIANCE_ATTENTION_RATIO",
    "BUDGET_VARIANCE_AT_RISK_RATIO",
    "LEAD_INACTIVITY_DAYS",
    "LOW_AVAILABLE_BALANCE_RATIO",
    "COMPLETION_APPROACHING_DAYS",
]
