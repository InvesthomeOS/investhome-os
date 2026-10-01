"""DetachedCommercialLockupDetector — bans the Proof 01 / Proof 02 information column."""

from __future__ import annotations

from typing import Any

SCHEMA = "DetachedCommercialLockupDetectorV1"

QUESTION = (
    "If I copy this entire text block onto another real-estate photograph, "
    "would it still work almost unchanged?"
)


def detect_detached_commercial_lockup(
    *,
    lockup_is_independent_vertical_stack: bool,
    would_work_on_another_photo_unchanged: bool,
    headline_offer_price_unit_cta_share_one_column: bool | None = None,
) -> dict[str, Any]:
    column = bool(lockup_is_independent_vertical_stack)
    if headline_offer_price_unit_cta_share_one_column is True:
        column = True
    portable = bool(would_work_on_another_photo_unchanged)
    failed = column or portable
    return {
        "schema": SCHEMA,
        "question": QUESTION,
        "lockup_is_independent_vertical_stack": column,
        "would_work_on_another_photo_unchanged": portable,
        "pass": not failed,
        "fail_when": (
            "headline, offer, price, unit, and CTA primarily form an independent vertical stack "
            "that could be moved onto another photograph without materially changing the campaign idea"
        ),
        "action_if_fail": "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW",
        "proof_01_would_fail": True,
        "proof_02_would_fail": True,
    }


def detached_commercial_lockup_detector_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "question": QUESTION,
        "fail_when": [
            "headline + offer + price + unit + CTA form an independent vertical stack",
            "the lockup would still work almost unchanged on another real-estate photograph",
        ],
        "meaning_if_yes": "The commercial system is generic.",
        "proof_01": "FAIL — TARİH idea with a left commercial stack",
        "proof_02": "FAIL — seam idea with a left information column",
        "status": "READY",
    }
