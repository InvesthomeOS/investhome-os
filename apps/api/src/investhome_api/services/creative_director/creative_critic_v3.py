"""Creative Critic V3 — extends V2 with commercial integration, reading path, persuasive power."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_critic_v2 import AXES as V2_AXES
from investhome_api.services.creative_director.creative_critic_v2 import PREMIUM_FLOORS as V2_FLOORS

SCHEMA = "CreativeCriticV3"

AXES = (
    "VISUAL_IDEA",
    "ART_DIRECTION",
    "PHOTO_INTEGRATION",
    "TYPOGRAPHIC_SOPHISTICATION",
    "COMMERCIAL_INTEGRATION",
    "COMMERCIAL_HIERARCHY",
    "READING_PATH",
    "BRAND_CHARACTER",
    "DEPTH",
    "NEGATIVE_SPACE",
    "DISTINCTIVENESS",
    "FINISH_QUALITY",
    "TWO_SECOND_IMPACT",
    "PERSUASIVE_POWER",
    "PUBLISHABILITY",
)

PREMIUM_FLOORS = {
    "VISUAL_IDEA": 8,
    "ART_DIRECTION": 8,
    "PHOTO_INTEGRATION": 9,
    "TYPOGRAPHIC_SOPHISTICATION": 8,
    "COMMERCIAL_INTEGRATION": 9,
    "COMMERCIAL_HIERARCHY": 9,
    "READING_PATH": 9,
    "BRAND_CHARACTER": 8,
    "DEPTH": 8,
    "DISTINCTIVENESS": 8,
    "FINISH_QUALITY": 9,
    "TWO_SECOND_IMPACT": 8,
    "PERSUASIVE_POWER": 9,
    "PUBLISHABILITY": 9,
}

BOOLEAN_GATES = (
    "ANTI_TEMPLATE_DETECTOR",
    "VISUAL_IDEA_GATE",
    "COMMERCIAL_SYSTEM_GATE",
    "DETACHED_COMMERCIAL_LOCKUP_DETECTOR",
    "THUMBNAIL_TEST",
    "ADVERTISEMENT_VS_POSTER_TEST",
    "PROJECT_REALITY",
)


def critic_v3_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "extends": "CreativeCriticV2",
        "v2_axes_preserved": list(V2_AXES),
        "v2_floors_preserved": dict(V2_FLOORS),
        "axes": list(AXES),
        "scale": "0-10",
        "premium_floors": dict(PREMIUM_FLOORS),
        "boolean_gates": list(BOOLEAN_GATES),
        "new_axes": [
            "COMMERCIAL_INTEGRATION",
            "READING_PATH",
            "PERSUASIVE_POWER",
        ],
        "raised_floors": {
            "COMMERCIAL_HIERARCHY": "8 → 9",
        },
        "reject_status": "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW",
        "pass_status": "PENDING_HUMAN_APPROVAL",
        "human_approved_requires_explicit_visual_approval": True,
        "inflate_forbidden": True,
        "status": "READY",
    }


def score_creative_v3(
    scores: dict[str, int],
    *,
    anti_template: str,
    visual_idea_gate: str,
    commercial_system_gate: str,
    detached_lockup: str,
    thumbnail: str,
    advertisement_vs_poster: str,
    project_reality: str,
) -> dict[str, Any]:
    normalized = {axis: int(scores.get(axis, 0)) for axis in AXES}
    floor_fail = [axis for axis, floor in PREMIUM_FLOORS.items() if normalized.get(axis, 0) < floor]
    bool_fail = []
    if anti_template != "PASS":
        bool_fail.append("ANTI_TEMPLATE_DETECTOR")
    if visual_idea_gate != "PASS":
        bool_fail.append("VISUAL_IDEA_GATE")
    if commercial_system_gate != "PASS":
        bool_fail.append("COMMERCIAL_SYSTEM_GATE")
    if detached_lockup != "PASS":
        bool_fail.append("DETACHED_COMMERCIAL_LOCKUP_DETECTOR")
    if thumbnail != "PASS":
        bool_fail.append("THUMBNAIL_TEST")
    if advertisement_vs_poster != "PASS":
        bool_fail.append("ADVERTISEMENT_VS_POSTER_TEST")
    if project_reality != "PASS":
        bool_fail.append("PROJECT_REALITY")
    automated_pass = not floor_fail and not bool_fail
    return {
        "schema": "CreativeCriticV3Result",
        "scores": normalized,
        "floor_failures": floor_fail,
        "boolean_failures": bool_fail,
        "automated_pass": automated_pass,
        "status": "PENDING_HUMAN_APPROVAL" if automated_pass else "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW",
        "human_approval": "REQUIRED",
        "publishability": normalized.get("PUBLISHABILITY"),
        "persuasive_power": normalized.get("PERSUASIVE_POWER"),
        "automated_pass_is_not_creative_approval": True,
    }
