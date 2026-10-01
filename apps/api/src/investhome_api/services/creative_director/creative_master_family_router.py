"""CreativeMasterFamilyRouterV1 — internal family selection.

Not a user-facing template picker. Ranks families against the project photograph
and campaign facts, then the adapter produces the creative.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from investhome_api.services.creative_director.creative_family_adapter import candidate_type_regions
from investhome_api.services.creative_director.graphic_field_director import _box_px, region_luma
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL


def _g(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_family_for_project(
    family: dict[str, Any],
    *,
    photo: Image.Image,
    protection: dict[str, Any],
    commercial_density: int,
) -> dict[str, Any]:
    family_id = str(family.get("family_id") or "")
    flex = dict(family.get("flexibility") or {})
    regions = candidate_type_regions(protection, photo.size)
    priority = list(flex.get("type_region_priority") or [])
    best_slot = None
    best_area = 0.0
    for name in priority:
        region = regions.get(name)
        if not region:
            continue
        area = float(region["w"]) * float(region["h"])
        spire = _box_px((protection.get("regions") or {}).get("SPIRE"), photo.size)
        px = _box_px(region, photo.size)
        if spire and px:
            overlap_w = max(0, min(px[2], spire[2]) - max(px[0], spire[0]))
            overlap_h = max(0, min(px[3], spire[3]) - max(px[1], spire[1]))
            if (overlap_w * overlap_h) / max(1, (px[2] - px[0]) * (px[3] - px[1])) > 0.28:
                continue
        if area > best_area:
            best_area = area
            best_slot = name
    luma = region_luma(photo, regions.get(best_slot) if best_slot else None)
    space = min(10.0, best_area * 28)
    # Temple is architectural daylight with a left-center spire.
    identity = {
        "EDITORIAL_DARK_FIELD": 8.5,
        "TYPE_IN_PLANE": 7.4,
        "SKY_EDITORIAL": 7.0,
        "MINIMAL_TOP_FIELD": 6.6,
    }.get(family_id, 5.0)
    commercial_fit = {
        "TYPE_IN_PLANE": 9.0,
        "EDITORIAL_DARK_FIELD": 8.2,
        "SKY_EDITORIAL": 6.4,
        "MINIMAL_TOP_FIELD": 5.8,
    }.get(family_id, 5.0)
    if commercial_density >= 5:
        commercial_fit = commercial_fit * 1.0
    contrast = 8.0
    if family_id in {"EDITORIAL_DARK_FIELD", "TYPE_IN_PLANE", "MINIMAL_TOP_FIELD"} and luma > 140:
        contrast = 6.5  # field/darken will create contrast
    if family_id == "SKY_EDITORIAL" and luma < 90:
        contrast = 5.5
    architecture = 8.8 if best_slot else 3.0
    if best_slot in {"top_center"}:
        architecture = 6.2
    total = 0.28 * space + 0.26 * identity + 0.22 * commercial_fit + 0.12 * contrast + 0.12 * architecture
    reasons = [
        f"available_type_slot={best_slot or 'none'} area={round(best_area, 3)}",
        f"identity_fit_for_architectural_photo={identity}",
        f"commercial_capacity_for_{commercial_density}_groups={commercial_fit}",
        f"region_luma={round(luma, 1)} contrast_plan={contrast}",
        "user_does_not_pick_this_family; router selects internally",
    ]
    if family_id == "EDITORIAL_DARK_FIELD":
        reasons.append("Right-column dark field can hold stacked display without covering the spire.")
    if family_id == "TYPE_IN_PLANE":
        reasons.append("Strongest commercial hierarchy; local plane darken instead of a constructed card.")
    if family_id == "SKY_EDITORIAL":
        reasons.append("Sky wash matches remaining upper negative space; left origin mirrors to the free side.")
    if family_id == "MINIMAL_TOP_FIELD":
        reasons.append("Architecture-dominant family; top field must yield to the spire via alternate slot.")
    return {
        "family_id": family_id,
        "score": round(total, 3),
        "slot": best_slot,
        "space": round(space, 3),
        "identity": identity,
        "commercial_fit": commercial_fit,
        "contrast": contrast,
        "architecture": architecture,
        "reasons": reasons,
    }


def rank_families(
    library: dict[str, Any],
    *,
    photo: Image.Image,
    protection: dict[str, Any],
    commercial_density: int = 6,
) -> dict[str, Any]:
    scored = [
        score_family_for_project(family, photo=photo, protection=protection, commercial_density=commercial_density)
        for family in list(library.get("families") or [])
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {
        "schema": "CreativeMasterFamilyRouterV1",
        "user_facing_picker": False,
        "ranking": scored,
        "selected": [item["family_id"] for item in scored[:3]],
        "reason": "Internal ranking for The Temple lansman on Day_004. Highest usable type area, architectural identity, and commercial capacity.",
    }


def request_router_rationale(
    photo: Image.Image,
    ranking: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Rank which design family fits this project photo. JSON only. Do not invent templates for a user picker."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Heuristic ranking already computed: "
                            + str([(r["family_id"], r["score"], r["slot"]) for r in ranking.get("ranking") or []])
                            + ". Confirm or mildly reorder. JSON: {order:[family_id], notes}."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(photo)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    order = [str(x) for x in list(parsed.get("order") or [])]
    if len(order) >= 3:
        ranking = dict(ranking)
        ranking["vision_order"] = order
        ranking["vision_notes"] = str(parsed.get("notes") or "")
        ranking["mode"] = "heuristic+vision"
    else:
        ranking = dict(ranking)
        ranking["mode"] = "heuristic"
    return ranking, calls
