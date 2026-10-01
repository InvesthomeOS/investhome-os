"""Phase 11.9 compositor — THE_REGISTER on Hybrid V2.

Layer order:
  field → identity / MERTEBE → %35 in the shaft → contact → object →
  atmosphere over feet → price/unit at inhabited mass → CTA at contact → logo / closure.

Typography is three altitudes of one instrument. No fact boxes. No buttons.
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
from investhome_api.services.creative_director.phase11_9_integrate import integrate_register
from investhome_api.services.creative_director.phase11_9_strategy import HEADLINE
from investhome_api.services.creative_director.responsive_commercial_hierarchy_v2 import (
    evaluate_hierarchy,
    optical_engine_report,
)

W, H = CANVAS_4X5
RENDER_SCALE = 2
INK = "#E8DFD0"
INK_SOFT = "#C4B49A"
GOLD = "#C4A36A"
BRONZE = "#8A5A24"
MUTED = "#8E7F6E"
DARK = "#1A1612"


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

    with tempfile.TemporaryDirectory(prefix="phase119-") as td:
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


def register_type_layout(obj_layout: dict[str, int]) -> dict[str, Any]:
    ox, oy, ow, oh = obj_layout["x"], obj_layout["y"], obj_layout["w"], obj_layout["h"]
    left = max(40, min(72, ox - 120))
    lantern_y = oy + int(oh * 0.20)
    inhabit_y = oy + int(oh * 0.58)
    contact_y = oy + int(oh * 0.88)
    offer_x = ox + int(ow * 0.36)
    return {
        "project": {"x": left, "y": 82, "size": 32, "tracking": 6.2, "weight": 700, "fill": INK},
        "location": {"x": left, "y": 104, "size": 11, "tracking": 3.6, "weight": 600, "fill": MUTED},
        "headline": {"x": left, "y": 160, "size": 42, "tracking": 3.2, "weight": 600, "fill": INK},
        "offer": {"x": offer_x, "y": lantern_y, "size": 124, "tracking": -5.2, "weight": 600, "fill": GOLD, "anchor": "start"},
        "offer_label": {"x": offer_x, "y": lantern_y + 36, "size": 13, "tracking": 6.4, "weight": 700, "fill": INK_SOFT, "anchor": "start"},
        "price": {"x": left, "y": inhabit_y, "size": 28, "tracking": 0.6, "weight": 600, "fill": INK, "anchor": "start"},
        "unit": {"x": left + 236, "y": inhabit_y, "size": 16, "tracking": 2.2, "weight": 600, "fill": INK_SOFT, "anchor": "start"},
        "cta": {"x": left, "y": min(H - 52, contact_y + 10), "size": 20, "tracking": 4.6, "weight": 700, "fill": GOLD, "anchor": "start"},
        "cta_rule": {"x": left, "y": min(H - 68, contact_y - 4), "w": 36, "h": 2},
        "closure": {"x": W // 2, "y": H - 28, "size": 11, "tracking": 2.6, "weight": 500, "fill": MUTED, "anchor": "middle"},
        "logo": {"x": left, "y": min(H - 96, contact_y + 36)},
        "object": dict(obj_layout),
    }


def hierarchy_layout_from_register(layout: dict[str, Any]) -> dict[str, Any]:
    """Subset consumed by ResponsiveCommercialHierarchyV2 optical + scale gates."""
    return {
        "project": layout["project"],
        "offer": layout["offer"],
        "offer_label": layout["offer_label"],
        "price": layout["price"],
        "unit": layout["unit"],
        "cta": layout["cta"],
        "cta_rule": layout["cta_rule"],
        "plate": {"x": 0, "y": 0, "w": W, "h": H},
    }


def campaign_svg(
    *,
    field: Image.Image,
    placed: Image.Image,
    overlay: Image.Image,
    contact: Image.Image,
    layout: dict[str, Any],
    logo_markup: str,
    font_css: str,
) -> str:
    ox, oy, ow, oh = layout["object"]["x"], layout["object"]["y"], layout["object"]["w"], layout["object"]["h"]
    logo = logo_markup
    if "<svg" in logo.lower():
        logo = logo.replace("<svg", '<svg width="118" height="28"', 1)
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    p, loc, hd = layout["project"], layout["location"], layout["headline"]
    off, lbl = layout["offer"], layout["offer_label"]
    pr, un, ct = layout["price"], layout["unit"], layout["cta"]
    rule, cl = layout["cta_rule"], layout["closure"]
    lx, ly = layout["logo"]["x"], layout["logo"]["y"]
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;background:{DARK};}}
svg{{display:block;}}
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <image data-semantic="creative_field" href="{_png_data_uri(field)}" x="0" y="0" width="{W}" height="{H}"/>

  <text data-role="project" x="{p['x']}" y="{p['y']}"
        font-family="Hybrid Grotesk, sans-serif" font-size="{p['size']}" font-weight="{p['weight']}"
        fill="{p['fill']}" letter-spacing="{p['tracking']}">THE TEMPLE</text>
  <text x="{loc['x']}" y="{loc['y']}"
        font-family="Hybrid Grotesk, sans-serif" font-size="{loc['size']}" font-weight="{loc['weight']}"
        fill="{loc['fill']}" letter-spacing="{loc['tracking']}">WASHINGTON D.C.</text>
  <text x="{hd['x']}" y="{hd['y']}"
        font-family="Hybrid Serif, serif" font-size="{hd['size']}" font-weight="{hd['weight']}"
        fill="{hd['fill']}" letter-spacing="{hd['tracking']}">{escape(HEADLINE)}</text>

  <text data-role="offer" x="{off['x']}" y="{off['y']}" text-anchor="{off.get('anchor', 'start')}"
        font-family="Hybrid Serif, serif" font-size="{off['size']}" font-weight="{off['weight']}"
        fill="{off['fill']}" letter-spacing="{off['tracking']}">{escape(REQUIRED_FACTS['discount'])}</text>
  <text data-role="offer_label" x="{lbl['x']}" y="{lbl['y']}"
        font-family="Hybrid Grotesk, sans-serif" font-size="{lbl['size']}" font-weight="{lbl['weight']}"
        fill="{lbl['fill']}" letter-spacing="{lbl['tracking']}">{escape(REQUIRED_FACTS['discount_label'])}</text>

  <image href="{_png_data_uri(contact)}" x="0" y="0" width="{W}" height="{H}"/>
  <image data-semantic="project_photo" href="{_png_data_uri(placed)}" x="{ox}" y="{oy}" width="{ow}" height="{oh}"/>
  <image data-semantic="atmosphere_occlusion" href="{_png_data_uri(overlay)}" x="0" y="0" width="{W}" height="{H}"/>

  <text data-role="price" x="{pr['x']}" y="{pr['y']}"
        font-family="Hybrid Serif, serif" font-size="{pr['size']}" font-weight="{pr['weight']}"
        fill="{pr['fill']}" letter-spacing="{pr['tracking']}">{escape(REQUIRED_FACTS['list_price'])}</text>
  <text data-role="unit" x="{un['x']}" y="{un['y']}"
        font-family="Hybrid Grotesk, sans-serif" font-size="{un['size']}" font-weight="{un['weight']}"
        fill="{un['fill']}" letter-spacing="{un['tracking']}">{escape(unit)}</text>

  <rect data-role="cta_cue" x="{rule['x']}" y="{rule['y']}" width="{rule['w']}" height="{rule['h']}" fill="{GOLD}"/>
  <text data-role="cta" x="{ct['x']}" y="{ct['y']}"
        font-family="Hybrid Grotesk, sans-serif" font-size="{ct['size']}" font-weight="{ct['weight']}"
        fill="{ct['fill']}" letter-spacing="{ct['tracking']}">{escape(REQUIRED_FACTS['cta'])}</text>

  <g data-semantic="project_logo" transform="translate({lx}, {ly})"
     style="filter:brightness(0) invert(1);opacity:0.92">{logo}</g>
  <text x="{cl['x']}" y="{cl['y']}" text-anchor="middle"
        font-family="Hybrid Serif, serif" font-size="{cl['size']}" font-weight="{cl['weight']}"
        fill="{cl['fill']}" letter-spacing="{cl['tracking']}">{escape(APPROVED_BOTTOM_COPY)}</text>
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
    )
    low = markup.lower()
    return (
        all(token in markup for token in needed)
        and "position:absolute" not in low
        and "rotate(90)" not in markup
        and "border-radius:999" not in low
        and "investhome" not in low
        and "uniloft" not in low
        and "button" not in low
    )


def compose_hybrid_v2(
    *,
    field: Image.Image,
    obj: Image.Image,
    logo_bytes: bytes,
) -> tuple[Image.Image, str, dict[str, Any], dict[str, Any]]:
    layers = integrate_register(field, obj.convert("RGBA"))
    layout = register_type_layout(layers["layout"])
    hier_layout = hierarchy_layout_from_register(layout)
    optical = optical_engine_report(hier_layout)
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
        field=layers["field"],
        placed=layers["placed"],
        overlay=layers["overlay"],
        contact=Image.alpha_composite(layers["ambient"], layers["cast"]),
        layout=layout,
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_css,
    )
    if not html_copy_ok(markup):
        raise RuntimeError("Phase 11.9 SVG copy gate failed")
    image = render_svg_html_to_png(markup, width=W, height=H, scale=RENDER_SCALE)
    hierarchy = evaluate_hierarchy(image, hier_layout)
    meta = {
        "renderer": "chromium_svg_hybrid_v2_register",
        "old_compiler_used": False,
        "concept": "THE_REGISTER",
        "layout": layout,
        "object_layout": layers["layout"],
        "optical": optical,
        "hierarchy": hierarchy,
        "contact": layers["contact"],
        "match": layers["match"],
        "output_size": list(image.size),
        "layer_order": (
            "field",
            "identity_headline",
            "printed_offer_in_shaft",
            "contact",
            "object",
            "atmosphere_feet",
            "price_unit_inhabited",
            "cta_contact",
            "logo_closure",
        ),
        "generated_architecture_pixels": 0,
    }
    return image, markup, meta, layers
