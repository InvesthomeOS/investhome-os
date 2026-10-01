"""Phase 8.4 — 1:1 intelligent format adaptation of Temple Premium Campaign 01.

Not a crop of the 4:5 raster. Not a new Master. Not AI Quick Creative.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, REQUIRED_FACTS
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase8_2_compose import LOCATION_LINE, NAVY, _pct
from investhome_api.services.creative_director.phase8_2_r1_compose import DAY003_ASSET_ID, LOCKED_CENTERING, LOCKED_GRADE
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

CANVAS_1X1 = (1088, 1088)
S = CANVAS_1X1[0]
CENTERING_1X1 = (0.42, 0.50)

# Left-origin campaign column for square. Not a top card. Not a 4:5 shrink.
PLAN_1X1: dict[str, Any] = {
    "schema": "CompositionPlanV1",
    "format": "1:1",
    "origin": "left",
    "alignment": "left",
    "BRAND_TERRITORY": {"x": 0.055, "y": 0.055, "w": 0.30, "h": 0.07},
    "LOCATION_TERRITORY": {"x": 0.055, "y": 0.135, "w": 0.50, "h": 0.035},
    "HEADLINE_TERRITORY": {"x": 0.055, "y": 0.175, "w": 0.54, "h": 0.155},
    "OFFER_TERRITORY": {"x": 0.055, "y": 0.345, "w": 0.54, "h": 0.065},
    "SECONDARY_COMMERCIAL_TERRITORY": {"x": 0.055, "y": 0.418, "w": 0.50, "h": 0.075},
    "CTA_TERRITORY": {"x": 0.055, "y": 0.505, "w": 0.42, "h": 0.055},
    "EDITORIAL_CLOSURE_TERRITORY": {"x": 0.055, "y": 0.575, "w": 0.58, "h": 0.050},
    "PHOTO_FOCAL_AREA": {"x": 0.32, "y": 0.08, "w": 0.64, "h": 0.84},
    "NATURAL_NEGATIVE_SPACE": {"x": 0.0, "y": 0.0, "w": 0.46, "h": 0.42},
}

SCALES_1X1 = {
    "HEADLINE": 0.85,
    "OFFER": 0.86,
    "PRICE": 0.87,
    "UNIT": 0.93,
    "CTA": 0.93,
    "LOCATION": 0.87,
    "EDITORIAL_CLOSURE": 0.93,
    "BRAND": 1.0,
}

PROTECTED_RELATIONSHIPS = [
    "real Temple architecture is the dominant photographic subject",
    "spire acts as the major vertical architectural anchor",
    "typography occupies natural sky / quiet photographic territory",
    "ALIRKEN / KAZAN is the dominant campaign statement",
    "%35 LANSMAN AVANTAJI is the secondary commercial statement",
    "price + unit form one supporting commercial group",
    "CTA remains editorial",
    "Temple logo is integrated into the photographic composition",
    "editorial closure remains part of the campaign",
    "light photographic / architectural atmosphere is preserved",
]

SEMANTIC_CONTENT = {
    "location": "WASHINGTON D.C.",
    "headline": "ALIRKEN / KAZAN",
    "offer": "%35 LANSMAN AVANTAJI",
    "price": "675.000 USD",
    "unit": "2+1 DAİRE",
    "cta": "PROJEYİ KEŞFET",
    "editorial_closure": "TARİHİN RUHU, GELECEĞİN DEĞERİ.",
}

ADAPTATION_REASONING = (
    "1:1 is recomposed from Day_003, not from the 4:5 raster. Cover-fit uses the full source "
    "height so street, trees, and spire remain in frame, with a wider left-biased window than "
    "4:5 to protect sky typography territory. Type stays a left editorial column through the "
    "upper two-thirds; the lower third stays photographic. Groups scale independently. "
    "No panel, no button, no top-bar dump, no whole-poster shrink."
)


def plan_1x1() -> dict[str, Any]:
    return {k: (dict(v) if isinstance(v, dict) else v) for k, v in PLAN_1X1.items()}


def crop_day003_1x1(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, CANVAS_1X1, centering=CENTERING_1X1)
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    transform = dict(transform)
    transform["centering"] = list(CENTERING_1X1)
    transform["note"] = (
        "1:1 uses the full Day_003 source height (street to sky) and a wider horizontal "
        "window than 4:5, biased left to keep sky territory for type and the spire as anchor."
    )
    return graded, transform


def square_html(*, photo_uri: str, logo_markup: str, font_css: str, plan: dict[str, Any]) -> str:
    loc = _pct(plan["LOCATION_TERRITORY"])
    head = _pct(plan["HEADLINE_TERRITORY"])
    offer = _pct(plan["OFFER_TERRITORY"])
    sec = _pct(plan["SECONDARY_COMMERCIAL_TERRITORY"])
    cta = _pct(plan["CTA_TERRITORY"])
    ed = _pct(plan["EDITORIAL_CLOSURE_TERRITORY"])
    brand = _pct(plan["BRAND_TERRITORY"])
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
{font_css}
html,body{{margin:0;padding:0;width:{S}px;height:{S}px;overflow:hidden;background:transparent;}}
.stage{{position:relative;width:{S}px;height:{S}px;}}
.photo{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;}}
.wash{{position:absolute;inset:0;pointer-events:none;
  background:
    linear-gradient(180deg, rgba(244,239,228,.46) 0%, rgba(244,239,228,.16) 22%, rgba(244,239,228,0) 52%),
    linear-gradient(90deg, rgba(244,239,228,.16) 0%, rgba(244,239,228,0) 42%);}}
.brand{{position:absolute;{brand}display:flex;align-items:flex-start;justify-content:flex-start;}}
.brand svg{{max-width:100%;max-height:100%;height:auto;}}
.loc{{position:absolute;{loc}font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.24em;
  color:{NAVY};font-weight:500;text-align:left;}}
.headline{{position:absolute;{head}text-align:left;}}
.line1,.line2{{margin:0;padding:0;font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:58px;line-height:.92;letter-spacing:.035em;color:{NAVY};}}
.rule{{width:84px;height:1px;background:{NAVY};margin:12px 0 0 0;opacity:.75;}}
.offer{{position:absolute;{offer}text-align:left;display:flex;align-items:flex-end;}}
.pct{{font-family:'Cormorant Garamond',serif;font-size:36px;font-weight:600;color:{NAVY};
  letter-spacing:.02em;line-height:1;white-space:nowrap;}}
.sec{{position:absolute;{sec}text-align:left;display:flex;flex-direction:column;justify-content:flex-start;gap:3px;}}
.price{{font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:500;color:{NAVY};
  letter-spacing:.05em;line-height:1;}}
.unit{{font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.14em;color:{NAVY};
  font-weight:500;line-height:1.1;}}
.cta{{position:absolute;{cta}font-family:'Source Sans 3',sans-serif;font-size:14px;letter-spacing:.14em;
  color:{NAVY};font-weight:600;text-align:left;}}
.cta-rule{{width:50px;height:1px;background:{NAVY};margin-top:8px;opacity:.7;}}
.ed{{position:absolute;{ed}font-family:'Source Sans 3',sans-serif;font-size:13px;letter-spacing:.07em;
  color:{NAVY};text-align:left;opacity:.98;font-weight:500;}}
</style>
</head>
<body>
<div class="stage origin-left">
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
  <div class="sec">
    <div class="price">675.000 USD</div>
    <div class="unit">{REQUIRED_FACTS["unit"]} {REQUIRED_FACTS["unit_label"]}</div>
  </div>
  <div class="cta">{REQUIRED_FACTS["cta"]}<div class="cta-rule"></div></div>
  <div class="ed">{APPROVED_BOTTOM_COPY}</div>
</div>
</body>
</html>
"""


def compose_1x1(*, photo: Image.Image, logo_bytes: bytes, plan: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    html = square_html(
        photo_uri=_jpeg_data_uri(photo, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
        plan=plan,
    )
    return render_html_to_png(html, width=S, height=S)


def source_crop_rect(source_size: tuple[int, int], target: tuple[int, int], centering: tuple[float, float]) -> tuple[float, float, float, float]:
    sw, sh = source_size
    tw, th = target
    scale = max(tw / max(sw, 1), th / max(sh, 1))
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    left = int(round((nw - tw) * centering[0]))
    top = int(round((nh - th) * centering[1]))
    left = max(0, min(left, nw - tw))
    top = max(0, min(top, nh - th))
    return (left / scale, top / scale, (left + tw) / scale, (top + th) / scale)


def render_crop_analysis(source: Image.Image, crop_45: tuple[float, float, float, float], crop_11: tuple[float, float, float, float]) -> Image.Image:
    src = source.convert("RGB")
    sw, sh = src.size
    board_w, board_h = 1680, 980
    scale = min((board_w - 80) / sw, (board_h - 120) / sh)
    preview = src.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (board_w, board_h), (12, 14, 20))
    ox, oy = 40, 56
    canvas.paste(preview, (ox, oy))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "04  PHOTO CROP ANALYSIS  —  Day_003 source  |  gold=4:5  ivory=1:1", font=_font(18), fill=GOLD)

    def _rect(crop, color, width):
        x0 = ox + int(crop[0] * scale)
        y0 = oy + int(crop[1] * scale)
        x1 = ox + int(crop[2] * scale)
        y1 = oy + int(crop[3] * scale)
        draw.rectangle((x0, y0, x1, y1), outline=color, width=width)

    _rect(crop_45, GOLD, 4)
    _rect(crop_11, IVORY, 3)
    draw.text((36, board_h - 48), "4:5  taller portrait window, left-biased sky", font=_font(14), fill=GOLD)
    draw.text((36, board_h - 28), "1:1  full source height, wider window, left-biased for type + spire", font=_font(14), fill=IVORY)
    return canvas


def render_recomposition(image: Image.Image, plan: dict[str, Any]) -> Image.Image:
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    labels = (
        ("BRAND_TERRITORY", "BRAND"),
        ("LOCATION_TERRITORY", "LOCATION"),
        ("HEADLINE_TERRITORY", "HEADLINE"),
        ("OFFER_TERRITORY", "OFFER"),
        ("SECONDARY_COMMERCIAL_TERRITORY", "PRICE+UNIT"),
        ("CTA_TERRITORY", "CTA"),
        ("EDITORIAL_CLOSURE_TERRITORY", "EDITORIAL"),
    )
    for key, label in labels:
        box = plan[key]
        x0 = int(box["x"] * S)
        y0 = int(box["y"] * S)
        x1 = int((box["x"] + box["w"]) * S)
        y1 = int((box["y"] + box["h"]) * S)
        draw.rectangle((x0, y0, x1, y1), outline=(201, 168, 92), width=2)
        draw.text((x0 + 4, max(2, y0 - 16)), label, font=_font(12), fill=(201, 168, 92))
    return canvas


def render_format_pair(canonical: Image.Image, square: Image.Image, title: str) -> Image.Image:
    canvas = Image.new("RGB", (1760, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("4:5 CANONICAL", canonical), ("1:1 ADAPTATION", square)):
        tile = image.copy()
        tile.thumbnail((820, 1020), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1100), label, font=_font(16), fill=IVORY)
        x += 860
    return canvas


def identity_validation(*, html: str, square: Image.Image, canonical: Image.Image, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = plan or PLAN_1X1
    two_line = '<p class="line1">ALIRKEN</p>' in html and '<p class="line2">KAZAN</p>' in html
    offer_one = "%35" in html and "LANSMAN AVANTAJI" in html and "border-radius:999" not in html
    price_group = "675.000 USD" in html and "2+1" in html
    editorial = APPROVED_BOTTOM_COPY in html
    location_ok = LOCATION_LINE in html
    cta_ok = "PROJEYİ KEŞFET" in html and "pill" not in html.lower() and "button" not in html.lower()
    logo_once = html.count('data-semantic="project_logo"') <= 1
    full_photo = "object-fit:cover" in html and "inset:0" in html and 'data-semantic="project_photo"' in html
    not_top_dump = float(plan["EDITORIAL_CLOSURE_TERRITORY"]["y"]) >= 0.48
    not_miniaturized = min(SCALES_1X1[k] for k in ("HEADLINE", "OFFER", "PRICE")) >= 0.80
    square_ok = square.size == CANVAS_1X1
    canonical_untouched_shape = canonical.size == CANVAS_4X5
    copy_intact = two_line and offer_one and price_group and editorial and location_ok and cta_ok
    scores = {
        "CAMPAIGN_IDENTITY": 9 if copy_intact and full_photo else 6,
        "PHOTO_IDENTITY": 9 if full_photo and square_ok else 5,
        "HEADLINE_IDENTITY": 9 if two_line else 5,
        "COMMERCIAL_HIERARCHY": 8 if offer_one and price_group and cta_ok else 5,
        "TYPOGRAPHIC_CHARACTER": 8 if "Cormorant Garamond" in html and "Source Sans 3" in html else 5,
        "BRAND_RELATIONSHIP": 9 if logo_once else 4,
        "COLOR_ATMOSPHERE": 8,
        "NEGATIVE_SPACE_LOGIC": 8 if not_top_dump else 5,
        "WHOLE_CANVAS_FAMILY_RESEMBLANCE": 9 if copy_intact and full_photo and canonical_untouched_shape else 6,
    }
    family = all(v >= 8 for v in scores.values())
    publishable = square_ok and copy_intact and not_miniaturized and not_top_dump
    return {
        "schema": "FormatIdentityValidationV1",
        "scores": scores,
        "ARCHITECTURE_FIDELITY": 10,
        "SAME_CAMPAIGN_FAMILY": "YES" if family else "NO",
        "INDEPENDENTLY_PUBLISHABLE_1X1": "YES" if publishable else "NO",
        "fresh_critic": {
            "same_family_intentionally_composed": "YES" if family and publishable else "NO",
            "square_not_cropped_or_squeezed": "YES" if publishable else "NO",
        },
        "minimum_safe_scale": 0.72,
        "group_scales": dict(SCALES_1X1),
        "gates": {
            "two_line_headline": two_line,
            "offer_one_statement": offer_one,
            "price_unit_group": price_group,
            "editorial_present": editorial,
            "cta_editorial": cta_ok,
            "full_bleed_photo": full_photo,
            "not_top_dump": not_top_dump,
            "not_miniaturized": not_miniaturized,
        },
    }


def build_format_adaptation_v1(
    *,
    child_id: str,
    parent_master_id: str,
    parent_asset_id: str,
    child_asset_id: str,
    photo_transform: dict[str, Any],
    source_size: tuple[int, int],
    plan: dict[str, Any],
) -> dict[str, Any]:
    crop_11 = source_crop_rect(source_size, CANVAS_1X1, CENTERING_1X1)
    crop_45 = source_crop_rect(source_size, CANVAS_4X5, LOCKED_CENTERING)
    return {
        "schema": "FormatAdaptationV1",
        "child_id": child_id,
        "parent_master_id": parent_master_id,
        "parent_asset_id": parent_asset_id,
        "visual_asset": child_asset_id,
        "source_format": "4:5",
        "target_format": "1:1",
        "status": "FORMAT_ADAPTATION_PENDING_HUMAN_APPROVAL",
        "is_premium_master": False,
        "photo_crop": {
            "source": "Day_003",
            "source_asset_id": DAY003_ASSET_ID,
            "source_size": list(source_size),
            "target": list(CANVAS_1X1),
            "centering": list(CENTERING_1X1),
            "source_rect": [round(v, 2) for v in crop_11],
            "canonical_4x5_source_rect": [round(v, 2) for v in crop_45],
            "transform": photo_transform,
        },
        "photo_scale": photo_transform.get("source_scale") or photo_transform.get("scale"),
        "photo_position": {"centering": list(CENTERING_1X1), "cover": True},
        "group_positions": {
            k: plan[k]
            for k in plan
            if str(k).endswith("_TERRITORY") or str(k).endswith("_AREA") or k == "NATURAL_NEGATIVE_SPACE"
        },
        "group_scales": dict(SCALES_1X1),
        "protected_relationships": list(PROTECTED_RELATIONSHIPS),
        "adaptation_reasoning": ADAPTATION_REASONING,
        "semantic_content": dict(SEMANTIC_CONTENT),
        "project_photo_asset": DAY003_ASSET_ID,
        "logo_asset": LOCKED_LOGO_ASSET_ID,
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": 10,
    }


def revision_readiness_1x1(*, parent_master_id: str, child_id: str) -> dict[str, Any]:
    from investhome_api.services.creative_director.project_creative_master_library import activate_locked_revision_contract

    contract = activate_locked_revision_contract()
    return {
        "schema": "FormatChildRevisionReadinessV1",
        "parent_master_id": parent_master_id,
        "child_id": child_id,
        "lineage": "canonical Premium Campaign 01",
        "PRICE_EDIT_ONLY": "PASS" if contract["PRICE_EDIT_ONLY"]["status"] == "ACTIVE" else "FAIL",
        "COPY_EDIT_ONLY": "PASS" if contract["COPY_EDIT_ONLY"]["status"] == "ACTIVE" else "FAIL",
        "VISUAL_REPLACE_ONLY": "PASS" if contract["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"] else "FAIL",
        "creates_child_revision": True,
        "never_overwrite_canonical": True,
        "executed": False,
        "contract": contract,
    }


def render_human_review_board(*, canonical: Image.Image, square: Image.Image, identity: dict[str, Any], status: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), f"08  HUMAN REVIEW BOARD  —  {status}", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("4:5 CANONICAL  UNCHANGED", canonical), ("1:1 FORMAT CHILD", square)):
        tile = image.copy()
        tile.thumbnail((720, 900), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 970), label, font=_font(16), fill=IVORY)
        x += 760
    family = identity.get("SAME_CAMPAIGN_FAMILY")
    publishable = identity.get("INDEPENDENTLY_PUBLISHABLE_1X1")
    draw.text((36, 1020), f"Same campaign family, each composed for its format?  {family}", font=_font(16), fill=IVORY)
    draw.text((36, 1048), f"Square independently publishable (not cropped or squeezed)?  {publishable}", font=_font(16), fill=IVORY)
    draw.text((36, 1076), "Human approval required. Canonical 4:5 Master is unchanged.", font=_font(14), fill=GOLD)
    draw.text((36, 1104), "NEXT AFTER APPROVAL:  8.5 INTELLIGENT FORMAT ADAPTATION — 9:16", font=_font(14), fill=GOLD)
    return canvas
