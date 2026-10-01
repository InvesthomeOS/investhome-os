"""CreativeCanvasBalanceV2 — negative space vs dead space."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

ROLES = (
    "ARCHITECTURE_PROTECTION",
    "VISUAL_PAUSE",
    "HIERARCHY_SUPPORT",
    "BRAND_BREATHING",
    "READING_FLOW",
    "CROP_BALANCE",
)


def _cov(mask: Image.Image, box: tuple[int, int, int, int], threshold: int = 80) -> float:
    crop = mask.crop(box)
    hist = crop.histogram()
    total = max(1, sum(hist))
    return sum(hist[threshold:]) / total


def creative_canvas_balance_v2(
    image: Image.Image,
    objects: dict[str, Any],
    field_mask: Image.Image | None,
    occupancy: dict[str, Any],
    groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    w, h = image.size
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    sky = (occupancy.get("layers") or {}).get("sky")
    type_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(type_mask)
    for item in objects.values():
        bounds = item.get("bounds") if isinstance(item, dict) else None
        if not isinstance(bounds, dict):
            continue
        x0 = int(float(bounds.get("x") or 0) * w)
        y0 = int(float(bounds.get("y") or 0) * h)
        x1 = int((float(bounds.get("x") or 0) + float(bounds.get("w") or 0)) * w)
        y1 = int((float(bounds.get("y") or 0) + float(bounds.get("h") or 0)) * h)
        draw.rectangle((x0, y0, x1, y1), fill=255)
    field = field_mask.convert("L").resize((w, h)) if isinstance(field_mask, Image.Image) else Image.new("L", (w, h), 0)
    hard_im = hard.convert("L") if isinstance(hard, Image.Image) else Image.new("L", (w, h), 0)
    sky_im = sky.convert("L") if isinstance(sky, Image.Image) else Image.new("L", (w, h), 0)
    regions = []
    dead = 0
    cols, rows = 2, 3
    for gy in range(rows):
        for gx in range(cols):
            box = (int(gx * w / cols), int(gy * h / rows), int((gx + 1) * w / cols), int((gy + 1) * h / rows))
            t, f, a, s = _cov(type_mask, box), _cov(field, box, 40), _cov(hard_im, box), _cov(sky_im, box, 40)
            if a > 0.18 and t < 0.04:
                role = "ARCHITECTURE_PROTECTION"
            elif t > 0.02 and f > 0.12:
                role = "HIERARCHY_SUPPORT"
            elif t < 0.015 and f > 0.2 and a < 0.08:
                role = "VISUAL_PAUSE"
            elif t < 0.02 and s > 0.25 and a < 0.12:
                role = "CROP_BALANCE"
            elif t > 0.008 and t < 0.04:
                role = "READING_FLOW"
            elif t < 0.008 and f < 0.08 and a < 0.10 and s < 0.12:
                role = "DEAD_SPACE"
                dead += 1
            else:
                role = "BRAND_BREATHING" if t < 0.03 else "HIERARCHY_SUPPORT"
            regions.append({"gx": gx, "gy": gy, "type": round(t, 3), "field": round(f, 3), "architecture": round(a, 3), "sky": round(s, 3), "space_role": role})
    group_span = 0.0
    if groups:
        boxes = [g.get("group_bbox") or {} for g in groups]
        if boxes:
            group_span = max((float(b.get("x") or 0) + float(b.get("w") or 0) for b in boxes), default=0) - min((float(b.get("x") or 0) for b in boxes), default=0)
    return {
        "schema": "CreativeCanvasBalanceV2",
        "regions": regions,
        "dead_space_count": dead,
        "dead_space_score": min(10.0, dead * 2.0),
        "negative_space_has_role": all(r["space_role"] != "DEAD_SPACE" or False for r in regions if r["type"] < 0.008),
        "pass": dead <= 1,
        "group_span": round(group_span, 4),
        "roles": list(ROLES),
    }
