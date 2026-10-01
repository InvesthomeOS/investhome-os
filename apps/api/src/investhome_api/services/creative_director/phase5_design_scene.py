"""Phase 5.3 — AI-generated editable design scene.

Multimodal model writes SVG/HTML. Chromium renders it. Day_004 is a real
image element. GPT Image is not the project designer.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
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
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.gpt_image_design.config import openai_api_key, resolve_base_url
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

logger = logging.getLogger(__name__)

WORKFLOW_ID_53 = "phase5_3_ai_design_scene"
PHASE52B_REJECTED_ASSET_ID = "1928d4eb-c541-46b8-aca5-048f3a75e8c4"
MAX_ATTEMPTS = 3
CANVAS_W, CANVAS_H = CANVAS_4X5
SEMANTIC_REQUIRED = (
    "headline",
    "unit_type",
    "price",
    "discount",
    "discount_label",
    "cta",
    "project_logo",
    "project_photo",
)
CRITIC_MIN = {
    "professional_design_quality": 8,
    "photo_design_integration": 8,
    "typographic_sophistication": 8,
    "visual_hierarchy": 8,
    "commercial_readability": 8,
    "premium_character": 8,
}
CRITIC_MAX = {
    "text_on_photo_likeness": 3,
    "template_likeness": 3,
    "visual_clutter": 4,
    "ornament_overuse": 3,
}


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_b64(image: Image.Image, quality: int = 86) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _jpeg_data_uri(image: Image.Image, quality: int = 90) -> str:
    return f"data:image/jpeg;base64,{_jpeg_b64(image, quality=quality)}"


def _extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
        logger.info("phase5.3 vision failed", exc_info=True)
        return {}, 0


def font_face_css(registry: dict[str, Any]) -> str:
    roles = dict(registry.get("roles") or {})
    display = dict(roles.get("DISPLAY_SERIF") or {})
    support = dict(roles.get("EDITORIAL_SANS") or {})
    blocks = []
    for spec, family in ((display, "Cormorant Garamond"), (support, "Source Sans 3")):
        path = spec.get("font_path")
        if not path or not Path(str(path)).is_file():
            continue
        payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
        blocks.append(
            f"@font-face{{font-family:'{family}';src:url('data:font/ttf;base64,{payload}') "
            f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
        )
    return "\n".join(blocks)


def inline_logo_svg(logo_bytes: bytes) -> str:
    text = logo_bytes.decode("utf-8", errors="ignore").strip()
    text = re.sub(r"<\?xml[^>]*>", "", text, count=1).strip()
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, count=1).strip()
    if "data-semantic=" not in text:
        text = re.sub(r"<svg\b", '<svg data-semantic="project_logo"', text, count=1, flags=re.IGNORECASE)
    return text


def detect_scene_type(markup: str) -> str:
    raw = (markup or "").lstrip().lower()
    if raw.startswith("<svg") or "<svg" in raw[:400]:
        if "<html" in raw or "<div" in raw or "<img" in raw:
            return "HTML_SVG"
        return "SVG"
    return "HTML_SVG"


def assemble_scene(
    markup: str,
    *,
    photo_uri: str,
    logo_markup: str,
    font_css: str,
) -> str:
    scene = markup or ""
    scene = scene.replace("{{PHOTO_SRC}}", photo_uri)
    scene = scene.replace("{{LOGO_MARKUP}}", logo_markup)
    scene = scene.replace("{{FONT_CSS}}", font_css)
    scene = re.sub(
        r"(<img\b[^>]*\bdata-semantic\s*=\s*[\"']project_photo[\"'][^>]*\bsrc\s*=\s*[\"'])[^\"']*",
        rf"\1{photo_uri}",
        scene,
        flags=re.IGNORECASE,
    )
    scene = re.sub(
        r"(<(?:image)\b[^>]*\bdata-semantic\s*=\s*[\"']project_photo[\"'][^>]*\b(?:href|xlink:href)\s*=\s*[\"'])[^\"']*",
        rf"\1{photo_uri}",
        scene,
        flags=re.IGNORECASE,
    )
    return scene


def wrap_html(markup: str, font_css: str) -> str:
    raw = (markup or "").strip()
    if re.search(r"<html[\s>]", raw, re.IGNORECASE):
        if "font-family:'Cormorant Garamond'" not in raw and "@font-face" not in raw:
            raw = raw.replace("</head>", f"<style>{font_css}</style></head>", 1) if "</head>" in raw.lower() else raw
            if "@font-face" not in raw:
                raw = f"<style>{font_css}</style>" + raw
        return raw
    inner = raw
    if not re.search(r"<svg[\s>]", raw, re.IGNORECASE):
        inner = f'<div id="stage">{raw}</div>'
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        f"<style>html,body{{margin:0;padding:0;width:{CANVAS_W}px;height:{CANVAS_H}px;overflow:hidden;background:#0c0e12;}}"
        f"#stage,svg{{width:{CANVAS_W}px;height:{CANVAS_H}px;display:block;}}"
        f"{font_css}</style></head><body>{inner}</body></html>"
    )


def persistable_markup(markup: str, photo_uri: str) -> str:
    return (markup or "").replace(photo_uri, "{{PHOTO_SRC}}")


def validate_scene(markup: str, facts: dict[str, str], photo_uri: str) -> dict[str, Any]:
    flags: list[str] = []
    folded = markup or ""
    lower = folded.casefold()
    if photo_uri not in folded:
        flags.append("project_photo_src_missing")
    if not re.search(r"<(?:img|image)\b", folded, re.IGNORECASE):
        flags.append("no_image_element")
    if re.search(r"<(?:img|image)\b[^>]+\b(?:src|href|xlink:href)\s*=\s*[\"']https?:", folded, re.IGNORECASE):
        flags.append("remote_image_forbidden")
    for key in SEMANTIC_REQUIRED:
        if f'data-semantic="{key}"' not in folded and f"data-semantic='{key}'" not in folded:
            flags.append(f"missing_semantic_{key}")
    required_text = [
        facts["headline"],
        facts["list_price"],
        facts["discount"],
        facts["discount_label"],
        f"{facts['unit']} {facts['unit_label']}" if facts.get("unit_label") else facts["unit"],
        facts["cta"],
    ]
    missing_text = [item for item in required_text if item and item.casefold() not in lower]
    if missing_text:
        flags.append("missing_campaign_text")
    if "dejavu" in lower and "emergency" not in lower:
        flags.append("dejavu_used")
    if re.search(r"<script[\s>]", folded, re.IGNORECASE):
        flags.append("script_forbidden")
    return {
        "pass": not flags,
        "flags": flags,
        "missing_text": missing_text,
        "semantic_editability": all(
            f'data-semantic="{key}"' in folded or f"data-semantic='{key}'" in folded for key in SEMANTIC_REQUIRED
        ),
        "text_accuracy": not missing_text,
    }


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


def render_html_to_png(html: str, *, width: int = CANVAS_W, height: int = CANVAS_H) -> Image.Image:
    """Chromium screenshot of the design scene. Fonts must be loaded first."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required to render AICreativeSceneV1") from exc
    with tempfile.TemporaryDirectory(prefix="phase53-") as td:
        path = Path(td) / "scene.html"
        path.write_text(html, encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page.goto(path.as_uri(), wait_until="load", timeout=60_000)
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(250)
            png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": width, "height": height})
            browser.close()
    return Image.open(io.BytesIO(png)).convert("RGB")


def request_photo_analysis(foundation: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You are analyzing one locked architectural photograph for advertising design. JSON only.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is the exact final 1088×1360 crop of Day_004. Identify spire, tower, main façade, "
                            "roof, project mass, sky, trees, road, high-detail regions, low-detail regions, and "
                            "usable negative space. Boxes 0-1 {x,y,w,h}. "
                            "JSON: {reading, focal_point, light, regions:{SPIRE,TOWER,MAIN_FACADE,ROOFLINE,"
                            "PROJECT_MASS,SKY,TREES,ROAD,NEGATIVE_SPACE_RIGHT,NEGATIVE_SPACE_LEFT},"
                            "high_detail, low_detail, design_opportunity}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed.setdefault("schema", "PhotoAnalysisV1")
    parsed["mode"] = "vision" if parsed.get("reading") or parsed.get("regions") else "unavailable"
    return parsed, calls


def _designer_contract(facts: dict[str, str]) -> str:
    return (
        "Write the COMPLETE executable design as markup. This is the advertisement, not a recommendation.\n"
        "Canvas exactly 1088×1360. scene_type SVG or HTML_SVG. Prefer SVG if it can carry the design.\n"
        "TOKENS you MUST use (the OS substitutes real assets; do not invent them):\n"
        "  {{PHOTO_SRC}} — real Day_004 jpeg data URI for the project photograph\n"
        "  {{LOGO_MARKUP}} — real Temple SVG markup. Insert it. Do not redraw the mark.\n"
        "  {{FONT_CSS}} — @font-face for Cormorant Garamond and Source Sans 3. Include in <style>.\n"
        "The photograph MUST be a real <img> or SVG <image> with data-semantic=\"project_photo\" and src/href={{PHOTO_SRC}}.\n"
        "Allowed on the photo: object-fit/object-position, clip-path, mask, CSS filters, vignette overlays.\n"
        "Forbidden: generating a building, tower, spire, façade, windows, or any replacement architecture.\n"
        "Tag every commercial node: data-semantic=headline|unit_type|price|discount|discount_label|cta|project_logo|project_photo.\n"
        "Exact strings, Turkish glyphs exact:\n"
        f"  {facts['headline']}\n"
        f"  {facts['list_price']}\n"
        f"  {facts['discount']}\n"
        f"  {facts['discount_label']}\n"
        f"  {facts['unit']} {facts['unit_label']}\n"
        f"  {facts['cta']}\n"
        "Hierarchy: ALIRKEN KAZAN is the campaign idea; 675.000 USD is the commercial anchor; "
        "%35 LANSMAN AVANTAJI and 2+1 DAİRE support; PROJEYİ KEŞFET is the action; the real logo is the brand.\n"
        "They must read as one visual story. Do not scatter them.\n"
        "Direction: premium Washington DC architectural editorial luxury real-estate investment. "
        "Sophisticated, confident, contemporary, restrained. Not flashy, not Canva, not UI.\n"
        "Hard reject: giant discount medal, ribbon, sweeping gold ornament, casino/jewelry/wedding aesthetic, "
        "dashboard cards, KPI boxes, giant button, random gold lines, cheap glow, giant opaque rectangle, "
        "headline through the spire, logo colliding with the spire, price destroying the primary façade, "
        "CTA hiding key architecture, text dumped over the building.\n"
        "Do not copy Phase 5.0 pixels or its generated building. Learn why it feels designed.\n"
        "JSON only: {scene_type, concept, visual_story, markup, semantic_elements, relationships, "
        "photo_filters, layers, protected_photo_relationship}"
    )


def request_scene(
    *,
    foundation: Image.Image,
    reference: Image.Image,
    rejected: Image.Image,
    logo: Image.Image,
    protection_map: Image.Image,
    analysis: dict[str, Any],
    fonts: dict[str, Any],
    facts: dict[str, str],
    previous_markup: str | None = None,
    previous_render: Image.Image | None = None,
    critique: str = "",
) -> tuple[dict[str, Any], int]:
    roles = fonts.get("roles") or {}
    font_note = (
        f"DISPLAY {(roles.get('DISPLAY_SERIF') or {}).get('font_file')} / "
        f"SUPPORT {(roles.get('EDITORIAL_SANS') or {}).get('font_file')}. Never DejaVu."
    )
    retry = ""
    if critique:
        retry = (
            "REWRITE the complete scene. You may change composition substantially. "
            "Do not nudge coordinates. Respond to this art-direction critique:\n"
            f"{critique}\n"
        )
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Image 1: exact 1088×1360 Day_004 foundation. This photograph is immutable.\n"
                "Image 2: Phase 5.0 quality reference — design feeling only. Do NOT copy its architecture.\n"
                "Image 3: Phase 5.2B rejected candidate — ornament, cards, fake luxury, text-on-photo, "
                "thin composition, poor typographic mass, weak integration. Do not repeat it.\n"
                "Image 4: real Temple logo preview.\n"
                "Image 5: protected architecture map.\n"
                f"Photo analysis: {json.dumps(analysis, default=str)[:2400]}\n"
                f"Fonts: {font_note}\n"
                + retry
                + _designer_contract(facts)
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(rejected)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(logo)}", "detail": "low"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(protection_map)}", "detail": "low"}},
    ]
    if previous_render is not None:
        content.append(
            {
                "type": "text",
                "text": "Image 6 is the previous browser render of YOUR scene. Rewrite the markup, do not polish coordinates.",
            }
        )
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(previous_render)}", "detail": "high"}}
        )
    if previous_markup:
        content.append({"type": "text", "text": "Previous markup (you may replace it entirely):\n" + previous_markup[:12000]})
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.55 if not critique else 0.45,
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the senior art director of a premium international real-estate advertising agency. "
                    "You write finished executable SVG/HTML advertisements. You do not describe layouts. JSON only."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    markup = str(parsed.get("markup") or parsed.get("scene_markup") or "")
    scene = {
        "schema": "AICreativeSceneV1",
        "scene_id": str(uuid4()),
        "scene_type": str(parsed.get("scene_type") or detect_scene_type(markup)),
        "concept": str(parsed.get("concept") or ""),
        "visual_story": str(parsed.get("visual_story") or ""),
        "markup": markup,
        "semantic_elements": parsed.get("semantic_elements") or [],
        "relationships": parsed.get("relationships") or {},
        "photo_filters": parsed.get("photo_filters") or "",
        "layers": parsed.get("layers") or [],
        "protected_photo_relationship": parsed.get("protected_photo_relationship") or "",
        "mode": "vision" if markup else "unavailable",
    }
    return scene, calls


def request_design_critic(
    *,
    foundation: Image.Image,
    reference: Image.Image,
    candidate: Image.Image,
    facts: dict[str, str],
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Independent luxury real-estate art director. You did not design this ad. "
                    "Ask whether this is a professionally art-directed campaign or text on a photograph. "
                    "Give art-direction critique, never x/y coordinates. JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 new browser-rendered candidate. Image 2 Day_004 photograph. "
                            "Image 3 Phase 5.0 quality reference (design feeling only; ignore its building).\n"
                            f"Required story: {facts['headline']} / {facts['list_price']} / "
                            f"{facts['discount']} {facts['discount_label']} / {facts['unit']} {facts['unit_label']} / {facts['cta']}.\n"
                            "JSON scores 0-10: professional_design_quality, photo_design_integration, "
                            "typographic_sophistication, visual_hierarchy, commercial_readability, photo_specificity, "
                            "premium_character, logo_integration, cta_integration, negative_space_usage, visual_balance, "
                            "text_on_photo_likeness, template_likeness, visual_clutter, ornament_overuse, "
                            "looks_like_designed_campaign (bool), critique (art-direction, actionable), notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["architecture_truth"] = 10
    parsed["mode"] = "vision" if parsed.get("professional_design_quality") is not None else "unavailable"
    parsed["pass"] = critic_pass(parsed) if parsed["mode"] == "vision" else False
    return parsed, calls


def _logo_preview(logo_bytes: bytes) -> Image.Image:
    canvas = Image.new("RGB", (480, 180), (22, 24, 30))
    try:
        from investhome_api.services.gpt_image_design.compose import logo_to_rgba

        rgba = logo_to_rgba(logo_bytes, "logo.svg", "image/svg+xml")
        if rgba is not None:
            fitted = rgba.copy()
            fitted.thumbnail((440, 150), Image.Resampling.LANCZOS)
            canvas.paste(fitted, (20, 15), fitted if fitted.mode == "RGBA" else None)
    except Exception:
        pass
    return canvas


def render_analysis_card(foundation: Image.Image, analysis: dict[str, Any], protection: Image.Image) -> Image.Image:
    im = protection.convert("RGB")
    if im.size != foundation.size:
        im = protection.resize(foundation.size, Image.Resampling.LANCZOS).convert("RGB")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    draw.rectangle((24, 24, 1064, 220), fill=(12, 14, 20))
    draw.text((40, 40), "PHOTO ANALYSIS — design must respond to this crop", fill=(201, 168, 92), font=font)
    draw.text((40, 70), str(analysis.get("reading") or "")[:110], fill=(236, 232, 224), font=font)
    draw.text((40, 100), f"focal: {str(analysis.get('focal_point') or '')[:90]}", fill=(236, 232, 224), font=font)
    draw.text((40, 130), f"opportunity: {str(analysis.get('design_opportunity') or '')[:90]}", fill=(236, 232, 224), font=font)
    return im


def generate_design_scene_4x5(
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
        "vad": list(blob.get("visual_art_director_tests") or []),
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
    before["visual_art_director_tests_count"] = len(preserved["vad"])

    fonts = build_font_registry()
    font_css = font_face_css(fonts)
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    logo_markup = inline_logo_svg(logo_bytes)
    try:
        reference = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE50_MASTER_ASSET_ID)))).convert("RGB")
    except Exception:
        reference = source
    try:
        rejected = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE52B_REJECTED_ASSET_ID)))).convert("RGB")
    except Exception:
        rejected = source
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, {"warmth": 0.10, "contrast": 1.06, "brightness": 0.99, "vignette": 0.08})
    photo_uri = _jpeg_data_uri(graded)
    logo_preview = _logo_preview(logo_bytes)

    provider_calls = 0
    gpt_image_calls = 0
    dna, c = analyze_reference_dna(reference)
    provider_calls += c
    protection, c = request_protection_map(graded)
    provider_calls += c
    protection_map = render_protection_map(graded, protection)
    analysis, c = request_photo_analysis(graded)
    provider_calls += c

    attempts: list[dict[str, Any]] = []
    previous_markup = None
    previous_render = None
    critique = ""
    winner = None
    for index in range(1, MAX_ATTEMPTS + 1):
        scene, c = request_scene(
            foundation=graded,
            reference=reference,
            rejected=rejected,
            logo=logo_preview,
            protection_map=protection_map,
            analysis=analysis,
            fonts=fonts,
            facts=campaign_facts,
            previous_markup=previous_markup,
            previous_render=previous_render,
            critique=critique,
        )
        provider_calls += c
        assembled = assemble_scene(
            str(scene.get("markup") or ""),
            photo_uri=photo_uri,
            logo_markup=logo_markup,
            font_css=font_css,
        )
        html = wrap_html(assembled, font_css)
        gate = validate_scene(html, campaign_facts, photo_uri)
        rendered = None
        render_error = None
        if gate["pass"]:
            try:
                rendered = render_html_to_png(html)
            except Exception as exc:
                render_error = str(exc)
                logger.info("phase5.3 render failed", extra={"error": render_error})
        else:
            render_error = ",".join(gate.get("flags") or [])
        if rendered is None:
            rendered = graded.copy()
            critic = {
                "architecture_truth": 10,
                "professional_design_quality": 0,
                "photo_design_integration": 0,
                "typographic_sophistication": 0,
                "visual_hierarchy": 0,
                "commercial_readability": 0,
                "premium_character": 0,
                "text_on_photo_likeness": 10,
                "template_likeness": 10,
                "visual_clutter": 10,
                "ornament_overuse": 10,
                "critique": f"Scene did not render. {render_error or 'invalid scene'}",
                "notes": render_error or "invalid scene",
                "mode": "unavailable",
                "pass": False,
            }
            critic_calls = 0
        else:
            critic, critic_calls = request_design_critic(
                foundation=graded, reference=reference, candidate=rendered, facts=campaign_facts
            )
            provider_calls += critic_calls
            if critic.get("mode") != "vision":
                critic["pass"] = False
            critic["architecture_truth"] = 10
            critic["pass"] = bool(critic.get("pass")) and critic_pass(critic) and bool(gate.get("pass"))
        pack = {
            "attempt": index,
            "scene": scene,
            "assembled_markup": assembled,
            "html": html,
            "gate": gate,
            "image": rendered,
            "critic": critic,
            "render_error": render_error,
            "parent_scene_id": attempts[-1]["scene"].get("scene_id") if attempts else None,
            "revision_instruction": critique or None,
        }
        attempts.append(pack)
        if critic.get("pass") and gate.get("pass"):
            winner = pack
            break
        previous_markup = assembled
        previous_render = rendered
        critique = str(critic.get("critique") or critic.get("notes") or "Rewrite as one designed campaign, not text on a photo.")

    if winner is None and attempts:
        winner = max(
            attempts,
            key=lambda p: float((p.get("critic") or {}).get("professional_design_quality") or 0)
            + float((p.get("critic") or {}).get("photo_design_integration") or 0),
        )
    plausible = bool(winner and winner["critic"].get("pass") and winner["gate"].get("pass"))
    stopped = bool(attempts) and not plausible
    provenance = architecture_provenance_qa(
        source=source, foundation=crop, final=(winner["image"] if winner else graded), transform=transform
    )
    final_image = winner["image"] if winner else graded
    scene_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(final_image),
        content_type="image/png",
        campaign_mode="project-ai-design-scene",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.3 AI design scene master 4:5",
    )
    roles = fonts.get("roles") or {}
    scene_record = {
        "schema": "AICreativeSceneV1",
        "scene_id": (winner or {}).get("scene", {}).get("scene_id") if winner else str(uuid4()),
        "project_id": TEMPLE_PROJECT_ID,
        "source_photo_asset_id": hero_id,
        "logo_asset_id": logo_id,
        "canvas": {"width": CANVAS_W, "height": CANVAS_H, "aspect": "4:5"},
        "scene_markup": persistable_markup((winner or {}).get("assembled_markup") or "", photo_uri) if winner else None,
        "scene_type": (winner or {}).get("scene", {}).get("scene_type") if winner else None,
        "fonts": {
            "display": (roles.get("DISPLAY_SERIF") or {}).get("font_file"),
            "support": (roles.get("EDITORIAL_SANS") or {}).get("font_file"),
            "registry": fonts.get("schema"),
        },
        "semantic_elements": (winner or {}).get("scene", {}).get("semantic_elements") if winner else [],
        "relationships": (winner or {}).get("scene", {}).get("relationships") if winner else {},
        "layers": (winner or {}).get("scene", {}).get("layers") if winner else [],
        "protected_architecture": protection,
        "photo_crop": transform,
        "photo_filters": (winner or {}).get("scene", {}).get("photo_filters") if winner else None,
        "created_at": _now(),
        "parent_scene_id": (winner or {}).get("parent_scene_id") if winner else None,
        "revision_instruction": (winner or {}).get("revision_instruction") if winner else None,
        "render_asset_id": str(scene_asset.id),
    }
    record = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_53,
        "created_at": _now(),
        "creative_method": "multimodal_ai_editable_svg_html_scene_browser_render",
        "source_asset_id": hero_id,
        "source_filename": HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None,
        "architecture_generation_used": False,
        "gpt_image_calls": gpt_image_calls,
        "gpt_image_edit_calls": 0,
        "real_logo_asset_id": logo_id,
        "design_model": VISION_MODEL,
        "scene_format": scene_record.get("scene_type"),
        "font_registry": fonts.get("schema"),
        "display_font": (roles.get("DISPLAY_SERIF") or {}).get("font_file"),
        "support_font": (roles.get("EDITORIAL_SANS") or {}).get("font_file"),
        "scene_attempts": len(attempts),
        "attempt_scores": [
            {
                "attempt": a["attempt"],
                "scene_id": a["scene"].get("scene_id"),
                "pass": a["critic"].get("pass"),
                "professional_design_quality": a["critic"].get("professional_design_quality"),
                "photo_design_integration": a["critic"].get("photo_design_integration"),
                "text_on_photo_likeness": a["critic"].get("text_on_photo_likeness"),
                "template_likeness": a["critic"].get("template_likeness"),
                "ornament_overuse": a["critic"].get("ornament_overuse"),
                "gate": a["gate"],
            }
            for a in attempts
        ],
        "winning_attempt": (winner or {}).get("attempt"),
        "final_scene_id": scene_record.get("scene_id"),
        "final_asset_id": str(scene_asset.id),
        "final_asset_url": asset_url(scene_asset.id),
        "final_size": list(final_image.size),
        "provider_call_count": provider_calls,
        "text_accuracy": bool((winner or {}).get("gate", {}).get("text_accuracy")),
        "semantic_editability": bool((winner or {}).get("gate", {}).get("semantic_editability")),
        "campaign_plausible": plausible,
        "stopped_after_critic_failure": stopped,
        "provenance_qa": provenance,
        "design_critic": (winner or {}).get("critic"),
        "ai_creative_scene": scene_record,
        "reference_dna": dna,
        "photo_analysis": analysis,
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
        for t in list(blob.get("design_scene_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_53)
    ]
    tests.append({k: v for k, v in record.items() if k != "ai_creative_scene"} | {"ai_creative_scene": scene_record})
    blob["design_scene_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    blob["architecture_lock_tests"] = preserved["lock"]
    blob["photo_foundation_tests"] = preserved["photo"]
    blob["creative_design_tests"] = preserved["design"]
    blob["creative_overlay_tests"] = preserved["overlay"]
    blob["creative_master_tests"] = preserved["master"]
    blob["production_creative_tests"] = preserved["production"]
    blob["visual_art_director_tests"] = preserved["vad"]
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
    after["visual_art_director_tests_count"] = len(list(blob.get("visual_art_director_tests") or []))
    _production_guard(before, after)
    if blob.get("visual_art_director_tests") != preserved["vad"]:
        raise RuntimeError("Phase 5.3 refused to change Phase 5.2B history")
    if blob.get("production_creative_tests") != preserved["production"]:
        raise RuntimeError("Phase 5.3 refused to change Phase 5.2 history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.3 refused to change production cover")
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
        "analysis": render_analysis_card(graded, analysis, protection_map),
        "final": final_image,
        "attempts": {a["attempt"]: a["image"] for a in attempts},
    }
    record["attempts"] = attempts
    record["fonts"] = fonts
    record["photo_uri"] = photo_uri
    _ = language
    return record
