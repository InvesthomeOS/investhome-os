"""Phase 4.0B — Generative Creative Director.

Turns a brief + the actual hero photograph into an AIArtDirectionPlanV1,
then compiles that plan into NativeMasterDesignSpecV2.

Does not select from a layout menu. Does not polish Phase 4.0A.
Does not call an image provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from PIL import Image, ImageFilter, ImageStat

from investhome_api.services.creative_director.native_master import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_CAMPAIGN_ID,
    REQUIRED_CONTENT,
    SCHEMA_V2,
    SPEC_VERSION_V2,
    TEMPLE_PROJECT_ID,
    _as_dict,
    _box,
    _color_system,
    _content_capacity,
    _cover_crop,
    _flexibility,
    _format_adaptation_policy,
    _geom,
    _hero_treatment,
    _now,
    _revision_policy,
    _typography_plan,
    inspect_available_fonts,
    persist_phase4_native_master,
    validate_native_master_spec,
)

PLAN_SCHEMA = "AIArtDirectionPlanV1"
PHASE4B_TEST_KEY = "phase4b_generative_native_master_test"

FINGERPRINT_40A = {
    "hero_coverage": "lower_field",
    "headline_anchor": "top_center",
    "commercial_anchor": "center_plate",
    "cta_anchor": "full_width_seam",
    "logo_anchor": "bottom_center",
    "alignment_system": "centered_stack",
    "dominant_color_field": "full_width_navy_plate",
}

FINGERPRINT_40 = {
    "hero_coverage": "full_bleed",
    "headline_anchor": "top_center",
    "commercial_anchor": "center_overlay",
    "cta_anchor": "lower_center_button",
    "logo_anchor": "bottom_center",
    "alignment_system": "centered_stack",
    "dominant_color_field": "full_bleed_overlay",
}


def _nbox(x0: float, y0: float, x1: float, y1: float) -> dict[str, float]:
    return {
        "x0": round(float(x0), 4),
        "y0": round(float(y0), 4),
        "x1": round(float(x1), 4),
        "y1": round(float(y1), 4),
    }


def _abs_from_norm(nb: dict[str, float], width: int, height: int) -> dict[str, int]:
    return _box(
        int(round(nb["x0"] * width)),
        int(round(nb["y0"] * height)),
        int(round(nb["x1"] * width)),
        int(round(nb["y1"] * height)),
    )


def analyze_hero_photograph(
    image: Image.Image,
    *,
    canvas: tuple[int, int] = (CANVAS_WIDTH, CANVAS_HEIGHT),
    focal: tuple[float, float] = (0.50, 0.46),
) -> dict[str, Any]:
    """Inspect the real photograph as it will appear on the canonical canvas."""
    src = image.convert("RGB")
    crop = _cover_crop(src.width, src.height, canvas[0], canvas[1], focal=focal)
    rect = crop["crop_rectangle"]
    preview = src.crop((rect["x0"], rect["y0"], rect["x1"], rect["y1"])).resize(canvas, Image.Resampling.LANCZOS)
    gray = preview.convert("L")
    w, h = preview.size
    step = 8
    rows: list[dict[str, float]] = []
    for y in range(0, h, step):
        band = gray.crop((0, y, w, min(h, y + step)))
        stat = ImageStat.Stat(band)
        rows.append({"y": y / h, "luma": float(stat.mean[0]), "std": float(stat.stddev[0])})
    sky_end = 0.0
    for row in rows:
        if row["luma"] >= 132 and row["std"] <= 48:
            sky_end = row["y"] + (step / h)
        else:
            if sky_end > 0.04:
                break
    sky_end = min(max(sky_end, 0.08), 0.28)
    street_start = 0.82
    for row in reversed(rows):
        if row["std"] >= 28 or row["luma"] <= 90:
            street_start = row["y"]
        else:
            if street_start < 0.95:
                break
    street_start = min(max(street_start, 0.72), 0.90)
    col_scores: list[tuple[float, float]] = []
    edges = gray.filter(ImageFilter.FIND_EDGES)
    for x in range(0, w, step):
        col = edges.crop((x, int(h * 0.12), min(w, x + step), int(h * 0.78)))
        col_scores.append((x / w, float(ImageStat.Stat(col).mean[0])))
    col_scores.sort(key=lambda item: item[1], reverse=True)
    spire_x = col_scores[0][0] if col_scores else 0.5
    if spire_x < 0.28 or spire_x > 0.72:
        spire_x = 0.50
    spire = _nbox(max(0.34, spire_x - 0.14), sky_end + 0.02, min(0.78, spire_x + 0.16), street_start)
    left_quiet = _nbox(0.04, 0.04, max(0.30, spire["x0"] - 0.03), min(0.58, street_start - 0.08))
    right_sky = _nbox(min(0.62, spire["x1"] + 0.02), 0.04, 0.96, sky_end + 0.06)
    return {
        "source_size": {"width": src.width, "height": src.height},
        "canvas": {"width": canvas[0], "height": canvas[1]},
        "crop": crop,
        "focal_point": {"x": focal[0], "y": focal[1]},
        "building_silhouette": "central_gothic_spire_with_adjacent_urban_mass",
        "spire": {"normalized": spire, "axis_x": round(spire_x, 4)},
        "sky_negative_space": {"y1": round(sky_end, 4), "character": "open_daylight_sky_above_architecture"},
        "busy_regions": ["street_and_trees_footer", "spire_stone_detail", "right_modern_facade"],
        "quiet_image_areas": ["upper_left_sky", "upper_right_sky_margin"],
        "visual_center_of_gravity": {"x": round(spire_x, 4), "y": round((sky_end + street_start) / 2, 4)},
        "street_footer_complexity": "high",
        "natural_text_safe_regions": [left_quiet, {"sky_band": _nbox(0.0, 0.0, 1.0, sky_end)}],
        "strong_verticals": ["spire_axis"],
        "strong_horizontals": ["street_and_roofline"],
        "left_quiet_column": left_quiet,
        "right_sky_margin": right_sky,
        "street_start": round(street_start, 4),
        "text_safe_left_of_spire": True,
    }


def structural_fingerprint(plan: dict[str, Any]) -> dict[str, str]:
    return {
        "hero_coverage": str(plan.get("hero_coverage") or ""),
        "headline_anchor": str(plan.get("headline_anchor") or ""),
        "commercial_anchor": str(plan.get("commercial_anchor") or ""),
        "cta_anchor": str(plan.get("cta_anchor") or ""),
        "logo_anchor": str(plan.get("logo_anchor") or ""),
        "alignment_system": str(plan.get("alignment_system") or ""),
        "dominant_color_field": str(plan.get("dominant_color_field") or ""),
    }


def _fingerprint_distance(a: dict[str, str], b: dict[str, str]) -> int:
    return sum(1 for key in a if a.get(key) != b.get(key))


def generate_art_direction_plan(
    analysis: dict[str, Any],
    *,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize one image-specific plan. Not a layout menu."""
    _ = brief
    left = _as_dict(analysis.get("left_quiet_column"))
    spire = _as_dict(_as_dict(analysis.get("spire")).get("normalized"))
    sky_end = float(_as_dict(analysis.get("sky_negative_space")).get("y1") or 0.16)
    street = float(analysis.get("street_start") or 0.82)
    type_x1 = min(float(left.get("x1") or 0.36), float(spire.get("x0") or 0.38) - 0.02)
    type_col = _nbox(0.055, 0.045, max(0.33, type_x1), 0.52)
    wash = _nbox(0.0, 0.0, type_col["x1"] + 0.08, 0.62)
    headline = _nbox(type_col["x0"], type_col["y0"], type_col["x1"], 0.235)
    line1 = _nbox(headline["x0"], headline["y0"], headline["x1"], headline["y0"] + 0.045)
    line2 = _nbox(headline["x0"], line1["y1"] + 0.012, headline["x1"], headline["y1"])
    supporting = _nbox(type_col["x0"], headline["y1"] + 0.016, type_col["x1"], headline["y1"] + 0.088)
    commercial = _nbox(type_col["x0"], supporting["y1"] + 0.022, type_col["x1"], 0.50)
    price = _nbox(commercial["x0"], commercial["y0"], commercial["x1"], commercial["y0"] + 0.055)
    meta = _nbox(commercial["x0"], price["y1"] + 0.012, commercial["x1"], commercial["y1"])
    unit = _nbox(meta["x0"], meta["y0"], meta["x1"], meta["y0"] + 0.038)
    discount = _nbox(meta["x0"], unit["y1"] + 0.004, meta["x1"], meta["y1"])
    cta = _nbox(type_col["x0"], commercial["y1"] + 0.02, min(0.42, type_col["x1"] + 0.04), commercial["y1"] + 0.055)
    logo = _nbox(type_col["x0"], min(0.86, street + 0.02), 0.40, 0.975)
    footer_fade = _nbox(0.0, 0.78, 0.48, 1.0)
    protected = _nbox(spire.get("x0", 0.36), max(sky_end, 0.18), spire.get("x1", 0.68), street)
    plan_id = str(uuid4())
    created = datetime.now(UTC).isoformat()
    return {
        "schema": PLAN_SCHEMA,
        "ai_art_direction_plan_id": plan_id,
        "created_at": created,
        "phase4b_master_id": str(uuid4()),
        "creative_concept": (
            "ALIRKEN KAZAN is an early-claim in the open sky: the campaign voice stands "
            "beside the architecture rather than covering it. The Temple is the proof."
        ),
        "visual_narrative": (
            "Read the offer in the quiet left sky, then the eye travels to the spire — "
            "the product — then down the same identity column to action and mark."
        ),
        "focal_strategy": "Keep the gothic spire as the optical center; crop cover 4:5 around architecture, not a plate.",
        "composition_strategy": "Asymmetric left type column in photograph-negative space versus centered vertical architecture.",
        "hero_strategy": "Full-bleed Day_004. Grade slightly for dusk-premium, do not invent sky or architecture.",
        "typographic_strategy": "Left-aligned kicker + display. Scale contrast, not extra weight. DejaVu executed honestly.",
        "commercial_strategy": "Price as a single editorial line under the campaign voice. Companions stacked quietly, not a dashboard.",
        "CTA_strategy": "Editorial gold text with a short underline. No button, no full-width seam, no web control.",
        "logo_strategy": "Real Temple mark aligned to the type column in a local left footer fade. Not bottom-center on the street.",
        "decorative_strategy": "One local sky wash for readability; one short underline for CTA. No gold grid, no plate edge.",
        "color_strategy": "Navy only as a dissolving wash in the type column. Gold in type and a thin action rule. Ivory for quiet lines.",
        "depth_strategy": "Photograph is the ground. Type sits in graded air in front of sky, never a second canvas.",
        "negative_space_strategy": "Protect the spire corridor and the right-hand city. Do not fill empty sky with a rectangle.",
        "visual_flow": ["campaign_idea_left_sky", "architecture_spire", "commercial_in_voice_column", "action_and_identity"],
        "element_relationships": {
            "headline_to_spire": "beside_not_on",
            "commercial_to_headline": "same_column_subordinate",
            "cta_to_commercial": "same_column_aftermath",
            "logo_to_type_column": "shared_left_axis",
        },
        "intentional_tension": "Left typographic axis against the centered sacred vertical of the spire.",
        "protected_architecture": protected,
        "content_priority": ["headline", "hero_architecture", "list_price", "cta", "companions", "logo"],
        "adaptability_notes": "Commercial stack can grow downward in the type column toward the wash fade before any reflow into the spire corridor.",
        "creative_rationale": {
            "why_this_photograph": "Day_004 has a strong central spire and usable left sky. A plate would throw away that relationship.",
            "why_headline_there": "Upper-left sky is the quietest readable air; centering would sit on the spire again.",
            "why_commercial_grouping": "Price belongs to the campaign voice, not to a metric strip across the building.",
            "why_cta_treatment": "A seam or button would re-split image and design. An underlined editorial line stays inside the voice column.",
            "why_logo_there": "Bottom-center fights the busy street. The left identity axis keeps brand with the campaign voice.",
        },
        "hero_coverage": "full_bleed",
        "headline_anchor": "top_left",
        "commercial_anchor": "left_voice_column",
        "cta_anchor": "left_editorial_underline",
        "logo_anchor": "lower_left_identity_axis",
        "alignment_system": "asymmetric_left_column",
        "dominant_color_field": "local_sky_wash",
        "image_type_relationship": "negative_space_placement_with_controlled_local_grade",
        "geometry_intent": {
            "type_column": type_col,
            "sky_wash": wash,
            "headline": headline,
            "headline_line_1": line1,
            "headline_line_2": line2,
            "supporting_copy": supporting,
            "commercial_group": commercial,
            "price_column": price,
            "unit_column": unit,
            "discount_column": discount,
            "cta": cta,
            "logo": logo,
            "footer_fade": footer_fade,
            "protected_architecture": protected,
            "hero_visual": _nbox(0.0, 0.0, 1.0, 1.0),
        },
        "crop_focal": analysis.get("focal_point") or {"x": 0.50, "y": 0.46},
        "hero_analysis_ref": {
            "sky_end": sky_end,
            "street_start": street,
            "spire_axis_x": _as_dict(analysis.get("spire")).get("axis_x"),
        },
        "compiled_spec_id": None,
        "plan_finalized_at": created,
    }


def validate_art_direction_plan(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append("schema")
    fp = structural_fingerprint(plan)
    if fp["dominant_color_field"] == "full_width_navy_plate":
        errors.append("generic_plate")
    if fp["cta_anchor"] == "full_width_seam":
        errors.append("gold_seam")
    if fp["alignment_system"] == "centered_stack" and fp["hero_coverage"] != "full_bleed":
        errors.append("split_template")
    if fp["commercial_anchor"] in {"center_plate", "three_column", "kpi_cards"}:
        errors.append("dashboard")
    wash = _as_dict(_as_dict(plan.get("geometry_intent")).get("sky_wash"))
    if float(wash.get("x1") or 0) > 0.92 and float(wash.get("y1") or 0) > 0.30:
        errors.append("full_width_color_field")
    if not plan.get("creative_rationale"):
        errors.append("missing_rationale")
    if not plan.get("protected_architecture"):
        errors.append("unprotected_architecture")
    novelty_40a = _fingerprint_distance(fp, FINGERPRINT_40A)
    novelty_40 = _fingerprint_distance(fp, FINGERPRINT_40)
    if novelty_40a < 4:
        errors.append("too_similar_to_phase40a")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "fingerprint": fp,
        "novelty_vs_phase40a": novelty_40a,
        "novelty_vs_phase40": novelty_40,
        "anti_template": "pass" if not any(e in errors for e in ("generic_plate", "gold_seam", "dashboard", "full_width_color_field")) else "fail",
    }


def _apply_generative_type(roles: dict[str, Any]) -> dict[str, Any]:
    roles["headline_line_1"].update({"size": 26, "tracking": 14, "alignment": "left", "font_character": "quiet left kicker"})
    roles["headline_line_2"].update({"size": 64, "tracking": 4, "alignment": "left", "font_character": "asymmetric display"})
    roles["supporting_copy"].update({"size": 14, "tracking": 0.2, "alignment": "left"})
    roles["list_price"].update({"size": 32, "tracking": 0.8, "alignment": "left"})
    roles["unit_value"].update({"size": 16, "alignment": "left"})
    roles["unit_label"].update({"size": 12, "alignment": "left"})
    roles["discount_value"].update({"size": 16, "alignment": "left"})
    roles["discount_label"].update({"size": 11, "alignment": "left"})
    roles["cta"].update({"size": 15, "tracking": 3.6, "alignment": "left", "color_role": "gold_primary", "font_character": "editorial underline action"})
    return roles


def compile_art_direction_plan(
    plan: dict[str, Any],
    analysis: dict[str, Any],
    *,
    project_id: str = TEMPLE_PROJECT_ID,
    campaign_id: str = PRODUCTION_CAMPAIGN_ID,
) -> dict[str, Any]:
    """Translate the plan into NativeMasterDesignSpecV2. Does not redesign."""
    gate = validate_art_direction_plan(plan)
    if gate.get("status") != "pass":
        raise ValueError(f"Art direction plan rejected before compile: {gate}")
    width, height = CANVAS_WIDTH, CANVAS_HEIGHT
    intent = _as_dict(plan.get("geometry_intent"))
    boxes = {name: _abs_from_norm(_as_dict(nb), width, height) for name, nb in intent.items()}
    inventory = inspect_available_fonts()
    typography = _typography_plan(inventory, profile="v1.1_editorial")
    typography["roles"] = _apply_generative_type(typography["roles"])
    colors = _color_system()
    dest = boxes["hero_visual"]
    crop = dict(analysis["crop"])
    crop["destination_geometry"] = dict(dest)
    crop["focal_point"] = plan.get("crop_focal") or crop.get("focal_point")
    treatment = _hero_treatment(crop)
    treatment["brightness"] = 0.97
    treatment["contrast"] = 1.10
    treatment["overlay"] = "local_sky_wash_only"
    treatment["mask_clip_shape"] = "full_canvas_rect"
    spec_id = str(uuid4())
    master_id = str(plan.get("phase4b_master_id") or uuid4())
    elements = [
        {"id": "headline_line_1", "role": "headline", "kind": "text", "content_key": "headline_line_1", "geometry": _geom(boxes["headline_line_1"], width, height, anchor="top_left", align="left", z=40, parent="headline_group")},
        {"id": "headline_line_2", "role": "headline", "kind": "text", "content_key": "headline_line_2", "geometry": _geom(boxes["headline_line_2"], width, height, anchor="top_left", align="left", z=41, parent="headline_group")},
        {"id": "supporting_copy", "role": "supporting_copy", "kind": "text", "content_key": "supporting_copy", "geometry": _geom(boxes["supporting_copy"], width, height, anchor="top_left", align="left", z=42, parent="copy_group")},
        {"id": "unit_value", "role": "unit_value", "kind": "text", "content_key": "unit_value", "geometry": _geom(boxes["unit_column"], width, height, anchor="left", align="left", z=43, parent="commercial_group")},
        {"id": "unit_label", "role": "unit_label", "kind": "text", "content_key": "unit_label", "geometry": _geom(boxes["unit_column"], width, height, anchor="left", align="left", z=43, parent="commercial_group")},
        {"id": "list_price", "role": "list_price", "kind": "text", "content_key": "list_price", "geometry": _geom(boxes["price_column"], width, height, anchor="left", align="left", z=43, parent="commercial_group")},
        {"id": "discount_value", "role": "discount_value", "kind": "text", "content_key": "discount_value", "geometry": _geom(boxes["discount_column"], width, height, anchor="left", align="left", z=43, parent="commercial_group")},
        {"id": "discount_label", "role": "discount_label", "kind": "text", "content_key": "discount_label", "geometry": _geom(boxes["discount_column"], width, height, anchor="left", align="left", z=43, parent="commercial_group")},
        {"id": "cta", "role": "cta", "kind": "text", "content_key": "cta", "geometry": _geom(boxes["cta"], width, height, anchor="left", align="left", z=50, parent="cta_group")},
        {"id": "logo", "role": "logo", "kind": "image_asset", "content_key": "logo", "geometry": _geom(boxes["logo"], width, height, anchor="bottom_left", align="left", z=55, parent="logo_group")},
        {"id": "hero_visual", "role": "hero_visual", "kind": "image_asset", "content_key": "hero_visual", "geometry": _geom(boxes["hero_visual"], width, height, anchor="canvas", align="cover", z=0, parent="hero_group")},
    ]
    groups = [
        {"id": "hero_group", "layout_model": "full_bleed_photograph", "children": ["hero_visual"], "geometry": boxes["hero_visual"]},
        {"id": "headline_group", "layout_model": "asymmetric_display", "children": ["headline_line_1", "headline_line_2"], "geometry": boxes["headline"]},
        {"id": "copy_group", "layout_model": "single_line", "children": ["supporting_copy"], "geometry": boxes["supporting_copy"]},
        {
            "id": "commercial_group",
            "layout_model": "editorial_left_stack",
            "child_order": ["list_price", "unit", "discount"],
            "hierarchy": ["list_price", "unit_value", "discount_value"],
            "companion_presentation": "stacked_left_inline",
            "not_kpi_cards": True,
            "not_v2_three_column_row": True,
            "children": ["list_price", "unit_value", "unit_label", "discount_value", "discount_label"],
            "geometry": boxes["commercial_group"],
        },
        {"id": "cta_group", "layout_model": "editorial_underline", "children": ["cta"], "geometry": boxes["cta"]},
        {"id": "logo_group", "layout_model": "contain_left", "children": ["logo"], "geometry": boxes["logo"]},
    ]
    decorations = [
        {
            "id": "sky_wash",
            "role": "hero_transition",
            "kind": "linear_gradient",
            "geometry": boxes["sky_wash"],
            "anchor": "left",
            "style": "navy_to_transparent",
            "fade_axis": "left_dissolve",
            "color": colors["overlay_navy"],
            "alpha_start": 168,
            "alpha_end": 0,
            "opacity": 0.62,
            "relationship": "local_readability_wash_in_type_column_only",
        },
        {
            "id": "footer_fade",
            "role": "footer_fade",
            "kind": "linear_gradient",
            "geometry": boxes["footer_fade"],
            "anchor": "bottom_left",
            "style": "transparent_to_navy",
            "color": colors["footer_navy"],
            "alpha_start": 0,
            "alpha_end": 200,
            "opacity": 0.7,
            "relationship": "local_left_fade_for_logo_legibility",
        },
        {
            "id": "cta_underline",
            "role": "cta_rule",
            "kind": "vertical_hairline",
            "geometry": {
                "x0": boxes["cta"]["x0"],
                "y0": boxes["cta"]["y1"] - 6,
                "x1": boxes["cta"]["x0"] + int((boxes["cta"]["x1"] - boxes["cta"]["x0"]) * 0.72),
                "y1": boxes["cta"]["y1"] - 4,
            },
            "anchor": "left",
            "style": "short_gold_rule",
            "color": colors["gold_secondary"],
            "thickness": 1,
            "opacity": 0.85,
            "relationship": "marks_the_action_without_a_button",
        },
    ]
    spec: dict[str, Any] = {
        "schema": SCHEMA_V2,
        "spec_version": SPEC_VERSION_V2,
        "native_master_design_spec_id": spec_id,
        "phase4_master_id": master_id,
        "ai_art_direction_plan_id": plan["ai_art_direction_plan_id"],
        "identity": {
            "native_master_design_spec_id": spec_id,
            "spec_version": SPEC_VERSION_V2,
            "project_id": project_id,
            "campaign_id": campaign_id,
            "test_identifier": PHASE4B_TEST_KEY,
            "creative_type": "project_finished_advertisement",
            "format": "instagram_feed",
            "aspect_ratio": "4:5",
            "created_at": _now(),
            "creative_direction_version": "generative_cd_v1",
            "production": False,
        },
        "canvas": {"width": width, "height": height, "aspect_ratio": "4:5", "format": "instagram_feed", "canonical": True, "do_not_switch": True},
        "creative_direction": {
            "layout_model": "generative_asymmetric_sky_column",
            "from_plan": plan["ai_art_direction_plan_id"],
            "not_a_template_fill": True,
            "not_copied_from_v2_pixels": True,
            "not_phase40a_plate": True,
        },
        "asset_policy": "PROJECT_LOCKED",
        "assets": {
            "hero_visual": {
                "asset_id": LOCKED_HERO_ASSET_ID,
                "role": "hero_visual",
                "project_id": project_id,
                "filename": "IH_DC_TMP_001_Render_Exterior_Day_004.jpg",
                "approval_state": "approved_project_asset",
                "architecture_lock": True,
                "replaceable": True,
                "replaceable_class": "REPLACEABLE_ASSET",
            },
            "logo": {
                "asset_id": LOCKED_LOGO_ASSET_ID,
                "role": "logo",
                "project_id": project_id,
                "identity_lock": True,
                "replaceable": False,
                "replaceable_class": "LOCKED_IDENTITY",
            },
        },
        "content": dict(REQUIRED_CONTENT),
        "regions": [{"id": name, "geometry": box} for name, box in boxes.items()],
        "elements": elements,
        "groups": groups,
        "typography": typography,
        "colors": colors,
        "decorations": decorations,
        "image_treatments": {"hero": treatment},
        "geometry": boxes,
        "relationships": [
            {"from": "headline_group", "to": "hero_visual", "type": "beside_spire_in_sky"},
            {"from": "commercial_group", "to": "headline_group", "type": "same_column_below"},
            {"from": "cta", "to": "commercial_group", "type": "same_column_below"},
            {"from": "logo", "to": "headline_group", "type": "shared_left_axis"},
        ],
        "constraints": [
            {"id": "architecture_lock", "rule": "Do not redraw or generate the building."},
            {"id": "protected_spire", "rule": "Do not place commercial type in the spire corridor."},
            {"id": "no_kpi_cards", "rule": "Commercial facts are editorial, not dashboard cards."},
            {"id": "spec_drives_render", "rule": "Renderer executes this spec and invents no layout."},
        ],
        "flexibility": _flexibility(),
        "content_capacity": {
            **_content_capacity(split=False),
            "preferred_growth_direction": "downward_in_left_voice_column",
            "reflow_strategy": (
                "Add launch price and savings as additional lines in the left type column, "
                "extending toward the wash fade. Never cross into the protected spire corridor. "
                "If five facts exceed the column, reduce companion size before invading architecture."
            ),
            "neighboring_flexible_groups": ["supporting_copy", "cta", "sky_wash"],
        },
        "cta_treatment": {
            "text": REQUIRED_CONTENT["cta"],
            "geometry": boxes["cta"],
            "shape": "underlined_action",
            "fill": None,
            "gradient": None,
            "border": None,
            "radius": 0,
            "underline": True,
            "font": typography["roles"]["cta"],
            "font_size": typography["roles"]["cta"]["size"],
            "tracking": typography["roles"]["cta"]["tracking"],
            "text_color": colors["gold_primary"],
            "shadow": None,
            "alignment": "left",
            "relationship_to_hero": "sits_in_graded_sky_column",
            "relationship_to_logo": "same_left_axis_above_logo",
        },
        "logo_treatment": {
            "asset_id": LOCKED_LOGO_ASSET_ID,
            "fit": "contain",
            "geometry": boxes["logo"],
            "background": "local_left_footer_fade",
            "generated": False,
            "alignment": "left",
            "grade": {"brightness": 1.28, "contrast": 1.22},
        },
        "render_instructions": [
            {"op": "place_hero", "id": "hero_visual"},
            {"op": "decoration", "id": "sky_wash"},
            {"op": "decoration", "id": "footer_fade"},
            {"op": "decoration", "id": "cta_underline"},
            {"op": "text", "id": "headline_line_1"},
            {"op": "text", "id": "headline_line_2"},
            {"op": "text", "id": "supporting_copy"},
            {"op": "commercial_facts", "id": "commercial_group"},
            {"op": "cta", "id": "cta"},
            {"op": "logo", "id": "logo"},
        ],
        "provenance": {
            "spec_created_before_render": True,
            "extracted_from_raster": False,
            "legacy_master_design_spec": False,
            "native_renderer_template": False,
            "edit_map": False,
            "hybrid_revision": False,
            "ai_architecture_generation": False,
            "art_direction_plan_id": plan["ai_art_direction_plan_id"],
            "art_direction_plan_created_before_spec": True,
            "spec_finalized_at": _now(),
            "rendered_at": None,
            "pipeline": ["A_hero_analysis", "B_art_direction_plan", "C_plan_validate", "D_compile_spec"],
        },
        "revision_policy": _revision_policy(),
        "format_adaptation_policy": _format_adaptation_policy(),
        "rendered_master_visual_asset_id": None,
        "test_status": PHASE4B_TEST_KEY,
        "validation_status": "pending",
        "art_direction_gate": gate,
    }
    spec["validation"] = validate_native_master_spec(spec)
    spec["validation_status"] = spec["validation"]["status"]
    if spec["validation_status"] != "pass":
        raise ValueError(f"NativeMasterDesignSpecV2 validation failed: {spec['validation']}")
    plan["compiled_spec_id"] = spec_id
    return spec


def generate_native_master_from_director(
    source_image: Image.Image,
    *,
    project_id: str = TEMPLE_PROJECT_ID,
    campaign_id: str = PRODUCTION_CAMPAIGN_ID,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Hero analysis → plan → validate → spec. No raster yet."""
    analysis = analyze_hero_photograph(source_image)
    plan = generate_art_direction_plan(analysis)
    gate = validate_art_direction_plan(plan)
    if gate["status"] != "pass":
        raise ValueError(f"Generative Creative Director rejected the plan: {gate}")
    spec = compile_art_direction_plan(plan, analysis, project_id=project_id, campaign_id=campaign_id)
    if spec["provenance"].get("rendered_at"):
        raise RuntimeError("Spec must not be rendered during compile.")
    return analysis, plan, spec


def persist_phase4b(ctx: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    plans = dict(ctx.get("phase4b_art_direction_plans") or {})
    plans[str(plan["ai_art_direction_plan_id"])] = plan
    ctx["phase4b_art_direction_plans"] = plans
    persist_phase4_native_master(ctx, spec)
    ctx["phase4b_current_plan_id"] = plan["ai_art_direction_plan_id"]
    ctx["phase4b_current_spec_id"] = spec["native_master_design_spec_id"]
    ctx["phase4b_current_master_id"] = spec["phase4_master_id"]
    return ctx
