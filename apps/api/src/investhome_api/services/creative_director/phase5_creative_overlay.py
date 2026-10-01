"""Phase 5.1D — AI-generated creative overlay on immutable Day_004.

Architecture pixels come only from the locked 5.1B photo foundation.
gpt-image-2 generates the advertising treatment as a separate overlay.
The OS compositor is not the designer. It only composites overlay + real logo.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
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

WORKFLOW_ID_51D = "phase5_1d_ai_creative_overlay"
WORKFLOW_ID_51D_R1 = "phase5_1d_r1_premium_editorial"
WORKFLOW_ID_51D_R2 = "phase5_1d_r2_photo_aware"
PARENT_51D_ASSET_ID = "cabcec54-9b9d-4512-a4b1-fd70dee99350"
PARENT_R1_ASSET_ID = "d1407aa8-aeda-480c-af52-2c0a65cb06c4"
DIRECTION_51D = "phase5_1d"
DIRECTION_R1 = "r1_premium_editorial"
DIRECTION_R2 = "r2_photo_aware"
CHROMA = (255, 0, 255)
OVERLAY_SIZE = "1088x1360"


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _facts() -> dict[str, str]:
    return dict(REQUIRED_FACTS)


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
        return "unspecified"
    x0, y0 = box["x"] * 100, box["y"] * 100
    x1, y1 = (box["x"] + box["w"]) * 100, (box["y"] + box["h"]) * 100
    return f"x {x0:.0f}–{x1:.0f}%, y {y0:.0f}–{y1:.0f}% of the 1088×1360 canvas"


def box_to_px(box: dict[str, float] | None, canvas: tuple[int, int] = CANVAS_4X5) -> tuple[int, int, int, int] | None:
    if not box:
        return None
    cw, ch = canvas
    x0 = int(round(box["x"] * cw))
    y0 = int(round(box["y"] * ch))
    x1 = int(round((box["x"] + box["w"]) * cw))
    y1 = int(round((box["y"] + box["h"]) * ch))
    return (max(0, x0), max(0, y0), min(cw, x1), min(ch, y1))


def normalize_overlay_plan(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(raw or {})
    protected = dict(data.get("protected") or {})
    spire = _clamp_box(protected.get("spire") or data.get("spire"))
    architecture = _clamp_box(protected.get("architecture") or data.get("architecture"))
    negatives = []
    for item in data.get("negative_space") or []:
        box = _clamp_box(item)
        if box:
            box["name"] = str((item or {}).get("name") or "quiet")
            negatives.append(box)
    plan = {
        "photograph_reading": str(data.get("photograph_reading") or ""),
        "focal_point": str(data.get("focal_point") or ""),
        "light": str(data.get("light") or ""),
        "protected": {"spire": spire, "architecture": architecture},
        "negative_space": negatives,
        "headline": _clamp_box(data.get("headline")),
        "commercial": _clamp_box(data.get("commercial")),
        "cta": _clamp_box(data.get("cta")),
        "logo": _clamp_box(data.get("logo")),
        "headline_strategy": str(data.get("headline_strategy") or (data.get("headline") or {}).get("strategy") or ""),
        "commercial_strategy": str(data.get("commercial_strategy") or (data.get("commercial") or {}).get("strategy") or ""),
        "cta_strategy": str(data.get("cta_strategy") or (data.get("cta") or {}).get("strategy") or ""),
        "logo_strategy": str(data.get("logo_strategy") or (data.get("logo") or {}).get("strategy") or ""),
        "typography_character": str(data.get("typography_character") or "restrained editorial serif"),
        "hierarchy": str(data.get("hierarchy") or "price primary; %35 secondary typographic; 2+1 supporting; one commercial system"),
        "graphic_accents": str(data.get("graphic_accents") or "minimal thin rules only if useful"),
        "transparent_must_remain": str(data.get("transparent_must_remain") or "spire, primary façade, roof, important architecture"),
        "mode": str(data.get("mode") or "vision"),
    }
    return plan


def plan_to_spatial_brief(plan: dict[str, Any] | None) -> str:
    """Language for gpt-image-2. Not OS compositor drawing instructions."""
    p = normalize_overlay_plan(plan)
    prot = p["protected"]
    quiet = "; ".join(f"{n.get('name')} {_box_pct(n)}" for n in p["negative_space"]) or "use actual sky/ground quiet areas"
    return "\n".join(
        [
            f"PHOTOGRAPH READING: {p['photograph_reading'] or 'exact 4:5 Day_004 crop'}",
            f"FOCAL POINT: {p['focal_point'] or 'gothic stone spire'}",
            f"LIGHT: {p['light'] or 'daylight'}",
            f"PROTECTED SPIRE (keep fully transparent): {_box_pct(prot.get('spire'))}",
            f"PROTECTED ARCHITECTURE (keep mostly transparent): {_box_pct(prot.get('architecture'))}",
            f"USABLE NEGATIVE SPACE: {quiet}",
            f"HEADLINE ZONE for ALIRKEN KAZAN: {_box_pct(p.get('headline'))}. {p['headline_strategy']}",
            f"COMMERCIAL SYSTEM ZONE (price + %35 + 2+1 together): {_box_pct(p.get('commercial'))}. {p['commercial_strategy']}",
            f"CTA ZONE for PROJEYİ KEŞFET: {_box_pct(p.get('cta'))}. {p['cta_strategy']}",
            f"REAL LOGO ZONE — leave empty/transparent, do not draw a logo: {_box_pct(p.get('logo'))}. {p['logo_strategy']}",
            f"TYPOGRAPHY: {p['typography_character']}",
            f"HIERARCHY: {p['hierarchy']}",
            f"ACCENTS: {p['graphic_accents']}",
            f"MUST STAY TRANSPARENT: {p['transparent_must_remain']}",
        ]
    )


def request_photo_aware_plan(foundation: Image.Image, facts: dict[str, str]) -> tuple[dict[str, Any], int]:
    """Stage A: gpt-4o sees the EXACT 4:5 Day_004 crop. Plan is awareness for gpt-image-2, not a compositor layout."""
    api_key = openai_api_key()
    if not api_key:
        return normalize_overlay_plan({"mode": "unavailable", "photograph_reading": "no_api_key"}), 0
    jpeg = io.BytesIO()
    foundation.convert("RGB").save(jpeg, format="JPEG", quality=90)
    b64 = base64.b64encode(jpeg.getvalue()).decode("ascii")
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the creative director for a luxury Washington DC real-estate 4:5 campaign. "
                    "This photograph is immutable. You do not redraw architecture. "
                    "You produce a CreativeOverlayPlan so an image model can paint a TRANSPARENT overlay "
                    "that responds to THIS exact crop. JSON only. Boxes are normalized 0-1 {x,y,w,h}. "
                    "Do not invent a template. Do not ask a compositor to set type."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is the EXACT final 1088×1360 Day_004 crop that will sit under the overlay.\n"
                            "Read the real spire, building mass, sky, trees, street, negative space, light, and balance.\n"
                            "Required copy (facts cannot change): "
                            f"{facts['headline']} / {facts['unit']} {facts['unit_label']} / {facts['list_price']} / "
                            f"{facts['discount']} {facts['discount_label']} / {facts['cta']}.\n"
                            "Headline must not cross the spire. Logo must not touch the spire. "
                            "Price must not sit on the main façade. %35 must not cover the main building. "
                            "Commercial facts must be ONE system, not scattered objects. "
                            "Do not repeat a right-side overload, giant price, floating %35, or decorative vertical gold rules.\n"
                            "JSON: {\n"
                            '  "photograph_reading": str, "focal_point": str, "light": str,\n'
                            '  "protected": {"spire": box, "architecture": box},\n'
                            '  "negative_space": [{"name": str, "x":n,"y":n,"w":n,"h":n}],\n'
                            '  "headline": box, "headline_strategy": str,\n'
                            '  "commercial": box, "commercial_strategy": str,\n'
                            '  "cta": box, "cta_strategy": str,\n'
                            '  "logo": box, "logo_strategy": str,\n'
                            '  "typography_character": str, "hierarchy": str, "graphic_accents": str,\n'
                            '  "transparent_must_remain": str\n'
                            "}"
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
        plan = normalize_overlay_plan(parsed)
        plan["mode"] = "vision"
        return plan, 1
    except Exception:
        logger.info("phase5.1d-r2 photo-aware plan unavailable", exc_info=True)
        return normalize_overlay_plan({"mode": "unavailable"}), 0


def overlay_prompt(
    facts: dict[str, str],
    *,
    chroma: bool,
    extra: str = "",
    direction: str = DIRECTION_51D,
    plan: dict[str, Any] | None = None,
) -> str:
    key = (
        "Fill every pixel that is NOT campaign graphics with solid MAGENTA #FF00FF. "
        "Magenta means empty. The real photograph will show through magenta. "
        "Do not use magenta inside letters."
        if chroma
        else "Use a fully transparent background. Empty pixels must be alpha=0 PNG transparency."
    )
    extra_line = extra.strip()
    if direction == DIRECTION_R2:
        art = [
            "Create a 4:5 CREATIVE OVERLAY only for a premium Washington DC real-estate campaign.",
            "Art direction: architectural editorial. High-end architecture magazine. Institutional luxury.",
            "This overlay must be PHOTO-AWARE of the exact 4:5 Day_004 crop described below.",
            "This is NOT a photograph of a building. Do NOT draw architecture, silhouettes, façades, windows, towers, or a spire.",
            "The BUILDING is the hero. Support it. Do not cover it. Do not fill every empty area.",
            key,
            "Do NOT repeat the failed R1: no enormous right-side stack, no giant price over architecture, ",
            "no disconnected %35, no floating LANSMAN AVANTAJI, no decorative vertical gold rules, no oversized headline.",
            "Commercial information must read as ONE designed system. Typography-led. Restrained navy/gold/ivory.",
            "Forbidden: ribbons, medals, giant badges, sweeping curves, stars, frames, dashboard cards, KPI blocks, extra campaign copy.",
            f"{facts['headline']} editorial, important but not enormous, working WITH the spire, never crossing it.",
            "Hierarchy: 675.000 USD primary and readable; %35 LANSMAN AVANTAJI secondary typographic not a medallion; 2+1 DAİRE supporting.",
            f"CTA {facts['cta']}: clear, premium, restrained. No mandatory arrow. No oversized button. Exact glyphs only.",
            "Do NOT draw a logo, logo box, empty frame, or decorative plate. Leave the planned logo zone empty for a real SVG.",
            "PHOTO-AWARE SPATIAL BRIEF FOR THIS EXACT CROP:",
            plan_to_spatial_brief(plan),
        ]
    elif direction == DIRECTION_R1:
        art = [
            "Create a 4:5 CREATIVE OVERLAY only for a premium Washington DC real-estate campaign.",
            "Art direction: architectural editorial. High-end architecture magazine. Institutional luxury.",
            "NOT a wedding invitation, jewelry ad, casino, certificate, ornamental brochure, or discount poster.",
            "This is NOT a photograph of a building. Do NOT draw architecture, silhouettes, façades, windows, towers, or a spire.",
            "The BUILDING is the hero. Design must support the photograph, not cover it.",
            key,
            "Implied photograph: a tall gothic stone spire rises through the LEFT-CENTER of the 4:5 frame to the top edge.",
            "The spire column is protected visual space. No headline, price, CTA, logo reservation, rule, or decoration may cross it.",
            "Use actual negative space. Generous empty canvas. Minimal graphic intervention.",
            "Typography-led. Strong hierarchy. Restrained navy / gold / ivory. Thin rules allowed. Subtle gradient/tonal support allowed.",
            "Forbidden decoration: ribbons, sweeping gold curves, giant seals, medals, ornamental frames, decorative stars, excessive borders, large opaque panels, KPI cards.",
            f"{facts['headline']} is the primary campaign message: large, confident, editorial. Two lines allowed. Breathing room. Not through the spire.",
            "Hierarchy (do not copy a template): price 675.000 USD primary and immediately readable; %35 LANSMAN AVANTAJI strong but typographic, NOT a giant badge/medallion; 2+1 DAİRE supporting.",
            f"CTA {facts['cta']}: elegant editorial or restrained outline. Not a giant button. No arrow unless truly necessary. Exact glyphs only.",
            "Do NOT draw a logo, logo box, empty frame, or decorative plate. Leave the FAR-LEFT TOP corner empty and transparent for a real SVG logo.",
            "Logo reservation must not touch the spire and must not collide with the headline.",
        ]
    else:
        art = [
            "Create a luxury real-estate Instagram 4:5 CREATIVE OVERLAY only.",
            "This is NOT a photograph of a building. Do NOT draw architecture.",
            "Forbidden: buildings, spires, towers, façades, windows, roofs, streets, cars, trees, skies-as-photo, any Temple.",
            "Allowed: typography, editorial graphics, gold rules, light fields, shadows, luxury ornaments, CTA treatment.",
            key,
            "The real project photo sits underneath. A tall stone gothic spire occupies the CENTER of the 4:5 frame.",
            "Keep the central vertical third mostly empty so the real building remains the hero.",
            "Place campaign design in negative space — typically left sky and lower-left — responding to that composition.",
            "Do not cover the spire with large display type.",
            "Do NOT draw a logo. Leave a clear empty plate in the upper type cluster for a real SVG logo to be composited later.",
            "Quality bar: premium editorial luxury advertising. Integrated campaign graphics, not HTML text on a rectangle.",
        ]
    return "\n".join(
        [
            *art,
            "Paint ONLY these exact strings, glyph-accurate, Turkish characters exact (İ, Ş):",
            f"  {facts['headline']}",
            f"  {facts['unit']} {facts['unit_label']}",
            f"  {facts['list_price']}",
            f"  {facts['discount']} {facts['discount_label']}",
            f"  {facts['cta']}",
            "No 438.750. No ROI. No extra claims. No duplicated words. No extra campaign copy.",
            extra_line,
        ]
    ).strip()


def has_useful_alpha(image: Image.Image) -> bool:
    if image.mode != "RGBA":
        return False
    alpha = image.getchannel("A").resize((64, 80), Image.Resampling.BOX)
    pix = list(alpha.getdata())
    clear = sum(1 for p in pix if p < 40)
    return clear / max(len(pix), 1) >= 0.22


def magenta_to_alpha(image: Image.Image, *, tolerance: int = 42) -> Image.Image:
    """Turn chroma-key magenta into transparency. Generic compositor tool, not a layout."""
    rgba = image.convert("RGBA")
    r, g, b, _a = rgba.split()
    inv_g = ImageChops.invert(g)
    score = ImageChops.multiply(ImageChops.multiply(r, inv_g), b)
    threshold = max(8, min(250, 255 - tolerance))
    mask = score.point(lambda p: 0 if p >= threshold else 255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    rgba.putalpha(mask)
    return rgba


def overlay_transparency_ratio(overlay: Image.Image) -> float:
    alpha = overlay.convert("RGBA").getchannel("A").resize((64, 80), Image.Resampling.BOX)
    pix = list(alpha.getdata())
    return sum(1 for p in pix if p < 40) / max(len(pix), 1)


def overlay_center_clear_ratio(overlay: Image.Image) -> float:
    """Share of the central vertical third that is empty so Day_004 remains the hero."""
    w, h = overlay.size
    crop = overlay.convert("RGBA").crop((int(w * 0.33), int(h * 0.10), int(w * 0.67), int(h * 0.90)))
    alpha = crop.getchannel("A").resize((24, 40), Image.Resampling.BOX)
    pix = list(alpha.getdata())
    return sum(1 for p in pix if p < 40) / max(len(pix), 1)


def composite_overlay(foundation: Image.Image, overlay: Image.Image) -> Image.Image:
    base = foundation.convert("RGBA")
    over = overlay.convert("RGBA")
    if over.size != base.size:
        over = over.resize(base.size, Image.Resampling.LANCZOS)
    return Image.alpha_composite(base, over)


def logo_box_from_overlay(overlay: Image.Image) -> tuple[int, int, int, int]:
    """Place the real SVG in the far-left sky reservation. Not a layout template for type."""
    w, h = overlay.size
    box_w, box_h = int(w * 0.20), int(h * 0.072)
    x0, y0 = 28, 26
    x1 = min(int(w * 0.34), x0 + box_w)
    y1 = y0 + box_h
    return (x0, y0, x1, y1)


def logo_box_from_plan(
    plan: dict[str, Any] | None,
    overlay: Image.Image,
) -> tuple[int, int, int, int]:
    """Insert the real SVG into the planned logo zone. Does not design type."""
    px = box_to_px((normalize_overlay_plan(plan) or {}).get("logo"), overlay.size)
    if px is None:
        return logo_box_from_overlay(overlay)
    x0, y0, x1, y1 = px
    if (x1 - x0) < 80 or (y1 - y0) < 36:
        return logo_box_from_overlay(overlay)
    return px


def render_photo_awareness_map(foundation: Image.Image, plan: dict[str, Any] | None) -> Image.Image:
    """DEBUG ONLY. Marks zones on the exact 4:5 crop. Must never become the advertisement."""
    im = foundation.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    p = normalize_overlay_plan(plan)
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font = None

    def _mark(box: dict[str, float] | None, color: tuple[int, int, int], label: str, width: int = 3) -> None:
        px = box_to_px(box, im.size)
        if px is None:
            return
        draw.rectangle(px, outline=color, width=width)
        draw.text((px[0] + 6, px[1] + 6), label, fill=color, font=font)

    _mark((p.get("protected") or {}).get("spire"), (220, 60, 60), "SPIRE PROTECTED", 4)
    _mark((p.get("protected") or {}).get("architecture"), (230, 140, 40), "ARCHITECTURE PROTECTED", 3)
    for item in p.get("negative_space") or []:
        _mark(item, (80, 190, 220), str(item.get("name") or "NEGATIVE"))
    _mark(p.get("headline"), (255, 255, 255), "HEADLINE")
    _mark(p.get("commercial"), (201, 168, 92), "COMMERCIAL")
    _mark(p.get("cta"), (90, 200, 130), "CTA")
    _mark(p.get("logo"), (200, 120, 255), "LOGO")
    return im


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


def verify_overlay_facts(
    image: Image.Image,
    facts: dict[str, str],
    *,
    overlay: Image.Image | None = None,
) -> tuple[dict[str, Any], int]:
    """gpt-4o reads campaign text from the composite. Architecture is judged from the overlay layer only."""
    api_key = openai_api_key()
    if not api_key:
        return {"pass": None, "mode": "unavailable", "reason": "no_api_key"}, 0
    jpeg = io.BytesIO()
    image.convert("RGB").save(jpeg, format="JPEG", quality=90)
    b64 = base64.b64encode(jpeg.getvalue()).decode("ascii")
    content: list[dict[str, Any]] = []
    required = [
        facts["headline"],
        f"{facts['unit']} {facts['unit_label']}",
        facts["list_price"],
        facts["discount"],
        facts["discount_label"],
        facts["cta"],
    ]
    overlay_note = ""
    if overlay is not None:
        layer = Image.new("RGB", overlay.size, (28, 30, 36))
        layer = Image.alpha_composite(layer.convert("RGBA"), overlay.convert("RGBA")).convert("RGB")
        ojpeg = io.BytesIO()
        layer.save(ojpeg, format="JPEG", quality=90)
        ob64 = base64.b64encode(ojpeg.getvalue()).decode("ascii")
        overlay_note = (
            "Image 1 is the final composite (real photograph + overlay). Read visible campaign text from image 1. "
            "Image 2 is the overlay layer only on a dark field. Judge contains_architecture from image 2 ONLY. "
            "The real building in image 1 must not count as generated architecture.\n"
        )
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ob64}", "detail": "high"}})
    else:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}})
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Proofread a luxury real-estate advertisement overlay. JSON only. Do not invent.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            overlay_note
                            + "Required exact visible facts:\n"
                            + "\n".join(f"- {row}" for row in required)
                            + "\nForbidden: 438.750, ROI, extra claims, extra campaign copy, arrows unless in required strings, duplicated words.\n"
                            "JSON: {\n"
                            '  "visible_strings": [str],\n'
                            '  "missing_required": [str],\n'
                            '  "wrong_price": bool,\n'
                            '  "contains_438750": bool,\n'
                            '  "contains_architecture": bool,\n'
                            '  "malformed_typography": bool,\n'
                            '  "has_ribbons_or_medallion": bool,\n'
                            '  "notes": str\n'
                            "}"
                        ),
                    },
                    *content,
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
        ok = not (
            missing
            or bool(parsed.get("wrong_price"))
            or bool(parsed.get("contains_438750"))
            or bool(parsed.get("contains_architecture"))
            or bool(parsed.get("malformed_typography"))
        )
        parsed["pass"] = ok
        parsed["mode"] = "vision"
        parsed["missing_required"] = missing
        return parsed, 1
    except Exception:
        logger.info("phase5.1d overlay fact check unavailable", exc_info=True)
        return {"pass": None, "mode": "unavailable", "reason": "vision_error"}, 0


def overlay_quality_ok(
    overlay: Image.Image,
    facts_check: dict[str, Any],
    *,
    direction: str = DIRECTION_51D,
) -> bool:
    if overlay_transparency_ratio(overlay) < 0.22:
        return False
    if overlay_center_clear_ratio(overlay) < 0.35:
        return False
    if facts_check.get("pass") is False:
        return False
    if direction in {DIRECTION_R1, DIRECTION_R2} and facts_check.get("has_ribbons_or_medallion"):
        return False
    return True


def request_overlay_bytes(
    *,
    facts: dict[str, str],
    availability,
    extra: str = "",
    force_chroma: bool = False,
    direction: str = DIRECTION_51D,
    plan: dict[str, Any] | None = None,
) -> tuple[bytes, str, int]:
    """gpt-image-2 generations only. Never send Day_004 into images/edits."""
    api_key = openai_api_key()
    calls = 0
    tag = {DIRECTION_R2: "r2", DIRECTION_R1: "r1"}.get(direction, "51d")
    if not force_chroma:
        try:
            remote = generate_image(
                api_key=api_key,
                model=availability.model,
                prompt=overlay_prompt(facts, chroma=False, extra=extra, direction=direction, plan=plan),
                size=OVERLAY_SIZE,
                quality=availability.quality,
                base_url=availability.base_url,
                variant=f"phase5-1d-{tag}-overlay-transparent",
                background="transparent",
                output_format="png",
            )
            calls += 1
            return decode_remote_image(remote), "generations_transparent_png", calls
        except GptImageProviderError:
            calls += 1
            logger.info("phase5.1d transparent overlay unsupported; chroma fallback")
    remote = generate_image(
        api_key=api_key,
        model=availability.model,
        prompt=overlay_prompt(facts, chroma=True, extra=extra, direction=direction, plan=plan),
        size=OVERLAY_SIZE,
        quality=availability.quality,
        base_url=availability.base_url,
        variant=f"phase5-1d-{tag}-overlay-chroma",
    )
    calls += 1
    return decode_remote_image(remote), "generations_magenta_chroma", calls


def prepare_overlay(raw: bytes, *, method: str) -> Image.Image:
    im = Image.open(io.BytesIO(raw))
    if method == "generations_transparent_png" and has_useful_alpha(im.convert("RGBA")):
        return im.convert("RGBA").resize(CANVAS_4X5, Image.Resampling.LANCZOS)
    keyed = magenta_to_alpha(im.convert("RGB").resize(CANVAS_4X5, Image.Resampling.LANCZOS))
    if overlay_transparency_ratio(keyed) < 0.18:
        # Native alpha may exist even if chroma failed.
        rgba = im.convert("RGBA").resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        if has_useful_alpha(rgba):
            return rgba
    return keyed


def generate_creative_overlay_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    revision: str | None = None,
    parent_asset_id: str | None = None,
) -> dict[str, Any]:
    """One 4:5 candidate. Does not overwrite 5.0 / 5.1 / 5.1A / 5.1B / 5.1C / production cover.

    revision='r1_premium_editorial' or 'r2_photo_aware' appends a new record and does not replace parents.
    """
    if revision == DIRECTION_R2:
        direction, workflow_id, default_parent = DIRECTION_R2, WORKFLOW_ID_51D_R2, PARENT_R1_ASSET_ID
    elif revision == DIRECTION_R1:
        direction, workflow_id, default_parent = DIRECTION_R1, WORKFLOW_ID_51D_R1, PARENT_51D_ASSET_ID
    else:
        direction, workflow_id, default_parent = DIRECTION_51D, WORKFLOW_ID_51D, None
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

    source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    centering = _centering_from_mass(source)
    foundation, transform = cover_fit_canvas(source, CANVAS_4X5, centering=centering)
    graded = apply_photographic_grade(
        foundation, {"warmth": 0.12, "contrast": 1.08, "brightness": 0.98, "vignette": 0.10}
    )
    facts = _facts()
    availability = provider_availability()
    plan: dict[str, Any] = {}
    if direction == DIRECTION_R2:
        plan, plan_calls = request_photo_aware_plan(graded, facts)
        provider_calls = plan_calls
    else:
        provider_calls = 0
    raw_overlay, overlay_method, overlay_calls = request_overlay_bytes(
        facts=facts, availability=availability, direction=direction, plan=plan or None
    )
    provider_calls += overlay_calls
    overlay = prepare_overlay(raw_overlay, method=overlay_method)
    preview = composite_overlay(graded, overlay)
    facts_check, vision_calls = verify_overlay_facts(preview, facts, overlay=overlay)
    provider_calls += vision_calls
    overlay_retries = 0
    if not overlay_quality_ok(overlay, facts_check, direction=direction):
        extra = (
            "RETRY. Previous overlay failed: keep the spire column empty, "
            "do not draw architecture, paint ONLY the required exact strings, "
            "and leave most of the canvas empty for the real photograph."
        )
        if direction == DIRECTION_R2:
            extra = (
                "RETRY. Stay photo-aware of the spatial brief. Do not cover the protected spire or architecture. "
                "Do not repeat R1. No giant right-side stack. Commercial facts as one system. "
                "No generated building. Exact campaign strings. Leave the logo zone empty."
            )
        if direction == DIRECTION_R1:
            extra = (
                "RETRY. Rejected the previous overlay. Editorial typography only. "
                "No ribbons, no sweeping gold curves, no giant medallion, no empty frames, no stars. "
                "Do not cross the left-center gothic spire. No generated building. "
                "Exact campaign strings only. No extra arrow. Leave far-left top empty for a real logo."
            )
        if facts_check.get("missing_required"):
            extra += " Missing: " + ", ".join(str(x) for x in facts_check["missing_required"])
        if facts_check.get("malformed_typography"):
            extra += " Typography was malformed. Redraw letters as exact campaign copy."
        if facts_check.get("contains_architecture"):
            extra += " You drew architecture in the overlay layer. Delete it. Overlay graphics only."
        force_chroma = overlay_transparency_ratio(overlay) < 0.22
        raw2, method2, calls2 = request_overlay_bytes(
            facts=facts,
            availability=availability,
            extra=extra,
            force_chroma=force_chroma,
            direction=direction,
            plan=plan or None,
        )
        overlay_retries = 1
        provider_calls += calls2
        overlay2 = prepare_overlay(raw2, method=method2)
        preview2 = composite_overlay(graded, overlay2)
        check2, v2 = verify_overlay_facts(preview2, facts, overlay=overlay2)
        provider_calls += v2
        if overlay_quality_ok(overlay2, check2, direction=direction) or (
            overlay_transparency_ratio(overlay2) + overlay_center_clear_ratio(overlay2)
            >= overlay_transparency_ratio(overlay) + overlay_center_clear_ratio(overlay)
        ):
            raw_overlay, overlay_method, overlay, facts_check = raw2, method2, overlay2, check2
    composed = composite_overlay(graded, overlay)
    logo = ResolvedSourceImage(
        asset_id=UUID(LOCKED_LOGO_ASSET_ID),
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category=None,
        tags=[],
        image_bytes=logo_bytes,
        role="project_logo",
    )
    logo_box = logo_box_from_plan(plan, overlay) if direction == DIRECTION_R2 else logo_box_from_overlay(overlay)
    with_logo, logo_meta = paste_logo(composed, logo, logo_box)
    final = with_logo.convert("RGB")
    provenance = architecture_provenance_qa(
        source=source, foundation=foundation, final=final, transform=transform
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(final),
        content_type="image/png",
        campaign_mode=(
            "project-creative-overlay-r2"
            if direction == DIRECTION_R2
            else "project-creative-overlay-r1"
            if direction == DIRECTION_R1
            else "project-creative-overlay"
        ),
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=(
            "PHASE 5.1D-R2 photo-aware overlay on Day_004 4:5"
            if direction == DIRECTION_R2
            else "PHASE 5.1D-R1 premium editorial overlay on Day_004 4:5"
            if direction == DIRECTION_R1
            else "PHASE 5.1D AI creative overlay on Day_004 4:5"
        ),
    )

    record = {
        "test_id": str(uuid4()),
        "workflow": workflow_id,
        "revision": revision,
        "parent_asset_id": parent_asset_id or default_parent,
        "art_direction": direction,
        "photo_awareness_used": direction == DIRECTION_R2,
        "plan_executed_by_os": False,
        "creative_overlay_plan": plan if direction == DIRECTION_R2 else None,
        "created_at": _now(),
        "source_asset_id": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "architecture_generation_used": False,
        "photo_foundation_method": "phase5_1b_locked_cover_fit_grade",
        "ai_creative_provider": "openai-image",
        "ai_creative_model": availability.model,
        "ai_creative_method": "gpt_image_generations_overlay_not_edits",
        "overlay_generation_method": overlay_method,
        "os_compositor_primary_designer": False,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "visible_commercial_content": [
            facts["headline"],
            f"{facts['unit']} {facts['unit_label']}",
            facts["list_price"],
            f"{facts['discount']} {facts['discount_label']}",
            facts["cta"],
        ],
        "final_asset_id": str(asset.id),
        "final_asset_url": asset_url(asset.id),
        "final_size": list(final.size),
        "architecture_modified": False,
        "ai_generated_building_used": False,
        "second_photo_patch": False,
        "duplicated_architecture": False,
        "non_uniform_scale": False,
        "video_started": False,
        "publishing_started": False,
        "gpt_image_edit_calls": 0,
        "provider_call_count": provider_calls,
        "overlay_retries": overlay_retries,
        "overlay_transparency_ratio": round(overlay_transparency_ratio(overlay), 4),
        "overlay_center_clear_ratio": round(overlay_center_clear_ratio(overlay), 4),
        "text_accuracy": facts_check,
        "text_accuracy_status": (
            "pass"
            if facts_check.get("pass") is True
            else "needs_human_review"
            if facts_check.get("pass") is False
            else "unchecked"
        ),
        "logo_meta": logo_meta,
        "transform": transform,
        "provenance_qa": provenance,
        "size_requested": OVERLAY_SIZE,
        "aspect_lock": ASPECT_TO_SIZE.get("4:5"),
    }

    tests = [
        t
        for t in preserved_overlay
        if not (isinstance(t, dict) and t.get("workflow") == workflow_id)
    ]
    tests.append(record)
    blob["creative_overlay_tests"] = tests
    blob["current_session_id"] = preserved_session
    blob["current_format_family_id"] = preserved_family
    blob["architecture_lock_tests"] = preserved_lock
    blob["photo_foundation_tests"] = preserved_photo
    blob["creative_design_tests"] = preserved_design
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
    _production_guard(before, after)
    if blob.get("current_session_id") != preserved_session:
        raise RuntimeError("Phase 5.1D refused to change current_session_id")
    if blob.get("current_format_family_id") != preserved_family:
        raise RuntimeError("Phase 5.1D refused to change current_format_family_id")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.1D refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": foundation,
        "foundation": graded,
        "overlay": overlay,
        "overlay_raw": Image.open(io.BytesIO(raw_overlay)).convert("RGBA"),
        "awareness_map": render_photo_awareness_map(graded, plan) if direction == DIRECTION_R2 else None,
        "final": final,
    }
    _ = language
    return record
