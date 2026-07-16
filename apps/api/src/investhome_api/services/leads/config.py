"""Lead qualification and scoring configuration."""

from decimal import Decimal

# Rule-based component weights (must sum to 1.0). Human-reviewed — not ML.
LEAD_SCORE_WEIGHTS: dict[str, Decimal] = {
    "budget_readiness": Decimal("0.20"),
    "timeline": Decimal("0.15"),
    "investment_capacity": Decimal("0.15"),
    "engagement": Decimal("0.10"),
    "meeting_completion": Decimal("0.10"),
    "document_readiness": Decimal("0.10"),
    "inventory_match_quality": Decimal("0.10"),
    "sales_confidence": Decimal("0.10"),
}

LEAD_SCORE_COMPONENT_KEYS = tuple(LEAD_SCORE_WEIGHTS.keys())

QUALIFICATION_ACTIVITY_FIELDS = [
    "investment_objective",
    "investment_capacity",
    "budget_min",
    "budget_max",
    "preferred_currency",
    "cash_or_financing",
    "expected_purchase_timeline",
    "preferred_markets",
    "preferred_projects",
    "preferred_property_types",
    "bedrooms_min",
    "bedrooms_max",
    "bathrooms_min",
    "bathrooms_max",
    "area_min",
    "area_max",
    "target_rental_yield",
    "expected_roi",
    "risk_tolerance",
    "decision_makers",
    "accredited_investor",
    "required_documents",
    "current_concerns",
    "sales_notes",
    "qualification_status",
]

# Valid qualification status transitions (human-reviewed workflow)
QUALIFICATION_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "new": {"in_review", "requires_more_information"},
    "in_review": {"qualified", "requires_more_information", "unqualified"},
    "requires_more_information": {"in_review", "unqualified"},
    "qualified": {"in_review", "requires_more_information"},
    "unqualified": {"in_review", "requires_more_information"},
}
