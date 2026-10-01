"""Phase 11.9 review boards. Not production art direction."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.project_object_extraction_v2 import composite_on
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY


def _tile(canvas: Image.Image, image: Image.Image | None, box: tuple[int, int, int, int], title: str, draw: ImageDraw.ImageDraw) -> None:
    x, y, w, h = box
    if image is None:
        draw.rectangle((x, y, x + w, y + h), fill=(28, 24, 20))
        draw.text((x + 16, y + h // 2), "missing", font=_font(16), fill=GOLD)
        return
    tile = image.copy()
    tile.thumbnail((w, h), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (x, y))
    draw.text((x, y + h + 8), title, font=_font(14), fill=IVORY)


def render_asset_opportunity_board(thumbs: dict[str, Image.Image], chosen: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "01  ASSET OPPORTUNITY  —  Day_003 not auto-selected   chosen: " + chosen, font=_font(16), fill=GOLD)
    order = (
        ("Day_001 street volume", "Day_001"),
        ("Day_002 lantern (Master 03)", "Day_002"),
        ("Day_008 plaza (Proof 01/02)", "Day_008"),
        ("Day_009 monument — SELECTED", "Day_009"),
        ("Sunset_001 (Master 02)", "Sunset_001"),
        ("Living_Room_001 listing risk", "Living_Room_001"),
    )
    x, y = 28, 56
    for title, key in order:
        img = thumbs.get(key)
        _tile(canvas, img, (x, y, 280, 400), title, draw)
        x += 310
        if x > 1700:
            x = 28
            y = 520
    draw.text((28, 1128), "Selected for lantern-to-residence mertebe. Not portal crop. Not Day_003 ledger.", font=_font(15), fill=IVORY)
    return canvas


def render_scene_integration_proof(field: Image.Image, obj: Image.Image, fused: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "06  SCENE INTEGRATION V2  —  field / object / integrated (no type)", font=_font(16), fill=GOLD)
    obj_plate = Image.new("RGB", (1088, 1360), (22, 20, 18))
    fitted = obj.copy()
    fitted.thumbnail((900, 1200), Image.Resampling.LANCZOS)
    obj_plate.paste(fitted, ((1088 - fitted.size[0]) // 2, (1360 - fitted.size[1]) // 2), fitted if fitted.mode == "RGBA" else None)
    x = 28
    for title, image in (("GENERATED FIELD", field), ("PROJECT OBJECT", obj_plate), ("INTEGRATED", fused)):
        _tile(canvas, image, (x, 56, 600, 1020), title, draw)
        x += 630
    return canvas


def render_typography_system(final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "07  TYPOGRAPHY  —  three altitudes of one register, not a type specimen", font=_font(16), fill=GOLD)
    tile = final.copy()
    tile.thumbnail((760, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    lines = [
        "Identity: THE TEMPLE names the instrument.",
        "Headline: MERTEBE — lantern-to-residence degree.",
        "High altitude: %35 in the shaft, occluded by stone.",
        "Inhabited altitude: 675.000 USD + 2+1 DAİRE.",
        "Contact: PROJEYİ KEŞFET + hairline cue.",
        "No vertical spine. No badge. No button. No fact stack.",
        "Logo: real Temple mark, light treatment on dark field.",
    ]
    y = 70
    for line in lines:
        draw.text((840, y), line, font=_font(18), fill=IVORY)
        y += 44
    return canvas


def render_commercial_hierarchy(final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "08  COMMERCIAL HIERARCHY V2  —  object → hook → value/product → action", font=_font(16), fill=GOLD)
    tile = final.copy()
    tile.thumbnail((760, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    path = [
        ("1 PROJECT", "Temple object + THE TEMPLE / MERTEBE"),
        ("2 OPPORTUNITY", "%35 at lantern altitude"),
        ("3 VALUE", "675.000 USD at inhabited mass"),
        ("4 PRODUCT", "2+1 DAİRE on the same altitude"),
        ("5 ACTION", "PROJEYİ KEŞFET at contact"),
    ]
    y = 80
    for title, note in path:
        draw.text((840, y), title, font=_font(22), fill=GOLD)
        draw.text((840, y + 32), note, font=_font(18), fill=IVORY)
        y += 96
    draw.text((840, 720), "15%: identity + visual idea + %35 + action cue.", font=_font(16), fill=IVORY)
    draw.text((840, 752), "25%: price and unit readable as one altitude.", font=_font(16), fill=IVORY)
    return canvas


def render_reference_quality_board(references: dict[str, Image.Image], final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "12  REFERENCE QUALITY  —  Grade-A craft beside Hybrid V2  (do not copy layouts)", font=_font(16), fill=GOLD)
    names = ("ORNEK_00013", "ORNEK_00011", "ORNEK_00006", "ORNEK_00008", "HYBRID V2")
    images = [
        references.get("ORNEK_00013.jpg"),
        references.get("ORNEK_00011.jpg"),
        references.get("ORNEK_00006.jpg"),
        references.get("ORNEK_00008.jpg"),
        final,
    ]
    x = 24
    for title, image in zip(names, images):
        _tile(canvas, image, (x, 56, 350, 1020), title, draw)
        x += 378
    return canvas


def render_quality_progression_board(
    old: Image.Image | None,
    v1: Image.Image | None,
    r1: Image.Image | None,
    v2: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "15  QUALITY PROGRESSION  —  A old-compiler   B Hybrid V1   C V1 R1   D Hybrid V2", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("A  OLD COMPILER", old), ("B  HYBRID V1", v1), ("C  V1 R1", r1), ("D  HYBRID V2", v2)):
        _tile(canvas, image, (x, 56, 450, 1020), title, draw)
        x += 472
    return canvas


def render_human_review_board(final: Image.Image, thumb15: Image.Image, thumb25: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "16  HUMAN REVIEW  —  Hybrid V2  PENDING HUMAN REVIEW   not a Master", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("FINAL 4:5", final), ("15%", thumb15), ("25%", thumb25)):
        _tile(canvas, image, (x, 56, 600, 1020), title, draw)
        x += 630
    return canvas


def object_edge_plate(obj: Image.Image, color: tuple[int, int, int] = (18, 16, 14)) -> Image.Image:
    plate, _layout = composite_on(obj, color, (1088, 1360))
    return plate


def thumbnail(image: Image.Image, scale: float) -> Image.Image:
    return image.resize(
        (max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale))),
        Image.Resampling.LANCZOS,
    )
