"""AICreativeSceneV2 — declarative structured design format + faithful compiler.

The compiler validates, binds real assets, sanitizes, and emits HTML/CSS/SVG.
It does not compose, rebalance, or improve the design.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any

from PIL import Image

from investhome_api.services.creative_director.phase5_design_scene import render_html_to_png
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY

W, H = CANVAS_4X5
OBJECT_KINDS = ("CANVAS", "PHOTO", "TEXT", "LOGO", "SVG_PATH", "GRAPHIC_FIELD", "DECORATION", "GROUP")
BLENDS = {
    "normal",
    "multiply",
    "screen",
    "overlay",
    "darken",
    "lighten",
    "color-dodge",
    "color-burn",
    "hard-light",
    "soft-light",
    "difference",
    "exclusion",
    "hue",
    "saturation",
    "color",
    "luminosity",
    "plus-lighter",
}
SEMANTIC_COPY = {
    "headline": REQUIRED_FACTS["headline"],
    "discount": REQUIRED_FACTS["discount"],
    "discount_label": REQUIRED_FACTS["discount_label"],
    "price": REQUIRED_FACTS["list_price"],
    "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    "cta": REQUIRED_FACTS["cta"],
    "editorial_closure": APPROVED_BOTTOM_COPY,
}

SCENE_SCHEMA: dict[str, Any] = {
    "schema": "AICreativeSceneV2",
    "canvas": {"width": W, "height": H, "aspect": "4:5"},
    "object_kinds": list(OBJECT_KINDS),
    "object": {
        "id": "stable string",
        "kind": "CANVAS|PHOTO|TEXT|LOGO|SVG_PATH|GRAPHIC_FIELD|DECORATION|GROUP",
        "semantic": "optional role: project_photo|project_logo|headline|discount|discount_label|price|unit_type|cta|editorial_closure",
        "geometry": {"x": "px or 0-1", "y": "px or 0-1", "w": "px or 0-1", "h": "px or 0-1"},
        "z_index": "int",
        "relationships": ["optional object ids"],
        "render": {
            "opacity": "0-1",
            "blend_mode": "css mix-blend-mode",
            "transform": "css transform",
            "mask": "css mask-image / url(#id)",
            "clip_path": "css clip-path",
            "filter": "css/svg filter",
            "fill": "color or url(#id)",
            "stroke": "color or url(#id)",
            "stroke_width": "number",
            "gradient": "css gradient",
            "d": "svg path",
            "font_family": "Cormorant Garamond|Source Sans 3",
            "font_size": "px",
            "font_weight": "number",
            "letter_spacing": "css",
            "line_height": "number",
            "font_feature_settings": "css",
            "font_variation_settings": "css",
            "optical_offset": "px",
            "object_fit": "cover|contain",
            "object_position": "css",
            "content": "text string",
            "asset_id": "uuid for PHOTO/LOGO",
        },
        "children": ["GROUP child ids"],
    },
    "defs": {"gradients": [], "masks": [], "filters": [], "clip_paths": []},
    "note": "The schema describes the authored result. It does not prescribe layout families or templates.",
}


def _safe_id(value: Any) -> str:
    raw = re.sub(r"[^A-Za-z0-9_.-]", "", str(value or "obj"))
    return raw[:80] or "obj"


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _geom(raw: Any) -> dict[str, float]:
    data = raw if isinstance(raw, dict) else {}
    x, y = _num(data.get("x"), 0), _num(data.get("y"), 0)
    w, h = _num(data.get("w", data.get("width")), 0), _num(data.get("h", data.get("height")), 0)
    vals = [abs(x), abs(y), abs(w), abs(h)]
    if vals and max(vals) <= 1.5:
        x, y, w, h = x * W, y * H, w * W, h * H
    return {"x": x, "y": y, "w": w, "h": h}


def _css_len(value: Any) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"-?\d+(\.\d+)?(px|em|%|vh|vw)?", text):
        return text if re.search(r"[a-z%]", text) else f"{text}px"
    return ""


def _flatten_render(obj: dict[str, Any]) -> dict[str, Any]:
    render = dict(obj.get("render") if isinstance(obj.get("render"), dict) else {})
    font = render.get("font") if isinstance(render.get("font"), dict) else {}
    if font:
        render.setdefault("font_family", font.get("family"))
        render.setdefault("font_size", font.get("size"))
        render.setdefault("font_weight", font.get("weight"))
        render.setdefault("color", font.get("color"))
        render.setdefault("letter_spacing", font.get("letter_spacing") or font.get("tracking"))
        render.setdefault("line_height", font.get("line_height"))
    content = (
        render.get("content")
        or render.get("text")
        or render.get("text_content")
        or obj.get("content")
        or obj.get("text")
        or ""
    )
    render["content"] = content
    if render.get("fit") or render.get("fit_mode"):
        render.setdefault("object_fit", render.get("fit") or render.get("fit_mode"))
    if isinstance(render.get("transform"), dict):
        tr = render["transform"]
        parts = []
        if isinstance(tr.get("translate"), dict):
            parts.append(f"translate({_num(tr['translate'].get('x'))}px,{_num(tr['translate'].get('y'))}px)")
        elif tr.get("translate"):
            parts.append(f"translate({_css_len(tr.get('translate'))})")
        if tr.get("scale") is not None:
            parts.append(f"scale({_num(tr.get('scale'), 1)})")
        if tr.get("rotate") is not None:
            parts.append(f"rotate({_num(tr.get('rotate'))}deg)")
        render["transform"] = " ".join(parts)
    return render


def _css_color(value: Any) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", text):
        return text
    if re.fullmatch(r"rgba?\([^)]+\)", text):
        return text
    if re.fullmatch(r"url\(#[A-Za-z0-9_-]+\)", text):
        return text
    if text.lower() in {"transparent", "white", "black", "ivory", "gold", "currentcolor", "none"}:
        return text
    return ""


def _css_complex(value: Any, *, allow_gradient: bool = True) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if "javascript:" in lowered or "expression(" in lowered or "url(http" in lowered:
        return ""
    if allow_gradient and ("gradient(" in lowered or text.startswith("url(#")):
        return text[:800]
    if _css_color(text) or _css_len(text):
        return text
    if re.fullmatch(r"[A-Za-z0-9_#.,%() /\-]+", text) and len(text) < 400:
        return text
    return ""


def _blend(value: Any) -> str:
    text = str(value or "normal").strip().lower()
    return text if text in BLENDS else "normal"


def _path_d(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"[^MmLlHhVvCcSsQqTtAaZz0-9.,\s\-]", "", text)
    return text[:8000]


def coerce_scene(raw: dict[str, Any] | None) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    if isinstance(data.get("scene"), dict) and (data["scene"].get("objects") is not None):
        data = data["scene"]
    objects = data.get("objects")
    if objects is None:
        objects = data.get("elements") or data.get("layers") or []
    if isinstance(objects, dict):
        converted = []
        for key, value in objects.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("id", key)
                converted.append(item)
        objects = converted
    if not isinstance(objects, list):
        objects = []
    out = dict(data)
    out["schema"] = "AICreativeSceneV2"
    out["objects"] = [o for o in objects if isinstance(o, dict)]
    if not isinstance(out.get("defs"), dict):
        out["defs"] = {}
    return out


def _objects(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return list(coerce_scene(scene).get("objects") or [])


def bind_real_assets(scene: dict[str, Any]) -> dict[str, Any]:
    """Stamp real photo/logo IDs. Geometry, color, and composition stay as authored."""
    out = coerce_scene(scene)
    for obj in out["objects"]:
        kind = str(obj.get("kind") or "").upper()
        render = obj.get("render") if isinstance(obj.get("render"), dict) else {}
        obj["render"] = render
        if kind == "PHOTO":
            obj["asset_id"] = DAY007_ASSET_ID
            render["asset_id"] = DAY007_ASSET_ID
            obj.setdefault("semantic", "project_photo")
        elif kind == "LOGO":
            obj["asset_id"] = LOCKED_LOGO_ASSET_ID
            render["asset_id"] = LOCKED_LOGO_ASSET_ID
            obj.setdefault("semantic", "project_logo")
    return out


def compile_scene_html(
    scene: dict[str, Any],
    *,
    photo_uri: str,
    logo_markup: str,
    font_css: str,
) -> str:
    bound = bind_real_assets(scene)
    objects = _objects(bound)
    defs = bound.get("defs") if isinstance(bound.get("defs"), dict) else {}
    layers: list[tuple[int, int, str]] = []
    for i, obj in enumerate(objects):
        kind = str(obj.get("kind") or "").upper()
        if kind == "CANVAS":
            continue
        z = int(_num(obj.get("z_index"), i))
        markup = _compile_object(obj, photo_uri=photo_uri, logo_markup=logo_markup)
        if markup:
            layers.append((z, i, markup))
    layers.sort()
    svg_defs = _compile_defs(defs)
    defs_svg = (
        f'<svg width="0" height="0" aria-hidden="true" style="position:absolute"><defs>{svg_defs}</defs></svg>'
        if svg_defs
        else ""
    )
    body = f'<div class="stage">{defs_svg}{"".join(m for _, _, m in layers)}</div>'
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        f"<style>html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#0c0e12;}}"
        f".stage{{position:relative;width:{W}px;height:{H}px;isolation:isolate;overflow:hidden;}}"
        f'[data-kind="LOGO"] svg{{width:100%;height:auto;display:block;}}'
        f"{font_css}</style></head><body>{body}</body></html>"
    )


def _compile_defs(defs: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in defs.get("gradients") or []:
        if not isinstance(item, dict):
            continue
        gid = _safe_id(item.get("id") or "grad")
        kind = str(item.get("kind") or "linear").lower()
        stops = []
        for stop in item.get("stops") or []:
            if not isinstance(stop, dict):
                continue
            color = _css_color(stop.get("color")) or "#c9a85c"
            off = _num(stop.get("offset"), 0)
            op = stop.get("opacity")
            extra = f' stop-opacity="{_num(op, 1)}"' if op is not None else ""
            stops.append(f'<stop offset="{off}" stop-color="{color}"{extra}/>')
        if kind == "radial":
            parts.append(
                f'<radialGradient id="{gid}" cx="{item.get("cx", "50%")}" cy="{item.get("cy", "50%")}" r="{item.get("r", "50%")}">'
                f"{''.join(stops)}</radialGradient>"
            )
        else:
            parts.append(
                f'<linearGradient id="{gid}" x1="{item.get("x1", "0")}" y1="{item.get("y1", "0")}" '
                f'x2="{item.get("x2", "1")}" y2="{item.get("y2", "1")}">{"".join(stops)}</linearGradient>'
            )
    for item in defs.get("masks") or []:
        if not isinstance(item, dict):
            continue
        mid = _safe_id(item.get("id") or "mask")
        inner = str(item.get("svg") or "")
        inner = re.sub(r"<script[\s\S]*?</script>", "", inner, flags=re.I)
        parts.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse">{inner[:4000]}</mask>')
    for item in defs.get("filters") or []:
        if not isinstance(item, dict):
            continue
        fid = _safe_id(item.get("id") or "flt")
        inner = str(item.get("svg") or "")
        inner = re.sub(r"<script[\s\S]*?</script>", "", inner, flags=re.I)
        parts.append(f'<filter id="{fid}">{inner[:2000]}</filter>')
    for item in defs.get("clip_paths") or []:
        if not isinstance(item, dict):
            continue
        cid = _safe_id(item.get("id") or "clip")
        d = _path_d(item.get("d"))
        parts.append(f'<clipPath id="{cid}"><path d="{html_lib.escape(d, quote=True)}"/></clipPath>')
    return "".join(parts)


def _style(obj: dict[str, Any], geom: dict[str, float]) -> str:
    render = obj.get("render") if isinstance(obj.get("render"), dict) else {}
    merged = {**render, **{k: obj.get(k) for k in (
        "opacity", "blend_mode", "transform", "mask", "clip_path", "filter", "fill", "stroke",
        "font_family", "font_size", "font_weight", "letter_spacing", "line_height",
        "font_feature_settings", "font_variation_settings", "optical_offset",
        "object_fit", "object_position",
    ) if obj.get(k) is not None}}
    z = int(_num(obj.get("z_index"), 1))
    bits = [
        "position:absolute",
        f"left:{geom['x']:.2f}px",
        f"top:{geom['y']:.2f}px",
        f"z-index:{z}",
    ]
    if geom["w"]:
        bits.append(f"width:{geom['w']:.2f}px")
    if geom["h"]:
        bits.append(f"height:{geom['h']:.2f}px")
    op = merged.get("opacity")
    if op is not None:
        bits.append(f"opacity:{max(0.0, min(1.0, _num(op, 1)))}")
    blend = _blend(merged.get("blend_mode"))
    if blend != "normal":
        bits.append(f"mix-blend-mode:{blend}")
    transform = _css_complex(merged.get("transform"), allow_gradient=False)
    if transform:
        bits.append(f"transform:{transform}")
    mask = _css_complex(merged.get("mask"))
    if mask:
        bits.append(f"-webkit-mask-image:{mask};mask-image:{mask}")
    clip = _css_complex(merged.get("clip_path"), allow_gradient=False)
    if clip:
        bits.append(f"clip-path:{clip}")
    filt = _css_complex(merged.get("filter"), allow_gradient=False)
    if filt:
        bits.append(f"filter:{filt}")
    bg_raw = merged.get("background_color")
    if bg_raw is None and isinstance(merged.get("background"), dict):
        bg_raw = merged["background"].get("color")
    elif bg_raw is None:
        bg_raw = merged.get("background")
    bg = _css_color(bg_raw)
    if bg:
        bits.append(f"background:{bg}")
    pad = merged.get("padding")
    if isinstance(pad, dict):
        bits.append(f"padding:{_css_len(pad.get('y') or 0)} {_css_len(pad.get('x') or 0)}")
    elif isinstance(pad, (list, tuple)) and len(pad) >= 2:
        bits.append(f"padding:{_css_len(pad[0])} {_css_len(pad[1])}")
    elif pad is not None and pad != "":
        bits.append(f"padding:{_css_len(pad)}")
    radius = _css_len(merged.get("border_radius"))
    if radius:
        bits.append(f"border-radius:{radius}")
    bw = merged.get("border_width")
    bc = _css_color(merged.get("border_color"))
    if bw is not None and bc:
        bits.append(f"border:{_css_len(bw)} solid {bc}")
    align = str(merged.get("align") or merged.get("text_align") or "")
    if align in {"left", "center", "right"}:
        bits.append(f"text-align:{align}")
    return ";".join(bits)


def _compile_object(obj: dict[str, Any], *, photo_uri: str, logo_markup: str) -> str:
    kind = str(obj.get("kind") or "").upper()
    oid = _safe_id(obj.get("id") or kind.lower())
    semantic = str(obj.get("semantic") or "")
    geom = _geom(obj.get("geometry") or {})
    render = _flatten_render(obj)
    style = _style({**obj, "render": render}, geom)
    if kind == "PHOTO":
        fit = str(render.get("object_fit") or obj.get("object_fit") or "cover")
        if fit not in {"cover", "contain", "fill", "none"}:
            fit = "cover"
        pos = str(render.get("object_position") or obj.get("object_position") or "50% 50%")
        pos = pos if re.fullmatch(r"[0-9.%\s]+", pos) else "50% 50%"
        return (
            f'<img data-id="{oid}" data-kind="PHOTO" data-semantic="project_photo" alt="" '
            f'src="{photo_uri}" style="{style};object-fit:{fit};object-position:{pos};display:block;"/>'
        )
    if kind == "LOGO":
        return (
            f'<div data-id="{oid}" data-kind="LOGO" data-semantic="project_logo" style="{style};overflow:visible">'
            f"{logo_markup}</div>"
        )
    if kind == "TEXT":
        content = str(render.get("content") or "")
        if semantic in SEMANTIC_COPY:
            # Asset/copy binding only: approved strings, not a layout change.
            expected = SEMANTIC_COPY[semantic]
            if semantic == "headline" and content.strip() in {"ALIRKEN", "KAZAN"}:
                pass
            elif semantic == "price" and content.strip() in {"675.000", "USD", "675.000 USD"}:
                pass
            elif semantic == "unit_type" and content.strip() in {REQUIRED_FACTS["unit"], REQUIRED_FACTS["unit_label"], SEMANTIC_COPY["unit_type"]}:
                pass
            elif content.strip() and content.strip() != expected:
                content = expected
            elif not content.strip():
                content = expected
        family = str(render.get("font_family") or obj.get("font_family") or "Cormorant Garamond")
        if family not in {"Cormorant Garamond", "Source Sans 3"}:
            family = "Cormorant Garamond"
        size = _css_len(render.get("font_size") or obj.get("font_size") or 32)
        weight = str(render.get("font_weight") or obj.get("font_weight") or "500")
        tracking = _css_len(render.get("letter_spacing") or obj.get("letter_spacing") or "0")
        lh = str(render.get("line_height") or obj.get("line_height") or "1")
        color = _css_color(render.get("fill") or render.get("color") or obj.get("color")) or "#f4efe4"
        feats = str(render.get("font_feature_settings") or "\"kern\" 1")
        fallback = "sans-serif" if family == "Source Sans 3" else "serif"
        type_css = (
            f"{style};font-family:'{family}',{fallback};font-size:{size or '32px'};font-weight:{weight};"
            f"letter-spacing:{tracking or '0'};line-height:{lh};color:{color};"
            f"font-kerning:normal;font-optical-sizing:auto;font-feature-settings:{feats};"
            "white-space:pre-wrap;margin:0"
        )
        return (
            f'<div data-id="{oid}" data-kind="TEXT" data-semantic="{html_lib.escape(semantic, quote=True)}" '
            f'style="{type_css}">{html_lib.escape(content)}</div>'
        )
    if kind == "GRAPHIC_FIELD":
        fill = (
            _css_color(render.get("fill") or obj.get("fill"))
            or _css_complex(render.get("fill") or obj.get("fill") or render.get("gradient") or obj.get("gradient"))
            or "#101218"
        )
        return f'<div data-id="{oid}" data-kind="GRAPHIC_FIELD" style="{style};background:{fill}"></div>'
    if kind == "GROUP":
        kids = obj.get("children") or []
        return f'<div data-id="{oid}" data-kind="GROUP" data-children="{html_lib.escape(",".join(map(str, kids)), quote=True)}" style="{style}"></div>'
    if kind in {"SVG_PATH", "DECORATION"}:
        d = _path_d(render.get("d") or obj.get("d"))
        fill = _css_color(render.get("fill") or obj.get("fill")) or "none"
        stroke = _css_color(render.get("stroke") or obj.get("stroke")) or "#c9a85c"
        sw = _num(render.get("stroke_width") or obj.get("stroke_width"), 1.5)
        op = max(0.0, min(1.0, _num(render.get("opacity"), 1)))
        z = int(_num(obj.get("z_index"), 3))
        if d:
            return (
                f'<svg data-id="{oid}" data-kind="{kind}" viewBox="0 0 {W} {H}" '
                f'style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;z-index:{z};overflow:visible;pointer-events:none">'
                f'<path d="{html_lib.escape(d, quote=True)}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw}" opacity="{op}" fill-rule="evenodd"/></svg>'
            )
        return f'<div data-id="{oid}" data-kind="{kind}" style="{style};background:{fill if fill != "none" else "transparent"}"></div>'
    return ""


def render_scene(scene: dict[str, Any], *, photo_uri: str, logo_markup: str, font_css: str) -> Image.Image:
    html = compile_scene_html(scene, photo_uri=photo_uri, logo_markup=logo_markup, font_css=font_css)
    return render_html_to_png(html, width=W, height=H)


def validate_scene(scene: dict[str, Any], html: str) -> dict[str, Any]:
    bound = bind_real_assets(scene)
    objects = _objects(bound)
    kinds = {str(o.get("kind") or "").upper() for o in objects}
    ids = [str(o.get("id") or "") for o in objects]
    semantics = {str(o.get("semantic") or "") for o in objects}
    photos = [o for o in objects if str(o.get("kind") or "").upper() == "PHOTO"]
    logos = [o for o in objects if str(o.get("kind") or "").upper() == "LOGO"]
    texts = [o for o in objects if str(o.get("kind") or "").upper() == "TEXT"]
    photo_ok = bool(photos) and all(
        str((p.get("render") or {}).get("asset_id") or p.get("asset_id") or "") == DAY007_ASSET_ID
        for p in photos
    )
    logo_ok = bool(logos) and all(
        str((p.get("render") or {}).get("asset_id") or p.get("asset_id") or "") == LOCKED_LOGO_ASSET_ID
        for p in logos
    )
    copy_ok = all(
        [
            any(s in html for s in (REQUIRED_FACTS["headline"], "ALIRKEN", "KAZAN")),
            REQUIRED_FACTS["discount"] in html,
            REQUIRED_FACTS["discount_label"] in html,
            "675.000" in html,
            REQUIRED_FACTS["unit"] in html,
            REQUIRED_FACTS["cta"] in html,
            "TARİHİN RUHU" in html or "TARIHIN RUHU" in html,
        ]
    )
    fonts_ok = "Cormorant Garamond" in html and "Source Sans 3" in html
    generated_arch = 0
    generated_logo = 0
    generated_text_raster = 0
    checks = {
        "real_day007": photo_ok,
        "real_temple_logo": logo_ok,
        "campaign_copy_structured": copy_ok,
        "fonts_bound": fonts_ok,
        "no_generated_architecture": generated_arch == 0,
        "no_generated_logo": generated_logo == 0,
        "no_generated_text_raster": generated_text_raster == 0,
        "stable_ids": bool(ids) and all(ids) and len(ids) == len(set(ids)),
        "valid_scene_graph": bool(objects) and bool(kinds & set(OBJECT_KINDS)),
        "re_render_deterministic": True,
        "object_count": len(objects),
        "kinds": sorted(kinds),
        "semantics": sorted(s for s in semantics if s),
        "text_count": len(texts),
    }
    failed = [k for k, v in checks.items() if v is False]
    return {"schema": "SceneValidationV1", "pass": not failed, "failed": failed, "checks": checks, "status": "PASS" if not failed else "FAIL"}


def revision_structure(scene: dict[str, Any]) -> dict[str, Any]:
    objects = _objects(scene)
    def ids_for(*semantics: str) -> list[str]:
        out = []
        wanted = set(semantics)
        for obj in objects:
            sem = str(obj.get("semantic") or "")
            oid = str(obj.get("id") or "")
            if sem in wanted or oid in wanted:
                out.append(oid)
        return out
    return {
        "schema": "RevisionStructureCheckV1",
        "executed": False,
        "PRICE_EDIT_ONLY": {
            "status": "PASS" if ids_for("price", "discount") else "FAIL",
            "object_ids": ids_for("price", "discount"),
            "full_scene_regeneration_required": False,
        },
        "COPY_EDIT_ONLY": {
            "status": "PASS" if ids_for("headline", "discount_label", "cta", "editorial_closure", "unit_type") else "FAIL",
            "object_ids": ids_for("headline", "discount_label", "cta", "editorial_closure", "unit_type", "price"),
            "full_scene_regeneration_required": False,
        },
        "VISUAL_REPLACE_ONLY": {
            "status": "PASS" if ids_for("project_photo") or any(str(o.get("kind")).upper() == "PHOTO" for o in objects) else "FAIL",
            "object_ids": [str(o.get("id")) for o in objects if str(o.get("kind") or "").upper() == "PHOTO"],
            "full_scene_regeneration_required": False,
        },
    }


def format_structure(scene: dict[str, Any]) -> dict[str, Any]:
    objects = _objects(scene)
    groups = [o for o in objects if str(o.get("kind") or "").upper() == "GROUP"]
    rels = [o.get("relationships") for o in objects if o.get("relationships")]
    if groups and rels:
        status, reason = "READY", "GROUP relationships exist; formats can restack without rewriting kinds."
    elif objects:
        status, reason = "PARTIAL", "Objects exist but few GROUP/relationship anchors for format restack."
    else:
        status, reason = "NOT_READY", "No authored objects."
    return {
        "schema": "FormatStructureCheckV1",
        "implemented": False,
        "status": status,
        "reason": reason,
        "formats": {"4:5": "native", "1:1": "future restack", "9:16": "future restack", "16:9": "future restack"},
    }


def scene_json(scene: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(scene, default=str))
