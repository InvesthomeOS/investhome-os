"""AIVisualArtDirectorV1 — creative direction first, compositor execution second.

Vision may see, analyze, design, and critique. It must not paint or generate pixels.
"""

from __future__ import annotations

import base64
import io
import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.contiguous_content_fit import largest_safe_rect
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

GRADE_A_REFERENCES = (
    ("8ee69d5b-b734-57e8-a9dd-06b8a15a4e57", "ORNEK_00013.jpg"),
    ("3a3c4832-a8c1-5a43-a518-d895ee78fbe1", "ORNEK_00001.jpg"),
    ("15e71ec3-ff92-5604-84aa-2582510d0615", "ORNEK_00006.jpg"),
    ("b57f0ba1-3cc7-583c-98a8-c4330a7e4cdd", "ORNEK_00015.jpg"),
    ("a1046460-04ad-5ef1-bd42-88042c4d9760", "ORNEK_00011.jpg"),
    ("1d0e8a8e-03e9-5ba1-bf25-b61c523ed6d2", "ORNEK_00008.jpg"),
)

BLUEPRINT_FIELDS = (
    "concept_name",
    "one_sentence_idea",
    "visual_axis",
    "photo_role",
    "headline_role",
    "commercial_offer_role",
    "logo_role",
    "cta_role",
    "tonal_treatment",
    "typographic_character",
    "gold_usage",
    "negative_space_strategy",
    "image_design_integration_strategy",
    "reading_order",
    "group_relationships",
    "intended_visual_tension",
    "why_it_fits_day_007",
    "borrowed_reference_craft",
    "deliberately_not_copied",
)

CRAFT_FIELDS = (
    "dominant_visual_axis",
    "photo_design_relationship",
    "headline_scale_relationship",
    "commercial_number_behavior",
    "logo_behavior",
    "cta_behavior",
    "alignment_system",
    "negative_space_behavior",
    "edge_behavior",
    "type_density",
    "gold_usage",
    "visual_tension",
    "asymmetry_or_symmetry",
    "hierarchy",
    "what_makes_it_designed",
)

TARGET_FIELDS = (
    "primary_architectural_hero",
    "spire",
    "visual_center",
    "visual_weight",
    "usable_sky",
    "quiet_regions",
    "noisy_regions",
    "perspective",
    "natural_reading_direction",
    "where_type_enhances",
    "where_type_damages",
    "where_brand_can_sign",
    "where_commercial_belongs",
)

POSITIVE_CRITIC = (
    "originality",
    "reference_craft_understanding",
    "photo_integration",
    "architectural_respect",
    "visual_hierarchy",
    "commercial_storytelling",
    "brand_integration",
    "cta_integration",
    "premium_character",
    "whole_canvas_composition",
    "production_feasibility",
)

RISK_CRITIC = ("listing_layout_risk", "template_risk", "text_dump_risk", "UI_risk")
RISK_MAX = {"listing_layout_risk": 2, "template_risk": 3, "text_dump_risk": 2, "UI_risk": 2}

FIDELITY_KEYS = (
    "visual_axis_fidelity",
    "hierarchy_fidelity",
    "group_relationship_fidelity",
    "photo_integration_fidelity",
    "commercial_storytelling_fidelity",
    "brand_relationship_fidelity",
    "cta_relationship_fidelity",
    "overall_concept_fidelity",
)

FINAL_POSITIVE = (
    "professional_art_direction",
    "reference_craft_transfer",
    "blueprint_fidelity",
    "composition",
    "whole_canvas_composition",
    "image_design_integration",
    "typography",
    "hierarchy",
    "commercial_storytelling",
    "commercial_clarity",
    "logo_integration",
    "cta_integration",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)

FINAL_BAD = (
    "TEXT_ON_PHOTO_FEEL",
    "TEMPLATE_FEEL",
    "LISTING_CARD_FEEL",
    "UI_FEEL",
    "TEXT_DUMP_FEEL",
    "CLUTTER",
)


def _jpeg_b64(image: Image.Image, quality: int = 78) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _img(image: Image.Image, *, quality: int = 78) -> dict[str, Any]:
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(image, quality)}", "detail": "high"},
    }


def _text(text: str) -> dict[str, str]:
    return {"type": "text", "text": text}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_craft(raw: Any, filename: str) -> dict[str, Any]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    nested = data.get("craft") if isinstance(data.get("craft"), dict) else {}
    if nested:
        merged = {**nested, **{k: v for k, v in data.items() if k != "craft"}}
        data = merged
    aliases = {
        "dominant_visual_axis": ("axis", "visual_axis", "dominant_axis"),
        "photo_design_relationship": ("photo_relationship", "photo_role", "photo_design"),
        "headline_scale_relationship": ("headline_scale", "headline", "type_scale"),
        "commercial_number_behavior": ("commercial_numbers", "numbers", "price_behavior"),
        "logo_behavior": ("logo", "brand_behavior"),
        "cta_behavior": ("cta",),
        "alignment_system": ("alignment",),
        "negative_space_behavior": ("negative_space", "negative_space_strategy"),
        "edge_behavior": ("edges", "edge"),
        "type_density": ("density",),
        "gold_usage": ("gold",),
        "visual_tension": ("tension",),
        "asymmetry_or_symmetry": ("symmetry", "asymmetry"),
        "hierarchy": ("visual_hierarchy",),
        "what_makes_it_designed": ("designed_because", "craft_signature", "why_designed"),
    }
    out = {"schema": "VisualReferenceCraftAnalysisV1", "filename": filename}
    for key in CRAFT_FIELDS:
        value = data.get(key)
        if value in (None, ""):
            for alias in aliases.get(key, ()):
                if data.get(alias) not in (None, ""):
                    value = data.get(alias)
                    break
        out[key] = str(value or "").strip()
    return out


def normalize_target(raw: Any) -> dict[str, Any]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    aliases = {
        "primary_architectural_hero": ("hero", "primary_hero", "architecture_hero"),
        "visual_center": ("center",),
        "visual_weight": ("weight",),
        "usable_sky": ("sky",),
        "quiet_regions": ("quiet",),
        "noisy_regions": ("noisy",),
        "natural_reading_direction": ("reading_direction",),
        "where_type_enhances": ("type_enhances", "typography_enhances"),
        "where_type_damages": ("type_damages", "typography_damages"),
        "where_brand_can_sign": ("brand_signature", "logo_placement"),
        "where_commercial_belongs": ("commercial_placement",),
    }
    out = {"schema": "TargetImageArtDirectionAnalysisV1"}
    for key in TARGET_FIELDS:
        value = data.get(key)
        if value in (None, ""):
            for alias in aliases.get(key, ()):
                if data.get(alias) not in (None, ""):
                    value = data.get(alias)
                    break
        out[key] = str(value or "").strip()
    return out


def _pick(data: dict[str, Any], key: str, aliases: tuple[str, ...] = ()) -> Any:
    if data.get(key) not in (None, ""):
        return data.get(key)
    for alias in aliases:
        if data.get(alias) not in (None, ""):
            return data.get(alias)
    nested = data.get("blueprint") if isinstance(data.get("blueprint"), dict) else {}
    if nested.get(key) not in (None, ""):
        return nested.get(key)
    return data.get(key)


def normalize_blueprint(raw: Any, index: int) -> dict[str, Any]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    aliases = {
        "concept_name": ("concept", "name", "title"),
        "one_sentence_idea": ("idea", "one_sentence", "sentence", "thesis"),
        "visual_axis": ("axis", "dominant_axis"),
        "photo_role": ("photo",),
        "headline_role": ("headline", "display_role"),
        "commercial_offer_role": ("commercial", "offer_role"),
        "logo_role": ("logo", "brand_role"),
        "cta_role": ("cta",),
        "borrowed_reference_craft": ("borrowed", "reference_principles"),
        "deliberately_not_copied": ("not_copied", "avoids"),
    }
    out = {
        "schema": "ArtDirectionBlueprintV1",
        "id": f"AD{index}",
        "blueprint_id": str(data.get("blueprint_id") or uuid4()),
    }
    for key in BLUEPRINT_FIELDS:
        value = _pick(data, key, aliases.get(key, ()))
        if key == "reading_order" and isinstance(value, list):
            out[key] = [str(item) for item in value]
        else:
            out[key] = value if isinstance(value, (str, list, dict)) else str(value or "").strip()
    if not out.get("concept_name"):
        out["concept_name"] = f"Concept {index}"
    return out


def _find_named_blob(blob: Any, filename: str) -> dict[str, Any]:
    stem = filename.split(".")[0].lower()
    if isinstance(blob, dict):
        for key, value in blob.items():
            if stem in str(key).lower() and isinstance(value, dict):
                return value
        for key in ("filename", "name", "file"):
            if stem in str(blob.get(key) or "").lower():
                return blob
        for value in blob.values():
            found = _find_named_blob(value, filename)
            if found:
                return found
    if isinstance(blob, list):
        for item in blob:
            found = _find_named_blob(item, filename)
            if found:
                return found
    return {}


def _coalesce_target(parsed: dict[str, Any]) -> dict[str, Any]:
    for key in ("target_analysis", "day_007", "day007", "target", "image_analysis", "photo_analysis"):
        value = parsed.get(key)
        if isinstance(value, dict) and any(value.get(f) for f in TARGET_FIELDS):
            return value
    return parsed.get("target_analysis") or parsed.get("day_007") or {}


def _coalesce_blueprints(parsed: dict[str, Any]) -> list[Any]:
    raw = parsed.get("blueprints") or parsed.get("concepts")
    if isinstance(raw, dict):
        ordered = [raw.get(f"AD{i}") or raw.get(str(i)) for i in range(1, 4)]
        raw = [item for item in ordered if item]
    if not isinstance(raw, list) or not raw:
        raw = [parsed.get(f"AD{i}") for i in range(1, 4) if isinstance(parsed.get(f"AD{i}"), dict)]
    return raw if isinstance(raw, list) else []
    raw = parsed.get("blueprints") or parsed.get("concepts")
    if isinstance(raw, dict):
        ordered = [raw.get(f"AD{i}") or raw.get(str(i)) for i in range(1, 4)]
        raw = [item for item in ordered if item]
    if not isinstance(raw, list) or not raw:
        raw = [parsed.get(f"AD{i}") for i in range(1, 4) if isinstance(parsed.get(f"AD{i}"), dict)]
    return raw if isinstance(raw, list) else []


def request_art_direction(
    *,
    day007: Image.Image,
    logo: Image.Image,
    references: list[tuple[str, Image.Image]],
    occupancy_board: Image.Image,
) -> tuple[dict[str, Any], int]:
    calls = 0
    analysis_content: list[dict[str, Any]] = [
        _text(
            "You are a senior visual art director. First ANALYZE only. Do not invent the campaign yet. "
            "Inspect every Grade-A reference as actual pixels. Describe observable craft relationships, not adjectives. "
            "Then analyze Day_007 as a designer: hero, spire, visual center, usable sky, where type would enhance or damage. "
            "Occupancy visualization is architecture protection context only — do not merely repeat measurements. "
            "JSON: {\"reference_craft\": {\"ORNEK_00013.jpg\": {dominant_visual_axis, photo_design_relationship, "
            "headline_scale_relationship, commercial_number_behavior, logo_behavior, cta_behavior, alignment_system, "
            "negative_space_behavior, edge_behavior, type_density, gold_usage, visual_tension, asymmetry_or_symmetry, "
            "hierarchy, what_makes_it_designed}, ...all six filenames...}, "
            "\"target_analysis\": {primary_architectural_hero, spire, visual_center, visual_weight, usable_sky, "
            "quiet_regions, noisy_regions, perspective, natural_reading_direction, where_type_enhances, "
            "where_type_damages, where_brand_can_sign, where_commercial_belongs}}. "
            "Each craft value must be a concrete visible relationship, not an adjective."
        ),
        _text("TARGET Day_007 cropped 4:5. Only project photo."),
        _img(day007, quality=84),
        _text("Architecture protection occupancy visualization. Not the design."),
        _img(occupancy_board, quality=70),
        _text("REAL Temple logo."),
        _img(logo, quality=90),
    ]
    for name, image in references:
        analysis_content.append(_text(f"Grade-A DESIGN_REFERENCE pixels: {name}. Inspect the actual design."))
        analysis_content.append(_img(image, quality=72))
    analysis_payload = {
        "model": VISION_MODEL,
        "temperature": 0.2,
        "max_tokens": 3500,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "VisualReferenceCraftAnalysisV1 + TargetImageArtDirectionAnalysisV1. JSON only. Observable relationships, not adjectives."},
            {"role": "user", "content": analysis_content},
        ],
    }
    analysis, n = _vision(analysis_payload)
    calls += n
    craft = {}
    for _asset, filename in GRADE_A_REFERENCES:
        entry = _find_named_blob(analysis, filename)
        craft[filename] = normalize_craft(entry, filename)
    target = normalize_target(_coalesce_target(analysis))
    blueprint_content: list[dict[str, Any]] = [
        _text(
            "You already analyzed the references and Day_007. Now invent exactly THREE genuinely different "
            "ArtDirectionBlueprintV1 concepts. Relational language only. No pixel coordinates. No rendered ads. "
            "Campaign copy locked: ALIRKEN KAZAN / 2+1 DAİRE / 675.000 USD / %35 / LANSMAN AVANTAJI / PROJEYİ KEŞFET. "
            "Canvas 1088x1360 4:5. Fonts: Cormorant Garamond + Source Sans 3. "
            "Compositor can execute a single-side editorial lockup, inward logo signature, photographic edge darkening, "
            "relational spacing, commercial numbers, contrast, collision. It cannot invent the concept. "
            "ANTI-PATTERNS: left dump + right headline; tiny corner lockup; unused giant photo with tiny type; "
            "independent floating logo; detached CTA; six unrelated rows; listing/brochure/dashboard; "
            "card/pill/badge/medallion; type parked on empty pixels. Use the WHOLE canvas compositionally. "
            "Each blueprint MUST include every field: concept_name, one_sentence_idea, visual_axis, photo_role, "
            "headline_role, commercial_offer_role, logo_role, cta_role, tonal_treatment, typographic_character, "
            "gold_usage, negative_space_strategy, image_design_integration_strategy, reading_order, "
            "group_relationships, intended_visual_tension, why_it_fits_day_007, borrowed_reference_craft, "
            "deliberately_not_copied. JSON: {\"blueprints\":[AD1,AD2,AD3]}."
        ),
        _text(json.dumps({"reference_craft": craft, "target_analysis": target}, ensure_ascii=False)[:11000]),
        _text("TARGET Day_007 again."),
        _img(day007, quality=78),
        _text("REAL Temple logo."),
        _img(logo, quality=88),
    ]
    for name, image in references[:3]:
        blueprint_content.append(_text(f"Keep this Grade-A reference in view: {name}"))
        blueprint_content.append(_img(image, quality=62))
    blueprint_payload = {
        "model": VISION_MODEL,
        "temperature": 0.45,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Senior visual art director. Three ArtDirectionBlueprintV1 objects. JSON only. No coordinates."},
            {"role": "user", "content": blueprint_content},
        ],
    }
    invented, n = _vision(blueprint_payload)
    calls += n
    blueprints_raw = _coalesce_blueprints(invented if invented else analysis)
    blueprints = [normalize_blueprint(item, idx + 1) for idx, item in enumerate(blueprints_raw[:3])]
    while len(blueprints) < 3:
        blueprints.append(normalize_blueprint({}, len(blueprints) + 1))
    return {
        "schema": "AIVisualArtDirectorV1",
        "reference_craft": craft,
        "target_analysis": target,
        "blueprints": blueprints,
        "mode": "vision" if (analysis or invented) else "unavailable",
        "references_provided": [name for name, _image in references],
        "reference_images_sent": len(references),
        "analysis_keys": list(analysis.keys()) if isinstance(analysis, dict) else [],
        "invented_keys": list(invented.keys()) if isinstance(invented, dict) else [],
    }, calls


def _score_map(raw: Any) -> dict[str, float]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    buckets = [data]
    for key in ("scores", "positives", "positive", "positive_scores", "dimensions", "risks", "risk"):
        nested = data.get(key)
        if isinstance(nested, dict):
            buckets.append(nested)
    out: dict[str, float] = {}
    for bucket in buckets:
        for key in (*POSITIVE_CRITIC, *RISK_CRITIC):
            if bucket.get(key) is not None and key not in out:
                out[key] = _num(bucket.get(key))
    return out


def blueprint_critic_pass(scores: dict[str, Any]) -> bool:
    if not scores:
        return False
    if any(_num(scores.get(key)) < 8 for key in POSITIVE_CRITIC):
        return False
    for key, ceiling in RISK_MAX.items():
        if _num(scores.get(key), 10) > ceiling:
            return False
    return True


def request_blueprint_critic(blueprints: list[dict[str, Any]], target: dict[str, Any]) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.05,
        "max_tokens": 2200,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "ArtDirectionCriticV1. Score BLUEPRINTS not pixels. Honest scores 0-10. JSON only.",
            },
            {
                "role": "user",
                "content": (
                    "Score AD1 AD2 AD3. You MUST return a numeric 0-10 for EVERY positive dimension "
                    "AND every risk. Do not omit positives. Positive: "
                    + ", ".join(POSITIVE_CRITIC)
                    + ". Risks: "
                    + ", ".join(RISK_CRITIC)
                    + ". Gate: positives>=8, listing<=2, template<=3, dump<=2, UI<=2. "
                    "Selection: composition > image/design integration > commercial storytelling > "
                    "reference craft > premium identity > feasibility. Do not pick easiest. "
                    "JSON: scores.AD1/AD2/AD3, winner_id or none, rationale.\n"
                    + json.dumps({"target": target, "blueprints": blueprints}, ensure_ascii=False)[:12000]
                ),
            },
        ],
    }
    parsed, calls = _vision(payload)
    scores_raw = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    scored = {}
    for item in blueprints:
        scored[item["id"]] = _score_map((scores_raw or {}).get(item["id"]) if isinstance(scores_raw, dict) else {})
        item["critic_scores"] = scored[item["id"]]
        item["critic_pass"] = blueprint_critic_pass(scored[item["id"]])
    winner_id = str(parsed.get("winner_id") or parsed.get("winner") or "").upper()
    if winner_id not in scored or not scored[winner_id]:
        winner_id = ""
    return {
        "schema": "ArtDirectionCriticV1",
        "scores": scored,
        "winner_id": winner_id or None,
        "rationale": str(parsed.get("rationale") or ""),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def select_winning_blueprint(blueprints: list[dict[str, Any]], critic: dict[str, Any]) -> dict[str, Any] | None:
    passing = [item for item in blueprints if item.get("critic_pass")]
    if not passing:
        return None
    preferred = str(critic.get("winner_id") or "")
    for item in passing:
        if item["id"] == preferred:
            return item

    def rank(item: dict[str, Any]) -> tuple:
        scores = item.get("critic_scores") or {}
        return (
            _num(scores.get("whole_canvas_composition")),
            _num(scores.get("visual_hierarchy")),
            _num(scores.get("photo_integration")),
            _num(scores.get("commercial_storytelling")),
            _num(scores.get("reference_craft_understanding")),
            _num(scores.get("premium_character")),
            _num(scores.get("production_feasibility")),
        )

    return max(passing, key=rank)


def _blueprint_text(blueprint: dict[str, Any]) -> str:
    parts = [str(blueprint.get(key) or "") for key in BLUEPRINT_FIELDS]
    return " ".join(parts).lower()


def infer_lockup_side(blueprint: dict[str, Any]) -> str:
    text = _blueprint_text(blueprint)
    right_hits = sum(
        phrase in text
        for phrase in (
            "right of the spire",
            "right sky",
            "eastern sky",
            "right-hand",
            "right field",
            "anchored right",
            "aligned to the right",
        )
    )
    left_hits = sum(
        phrase in text
        for phrase in (
            "left of the spire",
            "left sky",
            "western sky",
            "left-hand",
            "left field",
            "anchored left",
            "aligned to the left",
        )
    )
    if right_hits > left_hits:
        return "right"
    return "left"


def concept_executable_by_v3(blueprint: dict[str, Any]) -> tuple[bool, str]:
    intent_keys = (
        "concept_name",
        "one_sentence_idea",
        "visual_axis",
        "photo_role",
        "headline_role",
        "commercial_offer_role",
        "logo_role",
        "cta_role",
        "image_design_integration_strategy",
        "group_relationships",
        "negative_space_strategy",
    )
    text = " ".join(str(blueprint.get(key) or "") for key in intent_keys).lower()
    needles = (
        ("left information dump", "split left dump"),
        ("both sides", "uses both sides of the spire"),
        ("card", "card/pill/badge"),
        ("pill", "card/pill/badge"),
        ("badge", "card/pill/badge"),
        ("medallion", "card/pill/badge"),
        ("footer", "lower-third / footer lockup"),
        ("bottom third", "lower-third / footer lockup"),
        ("dashboard", "dashboard composition"),
        ("brochure", "brochure stack"),
    )
    for needle, reason in needles:
        if needle in text:
            return False, reason
    if "listing layout" in text or "property listing" in text:
        return False, "listing layout"
    if "dump" in text and "left" in text and "right" in text:
        return False, "split composition around the spire"
    if "across the spire" in text or "wrap the architecture" in text:
        return False, "type wrapping architecture"
    return True, "single-side editorial lockup with inward logo signature"


def translate_blueprint_to_plan(
    blueprint: dict[str, Any],
    occupancy: dict[str, Any],
    *,
    canvas: tuple[int, int] = (1088, 1360),
) -> dict[str, Any]:
    width, height = canvas
    side = infer_lockup_side(blueprint)
    executable, capability = concept_executable_by_v3(blueprint)
    text = _blueprint_text(blueprint)
    display_scale = 0.048
    if any(word in text for word in ("monumental", "one-third", "dominant display", "large headline")):
        display_scale = 0.052
    if any(word in text for word in ("restrained", "quiet type", "whisper")):
        display_scale = 0.044
    window = (
        {"x0": 0.0, "y0": 0.0, "x1": 0.46, "y1": 0.24}
        if side == "left"
        else {"x0": 0.54, "y0": 0.0, "x1": 1.0, "y1": 0.24}
    )
    safe = largest_safe_rect(occupancy, window=window, must_touch=side)
    inset = 0.055
    anchor_y = 0.028
    type_limit_y = 0.205
    if float(safe.get("w") or 0) >= 0.18 and float(safe.get("h") or 0) >= 0.08:
        if side == "left":
            inset = max(0.042, min(0.08, float(safe["x"]) + 0.02))
        else:
            inset = max(0.042, min(0.08, 1.0 - (float(safe["x"]) + float(safe["w"])) + 0.02))
        anchor_y = max(0.022, min(0.04, float(safe["y"]) + 0.01))
        type_limit_y = min(0.20, float(safe["y"]) + float(safe["h"]) - 0.01)
    col_x = inset if side == "left" else max(0.54, 1.0 - 0.42)
    objects = {
        "project_photo": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "role": "full_frame_hero"},
        "headline": {"x": col_x, "y": anchor_y, "w": 0.32, "h": display_scale * 2.1, "role": "display"},
        "project_logo": {
            "x": col_x + (0.22 if side == "left" else -0.02),
            "y": anchor_y,
            "w": 0.18,
            "h": 0.08,
            "placement": "inward_signature",
        },
        "discount": {"x": col_x, "y": anchor_y + display_scale * 2.2, "w": 0.16, "h": 0.045},
        "discount_label": {"x": col_x, "y": anchor_y + display_scale * 2.2 + 0.05, "w": 0.22, "h": 0.02},
        "price": {"x": col_x, "y": anchor_y + display_scale * 2.2 + 0.08, "w": 0.30, "h": 0.045},
        "unit_type": {"x": col_x, "y": anchor_y + display_scale * 2.2 + 0.13, "w": 0.22, "h": 0.02},
        "cta": {
            "x": col_x,
            "y": min(type_limit_y - 0.024, anchor_y + display_scale * 2.2 + 0.16),
            "w": 0.24,
            "h": 0.022,
        },
        "graphic_devices": {"x": col_x, "y": anchor_y + display_scale * 2.05, "w": 0.22, "h": 0.003, "kind": "hairline"},
        "tonal_treatment": {
            "x": 0.0 if side == "left" else 0.55,
            "y": 0.0,
            "w": 0.45,
            "h": 0.42,
            "kind": "photographic_field",
        },
    }
    return {
        "schema": "StructuredArtDirectionPlanV1",
        "plan_id": str(uuid4()),
        "blueprint_id": blueprint.get("blueprint_id"),
        "concept_name": blueprint.get("concept_name"),
        "alignment": side,
        "lockup_side": side,
        "scale": 1.0,
        "executable": executable,
        "v3_capability": capability,
        "visual_axis": blueprint.get("visual_axis"),
        "canvas": {"w": width, "h": height},
        "anchor": {"inset": round(inset, 4), "y": round(anchor_y, 4)},
        "territories": {
            "type_limit_y": round(type_limit_y, 4),
            "column": {
                "x": round(col_x, 4),
                "y": round(anchor_y, 4),
                "w": 0.38,
                "h": round(max(0.08, type_limit_y - anchor_y), 4),
            },
        },
        "typography": {
            "display_scale": display_scale,
            "discount_scale": 0.032,
            "number_scale": 0.034,
            "label_scale": 0.011,
            "unit_scale": 0.010,
            "cta_scale": 0.014,
        },
        "logo": {"placement": "inward_signature", "w": 0.11, "h": 0.045},
        "objects": objects,
        "spacing_ratios": {"headline_to_commercial": 0.08, "commercial_to_cta": 0.05},
        "z_order": [
            "project_photo",
            "tonal_treatment",
            "headline",
            "project_logo",
            "discount",
            "discount_label",
            "price",
            "unit_type",
            "graphic_devices",
            "cta",
        ],
        "graphic_primitives": ["hairline_after_headline", "hairline_before_discount", "hairline_before_cta"],
        "architecture_exclusions": {"spire": True, "building_mass": True},
        "allowed_adaptive_ranges": {"display_scale": [0.046, 0.068], "inset": [0.04, 0.08]},
        "reading_order": blueprint.get("reading_order") or ["headline", "logo", "discount", "price", "unit", "cta"],
        "identity": {
            "headline_role": blueprint.get("headline_role"),
            "commercial_offer_role": blueprint.get("commercial_offer_role"),
            "logo_role": blueprint.get("logo_role"),
            "cta_role": blueprint.get("cta_role"),
        },
    }


def heuristic_fidelity(blueprint: dict[str, Any], plan: dict[str, Any]) -> dict[str, float]:
    scores = {key: 8.2 for key in FIDELITY_KEYS}
    if not plan.get("executable"):
        return {key: 4.0 for key in FIDELITY_KEYS}
    inferred = infer_lockup_side(blueprint)
    if plan.get("alignment") != inferred:
        scores["visual_axis_fidelity"] = 5.0
    objects = plan.get("objects") or {}
    if float((objects.get("project_photo") or {}).get("w") or 0) < 0.99:
        scores["photo_integration_fidelity"] = 4.0
    if (objects.get("project_logo") or {}).get("placement") != "inward_signature":
        scores["brand_relationship_fidelity"] = 6.0
    text = _blueprint_text(blueprint)
    if "dump" in text or "listing layout" in text:
        scores["hierarchy_fidelity"] = 5.0
        scores["commercial_storytelling_fidelity"] = 5.0
    scores["overall_concept_fidelity"] = min(scores.values())
    return scores


def request_translation_fidelity(blueprint: dict[str, Any], plan: dict[str, Any]) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "BlueprintTranslationFidelityV1. Did the structured plan keep the blueprint's creative identity? JSON scores 0-10.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"blueprint": blueprint, "plan": plan, "need": list(FIDELITY_KEYS), "require": ">=8 each"},
                    ensure_ascii=False,
                )[:14000],
            },
        ],
    }
    parsed, calls = _vision(payload)
    base = heuristic_fidelity(blueprint, plan)
    if parsed:
        nested = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
        for key in FIDELITY_KEYS:
            if nested.get(key) is not None:
                base[key] = _num(nested.get(key), base[key])
    passed = all(_num(base.get(key)) >= 8 for key in FIDELITY_KEYS)
    return {
        "schema": "BlueprintTranslationFidelityV1",
        "scores": base,
        "pass": passed,
        "mode": "vision" if parsed else "heuristic",
    }, calls


def request_final_critic(
    candidate: Image.Image,
    day007: Image.Image,
    references: list[tuple[str, Image.Image]],
    blueprint: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Final critic for Phase 5.5A. Compare the rendered candidate against the winning blueprint, "
            "Day_007, and Grade-A references. Do not inflate. JSON scores: "
            + ", ".join(FINAL_POSITIVE)
            + ". Undesirable: "
            + ", ".join(FINAL_BAD)
            + ". Targets: positives >= 8 except architecture_fidelity >= 9. "
            "Undesirable ceilings: TEXT_ON_PHOTO<=3 TEMPLATE<=3 LISTING<=2 UI<=2 DUMP<=2 CLUTTER<=3."
        ),
        _text(json.dumps({"winning_blueprint": {k: blueprint.get(k) for k in ("id", "concept_name", *BLUEPRINT_FIELDS)}}, ensure_ascii=False)[:4000]),
        _text("CANDIDATE"),
        _img(candidate, quality=82),
        _text("DAY_007 source crop"),
        _img(day007, quality=70),
    ]
    for name, image in references[:4]:
        content.append(_text(f"Grade-A reference {name}"))
        content.append(_img(image, quality=62))
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Honest senior critic. JSON only. Do not inflate."},
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    out = flatten_critic(parsed if isinstance(parsed, dict) else {})
    nested = out.get("undesirable")
    if isinstance(nested, dict):
        for key in FINAL_BAD:
            if nested.get(key) is not None:
                out[key] = nested.get(key)
    return out, calls


def _board(title: str, rows: list[str], size: tuple[int, int] = (1600, 2000)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), title, font=_font(26), fill=(232, 214, 170))
    y = 88
    for row in rows:
        for line in _wrap(str(row), 92):
            if y > size[1] - 48:
                return image
            draw.text((48, y), line, font=_font(17), fill=(226, 222, 214))
            y += 24
        y += 6
    return image


def render_craft_board(craft: dict[str, Any], references: list[tuple[str, Image.Image]] | None = None) -> Image.Image:
    canvas = Image.new("RGB", (1880, 2480), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 28), "01  VisualReferenceCraftAnalysisV1", font=_font(26), fill=(232, 214, 170))
    y = 80
    refs = {name: img for name, img in (references or [])}
    for filename, item in (craft or {}).items():
        thumb = refs.get(filename)
        x_text = 40
        if thumb is not None:
            tile = thumb.copy()
            tile.thumbnail((280, 340), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (40, y))
            x_text = 340
        draw.text((x_text, y), filename, font=_font(18), fill=(201, 168, 92))
        ty = y + 28
        for key in CRAFT_FIELDS:
            value = str((item or {}).get(key) or "")
            if not value:
                continue
            for line in _wrap(f"{key}: {value}", 78 if thumb is not None else 96):
                if ty > 2420:
                    return canvas
                draw.text((x_text, ty), line, font=_font(15), fill=(226, 222, 214))
                ty += 20
        y = max(y + 360, ty + 16)
    return canvas


def render_target_board(target: dict[str, Any], day007: Image.Image | None = None) -> Image.Image:
    canvas = Image.new("RGB", (1680, 1400), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 28), "02  TargetImageArtDirectionAnalysisV1", font=_font(26), fill=(232, 214, 170))
    x_text = 40
    if day007 is not None:
        tile = day007.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (40, 80))
        x_text = 590
    y = 80
    for key in TARGET_FIELDS:
        for line in _wrap(f"{key}: {target.get(key)}", 62 if day007 is not None else 92):
            if y > 1340:
                return canvas
            draw.text((x_text, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 6
    return canvas


def render_blueprint_board(blueprint: dict[str, Any], title: str) -> Image.Image:
    rows = [f"{blueprint.get('id')}  {blueprint.get('concept_name')}", ""]
    for key in BLUEPRINT_FIELDS:
        rows.append(f"{key}: {blueprint.get(key)}")
    return _board(title, rows, (1600, 2200))


def render_comparison_board(blueprints: list[dict[str, Any]]) -> Image.Image:
    rows = []
    for item in blueprints:
        rows.append(f"{item.get('id')}  {item.get('concept_name')}")
        rows.append(str(item.get("one_sentence_idea") or ""))
        rows.append(f"axis: {item.get('visual_axis')}")
        rows.append(f"photo: {item.get('photo_role')}")
        rows.append("")
    return _board("06  Blueprint comparison", rows)


def render_critic_board(critic: dict[str, Any], blueprints: list[dict[str, Any]]) -> Image.Image:
    rows = [f"winner: {critic.get('winner_id')}", str(critic.get("rationale") or ""), ""]
    for item in blueprints:
        rows.append(str(item.get("id")))
        scores = item.get("critic_scores") or {}
        rows.append("  " + "  ".join(f"{k}={scores.get(k)}" for k in POSITIVE_CRITIC[:6]))
        rows.append("  " + "  ".join(f"{k}={scores.get(k)}" for k in (*POSITIVE_CRITIC[6:], *RISK_CRITIC)))
        rows.append(f"  pass={item.get('critic_pass')}")
        rows.append("")
    return _board("07  ArtDirectionCriticV1", rows)


def render_plan_board(plan: dict[str, Any]) -> Image.Image:
    rows = [
        str(plan.get("concept_name")),
        f"side={plan.get('lockup_side')} executable={plan.get('executable')}",
        f"anchor={plan.get('anchor')} territories={plan.get('territories')}",
        f"typography={plan.get('typography')}",
        f"logo={plan.get('logo')}",
        json.dumps(plan.get("objects"), ensure_ascii=False),
    ]
    return _board("09  StructuredArtDirectionPlanV1", rows, (1600, 1800))


def render_fidelity_board(fidelity: dict[str, Any]) -> Image.Image:
    scores = fidelity.get("scores") or {}
    rows = [f"pass={fidelity.get('pass')} mode={fidelity.get('mode')}"] + [f"{k}={scores.get(k)}" for k in FIDELITY_KEYS]
    return _board("10  BlueprintTranslationFidelityV1", rows, (1400, 900))


