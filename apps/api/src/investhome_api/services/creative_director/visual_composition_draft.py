"""VisualCompositionDraftV1 — disposable design guide, not the production asset.

GPT Image may paint the draft only. Production reconstruction uses real Day_007,
the real Temple logo, and GraphicDesignCompositorV3.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw

from investhome_api.config.settings import get_settings
from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.gpt_image_design.client import (
    GptImageProviderError,
    decode_remote_image,
    edit_image,
)
from investhome_api.services.gpt_image_design.compose import _fit_logo
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
)
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

VERTICAL_HARMONY = {
    "schema": "ArtDirectionBlueprintV1",
    "id": "AD1",
    "blueprint_id": "4a23730a-adda-4064-a6df-35b331df723b",
    "concept_name": "Vertical Harmony",
    "one_sentence_idea": (
        "Create a vertical visual harmony around the Temple spire while maintaining "
        "architecture as hero and integrating the commercial story into one premium campaign composition."
    ),
    "visual_axis": "Vertical alignment from spire to campaign lockup.",
    "photo_role": "Full-frame architectural hero. The spire is the visual center.",
    "headline_role": "Large display mass in vertical conversation with the spire, not a corner caption.",
    "commercial_offer_role": "One commercial group subordinate to the display, sharing the same vertical axis.",
    "logo_role": "Brand signature that closes the vertical composition, not a tiny mark colliding with the spire.",
    "cta_role": "Quiet inscription sharing the same alignment system.",
    "tonal_treatment": "Photographic edge atmosphere only. No card, panel, or UI field.",
    "typographic_character": "Tall slender editorial serif. Gold last line of the headline.",
    "gold_usage": "Headline accent and commercial number, not decoration.",
    "negative_space_strategy": "The unused photograph is composed breathing room, not leftover empty canvas.",
    "image_design_integration_strategy": "Type and architecture share one vertical rhythm.",
    "reading_order": ["headline", "discount", "price", "logo", "unit", "cta"],
    "group_relationships": "Display, commercial offer, brand, and CTA are one campaign column.",
    "intended_visual_tension": "Typography mass balanced against the spire, not parked in leftover sky.",
    "why_it_fits_day_007": "The spire already supplies a vertical axis. Design should converse with it.",
    "borrowed_reference_craft": "Grade-A editorial scale, alignment, and designed negative space.",
    "deliberately_not_copied": "No 5.5A tiny upper-left information stack. No listing rows. No pixel copy of a reference.",
}

DRAFT_POSITIVE = (
    "professional_art_direction",
    "whole_canvas_composition",
    "image_design_integration",
    "typography_mass",
    "hierarchy",
    "commercial_storytelling",
    "brand_relationship",
    "cta_relationship",
    "premium_character",
    "reference_craft_transfer",
)
DRAFT_BAD = ("TEXT_DUMP_FEEL", "LISTING_FEEL", "UI_FEEL", "TEMPLATE_FEEL", "CORNER_CLUSTER_FEEL")
DRAFT_BAD_MAX = {
    "TEXT_DUMP_FEEL": 2,
    "LISTING_FEEL": 2,
    "UI_FEEL": 2,
    "TEMPLATE_FEEL": 3,
    "CORNER_CLUSTER_FEEL": 2,
}

FIDELITY_KEYS = (
    "overall_visual_mass",
    "headline_scale",
    "headline_position",
    "commercial_scale",
    "commercial_position",
    "logo_relationship",
    "CTA_relationship",
    "spacing_rhythm",
    "tonal_treatment",
    "whole_canvas_balance",
    "hierarchy",
    "visual_tension",
)

FINAL_POSITIVE = (
    "professional_art_direction",
    "reference_craft_transfer",
    "visual_draft_fidelity",
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
    "CORNER_CLUSTER_FEEL",
    "CLUTTER",
)

EXTRACT_ROLES = ("headline", "discount", "discount_label", "price", "unit_type", "project_logo", "cta", "tonal_treatment")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _box(raw: Any) -> dict[str, float]:
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    return {
        "x": round(max(0.0, min(1.0, _num(data.get("x")))), 4),
        "y": round(max(0.0, min(1.0, _num(data.get("y")))), 4),
        "w": round(max(0.0, min(1.0, _num(data.get("w") or data.get("width")))), 4),
        "h": round(max(0.0, min(1.0, _num(data.get("h") or data.get("height")))), 4),
    }


def _jpeg_b64(image: Image.Image, quality: int = 78) -> str:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    import base64

    return base64.b64encode(buf.getvalue()).decode("ascii")


def _img(image: Image.Image, *, quality: int = 78) -> dict[str, Any]:
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(image, quality)}", "detail": "high"},
    }


def _text(text: str) -> dict[str, str]:
    return {"type": "text", "text": text}


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(image: Image.Image, quality: int = 78) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def draft_prompt(blueprint: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Create ONE 4:5 visual art-direction MOCKUP for a premium real-estate campaign.",
            "This is a DESIGN GUIDE for a compositor. It will never be published.",
            "Photograph is the provided Temple exterior (Day_007). Architecture is the hero.",
            "CONCEPT: Vertical Harmony. "
            + str(blueprint.get("one_sentence_idea") or ""),
            "Communicate this content as visual mass (spelling may be imperfect):",
            "ALIRKEN KAZAN / %35 LANSMAN AVANTAJI / 675.000 USD / THE TEMPLE / 2+1 DAİRE / PROJEYİ KEŞFET.",
            "1-second reading: ALIRKEN KAZAN → %35 LANSMAN AVANTAJI → 675.000 USD → THE TEMPLE, then unit and CTA.",
            "The WHOLE 4:5 frame must feel art-directed. The photo may dominate, but type mass, rhythm,",
            "tonal treatment and negative space must compose the entire canvas.",
            "REJECT: tiny upper-left information stack; brochure list; six independent text rows;",
            "tiny logo colliding with the spire; isolated CTA; giant unused photograph with design in one corner;",
            "photo+text overlay feel; listing layout; UI cards, pills, badges, medallions.",
            "Do not imitate a reference pixel-for-pixel. Borrow craft: scale, axis, tension, designed space.",
            "Navy/ivory/restrained gold. Editorial serif display. No extra marketing copy.",
        ]
    )


def _contact_sheet(references: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1536, 1024), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)
    x, y = 12, 12
    for name, image in references[:6]:
        thumb = image.copy()
        thumb.thumbnail((480, 480), Image.Resampling.LANCZOS)
        canvas.paste(thumb.convert("RGB"), (x, y))
        draw.text((x, y + thumb.size[1] + 4), name, font=_font(14), fill=(220, 216, 208))
        x += 510
        if x > 1100:
            x = 12
            y += 510
    return canvas


def generate_visual_composition_draft(
    *,
    day007: Image.Image,
    references: list[tuple[str, Image.Image]],
    blueprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blueprint = blueprint or VERTICAL_HARMONY
    avail = provider_availability()
    if not avail.available:
        return {"schema": "VisualCompositionDraftV1", "ok": False, "reason": avail.reason, "image_calls": 0}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    full_inputs: list[tuple[bytes, str, str]] = [(_png_bytes(day007), "day007.png", "image/png")]
    for name, image in references:
        full_inputs.append((_jpeg_bytes(image, 70), name, "image/jpeg"))
    sheet_inputs: list[tuple[bytes, str, str]] = [
        (_png_bytes(day007), "day007.png", "image/png"),
        (_jpeg_bytes(_contact_sheet(references), 78), "grade-a-contact-sheet.jpg", "image/jpeg"),
    ]
    attempts: list[tuple[list[tuple[bytes, str, str]], str]] = [
        (full_inputs, "1088x1360"),
        (full_inputs, "1024x1536"),
        (sheet_inputs, "1088x1360"),
    ]
    last_error = "draft generation failed"
    calls = 0
    for images, size in attempts:
        try:
            remote = edit_image(
                api_key=openai_api_key(),
                model=model,
                prompt=draft_prompt(blueprint),
                images=images,
                size=size,
                quality="high",
                base_url=resolve_base_url(settings),
                variant="phase5_5b_visual_composition_draft",
                timeout=300.0,
            )
            calls += 1
            draft = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
            if draft.size != (1088, 1360):
                draft = draft.resize((1088, 1360), Image.Resampling.LANCZOS)
            return {
                "schema": "VisualCompositionDraftV1",
                "ok": True,
                "image": draft,
                "disposable": True,
                "not_production": True,
                "architecture_untrusted": True,
                "logo_untrusted": True,
                "typography_untrusted": True,
                "image_calls": calls,
                "input_images": len(images),
                "requested_size": size,
                "model": model,
                "blueprint_id": blueprint.get("blueprint_id"),
                "concept_name": blueprint.get("concept_name"),
            }
        except GptImageProviderError as exc:
            calls += 1
            last_error = str(exc.detail)[:240]
    return {
        "schema": "VisualCompositionDraftV1",
        "ok": False,
        "reason": last_error,
        "image_calls": calls,
    }


def draft_critic_pass(scores: dict[str, Any]) -> bool:
    if not scores:
        return False
    if any(_num(scores.get(key)) < 8 for key in DRAFT_POSITIVE):
        return False
    for key, ceiling in DRAFT_BAD_MAX.items():
        if _num(scores.get(key), 10) > ceiling:
            return False
    return True


def request_draft_critic(
    draft: Image.Image,
    day007: Image.Image,
    references: list[tuple[str, Image.Image]],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Critique this VISUAL COMPOSITION DRAFT as a design guide, not a production ad. "
            "Ignore spelling. Score 0-10: "
            + ", ".join(DRAFT_POSITIVE)
            + ". Undesirable: "
            + ", ".join(DRAFT_BAD)
            + ". Gate: positives>=8, TEXT_DUMP<=2 LISTING<=2 UI<=2 TEMPLATE<=3 CORNER_CLUSTER<=2. "
            "Reject tiny upper-left stacks and unused giant photographs. JSON only."
        ),
        _text("DRAFT"),
        _img(draft, quality=82),
        _text("Day_007 source crop"),
        _img(day007, quality=62),
    ]
    for name, image in references[:3]:
        content.append(_text(f"Grade-A reference {name}"))
        content.append(_img(image, quality=58))
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Honest art director. JSON only. Do not inflate."},
            {"role": "user", "content": content},
        ],
    }
    parsed, calls = _vision(payload)
    scores = flatten_critic(parsed if isinstance(parsed, dict) else {})
    nested = scores.get("undesirable")
    if isinstance(nested, dict):
        for key in DRAFT_BAD:
            if nested.get(key) is not None:
                scores[key] = nested.get(key)
    scores["pass"] = draft_critic_pass(scores)
    scores["schema"] = "VisualDraftCriticV1"
    return scores, calls


def extract_visual_structure(draft: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "VisualDraftStructureExtractorV1. Measure the DRAFT pixels. JSON only. Normalized 0-1 boxes.",
            },
            {
                "role": "user",
                "content": [
                    _text(
                        "Extract visual structure from this composition draft. Ignore spelling. "
                        "Return boxes {x,y,w,h} for headline, discount, discount_label, price, unit_type, "
                        "project_logo, cta, tonal_treatment. Also: alignment_side left|right, vertical_axis_x, "
                        "headline_scale_ratio, discount_scale_ratio, price_scale_ratio, logo_relationship, "
                        "cta_relationship, visual_center {x,y}, group_distances, rule_geometry, "
                        "negative_space_distribution, mass_distribution, image_design_boundary."
                    ),
                    _img(draft, quality=84),
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    boxes = {}
    source = parsed.get("boxes") if isinstance(parsed.get("boxes"), dict) else parsed
    for role in EXTRACT_ROLES:
        boxes[role] = _box((source or {}).get(role) if isinstance(source, dict) else {})
    ok = float(boxes.get("headline", {}).get("w") or 0) >= 0.12 and float(boxes.get("headline", {}).get("h") or 0) >= 0.04
    return {
        "schema": "VisualDraftStructureExtractorV1",
        "boxes": boxes,
        "alignment_side": str((parsed or {}).get("alignment_side") or "left").lower(),
        "vertical_axis_x": _num((parsed or {}).get("vertical_axis_x"), 0.08),
        "headline_scale_ratio": _num((parsed or {}).get("headline_scale_ratio"), boxes["headline"]["h"]),
        "discount_scale_ratio": _num((parsed or {}).get("discount_scale_ratio"), boxes["discount"]["h"]),
        "price_scale_ratio": _num((parsed or {}).get("price_scale_ratio"), boxes["price"]["h"]),
        "logo_relationship": str((parsed or {}).get("logo_relationship") or ""),
        "cta_relationship": str((parsed or {}).get("cta_relationship") or ""),
        "visual_center": dict((parsed or {}).get("visual_center") or {}),
        "group_distances": (parsed or {}).get("group_distances"),
        "rule_geometry": (parsed or {}).get("rule_geometry"),
        "negative_space_distribution": str((parsed or {}).get("negative_space_distribution") or ""),
        "mass_distribution": str((parsed or {}).get("mass_distribution") or ""),
        "image_design_boundary": str((parsed or {}).get("image_design_boundary") or ""),
        "pass": ok,
        "mode": "vision" if parsed else "unavailable",
    }, calls


def reconstruction_spec_from_structure(structure: dict[str, Any], *, canvas: tuple[int, int] = (1088, 1360)) -> dict[str, Any]:
    boxes = dict(structure.get("boxes") or {})
    headline = boxes.get("headline") or {}
    discount = boxes.get("discount") or {}
    price = boxes.get("price") or {}
    logo = boxes.get("project_logo") or {}
    cta = boxes.get("cta") or {}
    side = str(structure.get("alignment_side") or "left")
    if side not in {"left", "right"}:
        side = "left" if _num(headline.get("x"), 0.1) < 0.45 else "right"
    inset = _num(headline.get("x"), 0.055) if side == "left" else max(0.04, 1.0 - (_num(headline.get("x")) + _num(headline.get("w"), 0.3)))
    inset = min(0.12, max(0.035, inset))
    anchor_y = min(0.08, max(0.018, _num(headline.get("y"), 0.03)))
    bottoms = [
        _num(headline.get("y")) + _num(headline.get("h")),
        _num(discount.get("y")) + _num(discount.get("h")),
        _num(price.get("y")) + _num(price.get("h")),
        _num(cta.get("y")) + _num(cta.get("h")),
    ]
    type_limit_y = min(0.42, max(0.18, max(bottoms) + 0.012))
    display_scale = min(0.10, max(0.046, _num(headline.get("h"), 0.08) / 2.15))
    discount_scale = min(0.07, max(0.028, _num(discount.get("h"), 0.04)))
    number_scale = min(0.07, max(0.030, _num(price.get("h"), 0.04)))
    logo_y = _num(logo.get("y"))
    headline_y = _num(headline.get("y"))
    placement = "inward_signature" if abs(logo_y - headline_y) < 0.10 else "column_end"
    objects = {
        "project_photo": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "role": "full_frame_hero", "source": "REAL_DAY_007"},
        "headline": headline,
        "discount": discount,
        "discount_label": boxes.get("discount_label") or {},
        "price": price,
        "unit_type": boxes.get("unit_type") or {},
        "project_logo": {**logo, "placement": placement, "source": "REAL_TEMPLE_LOGO"},
        "cta": cta,
        "graphic_devices": {"kind": "hairline"},
        "tonal_treatment": boxes.get("tonal_treatment") or {"kind": "photographic_field"},
    }
    art_plan = {
        "schema": "StructuredArtDirectionPlanV1",
        "source": "VisualDraftStructureExtractorV1",
        "alignment": side,
        "lockup_side": side,
        "scale": 1.0,
        "anchor": {"inset": round(inset, 4), "y": round(anchor_y, 4)},
        "territories": {"type_limit_y": round(type_limit_y, 4)},
        "typography": {
            "display_scale": round(display_scale, 4),
            "discount_scale": round(discount_scale, 4),
            "number_scale": round(number_scale, 4),
            "label_scale": 0.011,
            "unit_scale": 0.010,
            "cta_scale": min(0.018, max(0.012, _num(cta.get("h"), 0.016))),
        },
        "logo": {
            "placement": placement,
            "w": min(0.22, max(0.10, _num(logo.get("w"), 0.14))),
            "h": min(0.10, max(0.04, _num(logo.get("h"), 0.055))),
        },
    }
    return {
        "schema": "VisualReconstructionSpecV1",
        "spec_id": str(uuid4()),
        "concept_name": "Vertical Harmony",
        "geometry_source": "visual_composition_draft",
        "canvas": {"w": canvas[0], "h": canvas[1]},
        "objects": objects,
        "relationships": {
            "visual_axis": structure.get("vertical_axis_x"),
            "logo_relationship": structure.get("logo_relationship"),
            "cta_relationship": structure.get("cta_relationship"),
            "alignment": side,
        },
        "art_plan": art_plan,
        "real_photo": True,
        "real_logo": True,
        "production_typography": True,
    }


def visible_logo_alpha_box(logo_rgba: Image.Image, paste: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = (int(v) for v in paste)
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    fitted = _fit_logo(logo_rgba.convert("RGBA"), bw, bh)
    alpha = fitted.getchannel("A")
    mask = alpha.point(lambda a: 255 if a > 24 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return (x0, y0, x1, y1)
    return (x0 + bbox[0], y0 + bbox[1], x0 + bbox[2], y0 + bbox[3])


def visible_logo_clearance(
    *,
    logo_rgba: Image.Image,
    paste: tuple[int, int, int, int],
    occupancy: dict[str, Any],
    canvas: tuple[int, int],
    min_gap: int | None = None,
) -> dict[str, Any]:
    w, _h = canvas
    gap = int(min_gap if min_gap is not None else max(18, w * 0.028))
    tight = visible_logo_alpha_box(logo_rgba, paste)
    inflated = (tight[0] - gap, tight[1] - gap, tight[2] + gap, tight[3] + gap)
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    hits = bool(isinstance(hard, Image.Image) and box_hits_hard(hard, inflated, min_pixels=8))
    return {
        "schema": "VisibleLogoClearanceV1",
        "pass": not hits,
        "tight_px": list(tight),
        "inflated_px": list(inflated),
        "gap_px": gap,
        "uses_alpha_bounds": True,
    }


def reconstruction_fidelity_pass(scores: dict[str, Any]) -> bool:
    return bool(scores) and all(_num(scores.get(key)) >= 8 for key in FIDELITY_KEYS)


def request_reconstruction_fidelity(draft: Image.Image, reconstruction: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1100,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "VisualReconstructionFidelityV1. Ignore AI spelling and architecture pixel differences. JSON 0-10.",
            },
            {
                "role": "user",
                "content": [
                    _text(
                        "Compare DRAFT (image 1) vs STRUCTURED RECONSTRUCTION (image 2). "
                        "Ignore misspellings and whether the building pixels match. Compare composition: "
                        + ", ".join(FIDELITY_KEYS)
                        + ". Require >=8 each."
                    ),
                    _text("DRAFT"),
                    _img(draft, quality=80),
                    _text("RECONSTRUCTION"),
                    _img(reconstruction, quality=80),
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    nested = parsed.get("scores") if isinstance((parsed or {}).get("scores"), dict) else parsed
    scores = {key: _num((nested or {}).get(key)) for key in FIDELITY_KEYS}
    return {
        "schema": "VisualReconstructionFidelityV1",
        "scores": scores,
        "pass": reconstruction_fidelity_pass(scores),
        "mode": "vision" if parsed else "unavailable",
    }, calls


def request_final_critic(
    candidate: Image.Image,
    draft: Image.Image,
    day007: Image.Image,
    references: list[tuple[str, Image.Image]],
) -> tuple[dict[str, Any], int]:
    content: list[dict[str, Any]] = [
        _text(
            "Final critic for Phase 5.5B production reconstruction. Do not inflate. "
            "Ignore draft spelling. Architecture must remain Day_007. Scores: "
            + ", ".join(FINAL_POSITIVE)
            + ". Undesirable: "
            + ", ".join(FINAL_BAD)
        ),
        _text("CANDIDATE"),
        _img(candidate, quality=82),
        _text("VISUAL DRAFT"),
        _img(draft, quality=70),
        _text("DAY_007"),
        _img(day007, quality=62),
    ]
    for name, image in references[:2]:
        content.append(_text(f"Grade-A {name}"))
        content.append(_img(image, quality=56))
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.0,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Honest senior critic. JSON only."},
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


def _board(title: str, rows: list[str], size: tuple[int, int] = (1600, 1400)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), title, font=_font(24), fill=(232, 214, 170))
    y = 80
    for row in rows:
        for line in _wrap(str(row), 92):
            if y > size[1] - 48:
                return image
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 6
    return image


def render_input_board(day007: Image.Image, logo: Image.Image, references: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1880, 1260), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "01  INPUTS  —  Vertical Harmony  —  Day_007 + real logo + Grade-A pixels", font=_font(22), fill=(232, 214, 170))
    tile = day007.copy()
    tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 70))
    mark = logo.copy()
    mark.thumbnail((240, 140), Image.Resampling.LANCZOS)
    canvas.paste(mark.convert("RGB"), (36, 780))
    x, y = 580, 70
    for name, image in references:
        thumb = image.copy()
        thumb.thumbnail((200, 250), Image.Resampling.LANCZOS)
        canvas.paste(thumb.convert("RGB"), (x, y))
        draw.text((x, y + thumb.size[1] + 4), name, font=_font(12), fill=(180, 176, 168))
        x += 220
        if x > 1700:
            x = 580
            y += 300
    return canvas


def render_draft_vs(draft: Image.Image, reconstruction: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1600, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "07  DRAFT vs STRUCTURED RECONSTRUCTION  —  draft is not production", font=_font(18), fill=(201, 168, 92))
    a = draft.copy()
    a.thumbnail((720, 900), Image.Resampling.LANCZOS)
    b = reconstruction.copy()
    b.thumbnail((720, 900), Image.Resampling.LANCZOS)
    canvas.paste(a.convert("RGB"), (36, 56))
    canvas.paste(b.convert("RGB"), (820, 56))
    draw.text((36, 940), "DRAFT  disposable", font=_font(14), fill=(180, 176, 168))
    draw.text((820, 940), "RECONSTRUCTION  real photo + real logo + production type", font=_font(14), fill=(180, 176, 168))
    return canvas


def render_extraction_board(structure: dict[str, Any]) -> Image.Image:
    rows = [
        f"pass={structure.get('pass')} side={structure.get('alignment_side')} axis_x={structure.get('vertical_axis_x')}",
        f"logo_rel={structure.get('logo_relationship')}",
        f"cta_rel={structure.get('cta_relationship')}",
        json.dumps(structure.get("boxes"), ensure_ascii=False),
        str(structure.get("mass_distribution") or ""),
        str(structure.get("image_design_boundary") or ""),
    ]
    return _board("04  VisualDraftStructureExtractorV1", rows)


def render_spec_board(spec: dict[str, Any]) -> Image.Image:
    rows = [
        spec.get("concept_name"),
        f"geometry_source={spec.get('geometry_source')}",
        json.dumps(spec.get("art_plan"), ensure_ascii=False),
        json.dumps(spec.get("relationships"), ensure_ascii=False),
    ]
    return _board("05  VisualReconstructionSpecV1", rows, (1600, 1200))
