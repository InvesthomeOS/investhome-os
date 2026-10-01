"""Phase 11.8 capability boards. Technical proofs, not advertisements."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.project_object_extraction_v2 import composite_on
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY


def edge_test_board(obj: Image.Image, color: tuple[int, int, int], title: str) -> Image.Image:
    plate, layout = composite_on(obj, color, (1088, 1360))
    x, y, w, h = layout
    # Spire lives in the upper-left third of the object.
    spire = plate.crop((x, y, x + max(80, w // 3), y + max(80, h // 3)))
    zoom = spire.resize((spire.size[0] * 2, spire.size[1] * 2), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), f"OBJECT EXTRACTION V2  —  {title}   100% plate / 200% spire", font=_font(16), fill=GOLD)
    fitted = plate.copy()
    fitted.thumbnail((720, 1040), Image.Resampling.LANCZOS)
    canvas.paste(fitted, (40, 56))
    zoom.thumbnail((1080, 1040), Image.Resampling.LANCZOS)
    canvas.paste(zoom.convert("RGB"), (800, 56))
    draw.text((40, 1116), "100%", font=_font(15), fill=IVORY)
    draw.text((800, 1116), "200% SPIRE EDGE", font=_font(15), fill=IVORY)
    return canvas


def material_test_board(field: Image.Image, raw_obj: Image.Image, matched: Image.Image, fused: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "09  MATERIAL INTEGRATION V2  —  technical proof, not a campaign", font=_font(16), fill=GOLD)
    x = 24
    tiles = (
        ("FIELD", field),
        ("OBJECT MATCHED TO FIELD", _object_tile(matched)),
        ("INTEGRATED (NO COPY)", fused),
    )
    for title, image in tiles:
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(14), fill=IVORY)
        x += 630
    return canvas


def contact_test_board(field: Image.Image, fused: Image.Image, overlay: Image.Image, ambient: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "10  CONTACT / OCCLUSION  —  paper over feet + local shadow, no silhouette drop", font=_font(16), fill=GOLD)
    x = 24
    overlay_rgb = Image.new("RGB", overlay.size, (18, 16, 14))
    overlay_rgb.paste(overlay, (0, 0), overlay)
    amb_rgb = Image.new("RGB", ambient.size, (220, 210, 196))
    amb_rgb.paste(ambient, (0, 0), ambient)
    for title, image in (("FIELD", field), ("INTEGRATED", fused), ("OCCLUSION / CONTACT", amb_rgb)):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(14), fill=IVORY)
        x += 630
    return canvas


def _object_tile(obj: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1088, 1360), (28, 26, 24))
    fitted = obj.copy()
    fitted.thumbnail((900, 1200), Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((1088 - fitted.size[0]) // 2, (1360 - fitted.size[1]) // 2), fitted if fitted.mode == "RGBA" else None)
    return canvas


def hierarchy_scale_board(thumbs: dict[str, Image.Image]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "HIERARCHY V2  —  100 / 50 / 25 / 15   capability test, not a campaign", font=_font(16), fill=GOLD)
    x = 24
    for key, title in (("100", "100%"), ("50", "50%"), ("25", "25%"), ("15", "15%")):
        tile = thumbs[key].copy()
        tile.thumbnail((450, 1040), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(14), fill=IVORY)
        x += 475
    return canvas
