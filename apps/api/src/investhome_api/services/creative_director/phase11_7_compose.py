"""Phase 11.7 R1 compositor — same ledger concept, finished execution.

Layer order (THE_LEDGER):
  field → identity type → %35 on the plate → object → paper over feet →
  price / unit / CTA.

The monument occludes the printed offer. Paper occludes the hard foot crop.
No abs-positioned fact boxes. No vertical price spine.
"""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_design_scene import inline_logo_svg
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_6_strategy import HEADLINE
from investhome_api.services.creative_director.phase11_7_object import hybrid_layers

W, H = CANVAS_4X5
RENDER_SCALE = 2
INK = "#EDE6D8"
INK_SOFT = "#C9BBA6"
GOLD = "#B68A45"
BRONZE = "#7A4E1C"
PLATE = "#2A2218"
MUTED = "#8A7D6E"


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


def render_svg_html_to_png(markup: str, *, width: int, height: int, scale: int = RENDER_SCALE) -> Image.Image:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="phase117-") as td:
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


def _headline_markup() -> str:
    # Optical gap after Ş so TAŞ TEMİNAT does not collide at distance.
    if HEADLINE == "TAŞ TEMİNAT":
        return "TAŞ&#x2009;TEMİNAT"
    return escape(HEADLINE)


def campaign_svg_r1(
    *,
    field: Image.Image,
    placed: Image.Image,
    overlay: Image.Image,
    contact: Image.Image,
    layout: dict[str, int],
    paper_bbox: tuple[int, int, int, int],
    logo_markup: str,
    font_css: str,
) -> str:
    x0, y0, x1, y1 = paper_bbox
    cx = (x0 + x1) // 2
    paper_h = max(1, y1 - y0)
    offer_y = y0 + int(paper_h * 0.28)
    label_y = offer_y + 32
    value_y = y0 + int(paper_h * 0.70)
    cta_y = value_y + 40
    closure_y = min(H - 22, y1 + 16)
    logo = logo_markup
    if "<svg" in logo.lower():
        logo = logo.replace("<svg", '<svg width="124" height="30"', 1)
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    ox, oy, ow, oh = layout["x"], layout["y"], layout["w"], layout["h"]
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
  <image data-semantic="creative_field" href="{_png_data_uri(field)}" x="0" y="0" width="{W}" height="{H}"/>

  <text x="64" y="78" font-family="Hybrid Grotesk, sans-serif" font-size="13" font-weight="600"
        fill="{INK_SOFT}" letter-spacing="7.2">THE TEMPLE</text>
  <text x="64" y="100" font-family="Hybrid Grotesk, sans-serif" font-size="11" font-weight="600"
        fill="{MUTED}" letter-spacing="3.8">WASHINGTON D.C.</text>
  <text x="64" y="162" font-family="Hybrid Serif, serif" font-size="56" font-weight="600"
        fill="{INK}" letter-spacing="1.4">{_headline_markup()}</text>

  <text x="{cx}" y="{offer_y}" text-anchor="middle"
        font-family="Hybrid Serif, serif" font-size="168" font-weight="600"
        fill="{GOLD}" letter-spacing="-7">{escape(REQUIRED_FACTS["discount"])}</text>
  <text x="{cx}" y="{label_y}" text-anchor="middle"
        font-family="Hybrid Grotesk, sans-serif" font-size="13" font-weight="700"
        fill="{PLATE}" letter-spacing="7.2">{escape(REQUIRED_FACTS["discount_label"])}</text>

  <image href="{_png_data_uri(contact)}" x="0" y="0" width="{W}" height="{H}"/>
  <image data-semantic="project_photo" href="{_png_data_uri(placed)}" x="{ox}" y="{oy}" width="{ow}" height="{oh}"/>
  <image data-semantic="paper_occlusion" href="{_png_data_uri(overlay)}" x="0" y="0" width="{W}" height="{H}"/>

  <text x="{cx}" y="{value_y}" text-anchor="middle"
        font-family="Hybrid Serif, serif" font-size="32" font-weight="600"
        fill="{PLATE}" letter-spacing="1.0">{escape(REQUIRED_FACTS["list_price"])}<tspan dx="16" font-family="Hybrid Grotesk, sans-serif" font-size="16" font-weight="600" letter-spacing="3.0">{escape(unit)}</tspan></text>
  <text x="{cx}" y="{cta_y}" text-anchor="middle"
        font-family="Hybrid Grotesk, sans-serif" font-size="18" font-weight="700"
        fill="{BRONZE}" letter-spacing="6.4">{escape(REQUIRED_FACTS["cta"])}</text>

  <g data-semantic="project_logo" transform="translate({x0 + 18}, {y1 - 42})">{logo}</g>
  <text x="{cx}" y="{closure_y}" text-anchor="middle"
        font-family="Hybrid Serif, serif" font-size="11" font-weight="500"
        fill="{MUTED}" letter-spacing="2.8">{escape(APPROVED_BOTTOM_COPY)}</text>
</svg>
</body>
</html>
"""


def html_copy_ok_r1(markup: str) -> bool:
    needed = (
        "TAŞ",
        "TEMİNAT",
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
    )
    low = markup.lower()
    return (
        all(token in markup for token in needed)
        and "position:absolute" not in low
        and "rotate(90)" not in markup
        and "border-radius:999" not in low
        and "investhome" not in low
        and "uniloft" not in low
    )


def compose_hybrid_r1(
    *,
    field: Image.Image,
    obj: Image.Image,
    logo_bytes: bytes,
) -> tuple[Image.Image, str, dict[str, Any], Image.Image]:
    rgb = field.convert("RGB")
    layers = hybrid_layers(rgb, obj.convert("RGBA"))
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
    pbbox = tuple(int(v) for v in layers["paper_bbox"])
    markup = campaign_svg_r1(
        field=rgb,
        placed=layers["placed"],
        overlay=layers["overlay"],
        contact=layers["contact"],
        layout=layers["layout"],
        paper_bbox=pbbox,  # type: ignore[arg-type]
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_css,
    )
    if not html_copy_ok_r1(markup):
        raise RuntimeError("Phase 11.7 SVG copy gate failed")
    image = render_svg_html_to_png(markup, width=W, height=H, scale=RENDER_SCALE)
    fuse_meta = {
        "layout": layers["layout"],
        "paper_bbox": layers["paper_bbox"],
        "paper_coverage": layers["paper_coverage"],
        "occlusion": layers["occlusion"],
        "field_retained": True,
    }
    meta = {
        "renderer": "chromium_svg_layered_hybrid_r1",
        "old_compiler_used": False,
        "concept": "THE_LEDGER",
        "fuse": fuse_meta,
        "output_size": list(image.size),
        "removed": ("vertical_price_spine", "cta_under_headline", "full_silhouette_drop_shadow", "gold_rule_demo"),
        "layer_order": (
            "field",
            "identity_type",
            "printed_offer",
            "object",
            "paper_feet_occlusion",
            "value_cta",
        ),
    }
    return image, markup, meta, layers["fused"]
