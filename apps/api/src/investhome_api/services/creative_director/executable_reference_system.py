"""ExecutableReferenceSystemV1 — observable systems, not adjective DNA."""

from __future__ import annotations

import json
from typing import Any

from PIL import Image

from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

FORBIDDEN_PRIMARY = (
    "balanced composition",
    "bold typography",
    "premium negative space",
    "effective use of negative space",
    "clear typography hierarchy",
    "strong visual hierarchy",
)

# Observable systems from Phase 5.4D visual inspection. Vision may refine boxes, not replace these.
SEEDED: dict[str, dict[str, Any]] = {
    "ORNEK_00013.jpg": {
        "system_id": "DARK_FIELD_STACKED_DISPLAY",
        "filename": "ORNEK_00013.jpg",
        "canvas_system": {
            "image_field": {"x": 0.0, "y": 0.28, "w": 0.52, "h": 0.72},
            "graphic_field": {"x": 0.38, "y": 0.0, "w": 0.62, "h": 1.0},
            "dominant_axis": "vertical",
            "content_origin": "top_right",
            "safe_margins": {"top": 0.06, "right": 0.06, "bottom": 0.08, "left": 0.08},
        },
        "alignment_system": {
            "alignment": "right",
            "common_anchor": "right_edge_inset",
            "edge_relationship": "type shares the right margin of the dark field",
            "baseline_relationship": "stacked display with shared right flush",
        },
        "typography_system": {
            "display_scale": 0.11,
            "secondary_scale": 0.028,
            "commercial_number_scale": 0.0,
            "serif_sans_role": "display_sans_stacked; body sans lighter",
            "case": "uppercase_display",
            "tracking": "display_tight; body_open",
            "line_height": "stacked_display_0.95em",
            "emphasis_method": "final_line_gold_remainder_white",
        },
        "color_system": {
            "dominant_field": "#14181E",
            "text_color": "#F4EFE4",
            "accent_color": "#C9A85C",
            "number_color": "#C9A85C",
            "contrast_relationship": "light type on charcoal field",
        },
        "commercial_system": {
            "price_prominence": "none_in_reference",
            "discount_relationship": "none",
            "label_relationship": "body_copy_below_display",
            "grouping": "display_then_body",
            "divider_rule": "none_or_implied_by_scale",
        },
        "logo_system": {
            "relative_scale": 0.18,
            "visual_authority": "quiet_inscription",
            "clear_space": 0.04,
            "relationship_to_headline": "opposite_corner_of_field",
        },
        "cta_system": {
            "treatment": "none_or_embedded_body",
            "relative_prominence": "low",
            "alignment": "right",
        },
        "image_system": {
            "subject_placement": "left_lower_as_material",
            "crop_philosophy": "architecture_as_desaturated_material_not_full_bleed_plate",
            "subject_protection": "no_type_on_columns",
            "negative_space_relationship": "dark_field_is_the_negative_space",
        },
        "graphic_field_system": {
            "field": "solid_charcoal",
            "gradient_direction": "photo_dissolves_into_field_left_to_right",
            "masks": "architecture_kept_in_image_field",
            "geometric_surfaces": "none",
            "field_photo_interaction": "seamless_sky_becomes_the_field",
        },
        "do_not_copy": ["Washington colonnade", "DÜZENLİ/GÜVENLİ copy", "investhome lifestyle photo"],
    },
    "ORNEK_00001.jpg": {
        "system_id": "EDITORIAL_SKY_LEFT",
        "filename": "ORNEK_00001.jpg",
        "canvas_system": {
            "image_field": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "graphic_field": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.28},
            "dominant_axis": "vertical",
            "content_origin": "top_left",
            "safe_margins": {"top": 0.08, "right": 0.08, "bottom": 0.08, "left": 0.07},
        },
        "alignment_system": {
            "alignment": "left",
            "common_anchor": "left_inset",
            "edge_relationship": "type lives in sky, not on subject",
            "baseline_relationship": "headline block then supporting block",
        },
        "typography_system": {
            "display_scale": 0.042,
            "secondary_scale": 0.022,
            "commercial_number_scale": 0.0,
            "serif_sans_role": "sans_editorial",
            "case": "sentence_and_emphasis_line",
            "tracking": "display_normal",
            "line_height": "1.15",
            "emphasis_method": "middle_line_weight",
        },
        "color_system": {
            "dominant_field": "photographic_sky",
            "text_color": "#1C2430",
            "accent_color": "#C9A85C",
            "number_color": "#1C2430",
            "contrast_relationship": "dark type on light sky with soft top wash",
        },
        "commercial_system": {
            "price_prominence": "none",
            "discount_relationship": "none",
            "label_relationship": "offer_as_supporting_lines",
            "grouping": "headline_then_offer_copy",
            "divider_rule": "short_horizontal_rule",
        },
        "logo_system": {
            "relative_scale": 0.22,
            "visual_authority": "top_center_brand",
            "clear_space": 0.05,
            "relationship_to_headline": "above_and_independent",
        },
        "cta_system": {"treatment": "none", "relative_prominence": "none", "alignment": "left"},
        "image_system": {
            "subject_placement": "lower_right_lifestyle_proves_claim",
            "crop_philosophy": "sky_is_the_type_field",
            "subject_protection": "type_never_on_figure_or_capitol",
            "negative_space_relationship": "sky_wash_creates_legibility",
        },
        "graphic_field_system": {
            "field": "soft_white_to_photo_gradient",
            "gradient_direction": "top_to_subject",
            "masks": "none_hard",
            "geometric_surfaces": "none",
            "field_photo_interaction": "wash_not_card",
        },
        "do_not_copy": ["woman on balcony", "Capitol", "map pin icon", "UniLoft copy"],
    },
    "ORNEK_00006.jpg": {
        "system_id": "BREATHING_ROOM_TOP_FIELD",
        "filename": "ORNEK_00006.jpg",
        "canvas_system": {
            "image_field": {"x": 0.0, "y": 0.38, "w": 1.0, "h": 0.62},
            "graphic_field": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.44},
            "dominant_axis": "vertical",
            "content_origin": "top_center",
            "safe_margins": {"top": 0.08, "right": 0.12, "bottom": 0.08, "left": 0.12},
        },
        "alignment_system": {
            "alignment": "center",
            "common_anchor": "horizontal_center",
            "edge_relationship": "wide_side_margins",
            "baseline_relationship": "headline_flourish_body",
        },
        "typography_system": {
            "display_scale": 0.038,
            "secondary_scale": 0.018,
            "commercial_number_scale": 0.0,
            "serif_sans_role": "sans_centered_editorial",
            "case": "sentence",
            "tracking": "open",
            "line_height": "1.25",
            "emphasis_method": "one_bold_line",
        },
        "color_system": {
            "dominant_field": "#3A3530",
            "text_color": "#F4EFE4",
            "accent_color": "#C9A85C",
            "number_color": "#F4EFE4",
            "contrast_relationship": "light type on muted brown-grey field",
        },
        "commercial_system": {
            "price_prominence": "none",
            "discount_relationship": "none",
            "label_relationship": "body_only",
            "grouping": "headline_block",
            "divider_rule": "small_ornamental_break_not_copied_as_clipart",
        },
        "logo_system": {
            "relative_scale": 0.2,
            "visual_authority": "bottom_center",
            "clear_space": 0.05,
            "relationship_to_headline": "far_end_of_canvas",
        },
        "cta_system": {"treatment": "none", "relative_prominence": "none", "alignment": "center"},
        "image_system": {
            "subject_placement": "lower_interior_or_architecture",
            "crop_philosophy": "photo_occupies_lower_field",
            "subject_protection": "no_type_on_interior_subject",
            "negative_space_relationship": "top_field_is_intentional_air",
        },
        "graphic_field_system": {
            "field": "muted_top_field",
            "gradient_direction": "field_dissolves_down_into_photo",
            "masks": "soft",
            "geometric_surfaces": "none",
            "field_photo_interaction": "gradient_merge_not_hard_split",
        },
        "do_not_copy": ["UniLoft interior", "person on sofa", "ornamental flourish glyph"],
    },
    "ORNEK_00015.jpg": {
        "system_id": "TYPE_IN_PHOTO_DARKNESS",
        "filename": "ORNEK_00015.jpg",
        "canvas_system": {
            "image_field": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "graphic_field": {"x": 0.0, "y": 0.0, "w": 0.55, "h": 0.42},
            "dominant_axis": "vertical",
            "content_origin": "top_left",
            "safe_margins": {"top": 0.07, "right": 0.08, "bottom": 0.08, "left": 0.07},
        },
        "alignment_system": {
            "alignment": "left",
            "common_anchor": "left_inset",
            "edge_relationship": "type_in_darkest_photo_quadrant",
            "baseline_relationship": "headline_then_quiet_body",
        },
        "typography_system": {
            "display_scale": 0.036,
            "secondary_scale": 0.016,
            "commercial_number_scale": 0.0,
            "serif_sans_role": "sans_quiet",
            "case": "uppercase_short_display",
            "tracking": "open",
            "line_height": "1.1",
            "emphasis_method": "weight_split_two_phrases",
        },
        "color_system": {
            "dominant_field": "photographic_shadow",
            "text_color": "#F4EFE4",
            "accent_color": "#C9A85C",
            "number_color": "#F4EFE4",
            "contrast_relationship": "white type in low-key darkness",
        },
        "commercial_system": {
            "price_prominence": "none",
            "discount_relationship": "none",
            "label_relationship": "none",
            "grouping": "headline_only",
            "divider_rule": "none",
        },
        "logo_system": {
            "relative_scale": 0.16,
            "visual_authority": "bottom_center_quiet",
            "clear_space": 0.05,
            "relationship_to_headline": "distant",
        },
        "cta_system": {"treatment": "none", "relative_prominence": "none", "alignment": "left"},
        "image_system": {
            "subject_placement": "photo_is_the_entire_canvas",
            "crop_philosophy": "low_key_interior_or_architecture_shadows_are_the_field",
            "subject_protection": "type_only_in_shadow",
            "negative_space_relationship": "darkness_is_whitespace",
        },
        "graphic_field_system": {
            "field": "photographic_shadow_only",
            "gradient_direction": "none_or_subtle_top_falloff",
            "masks": "none",
            "geometric_surfaces": "none",
            "field_photo_interaction": "no_card_type_uses_existing_darkness",
        },
        "do_not_copy": ["kitchen island", "fruit basket", "UniLoft script lockup"],
    },
    "ORNEK_00011.jpg": {
        "system_id": "SUBJECT_CENTER_DESIGNED_SURROUND",
        "filename": "ORNEK_00011.jpg",
        "canvas_system": {
            "image_field": {"x": 0.18, "y": 0.28, "w": 0.64, "h": 0.62},
            "graphic_field": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.32},
            "dominant_axis": "vertical",
            "content_origin": "top_center",
            "safe_margins": {"top": 0.06, "right": 0.08, "bottom": 0.08, "left": 0.08},
        },
        "alignment_system": {
            "alignment": "center",
            "common_anchor": "center_axis",
            "edge_relationship": "brand_and_headline_above_subject",
            "baseline_relationship": "logo_address_headline",
        },
        "typography_system": {
            "display_scale": 0.034,
            "secondary_scale": 0.016,
            "commercial_number_scale": 0.0,
            "serif_sans_role": "sans_informational",
            "case": "sentence",
            "tracking": "normal",
            "line_height": "1.2",
            "emphasis_method": "one_taupe_callout_not_a_kpi_tile",
        },
        "color_system": {
            "dominant_field": "#ECE8E2",
            "text_color": "#4A4A4A",
            "accent_color": "#B08A62",
            "number_color": "#4A4A4A",
            "contrast_relationship": "grey type on light surround",
        },
        "commercial_system": {
            "price_prominence": "none",
            "discount_relationship": "none",
            "label_relationship": "one_callout_band",
            "grouping": "headline_then_callout",
            "divider_rule": "none",
        },
        "logo_system": {
            "relative_scale": 0.2,
            "visual_authority": "top_center",
            "clear_space": 0.04,
            "relationship_to_headline": "above",
        },
        "cta_system": {"treatment": "none", "relative_prominence": "none", "alignment": "center"},
        "image_system": {
            "subject_placement": "centered_architecture",
            "crop_philosophy": "building_as_subject_with_designed_surround",
            "subject_protection": "no_type_on_building",
            "negative_space_relationship": "light_ground_around_subject",
        },
        "graphic_field_system": {
            "field": "light_desaturated_surround",
            "gradient_direction": "none",
            "masks": "subject_held_sharp",
            "geometric_surfaces": "no_leader_lines_copied",
            "field_photo_interaction": "building_sits_in_designed_ground",
        },
        "do_not_copy": ["Capitol ghost", "walking-time leader lines", "UniLoft brick building"],
    },
    "ORNEK_00008.jpg": {
        "system_id": "TYPE_IN_ARCHITECTURAL_SHADOW",
        "filename": "ORNEK_00008.jpg",
        "canvas_system": {
            "image_field": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "graphic_field": {"x": 0.42, "y": 0.08, "w": 0.52, "h": 0.4},
            "dominant_axis": "vertical",
            "content_origin": "mid_right",
            "safe_margins": {"top": 0.08, "right": 0.07, "bottom": 0.1, "left": 0.08},
        },
        "alignment_system": {
            "alignment": "left_within_right_field",
            "common_anchor": "right_field_left_edge",
            "edge_relationship": "type_occupies_dark_facade_or_sky_not_a_card",
            "baseline_relationship": "headline_then_body_then_data",
        },
        "typography_system": {
            "display_scale": 0.04,
            "secondary_scale": 0.018,
            "commercial_number_scale": 0.055,
            "serif_sans_role": "sans_bronze_display",
            "case": "sentence_display",
            "tracking": "normal",
            "line_height": "1.12",
            "emphasis_method": "bronze_headline_white_body",
        },
        "color_system": {
            "dominant_field": "photographic_dark_facade",
            "text_color": "#F4EFE4",
            "accent_color": "#C4A06A",
            "number_color": "#F4EFE4",
            "contrast_relationship": "bronze and white on dark architecture or sky",
        },
        "commercial_system": {
            "price_prominence": "high_if_adapted",
            "discount_relationship": "paired_not_circled",
            "label_relationship": "adjacent_to_number",
            "grouping": "headline_body_commercial",
            "divider_rule": "none_do_not_copy_overlapping_circles",
        },
        "logo_system": {
            "relative_scale": 0.16,
            "visual_authority": "bottom_center",
            "clear_space": 0.04,
            "relationship_to_headline": "distant",
        },
        "cta_system": {"treatment": "inscription", "relative_prominence": "low", "alignment": "left_within_field"},
        "image_system": {
            "subject_placement": "architecture_fills_canvas",
            "crop_philosophy": "type_uses_existing_dark_planes",
            "subject_protection": "no_type_on_bright_facade_detail",
            "negative_space_relationship": "shadow_planes_are_the_field",
        },
        "graphic_field_system": {
            "field": "tonal_darkening_of_existing_planes",
            "gradient_direction": "local_falloff",
            "masks": "architecture_structure_preserved",
            "geometric_surfaces": "no_pills_no_circles",
            "field_photo_interaction": "darken_sky_or_shadow_only",
        },
        "do_not_copy": ["overlapping delivery circles", "UniLoft facade", "pampas grass terrace"],
    },
}

E_ASSIGNMENTS = {
    "E1": {
        "primary": "ORNEK_00013.jpg",
        "secondary": "ORNEK_00015.jpg",
        "key": "E1",
        "concept": "EDITORIAL_DARK_FIELD",
        "intent": (
            "Sophisticated architectural advertising. Strong display typography. "
            "Controlled dark/light relationship. Restrained gold accent. Architecture remains important."
        ),
    },
    "E2": {
        "primary": "ORNEK_00008.jpg",
        "secondary": "ORNEK_00001.jpg",
        "key": "E2",
        "concept": "PREMIUM_COMMERCIAL",
        "intent": (
            "Strongest sales advertisement. Immediate offer comprehension. "
            "Professional price hierarchy. %35 advantage clearly designed. Premium campaign character."
        ),
    },
    "E3": {
        "primary": "ORNEK_00006.jpg",
        "secondary": "ORNEK_00011.jpg",
        "key": "E3",
        "concept": "MINIMAL_ARCHITECTURAL",
        "intent": (
            "Quieter premium composition. Architecture dominant. Sophisticated whitespace. "
            "Minimal but strong commercial hierarchy. High-end development campaign character."
        ),
    },
}


def _strip_generic(text: str) -> str:
    raw = (text or "").strip()
    folded = raw.casefold()
    if any(p in folded for p in FORBIDDEN_PRIMARY):
        return ""
    return raw


def seeded_system(filename: str) -> dict[str, Any]:
    blob = dict(SEEDED.get(filename) or {})
    blob["schema"] = "ExecutableReferenceSystemV1"
    blob["source"] = "phase5_4d_visual_inspection"
    return blob


def request_executable_system(image: Image.Image, *, filename: str) -> tuple[dict[str, Any], int]:
    seed = seeded_system(filename)
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract EXECUTABLE design systems from one advertisement. "
                    "Use boxes 0-1 {x,y,w,h}, hex colors, alignment enums. "
                    "Forbidden as primary values: balanced composition, bold typography, "
                    "premium negative space, effective use of negative space. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Filename {filename}. Measure: canvas_system, alignment_system, "
                            "typography_system, color_system, commercial_system, logo_system, "
                            "cta_system, image_system, graphic_field_system. "
                            "Do not copy buildings, logos, or copy."
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
        "canvas_system",
        "alignment_system",
        "typography_system",
        "color_system",
        "commercial_system",
        "logo_system",
        "cta_system",
        "image_system",
        "graphic_field_system",
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
    merged["vision_refined"] = bool(parsed)
    merged["source"] = "phase5_4d_visual_inspection+vision_boxes"
    return merged, calls


def systems_for_candidate(key: str, catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    spec = E_ASSIGNMENTS[key]
    primary = catalog.get(spec["primary"]) or seeded_system(spec["primary"])
    secondary = catalog.get(spec["secondary"]) or seeded_system(spec["secondary"])
    return {
        "schema": "CandidateReferenceSystemsV1",
        "key": key,
        "concept": spec["concept"],
        "intent": spec["intent"],
        "primary": primary,
        "secondary": secondary,
        "primary_filename": spec["primary"],
        "secondary_filename": spec["secondary"],
        "system_id": primary.get("system_id"),
    }
