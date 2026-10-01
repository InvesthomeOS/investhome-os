"""Phase 9.0-R1 — Premium Campaign 02 composition rebuild.

The campaign is a warm editorial page that the Temple rises through.
The spire is the cut. Not photo-plus-centered-type.
"""

from __future__ import annotations

import os
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase9_0_compose import (
    INK,
    ORNEK_ASSET_ID,
    ORNEK_FILENAME,
    SUNSET_ASSET_ID,
    SUNSET_FILENAME,
    crop_sunset,
    render_pair,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
SPIRE_X = 0.483
PAGE_RIGHT = 0.455
CITY_TOP = 0.50
PARENT_MASTER_02_ASSET = "90e8dd65-1593-444f-9dc6-4a8c1d19bc78"

CONCEPT = {
    "schema": "CreativeConceptR1",
    "concept_name": "SPIRE_CUT_PAGE",
    "concept_sentence": (
        "The campaign uses a warm editorial page that the Temple rises through, "
        "so the spire becomes the cut between designed field and photographed city."
    ),
    "visual_gesture": (
        "Inverted-L photographic mass. Parchment page occupies the left-upper canvas. "
        "The spire remains photographic and cuts the page as a vertical seam."
    ),
    "photo_graphic_relationship": (
        "Sunset_001 is not a full-bleed rectangle. The city holds the lower canvas; "
        "the right sky stays photographic; the left-upper is a designed page. "
        "Soft dissolves at both seams. The photograph is a shaped mass, not a background."
    ),
    "spire_role": (
        "Editorial axis and cut. A hairline in the page continues the spire’s geometry. "
        "Headline lives to the left of the cut. The spire is not avoided; it authors the split."
    ),
    "headline_relationship": (
        "ALIRKEN KAZAN is left-aligned in the page, large, written against the spire cut — "
        "not a caption in the sky."
    ),
    "commercial_information_strategy": (
        "%35 is a graphic numeral in the page rhythm. LANSMAN AVANTAJI is its voice. "
        "Price and unit lock as one commercial phrase, not listing rows."
    ),
    "why_this_is_not_photo_plus_text": (
        "Remove the copy and the canvas still holds a parchment page, an L-shaped "
        "photographic world, and a spire cutting the page. That is a designed composition."
    ),
}


def _parchment(size: tuple[int, int]) -> Image.Image:
    width, height = size
    band = Image.new("RGB", (1, height))
    pix = band.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        pix[0, y] = (
            int(246 - t * 22),
            int(226 - t * 48),
            int(198 - t * 62),
        )
    image = band.resize((width, height), Image.Resampling.BILINEAR)
    noise = Image.frombytes("L", (width, height), os.urandom(width * height))
    return Image.blend(image, Image.merge("RGB", (noise, noise, noise)), 0.06)


def photo_page_mask(size: tuple[int, int] = CANVAS_4X5) -> Image.Image:
    """White = real Sunset_001 pixels. Black = editorial page. Soft seams. Spire stays photographic."""
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    city_y = int(height * CITY_TOP)
    page_x = int(width * PAGE_RIGHT)
    spire_px = int(width * SPIRE_X)
    draw.rectangle((0, city_y, width, height), fill=255)
    draw.rectangle((page_x, 0, width, city_y + 8), fill=255)
    draw.ellipse(
        (spire_px - int(width * 0.10), int(height * 0.08), spire_px + int(width * 0.11), int(height * 0.58)),
        fill=255,
    )
    return mask.filter(ImageFilter.GaussianBlur(radius=42))


def designed_canvas(photo: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """Parchment page + masked real photograph. This object must read as design without type."""
    page = _parchment(CANVAS_4X5)
    mask = photo_page_mask(CANVAS_4X5)
    canvas = page.copy()
    canvas.paste(photo.convert("RGB"), (0, 0), mask)
    meta = {
        "spire_x": SPIRE_X,
        "page_right": PAGE_RIGHT,
        "city_top": CITY_TOP,
        "mask_blur": 42,
        "note": "Real Sunset_001 pixels only. Mask hides photo; it does not generate architecture.",
    }
    return canvas, meta


def r1_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
    offer_label = REQUIRED_FACTS["discount_label"]
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    axis = f"{SPIRE_X * 100:.2f}%"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#ead3b3;}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.scene{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;}}
.axis{{position:absolute;left:{axis};top:3.6%;width:1px;height:12.5%;background:{INK};opacity:.42;}}
.page{{position:absolute;left:0;top:0;width:44%;height:49%;color:{INK};}}
.brand{{position:absolute;left:6.4%;top:3.8%;width:250px;height:54px;display:flex;align-items:center;}}
.brand svg{{width:100%;height:100%;display:block;}}
.loc{{position:absolute;left:6.6%;top:9.1%;margin:0;font-family:'Source Sans 3',sans-serif;
  font-size:12px;letter-spacing:.38em;font-weight:500;}}
.line1,.line2{{position:absolute;left:5.8%;margin:0;padding:0;font-family:'Cormorant Garamond',serif;
  font-weight:500;font-size:76px;line-height:.86;letter-spacing:.03em;}}
.line1{{top:12.2%;}}
.line2{{top:17.8%;}}
.rule{{position:absolute;left:6.6%;top:24.6%;width:52px;height:1px;background:{INK};opacity:.55;}}
.pct{{position:absolute;left:6.2%;top:26.2%;font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:78px;line-height:.9;letter-spacing:.02em;}}
.offer{{position:absolute;left:6.6%;top:33.6%;font-family:'Source Sans 3',sans-serif;font-size:13px;
  letter-spacing:.22em;font-weight:600;}}
.commercial{{position:absolute;left:6.6%;top:37.0%;font-family:'Cormorant Garamond',serif;font-size:22px;
  letter-spacing:.06em;font-weight:500;}}
.unit{{font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.18em;margin-left:14px;font-weight:500;}}
.cta{{position:absolute;left:6.6%;top:41.2%;font-family:'Source Sans 3',sans-serif;font-size:12px;
  letter-spacing:.26em;font-weight:600;}}
.ed{{position:absolute;left:6.6%;top:44.4%;width:36%;font-family:'Source Sans 3',sans-serif;font-size:11px;
  letter-spacing:.12em;font-weight:500;opacity:.9;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <div class="axis" data-semantic="spire_axis"></div>
  <div class="page">
    <div class="brand">{logo_markup}</div>
    <p class="loc">WASHINGTON D.C.</p>
    <p class="line1">ALIRKEN</p>
    <p class="line2">KAZAN</p>
    <div class="rule"></div>
    <div class="pct">{REQUIRED_FACTS["discount"]}</div>
    <div class="offer">{offer_label}</div>
    <div class="commercial">675.000 USD<span class="unit">{unit}</span></div>
    <div class="cta">{REQUIRED_FACTS["cta"]}</div>
    <div class="ed">{APPROVED_BOTTOM_COPY}</div>
  </div>
</div>
</body>
</html>
"""


def compose_master_02_r1(*, photo: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, Image.Image, str]:
    scene, _meta = designed_canvas(photo)
    registry = build_font_registry()
    html = r1_html(
        scene_uri=_jpeg_data_uri(scene, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
    )
    image = render_html_to_png(html, width=W, height=H).convert("RGB")
    return image, scene, html


def html_copy_ok(html: str) -> bool:
    needed = (
        "ALIRKEN",
        "KAZAN",
        "%35",
        "LANSMAN AVANTAJI",
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
        and "border-radius:999" not in html
        and "#1A2330" not in html
        and "sidebar" not in html.lower()
        and "text-align:center" not in html
    )


def render_logo_plate(logo_rgba: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1088, 420), (243, 226, 200))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "03  REAL TEMPLE LOGO", font=_font(18), fill=(42, 31, 22))
    mark = logo_rgba.convert("RGBA")
    mark.thumbnail((720, 280), Image.Resampling.LANCZOS)
    canvas.paste(mark, ((1088 - mark.size[0]) // 2, 80), mark)
    return canvas


def render_concept_board() -> Image.Image:
    rows = [
        f"NAME  {CONCEPT['concept_name']}",
        f"SENTENCE  {CONCEPT['concept_sentence']}",
        f"GESTURE  {CONCEPT['visual_gesture']}",
        f"PHOTO/GRAPHIC  {CONCEPT['photo_graphic_relationship']}",
        f"SPIRE  {CONCEPT['spire_role']}",
        f"HEADLINE  {CONCEPT['headline_relationship']}",
        f"COMMERCIAL  {CONCEPT['commercial_information_strategy']}",
        f"WITHOUT COPY  {CONCEPT['why_this_is_not_photo_plus_text']}",
    ]
    canvas = Image.new("RGB", (1680, 1480), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "04  CREATIVE CONCEPT R1  —  SPIRE CUT PAGE", font=_font(20), fill=GOLD)
    y = 80
    for row in rows:
        words = row.split()
        line = ""
        for word in words:
            trial = (line + " " + word).strip()
            if len(trial) > 92:
                draw.text((40, y), line, font=_font(16), fill=IVORY)
                y += 28
                line = word
            else:
                line = trial
        if line:
            draw.text((40, y), line, font=_font(16), fill=IVORY)
            y += 40
    return canvas
