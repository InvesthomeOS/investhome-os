"""Centralized business rules for executive dashboard health and alerts."""

from decimal import Decimal

# Funding gap thresholds (USD-equivalent; applied per currency without conversion).
FUNDING_GAP_ATTENTION: Decimal = Decimal("250000")
FUNDING_GAP_AT_RISK: Decimal = Decimal("1000000")

# Budget variance as a share of revised budget.
BUDGET_VARIANCE_ATTENTION_RATIO: Decimal = Decimal("0.10")
BUDGET_VARIANCE_AT_RISK_RATIO: Decimal = Decimal("0.20")

# Account available balance as a share of current balance.
LOW_AVAILABLE_BALANCE_RATIO: Decimal = Decimal("0.15")

# Days without activity for qualified leads.
LEAD_INACTIVITY_DAYS: int = 14

# Days before target completion to flag approaching deadline.
COMPLETION_APPROACHING_DAYS: int = 30

# Completed project statuses excluded from overdue completion checks.
COMPLETED_PROJECT_STATUSES = frozenset({"completed", "cancelled", "on_hold"})
