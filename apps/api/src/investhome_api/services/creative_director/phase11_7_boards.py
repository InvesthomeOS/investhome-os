"""Phase 11.7 review boards and finish studies."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY


def render_material_study(field: Image.Image, obj_plate: Image.Image, fused: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "04  MATERIAL INTEGRATION  —  field / isolated object / paper-occluded fuse", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("FIELD RETAINED", field), ("OBJECT R1", obj_plate), ("FUSE + PAPER OCCLUSION", fused)):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(15), fill=IVORY)
        x += 630
    return canvas


def render_type_study(r1: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "05  TYPOGRAPHY FINISH  —  identity on field / offer on plate / CTA completes the paper", font=_font(16), fill=GOLD)
    tile = r1.copy()
    tile.thumbnail((760, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    lines = [
        "Removed: vertical price spine (unreadable at 15%).",
        "Removed: CTA under headline (action arrived before value).",
        "Plate: %35 is the printed instrument.",
        "Plate: 675.000 USD + 2+1 DAİRE share one value line.",
        "Plate: PROJEYİ KEŞFET is the last beat, tracked, not a button.",
        "Field: THE TEMPLE / WASHINGTON D.C. / TAŞ TEMİNAT.",
        "Logo: dark mark on vellum, not inverted white on cream.",
        "No absolute fact boxes. No badge. No price card.",
    ]
    y = 70
    for line in lines:
        draw.text((840, y), line, font=_font(18), fill=IVORY)
        y += 42
    return canvas


def render_hierarchy_study(r1: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "06  COMMERCIAL HIERARCHY  —  PROJECT → OPPORTUNITY → VALUE → PRODUCT → ACTION", font=_font(16), fill=GOLD)
    tile = r1.copy()
    tile.thumbnail((760, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    path = [
        ("1 PROJECT", "Temple object + THE TEMPLE"),
        ("2 OPPORTUNITY", "%35 on the vellum plate"),
        ("3 VALUE", "675.000 USD on the same plate"),
        ("4 PRODUCT", "2+1 DAİRE in the value line"),
        ("5 ACTION", "PROJEYİ KEŞFET closes the instrument"),
    ]
    y = 80
    for title, note in path:
        draw.text((840, y), title, font=_font(22), fill=GOLD)
        draw.text((840, y + 32), note, font=_font(18), fill=IVORY)
        y += 96
    draw.text((840, 720), "15%: spire + %35 must survive.", font=_font(16), fill=IVORY)
    draw.text((840, 752), "25%: price and unit must be readable as one line.", font=_font(16), fill=IVORY)
    return canvas


def render_side_by_side(original: Image.Image, r1: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "09  BLIND SIDE-BY-SIDE  —  A  original hybrid   B  finish R1", font=_font(16), fill=GOLD)
    x = 80
    for title, image in (("A", original), ("B", r1)):
        tile = image.copy()
        tile.thumbnail((820, 1040), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1112), title, font=_font(22), fill=GOLD)
        x += 920
    return canvas


def render_human_board(original: Image.Image, r1: Image.Image, thumb: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "13  HUMAN REVIEW  —  Hybrid Finish R1  PENDING HUMAN REVIEW", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("A  11.6", original), ("B  R1", r1), ("R1  15%", thumb)):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(15), fill=IVORY)
        x += 630
    return canvas


def thumbnail(image: Image.Image, scale: float = 0.15) -> Image.Image:
    return image.resize(
        (max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale))),
        Image.Resampling.LANCZOS,
    )
