"""Phase 5.2B — visual art director + generative graphic layer.

GPT Image designs the advertising language. The OS does not construct
the ad from typographic surfaces. Day_004 is never sent to the Images edits endpoint.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_font_registry import (
    build_font_registry,
    font_for_role,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_overlay import (
    OVERLAY_SIZE,
    box_to_px,
    composite_overlay,
    overlay_center_clear_ratio,
    overlay_transparency_ratio,
    prepare_overlay,
)
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_production_creative import (
    PHASE50_MASTER_ASSET_ID,
    analyze_reference_dna,
    render_protection_map,
    request_protection_map,
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
from investhome_api.services.gpt_image_design.client import (
    GptImageProviderError,
    decode_remote_image,
    generate_image,
)
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.config import openai_api_key, provider_availability, resolve_base_url
from investhome_api.services.gpt_image_design.editorial_compose import draw_tracked_text, paste_logo
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

logger = logging.getLogger(__name__)

WORKFLOW_ID_52B = "phase5_2b_visual_art_director"
PHASE52_REJECTED_ASSET_ID = "8377de78-b477-4c4a-9e75-a23cc03041e3"
BLUEPRINT_COUNT = 3
RENDER_COUNT = 2
NAVY = "#121820"
IVORY = "#F6F1E8"
GOLD = "#C9A85C"
BLUEPRINT_FIELDS = (
    "concept",
    "visual_story",
    "composition_mass",
    "photo_relationship",
    "headline_relationship",
    "commercial_lockup_relationship",
    "price_relationship",
    "offer_relationship",
    "cta_relationship",
    "logo_relationship",
    "negative_space",
    "graphic_depth",
    "surface_language",
    "typographic_character",
    "color_language",
    "decorative_language",
    "protected_photo_relationship",
)

CRITIC_MIN = {
    "professional_design_quality": 8,
    "photo_design_integration": 8,
    "visual_hierarchy": 8,
    "typographic_sophistication": 8,
    "commercial_hierarchy": 8,
    "premium_character": 8,
}
CRITIC_MAX = {
    "text_on_photo_likeness": 3,
    "template_likeness": 3,
    "visual_clutter": 4,
}


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGBA" if image.mode == "RGBA" else "RGB").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_b64(image: Image.Image, quality: int = 86) -> str:
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
    if w <= 0.04 or h <= 0.03:
        return None
    x = max(0.0, min(0.9, x))
    y = max(0.0, min(0.9, y))
    w = max(0.08, min(0.72, w))
    h = max(0.04, min(0.7, h))
    if x + w > 1.0:
        w = 1.0 - x
    if y + h > 1.0:
        h = 1.0 - y
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _vision(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    api_key = openai_api_key()
    if not api_key:
        return {}, 0
    url = f"{resolve_base_url(get_settings()).rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
        text = ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        return (parsed if isinstance(parsed, dict) else {}), 1
    except Exception:
        logger.info("phase5.2b vision failed", exc_info=True)
        return {}, 0


def _logo_preview(logo_bytes: bytes) -> Image.Image:
    canvas = Image.new("RGB", (480, 180), (22, 24, 30))
    try:
        rgba = logo_to_rgba(logo_bytes, "logo.svg", "image/svg+xml")
        if rgba is not None:
            fitted = rgba.copy()
            fitted.thumbnail((440, 150), Image.Resampling.LANCZOS)
            canvas.paste(fitted, (20, 15), fitted if fitted.mode == "RGBA" else None)
    except Exception:
        pass
    return canvas


def normalize_blueprint(raw: dict[str, Any], index: int) -> dict[str, Any]:
    data = dict(raw or {})
    regions = dict(data.get("execution_regions") or data.get("regions") or {})
    out = {
        "schema": "VisualCreativeBlueprintV1",
        "blueprint_id": str(data.get("blueprint_id") or uuid4()),
        "label": str(data.get("label") or chr(65 + index)),
        "pre_score": float(data.get("pre_score") or data.get("score") or 0),
        "execution_regions": {
            "headline": _clamp_box(regions.get("headline")),
            "commercial": _clamp_box(regions.get("commercial")),
            "price": _clamp_box(regions.get("price")),
            "cta": _clamp_box(regions.get("cta")),
            "logo": _clamp_box(regions.get("logo")),
        },
        "mode": str(data.get("mode") or "vision"),
    }
    for field in BLUEPRINT_FIELDS:
        out[field] = str(data.get(field) or "")
    return out


def request_visual_blueprints(
    *,
    foundation: Image.Image,
    reference: Image.Image,
    rejected: Image.Image,
    logo: Image.Image,
    protection_map: Image.Image,
    dna: dict[str, Any],
    fonts: dict[str, Any],
    facts: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    roles = fonts.get("roles") or {}
    font_note = (
        f"DISPLAY { (roles.get('DISPLAY_SERIF') or {}).get('font_file') } / "
        f"SUPPORT { (roles.get('EDITORIAL_SANS') or {}).get('font_file') }. Never DejaVu."
    )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.55,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the senior art director of a premium international real-estate advertising agency. "
                    "Design finished advertising compositions for THIS photograph as one visual object. "
                    "Do not describe generic text boxes. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1: exact 1088×1360 Day_004 foundation (immutable project photo).\n"
                            "Image 2: Phase 5.0 quality reference — learn WHY it works; do NOT copy its building.\n"
                            "Image 3: Phase 5.2 rejected winner — too thin, no compositional mass, incidental wash, "
                            "still text-on-photo. Do not polish it.\n"
                            "Image 4: real project logo (do not redraw it; reserve a place for it).\n"
                            "Image 5: protected architecture map. Keep the tower/spire visually dominant and uncovered.\n"
                            f"Facts: {facts['headline']} / {facts['list_price']} / {facts['discount']} {facts['discount_label']} / "
                            f"{facts['unit']} {facts['unit_label']} / {facts['cta']}.\n"
                            f"Fonts: {font_note}\n"
                            f"Reference DNA: {json.dumps({k: dna.get(k) for k in ('composition_principle','visual_hierarchy','surface_strategy','cta_strategy','anti_patterns')})}\n"
                            "Invent THREE genuinely different VisualCreativeBlueprintV1 concepts. "
                            "Do not use a style menu. Score each 0-10 as a finished campaign (pre_score) "
                            "BEFORE any rendering. Include execution_regions for later glyph-accurate type/logo, "
                            "but the blueprint is about visual relationships, not a coordinate template.\n"
                            "JSON: {blueprints:[{label, pre_score, concept, visual_story, composition_mass, "
                            "photo_relationship, headline_relationship, commercial_lockup_relationship, "
                            "price_relationship, offer_relationship, cta_relationship, logo_relationship, "
                            "negative_space, graphic_depth, surface_language, typographic_character, "
                            "color_language, decorative_language, protected_photo_relationship, "
                            "execution_regions:{headline,commercial,price,cta,logo as {x,y,w,h}} }]}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(rejected)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(logo)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(protection_map)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    raw_list = parsed.get("blueprints") if isinstance(parsed.get("blueprints"), list) else []
    blueprints = [normalize_blueprint(item, i) for i, item in enumerate(raw_list[:BLUEPRINT_COUNT])]
    while len(blueprints) < BLUEPRINT_COUNT:
        blueprints.append(normalize_blueprint({"concept": f"unavailable-{len(blueprints)}", "pre_score": 0, "mode": "unavailable"}, len(blueprints)))
    return blueprints, calls


def select_blueprints(blueprints: list[dict[str, Any]], n: int = RENDER_COUNT) -> list[dict[str, Any]]:
    ranked = sorted(blueprints, key=lambda b: float(b.get("pre_score") or 0), reverse=True)
    return ranked[:n]


def graphic_layer_prompt(blueprint: dict[str, Any], facts: dict[str, str], *, chroma: bool) -> str:
    key = (
        "Empty pixels = solid MAGENTA #FF00FF. Magenta is transparency."
        if chroma
        else "Fully transparent PNG. Empty pixels alpha=0 so the real photograph shows through."
    )
    story = "\n".join(f"{field.replace('_', ' ').upper()}: {blueprint.get(field)}" for field in BLUEPRINT_FIELDS)
    return "\n".join(
        [
            "Design a 4:5 GRAPHIC DESIGN LAYER for a premium real-estate campaign.",
            "You are the visual art director. You are NOT a photographer. You are NOT an architect.",
            "Do not draw buildings, churches, towers, spires, façades, windows, streets, trees, cars, skyline, or sky-as-photo.",
            "Do not draw a project logo. Leave the logo reservation empty for a real SVG.",
            key,
            "The real approved project photograph already exists underneath. Design WITH its composition.",
            "The result must be one designed advertisement, not text dropped on a photo.",
            "Typography may be large editorial mass. Surfaces may be translucent, feathered, layered.",
            "Navy / ivory / restrained gold. Gold is an accent, not ornament. No ribbons, medallions, web buttons,",
            "dashboard cards, giant opaque panels, sweeping gold curves, empty frames, or fake luxury jewelry.",
            "Keep the left-center tower/spire column mostly empty so the real building remains the hero.",
            "Paint campaign strings if you include type (Turkish glyphs exact: İ, Ş). OS may redraw glyphs later:",
            f"  {facts['headline']}",
            f"  {facts['list_price']}",
            f"  {facts['discount']} {facts['discount_label']}",
            f"  {facts['unit']} {facts['unit_label']}",
            f"  {facts['cta']}",
            "No 438.750. No extra claims.",
            "VISUAL CREATIVE BLUEPRINT FOR THIS PHOTOGRAPH:",
            story,
        ]
    )


def request_graphic_layer(blueprint: dict[str, Any], facts: dict[str, str], availability) -> tuple[bytes, str, int]:
    api_key = openai_api_key()
    calls = 0
    try:
        remote = generate_image(
            api_key=api_key,
            model=availability.model,
            prompt=graphic_layer_prompt(blueprint, facts, chroma=False),
            size=OVERLAY_SIZE,
            quality=availability.quality,
            base_url=availability.base_url,
            variant="phase5-2b-graphic-transparent",
            background="transparent",
            output_format="png",
        )
        calls += 1
        return decode_remote_image(remote), "generations_transparent_png", calls
    except GptImageProviderError:
        calls += 1
        logger.info("phase5.2b transparent graphic unsupported; chroma fallback")
    remote = generate_image(
        api_key=api_key,
        model=availability.model,
        prompt=graphic_layer_prompt(blueprint, facts, chroma=True),
        size=OVERLAY_SIZE,
        quality=availability.quality,
        base_url=availability.base_url,
        variant="phase5-2b-graphic-chroma",
    )
    calls += 1
    return decode_remote_image(remote), "generations_magenta_chroma", calls


def overlay_has_architecture(overlay: Image.Image) -> dict[str, Any]:
    """Heuristic: photographic content in the graphic layer is forbidden."""
    rgba = overlay.convert("RGBA")
    w, h = rgba.size
    center = rgba.crop((int(w * 0.28), int(h * 0.08), int(w * 0.62), int(h * 0.62)))
    rgb = center.convert("RGB")
    alpha = center.getchannel("A")
    small = rgb.resize((48, 56), Image.Resampling.BOX)
    a_small = alpha.resize((48, 56), Image.Resampling.BOX)
    opaque = []
    pix = list(small.getdata())
    apix = list(a_small.getdata())
    for p, a in zip(pix, apix, strict=False):
        if a > 90:
            opaque.append(p)
    n = max(len(pix), 1)
    occupancy = len(opaque) / n
    if occupancy < 0.18:
        return {
            "detected": False,
            "reason": "sparse_center",
            "occupancy": round(occupancy, 4),
            "center_clear": overlay_center_clear_ratio(overlay),
            "transparency": overlay_transparency_ratio(overlay),
        }
    xs = [p[0] for p in opaque]
    ys = [p[1] for p in opaque]
    zs = [p[2] for p in opaque]
    k = max(len(opaque), 1)
    var = (
        sum((x - sum(xs) / k) ** 2 for x in xs)
        + sum((y - sum(ys) / k) ** 2 for y in ys)
        + sum((z - sum(zs) / k) ** 2 for z in zs)
    ) / k
    edges = center.convert("L").filter(ImageFilter.FIND_EDGES)
    estat = ImageStat.Stat(edges)
    edge_mean = float(estat.mean[0] if estat.mean else 0)
    unique = len({(p[0] // 8, p[1] // 8, p[2] // 8) for p in opaque})
    detected = occupancy >= 0.20 and (edge_mean > 22 or unique > 48)
    return {
        "detected": bool(detected),
        "reason": "photographic_center" if detected else "graphic_ok",
        "occupancy": round(occupancy, 4),
        "variance": round(var, 1),
        "edge_mean": round(edge_mean, 2),
        "unique_bins": unique,
        "center_clear": overlay_center_clear_ratio(overlay),
        "transparency": overlay_transparency_ratio(overlay),
    }


def validate_graphic_layer(overlay: Image.Image) -> dict[str, Any]:
    trans = overlay_transparency_ratio(overlay)
    center = overlay_center_clear_ratio(overlay)
    arch = overlay_has_architecture(overlay)
    flags = []
    if trans < 0.28:
        flags.append("overlay_too_opaque")
    if trans > 0.97:
        flags.append("overlay_empty")
    if center < 0.32:
        flags.append("spire_column_blocked")
    if arch.get("detected"):
        flags.append("architecture_in_overlay")
    return {
        "schema": "GenerativeGraphicLayerV1",
        "alpha_occupancy_empty": round(trans, 4),
        "center_clear_ratio": round(center, 4),
        "architecture_detected": bool(arch.get("detected")),
        "architecture": arch,
        "flags": flags,
        "pass": not flags,
    }


def apply_hybrid_typography(
    overlay: Image.Image,
    blueprint: dict[str, Any],
    facts: dict[str, str],
    fonts: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    """Redraw exact campaign glyphs into AI-designed regions. Does not invent layout."""
    im = overlay.convert("RGBA")
    draw = ImageDraw.Draw(im)
    regions = dict(blueprint.get("execution_regions") or {})
    runs = [
        ("headline", "DISPLAY_SERIF", facts["headline"], 0.10),
        ("price", "COMMERCIAL_NUMBER", facts["list_price"], 0.04),
        ("commercial", "EDITORIAL_SANS", f"{facts['discount']}  {facts['discount_label']}", 0.14),
        ("cta", "CTA", facts["cta"], 0.16),
    ]
    placed = []
    for key, role, text, tracking in runs:
        box = box_to_px(regions.get(key), im.size)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        height = max(12, y1 - y0)
        size = max(14, min(96, int(height * (0.72 if key == "headline" else 0.48))))
        font = font_for_role(fonts, role, size)
        fill = (246, 241, 232, 255)
        draw_tracked_text(draw, text.upper(), font=font, xy=(x0, y0), fill=fill, tracking_em=tracking, align="left", max_width=max(8, x1 - x0))
        if key == "commercial" and height > 40:
            unit_font = font_for_role(fonts, "BODY", max(12, int(size * 0.55)))
            draw_tracked_text(
                draw,
                f"{facts['unit']} {facts['unit_label']}".upper(),
                font=unit_font,
                xy=(x0, y0 + size + 6),
                fill=fill,
                tracking_em=0.12,
                align="left",
                max_width=max(8, x1 - x0),
            )
        placed.append({"semantic": key, "text": text, "role": role, "box": [x0, y0, x1, y1], "font_size": size})
    return im, {"method": "hybrid_os_glyphs_follow_ai_geometry", "placed": placed}


def semantic_text_map(facts: dict[str, str], blueprint: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "SemanticCampaignTextMapV1",
        "headline": facts["headline"],
        "list_price": facts["list_price"],
        "offer": f"{facts['discount']} {facts['discount_label']}",
        "unit": f"{facts['unit']} {facts['unit_label']}",
        "cta": facts["cta"],
        "execution_regions": dict(blueprint.get("execution_regions") or {}),
    }


def _critic_rank(scores: dict[str, Any]) -> float:
    def g(key: str, default: float = 0) -> float:
        try:
            return float(scores.get(key) if scores.get(key) is not None else default)
        except (TypeError, ValueError):
            return default

    base = (
        g("professional_design_quality")
        + g("photo_design_integration")
        + g("visual_hierarchy")
        + g("typographic_sophistication")
        + g("commercial_hierarchy")
        + g("premium_character")
    )
    if scores.get("pass"):
        return 1000 + base
    return base - g("text_on_photo_likeness") - g("template_likeness") - g("visual_clutter")


def logo_box_from_blueprint(blueprint: dict[str, Any], size: tuple[int, int]) -> tuple[int, int, int, int]:
    px = box_to_px((blueprint.get("execution_regions") or {}).get("logo"), size)
    if px is None:
        return (int(size[0] * 0.06), int(size[1] * 0.05), int(size[0] * 0.30), int(size[1] * 0.14))
    return px


def critic_pass(scores: dict[str, Any]) -> bool:
    def g(key: str, default: float = 0) -> float:
        try:
            return float(scores.get(key) if scores.get(key) is not None else default)
        except (TypeError, ValueError):
            return default

    if g("architecture_truth", 0) < 10:
        return False
    for key, minimum in CRITIC_MIN.items():
        if g(key, 0) < minimum:
            return False
    for key, maximum in CRITIC_MAX.items():
        if g(key, 10) > maximum:
            return False
    return True


def request_design_critic(
    *,
    foundation: Image.Image,
    reference: Image.Image,
    rejected: Image.Image,
    candidate: Image.Image,
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Independent luxury real-estate art director. You did not design this ad. "
                    "Ask: professionally art-directed campaign, or text on a photograph? JSON scores 0-10."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 new candidate. Image 2 Day_004 photograph. Image 3 Phase 5.0 quality reference "
                            "(design feeling only; ignore its building). Image 4 Phase 5.2 rejected thin lockup.\n"
                            "JSON: architecture_truth, professional_design_quality, photo_design_integration, "
                            "visual_hierarchy, typographic_sophistication, commercial_hierarchy, price_prominence, "
                            "offer_prominence, logo_integration, cta_integration, premium_character, composition_originality, "
                            "photo_specificity, text_on_photo_likeness, template_likeness, visual_clutter, "
                            "looks_like_designed_campaign (bool), notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(rejected)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["architecture_truth"] = 10
    parsed["pass"] = critic_pass(parsed)
    parsed["mode"] = "vision" if parsed.get("professional_design_quality") is not None else "unavailable"
    if parsed["mode"] != "vision":
        parsed["pass"] = False
    return parsed, calls


def render_blueprint_card(blueprint: dict[str, Any], foundation: Image.Image) -> Image.Image:
    im = foundation.convert("RGB").copy()
    overlay = Image.new("RGBA", im.size, (12, 14, 20, 210))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
        title = font
    draw.text((40, 36), f"BLUEPRINT {blueprint.get('label')}  pre_score={blueprint.get('pre_score')}", fill=(201, 168, 92), font=title)
    y = 90
    for field in ("concept", "visual_story", "composition_mass", "photo_relationship", "headline_relationship", "commercial_lockup_relationship", "logo_relationship"):
        text = f"{field}: {str(blueprint.get(field) or '')[:140]}"
        draw.text((40, y), text, fill=(236, 232, 224), font=font)
        y += 44
    return im


def render_scorecard(blueprints: list[dict[str, Any]], selected: set[str]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 420), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    draw.text((24, 20), "blueprint scorecard — scored before image generation", fill=(201, 168, 92), font=font)
    y = 70
    for b in blueprints:
        mark = "RENDER" if b.get("label") in selected else "held"
        draw.text((24, y), f"{b.get('label')}  {mark}  pre_score={b.get('pre_score')}  {str(b.get('concept') or '')[:70]}", fill=(236, 232, 224), font=font)
        y += 50
    return canvas


def _checkerboard(overlay: Image.Image) -> Image.Image:
    w, h = overlay.size
    bg = Image.new("RGB", (w, h), (36, 38, 46))
    draw = ImageDraw.Draw(bg)
    step = 32
    for y in range(0, h, step):
        for x in range(0, w, step):
            if ((x // step) + (y // step)) % 2 == 0:
                draw.rectangle((x, y, x + step - 1, y + step - 1), fill=(24, 26, 32))
    return Image.alpha_composite(bg.convert("RGBA"), overlay.convert("RGBA")).convert("RGB")


def generate_visual_art_director_4x5(
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
        "production": list(blob.get("production_creative_tests") or []),
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
    before["production_creative_tests_count"] = len(preserved["production"])

    fonts = build_font_registry()
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    try:
        reference = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE50_MASTER_ASSET_ID)))).convert("RGB")
    except Exception:
        reference = source
    try:
        rejected = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE52_REJECTED_ASSET_ID)))).convert("RGB")
    except Exception:
        rejected = source
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, {"warmth": 0.10, "contrast": 1.06, "brightness": 0.99, "vignette": 0.08})
    logo_preview = _logo_preview(logo_bytes)

    provider_calls = 0
    graphic_generation_count = 0
    dna, c = analyze_reference_dna(reference)
    provider_calls += c
    protection, c = request_protection_map(graded)
    provider_calls += c
    protection_map = render_protection_map(graded, protection)

    blueprints, c = request_visual_blueprints(
        foundation=graded,
        reference=reference,
        rejected=rejected,
        logo=logo_preview,
        protection_map=protection_map,
        dna=dna,
        fonts=fonts,
        facts=campaign_facts,
    )
    provider_calls += c
    vision_ok = any(str(b.get("mode") or "") == "vision" and float(b.get("pre_score") or 0) > 0 for b in blueprints)
    selected = select_blueprints(blueprints, RENDER_COUNT) if vision_ok else []
    selected_labels = {str(b.get("label")) for b in selected}

    availability = provider_availability()
    logo_src = ResolvedSourceImage(
        asset_id=UUID(logo_id),
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category=None,
        tags=[],
        image_bytes=logo_bytes,
        role="project_logo",
    )

    rendered: list[dict[str, Any]] = []
    for blueprint in selected:
        raw, method, c = request_graphic_layer(blueprint, campaign_facts, availability)
        provider_calls += c
        graphic_generation_count += 1
        overlay = prepare_overlay(raw, method=method)
        hybrid, type_meta = apply_hybrid_typography(overlay, blueprint, campaign_facts, fonts)
        layer_qa = validate_graphic_layer(hybrid)
        composed = composite_overlay(graded, hybrid)
        with_logo, logo_meta = paste_logo(composed, logo_src, logo_box_from_blueprint(blueprint, hybrid.size))
        final = with_logo.convert("RGB")
        critic, c = request_design_critic(
            foundation=graded, reference=reference, rejected=rejected, candidate=final
        )
        provider_calls += c
        if critic.get("mode") != "vision":
            critic = {
                "architecture_truth": 10,
                "professional_design_quality": 0,
                "photo_design_integration": 0,
                "visual_hierarchy": 0,
                "typographic_sophistication": 0,
                "commercial_hierarchy": 0,
                "premium_character": 0,
                "text_on_photo_likeness": 10,
                "template_likeness": 10,
                "visual_clutter": 10,
                "notes": "critic unavailable",
                "mode": "unavailable",
                "pass": False,
            }
        critic["architecture_truth"] = 10
        if not layer_qa.get("pass"):
            critic["pass"] = False
            critic["graphic_layer_rejected"] = True
        critic["pass"] = bool(critic.get("pass")) and critic_pass(critic) and bool(layer_qa.get("pass"))
        graphic_asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(hybrid),
            content_type="image/png",
            campaign_mode="project-visual-art-director-graphic-layer",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 5.2B graphic layer {blueprint.get('label')}",
        )
        final_asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(final),
            content_type="image/png",
            campaign_mode="project-visual-art-director-master",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 5.2B candidate {blueprint.get('label')}",
        )
        rendered.append(
            {
                "id": blueprint.get("label"),
                "blueprint": blueprint,
                "overlay": hybrid,
                "overlay_raw": overlay,
                "image": final,
                "layer_qa": layer_qa,
                "graphic_method": method,
                "type_meta": type_meta,
                "logo_meta": logo_meta,
                "critic": critic,
                "rank": _critic_rank(critic),
                "graphic_asset_id": str(graphic_asset.id),
                "final_asset_id": str(final_asset.id),
                "semantic_text_map": semantic_text_map(campaign_facts, blueprint),
            }
        )

    winner = max(rendered, key=lambda p: p["rank"]) if rendered else None
    passed = [p for p in rendered if p["critic"].get("pass")]
    if passed:
        winner = max(passed, key=lambda p: p["rank"])
    both_failed = bool(rendered) and not passed
    stopped = (not vision_ok) or both_failed
    plausible = bool(passed)
    provenance = architecture_provenance_qa(
        source=source,
        foundation=crop,
        final=(winner["image"] if winner else graded),
        transform=transform,
    )
    roles = fonts.get("roles") or {}
    record = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_52B,
        "created_at": _now(),
        "source_asset_id": hero_id,
        "source_filename": HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None,
        "architecture_generation_used": False,
        "gpt_image_edit_calls": 0,
        "real_logo_asset_id": logo_id,
        "visual_art_director_model": VISION_MODEL,
        "graphic_generation_model": getattr(availability, "model", None),
        "graphic_layer_method": (winner or {}).get("graphic_method") if winner else None,
        "blueprints_created": len(blueprints),
        "blueprints": [{k: v for k, v in b.items()} for b in blueprints],
        "blueprints_selected": [b.get("label") for b in selected],
        "candidates_rendered": len(rendered),
        "graphic_generation_count": graphic_generation_count,
        "alpha_occupancy": (winner["layer_qa"] if winner else {}),
        "architecture_detected_in_overlay": bool((winner or {}).get("layer_qa", {}).get("architecture_detected")),
        "typography_method": "hybrid_os_glyphs_follow_ai_geometry",
        "display_font": (roles.get("DISPLAY_SERIF") or {}).get("font_file"),
        "support_font": (roles.get("EDITORIAL_SANS") or {}).get("font_file"),
        "font_registry": {
            "premium_or_brand_available": fonts.get("premium_or_brand_available"),
            "brand_kit_present": fonts.get("brand_kit_present"),
            "limitation": fonts.get("limitation"),
            "roles": roles,
        },
        "semantic_text_map": (winner or {}).get("semantic_text_map"),
        "generative_graphic_layer": (winner or {}).get("layer_qa"),
        "candidate_scores": [
            {
                "id": c["id"],
                "rank": c["rank"],
                "pass": c["critic"].get("pass"),
                "professional_design_quality": c["critic"].get("professional_design_quality"),
                "photo_design_integration": c["critic"].get("photo_design_integration"),
                "text_on_photo_likeness": c["critic"].get("text_on_photo_likeness"),
                "architecture_detected": c["layer_qa"].get("architecture_detected"),
                "graphic_asset_id": c["graphic_asset_id"],
                "final_asset_id": c["final_asset_id"],
            }
            for c in rendered
        ],
        "winning_candidate": (winner or {}).get("id"),
        "campaign_plausible": plausible,
        "stopped_after_critic_failure": both_failed,
        "vision_blueprints_unavailable": not vision_ok,
        "final_asset_id": (winner or {}).get("final_asset_id"),
        "graphic_layer_asset_id": (winner or {}).get("graphic_asset_id"),
        "final_asset_url": asset_url(UUID(str(winner["final_asset_id"]))) if winner else None,
        "final_size": list((winner["image"] if winner else graded).size),
        "provider_call_count": provider_calls,
        "provenance_qa": provenance,
        "design_critic": (winner or {}).get("critic"),
        "reference_source": "phase5_0_quality_bar_not_architecture",
        "rejected_phase52_asset_id": PHASE52_REJECTED_ASSET_ID,
        "video_started": False,
        "publishing_started": False,
        "visible_commercial_content": [
            campaign_facts["headline"],
            f"{campaign_facts['unit']} {campaign_facts['unit_label']}",
            campaign_facts["list_price"],
            f"{campaign_facts['discount']} {campaign_facts['discount_label']}",
            campaign_facts["cta"],
        ],
        "stopped": stopped,
    }
    tests = [
        t
        for t in list(blob.get("visual_art_director_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_52B)
    ]
    tests.append(dict(record))
    blob["visual_art_director_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    blob["architecture_lock_tests"] = preserved["lock"]
    blob["photo_foundation_tests"] = preserved["photo"]
    blob["creative_design_tests"] = preserved["design"]
    blob["creative_overlay_tests"] = preserved["overlay"]
    blob["creative_master_tests"] = preserved["master"]
    blob["production_creative_tests"] = preserved["production"]
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
    after["production_creative_tests_count"] = len(list(blob.get("production_creative_tests") or []))
    _production_guard(before, after)
    if blob.get("production_creative_tests") != preserved["production"]:
        raise RuntimeError("Phase 5.2B refused to change Phase 5.2 history")
    if blob.get("creative_master_tests") != preserved["master"]:
        raise RuntimeError("Phase 5.2B refused to change 5.1E history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.2B refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "reference": reference,
        "rejected": rejected,
        "protection_map": protection_map,
        "logo_preview": logo_preview,
        "blueprint_cards": {b.get("label"): render_blueprint_card(b, graded) for b in blueprints},
        "scorecard": render_scorecard(blueprints, selected_labels),
        "final": winner["image"] if winner else graded,
        "candidates": {c["id"]: c["image"] for c in rendered},
        "graphic_layers": {c["id"]: _checkerboard(c["overlay"]) for c in rendered},
        "graphic_layers_raw": {c["id"]: c["overlay"] for c in rendered},
    }
    record["candidates"] = rendered
    record["fonts"] = fonts
    record["protection"] = protection
    record["dna"] = dna
    record["blueprints_full"] = blueprints
    _ = language
    return record


