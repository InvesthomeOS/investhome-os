"""Reference-guided Hybrid V2 reconstruction. Does not modify Hybrid V2 source."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_design_scene import inline_logo_svg
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase11_11_structure import RELATIVE
from investhome_api.services.creative_director.phase11_9_integrate import punch_residual_sky
from investhome_api.services.creative_director.responsive_commercial_hierarchy_v2 import (
    evaluate_hierarchy,
    optical_engine_report,
    render_svg_html_to_png,
)
from investhome_api.services.creative_director.scene_material_integration_v2 import (
    analyze_field,
    match_object_to_field,
)

W, H = CANVAS_4X5
INK = "#E8DFD0"
INK_SOFT = "#C4B49A"
GOLD = "#C4A36A"
MUTED = "#8E7F6E"


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


def foundation_layout(obj: Image.Image) -> dict[str, int]:
    """Place the real Temple fragment as lower-left page mass. Relative DNA, not 00013 pixels."""
    target_h = int(H * RELATIVE["hero_visual_mass_height"])
    scale = target_h / max(obj.size[1], 1)
    ow = max(1, int(obj.size[0] * scale))
    oh = target_h
    max_w = int(W * RELATIVE["hero_visual_mass_width"])
    if ow > max_w:
        scale = max_w / max(obj.size[0], 1)
        ow = max(1, int(obj.size[0] * scale))
        oh = max(1, int(obj.size[1] * scale))
    x = int(W * RELATIVE["hero_left_inset"])
    y = H - oh - int(H * RELATIVE["hero_bottom_inset"])
    return {"x": x, "y": y, "w": ow, "h": oh}


def type_layout(obj_layout: dict[str, int]) -> dict[str, Any]:
    right = int(W * (1.0 - RELATIVE["type_right_inset"]))
    top = int(H * RELATIVE["type_top"])
    rhythm = int(H * RELATIVE["commercial_group_rhythm"])
    offer = max(96, int(H * RELATIVE["offer_size_vs_canvas_height"]))
    identity = max(28, int(offer * RELATIVE["identity_vs_offer"]))
    price = max(22, int(offer * RELATIVE["price_vs_offer"]))
    unit = max(16, int(offer * RELATIVE["unit_vs_offer"]))
    cta = max(20, min(32, int(offer * RELATIVE["cta_vs_offer"])))
    y_id = top
    y_loc = y_id + int(rhythm * 0.85)
    y_off = y_loc + int(rhythm * 2.8)
    y_lbl = y_off + int(offer * 0.28)
    y_val = y_lbl + int(rhythm * 2.2)
    y_cta = y_val + int(rhythm * 2.0)
    # Keep the type column in the void to the right of the stone mass.
    void_left = obj_layout["x"] + int(obj_layout["w"] * 0.72)
    column_right = max(void_left + 220, right)
    column_right = min(int(W * 0.94), column_right)
    unit_x = column_right
    price_x = column_right - min(int(price * 8.6), int(price * 9) - 8)
    return {
        "project": {
            "x": column_right,
            "y": y_id,
            "size": identity,
            "tracking": 5.4,
            "weight": 700,
            "fill": INK,
            "anchor": "end",
        },
        "location": {
            "x": column_right,
            "y": y_loc,
            "size": 12,
            "tracking": 3.4,
            "weight": 600,
            "fill": MUTED,
            "anchor": "end",
        },
        "offer": {
            "x": column_right,
            "y": y_off,
            "size": offer,
            "tracking": -4.8,
            "weight": 600,
            "fill": INK,
            "anchor": "end",
        },
        "offer_label": {
            "x": column_right,
            "y": y_lbl,
            "size": 15,
            "tracking": 5.8,
            "weight": 700,
            "fill": INK_SOFT,
            "anchor": "end",
        },
        "price": {
            "x": price_x,
            "y": y_val,
            "size": price,
            "tracking": 0.5,
            "weight": 600,
            "fill": INK,
            "anchor": "start",
        },
        "unit": {
            "x": unit_x,
            "y": y_val,
            "size": unit,
            "tracking": 2.0,
            "weight": 600,
            "fill": INK_SOFT,
            "anchor": "end",
        },
        "cta": {
            "x": column_right,
            "y": y_cta,
            "size": cta,
            "tracking": 4.2,
            "weight": 700,
            "fill": GOLD,
            "anchor": "end",
        },
        "cta_rule": {
            "x": column_right - 42,
            "y": y_cta - int(cta * 0.95),
            "w": 42,
            "h": 2,
        },
        "closure": {
            "x": column_right,
            "y": int(H * (1.0 - RELATIVE["logo_inset"]) + 18),
            "size": 11,
            "tracking": 2.4,
            "weight": 500,
            "fill": MUTED,
            "anchor": "end",
        },
        "logo": {
            "x": column_right - 118,
            "y": int(H * (1.0 - RELATIVE["logo_inset"] - 0.04)),
        },
        "object": dict(obj_layout),
        "plate": {"x": 0, "y": 0, "w": W, "h": H},
    }


def hierarchy_layout_from_type(layout: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": layout["project"],
        "offer": layout["offer"],
        "offer_label": layout["offer_label"],
        "price": layout["price"],
        "unit": layout["unit"],
        "cta": layout["cta"],
        "cta_rule": layout["cta_rule"],
        "plate": layout["plate"],
    }


def campaign_svg(
    *,
    field: Image.Image,
    placed: Image.Image,
    layout: dict[str, Any],
    logo_markup: str,
    font_css: str,
) -> str:
    ox, oy, ow, oh = layout["object"]["x"], layout["object"]["y"], layout["object"]["w"], layout["object"]["h"]
    logo = logo_markup
    if "<svg" in logo.lower():
        logo = logo.replace("<svg", '<svg width="118" height="28"', 1)
    unit = f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
    p, loc = layout["project"], layout["location"]
    off, lbl = layout["offer"], layout["offer_label"]
    pr, un, ct = layout["price"], layout["unit"], layout["cta"]
    rule, cl = layout["cta_rule"], layout["closure"]
    lx, ly = layout["logo"]["x"], layout["logo"]["y"]

    def txt(spec: dict[str, Any], copy: str, family: str, role: str | None = None) -> str:
        role_attr = f' data-role="{role}"' if role else ""
        return (
            f'<text{role_attr} x="{spec["x"]}" y="{spec["y"]}" text-anchor="{spec.get("anchor", "start")}" '
            f'font-family="{family}" font-size="{spec["size"]}" font-weight="{spec["weight"]}" '
            f'fill="{spec["fill"]}" letter-spacing="{spec["tracking"]}">{escape(copy)}</text>'
        )

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;background:#161210;}}
svg{{display:block;}}
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <image data-semantic="creative_field" href="{_png_data_uri(field)}" x="0" y="0" width="{W}" height="{H}"/>
  <image data-semantic="project_photo" href="{_png_data_uri(placed)}" x="{ox}" y="{oy}" width="{ow}" height="{oh}"/>
  {txt(p, "THE TEMPLE", "Hybrid Grotesk, sans-serif", "project")}
  {txt(loc, "WASHINGTON D.C.", "Hybrid Grotesk, sans-serif")}
  {txt(off, REQUIRED_FACTS["discount"], "Hybrid Grotesk, sans-serif", "offer")}
  {txt(lbl, REQUIRED_FACTS["discount_label"], "Hybrid Grotesk, sans-serif", "offer_label")}
  {txt(pr, REQUIRED_FACTS["list_price"], "Hybrid Grotesk, sans-serif", "price")}
  {txt(un, unit, "Hybrid Grotesk, sans-serif", "unit")}
  <rect data-role="cta_cue" x="{rule['x']}" y="{rule['y']}" width="{rule['w']}" height="{rule['h']}" fill="{GOLD}"/>
  {txt(ct, REQUIRED_FACTS["cta"], "Hybrid Grotesk, sans-serif", "cta")}
  <g data-semantic="project_logo" transform="translate({lx}, {ly})"
     style="filter:brightness(0) invert(1);opacity:0.92">{logo}</g>
  {txt(cl, APPROVED_BOTTOM_COPY, "Hybrid Grotesk, sans-serif")}
</svg>
</body>
</html>
"""


def html_copy_ok(markup: str) -> bool:
    needed = (
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
        and "düzenli" not in low
        and "güvenli" not in low
        and "prestijli" not in low
    )


def compose_reference_guided(
    *,
    field: Image.Image,
    obj: Image.Image,
    logo_bytes: bytes,
) -> tuple[Image.Image, str, dict[str, Any], dict[str, Any]]:
    cleaned = punch_residual_sky(obj.convert("RGBA"))
    stats = analyze_field(field.convert("RGB"))
    matched, match_meta = match_object_to_field(cleaned, stats)
    obj_layout = foundation_layout(matched)
    placed = matched.resize((obj_layout["w"], obj_layout["h"]), Image.Resampling.LANCZOS)
    layout = type_layout(obj_layout)
    hier = hierarchy_layout_from_type(layout)
    optical = optical_engine_report(hier)
    registry = build_font_registry()
    font_css = "\n".join(
        block
        for block in (
            _font_face(registry, "DISPLAY_SANS", "Hybrid Grotesk"),
            _font_face(registry, "EDITORIAL_SANS", "Hybrid Grotesk"),
            _font_face(registry, "COMMERCIAL_NUMBER", "Hybrid Grotesk"),
        )
        if block
    )
    markup = campaign_svg(
        field=field.convert("RGB"),
        placed=placed,
        layout=layout,
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_css,
    )
    if not html_copy_ok(markup):
        raise RuntimeError("Phase 11.11 SVG copy gate failed")
    image = render_svg_html_to_png(markup, width=W, height=H, scale=2)
    hierarchy = evaluate_hierarchy(image, hier)
    fused = field.convert("RGBA")
    fused.paste(placed, (obj_layout["x"], obj_layout["y"]), placed)
    meta = {
        "renderer": "chromium_svg_reference_guided_hybrid_v2",
        "old_compiler_used": False,
        "layout": layout,
        "object_layout": obj_layout,
        "optical": optical,
        "hierarchy": hierarchy,
        "match": match_meta,
        "output_size": list(image.size),
        "generated_architecture_pixels": 0,
        "full_silhouette_drop_shadow": False,
    }
    layers = {
        "field": field.convert("RGB"),
        "object": cleaned,
        "placed": placed,
        "fused": fused.convert("RGB"),
        "layout": obj_layout,
    }
    return image, markup, meta, layers
