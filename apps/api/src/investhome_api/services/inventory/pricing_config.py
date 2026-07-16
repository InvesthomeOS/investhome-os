"""Centralized approval rules for inventory pricing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from investhome_api.models.inventory import PriceType, SENSITIVE_PRICE_TYPES

# Large change warning threshold (percent) — UI and notifications only.
LARGE_CHANGE_WARNING_PERCENT = Decimal("10")

# High-impact threshold for executive widgets.
HIGH_IMPACT_CHANGE_PERCENT = Decimal("10")
HIGH_IMPACT_CHANGE_AMOUNT = Decimal("50000")


@dataclass(frozen=True)
class ApprovalRuleContext:
    price_type: PriceType
    project_id: UUID | None
    current_amount: Decimal | None
    proposed_amount: Decimal
    change_percentage: Decimal | None
    requester_role_codes: frozenset[str]


def requires_approval(ctx: ApprovalRuleContext) -> bool:
    """All material price changes require approval in Sprint 4B4."""
    _ = ctx
    return True


def requires_sensitive_view(price_type: PriceType) -> bool:
    return price_type in SENSITIVE_PRICE_TYPES


def requires_sensitive_approve(price_type: PriceType) -> bool:
    return price_type in SENSITIVE_PRICE_TYPES


def is_high_impact(change_percentage: Decimal | None, change_amount: Decimal) -> bool:
    if change_percentage is not None and abs(change_percentage) >= HIGH_IMPACT_CHANGE_PERCENT:
        return True
    return abs(change_amount) >= HIGH_IMPACT_CHANGE_AMOUNT


def is_large_change(change_percentage: Decimal | None) -> bool:
    return change_percentage is not None and abs(change_percentage) >= LARGE_CHANGE_WARNING_PERCENT
