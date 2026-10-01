"""Creative Critic V2 — human publishability is the gate. Do not inflate scores."""

from __future__ import annotations

from typing import Any

AXES = (
    "VISUAL_IDEA",
    "ART_DIRECTION",
    "PHOTO_INTEGRATION",
    "TYPOGRAPHIC_SOPHISTICATION",
    "COMMERCIAL_HIERARCHY",
    "BRAND_CHARACTER",
    "DEPTH",
    "NEGATIVE_SPACE",
    "DISTINCTIVENESS",
    "FINISH_QUALITY",
    "TWO_SECOND_IMPACT",
    "PUBLISHABILITY",
)

PREMIUM_FLOORS = {
    "VISUAL_IDEA": 8,
    "ART_DIRECTION": 8,
    "PHOTO_INTEGRATION": 9,
    "TYPOGRAPHIC_SOPHISTICATION": 8,
    "COMMERCIAL_HIERARCHY": 8,
    "DISTINCTIVENESS": 8,
    "FINISH_QUALITY": 9,
    "TWO_SECOND_IMPACT": 8,
    "PUBLISHABILITY": 9,
}

BOOLEAN_GATES = ("ANTI_TEMPLATE_DETECTOR", "NO_COPY_TEST", "PROJECT_REALITY")


def empty_critic_v2() -> dict[str, Any]:
    return {
        "schema": "CreativeCriticV2",
        "scores": {axis: None for axis in AXES},
        "technical_correctness": "evaluated_separately",
        "note": "A technically perfect creative may still score PUBLISHABILITY = 3. That is allowed.",
        "inflate_forbidden": True,
        "human_publishability_question": "Would a demanding human actually publish this as a premium real-estate campaign?",
    }


def score_creative_v2(
    scores: dict[str, int],
    *,
    anti_template: str,
    no_copy: str,
    project_reality: str,
) -> dict[str, Any]:
    normalized = {axis: int(scores.get(axis, 0)) for axis in AXES}
    floor_fail = [axis for axis, floor in PREMIUM_FLOORS.items() if normalized.get(axis, 0) < floor]
    bool_fail = []
    if anti_template != "PASS":
        bool_fail.append("ANTI_TEMPLATE_DETECTOR")
    if no_copy != "PASS":
        bool_fail.append("NO_COPY_TEST")
    if project_reality != "PASS":
        bool_fail.append("PROJECT_REALITY")
    automated_pass = not floor_fail and not bool_fail
    return {
        "schema": "CreativeCriticV2Result",
        "scores": normalized,
        "floor_failures": floor_fail,
        "boolean_failures": bool_fail,
        "automated_pass": automated_pass,
        "status": "PENDING_HUMAN_APPROVAL" if automated_pass else "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW",
        "human_approval": "REQUIRED",
        "publishability": normalized.get("PUBLISHABILITY"),
        "automated_pass_is_not_creative_approval": True,
    }


def critic_v2_contract() -> dict[str, Any]:
    return {
        "schema": "CreativeCriticV2",
        "axes": list(AXES),
        "scale": "0-10",
        "premium_floors": dict(PREMIUM_FLOORS),
        "boolean_gates": list(BOOLEAN_GATES),
        "reject_status": "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW",
        "pass_status": "PENDING_HUMAN_APPROVAL",
        "human_approved_requires_explicit_visual_approval": True,
        "status": "READY",
    }
