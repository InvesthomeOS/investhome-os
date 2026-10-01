"""Phase 9.0-R2 — typographic completion of the locked R1 page-cut.

Photography, mask, and spire concept are unchanged.
Typography is fully recomposed across the parchment field.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

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
from investhome_api.services.creative_director.phase9_0_compose import INK, render_pair
from investhome_api.services.creative_director.phase9_0_r1_compose import SPIRE_X, designed_canvas
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
PARENT_R1_ASSET = "5d0a6e9e-f87e-4dcc-bd6d-c6d520baf283"

TYPE_PLAN = {
    "schema": "TypographicPlanR2",
    "field": "parchment page left-upper; type stays left of the spire cut",
    "masthead": "logo breathes at top left; WASHINGTON D.C. is the editorial eyebrow beneath it",
    "headline": "ALIRKEN / KAZAN as two lines with real leading; the dominant gesture in the page",
    "commercial": "%35 + LANSMAN AVANTAJI as a horizontal lockup — counterweight, not a line under the headline",
    "price_unit": "675.000 USD and 2+1 DAİRE as one commercial phrase",
    "closure": "PROJEYİ KEŞFET then editorial line as the ending of the page, above the city dissolve",
    "spire": "hairline in the page continues the spire; no copy on the stone",
}


def r2_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
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
.axis{{position:absolute;left:{axis};top:3.2%;width:1px;height:14%;background:{INK};opacity:.38;}}
.brand{{position:absolute;left:5.0%;top:3.1%;width:318px;height:78px;display:flex;align-items:center;}}
.brand svg{{width:100%;height:100%;display:block;}}
.loc{{position:absolute;left:5.2%;top:10.5%;margin:0;font-family:'Source Sans 3',sans-serif;
  font-size:14px;letter-spacing:.36em;font-weight:500;color:{INK};}}
.line1,.line2{{position:absolute;left:4.6%;margin:0;padding:0;font-family:'Cormorant Garamond',serif;
  font-weight:500;font-size:90px;line-height:1.0;letter-spacing:.035em;color:{INK};}}
.line1{{top:14.2%;}}
.line2{{top:24.2%;}}
.rule{{position:absolute;left:5.2%;top:32.8%;width:38%;height:1px;background:{INK};opacity:.48;}}
.lock{{position:absolute;left:5.0%;top:34.6%;width:36%;height:7.2%;display:flex;align-items:center;gap:22px;color:{INK};}}
.pct{{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:70px;line-height:1;letter-spacing:.02em;white-space:nowrap;}}
.offer{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.20em;font-weight:600;
  line-height:1.4;padding-top:4px;}}
.commercial{{position:absolute;left:5.2%;top:43.0%;font-family:'Cormorant Garamond',serif;font-size:34px;
  letter-spacing:.05em;font-weight:500;color:{INK};white-space:nowrap;}}
.unit{{font-family:'Source Sans 3',sans-serif;font-size:14px;letter-spacing:.20em;margin-left:18px;font-weight:500;}}
.cta{{position:absolute;left:5.2%;top:46.6%;font-family:'Source Sans 3',sans-serif;font-size:13px;
  letter-spacing:.26em;font-weight:600;color:{INK};}}
.ed{{position:absolute;left:5.2%;top:49.0%;width:34%;font-family:'Source Sans 3',sans-serif;font-size:12px;
  letter-spacing:.12em;font-weight:500;color:{INK};opacity:.92;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <div class="axis" data-semantic="spire_axis"></div>
  <div class="brand">{logo_markup}</div>
  <p class="loc">WASHINGTON D.C.</p>
  <p class="line1">ALIRKEN</p>
  <p class="line2">KAZAN</p>
  <div class="rule"></div>
  <div class="lock">
    <div class="pct">{REQUIRED_FACTS["discount"]}</div>
    <div class="offer">{REQUIRED_FACTS["discount_label"].replace(" ", "<br>")}</div>
  </div>
  <div class="commercial">675.000 USD<span class="unit">{unit}</span></div>
  <div class="cta">{REQUIRED_FACTS["cta"]}</div>
  <div class="ed">{APPROVED_BOTTOM_COPY}</div>
</div>
</body>
</html>
"""


def compose_master_02_r2(*, photo: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, Image.Image, str]:
    scene, _meta = designed_canvas(photo)
    registry = build_font_registry()
    html = r2_html(
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
        and "border-radius:999" not in html
        and "#1A2330" not in html
        and "sidebar" not in html.lower()
        and "text-align:center" not in html
    )


def render_type_plan(scene: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1680, 1180), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "02  TYPOGRAPHIC PLAN R2  —  locked page-cut, recomposed type", font=_font(18), fill=GOLD)
    tile = scene.copy()
    tile.thumbnail((620, 900), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    rows = [
        "FIELD  full parchment page, not the upper-left corner",
        "MASTHEAD  logo with air; WASHINGTON D.C. as eyebrow",
        "HEADLINE  ALIRKEN / KAZAN with real leading, toward the spire cut",
        "COMMERCIAL  %35 + LANSMAN AVANTAJI as a lockup",
        "PRICE  675.000 USD + 2+1 DAİRE as one phrase",
        "CLOSURE  CTA then editorial line at the page ending",
        "SPIRE  axis hairline; no copy on the stone",
        "LOCKED  Sunset_001, mask, crop, parchment/photo relationship",
    ]
    y = 70
    for row in rows:
        draw.text((700, y), row[:64], font=_font(16), fill=IVORY)
        y += 36
    return canvas


def render_legibility(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 820), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "05  LEGIBILITY  —  100% crop / 50% / 25%", font=_font(18), fill=GOLD)
    full = image.copy()
    crop = full.crop((0, 0, int(W * 0.52), int(H * 0.56))).resize((560, 620), Image.Resampling.LANCZOS)
    half = image.copy()
    half.thumbnail((int(W * 0.50), int(H * 0.50)), Image.Resampling.LANCZOS)
    quarter = image.copy()
    quarter.thumbnail((int(W * 0.25), int(H * 0.25)), Image.Resampling.LANCZOS)
    canvas.paste(crop.convert("RGB"), (36, 56))
    canvas.paste(half.convert("RGB"), (640, 56))
    canvas.paste(quarter.convert("RGB"), (1280, 56))
    draw.text((36, 690), "100%  page crop", font=_font(14), fill=IVORY)
    draw.text((640, 690), "50%", font=_font(14), fill=IVORY)
    draw.text((1280, 690), "25%  brand / ALIRKEN KAZAN / %35 / price", font=_font(14), fill=IVORY)
    return canvas
