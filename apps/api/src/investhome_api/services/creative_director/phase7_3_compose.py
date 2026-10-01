"""Phase 7.3 — grammar-led canvas, immutable Day_007 object, real logo, live type."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.config.settings import get_settings
from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_2_photo_object import (
    SLOT_FILL,
    _fit_size,
    _px,
    paste_real_logo,
    photo_percentage,
    place_photo_object,
)
from investhome_api.services.creative_director.phase7_3_grammar import MAX_IMAGE_CALLS
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked
from investhome_api.services.creative_director.visual_composition_draft import _jpeg_bytes, _png_bytes
from investhome_api.services.gpt_image_design.client import GptImageProviderError, decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.config import DEFAULT_MODEL, openai_api_key, provider_availability, resolve_base_url, resolve_model

_ = MAX_IMAGE_CALLS


def fallback_graphic_canvas(_layout: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", CANVAS_4X5, (11, 12, 16))
    overlay = Image.new("RGB", CANVAS_4X5, (22, 20, 18))
    canvas = Image.blend(canvas, overlay, 0.22)
    return canvas.filter(ImageFilter.GaussianBlur(radius=0.6))


def scrub_magenta(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    pixels = rgb.load()
    for y in range(rgb.size[1]):
        for x in range(rgb.size[0]):
            r, g, b = pixels[x, y]
            if r > 140 and g < 95 and b > 70:
                pixels[x, y] = (14, 16, 20)
    return rgb


def render_slot_map(layout: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", CANVAS_4X5, (16, 17, 22))
    draw = ImageDraw.Draw(canvas)
    box = _px(layout["photo_box"])
    shape = layout.get("photo_shape") or "rect"
    if shape == "ellipse":
        draw.ellipse(box, fill=SLOT_FILL)
    elif shape == "rounded":
        draw.rounded_rectangle(box, radius=max(16, (box[2] - box[0]) // 26), fill=SLOT_FILL)
    else:
        draw.rectangle(box, fill=SLOT_FILL)
    for key in ("brand_box", "headline", "offer", "price", "unit", "cta"):
        x0, y0, x1, y1 = _px(layout[key])
        draw.rectangle((x0, y0, x1, y1), outline=(48, 52, 62), width=1)
    return canvas


def canvas_artist_prompt(*, grammar: dict[str, Any], why: str, layout: dict[str, Any]) -> str:
    fields = grammar.get("fields") or {}
    return "\n".join(
        [
            "Create ONE original 4:5 premium advertising GRAPHIC / EDITORIAL ENVIRONMENT.",
            "A real photograph will be placed later into the MAGENTA mass. Leave magenta empty.",
            "No architecture, people, windows, spires, facades, or invented buildings anywhere.",
            "No logo. No THE TEMPLE wordmark. No campaign copy. Typography is added later as live type.",
            "Image 1 = slot map. Magenta = reserved photographic object. Dark boxes = live type later.",
            "Image 2 = Grade-A reference. Steal DESIGN LOGIC only: gravity, rhythm, depth, craft, tension.",
            "Do NOT copy the reference building, photography, logo, company name, text, or exact artwork.",
            "Image 3 = real Day_007 for architectural character of the later photo object. Do not redraw it.",
            "Image 4 = Temple logo for color character only. Do not draw it.",
            "Every graphic mark must have a compositional role. No generic gold decoration.",
            "Do not make a listing card, brochure grid, website hero, property card, or UI.",
            "Do not default to an ellipse, a left/right split, or a full-bleed photo poster.",
            "Photo object role from grammar: " + str(layout.get("photo_role") or ""),
            "Photo geometry from grammar: " + str(fields.get("PHOTO_GEOMETRY") or ""),
            "Compositional gravity: " + str(fields.get("COMPOSITIONAL_GRAVITY") or ""),
            "Photo-to-graphic relationship: " + str(fields.get("PHOTO_TO_GRAPHIC_RELATIONSHIP") or ""),
            "Negative space: " + str(fields.get("NEGATIVE_SPACE_STRUCTURE") or ""),
            "Depth method: " + str(fields.get("DEPTH_METHOD") or ""),
            "Edge behavior: " + str(fields.get("EDGE_BEHAVIOR") or ""),
            "Graphic motifs as BEHAVIOR not copy: " + str(fields.get("GRAPHIC_MOTIFS") or ""),
            "Canvas closure: " + str(fields.get("CANVAS_CLOSURE") or ""),
            "Premium craft signature: " + str(fields.get("PREMIUM_CRAFT_SIGNATURE") or ""),
            "Why this grammar fits Day_007: " + why,
            "The result must feel like a finished agency campaign world around a designed photographic mass.",
        ]
    )


def generate_graphic_canvas(
    *,
    slot_map: Image.Image,
    reference: Image.Image,
    day007: Image.Image,
    logo: Image.Image,
    grammar: dict[str, Any],
    why: str,
    layout: dict[str, Any],
    slot: str,
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        return {"ok": False, "reason": avail.reason, "image_calls": 0, "image": fallback_graphic_canvas(layout)}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    images = [
        (_png_bytes(slot_map), f"slot-{slot}.png", "image/png"),
        (_jpeg_bytes(reference, 88), "grade-a-grammar-source.jpg", "image/jpeg"),
        (_jpeg_bytes(day007, 72), "day007-character.jpg", "image/jpeg"),
        (_png_bytes(logo.convert("RGB")), "temple-logo-character.png", "image/png"),
    ]
    try:
        remote = edit_image(
            api_key=openai_api_key(),
            model=model,
            prompt=canvas_artist_prompt(grammar=grammar, why=why, layout=layout),
            images=images,
            size="1088x1360",
            quality="high",
            base_url=resolve_base_url(settings),
            variant=f"phase7_3_canvas_{slot}",
            timeout=300.0,
        )
        image = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        return {
            "ok": True,
            "image": scrub_magenta(image),
            "image_calls": 1,
            "model": model,
            "method": "GPT_IMAGE_GRAMMAR_CANVAS",
        }
    except GptImageProviderError as exc:
        return {
            "ok": False,
            "reason": str(exc.detail)[:240],
            "image_calls": 1,
            "model": model,
            "image": fallback_graphic_canvas(layout),
            "method": "FALLBACK_GRAPHIC_CANVAS",
        }


def _origin(box: dict[str, float], align: str, draw: ImageDraw.ImageDraw, font, text: str) -> tuple[float, float]:
    x0, y0, x1, y1 = _px(box)
    if align == "right":
        return x1, y0
    if align == "center":
        return (x0 + x1) / 2, y0
    return x0, y0


def paint_grammar_story(canvas: Image.Image, layout: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    out = canvas.convert("RGB")
    draw = ImageDraw.Draw(out)
    align = str(layout.get("alignment") or "left")
    anchor = {"left": "lt", "right": "rt", "center": "mt"}[align]

    def face(role: str, size: int):
        return font_for_role(registry, role, size)

    hx0, hy0, hx1, hy1 = _px(layout["headline"])
    hfont = _fit_size(lambda s: face("DISPLAY_SANS", s), REQUIRED_FACTS["headline"], hx1 - hx0, min(56, max(28, hy1 - hy0 + 8)))
    hx, hy = _origin(layout["headline"], align, draw, hfont, REQUIRED_FACTS["headline"])
    draw.text((hx, hy), REQUIRED_FACTS["headline"], font=hfont, fill=IVORY, anchor=anchor if align != "left" else None)

    ox0, oy0, ox1, oy1 = _px(layout["offer"])
    pfont = face("COMMERCIAL_NUMBER", min(92, max(48, oy1 - oy0 - 12)))
    ox, oy = _origin(layout["offer"], align, draw, pfont, REQUIRED_FACTS["discount"])
    percent_box = render_percent(
        draw,
        origin=(ox, oy),
        text=REQUIRED_FACTS["discount"],
        font=pfont,
        fill=GOLD,
        alignment="right" if align == "right" else "left",
    )
    lfont = face("BODY", 17)
    label_y = percent_box[3] + 6
    lx = percent_box[0] if align != "right" else percent_box[2]
    _draw_tracked(
        draw,
        (lx, label_y),
        REQUIRED_FACTS["discount_label"],
        lfont,
        IVORY,
        tracking=90,
        anchor="lt" if align != "right" else "rt",
    )

    px0, py0, px1, py1 = _px(layout["price"])
    nfont = _fit_size(lambda s: face("COMMERCIAL_NUMBER", s), REQUIRED_FACTS["list_price"], px1 - px0, min(46, py1 - py0 + 8), floor=26)
    cfont = face("BODY", max(13, int(getattr(nfont, "size", 36) * 0.34)))
    px, py = _origin(layout["price"], align, draw, nfont, REQUIRED_FACTS["list_price"])
    render_price(
        draw,
        origin=(px, py),
        text=REQUIRED_FACTS["list_price"],
        number_font=nfont,
        currency_font=cfont,
        fill=GOLD,
        alignment="right" if align == "right" else "left",
    )

    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    ux0, uy0, ux1, uy1 = _px(layout["unit"])
    ufont = _fit_size(lambda s: face("EDITORIAL_SERIF", s), unit, ux1 - ux0, min(30, uy1 - uy0 + 6), floor=16)
    ux, uy = _origin(layout["unit"], align, draw, ufont, unit)
    draw.text((ux, uy), unit, font=ufont, fill=IVORY, anchor=anchor if align != "left" else None)

    cx0, cy0, cx1, cy1 = _px(layout["cta"])
    cta_font = _fit_size(lambda s: face("CTA", s), REQUIRED_FACTS["cta"], cx1 - cx0, 18, floor=13)
    cx, cy = _origin(layout["cta"], align, draw, cta_font, REQUIRED_FACTS["cta"])
    _draw_tracked(draw, (cx, cy + 6), REQUIRED_FACTS["cta"], cta_font, IVORY, tracking=48, anchor=anchor)
    bbox = draw.textbbox((cx, cy + 6), REQUIRED_FACTS["cta"], font=cta_font, anchor=anchor)
    draw.line((bbox[0], bbox[3] + 5, bbox[2], bbox[3] + 5), fill=GOLD, width=1)

    ex0, ey0, ex1, ey1 = _px(layout["closure"])
    efont = face("BODY", 13)
    _draw_tracked(draw, ((ex0 + ex1) / 2, ey0), APPROVED_BOTTOM_COPY, efont, (198, 194, 186), tracking=210, anchor="mt")
    return out


def compose_grammar_candidate(
    *,
    graphic_canvas: Image.Image,
    photo: Image.Image,
    logo_rgba: Image.Image,
    layout: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    base = graphic_canvas.convert("RGB")
    if base.size != CANVAS_4X5:
        base = base.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
    placed, photo_meta = place_photo_object(base, photo, layout)
    branded = paste_real_logo(placed, logo_rgba, layout)
    final = paint_grammar_story(branded, layout)
    photo_meta["generated_logo_pixels"] = 0
    photo_meta["duplicate_temple_logo"] = False
    photo_meta["percentage"] = photo_percentage(layout["photo_box"])
    return final, photo_meta
