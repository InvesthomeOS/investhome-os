"""Phase 9.1-R1 — Looking Chamber spatial reveal.

The interior is the chamber. The right wall opens. The Temple exterior
is the architectural world the room looks toward.
"""

from __future__ import annotations

import os
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase9_0_compose import render_pair
from investhome_api.services.creative_director.phase9_1_compose import (
    ARCHITECTURE_ASSET_ID,
    ARCHITECTURE_FILENAME,
    INTERIOR_ASSET_ID,
    INTERIOR_FILENAME,
    ORNEK_ASSET_ID,
    ORNEK_FILENAME,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
INK_LIGHT = "#F4E6D2"
INK_MUTED = "#CDB89A"
INK_ROOM = "#2A1F16"

PARENT_MASTER_03_ASSET = "cdad2256-4b1c-41cc-b340-0d26badd47ab"

INTERIOR_CENTERING = (0.30, 0.40)
ARCHITECTURE_CENTERING = (0.66, 0.28)
INTERIOR_GRADE = {"warmth": 0.07, "contrast": 1.05, "brightness": 0.97, "vignette": 0.08}
ARCHITECTURE_GRADE = {"warmth": 0.03, "contrast": 1.07, "brightness": 1.00, "vignette": 0.04}

# Spatial opening: wider at the top, floor of the chamber continues underneath.
OPEN_TOP_X = 0.50
OPEN_BOT_X = 0.57
OPEN_FLOOR = 0.84
CEILING_FADE = 0.24

CONCEPT_R1 = {
    "schema": "CreativeConceptMaster03R1",
    "concept_name": "LOOKING_CHAMBER",
    "mechanism_sentence": (
        "The real interior is a photographic chamber whose right wall opens as a vertical "
        "spatial reveal, so the real Temple exterior is the architectural world the room looks toward."
    ),
    "visual_gesture": (
        "Interior mass holds left and floor. Ceiling dissolves into atmosphere. "
        "A tall unframed opening on the right reveals Temple architecture at scale."
    ),
    "not": [
        "picture-in-picture card",
        "rounded photo frame",
        "full-width dark header rectangle",
        "parchment page-cut",
        "full-bleed sky typography",
    ],
}

DISTINCTNESS_PRE = {
    "IS_THIS_FUNDAMENTALLY_DIFFERENT_FROM_MASTER_01": "YES",
    "IS_THIS_FUNDAMENTALLY_DIFFERENT_FROM_MASTER_02": "YES",
    "DOES_THE_CONCEPT_EXIST_WITHOUT_COPY": "YES",
    "IS_THERE_A_CLEAR_VISUAL_MECHANISM": "YES",
}


def crop_interior(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=INTERIOR_CENTERING)
    graded = apply_photographic_grade(crop, dict(INTERIOR_GRADE))
    transform = dict(transform)
    transform["centering"] = list(INTERIOR_CENTERING)
    transform["role"] = "chamber"
    return graded, transform


def crop_architecture(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=ARCHITECTURE_CENTERING)
    graded = apply_photographic_grade(crop, dict(ARCHITECTURE_GRADE))
    transform = dict(transform)
    transform["centering"] = list(ARCHITECTURE_CENTERING)
    transform["role"] = "architectural_reveal"
    return graded, transform


def _atmosphere() -> Image.Image:
    band = Image.new("RGB", (1, H))
    pix = band.load()
    for y in range(H):
        t = y / max(H - 1, 1)
        pix[0, y] = (
            int(22 + t * 18),
            int(16 + t * 14),
            int(12 + t * 10),
        )
    image = band.resize((W, H), Image.Resampling.BILINEAR)
    noise = Image.frombytes("L", (W, H), os.urandom(W * H))
    return Image.blend(image, Image.merge("RGB", (noise, noise, noise)), 0.055)


def _opening_polygon() -> list[tuple[int, int]]:
    top_x = int(W * OPEN_TOP_X)
    bot_x = int(W * OPEN_BOT_X)
    floor = int(H * OPEN_FLOOR)
    return [(top_x, 0), (W, 0), (W, floor), (bot_x, floor)]


def reveal_mask() -> Image.Image:
    """White = Temple exterior shows. Soft spatial opening, no frame."""
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(_opening_polygon(), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=28))


def interior_mask() -> Image.Image:
    """White = real interior. Opening is empty. Ceiling dissolves into atmosphere on the left."""
    mask = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(mask)
    draw.polygon(_opening_polygon(), fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=28))
    fade = Image.new("L", (W, H), 255)
    fade_h = int(H * CEILING_FADE)
    fp = fade.load()
    open_guard = int(W * (OPEN_TOP_X - 0.04))
    for y in range(fade_h):
        t = y / max(fade_h - 1, 1)
        val = int(255 * (t ** 1.25))
        for x in range(max(1, open_guard)):
            fp[x, y] = val
    return ImageChops.multiply(mask, fade)


def designed_chamber(*, interior: Image.Image, architecture: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """Atmosphere + chamber mass + architectural reveal. Must read as Looking Chamber without type."""
    canvas = _atmosphere()
    canvas.paste(architecture.convert("RGB"), (0, 0), reveal_mask())
    canvas.paste(interior.convert("RGB"), (0, 0), interior_mask())
    meta = {
        "open_top_x": OPEN_TOP_X,
        "open_bot_x": OPEN_BOT_X,
        "open_floor": OPEN_FLOOR,
        "ceiling_fade": CEILING_FADE,
        "interior": INTERIOR_FILENAME,
        "architecture": ARCHITECTURE_FILENAME,
        "concept": CONCEPT_R1["concept_name"],
        "mechanism": CONCEPT_R1["mechanism_sentence"],
    }
    return canvas, meta


def r1_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#16110d;}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.scene{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;}}
.brand{{position:absolute;left:4.6%;top:3.0%;width:252px;height:62px;}}
.brand svg{{width:252px;height:62px;display:block;filter:brightness(0) invert(1);opacity:.92;}}
.loc{{position:absolute;left:4.8%;top:9.2%;margin:0;color:{INK_MUTED};
  font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.36em;font-weight:500;}}
.line1,.line2{{position:absolute;left:4.5%;margin:0;padding:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-weight:500;font-size:74px;line-height:.94;letter-spacing:.035em;}}
.line1{{top:12.0%;}}
.line2{{top:19.0%;}}
.commercial{{position:absolute;left:4.8%;top:27.6%;display:flex;align-items:center;gap:14px;color:{INK_LIGHT};}}
.pct{{font-family:'Cormorant Garamond',serif;font-size:50px;font-weight:500;line-height:.9;}}
.offer{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.20em;font-weight:600;line-height:1.35;}}
.price{{position:absolute;left:4.8%;top:33.2%;margin:0;color:{INK_LIGHT};
  font-family:'Cormorant Garamond',serif;font-size:24px;font-weight:500;letter-spacing:.06em;}}
.unit{{margin-left:12px;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.16em;font-weight:600;opacity:.9;}}
.cta{{position:absolute;left:4.8%;top:36.2%;margin:0;color:{INK_MUTED};
  font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.28em;font-weight:600;}}
.ed{{position:absolute;left:4.8%;top:38.0%;margin:0;color:{INK_MUTED};
  font-family:'Cormorant Garamond',serif;font-size:14px;letter-spacing:.06em;font-weight:500;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <div class="brand">{logo_markup}</div>
  <p class="loc">WASHINGTON D.C.</p>
  <p class="line1">ALIRKEN</p>
  <p class="line2">KAZAN</p>
  <div class="commercial">
    <div class="pct">%35</div>
    <div class="offer">LANSMAN<br>AVANTAJI</div>
  </div>
  <p class="price">675.000 USD<span class="unit">{unit}</span></p>
  <p class="cta">{REQUIRED_FACTS["cta"]}</p>
  <p class="ed">{APPROVED_BOTTOM_COPY}</p>
</div>
</body>
</html>
"""


def compose_master_03_r1(*, interior: Image.Image, architecture: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, Image.Image, str, dict[str, Any]]:
    chamber, meta = designed_chamber(interior=interior, architecture=architecture)
    registry = build_font_registry()
    html = r1_html(
        scene_uri=_jpeg_data_uri(chamber, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
    )
    image = render_html_to_png(html, width=W, height=H).convert("RGB")
    return image, chamber, html, meta


def html_copy_ok(html: str) -> bool:
    needed = (
        "ALIRKEN",
        "KAZAN",
        "%35",
        "LANSMAN",
        "AVANTAJI",
        "675.000 USD",
        "2+1",
        "DAİRE",
        "PROJEYİ KEŞFET",
        APPROVED_BOTTOM_COPY,
        "WASHINGTON D.C.",
    )
    return (
        all(token in html for token in needed)
        and "THE TEMPLE" not in html
        and "investhome" not in html.lower()
        and "uniloft" not in html.lower()
        and "text-align:center" not in html
        and "#ead3b3" not in html
        and "border-radius" not in html
    )


def render_mechanism(chamber: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1560), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "05  CREATIVE MECHANISM  —  chamber opens toward the Temple", font=_font(18), fill=GOLD)
    tile = chamber.copy()
    tile.thumbnail((1128, 1360), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    draw.text((36, 1440), "LOOKING CHAMBER  no type  spatial reveal", font=_font(15), fill=IVORY)
    draw.text((36, 1472), CONCEPT_R1["mechanism_sentence"][:88], font=_font(13), fill=GOLD)
    return canvas


def render_labeled_asset(image: Image.Image, title: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1480), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((1128, 1360), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    draw.text((36, 1436), caption[:72], font=_font(14), fill=IVORY)
    return canvas
