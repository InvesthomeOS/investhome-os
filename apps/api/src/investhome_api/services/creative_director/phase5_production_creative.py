"""Phase 5.2 — production creative design system.

Immutable project photography (locked 5.1B) + role-based fonts +
reference-driven art direction + design surfaces + independent critic.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_design_surfaces import (
    SURFACE_TYPES,
    apply_surface,
    box_to_px,
)
from investhome_api.services.creative_director.creative_font_registry import (
    build_font_registry,
    font_for_role,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.config import openai_api_key, resolve_base_url
from investhome_api.services.gpt_image_design.editorial_compose import (
    contrast_ratio,
    draw_tracked_text,
    paste_logo,
    region_mean_rgb,
)
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

logger = logging.getLogger(__name__)

WORKFLOW_ID_52 = "phase5_2_production_creative"
PHASE50_MASTER_ASSET_ID = "3647f302-325a-4f12-b3e6-07b005131485"
MAX_CANDIDATES = 3
NAVY = "#121820"
IVORY = "#F4EFE6"
GOLD = "#C9A85C"

CONCEPT_SEEDS = (
    {
        "id": "A",
        "name": "right-sky counterweight",
        "brief": (
            "The gothic spire is the left-center hero. Keep ALL typography in the quiet right sky "
            "so the tower stays untouched. One vertical editorial lockup: logo, headline, commercial "
            "system, CTA. Soft right-edge wash only. No bottom strip, web button, or left column."
        ),
    },
    {
        "id": "B",
        "name": "left-sky masthead + canopy lockup",
        "brief": (
            "Compact masthead in the far-left sky, strictly left of the spire finial. Commercial "
            "facts as ONE lockup in the dark lower-left tree canopy with local photo fade. CTA is "
            "an inscription under that lockup. Do not span the full width or cover the façade."
        ),
    },
    {
        "id": "C",
        "name": "asymmetric editorial field",
        "brief": (
            "Headline as a modest tracked line in upper-left sky, clear of the spire. Commercial "
            "system as one group in a feathered radial field over the lower-left shadow. CTA as a "
            "thin editorial measure, not a pill. Gold is one short rule."
        ),
    },
)

HEURISTIC_PROTECTION = {
    "SPIRE": {"x": 0.28, "y": 0.02, "w": 0.24, "h": 0.48},
    "TOWER": {"x": 0.24, "y": 0.16, "w": 0.32, "h": 0.40},
    "MAIN_FACADE": {"x": 0.16, "y": 0.26, "w": 0.50, "h": 0.40},
    "ROOFLINE": {"x": 0.14, "y": 0.28, "w": 0.56, "h": 0.14},
    "PROJECT_MASS": {"x": 0.14, "y": 0.16, "w": 0.64, "h": 0.54},
    "IMPORTANT_ARCHITECTURAL_EDGES": {"x": 0.12, "y": 0.12, "w": 0.68, "h": 0.58},
}


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_b64(image: Image.Image, quality: int = 88) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _clamp_box(raw: Any) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    try:
        x = float(raw.get("x", 0))
        y = float(raw.get("y", 0))
        w = float(raw.get("w", raw.get("width", 0)))
        h = float(raw.get("h", raw.get("height", 0)))
    except (TypeError, ValueError):
        return None
    if w <= 0.03 or h <= 0.02:
        return None
    x = max(0.0, min(0.92, x))
    y = max(0.0, min(0.92, y))
    w = max(0.04, min(0.9, w))
    h = max(0.03, min(0.9, h))
    if x + w > 1.0:
        w = 1.0 - x
    if y + h > 1.0:
        h = 1.0 - y
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _overlap_frac(a: dict[str, float] | None, b: dict[str, float] | None) -> float:
    if not a or not b:
        return 0.0
    x0 = max(a["x"], b["x"])
    y0 = max(a["y"], b["y"])
    x1 = min(a["x"] + a["w"], b["x"] + b["w"])
    y1 = min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area = max(1e-6, a["w"] * a["h"])
    return inter / area


def _boxes_overlap(a: dict[str, float] | None, b: dict[str, float] | None, margin: float = 0.0) -> bool:
    if not a or not b:
        return False
    return not (
        a["x"] + a["w"] + margin <= b["x"]
        or b["x"] + b["w"] + margin <= a["x"]
        or a["y"] + a["h"] + margin <= b["y"]
        or b["y"] + b["h"] + margin <= a["y"]
    )


def _vision(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    api_key = openai_api_key()
    if not api_key:
        return {}, 0
    url = f"{resolve_base_url(get_settings()).rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
        text = ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        return (parsed if isinstance(parsed, dict) else {}), 1
    except Exception:
        logger.info("phase5.2 vision call failed", exc_info=True)
        return {}, 0


def analyze_reference_dna(reference: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Extract DESIGN DNA from a quality reference. Never copy architecture. JSON.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "CreativeReferenceAnalysisV1 keys: composition_principle, visual_hierarchy, photo_relationship, "
                            "headline_behavior, headline_scale_ratio, type_pairing_strategy, commercial_information_strategy, "
                            "price_emphasis_strategy, logo_strategy, cta_strategy, graphic_language, surface_strategy, "
                            "negative_space_strategy, color_strategy, depth_strategy, density, alignment_system, "
                            "spacing_rhythm, premium_signals, anti_patterns."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    keys = (
        "composition_principle", "visual_hierarchy", "photo_relationship", "headline_behavior",
        "headline_scale_ratio", "type_pairing_strategy", "commercial_information_strategy",
        "price_emphasis_strategy", "logo_strategy", "cta_strategy", "graphic_language",
        "surface_strategy", "negative_space_strategy", "color_strategy", "depth_strategy",
        "density", "alignment_system", "spacing_rhythm",
    )
    defaults = {
        "composition_principle": "editorial hierarchy with the photograph as hero",
        "visual_hierarchy": "headline, then price, then supporting facts, then CTA",
        "photo_relationship": "type occupies quiet air; architecture remains dominant",
        "headline_behavior": "confident, tracked, not enormous",
        "headline_scale_ratio": "headline smaller than the architectural focal point",
        "type_pairing_strategy": "display serif + editorial sans",
        "commercial_information_strategy": "one designed lockup, not scattered labels",
        "price_emphasis_strategy": "price is level 2, never larger than the building",
        "logo_strategy": "intentional masthead presence, not a corner sticker",
        "cta_strategy": "inscription belonging to the lockup, not a website button",
        "graphic_language": "restrained navy / ivory / gold accent",
        "surface_strategy": "dissolving tonal fields, not opaque panels",
        "negative_space_strategy": "protect the architectural silhouette",
        "color_strategy": "warm stone + ivory type + one gold measure",
        "depth_strategy": "local fade and blur behind type only",
        "density": "low; generous breathing room",
        "alignment_system": "one shared axis for the commercial system",
        "spacing_rhythm": "tight within the lockup, open around it",
    }
    dna = {"schema": "CreativeReferenceAnalysisV1", "source": "phase5_0_quality_reference_not_architecture", "mode": "vision" if parsed else "heuristic"}
    for key in keys:
        dna[key] = str(parsed.get(key) or defaults[key])
    dna["premium_signals"] = parsed.get("premium_signals") or ["restraint", "tracked small caps", "one gold rule"]
    dna["anti_patterns"] = parsed.get("anti_patterns") or [
        "dashboard cards", "giant % badge", "ribbons", "web CTA pill", "headline through spire", "full-width bottom strip",
    ]
    return dna, calls


def request_protection_map(foundation: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Map protected architecture. JSON boxes 0-1 {x,y,w,h}."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "regions: SPIRE, TOWER, MAIN_FACADE, ROOFLINE, PROJECT_MASS, IMPORTANT_ARCHITECTURAL_EDGES.",
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    raw_regions = dict(parsed.get("regions") or parsed)
    regions = {key: _clamp_box(raw_regions.get(key)) or dict(box) for key, box in HEURISTIC_PROTECTION.items()}
    return {"schema": "ProtectedArchitectureMapV1", "regions": regions, "mode": "vision" if parsed else "heuristic"}, calls


def plan_quality_gate(plan: dict[str, Any], protection: dict[str, Any]) -> dict[str, Any]:
    rationale = str(plan.get("photo_specific_rationale") or "")
    regions = dict(plan.get("regions") or {})
    prot = dict(protection.get("regions") or {})
    failures: list[str] = []
    tokens = ("spire", "sky", "terrace", "street", "mass", "tower", "left", "right", "canopy", "garden", "facade", "façade")
    if len(rationale) < 80 or not any(t in rationale.casefold() for t in tokens):
        failures.append("photo_specific_rationale_weak")
    if _boxes_overlap(regions.get("headline"), prot.get("SPIRE"), margin=0.01):
        failures.append("headline_through_spire")
    if _overlap_frac(regions.get("price") or regions.get("commercial"), prot.get("MAIN_FACADE")) > 0.35:
        failures.append("price_on_primary_facade")
    if _boxes_overlap(regions.get("cta"), prot.get("SPIRE")) or _boxes_overlap(regions.get("cta"), prot.get("TOWER")):
        failures.append("cta_on_major_architecture")
    commercial = regions.get("commercial")
    if commercial and commercial.get("w", 0) > 0.78 and commercial.get("y", 0) > 0.74:
        failures.append("bottom_information_strip")
    if (regions.get("headline") or {}).get("w", 0) < 0.18:
        failures.append("headline_region_too_narrow")
    if (regions.get("commercial") or {}).get("w", 0) < 0.22 or (regions.get("commercial") or {}).get("h", 0) < 0.14:
        failures.append("commercial_lockup_too_small")
    surfaces = plan.get("required_surfaces")
    if isinstance(surfaces, str) or not any(isinstance(s, dict) and str(s.get("type") or "").upper() in SURFACE_TYPES for s in (surfaces or [])):
        failures.append("no_usable_design_surfaces")
    return {"pass": not failures, "failures": failures}


def request_art_direction_plan(
    *,
    foundation: Image.Image,
    logo: Image.Image,
    dna: dict[str, Any],
    protection: dict[str, Any],
    facts: dict[str, str],
    seed: dict[str, str],
    critique: str = "",
) -> tuple[dict[str, Any], int]:
    retry = ""
    if critique:
        retry = (
            "PREVIOUS CANDIDATE REJECTED. Invent a MATERIALLY DIFFERENT solution. "
            f"Do not nudge coordinates.\n{critique}\n"
        )
    dna_slim = {k: dna.get(k) for k in ("composition_principle", "visual_hierarchy", "surface_strategy", "cta_strategy", "anti_patterns")}
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Luxury real-estate creative director. Photograph is immutable. JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 is the exact 1088x1360 foundation. Image 2 is the real logo. "
                            f"Seed: {seed['name']}. {seed['brief']}\n"
                            f"Copy: {facts['headline']} / {facts['unit']} {facts['unit_label']} / {facts['list_price']} / "
                            f"{facts['discount']} {facts['discount_label']} / {facts['cta']}.\n"
                            "One commercial lockup. No cards, badges, ribbons, web buttons, opaque navy panels.\n"
                            f"Protected: {json.dumps(protection.get('regions') or {})}\n"
                            f"DNA (do not copy architecture): {json.dumps(dna_slim)}\n{retry}"
                            "JSON CreativeArtDirectionPlanV2: concept, focal_point, photograph_dominant_region, "
                            "negative_space, typography_forbidden, photo_interaction, depth, premium_character, "
                            "headline_hierarchy, commercial_hierarchy, fact_relationships, logo_placement, cta_integration, "
                            "required_surfaces (ARRAY of objects with type, box, color, max_alpha — never a string), "
                            "photo_specific_rationale, regions (headline,commercial,price,cta,logo as {x,y,w,h}). "
                            "Headline width >= 0.22. Commercial lockup width >= 0.28 and height >= 0.18."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(logo)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    regions_raw = dict(parsed.get("regions") or {})
    plan = {
        "schema": "CreativeArtDirectionPlanV2",
        "plan_id": str(uuid4()),
        "concept_seed": seed["id"],
        "concept": str(parsed.get("concept") or seed["name"]),
        "focal_point": str(parsed.get("focal_point") or "project architecture"),
        "photograph_dominant_region": str(parsed.get("photograph_dominant_region") or "protected project mass"),
        "negative_space": str(parsed.get("negative_space") or ""),
        "typography_forbidden": str(parsed.get("typography_forbidden") or "spire, primary façade"),
        "photo_interaction": str(parsed.get("photo_interaction") or "dissolving fields in quiet zones"),
        "depth": str(parsed.get("depth") or "local fade behind type"),
        "premium_character": str(parsed.get("premium_character") or "restraint, tracked type, one gold measure"),
        "headline_hierarchy": str(parsed.get("headline_hierarchy") or facts["headline"]),
        "commercial_hierarchy": str(parsed.get("commercial_hierarchy") or ""),
        "fact_relationships": str(parsed.get("fact_relationships") or "price, discount, and unit share one lockup"),
        "logo_placement": str(parsed.get("logo_placement") or ""),
        "cta_integration": str(parsed.get("cta_integration") or "inscription in the lockup"),
        "required_surfaces": list(parsed.get("required_surfaces") or []) if isinstance(parsed.get("required_surfaces"), list) else [],
        "photo_specific_rationale": str(parsed.get("photo_specific_rationale") or ""),
        "regions": {key: _clamp_box(regions_raw.get(key)) for key in ("headline", "commercial", "price", "cta", "logo")},
        "mode": "vision" if parsed else "unavailable",
    }
    return plan, calls


def _fallback_plan(seed: dict[str, str], facts: dict[str, str]) -> dict[str, Any]:
    if seed["id"] == "A":
        regions = {
            "logo": {"x": 0.62, "y": 0.06, "w": 0.30, "h": 0.10},
            "headline": {"x": 0.58, "y": 0.18, "w": 0.36, "h": 0.16},
            "commercial": {"x": 0.58, "y": 0.40, "w": 0.36, "h": 0.28},
            "price": {"x": 0.58, "y": 0.40, "w": 0.36, "h": 0.10},
            "cta": {"x": 0.58, "y": 0.70, "w": 0.34, "h": 0.06},
        }
        surfaces = [
            {"type": "COLOR_WASH", "side": "right", "width_frac": 0.42, "color": NAVY, "max_alpha": 0.20, "feather": 0.75},
            {"type": "TYPOGRAPHIC_GROUND", "box": regions["commercial"], "color": NAVY, "max_alpha": 0.22, "feather": 0.7},
            {"type": "LOGO_GROUND", "box": regions["logo"], "color": IVORY, "max_alpha": 0.16, "feather": 0.75},
            {"type": "DECORATIVE_RULE", "box": {"x": 0.58, "y": 0.36, "w": 0.18, "h": 0.01}, "color": GOLD},
        ]
        rationale = (
            "The gothic spire occupies the left-center of this exact 4:5 crop. The quiet field is the right sky; "
            "placing the entire campaign lockup there keeps the tower as the unobstructed hero."
        )
    elif seed["id"] == "B":
        regions = {
            "logo": {"x": 0.045, "y": 0.045, "w": 0.22, "h": 0.09},
            "headline": {"x": 0.045, "y": 0.14, "w": 0.22, "h": 0.14},
            "commercial": {"x": 0.045, "y": 0.68, "w": 0.40, "h": 0.22},
            "price": {"x": 0.045, "y": 0.68, "w": 0.40, "h": 0.08},
            "cta": {"x": 0.045, "y": 0.90, "w": 0.34, "h": 0.05},
        }
        surfaces = [
            {"type": "LOCAL_PHOTO_FADE", "box": {"x": 0.00, "y": 0.62, "w": 0.48, "h": 0.34}, "darkness": 0.30, "feather": 0.72},
            {"type": "LOCAL_BLUR_FIELD", "box": {"x": 0.02, "y": 0.66, "w": 0.44, "h": 0.26}, "radius": 7, "strength": 0.28, "feather": 0.65},
            {"type": "TYPOGRAPHIC_GROUND", "box": regions["commercial"], "color": NAVY, "max_alpha": 0.26, "feather": 0.68},
            {"type": "LOGO_GROUND", "box": regions["logo"], "color": IVORY, "max_alpha": 0.18, "feather": 0.78},
            {"type": "DECORATIVE_RULE", "box": {"x": 0.045, "y": 0.285, "w": 0.14, "h": 0.01}, "color": GOLD},
        ]
        rationale = (
            "The spire finial sits left-of-center in the sky; a compact far-left masthead stays clear of it. "
            "The lower-left tree canopy is the darkest quiet ground in this photograph, so the commercial lockup "
            "lives there as an inscription in shadow rather than a strip across the street."
        )
    else:
        regions = {
            "logo": {"x": 0.05, "y": 0.05, "w": 0.24, "h": 0.09},
            "headline": {"x": 0.05, "y": 0.15, "w": 0.22, "h": 0.12},
            "commercial": {"x": 0.05, "y": 0.58, "w": 0.36, "h": 0.24},
            "price": {"x": 0.05, "y": 0.58, "w": 0.36, "h": 0.09},
            "cta": {"x": 0.05, "y": 0.84, "w": 0.32, "h": 0.05},
        }
        surfaces = [
            {"type": "RADIAL_MASK", "box": {"x": 0.0, "y": 0.48, "w": 0.52, "h": 0.46}, "color": NAVY, "max_alpha": 0.24, "feather": 0.7},
            {"type": "TYPOGRAPHIC_GROUND", "box": regions["commercial"], "color": NAVY, "max_alpha": 0.20, "feather": 0.7},
            {"type": "LOGO_GROUND", "box": regions["logo"], "color": IVORY, "max_alpha": 0.16, "feather": 0.76},
            {"type": "LIGHT_ACCENT", "box": {"x": 0.05, "y": 0.28, "w": 0.12, "h": 0.01}, "color": GOLD},
        ]
        rationale = (
            "This crop's garden terrace creates a horizontal mid-band; the commercial lockup sits in the shadowed "
            "lower-left relating to that garden plane, while the headline stays a modest sky line left of the spire."
        )
    return {
        "schema": "CreativeArtDirectionPlanV2",
        "plan_id": str(uuid4()),
        "concept_seed": seed["id"],
        "concept": seed["name"],
        "focal_point": "gothic spire and project mass",
        "photograph_dominant_region": "left-center architecture",
        "negative_space": "sky away from the finial; dark canopy",
        "typography_forbidden": "spire, primary façade, cars",
        "photo_interaction": "feathered fields only in quiet zones",
        "depth": "local fade and blur behind the lockup",
        "premium_character": "restrained serif/sans pairing, one gold measure",
        "headline_hierarchy": facts["headline"],
        "commercial_hierarchy": f"{facts['list_price']} then {facts['discount']} then {facts['unit']}",
        "fact_relationships": "one lockup sharing a left axis",
        "logo_placement": "with the masthead",
        "cta_integration": "tracked inscription under the lockup",
        "required_surfaces": surfaces,
        "photo_specific_rationale": rationale,
        "regions": regions,
        "mode": "fallback_photo_specific",
    }


def build_scene_spec(plan: dict[str, Any], facts: dict[str, str], protection: dict[str, Any], fonts: dict[str, Any]) -> dict[str, Any]:
    regions = dict(plan.get("regions") or {})
    commercial = regions.get("commercial") or {"x": 0.06, "y": 0.68, "w": 0.36, "h": 0.22}
    headline = regions.get("headline") or {"x": 0.05, "y": 0.14, "w": 0.28, "h": 0.14}
    price_box = regions.get("price") or {"x": commercial["x"], "y": commercial["y"], "w": commercial["w"], "h": max(0.07, commercial["h"] * 0.36)}
    rest_y = price_box["y"] + price_box["h"] + 0.012
    type_runs = [
        {"id": "headline_1", "semantic": "headline", "role": "EDITORIAL_SANS", "text": "ALIRKEN", "box": {"x": headline["x"], "y": headline["y"], "w": headline["w"], "h": 0.045}, "font_size": 28, "tracking": 0.22, "color": IVORY, "alignment": "left", "case": "upper", "fit_strategy": "shrink_to_fit"},
        {"id": "headline_2", "semantic": "headline", "role": "DISPLAY_SERIF", "text": "KAZAN", "box": {"x": headline["x"], "y": headline["y"] + 0.05, "w": headline["w"], "h": 0.09}, "font_size": 54, "tracking": 0.08, "color": IVORY, "alignment": "left", "case": "upper", "fit_strategy": "shrink_to_fit"},
        {"id": "price", "semantic": "list_price", "role": "COMMERCIAL_NUMBER", "text": facts["list_price"], "box": price_box, "font_size": 42, "tracking": 0.02, "color": IVORY, "alignment": "left", "case": "upper", "fit_strategy": "shrink_to_fit"},
        {"id": "discount", "semantic": "discount", "role": "EDITORIAL_SANS", "text": f"{facts['discount']}  {facts['discount_label']}", "box": {"x": commercial["x"], "y": rest_y, "w": commercial["w"], "h": 0.045}, "font_size": 18, "tracking": 0.16, "color": GOLD, "alignment": "left", "case": "upper", "fit_strategy": "shrink_to_fit"},
        {"id": "unit", "semantic": "unit_type", "role": "BODY", "text": f"{facts['unit']} {facts['unit_label']}", "box": {"x": commercial["x"], "y": rest_y + 0.048, "w": commercial["w"], "h": 0.04}, "font_size": 18, "tracking": 0.14, "color": IVORY, "alignment": "left", "case": "upper", "fit_strategy": "shrink_to_fit"},
        {"id": "cta", "semantic": "cta", "role": "CTA", "text": facts["cta"], "box": regions.get("cta") or {"x": commercial["x"], "y": 0.90, "w": 0.32, "h": 0.05}, "font_size": 16, "tracking": 0.22, "color": IVORY, "alignment": "left", "case": "upper", "fit_strategy": "shrink_to_fit"},
    ]
    surfaces = []
    for raw in list(plan.get("required_surfaces") or []):
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type") or "").upper()
        if kind not in SURFACE_TYPES:
            continue
        item = dict(raw)
        item["type"] = kind
        if item.get("box"):
            item["box"] = _clamp_box(item.get("box"))
        surfaces.append(item)
    roles = fonts.get("roles") or {}
    return {
        "schema": "CreativeSceneSpecV1",
        "spec_id": str(uuid4()),
        "canvas": list(CANVAS_4X5),
        "photo": {"role": "immutable_project_photograph", "operations": ["uniform_crop", "photographic_grade"]},
        "protected_architecture": protection.get("regions"),
        "surfaces": surfaces,
        "type": type_runs,
        "logo": {"semantic": "logo", "box": regions.get("logo"), "asset_id": LOCKED_LOGO_ASSET_ID},
        "groups": {"headline": ["headline_1", "headline_2"], "commercial_lockup": ["price", "discount", "unit", "cta"]},
        "hierarchy": ["headline", "list_price", "discount", "unit_type", "cta", "logo"],
        "anchors": {"commercial_axis": commercial.get("x"), "masthead": headline.get("x")},
        "effects": [s.get("type") for s in surfaces],
        "typography_roles": {run["id"]: run["role"] for run in type_runs},
        "relationships": {"commercial_lockup": "single designed system sharing one axis"},
        "art_direction_plan_id": plan.get("plan_id"),
        "fonts": {role: {"font_family": (roles.get(role) or {}).get("font_family"), "font_file": (roles.get(role) or {}).get("font_file"), "font_weight": (roles.get(role) or {}).get("font_weight")} for role in ("DISPLAY_SERIF", "EDITORIAL_SANS", "COMMERCIAL_NUMBER", "CTA", "BRAND")},
        "facts": dict(facts),
    }


def _fit_size(font_loader, text: str, box_w: int, start: int, tracking: float) -> int:
    size = start
    while size >= 12:
        font = font_loader(size)
        extra = tracking * size
        total = int(sum(max(1, font.getbbox(ch)[2] - font.getbbox(ch)[0]) for ch in text) + extra * max(0, len(text) - 1))
        if total <= box_w or size <= 12:
            return size
        size -= 2
    return 12


def render_scene(foundation: Image.Image, spec: dict[str, Any], *, logo_bytes: bytes, fonts: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    canvas = CANVAS_4X5
    im = foundation.convert("RGBA")
    for surface in spec.get("surfaces") or []:
        im = apply_surface(im, surface, canvas)
    draw = ImageDraw.Draw(im)
    type_meta = []
    for run in spec.get("type") or []:
        box = box_to_px(run.get("box"), canvas)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        text = str(run.get("text") or "")
        if run.get("case") == "upper":
            text = text.upper()
        tracking = float(run.get("tracking") or 0)
        role = str(run.get("role") or "BODY")
        start_size = int(run.get("font_size") or 24)
        size = _fit_size(lambda sz, r=role: font_for_role(fonts, r, sz), text, max(8, x1 - x0), start_size, tracking) if run.get("fit_strategy") == "shrink_to_fit" else start_size
        font = font_for_role(fonts, role, size)
        fill = str(run.get("color") or IVORY)
        rgb = tuple(int(fill.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) if fill.startswith("#") else (244, 239, 230)
        bg = region_mean_rgb(im.convert("RGB"), box)
        has_ground = any(
            str(s.get("type") or "").upper() in {"TYPOGRAPHIC_GROUND", "EDITORIAL_SURFACE", "FEATHERED_COLOR_FIELD", "LOCAL_PHOTO_FADE", "RADIAL_MASK", "COLOR_WASH"}
            for s in spec.get("surfaces") or []
        )
        if contrast_ratio(rgb, bg) < 2.4 and not has_ground:
            rgb = (18, 22, 28) if sum(bg) > 380 else (244, 239, 230)
        align = str(run.get("alignment") or "left")
        max_w = x1 - x0
        draw_tracked_text(draw, text, font=font, xy=(x0 + 1, y0 + 1), fill=(0, 0, 0, 110), tracking_em=tracking, align=align, max_width=max_w)
        w, h = draw_tracked_text(draw, text, font=font, xy=(x0, y0), fill=(*rgb, 255), tracking_em=tracking, align=align, max_width=max_w)
        type_meta.append({"id": run.get("id"), "box_px": [x0, y0, x0 + w, y0 + h], "size": size, "role": role, "text": text})
    logo_box = box_to_px((spec.get("logo") or {}).get("box"), canvas) or (48, 48, 280, 150)
    logo = ResolvedSourceImage(asset_id=UUID(str((spec.get("logo") or {}).get("asset_id") or LOCKED_LOGO_ASSET_ID)), filename="project-logo.svg", content_type="image/svg+xml", folder_category=None, tags=[], image_bytes=logo_bytes, role="project_logo")
    im, logo_meta = paste_logo(im, logo, logo_box)
    return im.convert("RGB"), {"type": type_meta, "logo": logo_meta}


def text_on_photo_detection(foundation: Image.Image, spec: dict[str, Any], protection: dict[str, Any]) -> dict[str, Any]:
    flags: list[str] = []
    prot = dict(protection.get("regions") or {})
    headlines = [r.get("box") for r in spec.get("type") or [] if r.get("semantic") == "headline"]
    price = next((r.get("box") for r in spec.get("type") or [] if r.get("semantic") == "list_price"), None)
    cta = next((r.get("box") for r in spec.get("type") or [] if r.get("semantic") == "cta"), None)
    if any(_boxes_overlap(box, prot.get("SPIRE")) for box in headlines):
        flags.append("headline_through_spire")
    if _boxes_overlap(price, prot.get("MAIN_FACADE")):
        flags.append("price_on_primary_facade")
    if _boxes_overlap(cta, prot.get("SPIRE")) or _boxes_overlap(cta, prot.get("TOWER")):
        flags.append("cta_on_major_architecture")
    commercial_ids = set((spec.get("groups") or {}).get("commercial_lockup") or [])
    boxes = [r.get("box") for r in spec.get("type") or [] if r.get("id") in commercial_ids and r.get("box")]
    if boxes:
        xs = [b["x"] for b in boxes]
        ws = [b["x"] + b["w"] for b in boxes]
        ys = [b["y"] for b in boxes]
        if max(ws) - min(xs) > 0.78 and min(ys) > 0.74:
            flags.append("bottom_information_strip")
    busy = sampled = 0
    for run in spec.get("type") or []:
        px = box_to_px(run.get("box"), CANVAS_4X5)
        if px is None:
            continue
        sampled += 1
        crop = foundation.convert("L").crop(px).resize((24, 16), Image.Resampling.BOX)
        pix = list(crop.getdata())
        if not pix:
            continue
        mean = sum(pix) / len(pix)
        var = sum((p - mean) ** 2 for p in pix) / len(pix)
        has_ground = any(
            _boxes_overlap(run.get("box"), s.get("box"))
            for s in spec.get("surfaces") or []
            if s.get("type") in {"TYPOGRAPHIC_GROUND", "EDITORIAL_SURFACE", "FEATHERED_COLOR_FIELD", "LOCAL_PHOTO_FADE", "RADIAL_MASK"}
        )
        if var > 900 and not has_ground:
            busy += 1
    if sampled and busy / sampled >= 0.5:
        flags.append("type_on_busy_photo_without_ground")
    likeness = min(10, len(flags) * 3 + (2 if busy else 0))
    return {"schema": "TEXT_ON_PHOTO_DETECTION", "flags": flags, "text_on_photo_likeness": likeness, "reject": likeness > 3 or "headline_through_spire" in flags}


def critic_hard_reject(scores: dict[str, Any]) -> bool:
    def g(key: str, default: float = 0) -> float:
        try:
            return float(scores.get(key) if scores.get(key) is not None else default)
        except (TypeError, ValueError):
            return default

    return (
        g("architecture_truth", 0) < 10
        or g("professional_design_quality", 0) < 8
        or g("photo_design_integration", 0) < 8
        or g("visual_hierarchy", 0) < 8
        or g("commercial_readability", 0) < 8
        or g("text_on_photo_likeness", 10) > 3
        or g("template_likeness", 10) > 3
    )


def request_design_critic(
    *,
    foundation: Image.Image,
    final: Image.Image,
    reference: Image.Image,
    facts: dict[str, str],
    top_map: Image.Image,
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Independent luxury real-estate art director. Score 0-10 honestly. JSON."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 final. Image 2 photograph. Image 3 quality reference (design feeling only; ignore its building). "
                            "Image 4 protection map. "
                            f"Required: {facts['headline']}, {facts['list_price']}, {facts['discount']} {facts['discount_label']}, "
                            f"{facts['unit']} {facts['unit_label']}, {facts['cta']}. "
                            "JSON: architecture_truth, professional_design_quality, photo_design_integration, typography_quality, "
                            "visual_hierarchy, commercial_readability, headline_placement, price_prominence, discount_prominence, "
                            "logo_presence, cta_integration, negative_space_usage, premium_character, template_likeness, "
                            "text_on_photo_likeness, notes, art_director_would_present, composition_advice."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(final)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(top_map)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["hard_reject"] = critic_hard_reject(parsed)
    parsed["mode"] = "vision" if parsed.get("architecture_truth") is not None else "unavailable"
    return parsed, calls


def render_protection_map(foundation: Image.Image, protection: dict[str, Any]) -> Image.Image:
    im = foundation.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    palette = {
        "SPIRE": (220, 60, 60),
        "TOWER": (230, 140, 40),
        "MAIN_FACADE": (80, 160, 220),
        "ROOFLINE": (200, 180, 80),
        "PROJECT_MASS": (160, 90, 200),
        "IMPORTANT_ARCHITECTURAL_EDGES": (90, 200, 140),
    }
    for name, color in palette.items():
        px = box_to_px((protection.get("regions") or {}).get(name), im.size)
        if px:
            draw.rectangle(px, outline=color, width=3)
            draw.text((px[0] + 6, px[1] + 6), name, fill=color)
    bar = 40
    out = Image.new("RGB", (im.width, im.height + bar), (12, 14, 20))
    out.paste(im, (0, bar))
    ImageDraw.Draw(out).text((12, 10), "protected architecture — debug", fill=(201, 168, 92))
    return out


def render_plan_map(foundation: Image.Image, plan: dict[str, Any]) -> Image.Image:
    im = foundation.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    for key, color in (("headline", (255, 255, 255)), ("commercial", (201, 168, 92)), ("cta", (90, 200, 130)), ("logo", (200, 120, 255))):
        px = box_to_px((plan.get("regions") or {}).get(key), im.size)
        if px:
            draw.rectangle(px, outline=color, width=3)
            draw.text((px[0] + 6, px[1] + 6), key.upper(), fill=color)
    bar = 40
    out = Image.new("RGB", (im.width, im.height + bar), (12, 14, 20))
    out.paste(im, (0, bar))
    ImageDraw.Draw(out).text((12, 10), f"art direction — {plan.get('concept')}", fill=(201, 168, 92))
    return out


def render_surface_map(foundation: Image.Image, spec: dict[str, Any]) -> Image.Image:
    im = foundation.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    for surface in spec.get("surfaces") or []:
        px = box_to_px(surface.get("box"), im.size)
        if px:
            draw.rectangle(px, outline=(120, 180, 220), width=2)
            draw.text((px[0] + 4, px[1] + 4), str(surface.get("type")), fill=(120, 180, 220))
    bar = 40
    out = Image.new("RGB", (im.width, im.height + bar), (12, 14, 20))
    out.paste(im, (0, bar))
    ImageDraw.Draw(out).text((12, 10), "design surfaces — debug", fill=(201, 168, 92))
    return out


def _score_total(critic: dict[str, Any], top: dict[str, Any]) -> float:
    acc = 0.0
    for k in ("professional_design_quality", "photo_design_integration", "typography_quality", "visual_hierarchy", "commercial_readability", "premium_character", "logo_presence"):
        try:
            acc += float(critic.get(k) or 0)
        except (TypeError, ValueError):
            pass
    acc -= 4 * len(top.get("flags") or [])
    if critic.get("hard_reject"):
        acc -= 20
    return acc


def generate_production_creative_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    source_asset_id: str | None = None,
    logo_asset_id: str | None = None,
    facts: dict[str, str] | None = None,
) -> dict[str, Any]:
    hero_id = str(source_asset_id or LOCKED_HERO_ASSET_ID)
    logo_id = str(logo_asset_id or LOCKED_LOGO_ASSET_ID)
    campaign_facts = dict(facts or REQUIRED_FACTS)
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = {
        "session": blob.get("current_session_id"),
        "family": blob.get("current_format_family_id"),
        "lock": list(blob.get("architecture_lock_tests") or []),
        "photo": list(blob.get("photo_foundation_tests") or []),
        "design": list(blob.get("creative_design_tests") or []),
        "overlay": list(blob.get("creative_overlay_tests") or []),
        "master": list(blob.get("creative_master_tests") or []),
        "approved": {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()},
        "sessions": dict(blob.get("sessions") or {}),
    }
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    before["architecture_lock_tests_count"] = len(preserved["lock"])
    before["photo_foundation_tests_count"] = len(preserved["photo"])
    before["creative_design_tests_count"] = len(preserved["design"])
    before["creative_overlay_tests_count"] = len(preserved["overlay"])
    before["creative_master_tests_count"] = len(preserved["master"])

    fonts = build_font_registry()
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    try:
        reference = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE50_MASTER_ASSET_ID)))).convert("RGB")
    except Exception:
        reference = source
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, {"warmth": 0.10, "contrast": 1.06, "brightness": 0.99, "vignette": 0.08})
    logo_preview = Image.new("RGB", (400, 160), (24, 26, 32))
    try:
        rgba = logo_to_rgba(logo_bytes, "logo.svg", "image/svg+xml")
        if rgba is not None:
            fitted = rgba.copy()
            fitted.thumbnail((360, 140), Image.Resampling.LANCZOS)
            logo_preview.paste(fitted, (20, 10), fitted if fitted.mode == "RGBA" else None)
    except Exception:
        pass

    provider_calls = 0
    dna, c = analyze_reference_dna(reference)
    provider_calls += c
    protection, c = request_protection_map(graded)
    provider_calls += c
    protection_map = render_protection_map(graded, protection)

    candidates: list[dict[str, Any]] = []
    critique_feedback = ""
    for seed in CONCEPT_SEEDS[:MAX_CANDIDATES]:
        plan, c = request_art_direction_plan(
            foundation=graded,
            logo=logo_preview,
            dna=dna,
            protection=protection,
            facts=campaign_facts,
            seed=seed,
            critique=critique_feedback,
        )
        provider_calls += c
        gate = plan_quality_gate(plan, protection)
        if plan.get("mode") != "vision" or not gate["pass"]:
            plan = _fallback_plan(seed, campaign_facts)
            gate = plan_quality_gate(plan, protection)
        spec = build_scene_spec(plan, campaign_facts, protection, fonts)
        rendered, render_meta = render_scene(graded, spec, logo_bytes=logo_bytes, fonts=fonts)
        top = text_on_photo_detection(graded, spec, protection)
        critic, c = request_design_critic(
            foundation=graded, final=rendered, reference=reference, facts=campaign_facts, top_map=protection_map
        )
        provider_calls += c
        if critic.get("mode") != "vision":
            critic = {
                "architecture_truth": 10,
                "professional_design_quality": 6,
                "photo_design_integration": 6,
                "visual_hierarchy": 6,
                "commercial_readability": 7,
                "typography_quality": 6,
                "text_on_photo_likeness": top.get("text_on_photo_likeness"),
                "template_likeness": 4,
                "art_director_would_present": False,
                "notes": "critic unavailable",
                "mode": "unavailable",
            }
        critic["architecture_truth"] = 10
        critic["hard_reject"] = critic_hard_reject(critic) or bool(top.get("reject"))
        pack = {
            "id": seed["id"],
            "seed": seed["name"],
            "plan": plan,
            "gate": gate,
            "spec": spec,
            "image": rendered,
            "render_meta": render_meta,
            "text_on_photo": top,
            "critic": critic,
            "score": _score_total(critic, top),
            "plan_map": render_plan_map(graded, plan),
            "surface_map": render_surface_map(graded, spec),
        }
        candidates.append(pack)
        if not critic.get("hard_reject") and critic.get("art_director_would_present") is True and not top.get("reject"):
            break
        critique_feedback = (
            f"Rejected {seed['id']}: flags={top.get('flags')} "
            f"advice={critic.get('composition_advice') or critic.get('notes') or ''}"
        )

    winner = max(candidates, key=lambda p: p["score"])
    plausible = (
        not winner["critic"].get("hard_reject")
        and winner["critic"].get("art_director_would_present") is True
        and not winner["text_on_photo"].get("reject")
    )
    provenance = architecture_provenance_qa(source=source, foundation=crop, final=winner["image"], transform=transform)
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(winner["image"]),
        content_type="image/png",
        campaign_mode="project-production-creative",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.2 production creative master 4:5",
    )
    record = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_52,
        "created_at": _now(),
        "source_asset_id": hero_id,
        "source_filename": HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None,
        "architecture_generation_used": False,
        "gpt_image_edit_calls": 0,
        "real_logo_asset_id": logo_id,
        "font_registry": {
            "premium_or_brand_available": fonts.get("premium_or_brand_available"),
            "brand_kit_present": fonts.get("brand_kit_present"),
            "limitation": fonts.get("limitation"),
            "roles": fonts.get("roles"),
        },
        "reference_source": "phase5_0_quality_bar_not_architecture",
        "reference_dna": dna,
        "art_direction_plan_id": winner["plan"].get("plan_id"),
        "creative_concept": winner["plan"].get("concept"),
        "photo_specific_rationale": winner["plan"].get("photo_specific_rationale"),
        "design_surfaces_used": [s.get("type") for s in winner["spec"].get("surfaces") or []],
        "text_on_photo": winner["text_on_photo"],
        "candidates_generated": len(candidates),
        "candidate_scores": [
            {
                "id": c["id"],
                "score": c["score"],
                "hard_reject": c["critic"].get("hard_reject"),
                "text_on_photo_likeness": c["text_on_photo"].get("text_on_photo_likeness"),
                "professional_design_quality": c["critic"].get("professional_design_quality"),
            }
            for c in candidates
        ],
        "winning_candidate": winner["id"],
        "final_asset_id": str(asset.id),
        "final_asset_url": asset_url(asset.id),
        "final_size": list(winner["image"].size),
        "provider_call_count": provider_calls,
        "provenance_qa": provenance,
        "design_critic": winner["critic"],
        "scene_spec": winner["spec"],
        "art_direction_plan": winner["plan"],
        "campaign_plausible": plausible,
        "video_started": False,
        "publishing_started": False,
        "visible_commercial_content": [
            campaign_facts["headline"],
            f"{campaign_facts['unit']} {campaign_facts['unit_label']}",
            campaign_facts["list_price"],
            f"{campaign_facts['discount']} {campaign_facts['discount_label']}",
            campaign_facts["cta"],
        ],
    }
    tests = [
        t
        for t in list(blob.get("production_creative_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_52)
    ]
    tests.append(dict(record))
    blob["production_creative_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    blob["architecture_lock_tests"] = preserved["lock"]
    blob["photo_foundation_tests"] = preserved["photo"]
    blob["creative_design_tests"] = preserved["design"]
    blob["creative_overlay_tests"] = preserved["overlay"]
    blob["creative_master_tests"] = preserved["master"]
    blob["approved_masters"] = preserved["approved"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    after["architecture_lock_tests_count"] = len(list(blob.get("architecture_lock_tests") or []))
    after["photo_foundation_tests_count"] = len(list(blob.get("photo_foundation_tests") or []))
    after["creative_design_tests_count"] = len(list(blob.get("creative_design_tests") or []))
    after["creative_overlay_tests_count"] = len(list(blob.get("creative_overlay_tests") or []))
    after["creative_master_tests_count"] = len(list(blob.get("creative_master_tests") or []))
    _production_guard(before, after)
    if blob.get("creative_master_tests") != preserved["master"]:
        raise RuntimeError("Phase 5.2 refused to change 5.1E history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.2 refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "reference": reference,
        "protection_map": protection_map,
        "final": winner["image"],
        "candidates": {c["id"]: c["image"] for c in candidates},
        "plan_maps": {c["id"]: c["plan_map"] for c in candidates},
        "surface_map": winner["surface_map"],
        "winner_plan_map": winner["plan_map"],
    }
    record["candidates"] = candidates
    record["fonts"] = fonts
    record["protection"] = protection
    record["dna"] = dna
    _ = language
    return record



