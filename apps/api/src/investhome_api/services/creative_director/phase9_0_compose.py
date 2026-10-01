"""Phase 9.0 — Premium Campaign 02 compositor.

Photo + graphic field merge. Real Sunset_001 pixels. Not Master 01. Not a panel.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

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
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
INK = "#2A1F16"
SUNSET_ASSET_ID = "65f68756-a006-43d4-9c86-2c0ec25ad229"
SUNSET_FILENAME = "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg"
ORNEK_FILENAME = "ORNEK_00012.jpg"
ORNEK_ASSET_ID = "f73556b5-e8a7-4c20-b874-0a6aef2a5570"
CENTERING = (0.50, 0.32)
GRADE = {"warmth": 0.10, "contrast": 1.08, "brightness": 0.98, "vignette": 0.10}

SHORTLIST = (
    ("IH_DC_TMP_001_Render_Exterior_Day_001.jpg", "5d26caf3-c237-4a78-9f3a-91f05dd24fa2", "street monument"),
    ("IH_DC_TMP_001_Render_Exterior_Day_002.jpg", "543aeb03-c4c9-46f9-9d9f-81bf53f45438", "street spire"),
    ("IH_DC_TMP_001_Render_Exterior_Day_004.jpg", "299bd265-a0ea-486d-866d-1947f103fd57", "daylight aerial"),
    ("IH_DC_TMP_001_Render_Exterior_Day_008.jpg", "2d44757b-079c-4a78-a4a9-5fe6370466c8", "lifestyle steps"),
    ("IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg", SUNSET_ASSET_ID, "SELECTED — dusk merge"),
    ("IH_DC_TMP_001_Render_Living_Room_005.jpg", "8837fa06-d71b-4c26-a5cb-9cb682748311", "interior considered"),
)


def crop_sunset(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=CENTERING)
    graded = apply_photographic_grade(crop, dict(GRADE))
    transform = dict(transform)
    transform["centering"] = list(CENTERING)
    transform["note"] = "Sunset_001 cover-fit. Spire as hinge. Warm sky reserved for atmospheric field merge."
    return graded, transform


def master_html(*, photo_uri: str, logo_markup: str, font_css: str) -> str:
    offer = f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#1a1410;}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.photo{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;}}
.field{{position:absolute;inset:0;pointer-events:none;
  background:
    radial-gradient(90% 48% at 50% 8%, rgba(255,214,170,.35) 0%, rgba(255,214,170,0) 70%),
    linear-gradient(180deg,
      rgba(248,228,204,.985) 0%,
      rgba(244,216,186,.96) 10%,
      rgba(238,196,156,.88) 18%,
      rgba(228,168,118,.58) 26%,
      rgba(210,132,78,.28) 34%,
      rgba(186,108,62,.10) 41%,
      rgba(140,70,40,.00) 49%);}}
.grain{{position:absolute;inset:0;pointer-events:none;opacity:.16;
  -webkit-mask-image:linear-gradient(180deg,#000 0%,#000 20%,transparent 48%);
  mask-image:linear-gradient(180deg,#000 0%,#000 20%,transparent 48%);}}
.column{{position:absolute;left:7%;right:7%;top:3.6%;display:flex;flex-direction:column;align-items:center;text-align:center;color:{INK};}}
.brand{{width:320px;height:64px;margin:0 auto 18px auto;display:flex;align-items:center;justify-content:center;}}
.brand svg{{width:100%;height:100%;max-width:320px;max-height:64px;display:block;}}
.loc{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.42em;font-weight:500;margin:0 0 16px 0;}}
.headline{{margin:0;}}
.line1,.line2{{margin:0;padding:0;font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:88px;line-height:.88;letter-spacing:.045em;}}
.rule{{width:64px;height:1px;background:{INK};margin:18px auto 20px auto;opacity:.62;}}
.pair{{display:flex;align-items:stretch;justify-content:center;gap:28px;margin:0 0 22px 0;}}
.divider{{width:1px;background:{INK};opacity:.28;}}
.offer{{font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:600;letter-spacing:.04em;
  display:flex;align-items:center;text-align:right;white-space:nowrap;}}
.pricebox{{display:flex;flex-direction:column;justify-content:center;text-align:left;gap:5px;}}
.price{{font-family:'Cormorant Garamond',serif;font-size:24px;font-weight:500;letter-spacing:.08em;line-height:1;}}
.unit{{font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.22em;font-weight:500;}}
.cta{{font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.28em;font-weight:600;margin-top:2px;}}
.cta-rule{{width:40px;height:1px;background:{INK};margin:10px auto 0 auto;opacity:.55;}}
.ed{{font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.16em;font-weight:500;margin-top:14px;opacity:.88;}}
</style>
</head>
<body>
<div class="stage">
  <img class="photo" data-semantic="project_photo" alt="" src="{photo_uri}"/>
  <div class="field" data-semantic="atmospheric_field"></div>
  <svg class="grain" xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" aria-hidden="true">
    <filter id="paper" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <rect width="100%" height="100%" filter="url(#paper)"/>
  </svg>
  <div class="column">
    <div class="brand">{logo_markup}</div>
    <p class="loc">WASHINGTON D.C.</p>
    <div class="headline">
      <p class="line1">ALIRKEN</p>
      <p class="line2">KAZAN</p>
    </div>
    <div class="rule"></div>
    <div class="pair">
      <div class="offer">{offer}</div>
      <div class="divider"></div>
      <div class="pricebox">
        <div class="price">675.000 USD</div>
        <div class="unit">{REQUIRED_FACTS["unit"]} {REQUIRED_FACTS["unit_label"]}</div>
      </div>
    </div>
    <div class="cta">{REQUIRED_FACTS["cta"]}<div class="cta-rule"></div></div>
    <div class="ed">{APPROVED_BOTTOM_COPY}</div>
  </div>
</div>
</body>
</html>
"""


def compose_master_02(*, photo: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, str]:
    registry = build_font_registry()
    html = master_html(
        photo_uri=_jpeg_data_uri(photo, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
    )
    image = render_html_to_png(html, width=W, height=H).convert("RGB")
    return image, html


def render_shortlist(items: list[tuple[str, Image.Image, str]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "02  TEMPLE PHOTO SHORTLIST  —  scored for ORNEK_00012 dusk-field merge", font=_font(18), fill=GOLD)
    x, y = 36, 56
    for i, (label, image, note) in enumerate(items[:6]):
        tile = image.copy()
        tile.thumbnail((580, 420), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + 430), f"{label[:42]}", font=_font(13), fill=IVORY)
        draw.text((x, y + 450), note[:48], font=_font(13), fill=GOLD)
        x += 620
        if i == 2:
            x, y = 36, 540
    return canvas


def render_assets(photo: Image.Image, logo_rgba: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1680, 980), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "03  SELECTED PROJECT ASSETS  —  Sunset_001 + real Temple logo", font=_font(18), fill=GOLD)
    tile = photo.copy()
    tile.thumbnail((1080, 860), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    logo = logo_rgba.convert("RGBA")
    logo.thumbnail((420, 220), Image.Resampling.LANCZOS)
    plate = Image.new("RGB", (480, 280), (244, 230, 210))
    px = (480 - logo.size[0]) // 2
    py = (280 - logo.size[1]) // 2
    plate.paste(logo, (px, py), logo)
    canvas.paste(plate, (1160, 80))
    draw.text((1160, 380), "LOCKED LOGO  7b58877e…", font=_font(14), fill=IVORY)
    draw.text((1160, 410), SUNSET_FILENAME[:42], font=_font(14), fill=IVORY)
    draw.text((1160, 440), SUNSET_ASSET_ID, font=_font(13), fill=GOLD)
    return canvas


def render_pair(left: Image.Image, right: Image.Image, left_label: str, right_label: str, title: str) -> Image.Image:
    canvas = Image.new("RGB", (1760, 1180), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    x = 36
    for label, image in ((left_label, left), (right_label, right)):
        tile = image.copy()
        tile.thumbnail((820, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1100), label[:52], font=_font(16), fill=IVORY)
        x += 860
    return canvas


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
    )
