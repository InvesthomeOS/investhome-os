"""Stage 4.0-R2 — one continuous photograph. No fragments. No patches."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.premium_story_recomposer_v1 import (
    CANVAS,
    CANVAS_H,
    CANVAS_W,
    GOLD,
    IVORY,
    _crop_frac,
    _scale,
    knock_navy,
    sample_navy,
)
from investhome_api.services.creative_director.semantic_layer_exclusivity_v1 import (
    refuse_if_unclean,
    strip_source_typography_from_photo,
    validate_semantic_exclusivity,
)

# One crop of the original colonnade, including its native navy fade.
PHOTO = {"x": 0.0, "y": 0.17, "w": 0.56, "h": 0.83, "scale": 0.92, "x_px": 0, "bottom": 1.0}

# Type from original pixels. Crops stay in the navy field so they cannot carry stone.
HEADLINE = {"x": 0.48, "y": 0.16, "w": 0.47, "h": 0.26, "right": 0.055, "top": 0.145, "scale": 1.0}
SUBHEAD = {"x": 0.49, "y": 0.45, "w": 0.46, "h": 0.125, "right": 0.055, "top": 0.445, "scale": 1.0}
LASTLINE = {"x": 0.56, "y": 0.575, "w": 0.39, "h": 0.048, "right": 0.055, "scale": 1.0}
LOGO = {"x": 0.58, "y": 0.85, "w": 0.38, "h": 0.12, "right": 0.07, "top": 0.735, "scale": 1.0}


def isolate_type(layer: Image.Image, navy: tuple[int, int, int], *, min_lum: int = 205) -> Image.Image:
    """Keep original white/gold type. Drop navy and photographic stone."""
    layer = layer.convert("RGBA")
    pix = layer.load()
    w, h = layer.size
    nr, ng, nb = navy
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if abs(r - nr) <= 30 and abs(g - ng) <= 30 and abs(b - nb) <= 30:
                pix[x, y] = (r, g, b, 0)
                continue
            lum = (r + g + b) / 3.0
            gold = r > 148 and 108 < g < 214 and b < 155 and r > b + 22
            if gold or lum >= min_lum:
                continue
            pix[x, y] = (r, g, b, 0)
    return layer


def trim_alpha(layer: Image.Image) -> Image.Image:
    box = layer.getbbox()
    return layer.crop(box) if box else layer


def compose_story_r2(original: Image.Image) -> dict[str, Any]:
    if original.size[0] < 1000 or original.size[1] < 1200:
        raise RuntimeError("Stage 4.0-R2 requires the original 4:5 master")
    navy = sample_navy(original)
    canvas = Image.new("RGBA", CANVAS, navy + (255,))

    type_boxes = (HEADLINE, SUBHEAD, LASTLINE, LOGO)
    photo = strip_source_typography_from_photo(
        original,
        _scale(_crop_frac(original, PHOTO), PHOTO["scale"]),
        PHOTO,
        type_boxes,
        navy,
    )
    photo_x = int(PHOTO["x_px"])
    photo_y = int(PHOTO["bottom"] * CANVAS_H) - photo.size[1]
    canvas.alpha_composite(photo, (photo_x, max(0, photo_y)))
    photo_right = photo_x + photo.size[0]

    headline = trim_alpha(isolate_type(_scale(_crop_frac(original, HEADLINE), HEADLINE["scale"]), navy))
    subhead = trim_alpha(isolate_type(_scale(_crop_frac(original, SUBHEAD), SUBHEAD["scale"]), navy))
    lastline = knock_navy(_scale(_crop_frac(original, LASTLINE), LASTLINE["scale"]), navy, tol=18)
    logo = trim_alpha(isolate_type(_scale(_crop_frac(original, LOGO), LOGO["scale"]), navy, min_lum=145))

    def paste_right(layer: Image.Image, *, right: float, top: float, clear_of_photo: bool) -> tuple[int, int]:
        x = int(CANVAS_W - right * CANVAS_W - layer.size[0])
        y = int(top * CANVAS_H)
        if clear_of_photo:
            x = max(x, photo_right + 28)
        x = min(max(24, x), CANVAS_W - layer.size[0] - 24)
        y = max(0, y)
        canvas.alpha_composite(layer, (x, y))
        return (x, y)

    head_xy = paste_right(headline, right=HEADLINE["right"], top=HEADLINE["top"], clear_of_photo=False)
    sub_xy = paste_right(subhead, right=SUBHEAD["right"], top=SUBHEAD["top"], clear_of_photo=True)
    last_top = (sub_xy[1] + int((LASTLINE["y"] - SUBHEAD["y"]) * original.size[1] * SUBHEAD["scale"])) / CANVAS_H
    last_xy = paste_right(lastline, right=LASTLINE["right"], top=last_top, clear_of_photo=True)
    logo_x = int(CANVAS_W - LOGO["right"] * CANVAS_W - logo.size[0])
    logo_y = int(LOGO["top"] * CANVAS_H)
    logo_x = max(logo_x, photo_right + 40)
    logo_y = min(logo_y, int(0.84 * CANVAS_H) - logo.size[1])
    logo_x = min(logo_x, CANVAS_W - logo.size[0] - 40)
    canvas.alpha_composite(logo, (max(0, logo_x), max(0, logo_y)))

    story = canvas.convert("RGB")
    if story.size != CANVAS:
        raise RuntimeError("R2 Story is not 1080×1920")
    placements = {
        "PHOTO": {"xy": [photo_x, photo_y], "size": list(photo.size), "crop": PHOTO, "scale": PHOTO["scale"]},
        "HEADLINE": {"xy": list(head_xy), "size": list(headline.size)},
        "SUBHEAD": {"xy": list(sub_xy), "size": list(subhead.size)},
        "LASTLINE": {"xy": list(last_xy), "size": list(lastline.size)},
        "LOGO": {"xy": [logo_x, logo_y], "size": list(logo.size)},
    }
    validation = validate_semantic_exclusivity(
        story=story,
        placements=placements,
        navy=navy,
        photo_pastes=1,
        layer_roles=["PROJECT_PHOTO", "HEADLINE", "BODY_COPY", "HIGHLIGHT", "LOGO"],
    )
    return {
        "story": story,
        "navy": navy,
        "photo_pastes": 1,
        "placements": placements,
        "validation": validation,
    }


def compose_story_clean(original: Image.Image) -> dict[str, Any]:
    packed = compose_story_r2(original)
    refuse_if_unclean(packed["validation"])
    return packed


def render_source_vs_r2(original: Image.Image, r2: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1280), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "SOURCE 4:5  vs  STORY R2  —  one continuous photograph", font=_font(18), fill=GOLD)
    left = original.copy()
    right = r2.copy()
    left.thumbnail((720, 1120), Image.Resampling.LANCZOS)
    right.thumbnail((560, 1120), Image.Resampling.LANCZOS)
    canvas.paste(left.convert("RGB"), (80, 70))
    canvas.paste(right.convert("RGB"), (1100, 70))
    draw.text((80, 1220), f"ORIGINAL 4:5  {original.size[0]}×{original.size[1]}", font=_font(14), fill=IVORY)
    draw.text((1100, 1220), "R2  9:16  one crop, one scale, one position", font=_font(14), fill=IVORY)
    return canvas
