"""ContiguousContentFitTestV1 — can this exact campaign composition fit?

A fat bounding box is not a usable field. Architecture-clear contiguous
geometry is the only packing surface. The surface must also be the family's
own field, not an accidental sliver elsewhere on the canvas.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from investhome_api.services.creative_director.commercial_offer_composer import measure_production_copy
from investhome_api.services.creative_director.photo_family_eligibility import (
    DENSITY_RANK,
    IDENTITY_SCALE_MIN,
    family_compatibility_rules,
    lockup_requirement,
)


def family_search_window(family_id: str) -> dict[str, Any]:
    rules = family_compatibility_rules()["families"].get(family_id) or {}
    if family_id == "MINIMAL_TOP_FIELD":
        return {
            "x0": 0.0,
            "y0": 0.0,
            "x1": 1.0,
            "y1": 0.46,
            "touch": "top",
            "min_w": rules.get("min_contiguous_width", 0.62),
            "min_h": rules.get("min_contiguous_height", 0.28),
        }
    if family_id == "SKY_EDITORIAL":
        return {
            "x0": 0.0,
            "y0": 0.0,
            "x1": 1.0,
            "y1": 0.52,
            "touch": "top",
            "min_w": rules.get("min_contiguous_width", 0.26),
            "min_h": rules.get("min_contiguous_height", 0.32),
        }
    if family_id == "EDITORIAL_DARK_FIELD":
        return {
            "x0": 0.0,
            "y0": 0.0,
            "x1": 1.0,
            "y1": 1.0,
            "touch": "side",
            "min_w": rules.get("min_contiguous_width", 0.28),
            "min_h": rules.get("min_contiguous_height", 0.36),
        }
    return {
        "x0": 0.0,
        "y0": 0.0,
        "x1": 1.0,
        "y1": 1.0,
        "touch": "any",
        "min_w": rules.get("min_contiguous_width", 0.30),
        "min_h": rules.get("min_contiguous_height", 0.34),
    }


def _touches(rect: dict[str, Any], mode: str | None) -> bool:
    if mode in (None, "any"):
        return True
    x = float(rect.get("x") or 0)
    y = float(rect.get("y") or 0)
    w = float(rect.get("w") or 0)
    if mode == "top":
        return y <= 0.04
    if mode == "bottom":
        return (y + float(rect.get("h") or 0)) >= 0.96
    if mode == "side":
        return x <= 0.04 or (x + w) >= 0.96
    return True


def largest_safe_rect(
    occupancy: dict[str, Any],
    *,
    grid: tuple[int, int] = (54, 68),
    window: dict[str, Any] | None = None,
    must_touch: str | None = None,
) -> dict[str, Any]:
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    size = occupancy.get("size") or [1088, 1360]
    w, h = int(size[0]), int(size[1])
    gw, gh = grid
    if isinstance(hard, Image.Image):
        small = hard.convert("L").resize((gw, gh), Image.Resampling.BOX)
    else:
        small = Image.new("L", (gw, gh), 0)
    px = small.load()
    win = window or {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0}
    x0 = int(float(win.get("x0") or 0) * gw)
    x1 = max(x0 + 1, int(float(win.get("x1") or 1) * gw))
    y0 = int(float(win.get("y0") or 0) * gh)
    y1 = max(y0 + 1, int(float(win.get("y1") or 1) * gh))
    safe = [[False] * gw for _ in range(gh)]
    for y in range(gh):
        for x in range(gw):
            if x0 <= x < x1 and y0 <= y < y1 and int(px[x, y]) < 88:
                safe[y][x] = True
    heights = [0] * gw
    best = {"area": 0.0, "x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0, "cells": 0}
    for y in range(gh):
        for x in range(gw):
            heights[x] = heights[x] + 1 if safe[y][x] else 0
        stack: list[int] = []
        for i in range(gw + 1):
            cur = heights[i] if i < gw else 0
            while stack and heights[stack[-1]] > cur:
                hh = heights[stack.pop()]
                left = stack[-1] + 1 if stack else 0
                width = i - left
                cells = hh * width
                candidate = {
                    "area": round(cells / float(gw * gh), 4),
                    "x": round(left / gw, 4),
                    "y": round((y - hh + 1) / gh, 4),
                    "w": round(width / gw, 4),
                    "h": round(hh / gh, 4),
                    "cells": cells,
                }
                if cells > best["cells"] and _touches(candidate, must_touch):
                    best = candidate
            stack.append(i)
    best["schema"] = "ArchitectureClearRectV1"
    best["canvas"] = [w, h]
    best["window"] = {k: win.get(k) for k in ("x0", "y0", "x1", "y1")}
    best["must_touch"] = must_touch
    best.pop("cells", None)
    return best


def family_safe_rect(occupancy: dict[str, Any], family: dict[str, Any]) -> dict[str, Any]:
    family_id = str(family.get("family_id") or "")
    spec = family_search_window(family_id)
    rect = largest_safe_rect(occupancy, window=spec, must_touch=str(spec.get("touch") or "any"))
    rect["family_id"] = family_id
    rect["min_w"] = spec.get("min_w")
    rect["min_h"] = spec.get("min_h")
    return rect


def contiguous_content_fit(
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    safe: dict[str, Any] | None = None,
    canvas: tuple[int, int] = (1088, 1360),
    scale: float | None = None,
) -> dict[str, Any]:
    family_id = str(family.get("family_id") or "")
    if family_id == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN":
        from investhome_api.services.creative_director.full_frame_architectural_family import multi_zone_contiguous_fit

        return multi_zone_contiguous_fit(
            occupancy=occupancy, family=family, fonts=fonts, canvas=canvas, scale=scale
        )
    rules = family_compatibility_rules()["families"].get(family_id) or {}
    safe = safe or family_safe_rect(occupancy, family)
    scale_min = float((family.get("flexibility") or {}).get("scale_min") or IDENTITY_SCALE_MIN.get(family_id, 0.78))
    eval_scale = float(scale_min if scale is None else scale)
    metrics = measure_production_copy(fonts=fonts, family=family, canvas=canvas, scale=eval_scale)
    req = lockup_requirement(metrics, family, canvas)
    sw, sh = float(safe.get("w") or 0), float(safe.get("h") or 0)
    need_w, need_h = float(req["width"]), float(req["height"])
    min_w = float(rules.get("min_contiguous_width") or safe.get("min_w") or 0)
    min_h = float(rules.get("min_contiguous_height") or safe.get("min_h") or 0)
    width_ok = sw >= need_w * 0.98
    height_ok = sh >= need_h * 0.98
    identity_ok = (min_w <= 0 or sw >= min_w * 0.98) and (min_h <= 0 or sh >= min_h * 0.98)
    near = sw >= need_w * 0.85 and sh >= need_h * 0.85 and sw >= min_w * 0.85 and sh >= min_h * 0.85
    if width_ok and height_ok and identity_ok:
        status = "FIT"
    elif near and bool(rules.get("allows_created_navy_field")) and identity_ok:
        status = "CONDITIONAL_FIT"
    else:
        status = "NO_FIT"
    return {
        "schema": "ContiguousContentFitTestV1",
        "family_id": family_id,
        "status": status,
        "safe_rect": {k: safe.get(k) for k in ("x", "y", "w", "h", "area")},
        "required_lockup": req,
        "family_min_field": {"w": min_w, "h": min_h},
        "identity_ok": identity_ok,
        "scale_evaluated": eval_scale,
        "identity_scale_min": scale_min,
        "width_ok": width_ok,
        "height_ok": height_ok,
        "note": "Packs the actual campaign lockup into the family-zone architecture-clear rectangle, not a fat plane bbox or an accidental sliver.",
        "reason": (
            f"safe {sw:.3f}x{sh:.3f} vs lockup {need_w:.3f}x{need_h:.3f} family-min {min_w:.2f}x{min_h:.2f} at scale {eval_scale}"
        ),
    }


def evaluate_family_eligibility_v2(
    *,
    photo: Image.Image,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    composition: dict[str, Any] | None = None,
    density: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from investhome_api.services.creative_director.photo_family_eligibility import (
        campaign_density_profile,
        classify_photo_composition,
        evaluate_family_eligibility,
    )

    composition = composition or classify_photo_composition(photo, occupancy)
    density = density or campaign_density_profile(
        fonts=fonts, family=family, canvas=tuple(occupancy.get("size") or (1088, 1360))
    )
    v1 = evaluate_family_eligibility(
        photo=photo,
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        composition=composition,
        density=density,
    )
    safe = family_safe_rect(occupancy, family)
    fit = contiguous_content_fit(occupancy=occupancy, family=family, fonts=fonts, safe=safe)
    family_max = str(
        family_compatibility_rules()["families"].get(str(family.get("family_id") or ""), {}).get("max_campaign_density")
        or "HIGH"
    )
    density_ok = DENSITY_RANK.get(str(density.get("level") or "HIGH"), 3) <= DENSITY_RANK.get(family_max, 3)
    if fit["status"] == "FIT" and density_ok and v1.get("checks", {}).get("family_identity", {}).get("pass", True):
        status = "ELIGIBLE"
        fit_label = "FIT"
    elif fit["status"] == "CONDITIONAL_FIT" and density_ok:
        status = "CONDITIONALLY_ELIGIBLE"
        fit_label = "CONDITIONAL_FIT"
    else:
        status = "NOT_ELIGIBLE"
        fit_label = "NO_FIT"
    reasons = list(v1.get("reasons") or [])
    reasons.insert(0, fit["reason"])
    return {
        "schema": "FamilyEligibilityResultV2",
        "family_id": family.get("family_id"),
        "status": status,
        "contiguous_fit": fit_label,
        "fit": fit,
        "safe_rect": safe,
        "v1_status": v1.get("status"),
        "v1_false_positive": v1.get("status") == "ELIGIBLE" and fit["status"] == "NO_FIT",
        "density_ok": density_ok,
        "primary_reason": reasons[0] if reasons else fit["reason"],
        "reasons": reasons,
        "checks": v1.get("checks"),
        "required_lockup": fit.get("required_lockup"),
    }
