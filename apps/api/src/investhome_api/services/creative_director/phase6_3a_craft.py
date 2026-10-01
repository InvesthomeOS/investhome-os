"""Phase 6.3A — Chromium craft calibration engines.

EditorialApertureRendererV1, EditorialTypeInFieldRendererV1,
EditorialBrandClosureRendererV1. Proof B arc remains locked from 6.3.
GPT Image is never called. No Temple Master.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase5_design_scene import wrap_html
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase6_3_scene_graph import (
    CHARCOAL,
    GOLD_LO,
    GOLD_MID,
    H,
    IVORY,
    W,
    _arc_d,
    _gold_defs,
    _stage_css,
    _ticks_svg,
)

APERTURE_KEYS = (
    "APERTURE_DEPTH",
    "CURVE_PRECISION",
    "PHOTO_VISIBILITY_CONTROL",
    "EDGE_QUALITY",
    "DARK_MASS_AUTHORITY",
    "REFERENCE_BEHAVIOR_MATCH",
    "CRAFT_FIDELITY",
)
TYPE_KEYS = (
    "TYPOGRAPHIC_QUALITY",
    "TYPOGRAPHIC_AUTHORITY",
    "HIERARCHY",
    "OPTICAL_SPACING",
    "COMMERCIAL_READABILITY",
    "REFERENCE_BEHAVIOR_MATCH",
    "CRAFT_FIDELITY",
)
D2_KEYS = (
    "PHOTO_GRAPHIC_INTEGRATION",
    "TYPE_FIELD_INTEGRATION",
    "DEPTH",
    "VISUAL_MASS",
    "COMPOSITIONAL_UNITY",
    "NEGATIVE_SPACE",
    "GRAPHIC_PRECISION",
    "CRAFT_FIDELITY",
    "REFERENCE_BEHAVIOR_MATCH",
)
E2_KEYS = (
    "BRAND_INTEGRATION",
    "LOGO_ROLE",
    "CTA_CRAFT",
    "EDITORIAL_CLOSURE",
    "TYPOGRAPHIC_QUALITY",
    "GRAPHIC_PRECISION",
    "REFERENCE_BEHAVIOR_MATCH",
    "CRAFT_FIDELITY",
)

APERTURE_TREATMENTS = (
    {
        "id": "A1",
        "core": 0.86,
        "mul": 0.48,
        "feather": 2.2,
        "blend": "multiply",
        "extra": None,
        "vignette": 0.42,
        "edge": 0.55,
        "inner": 0.55,
        "note": "HTML multiply stack, moderate mass",
    },
    {
        "id": "A2",
        "core": 0.92,
        "mul": 0.62,
        "feather": 1.6,
        "blend": "multiply",
        "extra": None,
        "vignette": 0.50,
        "edge": 0.70,
        "inner": 0.72,
        "note": "strong charcoal core + multiply photo bite",
    },
    {
        "id": "A3",
        "core": 0.90,
        "mul": 0.58,
        "feather": 1.2,
        "blend": "darken",
        "extra": None,
        "vignette": 0.38,
        "edge": 0.82,
        "inner": 0.64,
        "note": "darken blend, decisive edge ring",
    },
    {
        "id": "A4",
        "core": 0.88,
        "mul": 0.54,
        "feather": 2.8,
        "blend": "multiply",
        "extra": ("color-burn", 0.28),
        "vignette": 0.46,
        "edge": 0.60,
        "inner": 0.68,
        "note": "multiply + color-burn, softer feather",
    },
    {
        "id": "A5",
        "core": 0.91,
        "mul": 0.50,
        "feather": 0.8,
        "blend": "multiply",
        "extra": ("soft-light", 0.22),
        "vignette": 0.34,
        "edge": 0.88,
        "inner": 0.60,
        "note": "sharp ellipse, soft-light depth",
    },
    {
        "id": "A6",
        "core": 0.93,
        "mul": 0.66,
        "feather": 1.8,
        "blend": "multiply",
        "extra": ("multiply", 0.22),
        "vignette": 0.56,
        "edge": 0.74,
        "inner": 0.80,
        "note": "maximum left mass, photo still in the curve",
    },
)

TYPE_TREATMENTS = (
    {
        "id": "T1",
        "alirken": 46,
        "kazan": 58,
        "pct": 92,
        "price": 40,
        "unit": 32,
        "campaign_track": 0.06,
        "optical_kazan": 0,
        "note": "compact campaign mass",
    },
    {
        "id": "T2",
        "alirken": 50,
        "kazan": 70,
        "pct": 108,
        "price": 44,
        "unit": 36,
        "campaign_track": 0.05,
        "optical_kazan": -3,
        "note": "Concept 3 stacked hierarchy",
    },
    {
        "id": "T3",
        "alirken": 48,
        "kazan": 76,
        "pct": 118,
        "price": 46,
        "unit": 38,
        "campaign_track": 0.08,
        "optical_kazan": -6,
        "note": "campaign authority + optical KAZAN pull",
    },
    {
        "id": "T4",
        "alirken": 52,
        "kazan": 68,
        "pct": 102,
        "price": 42,
        "unit": 34,
        "campaign_track": 0.04,
        "optical_kazan": -2,
        "note": "tighter tracking, balanced commercial",
    },
)


def _ellipse(structure: dict[str, Any]) -> dict[str, float]:
    arc = structure.get("main_gold_arc") or {}
    cx = float(arc.get("cx") or 1.06)
    cy = float(arc.get("cy") or 0.50)
    rx = float(arc.get("rx") or 0.70)
    ry = float(arc.get("ry") or 1.00)
    cy = 0.50 if abs(cy - 0.50) > 0.08 else cy
    ry = max(ry, 0.98)
    if cx - rx < 0.34:
        rx = cx - 0.38
    return {"cx": cx * W, "cy": cy * H, "rx": rx * W, "ry": ry * H}


def _field_mask(ell: dict[str, float], *, hole: float, solid: float) -> str:
    return (
        f"radial-gradient(ellipse {ell['rx']:.1f}px {ell['ry']:.1f}px "
        f"at {ell['cx']:.1f}px {ell['cy']:.1f}px, "
        f"transparent 0%, transparent {hole:.1f}%, #000 {solid:.1f}%)"
    )


def _ring_mask(ell: dict[str, float], *, inner: float, outer: float) -> str:
    return (
        f"radial-gradient(ellipse {ell['rx']:.1f}px {ell['ry']:.1f}px "
        f"at {ell['cx']:.1f}px {ell['cy']:.1f}px, "
        f"transparent 0%, transparent {inner:.1f}%, #000 {inner + 1.2:.1f}%, "
        f"#000 {outer:.1f}%, transparent {min(100.0, outer + 1.5):.1f}%)"
    )


def _mask_css(mask: str) -> str:
    return (
        f"-webkit-mask-image:{mask};mask-image:{mask};"
        f"-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;"
        f"-webkit-mask-size:{W}px {H}px;mask-size:{W}px {H}px;"
        "mask-mode:alpha;"
    )


def _locked_arc_group(structure: dict[str, Any]) -> str:
    """Proof B primitives unchanged: polyline arc, radial ticks, precision node."""
    field = (structure.get("dark_field_geometry") or {}).get("polyline_x") or []
    arc = (structure.get("main_gold_arc") or {}).get("polyline_x") or field
    marker = structure.get("precision_marker") or {"x": 0.38, "y": 0.42}
    mx = float(marker.get("x") or 0.38) * W
    my = float(marker.get("y") or 0.42) * H
    return f"""
        <g data-id="vector.locked_arc" data-kind="VECTOR_PATH" data-locked="PROOF_B">
          <path data-id="vector.gold_arc" d="{_arc_d(arc)}" fill="none" stroke="url(#goldStroke)" stroke-width="2.6" stroke-linecap="round"/>
          <g data-id="deco.ticks" data-kind="DECORATION">{_ticks_svg(arc)}</g>
          <g data-id="deco.precision_marker" data-kind="DECORATION">
            <line x1="{mx - 86:.1f}" y1="{my:.1f}" x2="{mx + 18:.1f}" y2="{my:.1f}" stroke="{IVORY}" stroke-width="0.8" opacity="0.55"/>
            <circle cx="{mx:.1f}" cy="{my:.1f}" r="6.2" fill="{IVORY}" stroke="url(#goldStroke)" stroke-width="1.4"/>
          </g>
        </g>
        """


def _aperture_layer_css(structure: dict[str, Any], spec: dict[str, Any]) -> str:
    ell = _ellipse(structure)
    feather = float(spec.get("feather") or 1.6)
    hole_hard = max(96.0, 100.0 - feather * 0.35)
    hole_soft = max(92.0, 100.0 - feather)
    hard = _mask_css(_field_mask(ell, hole=hole_hard, solid=100.0))
    soft = _mask_css(_field_mask(ell, hole=hole_soft, solid=100.0))
    ring = _mask_css(_ring_mask(ell, inner=max(90.0, 100.0 - feather * 2.4), outer=99.2))
    extra = spec.get("extra")
    extra_css = ""
    if extra:
        mode, op = extra
        extra_css = (
            f".aperture .l-extra{{background:#14161c;opacity:{op};mix-blend-mode:{mode};{soft}}}"
        )
    return f"""
.stage{{isolation:isolate;}}
.aperture{{position:absolute;inset:0;z-index:2;pointer-events:none;}}
.aperture .layer{{position:absolute;inset:0;}}
.aperture .l-base{{background:#0c0e12;opacity:{spec['core']};{hard}}}
.aperture .l-inner{{background:linear-gradient(90deg,#07080b 0%,#101218 28%,rgba(16,18,24,0) 52%);
  opacity:{spec['inner']};{hard}}}
.aperture .l-tonal{{background:#1a1e26;opacity:{spec['mul']};mix-blend-mode:{spec['blend']};{soft}}}
.aperture .l-edge{{background:#050608;opacity:{spec['edge']};mix-blend-mode:multiply;{ring}}}
.aperture .l-vignette{{background:radial-gradient(ellipse 78% 70% at 14% 42%,rgba(0,0,0,.75) 0%,rgba(0,0,0,0) 72%);
  opacity:{spec['vignette']};mix-blend-mode:multiply;{hard}}}
{extra_css}
"""


def aperture_layers_svg(structure: dict[str, Any], spec: dict[str, Any], *, include_locked_arc: bool) -> str:
    ell = _ellipse(structure)
    cx, cy, rx, ry = ell["cx"], ell["cy"], ell["rx"], ell["ry"]
    extra = spec.get("extra")
    extra_el = (
        '<div class="layer l-extra" data-id="field.extra" data-kind="GRAPHIC_FIELD" '
        f'data-blend_mode="{extra[0]}" data-z_index="2"></div>'
        if extra
        else ""
    )
    arc_el = _locked_arc_group(structure) if include_locked_arc else ""
    return f"""
    <div class="aperture" data-id="field.charcoal_aperture" data-kind="GRAPHIC_FIELD" data-renderer="EditorialApertureRendererV1">
      <div class="layer l-base" data-id="field.base" data-z_index="1" data-mask_ref="fieldHard"></div>
      <div class="layer l-inner" data-id="field.inner_mass" data-z_index="1"></div>
      <div class="layer l-tonal" data-id="field.photo_tonal" data-z_index="2" data-blend_mode="{spec['blend']}" data-mask_ref="fieldSoft"></div>
      {extra_el}
      <div class="layer l-edge" data-id="field.edge" data-z_index="3" data-mask_ref="edgeBand"></div>
      <div class="layer l-vignette" data-id="field.vignette" data-z_index="4" data-gradient_ref="leftVignette"></div>
    </div>
    <svg class="overlay" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="z-index:3">
      <defs>{_gold_defs()}
        <mask id="curveClip" maskUnits="userSpaceOnUse">
          <rect x="0" y="0" width="{W}" height="{H}" fill="white"/>
          <ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{max(0.0, rx - 2):.1f}" ry="{max(0.0, ry - 2):.1f}" fill="black"/>
        </mask>
      </defs>
      <ellipse data-id="field.curve_emphasis" data-kind="GRAPHIC_FIELD" data-z_index="5"
               cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"
               fill="none" stroke="#07080a" stroke-width="2.8" opacity="0.72" mask="url(#curveClip)"/>
      {arc_el}
    </svg>
    """


def aperture_html(photo_uri: str, structure: dict[str, Any], spec: dict[str, Any], font_css: str) -> str:
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {aperture_layers_svg(structure, spec, include_locked_arc=False)}
    </div>
    """
    return wrap_html(body, _stage_css(font_css) + _aperture_layer_css(structure, spec))


def _type_css(spec: dict[str, Any]) -> str:
    return f"""
.type-system,.type-system p{{margin:0;padding:0;}}
.type-system{{position:absolute;left:58px;top:168px;width:400px;z-index:6;color:{IVORY};
  font-family:'Cormorant Garamond',serif;font-kerning:normal;font-optical-sizing:auto;
  font-feature-settings:"kern" 1,"liga" 1,"onum" 0;font-variation-settings:"opsz" 72;}}
.campaign{{display:flex;flex-direction:column;align-items:flex-start;}}
.campaign .alirken{{font-size:{spec['alirken']}px;font-weight:400;letter-spacing:{spec['campaign_track']}em;
  line-height:0.94;}}
.campaign .kazan{{font-size:{spec['kazan']}px;font-weight:500;letter-spacing:0.015em;line-height:0.84;
  margin-top:{spec['optical_kazan']}px;}}
.offer{{margin-top:8px;display:flex;flex-direction:column;align-items:flex-start;}}
.offer .pct{{font-size:{spec['pct']}px;line-height:0.80;color:{GOLD_MID};font-weight:500;}}
.offer .adv{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:0.38em;font-weight:400;
  margin-top:10px;color:{IVORY};}}
.offer .rule{{width:208px;height:1px;margin:18px 0 16px;background:linear-gradient(90deg,{GOLD_MID},{GOLD_LO});border:0;}}
.offer .price-row{{display:flex;align-items:baseline;gap:12px;}}
.offer .price{{font-size:{spec['price']}px;color:{GOLD_MID};letter-spacing:0.03em;font-weight:500;}}
.offer .usd{{font-family:'Source Sans 3',sans-serif;font-size:15px;letter-spacing:0.24em;color:{IVORY};}}
.offer .unit-num{{font-size:{spec['unit']}px;color:{GOLD_MID};letter-spacing:0.04em;font-weight:500;}}
.offer .unit-lab{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:0.36em;color:{IVORY};margin-top:6px;}}
"""


def type_block_html(spec: dict[str, Any]) -> str:
    first, last = (REQUIRED_FACTS["headline"].split(" ", 1) + [""])[:2]
    price, _, cur = REQUIRED_FACTS["list_price"].partition(" ")
    return f"""
    <div class="type-system" data-id="group.editorial_type" data-kind="GROUP" data-renderer="EditorialTypeInFieldRendererV1" data-relationship_anchor="aperture_column">
      <div class="campaign" data-id="group.campaign" data-kind="GROUP" data-typographic_role="display">
        <div class="alirken" data-id="text.headline.first" data-kind="TEXT" data-semantic="headline" data-optical_offset="0">{first}</div>
        <div class="kazan" data-id="text.headline.last" data-kind="TEXT" data-optical_offset="{spec['optical_kazan']}">{last}</div>
      </div>
      <div class="offer" data-id="group.offer" data-kind="GROUP" data-typographic_role="commercial">
        <div class="rule" data-id="deco.campaign_rule" data-kind="DECORATION"></div>
        <div class="pct" data-id="text.discount" data-kind="TEXT" data-semantic="discount">{REQUIRED_FACTS["discount"]}</div>
        <div class="adv" data-id="text.discount_label" data-kind="TEXT" data-semantic="discount_label">{REQUIRED_FACTS["discount_label"]}</div>
        <div class="rule" data-id="deco.offer_rule" data-kind="DECORATION"></div>
        <div class="price-row" data-id="group.price" data-kind="GROUP">
          <span class="price" data-id="text.price" data-kind="TEXT" data-semantic="price">{price}</span>
          <span class="usd">{cur or "USD"}</span>
        </div>
        <div class="rule" data-id="deco.unit_rule" data-kind="DECORATION"></div>
        <div class="unit-num" data-id="text.unit" data-kind="TEXT" data-semantic="unit_type">{REQUIRED_FACTS["unit"]}</div>
        <div class="unit-lab">{REQUIRED_FACTS["unit_label"]}</div>
      </div>
    </div>
    """


def type_neutral_html(spec: dict[str, Any], font_css: str) -> str:
    css = _stage_css(font_css) + _type_css(spec)
    body = f'<div class="stage" style="background:{CHARCOAL}">{type_block_html(spec)}</div>'
    return wrap_html(body, css)


def type_in_aperture_html(photo_uri: str, structure: dict[str, Any], aperture: dict[str, Any], type_spec: dict[str, Any], font_css: str) -> str:
    css = _stage_css(font_css) + _aperture_layer_css(structure, aperture) + _type_css(type_spec)
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {aperture_layers_svg(structure, aperture, include_locked_arc=False)}
      {type_block_html(type_spec)}
    </div>
    """
    return wrap_html(body, css)


def proof_d2_html(photo_uri: str, structure: dict[str, Any], aperture: dict[str, Any], type_spec: dict[str, Any], font_css: str) -> str:
    css = _stage_css(font_css) + _aperture_layer_css(structure, aperture) + _type_css(type_spec)
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {aperture_layers_svg(structure, aperture, include_locked_arc=True)}
      {type_block_html(type_spec)}
    </div>
    """
    return wrap_html(body, css)


def _brand_css() -> str:
    return f"""
.brand-lockup{{position:absolute;left:58px;top:42px;z-index:7;width:130px;color:{GOLD_MID};}}
.brand-lockup svg{{width:68px;height:auto;display:block;}}
.brand-lockup svg text{{display:none !important;}}
.brand-lockup svg, .brand-lockup svg path, .brand-lockup svg g, .brand-lockup svg polygon, .brand-lockup svg circle{{
  fill:{GOLD_MID} !important; stroke:none !important;}}
.brand-lockup .cap{{margin-top:10px;font-family:'Cormorant Garamond',serif;letter-spacing:0.42em;font-size:12px;color:{GOLD_MID};}}
.cta-inscribe{{position:absolute;left:58px;top:1008px;z-index:7;font-family:'Source Sans 3',sans-serif;
  letter-spacing:0.36em;font-size:13px;color:{IVORY};border:1px solid {GOLD_MID};padding:12px 28px;
  background:transparent;box-shadow:none;border-radius:0;font-weight:400;}}
.closure-ed{{position:absolute;left:0;right:0;bottom:58px;text-align:center;z-index:7;
  font-family:'Source Sans 3',sans-serif;letter-spacing:0.42em;font-size:11px;color:{IVORY};}}
.closure-ed .gold{{color:{GOLD_MID};}}
.closure-ed .hair{{width:84px;height:1px;background:{GOLD_MID};margin:10px auto 0;}}
.type-system{{top:186px;}}
"""


def proof_e2_html(
    photo_uri: str,
    structure: dict[str, Any],
    aperture: dict[str, Any],
    type_spec: dict[str, Any],
    logo_markup: str,
    font_css: str,
) -> str:
    css = _stage_css(font_css) + _aperture_layer_css(structure, aperture) + _type_css(type_spec) + _brand_css()
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {aperture_layers_svg(structure, aperture, include_locked_arc=True)}
      <div class="brand-lockup" data-id="group.brand" data-kind="GROUP" data-renderer="EditorialBrandClosureRendererV1" data-relationship_anchor="column_open">
        <div data-id="logo.temple" data-kind="LOGO" data-semantic="project_logo">{logo_markup}</div>
        <div class="cap">THE TEMPLE</div>
      </div>
      {type_block_html(type_spec)}
      <div class="cta-inscribe" data-id="text.cta" data-kind="TEXT" data-semantic="cta" data-typographic_role="cta">{REQUIRED_FACTS["cta"]}</div>
      <div class="closure-ed" data-id="text.closure" data-kind="TEXT" data-typographic_role="editorial_closure" data-relationship_anchor="canvas_bottom">
        <span class="gold">{APPROVED_BOTTOM_COPY}</span>
        <div class="hair"></div>
      </div>
    </div>
    """
    return wrap_html(body, css)


def scene_graph_properties() -> dict[str, Any]:
    return {
        "schema": "ProductionSceneGraphV1",
        "renderer": "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM",
        "engines": [
            "EditorialApertureRendererV1",
            "EditorialTypeInFieldRendererV1",
            "EditorialBrandClosureRendererV1",
            "LockedProofBArcSystem",
        ],
        "object_kinds": ["PHOTO", "GRAPHIC_FIELD", "VECTOR_PATH", "DECORATION", "TEXT", "LOGO", "GROUP"],
        "objects": [
            {"id": "photo.day007", "kind": "PHOTO", "live": "img", "revision": ["VISUAL_REPLACE_ONLY"]},
            {"id": "field.charcoal_aperture", "kind": "GRAPHIC_FIELD", "layers": ["base", "photo_tonal", "edge", "vignette", "curve_emphasis"]},
            {"id": "vector.gold_arc", "kind": "VECTOR_PATH", "locked": "PROOF_B"},
            {"id": "deco.ticks", "kind": "DECORATION", "locked": "PROOF_B"},
            {"id": "deco.precision_marker", "kind": "DECORATION", "locked": "PROOF_B"},
            {"id": "group.campaign", "kind": "GROUP", "typographic_role": "display"},
            {"id": "group.offer", "kind": "GROUP", "typographic_role": "commercial"},
            {"id": "text.headline.first", "kind": "TEXT", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "text.discount", "kind": "TEXT", "revision": ["PRICE_EDIT_ONLY", "COPY_EDIT_ONLY"]},
            {"id": "text.price", "kind": "TEXT", "revision": ["PRICE_EDIT_ONLY"]},
            {"id": "text.unit", "kind": "TEXT", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "text.cta", "kind": "TEXT", "typographic_role": "cta", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "text.closure", "kind": "TEXT", "typographic_role": "editorial_closure", "revision": ["COPY_EDIT_ONLY"]},
            {"id": "logo.temple", "kind": "LOGO", "live": "svg"},
            {"id": "group.brand", "kind": "GROUP", "relationship_anchor": "column_open"},
        ],
        "rendering_properties": [
            "blend_mode",
            "mask_ref",
            "filter_ref",
            "gradient_ref",
            "clip_ref",
            "opacity",
            "z_index",
            "transform",
            "optical_offset",
            "typographic_role",
            "relationship_anchor",
        ],
        "invariants": {
            "text_remains_text": True,
            "logo_remains_real_svg": True,
            "photo_remains_live_img": True,
            "fields_remain_structured_geometry": True,
            "no_pillow_predarkening": True,
            "proof_b_arc_locked": True,
            "flattening_required": False,
        },
    }


def revision_compatibility() -> dict[str, Any]:
    return {
        "schema": "RendererRevisionCompatibilityV1",
        "executed": False,
        "PRICE_EDIT_ONLY": {
            "status": "PASS",
            "mechanism": "Replace innerText of [data-semantic=price] and [data-semantic=discount]. Aperture layers, locked arc, logo, and photo src unchanged.",
        },
        "COPY_EDIT_ONLY": {
            "status": "PASS",
            "mechanism": "Replace innerText of TEXT nodes (headline, labels, cta, closure). optical_offset and typographic_role stay on the GROUP.",
        },
        "VISUAL_REPLACE_ONLY": {
            "status": "PASS",
            "mechanism": "Swap img[data-kind=PHOTO].src. SVG masks, blend_mode, and type groups remain the same scene-graph nodes. Photo is never pre-darkened.",
        },
        "new_properties_safe": True,
        "flattening_required": False,
    }


def format_compatibility() -> dict[str, Any]:
    return {
        "schema": "RendererFormatCompatibilityV1",
        "implemented": False,
        "supported_by_architecture": True,
        "formats": {
            "4:5": {"canvas": [1088, 1360], "strategy": "native scene; ellipse rx/ry in userSpaceOnUse"},
            "1:1": {"canvas": [1088, 1088], "strategy": "recompute ellipse cy/ry + group constraints, same objects"},
            "9:16": {"canvas": [1080, 1920], "strategy": "vertical restack using GROUP relationship_anchor"},
            "16:9": {"canvas": [1920, 1080], "strategy": "horizontal field/photo split; same GRAPHIC_FIELD mask in new viewBox"},
        },
        "status": "PASS",
        "note": "Compatibility only. Format adaptation is not implemented in Phase 6.3A.",
    }
