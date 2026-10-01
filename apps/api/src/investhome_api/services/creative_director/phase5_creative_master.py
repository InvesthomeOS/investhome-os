"""Phase 5.1E — AI-designed advertisement on an immutable project photograph.

Architecture pixels come only from the locked 5.1B photo foundation.
gpt-image-2 designs the graphic layer. The OS only composites + places the real logo.

Reusable for any Investhome project: pass that project's approved source photo and logo.
The AI may redesign the advertisement. It may not redesign the project.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_overlay import (
    OVERLAY_SIZE,
    box_to_px,
    composite_overlay,
    prepare_overlay,
    overlay_transparency_ratio,
)
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
from investhome_api.services.gpt_image_design.client import (
    GptImageProviderError,
    decode_remote_image,
    generate_image,
)
from investhome_api.services.gpt_image_design.config import (
    ASPECT_TO_SIZE,
    openai_api_key,
    provider_availability,
    resolve_base_url,
)
from investhome_api.services.gpt_image_design.editorial_compose import paste_logo
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

logger = logging.getLogger(__name__)

WORKFLOW_ID_51E = "phase5_1e_final_master"
MAX_DESIGN_RETRIES = 2
CRITIQUE_FAIL_KEYS = (
    "headline_intersects_spire",
    "typography_covers_major_architecture",
    "price_dominates",
    "commercial_disconnected",
    "cta_floats",
    "logo_pasted",
    "text_unreadable",
    "supporting_too_small",
    "dashboard_cards",
    "giant_badge",
    "ribbons",
    "excessive_gold_curves",
    "giant_opaque_panel",
    "template_composition",
    "text_on_photo",
    "architecture_not_hero",
    "malformed_typography",
    "contains_generated_architecture",
)


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


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
    if w <= 0.02 or h <= 0.02:
        return None
    x = max(0.0, min(0.92, x))
    y = max(0.0, min(0.92, y))
    w = max(0.04, min(0.9, w))
    h = max(0.04, min(0.9, h))
    if x + w > 1.0:
        w = 1.0 - x
    if y + h > 1.0:
        h = 1.0 - y
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _box_pct(box: dict[str, float] | None) -> str:
    if not box:
        return "unspecified — invent an elegant relationship to the photograph"
    x0, y0 = box["x"] * 100, box["y"] * 100
    x1, y1 = (box["x"] + box["w"]) * 100, (box["y"] + box["h"]) * 100
    return f"x {x0:.0f}–{x1:.0f}%, y {y0:.0f}–{y1:.0f}% of the 1088×1360 canvas"


def _font(size: int = 16):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def normalize_composition_plan(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(raw or {})
    regions = dict(data.get("regions") or {})
    safe = [_clamp_box(x) for x in (data.get("safe_regions") or [])]
    forbidden = [_clamp_box(x) for x in (data.get("forbidden_regions") or [])]
    return {
        "plan_id": str(data.get("plan_id") or uuid4()),
        "schema": "CreativeCompositionPlanV1",
        "concept": str(data.get("concept") or ""),
        "visual_story": str(data.get("visual_story") or ""),
        "focal_point": str(data.get("focal_point") or ""),
        "protected_architecture": str(data.get("protected_architecture") or ""),
        "headline_strategy": str(data.get("headline_strategy") or ""),
        "commercial_information_strategy": str(data.get("commercial_information_strategy") or ""),
        "cta_strategy": str(data.get("cta_strategy") or ""),
        "logo_strategy": str(data.get("logo_strategy") or ""),
        "typography_strategy": str(data.get("typography_strategy") or ""),
        "contrast_strategy": str(data.get("contrast_strategy") or ""),
        "negative_space_strategy": str(data.get("negative_space_strategy") or ""),
        "depth_strategy": str(data.get("depth_strategy") or ""),
        "graphic_language": str(data.get("graphic_language") or ""),
        "color_language": str(data.get("color_language") or "restrained navy / gold / ivory"),
        "reading_order": str(data.get("reading_order") or "headline → price → unit/%35 as one group → CTA"),
        "element_relationships": str(data.get("element_relationships") or ""),
        "regions": {
            "spire": _clamp_box(regions.get("spire") or data.get("spire")),
            "architecture": _clamp_box(regions.get("architecture") or data.get("architecture")),
            "headline": _clamp_box(regions.get("headline") or data.get("headline")),
            "commercial": _clamp_box(regions.get("commercial") or data.get("commercial")),
            "cta": _clamp_box(regions.get("cta") or data.get("cta")),
            "logo": _clamp_box(regions.get("logo") or data.get("logo")),
        },
        "safe_regions": [b for b in safe if b],
        "forbidden_regions": [b for b in forbidden if b],
        "mode": str(data.get("mode") or "vision"),
        "created_before_graphic_generation": True,
    }


def plan_to_generation_brief(plan: dict[str, Any], facts: dict[str, str]) -> str:
    p = normalize_composition_plan(plan)
    r = p["regions"]
    return "\n".join(
        [
            f"CONCEPT: {p['concept']}",
            f"VISUAL STORY: {p['visual_story']}",
            f"FOCAL POINT: {p['focal_point']}",
            f"PROTECTED ARCHITECTURE: {p['protected_architecture']}",
            f"SPIRE / TOWER KEEP TRANSPARENT: {_box_pct(r.get('spire'))}",
            f"PRIMARY BUILDING MASS KEEP MOSTLY TRANSPARENT: {_box_pct(r.get('architecture'))}",
            f"HEADLINE STRATEGY: {p['headline_strategy']} Zone: {_box_pct(r.get('headline'))}",
            f"COMMERCIAL SYSTEM (one group, not five objects): {p['commercial_information_strategy']} Zone: {_box_pct(r.get('commercial'))}",
            f"CTA STRATEGY: {p['cta_strategy']} Zone: {_box_pct(r.get('cta'))}",
            f"LOGO STRATEGY (leave empty for a real SVG; do not draw a logo): {p['logo_strategy']} Zone: {_box_pct(r.get('logo'))}",
            f"TYPOGRAPHY: {p['typography_strategy']}",
            f"CONTRAST / DEPTH / NEGATIVE SPACE: {p['contrast_strategy']} / {p['depth_strategy']} / {p['negative_space_strategy']}",
            f"GRAPHIC LANGUAGE: {p['graphic_language']}",
            f"COLOR: {p['color_language']}",
            f"READING ORDER: {p['reading_order']}",
            f"ELEMENT RELATIONSHIPS: {p['element_relationships']}",
            f"HIERARCHY: 1 {facts['headline']}  2 {facts['list_price']}  3 {facts['unit']} {facts['unit_label']} + {facts['discount']} {facts['discount_label']}  4 {facts['cta']}",
        ]
    )


def graphic_design_prompt(
    facts: dict[str, str],
    plan: dict[str, Any],
    *,
    chroma: bool,
    critique_feedback: str = "",
) -> str:
    key = (
        "Fill every pixel that is NOT campaign graphics with solid MAGENTA #FF00FF. Magenta means empty."
        if chroma
        else "Fully transparent PNG background. Empty pixels alpha=0. The real photograph shows through."
    )
    return "\n".join(
        [
            "Design a 4:5 GRAPHIC DESIGN LAYER for a premium real-estate campaign.",
            "You are the advertising designer. You are NOT a photographer. You are NOT an architect.",
            "Do not draw buildings, façades, windows, roofs, towers, spires, streets, trees, cars, or sky-as-photo.",
            "Do not draw a project logo. Leave the planned logo zone empty.",
            key,
            "The real approved project photograph already exists underneath. Design WITH its composition.",
            "The result must feel like one coherent premium advertisement, not text pasted on a photo.",
            "Allowed: campaign typography, local tonal fields, controlled gradients, subtle masks, thin editorial rules,",
            "restrained geometric framing, typography/image overlap only where justified, local contrast, gold accents.",
            "Forbidden: giant opaque panels, dashboard cards, KPI tiles, badges, medals, ribbons, sweeping gold curves,",
            "enormous price covering the building, tiny unreadable supporting copy, disconnected floating objects.",
            "Do NOT reuse a right-side type stack, a bottom fact strip of three columns, or a giant centered headline on a spire.",
            "Commercial facts must read as ONE designed system with hierarchy — not five unrelated labels.",
            "Typography uses proportion and breathing room. Do not compensate with enormous type.",
            "Paint ONLY these exact strings, Turkish glyphs exact (İ, Ş):",
            f"  {facts['headline']}",
            f"  {facts['unit']} {facts['unit_label']}",
            f"  {facts['list_price']}",
            f"  {facts['discount']} {facts['discount_label']}",
            f"  {facts['cta']}",
            "No 438.750. No extra claims. No duplicated words. Prefer exact CTA with no extra arrow.",
            "CREATIVE COMPOSITION PLAN FOR THIS EXACT 4:5 PHOTOGRAPH:",
            plan_to_generation_brief(plan, facts),
            critique_feedback.strip(),
        ]
    ).strip()


def request_composition_plan(
    foundation: Image.Image,
    facts: dict[str, str],
    *,
    critique_feedback: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Stage A — vision art director sees the exact 4:5 foundation. Not a compositor layout."""
    api_key = openai_api_key()
    if not api_key:
        return normalize_composition_plan({"mode": "unavailable", "concept": "no_api_key"}), 0
    jpeg = io.BytesIO()
    foundation.convert("RGB").save(jpeg, format="JPEG", quality=90)
    b64 = base64.b64encode(jpeg.getvalue()).decode("ascii")
    retry = ""
    if critique_feedback:
        retry = (
            "\nPREVIOUS COMPOSITION WAS REJECTED. Invent a NEW composition concept. "
            "Do not nudge coordinates. Do not repeat a bottom strip, right stack, or spire-colliding headline.\n"
            f"{critique_feedback}\n"
        )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the creative director for a luxury real-estate 4:5 campaign. "
                    "The photograph is immutable project architecture. You do not redraw it. "
                    "Think like an advertising art director, not a layout engine hunting empty rectangles. "
                    "Ask where typography can interact with THIS photograph elegantly. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is the EXACT final 1088×1360 crop of the approved project photograph.\n"
                            "Identify the architectural focal point, spire/tower if any, skyline, sky, busy vs quiet areas, "
                            "high/low contrast, natural reading path, and where a headline, one commercial-information system, "
                            "CTA, and real-logo reservation can live without damaging the hero architecture.\n"
                            f"Required copy: {facts['headline']} / {facts['unit']} {facts['unit_label']} / "
                            f"{facts['list_price']} / {facts['discount']} {facts['discount_label']} / {facts['cta']}.\n"
                            "Hierarchy: 1 headline  2 price  3 unit + %35 as one system  4 CTA. "
                            "Do not force cards, a right panel, a bottom panel, or badges.\n"
                            f"{retry}"
                            "JSON CreativeCompositionPlanV1: {\n"
                            '  "concept": str, "visual_story": str, "focal_point": str, "protected_architecture": str,\n'
                            '  "headline_strategy": str, "commercial_information_strategy": str, "cta_strategy": str,\n'
                            '  "logo_strategy": str, "typography_strategy": str, "contrast_strategy": str,\n'
                            '  "negative_space_strategy": str, "depth_strategy": str, "graphic_language": str,\n'
                            '  "color_language": str, "reading_order": str, "element_relationships": str,\n'
                            '  "regions": {"spire": box, "architecture": box, "headline": box, "commercial": box, "cta": box, "logo": box},\n'
                            '  "safe_regions": [box], "forbidden_regions": [box]\n'
                            "} Boxes are normalized 0-1 {x,y,w,h}."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ],
            },
        ],
    }
    settings = get_settings()
    url = f"{resolve_base_url(settings).rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
        text = ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        if not isinstance(parsed, dict):
            parsed = {}
        plan = normalize_composition_plan(parsed)
        plan["mode"] = "vision"
        return plan, 1
    except Exception:
        logger.info("phase5.1e composition plan unavailable", exc_info=True)
        return normalize_composition_plan({"mode": "unavailable"}), 0


def critique_rejected(critique: dict[str, Any]) -> bool:
    if critique.get("pass") is True:
        return False
    if critique.get("pass") is False:
        return True
    return any(bool(critique.get(k)) for k in CRITIQUE_FAIL_KEYS) or bool(critique.get("missing_required"))


def request_design_critique(
    *,
    final: Image.Image,
    overlay: Image.Image,
    foundation: Image.Image,
    facts: dict[str, str],
) -> tuple[dict[str, Any], int]:
    """Vision design gate. Does not move coordinates. Rejects R1/R2 failure modes."""
    api_key = openai_api_key()
    if not api_key:
        return {"pass": None, "mode": "unavailable", "failures": []}, 0

    def _jpeg(im: Image.Image) -> str:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=88)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    layer = Image.new("RGB", overlay.size, (28, 30, 36))
    layer = Image.alpha_composite(layer.convert("RGBA"), overlay.convert("RGBA")).convert("RGB")
    required = [
        facts["headline"],
        f"{facts['unit']} {facts['unit_label']}",
        facts["list_price"],
        facts["discount"],
        facts["discount_label"],
        facts["cta"],
    ]
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a ruthless creative director reviewing a luxury real-estate advertisement. "
                    "Image 1 is the final composite. Image 2 is the graphic layer only. Image 3 is the immutable photograph. "
                    "Judge generated architecture from image 2 only. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Required exact facts:\n"
                            + "\n".join(f"- {row}" for row in required)
                            + "\nReject if ANY: headline intersects spire/tower; type covers major architecture; "
                            "price dominates the whole ad; commercial facts disconnected; CTA floats; logo looks pasted; "
                            "text unreadable; supporting copy too small; dashboard cards; giant badge/medallion; ribbons; "
                            "excessive gold curves; giant opaque panel; template look; text-on-photo; architecture not the hero; "
                            "malformed Turkish; generated building in the graphic layer; 438.750.\n"
                            "JSON: {\n"
                            '  "visible_strings": [str], "missing_required": [str],\n'
                            '  "headline_intersects_spire": bool, "typography_covers_major_architecture": bool,\n'
                            '  "price_dominates": bool, "commercial_disconnected": bool, "cta_floats": bool,\n'
                            '  "logo_pasted": bool, "text_unreadable": bool, "supporting_too_small": bool,\n'
                            '  "dashboard_cards": bool, "giant_badge": bool, "ribbons": bool,\n'
                            '  "excessive_gold_curves": bool, "giant_opaque_panel": bool, "template_composition": bool,\n'
                            '  "text_on_photo": bool, "architecture_not_hero": bool, "malformed_typography": bool,\n'
                            '  "contains_generated_architecture": bool, "wrong_price": bool,\n'
                            '  "notes": str, "composition_advice": str\n'
                            "}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg(final)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg(layer)}", "detail": "high"}},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{_jpeg(foundation)}", "detail": "low"},
                    },
                ],
            },
        ],
    }
    settings = get_settings()
    url = f"{resolve_base_url(settings).rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
        text = ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        if not isinstance(parsed, dict):
            parsed = {}
        missing = [str(x) for x in (parsed.get("missing_required") or []) if str(x).strip()]
        parsed["missing_required"] = missing
        failed = [k for k in CRITIQUE_FAIL_KEYS if parsed.get(k)]
        if missing:
            failed.append("missing_required")
        if parsed.get("wrong_price"):
            failed.append("wrong_price")
        parsed["failures"] = failed
        parsed["pass"] = not failed
        parsed["mode"] = "vision"
        return parsed, 1
    except Exception:
        logger.info("phase5.1e design critique unavailable", exc_info=True)
        return {"pass": None, "mode": "unavailable", "failures": [], "notes": "critique_error"}, 0


def request_graphic_layer(
    *,
    facts: dict[str, str],
    plan: dict[str, Any],
    availability,
    critique_feedback: str = "",
) -> tuple[bytes, str, int]:
    """gpt-image-2 generations only. Never send the project photograph to images/edits."""
    api_key = openai_api_key()
    calls = 0
    try:
        remote = generate_image(
            api_key=api_key,
            model=availability.model,
            prompt=graphic_design_prompt(facts, plan, chroma=False, critique_feedback=critique_feedback),
            size=OVERLAY_SIZE,
            quality=availability.quality,
            base_url=availability.base_url,
            variant="phase5-1e-graphic-transparent",
            background="transparent",
            output_format="png",
        )
        calls += 1
        return decode_remote_image(remote), "generations_transparent_png", calls
    except GptImageProviderError:
        calls += 1
        logger.info("phase5.1e transparent graphic unsupported; chroma fallback")
    remote = generate_image(
        api_key=api_key,
        model=availability.model,
        prompt=graphic_design_prompt(facts, plan, chroma=True, critique_feedback=critique_feedback),
        size=OVERLAY_SIZE,
        quality=availability.quality,
        base_url=availability.base_url,
        variant="phase5-1e-graphic-chroma",
    )
    calls += 1
    return decode_remote_image(remote), "generations_magenta_chroma", calls


def logo_box_from_plan(plan: dict[str, Any], canvas: tuple[int, int] = CANVAS_4X5) -> tuple[int, int, int, int]:
    px = box_to_px(normalize_composition_plan(plan)["regions"].get("logo"), canvas)
    if px is None:
        w, h = canvas
        return (int(w * 0.06), int(h * 0.05), int(w * 0.28), int(h * 0.13))
    return px


def render_region_map(
    foundation: Image.Image,
    plan: dict[str, Any],
    *,
    title: str,
    include_safe: bool = True,
) -> Image.Image:
    im = foundation.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    font = _font(16)
    p = normalize_composition_plan(plan)
    r = p["regions"]

    def _mark(box: dict[str, float] | None, color: tuple[int, int, int], label: str, width: int = 3) -> None:
        px = box_to_px(box, im.size)
        if px is None:
            return
        draw.rectangle(px, outline=color, width=width)
        draw.text((px[0] + 6, max(4, px[1] + 4)), label, fill=color, font=font)

    _mark(r.get("spire"), (220, 60, 60), "PROTECTED SPIRE", 4)
    _mark(r.get("architecture"), (230, 140, 40), "PROTECTED ARCHITECTURE", 3)
    if include_safe:
        for i, box in enumerate(p.get("safe_regions") or []):
            _mark(box, (80, 190, 220), f"QUIET {i + 1}")
        for i, box in enumerate(p.get("forbidden_regions") or []):
            _mark(box, (180, 60, 90), f"FORBIDDEN {i + 1}")
    _mark(r.get("headline"), (255, 255, 255), "HEADLINE")
    _mark(r.get("commercial"), (201, 168, 92), "COMMERCIAL SYSTEM")
    _mark(r.get("cta"), (90, 200, 130), "CTA")
    _mark(r.get("logo"), (200, 120, 255), "LOGO")
    bar = 40
    out = Image.new("RGB", (im.width, im.height + bar), (12, 14, 20))
    out.paste(im, (0, bar))
    ImageDraw.Draw(out).text((12, 10), title, fill=(201, 168, 92), font=font)
    return out


def render_hierarchy_map(final: Image.Image, plan: dict[str, Any]) -> Image.Image:
    im = final.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    font = _font(18)
    r = normalize_composition_plan(plan)["regions"]
    labels = [
        (r.get("headline"), "1 HEADLINE", (255, 255, 255)),
        (r.get("commercial"), "2-3 COMMERCIAL SYSTEM", (201, 168, 92)),
        (r.get("cta"), "4 CTA", (90, 200, 130)),
        (r.get("logo"), "LOGO", (200, 120, 255)),
    ]
    for box, label, color in labels:
        px = box_to_px(box, im.size)
        if px is None:
            continue
        draw.rectangle(px, outline=color, width=3)
        draw.text((px[0] + 8, px[1] + 8), label, fill=color, font=font)
    bar = 40
    out = Image.new("RGB", (im.width, im.height + bar), (12, 14, 20))
    out.paste(im, (0, bar))
    ImageDraw.Draw(out).text((12, 10), "design hierarchy map — debug only", fill=(201, 168, 92), font=font)
    return out


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


def generate_creative_master_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    source_asset_id: str | None = None,
    logo_asset_id: str | None = None,
    facts: dict[str, str] | None = None,
    source_filename: str | None = None,
) -> dict[str, Any]:
    """One 4:5 master candidate. Does not overwrite 5.0 / 5.1 / 5.1B / 5.1C / 5.1D / R1 / R2 / production cover.

    Any project may pass its approved Media Library source photo and logo.
    """
    hero_id = str(source_asset_id or LOCKED_HERO_ASSET_ID)
    logo_id = str(logo_asset_id or LOCKED_LOGO_ASSET_ID)
    campaign_facts = dict(facts or REQUIRED_FACTS)
    filename = source_filename or (HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None)

    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved_session = blob.get("current_session_id")
    preserved_family = blob.get("current_format_family_id")
    preserved_lock = list(blob.get("architecture_lock_tests") or [])
    preserved_photo = list(blob.get("photo_foundation_tests") or [])
    preserved_design = list(blob.get("creative_design_tests") or [])
    preserved_overlay = list(blob.get("creative_overlay_tests") or [])
    preserved_masters = {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()}
    preserved_sessions = dict(blob.get("sessions") or {})
    before["phase5_current_session_id"] = preserved_session
    before["phase5_current_format_family_id"] = preserved_family
    before["architecture_lock_tests_count"] = len(preserved_lock)
    before["photo_foundation_tests_count"] = len(preserved_photo)
    before["creative_design_tests_count"] = len(preserved_design)
    before["creative_overlay_tests_count"] = len(preserved_overlay)

    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    centering = _centering_from_mass(source)
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=centering)
    graded = apply_photographic_grade(
        crop, {"warmth": 0.12, "contrast": 1.08, "brightness": 0.98, "vignette": 0.10}
    )
    availability = provider_availability()
    provider_calls = 0
    attempts: list[dict[str, Any]] = []
    critique_feedback = ""
    chosen: dict[str, Any] | None = None

    for attempt in range(MAX_DESIGN_RETRIES + 1):
        plan, plan_calls = request_composition_plan(
            graded, campaign_facts, critique_feedback=critique_feedback or None
        )
        provider_calls += plan_calls
        raw, method, g_calls = request_graphic_layer(
            facts=campaign_facts,
            plan=plan,
            availability=availability,
            critique_feedback=critique_feedback,
        )
        provider_calls += g_calls
        overlay = prepare_overlay(raw, method=method)
        composed = composite_overlay(graded, overlay)
        logo = ResolvedSourceImage(
            asset_id=UUID(logo_id),
            filename="project-logo.svg",
            content_type="image/svg+xml",
            folder_category=None,
            tags=[],
            image_bytes=logo_bytes,
            role="project_logo",
        )
        with_logo, logo_meta = paste_logo(composed, logo, logo_box_from_plan(plan, overlay.size))
        final = with_logo.convert("RGB")
        critique, c_calls = request_design_critique(
            final=final, overlay=overlay, foundation=graded, facts=campaign_facts
        )
        provider_calls += c_calls
        pack = {
            "plan": plan,
            "overlay": overlay,
            "raw": raw,
            "method": method,
            "final": final,
            "logo_meta": logo_meta,
            "critique": critique,
            "attempt": attempt,
        }
        attempts.append(pack)
        chosen = pack
        if not critique_rejected(critique):
            break
        critique_feedback = (
            f"Critique failures: {', '.join(critique.get('failures') or [])}. "
            f"{critique.get('composition_advice') or critique.get('notes') or ''}"
        )

    assert chosen is not None
    attempts_run = len(attempts)
    if critique_rejected(chosen["critique"]):

        def _score(p: dict[str, Any]) -> tuple[int, int]:
            # Prefer fewer failures; if tied, keep the later composition (it saw the critique).
            return (len(list((p.get("critique") or {}).get("failures") or [])), -int(p.get("attempt") or 0))

        chosen = min(attempts, key=_score)

    final = chosen["final"]
    overlay = chosen["overlay"]
    plan = chosen["plan"]
    critique = chosen["critique"]
    provenance = architecture_provenance_qa(source=source, foundation=crop, final=final, transform=transform)
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(final),
        content_type="image/png",
        campaign_mode="project-creative-master",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.1E AI creative master on immutable project photo 4:5",
    )
    record = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_51E,
        "created_at": _now(),
        "source_asset_id": hero_id,
        "source_filename": filename,
        "source_pixel_provenance": "immutable_project_photo_uniform_cover_crop_then_photographic_grade",
        "architecture_generation_used": False,
        "photo_foundation_method": "phase5_1b_locked_cover_fit_grade",
        "creative_director_model": VISION_MODEL,
        "creative_composition_plan_id": plan.get("plan_id"),
        "ai_creative_model": availability.model,
        "graphic_generation_method": chosen["method"],
        "ai_creative_method": "gpt_image_generations_overlay_not_edits",
        "os_compositor_primary_designer": False,
        "plan_executed_by_os": False,
        "logo_asset_id": logo_id,
        "visible_commercial_content": [
            campaign_facts["headline"],
            f"{campaign_facts['unit']} {campaign_facts['unit_label']}",
            campaign_facts["list_price"],
            f"{campaign_facts['discount']} {campaign_facts['discount_label']}",
            campaign_facts["cta"],
        ],
        "final_asset_id": str(asset.id),
        "final_asset_url": asset_url(asset.id),
        "final_size": list(final.size),
        "architecture_modified": False,
        "ai_generated_building_used": False,
        "gpt_image_edit_calls": 0,
        "design_retry_count": max(0, attempts_run - 1),
        "provider_call_count": provider_calls,
        "overlay_transparency_ratio": round(overlay_transparency_ratio(overlay), 4),
        "video_started": False,
        "publishing_started": False,
        "logo_meta": chosen["logo_meta"],
        "transform": transform,
        "provenance_qa": provenance,
        "creative_composition_plan": plan,
        "design_critique": critique,
        "size_requested": OVERLAY_SIZE,
        "aspect_lock": ASPECT_TO_SIZE.get("4:5"),
        "reusable_contract": {
            "rule": "REAL PROJECT IMAGE + AI CREATIVE DESIGN = FINAL CREATIVE",
            "source_asset_parameter": True,
            "logo_asset_parameter": True,
            "architecture_from_source_photo_only": True,
        },
    }
    stored = dict(record)
    tests = [
        t
        for t in list(blob.get("creative_master_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_51E)
    ]
    tests.append(stored)
    blob["creative_master_tests"] = tests
    blob["current_session_id"] = preserved_session
    blob["current_format_family_id"] = preserved_family
    blob["architecture_lock_tests"] = preserved_lock
    blob["photo_foundation_tests"] = preserved_photo
    blob["creative_design_tests"] = preserved_design
    blob["creative_overlay_tests"] = preserved_overlay
    blob["approved_masters"] = preserved_masters
    blob["sessions"] = preserved_sessions
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
    _production_guard(before, after)
    if blob.get("current_session_id") != preserved_session:
        raise RuntimeError("Phase 5.1E refused to change current_session_id")
    if blob.get("current_format_family_id") != preserved_family:
        raise RuntimeError("Phase 5.1E refused to change current_format_family_id")
    if list(blob.get("creative_overlay_tests") or []) != preserved_overlay:
        raise RuntimeError("Phase 5.1E refused to change R1/R2 overlay history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.1E refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "overlay": overlay,
        "final": final,
        "analysis_map": render_region_map(graded, plan, title="photo analysis map — debug only"),
        "composition_map": render_region_map(
            graded, plan, title="creative composition plan — debug only, not the ad", include_safe=True
        ),
        "hierarchy_map": render_hierarchy_map(final, plan),
        "overlay_preview": _checkerboard(overlay),
    }
    _ = language
    return record
