"""ReferenceMasterFamilyV1 + CreativeMasterFamilyLibraryV1.

Grade-A DESIGN_REFERENCES become executable families. Not pixel templates.
Does not copy source project image, logo, name, price, or copy.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from PIL import Image

from investhome_api.services.creative_director.executable_reference_system import (
    FORBIDDEN_PRIMARY,
    SEEDED,
    _strip_generic,
)
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
from investhome_api.services.creative_director.reference_quality_filter import GRADE_A
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

GRADE_A_ORDER = (
    "ORNEK_00013.jpg",
    "ORNEK_00001.jpg",
    "ORNEK_00006.jpg",
    "ORNEK_00015.jpg",
    "ORNEK_00011.jpg",
    "ORNEK_00008.jpg",
)

# Clustered from the six Grade-A systems. 00013+00015 share darkness-as-field.
# 00006+00011 share designed surround / breathing room. 00001 and 00008 stand alone.
FAMILY_CLUSTERS = (
    {
        "family_id": "EDITORIAL_DARK_FIELD",
        "primary": "ORNEK_00013.jpg",
        "members": ("ORNEK_00013.jpg", "ORNEK_00015.jpg"),
        "identity": "Stacked display on a designed dark field. Gold last line. Architecture as material, not a listing plate.",
    },
    {
        "family_id": "SKY_EDITORIAL",
        "primary": "ORNEK_00001.jpg",
        "members": ("ORNEK_00001.jpg",),
        "identity": "Editorial type in a light sky wash. Photo proves the claim. Left origin with a short rule.",
    },
    {
        "family_id": "MINIMAL_TOP_FIELD",
        "primary": "ORNEK_00006.jpg",
        "members": ("ORNEK_00006.jpg", "ORNEK_00011.jpg"),
        "identity": "Architecture occupies the lower field. Type lives in a designed top band with generous air.",
    },
    {
        "family_id": "TYPE_IN_PLANE",
        "primary": "ORNEK_00008.jpg",
        "members": ("ORNEK_00008.jpg",),
        "identity": "Type occupies a dark architectural or sky plane. Photo is the field. No circles, no badges.",
    },
)


def _box(x: float, y: float, w: float, h: float) -> dict[str, float]:
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def seeded_reference_family(filename: str) -> dict[str, Any]:
    exe = dict(SEEDED.get(filename) or {})
    canvas = dict(exe.get("canvas_system") or {})
    align = dict(exe.get("alignment_system") or {})
    type_sys = dict(exe.get("typography_system") or {})
    color = dict(exe.get("color_system") or {})
    logo = dict(exe.get("logo_system") or {})
    cta = dict(exe.get("cta_system") or {})
    image = dict(exe.get("image_system") or {})
    field = dict(exe.get("graphic_field_system") or {})
    commercial = dict(exe.get("commercial_system") or {})
    origin = str(canvas.get("content_origin") or "top_right")
    alignment = str(align.get("alignment") or "right")
    if alignment.startswith("left"):
        alignment = "left" if "right" not in alignment else "left"
        if "within_right" in str(align.get("alignment") or ""):
            alignment = "left"
            origin = "mid_right"
    display = float(type_sys.get("display_scale") or 0.06)
    secondary = float(type_sys.get("secondary_scale") or 0.02)
    number = float(type_sys.get("commercial_number_scale") or 0.0) or max(0.036, display * 0.55)
    graphic_field = dict(canvas.get("graphic_field") or _box(0.0, 0.0, 1.0, 0.3))
    image_field = dict(canvas.get("image_field") or _box(0.0, 0.0, 1.0, 1.0))
    return {
        "schema": "ReferenceMasterFamilyV1",
        "filename": filename,
        "reference_id": next((rid for rid, name in GRADE_A.items() if name == filename), None),
        "system_id": exe.get("system_id"),
        "canvas": {
            "aspect": "4:5",
            "margins": dict(canvas.get("safe_margins") or {"top": 0.07, "right": 0.07, "bottom": 0.08, "left": 0.07}),
            "dominant_axes": canvas.get("dominant_axis") or "vertical",
            "visual_center": origin,
            "content_origin": origin,
        },
        "photo": {
            "bounds": image_field,
            "crop_behavior": image.get("crop_philosophy"),
            "image_dominance": round(float(image_field.get("w", 1) * image_field.get("h", 1)), 3),
            "subject_location": image.get("subject_placement"),
            "image_field_relationship": field.get("field_photo_interaction") or image.get("negative_space_relationship"),
        },
        "brand": {
            "bounds": _box(0.36, 0.88, 0.28, 0.08) if "center" in str(logo.get("visual_authority") or "") else _box(0.64, 0.88, 0.28, 0.08),
            "relative_scale": float(logo.get("relative_scale") or 0.18),
            "clear_space": float(logo.get("clear_space") or 0.04),
            "relationship": logo.get("relationship_to_headline"),
            "authority": logo.get("visual_authority"),
        },
        "headline": {
            "bounds": graphic_field,
            "width": float(graphic_field.get("w") or 0.5),
            "scale_ratio": display,
            "alignment": alignment if alignment in {"left", "right", "center"} else "right",
            "line_structure": "stacked_display" if display >= 0.07 else "two_or_three_lines",
            "font_role": "DISPLAY_SERIF" if display >= 0.05 else "EDITORIAL_SANS",
            "emphasis_system": type_sys.get("emphasis_method"),
        },
        "commercial_offer": {
            "price_bounds": None,
            "relative_size": number,
            "relationship_to_headline": commercial.get("grouping"),
            "discount_relationship": commercial.get("discount_relationship"),
            "supporting_label_relationship": commercial.get("label_relationship"),
            "price_prominence": commercial.get("price_prominence"),
        },
        "cta": {
            "bounds": _box(graphic_field.get("x", 0.5), 0.72, min(0.42, graphic_field.get("w", 0.4)), 0.04),
            "alignment": cta.get("alignment") or alignment,
            "prominence": cta.get("relative_prominence") or "low",
            "visual_treatment": cta.get("treatment") or "inscription",
        },
        "graphic_devices": {
            "fields": field.get("field"),
            "rules": commercial.get("divider_rule"),
            "masks": field.get("masks"),
            "dividers": commercial.get("divider_rule"),
            "color_surfaces": color.get("dominant_field"),
            "image_boundaries": field.get("field_photo_interaction"),
            "controlled_overlays": field.get("gradient_direction"),
        },
        "typography": {
            "serif_sans_role": type_sys.get("serif_sans_role"),
            "size_ratios": {"display": display, "secondary": secondary, "number": number},
            "weights": type_sys.get("emphasis_method"),
            "tracking": type_sys.get("tracking"),
            "leading": type_sys.get("line_height"),
            "case": type_sys.get("case"),
            "color": {
                "text": color.get("text_color"),
                "accent": color.get("accent_color"),
                "number": color.get("number_color"),
                "field": color.get("dominant_field"),
            },
            "emphasis": type_sys.get("emphasis_method"),
        },
        "spacing": {
            "group_gaps": 0.028,
            "internal_spacing": 0.01,
            "edge_relationships": align.get("edge_relationship"),
            "baseline_relationships": align.get("baseline_relationship"),
        },
        "z_order": ["project_photo", "graphic_field", "typography", "project_logo"],
        "constraints": list(exe.get("do_not_copy") or []) + ["no_cards", "no_pills", "no_kpi", "no_web_button", "no_source_copy"],
        "flexibility": {
            "may_mirror": True,
            "scale_min": 0.78,
            "scale_max": 1.1,
        },
        "source": "phase5_4d_visual_inspection",
    }


def request_reference_family(image: Image.Image, *, filename: str) -> tuple[dict[str, Any], int]:
    seed = seeded_reference_family(filename)
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Deconstruct this advertisement into STRUCTURE and RELATIONSHIPS. "
                    "Boxes 0-1 {x,y,w,h}. Hex colors. Alignment enums. "
                    "Do not copy buildings, logos, project names, prices, or copy. "
                    "Forbidden as primary values: " + ", ".join(FORBIDDEN_PRIMARY) + ". JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Filename {filename}. Return JSON with canvas, photo, brand, headline, "
                            "commercial_offer, cta, graphic_devices, typography, spacing, z_order, "
                            "constraints, flexibility. Measure. Do not write adjectives as the system."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(image)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    merged = dict(seed)
    for key in (
        "canvas",
        "photo",
        "brand",
        "headline",
        "commercial_offer",
        "cta",
        "graphic_devices",
        "typography",
        "spacing",
        "flexibility",
    ):
        incoming = parsed.get(key)
        if not isinstance(incoming, dict):
            continue
        cleaned = {
            k: v
            for k, v in incoming.items()
            if not (isinstance(v, str) and any(p in v.casefold() for p in FORBIDDEN_PRIMARY))
        }
        if cleaned:
            base = dict(merged.get(key) or {})
            base.update(cleaned)
            merged[key] = base
    if isinstance(parsed.get("z_order"), list) and parsed["z_order"]:
        merged["z_order"] = [str(x) for x in parsed["z_order"][:8]]
    merged["vision_refined"] = bool(parsed)
    merged["source"] = "phase5_4d_visual_inspection+vision_boxes"
    _ = _strip_generic
    return merged, calls


def _family_spec_from_cluster(cluster: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    primary_name = cluster["primary"]
    members = [catalog.get(name) or seeded_reference_family(name) for name in cluster["members"]]
    primary = catalog.get(primary_name) or seeded_reference_family(primary_name)
    headline = dict(primary.get("headline") or {})
    typo = dict(primary.get("typography") or {})
    color = dict(typo.get("color") or {})
    ratios = dict(typo.get("size_ratios") or {})
    canvas = dict(primary.get("canvas") or {})
    brand = dict(primary.get("brand") or {})
    cta = dict(primary.get("cta") or {})
    commercial = dict(primary.get("commercial_offer") or {})
    devices = dict(primary.get("graphic_devices") or {})
    family_id = cluster["family_id"]
    alignment = str(headline.get("alignment") or "right")
    if family_id == "SKY_EDITORIAL":
        overlay = "top_light_wash"
        crop_bias = {"x": 0.62, "y": 0.32}
        type_priority = ["top_left", "top_right", "top_band"]
        logo_slot = "top_center"
        display_role = "DISPLAY_SERIF"
        field_hex = "#E8E2D6"
        text_hex = "#1C2430"
        number_scale = 0.042
    elif family_id == "MINIMAL_TOP_FIELD":
        overlay = "top_charcoal_dissolve"
        crop_bias = {"x": 0.55, "y": 0.68}
        type_priority = ["top_center", "top_right", "top_band"]
        logo_slot = "bottom_center"
        display_role = "DISPLAY_SERIF"
        field_hex = "#3A3530"
        text_hex = "#F4EFE4"
        number_scale = 0.034
    elif family_id == "TYPE_IN_PLANE":
        overlay = "local_plane_darken"
        crop_bias = {"x": 0.52, "y": 0.48}
        type_priority = ["mid_right", "top_right", "right_column"]
        logo_slot = "bottom_center"
        display_role = "DISPLAY_SERIF"
        field_hex = "#14181E"
        text_hex = "#F4EFE4"
        number_scale = 0.07
    else:
        overlay = "right_top_charcoal_dissolve"
        crop_bias = {"x": 0.42, "y": 0.58}
        type_priority = ["right_column", "top_right", "top_band"]
        logo_slot = "bottom_of_column"
        display_role = "DISPLAY_SERIF"
        field_hex = "#14181E"
        text_hex = str(color.get("text") or "#F4EFE4")
        number_scale = max(0.046, float(ratios.get("number") or 0.046))
        alignment = "right"
    return {
        "schema": "CreativeMasterFamilySpecV1",
        "family_id": family_id,
        "family_spec_id": str(uuid4()),
        "identity": cluster["identity"],
        "source_references": list(cluster["members"]),
        "primary_reference": primary_name,
        "member_systems": [m.get("system_id") for m in members],
        "canvas": {
            "aspect": "4:5",
            "width": 1088,
            "height": 1360,
            "margins": dict(canvas.get("margins") or {"top": 0.07, "right": 0.07, "bottom": 0.08, "left": 0.07}),
            "dominant_axes": canvas.get("dominant_axes") or "vertical",
            "visual_center": canvas.get("visual_center"),
        },
        "photo": dict(primary.get("photo") or {}),
        "brand": {**brand, "slot": logo_slot, "asset_must_be_real": True},
        "headline": {
            **headline,
            "alignment": alignment,
            "font_role": display_role,
            "split_last_line_gold": family_id == "EDITORIAL_DARK_FIELD",
        },
        "unit_type": {"role": "SUPPORTING_INFORMATION_GROUP", "scale": float(ratios.get("secondary") or 0.02), "case": "uppercase", "tracking": 180},
        "price": {
            "role": "COMMERCIAL_OFFER_GROUP",
            "scale": number_scale,
            "alignment": alignment if family_id != "SKY_EDITORIAL" else "left",
            "prominence": "major" if family_id == "TYPE_IN_PLANE" else "designed",
        },
        "discount": {"role": "COMMERCIAL_OFFER_GROUP", "scale": number_scale * 0.62, "relationship": "paired_with_label"},
        "discount_label": {"role": "COMMERCIAL_OFFER_GROUP", "scale": float(ratios.get("secondary") or 0.018), "relationship": "under_or_beside_discount"},
        "cta": {**cta, "font_role": "CTA", "treatment": "tracked_inscription"},
        "graphic_devices": {
            **devices,
            "overlay": overlay,
            "field_hex": field_hex if family_id != "SKY_EDITORIAL" else "#E8E2D6",
            "text_hex": text_hex,
            "accent_hex": str(color.get("accent") or "#C9A85C"),
            "rule": "short_gold_rule" if family_id in {"EDITORIAL_DARK_FIELD", "SKY_EDITORIAL", "TYPE_IN_PLANE"} else "none",
            "forbidden": ["cards", "pills", "kpi_tiles", "web_buttons", "overlapping_circles", "source_logo", "source_copy"],
        },
        "typography": {
            "display_role": display_role,
            "support_role": "EDITORIAL_SANS",
            "number_role": "COMMERCIAL_NUMBER",
            "cta_role": "CTA",
            "display_scale": float(ratios.get("display") or 0.07),
            "secondary_scale": float(ratios.get("secondary") or 0.02),
            "number_scale": number_scale,
            "tracking_display": 40 if family_id == "EDITORIAL_DARK_FIELD" else 20,
            "tracking_support": 160,
            "tracking_cta": 240,
            "case": "uppercase",
            "text_hex": text_hex,
            "accent_hex": str(color.get("accent") or "#C9A85C"),
            "ink_hex": "#1C2430",
        },
        "spacing": {
            "after_headline": 0.022 if family_id != "MINIMAL_TOP_FIELD" else 0.016,
            "after_unit": 0.016,
            "after_price": 0.012,
            "after_offer": 0.046,
            "edge_inset": 0.06,
            "column_gap": 0.012,
        },
        "z_order": ["project_photo", "graphic_field", "typography", "project_logo"],
        "constraints": [
            "do_not_copy_source_photo",
            "do_not_copy_source_logo",
            "do_not_copy_source_copy",
            "no_type_on_spire",
            "no_cards",
            "no_pills",
            "no_dashboard",
            "architecture_stays_real",
        ],
        "flexibility": {
            "may_mirror": True,
            "alternate_alignment": "left" if alignment == "right" else ("right" if alignment == "left" else "right"),
            "type_region_priority": type_priority,
            "scale_min": 0.78,
            "scale_max": 1.08,
            "crop_bias": crop_bias,
            "may_compress_leading": True,
        },
        "roles": ["project_photo", "project_logo", "headline", "unit_type", "price", "discount", "discount_label", "cta"],
        "commercial": commercial,
        "user_facing_picker": False,
    }


def build_family_library(catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    families = [_family_spec_from_cluster(cluster, catalog) for cluster in FAMILY_CLUSTERS]
    return {
        "schema": "CreativeMasterFamilyLibraryV1",
        "library_id": str(uuid4()),
        "family_count": len(families),
        "families": families,
        "clusters": [
            {
                "family_id": c["family_id"],
                "members": list(c["members"]),
                "identity": c["identity"],
            }
            for c in FAMILY_CLUSTERS
        ],
        "grade_a_only": True,
        "user_facing_template_picker": False,
        "note": "Internal design systems. The user never selects template 1/2/3.",
    }


def family_by_id(library: dict[str, Any], family_id: str) -> dict[str, Any]:
    for item in list(library.get("families") or []):
        if item.get("family_id") == family_id:
            return dict(item)
    if family_id == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN":
        from investhome_api.services.creative_director.full_frame_architectural_family import full_frame_family_spec

        return full_frame_family_spec()
    raise KeyError(family_id)
