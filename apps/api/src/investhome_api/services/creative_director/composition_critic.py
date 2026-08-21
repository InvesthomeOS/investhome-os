"""Composition Quality Critic — gate design spec vs golden principles (one revise max)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _el_ids(spec: dict[str, Any]) -> set[str]:
    return {
        str(el.get("id") or "")
        for el in (spec.get("elements") or [])
        if isinstance(el, dict)
    }


def _types(spec: dict[str, Any]) -> set[str]:
    return {
        str(el.get("type") or "").lower()
        for el in (spec.get("elements") or [])
        if isinstance(el, dict)
    }


def critique_composition(
    *,
    composition_plan: dict[str, Any],
    design_spec: dict[str, Any],
) -> dict[str, Any]:
    """Score composition fidelity before render. status=pass|fail."""
    ids = _el_ids(design_spec)
    types = _types(design_spec)
    intent = str(composition_plan.get("campaign_intent") or design_spec.get("campaign_intent") or "")
    family = str(composition_plan.get("layout_family") or "")
    issues: list[str] = []
    checks: dict[str, bool] = {}

    has_overlay = bool(types & {"overlay", "gradient"}) or any(
        "gradient" in i or "overlay" in i or "vignette" in i for i in ids
    )
    checks["has_contrast_overlay"] = has_overlay
    if not has_overlay:
        issues.append("missing_contrast_overlay")

    checks["has_logo"] = "logo" in ids
    if "logo" not in ids:
        issues.append("missing_logo")

    checks["has_headline"] = "headline" in ids
    if "headline" not in ids:
        issues.append("missing_headline")

    checks["has_cta"] = "cta" in ids
    if "cta" not in ids:
        issues.append("missing_cta")

    checks["locked_background"] = bool(design_spec.get("locked_background"))
    if not design_spec.get("locked_background"):
        issues.append("background_not_locked")

    # Intentional placement: headline should not sit at very top (y < 8% of canvas)
    canvas = design_spec.get("canvas") if isinstance(design_spec.get("canvas"), dict) else {}
    height = float(canvas.get("height") or 1350)
    headline = next(
        (e for e in (design_spec.get("elements") or []) if isinstance(e, dict) and e.get("id") == "headline"),
        None,
    )
    intentional = True
    if headline is not None:
        y = float(headline.get("y") or 0)
        # Fail if stuck at top like simplified stack (except lifestyle/brand upper editorial)
        if family == "price_lower_third" and y < height * 0.35:
            intentional = False
            issues.append("headline_not_in_lower_third")
        if family == "lifestyle_editorial" and y > height * 0.45:
            intentional = False
            issues.append("lifestyle_headline_not_upper")
    checks["headline_placement_intentional"] = intentional

    # Hierarchy: headline font > support font when both present
    hierarchy_ok = True
    support = next(
        (
            e
            for e in (design_spec.get("elements") or [])
            if isinstance(e, dict) and str(e.get("role") or "") in {"support_message", "subheadline"}
        ),
        None,
    )
    if headline and support:
        ht = headline.get("typography") if isinstance(headline.get("typography"), dict) else {}
        st = support.get("typography") if isinstance(support.get("typography"), dict) else {}
        hs = float(ht.get("font_size") or 0)
        ss = float(st.get("font_size") or 0)
        if hs and ss and hs < ss * 1.25:
            hierarchy_ok = False
            issues.append("weak_type_hierarchy")
    checks["typography_hierarchy"] = hierarchy_ok

    # Premium simplicity: not too many text layers
    textish = [
        e
        for e in (design_spec.get("elements") or [])
        if isinstance(e, dict) and str(e.get("type") or "").lower() in {"text", "badge", "cta"}
    ]
    checks["not_overcrowded"] = len(textish) <= 10
    if len(textish) > 10:
        issues.append("overcrowded_copy")

    # Price family needs price layers
    if "price" in family or intent in {"price_campaign", "sales_offer", "launch", "launch_price"}:
        has_price = "new-price" in ids or "old-price" in ids
        checks["price_hierarchy"] = has_price
        if not has_price:
            issues.append("missing_price_block")
    else:
        checks["price_hierarchy"] = True

    # Composition plan presence
    checks["has_composition_plan"] = bool(composition_plan.get("layout_family"))
    if not composition_plan.get("layout_family"):
        issues.append("missing_composition_plan")

    checks["has_decorative_or_shape"] = bool(
        types & {"shape", "rectangle", "line", "divider", "overlay", "gradient", "badge"}
    ) or any("frame" in i or "divider" in i or "pill" in i for i in ids)
    if not checks["has_decorative_or_shape"] and family != "project_brand_minimal":
        issues.append("flat_template_no_structure")

    fail_keys = {
        "missing_contrast_overlay",
        "missing_logo",
        "missing_headline",
        "missing_cta",
        "headline_not_in_lower_third",
        "weak_type_hierarchy",
        "missing_price_block",
        "flat_template_no_structure",
        "missing_composition_plan",
    }
    hard_fail = [i for i in issues if i in fail_keys]
    status = "pass" if not hard_fail else "fail"
    score = max(1, 10 - len(hard_fail) * 2 - max(0, len(issues) - len(hard_fail)))

    return {
        "status": status,
        "score": score,
        "checks": checks,
        "issues": issues,
        "layout_family": family,
        "campaign_intent": intent,
        "fixed_once": False,
    }


def revise_design_spec_once(
    *,
    design_spec: dict[str, Any],
    composition_plan: dict[str, Any],
    critique: dict[str, Any],
) -> dict[str, Any]:
    """One-time deterministic repair of common critic failures (no provider)."""
    spec = deepcopy(design_spec)
    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
    width = int(canvas.get("width") or 1080)
    height = int(canvas.get("height") or 1350)
    issues = set(critique.get("issues") or [])
    elements = list(spec.get("elements") or [])
    ids = {str(e.get("id")) for e in elements if isinstance(e, dict)}

    def _ensure_overlay(eid: str, y: int, h: int, fill: str, z: int = 5) -> None:
        nonlocal elements, ids
        if eid in ids:
            return
        elements.append(
            {
                "id": eid,
                "type": "gradient",
                "role": "overlay",
                "locked": False,
                "editable": True,
                "x": 0,
                "y": y,
                "width": width,
                "height": h,
                "z_index": z,
                "opacity": 1.0,
                "style": {"fill": fill, "shape_kind": "rect"},
            }
        )
        ids.add(eid)

    if "missing_contrast_overlay" in issues:
        family = str(composition_plan.get("layout_family") or "")
        if family == "lifestyle_editorial":
            _ensure_overlay(
                "overlay-top-light",
                0,
                int(height * 0.34),
                "linear-gradient(to bottom, rgba(245,240,232,0.92) 0%, rgba(245,240,232,0.55) 55%, transparent 100%)",
                4,
            )
            _ensure_overlay(
                "overlay-bottom-dark",
                int(height * 0.68),
                int(height * 0.32),
                "linear-gradient(to top, rgba(12,10,8,0.78) 0%, rgba(12,10,8,0.35) 55%, transparent 100%)",
                5,
            )
        elif family == "location_place_led":
            _ensure_overlay(
                "overlay-top-dark",
                0,
                int(height * 0.28),
                "linear-gradient(to bottom, rgba(8,6,4,0.72) 0%, rgba(8,6,4,0.25) 70%, transparent 100%)",
                4,
            )
        else:
            _ensure_overlay(
                "overlay-bottom-dark",
                int(height * 0.48),
                int(height * 0.52),
                "linear-gradient(to top, rgba(8,6,4,0.92) 0%, rgba(8,6,4,0.55) 45%, transparent 100%)",
                5,
            )

    if "headline_not_in_lower_third" in issues:
        for e in elements:
            if isinstance(e, dict) and e.get("id") == "headline":
                e["y"] = int(height * 0.50)
                break

    if "weak_type_hierarchy" in issues:
        for e in elements:
            if not isinstance(e, dict):
                continue
            if e.get("id") == "headline":
                typo = dict(e.get("typography") or {})
                typo["font_size"] = max(int(typo.get("font_size") or 0), int(width * 0.078))
                e["typography"] = typo

    # Drop extras if overcrowded (keep semantic ids)
    if "overcrowded_copy" in issues:
        keep_priority = {
            "master_background",
            "logo",
            "headline",
            "cta",
            "new-price",
            "old-price",
            "discount-badge",
            "subheadline",
            "unit-label",
            "support-message-1",
        }
        overlays = [e for e in elements if isinstance(e, dict) and str(e.get("type")).lower() in {"gradient", "overlay", "shape", "divider", "line", "rectangle"}]
        semantic = [e for e in elements if isinstance(e, dict) and e.get("id") in keep_priority]
        elements = overlays + semantic

    spec["elements"] = elements
    return spec


def geometry_check_design_spec(design_spec: dict[str, Any]) -> dict[str, Any]:
    """Light post-render geometry check — no provider calls."""
    canvas = design_spec.get("canvas") if isinstance(design_spec.get("canvas"), dict) else {}
    width = float(canvas.get("width") or 1080)
    height = float(canvas.get("height") or 1350)
    margin = width * 0.04
    issues: list[str] = []
    boxes: list[tuple[str, float, float, float, float]] = []

    for el in design_spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        eid = str(el.get("id") or "")
        et = str(el.get("type") or "").lower()
        if et in {"gradient", "overlay"} or eid == "master_background":
            continue
        x = float(el.get("x") or 0)
        y = float(el.get("y") or 0)
        w = float(el.get("width") or 0)
        h = float(el.get("height") or 0)
        if w < 8 or h < 8:
            issues.append(f"tiny_box:{eid}")
        if x < -2 or y < -2 or x + w > width + 2 or y + h > height + 2:
            issues.append(f"overflow:{eid}")
        if eid in {"logo", "headline", "cta"} and (x < margin * 0.25 or x + w > width - margin * 0.25):
            # soft margin warn
            if x < 0 or x + w > width:
                issues.append(f"unsafe_margin:{eid}")
        typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
        style = el.get("style") if isinstance(el.get("style"), dict) else {}
        fs = float(typo.get("font_size") or style.get("font_size") or 0)
        if et in {"text", "cta", "badge"} and fs and fs < 14:
            issues.append(f"tiny_text:{eid}")
        boxes.append((eid, x, y, w, h))

    # Collision among semantic text/cta (IoU rough)
    semantic = [b for b in boxes if b[0] in {"headline", "cta", "logo", "new-price", "old-price"}]
    for i, a in enumerate(semantic):
        for b in semantic[i + 1 :]:
            ax1, ay1, ax2, ay2 = a[1], a[2], a[1] + a[3], a[2] + a[4]
            bx1, by1, bx2, by2 = b[1], b[2], b[1] + b[3], b[2] + b[4]
            ix1, iy1 = max(ax1, bx1), max(ay1, by1)
            ix2, iy2 = min(ax2, bx2), min(ay2, by2)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                if inter > min(a[3] * a[4], b[3] * b[4]) * 0.35:
                    issues.append(f"collision:{a[0]}|{b[0]}")

    return {
        "status": "pass" if not issues else "warn",
        "issues": issues,
        "provider_calls": 0,
    }


def fix_geometry_once(design_spec: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    """Clamp overflow / nudge colliding CTA below price."""
    spec = deepcopy(design_spec)
    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
    width = float(canvas.get("width") or 1080)
    height = float(canvas.get("height") or 1350)
    issues = geometry.get("issues") or []
    by_id = {
        str(e.get("id")): e
        for e in (spec.get("elements") or [])
        if isinstance(e, dict) and e.get("id")
    }
    for issue in issues:
        if issue.startswith("overflow:"):
            eid = issue.split(":", 1)[1]
            el = by_id.get(eid)
            if not el:
                continue
            w = float(el.get("width") or 0)
            h = float(el.get("height") or 0)
            el["x"] = int(max(0, min(float(el.get("x") or 0), width - w)))
            el["y"] = int(max(0, min(float(el.get("y") or 0), height - h)))
        if issue.startswith("collision:") and "cta" in issue:
            cta = by_id.get("cta")
            price = by_id.get("new-price") or by_id.get("old-price")
            if cta and price:
                cta["y"] = int(
                    float(price.get("y") or 0) + float(price.get("height") or 0) + height * 0.04
                )
    return spec
