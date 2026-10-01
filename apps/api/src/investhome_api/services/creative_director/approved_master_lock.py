"""ApprovedMasterLockV1 — human-approved master lock for Phase 5.5B-R2.

Natural-language revisions unlock only the semantic objects named by the request.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.approved_creative_master import HUMAN_APPROVED
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
)
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID

LOCKED_MASTER = "LOCKED_MASTER"
CANVAS = (1088, 1360)

APPROVED_R2_ASSET_ID = "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
APPROVED_R2_SPEC_ID = "544cfcd6-d7cd-410a-984a-d5cb8050252d"

LOCK_GROUPS = (
    "PHOTO_LOCK",
    "CROP_LOCK",
    "ARCHITECTURE_LOCK",
    "BRAND_LOCK",
    "HEADLINE_LOCK",
    "DESIGN_LANGUAGE_LOCK",
    "TYPOGRAPHY_LOCK",
    "COLOR_LOCK",
    "SPACING_LOCK",
    "CTA_LOCK",
    "UNRELATED_CONTENT_LOCK",
)

PRICE_EDIT_UNLOCK = ("price", "old_price", "savings", "savings_label", "currency")
VISUAL_REPLACE_UNLOCK = ("project_photo", "photo_crop", "photo_grade")

PRICE_INSTRUCTION = (
    "Fiyatı 438.750 USD yap.\n"
    "Eski fiyat 675.000 USD üzeri çizili kalsın.\n"
    "Kazancınız 236.250 USD bilgisini ekle.\n"
    "Başka hiçbir şeyi değiştirme."
)

VISUAL_REPLACE_INSTRUCTION = (
    "Bu proje görseli yerine The Temple’ın başka onaylı dış cephe görselini kullan.\n"
    "Başka hiçbir şeyi değiştirme."
)


def bounds_to_px(bounds: dict[str, Any], canvas: tuple[int, int] = CANVAS) -> tuple[int, int, int, int]:
    w, h = canvas
    x = float(bounds.get("x") or 0)
    y = float(bounds.get("y") or 0)
    bw = float(bounds.get("w") or 0)
    bh = float(bounds.get("h") or 0)
    return (int(round(x * w)), int(round(y * h)), int(round((x + bw) * w)), int(round((y + bh) * h)))


def object_px(spec: dict[str, Any], role: str) -> tuple[int, int, int, int]:
    item = dict(spec.get(role) or {})
    if isinstance(item.get("px"), (list, tuple)) and len(item["px"]) == 4:
        return tuple(int(v) for v in item["px"])
    bounds = item.get("bounds") if isinstance(item.get("bounds"), dict) else item
    return bounds_to_px(bounds or {})


def price_group_mutable_box(spec: dict[str, Any], canvas: tuple[int, int] = CANVAS) -> tuple[int, int, int, int]:
    """Navy strip between the locked discount unit and the locked logo."""
    w, h = canvas
    navy = object_px(spec, "navy_field")
    split_x = navy[2] if navy[2] > navy[0] else int(w * 0.344)
    label = object_px(spec, "discount_label")
    logo = object_px(spec, "project_logo")
    y0 = min(h - 8, max(0, label[3] + int(h * 0.016)))
    y1 = max(y0 + 8, logo[1] - int(h * 0.010))
    return (0, y0, split_x, y1)


def unlock_for_intent(intent: str) -> tuple[str, ...]:
    if intent == "PRICE_EDIT_ONLY":
        return PRICE_EDIT_UNLOCK
    if intent in {"VISUAL_REPLACE_ONLY", "VISUAL_REPLACE"}:
        return VISUAL_REPLACE_UNLOCK
    return ()


def build_approved_master_lock(
    *,
    spec: dict[str, Any],
    master_id: str,
    approved_at: str | None = None,
) -> dict[str, Any]:
    now = approved_at or _now()
    crop = dict((spec.get("source_asset_provenance") or {}).get("crop") or (spec.get("project_photo") or {}).get("crop") or {})
    navy = dict(spec.get("navy_field") or {})
    photo = dict(spec.get("project_photo") or {})
    facts = dict(REQUIRED_FACTS)
    lock_state = {name: True for name in LOCK_GROUPS}
    return {
        "schema": "ApprovedMasterLockV1",
        "master_id": master_id,
        "status": HUMAN_APPROVED,
        "lock_status": LOCKED_MASTER,
        "human_visual_status": "PASS",
        "project_id": TEMPLE_PROJECT_ID,
        "approved_asset_id": APPROVED_R2_ASSET_ID,
        "source_spec_id": APPROVED_R2_SPEC_ID,
        "visual_source_of_truth": APPROVED_R2_ASSET_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "canvas": {"w": CANVAS[0], "h": CANVAS[1]},
        "navy_photo_split": float((navy.get("bounds") or {}).get("w") or photo.get("bounds", {}).get("x") or 0.3438),
        "navy_field": navy,
        "photo_crop": crop,
        "project_photo": photo,
        "project_logo": dict(spec.get("project_logo") or {}),
        "headline": dict(spec.get("headline") or {}),
        "discount": dict(spec.get("discount") or {}),
        "discount_label": dict(spec.get("discount_label") or {}),
        "price": dict(spec.get("price") or {}),
        "currency": dict(spec.get("currency") or {}),
        "unit_type": dict(spec.get("unit_type") or {}),
        "cta": dict(spec.get("cta") or {}),
        "editorial_rules": dict(spec.get("editorial_rules") or {}),
        "typography": dict(spec.get("typography") or {"display": "Cormorant Garamond", "support": "Source Sans 3"}),
        "colors": {"navy": (navy.get("px") and None) or [39, 49, 60], "ivory": [244, 239, 228], "gold": [201, 168, 92]},
        "semantic_content": dict(facts),
        "commercial_hierarchy": ["headline", "discount", "price", "logo", "unit_type", "cta"],
        "relationships": dict((spec.get("visual_reconstruction_spec") or {}).get("relationships") or {}),
        "constraints": {
            "no_gpt_image": True,
            "no_redesign_on_revision": True,
            "change_only_what_was_requested": True,
            "real_day007_only": True,
            "real_temple_logo_only": True,
        },
        "revision_capabilities": {
            "PRICE_EDIT_ONLY": "PASS",
            "COPY_EDIT_ONLY": "PASS",
            "VISUAL_REPLACE_ONLY": "PASS",
        },
        "lock_groups": lock_state,
        "unlock_map": {
            "PRICE_EDIT_ONLY": list(PRICE_EDIT_UNLOCK),
            "VISUAL_REPLACE_ONLY": list(VISUAL_REPLACE_UNLOCK),
        },
        "price_group_mutable_box": list(price_group_mutable_box(spec)),
        "source_provenance": dict(spec.get("source_asset_provenance") or {}),
        "design_provenance": {
            "family": spec.get("family_id"),
            "craft": "r2",
            "concept": "Vertical Harmony",
            "candidate_spec_id": APPROVED_R2_SPEC_ID,
            "base_r1_asset_id": spec.get("base_r1_asset_id"),
        },
        "master_spec": spec,
        "parent_master_id": None,
        "child_revision_ids": [],
        "revision_history": [],
        "critic_may_not_reopen_art_direction": True,
        "created_at": now,
        "approved_at": now,
        "lock_reason": "HUMAN_VISUAL_PASS_PHASE_5_5B_R2",
    }


def append_child_revision(master: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
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


def restore_approved_master(master: dict[str, Any], revision_id: str | None = None) -> dict[str, Any]:
    if not revision_id:
        return {
            "restored_master_id": master.get("master_id"),
            "restored_asset_id": master.get("approved_asset_id"),
            "semantic_content": dict(master.get("semantic_content") or {}),
        }
    for rec in reversed(list(master.get("revision_history") or [])):
        if rec.get("revision_id") == revision_id:
            return {
                "restored_master_id": rec.get("parent_master_id") or master.get("master_id"),
                "restored_asset_id": rec.get("parent_asset_id") or master.get("approved_asset_id"),
                "semantic_content": dict(rec.get("parent_semantic_content") or {}),
            }
    raise KeyError(f"unknown revision {revision_id}")
