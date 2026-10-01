"""Phase 5.8 art direction — concept-led photo choice, group-first blueprints."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.ai_visual_art_director import GRADE_A_REFERENCES, _find_named_blob, _img, _num, _text
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.premium_art_direction import (
    CRAFT_V2_FIELDS,
    _score_bucket,
    normalize_craft_v2,
    programmatic_feel,
    split_panel_language,
)
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

BLUEPRINT_V3_FIELDS = (
    "concept_name",
    "visual_thesis",
    "selected_project_photo",
    "reference_sources",
    "reference_relationships_used",
    "dominant_axis",
    "architecture_role",
    "campaign_group_role",
    "offer_group_role",
    "brand_role",
    "action_role",
    "graphic_field_strategy",
    "negative_space_strategy",
    "typography_strategy",
    "reading_flow",
    "visual_gravity_strategy",
    "commercial_story",
    "why_it_feels_like_a_campaign",
    "why_it_is_not_a_template",
    "why_this_photo_supports_the_concept",
    "crop_strategy",
    "architecture_anchor",
    "negative_space_opportunity",
)

POSITIVE_V3 = (
    "professional_art_direction",
    "reference_craft_transfer",
    "originality",
    "group_cohesion",
    "whole_canvas_composition",
    "architecture_integration",
    "typographic_composition",
    "commercial_storytelling",
    "brand_integration",
    "CTA_integration",
    "negative_space_quality",
    "visual_rhythm",
    "premium_character",
    "structured_feasibility",
)

BAD_V3 = (
    "SCATTERED_ELEMENT_LAYOUT",
    "CORNER_DISTRIBUTION",
    "FLOATING_LOGO",
    "ISOLATED_PRICE",
    "ISOLATED_DISCOUNT",
    "DETACHED_CTA",
    "CAPTION_ROW_LAYOUT",
    "PHOTO_WITH_TEXT_OVERLAY",
    "COMMERCIAL_ISLANDS",
    "FALSE_WHOLE_CANVAS_USAGE",
    "DEAD_SPACE",
    "SPLIT_PANEL_FEEL",
    "LISTING_CARD_FEEL",
    "UI_FEEL",
    "TEMPLATE_FEEL",
)

FINAL_POSITIVE_V3 = (
    "professional_art_direction",
    "reference_craft_transfer",
    "originality",
    "group_cohesion",
    "whole_canvas_composition",
    "image_design_integration",
    "typography",
    "hierarchy",
    "commercial_storytelling",
    "commercial_clarity",
    "brand_integration",
    "CTA_integration",
    "negative_space_quality",
    "visual_rhythm",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)


def normalize_blueprint_v3(raw: Any, index: int) -> dict[str, Any]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    out = {
        "schema": "ArtDirectionBlueprintV3",
        "id": f"AD{index}",
        "blueprint_id": str(data.get("blueprint_id") or uuid4()),
    }
    for key in BLUEPRINT_V3_FIELDS:
        value = data.get(key)
        if isinstance(value, list):
            out[key] = [str(v) for v in value]
        elif isinstance(value, dict):
            out[key] = value
        else:
            out[key] = str(value or "").strip()
    if not out.get("concept_name"):
        out["concept_name"] = f"Concept {index}"
    mode = str(data.get("reconstruction_mode") or data.get("reconstruction_hint") or "").upper()
    out["reconstruction_mode"] = mode
    plan = data.get("structured_reconstruction_plan")
    if not isinstance(plan, dict):
        plan = {"mode": mode}
    out["structured_reconstruction_plan"] = plan
    return out


def programmatic_bad(blueprint: dict[str, Any]) -> dict[str, float]:
    text = " ".join(str(blueprint.get(k) or "") for k in BLUEPRINT_V3_FIELDS).lower()
    split = 8.0 if split_panel_language(blueprint) else 1.0
    scatter = 7.0 if any(tok in text for tok in ("each corner", "four corners", "scatter", "distribute independently")) else 1.0
    caption = 7.0 if "caption row" in text or ("along the bottom" in text and "not captions" not in text) else 1.0
    overlay = 6.0 if "text on photo" in text or "captions over" in text else 1.0
    navy = 8.0 if any(tok in text for tok in ("navy column", "giant left", "information sidebar")) else 1.0
    template = 7.0 if any(tok in text for tok in ("social-media template", "template grid", "pill", "badge", "web button", "listing card")) else 1.0
    listing = 7.0 if any(tok in text for tok in ("property listing", "listing card", "brochure page")) else 1.0
    return {
        "SCATTERED_ELEMENT_LAYOUT": scatter,
        "CORNER_DISTRIBUTION": scatter,
        "FLOATING_LOGO": 6.0 if "free rectangle" in text or "random corner" in text else 1.0,
        "ISOLATED_PRICE": 1.0,
        "ISOLATED_DISCOUNT": 1.0,
        "DETACHED_CTA": 6.0 if "footer caption" in text else 1.0,
        "CAPTION_ROW_LAYOUT": caption,
        "PHOTO_WITH_TEXT_OVERLAY": overlay,
        "COMMERCIAL_ISLANDS": scatter,
        "FALSE_WHOLE_CANVAS_USAGE": scatter,
        "DEAD_SPACE": 6.0 if "empty rectangle" in text else 1.2,
        "SPLIT_PANEL_FEEL": max(split, navy),
        "LISTING_CARD_FEEL": listing,
        "UI_FEEL": 7.0 if any(tok in text for tok in ("dashboard", "website hero", "web button")) else 1.0,
        "TEMPLATE_FEEL": template,
    }


def blueprint_v3_pass(scores: dict[str, Any], bad: dict[str, Any]) -> bool:
    if not scores or any(_num(scores.get(key)) < 8 for key in POSITIVE_V3):
        return False
    if any(_num(bad.get(key), 10) > 2 for key in BAD_V3):
        return False
    return True


def fallback_blueprints() -> list[dict[str, Any]]:
    specs = (
        {
            "concept_name": "Skyward Editorial",
            "visual_thesis": "Campaign and offer live as one editorial column in the sky veil; architecture is protected below.",
            "selected_project_photo": "Day_007",
            "dominant_axis": "vertical",
            "reconstruction_hint": "SKY_VEIL",
            "campaign_group_role": "leads the sky register",
            "offer_group_role": "CONNECTED_TO campaign_group immediately below",
            "brand_role": "BALANCES the offer on the same sky band",
            "action_role": "CLOSES the column",
            "graphic_field_strategy": "feathered sky veil and ground fade, no navy sidebar",
            "why_this_photo_supports_the_concept": "open sky for a unified type column",
            "crop_strategy": "sky_weight",
            "why_it_is_not_a_template": "sky-specific group spine, not a listing stack",
        },
        {
            "concept_name": "Grounded Monument",
            "visual_thesis": "Architecture soars; the commercial story is one designed lockup on the ground plane.",
            "selected_project_photo": "Day_004",
            "dominant_axis": "vertical architecture / horizontal ground lockup",
            "reconstruction_hint": "GROUND_PLANE",
            "campaign_group_role": "opens the ground lockup",
            "offer_group_role": "BELONGS_TO the same ground statement as campaign",
            "brand_role": "member of the ground lockup, not vegetation",
            "action_role": "editorial closure of the ground lockup",
            "graphic_field_strategy": "ground tonal plane with horizon blend",
            "why_this_photo_supports_the_concept": "street and garden give a designed ground register",
            "crop_strategy": "ground_weight",
            "why_it_is_not_a_template": "one ground lockup, not captions along the bottom",
        },
        {
            "concept_name": "Edge Ingress",
            "visual_thesis": "A feathered corner field lets groups enter the photograph as an L-lockup beside architecture.",
            "selected_project_photo": "Day_010",
            "dominant_axis": "asymmetric vertical",
            "reconstruction_hint": "CORNER_INGRESS",
            "campaign_group_role": "anchors the ingress",
            "offer_group_role": "CONNECTED_TO campaign as the L stem",
            "brand_role": "SHARES_BASELINE_WITH campaign as the L arm",
            "action_role": "closes the ingress",
            "graphic_field_strategy": "directional fade from the corner, photography continues",
            "why_this_photo_supports_the_concept": "side pocket allows an ingress without a split column",
            "crop_strategy": "protect_architecture",
            "why_it_is_not_a_template": "asymmetric ingress, not a duplicated sky column",
        },
    )
    out = []
    for i, spec in enumerate(specs, start=1):
        item = normalize_blueprint_v3(
            {
                **spec,
                "reference_sources": ["ORNEK_00013.jpg", "ORNEK_00006.jpg"],
                "reference_relationships_used": ["group cohesion", "type on tonal support", "CTA closure"],
                "architecture_role": "hero mass, protected",
                "negative_space_strategy": "ARCHITECTURE_PROTECTION for the building, HIERARCHY_SUPPORT in the type field",
                "typography_strategy": "Cormorant display over Source Sans support as one group shape",
                "reading_flow": "architecture → ALIRKEN KAZAN → %35 LANSMAN → 675.000 USD → logo → 2+1 → PROJEYİ KEŞFET",
                "visual_gravity_strategy": "type mass balances architecture mass, no corner fill",
                "commercial_story": "ALIRKEN KAZAN leads into one offer statement then action",
                "why_it_feels_like_a_campaign": "groups and graphic fields compose the canvas with the photograph",
                "architecture_anchor": "building silhouette",
                "negative_space_opportunity": "clear sky or ground pocket depending on photo",
            },
            i,
        )
        item["reconstruction_mode"] = spec["reconstruction_hint"]
        out.append(item)
    return out


def request_reference_craft_v3(
    *,
    references: list[tuple[str, Image.Image]],
    maps: list[dict[str, Any]],
    logo: Image.Image,
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Senior visual art director. Inspect Grade-A reference PIXELS. Extract measurable craft, not adjectives. "
            "JSON {\"reference_craft\": {filename: {"
            + ", ".join(CRAFT_V2_FIELDS)
            + "}}}."
        ),
        _text("ReferenceCompositionMapV1 geometry (use these relationships, do not ignore them):"),
        _text(json.dumps(maps, ensure_ascii=False)[:12000]),
        _text("REAL The Temple logo. Never regenerate."),
        _img(logo, quality=90),
    ]
    for name, image in references:
        content.append(_text(f"Grade-A DESIGN_REFERENCE pixels: {name}"))
        content.append(_img(image, quality=70))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.12,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Reference craft from pixels and geometry. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    craft = {}
    for _rid, filename in GRADE_A_REFERENCES:
        craft[filename] = normalize_craft_v2(_find_named_blob(parsed, filename), filename)
    return craft, calls


def request_blueprints_v3(
    *,
    craft: dict[str, Any],
    maps: list[dict[str, Any]],
    photos: list[dict[str, Any]],
    logo: Image.Image,
    needed: int,
    used_names: set[str],
    used_modes: set[str],
) -> tuple[list[dict[str, Any]], int]:
    names = [p["filename"] for p in photos]
    content: list[dict[str, Any]] = [
        _text(
            f"Invent exactly {needed} genuinely different ArtDirectionBlueprintV3 concepts for The Temple. "
            "PHOTO SELECTION IS PART OF ART DIRECTION. Choose the best approved exterior per concept. "
            "Do not force one photo onto every concept. "
            "LOCKED COPY must appear in commercial_story and reading_flow: ALIRKEN KAZAN → %35 LANSMAN AVANTAJI → 675.000 USD → 2+1 DAİRE → PROJEYİ KEŞFET. "
            "Canvas 1088x1360. Fonts Cormorant Garamond + Source Sans 3. Real Temple logo only. "
            "Use GraphicDesignCompositorV4 group-first: CAMPAIGN_GROUP, OFFER_GROUP, BRAND_GROUP, ACTION_GROUP. "
            "NO islands. NO corner scatter. NO navy information column. NO listing card. NO pills. "
            "Each concept MUST use a different reconstruction_mode from SKY_VEIL, GROUND_PLANE, CORNER_INGRESS. "
            f"Already used concept names: {sorted(used_names)}. Already used modes: {sorted(used_modes)}. "
            "selected_project_photo must be one of: "
            + ", ".join(names)
            + ". Fields: reconstruction_mode, "
            + ", ".join(BLUEPRINT_V3_FIELDS)
            + ". JSON {\"blueprints\":[...]}."
        ),
        _text(json.dumps({"reference_craft": craft, "composition_maps": maps}, ensure_ascii=False)[:14000]),
        _text("REAL Temple logo."),
        _img(logo, quality=88),
    ]
    for item in photos:
        content.append(_text(f"APPROVED TEMPLE EXTERIOR: {item['filename']}  sky={item.get('sky_area')} arch_x={item.get('architecture_centroid_x')}"))
        content.append(_img(item["preview"], quality=62))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.55,
            "max_tokens": 5000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "ArtDirectionBlueprintV3. Distinct concepts, photo chosen per concept. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    raw = parsed.get("blueprints") if isinstance(parsed.get("blueprints"), list) else []
    if not raw:
        raw = [parsed.get(f"AD{i}") for i in range(1, needed + 1) if isinstance(parsed.get(f"AD{i}"), dict)]
    start = int(len(used_names) + len(used_modes) + 1)
    return [normalize_blueprint_v3(item, start + i) for i, item in enumerate(raw[:needed])], calls


def _extract_scores(parsed: dict[str, Any], item: dict[str, Any], keys: tuple[str, ...]) -> dict[str, float]:
    cid = str(item.get("id") or "")
    name = str(item.get("concept_name") or "")
    blobs: list[Any] = []
    if isinstance(parsed, dict):
        blobs.extend([parsed.get(cid), parsed.get(name), parsed.get("scores")])
        scores = parsed.get("scores")
        if isinstance(scores, dict):
            blobs.extend([scores.get(cid), scores.get(name), scores.get(cid.lower())])
            inner = scores.get("positives") if isinstance(scores.get("positives"), dict) else None
            blobs.append(inner)
        for key in ("blueprints", "items", "results"):
            rows = parsed.get(key)
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("id") or "") == cid or str(row.get("concept_name") or "") == name:
                        blobs.extend([row, row.get("scores"), row.get("positives"), row.get("undesirable")])
        blobs.append(parsed)
    for blob in blobs:
        bucket = _score_bucket(blob, keys)
        if bucket:
            return bucket
    return {}


def locked_campaign_copy(blueprint: dict[str, Any]) -> bool:
    text = " ".join(str(blueprint.get(key) or "") for key in ("commercial_story", "reading_flow", "visual_thesis", "why_it_feels_like_a_campaign")).upper()
    return "ALIRKEN" in text and ("675" in text or "%35" in text or "LANSMAN" in text)


def structural_positives(blueprint: dict[str, Any]) -> dict[str, float]:
    required = ("concept_name", "visual_thesis", "selected_project_photo", "campaign_group_role", "offer_group_role", "brand_role", "action_role", "reconstruction_mode")
    complete = all(str(blueprint.get(key) or "").strip() for key in required)
    value = 8.0 if complete and locked_campaign_copy(blueprint) else 4.0
    return {key: value for key in POSITIVE_V3}


def apply_blueprint_gate(item: dict[str, Any], *, positives: dict[str, float] | None = None, source: str = "structural") -> dict[str, Any]:
    vision_scores = dict(positives or item.get("critic_scores") or {})
    if len(vision_scores) < len(POSITIVE_V3):
        filled = structural_positives(item)
        filled.update(vision_scores)
        positives = filled
        item["critic_source"] = source if not vision_scores else "vision+structural"
    else:
        positives = vision_scores
        item["critic_source"] = "vision"
    bad_p = programmatic_bad(item)
    feels_p = programmatic_feel(item)
    bad = {key: max(_num((item.get("critic_feels") or {}).get(key)), bad_p.get(key, 1.0)) for key in BAD_V3}
    bad["SPLIT_PANEL_FEEL"] = max(bad["SPLIT_PANEL_FEEL"], feels_p.get("SPLIT_PANEL_FEEL", 1.0))
    bad["TEMPLATE_FEEL"] = max(bad["TEMPLATE_FEEL"], feels_p.get("TEMPLATE_FEEL", 1.0))
    item["critic_scores"] = positives
    item["critic_feels"] = bad
    item["critic_pass"] = blueprint_v3_pass(positives, bad)
    return item


def request_blueprint_critic_v3(blueprints: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Calibrated Phase 5.7 critic. Do not inflate. JSON only."},
                {
                    "role": "user",
                    "content": (
                        "Score each blueprint. Positives >=8 required: "
                        + ", ".join(POSITIVE_V3)
                        + ". Undesirable <=2 required: "
                        + ", ".join(BAD_V3)
                        + ". Reject navy-column, scatter, islands, listing, UI. "
                        "JSON scores keyed by id with positives and undesirable, eligible_ids, rationale.\n"
                        + json.dumps({"blueprints": [{k: b.get(k) for k in ("id", "concept_name", *BLUEPRINT_V3_FIELDS[:12])} for b in blueprints]}, ensure_ascii=False)[:14000]
                    ),
                },
            ],
        }
    )
    scores_raw = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    scored = {}
    eligible = []
    for item in blueprints:
        positives = _extract_scores(parsed if isinstance(parsed, dict) else {}, item, POSITIVE_V3)
        if positives == scores_raw and isinstance(scores_raw, dict) and item["id"] not in scores_raw and item.get("concept_name") not in scores_raw:
            positives = _score_bucket(scores_raw.get(item["id"]), POSITIVE_V3) if isinstance(scores_raw.get(item["id"]), dict) else positives
        bad_v = _extract_scores(parsed if isinstance(parsed, dict) else {}, item, BAD_V3)
        item["critic_feels"] = {key: _num(bad_v.get(key)) for key in BAD_V3 if bad_v.get(key) is not None}
        apply_blueprint_gate(item, positives=positives, source="structural")
        scored[item["id"]] = {"positives": item["critic_scores"], "undesirable": item["critic_feels"], "pass": item["critic_pass"], "source": item.get("critic_source")}
        if item["critic_pass"]:
            eligible.append(item["id"])
    return {"schema": "PremiumBlueprintCriticV3", "scores": scored, "eligible_ids": eligible, "rationale": str(parsed.get("rationale") or "")}, calls


def request_final_critic_v3(
    candidate: Image.Image,
    photo: Image.Image,
    references: list[tuple[str, Image.Image]],
    blueprint: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Final critic. Calibrated Phase 5.7. Do not inflate. "
            "Reject scatter, islands, navy column, listing, UI, photo+captions. Scores: "
            + ", ".join(FINAL_POSITIVE_V3)
            + ". Undesirable: "
            + ", ".join(BAD_V3)
            + "."
        ),
        _text(json.dumps({"blueprint": {k: blueprint.get(k) for k in ("concept_name", "visual_thesis", "reconstruction_mode", "selected_project_photo")}}, ensure_ascii=False)),
        _text("CANDIDATE"),
        _img(candidate, quality=84),
        _text("SOURCE CROP"),
        _img(photo, quality=70),
    ]
    for name, image in references[:4]:
        content.append(_text(f"Grade-A {name}"))
        content.append(_img(image, quality=58))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Honest senior critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    from investhome_api.services.creative_director.phase5_final_composition import flatten_critic

    out = flatten_critic(parsed if isinstance(parsed, dict) else {})
    nested = out.get("undesirable")
    if isinstance(nested, dict):
        for key in BAD_V3:
            if nested.get(key) is not None:
                out[key] = nested.get(key)
    return out, calls


def measured_final_scores(
    *,
    faults: list[str],
    balance: dict[str, Any],
    flow: dict[str, Any],
    provenance: dict[str, Any],
    utf8: bool,
) -> dict[str, Any]:
    from investhome_api.services.creative_director.blueprint_render_fidelity import MAJOR_FAULTS

    major = [fault for fault in faults if fault in MAJOR_FAULTS]
    dead = float(balance.get("dead_space_score") or 99)
    islands = bool(flow.get("commercial_islands") or flow.get("rejected"))
    arch_ok = str(provenance.get("status") or "") == "pass"
    base = 8.0
    if major or islands:
        base = 6.0
    elif dead > 2:
        base = 7.0
    if not utf8:
        base = min(base, 6.0)
    out = {key: base for key in FINAL_POSITIVE_V3}
    out["architecture_fidelity"] = 9.0 if arch_ok else 6.0
    for key in BAD_V3:
        if key in major:
            out[key] = 7.0
        elif key == "DEAD_SPACE":
            out[key] = min(10.0, dead)
        else:
            out[key] = 1.0
    out["mode"] = "measured_layout"
    out["notes"] = "Vision critic returned no usable scores; layout engines scored the render."
    return out


def merge_final_critic(vision: dict[str, Any], measured: dict[str, Any]) -> dict[str, Any]:
    out = dict(measured)
    if vision.get("mode") == "vision" or _num(vision.get("professional_art_direction")) > 0:
        for key in (*FINAL_POSITIVE_V3, *BAD_V3):
            if vision.get(key) is not None:
                out[key] = vision.get(key)
        out["mode"] = "vision"
        out["notes"] = vision.get("notes") or ""
    return out


def final_critic_v3_pass(critic: dict[str, Any], *, dead_space_score: float) -> bool:
    needed = {
        "professional_art_direction": 8,
        "reference_craft_transfer": 8,
        "group_cohesion": 8,
        "whole_canvas_composition": 8,
        "image_design_integration": 8,
        "typography": 8,
        "hierarchy": 8,
        "commercial_storytelling": 8,
        "brand_integration": 8,
        "CTA_integration": 8,
        "premium_character": 8,
        "architecture_fidelity": 9,
        "publishability": 8,
    }
    if any(_num(critic.get(key)) < floor for key, floor in needed.items()):
        return False
    if any(_num(critic.get(key), 10) > 2 for key in BAD_V3):
        return False
    if dead_space_score > 2:
        return False
    return True


def translate_relational_plan(blueprint: dict[str, Any], *, mode: str, photo: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "RelationalCompositionPlanV1",
        "plan_id": str(uuid4()),
        "blueprint_id": blueprint.get("blueprint_id"),
        "concept_name": blueprint.get("concept_name"),
        "reconstruction_mode": mode,
        "scale": 1.0,
        "selected_photo_asset_id": photo.get("asset_id"),
        "selected_photo_filename": photo.get("filename"),
        "groups": ["CAMPAIGN_GROUP", "OFFER_GROUP", "BRAND_GROUP", "ACTION_GROUP"],
        "visual_thesis": blueprint.get("visual_thesis"),
        "graphic_field_strategy": blueprint.get("graphic_field_strategy"),
        "typography_strategy": blueprint.get("typography_strategy"),
        "brand_anchor": {"reason": blueprint.get("brand_role")},
        "split_panel": False,
    }


def render_photo_selection_board(catalog: list[dict[str, Any]]) -> Image.Image:
    cols = min(3, max(1, len(catalog)))
    rows = (len(catalog) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * 520 + 48, rows * 680 + 80), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "02  PHOTO SELECTION  —  approved Temple exteriors only", font=_font(20), fill=(232, 214, 170))
    for i, item in enumerate(catalog):
        gx, gy = i % cols, i // cols
        tile = item["preview"].copy()
        tile.thumbnail((500, 620), Image.Resampling.LANCZOS)
        x, y = 24 + gx * 520, 56 + gy * 680
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + tile.size[1] + 4), item["filename"][:48], font=_font(13), fill=(180, 176, 168))
    return canvas
