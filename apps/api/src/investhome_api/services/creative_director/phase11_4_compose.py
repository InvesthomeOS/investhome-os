"""Phase 11.4 compositor — The Threshold.

Real Day_009 pixels only. Three Gothic portals as the commercial grid.
No architecture generation. No Day_008. No left information column.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import inline_logo_svg, render_html_to_png
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_4_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY009_ASSET_ID,
    DAY009_FILENAME,
    HEADLINE,
    HEADLINE_LINE_1,
    HEADLINE_LINE_2,
    TWO_SECOND,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
# Custom 4:5 window inside Day_009 (square). Y-centering of cover-fit is a no-op on a square.
CROP_BOX = {"left": 0.26, "top": 0.00, "height": 0.92}
GRADE = {"warmth": 0.04, "contrast": 1.08, "brightness": 0.98, "vignette": 0.03}
INK = "#F4EFE6"
INK_SOFT = "#D9CBB6"
INK_MUTED = "#B7A78F"
STONE = "#E8C98A"
GROUND = "#1C1814"

# After luminance probe of the zoomed Day_009 window: dark Gothic glass sits ~x 0.40–0.62, y 0.58–0.76.
LEFT_ARCH = {"left": 0.40, "top": 0.58, "right": 0.50, "bottom": 0.76}
CENTER_ARCH = {"left": 0.50, "top": 0.57, "right": 0.62, "bottom": 0.76}
FRIEZE = {"left": 0.38, "top": 0.49, "right": 0.66, "bottom": 0.58}


def _png_data_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def campaign_font_css(registry: dict[str, Any]) -> str:
    """Civic grotesque. Do not inherit Master serif or Proof 02 Source-on-plinth as a default look."""
    roles = dict(registry.get("roles") or {})
    sans = dict(roles.get("DISPLAY_SANS") or {}) or dict(roles.get("EDITORIAL_SANS") or {})
    path = sans.get("font_path")
    if not path or not Path(str(path)).is_file():
        support = dict(roles.get("EDITORIAL_SANS") or {})
        path = support.get("font_path")
    if not path or not Path(str(path)).is_file():
        return ""
    payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
    family = "Campaign Grotesk"
    return (
        f"@font-face{{font-family:'{family}';src:url('data:font/ttf;base64,{payload}') "
        f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
    )


def crop_threshold_photo(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    sw, sh = source.size
    ch = max(1, int(sh * float(CROP_BOX["height"])))
    cw = max(1, int(ch * W / H))
    left = min(max(0, int(sw * float(CROP_BOX["left"]))), max(0, sw - cw))
    top = min(max(0, int(sh * float(CROP_BOX["top"]))), max(0, sh - ch))
    window = source.crop((left, top, left + cw, top + ch)).resize((W, H), Image.Resampling.LANCZOS)
    graded = apply_photographic_grade(window, dict(GRADE))
    transform = {
        "role": "civic_threshold",
        "source": DAY009_FILENAME,
        "asset_id": DAY009_ASSET_ID,
        "mode": "zoomed_4x5_window",
        "box": {"left": left, "top": top, "width": cw, "height": ch, "source_size": [sw, sh]},
        "crop_box": dict(CROP_BOX),
    }
    return graded, transform


def _arch_void_mask(size: tuple[int, int]) -> Image.Image:
    """Deepen the already-dark portal glass so an opening can hold a numeral. Real pixels remain."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for spec, fill in ((LEFT_ARCH, 88), (CENTER_ARCH, 40)):
        box = (
            int(size[0] * float(spec["left"])),
            int(size[1] * float(spec["top"])),
            int(size[0] * float(spec["right"])),
            int(size[1] * float(spec["bottom"])),
        )
        draw.ellipse(box, fill=fill)
    return mask.filter(ImageFilter.GaussianBlur(radius=18))


def _dedication_mask(size: tuple[int, int]) -> Image.Image:
    """Darken the sunlit cornice just above the portals so a dedication can be inscribed. Real pixels remain."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    box = (
        int(size[0] * float(FRIEZE["left"])),
        int(size[1] * float(FRIEZE["top"])),
        int(size[0] * float(FRIEZE["right"])),
        int(size[1] * float(FRIEZE["bottom"])),
    )
    draw.rectangle(box, fill=118)
    return mask.filter(ImageFilter.GaussianBlur(radius=22))


def designed_threshold(*, source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    photo, transform = crop_threshold_photo(source)
    canvas = photo.convert("RGB")
    overlay = Image.new("RGB", canvas.size, (16, 12, 10))
    void = _arch_void_mask(canvas.size).point(lambda p: int(p * 0.70))
    band = _dedication_mask(canvas.size)
    canvas = Image.composite(overlay, canvas, void)
    canvas = Image.composite(overlay, canvas, band)
    meta = {
        "concept": CONCEPT_NAME,
        "sentence": CONCEPT_SENTENCE,
        "transform": transform,
        "internal_generated_pixels": 0,
        "mask": "photographic deepening of portal glass and cornice band only — real Day_009 pixels remain",
        "depth": "street → lawn → fence → three portals → tower → lantern → sky",
    }
    return canvas, meta


def render_crop_grid(source: Image.Image) -> Image.Image:
    photo, _ = crop_threshold_photo(source)
    canvas = photo.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for i in range(1, 10):
        x = int(W * i / 10)
        y = int(H * i / 10)
        draw.line((x, 0, x, H), fill=(255, 220, 120), width=1)
        draw.line((0, y, W, y), fill=(255, 220, 120), width=1)
        draw.text((x + 4, 8), f"{i/10:.1f}", font=_font(14), fill=GOLD)
        draw.text((8, y + 4), f"{i/10:.1f}", font=_font(14), fill=GOLD)
    for spec, name in ((LEFT_ARCH, "L"), (CENTER_ARCH, "C"), (FRIEZE, "F")):
        box = (
            int(W * spec["left"]),
            int(H * spec["top"]),
            int(W * spec["right"]),
            int(H * spec["bottom"]),
        )
        draw.rectangle(box, outline=(80, 200, 255), width=2)
        draw.text((box[0] + 6, box[1] + 6), name, font=_font(16), fill=(80, 200, 255))
    return canvas


def campaign_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:{GROUND};}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.scene{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;}}
.loc{{position:absolute;left:6.5%;bottom:13.8%;margin:0;color:{INK_MUTED};
  font-family:'Campaign Grotesk',sans-serif;font-size:11px;letter-spacing:.38em;font-weight:600;}}
.hwrap{{position:absolute;left:38%;top:49.6%;width:28%;text-align:center;color:{INK};}}
.h1,.h2{{margin:0;padding:0;font-family:'Campaign Grotesk',sans-serif;line-height:.86;}}
.h1{{font-size:42px;font-weight:800;letter-spacing:.10em;}}
.h2{{font-size:42px;font-weight:500;letter-spacing:.32em;margin-top:2px;}}
.offer{{position:absolute;left:40.2%;top:59.4%;width:10.4%;text-align:center;color:{STONE};}}
.pct{{margin:0;font-family:'Campaign Grotesk',sans-serif;font-size:72px;font-weight:800;line-height:.78;letter-spacing:-.06em;}}
.offerlab{{margin:3px 0 0 0;font-family:'Campaign Grotesk',sans-serif;font-size:8px;letter-spacing:.12em;font-weight:700;color:{INK};}}
.cta{{position:absolute;left:50.4%;top:71.6%;width:12.2%;margin:0;text-align:center;
  font-family:'Campaign Grotesk',sans-serif;font-size:10px;letter-spacing:.24em;font-weight:700;color:{INK};}}
.brand{{position:absolute;left:6.5%;bottom:7.2%;width:176px;height:42px;}}
.brand svg{{width:176px;height:42px;display:block;opacity:.94;filter:brightness(0) invert(1);}}
.value{{position:absolute;right:6.5%;bottom:4.8%;color:{INK};text-align:right;}}
.price{{margin:0;font-family:'Campaign Grotesk',sans-serif;font-size:30px;font-weight:700;letter-spacing:.03em;}}
.unit{{display:block;margin-top:5px;font-family:'Campaign Grotesk',sans-serif;font-size:11px;letter-spacing:.28em;font-weight:600;color:{INK_SOFT};}}
.ed{{position:absolute;left:6.5%;bottom:3.2%;margin:0;color:{INK_MUTED};text-align:left;
  font-family:'Campaign Grotesk',sans-serif;font-size:10px;letter-spacing:.14em;font-weight:500;max-width:46%;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <p class="loc">WASHINGTON D.C.</p>
  <div class="hwrap">
    <p class="h1" data-semantic="headline">{HEADLINE_LINE_1}</p>
    <p class="h2" data-semantic="headline">{HEADLINE_LINE_2}</p>
  </div>
  <div class="offer">
    <p class="pct" data-semantic="discount">{REQUIRED_FACTS["discount"]}</p>
    <p class="offerlab" data-semantic="discount_label">{REQUIRED_FACTS["discount_label"]}</p>
  </div>
  <p class="cta" data-semantic="cta">{REQUIRED_FACTS["cta"]}</p>
  <div class="brand" data-semantic="project_logo">{logo_markup}</div>
  <div class="value">
    <p class="price" data-semantic="price">{REQUIRED_FACTS["list_price"]}</p>
    <span class="unit" data-semantic="unit_type">{unit}</span>
  </div>
  <p class="ed" data-semantic="editorial_closure">{APPROVED_BOTTOM_COPY}</p>
</div>
</body>
</html>
"""


def compose_proof(*, source: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, Image.Image, str, dict[str, Any]]:
    scene, meta = designed_threshold(source=source)
    registry = build_font_registry()
    html = campaign_html(
        scene_uri=_png_data_uri(scene),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=campaign_font_css(registry),
    )
    image = render_html_to_png(html, width=W, height=H).convert("RGB")
    meta["headline"] = HEADLINE
    meta["offer"] = f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}"
    return image, scene, html, meta


def html_copy_ok(html: str) -> bool:
    needed = (
        HEADLINE_LINE_1,
        HEADLINE_LINE_2,
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
    low = html.lower()
    body = html.split("</style>", 1)[-1]
    return (
        all(token in html for token in needed)
        and "TARİH" not in html.replace(APPROVED_BOTTOM_COPY, "")
        and "investhome" not in low
        and "uniloft" not in low
        and "border-radius:999" not in html
        and "border-radius: 999" not in html
        and "photographic_i" not in low
        and "Day_008" not in html
    )


def thumbnail_image(image: Image.Image, *, scale: float = 0.15) -> Image.Image:
    tw, th = max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale))
    return image.resize((tw, th), Image.Resampling.LANCZOS)


def render_opportunity_board(items: list[tuple[str, Image.Image, str]]) -> Image.Image:
    cols, rows = 5, 4
    canvas = Image.new("RGB", (1920, 1480), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "01  TEMPLE ASSET OPPORTUNITY  —  architecture-led commercial scan  (Day_008 not auto-selected)", font=_font(16), fill=GOLD)
    x0, y0, tw, th, gap = 28, 48, 352, 300, 18
    for i, (label, image, note) in enumerate(items[: cols * rows]):
        col, row = i % cols, i // cols
        x = x0 + col * (tw + gap)
        y = y0 + row * (th + 48)
        tile = image.copy()
        tile.thumbnail((tw, th - 36), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + tile.size[1] + 6), label[:42], font=_font(12), fill=IVORY)
        draw.text((x, y + tile.size[1] + 24), note[:48], font=_font(11), fill=GOLD)
    return canvas


def render_art_direction_board(source: Image.Image, crop: Image.Image, scene: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "08  ART DIRECTION  —  Day_009 doorway crop / portal voids / no-copy  (0 generated architecture)", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("SOURCE  Day_009", source), ("4:5 THRESHOLD CROP", crop), ("NO-COPY  THE THRESHOLD", scene)):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 1108), title[:46], font=_font(15), fill=IVORY)
        x += 630
    return canvas


def render_commercial_system_board(scene: Image.Image, final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "07  COMMERCIAL SYSTEM  —  same architecture, campaign must make it stronger not busier", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("VISUAL IDEA  (no copy)", scene), ("COMMERCIAL SYSTEM", final)):
        tile = image.copy()
        tile.thumbnail((900, 1040), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 1110), title, font=_font(16), fill=IVORY)
        x += 940
    draw.text((28, 1144), "Offer in left portal  ·  headline on stone band  ·  CTA at center door  ·  price on arrival ground", font=_font(13), fill=GOLD)
    return canvas


def render_thumbnail_board(final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1600, 1100), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "10  THUMBNAIL / SCALE TEST  —  15% is the gate; 25% and 50% inspect finish", font=_font(16), fill=GOLD)
    x = 40
    for label, scale in (("15%", 0.15), ("25%", 0.25), ("50%", 0.50)):
        tile = thumbnail_image(final, scale=scale)
        canvas.paste(tile.convert("RGB"), (x, 80))
        draw.text((x, 80 + tile.size[1] + 12), f"{label}  {tile.size[0]}×{tile.size[1]}", font=_font(15), fill=IVORY)
        x += tile.size[0] + 48
    draw.text((28, 1040), "Required at 15%: one visual event, one message, one commercial hook, architecture still dominant.", font=_font(14), fill=GOLD)
    return canvas


def render_semantic_map(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1480), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "13  SEMANTIC REVISION MAP  —  territories follow the doorway, not a column", font=_font(16), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((1144, 1280), Image.Resampling.LANCZOS)
    ox, oy = 28, 48
    canvas.paste(tile.convert("RGB"), (ox, oy))
    tw, th = tile.size
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    zones = [
        ((0.00, 0.00, 1.00, 1.00), (180, 140, 80, 36), "PHOTO"),
        ((0.26, 0.37, 0.72, 0.46), (220, 80, 80, 80), "HEADLINE"),
        ((0.275, 0.48, 0.43, 0.66), (80, 200, 120, 80), "OFFER"),
        ((0.425, 0.70, 0.59, 0.75), (90, 90, 220, 80), "CTA"),
        ((0.06, 0.88, 0.22, 0.92), (80, 160, 220, 80), "LOGO"),
        ((0.06, 0.93, 0.38, 0.97), (200, 180, 60, 80), "PRICE"),
        ((0.06, 0.97, 0.28, 0.995), (160, 100, 200, 80), "UNIT"),
        ((0.55, 0.94, 0.94, 0.99), (200, 200, 200, 70), "CLOSURE"),
    ]
    for (l, t, r, b), color, _name in zones:
        box = [ox + l * tw, oy + t * th, ox + r * tw, oy + b * th]
        od.rectangle(box, outline=color, width=2)
    canvas.paste(overlay, (0, 0), overlay)
    draw.text(
        (28, 1356),
        "PHOTO=Day_009 doorway   HEADLINE=stone band   OFFER=left portal   CTA=center threshold   PRICE/UNIT=ground   LOGO=lawn",
        font=_font(12),
        fill=IVORY,
    )
    draw.text((28, 1380), "PRICE_ONLY / HEADLINE_ONLY / VISUAL_REPLACE_ONLY compatible. No revisions in 11.4.", font=_font(12), fill=GOLD)
    draw.text((28, 1404), "Do not collapse these territories into a left column to make editing easier.", font=_font(12), fill=GOLD)
    return canvas


def render_review_board(scene: Image.Image, final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "14  HUMAN REVIEW  —  Stage 3 Creative Quality Proof 03  DRAFT", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("NO-COPY", scene), ("WITH CAMPAIGN", final)):
        tile = image.copy()
        tile.thumbnail((900, 1040), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 1110), title, font=_font(16), fill=IVORY)
        x += 940
    draw.text((28, 1144), TWO_SECOND[:130], font=_font(13), fill=GOLD)
    return canvas
