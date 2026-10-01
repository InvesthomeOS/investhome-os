"""Phase 8.2 — one Temple Premium Master from human-selected ORNEK_00001.

Full-canvas photograph. Type in natural negative space. Not a new compositor.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY
from investhome_api.services.creative_director.temple_exterior_catalog import load_temple_exteriors

W, H = CANVAS_4X5
NAVY = "#1A2330"
SOURCE_ID = "3a3c4832-a8c1-5a43-a518-d895ee78fbe1"
SOURCE_FILENAME = "ORNEK_00001.jpg"
LOCATION_LINE = "WASHINGTON D.C."


def _headline_field_score(image: Image.Image) -> float:
    """Pale, quiet upper-left field — the ORNEK_00001 type territory."""
    w, h = image.size
    field = image.crop((0, 0, int(w * 0.48), int(h * 0.34))).convert("RGB")
    gray = field.convert("L")
    mean = ImageStat.Stat(gray).mean[0] / 255.0
    edge = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0] / 255.0
    rgb = field.resize((48, 34), Image.Resampling.BOX)
    px = rgb.load()
    sat_acc = 0.0
    n = 0
    for y in range(34):
        for x in range(48):
            r, g, b = px[x, y]
            sat_acc += (max(r, g, b) - min(r, g, b)) / 255.0
            n += 1
    sat = sat_acc / max(n, 1)
    return round(mean * 1.6 - edge * 2.4 - sat * 0.6, 4)


def score_photo_for_ornek00001(item: dict[str, Any]) -> float:
    occ = item.get("occupancy") or {}
    cov = occ.get("coverage") or {}
    sky = float(item.get("sky_area") or 0)
    left = float(cov.get("sky_left") or 0)
    right = float(cov.get("sky_right") or 0)
    hard = float(item.get("hard_coverage") or 0)
    cx = float(item.get("architecture_centroid_x") or 0.5)
    pocket = max(left, right)
    left_bonus = 0.22 if left >= right and cx >= 0.52 else 0.0
    dense_penalty = max(0.0, hard - 0.52) * 1.1
    src = item.get("source") or item.get("preview")
    headline = 0.0
    if src is not None:
        crop, _ = cover_fit_canvas(src.convert("RGB"), CANVAS_4X5, centering=(0.46, 0.28))
        headline = _headline_field_score(crop)
    return round(sky * 1.1 + pocket * 2.0 + left_bonus + headline * 2.4 - dense_penalty, 4)


def select_temple_photo(catalog: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ranked = sorted(catalog, key=score_photo_for_ornek00001, reverse=True)
    winner = dict(ranked[0])
    winner["selection_reason"] = (
        f"{winner.get('filename')} has the strongest upper-left quiet sky for ORNEK_00001's "
        "full-canvas type-in-sky structure: pale headline territory, architecture remaining "
        "the visual world, spire as vertical anchor rather than an aerial roof-stack. "
        f"sky={float(winner.get('sky_area') or 0):.3f}, "
        f"centroid_x={float(winner.get('architecture_centroid_x') or 0):.3f}."
    )
    winner["selection_score"] = score_photo_for_ornek00001(winner)
    return winner, ranked


def crop_selected_photo(item: dict[str, Any]) -> tuple[Image.Image, dict[str, Any], dict[str, Any]]:
    cx = float(item.get("architecture_centroid_x") or 0.58)
    centering = (0.46 if cx >= 0.52 else 0.54, 0.28)
    crop, transform = cover_fit_canvas(item["source"], CANVAS_4X5, centering=centering)
    graded = apply_photographic_grade(crop, {"warmth": 0.06, "contrast": 1.05, "brightness": 1.01, "vignette": 0.06})
    occupancy = build_photo_occupancy_map(graded)
    transform = dict(transform)
    transform["centering"] = list(centering)
    return graded, occupancy, transform


def _box(x: float, y: float, w: float, h: float) -> dict[str, float]:
    x = max(0.03, min(0.70, float(x)))
    y = max(0.02, min(0.86, float(y)))
    w = max(0.16, min(0.70, float(w)))
    h = max(0.026, min(0.28, float(h)))
    if x + w > 0.96:
        w = 0.96 - x
    if y + h > 0.94:
        h = 0.94 - y
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _stack_column(*, x: float, y0: float, y1: float, w: float) -> dict[str, dict[str, float]]:
    top = max(0.03, y0)
    bottom = min(0.48, max(top + 0.30, y1))
    span = bottom - top
    parts = (
        ("BRAND_TERRITORY", 0.12, min(0.32, w)),
        ("LOCATION_TERRITORY", 0.07, min(0.52, w)),
        ("HEADLINE_TERRITORY", 0.34, min(0.62, w + 0.10)),
        ("OFFER_TERRITORY", 0.14, min(0.50, w)),
        ("SECONDARY_COMMERCIAL_TERRITORY", 0.12, min(0.52, w)),
        ("CTA_TERRITORY", 0.10, min(0.40, w)),
        ("EDITORIAL_CLOSURE_TERRITORY", 0.11, min(0.56, w + 0.04)),
    )
    out: dict[str, dict[str, float]] = {}
    y = top
    for name, frac, width in parts:
        h = span * frac
        out[name] = _box(x, y, width, h)
        y += h
    return out


def composition_plan_v1(occupancy: dict[str, Any]) -> dict[str, Any]:
    regions = occupancy.get("regions") or {}
    pockets = occupancy.get("pockets") or {}
    cov = occupancy.get("coverage") or {}
    left = pockets.get("left") or regions.get("sky_left")
    right = pockets.get("right") or regions.get("sky_right")
    left_area = float((left or {}).get("area") or cov.get("sky_left") or 0)
    right_area = float((right or {}).get("area") or cov.get("sky_right") or 0)
    origin = "left"
    field = left if isinstance(left, dict) else None
    if right_area > left_area + 0.01 and isinstance(right, dict):
        origin = "right"
        field = right
    if not isinstance(field, dict):
        field = {"x": 0.07 if origin == "left" else 0.42, "y": 0.04, "w": 0.50, "h": 0.34}
    x = float(field.get("x") or 0.07)
    w = max(0.42, min(0.56, float(field.get("w") or 0.5)))
    y0 = float(field.get("y") or 0.03)
    field_h = min(0.38, float(field.get("h") or 0.34))
    if origin == "left":
        x = min(x, 0.10)
    else:
        x = max(x, 0.40)
    stacked = _stack_column(x=x, y0=y0, y1=y0 + field_h + 0.04, w=w)
    hard = regions.get("hard_protected") or {"x": 0.28, "y": 0.22, "w": 0.55, "h": 0.70}
    sky = regions.get("preferred_negative_space") or {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.38}
    headline = stacked["HEADLINE_TERRITORY"]
    editorial = stacked["EDITORIAL_CLOSURE_TERRITORY"]
    plan = {
        "schema": "CompositionPlanV1",
        "source": SOURCE_FILENAME,
        "origin": origin,
        "PHOTO_FOCAL_AREA": hard,
        "NATURAL_NEGATIVE_SPACE": sky,
        "HEADLINE_TERRITORY": headline,
        "LOCATION_TERRITORY": stacked["LOCATION_TERRITORY"],
        "OFFER_TERRITORY": stacked["OFFER_TERRITORY"],
        "SECONDARY_COMMERCIAL_TERRITORY": stacked["SECONDARY_COMMERCIAL_TERRITORY"],
        "BRAND_TERRITORY": stacked["BRAND_TERRITORY"],
        "CTA_TERRITORY": stacked["CTA_TERRITORY"],
        "EDITORIAL_CLOSURE_TERRITORY": editorial,
        "alignment": origin,
        "sky_column": {"x": x, "y": y0, "w": w, "h": field_h},
        "note": "Territories derived from photographic occupancy, not a generic sidebar grid.",
    }
    photo_power = float(occupancy.get("sky_area") or 0) >= 0.12 or float(cov.get("hard_protected") or 0) >= 0.28
    type_end = editorial["y"] + editorial["h"]
    type_in_field = type_end <= 0.52 and headline["y"] < 0.28
    plan["photo_without_type_still_powerful"] = bool(photo_power)
    plan["type_belongs_to_photograph"] = bool(type_in_field and origin in {"left", "right"})
    plan["quality_gate"] = "PASS" if plan["photo_without_type_still_powerful"] and plan["type_belongs_to_photograph"] else "FAIL"
    return plan


def _pct(box: dict[str, float]) -> str:
    return (
        f"left:{box['x'] * 100:.2f}%;top:{box['y'] * 100:.2f}%;"
        f"width:{box['w'] * 100:.2f}%;height:{box['h'] * 100:.2f}%;"
    )


def master_html(*, photo_uri: str, logo_markup: str, font_css: str, plan: dict[str, Any]) -> str:
    loc = _pct(plan["LOCATION_TERRITORY"])
    head = _pct(plan["HEADLINE_TERRITORY"])
    offer = _pct(plan["OFFER_TERRITORY"])
    sec = _pct(plan["SECONDARY_COMMERCIAL_TERRITORY"])
    cta = _pct(plan["CTA_TERRITORY"])
    ed = _pct(plan["EDITORIAL_CLOSURE_TERRITORY"])
    brand = _pct(plan["BRAND_TERRITORY"])
    origin = "left" if plan.get("origin") == "left" else "right"
    head_px = int(min(90, max(56, plan["HEADLINE_TERRITORY"]["h"] * H * 0.42)))
    offer_px = int(min(36, max(22, plan["OFFER_TERRITORY"]["h"] * H * 0.42)))
    loc_px = int(min(15, max(11, plan["LOCATION_TERRITORY"]["h"] * H * 0.55)))
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:transparent;}}
.stage{{position:relative;width:{W}px;height:{H}px;}}
.photo{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;}}
.wash{{position:absolute;inset:0;pointer-events:none;
  background:
    linear-gradient(180deg, rgba(244,239,228,.50) 0%, rgba(244,239,228,.22) 18%, rgba(244,239,228,0) 38%),
    linear-gradient(90deg, rgba(244,239,228,.16) 0%, rgba(244,239,228,0) 46%);}}
.brand{{position:absolute;{brand}display:flex;align-items:flex-start;justify-content:flex-start;}}
.origin-right .brand{{justify-content:flex-end;}}
.brand svg{{max-width:100%;max-height:100%;height:auto;}}
.loc{{position:absolute;{loc}font-family:'Source Sans 3',sans-serif;font-size:{loc_px}px;letter-spacing:.46em;
  color:{NAVY};font-weight:500;text-align:{origin};}}
.headline{{position:absolute;{head}text-align:{origin};}}
.line1,.line2{{margin:0;padding:0;font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:{head_px}px;line-height:.92;letter-spacing:.04em;color:{NAVY};}}
.rule{{width:92px;height:1px;background:{NAVY};margin:14px 0 0 0;opacity:.75;}}
.origin-right .rule,.origin-right .cta-rule{{margin-left:auto;}}
.offer{{position:absolute;{offer}text-align:{origin};}}
.pct{{font-family:'Cormorant Garamond',serif;font-size:{offer_px}px;color:{NAVY};letter-spacing:.04em;}}
.sec{{position:absolute;{sec}font-family:'Cormorant Garamond',serif;font-size:22px;color:{NAVY};
  letter-spacing:.08em;text-align:{origin};}}
.unit{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.28em;margin-left:14px;}}
.cta{{position:absolute;{cta}font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.38em;
  color:{NAVY};font-weight:500;text-align:{origin};}}
.cta-rule{{width:54px;height:1px;background:{NAVY};margin-top:10px;opacity:.7;}}
.ed{{position:absolute;{ed}font-family:'Source Sans 3',sans-serif;font-size:12px;letter-spacing:.22em;
  color:{NAVY};text-align:{origin};opacity:.92;}}
</style>
</head>
<body>
<div class="stage origin-{origin}">
  <img class="photo" data-semantic="project_photo" alt="" src="{photo_uri}"/>
  <div class="wash"></div>
  <div class="brand">{logo_markup}</div>
  <div class="loc">{LOCATION_LINE}</div>
  <div class="headline">
    <p class="line1">ALIRKEN</p>
    <p class="line2">KAZAN</p>
    <div class="rule"></div>
  </div>
  <div class="offer"><div class="pct">{REQUIRED_FACTS["discount"]} {REQUIRED_FACTS["discount_label"]}</div></div>
  <div class="sec">675.000 USD<span class="unit">{REQUIRED_FACTS["unit"]} {REQUIRED_FACTS["unit_label"]}</span></div>
  <div class="cta">{REQUIRED_FACTS["cta"]}<div class="cta-rule"></div></div>
  <div class="ed">{APPROVED_BOTTOM_COPY}</div>
</div>
</body>
</html>
"""


def compose_from_plan(*, photo: Image.Image, logo_bytes: bytes, plan: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    html = master_html(
        photo_uri=_jpeg_data_uri(photo, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
        plan=plan,
    )
    return render_html_to_png(html, width=W, height=H)


def render_photo_candidates(ranked: list[dict[str, Any]], selected_id: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "02  APPROVED TEMPLE EXTERIORS  —  scored for ORNEK_00001 sky field", font=_font(18), fill=GOLD)
    x, y = 36, 64
    for item in ranked[:8]:
        tile = item["preview"].copy()
        tile.thumbnail((430, 430), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        mark = "SELECTED" if item["asset_id"] == selected_id else f"sky {float(item.get('sky_area') or 0):.2f}"
        draw.text((x, y + tile.size[1] + 6), f"{item['filename'][:34]}", font=_font(12), fill=IVORY)
        draw.text((x, y + tile.size[1] + 24), mark, font=_font(13), fill=GOLD if item["asset_id"] == selected_id else (180, 176, 168))
        x += 470
        if x > 1700:
            x = 36
            y += 500
    return canvas


def render_plan_board(photo: Image.Image, plan: dict[str, Any]) -> Image.Image:
    image = photo.copy().convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    palette = {
        "PHOTO_FOCAL_AREA": (80, 180, 255, 50),
        "NATURAL_NEGATIVE_SPACE": (40, 170, 90, 40),
        "HEADLINE_TERRITORY": (255, 255, 255, 55),
        "LOCATION_TERRITORY": (200, 200, 200, 50),
        "OFFER_TERRITORY": (201, 168, 92, 55),
        "SECONDARY_COMMERCIAL_TERRITORY": (201, 168, 92, 40),
        "BRAND_TERRITORY": (120, 255, 120, 50),
        "CTA_TERRITORY": (180, 120, 255, 50),
        "EDITORIAL_CLOSURE_TERRITORY": (244, 239, 228, 45),
    }
    for key, color in palette.items():
        box = plan.get(key) or {}
        x0 = int(float(box["x"]) * W)
        y0 = int(float(box["y"]) * H)
        x1 = int((float(box["x"]) + float(box["w"])) * W)
        y1 = int((float(box["y"]) + float(box["h"])) * H)
        draw.rectangle((x0, y0, x1, y1), outline=color[:3] + (230,), width=2)
        ImageDraw.Draw(image).text((x0 + 6, y0 + 4), key.replace("_TERRITORY", "").replace("_AREA", "")[:22], fill=color[:3], font=_font(12))
    return image.convert("RGB")


def render_labeled(image: Image.Image, title: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (920, 1220), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), title, font=_font(18), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((860, 1080), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (30, 56))
    draw.text((30, 1168), caption[:70], font=_font(14), fill=IVORY)
    return canvas


def render_pair(left: Image.Image, right: Image.Image, left_label: str, right_label: str, title: str) -> Image.Image:
    canvas = Image.new("RGB", (1680, 1120), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), title, font=_font(18), fill=GOLD)
    x = 36
    for label, image in ((left_label, left), (right_label, right)):
        tile = image.copy()
        tile.thumbnail((780, 980), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 64))
        draw.text((x, 1064), label[:56], font=_font(16), fill=IVORY)
        x += 820
    return canvas


def load_catalog(db) -> list[dict[str, Any]]:
    return load_temple_exteriors(db)
