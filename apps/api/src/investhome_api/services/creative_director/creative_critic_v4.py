"""Creative Critic V4 — V3 plus photo/field relationship; Hybrid V2 floors."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_critic_v3 import AXES as V3_AXES
from investhome_api.services.creative_director.creative_critic_v3 import BOOLEAN_GATES
from investhome_api.services.creative_director.creative_critic_v3 import PREMIUM_FLOORS as V3_FLOORS

SCHEMA = "CreativeCriticV4"

AXES = (
    "VISUAL_IDEA",
    "ART_DIRECTION",
    "PHOTO_INTEGRATION",
    "PHOTO_FIELD_RELATIONSHIP",
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
    "VISUAL_IDEA": 9,
    "ART_DIRECTION": 9,
    "PHOTO_INTEGRATION": 9,
    "PHOTO_FIELD_RELATIONSHIP": 9,
    "TYPOGRAPHIC_SOPHISTICATION": 9,
    "COMMERCIAL_INTEGRATION": 9,
    "COMMERCIAL_HIERARCHY": 9,
    "READING_PATH": 9,
    "BRAND_CHARACTER": 8,
    "DEPTH": 9,
    "DISTINCTIVENESS": 9,
    "FINISH_QUALITY": 9,
    "TWO_SECOND_IMPACT": 9,
    "PERSUASIVE_POWER": 9,
    "PUBLISHABILITY": 9,
}


def critic_v4_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "extends": "CreativeCriticV3",
        "v3_axes_preserved": list(V3_AXES),
        "v3_floors_preserved": dict(V3_FLOORS),
        "axes": list(AXES),
        "scale": "0-10",
        "premium_floors": dict(PREMIUM_FLOORS),
        "boolean_gates": list(BOOLEAN_GATES),
        "new_axes": ["PHOTO_FIELD_RELATIONSHIP"],
        "inflate_forbidden": True,
        "status": "READY",
        "pass_status": "HYBRID_V2_CREATIVE_PENDING_HUMAN_REVIEW",
        "fail_status": "HYBRID_V2_CREATIVE_FAIL",
        "human_approved_requires_explicit_visual_approval": True,
        "router_eligible_on_pass": False,
        "master_on_pass": False,
    }


def score_creative_v4(
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
        "schema": "CreativeCriticV4Result",
        "scores": normalized,
        "floor_failures": floor_fail,
        "boolean_failures": bool_fail,
        "automated_pass": automated_pass,
        "status": "HYBRID_V2_CREATIVE_PENDING_HUMAN_REVIEW" if automated_pass else "HYBRID_V2_CREATIVE_FAIL",
        "human_approval": "REQUIRED",
        "router_eligible": False,
        "master": False,
        "publishability": normalized.get("PUBLISHABILITY"),
        "photo_field_relationship": normalized.get("PHOTO_FIELD_RELATIONSHIP"),
        "automated_pass_is_not_creative_approval": True,
        "inflate_forbidden": True,
    }
