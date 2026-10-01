"""PhotoFamilyEligibilityEngineV1 — photo geometry must support the family before composition.

Eligibility comes before ranking. Incompatible photos are rejected, not forced.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageFilter, ImageStat

from investhome_api.services.creative_director.commercial_offer_composer import measure_production_copy
from investhome_api.services.creative_director.creative_contrast_engine import INK, IVORY, contrast_ratio, sample_background
from investhome_api.services.creative_director.family_composition_constraints import family_constraints
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map

ALL_MASTER_FAMILIES = (
    "EDITORIAL_DARK_FIELD",
    "SKY_EDITORIAL",
    "MINIMAL_TOP_FIELD",
    "TYPE_IN_PLANE",
)

DENSITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

# Identity-preserving minimum scale. Below this the family becomes a different design.
IDENTITY_SCALE_MIN = {
    "EDITORIAL_DARK_FIELD": 0.78,
    "SKY_EDITORIAL": 0.78,
    "MINIMAL_TOP_FIELD": 0.78,
    "TYPE_IN_PLANE": 0.78,
    "FULL_FRAME_ARCHITECTURAL_CAMPAIGN": 0.78,
}


def family_compatibility_rules() -> dict[str, Any]:
    return {
        "schema": "FamilyPhotoCompatibilityRulesV1",
        "families": {
            "EDITORIAL_DARK_FIELD": {
                "requires": [
                    "large contiguous edge field",
                    "or safely extendable dark/tonal region from a canvas edge",
                ],
                "compatible_traits": ["SIDE_NEGATIVE_SPACE", "GRAPHICAL_EDGE_FIELD"],
                "incompatible_traits": ["FULL_FRAME_ARCHITECTURE", "LOW_NEGATIVE_SPACE"],
                "min_contiguous_width": 0.28,
                "min_contiguous_height": 0.36,
                "min_extendable_area": 0.16,
                "min_plane_area": 0.14,
                "allows_created_navy_field": True,
                "created_field_must_not_cover_architecture": True,
                "needs_dark_or_extendable": True,
                "max_campaign_density": "HIGH",
                "identity_breakers": ["light_sky_as_primary_field", "type_on_facade", "tiny_display"],
            },
            "SKY_EDITORIAL": {
                "requires": ["sufficient uninterrupted sky negative space"],
                "compatible_traits": ["TOP_NEGATIVE_SPACE", "SIDE_NEGATIVE_SPACE", "OPEN_SKY"],
                "incompatible_traits": ["FULL_FRAME_ARCHITECTURE", "INTERRUPTED_SKY_ONLY"],
                "min_contiguous_width": 0.26,
                "min_contiguous_height": 0.32,
                "min_sky_area": 0.22,
                "allows_created_navy_field": False,
                "needs_light_sky": True,
                "max_campaign_density": "MEDIUM",
                "identity_breakers": ["navy_field_destroying_sky_identity", "type_on_facade"],
            },
            "TYPE_IN_PLANE": {
                "requires": ["a naturally dark low-detail photographic plane"],
                "compatible_traits": ["DARK_QUIET_PLANE"],
                "incompatible_traits": ["LIGHT_STONE_DOMINANT", "LOW_NEGATIVE_SPACE"],
                "min_contiguous_width": 0.30,
                "min_contiguous_height": 0.34,
                "min_plane_area": 0.14,
                "max_plane_luma": 92,
                "allows_created_navy_field": False,
                "max_campaign_density": "HIGH",
                "identity_breakers": ["invented_white_card", "mosaic_rectangles", "no_natural_plane"],
            },
            "MINIMAL_TOP_FIELD": {
                "requires": [
                    "enough top canvas for an architectural editorial band",
                    "building remaining in the lower field without being crushed",
                ],
                "compatible_traits": ["TOP_NEGATIVE_SPACE", "LOWER_ARCHITECTURE"],
                "incompatible_traits": ["FULL_FRAME_ARCHITECTURE", "LOW_NEGATIVE_SPACE"],
                "min_contiguous_width": 0.62,
                "min_contiguous_height": 0.28,
                "min_top_band": 0.28,
                "allows_created_navy_field": True,
                "created_field_zone": "top_band_only",
                "max_campaign_density": "MEDIUM",
                "identity_breakers": ["crushing_the_building", "side_navy_column"],
            },
            "FULL_FRAME_ARCHITECTURAL_CAMPAIGN": {
                "requires": [
                    "centered or near-centered architecture as the hero",
                    "architecture-clear perimeter territories for distributed groups",
                ],
                "compatible_traits": [
                    "FULL_FRAME_ARCHITECTURE",
                    "CENTERED_ARCHITECTURE",
                    "LOW_NEGATIVE_SPACE",
                    "INTERRUPTED_SKY",
                ],
                "incompatible_traits": [],
                "min_contiguous_width": 0.16,
                "min_contiguous_height": 0.12,
                "allows_created_navy_field": False,
                "allows_edge_tonal_integration": True,
                "created_field_must_not_cover_architecture": True,
                "max_campaign_density": "HIGH",
                "identity_breakers": ["header_bar", "footer_bar", "property_card", "four_boxes", "type_on_spire"],
                "multi_zone": True,
            },
        },
        "note": "Executable geometry rules. Attractiveness is not eligibility.",
    }


def campaign_density_profile(
    *,
    fonts: dict[str, Any],
    family: dict[str, Any],
    canvas: tuple[int, int] = CANVAS_4X5,
    scale: float = 1.0,
) -> dict[str, Any]:
    metrics = measure_production_copy(fonts=fonts, family=family, canvas=canvas, scale=scale)
    req = lockup_requirement(metrics, family, canvas)
    area = req["width"] * req["height"]
    groups = 6
    if area >= 0.16 or groups >= 6:
        level = "HIGH"
    elif area >= 0.10 or groups >= 4:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "schema": "CampaignDensityProfileV1",
        "level": level,
        "semantic_groups": groups,
        "copy_units": [
            metrics["headline"]["text"],
            metrics["unit_type"]["text"],
            metrics["price"]["text"],
            metrics["discount"]["text"],
            metrics["discount_label"]["text"],
            metrics["cta"]["text"],
        ],
        "measured_lockup": req,
        "metrics": {
            k: {"width": v.get("width"), "height": v.get("height"), "text": v.get("text")}
            for k, v in metrics.items()
            if isinstance(v, dict) and "width" in v
        },
        "note": "Temple commercial system is six designed groups, not a single headline.",
    }


def lockup_requirement(metrics: dict[str, Any], family: dict[str, Any], canvas: tuple[int, int]) -> dict[str, float]:
    w, h = canvas
    spacing = dict(family.get("spacing") or {})
    keys = ("headline_first", "headline_last", "unit_type", "price", "discount", "discount_label", "cta")
    stack_h = sum(int(metrics[k]["height"]) for k in keys if k in metrics)
    stack_h += int(
        h
        * (
            float(spacing.get("after_headline") or 0.02)
            + float(spacing.get("after_unit") or 0.016)
            + float(spacing.get("after_price") or 0.012)
            + float(spacing.get("after_offer") or 0.04)
            + 0.035
        )
    )
    stack_w = max(int(metrics[k]["width"]) for k in keys if k in metrics)
    logo_h = int(h * 0.055)
    logo_w = int(w * 0.16)
    return {
        "width": round(max(stack_w, logo_w) / w, 4),
        "height": round((stack_h + logo_h) / h, 4),
        "headline_height": round(
            (int(metrics["headline_first"]["height"]) + int(metrics["headline_last"]["height"])) / h, 4
        ),
        "commercial_height": round(
            (
                int(metrics["unit_type"]["height"])
                + int(metrics["price"]["height"])
                + int(metrics["discount"]["height"])
                + int(metrics["discount_label"]["height"])
            )
            / h,
            4,
        ),
        "cta_height": round(int(metrics["cta"]["height"]) / h, 4),
        "logo_width": round(logo_w / w, 4),
        "logo_height": round(logo_h / h, 4),
    }


def _pocket_area(pocket: dict[str, float] | None) -> float:
    if not isinstance(pocket, dict):
        return 0.0
    return max(0.0, float(pocket.get("w") or 0) * float(pocket.get("h") or 0))


def _best_pocket(occupancy: dict[str, Any]) -> tuple[str, dict[str, float] | None]:
    pockets = occupancy.get("pockets") or {}
    ranked = []
    for side in ("left", "right"):
        box = pockets.get(side)
        if isinstance(box, dict):
            ranked.append((float(box.get("w") or 0) * float(box.get("h") or 0), side, box))
    if not ranked:
        return "none", None
    ranked.sort(reverse=True)
    return ranked[0][1], ranked[0][2]


def _dark_quiet_plane(photo: Image.Image, occupancy: dict[str, Any]) -> dict[str, float]:
    gray = photo.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    gw, gh = 54, 68
    g = gray.resize((gw, gh), Image.Resampling.BOX)
    e = edges.resize((gw, gh), Image.Resampling.BOX)
    hmask = hard.resize((gw, gh), Image.Resampling.BOX) if isinstance(hard, Image.Image) else Image.new("L", (gw, gh), 0)
    gp, ep, hp = g.load(), e.load(), hmask.load()
    cells: list[tuple[int, int]] = []
    for y in range(gh):
        for x in range(gw):
            if int(hp[x, y]) > 80:
                continue
            if int(gp[x, y]) < 92 and int(ep[x, y]) < 32:
                cells.append((x, y))
    if not cells:
        return {"area": 0.0, "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0, "mean_luma": 255.0, "edge": False}
    cell_set = set(cells)
    seen: set[tuple[int, int]] = set()
    best: list[tuple[int, int]] = []
    for start in cells:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component: list[tuple[int, int]] = []
        while stack:
            cx, cy = stack.pop()
            component.append((cx, cy))
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if (nx, ny) in cell_set and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
        if len(component) > len(best):
            best = component
    xs = [c[0] for c in best]
    ys = [c[1] for c in best]
    x0 = min(xs) / gw
    x1 = (max(xs) + 1) / gw
    y0 = min(ys) / gh
    y1 = (max(ys) + 1) / gh
    area = round(len(best) / float(gw * gh), 4)
    return {
        "area": area,
        "x": round(x0, 4),
        "y": round(y0, 4),
        "width": round(x1 - x0, 4),
        "height": round(y1 - y0, 4),
        "mean_luma": round(sum(int(gp[x, y]) for x, y in best) / max(1, len(best)), 1),
        "edge": bool(x0 <= 0.12 or x1 >= 0.88),
    }


def classify_photo_composition(photo: Image.Image, occupancy: dict[str, Any]) -> dict[str, Any]:
    cov = occupancy.get("coverage") or {}
    hard = float(cov.get("hard_protected") or 0)
    sky = float(occupancy.get("sky_area") or 0)
    text = float(cov.get("text_safe") or 0)
    ext = float(cov.get("graphically_extendable") or 0)
    soft = float(cov.get("soft_occupied") or 0)
    centroid = float(occupancy.get("architecture_centroid_x") or 0.5)
    left = (occupancy.get("pockets") or {}).get("left") or {}
    right = (occupancy.get("pockets") or {}).get("right") or {}
    left_h = float(left.get("h") or 0)
    right_h = float(right.get("h") or 0)
    left_w = float(left.get("w") or 0)
    right_w = float(right.get("w") or 0)
    top_band = max(left_h, right_h)
    side_w = max(left_w, right_w)
    plane = _dark_quiet_plane(photo, occupancy)
    traits: list[str] = []
    if 0.38 <= centroid <= 0.62:
        traits.append("CENTERED_ARCHITECTURE")
    elif centroid < 0.38:
        traits.append("LEFT_HEAVY_ARCHITECTURE")
    else:
        traits.append("RIGHT_HEAVY_ARCHITECTURE")
    if hard >= 0.42 and sky < 0.20:
        traits.append("FULL_FRAME_ARCHITECTURE")
    if top_band >= 0.28 and sky >= 0.20:
        traits.append("TOP_NEGATIVE_SPACE")
    elif 0.14 <= top_band < 0.28:
        traits.append("SHALLOW_TOP_SKY")
        traits.append("INTERRUPTED_SKY")
    if side_w >= 0.28 and max(left_h, right_h) >= 0.34:
        traits.append("SIDE_NEGATIVE_SPACE")
    if ext >= 0.16 and (left_w >= 0.26 or right_w >= 0.26):
        traits.append("GRAPHICAL_EDGE_FIELD")
    if sky >= 0.28 and top_band >= 0.30:
        traits.append("OPEN_SKY")
    if text < 0.14 and sky < 0.22:
        traits.append("LOW_NEGATIVE_SPACE")
    if soft >= 0.10:
        traits.append("HIGH_VISUAL_NOISE")
    if plane["area"] >= 0.14 and plane["mean_luma"] < 92 and float(plane.get("height") or 0) >= 0.28:
        traits.append("DARK_QUIET_PLANE")
    else:
        traits.append("NO_DARK_QUIET_PLANE")
    if hard >= 0.28 and centroid >= 0.35 and centroid <= 0.65:
        traits.append("LOWER_ARCHITECTURE")
    gray = photo.convert("L")
    mean_luma = float(ImageStat.Stat(gray).mean[0])
    if mean_luma > 145:
        traits.append("LIGHT_STONE_DOMINANT")
    primary = "FULL_FRAME_ARCHITECTURE" if "FULL_FRAME_ARCHITECTURE" in traits else traits[0]
    if "LOW_NEGATIVE_SPACE" in traits:
        primary = "LOW_NEGATIVE_SPACE"
    if "SHALLOW_TOP_SKY" in traits and "CENTERED_ARCHITECTURE" in traits:
        primary = "CENTERED_ARCHITECTURE_SHALLOW_SKY"
    return {
        "schema": "ProjectPhotoCompositionClassV1",
        "primary_class": primary,
        "traits": traits,
        "measurements": {
            "hard_protected": hard,
            "sky_area": sky,
            "text_safe": text,
            "graphically_extendable": ext,
            "soft_occupied": soft,
            "architecture_centroid_x": centroid,
            "left_pocket": left,
            "right_pocket": right,
            "top_band_height": round(top_band, 4),
            "max_side_width": round(side_w, 4),
            "dark_quiet_plane": plane,
            "mean_luma": round(mean_luma, 1),
        },
    }


def _canvas_from_occupancy(occupancy: dict[str, Any], photo: Image.Image) -> tuple[int, int]:
    size = occupancy.get("size")
    if isinstance(size, list) and len(size) == 2:
        return int(size[0]), int(size[1])
    return photo.size


def _contrast_possible(photo: Image.Image, occupancy: dict[str, Any], family_id: str, pocket: dict[str, float] | None) -> tuple[bool, str]:
    w, h = photo.size
    if pocket:
        box = (
            int(float(pocket.get("x") or 0) * w),
            int(float(pocket.get("y") or 0) * h),
            int((float(pocket.get("x") or 0) + float(pocket.get("w") or 0.2)) * w),
            int((float(pocket.get("y") or 0) + min(0.12, float(pocket.get("h") or 0.12))) * h),
        )
    else:
        box = (int(w * 0.08), int(h * 0.04), int(w * 0.4), int(h * 0.16))
    bg = sample_background(photo, box)
    luma = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]
    rules = family_compatibility_rules()["families"][family_id]
    if family_id == "SKY_EDITORIAL":
        ok = contrast_ratio(INK, bg) >= 3.0 and luma >= 118
        return ok, "navy_on_light_sky" if ok else "sky_pocket_not_light_enough_for_ink"
    if family_id == "TYPE_IN_PLANE":
        ok = luma < 100 and contrast_ratio(IVORY, bg) >= 3.0
        return ok, "ivory_on_dark_plane" if ok else "no_dark_plane_for_ivory"
    if rules.get("allows_created_navy_field"):
        extendable = float((occupancy.get("coverage") or {}).get("graphically_extendable") or 0)
        if extendable >= 0.10:
            navy = (20, 24, 30)
            ok = contrast_ratio(IVORY, navy) >= 8.0
            return ok, "ivory_on_created_navy" if ok else "created_navy_contrast_fail"
        ok = luma < 110 and contrast_ratio(IVORY, bg) >= 3.0
        return ok, "ivory_on_existing_dark" if ok else "no_dark_or_extendable_field_for_ivory"
    ok = contrast_ratio(IVORY, bg) >= 3.0 or contrast_ratio(INK, bg) >= 3.0
    return ok, "family_approved_pair" if ok else "no_family_approved_contrast"


def evaluate_family_eligibility(
    *,
    photo: Image.Image,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    composition: dict[str, Any] | None = None,
    density: dict[str, Any] | None = None,
) -> dict[str, Any]:
    family_id = str(family.get("family_id") or "")
    rules = family_compatibility_rules()["families"][family_id]
    composition = composition or classify_photo_composition(photo, occupancy)
    scale = float((family.get("flexibility") or {}).get("scale_min") or IDENTITY_SCALE_MIN.get(family_id, 0.78))
    canvas = _canvas_from_occupancy(occupancy, photo)
    metrics = measure_production_copy(fonts=fonts, family=family, canvas=canvas, scale=scale)
    req = lockup_requirement(metrics, family, canvas)
    density = density or campaign_density_profile(fonts=fonts, family=family, canvas=canvas, scale=1.0)
    side, pocket = _best_pocket(occupancy)
    traits = list(composition.get("traits") or [])
    meas = dict(composition.get("measurements") or {})
    checks: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []

    pocket_w = float((pocket or {}).get("w") or 0)
    pocket_h = float((pocket or {}).get("h") or 0)
    field_source = "sky_pocket"
    if family_id == "EDITORIAL_DARK_FIELD":
        plane = dict(meas.get("dark_quiet_plane") or {})
        plane_w = float(plane.get("width") or 0)
        plane_h = float(plane.get("height") or 0)
        if (
            plane.get("edge")
            and float(plane.get("area") or 0) >= float(rules.get("min_plane_area") or 0.14)
            and plane_h >= float(rules.get("min_contiguous_height") or 0.36) * 0.85
            and plane_w >= float(rules.get("min_contiguous_width") or 0.28) * 0.85
        ):
            pocket_w, pocket_h = plane_w, plane_h
            field_source = "dark_quiet_plane"
            side = "edge"
        elif float((occupancy.get("coverage") or {}).get("graphically_extendable") or 0) >= float(
            rules.get("min_extendable_area") or 0.16
        ) and max(pocket_h, plane_h) >= req["height"] * 0.85:
            pocket_w = max(pocket_w, plane_w, float(rules.get("min_contiguous_width") or 0.28))
            pocket_h = max(pocket_h, plane_h)
            field_source = "graphically_extendable"
    min_w = float(rules.get("min_contiguous_width") or 0.26)
    min_h = float(rules.get("min_contiguous_height") or 0.32)
    if family_id == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN":
        from investhome_api.services.creative_director.full_frame_architectural_family import multi_zone_contiguous_fit

        mz = multi_zone_contiguous_fit(occupancy=occupancy, family=family, fonts=fonts, canvas=canvas, scale=scale)
        ok = mz.get("status") == "FIT"
        checks["required_negative_space"] = {
            "pass": ok,
            "multi_zone": True,
            "flex_mode": mz.get("flex_mode"),
            "zones": mz.get("zones"),
        }
        checks["commercial_space"] = {"pass": ok, "required_commercial_height": req["commercial_height"]}
        checks["logo_space"] = {"pass": ok, "required": req["logo_width"]}
        checks["cta_space"] = {"pass": ok}
        if not ok:
            reasons.append(str(mz.get("reason") or "perimeter territories cannot hold the HIGH-density groups"))
        contrast_ok, contrast_note = _contrast_possible(photo, occupancy, family_id, pocket)
        checks["contrast"] = {"pass": True, "note": "edge_tonal_integration"}
        checks["family_identity"] = {"pass": True, "reasons": []}
        checks["architecture_clearance"] = {"pass": ok}
        checks["content_density"] = {
            "pass": True,
            "campaign": str(density.get("level") or "HIGH"),
            "family_max": "HIGH",
        }
        if not ok:
            checks["architecture_clearance"] = {"pass": False}
        status = "ELIGIBLE" if ok else "NOT_ELIGIBLE"
        return {
            "schema": "FamilyEligibilityResultV1",
            "family_id": family_id,
            "status": status,
            "reasons": reasons,
            "checks": checks,
            "composition": composition,
            "density": density,
            "required_lockup": req,
            "flex_mode": mz.get("flex_mode"),
        }
    if family_id == "MINIMAL_TOP_FIELD":
        top_h = float(meas.get("top_band_height") or pocket_h)
        headline_ok = top_h >= float(rules.get("min_top_band") or 0.28) and top_h >= req["height"] * 0.92
        checks["required_negative_space"] = {
            "pass": headline_ok,
            "top_band_height": top_h,
            "required_height": req["height"],
        }
        if not headline_ok:
            reasons.append(f"top band {top_h:.3f} cannot hold lockup height {req['height']:.3f}")
    elif family_id == "TYPE_IN_PLANE":
        plane = dict(meas.get("dark_quiet_plane") or {})
        plane_ok = float(plane.get("area") or 0) >= float(rules.get("min_plane_area") or 0.14) and float(
            plane.get("width") or 0
        ) >= min_w * 0.85
        checks["required_negative_space"] = {"pass": plane_ok, "plane": plane, "required": req}
        if not plane_ok:
            reasons.append("no naturally dark low-detail plane large enough for the headline system")
    else:
        space_ok = pocket_w >= min_w * 0.9 and pocket_h >= min_h * 0.9 and pocket_h >= req["height"] * 0.92
        if family_id == "EDITORIAL_DARK_FIELD" and not space_ok:
            ext = float((occupancy.get("coverage") or {}).get("graphically_extendable") or 0)
            space_ok = ext >= float(rules.get("min_extendable_area") or 0.16) and pocket_h >= req["height"] * 0.92
        checks["required_negative_space"] = {
            "pass": space_ok,
            "pocket_side": side,
            "pocket_w": pocket_w,
            "pocket_h": pocket_h,
            "field_source": field_source,
            "required_w": req["width"],
            "required_h": req["height"],
        }
        if not space_ok:
            reasons.append(
                f"{side} pocket {pocket_w:.3f}x{pocket_h:.3f} cannot hold headline lockup {req['width']:.3f}x{req['height']:.3f}"
            )

    commercial_h = req["commercial_height"] + req["cta_height"]
    commercial_ok = pocket_h >= (req["headline_height"] + commercial_h) * 0.95 if pocket_h else False
    if family_id == "MINIMAL_TOP_FIELD":
        commercial_ok = float(meas.get("top_band_height") or 0) >= req["height"] * 0.95
    if family_id == "TYPE_IN_PLANE":
        plane = dict(meas.get("dark_quiet_plane") or {})
        commercial_ok = float(plane.get("height") or 0) >= req["height"] * 0.9
    checks["commercial_space"] = {"pass": commercial_ok, "required_commercial_height": commercial_h}
    if not commercial_ok:
        reasons.append("price + %35 + label + unit cannot fit without entering protected architecture")

    logo_ok = pocket_w >= req["logo_width"] + 0.04 and pocket_h >= req["logo_height"] + 0.02
    if family_id == "MINIMAL_TOP_FIELD":
        logo_ok = float(meas.get("top_band_height") or 0) >= req["logo_height"] + 0.04
    if family_id == "TYPE_IN_PLANE":
        plane = dict(meas.get("dark_quiet_plane") or {})
        logo_ok = float(plane.get("width") or 0) >= req["logo_width"] + 0.04
    checks["logo_space"] = {"pass": bool(logo_ok), "required": req["logo_width"]}
    if not logo_ok:
        reasons.append("real logo cannot sit with required clear space off architecture")

    cta_ok = bool(commercial_ok) and pocket_h >= req["cta_height"] + 0.04
    if family_id == "MINIMAL_TOP_FIELD":
        cta_ok = bool(commercial_ok)
    if "HIGH_VISUAL_NOISE" in traits and pocket_h < req["height"]:
        cta_ok = False
    checks["cta_space"] = {"pass": bool(cta_ok)}
    if not cta_ok:
        reasons.append("CTA has no readable quiet region outside architecture and street noise")

    contrast_ok, contrast_note = _contrast_possible(photo, occupancy, family_id, pocket)
    if family_id == "TYPE_IN_PLANE" and "DARK_QUIET_PLANE" not in traits:
        contrast_ok = False
        contrast_note = "no_dark_plane_for_ivory"
    checks["contrast"] = {"pass": contrast_ok, "note": contrast_note}
    if not contrast_ok:
        reasons.append(f"family-approved contrast unavailable ({contrast_note})")

    identity_ok = True
    identity_reasons: list[str] = []
    for breaker in rules.get("identity_breakers") or []:
        if breaker == "light_sky_as_primary_field" and family_id == "EDITORIAL_DARK_FIELD":
            if "OPEN_SKY" in traits and "GRAPHICAL_EDGE_FIELD" not in traits and pocket_h < min_h:
                identity_ok = False
                identity_reasons.append("would become a sky editorial, not a dark-field stacked display")
        if breaker == "navy_field_destroying_sky_identity" and family_id == "SKY_EDITORIAL":
            if pocket_h < min_h:
                identity_ok = False
                identity_reasons.append("fitting HIGH density would require a navy field that destroys sky identity")
        if breaker == "no_natural_plane" and family_id == "TYPE_IN_PLANE" and "DARK_QUIET_PLANE" not in traits:
            identity_ok = False
            identity_reasons.append("forcing type into sky or a card would be a different family")
        if breaker == "crushing_the_building" and family_id == "MINIMAL_TOP_FIELD":
            if float(meas.get("hard_protected") or 0) >= 0.38 and float(meas.get("top_band_height") or 0) < 0.28:
                identity_ok = False
                identity_reasons.append("creating a top band large enough would crush the building")
        if breaker == "tiny_display" and family_id == "EDITORIAL_DARK_FIELD" and pocket_h < req["height"] * 0.8:
            identity_ok = False
            identity_reasons.append("display would have to shrink below family identity scale")
    checks["family_identity"] = {"pass": identity_ok, "reasons": identity_reasons}
    reasons.extend(identity_reasons)

    arch_ok = "FULL_FRAME_ARCHITECTURE" not in traits or pocket_h >= req["height"]
    if not commercial_ok or not checks["required_negative_space"]["pass"]:
        arch_ok = False
    checks["architecture_clearance"] = {"pass": arch_ok}
    if not arch_ok:
        reasons.append("hard-protected architecture cannot remain clear of the required lockup")

    family_max = str(rules.get("max_campaign_density") or "HIGH")
    campaign_level = str(density.get("level") or "HIGH")
    density_ok = DENSITY_RANK[campaign_level] <= DENSITY_RANK[family_max]
    checks["content_density"] = {
        "pass": density_ok,
        "campaign": campaign_level,
        "family_max": family_max,
    }
    if not density_ok:
        reasons.append(f"campaign density {campaign_level} exceeds family capacity {family_max}")

    incompatible = [t for t in (rules.get("incompatible_traits") or []) if t in traits]
    if incompatible and checks["required_negative_space"]["pass"] is False:
        reasons.append("photo traits incompatible: " + ", ".join(incompatible))

    required_keys = (
        "required_negative_space",
        "commercial_space",
        "logo_space",
        "cta_space",
        "contrast",
        "family_identity",
        "architecture_clearance",
        "content_density",
    )
    passed = [k for k in required_keys if checks[k]["pass"]]
    failed = [k for k in required_keys if not checks[k]["pass"]]
    near = pocket_h >= req["height"] * 0.85 and pocket_w >= min_w * 0.85
    if family_id == "MINIMAL_TOP_FIELD":
        near = float(meas.get("top_band_height") or 0) >= req["height"] * 0.85
    if family_id == "TYPE_IN_PLANE":
        plane = dict(meas.get("dark_quiet_plane") or {})
        near = float(plane.get("height") or 0) >= req["height"] * 0.85
    if not failed:
        status = "ELIGIBLE"
    elif (
        near
        and identity_ok
        and density_ok
        and bool(rules.get("allows_created_navy_field"))
        and "family_identity" not in failed
        and "content_density" not in failed
        and len(failed) <= 3
    ):
        status = "CONDITIONALLY_ELIGIBLE"
        reasons.append("pocket within 15% of required size; family-approved field may complete contrast without covering architecture")
    else:
        status = "NOT_ELIGIBLE"
    if not identity_ok or not density_ok:
        status = "NOT_ELIGIBLE"
    if not checks["required_negative_space"]["pass"] and not near:
        status = "NOT_ELIGIBLE"
    if not commercial_ok and not near:
        status = "NOT_ELIGIBLE"

    return {
        "schema": "FamilyEligibilityResultV1",
        "family_id": family_id,
        "status": status,
        "checks": checks,
        "failed": failed,
        "passed": passed,
        "reasons": reasons,
        "primary_reason": reasons[0] if reasons else "all eligibility checks passed",
        "pocket": {"side": side, "box": pocket},
        "required_lockup": req,
        "scale_evaluated": scale,
        "traits_seen": traits,
        "incompatible_traits": incompatible,
    }


def occupancy_for_family(source: Image.Image, family: dict[str, Any]) -> tuple[Image.Image, dict[str, Any], dict[str, Any]]:
    family_id = str(family.get("family_id") or "")
    ys = {
        "EDITORIAL_DARK_FIELD": (0.24, 0.32, 0.40),
        "SKY_EDITORIAL": (0.20, 0.28, 0.36),
        "TYPE_IN_PLANE": (0.34, 0.44, 0.52),
        "MINIMAL_TOP_FIELD": (0.22, 0.30, 0.62),
        "FULL_FRAME_ARCHITECTURAL_CAMPAIGN": (0.38, 0.42, 0.46),
    }.get(family_id, (0.30, 0.42))
    best = None
    for y in ys:
        crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.55, float(y)))
        graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
        occ = build_photo_occupancy_map(graded)
        sky = float(occ.get("sky_area") or 0)
        text = float((occ.get("coverage") or {}).get("text_safe") or 0)
        score = sky * 2 + text
        if best is None or score > best[0]:
            best = (
                score,
                graded,
                {"centering": [0.55, float(y)], "source_crop": transform.get("source_crop"), "canvas": list(CANVAS_4X5)},
                occ,
            )
    assert best is not None
    return best[1], best[2], best[3]


def evaluate_all_families(
    *,
    source: Image.Image,
    families: list[dict[str, Any]],
    fonts: dict[str, Any],
) -> dict[str, Any]:
    probe, crop, occupancy = occupancy_for_family(source, {"family_id": "SKY_EDITORIAL"})
    composition = classify_photo_composition(probe, occupancy)
    density = campaign_density_profile(
        fonts=fonts,
        family=next((f for f in families if f.get("family_id") == "EDITORIAL_DARK_FIELD"), families[0]),
        canvas=CANVAS_4X5,
        scale=1.0,
    )
    results = []
    for family in families:
        graded, _crop, occ = occupancy_for_family(source, family)
        item = evaluate_family_eligibility(
            photo=graded,
            occupancy=occ,
            family=family,
            fonts=fonts,
            composition=classify_photo_composition(graded, occ),
            density=density,
        )
        item["crop"] = _crop
        results.append(item)
    eligible = [r for r in results if r["status"] == "ELIGIBLE"]
    conditional = [r for r in results if r["status"] == "CONDITIONALLY_ELIGIBLE"]
    none_fit = all(r["status"] == "NOT_ELIGIBLE" for r in results)
    missing = None
    if none_fit:
        missing = (
            f"{composition.get('primary_class')} / interrupted sky / low contiguous negative space / "
            f"{density.get('level')} commercial density"
        )
    suitability = "LOW"
    if eligible:
        suitability = "HIGH"
    elif conditional:
        suitability = "MEDIUM"
    elif float(composition.get("measurements", {}).get("sky_area") or 0) >= 0.18:
        suitability = "LOW"
    return {
        "schema": "PhotoFamilyEligibilityReportV1",
        "composition": composition,
        "density": density,
        "results": results,
        "eligible_family_ids": [r["family_id"] for r in eligible],
        "conditional_family_ids": [r["family_id"] for r in conditional],
        "eligible_count": len(eligible),
        "no_existing_family_fits": none_fit,
        "missing_family_requirement": missing,
        "day004_creative_suitability": suitability,
        "probe_crop": crop,
        "occupancy": occupancy,
        "foundation": probe,
    }


def score_image_suitability(
    *,
    photo: Image.Image,
    occupancy: dict[str, Any],
    family_results: list[dict[str, Any]],
    composition: dict[str, Any],
) -> dict[str, Any]:
    meas = dict(composition.get("measurements") or {})
    sky = float(meas.get("sky_area") or occupancy.get("sky_area") or 0)
    hard = float(meas.get("hard_protected") or 0)
    noise = float((occupancy.get("coverage") or {}).get("soft_occupied") or 0)
    eligible = sum(1 for r in family_results if r.get("status") == "ELIGIBLE")
    conditional = sum(1 for r in family_results if r.get("status") == "CONDITIONALLY_ELIGIBLE")
    pocket_h = float(meas.get("top_band_height") or 0)
    pocket_w = float(meas.get("max_side_width") or 0)
    contiguous = pocket_h * min(pocket_w, 0.46)
    score = round(
        eligible * 40.0
        + conditional * 12.0
        + contiguous * 22.0
        + sky * 4.0
        - hard * 8.0
        - noise * 6.0
        - (8.0 if eligible == 0 and conditional == 0 else 0.0),
        3,
    )
    if eligible:
        band = "HIGH"
    elif conditional:
        band = "MEDIUM"
    else:
        band = "LOW"
    commercial = "LOW"
    if eligible and pocket_h >= 0.32:
        commercial = "HIGH"
    elif eligible or pocket_h >= 0.24:
        commercial = "MEDIUM"
    return {
        "schema": "ProjectCreativeImageSuitabilityV1",
        "score": score,
        "band": band,
        "negative_space": round(sky, 4),
        "architecture_clearance_potential": round(1.0 - hard, 4),
        "visual_noise": round(noise, 4),
        "commercial_text_capacity": commercial,
        "compatible_master_families": [r["family_id"] for r in family_results if r.get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}],
        "premium_campaign_suitability": band,
        "composition": composition.get("primary_class"),
        "traits": composition.get("traits"),
    }


SKIP_EXTERIOR_TOKENS = (
    "logo",
    "ornek",
    "screenshot",
    "composed",
    "campaign",
    "interior",
    "ic_mekan",
    "living",
    "bedroom",
    "kitchen",
    "bathroom",
    "bath",
    "suite",
    "lobby",
    "amenity",
    "gf1",
    "gf2",
    "gf3",
    "master-family",
    "quality",
    "phase5",
    ".svg",
)
KEEP_EXTERIOR_TOKENS = ("exterior", "day_00", "day_0", "facade", "façade", "cephe")


def is_approved_exterior_filename(filename: str, content_type: str = "") -> bool:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if ctype and not ctype.startswith("image/"):
        return False
    if "svg" in name or ctype.endswith("svg+xml"):
        return False
    if any(tok in name for tok in SKIP_EXTERIOR_TOKENS):
        return False
    return any(tok in name for tok in KEEP_EXTERIOR_TOKENS)


def evaluate_image_for_creative_use(
    *,
    source: Image.Image,
    families: list[dict[str, Any]],
    fonts: dict[str, Any],
) -> dict[str, Any]:
    crop, _transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.55, 0.28))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = build_photo_occupancy_map(graded)
    composition = classify_photo_composition(graded, occupancy)
    density = campaign_density_profile(
        fonts=fonts,
        family=next((f for f in families if f.get("family_id") == "EDITORIAL_DARK_FIELD"), families[0]),
        canvas=CANVAS_4X5,
        scale=1.0,
    )
    results = [
        evaluate_family_eligibility(
            photo=graded,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            composition=composition,
            density=density,
        )
        for family in families
    ]
    suitability = score_image_suitability(
        photo=graded,
        occupancy=occupancy,
        family_results=results,
        composition=composition,
    )
    return {
        "composition": composition,
        "density_level": density.get("level"),
        "results": results,
        "suitability": suitability,
        "foundation": graded,
    }


def rank_eligible_families(
    library: dict[str, Any],
    eligibility: dict[str, Any],
    *,
    photo: Image.Image,
    protection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from investhome_api.services.creative_director.creative_master_family_router import rank_families

    allowed = list(eligibility.get("eligible_family_ids") or [])
    if not allowed:
        return {
            "schema": "EligibleFamilyRankingV1",
            "user_facing_picker": False,
            "eligibility_before_preference": True,
            "ranking": [],
            "selected": [],
            "note": "NO_EXISTING_FAMILY_FITS" if eligibility.get("no_existing_family_fits") else "NO_ELIGIBLE_FAMILIES_TO_RANK",
        }
    filtered = dict(library)
    filtered["families"] = [f for f in list(library.get("families") or []) if f.get("family_id") in allowed]
    ranked = rank_families(
        filtered,
        photo=photo,
        protection=protection or {"regions": {}},
        commercial_density=6,
    )
    ranked["schema"] = "EligibleFamilyRankingV1"
    ranked["eligibility_before_preference"] = True
    ranked["ineligible_excluded"] = [
        r.get("family_id")
        for r in list(eligibility.get("results") or [])
        if r.get("family_id") not in allowed
    ]
    return ranked


def analyze_creative_composition(photo: Image.Image, occupancy: dict[str, Any]) -> dict[str, Any]:
    composition = classify_photo_composition(photo, occupancy)
    meas = dict(composition.get("measurements") or {})
    plane = dict(meas.get("dark_quiet_plane") or occupancy.get("dark_plane") or {})
    regions = dict(occupancy.get("regions") or {})
    cov = dict(occupancy.get("coverage") or {})
    pockets = dict(occupancy.get("pockets") or {})
    headline_safe = plane if float(plane.get("area") or 0) >= 0.10 else (pockets.get("left") or pockets.get("right") or regions.get("text_safe"))
    return {
        "schema": "Day002CreativeCompositionAnalysisV1",
        "architecture_silhouette": {
            "hard_protected": cov.get("hard_protected"),
            "centroid_x": occupancy.get("architecture_centroid_x"),
            "bbox": regions.get("hard_protected"),
        },
        "dark_contiguous_plane": plane,
        "usable_negative_space": {
            "text_safe": cov.get("text_safe"),
            "sky_area": occupancy.get("sky_area"),
            "graphically_extendable": cov.get("graphically_extendable"),
            "top_band_height": meas.get("top_band_height"),
            "pockets": pockets,
        },
        "visual_center": [0.50, 0.42],
        "architectural_focal_point": {
            "x": occupancy.get("architecture_centroid_x"),
            "y": 0.46,
        },
        "logo_safe_region": regions.get("logo_safe"),
        "headline_safe_region": headline_safe,
        "commercial_safe_region": regions.get("commercial_safe") or headline_safe,
        "cta_safe_region": regions.get("cta_safe") or headline_safe,
        "contrast_map": {
            "plane_mean_luma": plane.get("mean_luma"),
            "photo_mean_luma": meas.get("mean_luma"),
            "ivory_on_plane": "PASS" if float(plane.get("mean_luma") or 255) < 100 else "FAIL",
        },
        "composition_class": composition,
        "note": "Source of truth is this occupancy analysis, not the 5.4H summary numbers.",
    }
