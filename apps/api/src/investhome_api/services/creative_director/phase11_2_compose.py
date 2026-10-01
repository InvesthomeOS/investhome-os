"""Phase 11.2 compositor — The Seam.

Real Day_008 pixels only. Historic stone and new brick in one photograph.
No architecture generation. No Proof 01 letter İ. No TARİH device.
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
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_2_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY008_ASSET_ID,
    DAY008_FILENAME,
    HEADLINE,
    HEADLINE_LINE_1,
    HEADLINE_LINE_2,
    TWO_SECOND,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
CENTERING = (0.56, 0.40)
GRADE = {"warmth": 0.03, "contrast": 1.07, "brightness": 0.99, "vignette": 0.0}
# Washes live only on the modern brick — not the sky, not a left-half type slab.
HEADLINE_WASH = {"left": 0.06, "top": 0.24, "right": 0.49, "bottom": 0.50, "fill": 78}
PLINTH_WASH = {"left": 0.06, "top": 0.48, "right": 0.50, "bottom": 0.74, "fill": 122}
SEAM_X = 0.49
STONE = "#C9A56A"
INK = "#F6EFE4"
INK_SOFT = "#D8C7AE"
INK_MUTED = "#B7A48A"


def _png_data_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def campaign_font_css(registry: dict[str, Any]) -> str:
    """Source Sans as the modern insertion voice. No inherited luxury serif."""
    roles = dict(registry.get("roles") or {})
    sans = dict(roles.get("DISPLAY_SANS") or {}) or dict(roles.get("EDITORIAL_SANS") or {})
    path = sans.get("font_path")
    if not path or not Path(str(path)).is_file():
        support = dict(roles.get("EDITORIAL_SANS") or {})
        path = support.get("font_path")
    if not path or not Path(str(path)).is_file():
        return ""
    payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:'Source Sans 3';src:url('data:font/ttf;base64,{payload}') "
        f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
    )


def crop_seam_photo(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=CENTERING)
    graded = apply_photographic_grade(crop, dict(GRADE))
    transform = dict(transform)
    transform["role"] = "historic_modern_seam"
    transform["source"] = DAY008_FILENAME
    transform["asset_id"] = DAY008_ASSET_ID
    transform["centering"] = list(CENTERING)
    return graded, transform


def _soft_wash(size: tuple[int, int], spec: dict[str, float | int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    box = (
        int(size[0] * float(spec["left"])),
        int(size[1] * float(spec["top"])),
        int(size[0] * float(spec["right"])),
        int(size[1] * float(spec["bottom"])),
    )
    draw.rectangle(box, fill=int(spec["fill"]))
    return mask.filter(ImageFilter.GaussianBlur(radius=28))


def designed_seam(*, source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """No-copy: authored crop of the real join + photographic washes on the modern volume."""
    photo, transform = crop_seam_photo(source)
    canvas = photo.convert("RGB")
    overlay = Image.new("RGB", canvas.size, (26, 20, 16))
    headline_mask = _soft_wash(canvas.size, HEADLINE_WASH)
    plinth_mask = _soft_wash(canvas.size, PLINTH_WASH)
    canvas = Image.composite(overlay, canvas, headline_mask)
    canvas = Image.composite(overlay, canvas, plinth_mask)
    meta = {
        "concept": CONCEPT_NAME,
        "sentence": CONCEPT_SENTENCE,
        "transform": transform,
        "internal_generated_pixels": 0,
        "mask": "photographic washes on modern brick/plinth only — real Day_008 pixels remain",
        "seam_x": SEAM_X,
        "depth": "steps → street → lawn → two façades → spire → sky",
    }
    return canvas, meta


def campaign_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#1a1612;}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.scene{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;}}
.brand{{position:absolute;left:7.2%;top:26.2%;width:210px;height:48px;}}
.brand svg{{width:210px;height:48px;display:block;opacity:.94;filter:brightness(0) invert(1);}}
.loc{{position:absolute;left:7.4%;top:31.4%;margin:0;color:{INK_MUTED};
  font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.46em;font-weight:600;}}
.h1,.h2{{position:absolute;left:7.0%;margin:0;padding:0;color:{INK};
  font-family:'Source Sans 3',sans-serif;line-height:.88;}}
.h1{{top:34.2%;font-size:64px;font-weight:800;letter-spacing:.02em;}}
.h2{{top:40.2%;font-size:42px;font-weight:500;letter-spacing:.14em;}}
.plinth{{position:absolute;left:7.2%;top:51.6%;width:40%;color:{INK};}}
.pct{{margin:0;font-family:'Source Sans 3',sans-serif;font-size:62px;font-weight:800;line-height:.82;letter-spacing:-.02em;color:{STONE};}}
.offer{{margin:8px 0 0 0;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.32em;font-weight:700;color:{INK};}}
.price{{margin:16px 0 0 0;font-family:'Source Sans 3',sans-serif;font-size:24px;font-weight:700;letter-spacing:.04em;}}
.unit{{display:block;margin-top:6px;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.26em;font-weight:600;color:{INK_SOFT};}}
.cta{{margin:16px 0 0 0;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.36em;font-weight:700;color:{INK};}}
.ed{{position:absolute;left:7.2%;bottom:3.4%;margin:0;color:{INK_MUTED};
  font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.18em;font-weight:500;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <div class="brand" data-semantic="project_logo">{logo_markup}</div>
  <p class="loc">WASHINGTON D.C.</p>
  <p class="h1" data-semantic="headline">{HEADLINE_LINE_1}</p>
  <p class="h2" data-semantic="headline">{HEADLINE_LINE_2}</p>
  <div class="plinth">
    <p class="pct" data-semantic="discount">{REQUIRED_FACTS["discount"]}</p>
    <p class="offer" data-semantic="discount_label">{REQUIRED_FACTS["discount_label"]}</p>
    <p class="price" data-semantic="price">{REQUIRED_FACTS["list_price"]}<span class="unit" data-semantic="unit_type">{unit}</span></p>
    <p class="cta" data-semantic="cta">{REQUIRED_FACTS["cta"]}</p>
  </div>
  <p class="ed" data-semantic="editorial_closure">{APPROVED_BOTTOM_COPY}</p>
</div>
</body>
</html>
"""


def compose_proof(*, source: Image.Image, logo_bytes: bytes) -> tuple[Image.Image, Image.Image, str, dict[str, Any]]:
    scene, meta = designed_seam(source=source)
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
        and "THE TEMPLE" not in html
        and "investhome" not in low
        and "uniloft" not in low
        and "border-radius:999" not in html
        and "text-align:center" not in html
        and "Cormorant Garamond" not in body
        and "photographic_i" not in low
    )


def render_opportunity_board(items: list[tuple[str, Image.Image, str]]) -> Image.Image:
    cols, rows = 5, 4
    canvas = Image.new("RGB", (1920, 1480), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "03  TEMPLE CHARACTER / ASSET OPPORTUNITY  —  all approved real photography", font=_font(16), fill=GOLD)
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
    draw.text((28, 16), "07  ART DIRECTION  —  seam crop / modern plinth wash / no-copy  (0 generated architecture)", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("SOURCE  Day_008", source), ("4:5 SEAM CROP", crop), ("NO-COPY  THE SEAM", scene)):
        tile = image.copy()
        tile.thumbnail((600, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 1108), title[:46], font=_font(15), fill=IVORY)
        x += 630
    return canvas


def render_semantic_map(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1480), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "11  SEMANTIC REVISION MAP  —  territories follow the seam", font=_font(16), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((1144, 1280), Image.Resampling.LANCZOS)
    ox, oy = 28, 48
    canvas.paste(tile.convert("RGB"), (ox, oy))
    tw, th = tile.size
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # Approximate semantic territories on the placed tile (percent of proof canvas).
    zones = [
        ((0.00, 0.00, 1.00, 1.00), (180, 140, 80, 36), "PHOTO"),
        ((0.07, 0.26, 0.28, 0.31), (80, 160, 220, 80), "LOGO"),
        ((0.07, 0.34, 0.46, 0.48), (220, 80, 80, 80), "HEADLINE"),
        ((0.07, 0.52, 0.28, 0.62), (80, 200, 120, 80), "OFFER"),
        ((0.07, 0.62, 0.36, 0.70), (200, 180, 60, 80), "PRICE"),
        ((0.07, 0.70, 0.28, 0.74), (160, 100, 200, 80), "UNIT"),
        ((0.07, 0.74, 0.36, 0.78), (90, 90, 220, 80), "CTA"),
        ((0.07, 0.95, 0.55, 0.99), (200, 200, 200, 70), "CLOSURE"),
    ]
    for (l, t, r, b), color, _name in zones:
        box = [ox + l * tw, oy + t * th, ox + r * tw, oy + b * th]
        od.rectangle(box, outline=color, width=2)
    canvas.paste(overlay, (0, 0), overlay)
    draw.text(
        (28, 1356),
        "PHOTO=Day_008 seam   LOGO/HEADLINE/OFFER/PRICE/UNIT/CTA live on the modern volume   CLOSURE=ground whisper",
        font=_font(12),
        fill=IVORY,
    )
    draw.text((28, 1380), "PRICE_ONLY / HEADLINE_ONLY / VISUAL_REPLACE_ONLY compatible. No revisions in 11.2.", font=_font(12), fill=GOLD)
    draw.text((28, 1404), "Do not compromise the seam to create boxes. Territories follow the design.", font=_font(12), fill=GOLD)
    return canvas


def render_review_board(scene: Image.Image, final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (18, 15, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "12  HUMAN REVIEW  —  Stage 3 Creative Quality Proof 02  DRAFT", font=_font(16), fill=GOLD)
    x = 28
    for title, image in (("NO-COPY", scene), ("WITH CAMPAIGN", final)):
        tile = image.copy()
        tile.thumbnail((900, 1040), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 1110), title, font=_font(16), fill=IVORY)
        x += 940
    draw.text((28, 1144), TWO_SECOND[:120], font=_font(13), fill=GOLD)
    return canvas
