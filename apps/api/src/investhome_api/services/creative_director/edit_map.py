"""Edit Map v1 — raster-aware description of ONE approved finished-ad cover.

AI remains the designer. This module does not author visual design, render
templates, or run bounded local recomposition. It records what exists on the
current raster so later revision can preserve the commercial group.

Provider capabilities (analyze_design, edit_region, …) may help generate a map.
They do not own this schema.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EDIT_MAP_VERSION = "1.1"
MIN_MAP_CONFIDENCE = 0.55
CLEAN_PAD_PX = 4
AA_LUMA_MIN = 48

# OS-owned capability names. Not GPT Image keys. Not invoked in Phase 1.
EDIT_MAP_PROVIDER_CAPABILITIES = (
    "generate_finished_ad",
    "analyze_design",
    "edit_region",
    "replace_hero",
    "adapt_format",
)

REQUIRED_OCCUPIED_ROLES = (
    "hero_visual",
    "headline",
    "subheadline",
    "unit_label",
    "old_price",
    "discount",
    "logo",
    "cta",
    "supporting_copy",
)

FUTURE_PRICE_ROLES = ("new_price", "savings_price")
COMMERCIAL_CHILD_ROLES = ("unit_label", "old_price", "discount")


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def bbox_dict(x0: int, y0: int, x1: int, y1: int) -> dict[str, int]:
    return {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)}


def bbox_inside_canvas(bbox: dict[str, int], width: int, height: int) -> bool:
    return (
        0 <= bbox["x0"] < bbox["x1"] <= width
        and 0 <= bbox["y0"] < bbox["y1"] <= height
    )


def bbox_contains(parent: dict[str, int], child: dict[str, int], slack: int = 8) -> bool:
    return (
        child["x0"] >= parent["x0"] - slack
        and child["y0"] >= parent["y0"] - slack
        and child["x1"] <= parent["x1"] + slack
        and child["y1"] <= parent["y1"] + slack
    )


def bbox_iou(a: dict[str, int], b: dict[str, int]) -> float:
    ix0 = max(a["x0"], b["x0"])
    iy0 = max(a["y0"], b["y0"])
    ix1 = min(a["x1"], b["x1"])
    iy1 = min(a["y1"], b["y1"])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(1, (a["x1"] - a["x0"]) * (a["y1"] - a["y0"]))
    area_b = max(1, (b["x1"] - b["x0"]) * (b["y1"] - b["y0"]))
    return inter / float(area_a + area_b - inter)


def _luma(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _is_gold(r: int, g: int, b: int) -> bool:
    return r > 180 and g > 140 and b < 140


def _is_white(r: int, g: int, b: int) -> bool:
    return (not _is_gold(r, g, b)) and _luma(r, g, b) >= 210


def _is_navy(r: int, g: int, b: int) -> bool:
    return _luma(r, g, b) < 40


def _is_soft_commercial_type(r: int, g: int, b: int) -> bool:
    """Anti-aliased gold/white on navy. Not photo chroma."""
    lum = _luma(r, g, b)
    if lum < AA_LUMA_MIN:
        return False
    if _is_gold(r, g, b) or _is_white(r, g, b):
        return True
    goldish = r > 120 and g > 90 and b < 130 and r >= g - 8 and (r - b) > 25
    light = lum >= 90 and abs(r - g) < 40 and abs(g - b) < 40
    return bool(goldish or light)


def _is_photo(r: int, g: int, b: int) -> bool:
    lum = _luma(r, g, b)
    return 50 <= lum < 200 and not _is_gold(r, g, b)


def _row_fractions(px: Any, y: int, width: int, x0: int, x1: int, step: int = 2) -> dict[str, float]:
    gold = white = navy = photo = 0
    n = 0
    for x in range(x0, x1, step):
        n += 1
        r, g, b = px[x, y]
        if _is_gold(r, g, b):
            gold += 1
        elif _is_white(r, g, b):
            white += 1
        elif _is_navy(r, g, b):
            navy += 1
        elif _is_photo(r, g, b):
            photo += 1
    tot = max(1, n)
    return {
        "gold": gold / tot,
        "white": white / tot,
        "navy": navy / tot,
        "photo": photo / tot,
        "type": (gold + white) / tot,
    }


def _type_bbox(
    px: Any,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    *,
    gold: bool = True,
    white: bool = True,
    step: int = 1,
) -> dict[str, int] | None:
    xs: list[int] = []
    ys: list[int] = []
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            r, g, b = px[x, y]
            hit = (gold and _is_gold(r, g, b)) or (white and _is_white(r, g, b))
            if hit:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return bbox_dict(min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _cluster_xs(xs: list[int], gap: int = 24) -> list[tuple[int, int]]:
    if not xs:
        return []
    xs = sorted(xs)
    out = [[xs[0], xs[0]]]
    for x in xs[1:]:
        if x - out[-1][1] > gap:
            out.append([x, x])
        else:
            out[-1][1] = x
    return [(a, b) for a, b in out]


def measure_commercial_visual_bounds(image: Any, layout: dict[str, Any]) -> dict[str, Any]:
    """Tight raster extent of commercial type/decoration between copy and hero."""
    from PIL import Image as PILImage

    if not isinstance(image, PILImage.Image):
        raise TypeError("measure_commercial_visual_bounds requires a PIL Image")
    im = image.convert("RGB")
    width, height = im.size
    px = im.load()
    photo_start = int(layout.get("photo_start") or height)
    sub = layout.get("subheadline_bbox")
    head = layout.get("headline_bbox")
    after_copy = 0
    if sub:
        after_copy = int(sub["y1"])
    elif head:
        after_copy = int(head["y1"])
    y0 = min(max(after_copy + 2, 0), photo_start)
    y1 = photo_start
    pad_x = int(width * 0.06)
    x0, x1 = pad_x, width - pad_x
    strict: list[tuple[int, int]] = []
    soft: list[tuple[int, int]] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            if _is_gold(r, g, b) or _is_white(r, g, b):
                strict.append((x, y))
            elif _is_soft_commercial_type(r, g, b):
                soft.append((x, y))
    pts = strict + soft
    if not pts:
        semantic = layout.get("commercial_bbox")
        return {
            "visual_bbox": dict(semantic) if semantic else None,
            "strict_bbox": dict(semantic) if semantic else None,
            "strict_count": 0,
            "soft_count": 0,
            "anti_alias_extent": {"left_px": 0, "up_px": 0, "right_px": 0, "down_px": 0},
            "hero_boundary": photo_start,
            "scan": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        }

    def _bbox(points: list[tuple[int, int]]) -> dict[str, int]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return bbox_dict(min(xs), min(ys), max(xs) + 1, max(ys) + 1)

    visual = _bbox(pts)
    strict_box = _bbox(strict) if strict else dict(visual)
    aa = {
        "left_px": max(0, strict_box["x0"] - visual["x0"]),
        "up_px": max(0, strict_box["y0"] - visual["y0"]),
        "right_px": max(0, visual["x1"] - strict_box["x1"]),
        "down_px": max(0, visual["y1"] - strict_box["y1"]),
    }
    return {
        "visual_bbox": visual,
        "strict_bbox": strict_box,
        "strict_count": len(strict),
        "soft_count": len(soft),
        "anti_alias_extent": aa,
        "hero_boundary": photo_start,
        "scan": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
    }


def compute_safe_commercial_region(
    *,
    visual_bbox: dict[str, int] | None,
    semantic_bbox: dict[str, int] | None,
    headline_bbox: dict[str, int] | None,
    subheadline_bbox: dict[str, int] | None,
    hero_bbox: dict[str, int] | None,
    canvas_width: int,
    canvas_height: int,
    anti_alias_extent: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Cover all commercial pixels with a small pad. Never enter the hero."""
    aa = anti_alias_extent or {}
    requested = {
        "left_px": max(CLEAN_PAD_PX, int(aa.get("left_px") or 0) + 2),
        "right_px": max(CLEAN_PAD_PX, int(aa.get("right_px") or 0) + 2),
        "up_px": max(CLEAN_PAD_PX, int(aa.get("up_px") or 0) + 2),
        "down_px": max(CLEAN_PAD_PX, int(aa.get("down_px") or 0) + 2),
    }
    seed = visual_bbox or semantic_bbox
    if not seed:
        raise ValueError("commercial visual/semantic bbox missing")
    hero_y0 = int(hero_bbox["y0"]) if hero_bbox else canvas_height
    sub_y1 = int(subheadline_bbox["y1"]) if subheadline_bbox else 0
    head_y1 = int(headline_bbox["y1"]) if headline_bbox else 0
    copy_floor = max(sub_y1, head_y1)

    x0 = max(0, seed["x0"] - requested["left_px"])
    y0 = max(0, seed["y0"] - requested["up_px"])
    x1 = min(canvas_width, seed["x1"] + requested["right_px"])
    y1 = min(canvas_height, seed["y1"] + requested["down_px"])
    blocked: list[str] = []
    if y1 > hero_y0:
        y1 = hero_y0
        blocked.append("hero_visual")
    if y0 < copy_floor:
        # Keep covering visual pixels; only stop the pad if it would overlap copy.
        if seed["y0"] >= copy_floor:
            y0 = copy_floor
            blocked.append("subheadline" if sub_y1 >= head_y1 else "headline")
        else:
            blocked.append("subheadline" if subheadline_bbox else "headline")
    applied = {
        "left_px": seed["x0"] - x0,
        "up_px": seed["y0"] - y0,
        "right_px": x1 - seed["x1"],
        "down_px": y1 - seed["y1"],
    }
    safe = bbox_dict(x0, y0, x1, y1)
    up_room = max(0, safe["y0"] - copy_floor)
    down_room = max(0, hero_y0 - safe["y1"])
    left_room = safe["x0"]
    right_room = max(0, canvas_width - safe["x1"])
    allowed = []
    if up_room:
        allowed.append("up")
    if down_room:
        allowed.append("down")
    if left_room:
        allowed.append("left")
    if right_room:
        allowed.append("right")
    additional_price_rows = 0 if (up_room + down_room) < 64 else (1 if (up_room + down_room) < 120 else 2)
    expansion = {
        "up_px": up_room,
        "down_px": down_room,
        "left_px": left_room,
        "right_px": right_room,
        "allowed_directions": allowed,
        "maximum_safe_expansion": {
            "up_px": up_room,
            "down_px": down_room,
            "left_px": left_room,
            "right_px": right_room,
        },
        "blocked_by": list(blocked) + (["hero_visual"] if down_room == 0 else []),
        "internal_capacity": {
            "additional_price_rows": additional_price_rows,
            "down_px_before_hero": down_room,
            "up_px_before_copy": up_room,
            "note": (
                "Downward expansion stops before the hero photograph. "
                "Price-slot growth may use bounded upward expansion only if copy stays locked. "
                "1 occupied price slot → 3 still requires bounded local recomposition."
            ),
        },
    }
    # Unique blocked_by, preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for item in expansion["blocked_by"]:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    expansion["blocked_by"] = uniq
    return {
        "safe_bbox": safe,
        "safety_margin": {
            "requested_px": requested,
            "anti_alias_extent_px": {
                "left_px": int(aa.get("left_px") or 0),
                "up_px": int(aa.get("up_px") or 0),
                "right_px": int(aa.get("right_px") or 0),
                "down_px": int(aa.get("down_px") or 0),
            },
            "applied_px": applied,
            "clean_pad_px": CLEAN_PAD_PX,
            "unit": "px",
            "note": (
                f"{CLEAN_PAD_PX}px clean pad around visual bounds plus measured anti-alias. "
                "Downward pad is clamped so the mutable region never enters the hero."
            ),
        },
        "hero_boundary": {"y": hero_y0, "source": "photo_start"},
        "blocked_by": uniq,
        "expansion": expansion,
        "copy_floor_y": copy_floor,
    }


def commercial_pixel_coverage(
    image: Any,
    safe_bbox: dict[str, int],
    layout: dict[str, Any],
) -> dict[str, Any]:
    """Count commercial type pixels in the copy→hero band that sit outside the safe mask."""
    from PIL import Image as PILImage

    im = image.convert("RGB") if isinstance(image, PILImage.Image) else image
    px = im.load()
    photo_start = int(layout.get("photo_start") or im.size[1])
    sub = layout.get("subheadline_bbox")
    y0 = int(sub["y1"]) + 2 if sub else 0
    y1 = photo_start
    pad_x = int(im.size[0] * 0.06)
    outside = 0
    inside = 0
    for y in range(y0, y1):
        for x in range(pad_x, im.size[0] - pad_x):
            r, g, b = px[x, y]
            if not (_is_gold(r, g, b) or _is_white(r, g, b)):
                continue
            if safe_bbox["x0"] <= x < safe_bbox["x1"] and safe_bbox["y0"] <= y < safe_bbox["y1"]:
                inside += 1
            else:
                outside += 1
    return {
        "strict_inside_safe": inside,
        "strict_outside_safe": outside,
        "ghost_risk": outside > 0,
        "status": "pass" if outside == 0 else "fail",
        "band": {"x0": pad_x, "y0": y0, "x1": im.size[0] - pad_x, "y1": y1},
    }


def analyze_raster(image: Any) -> dict[str, Any]:
    """Band/column geometry from the finished raster. Not a rendering template."""
    from PIL import Image

    if not isinstance(image, Image.Image):
        raise TypeError("analyze_raster requires a PIL Image")
    im = image.convert("RGB")
    width, height = im.size
    px = im.load()
    x_mid0 = int(width * 0.18)
    x_mid1 = int(width * 0.82)

    photo_start = None
    run = 0
    candidate = None
    # Ignore thin ornament / serif antialias rows. The hero is a sustained photo band.
    for y in range(int(height * 0.22), int(height * 0.72)):
        frac = _row_fractions(px, y, width, x_mid0, x_mid1)
        if frac["photo"] > 0.50 and frac["navy"] < 0.18:
            if candidate is None:
                candidate = y
            run += 1
            if run >= 16:
                photo_start = candidate
                break
        else:
            run = 0
            candidate = None
    if photo_start is None:
        return {
            "canvas_width": width,
            "canvas_height": height,
            "confidence": 0.15,
            "reason": "photo_start_not_found",
            "photo_start": None,
        }

    navy_footer = height
    for y in range(int(height * 0.72), height):
        frac = _row_fractions(px, y, width, x_mid0, x_mid1)
        if frac["navy"] > 0.80 and frac["photo"] < 0.15:
            navy_footer = y
            break

    cta_rows = [
        y
        for y in range(max(photo_start, int(height * 0.70)), navy_footer)
        if _row_fractions(px, y, width, x_mid0, x_mid1)["gold"] > 0.28
    ]
    cta_bbox = None
    if cta_rows:
        cta_bbox = _type_bbox(
            px,
            int(width * 0.12),
            min(cta_rows) - 4,
            int(width * 0.88),
            min(max(cta_rows) + 8, navy_footer),
            gold=True,
            white=False,
        )

    logo_bbox = _type_bbox(
        px,
        int(width * 0.20),
        navy_footer,
        int(width * 0.80),
        height,
        gold=True,
        white=True,
    )

    plate_y1 = photo_start
    type_rows = []
    for y in range(0, plate_y1):
        frac = _row_fractions(px, y, width, x_mid0, x_mid1)
        type_rows.append((y, frac))

    def _runs(pred, min_len: int = 6) -> list[tuple[int, int]]:
        runs: list[tuple[int, int]] = []
        start = None
        for y, frac in type_rows:
            if pred(frac):
                if start is None:
                    start = y
            elif start is not None:
                if y - start >= min_len:
                    runs.append((start, y))
                start = None
        if start is not None and plate_y1 - start >= min_len:
            runs.append((start, plate_y1))
        return runs

    white_runs = _runs(lambda f: f["white"] > 0.06)
    gold_runs = _runs(lambda f: f["gold"] > 0.06)

    headline_white = white_runs[0] if white_runs else None
    headline_gold = None
    subhead_run = None
    if gold_runs:
        headline_gold = gold_runs[0]
        if headline_gold[1] - headline_gold[0] > 70:
            split = headline_gold[0] + int((headline_gold[1] - headline_gold[0]) * 0.62)
            subhead_run = (split, headline_gold[1])
            headline_gold = (headline_gold[0], split)
        elif len(gold_runs) > 1 and gold_runs[1][0] - headline_gold[1] < 48:
            subhead_run = gold_runs[1]

    after_copy = 0
    if subhead_run:
        after_copy = subhead_run[1]
    elif headline_gold:
        after_copy = headline_gold[1]
    elif headline_white:
        after_copy = headline_white[1]

    # Commercial group = remaining navy plate below copy, including internal
    # navy gaps between the 3-column lines. Do not take only the last type fragment.
    scan_from = after_copy + 8
    first_type = None
    for y, frac in type_rows:
        if y < scan_from:
            continue
        if frac["type"] > 0.02:
            first_type = y
            break
    if first_type is None:
        first_type = min(scan_from + 12, max(0, plate_y1 - 80))
    commercial_run = (first_type, max(first_type + 24, plate_y1 - 2))

    pad_x = int(width * 0.06)
    headline_bbox = None
    hy0 = headline_white[0] if headline_white else (headline_gold[0] if headline_gold else 40)
    hy1 = headline_gold[1] if headline_gold else (headline_white[1] if headline_white else 180)
    headline_bbox = _type_bbox(px, pad_x, max(0, hy0 - 6), width - pad_x, hy1 + 4)
    if headline_bbox is None and headline_white:
        headline_bbox = bbox_dict(pad_x, headline_white[0], width - pad_x, headline_white[1])

    subheadline_bbox = None
    if subhead_run:
        subheadline_bbox = _type_bbox(
            px, pad_x, subhead_run[0] - 2, width - pad_x, min(subhead_run[1] + 6, plate_y1)
        )

    commercial_bbox = None
    column_boxes: dict[str, dict[str, int] | None] = {
        "unit_label": None,
        "old_price": None,
        "discount": None,
    }
    column_layout = None
    if commercial_run:
        cy0 = commercial_run[0]
        cy1 = min(commercial_run[1] + 12, plate_y1 - 4)
        commercial_bbox = _type_bbox(px, pad_x, cy0, width - pad_x, cy1)
        if commercial_bbox is None:
            commercial_bbox = bbox_dict(pad_x, cy0, width - pad_x, cy1)
        cx0, cx1 = commercial_bbox["x0"], commercial_bbox["x1"]
        xs_active = []
        for x in range(cx0, cx1):
            hits = 0
            for y in range(cy0, cy1, 2):
                r, g, b = px[x, y]
                if _is_gold(r, g, b) or _is_white(r, g, b):
                    hits += 1
                    if hits >= 4:
                        xs_active.append(x)
                        break
        clusters = _cluster_xs(xs_active, gap=max(18, int(width * 0.03)))
        if len(clusters) >= 3:
            # Use the three heaviest clusters as L/C/R.
            ranked = sorted(clusters, key=lambda c: c[1] - c[0], reverse=True)[:3]
            ranked = sorted(ranked, key=lambda c: c[0])
            col_ranges = ranked
            column_confidence = 0.86
        else:
            span = max(1, cx1 - cx0)
            third = span / 3.0
            col_ranges = [
                (cx0, int(cx0 + third)),
                (int(cx0 + third), int(cx0 + 2 * third)),
                (int(cx0 + 2 * third), cx1),
            ]
            column_confidence = 0.72 if len(clusters) != 3 else 0.8

        roles = ("unit_label", "old_price", "discount")
        for role, (left, right) in zip(roles, col_ranges, strict=True):
            box = _type_bbox(px, left, cy0, max(left + 8, right), cy1)
            column_boxes[role] = box or bbox_dict(left, cy0, right, cy1)

        gaps = []
        for i in range(2):
            gaps.append(max(0, col_ranges[i + 1][0] - col_ranges[i][1]))
        column_layout = {
            "layout": "three_column_row",
            "columns": [
                {"role": "unit_label", "side": "left", "rank": 0, "x_range": [col_ranges[0][0], col_ranges[0][1]]},
                {"role": "old_price", "side": "center", "rank": 1, "x_range": [col_ranges[1][0], col_ranges[1][1]]},
                {"role": "discount", "side": "right", "rank": 2, "x_range": [col_ranges[2][0], col_ranges[2][1]]},
            ],
            "internal_spacing_px": {
                "left_to_center": gaps[0] if gaps else None,
                "center_to_right": gaps[1] if len(gaps) > 1 else None,
            },
            "confidence": column_confidence,
        }

    hero_bbox = bbox_dict(0, photo_start, width, navy_footer)
    plate_bbox = bbox_dict(0, 0, width, photo_start)

    confidences = {
        "photo_start": 0.92 if photo_start else 0.2,
        "headline": 0.84 if headline_bbox else 0.3,
        "subheadline": 0.70 if subheadline_bbox else 0.35,
        "commercial_group": 0.80 if commercial_bbox else 0.25,
        "columns": (column_layout or {}).get("confidence") or 0.3,
        "cta": 0.86 if cta_bbox else 0.4,
        "logo": 0.78 if logo_bbox else 0.4,
        "hero_visual": 0.93,
    }
    overall = round(sum(confidences.values()) / len(confidences), 3)

    return {
        "canvas_width": width,
        "canvas_height": height,
        "photo_start": photo_start,
        "navy_footer": navy_footer,
        "headline_bbox": headline_bbox,
        "subheadline_bbox": subheadline_bbox,
        "commercial_bbox": commercial_bbox,
        "column_boxes": column_boxes,
        "column_layout": column_layout,
        "hero_bbox": hero_bbox,
        "background_plate_bbox": plate_bbox,
        "cta_bbox": cta_bbox,
        "logo_bbox": logo_bbox,
        "confidence": overall,
        "confidence_by_region": confidences,
        "reason": None,
    }


def _region(
    *,
    region_id: str,
    role: str,
    bbox: dict[str, int] | None,
    occupied: bool,
    group_id: str | None,
    hierarchy_rank: int,
    confidence: float,
    typography: dict[str, Any] | None = None,
    background_context: str | None = None,
    spacing: dict[str, Any] | None = None,
    expansion: dict[str, Any] | None = None,
    mutable_for: list[str] | None = None,
    source_asset_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": region_id,
        "semantic_role": role,
        "bbox": bbox,
        "occupied": occupied,
        "group_id": group_id,
        "hierarchy_rank": hierarchy_rank,
        "typography": typography,
        "background_context": background_context,
        "spacing_relationships": spacing or {},
        "expansion": expansion or {
            "allowed_directions": [],
            "maximum_safe_expansion": {"up_px": 0, "down_px": 0, "left_px": 0, "right_px": 0},
            "blocked_by": [],
        },
        "mutable_for": list(mutable_for or []),
        "source_asset_id": source_asset_id,
        "confidence": round(float(confidence), 3),
        "rendered_pixels": bool(occupied and bbox),
    }
    if extra:
        payload.update(extra)
    return payload


def _gap(a: dict[str, int] | None, b: dict[str, int] | None, axis: str) -> int | None:
    if not a or not b:
        return None
    if axis == "below":
        return max(0, b["y0"] - a["y1"])
    if axis == "above":
        return max(0, a["y0"] - b["y1"])
    if axis == "right":
        return max(0, b["x0"] - a["x1"])
    if axis == "left":
        return max(0, a["x0"] - b["x1"])
    return None


def build_edit_map(
    layout: dict[str, Any],
    *,
    cover_asset_id: str,
    source_visual_asset_id: str,
    logo_asset_id: str,
    created_from: dict[str, Any] | None = None,
    occupied_price_slots: dict[str, bool] | None = None,
    image: Any = None,
) -> dict[str, Any]:
    """Attach semantic facts to raster geometry. Raster is visual truth."""
    width = int(layout["canvas_width"])
    height = int(layout["canvas_height"])
    conf = layout.get("confidence_by_region") or {}
    headline = layout.get("headline_bbox")
    subhead = layout.get("subheadline_bbox")
    commercial = layout.get("commercial_bbox")
    hero = layout.get("hero_bbox")
    plate = layout.get("background_plate_bbox")
    cta = layout.get("cta_bbox")
    logo = layout.get("logo_bbox")
    cols = layout.get("column_boxes") or {}
    unit = cols.get("unit_label")
    old_price = cols.get("old_price")
    discount = cols.get("discount")
    column_layout = layout.get("column_layout")
    slots = {
        "old_price": True,
        "new_price": False,
        "savings_price": False,
        **(occupied_price_slots or {}),
    }
    new_occ = bool(slots.get("new_price"))
    sav_occ = bool(slots.get("savings_price"))
    new_bbox = None
    sav_bbox = None
    if (new_occ or sav_occ) and (old_price or commercial):
        base = dict(old_price or commercial)
        h = max(1, base["y1"] - base["y0"])
        if new_occ and sav_occ:
            third = h / 3.0
            old_price = bbox_dict(base["x0"], base["y0"], base["x1"], int(base["y0"] + third))
            new_bbox = bbox_dict(
                base["x0"], int(base["y0"] + third), base["x1"], int(base["y0"] + 2 * third)
            )
            sav_bbox = bbox_dict(base["x0"], int(base["y0"] + 2 * third), base["x1"], base["y1"])
        elif new_occ:
            mid = (base["y0"] + base["y1"]) // 2
            old_price = bbox_dict(base["x0"], base["y0"], base["x1"], mid)
            new_bbox = bbox_dict(base["x0"], mid, base["x1"], base["y1"])
        if column_layout:
            column_layout = dict(column_layout)
            column_layout["layout"] = "restacked_price_hierarchy"
            column_layout["note"] = (
                "Price occupancy grew inside commercial_group. "
                "Bands are inferred from the center column, not a template."
            )

    gap_headline_commercial = _gap(headline, commercial, "below")
    gap_commercial_hero = _gap(commercial, hero, "below")
    gap_sub_commercial = _gap(subhead, commercial, "below")

    visual_info: dict[str, Any] = {}
    safe_info: dict[str, Any] = {}
    semantic_bbox = dict(commercial) if commercial else None
    visual_bbox = None
    if image is not None and commercial and hero:
        visual_info = measure_commercial_visual_bounds(image, layout)
        visual_bbox = visual_info.get("visual_bbox")
        safe_info = compute_safe_commercial_region(
            visual_bbox=visual_bbox,
            semantic_bbox=semantic_bbox,
            headline_bbox=headline,
            subheadline_bbox=subhead,
            hero_bbox=hero,
            canvas_width=width,
            canvas_height=height,
            anti_alias_extent=visual_info.get("anti_alias_extent"),
        )
        commercial = safe_info["safe_bbox"]
        gap_headline_commercial = _gap(headline, commercial, "below")
        gap_commercial_hero = _gap(commercial, hero, "below")
        gap_sub_commercial = _gap(subhead, commercial, "below")
        commercial_expansion = {
            "allowed_directions": list(safe_info["expansion"]["allowed_directions"]),
            "maximum_safe_expansion": dict(safe_info["expansion"]["maximum_safe_expansion"]),
            "blocked_by": list(safe_info["blocked_by"]),
            "internal_capacity": dict(safe_info["expansion"]["internal_capacity"]),
            "up_px": safe_info["expansion"]["up_px"],
            "down_px": safe_info["expansion"]["down_px"],
            "left_px": safe_info["expansion"]["left_px"],
            "right_px": safe_info["expansion"]["right_px"],
        }
    else:
        internal_down = 0
        if commercial and hero:
            internal_down = max(0, hero["y0"] - commercial["y1"])
        additional_price_rows = 0 if internal_down < 64 else (1 if internal_down < 120 else 2)
        commercial_expansion = {
            "allowed_directions": ["down_internal"] if internal_down else [],
            "maximum_safe_expansion": {
                "up_px": 0,
                "down_px": min(internal_down, 24),
                "left_px": 0,
                "right_px": 0,
            },
            "blocked_by": ["headline", "subheadline", "hero_visual", "canvas_left", "canvas_right"],
            "internal_capacity": {
                "additional_price_rows": additional_price_rows,
                "down_px_before_hero": internal_down,
                "note": (
                    "Center column is sized for label + one occupied price. "
                    "1 occupied price slot → 3 occupied price slots exceeds internal "
                    "capacity and requires bounded local recomposition of commercial_group."
                ),
            },
            "up_px": 0,
            "down_px": min(internal_down, 24) if commercial and hero else 0,
            "left_px": 0,
            "right_px": 0,
        }

    pixel_coverage = None
    if image is not None and commercial:
        pixel_coverage = commercial_pixel_coverage(image, commercial, layout)

    regions = [
        _region(
            region_id="background_plate",
            role="background_plate",
            bbox=plate,
            occupied=True,
            group_id=None,
            hierarchy_rank=0,
            confidence=conf.get("photo_start", 0.8),
            background_context="solid",
            extra={"color_class": "navy"},
        ),
        _region(
            region_id="hero_visual",
            role="hero_visual",
            bbox=hero,
            occupied=True,
            group_id=None,
            hierarchy_rank=1,
            confidence=conf.get("hero_visual", 0.9),
            background_context="photo",
            mutable_for=["VISUAL_REPLACE_ONLY"],
            source_asset_id=source_visual_asset_id,
            expansion={
                "allowed_directions": [],
                "maximum_safe_expansion": {"up_px": 0, "down_px": 0, "left_px": 0, "right_px": 0},
                "blocked_by": ["commercial_group", "cta", "logo", "canvas"],
            },
            spacing={"above": "commercial_group", "below": "cta", "approximate_gaps": {"above_px": gap_commercial_hero}},
        ),
        _region(
            region_id="headline",
            role="headline",
            bbox=headline,
            occupied=True,
            group_id="copy_group",
            hierarchy_rank=2,
            confidence=conf.get("headline", 0.7),
            typography={
                "family_class": "serif_display",
                "approximate_size": "large",
                "weight": "regular",
                "color": "white_and_gold",
                "alignment": "center",
                "tracking": None,
            },
            background_context="solid",
            mutable_for=[],
            spacing={"below": "subheadline", "approximate_gaps": {"below_px": _gap(headline, subhead, "below")}},
        ),
        _region(
            region_id="subheadline",
            role="subheadline",
            bbox=subhead,
            occupied=bool(subhead),
            group_id="copy_group",
            hierarchy_rank=3,
            confidence=conf.get("subheadline", 0.6),
            typography={
                "family_class": "sans_or_serif_small",
                "approximate_size": "small",
                "weight": "regular",
                "color": "gold",
                "alignment": "center",
                "tracking": None,
            },
            background_context="solid",
            spacing={"above": "headline", "below": "commercial_group", "approximate_gaps": {"below_px": gap_sub_commercial}},
        ),
        _region(
            region_id="supporting_copy",
            role="supporting_copy",
            bbox=subhead,
            occupied=bool(subhead),
            group_id="copy_group",
            hierarchy_rank=3,
            confidence=round(float(conf.get("subheadline", 0.6)) * 0.9, 3),
            typography={
                "family_class": "sans_or_serif_small",
                "approximate_size": "small",
                "weight": "regular",
                "color": "gold",
                "alignment": "center",
                "tracking": None,
            },
            background_context="solid",
            extra={"coincides_with": "subheadline", "note": "Same visual line as subheadline on this raster."},
        ),
        _region(
            region_id="commercial_group",
            role="commercial_group",
            bbox=commercial,
            occupied=True,
            group_id="commercial_group",
            hierarchy_rank=4,
            confidence=conf.get("commercial_group", 0.7),
            background_context="solid",
            mutable_for=["PRICE_EDIT_ONLY"],
            expansion=commercial_expansion,
            spacing={
                "above": "headline",
                "below": "hero_visual",
                "approximate_gaps": {
                    "above_px": gap_headline_commercial,
                    "below_px": gap_commercial_hero,
                },
            },
            extra={
                "children": ["unit_label", "old_price"]
                + (["new_price"] if new_occ else [])
                + (["savings_price"] if sav_occ else [])
                + ["discount"],
                "column_relationship": column_layout,
                "semantic_bbox": semantic_bbox,
                "visual_bbox": visual_bbox,
                "safe_bbox": commercial,
                "safety_margin": safe_info.get("safety_margin"),
                "hero_boundary": safe_info.get("hero_boundary")
                or ({"y": hero["y0"], "source": "photo_start"} if hero else None),
                "blocked_by": list(commercial_expansion.get("blocked_by") or []),
                "pixel_coverage": pixel_coverage,
                "blocked_boundaries": {
                    "above": "headline",
                    "below": "hero_visual",
                    "left": "canvas",
                    "right": "canvas",
                },
            },
        ),
        _region(
            region_id="unit_label",
            role="unit_label",
            bbox=unit,
            occupied=True,
            group_id="commercial_group",
            hierarchy_rank=5,
            confidence=conf.get("columns", 0.7),
            typography={
                "family_class": "sans_stat",
                "approximate_size": "large_over_small_caption",
                "weight": "regular",
                "color": "white_over_gold_caption",
                "alignment": "center",
                "tracking": None,
            },
            background_context="solid",
            mutable_for=["PRICE_EDIT_ONLY"],
            extra={"column": "left"},
        ),
        _region(
            region_id="old_price",
            role="old_price",
            bbox=old_price,
            occupied=True,
            group_id="commercial_group",
            hierarchy_rank=5,
            confidence=conf.get("columns", 0.7),
            typography={
                "family_class": "sans_stat",
                "approximate_size": "caption_over_large",
                "weight": "regular",
                "color": "gold_caption_over_white_price",
                "alignment": "center",
                "tracking": None,
            },
            background_context="solid",
            mutable_for=["PRICE_EDIT_ONLY"],
            extra={
                "column": "center",
                "note": "old_price is a column inside commercial_group, not an isolated text box.",
            },
        ),
        _region(
            region_id="discount",
            role="discount",
            bbox=discount,
            occupied=True,
            group_id="commercial_group",
            hierarchy_rank=5,
            confidence=conf.get("columns", 0.7),
            typography={
                "family_class": "sans_stat",
                "approximate_size": "caption_over_large",
                "weight": "regular",
                "color": "gold_caption_over_white_value",
                "alignment": "center",
                "tracking": None,
            },
            background_context="solid",
            mutable_for=["PRICE_EDIT_ONLY"],
            extra={"column": "right"},
        ),
        _region(
            region_id="new_price",
            role="new_price",
            bbox=new_bbox,
            occupied=new_occ,
            group_id="commercial_group",
            hierarchy_rank=6,
            confidence=0.62 if new_occ else 1.0,
            extra={
                "slot_kind": "occupied" if new_occ else "future",
                "column": "center",
                "note": (
                    "Launch price inferred inside commercial_group after bounded recomposition."
                    if new_occ
                    else "Not on this raster. Occupying this slot later requires bounded local recomposition."
                ),
            },
        ),
        _region(
            region_id="savings_price",
            role="savings_price",
            bbox=sav_bbox,
            occupied=sav_occ,
            group_id="commercial_group",
            hierarchy_rank=6,
            confidence=0.62 if sav_occ else 1.0,
            extra={
                "slot_kind": "occupied" if sav_occ else "future",
                "column": "center",
                "note": (
                    "Savings inferred inside commercial_group after bounded recomposition."
                    if sav_occ
                    else "Not on this raster. Occupying this slot later requires bounded local recomposition."
                ),
            },
        ),
        _region(
            region_id="cta",
            role="cta",
            bbox=cta,
            occupied=bool(cta),
            group_id=None,
            hierarchy_rank=7,
            confidence=conf.get("cta", 0.7),
            typography={
                "family_class": "sans_button",
                "approximate_size": "medium",
                "weight": "semibold",
                "color": "navy_on_gold",
                "alignment": "center",
                "tracking": "wide",
            },
            background_context="button",
            mutable_for=[],
        ),
        _region(
            region_id="logo",
            role="logo",
            bbox=logo,
            occupied=bool(logo),
            group_id=None,
            hierarchy_rank=8,
            confidence=conf.get("logo", 0.7),
            background_context="solid",
            mutable_for=["LOGO_EDIT_ONLY"],
            source_asset_id=logo_asset_id,
        ),
    ]

    groups = [
        {
            "id": "copy_group",
            "semantic_role": "copy_group",
            "children": ["headline", "subheadline", "supporting_copy"],
            "bbox": headline,
        },
        {
            "id": "commercial_group",
            "semantic_role": "commercial_group",
            "children": ["unit_label", "old_price"]
            + (["new_price"] if new_occ else [])
            + (["savings_price"] if sav_occ else [])
            + ["discount"],
            "future_children": [
                role
                for role, occ in (("new_price", new_occ), ("savings_price", sav_occ))
                if not occ
            ],
            "bbox": commercial,
            "semantic_bbox": semantic_bbox,
            "visual_bbox": visual_bbox,
            "safe_bbox": commercial,
            "safety_margin": safe_info.get("safety_margin"),
            "hero_boundary": safe_info.get("hero_boundary")
            or ({"y": hero["y0"], "source": "photo_start"} if hero else None),
            "blocked_by": list(commercial_expansion.get("blocked_by") or []),
            "pixel_coverage": pixel_coverage,
            "column_relationship": column_layout,
            "blocked_boundaries": {
                "above": "headline",
                "below": "hero_visual",
                "left": "canvas",
                "right": "canvas",
            },
            "expansion": commercial_expansion,
            "spacing_relationships": {
                "above": "headline",
                "below": "hero_visual",
                "approximate_gaps": {
                    "above_px": gap_headline_commercial,
                    "below_px": gap_commercial_hero,
                },
            },
        },
    ]

    preservation = build_preservation_map()
    overall = float(layout.get("confidence") or 0.0)
    map_id = str(uuid4())
    edit_map = {
        "id": map_id,
        "edit_map_version": EDIT_MAP_VERSION,
        "cover_asset_id": str(cover_asset_id),
        "canvas_width": width,
        "canvas_height": height,
        "source_visual_asset_id": str(source_visual_asset_id),
        "logo_asset_id": str(logo_asset_id),
        "created_from": {
            "method": "raster_band_analysis+visual_bounds",
            "provider": None,
            "provider_calls": 0,
            "semantic_facts": True,
            "design_spec_authoritative": False,
            "debug_overlay_role": "internal_evidence_only",
            **(created_from or {}),
        },
        "regions": regions,
        "groups": groups,
        "future_slots": {
            "old_price": {"occupied": True, "rendered_pixels": True},
            "new_price": {"occupied": new_occ, "rendered_pixels": new_occ},
            "savings_price": {"occupied": sav_occ, "rendered_pixels": sav_occ},
        },
        "immutable_mask_metadata": preservation,
        "confidence": overall,
        "confidence_by_region": conf,
        "validation_status": "pending",
        "validation": {},
    }
    return edit_map


def build_preservation_map() -> dict[str, Any]:
    """Intent → mutable/immutable regions. Not a whole-canvas unlock mask."""
    commercial = ["commercial_group", "unit_label", "old_price", "discount"]
    outside_price = [
        "hero_visual",
        "headline",
        "subheadline",
        "supporting_copy",
        "logo",
        "cta",
        "background_plate",
    ]
    return {
        "PRICE_EDIT_ONLY": {
            "mutable": list(commercial),
            "immutable": list(outside_price),
            "note": (
                "Only commercial_group.safe_bbox may change. "
                "Hero, headline, logo, CTA stay locked. Mutable mask must cover all "
                "original commercial pixels so ghosts cannot remain."
            ),
        },
        "VISUAL_REPLACE_ONLY": {
            "mutable": ["hero_visual"],
            "immutable": [
                "headline",
                "subheadline",
                "supporting_copy",
                "commercial_group",
                "unit_label",
                "old_price",
                "discount",
                "logo",
                "cta",
                "background_plate",
            ],
            "note": "Only the photographic hero may change. Commercial typography stays locked.",
        },
    }


def validate_edit_map(
    edit_map: dict[str, Any],
    *,
    expected_cover_asset_id: str | None = None,
    expected_source_visual_asset_id: str | None = None,
    expected_logo_asset_id: str | None = None,
    current_cover_asset_id: str | None = None,
) -> dict[str, Any]:
    """Fail closed on structural lies. Low confidence is not faked as precise."""
    failures: list[str] = []
    warnings: list[str] = []
    width = int(edit_map.get("canvas_width") or 0)
    height = int(edit_map.get("canvas_height") or 0)
    regions = {r["id"]: r for r in edit_map.get("regions") or [] if isinstance(r, dict)}
    groups = {g["id"]: g for g in edit_map.get("groups") or [] if isinstance(g, dict)}

    if expected_cover_asset_id and str(edit_map.get("cover_asset_id")) != str(expected_cover_asset_id):
        failures.append("cover_asset_id_mismatch")
    if current_cover_asset_id and str(edit_map.get("cover_asset_id")) != str(current_cover_asset_id):
        failures.append("edit_map_cover_is_not_current_cover")
    if expected_source_visual_asset_id and str(edit_map.get("source_visual_asset_id")) != str(
        expected_source_visual_asset_id
    ):
        failures.append("source_visual_asset_mismatch")
    if expected_logo_asset_id and str(edit_map.get("logo_asset_id")) != str(expected_logo_asset_id):
        failures.append("logo_asset_mismatch")

    for role in REQUIRED_OCCUPIED_ROLES:
        region = regions.get(role)
        if region is None:
            failures.append(f"missing_region:{role}")
            continue
        if not region.get("occupied"):
            failures.append(f"required_region_unoccupied:{role}")
        bbox = region.get("bbox")
        if not bbox:
            failures.append(f"required_region_missing_bbox:{role}")
        elif not bbox_inside_canvas(bbox, width, height):
            failures.append(f"bbox_outside_canvas:{role}")

    for role in FUTURE_PRICE_ROLES:
        region = regions.get(role)
        if region is None:
            failures.append(f"missing_future_slot:{role}")
            continue
        if region.get("occupied"):
            if not region.get("bbox"):
                failures.append(f"occupied_slot_missing_bbox:{role}")
            elif not bbox_inside_canvas(region["bbox"], width, height):
                failures.append(f"bbox_outside_canvas:{role}")
            continue
        if region.get("rendered_pixels"):
            failures.append(f"unoccupied_slot_has_rendered_pixels:{role}")
        if region.get("bbox"):
            failures.append(f"unoccupied_slot_has_pixel_bbox:{role}")

    commercial = regions.get("commercial_group")
    hero = regions.get("hero_visual")
    if commercial and hero and commercial.get("bbox") and hero.get("bbox"):
        overlap = bbox_iou(commercial["bbox"], hero["bbox"])
        if overlap > 0.0 or commercial["bbox"]["y1"] > hero["bbox"]["y0"]:
            failures.append("safe_bbox_invades_hero")
    headline = regions.get("headline")
    if commercial and headline and commercial.get("bbox") and headline.get("bbox"):
        if bbox_iou(commercial["bbox"], headline["bbox"]) > 0.02:
            failures.append("commercial_group_overlaps_headline")
    subhead = regions.get("subheadline")
    if commercial and subhead and commercial.get("bbox") and subhead.get("bbox"):
        if bbox_iou(commercial["bbox"], subhead["bbox"]) > 0.02:
            failures.append("commercial_group_overlaps_subheadline")
    coverage = (commercial or {}).get("pixel_coverage") or {}
    if coverage.get("ghost_risk") is True or coverage.get("strict_outside_safe"):
        failures.append("commercial_pixels_outside_safe_bbox")
    safe = (commercial or {}).get("safe_bbox")
    visual = (commercial or {}).get("visual_bbox")
    if safe and visual:
        if not bbox_contains(safe, visual, slack=0):
            failures.append("visual_bbox_not_inside_safe_bbox")
    if hero and safe and safe["y1"] > hero["bbox"]["y0"]:
        failures.append("safe_bbox_invades_hero")

    group = groups.get("commercial_group")
    if group is None:
        failures.append("missing_commercial_group")
    else:
        children = list(group.get("children") or [])
        for role in COMMERCIAL_CHILD_ROLES:
            if role not in children:
                failures.append(f"commercial_group_missing_child:{role}")
            child = regions.get(role)
            if child and commercial and child.get("bbox") and commercial.get("bbox"):
                if not bbox_contains(commercial["bbox"], child["bbox"], slack=16):
                    failures.append(f"child_outside_commercial_group:{role}")

    logo = regions.get("logo")
    cta = regions.get("cta")
    if logo and cta and logo.get("bbox") and cta.get("bbox"):
        if bbox_iou(logo["bbox"], cta["bbox"]) > 0.4:
            failures.append("logo_not_separate_from_cta")

    cols = (group or {}).get("column_relationship") or {}
    if cols.get("layout") != "three_column_row":
        warnings.append("commercial_group_column_relationship_weak")

    overall = float(edit_map.get("confidence") or 0.0)
    status = "pass"
    if failures:
        status = "fail"
    elif overall < MIN_MAP_CONFIDENCE:
        status = "insufficient_confidence"
        warnings.append("confidence_below_threshold")

    result = {
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "confidence": overall,
    }
    edit_map["validation"] = result
    edit_map["validation_status"] = status
    return result


def resolve_current_cover_asset_id(
    ctx: dict[str, Any],
    *,
    fallback: UUID | str | None = None,
) -> UUID:
    """Visual source of truth = current approved cover, never v1 master unless it is current."""
    mc = _as_dict(ctx.get("master_creative"))
    for raw in (
        mc.get("current_cover_asset_id"),
        ctx.get("current_cover_asset_id"),
        ctx.get("finished_ad_raster_asset_id"),
        ctx.get("latest_master_ad_asset_id"),
        fallback,
    ):
        if raw:
            return UUID(str(raw))
    raise ValueError("current_cover_asset_id cannot be resolved")


def stamp_current_cover(
    ctx: dict[str, Any],
    cover_asset_id: UUID | str,
    *,
    edit_map_id: str | None = None,
) -> dict[str, Any]:
    cover = str(cover_asset_id)
    ctx["current_cover_asset_id"] = cover
    mc = _as_dict(ctx.get("master_creative"))
    mc["current_cover_asset_id"] = cover
    if edit_map_id:
        mc["current_edit_map_id"] = str(edit_map_id)
        ctx["current_edit_map_id"] = str(edit_map_id)
    ctx["master_creative"] = mc
    return ctx


def load_edit_map(
    ctx: dict[str, Any],
    *,
    cover_asset_id: UUID | str | None = None,
    map_id: str | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Load the Edit Map bound to the current cover. Never reuse another cover's map."""
    maps = _as_dict(ctx.get("edit_maps"))
    mid = map_id or ctx.get("current_edit_map_id")
    mc = _as_dict(ctx.get("master_creative"))
    if not mid:
        mid = mc.get("current_edit_map_id")
    if not mid and cover_asset_id:
        mid = _as_dict(ctx.get("edit_maps_by_cover")).get(str(cover_asset_id))
    if not mid:
        return None, None
    edit_map = maps.get(str(mid))
    if not isinstance(edit_map, dict):
        return str(mid), None
    if cover_asset_id and str(edit_map.get("cover_asset_id")) != str(cover_asset_id):
        return str(mid), None
    return str(mid), edit_map


def persist_edit_map(ctx: dict[str, Any], edit_map: dict[str, Any]) -> dict[str, Any]:
    map_id = str(edit_map["id"])
    cover = str(edit_map["cover_asset_id"])
    maps = _as_dict(ctx.get("edit_maps"))
    maps[map_id] = edit_map
    by_cover = _as_dict(ctx.get("edit_maps_by_cover"))
    by_cover[cover] = map_id
    ctx["edit_maps"] = maps
    ctx["edit_maps_by_cover"] = by_cover
    stamp_current_cover(ctx, cover, edit_map_id=map_id)
    return ctx


def rebind_edit_map_for_cover(ctx: dict[str, Any], cover_asset_id: UUID | str) -> str | None:
    cover = str(cover_asset_id)
    by_cover = _as_dict(ctx.get("edit_maps_by_cover"))
    map_id = by_cover.get(cover)
    stamp_current_cover(ctx, cover, edit_map_id=str(map_id) if map_id else None)
    if not map_id:
        mc = _as_dict(ctx.get("master_creative"))
        mc["current_edit_map_id"] = None
        ctx["current_edit_map_id"] = None
        ctx["master_creative"] = mc
    return str(map_id) if map_id else None


def _read_cover_bytes(db: Session, asset_id: UUID) -> bytes:
    from investhome_api.services.creative_studio_media_service import (
        get_asset_or_404,
        open_asset_content,
    )

    asset = get_asset_or_404(asset_id, db)
    stream, _media = open_asset_content(asset)
    try:
        return stream.read()
    finally:
        try:
            stream.close()
        except Exception:
            pass


def build_edit_map_from_raster_bytes(
    raster_bytes: bytes,
    *,
    cover_asset_id: str,
    source_visual_asset_id: str,
    logo_asset_id: str,
    created_from: dict[str, Any] | None = None,
    occupied_price_slots: dict[str, bool] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from PIL import Image
    import io

    image = Image.open(io.BytesIO(raster_bytes)).convert("RGB")
    layout = analyze_raster(image)
    edit_map = build_edit_map(
        layout,
        cover_asset_id=cover_asset_id,
        source_visual_asset_id=source_visual_asset_id,
        logo_asset_id=logo_asset_id,
        created_from=created_from,
        occupied_price_slots=occupied_price_slots,
        image=image,
    )
    return edit_map, layout


def attach_edit_map_for_cover(
    db: Session,
    ctx: dict[str, Any],
    *,
    cover_asset_id: UUID | str,
    source_visual_asset_id: UUID | str,
    logo_asset_id: UUID | str,
    occupied_price_slots: dict[str, bool] | None = None,
) -> dict[str, Any] | None:
    """Generate + validate + persist. Fail-soft: never block generate/revise."""
    cover = UUID(str(cover_asset_id))
    try:
        raster = _read_cover_bytes(db, cover)
        edit_map, _layout = build_edit_map_from_raster_bytes(
            raster,
            cover_asset_id=str(cover),
            source_visual_asset_id=str(source_visual_asset_id),
            logo_asset_id=str(logo_asset_id),
            occupied_price_slots=occupied_price_slots,
        )
        validate_edit_map(
            edit_map,
            expected_cover_asset_id=str(cover),
            expected_source_visual_asset_id=str(source_visual_asset_id),
            expected_logo_asset_id=str(logo_asset_id),
            current_cover_asset_id=str(cover),
        )
        persist_edit_map(ctx, edit_map)
        return edit_map
    except Exception as exc:
        logger.warning("edit_map_attach_failed cover=%s: %s", cover, exc)
        stamp_current_cover(ctx, cover)
        return None


def render_debug_overlay(image: Any, edit_map: dict[str, Any]) -> Any:
    """Internal evidence only. Must never become the user-facing creative."""
    from PIL import ImageDraw, ImageFont

    im = image.convert("RGBA")
    overlay = im.copy()
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    colors = {
        "hero_visual": (0, 200, 255, 255),
        "headline": (255, 255, 255, 255),
        "subheadline": (180, 180, 180, 255),
        "supporting_copy": (160, 160, 200, 255),
        "commercial_group": (255, 200, 40, 255),
        "unit_label": (80, 220, 120, 255),
        "old_price": (255, 80, 80, 255),
        "new_price": (255, 120, 160, 255),
        "savings_price": (255, 160, 80, 255),
        "discount": (255, 140, 40, 255),
        "cta": (220, 80, 255, 255),
        "logo": (120, 255, 80, 255),
        "background_plate": (80, 120, 255, 255),
    }
    for region in edit_map.get("regions") or []:
        if not region.get("occupied") or not region.get("bbox"):
            continue
        role = region.get("semantic_role")
        box = region["bbox"]
        color = colors.get(role, (255, 255, 0, 255))
        width = 5 if role == "commercial_group" else (4 if role == "hero_visual" else 2)
        draw.rectangle(
            [box["x0"], box["y0"], box["x1"] - 1, box["y1"] - 1],
            outline=color,
            width=width,
        )
        label = f"{role} {'{:.2f}'.format(float(region.get('confidence') or 0))}"
        ty = max(0, box["y0"] - 12)
        if font:
            draw.text((box["x0"] + 4, ty), label, fill=color, font=font)
        else:
            draw.text((box["x0"] + 4, ty), label, fill=color)
    return overlay.convert("RGB")


def render_geometry_debug(image: Any, edit_map: dict[str, Any]) -> Any:
    """Internal QA: semantic / visual / safe commercial boxes + hero boundary."""
    from PIL import ImageDraw, ImageFont

    im = image.convert("RGB")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    commercial = next(
        (
            r
            for r in (edit_map.get("regions") or [])
            if isinstance(r, dict) and r.get("semantic_role") == "commercial_group"
        ),
        {},
    )
    hero = next(
        (
            r
            for r in (edit_map.get("regions") or [])
            if isinstance(r, dict) and r.get("semantic_role") == "hero_visual"
        ),
        {},
    )

    def _box(item: dict[str, Any] | None, color: tuple[int, int, int], width: int, label: str) -> None:
        if not item:
            return
        draw.rectangle(
            [item["x0"], item["y0"], item["x1"] - 1, item["y1"] - 1],
            outline=color,
            width=width,
        )
        ty = max(0, item["y0"] - 12)
        if font:
            draw.text((item["x0"] + 4, ty), label, fill=color, font=font)
        else:
            draw.text((item["x0"] + 4, ty), label, fill=color)

    _box(commercial.get("semantic_bbox"), (255, 80, 220), 2, "semantic")
    _box(commercial.get("visual_bbox"), (80, 255, 80), 3, "visual")
    _box(commercial.get("safe_bbox") or commercial.get("bbox"), (255, 200, 40), 5, "safe")
    hero_y = None
    boundary = commercial.get("hero_boundary")
    if isinstance(boundary, dict):
        hero_y = boundary.get("y")
    if hero_y is None and hero.get("bbox"):
        hero_y = hero["bbox"]["y0"]
    if hero_y is not None:
        y = int(hero_y)
        draw.line([(0, y), (im.size[0] - 1, y)], fill=(255, 40, 40), width=3)
        if font:
            draw.text((8, max(0, y - 14)), f"hero boundary y={y}", fill=(255, 40, 40), font=font)
        else:
            draw.text((8, max(0, y - 14)), f"hero boundary y={y}", fill=(255, 40, 40))
    return im
