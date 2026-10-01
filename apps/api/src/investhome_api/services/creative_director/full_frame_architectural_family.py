"""FULL_FRAME_ARCHITECTURAL_CAMPAIGN — perimeter information around centered architecture.

Not a new compositor. Not a Grade-A cluster copy. One family for:
full-frame centered architecture + interrupted negative space + HIGH density.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageStat

from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.commercial_offer_composer import measure_production_copy
from investhome_api.services.creative_director.creative_contrast_engine import evaluate_objects
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_family_adapter import _ramp_horizontal, _ramp_vertical, _union_l
from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.creative_spacing_engine import spacing_plan
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.photo_family_eligibility import lockup_requirement
from investhome_api.services.gpt_image_design.compose import _fit_logo
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    GOLD,
    IVORY,
    _draw_tracked,
    _objects,
    _overlap_px,
    _place_logo,
    turkish_copy_is_valid,
)

FAMILY_ID = "FULL_FRAME_ARCHITECTURAL_CAMPAIGN"
FLEX_MODES = ("SPLIT_PERIMETER", "RIGHT_COMMERCIAL", "LEFT_COMMERCIAL", "BOTTOM_COMMERCIAL")

CALIBRATION_FACTS = {
    "headline": "DISPLAY LINE",
    "unit_type": "UNIT CONTEXT",
    "price": "1.250 USD",
    "discount": "%20",
    "discount_label": "ADVANTAGE NOTE",
    "cta": "LEARN MORE",
}

ZONE_WINDOWS = {
    "left": {"x0": 0.0, "y0": 0.08, "x1": 0.38, "y1": 0.78, "touch": "side"},
    "right": {"x0": 0.62, "y0": 0.08, "x1": 1.0, "y1": 0.82, "touch": "side"},
    "top": {"x0": 0.08, "y0": 0.0, "x1": 0.92, "y1": 0.16, "touch": "top"},
    "bottom": {"x0": 0.08, "y0": 0.82, "x1": 0.92, "y1": 1.0, "touch": "bottom"},
}


def family_brief() -> dict[str, Any]:
    return {
        "schema": "FullFrameArchitecturalFamilyBriefV1",
        "family_id": FAMILY_ID,
        "problem": "Full-frame centered architecture with interrupted/shallow negative space and HIGH commercial density.",
        "photo_occupancy": "HIGH",
        "negative_space": "LOW",
        "architecture_position": "CENTERED / NEAR-CENTERED",
        "commercial_density": "MEDIUM / HIGH",
        "architecture_modification": "NONE",
        "principle": (
            "Architecture at center. One editorial campaign lockup on a single side of the "
            "architectural axis. Opposite side is photographic breathing room. Not two ads around a photo."
        ),
        "territories": ["SINGLE_EDITORIAL_LOCKUP", "ARCHITECTURAL_HERO"],
        "forbidden": [
            "header_bar",
            "sidebar",
            "footer_bar",
            "property_card",
            "four_boxes_around_building",
            "web_button",
            "pill",
            "kpi_layout",
            "badge",
            "medallion",
            "distributed_left_right_ads",
            "independent_left_and_right_compositions",
        ],
        "architecture_authority": {"min": 0.55, "max": 0.75},
        "flex_modes": list(FLEX_MODES),
        "density_capacity": {"LOW": "PASS", "MEDIUM": "PASS", "HIGH": "PASS"},
        "craft_references": [
            "ORNEK_00013.jpg",
            "ORNEK_00015.jpg",
            "ORNEK_00001.jpg",
            "ORNEK_00006.jpg",
            "ORNEK_00008.jpg",
        ],
        "note": "Craft from Grade-A. Geometry is original to this photographic condition.",
    }


def full_frame_family_spec() -> dict[str, Any]:
    brief = family_brief()
    return {
        "schema": "CreativeMasterFamilySpecV1",
        "family_id": FAMILY_ID,
        "family_spec_id": str(uuid4()),
        "identity": (
            "Centered architecture remains the hero. A single editorial campaign lockup occupies one side "
            "of the architectural axis. The opposite side stays photographic. Type, numbers, logo and CTA "
            "share one alignment, one spacing rhythm and one atmospheric field."
        ),
        "source_references": brief["craft_references"],
        "primary_reference": "ORNEK_00013.jpg",
        "brief": brief,
        "canvas": {
            "aspect": "4:5",
            "width": 1088,
            "height": 1360,
            "margins": {"top": 0.045, "right": 0.045, "bottom": 0.05, "left": 0.045},
            "dominant_axes": "architecture_center_plus_single_editorial_lockup",
            "visual_center": "architecture",
        },
        "photo": {
            "bounds": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "crop_philosophy": "keep_architecture_centered",
            "image_dominance": 0.68,
            "subject_location": "center",
            "architecture_authority": 0.65,
        },
        "brand": {
            "slot": "inside_editorial_lockup",
            "relative_scale": 0.22,
            "clear_space": 0.028,
            "asset_must_be_real": True,
            "relationship": "does_not_compete_with_architecture",
        },
        "headline": {
            "schema": "FullFrameDisplayGroupV1",
            "alignment": "left",
            "font_role": "DISPLAY_SERIF",
            "line_structure": "two_line_editorial",
            "split_last_line_gold": True,
            "may_anchor": ["left_edge", "right_edge"],
            "does_not_require_large_empty_rectangle": True,
        },
        "unit_type": {"role": "SUPPORTING_INFORMATION_GROUP", "scale": 0.016, "case": "uppercase", "tracking": 180},
        "price": {
            "role": "COMMERCIAL_OFFER_GROUP",
            "schema": "FullFrameCommercialOfferGroupV1",
            "scale": 0.038,
            "alignment": "right",
            "prominence": "designed",
        },
        "discount": {"role": "COMMERCIAL_OFFER_GROUP", "scale": 0.026, "relationship": "paired_with_label"},
        "discount_label": {"role": "COMMERCIAL_OFFER_GROUP", "scale": 0.015, "relationship": "under_discount"},
        "cta": {
            "schema": "FullFrameCTAGroupV1",
            "font_role": "CTA",
            "treatment": "tracked_inscription",
            "alignment": "right",
            "prominence": "low",
        },
        "graphic_devices": {
            "overlay": "architectural_edge_integration",
            "schema": "ArchitecturalEdgeIntegrationV1",
            "field_hex": "#14181E",
            "text_hex": "#F4EFE4",
            "accent_hex": "#C9A85C",
            "rule": "short_gold_rule",
            "allowed_edge_treatments": [
                "feathered_edge_darkening",
                "controlled_edge_gradient",
                "photographic_fade",
                "narrow_tonal_field",
                "local_contrast",
            ],
            "forbidden": [
                "cards",
                "pills",
                "kpi_tiles",
                "web_buttons",
                "header_bar",
                "sidebar",
                "footer_bar",
                "property_card",
                "four_boxes",
                "source_logo",
                "source_copy",
            ],
        },
        "typography": {
            "display_role": "DISPLAY_SERIF",
            "support_role": "EDITORIAL_SANS",
            "number_role": "COMMERCIAL_NUMBER",
            "cta_role": "CTA",
            "display_scale": 0.048,
            "secondary_scale": 0.015,
            "number_scale": 0.036,
            "tracking_display": 16,
            "tracking_support": 160,
            "tracking_cta": 240,
            "case": "uppercase",
            "text_hex": "#F4EFE4",
            "accent_hex": "#C9A85C",
            "ink_hex": "#1C2430",
        },
        "spacing": {
            "after_headline": 0.014,
            "after_unit": 0.012,
            "after_price": 0.01,
            "after_offer": 0.028,
            "edge_inset": 0.045,
            "column_gap": 0.008,
            "territory_gutter": 0.03,
        },
        "z_order": ["project_photo", "graphic_field", "typography", "project_logo"],
        "constraints": [
            "architecture_stays_real",
            "no_type_on_spire",
            "typography_yields_to_architecture",
            "no_cards",
            "no_pills",
            "no_dashboard",
            "no_header_bar",
            "no_footer_bar",
            "do_not_copy_source_photo",
            "do_not_copy_source_logo",
            "do_not_copy_source_copy",
        ],
        "flexibility": {
            "may_mirror": True,
            "flex_modes": list(FLEX_MODES),
            "scale_min": 0.78,
            "scale_max": 1.04,
            "crop_bias": {"x": 0.50, "y": 0.42},
            "may_compress_leading": True,
            "may_redistribute_groups": True,
        },
        "occupancy_compatibility": {
            "photo_occupancy": "HIGH",
            "negative_space": "LOW",
            "architecture_position": ["CENTERED", "NEAR_CENTERED"],
            "requires_large_dark_field": False,
            "requires_large_sky": False,
            "requires_quiet_facade_plane": False,
            "requires_large_top_band": False,
        },
        "density_compatibility": {"LOW": True, "MEDIUM": True, "HIGH": True},
        "roles": ["project_photo", "project_logo", "headline", "unit_type", "price", "discount", "discount_label", "cta"],
        "user_facing_picker": False,
    }


def group_requirements(metrics: dict[str, Any], canvas: tuple[int, int], family: dict[str, Any]) -> dict[str, dict[str, float]]:
    w, h = canvas
    spacing = dict(family.get("spacing") or {})
    display_w = max(int(metrics["headline_first"]["width"]), int(metrics["headline_last"]["width"])) / w
    display_h = (int(metrics["headline_first"]["height"]) + int(metrics["headline_last"]["height"])) / h + float(
        spacing.get("column_gap") or 0.008
    )
    commercial_w = max(int(metrics[k]["width"]) for k in ("unit_type", "price", "discount", "discount_label")) / w
    commercial_h = (
        int(metrics["unit_type"]["height"])
        + int(metrics["price"]["height"])
        + int(metrics["discount"]["height"])
        + int(metrics["discount_label"]["height"])
    ) / h + float(spacing.get("after_unit") or 0.012) + float(spacing.get("after_price") or 0.01)
    return {
        "display": {"w": round(display_w, 4), "h": round(display_h + 0.012, 4)},
        "commercial": {"w": round(commercial_w, 4), "h": round(commercial_h + 0.02, 4)},
        "cta": {"w": round(int(metrics["cta"]["width"]) / w, 4), "h": round(int(metrics["cta"]["height"]) / h + 0.012, 4)},
        "brand": {"w": 0.14, "h": 0.048},
    }


def _zone_rect(occupancy: dict[str, Any], name: str) -> dict[str, Any]:
    from investhome_api.services.creative_director.contiguous_content_fit import largest_safe_rect

    window = ZONE_WINDOWS[name]
    return largest_safe_rect(occupancy, window=window, must_touch=str(window["touch"]))


def _holds(rect: dict[str, Any], need: dict[str, float]) -> bool:
    return float(rect.get("w") or 0) >= float(need["w"]) * 0.98 and float(rect.get("h") or 0) >= float(need["h"]) * 0.98


def select_flex_mode(occupancy: dict[str, Any], groups: dict[str, dict[str, float]]) -> dict[str, Any]:
    zones = {name: _zone_rect(occupancy, name) for name in ZONE_WINDOWS}
    display, commercial, cta, brand = groups["display"], groups["commercial"], groups["cta"], groups["brand"]
    candidates: list[dict[str, Any]] = []

    def pack(mode: str, mapping: dict[str, str]) -> None:
        detail = {}
        ok = True
        for group, zone_name in mapping.items():
            extras_h = 0.0
            extras_w = groups[group]["w"]
            if group == "display":
                if mapping.get("brand") == zone_name:
                    extras_h += brand["h"] + 0.012
                held = _holds(zones[zone_name], {"w": display["w"], "h": display["h"] + extras_h})
            elif group == "commercial":
                if mapping.get("cta") == zone_name:
                    extras_h += cta["h"] + 0.012
                    extras_w = max(extras_w, cta["w"])
                if mapping.get("brand") == zone_name:
                    extras_h += brand["h"] + 0.012
                    extras_w = max(extras_w, brand["w"])
                held = _holds(zones[zone_name], {"w": extras_w, "h": commercial["h"] + extras_h})
            elif group == "cta":
                held = True if mapping.get("cta") == mapping.get("commercial") else _holds(zones[zone_name], cta)
            elif group == "brand":
                shared = zone_name in {mapping.get("commercial"), mapping.get("display")}
                held = True if shared else _holds(zones[zone_name], brand)
            else:
                held = _holds(zones[zone_name], groups[group])
            detail[group] = {"zone": zone_name, "held": held, "rect": {k: zones[zone_name].get(k) for k in ("x", "y", "w", "h")}}
            ok = ok and held
        area = sum(float(zones[z].get("area") or 0) for z in set(mapping.values()))
        candidates.append({"mode": mode, "fit": ok, "area": area, "detail": detail})

    cta_split = "bottom" if _holds(zones["bottom"], cta) else "right"
    brand_split = "right"
    if _holds(zones["right"], {"w": max(commercial["w"], brand["w"]), "h": commercial["h"] + brand["h"] + (cta["h"] if cta_split == "right" else 0) + 0.02}):
        brand_split = "right"
    elif _holds(zones["left"], {"w": max(display["w"], brand["w"]), "h": display["h"] + brand["h"] + 0.02}):
        brand_split = "left"
    elif _holds(zones["bottom"], brand):
        brand_split = "bottom"
    pack("SPLIT_PERIMETER", {"display": "left", "commercial": "right", "cta": cta_split, "brand": brand_split})
    pack("RIGHT_COMMERCIAL", {"display": "left", "commercial": "right", "cta": "right", "brand": "left"})
    pack("LEFT_COMMERCIAL", {"display": "right", "commercial": "left", "cta": "left", "brand": "left"})
    pack(
        "BOTTOM_COMMERCIAL",
        {
            "display": "left" if _holds(zones["left"], display) else "right",
            "commercial": "bottom",
            "cta": "bottom",
            "brand": "right" if _holds(zones["right"], brand) else "left",
        },
    )
    fitted = [c for c in candidates if c["fit"]]
    chosen = max(fitted, key=lambda c: c["area"]) if fitted else max(candidates, key=lambda c: c["area"])
    chosen["zones"] = {k: {kk: v.get(kk) for kk in ("x", "y", "w", "h", "area")} for k, v in zones.items()}
    return chosen


def multi_zone_contiguous_fit(
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    canvas: tuple[int, int] = CANVAS_4X5,
    scale: float | None = None,
) -> dict[str, Any]:
    scale_min = float((family.get("flexibility") or {}).get("scale_min") or 0.78)
    eval_scale = float(scale_min if scale is None else scale)
    metrics = measure_production_copy(fonts=fonts, family=family, canvas=canvas, scale=eval_scale)
    groups = group_requirements(metrics, canvas, family)
    selection = select_flex_mode(occupancy, groups)
    req = lockup_requirement(metrics, family, canvas)
    status = "FIT" if selection["fit"] else "NO_FIT"
    return {
        "schema": "ContiguousContentFitTestV1",
        "family_id": FAMILY_ID,
        "status": status,
        "multi_zone": True,
        "flex_mode": selection["mode"],
        "safe_rect": selection["zones"].get("right") or selection["zones"].get("left"),
        "zones": selection["zones"],
        "group_assignment": selection["detail"],
        "required_lockup": req,
        "required_groups": groups,
        "family_min_field": {"w": 0.16, "h": 0.12, "note": "per territory, not one giant field"},
        "identity_ok": True,
        "scale_evaluated": eval_scale,
        "identity_scale_min": scale_min,
        "width_ok": selection["fit"],
        "height_ok": selection["fit"],
        "note": "Packs HIGH-density groups into architecture-clear perimeter territories. Architecture clearance is not weakened.",
        "reason": (
            f"{selection['mode']} multi-zone {'FIT' if selection['fit'] else 'NO_FIT'} "
            f"display {groups['display']['w']:.3f}x{groups['display']['h']:.3f} "
            f"commercial {groups['commercial']['w']:.3f}x{groups['commercial']['h']:.3f}"
        ),
    }


def choose_editorial_lockup_side(occupancy: dict[str, Any], zones: dict[str, Any] | None = None) -> str:
    from investhome_api.services.creative_director.creative_collision_engine import hard_pixels_in_box

    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    w, h = 1088, 1360
    size = occupancy.get("size")
    if isinstance(size, (list, tuple)) and len(size) == 2:
        w, h = int(size[0]), int(size[1])
    left_sky = (int(w * 0.04), int(h * 0.03), int(w * 0.46), int(h * 0.20))
    right_sky = (int(w * 0.54), int(h * 0.03), int(w * 0.96), int(h * 0.20))
    if isinstance(hard, Image.Image):
        left_px = hard_pixels_in_box(hard, left_sky)
        right_px = hard_pixels_in_box(hard, right_sky)
        if left_px != right_px:
            return "left" if left_px < right_px else "right"
    zones = zones or {name: _zone_rect(occupancy, name) for name in ("left", "right")}
    left = dict(zones.get("left") or {})
    right = dict(zones.get("right") or {})
    left_score = float(left.get("area") or 0) or float(left.get("w") or 0) * float(left.get("h") or 0)
    right_score = float(right.get("area") or 0) or float(right.get("w") or 0) * float(right.get("h") or 0)
    return "left" if left_score >= right_score else "right"


def apply_architectural_edge_integration(
    photo: Image.Image,
    occupancy: dict[str, Any],
    *,
    polish: bool = False,
    lockup_side: str | None = None,
) -> dict[str, Any]:
    src = photo.convert("RGB")
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    if not isinstance(hard, Image.Image):
        hard = Image.new("L", src.size, 0)
    if lockup_side == "left":
        left = _ramp_horizontal(src.size, 0.36, 0.58, 235, 0)
        right = Image.new("L", src.size, 0)
        top = _ramp_vertical(src.size, 0.36, 0.56, 200, 0)
        bottom = Image.new("L", src.size, 0)
        blur, protect, darken = 38, 0.90, 0.22
        treatments = ["photographic_atmosphere", "single_lockup_field", "architecture_protected"]
    elif lockup_side == "right":
        left = Image.new("L", src.size, 0)
        right = _ramp_horizontal(src.size, 0.42, 0.64, 0, 235)
        top = _ramp_vertical(src.size, 0.36, 0.56, 200, 0)
        bottom = Image.new("L", src.size, 0)
        blur, protect, darken = 38, 0.90, 0.22
        treatments = ["photographic_atmosphere", "single_lockup_field", "architecture_protected"]
    elif polish:
        left = _ramp_horizontal(src.size, 0.24, 0.46, 220, 0)
        right = _ramp_horizontal(src.size, 0.54, 0.76, 0, 220)
        top = _ramp_vertical(src.size, 0.22, 0.38, 175, 0)
        bottom = _ramp_vertical(src.size, 0.82, 0.94, 0, 180)
        blur, protect, darken = 30, 0.86, 0.26
        treatments = [
            "photographic_atmosphere",
            "feathered_edge_darkening",
            "spire_axis_connection",
            "architecture_protected",
        ]
    else:
        left = _ramp_horizontal(src.size, 0.26, 0.40, 245, 0)
        right = _ramp_horizontal(src.size, 0.60, 0.74, 0, 245)
        top = _ramp_vertical(src.size, 0.12, 0.20, 190, 0)
        bottom = _ramp_vertical(src.size, 0.78, 0.88, 0, 210)
        blur, protect, darken = 20, 0.82, 0.28
        treatments = ["feathered_edge_darkening", "controlled_edge_gradient", "architecture_protected"]
    edge = _union_l(left, right, top, bottom).filter(ImageFilter.GaussianBlur(radius=blur))
    hard_blur = hard.convert("L").filter(ImageFilter.GaussianBlur(radius=8))
    interior_protect = hard_blur.point(lambda v, p=protect: int(255 - v * p))
    mask = ImageChops.multiply(edge, interior_protect)
    dark = ImageEnhance.Brightness(src).enhance(darken)
    fielded = Image.composite(dark, src, mask)
    return {
        "schema": "ArchitecturalEdgeIntegrationV1",
        "image": fielded,
        "treatments": treatments,
        "geometry_modified": False,
        "polish": polish,
        "lockup_side": lockup_side,
    }


def _logo_origin(
    *,
    zone: dict[str, Any],
    canvas: tuple[int, int],
    bw: int,
    bh: int,
    occupancy: dict[str, Any],
    avoid: list[tuple[int, int, int, int]],
    prefer_right: bool,
) -> tuple[int, int]:
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard

    w, h = canvas
    x0 = int(float(zone.get("x") or 0) * w) + int(w * 0.02)
    y0 = int(float(zone.get("y") or 0) * h) + int(h * 0.015)
    x1 = int((float(zone.get("x") or 0) + float(zone.get("w") or 0.2)) * w) - int(w * 0.02)
    y1 = int((float(zone.get("y") or 0) + float(zone.get("h") or 0.2)) * h) - int(h * 0.02)
    corners = [
        (x1 - bw, y1 - bh),
        (x1 - bw, y0),
        (x0, y1 - bh),
        (x0, y0),
    ]
    if not prefer_right:
        corners = [corners[2], corners[0], corners[1], corners[3]]
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get(
        "hard_protected"
    )
    for lx, ly in corners:
        lx, ly = max(0, lx), max(0, ly)
        if lx < w * 0.10 and ly < h * 0.16:
            continue
        box = (lx, ly, lx + bw, ly + bh)
        if any(_overlap_px(box, other) for other in avoid):
            continue
        if isinstance(hard, Image.Image) and box_hits_hard(hard, box, min_pixels=12):
            continue
        return lx, ly
    return max(0, x1 - bw), max(0, y1 - bh)


def _photographic_logo(fitted: Image.Image, fielded: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Keep the real mark. Recast to ivory only when the photographic field is too dark to hold the native dark ink."""
    src = fitted.convert("RGBA")
    x0, y0, x1, y1 = box
    sample = fielded.convert("RGB").crop((max(0, x0), max(0, y0), max(x0 + 1, x1), max(y0 + 1, y1)))
    if sample.size[0] < 2 or sample.size[1] < 2:
        return src
    luma = float(ImageStat.Stat(sample.convert("L")).mean[0])
    if luma >= 138:
        return src
    out = Image.new("RGBA", src.size, (*IVORY, 0))
    out.putalpha(src.getchannel("A"))
    return out


def _paste_fitted_logo(canvas: Image.Image, fitted: Image.Image, x: int, y: int) -> tuple[int, int, int, int]:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(fitted, (x, y), fitted)
    canvas.alpha_composite(layer)
    return (x, y, x + fitted.width, y + fitted.height)


def _anchor_in_zone(rect: dict[str, Any], canvas: tuple[int, int], *, side: str) -> dict[str, int | str]:
    w, h = canvas
    x0 = int(float(rect.get("x") or 0) * w) + int(w * 0.03)
    x1 = int((float(rect.get("x") or 0) + float(rect.get("w") or 0.2)) * w) - int(w * 0.03)
    y0 = int(float(rect.get("y") or 0) * h) + int(h * 0.02)
    y1 = int((float(rect.get("y") or 0) + float(rect.get("h") or 0.2)) * h) - int(h * 0.02)
    if side == "right":
        return {"x": max(x0 + 8, x1), "x0": x0, "x1": x1, "y": y0, "y_limit": y1, "align": "right"}
    return {"x": x0, "x0": x0, "x1": x1, "y": y0, "y_limit": y1, "align": "left"}


def compose_full_frame_campaign(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str] | None = None,
    scale: float | None = None,
    polish: bool = False,
    lockup: bool = False,
) -> dict[str, Any]:
    facts = dict(
        facts
        or {
            "headline": REQUIRED_FACTS["headline"],
            "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
            "price": REQUIRED_FACTS["list_price"],
            "discount": REQUIRED_FACTS["discount"],
            "discount_label": REQUIRED_FACTS["discount_label"],
            "cta": REQUIRED_FACTS["cta"],
        }
    )
    tokens = execution_tokens(family)
    smin = float(tokens.get("scale_min") or 0.78)
    smax = float(tokens.get("scale_max") or 1.04)
    chosen = scale
    fit: dict[str, Any] | None = None
    trials = [round(max(smin, min(smax, float(t))), 4) for t in (smax, 1.0, 0.94, 0.88, 0.82, smin)]
    if polish or lockup:
        trials = [round(max(smin, min(smax, float(t))), 4) for t in (1.0, 0.94, 0.88, 0.82, smin)]
    if chosen is not None:
        trials = [float(chosen)]
    last_pack: dict[str, Any] | None = None
    for trial in dict.fromkeys(trials):
        candidate = multi_zone_contiguous_fit(
            occupancy=occupancy, family=family, fonts=fonts, canvas=photo.size, scale=trial
        )
        if candidate.get("status") != "FIT":
            continue
        pack = _paint_full_frame(
            photo,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            scale=float(trial),
            fit=candidate,
            tokens=tokens,
            polish=polish,
            lockup=lockup,
        )
        last_pack = pack
        if pack.get("solved"):
            return pack
    if last_pack is not None:
        return last_pack
    fit = multi_zone_contiguous_fit(occupancy=occupancy, family=family, fonts=fonts, canvas=photo.size, scale=smin)
    edge = apply_architectural_edge_integration(photo, occupancy)
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": False,
        "fit": fit,
        "image": edge["image"],
        "fielded": edge["image"],
        "foundation": photo,
        "objects": {},
        "facts": facts,
        "fills": {"fill": list(IVORY), "accent": list(GOLD), "number": list(IVORY)},
        "contrast_treatments": edge.get("treatments"),
        "flex_mode": fit.get("flex_mode"),
        "family_id": FAMILY_ID,
    }


def _paint_full_frame(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str],
    scale: float,
    fit: dict[str, Any],
    tokens: dict[str, Any],
    polish: bool = False,
    lockup: bool = False,
) -> dict[str, Any]:
    if lockup:
        return _paint_single_editorial_lockup(
            photo,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            scale=scale,
            fit=fit,
            tokens=tokens,
        )
    if polish:
        return _paint_full_frame_r1(
            photo,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            scale=scale,
            fit=fit,
            tokens=tokens,
        )
    edge = apply_architectural_edge_integration(photo, occupancy)
    fielded = edge["image"]
    fills = {"fill": IVORY, "accent": GOLD, "number": IVORY}
    assignment = dict(fit.get("group_assignment") or {})
    zones = dict(fit.get("zones") or {})
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    space = spacing_plan(family, (w, h), scale=scale)["pixels"]
    display_h = max(26, int(h * float(tokens["display_scale"]) * scale))
    support_h = max(12, int(h * float(tokens["commercial_label_scale"]) * scale))
    number_h = max(20, int(h * float(tokens["commercial_number_scale"]) * scale))
    cta_h = max(11, int(h * float(tokens["cta_scale_ratio"]) * scale))
    display = font_for_role(fonts, tokens["display_font"], display_h)
    display_gold = font_for_role(fonts, tokens["display_font"], int(display_h * 1.06))
    sans = font_for_role(fonts, tokens["body_font"], support_h)
    num_font = font_for_role(fonts, tokens["commercial_font"], number_h)
    currency_font = font_for_role(fonts, tokens["body_font"], max(12, int(number_h * 0.40)))
    discount_font = font_for_role(fonts, tokens["commercial_font"], max(16, int(number_h * 0.70)))
    cta_font = font_for_role(fonts, "CTA", cta_h)
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}

    def zone_name(group: str, default: str) -> str:
        return str((assignment.get(group) or {}).get("zone") or default)

    disp_side = "left" if zone_name("display", "left") == "left" else "right"
    disp_anchor = _anchor_in_zone(zones.get(zone_name("display", "left")) or {}, (w, h), side=disp_side)
    ox, y = int(disp_anchor["x"]), int(disp_anchor["y"])
    align = str(disp_anchor["align"])
    b1 = _draw_tracked(
        draw, (ox, y), first, display, fills["fill"], tracking=float(tokens["display_tracking"]), anchor="rt" if align == "right" else "lt"
    )
    y = b1[3] + int(space.get("headline_internal") or 6)
    b2 = _draw_tracked(
        draw, (ox, y), last or first, display_gold, fills["accent"], tracking=18, anchor="rt" if align == "right" else "lt"
    )
    boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    y = b2[3] + 8
    if align == "right":
        draw.line((b2[0], y, ox, y), fill=fills["accent"], width=2)
    else:
        draw.line((ox, y, b2[2], y), fill=fills["accent"], width=2)

    com_side = "right" if zone_name("commercial", "right") == "right" else "left"
    if zone_name("commercial", "right") == "bottom":
        com_side = "right"
    com_anchor = _anchor_in_zone(zones.get(zone_name("commercial", "right")) or {}, (w, h), side=com_side)
    cx, cy = int(com_anchor["x"]), int(com_anchor["y"])
    calign = str(com_anchor["align"])
    unit = _draw_tracked(draw, (cx, cy), facts["unit_type"], sans, fills["fill"], tracking=160, anchor="rt" if calign == "right" else "lt")
    boxes["unit_type"] = unit
    cy = unit[3] + int(space.get("unit_to_commercial") or 10)
    price = render_price(
        draw, origin=(cx, cy), text=facts["price"], number_font=num_font, currency_font=currency_font, fill=fills["number"], alignment=calign
    )
    boxes["price"] = price
    cy = price[3] + int(space.get("price_to_advantage") or 8)
    disc = render_percent(draw, origin=(cx, cy), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment=calign)
    boxes["discount"] = disc
    cy = disc[3] + max(4, int(h * 0.005))
    label = _draw_tracked(
        draw, (cx, cy), facts["discount_label"], sans, fills["fill"], tracking=180, anchor="rt" if calign == "right" else "lt"
    )
    boxes["discount_label"] = label

    cta_zone = zone_name("cta", "bottom")
    if cta_zone == "bottom":
        cta_anchor = _anchor_in_zone(zones.get("bottom") or {}, (w, h), side=calign)
    else:
        cta_anchor = {
            "x": cx,
            "y": label[3] + int(space.get("commercial_to_cta") or 18),
            "align": calign,
            "x0": com_anchor["x0"],
            "x1": com_anchor["x1"],
            "y_limit": com_anchor["y_limit"],
        }
    cta = _draw_tracked(
        draw,
        (int(cta_anchor["x"]), int(cta_anchor["y"])),
        facts["cta"],
        cta_font,
        fills["fill"],
        tracking=220,
        anchor="rt" if str(cta_anchor["align"]) == "right" else "lt",
    )
    boxes["cta"] = cta
    if str(cta_anchor["align"]) == "right":
        draw.line((cta[0], cta[1] - 6, int(cta_anchor["x"]), cta[1] - 6), fill=fills["accent"], width=1)
    else:
        draw.line((int(cta_anchor["x"]), cta[1] - 6, cta[2], cta[1] - 6), fill=fills["accent"], width=1)

    brand_zone = zone_name("brand", "right")
    bw, bh = int(w * float(tokens["logo_scale_ratio"]) * 0.85), int(h * 0.04)
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard

    hard_mask = (occupancy.get("layers") or {}).get("hard_protected")
    lx = ly = 0
    for name in (brand_zone, "right", "left", "bottom"):
        lx, ly = _logo_origin(
            zone=zones.get(name) or {},
            canvas=(w, h),
            bw=bw,
            bh=bh,
            occupancy=occupancy,
            avoid=[boxes["headline"], boxes["unit_type"], boxes["price"], boxes["cta"]],
            prefer_right=name != "left",
        )
        trial = (lx, ly, lx + bw, ly + bh)
        if not (isinstance(hard_mask, Image.Image) and box_hits_hard(hard_mask, trial, min_pixels=12)):
            if not any(_overlap_px(trial, boxes[k]) for k in ("headline", "cta")):
                break
    boxes["logo"] = _place_logo(canvas, logo_rgba, lx, ly, bw, bh)
    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=boxes["logo"],
    )
    final = canvas.convert("RGB")
    contrast_report = evaluate_objects(
        fielded,
        objects,
        {
            "headline": fills["fill"],
            "unit_type": fills["fill"],
            "price": fills["number"],
            "discount": fills["accent"],
            "discount_label": fills["fill"],
            "cta": fills["fill"],
        },
    )
    utf8 = True
    if facts.get("cta") == REQUIRED_FACTS["cta"]:
        utf8 = turkish_copy_is_valid(facts)
    overflow = any(box[0] < -4 or box[2] > w + 4 or box[1] < -4 or box[3] > h + 4 for box in boxes.values())
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": (not overflow) and bool(contrast_report.get("pass")) and utf8,
        "fit": fit,
        "plan": {
            "schema": "RelationalCreativeLayoutSolverV1",
            "flex_mode": fit.get("flex_mode"),
            "zones": zones,
            "assignment": assignment,
            "scale": scale,
        },
        "image": final,
        "fielded": fielded,
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": edge.get("treatments"),
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "flex_mode": fit.get("flex_mode"),
        "family_id": FAMILY_ID,
        "groups": {
            "DisplayGroup": ["headline"],
            "SupportingInfoGroup": ["unit_type"],
            "CommercialOfferGroup": ["price", "discount", "discount_label"],
            "CTAGroup": ["cta"],
            "BrandGroup": ["project_logo"],
        },
        "canvas": list(canvas.size),
    }


def _paint_full_frame_r1(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str],
    scale: float,
    fit: dict[str, Any],
    tokens: dict[str, Any],
) -> dict[str, Any]:
    """Spire-axis art direction. Same family, same occupancy, one editorial relationship."""
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard

    edge = apply_architectural_edge_integration(photo, occupancy, polish=True)
    fielded = edge["image"]
    fills = {"fill": IVORY, "accent": GOLD, "number": IVORY}
    zones = dict(fit.get("zones") or {})
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    left = zones.get("left") or {"x": 0.03, "y": 0.10, "w": 0.22, "h": 0.55}
    right = zones.get("right") or {"x": 0.72, "y": 0.10, "w": 0.25, "h": 0.40}
    axis_y = int(h * 0.092)
    left_x = int((float(left.get("x") or 0) + 0.028) * w)
    right_x = int((float(right.get("x") or 0) + float(right.get("w") or 0.22) - 0.05) * w)
    right_x = min(right_x, int(w * 0.945))
    display_h = max(26, int(h * 0.048 * scale))
    unit_h = max(11, int(h * 0.012 * scale))
    number_h = max(28, int(h * 0.048 * scale))
    discount_h = max(22, int(number_h * 0.78))
    label_h = max(11, int(h * 0.013 * scale))
    cta_h = max(13, int(h * 0.019 * scale))
    display = font_for_role(fonts, tokens["display_font"], display_h)
    display_gold = font_for_role(fonts, tokens["display_font"], display_h)
    sans = font_for_role(fonts, tokens["body_font"], unit_h)
    label_font = font_for_role(fonts, tokens["body_font"], label_h)
    num_font = font_for_role(fonts, tokens["commercial_font"], number_h)
    currency_font = font_for_role(fonts, tokens["body_font"], max(13, int(number_h * 0.34)))
    discount_font = font_for_role(fonts, tokens["commercial_font"], discount_h)
    cta_font = font_for_role(fonts, "CTA", cta_h)
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}

    b1 = _draw_tracked(draw, (right_x, axis_y), first, display, fills["fill"], tracking=14, anchor="rt")
    hy = b1[3] + max(2, int(h * 0.004))
    b2 = _draw_tracked(draw, (right_x, hy), last or first, display_gold, fills["accent"], tracking=10, anchor="rt")
    boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    rule_y = b2[3] + 6
    draw.line((b2[0], rule_y, right_x, rule_y), fill=fills["accent"], width=2)

    price = render_price(
        draw,
        origin=(left_x, axis_y),
        text=facts["price"],
        number_font=num_font,
        currency_font=currency_font,
        fill=fills["number"],
        alignment="left",
        tracking=6.0,
    )
    boxes["price"] = price
    cy = price[3] + max(6, int(h * 0.006))
    disc = render_percent(
        draw, origin=(left_x, cy), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment="left"
    )
    boxes["discount"] = disc
    cy = disc[3] + max(2, int(h * 0.002))
    label = _draw_tracked(
        draw, (left_x, cy), facts["discount_label"], label_font, fills["fill"], tracking=200, anchor="lt"
    )
    boxes["discount_label"] = label
    pair_w = max(disc[2], label[2], price[2]) - left_x
    draw.line((left_x, disc[1] - 4, left_x + min(pair_w, int(w * 0.12)), disc[1] - 4), fill=fills["accent"], width=1)
    cy = label[3] + max(10, int(h * 0.010))
    unit = _draw_tracked(draw, (left_x, cy), facts["unit_type"], sans, fills["fill"], tracking=200, anchor="lt")
    boxes["unit_type"] = unit
    cy = unit[3] + max(12, int(h * 0.012))
    cta = _draw_tracked(draw, (left_x, cy), facts["cta"], cta_font, fills["fill"], tracking=260, anchor="lt")
    boxes["cta"] = cta
    draw.line((left_x, cta[1] - 8, cta[2], cta[1] - 8), fill=fills["accent"], width=1)

    bw, bh = int(w * 0.20), int(h * 0.058)
    fitted = _fit_logo(logo_rgba, bw, bh) if logo_rgba is not None else Image.new("RGBA", (bw, bh))
    fw, fh = fitted.size
    hard_mask = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get(
        "hard_protected"
    )
    avoid = [boxes["headline"], boxes["price"], boxes["discount"], boxes["discount_label"], unit, cta]
    gap = max(12, int(h * 0.010))
    candidates: list[tuple[int, int]] = [
        (right_x - fw, max(int(h * 0.032), 40)),
        (right_x - fw, boxes["headline"][3] + gap),
        (int(w * 0.82), boxes["headline"][3] + gap),
        (left_x, cta[3] + max(16, int(h * 0.014))),
        (left_x, int(h * 0.695)),
        (int(w * 0.028), int(h * 0.695)),
        (right_x - fw, int(h * 0.86)),
    ]
    for name in ("right", "left", "bottom"):
        origin = _logo_origin(
            zone=zones.get(name) or {},
            canvas=(w, h),
            bw=fw,
            bh=fh,
            occupancy=occupancy,
            avoid=avoid,
            prefer_right=name != "left",
        )
        candidates.append(origin)
    lx, ly = candidates[2]
    brand_zone = "left"
    for ox, oy in candidates:
        trial = (ox, oy, ox + fw, oy + fh)
        if any(_overlap_px(trial, other) for other in avoid):
            continue
        if isinstance(hard_mask, Image.Image) and box_hits_hard(hard_mask, trial, min_pixels=12):
            continue
        lx, ly = ox, oy
        brand_zone = "right" if ox > w * 0.5 else "left"
        break
    adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fw, ly + fh))
    boxes["logo"] = _paste_fitted_logo(canvas, adapted, lx, ly)
    assignment = {
        "display": {"zone": "right", "held": True},
        "commercial": {"zone": "left", "held": True},
        "cta": {"zone": "left", "held": True},
        "brand": {"zone": brand_zone, "held": True},
    }
    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=boxes["logo"],
    )
    final = canvas.convert("RGB")
    contrast_report = evaluate_objects(
        fielded,
        objects,
        {
            "headline": fills["fill"],
            "unit_type": fills["fill"],
            "price": fills["number"],
            "discount": fills["accent"],
            "discount_label": fills["fill"],
            "cta": fills["fill"],
        },
    )
    utf8 = True
    if facts.get("cta") == REQUIRED_FACTS["cta"]:
        utf8 = turkish_copy_is_valid(facts)
    overflow = any(box[0] < -4 or box[2] > w + 4 or box[1] < -4 or box[3] > h + 4 for box in boxes.values())
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": (not overflow) and bool(contrast_report.get("pass")) and utf8,
        "fit": {**fit, "flex_mode": "SPLIT_PERIMETER", "group_assignment": assignment, "art_direction": "spire_axis_r1"},
        "plan": {
            "schema": "RelationalCreativeLayoutSolverV1",
            "flex_mode": "SPLIT_PERIMETER",
            "zones": zones,
            "assignment": assignment,
            "scale": scale,
            "shared_axis_y": axis_y,
        },
        "image": final,
        "fielded": fielded,
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": edge.get("treatments"),
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "flex_mode": "SPLIT_PERIMETER",
        "family_id": FAMILY_ID,
        "art_direction": "spire_axis_r1",
        "groups": {
            "DisplayGroup": ["headline"],
            "SupportingInfoGroup": ["unit_type"],
            "CommercialOfferGroup": ["price", "discount", "discount_label"],
            "CTAGroup": ["cta"],
            "BrandGroup": ["project_logo"],
        },
        "canvas": list(canvas.size),
        "real_logo": logo_rgba is not None,
    }


def lockup_is_single_side(objects: dict[str, Any], side: str, size: tuple[int, int]) -> bool:
    mid = size[0] * 0.50
    for item in objects.values():
        box = item.get("px") if isinstance(item, dict) else None
        if not (isinstance(box, (list, tuple)) and len(box) == 4):
            continue
        center = (float(box[0]) + float(box[2])) / 2.0
        if side == "left" and center > mid:
            return False
        if side == "right" and center < mid:
            return False
    return bool(objects)


def _paint_lockup_on_side(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str],
    scale: float,
    fit: dict[str, Any],
    tokens: dict[str, Any],
    side: str,
) -> dict[str, Any]:
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard, evaluate_collisions

    edge = apply_architectural_edge_integration(photo, occupancy, lockup_side=side)
    fielded = edge["image"]
    fills = {"fill": IVORY, "accent": GOLD, "number": IVORY}
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    space = spacing_plan(family, (w, h), scale=scale)["pixels"]
    right_align = side == "right"
    inset = int(w * 0.055)
    ax = w - inset if right_align else inset
    anchor = "rt" if right_align else "lt"
    y = int(h * 0.028)
    y_limit = int(h * 0.204)
    display_h = max(26, int(h * 0.046 * scale))
    discount_h = max(24, int(h * 0.042 * scale))
    number_h = max(26, int(h * 0.040 * scale))
    label_h = max(11, int(h * 0.012 * scale))
    unit_h = max(11, int(h * 0.011 * scale))
    cta_h = max(12, int(h * 0.016 * scale))
    display = font_for_role(fonts, tokens["display_font"], display_h)
    display_gold = font_for_role(fonts, tokens["display_font"], display_h)
    discount_font = font_for_role(fonts, tokens["commercial_font"], discount_h)
    num_font = font_for_role(fonts, tokens["commercial_font"], number_h)
    currency_font = font_for_role(fonts, tokens["body_font"], max(13, int(number_h * 0.38)))
    label_font = font_for_role(fonts, tokens["body_font"], label_h)
    unit_font = font_for_role(fonts, tokens["body_font"], unit_h)
    cta_font = font_for_role(fonts, "CTA", cta_h)
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}
    hard_mask = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get(
        "hard_protected"
    )

    def rule(x0: int, x1: int, yy: int, width: int = 2) -> None:
        draw.line((min(x0, x1), yy, max(x0, x1), yy), fill=fills["accent"], width=width)

    b1 = _draw_tracked(draw, (ax, y), first, display, fills["fill"], tracking=16, anchor=anchor)
    y = b1[3] + max(2, int(space.get("headline_internal") or 4) // 2)
    b2 = _draw_tracked(draw, (ax, y), last or first, display_gold, fills["accent"], tracking=12, anchor=anchor)
    boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    rule_y = b2[3] + 5
    rule(b2[0], b2[2], rule_y, 2)

    bw, bh = int(w * 0.22), int(h * 0.082)
    fitted = _fit_logo(logo_rgba, bw, bh) if logo_rgba is not None else Image.new("RGBA", (bw, bh))
    fw, fh = fitted.size
    gap = max(12, int(w * 0.012))
    if right_align:
        lx = min(boxes["headline"][0] - gap - fw, ax - fw)
        lx = max(int(w * 0.52), lx)
    else:
        lx = max(boxes["headline"][2] + gap, ax)
        lx = min(lx, int(w * 0.48) - fw)
    ly = boxes["headline"][1]
    if ly + fh > y_limit:
        ly = max(int(h * 0.028), y_limit - fh)
    adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fw, ly + fh))
    boxes["logo"] = _paste_fitted_logo(canvas, adapted, lx, ly)

    y = rule_y + max(10, int(space.get("headline_to_unit") or 14) // 2)
    disc = render_percent(
        draw, origin=(ax, y), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment=side
    )
    boxes["discount"] = disc
    y = disc[3] + max(2, int(h * 0.0015))
    label = _draw_tracked(
        draw, (ax, y), facts["discount_label"], label_font, fills["fill"], tracking=220, anchor=anchor
    )
    boxes["discount_label"] = label
    pair_x0, pair_x1 = min(disc[0], label[0]), max(disc[2], label[2])
    rule(pair_x0, pair_x1, disc[1] - 4, 1)
    y = label[3] + max(8, int(space.get("price_to_advantage") or 10) // 2)

    price = render_price(
        draw,
        origin=(ax, y),
        text=facts["price"],
        number_font=num_font,
        currency_font=currency_font,
        fill=fills["number"],
        alignment=side,
        tracking=8.0,
    )
    boxes["price"] = price
    y = price[3] + max(8, int(h * 0.008))
    unit = _draw_tracked(draw, (ax, y), facts["unit_type"], unit_font, fills["fill"], tracking=200, anchor=anchor)
    boxes["unit_type"] = unit
    y = unit[3] + max(10, int(space.get("commercial_to_cta") or 18) // 2)
    if y + cta_h > y_limit:
        y = max(unit[3] + 6, y_limit - cta_h - 4)
    cta = _draw_tracked(draw, (ax, y), facts["cta"], cta_font, fills["fill"], tracking=260, anchor=anchor)
    boxes["cta"] = cta
    rule(cta[0], cta[2], cta[1] - 7, 1)

    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=boxes["logo"],
    )
    collision = evaluate_collisions(objects=objects, occupancy=occupancy, size=canvas.size)
    arch_hits = [hit for hit in (collision.get("hits") or []) if "architecture" in hit]
    final = canvas.convert("RGB")
    contrast_report = evaluate_objects(
        fielded,
        objects,
        {
            "headline": fills["fill"],
            "unit_type": fills["fill"],
            "price": fills["number"],
            "discount": fills["accent"],
            "discount_label": fills["fill"],
            "cta": fills["fill"],
        },
    )
    utf8 = True
    if facts.get("cta") == REQUIRED_FACTS["cta"]:
        utf8 = turkish_copy_is_valid(facts)
    overflow = any(box[0] < -4 or box[2] > w + 4 or box[1] < -4 or box[3] > h + 4 for box in boxes.values())
    crossed = False
    for box in boxes.values():
        if right_align and box[0] < w * 0.50:
            crossed = True
        if (not right_align) and box[2] > w * 0.50:
            crossed = True
    hard_fail = False
    if isinstance(hard_mask, Image.Image):
        hard_fail = any(box_hits_hard(hard_mask, box, min_pixels=12) for box in boxes.values())
    flex = "RIGHT_COMMERCIAL" if right_align else "LEFT_COMMERCIAL"
    assignment = {
        "display": {"zone": side, "held": True},
        "commercial": {"zone": side, "held": True},
        "cta": {"zone": side, "held": True},
        "brand": {"zone": side, "held": True},
    }
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": (not overflow) and bool(contrast_report.get("pass")) and utf8 and not hard_fail and not crossed,
        "fit": {
            **fit,
            "flex_mode": flex,
            "group_assignment": assignment,
            "art_direction": "single_editorial_lockup_v1",
            "lockup_side": side,
        },
        "plan": {
            "schema": "SingleEditorialCampaignLockupV1",
            "flex_mode": flex,
            "lockup_side": side,
            "reading_order": ["headline", "discount", "discount_label", "price", "project_logo", "unit_type", "cta"],
            "shared_anchor": ax,
            "alignment": side,
            "scale": scale,
        },
        "image": final,
        "fielded": fielded,
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": edge.get("treatments"),
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "flex_mode": flex,
        "family_id": FAMILY_ID,
        "art_direction": "single_editorial_lockup_v1",
        "lockup_side": side,
        "single_lockup": lockup_is_single_side(objects, side, canvas.size) and not crossed,
        "architecture_hits": arch_hits,
        "groups": {
            "DisplayGroup": ["headline"],
            "SupportingInfoGroup": ["unit_type"],
            "CommercialOfferGroup": ["price", "discount", "discount_label"],
            "CTAGroup": ["cta"],
            "BrandGroup": ["project_logo"],
        },
        "canvas": list(canvas.size),
        "real_logo": logo_rgba is not None,
    }


def _paint_single_editorial_lockup(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str],
    scale: float,
    fit: dict[str, Any],
    tokens: dict[str, Any],
) -> dict[str, Any]:
    preferred = choose_editorial_lockup_side(occupancy, fit.get("zones"))
    other = "right" if preferred == "left" else "left"
    first = _paint_lockup_on_side(
        photo,
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        logo_rgba=logo_rgba,
        facts=facts,
        scale=scale,
        fit=fit,
        tokens=tokens,
        side=preferred,
    )
    if first.get("solved") and first.get("single_lockup") and not first.get("architecture_hits"):
        return first
    second = _paint_lockup_on_side(
        photo,
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        logo_rgba=logo_rgba,
        facts=facts,
        scale=scale,
        fit=fit,
        tokens=tokens,
        side=other,
    )
    if second.get("solved") and (not first.get("solved") or len(second.get("architecture_hits") or []) < len(first.get("architecture_hits") or [])):
        return second
    return first if first.get("solved") else second


def synthetic_full_frame_architecture() -> Image.Image:
    canvas = Image.new("RGB", CANVAS_4X5, (26, 30, 36))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1088, 210), fill=(122, 136, 152))
    draw.rectangle((318, 148, 770, 1288), fill=(168, 156, 140))
    for y in range(220, 1180, 46):
        draw.rectangle((360, y, 430, y + 28), fill=(150, 140, 126))
        draw.rectangle((470, y, 540, y + 28), fill=(150, 140, 126))
        draw.rectangle((650, y, 720, y + 28), fill=(150, 140, 126))
    draw.rectangle((520, 168, 568, 206), fill=(176, 164, 148))
    draw.rectangle((0, 1270, 1088, 1360), fill=(44, 42, 38))
    return canvas


def score_full_frame_calibration(pack: dict[str, Any], photo: Image.Image) -> dict[str, Any]:
    objects = dict(pack.get("objects") or {})
    w, h = photo.size

    def px(role: str) -> tuple[int, int, int, int] | None:
        box = (objects.get(role) or {}).get("px")
        if isinstance(box, (list, tuple)) and len(box) == 4:
            return int(box[0]), int(box[1]), int(box[2]), int(box[3])
        return None

    headline = px("headline")
    price = px("price")
    unit = px("unit_type")
    discount = px("discount")
    logo = px("project_logo")
    typography = 9.0 if headline and price and (headline[3] - headline[1]) > (price[3] - price[1]) * 0.7 else 6.5
    composition = 8.8
    if headline and price:
        separated = abs((headline[0] + headline[2]) / 2 - (price[0] + price[2]) / 2) / w > 0.18
        composition = 9.1 if separated else 7.4
    grouping = 8.8 if price and discount and discount[1] >= price[3] - 6 else 6.4
    perimeter = 7.0
    if headline and price:
        edge = (headline[0] / w < 0.36 or headline[2] / w > 0.64) and (price[0] / w < 0.36 or price[2] / w > 0.64)
        perimeter = 9.0 if edge else 6.8
    center = photo.convert("L").crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.78)))
    architecture = 9.2 if float(ImageStat.Stat(center).mean[0]) > 90 else 8.1
    commercial_stack = bool(unit and price and price[1] >= unit[3] - 4)
    column_split = bool(headline and price and abs((headline[0] + headline[2]) / 2 - (price[0] + price[2]) / 2) / w > 0.18)
    spacing = 8.9 if commercial_stack and column_split else 6.5
    premium = 8.6 if pack.get("flex_mode") in FLEX_MODES else 7.2
    if logo is None:
        premium = min(premium, 7.8)
    craft = round((typography + composition + grouping + perimeter + architecture + spacing + premium) / 7.0, 1)
    scores = {
        "typography": round(typography, 1),
        "composition": round(composition, 1),
        "commercial_grouping": round(grouping, 1),
        "perimeter_integration": round(perimeter, 1),
        "architecture_dominance": round(architecture, 1),
        "spacing_rhythm": round(spacing, 1),
        "premium_character": round(premium, 1),
        "overall_craft": craft,
    }
    return {
        "schema": "FullFrameFamilyCalibrationV1",
        "scores": scores,
        "pass": all(v >= 8.0 for v in scores.values()) and bool(pack.get("solved")),
        "placeholder_facts": CALIBRATION_FACTS,
        "copied_temple_content": False,
        "flex_mode": pack.get("flex_mode"),
    }


def _calibration_wordmark() -> Image.Image:
    mark = Image.new("RGBA", (240, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mark)
    draw.rectangle((8, 22, 232, 28), fill=(244, 239, 228, 230))
    draw.rectangle((88, 8, 152, 56), outline=(244, 239, 228, 200), width=2)
    return mark


def run_full_frame_calibration(*, fonts: dict[str, Any], logo_rgba: Image.Image | None) -> dict[str, Any]:
    from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map

    family = full_frame_family_spec()
    photo = synthetic_full_frame_architecture()
    occupancy = build_photo_occupancy_map(photo)
    pack = compose_full_frame_campaign(
        photo,
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        logo_rgba=logo_rgba or _calibration_wordmark(),
        facts=CALIBRATION_FACTS,
    )
    report = score_full_frame_calibration(pack, pack.get("fielded") or photo)
    report["fit"] = pack.get("fit")
    report["solved"] = pack.get("solved")
    report["pack"] = pack
    report["photo"] = photo
    report["family"] = family
    return report


