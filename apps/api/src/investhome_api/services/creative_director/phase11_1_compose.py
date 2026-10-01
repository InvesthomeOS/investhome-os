"""Phase 11.1 compositor — Photographic İ. Real Day_008 pixels. No architecture generation."""

from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import (
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_1_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY008_ASSET_ID,
    DAY008_FILENAME,
    HEADLINE,
    TWO_SECOND,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

W, H = CANVAS_4X5
PAPER = (241, 230, 214)
INK = "#2A2218"
INK_SOFT = "#6A5A48"
BRONZE = "#A8844A"
STEM_BOX = {"left": 0.402, "top": 0.168, "width": 0.196, "height": 0.548}
TITTLE_BOX = {"left": 0.448, "top": 0.078, "width": 0.104, "height": 0.068}
STEM_SOURCE = (0.58, 0.00, 0.86, 0.70)
TITTLE_SOURCE = (0.64, 0.00, 0.80, 0.16)
GRADE = {"warmth": 0.04, "contrast": 1.06, "brightness": 1.0, "vignette": 0.0}


def _png_data_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def paper_field(size: tuple[int, int] = CANVAS_4X5) -> Image.Image:
    field = Image.new("RGB", size, PAPER)
    noise = Image.effect_noise(size, 16).convert("L")
    grain = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(field, grain, 0.028)


def crop_source_window(source: Image.Image, window: tuple[float, float, float, float], target: tuple[int, int], role: str) -> tuple[Image.Image, dict[str, Any]]:
    sw, sh = source.size
    box = (
        int(window[0] * sw),
        int(window[1] * sh),
        int(window[2] * sw),
        int(window[3] * sh),
    )
    region = source.crop(box).convert("RGB")
    crop, transform = cover_fit_canvas(region, target, centering=(0.50, 0.42))
    graded = apply_photographic_grade(crop, dict(GRADE))
    transform = dict(transform)
    transform["role"] = role
    transform["source"] = DAY008_FILENAME
    transform["asset_id"] = DAY008_ASSET_ID
    transform["source_window"] = list(window)
    transform["source_crop_px"] = list(box)
    return graded, transform


def crop_letter_photo(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    tw = int(W * STEM_BOX["width"])
    th = int(H * STEM_BOX["height"])
    return crop_source_window(source, STEM_SOURCE, (tw, th), "photographic_i_stem")


def designed_letter(*, source: Image.Image) -> tuple[Image.Image, Image.Image, dict[str, Any]]:
    """No-copy: real Temple photography as the dotted Turkish İ."""
    sw = int(W * STEM_BOX["width"])
    sh = int(H * STEM_BOX["height"])
    tw = int(W * TITTLE_BOX["width"])
    th = int(H * TITTLE_BOX["height"])
    stem, stem_tf = crop_source_window(source, STEM_SOURCE, (sw, sh), "photographic_i_stem")
    tittle, tittle_tf = crop_source_window(source, TITTLE_SOURCE, (tw, th), "photographic_i_tittle")
    canvas = paper_field(CANVAS_4X5)
    sx = int(W * STEM_BOX["left"])
    sy = int(H * STEM_BOX["top"])
    tx = int(W * TITTLE_BOX["left"])
    ty = int(H * TITTLE_BOX["top"])
    canvas.paste(stem.convert("RGB"), (sx, sy))
    canvas.paste(tittle.convert("RGB"), (tx, ty))
    meta = {
        "concept": CONCEPT_NAME,
        "sentence": CONCEPT_SENTENCE,
        "stem": dict(STEM_BOX),
        "tittle": dict(TITTLE_BOX),
        "paste": {"stem": {"x": sx, "y": sy, "width": stem.size[0], "height": stem.size[1]}, "tittle": {"x": tx, "y": ty, "width": tittle.size[0], "height": tittle.size[1]}},
        "transform": {"stem": stem_tf, "tittle": tittle_tf},
        "internal_generated_pixels": 0,
        "mask": "none — two source-window crops of Day_008 form stem + tittle of İ",
    }
    return canvas, stem.convert("RGBA"), meta


def campaign_html(*, scene_uri: str, logo_markup: str, font_css: str) -> str:
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:rgb(241,230,214);}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.scene{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block;}}
.brand{{position:absolute;left:6.2%;top:3.1%;width:236px;height:54px;}}
.brand svg{{width:236px;height:54px;display:block;opacity:.92;}}
.loc{{position:absolute;left:6.4%;top:8.3%;margin:0;color:{INK_SOFT};
  font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.42em;font-weight:600;}}
.tar{{position:absolute;left:16.4%;top:42.4%;margin:0;padding:0;color:{INK};
  font-family:'Source Sans 3',sans-serif;font-weight:800;font-size:96px;line-height:.8;letter-spacing:.04em;}}
.h{{position:absolute;left:61.8%;top:42.4%;margin:0;padding:0;color:{INK};
  font-family:'Source Sans 3',sans-serif;font-weight:800;font-size:96px;line-height:.8;letter-spacing:.04em;}}
.commercial{{position:absolute;left:6.2%;top:76.8%;width:32%;color:{INK};}}
.pct{{margin:0;font-family:'Source Sans 3',sans-serif;font-size:44px;font-weight:800;line-height:.9;letter-spacing:.01em;color:{BRONZE};}}
.offer{{margin:8px 0 0 0;font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.28em;font-weight:700;color:{INK};}}
.price{{margin:18px 0 0 0;font-family:'Source Sans 3',sans-serif;font-size:18px;font-weight:700;letter-spacing:.04em;}}
.unit{{display:block;margin-top:6px;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.22em;font-weight:600;color:{INK_SOFT};}}
.cta{{margin:16px 0 0 0;font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.34em;font-weight:700;color:{INK};}}
.ed{{position:absolute;left:6.2%;bottom:3.4%;margin:0;color:{INK_SOFT};
  font-family:'Source Sans 3',sans-serif;font-size:11px;letter-spacing:.16em;font-weight:500;}}
</style>
</head>
<body>
<div class="stage">
  <img class="scene" data-semantic="project_photo" alt="" src="{scene_uri}"/>
  <div class="brand" data-semantic="project_logo">{logo_markup}</div>
  <p class="loc">WASHINGTON D.C.</p>
  <p class="tar" data-semantic="headline">{HEADLINE[:3]}</p>
  <p class="h" data-semantic="headline">H</p>
  <div class="commercial">
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
    scene, column_rgba, meta = designed_letter(source=source)
    registry = build_font_registry()
    html = campaign_html(
        scene_uri=_png_data_uri(scene),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
    )
    image = render_html_to_png(html, width=W, height=H).convert("RGB")
    meta["headline"] = HEADLINE
    meta["offer"] = f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}"
    return image, scene, html, meta


def html_copy_ok(html: str) -> bool:
    needed = (
        "TAR",
        ">H</p>",
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
        and "THE TEMPLE" not in html
        and "investhome" not in low
        and "uniloft" not in low
        and "border-radius:999" not in html
        and "text-align:center" not in html
        and "Cormorant Garamond" not in body
    )


def render_opportunity_board(items: list[tuple[str, Image.Image, str]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (22, 18, 14))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "01  TEMPLE ASSET OPPORTUNITY  —  unused library scored for a fourth idea", font=_font(18), fill=GOLD)
    x, y = 36, 56
    for i, (label, image, note) in enumerate(items[:8]):
        tile = image.copy()
        tile.thumbnail((430, 430), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + 440), label[:40], font=_font(13), fill=IVORY)
        draw.text((x, y + 462), note[:48], font=_font(13), fill=GOLD)
        x += 470
        if i == 3:
            x, y = 36, 620
    return canvas


def render_art_direction_board(source: Image.Image, column: Image.Image, scene: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (22, 18, 14))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "07  ART DIRECTION  —  crop / typographic I / printed letter  (no generated architecture)", font=_font(18), fill=GOLD)
    x = 36
    for title, image in (("SOURCE  Day_008", source), ("STEM CROP", column.convert("RGB")), ("NO-COPY İ", scene)):
        tile = image.copy()
        tile.thumbnail((580, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1100), title[:42], font=_font(15), fill=IVORY)
        x += 620
    return canvas


def render_labeled(image: Image.Image, title: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1480), (22, 18, 14))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((1128, 1360), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    draw.text((36, 1436), caption[:78], font=_font(14), fill=IVORY)
    return canvas


def render_semantic_map(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1200, 1480), (22, 18, 14))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "11  SEMANTIC REVISION MAP  —  territories follow the design", font=_font(18), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((1128, 1360), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 56))
    notes = [
        "PHOTO  = photographic I (Day_008 spire)",
        "HEADLINE = TAR + H  (I is architecture)",
        "OFFER / PRICE / UNIT / CTA  = left inscription",
        "LOGO  = Temple only   CLOSURE  = base whisper",
        "PRICE_ONLY / HEADLINE_ONLY / VISUAL_REPLACE_ONLY compatible. No revisions in 11.1.",
    ]
    y = 1434
    draw.text((36, y), "  ·  ".join(notes)[:120], font=_font(12), fill=IVORY)
    return canvas


def render_review_board(scene: Image.Image, final: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (22, 18, 14))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "12  HUMAN REVIEW  —  Stage 3 Creative Quality Proof 01  DRAFT", font=_font(18), fill=GOLD)
    x = 36
    for title, image in (("NO-COPY", scene), ("WITH CAMPAIGN", final)):
        tile = image.copy()
        tile.thumbnail((880, 1040), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1110), title, font=_font(16), fill=IVORY)
        x += 940
    draw.text((36, 1144), TWO_SECOND[:110], font=_font(14), fill=GOLD)
    return canvas
