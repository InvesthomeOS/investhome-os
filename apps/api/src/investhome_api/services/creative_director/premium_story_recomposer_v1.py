"""DEPRECATED REPOSITION COMPOSER — Stage 4.0 Story crop/reposition.

Archived proof that technical integrity gates can hold.
Replaced by PremiumFormatRecomposerV1. Do not use as the production format path.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.premium_format_adapter_v1 import STORY_CANVAS, story_safe_zone_v1
from investhome_api.services.creative_director.phase12_0_ingestion import SELECTED_ASSET_ID, SELECTED_FILENAME
from investhome_api.services.creative_director.semantic_layer_exclusivity_v1 import (
    strip_source_typography_from_photo,
    validate_semantic_exclusivity,
)

CANVAS_W = int(STORY_CANVAS["width"])
CANVAS_H = int(STORY_CANVAS["height"])
CANVAS = (CANVAS_W, CANVAS_H)
GOLD = (201, 168, 92)
IVORY = (236, 230, 218)

# Exclusive 4:5 masses measured from the original pixels.
# PRESTİJLİ lives at y≈0.35–0.40; the colonnade begins around y≈0.27.
SOURCE_MASSES = {
    "PHOTO": {"x": 0.0, "y": 0.26, "w": 0.50, "h": 0.74},
    "HEADLINE": {"x": 0.47, "y": 0.05, "w": 0.48, "h": 0.37},
    "SUBHEAD": {"x": 0.44, "y": 0.42, "w": 0.51, "h": 0.30},
    "LOGO": {"x": 0.52, "y": 0.85, "w": 0.44, "h": 0.12},
}

# Native 9:16: extra height is navy between the type groups. Photo stays left mass.
STORY_PLACEMENT = {
    "HEADLINE": {"right": 0.055, "top": 0.14, "scale": 1.04},
    "SUBHEAD": {"right": 0.055, "top": 0.44, "scale": 1.04},
    "PHOTO": {"left": 0.0, "bottom": 1.0, "scale": 1.04},
    "LOGO": {"right": 0.055, "top": 0.78, "scale": 1.0},
}


def _crop_frac(image: Image.Image, box: dict[str, float]) -> Image.Image:
    w, h = image.size
    x0 = max(0, int(box["x"] * w))
    y0 = max(0, int(box["y"] * h))
    x1 = min(w, int((box["x"] + box["w"]) * w))
    y1 = min(h, int((box["y"] + box["h"]) * h))
    return image.crop((x0, y0, x1, y1)).convert("RGBA")


def sample_navy(original: Image.Image) -> tuple[int, int, int]:
    w, h = original.size
    probes = ((int(w * 0.82), int(h * 0.06)), (int(w * 0.70), int(h * 0.18)), (int(w * 0.90), int(h * 0.72)))
    px = original.convert("RGB")
    acc = [0, 0, 0]
    for x, y in probes:
        r, g, b = px.getpixel((x, y))
        acc[0] += r
        acc[1] += g
        acc[2] += b
    n = len(probes)
    return (acc[0] // n, acc[1] // n, acc[2] // n)


def knock_navy(layer: Image.Image, navy: tuple[int, int, int], *, tol: int = 26) -> Image.Image:
    """Keep type/logo pixels; drop the designed navy so layers can overlap the photo mass."""
    layer = layer.convert("RGBA")
    pix = layer.load()
    w, h = layer.size
    nr, ng, nb = navy
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if abs(r - nr) <= tol and abs(g - ng) <= tol and abs(b - nb) <= tol:
                pix[x, y] = (r, g, b, 0)
    return layer


def _scale(layer: Image.Image, scale: float) -> Image.Image:
    if abs(scale - 1.0) < 0.01:
        return layer
    w, h = layer.size
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return layer.resize(size, Image.Resampling.LANCZOS)


def _paste_right(canvas: Image.Image, layer: Image.Image, *, right: float, top: float) -> tuple[int, int]:
    x = int(CANVAS_W - right * CANVAS_W - layer.size[0])
    y = int(top * CANVAS_H)
    canvas.alpha_composite(layer, (max(0, x), max(0, y)))
    return (x, y)


def _paste_left_bottom(canvas: Image.Image, layer: Image.Image, *, left: float, bottom: float) -> tuple[int, int]:
    x = int(left * CANVAS_W)
    y = int(bottom * CANVAS_H) - layer.size[1]
    canvas.alpha_composite(layer, (max(0, x), max(0, y)))
    return (x, y)


def is_simple_resize(original: Image.Image, story: Image.Image) -> bool:
    if story.size != CANVAS:
        return True
    stretched = original.convert("RGB").resize(CANVAS, Image.Resampling.LANCZOS)
    if _near_equal(story.convert("RGB"), stretched, tol=8):
        return True
    y0 = (CANVAS_H - original.size[1]) // 2
    if y0 > 0:
        letterbox = Image.new("RGB", CANVAS, sample_navy(original))
        ox = (CANVAS_W - original.size[0]) // 2
        letterbox.paste(original.convert("RGB"), (max(0, ox), y0))
        if _near_equal(story.convert("RGB"), letterbox, tol=8):
            return True
    return False


def _near_equal(a: Image.Image, b: Image.Image, *, tol: int) -> bool:
    if a.size != b.size:
        return False
    extrema = ImageChops.difference(a, b).getextrema()
    peaks = [item[1] if isinstance(item, tuple) else item for item in extrema]
    return max(peaks) <= tol


def recompose_ornek_00013_to_story(original: Image.Image) -> dict[str, Any]:
    if original.size[0] < 1000 or original.size[1] < 1200:
        raise RuntimeError("Stage 4.0 retry requires the original 4:5 master pixels")
    navy = sample_navy(original)
    canvas = Image.new("RGBA", CANVAS, navy + (255,))
    photo = strip_source_typography_from_photo(
        original,
        knock_navy(
            _scale(_crop_frac(original, SOURCE_MASSES["PHOTO"]), STORY_PLACEMENT["PHOTO"]["scale"]),
            navy,
            tol=22,
        ),
        SOURCE_MASSES["PHOTO"],
        (SOURCE_MASSES["HEADLINE"], SOURCE_MASSES["SUBHEAD"], SOURCE_MASSES["LOGO"]),
        navy,
    )
    headline = _scale(_crop_frac(original, SOURCE_MASSES["HEADLINE"]), STORY_PLACEMENT["HEADLINE"]["scale"])
    subhead = _scale(_crop_frac(original, SOURCE_MASSES["SUBHEAD"]), STORY_PLACEMENT["SUBHEAD"]["scale"])
    logo = _scale(_crop_frac(original, SOURCE_MASSES["LOGO"]), STORY_PLACEMENT["LOGO"]["scale"])
    # Photo first with navy knocked out so the fade is not a hard seam under the type field.
    photo_xy = _paste_left_bottom(canvas, photo, left=STORY_PLACEMENT["PHOTO"]["left"], bottom=STORY_PLACEMENT["PHOTO"]["bottom"])
    head_xy = _paste_right(canvas, headline, right=STORY_PLACEMENT["HEADLINE"]["right"], top=STORY_PLACEMENT["HEADLINE"]["top"])
    sub_xy = _paste_right(canvas, subhead, right=STORY_PLACEMENT["SUBHEAD"]["right"], top=STORY_PLACEMENT["SUBHEAD"]["top"])
    logo_xy = _paste_right(canvas, logo, right=STORY_PLACEMENT["LOGO"]["right"], top=STORY_PLACEMENT["LOGO"]["top"])
    story = canvas.convert("RGB")
    if story.size != CANVAS:
        raise RuntimeError("Story canvas is not 1080×1920")
    simple = is_simple_resize(original, story)
    zone = story_safe_zone_v1()
    well = zone["content_well"]
    placements = {
        "PHOTO": {"xy": photo_xy, "size": list(photo.size)},
        "HEADLINE": {"xy": head_xy, "size": list(headline.size)},
        "SUBHEAD": {"xy": sub_xy, "size": list(subhead.size)},
        "LOGO": {"xy": logo_xy, "size": list(logo.size)},
    }
    return {
        "story": story,
        "navy": navy,
        "simple_resize": simple,
        "placements": placements,
        "validation": validate_semantic_exclusivity(
            story=story,
            placements=placements,
            navy=navy,
            photo_pastes=1,
            layer_roles=["PROJECT_PHOTO", "HEADLINE", "BODY_COPY", "LOGO"],
        ),
        "safe_zone": zone,
        "content_well": well,
        "source_filename": SELECTED_FILENAME,
        "source_asset_id": SELECTED_ASSET_ID,
    }


def render_source_vs_story(original: Image.Image, story: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1280), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "03  SOURCE 4:5  vs  STORY 9:16  —  format adaptation, not a new campaign", font=_font(18), fill=GOLD)
    left = original.copy()
    right = story.copy()
    left.thumbnail((820, 1120), Image.Resampling.LANCZOS)
    right.thumbnail((620, 1120), Image.Resampling.LANCZOS)
    canvas.paste(left.convert("RGB"), (80, 70))
    canvas.paste(right.convert("RGB"), (1060, 70))
    draw.text((80, 1220), f"ORIGINAL 4:5  {original.size[0]}×{original.size[1]}  {SELECTED_FILENAME}", font=_font(14), fill=IVORY)
    draw.text((1060, 1220), f"STORY 9:16  {story.size[0]}×{story.size[1]}", font=_font(14), fill=IVORY)
    return canvas


def render_mobile_preview(story: Image.Image) -> Image.Image:
    frame_w, frame_h = 720, 1280
    canvas = Image.new("RGB", (frame_w, frame_h), (8, 9, 12))
    draw = ImageDraw.Draw(canvas)
    bezel = 28
    inner = (bezel, 56, frame_w - bezel, frame_h - 48)
    draw.rounded_rectangle((8, 8, frame_w - 8, frame_h - 8), radius=48, outline=(40, 42, 48), width=3)
    draw.rounded_rectangle((18, 22, frame_w - 18, 46), radius=10, fill=(20, 22, 28))
    preview = story.copy()
    preview.thumbnail((inner[2] - inner[0], inner[3] - inner[1]), Image.Resampling.LANCZOS)
    canvas.paste(preview.convert("RGB"), (inner[0] + ((inner[2] - inner[0]) - preview.size[0]) // 2, inner[1]))
    draw.text((36, frame_h - 36), "04  MOBILE PREVIEW  —  Instagram Story chrome is not part of the ad", font=_font(13), fill=(160, 156, 148))
    return canvas.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=2))


def render_human_review_board(*, original: Image.Image, story: Image.Image, review: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "05  HUMAN REVIEW  —  IS THIS A NATIVE STORY OF ORNEK_00013?", font=_font(18), fill=GOLD)
    draw.text((36, 46), "Do not auto-approve. Visual review is final.", font=_font(14), fill=(180, 176, 168))
    left = original.copy()
    right = story.copy()
    left.thumbnail((620, 900), Image.Resampling.LANCZOS)
    right.thumbnail((460, 900), Image.Resampling.LANCZOS)
    canvas.paste(left.convert("RGB"), (48, 88))
    canvas.paste(right.convert("RGB"), (720, 88))
    draw.text((48, 1010), "ORIGINAL 4:5", font=_font(14), fill=IVORY)
    draw.text((720, 1010), "STORY 9:16  PENDING HUMAN REVIEW", font=_font(14), fill=IVORY)
    y = 100
    for key in (
        "SAME CAMPAIGN",
        "SIMPLE RESIZE",
        "VISUAL IDENTITY PRESERVED",
        "TYPOGRAPHIC CHARACTER PRESERVED",
        "PHOTO ROLE PRESERVED",
        "BRAND CHARACTER PRESERVED",
        "STORY COMPOSITION FEELS NATIVE",
    ):
        val = review.get(key, "—")
        color = (120, 200, 140) if val == "YES" else ((220, 90, 90) if val == "NO" else IVORY)
        if key == "SIMPLE RESIZE":
            color = (120, 200, 140) if val == "NO" else (220, 90, 90)
        draw.text((1260, y), f"{key}:  {val}", font=_font(16), fill=color)
        y += 36
    draw.text((1260, y + 16), "STATUS: PREMIUM_STORY_PENDING_HUMAN_REVIEW", font=_font(15), fill=GOLD)
    draw.text((1260, y + 52), "GPT IMAGE CALLS: 0", font=_font(15), fill=IVORY)
    draw.text((1260, y + 88), "Not The Temple. Not UniLoft.", font=_font(14), fill=(180, 176, 168))
    return canvas
