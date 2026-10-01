"""Stage 4.0-R1 — vertical polish of the existing Investhome brand Story.

Parent is the already-rendered 9:16 Story. Type, copy, and campaign identity stay.
Only photo scale/crop/position and logo seating change. No stretch. No new imagery.
"""

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
    render_mobile_preview,
    sample_navy,
)

# Locked type boxes from the parent Story render. Do not restyle.
PARENT_TYPE = {
    "HEADLINE": {"xy": (481, 268), "size": (539, 520)},
    "SUBHEAD": {"xy": (447, 844), "size": (573, 421)},
    "LOGO": {"xy": (545, 1497), "size": (475, 162)},
}

# Same source photograph as the master. Taller presence, uniform scale, no stretch.
PHOTO_CROP = {"x": 0.0, "y": 0.22, "w": 0.52, "h": 0.78}
PHOTO_SCALE = 1.38
LOGO_TOP = 0.812


def _extract(parent: Image.Image, box: dict[str, Any]) -> Image.Image:
    x, y = box["xy"]
    w, h = box["size"]
    return parent.crop((x, y, x + w, y + h)).convert("RGBA")


def polish_story_r1(*, parent_story: Image.Image, original: Image.Image) -> dict[str, Any]:
    if tuple(parent_story.size) != CANVAS:
        raise RuntimeError("Stage 4.0-R1 requires the parent 1080×1920 Story")
    navy = sample_navy(original)
    canvas = Image.new("RGBA", CANVAS, navy + (255,))
    headline = _extract(parent_story, PARENT_TYPE["HEADLINE"])
    subhead = _extract(parent_story, PARENT_TYPE["SUBHEAD"])
    logo = knock_navy(_extract(parent_story, PARENT_TYPE["LOGO"]), navy, tol=28)
    photo = _scale(_crop_frac(original, PHOTO_CROP), PHOTO_SCALE)
    photo_x, photo_y = 0, CANVAS_H - photo.size[1]
    canvas.alpha_composite(photo.convert("RGBA"), (photo_x, max(0, photo_y)))
    hx, hy = PARENT_TYPE["HEADLINE"]["xy"]
    sx, sy = PARENT_TYPE["SUBHEAD"]["xy"]
    canvas.alpha_composite(headline, (hx, hy))
    canvas.alpha_composite(subhead, (sx, sy))
    logo_x = CANVAS_W - int(0.055 * CANVAS_W) - logo.size[0]
    logo_y = int(LOGO_TOP * CANVAS_H)
    canvas.alpha_composite(logo, (max(0, logo_x), max(0, logo_y)))
    story = canvas.convert("RGB")
    if story.size != CANVAS:
        raise RuntimeError("R1 Story is not 1080×1920")
    return {
        "story": story,
        "parent": parent_story.convert("RGB"),
        "placements": {
            "PHOTO": {"xy": [photo_x, photo_y], "size": list(photo.size), "scale": PHOTO_SCALE},
            "HEADLINE": PARENT_TYPE["HEADLINE"],
            "SUBHEAD": PARENT_TYPE["SUBHEAD"],
            "LOGO": {"xy": [logo_x, logo_y], "size": list(logo.size)},
        },
        "photo_stretched": False,
    }


def render_source_vs_r1(parent_story: Image.Image, r1: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1600, 1280), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "SOURCE STORY  vs  R1  —  vertical polish only", font=_font(18), fill=GOLD)
    left = parent_story.copy()
    right = r1.copy()
    left.thumbnail((620, 1120), Image.Resampling.LANCZOS)
    right.thumbnail((620, 1120), Image.Resampling.LANCZOS)
    canvas.paste(left.convert("RGB"), (80, 70))
    canvas.paste(right.convert("RGB"), (880, 70))
    draw.text((80, 1220), "PARENT STORY  9:16", font=_font(14), fill=IVORY)
    draw.text((880, 1220), "R1  9:16  vertical rebalance", font=_font(14), fill=IVORY)
    return canvas
