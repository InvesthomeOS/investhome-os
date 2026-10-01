"""Hybrid SVG compositor — field + masked photo object + vector type.

Not the old compiler: no flattened photographic plate, no absolutely
positioned HTML fact boxes.
"""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image, ImageFilter

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_design_scene import inline_logo_svg
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_6_strategy import HEADLINE

W, H = CANVAS_4X5
RENDER_SCALE = 2
INK = "#E8DFD0"
INK_SOFT = "#C9BBA6"
GOLD = "#C4A36A"
MUTED = "#8F8476"


def _png_data_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def _font_face(registry: dict[str, Any], role: str, family: str) -> str:
    spec = dict((registry.get("roles") or {}).get(role) or {})
    path = spec.get("font_path")
    if not path or not Path(str(path)).is_file():
        return ""
    payload = base64.b64encode(Path(str(path)).read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:'{family}';src:url('data:font/ttf;base64,{payload}') "
        f"format('truetype');font-weight:300 800;font-style:normal;font-display:block;}}"
    )


def contact_shadow(obj: Image.Image) -> Image.Image:
    alpha = obj.split()[-1]
    shadow = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    black = Image.new("RGBA", obj.size, (0, 0, 0, 160))
    shadow.paste(black, (0, 0), alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    return shadow


def object_layout(obj: Image.Image) -> dict[str, int]:
    target_h = int(H * 0.70)
    scale = target_h / max(obj.size[1], 1)
    ow = max(1, int(obj.size[0] * scale))
    oh = max(1, int(obj.size[1] * scale))
    if ow > int(W * 0.82):
        scale = (W * 0.82) / max(obj.size[0], 1)
        ow = max(1, int(obj.size[0] * scale))
        oh = max(1, int(obj.size[1] * scale))
    x = max(int(W * 0.22), (W - ow) // 2)
    y = int(H * 0.10)
    return {"x": x, "y": y, "w": ow, "h": oh}


def render_svg_html_to_png(markup: str, *, width: int, height: int, scale: int = RENDER_SCALE) -> Image.Image:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="phase116-") as td:
        path = Path(td) / "scene.html"
        path.write_text(markup, encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=scale,
            )
            page.goto(path.as_uri(), wait_until="load", timeout=60_000)
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(350)
            png = page.screenshot(
                type="png",
                clip={"x": 0, "y": 0, "width": width, "height": height},
            )
            browser.close()
    return Image.open(io.BytesIO(png)).convert("RGB")


def campaign_svg(
    *,
    field: Image.Image,
    obj: Image.Image,
    logo_markup: str,
    font_css: str,
) -> str:
    layout = object_layout(obj)
    placed = obj.resize((layout["w"], layout["h"]), Image.Resampling.LANCZOS)
    shadow = contact_shadow(placed)
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    price = REQUIRED_FACTS["list_price"]
    # Split price so USD can sit as a smaller companion, not a caption stack.
    amount, _, currency = price.partition(" ")
    logo = logo_markup
    if "<svg" in logo.lower():
        logo = logo.replace("<svg", '<svg width="168" height="40"', 1)
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;background:#0b0a09;}}
svg{{display:block;}}
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <mask id="objectMask">
      <image href="{_png_data_uri(placed)}" x="{layout['x']}" y="{layout['y']}" width="{layout['w']}" height="{layout['h']}"/>
    </mask>
    <clipPath id="page">
      <rect x="0" y="0" width="{W}" height="{H}"/>
    </clipPath>
  </defs>
  <g clip-path="url(#page)">
    <image data-semantic="creative_field" href="{_png_data_uri(field)}" x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>

    <text x="544" y="1218" text-anchor="middle"
          font-family="Hybrid Grotesk, sans-serif" font-size="188" font-weight="800"
          fill="{GOLD}" fill-opacity="0.92" letter-spacing="-8">{escape(REQUIRED_FACTS["discount"])}</text>
    <text x="544" y="1262" text-anchor="middle"
          font-family="Hybrid Grotesk, sans-serif" font-size="16" font-weight="700"
          fill="#2C261C" fill-opacity="0.78" letter-spacing="8">{escape(REQUIRED_FACTS["discount_label"])}</text>

    <text x="72" y="86" font-family="Hybrid Serif, serif" font-size="17" font-weight="600"
          fill="{INK_SOFT}" letter-spacing="9">THE TEMPLE</text>
    <text x="72" y="112" font-family="Hybrid Grotesk, sans-serif" font-size="11" font-weight="600"
          fill="{MUTED}" letter-spacing="4.2">WASHINGTON D.C.</text>
    <text x="72" y="168" font-family="Hybrid Serif, serif" font-size="54" font-weight="600"
          fill="{INK}" letter-spacing="1.2">{escape(HEADLINE)}</text>
    <text x="72" y="198" font-family="Hybrid Grotesk, sans-serif" font-size="12" font-weight="600"
          fill="{GOLD}" letter-spacing="5.4">{escape(REQUIRED_FACTS["cta"])}</text>

    <image href="{_png_data_uri(shadow)}" x="{layout['x']}" y="{layout['y'] + 18}" width="{layout['w']}" height="{layout['h']}" opacity="0.55"/>
    <image data-semantic="project_photo" href="{_png_data_uri(placed)}" x="{layout['x']}" y="{layout['y']}" width="{layout['w']}" height="{layout['h']}"/>

    <g transform="translate(1004, 430) rotate(90)">
      <text font-family="Hybrid Grotesk, sans-serif" font-size="42" font-weight="700"
            fill="{INK}" letter-spacing="1.4">{escape(amount)}</text>
      <text x="212" font-family="Hybrid Grotesk, sans-serif" font-size="16" font-weight="600"
            fill="{INK_SOFT}" letter-spacing="4.8">{escape(currency)}</text>
      <text x="0" y="28" font-family="Hybrid Grotesk, sans-serif" font-size="13" font-weight="600"
            fill="{MUTED}" letter-spacing="3.6">{escape(unit)}</text>
    </g>

    <rect x="{layout['x'] + 40}" y="{layout['y'] + int(layout['h'] * 0.62)}" width="2" height="86"
          fill="{GOLD}" fill-opacity="0.85" mask="url(#objectMask)"/>

    <g data-semantic="project_logo" transform="translate(72, 1268)" style="filter:brightness(0) invert(1);opacity:.9">{logo}</g>
    <text x="72" y="1336" font-family="Hybrid Serif, serif" font-size="11" font-weight="500"
          fill="{MUTED}" letter-spacing="2.4">{escape(APPROVED_BOTTOM_COPY)}</text>
  </g>
</svg>
</body>
</html>
"""


def html_copy_ok(markup: str) -> bool:
    needed = (
        HEADLINE,
        "THE TEMPLE",
        "WASHINGTON D.C.",
        "%35",
        "LANSMAN",
        "AVANTAJI",
        "675.000",
        "USD",
        "2+1",
        "DAİRE",
        "PROJEYİ KEŞFET",
        APPROVED_BOTTOM_COPY,
        "<svg",
        "data-semantic=\"project_photo\"",
        "data-semantic=\"creative_field\"",
    )
    low = markup.lower()
    return (
        all(token in markup for token in needed)
        and "position:absolute" not in low
        and "border-radius:999" not in low
        and "investhome" not in low
        and "uniloft" not in low
        and "class=\"scene\"" not in low
    )


def compose_hybrid_proof(
    *,
    field: Image.Image,
    obj: Image.Image,
    logo_bytes: bytes,
) -> tuple[Image.Image, str, dict[str, Any]]:
    registry = build_font_registry()
    font_css = "\n".join(
        block
        for block in (
            _font_face(registry, "DISPLAY_SERIF", "Hybrid Serif"),
            _font_face(registry, "EDITORIAL_SERIF", "Hybrid Serif"),
            _font_face(registry, "DISPLAY_SANS", "Hybrid Grotesk"),
            _font_face(registry, "EDITORIAL_SANS", "Hybrid Grotesk"),
            _font_face(registry, "COMMERCIAL_NUMBER", "Hybrid Grotesk"),
        )
        if block
    )
    markup = campaign_svg(
        field=field.convert("RGB"),
        obj=obj.convert("RGBA"),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_css,
    )
    if not html_copy_ok(markup):
        raise RuntimeError("Phase 11.6 SVG copy / composition gate failed")
    image = render_svg_html_to_png(markup, width=W, height=H, scale=RENDER_SCALE)
    layout = object_layout(obj)
    meta = {
        "renderer": "chromium_svg_scene_graph",
        "old_compiler_used": False,
        "canvas": [W, H],
        "render_scale": RENDER_SCALE,
        "output_size": list(image.size),
        "object_layout": layout,
        "layers": [
            "generated_creative_field",
            "printed_offer_numeral_behind_object",
            "letterhead_and_headline_on_field",
            "contact_shadow",
            "real_temple_object",
            "vertical_price_spine",
            "gold_rule_masked_to_object",
            "real_logo_svg",
            "editorial_closure",
        ],
        "headline": HEADLINE,
    }
    return image, markup, meta


def compose_development_plate(*, field: Image.Image, obj: Image.Image) -> Image.Image:
    layout = object_layout(obj)
    placed = obj.resize((layout["w"], layout["h"]), Image.Resampling.LANCZOS)
    shadow = contact_shadow(placed)
    plate = field.convert("RGB")
    plate.paste(shadow, (layout["x"], layout["y"] + 18), shadow)
    plate.paste(placed, (layout["x"], layout["y"]), placed)
    return plate
