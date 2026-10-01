"""Phase 7.4 — stage real Day_007, design around it, lock photo pixels back."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.config.settings import get_settings
from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
from investhome_api.services.creative_director.graphic_field_director import apply_graphic_field_to_foundation
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_2_photo_object import (
    _fit_size,
    _px,
    paste_real_logo,
    photo_percentage,
    place_photo_object,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked
from investhome_api.services.creative_director.visual_composition_draft import _jpeg_bytes, _png_bytes
from investhome_api.services.gpt_image_design.client import GptImageProviderError, decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.config import DEFAULT_MODEL, openai_api_key, provider_availability, resolve_base_url, resolve_model

MAX_IMAGE_CALLS = 3


def photo_protect_mask(layout: dict[str, Any]) -> dict[str, Any]:
    protect = Image.new("L", CANVAS_4X5, 0)
    draw = ImageDraw.Draw(protect)
    box = _px(layout["photo_box"])
    shape = str(layout.get("photo_shape") or "rect")
    if shape == "ellipse":
        draw.ellipse(box, fill=255)
    elif shape == "rounded":
        draw.rounded_rectangle(box, radius=max(16, (box[2] - box[0]) // 26), fill=255)
    else:
        draw.rectangle(box, fill=255)
    protect = protect.filter(ImageFilter.MaxFilter(9))
    white = Image.new("RGBA", CANVAS_4X5, (255, 255, 255, 255))
    mask_rgba = Image.composite(white, Image.new("RGBA", CANVAS_4X5, (0, 0, 0, 0)), protect)
    buf = io.BytesIO()
    mask_rgba.save(buf, format="PNG")
    return {"mask_l": protect, "mask_rgba": mask_rgba, "mask_png": buf.getvalue()}


def stage_photo(photo: Image.Image, layout: dict[str, Any]) -> Image.Image:
    field = Image.new("RGB", CANVAS_4X5, (12, 13, 18))
    placed, _meta = place_photo_object(field, photo, layout)
    return placed


def canvas_prompt(direction: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are finishing a 4:5 premium advertising canvas.",
            "Image 1 already contains the REAL Day_007 photograph in its designed position.",
            "That photograph is LOCKED. Do not redraw, inpaint, outpaint, or invent architecture inside it.",
            "Design the GRAPHIC / ATMOSPHERIC WORLD around it so the whole canvas becomes a campaign.",
            "Image 2 is ORNEK_00013 — a visual craft reference. Match its DESIGN RELATIONSHIPS and craft level.",
            "Do NOT copy its building, photography, logo, company name, copy, or exact artwork.",
            "Image 3 is the real Temple logo for color character only. Do not draw any logo or wordmark.",
            "Do not paint campaign copy. Typography is live type later.",
            "Typography will become visual mass in the regions described by this composition:",
            str(direction.get("composition_instruction") or ""),
            "How Day_007 participates: " + str(direction.get("how_day007_participates") or ""),
            "Headline is visual mass, not a label. %35 LANSMAN AVANTAJI is one commercial counterweight.",
            "Leave breathing room where type will sit. No listing card, UI, brochure grid, or web button.",
            "No generic gold decoration without a compositional role.",
        ]
    )


def generate_around_photo(
    *,
    staged: Image.Image,
    reference: Image.Image,
    logo: Image.Image,
    layout: dict[str, Any],
    direction: dict[str, Any],
    slot: str,
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        return {"ok": False, "reason": avail.reason, "image_calls": 0, "image": staged, "method": "STAGED_PHOTO_ONLY"}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    mask = photo_protect_mask(layout)
    images = [
        (_png_bytes(staged), f"staged-day007-{slot}.png", "image/png"),
        (_jpeg_bytes(reference, 90), "ornek-00013.jpg", "image/jpeg"),
        (_png_bytes(logo.convert("RGB")), "temple-logo-character.png", "image/png"),
    ]
    try:
        remote = edit_image(
            api_key=openai_api_key(),
            model=model,
            prompt=canvas_prompt(direction),
            images=images,
            size="1088x1360",
            quality="high",
            base_url=resolve_base_url(settings),
            variant=f"phase7_4_around_photo_{slot}",
            timeout=300.0,
            mask=mask["mask_png"],
        )
        generated = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
        if generated.size != CANVAS_4X5:
            generated = generated.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        around = apply_graphic_field_to_foundation(staged, generated, mask["mask_l"])
        return {"ok": True, "image": around, "image_calls": 1, "model": model, "method": "GPT_AROUND_STAGED_DAY007"}
    except GptImageProviderError as exc:
        return {
            "ok": False,
            "reason": str(exc.detail)[:240],
            "image_calls": 1,
            "model": model,
            "image": staged,
            "method": "STAGED_PHOTO_ONLY",
        }


def _origin(box: dict[str, float], align: str) -> tuple[float, float]:
    x0, y0, x1, _y1 = _px(box)
    if align == "right":
        return x1, y0
    if align == "center":
        return (x0 + x1) / 2, y0
    return x0, y0


def paint_visual_mass(canvas: Image.Image, layout: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    out = canvas.convert("RGB")
    draw = ImageDraw.Draw(out)
    align = str(layout.get("alignment") or "left")
    if align not in {"left", "right", "center"}:
        align = "left"
    anchor = {"left": "lt", "right": "rt", "center": "mt"}[align]
    h_mul = float(layout.get("headline_scale") or 1.0)
    o_mul = float(layout.get("offer_scale") or 1.0)
    p_mul = float(layout.get("price_scale") or 0.7)

    def face(role: str, size: int):
        return font_for_role(registry, role, size)

    hx0, hy0, hx1, hy1 = _px(layout["headline"])
    h_size = min(78, max(34, int((hy1 - hy0) * 1.15 * h_mul)))
    hfont = _fit_size(lambda s: face("DISPLAY_SANS", s), REQUIRED_FACTS["headline"], hx1 - hx0, h_size, floor=28)
    hx, hy = _origin(layout["headline"], align)
    draw.text((hx, hy), REQUIRED_FACTS["headline"], font=hfont, fill=IVORY, anchor=None if align == "left" else anchor)

    ox0, oy0, ox1, oy1 = _px(layout["offer"])
    pfont = face("COMMERCIAL_NUMBER", min(110, max(52, int((oy1 - oy0) * 0.72 * o_mul))))
    ox, oy = _origin(layout["offer"], align)
    percent_box = render_percent(
        draw,
        origin=(ox, oy),
        text=REQUIRED_FACTS["discount"],
        font=pfont,
        fill=GOLD,
        alignment="right" if align == "right" else "left",
    )
    lfont = face("BODY", max(15, int(getattr(pfont, "size", 72) * 0.22)))
    lx = percent_box[0] if align != "right" else percent_box[2]
    _draw_tracked(
        draw,
        (lx, percent_box[3] + 4),
        REQUIRED_FACTS["discount_label"],
        lfont,
        IVORY,
        tracking=80,
        anchor="lt" if align != "right" else "rt",
    )

    px0, py0, px1, py1 = _px(layout["price"])
    n_size = min(56, max(30, int((py1 - py0) * 1.05 * p_mul)))
    nfont = _fit_size(lambda s: face("COMMERCIAL_NUMBER", s), REQUIRED_FACTS["list_price"], px1 - px0, n_size, floor=24)
    cfont = face("BODY", max(13, int(getattr(nfont, "size", 36) * 0.34)))
    px, py = _origin(layout["price"], align)
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
    ufont = _fit_size(lambda s: face("EDITORIAL_SERIF", s), unit, ux1 - ux0, min(32, uy1 - uy0 + 8), floor=16)
    ux, uy = _origin(layout["unit"], align)
    draw.text((ux, uy), unit, font=ufont, fill=IVORY, anchor=None if align == "left" else anchor)

    cx0, cy0, cx1, cy1 = _px(layout["cta"])
    cta_font = _fit_size(lambda s: face("CTA", s), REQUIRED_FACTS["cta"], cx1 - cx0, 18, floor=13)
    cx, cy = _origin(layout["cta"], align)
    _draw_tracked(draw, (cx, cy + 4), REQUIRED_FACTS["cta"], cta_font, IVORY, tracking=52, anchor=anchor)
    bbox = draw.textbbox((cx, cy + 4), REQUIRED_FACTS["cta"], font=cta_font, anchor=anchor)
    draw.line((bbox[0], bbox[3] + 5, bbox[2], bbox[3] + 5), fill=GOLD, width=1)

    ex0, ey0, ex1, ey1 = _px(layout["closure"])
    efont = face("BODY", 13)
    _draw_tracked(draw, ((ex0 + ex1) / 2, ey0), APPROVED_BOTTOM_COPY, efont, (198, 194, 186), tracking=210, anchor="mt")
    return out


def compose_direct_candidate(
    *,
    around: Image.Image,
    photo: Image.Image,
    logo_rgba: Image.Image,
    layout: dict[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    base = around.convert("RGB")
    if base.size != CANVAS_4X5:
        base = base.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
    placed, photo_meta = place_photo_object(base, photo, layout)
    branded = paste_real_logo(placed, logo_rgba, layout)
    final = paint_visual_mass(branded, layout)
    photo_meta["generated_logo_pixels"] = 0
    photo_meta["percentage"] = photo_percentage(layout["photo_box"])
    return final, photo_meta
