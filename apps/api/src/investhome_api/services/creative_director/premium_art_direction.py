"""Premium reference-grounded art direction for Phase 5.6.

Vision inspects Grade-A pixels. Compositor executes. No GPT Image production.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.ai_visual_art_director import (
    GRADE_A_REFERENCES,
    _find_named_blob,
    _img,
    _num,
    _text,
    normalize_craft,
)
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

CRAFT_V2_FIELDS = (
    "image_to_graphic_relationship",
    "dominant_visual_axis",
    "typography_scale_ratios",
    "headline_placement",
    "information_distribution",
    "negative_space_usage",
    "deliberate_occupied_space",
    "brand_integration",
    "price_integration",
    "commercial_hierarchy",
    "decorative_geometry",
    "edge_relationships",
    "image_cropping_strategy",
    "visual_depth",
    "tonal_transitions",
    "foreground_background",
    "asymmetry",
    "rhythm",
    "tension",
    "balance",
    "cta_integration",
)

BLUEPRINT_V2_FIELDS = (
    "concept_name",
    "visual_thesis",
    "reference_sources",
    "reference_craft_used",
    "architecture_role",
    "headline_role",
    "commercial_story",
    "brand_role",
    "CTA_role",
    "negative_space_strategy",
    "whole_canvas_strategy",
    "graphic_field_strategy",
    "typography_strategy",
    "why_this_is_not_a_template",
    "structured_reconstruction_plan",
    "brand_anchor_reason",
    "brand_relationship",
    "brand_clear_space",
    "brand_visual_role",
)

POSITIVE_V2 = (
    "professional_art_direction",
    "reference_craft_transfer",
    "originality",
    "whole_canvas_composition",
    "architecture_integration",
    "typographic_composition",
    "commercial_storytelling",
    "brand_integration",
    "negative_space_quality",
    "premium_character",
    "structured_feasibility",
)

FEEL_V2 = (
    "TEMPLATE_FEEL",
    "LISTING_FEEL",
    "UI_FEEL",
    "TEXT_DUMP_FEEL",
    "DEAD_SPACE_FEEL",
    "SPLIT_PANEL_FEEL",
)

FINAL_POSITIVE_V2 = (
    "professional_art_direction",
    "reference_craft_transfer",
    "originality",
    "whole_canvas_composition",
    "image_design_integration",
    "typography",
    "hierarchy",
    "commercial_storytelling",
    "commercial_clarity",
    "logo_integration",
    "cta_integration",
    "negative_space_quality",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)

FINAL_BAD_V2 = (
    "TEXT_ON_PHOTO_FEEL",
    "TEMPLATE_FEEL",
    "LISTING_CARD_FEEL",
    "UI_FEEL",
    "TEXT_DUMP_FEEL",
    "CORNER_CLUSTER_FEEL",
    "CLUTTER",
    "DEAD_SPACE_FEEL",
    "SPLIT_PANEL_FEEL",
)

MODES = ("SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS")

_SPLIT_MARKERS = (
    "navy column",
    "left column",
    "right column",
    "split panel",
    "split-column",
    "photo on one side",
    "information on the other",
    "information panel",
    "text column",
    "giant left",
    "full-height band",
    "listing card",
    "floating card",
    "rounded rectangle",
    "price badge",
    "discount medallion",
    "pill button",
    "dashboard",
    "website hero",
)


def _pick(data: dict[str, Any], key: str) -> Any:
    if data.get(key) not in (None, ""):
        return data.get(key)
    nested = data.get("blueprint") if isinstance(data.get("blueprint"), dict) else {}
    if nested.get(key) not in (None, ""):
        return nested.get(key)
    plan = data.get("structured_reconstruction_plan")
    if isinstance(plan, dict) and plan.get(key) not in (None, ""):
        return plan.get(key)
    return data.get(key)


def normalize_craft_v2(raw: Any, filename: str) -> dict[str, Any]:
    base = normalize_craft(raw, filename)
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    nested = data.get("craft") if isinstance(data.get("craft"), dict) else {}
    merged = {**base, **nested, **data}
    out = {"schema": "ReferenceCraftBlueprintV2", "filename": filename}
    for key in CRAFT_V2_FIELDS:
        value = merged.get(key)
        if value in (None, ""):
            aliases = {
                "image_to_graphic_relationship": merged.get("photo_design_relationship"),
                "typography_scale_ratios": merged.get("headline_scale_relationship"),
                "headline_placement": merged.get("headline"),
                "negative_space_usage": merged.get("negative_space_behavior"),
                "edge_relationships": merged.get("edge_behavior"),
                "cta_integration": merged.get("cta_behavior"),
                "brand_integration": merged.get("logo_behavior"),
                "price_integration": merged.get("commercial_number_behavior"),
            }
            value = aliases.get(key)
        out[key] = str(value or "").strip()
    return out


def normalize_blueprint_v2(raw: Any, index: int) -> dict[str, Any]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    out = {
        "schema": "ArtDirectionBlueprintV2",
        "id": f"AD{index}",
        "blueprint_id": str(data.get("blueprint_id") or uuid4()),
    }
    for key in BLUEPRINT_V2_FIELDS:
        value = _pick(data, key)
        if key == "visual_thesis" and not value:
            value = _pick(data, "one_sentence_idea")
        if key == "CTA_role" and not value:
            value = _pick(data, "cta_role")
        if key == "brand_role" and not value:
            value = _pick(data, "logo_role")
        if key in {"reference_sources", "reference_craft_used"} and isinstance(value, list):
            out[key] = [str(item) for item in value]
        elif key == "structured_reconstruction_plan" and isinstance(value, dict):
            out[key] = value
        else:
            out[key] = value if isinstance(value, (str, list, dict)) else str(value or "").strip()
    if not out.get("concept_name"):
        out["concept_name"] = f"Concept {index}"
    return out


def blueprint_text(blueprint: dict[str, Any]) -> str:
    parts = [str(blueprint.get(key) or "") for key in BLUEPRINT_V2_FIELDS]
    plan = blueprint.get("structured_reconstruction_plan")
    if isinstance(plan, dict):
        parts.append(json.dumps(plan, ensure_ascii=False))
    return " ".join(parts).lower()


def split_panel_language(blueprint: dict[str, Any]) -> bool:
    text = blueprint_text(blueprint)
    return any(marker in text for marker in _SPLIT_MARKERS)


def infer_mode(blueprint: dict[str, Any], index: int, used: set[str]) -> str:
    plan = blueprint.get("structured_reconstruction_plan")
    if isinstance(plan, dict):
        raw = str(plan.get("mode") or plan.get("reconstruction_mode") or "").upper()
        if raw in MODES and raw not in used:
            return raw
    text = blueprint_text(blueprint)
    ranked = []
    if any(tok in text for tok in ("sky", "upper fram", "horizon", "top veil")):
        ranked.append("SKY_VEIL")
    if any(tok in text for tok in ("ground", "street", "lower fram", "bottom plane")):
        ranked.append("GROUND_PLANE")
    if any(tok in text for tok in ("ingress", "asymmetric field", "corner", "enter the photograph", "feather")):
        ranked.append("CORNER_INGRESS")
    for mode in ranked:
        if mode not in used:
            return mode
    for mode in MODES:
        if mode not in used:
            return mode
    return MODES[index % 3]


def translate_premium_plan(blueprint: dict[str, Any], *, mode: str) -> dict[str, Any]:
    brand = {
        "brand_anchor_reason": str(blueprint.get("brand_anchor_reason") or blueprint.get("brand_role") or ""),
        "brand_relationship": str(blueprint.get("brand_relationship") or ""),
        "brand_clear_space": str(blueprint.get("brand_clear_space") or ""),
        "brand_visual_role": str(blueprint.get("brand_visual_role") or blueprint.get("brand_role") or ""),
    }
    return {
        "schema": "StructuredPremiumPlanV1",
        "plan_id": str(uuid4()),
        "blueprint_id": blueprint.get("blueprint_id"),
        "concept_name": blueprint.get("concept_name"),
        "reconstruction_mode": mode,
        "scale": 1.0,
        "split_panel": False,
        "visual_thesis": blueprint.get("visual_thesis"),
        "whole_canvas_strategy": blueprint.get("whole_canvas_strategy"),
        "graphic_field_strategy": blueprint.get("graphic_field_strategy"),
        "typography_strategy": blueprint.get("typography_strategy"),
        "brand_anchor": brand,
        "objects": {
            "project_photo": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "role": "full_frame_hero"},
            "graphic_field": {"kind": mode.lower(), "photographic_continuation": True},
        },
        "z_order": ["project_photo", "graphic_field", "headline", "discount", "price", "project_logo", "cta"],
    }


def _score_bucket(raw: Any, keys: tuple[str, ...]) -> dict[str, float]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    buckets = [data]
    for key in ("scores", "positives", "risks", "undesirable", "feels"):
        nested = data.get(key)
        if isinstance(nested, dict):
            buckets.append(nested)
    out: dict[str, float] = {}
    for bucket in buckets:
        for key in keys:
            if bucket.get(key) is not None and key not in out:
                out[key] = _num(bucket.get(key))
    return out


def programmatic_feel(blueprint: dict[str, Any]) -> dict[str, float]:
    text = blueprint_text(blueprint)
    split = 8.0 if split_panel_language(blueprint) else 1.0
    listing = 7.0 if any(tok in text for tok in ("listing", "brochure", "itemized", "information list")) else 1.0
    template = 7.0 if any(tok in text for tok in ("template", "badge", "pill", "card", "medallion", "button")) else 1.0
    dump = 6.0 if ("stack" in text and "equal" in text) or "text dump" in text else 1.0
    ui = 7.0 if any(tok in text for tok in ("dashboard", "ui ", "website hero")) else 1.0
    dead = 6.0 if any(tok in text for tok in ("empty rectangle", "unused lower", "dead space")) else 1.2
    return {
        "TEMPLATE_FEEL": template,
        "LISTING_FEEL": listing,
        "UI_FEEL": ui,
        "TEXT_DUMP_FEEL": dump,
        "DEAD_SPACE_FEEL": dead,
        "SPLIT_PANEL_FEEL": split,
    }


def blueprint_v2_pass(scores: dict[str, Any], feels: dict[str, Any]) -> bool:
    if not scores:
        return False
    if any(_num(scores.get(key)) < 8 for key in POSITIVE_V2):
        return False
    if any(_num(feels.get(key), 10) > 2 for key in FEEL_V2):
        return False
    return True


def request_premium_art_direction(
    *,
    day007: Image.Image,
    logo: Image.Image,
    references: list[tuple[str, Image.Image]],
    occupancy_board: Image.Image,
) -> tuple[dict[str, Any], int]:
    calls = 0
    analysis_content: list[dict[str, Any]] = [
        _text(
            "You are a senior visual art director. ANALYZE only. Inspect every Grade-A reference as actual pixels. "
            "Extract concrete visual craft, not adjectives like premium/luxury/balanced. "
            "JSON: {\"reference_craft\": {\"ORNEK_00013.jpg\": {"
            + ", ".join(CRAFT_V2_FIELDS)
            + "}, ...all six filenames...}}."
        ),
        _text("TARGET Day_007 cropped 4:5. Only the real project photograph."),
        _img(day007, quality=84),
        _text("Architecture occupancy visualization. Protection context only."),
        _img(occupancy_board, quality=70),
        _text("REAL The Temple logo. Never regenerate it."),
        _img(logo, quality=90),
    ]
    for name, image in references:
        analysis_content.append(_text(f"Grade-A DESIGN_REFERENCE pixels: {name}. Inspect the actual design."))
        analysis_content.append(_img(image, quality=72))
    analysis, n = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.15,
            "max_tokens": 4200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "ReferenceCraftBlueprintV2. JSON only. Observable craft relationships."},
                {"role": "user", "content": analysis_content},
            ],
        }
    )
    calls += n
    craft = {}
    for _rid, filename in GRADE_A_REFERENCES:
        craft[filename] = normalize_craft_v2(_find_named_blob(analysis, filename), filename)
    blueprint_content: list[dict[str, Any]] = [
        _text(
            "Invent exactly THREE genuinely different ArtDirectionBlueprintV2 concepts for The Temple. "
            "They must not be layout variations of each other. "
            "LOCKED COPY: ALIRKEN KAZAN / %35 / LANSMAN AVANTAJI / 675.000 USD / 2+1 DAİRE / PROJEYİ KEŞFET. "
            "Canvas 1088x1360. Fonts: Cormorant Garamond + Source Sans 3. Real Day_007 + real logo. "
            "FORBIDDEN: navy/photo split column; photo on one side information on the other; listing card; "
            "floating card; pill; badge; medallion; button; dashboard; website hero; giant empty colored rectangle; "
            "one vertical text list; dead unused lower space. "
            "REQUIRED: whole canvas composed; architecture remains the hero; type participates in the photograph; "
            "negative space with a reason; brand location with a reason. "
            "Each blueprint structured_reconstruction_plan.mode MUST be one of SKY_VEIL, GROUND_PLANE, CORNER_INGRESS "
            "and the three blueprints MUST use three different modes. "
            "SKY_VEIL = full-bleed architecture with designed sky/ground veils, type split across the canvas. "
            "GROUND_PLANE = architecture-led, commercial story designed into the ground plane, headline in sky. "
            "CORNER_INGRESS = feathered partial field entering the photo, photography continues through the fade. "
            "Fields: "
            + ", ".join(BLUEPRINT_V2_FIELDS)
            + ". JSON: {\"blueprints\":[AD1,AD2,AD3]}."
        ),
        _text(json.dumps({"reference_craft": craft}, ensure_ascii=False)[:12000]),
        _text("TARGET Day_007 again."),
        _img(day007, quality=78),
        _text("REAL Temple logo."),
        _img(logo, quality=88),
    ]
    for name, image in references[:4]:
        blueprint_content.append(_text(f"Keep this Grade-A reference in view: {name}"))
        blueprint_content.append(_img(image, quality=62))
    invented, n = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.55,
            "max_tokens": 4500,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "ArtDirectionBlueprintV2. Three distinct whole-canvas concepts. JSON only."},
                {"role": "user", "content": blueprint_content},
            ],
        }
    )
    calls += n
    raw = invented.get("blueprints") if isinstance(invented.get("blueprints"), list) else []
    if not raw:
        raw = [invented.get(f"AD{i}") for i in range(1, 4) if isinstance(invented.get(f"AD{i}"), dict)]
    blueprints = [normalize_blueprint_v2(item, i + 1) for i, item in enumerate(raw[:3])]
    return {
        "schema": "PremiumArtDirectionV2",
        "mode": "vision" if analysis or invented else "unavailable",
        "reference_craft": craft,
        "blueprints": blueprints,
        "references_provided": len(references),
    }, calls


def request_premium_blueprint_critic(blueprints: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 2400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Honest art-direction critic. Score BLUEPRINTS. Do not inflate. JSON only."},
            {
                "role": "user",
                "content": (
                    "Score AD1 AD2 AD3. Positives 0-10 (ALL must be >=8 to pass): "
                    + ", ".join(POSITIVE_V2)
                    + ". Undesirable 0-10 (ALL must be <=2): "
                    + ", ".join(FEEL_V2)
                    + ". REJECT any concept that is photo + information column, listing, UI, or dead-space navy band. "
                    "JSON: scores.AD1/AD2/AD3 with positives and feels, eligible_ids, rationale.\n"
                    + json.dumps({"blueprints": blueprints}, ensure_ascii=False)[:14000]
                ),
            },
        ],
    }
    parsed, calls = _vision(payload)
    scores_raw = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    scored = {}
    eligible = []
    for item in blueprints:
        positives = _score_bucket((scores_raw or {}).get(item["id"]) if isinstance(scores_raw, dict) else {}, POSITIVE_V2)
        feels_v = _score_bucket((scores_raw or {}).get(item["id"]) if isinstance(scores_raw, dict) else {}, FEEL_V2)
        feels_p = programmatic_feel(item)
        feels = {key: max(_num(feels_v.get(key)), feels_p[key]) for key in FEEL_V2}
        item["critic_scores"] = positives
        item["critic_feels"] = feels
        item["critic_pass"] = blueprint_v2_pass(positives, feels) and not split_panel_language(item)
        scored[item["id"]] = {"positives": positives, "feels": feels, "pass": item["critic_pass"]}
        if item["critic_pass"]:
            eligible.append(item["id"])
    return {
        "schema": "PremiumBlueprintCriticV2",
        "scores": scored,
        "eligible_ids": eligible,
        "rationale": str(parsed.get("rationale") or ""),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def rank_eligible(blueprints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passing = [item for item in blueprints if item.get("critic_pass")]

    def rank(item: dict[str, Any]) -> tuple:
        scores = item.get("critic_scores") or {}
        return (
            _num(scores.get("professional_art_direction")),
            _num(scores.get("whole_canvas_composition")),
            _num(scores.get("reference_craft_transfer")),
            _num(scores.get("premium_character")),
            _num(scores.get("originality")),
        )

    return sorted(passing, key=rank, reverse=True)


def request_premium_final_critic(
    candidate: Image.Image,
    day007: Image.Image,
    references: list[tuple[str, Image.Image]],
    blueprint: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Final critic for a premium Temple campaign candidate. Do not inflate. "
            "Reject split-panel, listing-card, UI, text-dump, dead-space, and photo+column designs. "
            "Scores: "
            + ", ".join(FINAL_POSITIVE_V2)
            + ". Undesirable: "
            + ", ".join(FINAL_BAD_V2)
            + ". Gates: professional_art_direction, reference_craft_transfer, whole_canvas_composition, "
            "image_design_integration, typography, hierarchy, commercial_storytelling, premium_character >= 8; "
            "architecture_fidelity >= 9; all undesirable <= 2."
        ),
        _text(json.dumps({"blueprint": {k: blueprint.get(k) for k in ("id", "concept_name", *BLUEPRINT_V2_FIELDS[:8])}}, ensure_ascii=False)[:3500]),
        _text("CANDIDATE"),
        _img(candidate, quality=84),
        _text("DAY_007 source crop"),
        _img(day007, quality=70),
    ]
    for name, image in references[:4]:
        content.append(_text(f"Grade-A reference {name}"))
        content.append(_img(image, quality=60))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Honest senior critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    out = flatten_critic(parsed if isinstance(parsed, dict) else {})
    nested = out.get("undesirable")
    if isinstance(nested, dict):
        for key in FINAL_BAD_V2:
            if nested.get(key) is not None:
                out[key] = nested.get(key)
    return out, calls


def final_critic_pass(critic: dict[str, Any], *, dead_space_score: float) -> bool:
    needed = {
        "professional_art_direction": 8,
        "reference_craft_transfer": 8,
        "whole_canvas_composition": 8,
        "image_design_integration": 8,
        "typography": 8,
        "hierarchy": 8,
        "commercial_storytelling": 8,
        "premium_character": 8,
        "architecture_fidelity": 9,
    }
    if any(_num(critic.get(key)) < floor for key, floor in needed.items()):
        return False
    if any(_num(critic.get(key), 10) > 2 for key in FINAL_BAD_V2):
        return False
    if dead_space_score > 2:
        return False
    return True


def apply_layout_fault_caps(
    critic: dict[str, Any],
    objects: dict[str, Any],
    *,
    field_mass: float = 0.2,
    islands: bool = False,
) -> dict[str, Any]:
    from investhome_api.services.creative_director.blueprint_render_fidelity import apply_critic_calibration, detect_layout_faults

    return apply_critic_calibration(critic, detect_layout_faults(objects, field_mass=field_mass, islands=islands))


def creative_canvas_balance(
    image: Image.Image,
    objects: dict[str, Any],
    field_mask: Image.Image | None,
    occupancy: dict[str, Any],
) -> dict[str, Any]:
    w, h = image.size
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    sky = (occupancy.get("layers") or {}).get("sky")
    type_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(type_mask)
    for item in objects.values():
        bounds = item.get("bounds") if isinstance(item, dict) else None
        if not isinstance(bounds, dict):
            continue
        x0 = int(float(bounds.get("x") or 0) * w)
        y0 = int(float(bounds.get("y") or 0) * h)
        x1 = int((float(bounds.get("x") or 0) + float(bounds.get("w") or 0)) * w)
        y1 = int((float(bounds.get("y") or 0) + float(bounds.get("h") or 0)) * h)
        draw.rectangle((x0, y0, x1, y1), fill=255)
    field = field_mask.convert("L").resize((w, h)) if isinstance(field_mask, Image.Image) else Image.new("L", (w, h), 0)
    hard_im = hard.convert("L") if isinstance(hard, Image.Image) else Image.new("L", (w, h), 0)
    sky_im = sky.convert("L") if isinstance(sky, Image.Image) else Image.new("L", (w, h), 0)

    def cov(mask: Image.Image, box: tuple[int, int, int, int], threshold: int = 80) -> float:
        crop = mask.crop(box)
        hist = crop.histogram()
        total = max(1, sum(hist))
        return sum(hist[threshold:]) / total

    cells = []
    dead = 0
    cols, rows = 2, 3
    for gy in range(rows):
        for gx in range(cols):
            box = (int(gx * w / cols), int(gy * h / rows), int((gx + 1) * w / cols), int((gy + 1) * h / rows))
            t, f, a, s = cov(type_mask, box), cov(field, box, 40), cov(hard_im, box), cov(sky_im, box, 40)
            cell = {"gx": gx, "gy": gy, "type": round(t, 3), "field": round(f, 3), "architecture": round(a, 3), "sky": round(s, 3)}
            if f > 0.55 and t < 0.02 and a < 0.10:
                cell["dead"] = True
                dead += 1
            elif t < 0.008 and f < 0.08 and a < 0.10 and s < 0.12:
                cell["dead"] = True
                dead += 1
            else:
                cell["dead"] = False
            cells.append(cell)
    top = sum(1 for c in cells if c["gy"] == 0 and (c["type"] > 0.01 or c["architecture"] > 0.08 or c["sky"] > 0.2))
    mid = sum(1 for c in cells if c["gy"] == 1 and (c["type"] > 0.01 or c["architecture"] > 0.15))
    bot = sum(1 for c in cells if c["gy"] == 2 and (c["type"] > 0.01 or c["architecture"] > 0.08 or c["field"] > 0.15))
    left = sum(1 for c in cells if c["gx"] == 0 and (c["type"] > 0.01 or c["architecture"] > 0.1))
    right = sum(1 for c in cells if c["gx"] == 1 and (c["type"] > 0.01 or c["architecture"] > 0.1))
    dead_score = min(10.0, dead * 2.0)
    integration = 8.5 if dead_score <= 2 and top and bot else 4.0
    return {
        "schema": "CreativeCanvasBalanceV1",
        "intentional_visual_mass": round(3.0 + top + mid + bot, 2),
        "negative_space": round(max(0.0, 10.0 - dead_score - 1.0), 2),
        "dead_space": dead_score,
        "dead_space_score": dead_score,
        "top_balance": round(top * 5.0, 2),
        "middle_balance": round(mid * 5.0, 2),
        "bottom_balance": round(bot * 5.0, 2),
        "left_right_balance": round(min(left, right) * 5.0, 2),
        "photo_graphic_integration": integration,
        "cells": cells,
        "pass": dead_score <= 2,
    }


def _board(title: str, rows: list[str], size: tuple[int, int] = (1600, 2100)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), title, font=_font(24), fill=(232, 214, 170))
    y = 80
    for row in rows:
        for line in _wrap(str(row), 96):
            if y > size[1] - 40:
                return image
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 8
    return image


def render_craft_v2_board(craft: dict[str, Any], references: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1880, 2600), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 24), "01  REFERENCE CRAFT  —  Grade-A pixels inspected", font=_font(24), fill=(232, 214, 170))
    refs = {name: img for name, img in references}
    y = 72
    for filename, item in (craft or {}).items():
        thumb = refs.get(filename)
        if thumb is not None:
            tile = thumb.copy()
            tile.thumbnail((260, 300), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (40, y))
        draw.text((320, y), filename, font=_font(18), fill=(201, 168, 92))
        ty = y + 28
        for key in CRAFT_V2_FIELDS[:8]:
            draw.text((320, ty), f"{key}: {str((item or {}).get(key) or '')[:88]}", font=_font(14), fill=(220, 216, 208))
            ty += 20
        y += 340
        if y > 2400:
            break
    return canvas


def render_blueprint_v2_board(blueprint: dict[str, Any], title: str) -> Image.Image:
    rows = [f"{key}: {blueprint.get(key)}" for key in BLUEPRINT_V2_FIELDS]
    return _board(title, rows)


def render_blueprint_critic_board(critic: dict[str, Any], blueprints: list[dict[str, Any]]) -> Image.Image:
    rows = [f"eligible  {critic.get('eligible_ids')}", str(critic.get("rationale") or "")]
    for item in blueprints:
        rows.append(f"{item.get('id')}  {item.get('concept_name')}  pass={item.get('critic_pass')}")
        rows.append(str(item.get("critic_scores")))
        rows.append(str(item.get("critic_feels")))
    return _board("06  BLUEPRINT CRITIC", rows)


def render_balance_board(balance: dict[str, Any], candidate: Image.Image | None) -> Image.Image:
    canvas = Image.new("RGB", (1600, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "CREATIVE CANVAS BALANCE V1", fill=(201, 168, 92), font=_font(20))
    if candidate is not None:
        tile = candidate.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36, 70))
    x, y = 600, 80
    for key in (
        "intentional_visual_mass",
        "negative_space",
        "dead_space_score",
        "top_balance",
        "middle_balance",
        "bottom_balance",
        "left_right_balance",
        "photo_graphic_integration",
    ):
        draw.text((x, y), f"{key}  {balance.get(key)}", fill=(236, 230, 218), font=_font(16))
        y += 32
    draw.text((x, y + 12), f"PASS  {balance.get('pass')}", fill=(80, 200, 120) if balance.get("pass") else (220, 80, 80), font=_font(18))
    return canvas
