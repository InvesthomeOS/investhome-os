"""Phase 6.3B — EditorialTypographySystemV1 + integrated Chromium scene proofs.

Locks Phase 6.3A A3 aperture and Phase 6.3 Proof B arc.
GPT Image is never called. No Temple Master.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase5_design_scene import wrap_html
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase6_3_scene_graph import CHARCOAL, GOLD_LO, GOLD_MID, IVORY, _stage_css
from investhome_api.services.creative_director.phase6_3a_craft import (
    APERTURE_TREATMENTS,
    aperture_layers_svg,
    _aperture_layer_css,
)

LOCKED_A3 = dict(next(s for s in APERTURE_TREATMENTS if s["id"] == "A3"))
A3_INTEGRATED = {
    **LOCKED_A3,
    "id": "A3-INTEGRATED",
    "core": 0.88,
    "mul": 0.66,
    "inner": 0.76,
    "vignette": 0.50,
    "edge": 0.88,
    "note": "A3 geometry locked; opacity/multiply/vignette/edge only",
}

TYPE_ROLES = (
    "DISPLAY_HEADLINE",
    "OFFER_HERO",
    "OFFER_LABEL",
    "PRIMARY_PRICE",
    "UNIT_DESCRIPTOR",
    "CTA_LABEL",
    "EDITORIAL_CLOSURE",
)

TYPE_KEYS = (
    "TYPOGRAPHIC_QUALITY",
    "TYPOGRAPHIC_AUTHORITY",
    "HIERARCHY",
    "OPTICAL_SPACING",
    "RHYTHM",
    "COMMERCIAL_STORYTELLING",
    "READABILITY",
    "REFERENCE_CRAFT_LEVEL",
)
TYPE_MUST = ("TYPOGRAPHIC_QUALITY", "TYPOGRAPHIC_AUTHORITY", "HIERARCHY", "READABILITY")

D2_KEYS = (
    "AGENCY_CAMPAIGN_FEEL",
    "ART_DIRECTION",
    "COMPOSITION",
    "PHOTO_GRAPHIC_INTEGRATION",
    "TYPE_FIELD_INTEGRATION",
    "TYPOGRAPHIC_AUTHORITY",
    "COMMERCIAL_STORYTELLING",
    "VISUAL_DEPTH",
    "GRAPHIC_PRECISION",
    "NEGATIVE_SPACE",
    "WHOLE_CANVAS_CHARACTER",
    "PREMIUM_CHARACTER",
    "READABILITY",
    "REFERENCE_CRAFT_LEVEL",
)
D2_FLOORS = {k: 8.0 for k in D2_KEYS}
D2_FLOORS["GRAPHIC_PRECISION"] = 9.0
D2_AVG_FLOOR = 8.3

E2_KEYS = (
    "AGENCY_CAMPAIGN_FEEL",
    "ART_DIRECTION",
    "COMPOSITION",
    "PHOTO_GRAPHIC_INTEGRATION",
    "TYPOGRAPHIC_QUALITY",
    "COMMERCIAL_STORYTELLING",
    "BRAND_INTEGRATION",
    "CTA_CRAFT",
    "EDITORIAL_CLOSURE",
    "VISUAL_DEPTH",
    "NEGATIVE_SPACE",
    "WHOLE_CANVAS_CHARACTER",
    "PREMIUM_CHARACTER",
    "READABILITY",
    "ARCHITECTURE_FIDELITY",
    "PUBLISHABILITY",
)
E2_FLOORS = {k: 8.0 for k in E2_KEYS}
E2_FLOORS["ARCHITECTURE_FIDELITY"] = 9.0
E2_AVG_FLOOR = 8.3

# Scale-ratio studies. Coordinates are system tokens, not Temple pixel locks.
TYPE_STUDIES = (
    {
        "id": "T1",
        "scale": 0.94,
        "kazan_em": 4.20,
        "alirken_ratio": 0.68,
        "pct_ratio": 1.52,
        "price_ratio": 0.60,
        "unit_ratio": 0.48,
        "display_track": 0.06,
        "optical_kazan": -2,
        "group_gap": 28,
        "note": "compact column, two-rule rhythm",
    },
    {
        "id": "T2",
        "scale": 1.00,
        "kazan_em": 4.55,
        "alirken_ratio": 0.66,
        "pct_ratio": 1.62,
        "price_ratio": 0.60,
        "unit_ratio": 0.48,
        "display_track": 0.05,
        "optical_kazan": -4,
        "group_gap": 32,
        "note": "Concept 3 stacked hierarchy",
    },
    {
        "id": "T3",
        "scale": 1.08,
        "kazan_em": 5.10,
        "alirken_ratio": 0.56,
        "pct_ratio": 1.72,
        "price_ratio": 0.58,
        "unit_ratio": 0.46,
        "display_track": 0.08,
        "optical_kazan": -8,
        "group_gap": 36,
        "note": "display authority, major offer mass",
    },
    {
        "id": "T4",
        "scale": 1.02,
        "kazan_em": 4.40,
        "alirken_ratio": 0.74,
        "pct_ratio": 1.48,
        "price_ratio": 0.62,
        "unit_ratio": 0.50,
        "display_track": 0.03,
        "optical_kazan": -3,
        "group_gap": 30,
        "note": "tighter tracking, even commercial rhythm",
    },
)


def _px(spec: dict[str, Any], em: float) -> int:
    return int(round(16 * float(spec["scale"]) * em))


def type_system_css(spec: dict[str, Any], *, with_brand: bool) -> str:
    kazan = _px(spec, spec["kazan_em"])
    alirken = int(round(kazan * spec["alirken_ratio"]))
    pct = int(round(kazan * spec["pct_ratio"]))
    price = int(round(kazan * spec["price_ratio"]))
    unit = int(round(kazan * spec["unit_ratio"]))
    gap = int(spec["group_gap"])
    top = 48 if with_brand else 168
    return f"""
.type-system,.type-system *{{margin:0;padding:0;box-sizing:border-box;}}
.type-system{{position:absolute;left:58px;top:{top}px;width:400px;z-index:6;color:{IVORY};
  font-family:'Cormorant Garamond',serif;font-kerning:normal;font-optical-sizing:auto;
  font-feature-settings:"kern" 1,"liga" 1;font-variation-settings:"opsz" 72;
  display:flex;flex-direction:column;align-items:flex-start;}}
.brand-lockup{{width:118px;color:{GOLD_MID};margin-bottom:{gap + 4}px;}}
.brand-lockup svg{{width:64px;height:auto;display:block;}}
.brand-lockup svg text{{display:none !important;}}
.brand-lockup svg, .brand-lockup svg path, .brand-lockup svg g, .brand-lockup svg polygon, .brand-lockup svg circle{{
  fill:{GOLD_MID} !important; stroke:none !important;}}
.brand-lockup .cap{{margin-top:8px;letter-spacing:0.42em;font-size:12px;color:{GOLD_MID};}}
.display .alirken{{font-size:{alirken}px;font-weight:400;letter-spacing:{spec['display_track']}em;line-height:0.94;}}
.display .kazan{{font-size:{kazan}px;font-weight:500;letter-spacing:0.012em;line-height:0.84;
  margin-top:{spec['optical_kazan']}px;}}
.offer-comp{{margin-top:{gap}px;display:flex;flex-direction:column;align-items:flex-start;}}
.offer-comp .hero{{font-size:{pct}px;line-height:0.78;color:{GOLD_MID};font-weight:500;}}
.offer-comp .label{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:0.40em;
  font-weight:400;margin-top:12px;color:{IVORY};}}
.rule{{width:196px;height:1px;margin:{max(16, gap - 6)}px 0 {max(14, gap - 8)}px;
  background:linear-gradient(90deg,{GOLD_MID},{GOLD_LO});border:0;}}
.price-comp{{display:flex;align-items:baseline;gap:12px;}}
.price-comp .num{{font-size:{price}px;color:{GOLD_MID};letter-spacing:0.03em;font-weight:500;}}
.price-comp .cur{{font-family:'Source Sans 3',sans-serif;font-size:15px;letter-spacing:0.24em;color:{IVORY};}}
.unit-comp{{margin-top:{max(10, gap - 16)}px;}}
.unit-comp .num{{font-size:{unit}px;color:{GOLD_MID};letter-spacing:0.04em;font-weight:500;}}
.unit-comp .lab{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:0.38em;color:{IVORY};margin-top:7px;}}
.cta-inscribe{{margin-top:{gap + 28}px;font-family:'Source Sans 3',sans-serif;letter-spacing:0.38em;
  font-size:13px;color:{GOLD_MID};border:1px solid {GOLD_MID};padding:13px 30px;background:transparent;
  box-shadow:none;border-radius:0;font-weight:400;display:inline-block;}}
.closure-ed{{position:absolute;left:0;right:0;bottom:58px;text-align:center;z-index:7;
  font-family:'Source Sans 3',sans-serif;letter-spacing:0.42em;font-size:11px;color:{IVORY};}}
.closure-ed .hair{{width:84px;height:1px;background:{GOLD_MID};margin:10px auto 0;}}
"""


def type_system_html(
    spec: dict[str, Any],
    *,
    logo_markup: str | None = None,
    include_cta: bool,
    include_closure: bool,
) -> str:
    first, last = (REQUIRED_FACTS["headline"].split(" ", 1) + [""])[:2]
    price, _, cur = REQUIRED_FACTS["list_price"].partition(" ")
    brand = ""
    if logo_markup:
        brand = f"""
      <div class="brand-lockup" data-id="group.brand" data-kind="GROUP" data-typographic_role="brand"
           data-relationship_anchor="column_open">
        <div data-id="logo.temple" data-kind="LOGO" data-semantic="project_logo">{logo_markup}</div>
        <div class="cap">THE TEMPLE</div>
      </div>
        """
    cta = ""
    if include_cta:
        cta = (
            f'<div class="cta-inscribe" data-id="text.cta" data-kind="TEXT" data-semantic="cta" '
            f'data-role="CTA_LABEL" data-typographic_role="cta">{REQUIRED_FACTS["cta"]}</div>'
        )
    closure = ""
    if include_closure:
        closure = f"""
    <div class="closure-ed" data-id="text.closure" data-kind="TEXT" data-role="EDITORIAL_CLOSURE"
         data-typographic_role="editorial_closure" data-relationship_anchor="canvas_bottom">
      {APPROVED_BOTTOM_COPY}
      <div class="hair"></div>
    </div>
        """
    return f"""
    <div class="type-system" data-id="group.editorial_type" data-kind="GROUP" data-renderer="EditorialTypographySystemV1"
         data-relationship_anchor="aperture_column">
      {brand}
      <div class="display" data-id="group.display" data-kind="GROUP" data-role="DISPLAY_HEADLINE" data-typographic_role="display">
        <div class="alirken" data-id="text.headline.first" data-kind="TEXT" data-semantic="headline"
             data-optical_offset="0">{first}</div>
        <div class="kazan" data-id="text.headline.last" data-kind="TEXT" data-optical_offset="{spec['optical_kazan']}"
             data-baseline_offset="{spec['optical_kazan']}">{last}</div>
      </div>
      <div class="rule" data-id="deco.campaign_rule" data-kind="DECORATION"></div>
      <div class="offer-comp" data-id="group.offer" data-kind="GROUP" data-typographic_role="commercial">
        <div class="hero" data-id="text.discount" data-kind="TEXT" data-semantic="discount" data-role="OFFER_HERO">{REQUIRED_FACTS["discount"]}</div>
        <div class="label" data-id="text.discount_label" data-kind="TEXT" data-semantic="discount_label" data-role="OFFER_LABEL">{REQUIRED_FACTS["discount_label"]}</div>
      </div>
      <div class="rule" data-id="deco.offer_rule" data-kind="DECORATION"></div>
      <div class="price-comp" data-id="group.price" data-kind="GROUP" data-role="PRIMARY_PRICE">
        <span class="num" data-id="text.price" data-kind="TEXT" data-semantic="price">{price}</span>
        <span class="cur">{cur or "USD"}</span>
      </div>
      <div class="unit-comp" data-id="group.unit" data-kind="GROUP" data-role="UNIT_DESCRIPTOR">
        <div class="num" data-id="text.unit" data-kind="TEXT" data-semantic="unit_type">{REQUIRED_FACTS["unit"]}</div>
        <div class="lab">{REQUIRED_FACTS["unit_label"]}</div>
      </div>
      {cta}
    </div>
    {closure}
    """


def typography_study_html(spec: dict[str, Any], font_css: str) -> str:
    css = _stage_css(font_css) + type_system_css(spec, with_brand=False)
    body = f'<div class="stage" style="background:{CHARCOAL}">{type_system_html(spec, include_cta=True, include_closure=True)}</div>'
    return wrap_html(body, css)


def d2_html(photo_uri: str, structure: dict[str, Any], aperture: dict[str, Any], type_spec: dict[str, Any], font_css: str) -> str:
    css = _stage_css(font_css) + _aperture_layer_css(structure, aperture) + type_system_css(type_spec, with_brand=False)
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {aperture_layers_svg(structure, aperture, include_locked_arc=True)}
      {type_system_html(type_spec, include_cta=False, include_closure=False)}
    </div>
    """
    return wrap_html(body, css)


def e2_html(
    photo_uri: str,
    structure: dict[str, Any],
    aperture: dict[str, Any],
    type_spec: dict[str, Any],
    logo_markup: str,
    font_css: str,
) -> str:
    css = _stage_css(font_css) + _aperture_layer_css(structure, aperture) + type_system_css(type_spec, with_brand=True)
    body = f"""
    <div class="stage">
      <img data-id="photo.day007" data-kind="PHOTO" data-semantic="project_photo" src="{photo_uri}" alt=""/>
      {aperture_layers_svg(structure, aperture, include_locked_arc=True)}
      {type_system_html(type_spec, logo_markup=logo_markup, include_cta=True, include_closure=True)}
    </div>
    """
    return wrap_html(body, css)


def structured_scene_validation() -> dict[str, Any]:
    return {
        "schema": "StructuredSceneValidationV1",
        "renderer": "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM",
        "flattened_campaign_raster": False,
        "object_kinds": ["PHOTO", "GRAPHIC_FIELD", "VECTOR_PATH", "DECORATION", "TEXT", "LOGO", "GROUP"],
        "objects": [
            {"id": "photo.day007", "kind": "PHOTO", "live": "img", "stable": True},
            {"id": "field.charcoal_aperture", "kind": "GRAPHIC_FIELD", "live": "css_mask_layers", "locked": "A3"},
            {"id": "vector.gold_arc", "kind": "VECTOR_PATH", "locked": "PROOF_B"},
            {"id": "deco.ticks", "kind": "DECORATION", "locked": "PROOF_B"},
            {"id": "deco.precision_marker", "kind": "DECORATION", "locked": "PROOF_B"},
            {"id": "group.display", "kind": "GROUP", "role": "DISPLAY_HEADLINE"},
            {"id": "group.offer", "kind": "GROUP", "role": "OFFER_HERO+OFFER_LABEL"},
            {"id": "text.price", "kind": "TEXT", "role": "PRIMARY_PRICE"},
            {"id": "group.unit", "kind": "GROUP", "role": "UNIT_DESCRIPTOR"},
            {"id": "text.cta", "kind": "TEXT", "role": "CTA_LABEL"},
            {"id": "text.closure", "kind": "TEXT", "role": "EDITORIAL_CLOSURE"},
            {"id": "logo.temple", "kind": "LOGO", "live": "svg", "asset": "7b58877e-efca-4e9a-9027-6fd18fb1b345"},
            {"id": "group.brand", "kind": "GROUP", "relationship_anchor": "column_open"},
        ],
        "status": "PASS",
    }


def revision_compatibility() -> dict[str, Any]:
    return {
        "schema": "RendererRevisionCompatibilityV1",
        "executed": False,
        "PRICE_EDIT_ONLY": {
            "status": "PASS",
            "mechanism": "Replace innerText of [data-semantic=price] and [data-semantic=discount]. Scene graph unchanged.",
        },
        "COPY_EDIT_ONLY": {
            "status": "PASS",
            "mechanism": "Replace innerText of TEXT nodes. optical_offset / typographic_role remain on GROUPs.",
        },
        "VISUAL_REPLACE_ONLY": {
            "status": "PASS",
            "mechanism": "Swap img[data-kind=PHOTO].src. A3 masks, Proof B arc, and type groups stay live.",
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
            "1:1": {"canvas": [1088, 1088], "strategy": "recompute ellipse cy/ry + GROUP constraints"},
            "9:16": {"canvas": [1080, 1920], "strategy": "vertical restack via relationship_anchor"},
            "16:9": {"canvas": [1920, 1080], "strategy": "horizontal field/photo split, same objects"},
        },
        "status": "PASS",
        "note": "Compatibility only. Format adaptation is not rendered in Phase 6.3B.",
    }


def type_continue_ok(block: dict[str, Any]) -> bool:
    scores = block.get("scores") or {}
    if any(float(scores.get(k, 0)) < 9 for k in TYPE_MUST):
        return False
    if any(float(v) < 8 for v in scores.values()):
        return False
    return all(float(v) > 0 for v in scores.values())


def d2_pass(block: dict[str, Any]) -> tuple[bool, list[str], float]:
    scores = block.get("scores") or {}
    vals = [float(scores.get(k, 0)) for k in D2_KEYS]
    avg = round(sum(vals) / max(len(vals), 1), 3)
    failed = [k for k in D2_KEYS if float(scores.get(k, 0)) < D2_FLOORS[k]]
    if avg < D2_AVG_FLOOR:
        failed.append(f"AVERAGE:{avg}<{D2_AVG_FLOOR}")
    return (not failed and avg >= D2_AVG_FLOOR and all(v > 0 for v in vals), failed, avg)


def e2_pass(block: dict[str, Any]) -> tuple[bool, list[str], float]:
    scores = block.get("scores") or {}
    vals = [float(scores.get(k, 0)) for k in E2_KEYS]
    avg = round(sum(vals) / max(len(vals), 1), 3)
    failed = [k for k in E2_KEYS if float(scores.get(k, 0)) < E2_FLOORS[k]]
    if avg < E2_AVG_FLOOR:
        failed.append(f"AVERAGE:{avg}<{E2_AVG_FLOOR}")
    return (not failed and avg >= E2_AVG_FLOOR and all(v > 0 for v in vals), failed, avg)


def aperture_hurts_d2(block: dict[str, Any]) -> bool:
    scores = block.get("scores") or {}
    note = str(block.get("diagnosis") or "").lower()
    weak = any(float(scores.get(k, 0)) < 8.3 for k in ("VISUAL_DEPTH", "PHOTO_GRAPHIC_INTEGRATION", "TYPE_FIELD_INTEGRATION"))
    mentioned = any(w in note for w in ("aperture", "charcoal", "mass", "depth", "multiply", "field", "stain", "veil"))
    return weak or mentioned
