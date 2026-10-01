"""CreativeStrategyV1 — exists BEFORE layout. No coordinates. No renderer primitives."""

from __future__ import annotations

from typing import Any

SCHEMA = "CreativeStrategyV1"

STRATEGY_FIELDS = (
    "project_story",
    "campaign_objective",
    "target_emotion",
    "primary_message",
    "commercial_message",
    "available_real_assets",
    "strongest_project_characteristic",
    "selected_design_dna",
    "creative_tension",
    "visual_idea",
    "why_this_idea_fits_this_project",
)


def empty_creative_strategy() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNSET",
        "layout_forbidden_until_strategy_exists": True,
        **{field: None for field in STRATEGY_FIELDS},
        "no_copy_test": {"required": True, "status": "NOT_RUN"},
        "two_second_test": {"required": True, "status": "NOT_RUN", "answer": None},
        "project_reality": {
            "architecture_invented": False,
            "interior_invented": False,
            "exterior_invented": False,
            "logo_invented": False,
            "facts_invented": False,
        },
    }


def validate_creative_strategy(strategy: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in STRATEGY_FIELDS if not str((strategy or {}).get(field) or "").strip()]
    ready = not missing
    return {
        "schema": "CreativeStrategyValidationV1",
        "pass": ready,
        "missing_fields": missing,
        "layout_allowed": ready,
        "reason": None if ready else "Strategy must exist before layout, typography, or render.",
    }


def creative_strategy_schema() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "fields": list(STRATEGY_FIELDS),
        "order": "strategy before layout",
        "example_user_intent": "The Temple için premium bir lansman reklamı hazırla.",
        "user_does_not_specify": [
            "layout",
            "typography",
            "hierarchy",
            "composition",
            "masking",
            "art direction",
            "negative space",
            "image treatment",
            "graphic mechanism",
        ],
        "engine_decides": [
            "visual idea",
            "design DNA",
            "photo role",
            "typographic system",
            "commercial hierarchy",
            "graphic devices",
        ],
        "status": "READY",
    }
