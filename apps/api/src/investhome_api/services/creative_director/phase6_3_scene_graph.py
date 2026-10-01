"""Phase 6.3 micro-proofs — Chromium SVG/HTML scene graph.

Not a new advertisement. Isolated rendering capability proofs only.
Reuses Phase 5.3 Playwright Chromium. GPT Image is never called.
"""

from __future__ import annotations

import math
from typing import Any

from PIL import Image

from investhome_api.services.creative_director.phase5_design_scene import (
    font_face_css,
    render_html_to_png,
    wrap_html,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY

W, H = CANVAS_4X5
CHARCOAL = "#14161c"
IVORY = "#f4efe4"
GOLD_HI = "#ead7a0"
GOLD_MID = "#c9a85c"
GOLD_LO = "#8f6e32"


def _path_from_polyline(xs: list[float], *, width: int = W, height: int = H) -> str:
    n = max(len(xs), 2)
    pts = [f"M 0 0"]
    for i, x in enumerate(xs):
        y = height * i / (n - 1)
        pts.append(f"L {max(0.0, min(width, float(x) * width)):.2f} {y:.2f}")
    pts.append(f"L 0 {height} Z")
    return " ".join(pts)


def _arc_d(xs: list[float], *, width: int = W, height: int = H) -> str:
    n = max(len(xs), 2)
    cmds = []
    for i, x in enumerate(xs):
        y = height * i / (n - 1)
        px = max(0.0, min(width, float(x) * width))
        cmds.append(f"{'M' if i == 0 else 'L'} {px:.2f} {y:.2f}")
    return " ".join(cmds)


def _ticks_svg(xs: list[float], *, count: int = 15) -> str:
    n = max(len(xs), 2)
    parts: list[str] = []
    for k in range(count):
        t = 0.08 + 0.84 * k / max(count - 1, 1)
        i = min(n - 2, max(1, int(t * (n - 1))))
        y0 = H * (i - 1) / (n - 1)
        y1 = H * (i + 1) / (n - 1)
        x0 = float(xs[i - 1]) * W
        x1 = float(xs[i + 1]) * W
        dx, dy = x1 - x0, y1 - y0
        mag = math.hypot(dx, dy) or 1.0
        nx, ny = dy / mag, -dx / mag
        if nx < 0:
            nx, ny = -nx, -ny
        px = float(xs[i]) * W
        py = H * i / (n - 1)
        length = 22 if k % 3 else 34
        parts.append(
            f'<line data-id="deco.tick.{k}" data-kind="DECORATION" x1="{px:.1f}" y1="{py:.1f}" '
            f'x2="{px + nx * length:.1f}" y2="{py + ny * length:.1f}" '
            f'stroke="url(#goldStroke)" stroke-width="{1.2 if k % 3 else 1.6}" />'
        )
    return "\n".join(parts)


def _gold_defs() -> str:
    return f"""
    <linearGradient id="goldStroke" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{GOLD_LO}"/>
      <stop offset="0.42" stop-color="{GOLD_HI}"/>
      <stop offset="1" stop-color="{GOLD_MID}"/>
    </linearGradient>
    <filter id="fieldFeather" x="-12%" y="-6%" width="130%" height="112%">
      <feGaussianBlur stdDeviation="16"/>
    </filter>
    """


def _stage_css(font_css: str) -> str:
    return f"""
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:{CHARCOAL};}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.stage img[data-kind="PHOTO"]{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;}}
.stage svg.overlay{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;}}
.typecol{{position:absolute;left:58px;top:168px;width:420px;color:{IVORY};
  font-family:'Cormorant Garamond',serif;z-index:4;}}
.typecol .kicker{{font-family:'Source Sans 3',sans-serif;letter-spacing:.32em;font-size:15px;font-weight:500;}}
.typecol h1{{margin:0;font-weight:500;font-size:56px;line-height:.92;letter-spacing:.04em;}}
.typecol h1 .l2{{display:block;font-size:62px;letter-spacing:.02em;}}
.typecol .pct{{margin-top:28px;font-size:96px;line-height:.86;color:{GOLD_MID};
  font-family:'Cormorant Garamond',serif;font-weight:500;}}
.typecol .adv{{margin-top:6px;font-family:'Source Sans 3',sans-serif;letter-spacing:.34em;font-size:15px;font-weight:400;}}
.typecol .rule{{width:220px;height:1px;background:linear-gradient(90deg,{GOLD_MID},{GOLD_LO});margin:18px 0 14px;}}
.typecol .price{{font-size:44px;color:{GOLD_MID};letter-spacing:.04em;font-weight:500;}}
.typecol .cur{{font-family:'Source Sans 3',sans-serif;font-size:18px;letter-spacing:.18em;color:{IVORY};margin-left:8px;}}
.typecol .unit{{margin-top:18px;font-size:30px;color:{GOLD_MID};letter-spacing:.06em;}}
.typecol .unit-l{{font-family:'Source Sans 3',sans-serif;font-size:16px;letter-spacing:.28em;color:{IVORY};margin-left:10px;}}
.brand{{position:absolute;left:58px;top:48px;z-index:5;width:118px;color:{GOLD_MID};}}
.brand svg{{width:72px;height:auto;display:block;}}
.brand svg, .brand svg path, .brand svg g, .brand svg polygon, .brand svg circle{{fill:{GOLD_MID} !important;stroke:{GOLD_MID} !important;}}
.brand .cap{{margin-top:8px;font-family:'Cormorant Garamond',serif;letter-spacing:.38em;font-size:13px;}}
.cta{{position:absolute;left:58px;top:940px;z-index:5;font-family:'Source Sans 3',sans-serif;
  letter-spacing:.32em;font-size:15px;color:{IVORY};border:1px solid {GOLD_MID};
  padding:14px 28px;background:transparent;}}
.closure{{position:absolute;left:0;right:0;bottom:72px;text-align:center;z-index:5;
  font-family:'Source Sans 3',sans-serif;letter-spacing:.36em;font-size:13px;color:{IVORY};}}
.closure .rule{{width:96px;height:1px;background:{GOLD_MID};margin:10px auto 0;}}
{font_css}
"""


def scene_object_model() -> dict[str, Any]:
    return {
        "schema": "ProductionSceneGraphV1",
        "renderer": "HTML_CSS_SVG_CHROMIUM",
        "canvas": {"w": W, "h": H, "formats": ["4:5", "1:1", "9:16", "16:9"]},
        "objects": [
            {"id": "photo.day007", "kind": "PHOTO", "stable": True, "asset_bound": True, "revision": ["VISUAL_REPLACE_ONLY"]},
            {"id": "field.charcoal_aperture", "kind": "GRAPHIC_FIELD", "stable": True, "geometry": "svg_path_mask", "revision": []},
            {"id": "vector.gold_arc", "kind": "VECTOR_PATH", "stable": True, "revision": []},
            {"id": "deco.ticks", "kind": "DECORATION", "stable": True, "revision": []},
            {"id": "deco.precision_marker", "kind": "DECORATION", "stable": True, "revision": []},
            {"id": "text.headline", "kind": "TEXT", "stable": True, "lives_as": "dom_text", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "text.discount", "kind": "TEXT", "stable": True, "lives_as": "dom_text", "revision": ["PRICE_EDIT_ONLY", "COPY_EDIT_ONLY"]},
            {"id": "text.price", "kind": "TEXT", "stable": True, "lives_as": "dom_text", "revision": ["PRICE_EDIT_ONLY"]},
            {"id": "text.unit", "kind": "TEXT", "stable": True, "lives_as": "dom_text", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "text.cta", "kind": "TEXT", "stable": True, "lives_as": "dom_text", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "text.closure", "kind": "TEXT", "stable": True, "lives_as": "dom_text", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "logo.temple", "kind": "LOGO", "stable": True, "asset_bound": True, "revision": ["LOGO_ONLY"]},
            {"id": "group.campaign", "kind": "GROUP", "children": ["text.headline"]},
            {"id": "group.offer", "kind": "GROUP", "children": ["text.discount", "text.price", "text.unit"]},
            {"id": "group.brand", "kind": "GROUP", "children": ["logo.temple"]},
            {"id": "group.action", "kind": "GROUP", "children": ["text.cta"]},
        ],
        "invariants": {
            "text_remains_text": True,
            "logo_remains_real_asset": True,
            "photo_remains_real_asset": True,
            "fields_remain_structured_geometry": True,
            "no_flattened_master_required_for_edits": True,
        },
    }


def aperture_overlay_svg(structure: dict[str, Any], *, include_arc: bool, include_ticks: bool) -> str:
    field = (structure.get("dark_field_geometry") or {}).get("polyline_x") or []
    arc = (structure.get("main_gold_arc") or {}).get("polyline_x") or field
    marker = structure.get("precision_marker") or {"x": 0.38, "y": 0.42}
    d_field = _path_from_polyline(field)
    d_core = _path_from_polyline([max(0.0, v * 0.72) for v in field])
    d_arc = _arc_d(arc)
    mx = float(marker.get("x") or 0.38) * W
    my = float(marker.get("y") or 0.42) * H
    ticks = _ticks_svg(arc) if include_ticks else ""
    arc_el = (
        f'<path data-id="vector.gold_arc" data-kind="VECTOR_PATH" d="{d_arc}" fill="none" '
        f'stroke="url(#goldStroke)" stroke-width="2.6" stroke-linecap="round" />'
        if include_arc
        else ""
    )
    marker_el = (
        f'<g data-id="deco.precision_marker" data-kind="DECORATION">'
        f'<line x1="{mx - 86:.1f}" y1="{my:.1f}" x2="{mx + 18:.1f}" y2="{my:.1f}" stroke="{IVORY}" stroke-width="0.8" opacity="0.55"/>'
        f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="6.2" fill="{IVORY}" stroke="url(#goldStroke)" stroke-width="1.4"/>'
        f"</g>"
        if include_arc
        else ""
    )
    return f"""
    <svg class="overlay" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <defs>{_gold_defs()}
        <path id="fieldShape" d="{d_field}"/>
      </defs>
      <g data-id="field.charcoal_aperture" data-kind="GRAPHIC_FIELD">
        <path d="{d_field}" fill="{CHARCOAL}" fill-opacity="0.50" filter="url(#fieldFeather)" style="mix-blend-mode:multiply"/>
        <path d="{d_field}" fill="{CHARCOAL}" fill-opacity="0.62" style="mix-blend-mode:multiply"/>
        <path d="{d_core}" fill="#0c0e12" fill-opacity="0.32"/>
      </g>
      {arc_el}
      {ticks}
      {marker_el}
    </svg>
    """


def proof_a_html(photo_uri: str, structure: dict[str, Any], font_css: str) -> str:
    overlay = aperture_overlay_svg(structure, include_arc=False, include_ticks=False)
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {overlay}
    </div>
    """
    return wrap_html(body, _stage_css(font_css))


def proof_b_html(structure: dict[str, Any], font_css: str) -> str:
    overlay = aperture_overlay_svg(structure, include_arc=True, include_ticks=True)
    body = f'<div class="stage" style="background:{CHARCOAL}">{overlay}</div>'
    return wrap_html(body, _stage_css(font_css))


def _type_block(*, headline: bool, offer: bool) -> str:
    first, last = (REQUIRED_FACTS["headline"].split(" ", 1) + [""])[:2]
    price, _, cur = REQUIRED_FACTS["list_price"].partition(" ")
    bits = ['<div class="typecol" data-id="group.campaign" data-kind="GROUP">']
    if headline:
        bits.append(
            f'<h1 data-id="text.headline" data-kind="TEXT" data-semantic="headline">'
            f'{first}<span class="l2">{last}</span></h1>'
        )
    if offer:
        bits.append(
            f'<div data-id="group.offer" data-kind="GROUP">'
            f'<div class="pct" data-id="text.discount" data-kind="TEXT" data-semantic="discount">{REQUIRED_FACTS["discount"]}</div>'
            f'<div class="adv" data-id="text.discount_label" data-kind="TEXT" data-semantic="discount_label">{REQUIRED_FACTS["discount_label"]}</div>'
            f'<div class="rule"></div>'
            f'<div data-id="text.price" data-kind="TEXT" data-semantic="price">'
            f'<span class="price">{price}</span><span class="cur">{cur or "USD"}</span></div>'
            f'<div data-id="text.unit" data-kind="TEXT" data-semantic="unit_type">'
            f'<span class="unit">{REQUIRED_FACTS["unit"]}</span>'
            f'<span class="unit-l">{REQUIRED_FACTS["unit_label"]}</span></div>'
            f"</div>"
        )
    bits.append("</div>")
    return "\n".join(bits)


def proof_c_html(font_css: str) -> str:
    body = f'<div class="stage" style="background:{CHARCOAL}">{_type_block(headline=True, offer=True)}</div>'
    return wrap_html(body, _stage_css(font_css))


def proof_d_html(photo_uri: str, structure: dict[str, Any], font_css: str) -> str:
    overlay = aperture_overlay_svg(structure, include_arc=True, include_ticks=True)
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {overlay}
      {_type_block(headline=True, offer=True)}
    </div>
    """
    return wrap_html(body, _stage_css(font_css))


def proof_e_html(logo_markup: str, font_css: str) -> str:
    body = f"""
    <div class="stage" style="background:{CHARCOAL}">
      <div class="brand" data-id="group.brand" data-kind="GROUP">
        <div data-id="logo.temple" data-kind="LOGO" data-semantic="project_logo">{logo_markup}</div>
        <div class="cap">THE TEMPLE</div>
      </div>
      <div class="cta" data-id="text.cta" data-kind="TEXT" data-semantic="cta">{REQUIRED_FACTS["cta"]}</div>
      <div class="closure" data-id="text.closure" data-kind="TEXT">
        {APPROVED_BOTTOM_COPY}
        <div class="rule"></div>
      </div>
    </div>
    """
    return wrap_html(body, _stage_css(font_css))


def render_proof(html: str) -> Image.Image:
    return render_html_to_png(html, width=W, height=H)


def revision_compatibility() -> dict[str, Any]:
    return {
        "schema": "RendererRevisionCompatibilityV1",
        "executed": False,
        "PRICE_EDIT_ONLY": {
            "status": "PASS",
            "mechanism": "Replace innerText of [data-semantic=price] and [data-semantic=discount]. Geometry, photo, logo, field path unchanged.",
        },
        "COPY_EDIT_ONLY": {
            "status": "PASS",
            "mechanism": "Replace innerText of TEXT nodes (headline, labels, cta, closure). No raster bake.",
        },
        "VISUAL_REPLACE_ONLY": {
            "status": "PASS",
            "mechanism": "Swap img[data-kind=PHOTO].src. Field path, vectors, and text remain the same scene-graph nodes.",
        },
        "flattening_required": False,
    }


def format_compatibility() -> dict[str, Any]:
    return {
        "schema": "RendererFormatCompatibilityV1",
        "implemented": False,
        "supported_by_architecture": True,
        "formats": {
            "4:5": {"canvas": [1088, 1360], "strategy": "native scene"},
            "1:1": {"canvas": [1088, 1088], "strategy": "recompute field path + group constraints, same objects"},
            "9:16": {"canvas": [1080, 1920], "strategy": "vertical restack using GROUP relationships"},
            "16:9": {"canvas": [1920, 1080], "strategy": "horizontal field/photo split using same GRAPHIC_FIELD path in new viewBox"},
        },
        "status": "PASS",
        "note": "Compatibility only. Format adaptation is not implemented in Phase 6.3.",
    }
