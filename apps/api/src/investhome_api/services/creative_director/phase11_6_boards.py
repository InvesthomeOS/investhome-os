"""Review boards for Phase 11.6. Not production art direction."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY


def render_composition_development(
    field: Image.Image,
    obj_plate: Image.Image,
    composed: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (16, 14, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "08  COMPOSITION DEVELOPMENT  —  field / object / field+object (no type)", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (
        ("GENERATED FIELD", field),
        ("REAL OBJECT", obj_plate),
        ("FIELD + OBJECT", composed),
    ):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(15), fill=IVORY)
        x += 630
    return canvas


def render_comparison_board(
    proof_01: Image.Image | None,
    proof_02: Image.Image | None,
    proof_03: Image.Image | None,
    hybrid: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (16, 14, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "10  PROOF COMPARISON  —  overlay compiler vs hybrid engine", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (
        ("PROOF 01  letter", proof_01),
        ("PROOF 02  seam", proof_02),
        ("PROOF 03  threshold", proof_03),
        ("HYBRID  ledger", hybrid),
    ):
        if image is None:
            draw.rectangle((x, 56, x + 450, 1080), fill=(28, 24, 20))
            draw.text((x + 24, 520), "missing", font=_font(18), fill=GOLD)
        else:
            tile = image.copy()
            tile.thumbnail((450, 1020), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(14), fill=IVORY)
        x += 472
    return canvas


def render_human_review_board(
    field: Image.Image,
    obj_plate: Image.Image,
    proof: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (16, 14, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "13  HUMAN REVIEW  —  Hybrid Premium Proof  PENDING HUMAN REVIEW", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("FIELD", field), ("OBJECT", obj_plate), ("FINAL", proof)):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1108), title, font=_font(15), fill=IVORY)
        x += 630
    return canvas
