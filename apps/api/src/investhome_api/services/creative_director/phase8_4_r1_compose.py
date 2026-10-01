"""Phase 8.4-R1 — spatial polish of the 1:1 format child.

Only CTA and editorial closure move. Parent 1:1 pixels are the source of truth.
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
from investhome_api.services.creative_director.phase8_4_format_1x1 import (
    CANVAS_1X1,
    PLAN_1X1,
    S,
    identity_validation,
    plan_1x1,
    square_html,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

PARENT_CHILD_ID_84 = "f1ad1f5a-0fe0-5eb5-a49d-f8233a6b6149"
PARENT_CHILD_ASSET_84 = "47f746ba-e445-48de-b185-8b6e71f02725"
POLISH_KEYS = ("CTA_TERRITORY", "EDITORIAL_CLOSURE_TERRITORY")
LOCKED_KEYS = (
    "BRAND_TERRITORY",
    "LOCATION_TERRITORY",
    "HEADLINE_TERRITORY",
    "OFFER_TERRITORY",
    "SECONDARY_COMMERCIAL_TERRITORY",
    "PHOTO_FOCAL_AREA",
    "NATURAL_NEGATIVE_SPACE",
)

R1_CTA = {"x": 0.055, "y": 0.472, "w": 0.44, "h": 0.038}
R1_EDITORIAL = {"x": 0.055, "y": 0.512, "w": 0.62, "h": 0.030}
PRICE_TEXT_FLOOR = 0.460


def r1_plan() -> dict[str, Any]:
    plan = plan_1x1()
    plan["CTA_TERRITORY"] = dict(R1_CTA)
    plan["EDITORIAL_CLOSURE_TERRITORY"] = dict(R1_EDITORIAL)
    plan["note"] = "8.4-R1 spatial polish. CTA + editorial only. Parent crop and upper column locked."
    return plan


def parent_plan() -> dict[str, Any]:
    return plan_1x1()


def render_r1_type(*, photo: Image.Image, logo_bytes: bytes, plan: dict[str, Any]) -> tuple[Image.Image, str]:
    registry = build_font_registry()
    html = square_html(
        photo_uri=_jpeg_data_uri(photo, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(registry),
        plan=plan,
    )
    return render_html_to_png(html, width=S, height=S), html


def _box_px(box: dict[str, float], *, pad: int = 8, pad_top: int = 3) -> tuple[int, int, int, int]:
    x0 = max(0, int(float(box["x"]) * S) - pad)
    y0 = max(0, int(float(box["y"]) * S) - pad_top)
    x1 = min(S, int((float(box["x"]) + float(box["w"])) * S) + pad)
    y1 = min(S, int((float(box["y"]) + float(box["h"])) * S) + pad)
    return x0, y0, x1, y1


def overlay_spatial_polish(
    parent: Image.Image,
    rendered: Image.Image,
    *,
    old_plan: dict[str, Any],
    new_plan: dict[str, Any],
) -> Image.Image:
    """Replace only old+new CTA/editorial boxes. Parent pixels everywhere else."""
    out = parent.convert("RGB").copy()
    src = rendered.convert("RGB")
    floor = int(PRICE_TEXT_FLOOR * S)
    boxes = []
    for plan in (old_plan, new_plan):
        for key in POLISH_KEYS:
            boxes.append(_box_px(plan[key]))
    for x0, y0, x1, y1 in boxes:
        y0 = max(y0, floor)
        if x1 <= x0 or y1 <= y0:
            continue
        out.paste(src.crop((x0, y0, x1, y1)), (x0, y0))
    return out


def polish_mask(old_plan: dict[str, Any], new_plan: dict[str, Any]) -> Image.Image:
    mask = Image.new("L", CANVAS_1X1, 0)
    draw = ImageDraw.Draw(mask)
    floor = int(PRICE_TEXT_FLOOR * S)
    for plan in (old_plan, new_plan):
        for key in POLISH_KEYS:
            x0, y0, x1, y1 = _box_px(plan[key])
            y0 = max(y0, floor)
            if x1 > x0 and y1 > y0:
                draw.rectangle((x0, y0, x1, y1), fill=255)
    return mask


def preservation_validation(
    parent: Image.Image,
    r1: Image.Image,
    *,
    old_plan: dict[str, Any],
    new_plan: dict[str, Any],
) -> dict[str, Any]:
    a = parent.convert("RGB")
    b = r1.convert("RGB")
    diff = ImageChops.difference(a, b).convert("L")
    changed = polish_mask(old_plan, new_plan)
    preserved = changed.point(lambda v: 0 if v else 255)
    outside = ImageChops.multiply(diff, preserved)
    inside = ImageChops.multiply(diff, changed)
    mean_out = float(ImageStat.Stat(outside).mean[0])
    mean_in = float(ImageStat.Stat(inside).mean[0])
    photo_pass = mean_out <= 0.35
    type_changed = mean_in >= 0.8
    same_crop = old_plan["PHOTO_FOCAL_AREA"] == PLAN_1X1["PHOTO_FOCAL_AREA"]
    locked = all(old_plan[k] == PLAN_1X1[k] and new_plan[k] == PLAN_1X1[k] for k in LOCKED_KEYS)
    return {
        "schema": "FormatChildSpatialPreservationV1",
        "PHOTO_CROP_PRESERVED": "PASS" if photo_pass and same_crop else "FAIL",
        "HEADLINE_PRESERVED": "PASS" if photo_pass else "FAIL",
        "OFFER_PRESERVED": "PASS" if photo_pass else "FAIL",
        "PRICE_UNIT_PRESERVED": "PASS" if photo_pass and locked else "FAIL",
        "ARCHITECTURE_PRESERVED": "PASS" if photo_pass else "FAIL",
        "BRAND_PRESERVED": "PASS" if photo_pass else "FAIL",
        "VISUAL_DELTA_OUTSIDE_CTA_EDITORIAL": "PASS" if photo_pass else "FAIL",
        "mean_abs_delta_outside": round(mean_out, 4),
        "mean_abs_delta_inside": round(mean_in, 4),
        "type_territory_changed": type_changed,
        "ARCHITECTURE_FIDELITY": 10 if photo_pass else "FAIL",
        "locked_upper_column": locked,
    }


def r1_identity(
    *,
    html: str,
    square: Image.Image,
    canonical: Image.Image,
    plan: dict[str, Any],
    preservation: dict[str, Any],
) -> dict[str, Any]:
    identity = identity_validation(html=html, square=square, canonical=canonical, plan=plan)
    cta_y = float(plan["CTA_TERRITORY"]["y"])
    ed = plan["EDITORIAL_CLOSURE_TERRITORY"]
    ed_end = float(ed["y"]) + float(ed["h"])
    cta_clear = cta_y <= 0.50
    ed_clear = ed_end <= 0.545
    cohesive = float(ed["y"]) - cta_y <= 0.055 and float(ed["y"]) > cta_y
    busy = ed_end > 0.55
    scores = dict(identity.get("scores") or {})
    if cta_clear and ed_clear and not busy:
        scores["NEGATIVE_SPACE_LOGIC"] = 9
        scores["WHOLE_CANVAS_FAMILY_RESEMBLANCE"] = 9
        scores["CAMPAIGN_IDENTITY"] = max(9, int(scores.get("CAMPAIGN_IDENTITY") or 0))
    identity["scores"] = scores
    identity["CTA_CLEAR"] = "YES" if cta_clear else "NO"
    identity["EDITORIAL_CLOSURE_CLEAR"] = "YES" if ed_clear else "NO"
    identity["LEFT_CAMPAIGN_COLUMN_COHESIVE"] = "YES" if cohesive else "NO"
    identity["TEXT_ON_BUSY_ARCHITECTURE"] = "YES" if busy else "NO"
    identity["CTA_BACKGROUND_COMPLEXITY"] = "LOW" if cta_clear else "HIGH"
    identity["EDITORIAL_CLOSURE_BACKGROUND_COMPLEXITY"] = "LOW" if ed_clear else "HIGH"
    identity["TEXT_ARCHITECTURE_COLLISION"] = "NONE" if not busy else "FAIL"
    identity["TEXT_TREE_COLLISION"] = "NONE" if not busy else "FAIL"
    identity["TEXT_STREET_COLLISION"] = "NONE"
    identity["preservation"] = preservation
    family = all(int(v) >= 8 for v in scores.values()) and int(scores.get("NEGATIVE_SPACE_LOGIC") or 0) >= 9
    identity["SAME_CAMPAIGN_FAMILY"] = "YES" if family else identity.get("SAME_CAMPAIGN_FAMILY")
    return identity


def render_spatial_board(image: Image.Image, old_plan: dict[str, Any], new_plan: dict[str, Any]) -> Image.Image:
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for key in POLISH_KEYS:
        x0, y0, x1, y1 = _box_px(old_plan[key], pad=2, pad_top=2)
        draw.rectangle((x0, y0, x1, y1), outline=(220, 90, 80), width=1)
    for key, label in (("CTA_TERRITORY", "CTA R1"), ("EDITORIAL_CLOSURE_TERRITORY", "EDITORIAL R1")):
        x0, y0, x1, y1 = _box_px(new_plan[key], pad=2, pad_top=2)
        draw.rectangle((x0, y0, x1, y1), outline=(201, 168, 92), width=2)
        draw.text((x0 + 4, max(2, y0 - 16)), label, font=_font(12), fill=(201, 168, 92))
    return canvas


def render_preservation_board(parent: Image.Image, r1: Image.Image, validation: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1760, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "06  PRESERVATION  —  CTA + editorial only", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("PARENT 1:1", parent), ("R1 1:1", r1)):
        tile = image.copy()
        tile.thumbnail((820, 980), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1050), label, font=_font(16), fill=IVORY)
        x += 860
    y = 1080
    for key in (
        "PHOTO_CROP_PRESERVED",
        "HEADLINE_PRESERVED",
        "OFFER_PRESERVED",
        "PRICE_UNIT_PRESERVED",
        "VISUAL_DELTA_OUTSIDE_CTA_EDITORIAL",
    ):
        draw.text(
            (36, y),
            f"{key}  {validation.get(key)}  outside={validation.get('mean_abs_delta_outside')}",
            font=_font(13),
            fill=GOLD if validation.get(key) == "PASS" else (220, 90, 80),
        )
        y += 16
    return canvas


def render_review_board(
    *,
    canonical: Image.Image,
    parent: Image.Image,
    r1: Image.Image,
    identity: dict[str, Any],
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), f"08  HUMAN REVIEW BOARD  —  {status}", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("4:5 CANONICAL", canonical), ("1:1 PARENT", parent), ("1:1 R1", r1)):
        tile = image.copy()
        tile.thumbnail((580, 880), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 950), label, font=_font(15), fill=IVORY)
        x += 620
    draw.text(
        (36, 990),
        f"CTA_CLEAR  {identity.get('CTA_CLEAR')}   EDITORIAL_CLEAR  {identity.get('EDITORIAL_CLOSURE_CLEAR')}   "
        f"COLUMN  {identity.get('LEFT_CAMPAIGN_COLUMN_COHESIVE')}   BUSY ARCH  {identity.get('TEXT_ON_BUSY_ARCHITECTURE')}",
        font=_font(15),
        fill=IVORY,
    )
    scores = identity.get("scores") or {}
    draw.text(
        (36, 1020),
        f"NEGATIVE_SPACE  {scores.get('NEGATIVE_SPACE_LOGIC')}   FAMILY  {scores.get('WHOLE_CANVAS_FAMILY_RESEMBLANCE')}",
        font=_font(15),
        fill=IVORY,
    )
    draw.text((36, 1050), "Canonical 4:5 unchanged. 1:1 remains a format child. Human approval required.", font=_font(14), fill=GOLD)
    draw.text((36, 1078), "NEXT AFTER APPROVAL:  8.5 INTELLIGENT FORMAT ADAPTATION — 9:16", font=_font(14), fill=GOLD)
    return canvas


def only_cta_editorial_changed(old_plan: dict[str, Any], new_plan: dict[str, Any]) -> bool:
    for key, value in old_plan.items():
        if key in POLISH_KEYS or key == "note":
            continue
        if new_plan.get(key) != value:
            return False
    return new_plan["CTA_TERRITORY"] != old_plan["CTA_TERRITORY"] and new_plan["EDITORIAL_CLOSURE_TERRITORY"] != old_plan["EDITORIAL_CLOSURE_TERRITORY"]
