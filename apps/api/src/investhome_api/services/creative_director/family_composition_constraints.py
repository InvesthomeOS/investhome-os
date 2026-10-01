"""Family composition constraints — design relationships, not source coordinates."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

FLEX_MODES = (
    "NORMAL",
    "MIRRORED",
    "COMPRESSED",
    "EXPANDED_FIELD",
    "VERTICAL_STACK",
    "HORIZONTAL_SPLIT",
)

PROOF_FAMILIES = (
    "EDITORIAL_DARK_FIELD",
    "TYPE_IN_PLANE",
    "SKY_EDITORIAL",
)


def family_constraints(family_id: str) -> dict[str, Any]:
    common_forbidden = (
        "source_coordinates_as_placement",
        "type_on_hard_architecture",
        "type_on_spire_silhouette",
        "headline_vs_logo_overlap",
        "cards",
        "pills",
        "dashboard_panel",
        "web_button",
        "tiny_percentage",
        "isolated_floating_labels",
        "stair_step_building_cutout",
        "generative_architecture_edit",
        "dark_navy_on_dark_building",
        "ivory_on_near_white_sky",
    )
    if family_id == "EDITORIAL_DARK_FIELD":
        return {
            "schema": "FamilyCompositionConstraintsV1",
            "family_id": family_id,
            "required": [
                "stacked_display",
                "gold_last_line",
                "shared_flush_alignment",
                "designed_dark_field_under_type",
                "commercial_offer_as_one_system",
                "architecture_pixels_remain_source",
            ],
            "preferred": [
                "right_aligned",
                "field_from_canvas_edge",
                "occupy_negative_space",
                "display_to_price_scale_ratio",
            ],
            "optional": [
                "may_mirror_to_left",
                "may_stack_vertically",
                "may_expand_field_from_edge",
                "may_compress_within_family_limits",
                "may_use_designed_split",
            ],
            "forbidden": list(common_forbidden) + ["light_sky_as_primary_field"],
            "flex_modes": ["EXPANDED_FIELD", "MIRRORED", "HORIZONTAL_SPLIT", "VERTICAL_STACK", "COMPRESSED"],
            "alignment_rhythm": "flush_end",
            "default_alignment": "right",
            "mirror_alignment": "left",
            "min_architecture_clearance": 0.028,
            "max_type_width": 0.46,
            "display_to_price_ratio": 1.35,
            "field_from": "canvas_edge",
            "approved_contrast": ["ivory_on_navy", "gold_on_navy", "ivory_on_dark_photo"],
            "max_campaign_density": "HIGH",
        }
    if family_id == "TYPE_IN_PLANE":
        return {
            "schema": "FamilyCompositionConstraintsV1",
            "family_id": family_id,
            "required": [
                "type_in_one_photographic_or_tonal_plane",
                "photo_is_the_field",
                "commercial_offer_as_one_system",
                "price_prominence",
                "architecture_pixels_remain_source",
            ],
            "preferred": [
                "left_origin_inside_the_plane",
                "bronze_then_ivory_headline",
                "occupy_text_safe_plane",
            ],
            "optional": ["may_mirror", "may_compress", "may_stack_vertically", "soft_local_darken"],
            "forbidden": list(common_forbidden) + ["overlapping_circles", "mosaic_rectangles", "white_info_card"],
            "flex_modes": ["NORMAL", "MIRRORED", "COMPRESSED", "VERTICAL_STACK"],
            "alignment_rhythm": "left_in_plane",
            "default_alignment": "left",
            "mirror_alignment": "right",
            "min_architecture_clearance": 0.024,
            "max_type_width": 0.44,
            "display_to_price_ratio": 0.92,
            "field_from": "local_plane",
            "approved_contrast": ["ivory_on_dark_plane", "gold_on_dark_plane"],
            "max_campaign_density": "HIGH",
        }
    if family_id == "SKY_EDITORIAL":
        return {
            "schema": "FamilyCompositionConstraintsV1",
            "family_id": family_id,
            "required": [
                "type_in_sky_or_light_wash",
                "dark_type_on_light",
                "short_gold_rule",
                "left_origin_rhythm",
                "commercial_offer_as_one_system",
                "architecture_pixels_remain_source",
            ],
            "preferred": ["top_left_negative_space", "photo_proves_the_claim"],
            "optional": ["may_mirror_to_right_sky", "may_compress", "may_stack_vertically", "light_top_wash"],
            "forbidden": list(common_forbidden) + ["navy_field_destroying_sky_identity"],
            "flex_modes": ["NORMAL", "MIRRORED", "COMPRESSED", "VERTICAL_STACK"],
            "alignment_rhythm": "left_origin",
            "default_alignment": "left",
            "mirror_alignment": "right",
            "min_architecture_clearance": 0.03,
            "max_type_width": 0.42,
            "display_to_price_ratio": 1.45,
            "field_from": "sky_wash",
            "approved_contrast": ["navy_on_light_sky", "navy_on_ivory_wash", "gold_accent_on_light"],
            "max_campaign_density": "MEDIUM",
        }
    if family_id == "MINIMAL_TOP_FIELD":
        return {
            "schema": "FamilyCompositionConstraintsV1",
            "family_id": family_id,
            "required": [
                "architecture_occupies_lower_field",
                "type_in_designed_top_band",
                "generous_air",
                "commercial_offer_as_one_system",
                "architecture_pixels_remain_source",
            ],
            "preferred": ["top_center_or_top_right", "logo_bottom_center"],
            "optional": ["may_compress", "top_charcoal_dissolve"],
            "forbidden": list(common_forbidden) + ["crushing_the_building", "navy_side_field"],
            "flex_modes": ["NORMAL", "COMPRESSED", "HORIZONTAL_SPLIT"],
            "alignment_rhythm": "top_band",
            "default_alignment": "center",
            "mirror_alignment": "right",
            "min_architecture_clearance": 0.03,
            "max_type_width": 0.72,
            "display_to_price_ratio": 1.5,
            "field_from": "top_band",
            "approved_contrast": ["ivory_on_charcoal", "ivory_on_navy"],
            "max_campaign_density": "MEDIUM",
        }
    if family_id == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN":
        return {
            "schema": "FamilyCompositionConstraintsV1",
            "family_id": family_id,
            "required": [
                "architecture_is_the_hero",
                "perimeter_territories_not_one_giant_field",
                "commercial_offer_as_one_system",
                "architecture_pixels_remain_source",
                "typography_yields_to_architecture",
            ],
            "preferred": ["split_perimeter", "feathered_edge_integration", "quiet_logo_edge"],
            "optional": ["LEFT_COMMERCIAL", "RIGHT_COMMERCIAL", "BOTTOM_COMMERCIAL", "may_compress_within_family_limits"],
            "forbidden": list(common_forbidden)
            + ["header_bar", "footer_bar", "sidebar", "property_card", "four_boxes_around_building"],
            "flex_modes": ["SPLIT_PERIMETER", "RIGHT_COMMERCIAL", "LEFT_COMMERCIAL", "BOTTOM_COMMERCIAL"],
            "alignment_rhythm": "perimeter_flush",
            "default_alignment": "split",
            "mirror_alignment": "LEFT_COMMERCIAL",
            "min_architecture_clearance": 0.024,
            "max_type_width": 0.32,
            "display_to_price_ratio": 1.35,
            "field_from": "feathered_canvas_edge",
            "approved_contrast": ["ivory_on_edge_tone", "gold_on_edge_tone"],
            "max_campaign_density": "HIGH",
        }
    return {
        "schema": "FamilyCompositionConstraintsV1",
        "family_id": family_id,
        "required": ["architecture_pixels_remain_source", "commercial_offer_as_one_system"],
        "preferred": [],
        "optional": ["may_compress"],
        "forbidden": list(common_forbidden),
        "flex_modes": ["NORMAL", "COMPRESSED"],
        "alignment_rhythm": "flush_end",
        "default_alignment": "right",
        "mirror_alignment": "left",
        "min_architecture_clearance": 0.03,
        "max_type_width": 0.42,
        "display_to_price_ratio": 1.2,
        "field_from": "canvas_edge",
        "approved_contrast": ["ivory_on_navy", "navy_on_light_sky"],
    }


def all_family_constraints() -> dict[str, Any]:
    return {
        "schema": "FamilyConstraintLibraryV1",
        "families": {fid: family_constraints(fid) for fid in PROOF_FAMILIES},
        "note": "Preserve design logic, not source coordinates.",
    }


def render_constraint_map(families: list[dict[str, Any]] | None = None) -> Image.Image:
    canvas = Image.new("RGB", (1480, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "FAMILY CONSTRAINTS  —  relationships, not x=0.72", fill=(201, 168, 92))
    ids = [f.get("family_id") for f in (families or []) if f.get("family_id") in PROOF_FAMILIES] or list(PROOF_FAMILIES)
    x = 36
    for fid in ids:
        spec = family_constraints(str(fid))
        tile = Image.new("RGB", (460, 860), (22, 24, 32))
        td = ImageDraw.Draw(tile)
        td.text((16, 16), str(fid), fill=(236, 230, 218))
        y = 52
        td.text((16, y), "REQUIRED", fill=(201, 168, 92))
        y += 24
        for item in spec["required"]:
            td.text((16, y), "• " + str(item)[:44], fill=(210, 206, 198))
            y += 20
        y += 10
        td.text((16, y), "PREFERRED / OPTIONAL", fill=(201, 168, 92))
        y += 24
        for item in list(spec["preferred"]) + list(spec["optional"]):
            td.text((16, y), "• " + str(item)[:44], fill=(170, 166, 158))
            y += 20
        y += 10
        td.text((16, y), "FORBIDDEN", fill=(220, 110, 90))
        y += 24
        for item in list(spec["forbidden"])[:8]:
            td.text((16, y), "• " + str(item)[:44], fill=(190, 140, 130))
            y += 20
        y += 12
        td.text((16, y), "FLEX  " + "  ".join(spec["flex_modes"]), fill=(140, 190, 170))
        canvas.paste(tile, (x, 64))
        x += 480
    return canvas
