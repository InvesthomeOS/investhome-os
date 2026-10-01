"""Phase 11.10 review boards. Feasibility artifacts, not production art direction."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY


def _tile(canvas, image, box, title, draw) -> None:
    x, y, w, h = box
    if image is None:
        draw.rectangle((x, y, x + w, y + h), fill=(28, 24, 20))
        draw.text((x + 12, y + h // 2), "missing", font=_font(16), fill=GOLD)
        return
    tile = image.copy()
    tile.thumbnail((w, h), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (x, y))
    draw.text((x, y + h + 6), title, font=_font(14), fill=IVORY)


def source_selection_board(fitted: Image.Image, mask_vis: Image.Image, filename: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), f"02  SOURCE SELECTION  —  {filename}   4:5 fit / architecture preserve mask", font=_font(16), fill=GOLD)
    _tile(canvas, fitted, (40, 56, 880, 1040), "FITTED SOURCE (protected architecture)", draw)
    _tile(canvas, mask_vis, (980, 56, 880, 1040), "MASK PREVIEW (red = editable field)", draw)
    return canvas


def commercial_detail_board(final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "09  COMMERCIAL DETAIL  —  type as designed in the visual master", font=_font(16), fill=GOLD)
    tile = final.copy()
    tile.thumbnail((760, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    w, h = final.size
    crops = [
        ("IDENTITY", (0, 0, int(w * 0.55), int(h * 0.28))),
        ("OFFER", (int(w * 0.20), int(h * 0.18), int(w * 0.95), int(h * 0.55))),
        ("VALUE / CTA", (0, int(h * 0.62), w, h)),
    ]
    y = 56
    x = 820
    for title, box in crops:
        crop = final.crop(box)
        crop.thumbnail((1040, 340), Image.Resampling.LANCZOS)
        canvas.paste(crop.convert("RGB"), (x, y))
        draw.text((x, y + crop.size[1] + 4), title, font=_font(14), fill=IVORY)
        y += 360
    return canvas


def grade_a_comparison_board(
    references: dict[str, Image.Image],
    hybrid: Image.Image | None,
    native: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "11  QUALITY COMPARISON  —  Grade-A craft references / Candidate A / Candidate B", font=_font(16), fill=GOLD)
    refs = [
        references.get("ORNEK_00013.jpg"),
        references.get("ORNEK_00011.jpg"),
        references.get("ORNEK_00008.jpg"),
    ]
    x = 20
    for i, image in enumerate(refs):
        _tile(canvas, image, (x, 56, 280, 980), f"REF {i+1}", draw)
        x += 300
    _tile(canvas, hybrid, (x, 56, 480, 980), "CANDIDATE A", draw)
    x += 500
    _tile(canvas, native, (x, 56, 480, 980), "CANDIDATE B", draw)
    return canvas


def human_review_board(final: Image.Image, thumb: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "14  HUMAN REVIEW  —  AI-native feasibility   PENDING HUMAN REVIEW", font=_font(16), fill=GOLD)
    _tile(canvas, final, (40, 56, 900, 1040), "FINAL 4:5", draw)
    _tile(canvas, thumb, (1000, 56, 860, 1040), "15%", draw)
    return canvas
