"""Phase 8.1 — one curated Temple Premium Master. Controlled construction, not generation."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import font_face_css, render_html_to_png
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_2_doctrine import PHOTO_MAX_MASS, PHOTO_MIN_MASS, TERRITORIES_72
from investhome_api.services.creative_director.phase7_2_photo_object import (
    clamp_photo_mass,
    paste_real_logo,
    photo_percentage,
    place_photo_object,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5

# Curated once. Not a family of seeded experiments.
MASTER_LAYOUT: dict[str, Any] = {
    "photo_role": "lower_left_architectural_object",
    "photo_shape": "rect",
    "photo_box": {"x": 0.0, "y": 0.34, "w": 0.64, "h": 0.56},
    "centering": (0.52, 0.32),
    "brand_box": {"x": 0.70, "y": 0.80, "w": 0.24, "h": 0.09},
    "headline": {"x": 0.386, "y": 0.047, "w": 0.57, "h": 0.20},
    "offer": {"x": 0.680, "y": 0.265, "w": 0.28, "h": 0.13},
    "price": {"x": 0.680, "y": 0.430, "w": 0.28, "h": 0.08},
    "unit": {"x": 0.680, "y": 0.530, "w": 0.26, "h": 0.06},
    "cta": {"x": 0.680, "y": 0.675, "w": 0.26, "h": 0.06},
    "closure": {"x": 0.08, "y": 0.918, "w": 0.84, "h": 0.045},
    "grade": {"warmth": 0.10, "contrast": 1.08, "brightness": 0.97},
}


def locked_layout() -> dict[str, Any]:
    layout = dict(MASTER_LAYOUT)
    layout["photo_box"] = clamp_photo_mass(dict(MASTER_LAYOUT["photo_box"]))
    return layout


def master_field_html(font_css: str) -> str:
    """Dark campaign field + live type. Photo slot stays empty for immutable paste."""
    gold = f"rgb{GOLD}"
    ivory = f"rgb{IVORY}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;background:#0b0d11;overflow:hidden;}}
.stage{{position:relative;width:{W}px;height:{H}px;
  background:radial-gradient(ellipse at 22% 78%, #181b22 0%, #0b0d11 46%);}}
.headline{{position:absolute;left:420px;top:58px;width:620px;}}
.line1,.line2{{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:104px;line-height:.90;
  letter-spacing:.035em;margin:0;padding:0;}}
.line1{{color:{ivory};}}
.line2{{color:{gold};}}
.rule{{width:152px;height:1px;background:{gold};margin:20px 0 0 2px;opacity:.88;}}
.offer{{position:absolute;left:740px;top:360px;width:300px;}}
.pct{{font-family:'Cormorant Garamond',serif;font-size:76px;line-height:.92;color:{gold};letter-spacing:.02em;}}
.adv{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.42em;color:{ivory};
  margin-top:12px;font-weight:500;}}
.price{{position:absolute;left:740px;top:584px;width:300px;font-family:'Cormorant Garamond',serif;
  font-size:40px;color:{gold};letter-spacing:.05em;}}
.cur{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.28em;margin-left:10px;
  color:{gold};vertical-align:8px;}}
.unit{{position:absolute;left:740px;top:720px;width:300px;font-family:'Cormorant Garamond',serif;
  font-size:26px;color:{ivory};letter-spacing:.14em;}}
.cta{{position:absolute;left:740px;top:918px;width:280px;font-family:'Source Sans 3',sans-serif;
  font-size:13px;letter-spacing:.40em;color:{ivory};font-weight:500;}}
.cta-rule{{width:64px;height:1px;background:{gold};margin-top:14px;}}
.closure{{position:absolute;left:80px;top:1250px;width:928px;text-align:center;
  font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.42em;color:{ivory};}}
</style>
</head>
<body>
<div class="stage">
  <div class="headline">
    <p class="line1">ALIRKEN</p>
    <p class="line2">KAZAN</p>
    <div class="rule"></div>
  </div>
  <div class="offer">
    <div class="pct">{REQUIRED_FACTS["discount"]}</div>
    <div class="adv">{REQUIRED_FACTS["discount_label"]}</div>
  </div>
  <div class="price">675.000<span class="cur">USD</span></div>
  <div class="unit">{REQUIRED_FACTS["unit"]} {REQUIRED_FACTS["unit_label"]}</div>
  <div class="cta">{REQUIRED_FACTS["cta"]}<div class="cta-rule"></div></div>
  <div class="closure">{APPROVED_BOTTOM_COPY}</div>
</div>
</body>
</html>
"""


def compose_temple_premium_master_01(
    *,
    photo: Image.Image,
    logo_rgba: Image.Image,
) -> tuple[Image.Image, dict[str, Any]]:
    layout = locked_layout()
    registry = build_font_registry()
    field = render_html_to_png(master_field_html(font_face_css(registry)), width=W, height=H)
    placed, photo_meta = place_photo_object(field, photo, layout)
    branded = paste_real_logo(placed, logo_rgba, layout)
    photo_meta["generated_logo_pixels"] = 0
    photo_meta["duplicate_temple_logo"] = False
    photo_meta["internal_generated_pixels"] = 0
    photo_meta["architecture_fidelity"] = 10
    photo_meta["percentage"] = photo_percentage(layout["photo_box"])
    assert PHOTO_MIN_MASS <= photo_meta["percentage"] <= PHOTO_MAX_MASS
    return branded.convert("RGB"), {"layout": layout, "photo": photo_meta, "territories": TERRITORIES_72}


def render_reference_vs_master(reference: Image.Image, master: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1600, 1080), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "03  REFERENCE vs THE TEMPLE PREMIUM MASTER 01", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("ORNEK_00013  —  craft source, not a template", reference), ("THE TEMPLE — PREMIUM CAMPAIGN 01", master)):
        tile = image.copy()
        tile.thumbnail((740, 940), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 64))
        draw.text((x, 1020), label[:56], font=_font(16), fill=IVORY)
        x += 780
    return canvas


def render_human_review_board(reference: Image.Image, master: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 24), "08  HUMAN REVIEW BOARD  —  THE TEMPLE PREMIUM MASTER 01", font=_font(20), fill=GOLD)
    draw.text((40, 56), "DRAFT  ·  pending human visual approval  ·  not router-eligible", font=_font(16), fill=(180, 176, 168))
    x = 40
    for label, image in (("DESIGN_REFERENCES  /  ORNEK_00013", reference), ("THE TEMPLE — PREMIUM CAMPAIGN 01", master)):
        tile = image.copy()
        tile.thumbnail((880, 960), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 96))
        draw.text((x, 1064), label[:52], font=_font(16), fill=IVORY)
        x += 940
    return canvas


def render_territory_overlay(master: Image.Image, layout: dict[str, Any]) -> Image.Image:
    image = master.copy().convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    colors = {
        "photo_box": (80, 180, 255, 70),
        "headline": (255, 255, 255, 50),
        "offer": (201, 168, 92, 60),
        "price": (201, 168, 92, 50),
        "unit": (244, 239, 228, 40),
        "cta": (180, 120, 255, 50),
        "brand_box": (120, 255, 120, 50),
        "closure": (244, 239, 228, 40),
    }
    labels = {
        "photo_box": "PROJECT_PHOTO_OBJECT",
        "headline": "HEADLINE",
        "offer": "OFFER",
        "price": "PRICE",
        "unit": "UNIT",
        "cta": "CTA",
        "brand_box": "BRAND",
        "closure": "EDITORIAL_CLOSURE",
    }
    for key, color in colors.items():
        box = layout.get(key) or {}
        x0 = int(box["x"] * W)
        y0 = int(box["y"] * H)
        x1 = int((box["x"] + box["w"]) * W)
        y1 = int((box["y"] + box["h"]) * H)
        draw.rectangle((x0, y0, x1, y1), outline=color[:3] + (220,), width=2)
        draw.rectangle((x0, y0, x0 + 8 * len(labels[key]), y0 + 22), fill=(12, 14, 20, 190))
        ImageDraw.Draw(image).text((x0 + 6, y0 + 4), labels[key], fill=color[:3], font=_font(13))
    return image.convert("RGB")
