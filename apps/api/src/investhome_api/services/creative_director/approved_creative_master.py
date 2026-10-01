"""ApprovedCreativeMasterV1 — structured editable state for a human-approved master.

The PNG is a render. The scene + group geometry are the source of truth.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.creative_master_library import (
    APPROVED_R1_ASSET_ID,
    CANVAS,
    MASTER_COMMERCIAL_R1_ID,
    scene_premium_commercial_r1,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_CAMPAIGN_ID,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
)

HUMAN_APPROVED = "HUMAN_APPROVED"

GROUP_GEOMETRY = {
    "project_photo": {"box": [0, 0, 1088, 1360], "mutable_for": []},
    "logo": {"box": [40, 30, 196, 98], "mutable_for": []},
    "headline": {"box": [40, 112, 292, 210], "mutable_for": ["COPY_REVISION"]},
    "unit_type": {"box": [40, 210, 292, 248], "mutable_for": ["UNIT_REVISION"]},
    "commercial": {"box": [592, 72, 1048, 268], "mutable_for": ["PRICE_REVISION"]},
    "cta": {"box": [40, 1194, 500, 1248], "mutable_for": ["CTA_REVISION"]},
}

IMMUTABLE_GROUPS = ("project_photo", "logo", "headline", "unit_type", "cta")
EDITABLE_GROUPS = ("commercial",)

COLOR_SYSTEM = {
    "ink": "#161C24",
    "gold": "#C9A56A",
    "ivory": "#F7F2EA",
    "support": "#3A414C",
    "struck": "#5C6370",
}

TYPOGRAPHY = {
    "DISPLAY": "Cormorant Garamond",
    "SUPPORT": "Source Sans 3",
}

PROTECTED_ARCHITECTURE = {
    "source_photo_asset_id": LOCKED_HERO_ASSET_ID,
    "filename": "IH_DC_TMP_001_Render_Exterior_Day_004.jpg",
    "no_generation": True,
    "no_redraw": True,
    "uniform_crop_only": True,
}

PHOTO_CROP = {
    "method": "cover_fit_canvas",
    "centering": "mass_lock",
    "canvas": [1088, 1360],
    "locked": True,
}


def commercial_mutable_box() -> tuple[int, int, int, int]:
    """Allowed pixel region for PRICE_REVISION reflow (padding for extra lines)."""
    return (580, 56, 1068, 300)


def build_approved_creative_master(*, approved_at: str | None = None) -> dict[str, Any]:
    facts = dict(REQUIRED_FACTS)
    now = approved_at or _now()
    return {
        "schema": "ApprovedCreativeMasterV1",
        "master_id": MASTER_COMMERCIAL_R1_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "campaign_id": PRODUCTION_CAMPAIGN_ID,
        "design_family": "PREMIUM_COMMERCIAL",
        "approval_status": HUMAN_APPROVED,
        "human_visual_status": "PASS",
        "approved_asset_id": APPROVED_R1_ASSET_ID,
        "source_photo_asset_id": LOCKED_HERO_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "canvas": dict(CANVAS),
        "typography": dict(TYPOGRAPHY),
        "color_system": dict(COLOR_SYSTEM),
        "semantic_content": dict(facts),
        "element_group_geometry": {k: dict(v) for k, v in GROUP_GEOMETRY.items()},
        "photo_crop": dict(PHOTO_CROP),
        "photo_grade": dict(LOCKED_GRADE),
        "visual_hierarchy": {
            "L1": "ALIRKEN KAZAN",
            "L2": "675.000 USD",
            "L3": "%35 LANSMAN AVANTAJI",
            "L4": "2+1 DAİRE",
            "L5": "PROJEYİ KEŞFET",
        },
        "relationships": {
            "headline_owns_unit": True,
            "price_owns_discount": True,
            "cta_is_editorial_inscription": True,
            "photo_is_hero": True,
        },
        "protected_architecture": dict(PROTECTED_ARCHITECTURE),
        "editable_groups": list(EDITABLE_GROUPS),
        "immutable_groups": list(IMMUTABLE_GROUPS),
        "scene_markup": scene_premium_commercial_r1(facts),
        "scene_type": "HTML_SVG",
        "revision_history": [],
        "parent_master_id": None,
        "child_revision_ids": [],
        "created_at": now,
        "approved_at": now,
        "lock_reason": "HUMAN_VISUAL_PASS_PHASE_5_4A_R1",
        "critic_may_not_reopen_art_direction": True,
    }


def append_revision(master: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
    blob = dict(master)
    history = list(blob.get("revision_history") or [])
    history.append(dict(revision))
    blob["revision_history"] = history
    children = list(blob.get("child_revision_ids") or [])
    rid = revision.get("revision_id")
    if rid and rid not in children:
        children.append(rid)
    blob["child_revision_ids"] = children
    return blob


def restore_parent_scene(master: dict[str, Any], revision_id: str | None = None) -> dict[str, Any]:
    """Reversible restore. Empty revision_id restores the approved root."""
    if not revision_id:
        return {
            "restored_master_id": master.get("master_id"),
            "scene_markup": master.get("scene_markup"),
            "semantic_content": dict(master.get("semantic_content") or {}),
            "revision_number": 1,
        }
    for rec in reversed(list(master.get("revision_history") or [])):
        if rec.get("revision_id") == revision_id:
            return {
                "restored_master_id": rec.get("parent_master_id") or master.get("master_id"),
                "scene_markup": rec.get("parent_scene_markup"),
                "semantic_content": dict(rec.get("parent_semantic_content") or {}),
                "revision_number": rec.get("revision_number"),
            }
    raise KeyError(f"unknown revision {revision_id}")
