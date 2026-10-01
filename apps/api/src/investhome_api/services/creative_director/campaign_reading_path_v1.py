"""CampaignReadingPathV1 — intentional attention sequence, not leftover placement."""

from __future__ import annotations

from typing import Any

SCHEMA = "CampaignReadingPathV1"

STAGES = (
    "ENTRY_POINT",
    "SECONDARY_ATTENTION",
    "COMMERCIAL_REVEAL",
    "VALUE_CONFIRMATION",
    "ACTION",
)

ABSTRACT_FLOW = (
    "VISUAL_EVENT",
    "CAMPAIGN_MESSAGE",
    "OFFER",
    "PRICE_PRODUCT",
    "ACTION",
)


def empty_reading_path() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "stages": {stage: None for stage in STAGES},
        "abstract_flow": list(ABSTRACT_FLOW),
        "note": "The exact structure may vary. It must be intentional.",
        "status": "UNSET",
    }


def validate_reading_path(path: dict[str, Any]) -> dict[str, Any]:
    stages = dict((path or {}).get("stages") or {})
    missing = [stage for stage in STAGES if not str(stages.get(stage) or "").strip()]
    return {
        "schema": "CampaignReadingPathValidationV1",
        "pass": not missing,
        "missing_stages": missing,
        "reason": None if not missing else "Every reading-path stage must be named before render.",
    }


def campaign_reading_path_schema() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "stages": list(STAGES),
        "example_abstract_structure": " → ".join(ABSTRACT_FLOW),
        "rule": (
            "Model what the viewer encounters: visual event, campaign message, offer, "
            "price/product, action. Variation is allowed. Accidental leftover placement is not."
        ),
        "status": "READY",
    }
