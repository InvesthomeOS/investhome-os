"""GraphicFieldArtDirectorV1 + ArchitectureProtectionMaskV2.

Generative pixels are applied only in allowed non-architecture regions.
The foundation never leaves the composite. No post-hoc architecture paste-back.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from investhome_api.config.settings import get_settings
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
from investhome_api.services.creative_director.project_architecture_lock import derive_architecture_mask
from investhome_api.services.gpt_image_design.client import decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
)
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

NO_TEXT = (
    "CREATE ONLY NON-TEXT GRAPHIC ART DIRECTION. "
    "NO WORDS. NO LETTERS. NO NUMBERS. NO LOGOS. NO SYMBOLIC FAKE WORDMARKS. "
    "No lorem ipsum. No fake text-like marks. No captions. No UI chrome."
)


def _box_px(box: dict[str, Any] | None, size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    if not isinstance(box, dict):
        return None
    try:
        x, y, w, h = float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
    except (KeyError, TypeError, ValueError):
        return None
    width, height = size
    x0 = max(0, int(x * width))
    y0 = max(0, int(y * height))
    x1 = min(width, int((x + w) * width))
    y1 = min(height, int((y + h) * height))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(image: Image.Image, quality: int = 82) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def architecture_protection_mask_v2(
    foundation: Image.Image,
    protection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Protect complete architecture. OpenAI: transparent=edit, opaque=preserve."""
    src = foundation.convert("RGB")
    protect = derive_architecture_mask(src).convert("L")
    draw = ImageDraw.Draw(protect)
    for box in dict((protection or {}).get("regions") or {}).values():
        px = _box_px(box, src.size)
        if px:
            draw.rectangle(px, fill=255)
    # Over-preserve edges. Architecture must never leave the foundation.
    protect = protect.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MaxFilter(7))
    protect = protect.point(lambda v: 255 if v > 32 else 0)
    white = Image.new("RGBA", src.size, (255, 255, 255, 255))
    mask_rgba = Image.composite(white, Image.new("RGBA", src.size, (0, 0, 0, 0)), protect)
    hist = protect.histogram()
    coverage = sum(hist[33:]) / float(src.width * src.height)
    overlay = src.convert("RGBA")
    red = Image.new("RGBA", src.size, (200, 40, 40, 88))
    overlay = Image.composite(Image.alpha_composite(overlay, red), overlay, protect)
    return {
        "schema": "ArchitectureProtectionMaskV2",
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
        "editable": ("sky", "non-architectural graphic regions", "tonal fields outside the building"),
        "protected_coverage": round(coverage, 4),
        "size": list(src.size),
        "mask_l": protect,
        "mask_rgba": mask_rgba,
        "visualization": overlay.convert("RGB"),
        "openai_convention": "transparent=edit opaque=preserve",
        "composite_rule": "generated_pixels_only_where_protect_is_0",
    }


def openai_mask_png(mask: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    mask["mask_rgba"].save(buf, format="PNG")
    return buf.getvalue()


def apply_graphic_field_to_foundation(
    foundation: Image.Image,
    generated: Image.Image,
    protect_l: Image.Image,
) -> Image.Image:
    """Foundation stays. Generated treatment only in editable (protect=0) pixels."""
    base = foundation.convert("RGB")
    gen = generated.convert("RGB")
    if gen.size != base.size:
        gen = gen.resize(base.size, Image.Resampling.LANCZOS)
    protect = protect_l.convert("L")
    if protect.size != base.size:
        protect = protect.resize(base.size, Image.Resampling.NEAREST)
    core = protect.point(lambda v: 255 if v > 32 else 0)
    edit = core.point(lambda v: 0 if v > 32 else 255).filter(ImageFilter.GaussianBlur(radius=1.4))
    blended = Image.composite(gen, base, edit)
    return Image.composite(base, blended, core)


def protected_pixels_unchanged(foundation: Image.Image, result: Image.Image, protect_l: Image.Image) -> bool:
    base = foundation.convert("RGB")
    out = result.convert("RGB")
    if base.size != out.size:
        return False
    protect = protect_l.convert("L").resize(base.size, Image.Resampling.NEAREST)
    bp, op, pp = base.load(), out.load(), protect.load()
    w, h = base.size
    checked = 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            if int(pp[x, y]) < 200:
                continue
            checked += 1
            if bp[x, y] != op[x, y]:
                return False
    return checked > 40


def request_graphic_field_plan(
    *,
    foundation: Image.Image,
    protection_preview: Image.Image,
    systems: dict[str, Any],
    references: list[Image.Image],
    direction: dict[str, str],
) -> tuple[dict[str, Any], int]:
    primary = dict(systems.get("primary") or {})
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Image 1 is the locked Temple Day_004 4:5 foundation. NO TEXT on it. "
                "Image 2 is the architecture protection map (red = immutable building). "
                "Later images are Grade A references for FIELD LANGUAGE only. Do not copy their buildings or logos.\n"
                f"CONCEPT {direction.get('key')} {direction.get('concept')}: {direction.get('intent')}\n"
                f"Primary system {primary.get('system_id')}: "
                f"{json.dumps({k: primary.get(k) for k in ('canvas_system','graphic_field_system','color_system','alignment_system','image_system')}, ensure_ascii=True)[:3500]}\n"
                "Design NON-TEXT graphic fields only: tonal fields, gradients, masks, atmosphere, "
                "negative-space creation, restrained accent without letters.\n"
                "Forbidden: words, numbers, logos, white cards, listing panels, pills, badges, KPI tiles, "
                "web buttons, architecture regeneration.\n"
                "JSON GraphicFieldArtDirectionV1: field_placement, gradient, accent, architecture_interaction, "
                "semantic_regions {headline,unit_type,price,discount,cta,logo as {x,y,w,h}}, "
                "why_type_will_sit_in_the_field, why_this_is_not_a_card."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(protection_preview)}", "detail": "low"}},
    ]
    for ref in references[:3]:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(ref, quality=72)}", "detail": "high"}}
        )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.3,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Graphic-field art director. You design NON-TEXT environments for typography. "
                    "You do not write words. JSON only."
                ),
            },
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    regions = dict(parsed.get("semantic_regions") or parsed.get("regions") or {})
    plan = {
        "schema": "GraphicFieldArtDirectionV1",
        "plan_id": str(uuid4()),
        "key": direction.get("key"),
        "concept": direction.get("concept"),
        "field_placement": str(parsed.get("field_placement") or primary.get("graphic_field_system")),
        "gradient": str(parsed.get("gradient") or ""),
        "accent": str(parsed.get("accent") or "restrained gold, no letters"),
        "architecture_interaction": str(parsed.get("architecture_interaction") or "do not paint the building"),
        "semantic_regions": regions,
        "why_type_will_sit_in_the_field": str(parsed.get("why_type_will_sit_in_the_field") or ""),
        "why_this_is_not_a_card": str(parsed.get("why_this_is_not_a_card") or ""),
        "system_id": primary.get("system_id"),
        "mode": "vision" if parsed else "seed",
    }
    return plan, calls


def build_graphic_field_prompt(plan: dict[str, Any], systems: dict[str, Any], direction: dict[str, str]) -> str:
    primary = dict(systems.get("primary") or {})
    field = primary.get("graphic_field_system") or {}
    color = primary.get("color_system") or {}
    return (
        f"{NO_TEXT}\n"
        "IMAGE 1 is the exact Temple photograph crop. It is architectural ground truth. "
        "Do not regenerate, beautify, or complete the building, spire, façade, windows, or roof. "
        "Additional images are Grade A references for tonal/field language only.\n"
        f"CONCEPT {direction.get('key')} {direction.get('concept')}: {direction.get('intent')}\n"
        f"System {primary.get('system_id')}. Field: {json.dumps(field, ensure_ascii=True)[:900]}\n"
        f"Color field {color.get('dominant_field')} accent {color.get('accent_color')}.\n"
        f"Plan: {plan.get('field_placement')} | {plan.get('gradient')} | {plan.get('accent')}\n"
        "Paint graphic treatment ONLY in sky and non-architectural regions indicated by the mask. "
        "Leave protected architecture pixels unchanged.\n"
        "No white information rectangle. No listing panel. No property card. No dashboard. "
        "No gold medallion. No ribbon. No web button.\n"
        "The result must look like an advertising foundation BEFORE typography."
    )


def generate_graphic_field(
    *,
    foundation: Image.Image,
    mask: dict[str, Any],
    references: list[Image.Image],
    prompt: str,
    quality: str = "high",
) -> tuple[Image.Image, dict[str, Any]]:
    avail = provider_availability()
    if not avail.available:
        raise RuntimeError(f"GPT Image unavailable: {avail.reason}")
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    images: list[tuple[bytes, str, str]] = [(_png_bytes(foundation), "temple-foundation.png", "image/png")]
    for idx, ref in enumerate(references[:3]):
        images.append((_jpeg_bytes(ref), f"grade-a-{idx + 1}.jpg", "image/jpeg"))
    remote = edit_image(
        api_key=openai_api_key(),
        model=model,
        prompt=prompt,
        images=images,
        size="1088x1360",
        quality=quality,
        base_url=resolve_base_url(settings),
        variant="phase5_4e_graphic_field",
        mask=openai_mask_png(mask),
    )
    generated = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
    applied = apply_graphic_field_to_foundation(foundation, generated, mask["mask_l"])
    return applied, {
        "model": model,
        "quality": quality,
        "size": "1088x1360",
        "input_images": len(images),
        "architecture_pixels_from": "immutable_foundation",
        "composite": "generated_only_in_editable_mask",
    }


def inspect_field_has_text(field: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Detect any letters, numbers, logos, or fake wordmarks. JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "JSON: {has_text:boolean, has_logo:boolean, has_numbers:boolean, notes}",
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(field)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    return {
        "has_text": bool(parsed.get("has_text") or parsed.get("has_numbers") or parsed.get("has_logo")),
        "has_logo": bool(parsed.get("has_logo")),
        "has_numbers": bool(parsed.get("has_numbers")),
        "notes": str(parsed.get("notes") or ""),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def region_luma(image: Image.Image, box: dict[str, Any] | None) -> float:
    px = _box_px(box, image.size)
    if not px:
        return float(ImageStat.Stat(image.convert("L")).mean[0])
    crop = image.convert("L").crop(px)
    return float(ImageStat.Stat(crop).mean[0])


def run_graphic_field_pass(
    *,
    foundation: Image.Image,
    mask: dict[str, Any],
    references: list[Image.Image],
    prompt: str,
    quality: str = "high",
    max_retries: int = 2,
) -> tuple[Image.Image, dict[str, Any], dict[str, Any], int]:
    """Generate a non-text field; retry if letters/logos appear. Composite onto foundation."""
    vision = 0
    applied = foundation.convert("RGB")
    gen_meta: dict[str, Any] = {}
    inspect: dict[str, Any] = {"has_text": False, "mode": "skipped"}
    working_prompt = prompt
    for attempt in range(max_retries + 1):
        applied, gen_meta = generate_graphic_field(
            foundation=foundation,
            mask=mask,
            references=references,
            prompt=working_prompt,
            quality=quality,
        )
        gen_meta["attempt"] = attempt + 1
        inspect, calls = inspect_field_has_text(applied)
        vision += calls
        if not inspect.get("has_text"):
            break
        working_prompt = (
            prompt
            + "\nThe previous attempt contained letters, numbers, or a fake wordmark. "
            "Paint ONLY tonal fields, gradients, and atmosphere. Zero glyphs. Zero logos."
        )
    gen_meta["field_text_inspect"] = inspect
    gen_meta["protected_pixels_unchanged"] = protected_pixels_unchanged(
        foundation, applied, mask["mask_l"]
    )
    return applied, gen_meta, inspect, vision


def inspect_final_candidate(
    *,
    candidate: Image.Image,
    foundation: Image.Image,
    graphic_field: Image.Image,
    required: list[str],
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
                    "Inspect the FINAL compositor advertisement, not the graphic field alone. "
                    "JSON only. Be literal. Do not inflate quality."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 is the FINAL compositor output. Image 2 is the locked Day_004 foundation. "
                            "Image 3 is the non-text graphic field before type.\n"
                            "Required exact strings: " + " | ".join(required) + "\n"
                            "JSON: observed_text, missing_required, mojibake, fake_logo, architecture_changed, "
                            "spire_collision, property_card, dashboard, kpi_layout, generic_web_cta, "
                            "unreadable_commercial, pasted_typography, field_and_type_one_composition, notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(graphic_field, quality=70)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    observed = [str(x) for x in list(parsed.get("observed_text") or [])]
    return {
        "schema": "GraphicFieldFinalInspectV1",
        "observed_text": observed,
        "missing_required": list(parsed.get("missing_required") or []),
        "mojibake": bool(parsed.get("mojibake")),
        "fake_logo": bool(parsed.get("fake_logo")),
        "architecture_changed": bool(parsed.get("architecture_changed")),
        "spire_collision": bool(parsed.get("spire_collision")),
        "property_card": bool(parsed.get("property_card")),
        "dashboard": bool(parsed.get("dashboard")),
        "kpi_layout": bool(parsed.get("kpi_layout")),
        "generic_web_cta": bool(parsed.get("generic_web_cta")),
        "unreadable_commercial": bool(parsed.get("unreadable_commercial")),
        "pasted_typography": bool(parsed.get("pasted_typography")),
        "field_and_type_one_composition": parsed.get("field_and_type_one_composition", True),
        "notes": str(parsed.get("notes") or ""),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def request_graphic_field_critic(
    *,
    candidate: Image.Image,
    foundation: Image.Image,
    references: list[Image.Image],
    concept: str,
    system_id: str,
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"FINAL compositor candidate {concept}. Executable system {system_id}. "
                "Image 1 = final ad (type+logo by OS compositor). Image 2 = Day_004 foundation. "
                "Later images are Grade A references that supplied the executable system.\n"
                "Score 0-10 honestly, do not inflate: professional_art_direction, "
                "reference_system_fidelity, composition, image_design_integration, typography, "
                "hierarchy, commercial_clarity, logo_integration, cta_integration, premium_character, "
                "readability, architecture_fidelity, publishability.\n"
                "Also: anti_patterns (array), critique, notes, hard_reject_reasons (array)."
            ),
        },
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
    ]
    for ref in references[:3]:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(ref, quality=68)}", "detail": "low"}}
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
                    "Independent luxury real-estate art director. Score the FINAL compositor output. "
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


def critic_targets_met_54e(scores: dict[str, Any]) -> tuple[bool, list[str]]:
    def g(key: str, default: float = 0) -> float:
        try:
            return float(scores.get(key, default))
        except (TypeError, ValueError):
            return default

    reasons: list[str] = []
    mins = {
        "professional_art_direction": 8,
        "reference_system_fidelity": 8,
        "composition": 8,
        "image_design_integration": 8,
        "typography": 8,
        "hierarchy": 8,
        "commercial_clarity": 8,
        "logo_integration": 8,
        "premium_character": 8,
        "architecture_fidelity": 9,
        "publishability": 8,
    }
    for key, minimum in mins.items():
        if g(key) < minimum:
            reasons.append(f"{key}={g(key)} < {minimum}")
    return not reasons, reasons


def hard_reject_54e(*, inspect: dict[str, Any], architecture_qa: dict[str, Any] | None = None) -> list[str]:
    reasons: list[str] = []
    qa_status = str((architecture_qa or {}).get("architecture_integrity_status") or (architecture_qa or {}).get("status") or "")
    if qa_status == "fail" or inspect.get("architecture_changed"):
        reasons.append("architecture_changed")
    if inspect.get("mojibake"):
        reasons.append("malformed_turkish_text")
    if inspect.get("fake_logo"):
        reasons.append("fake_logo")
    if inspect.get("spire_collision"):
        reasons.append("text_collision_with_spire")
    if inspect.get("property_card"):
        reasons.append("property_card")
    if inspect.get("dashboard") or inspect.get("kpi_layout"):
        reasons.append("dashboard_kpi_layout")
    if inspect.get("generic_web_cta"):
        reasons.append("generic_web_cta")
    if inspect.get("unreadable_commercial") or inspect.get("missing_required"):
        reasons.append("unreadable_commercial_information")
    if inspect.get("pasted_typography"):
        reasons.append("typography_independently_pasted")
    if inspect.get("field_and_type_one_composition") is False:
        reasons.append("graphic_field_and_typography_not_one_composition")
    return sorted(set(reasons))
