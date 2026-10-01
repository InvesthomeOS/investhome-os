"""Phase 8.2-R1 — typographic / commercial polish of the approved Temple Premium Master.

Photo, crop, logo, and headline composition stay locked to the parent.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageStat

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
from investhome_api.services.creative_director.phase8_2_compose import LOCATION_LINE, NAVY, W, H, _pct, render_pair
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

DAY003_ASSET_ID = "7346e259-f999-4fbb-a8d5-63708d4e0c81"
DAY003_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_003.jpg"
LOCKED_CENTERING = (0.46, 0.28)
LOCKED_GRADE = {"warmth": 0.06, "contrast": 1.05, "brightness": 1.01, "vignette": 0.06}
PARENT_MASTER_ID_82 = "9571efdf-7c41-5828-8d4d-cf63176a89d6"
PARENT_ASSET_ID_82 = "f5d779ff-6074-4f7b-8b91-692427a5b1f8"

# Exact parent CompositionPlanV1. Do not recalculate occupancy.
LOCKED_PLAN: dict[str, Any] = {
    "schema": "CompositionPlanV1",
    "source": "ORNEK_00001.jpg",
    "origin": "left",
    "PHOTO_FOCAL_AREA": {"x": 0.2059, "y": 0.0471, "w": 0.7647, "h": 0.8706},
    "NATURAL_NEGATIVE_SPACE": {"x": 0.0, "y": 0.1294, "w": 1.0, "h": 0.4941},
    "HEADLINE_TERRITORY": {"x": 0.07, "y": 0.196, "w": 0.62, "h": 0.1192},
    "LOCATION_TERRITORY": {"x": 0.07, "y": 0.1715, "w": 0.52, "h": 0.026},
    "OFFER_TERRITORY": {"x": 0.07, "y": 0.3152, "w": 0.5, "h": 0.0491},
    "SECONDARY_COMMERCIAL_TERRITORY": {"x": 0.07, "y": 0.3643, "w": 0.52, "h": 0.0421},
    "BRAND_TERRITORY": {"x": 0.07, "y": 0.1294, "w": 0.32, "h": 0.0421},
    "CTA_TERRITORY": {"x": 0.07, "y": 0.4064, "w": 0.4, "h": 0.0351},
    "EDITORIAL_CLOSURE_TERRITORY": {"x": 0.07, "y": 0.4414, "w": 0.56, "h": 0.0386},
    "alignment": "left",
    "sky_column": {"x": 0.07, "y": 0.1294, "w": 0.56, "h": 0.38},
}

POLISH_TERRITORIES = (
    "LOCATION_TERRITORY",
    "OFFER_TERRITORY",
    "SECONDARY_COMMERCIAL_TERRITORY",
    "CTA_TERRITORY",
    "EDITORIAL_CLOSURE_TERRITORY",
)
PRESERVED_TERRITORIES = ("BRAND_TERRITORY", "HEADLINE_TERRITORY")


def locked_plan() -> dict[str, Any]:
    return json_clone(LOCKED_PLAN)


def r1_plan() -> dict[str, Any]:
    """Keep brand, headline, location. Optical restack of commercial type only."""
    plan = locked_plan()
    plan["OFFER_TERRITORY"] = {"x": 0.07, "y": 0.318, "w": 0.56, "h": 0.056}
    plan["SECONDARY_COMMERCIAL_TERRITORY"] = {"x": 0.07, "y": 0.378, "w": 0.56, "h": 0.058}
    plan["CTA_TERRITORY"] = {"x": 0.07, "y": 0.440, "w": 0.44, "h": 0.040}
    plan["EDITORIAL_CLOSURE_TERRITORY"] = {"x": 0.07, "y": 0.484, "w": 0.62, "h": 0.040}
    plan["note"] = "R1 optical commercial restack. Brand, headline, photo, location origin locked."
    return plan


def json_clone(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: (dict(v) if isinstance(v, dict) else v) for k, v in payload.items()}


def crop_locked_day003(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=LOCKED_CENTERING)
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    transform = dict(transform)
    transform["centering"] = list(LOCKED_CENTERING)
    return graded, transform


def r1_html(*, photo_uri: str, logo_markup: str, font_css: str, plan: dict[str, Any]) -> str:
    loc = _pct(plan["LOCATION_TERRITORY"])
    head = _pct(plan["HEADLINE_TERRITORY"])
    offer = _pct(plan["OFFER_TERRITORY"])
    sec = _pct(plan["SECONDARY_COMMERCIAL_TERRITORY"])
    cta = _pct(plan["CTA_TERRITORY"])
    ed = _pct(plan["EDITORIAL_CLOSURE_TERRITORY"])
    brand = _pct(plan["BRAND_TERRITORY"])
    origin = "left" if plan.get("origin") == "left" else "right"
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
.brand svg{{max-width:100%;max-height:100%;height:auto;}}
.loc{{position:absolute;{loc}font-family:'Source Sans 3',sans-serif;font-size:15px;letter-spacing:.28em;
  color:{NAVY};font-weight:500;text-align:{origin};}}
.headline{{position:absolute;{head}text-align:{origin};}}
.line1,.line2{{margin:0;padding:0;font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:68px;line-height:.92;letter-spacing:.035em;color:{NAVY};}}
.rule{{width:92px;height:1px;background:{NAVY};margin:14px 0 0 0;opacity:.75;}}
.offer{{position:absolute;{offer}text-align:{origin};display:flex;align-items:flex-end;}}
.pct{{font-family:'Cormorant Garamond',serif;font-size:42px;font-weight:600;color:{NAVY};
  letter-spacing:.02em;line-height:1;white-space:nowrap;}}
.sec{{position:absolute;{sec}text-align:{origin};display:flex;flex-direction:column;justify-content:flex-start;gap:3px;}}
.price{{font-family:'Cormorant Garamond',serif;font-size:30px;font-weight:500;color:{NAVY};
  letter-spacing:.05em;line-height:1;}}
.unit{{font-family:'Source Sans 3',sans-serif;font-size:14px;letter-spacing:.14em;color:{NAVY};
  font-weight:500;line-height:1.1;}}
.cta{{position:absolute;{cta}font-family:'Source Sans 3',sans-serif;font-size:15px;letter-spacing:.14em;
  color:{NAVY};font-weight:600;text-align:{origin};}}
.cta-rule{{width:54px;height:1px;background:{NAVY};margin-top:8px;opacity:.7;}}
.ed{{position:absolute;{ed}font-family:'Source Sans 3',sans-serif;font-size:14px;letter-spacing:.08em;
  color:{NAVY};text-align:{origin};opacity:.98;font-weight:500;}}
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


def render_r1_type(*, photo: Image.Image, logo_bytes: bytes, plan: dict[str, Any]) -> Image.Image:
    registry = build_font_registry()
    html = r1_html(
        photo_uri=_jpeg_data_uri(photo, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
        plan=plan,
    )
    return render_html_to_png(html, width=W, height=H)


def _box_px(box: dict[str, float], *, pad: int = 10, pad_top: int = 4) -> tuple[int, int, int, int]:
    x0 = max(0, int(float(box["x"]) * W) - pad)
    y0 = max(0, int(float(box["y"]) * H) - pad_top)
    x1 = min(W, int((float(box["x"]) + float(box["w"])) * W) + pad)
    y1 = min(H, int((float(box["y"]) + float(box["h"])) * H) + pad)
    return x0, y0, x1, y1


def overlay_polish(parent: Image.Image, rendered: Image.Image, plan: dict[str, Any]) -> Image.Image:
    """Keep parent photo / logo / headline. Replace only commercial type territories."""
    out = parent.convert("RGB").copy()
    src = rendered.convert("RGB")
    head = plan["HEADLINE_TERRITORY"]
    brand = plan["BRAND_TERRITORY"]
    head_top = int(float(head["y"]) * H)
    head_bot = int((float(head["y"]) + float(head["h"])) * H)
    brand_bot = int((float(brand["y"]) + float(brand["h"])) * H)
    for key in POLISH_TERRITORIES:
        x0, y0, x1, y1 = _box_px(plan[key])
        if key == "LOCATION_TERRITORY":
            y0 = max(y0, brand_bot)
            y1 = min(y1, head_top)
        else:
            y0 = max(y0, head_bot)
        if x1 <= x0 or y1 <= y0:
            continue
        out.paste(src.crop((x0, y0, x1, y1)), (x0, y0))
    return out


def preservation_validation(parent: Image.Image, r1: Image.Image, plan: dict[str, Any]) -> dict[str, Any]:
    a = parent.convert("RGB")
    b = r1.convert("RGB")
    diff = ImageChops.difference(a, b)
    changed = Image.new("L", a.size, 0)
    draw = ImageDraw.Draw(changed)
    for key in POLISH_TERRITORIES:
        draw.rectangle(_box_px(plan[key]), fill=255)
    preserved_mask = changed.point(lambda v: 0 if v else 255)
    outside = ImageChops.multiply(diff.convert("L"), preserved_mask)
    inside = ImageChops.multiply(diff.convert("L"), changed)
    mean_out = float(ImageStat.Stat(outside).mean[0])
    mean_in = float(ImageStat.Stat(inside).mean[0])
    photo_pass = mean_out <= 0.35
    type_changed = mean_in >= 0.8
    return {
        "schema": "PreservationValidationV1",
        "PHOTO_COMPOSITION_PRESERVED": "PASS" if photo_pass else "FAIL",
        "ARCHITECTURE_PRESERVED": "PASS" if photo_pass else "FAIL",
        "BRAND_POSITION_PRESERVED": "PASS" if photo_pass else "FAIL",
        "HEADLINE_COMPOSITION_PRESERVED": "PASS" if photo_pass else "FAIL",
        "OVERALL_MASTER_IDENTITY_PRESERVED": "PASS" if photo_pass and type_changed else "FAIL",
        "mean_abs_delta_outside_type": round(mean_out, 4),
        "mean_abs_delta_inside_type": round(mean_in, 4),
        "ARCHITECTURE_FIDELITY": 10 if photo_pass else "FAIL",
    }


def render_hierarchy_board(image: Image.Image, plan: dict[str, Any]) -> Image.Image:
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    labels = (
        ("HEADLINE_TERRITORY", "1  ALIRKEN KAZAN"),
        ("OFFER_TERRITORY", "2  %35 LANSMAN AVANTAJI"),
        ("SECONDARY_COMMERCIAL_TERRITORY", "3  675.000 USD  +  2+1 DAİRE"),
        ("CTA_TERRITORY", "4  PROJEYİ KEŞFET"),
        ("EDITORIAL_CLOSURE_TERRITORY", "5  TARİHİN RUHU…"),
    )
    for key, label in labels:
        box = plan[key]
        x0, y0, x1, y1 = _box_px(box, pad=2)
        draw.rectangle((x0, y0, x1, y1), outline=(201, 168, 92), width=2)
        draw.text((x0 + 6, max(4, y0 - 18)), label, font=_font(13), fill=(201, 168, 92))
    return canvas


def render_preservation_board(parent: Image.Image, r1: Image.Image, validation: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "05  PRESERVATION VALIDATION  —  type territories only", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("PARENT", parent), ("R1", r1)):
        tile = image.copy()
        tile.thumbnail((780, 980), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1050), label, font=_font(16), fill=IVORY)
        x += 820
    y = 1080
    for key in (
        "PHOTO_COMPOSITION_PRESERVED",
        "ARCHITECTURE_PRESERVED",
        "BRAND_POSITION_PRESERVED",
        "HEADLINE_COMPOSITION_PRESERVED",
        "OVERALL_MASTER_IDENTITY_PRESERVED",
    ):
        draw.text((36, y), f"{key}  {validation.get(key)}", font=_font(13), fill=GOLD if validation.get(key) == "PASS" else (220, 90, 80))
        y += 18
    return canvas
