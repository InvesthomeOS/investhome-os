"""Phase 11.11 review boards. Not production art direction."""

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


def reference_selection_board(refs: dict[str, Image.Image], selected: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "01  REFERENCE SELECTION  —  Grade-A DESIGN_REFERENCES   not auto ORNEK_00001", font=_font(16), fill=GOLD)
    order = (
        "ORNEK_00013.jpg",
        "ORNEK_00001.jpg",
        "ORNEK_00011.jpg",
        "ORNEK_00008.jpg",
        "ORNEK_00015.jpg",
        "ORNEK_00006.jpg",
    )
    x, y = 28, 56
    for name in order:
        mark = "  SELECTED" if name == selected else ""
        _tile(canvas, refs.get(name), (x, y, 280, 980), name.replace(".jpg", "") + mark, draw)
        x += 315
    return canvas


def temple_asset_match_board(thumbs: dict[str, Image.Image], chosen: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), f"05  TEMPLE ASSET MATCH  —  structure first, then photograph   chosen: {chosen}", font=_font(16), fill=GOLD)
    order = (
        ("Day_008 tower fragment — SELECTED", "Day_008"),
        ("Day_002 lantern (Master 03)", "Day_002"),
        ("Day_009 (THE_REGISTER photo)", "Day_009"),
        ("Day_001 street wall", "Day_001"),
        ("Sunset_001 (Master 02)", "Sunset_001"),
        ("Living_Room_001 interior", "Living_Room_001"),
    )
    x = 28
    for title, key in order:
        _tile(canvas, thumbs.get(key), (x, 56, 280, 980), title, draw)
        x += 315
    return canvas


def reconstruction_development(
    reference: Image.Image | None,
    crop: Image.Image | None,
    obj: Image.Image | None,
    field: Image.Image | None,
    fused: Image.Image | None,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "07  RECONSTRUCTION DEVELOPMENT  —  interpret / adapt / finish   no A/B", font=_font(16), fill=GOLD)
    obj_plate = None
    if obj is not None:
        obj_plate = Image.new("RGB", (1088, 1360), (22, 20, 18))
        fitted = obj.copy()
        fitted.thumbnail((900, 1200), Image.Resampling.LANCZOS)
        ox = (1088 - fitted.size[0]) // 2
        oy = (1360 - fitted.size[1]) // 2
        obj_plate.paste(fitted, (ox, oy), fitted if fitted.mode == "RGBA" else None)
    x = 20
    for title, image in (
        ("SELECTED REFERENCE (DNA ONLY)", reference),
        ("TEMPLE CROP", crop),
        ("EXTRACTED OBJECT V2", obj_plate),
        ("DESIGNED VOID", field),
        ("INTEGRATED (NO TYPE)", fused),
    ):
        _tile(canvas, image, (x, 56, 360, 1020), title, draw)
        x += 380
    return canvas


def comparison_board(
    reference: Image.Image | None,
    hybrid: Image.Image | None,
    guided: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "12  QUALITY COMPARISON  —  craft reference / Candidate A / Candidate B", font=_font(16), fill=GOLD)
    _tile(canvas, reference, (40, 56, 560, 1020), "REF", draw)
    _tile(canvas, hybrid, (680, 56, 560, 1020), "CANDIDATE A", draw)
    _tile(canvas, guided, (1320, 56, 560, 1020), "CANDIDATE B", draw)
    return canvas


def human_review_board(final: Image.Image, thumb: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "15  HUMAN REVIEW  —  reference-guided feasibility   PENDING HUMAN REVIEW", font=_font(16), fill=GOLD)
    tile = final.copy()
    tile.thumbnail((760, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (40, 56))
    t = thumb.copy()
    t.thumbnail((220, 280), Image.Resampling.LANCZOS)
    canvas.paste(t.convert("RGB"), (860, 56))
    draw.text((860, 56 + t.size[1] + 10), "15%", font=_font(14), fill=IVORY)
    draw.text((40, 1144), "FINAL 4:5", font=_font(14), fill=IVORY)
    return canvas
