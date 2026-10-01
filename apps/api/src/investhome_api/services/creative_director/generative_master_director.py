"""Generative Design Master director — GPT Image designs the advertisement around Day_004.

Does not rebuild reference storage, Drive, or Phase 5.5 revision.
Does not ask the image model to redraw The Temple logo or architecture.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.project_architecture_lock import (
    architecture_lock_prompt_lines,
    derive_architecture_mask,
)
from investhome_api.services.gpt_image_design.client import decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.compose import _fit_logo, logo_to_rgba
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
)
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL
from investhome_api.config.settings import get_settings

G_DIRECTIONS = (
    {
        "key": "G1",
        "concept": "PREMIUM_EDITORIAL_CAMPAIGN",
        "intent": (
            "Premium editorial advertising. Reference-driven sophistication. "
            "Architecture remains dominant. Strong editorial typography. "
            "Commercial information elegant but immediately readable. No magazine-cover cliché."
        ),
    },
    {
        "key": "G2",
        "concept": "HIGH_IMPACT_INVESTMENT_CAMPAIGN",
        "intent": (
            "Strongest commercial advertisement. ALIRKEN KAZAN and the offer communicate immediately. "
            "675.000 USD and %35 LANSMAN AVANTAJI as a designed commercial system. "
            "Strongest social-media advertising candidate. Not a listing card."
        ),
    },
    {
        "key": "G3",
        "concept": "CONTEMPORARY_ARCHITECTURAL_LUXURY",
        "intent": (
            "Most art-directed option. Contemporary architectural campaign. "
            "Sophisticated interaction between photography, typography and graphic fields. "
            "Distinctive but commercially usable. Architecture recognizable and unchanged."
        ),
    },
)

REQUIRED_COPY = (
    REQUIRED_FACTS["headline"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["list_price"],
    REQUIRED_FACTS["discount"],
    REQUIRED_FACTS["discount_label"],
    REQUIRED_FACTS["cta"],
)

MOJIBAKE_MARKERS = (
    "DAÄ",
    "PROJEYÄ",
    "KEÅ",
    "KEÄ",
    "DAA°",
    "AVANTAJ ",
    "Ä°",
    "Åž",
    "Å½",
    "Äž",
)

FORBIDDEN_FEEL = (
    "white property card",
    "translucent information rectangle",
    "listing template",
    "dashboard",
    "Canva template",
    "giant lower third",
    "badge",
    "medallion",
    "ribbon",
    "web button",
    "tiny unreadable information",
    "simple text overlay on a photo",
)

EDITABLE_GROUPS = ("headline", "unit_type", "price", "discount", "discount_label", "cta", "logo")


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(image: Image.Image, quality: int = 88) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _box(raw: Any) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    try:
        x = float(raw.get("x", 0))
        y = float(raw.get("y", 0))
        w = float(raw.get("w", raw.get("width", 0)))
        h = float(raw.get("h", raw.get("height", 0)))
    except (TypeError, ValueError):
        return None
    x = max(0.0, min(0.98, x))
    y = max(0.0, min(0.98, y))
    w = max(0.04, min(1.0 - x, w))
    h = max(0.03, min(1.0 - y, h))
    if w < 0.04 or h < 0.03:
        return None
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def box_px(box: dict[str, Any] | None, size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    parsed = _box(box)
    if not parsed:
        return None
    width, height = size
    x0 = max(0, int(parsed["x"] * width))
    y0 = max(0, int(parsed["y"] * height))
    x1 = min(width, int((parsed["x"] + parsed["w"]) * width))
    y1 = min(height, int((parsed["y"] + parsed["h"]) * height))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def architecture_protection_mask_v1(
    foundation: Image.Image,
    protection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Protect architecture. OpenAI mask: transparent = edit, opaque = preserve."""
    src = foundation.convert("RGB")
    auto = derive_architecture_mask(src)
    protect = auto.convert("L")
    draw = ImageDraw.Draw(protect)
    for box in dict((protection or {}).get("regions") or {}).values():
        px = box_px(box, src.size)
        if px:
            draw.rectangle(px, fill=255)
    protect = protect.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(radius=1.2))
    protect = protect.point(lambda v: 255 if v > 48 else 0)
    rgba = Image.new("RGBA", src.size, (0, 0, 0, 0))
    rgba.putalpha(protect)
    white = Image.new("RGBA", src.size, (255, 255, 255, 255))
    mask_rgba = Image.composite(white, Image.new("RGBA", src.size, (0, 0, 0, 0)), protect)
    coverage = sum(protect.getdata()) / (255.0 * src.width * src.height)
    overlay = src.convert("RGBA")
    red = Image.new("RGBA", src.size, (200, 40, 40, 90))
    overlay = Image.composite(Image.alpha_composite(overlay, red), overlay, protect)
    return {
        "schema": "ArchitectureProtectionMaskV1",
        "protected": (
            "complete Temple building",
            "spire",
            "façade",
            "windows",
            "roof",
            "entrance",
            "architectural edges",
            "important building geometry",
        ),
        "editable": (
            "sky / negative space",
            "controlled surrounding graphic regions",
            "non-architectural overlay space",
            "graphic design surfaces",
            "typographic composition",
            "tonal integration",
        ),
        "protected_coverage": round(coverage, 4),
        "size": list(src.size),
        "mask_l": protect,
        "mask_rgba": mask_rgba,
        "visualization": overlay.convert("RGB"),
        "openai_convention": "transparent=edit opaque=preserve",
    }


def openai_mask_png(mask: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    mask["mask_rgba"].save(buf, format="PNG")
    return buf.getvalue()


def _dna_excerpt(retrieved: list[dict[str, Any]]) -> str:
    rows = []
    for item in retrieved[:6]:
        dna = dict(item.get("dna") or {})
        rows.append(
            {
                "reference_id": item.get("reference_id"),
                "filename": item.get("filename"),
                "why": dna.get("WHY_IT_WORKS"),
                "reusable": dna.get("REUSABLE_PRINCIPLES"),
                "do_not_copy": dna.get("DO_NOT_COPY"),
                "typography": dna.get("typography_hierarchy"),
                "integration": dna.get("text_image_integration"),
                "price": dna.get("price_behavior") or dna.get("commercial_information_strategy"),
            }
        )
    return json.dumps(rows, ensure_ascii=True)[:7000]


def request_generative_master_brief(
    *,
    foundation: Image.Image,
    logo_preview: Image.Image,
    protection_preview: Image.Image,
    retrieved: list[dict[str, Any]],
    photo_analysis: dict[str, Any],
    doctrine: dict[str, Any],
    direction: dict[str, str],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Inspect ALL images. Image 1 = exact Temple Day_004 4:5 crop. "
                "Image 2 = real Temple logo (do not redraw it; plan a placement only). "
                "Image 3 = architecture protection map. Remaining images = DESIGN_REFERENCES "
                "for art-direction quality only. Do not copy their buildings, logos, or copy.\n"
                f"CONCEPT {direction['key']}: {direction['concept']}\n{direction['intent']}\n"
                f"Copy (exact UTF-8): {' / '.join(REQUIRED_COPY)}\n"
                f"Photo analysis: {json.dumps(photo_analysis, ensure_ascii=True)[:1800]}\n"
                f"Doctrine rules: {json.dumps(list((doctrine or {}).get('core_rules') or [])[:12], ensure_ascii=True)}\n"
                f"Reference DNA: {_dna_excerpt(retrieved)}\n"
                "Forbidden: " + "; ".join(FORBIDDEN_FEEL) + "\n"
                "Return GenerativeMasterBriefV1 JSON with: overall_concept, photographic_treatment, "
                "image_design_integration, headline_composition, logo_relationship, typography_character, "
                "price_system, discount_system, cta_system, graphic_interventions, negative_space, "
                "protected_architecture, reading_hierarchy, visual_balance, "
                "zones {headline,unit_type,price,discount,discount_label,cta,logo,graphic_field as {x,y,w,h}}, "
                "reference_applications [{reference_id,principle,planned_application}], "
                "why_this_is_not_text_on_photo. This brief is not the final creative."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(logo_preview)}", "detail": "low"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(protection_preview)}", "detail": "low"}},
    ]
    for item in retrieved[:6]:
        preview = item.get("_preview")
        if isinstance(preview, Image.Image):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(preview, quality=72)}", "detail": "high"},
                }
            )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.35,
        "max_tokens": 2200,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior art director writing a generative master brief. "
                    "The AI may design the advertisement. The AI may not redesign the project. JSON only."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    zones_raw = dict(parsed.get("zones") or {})
    brief = {
        "schema": "GenerativeMasterBriefV1",
        "brief_id": str(uuid4()),
        "key": direction["key"],
        "concept": direction["concept"],
        "intent": direction["intent"],
        "overall_concept": str(parsed.get("overall_concept") or direction["intent"]),
        "photographic_treatment": str(parsed.get("photographic_treatment") or "keep Day_004 architecture; design around it"),
        "image_design_integration": str(parsed.get("image_design_integration") or ""),
        "headline_composition": str(parsed.get("headline_composition") or ""),
        "logo_relationship": str(parsed.get("logo_relationship") or "real logo composited after generation"),
        "typography_character": str(parsed.get("typography_character") or "Cormorant Garamond display / Source Sans 3 support"),
        "price_system": str(parsed.get("price_system") or "675.000 USD as a designed commercial number"),
        "discount_system": str(parsed.get("discount_system") or "%35 LANSMAN AVANTAJI as a designed pair"),
        "cta_system": str(parsed.get("cta_system") or "PROJEYİ KEŞFET as an inscription, not a web button"),
        "graphic_interventions": str(parsed.get("graphic_interventions") or ""),
        "negative_space": str(parsed.get("negative_space") or ""),
        "protected_architecture": str(parsed.get("protected_architecture") or "spire, façade, windows, roof, entrance"),
        "reading_hierarchy": str(parsed.get("reading_hierarchy") or "ALIRKEN KAZAN → offer → CTA"),
        "visual_balance": str(parsed.get("visual_balance") or ""),
        "zones": {key: _box(zones_raw.get(key)) for key in (*EDITABLE_GROUPS, "graphic_field")},
        "reference_applications": list(parsed.get("reference_applications") or [])[:8],
        "why_this_is_not_text_on_photo": str(parsed.get("why_this_is_not_text_on_photo") or ""),
        "mode": "vision" if parsed.get("overall_concept") else "unavailable",
        "reference_ids": [str(item.get("reference_id")) for item in retrieved[:6]],
    }
    return brief, calls


def build_edit_prompt(brief: dict[str, Any], direction: dict[str, str]) -> str:
    lock = "\n".join(architecture_lock_prompt_lines())
    apps = json.dumps(brief.get("reference_applications") or [], ensure_ascii=True)[:1600]
    return (
        f"{lock}\n"
        "MODE: design an advertisement AROUND the real project photograph (image 1). "
        "Do NOT invent a new Temple building. Do NOT repaint protected architecture. "
        "Additional images are DESIGN_REFERENCES for visual language only — do not copy their "
        "buildings, logos, people, or copy.\n"
        f"CONCEPT {direction['key']} {direction['concept']}: {direction['intent']}\n"
        f"Brief: {brief.get('overall_concept')}\n"
        f"Integration: {brief.get('image_design_integration')}\n"
        f"Headline: {brief.get('headline_composition')}\n"
        f"Price system: {brief.get('price_system')}\n"
        f"Discount system: {brief.get('discount_system')}\n"
        f"CTA: {brief.get('cta_system')}\n"
        f"Graphics: {brief.get('graphic_interventions')}\n"
        f"Negative space: {brief.get('negative_space')}\n"
        f"Typography: {brief.get('typography_character')}\n"
        f"Reference applications: {apps}\n"
        "Exact campaign text if you render type (UTF-8 Turkish, no mojibake):\n"
        "ALIRKEN KAZAN\n"
        "2+1 DAİRE\n"
        "675.000 USD\n"
        "%35 LANSMAN AVANTAJI\n"
        "PROJEYİ KEŞFET\n"
        "Do NOT draw The Temple logo or any angel/wordmark. Leave a clean logo zone. "
        "The real logo will be composited afterwards.\n"
        "You MAY design graphic fields, editorial framing, sky treatment, color fields, "
        "typographic zones, and hierarchy in non-architectural space.\n"
        "Forbidden: white/translucent property card, listing template, dashboard, Canva look, "
        "giant lower third, badge, medallion, ribbon, web button, tiny unreadable type, "
        "headline or logo over the spire, text simply dropped on the photo.\n"
        "Agency-quality real-estate advertising. Premium, restrained, commercially clear."
    )


def run_generative_edit(
    *,
    foundation: Image.Image,
    retrieved: list[dict[str, Any]],
    mask_png: bytes,
    prompt: str,
    quality: str = "high",
) -> tuple[Image.Image, dict[str, Any]]:
    avail = provider_availability()
    if not avail.available:
        raise RuntimeError(f"GPT Image unavailable: {avail.reason}")
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    images: list[tuple[bytes, str, str]] = [(_png_bytes(foundation), "temple-day004.png", "image/png")]
    for idx, item in enumerate(retrieved[:5]):
        preview = item.get("_preview")
        if isinstance(preview, Image.Image):
            images.append((_jpeg_bytes(preview), f"reference-{idx + 1}.jpg", "image/jpeg"))
    remote = edit_image(
        api_key=openai_api_key(),
        model=model,
        prompt=prompt,
        images=images,
        size="1088x1360",
        quality=quality,
        base_url=resolve_base_url(settings),
        variant="phase5_4c_generative_master",
        mask=mask_png,
    )
    raw = decode_remote_image(remote)
    generated = Image.open(io.BytesIO(raw)).convert("RGB")
    if generated.size != foundation.size:
        generated = generated.resize(foundation.size, Image.Resampling.LANCZOS)
    return generated, {"model": model, "quality": quality, "size": "1088x1360", "input_images": len(images)}


def inspect_generated_candidate(
    *,
    candidate: Image.Image,
    foundation: Image.Image,
    brief: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Inspect a generated real-estate advertisement. JSON only. Be literal about visible text.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 is the generated candidate. Image 2 is locked Day_004.\n"
                            "Required exact strings: " + " | ".join(REQUIRED_COPY) + "\n"
                            "JSON: observed_text (array of visible strings), missing_required (array), "
                            "mojibake (boolean), fake_logo (boolean), fake_logo_box {x,y,w,h}|null, "
                            "architecture_changed (boolean), text_on_photo (boolean), property_card (boolean), "
                            "dashboard (boolean), spire_collision (boolean), "
                            "zones {headline,unit_type,price,discount,discount_label,cta,logo as {x,y,w,h}}, "
                            "typography_needs_replacement (boolean), notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    zones_raw = dict(parsed.get("zones") or brief.get("zones") or {})
    observed = [str(x) for x in list(parsed.get("observed_text") or [])]
    blob = " ".join(observed)
    mojibake = bool(parsed.get("mojibake")) or any(marker in blob for marker in MOJIBAKE_MARKERS)
    missing = [item for item in REQUIRED_COPY if item not in blob]
    inspect = {
        "schema": "GenerativeCandidateInspectV1",
        "observed_text": observed,
        "missing_required": list(parsed.get("missing_required") or missing),
        "mojibake": mojibake,
        "fake_logo": bool(parsed.get("fake_logo")),
        "fake_logo_box": _box(parsed.get("fake_logo_box")),
        "architecture_changed": bool(parsed.get("architecture_changed")),
        "text_on_photo": bool(parsed.get("text_on_photo")),
        "property_card": bool(parsed.get("property_card")),
        "dashboard": bool(parsed.get("dashboard")),
        "spire_collision": bool(parsed.get("spire_collision")),
        "zones": {key: _box(zones_raw.get(key)) or _box((brief.get("zones") or {}).get(key)) for key in EDITABLE_GROUPS},
        "typography_needs_replacement": bool(
            parsed.get("typography_needs_replacement") or mojibake or missing or parsed.get("missing_required")
        ),
        "notes": str(parsed.get("notes") or ""),
        "mode": "vision" if parsed else "unavailable",
        "brief_key": brief.get("key"),
    }
    return inspect, calls


def contains_mojibake(text: str) -> bool:
    raw = text or ""
    return any(marker in raw for marker in MOJIBAKE_MARKERS)


def hard_reject_reasons(
    *,
    inspect: dict[str, Any],
    architecture_qa: dict[str, Any] | None = None,
    critic: dict[str, Any] | None = None,
) -> list[str]:
    reasons: list[str] = []
    qa_status = str((architecture_qa or {}).get("architecture_integrity_status") or (architecture_qa or {}).get("status") or "")
    if qa_status == "fail" or inspect.get("architecture_changed"):
        reasons.append("architecture_changed")
    if inspect.get("fake_logo"):
        reasons.append("fake_logo")
    if inspect.get("mojibake") or any(contains_mojibake(x) for x in list(inspect.get("observed_text") or [])):
        reasons.append("malformed_turkish_text")
    if inspect.get("property_card"):
        reasons.append("obvious_property_card")
    if inspect.get("dashboard"):
        reasons.append("obvious_dashboard")
    if inspect.get("spire_collision"):
        reasons.append("text_collision_with_spire")
    if inspect.get("text_on_photo") and not inspect.get("typography_needs_replacement"):
        reasons.append("simple_text_overlay")
    if inspect.get("missing_required") and not inspect.get("typography_needs_replacement"):
        reasons.append("unreadable_or_missing_commercial_information")
    critic = critic or {}
    try:
        if float(critic.get("TEXT_ON_PHOTO_FEEL") or 0) > 6:
            reasons.append("simple_text_overlay")
    except (TypeError, ValueError):
        pass
    return sorted(set(reasons))


def composite_real_logo(
    image: Image.Image,
    *,
    logo_rgba: Image.Image | None,
    box: dict[str, Any] | None,
    cover_box: dict[str, Any] | None = None,
    foundation: Image.Image | None = None,
) -> Image.Image:
    canvas = image.convert("RGBA")
    if cover_box and foundation is not None:
        px = box_px(cover_box, canvas.size)
        if px:
            patch = foundation.convert("RGBA").crop(px)
            canvas.paste(patch, (px[0], px[1]))
    if logo_rgba is None:
        return canvas.convert("RGB")
    px = box_px(box, canvas.size)
    if not px:
        w, h = canvas.size
        px = (int(w * 0.62), int(h * 0.04), int(w * 0.94), int(h * 0.14))
    x0, y0, x1, y1 = px
    fitted = _fit_logo(logo_rgba, max(8, x1 - x0), max(8, y1 - y0))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(fitted, (x0, y0), fitted)
    return Image.alpha_composite(canvas, layer).convert("RGB")


def overlay_verified_typography(
    image: Image.Image,
    *,
    zones: dict[str, Any],
    fonts: dict[str, Any],
    facts: dict[str, str],
) -> Image.Image:
    canvas = image.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    roles = {
        "headline": ("DISPLAY_SERIF", facts["headline"], "#F4EFE4", 0),
        "unit_type": ("EDITORIAL_SANS", f"{facts['unit']} {facts['unit_label']}", "#E6E0D4", 0),
        "price": ("COMMERCIAL_NUMBER", facts["list_price"], "#F7F2E8", 0),
        "discount": ("COMMERCIAL_NUMBER", facts["discount"], "#C9A85C", 0),
        "discount_label": ("EDITORIAL_SANS", facts["discount_label"], "#E6E0D4", 80),
        "cta": ("CTA", facts["cta"], "#F4EFE4", 120),
    }
    for key, (role, text, color, tracking) in roles.items():
        px = box_px(zones.get(key), canvas.size)
        if not px:
            continue
        x0, y0, x1, y1 = px
        size = max(18, int((y1 - y0) * (0.72 if key != "headline" else 0.62)))
        if key == "headline":
            size = max(42, int((x1 - x0) * 0.11))
        if key == "price":
            size = max(36, int((x1 - x0) * 0.16))
        font = font_for_role(fonts, role, size)
        fill = _hex_rgb(color)
        # Soft local darkening behind type — not a white card.
        shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(shade).rectangle(px, fill=(12, 14, 18, 70))
        canvas = Image.alpha_composite(canvas, shade)
        draw = ImageDraw.Draw(canvas)
        _draw_tracked(draw, (x0, y0), text, font, fill, tracking)
    return canvas.convert("RGB")


def _hex_rgb(value: str) -> tuple[int, int, int]:
    raw = (value or "#FFFFFF").lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: int,
) -> None:
    x, y = origin
    if tracking <= 0:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += int(font.getlength(ch) + tracking / 1000 * float(getattr(font, "size", 32) or 32))


def build_generative_master_design_spec(
    *,
    key: str,
    brief: dict[str, Any],
    inspect: dict[str, Any],
    crop: dict[str, Any],
    architecture_mask: dict[str, Any],
    decorative_locked: bool,
    text_replaced: bool,
    logo_composited: bool,
) -> dict[str, Any]:
    zones = dict(inspect.get("zones") or brief.get("zones") or {})
    groups = []
    for role in EDITABLE_GROUPS:
        box = _box(zones.get(role))
        groups.append(
            {
                "role": role,
                "box": box,
                "editable": True,
                "mutable_for": {
                    "headline": ["COPY_EDIT_ONLY"],
                    "unit_type": ["COPY_EDIT_ONLY"],
                    "price": ["PRICE_EDIT_ONLY"],
                    "discount": ["PRICE_EDIT_ONLY", "COPY_EDIT_ONLY"],
                    "discount_label": ["COPY_EDIT_ONLY"],
                    "cta": ["COPY_EDIT_ONLY"],
                    "logo": ["LOGO_ONLY"],
                }.get(role, ["COPY_EDIT_ONLY"]),
            }
        )
    spec_id = str(uuid4())
    return {
        "schema": "GenerativeMasterDesignSpecV1",
        "spec_id": spec_id,
        "candidate_key": key,
        "canvas": {"width": 1088, "height": 1360, "aspect": "4:5"},
        "project_photo_source": "299bd265-a0ea-486d-866d-1947f103fd57",
        "exact_crop": crop,
        "photographic_treatment": brief.get("photographic_treatment"),
        "logo": {"asset_id": "7b58877e-efca-4e9a-9027-6fd18fb1b345", "composited": logo_composited, "ai_redrawn": False},
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
        "graphic_regions": [zones.get("graphic_field")] if zones.get("graphic_field") else [],
        "typography_roles": {
            "display": "Cormorant Garamond",
            "information": "Source Sans 3",
            "commercial_number": "Source Sans 3 / Cormorant Garamond",
            "cta": "Source Sans 3",
        },
        "color_roles": brief.get("typography_character"),
        "alignment": brief.get("visual_balance"),
        "spacing": brief.get("negative_space"),
        "z_order": ["project_photo", "locked_art_direction", "verified_typography", "real_logo"],
        "relationships": {
            "price_discount": "designed commercial pair",
            "headline_to_offer": brief.get("reading_hierarchy"),
        },
        "masks": {
            "architecture": {
                "schema": "ArchitectureProtectionMaskV1",
                "protected_coverage": architecture_mask.get("protected_coverage"),
                "convention": architecture_mask.get("openai_convention"),
            }
        },
        "protected_architecture": list(architecture_mask.get("protected") or []),
        "editable_commercial_groups": groups,
        "locked_decorative_art_direction_layer": decorative_locked,
        "structured_text_replaced": text_replaced,
        "reference_ids": list(brief.get("reference_ids") or []),
        "reference_applications": list(brief.get("reference_applications") or []),
    }


def revision_readiness(spec: dict[str, Any]) -> dict[str, Any]:
    groups = {item.get("role"): item for item in list(spec.get("editable_commercial_groups") or []) if isinstance(item, dict)}

    def has_box(role: str, min_w: float = 0.12, min_h: float = 0.04) -> bool:
        box = _box((groups.get(role) or {}).get("box"))
        return bool(box and box["w"] >= min_w and box["h"] >= min_h)

    price = has_box("price", 0.16, 0.045)
    copy_ok = has_box("headline", 0.18, 0.05) and has_box("cta", 0.10, 0.03)
    visual = bool(spec.get("project_photo_source")) and bool(spec.get("exact_crop"))
    checks = {
        "PRICE_EDIT_ONLY": "PASS" if price else "FAIL",
        "COPY_EDIT_ONLY": "PASS" if copy_ok else "FAIL",
        "VISUAL_REPLACE_ONLY": "PASS" if visual else "FAIL",
    }
    overall = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"
    return {
        "schema": "GenerativeRevisionReadinessV1",
        "revision_readiness": overall,
        "checks": checks,
        "executed": False,
        "note": "Readiness only. Phase 5.5 revision was not run.",
    }


def request_generative_critic(
    *,
    candidate: Image.Image,
    foundation: Image.Image,
    references: list[Image.Image],
    concept: str,
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Candidate concept: {concept}. Image 1 = candidate. Image 2 = Day_004. "
                "Later images are DESIGN_REFERENCES used as the quality bar.\n"
                "Scores 0-10: professional_art_direction, reference_quality_alignment, image_design_integration, "
                "typography, hierarchy, commercial_clarity, logo_integration, cta_integration, premium_character, "
                "originality, readability, architecture_fidelity, publishability, "
                "TEXT_ON_PHOTO_FEEL (0 integrated / 10 dumped), TEMPLATE_FEEL, UI_FEEL, CLUTTER. "
                "Also: anti_patterns (array), critique, notes, hard_reject_reasons (array)."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
    ]
    for ref in references[:4]:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(ref, quality=70)}", "detail": "low"}}
        )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1700,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Independent luxury real-estate art director. Score honestly against the references. "
                    "Do not inflate scores. JSON only."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    parsed["mode"] = "vision" if parsed.get("professional_art_direction") is not None else "unavailable"
    return parsed, calls


def critic_targets_met_54c(scores: dict[str, Any]) -> tuple[bool, list[str]]:
    def g(key: str, default: float = 0) -> float:
        try:
            return float(scores.get(key, default))
        except (TypeError, ValueError):
            return default

    reasons: list[str] = []
    mins = {
        "professional_art_direction": 8,
        "reference_quality_alignment": 7,
        "image_design_integration": 8,
        "typography": 8,
        "hierarchy": 8,
        "commercial_clarity": 8,
        "logo_integration": 7,
        "premium_character": 8,
        "architecture_fidelity": 9,
        "publishability": 8,
    }
    maxes = {"TEXT_ON_PHOTO_FEEL": 3, "TEMPLATE_FEEL": 3, "UI_FEEL": 2, "CLUTTER": 4}
    for key, minimum in mins.items():
        if g(key) < minimum:
            reasons.append(f"{key}={g(key)} < {minimum}")
    for key, maximum in maxes.items():
        if g(key, 10) > maximum:
            reasons.append(f"{key}={g(key, 10)} > {maximum}")
    return not reasons, reasons
