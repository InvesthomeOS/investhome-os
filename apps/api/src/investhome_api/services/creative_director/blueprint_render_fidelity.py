"""BlueprintRenderFidelityV1, ReferenceCraftGapV1, critic calibration."""

from __future__ import annotations

from typing import Any

MAJOR_FAULTS = (
    "SCATTERED_ELEMENT_LAYOUT",
    "CORNER_DISTRIBUTION",
    "FLOATING_LOGO",
    "ISOLATED_PRICE",
    "ISOLATED_DISCOUNT",
    "DETACHED_CTA",
    "CAPTION_ROW_LAYOUT",
    "PHOTO_WITH_TEXT_OVERLAY",
    "COMMERCIAL_ISLANDS",
    "FALSE_WHOLE_CANVAS_USAGE",
)

CAPPED = ("professional_art_direction", "whole_canvas_composition", "image_design_integration")


def _c(objects: dict[str, Any], role: str) -> tuple[float, float] | None:
    box = (objects.get(role) or {}).get("bounds")
    if not isinstance(box, dict) or not box:
        return None
    return float(box["x"]) + float(box["w"]) / 2, float(box["y"]) + float(box["h"]) / 2


def _dist(a: tuple[float, float] | None, b: tuple[float, float] | None) -> float:
    if a is None or b is None:
        return 1.0
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _corner(pt: tuple[float, float] | None) -> str | None:
    if pt is None:
        return None
    x, y = pt
    if x < 0.22 and y < 0.22:
        return "tl"
    if x > 0.78 and y < 0.22:
        return "tr"
    if x < 0.22 and y > 0.78:
        return "bl"
    if x > 0.78 and y > 0.78:
        return "br"
    return None


def detect_layout_faults(objects: dict[str, Any], *, field_mass: float = 0.2, islands: bool = False) -> list[str]:
    faults: list[str] = []
    h = _c(objects, "headline")
    d = _c(objects, "discount")
    p = _c(objects, "price")
    logo = _c(objects, "project_logo")
    cta = _c(objects, "cta")
    unit = _c(objects, "unit_type")
    commercial = [pt for pt in (h, d, p, cta) if pt]
    quads = set()
    for pt in commercial:
        qx = 0 if pt[0] < 0.5 else 1
        qy = 0 if pt[1] < 0.5 else 1
        quads.add((qx, qy))
    if len(quads) >= 3:
        faults.append("SCATTERED_ELEMENT_LAYOUT")
    corners = {_corner(pt) for pt in (h, d, p, cta, logo) if _corner(pt)}
    if len(corners) >= 3:
        faults.append("CORNER_DISTRIBUTION")
    others = [pt for pt in (h, d, p, cta, unit) if pt]
    if logo and others and min(_dist(logo, o) for o in others) > 0.22:
        faults.append("FLOATING_LOGO")
    if p and _dist(p, d) > 0.22 and _dist(p, h) > 0.22:
        faults.append("ISOLATED_PRICE")
    if d and _dist(d, p) > 0.25 and _dist(d, h) > 0.25:
        faults.append("ISOLATED_DISCOUNT")
    offer = d or p
    if cta and offer and _dist(cta, offer) > 0.28 and _dist(cta, p) > 0.28:
        faults.append("DETACHED_CTA")
    row = [pt for pt in (d, p, unit, cta) if pt]
    if len(row) >= 3 and all(pt[1] > 0.72 for pt in row):
        ys = [pt[1] for pt in row]
        if max(ys) - min(ys) < 0.08:
            faults.append("CAPTION_ROW_LAYOUT")
    if field_mass < 0.08:
        faults.append("PHOTO_WITH_TEXT_OVERLAY")
    if islands or (p and d and _dist(p, d) > 0.38):
        faults.append("COMMERCIAL_ISLANDS")
    if "SCATTERED_ELEMENT_LAYOUT" in faults or "CORNER_DISTRIBUTION" in faults:
        faults.append("FALSE_WHOLE_CANVAS_USAGE")
    return list(dict.fromkeys(faults))


def apply_critic_calibration(scores: dict[str, Any], faults: list[str]) -> dict[str, Any]:
    out = dict(scores)
    out["layout_faults"] = list(faults)
    out["schema"] = "CriticCalibrationV1"
    if any(f in MAJOR_FAULTS for f in faults):
        for key in CAPPED:
            if float(out.get(key) or 0) > 7:
                out[key] = 7
        out["calibration_capped"] = True
    else:
        out["calibration_capped"] = False
    return out


def _clip(v: float) -> int:
    return max(0, min(10, int(round(v))))


def blueprint_render_fidelity(
    objects: dict[str, Any],
    groups: list[dict[str, Any]],
    flow: dict[str, Any],
    *,
    field_mass: float,
    intended_mode: str,
) -> dict[str, Any]:
    h = _c(objects, "headline")
    d = _c(objects, "discount")
    p = _c(objects, "price")
    logo = _c(objects, "project_logo")
    cta = _c(objects, "cta")
    cohesion = 10.0
    for group in groups:
        children = group.get("children") or []
        pts = [_c(objects, c) for c in children]
        pts = [pt for pt in pts if pt]
        if len(pts) >= 2:
            span = max(_dist(a, b) for a in pts for b in pts)
            if span > 0.12:
                cohesion -= 3
            elif span > 0.08:
                cohesion -= 1
    offer_span = _dist(d, p)
    commercial = 10.0 if offer_span <= 0.12 else 4.0
    brand = 10.0 if logo and (h or p) and min(_dist(logo, h or p), _dist(logo, p or h)) <= 0.22 else 4.0
    flow_s = 3.0 if flow.get("commercial_islands") or flow.get("rejected") else 9.0
    type_s = 9.0 if h and d and h[1] <= d[1] + 0.02 else 6.0
    field_s = 9.0 if field_mass >= 0.08 else 4.0
    mass = 9.0 if not (h and d and abs(h[0] - d[0]) > 0.55) else 4.0
    hierarchy = 9.0 if h and d and p and h[1] <= d[1] <= (cta[1] if cta else 1) else 5.0
    negative = 8.0 if intended_mode else 6.0
    whole = min(cohesion, commercial, brand, flow_s, mass)
    scores = {
        "group_relationship_fidelity": _clip(cohesion),
        "visual_mass_fidelity": _clip(mass),
        "hierarchy_fidelity": _clip(hierarchy),
        "reading_flow_fidelity": _clip(flow_s),
        "typography_fidelity": _clip(type_s),
        "commercial_lockup_fidelity": _clip(commercial),
        "brand_relationship_fidelity": _clip(brand),
        "graphic_field_fidelity": _clip(field_s),
        "negative_space_fidelity": _clip(negative),
        "whole_canvas_fidelity": _clip(whole),
    }
    return {
        "schema": "BlueprintRenderFidelityV1",
        "scores": scores,
        "pass": all(v >= 8 for v in scores.values()),
        "mode": intended_mode,
    }


def reference_craft_gap(ref_maps: list[dict[str, Any]], render_map: dict[str, Any]) -> dict[str, float]:
    def mean(key: str) -> float:
        vals = [float(m.get(key) or 0) for m in ref_maps]
        return sum(vals) / max(1, len(vals))

    ref_type = mean("typographic_mass")
    ref_graphic = mean("graphic_mass")
    ref_axis = sum(1 for m in ref_maps if m.get("dominant_compositional_axis") == "vertical") / max(1, len(ref_maps))
    gaps = {
        "group_cohesion": abs(float(render_map.get("distance_related") or 0.4) - mean("distance_related")),
        "visual_rhythm": abs(float(render_map.get("typographic_mass") or 0) - ref_type),
        "hierarchy": abs(float(render_map.get("distance_related") or 0.3) - mean("distance_related")),
        "typographic_mass": abs(float(render_map.get("typographic_mass") or 0) - ref_type),
        "graphic_depth": abs(float(render_map.get("graphic_mass") or 0) - ref_graphic),
        "photo_design_integration": 0.0 if render_map.get("photo_type_interaction") == "type_on_tonal_support" else 0.35,
        "negative_space_quality": 0.15 if render_map.get("negative_space_function") else 0.4,
        "whole_canvas_composition": 0.1 if render_map.get("dominant_compositional_axis") == ("vertical" if ref_axis >= 0.5 else "horizontal") else 0.35,
    }
    overall = sum(gaps.values()) / max(1, len(gaps))
    return {**{k: round(v, 4) for k, v in gaps.items()}, "overall": round(overall, 4)}


def craft_gap_report(old_gap: dict[str, float], new_gap: dict[str, float]) -> dict[str, Any]:
    improvement = round(float(old_gap.get("overall") or 0) - float(new_gap.get("overall") or 0), 4)
    return {
        "schema": "ReferenceCraftGapV1",
        "OLD_GAP": old_gap,
        "NEW_GAP": new_gap,
        "IMPROVEMENT": improvement,
    }


def score_calibration_render(objects: dict[str, Any], groups: list[dict[str, Any]], flow: dict[str, Any], field_mass: float) -> dict[str, int]:
    fid = blueprint_render_fidelity(objects, groups, flow, field_mass=field_mass, intended_mode="CALIBRATION")
    s = fid["scores"]
    return {
        "composition_grammar_fidelity": s["group_relationship_fidelity"],
        "group_cohesion": s["group_relationship_fidelity"],
        "typography": s["typography_fidelity"],
        "visual_rhythm": s["visual_mass_fidelity"],
        "graphic_depth": s["graphic_field_fidelity"],
        "negative_space": s["negative_space_fidelity"],
        "reading_flow": s["reading_flow_fidelity"],
        "brand_integration": s["brand_relationship_fidelity"],
    }
