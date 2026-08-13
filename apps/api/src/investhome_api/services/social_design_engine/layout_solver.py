"""Deterministic layout solver — blueprint → pixel geometry.

Order: place groups on the grid → size groups to content → line-break →
THEN shrink font. Collision against other groups, canvas bounds, and
protected focal regions. LLM never invents pixels.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.social_design_engine.composition_blueprint import (
    METRIC_LAYOUT_TO_ELEMENT,
    CompositionBlueprint,
    NormRect,
)
from investhome_api.services.social_design_engine.layout import (
    LINE_HEIGHT,
    auto_layout_text,
    layout_cta_element,
    layout_metric_group,
    measure_text_block,
)
from investhome_api.services.social_design_engine.ops import FORMAT_PRESETS
from investhome_api.services.social_design_engine.typography import (
    apply_headline_typography,
    hierarchy_font_prefs,
    min_readable_size,
)

GROUP_GAP_PCT = 1.6


def norm_to_px(rect: NormRect, canvas_w: int, canvas_h: int) -> dict[str, int]:
    c = rect.clamped()
    x = int(round(canvas_w * c.x / 100.0))
    y = int(round(canvas_h * c.y / 100.0))
    w = max(8, int(round(canvas_w * c.w / 100.0)))
    h = max(8, int(round(canvas_h * c.h / 100.0)))
    x = max(0, min(x, canvas_w - 8))
    y = max(0, min(y, canvas_h - 8))
    w = min(w, canvas_w - x)
    h = min(h, canvas_h - y)
    return {"x": x, "y": y, "width": w, "height": h}


def px_to_norm(x: int, y: int, w: int, h: int, canvas_w: int, canvas_h: int) -> NormRect:
    cw = max(1, canvas_w)
    ch = max(1, canvas_h)
    return NormRect(
        x=100.0 * x / cw,
        y=100.0 * y / ch,
        w=100.0 * w / cw,
        h=100.0 * h / ch,
    ).clamped()


def blueprint_slots(bp: CompositionBlueprint, canvas_w: int, canvas_h: int) -> dict[str, dict[str, int]]:
    """Role slots from blueprint regions — used by layout grammar + design plan."""
    slots: dict[str, dict[str, int]] = {}
    headline = norm_to_px(bp.headline_region, canvas_w, canvas_h)
    slots["headline"] = {**headline, "max_height": headline["height"]}
    if bp.support_region is not None:
        body = norm_to_px(bp.support_region, canvas_w, canvas_h)
        slots["body"] = {**body, "max_height": body["height"]}
    if bp.brand_region is not None:
        brand = norm_to_px(bp.brand_region, canvas_w, canvas_h)
        slots["eyebrow"] = {**brand, "max_height": brand["height"]}
        slots["brand"] = {**brand, "max_height": brand["height"]}
    if bp.metric_region is not None:
        metric = norm_to_px(bp.metric_region, canvas_w, canvas_h)
        slots["metric_group"] = {**metric, "max_height": metric["height"]}
    if bp.cta_region is not None:
        cta = norm_to_px(bp.cta_region, canvas_w, canvas_h)
        slots["cta"] = cta
    return slots


def _boxes_overlap(a: dict[str, Any], b: dict[str, Any], gap: int = 0) -> bool:
    ax2 = int(a.get("x") or 0) + int(a.get("width") or 0)
    ay2 = int(a.get("y") or 0) + int(a.get("height") or 0)
    bx2 = int(b.get("x") or 0) + int(b.get("width") or 0)
    by2 = int(b.get("y") or 0) + int(b.get("height") or 0)
    ax1, ay1 = int(a.get("x") or 0), int(a.get("y") or 0)
    bx1, by1 = int(b.get("x") or 0), int(b.get("y") or 0)
    return not (ax2 + gap <= bx1 or bx2 + gap <= ax1 or ay2 + gap <= by1 or by2 + gap <= ay1)


def _protected_px(bp: CompositionBlueprint, canvas_w: int, canvas_h: int) -> dict[str, int]:
    return norm_to_px(bp.focal_region, canvas_w, canvas_h)


def collide_with_focal(box: dict[str, int], protected: dict[str, int], *, canvas_h: int) -> dict[str, int]:
    if not _boxes_overlap(box, protected, gap=8):
        return box
    # Prefer moving into negative space above the protected mass; else below.
    above_h = protected["y"] - 8
    if box["height"] <= above_h and above_h > 40:
        return {**box, "y": max(24, above_h - box["height"])}
    below = protected["y"] + protected["height"] + 8
    if below + box["height"] <= canvas_h - 24:
        return {**box, "y": below}
    # Sidestep left if still overlapping.
    if box["x"] + box["width"] > protected["x"]:
        left = max(24, protected["x"] - box["width"] - 8)
        if left >= 24:
            return {**box, "x": left}
    return box


def resolve_group_collisions(
    boxes: dict[str, dict[str, int]],
    *,
    canvas_w: int,
    canvas_h: int,
    protected: dict[str, int] | None = None,
    gap: int | None = None,
) -> dict[str, dict[str, int]]:
    """Headline/support/metrics/CTA/brand vs each other, bounds, and focal."""
    order = ["eyebrow", "brand", "headline", "body", "metric_group", "cta"]
    gap = gap if gap is not None else max(12, int(round(canvas_h * 0.014)))
    working = {k: dict(v) for k, v in boxes.items()}
    if protected:
        for key in list(working):
            if key in {"headline", "body", "metric_group", "cta", "eyebrow", "brand"}:
                working[key] = collide_with_focal(working[key], protected, canvas_h=canvas_h)

    placed: list[str] = []
    for key in order:
        if key not in working:
            continue
        box = working[key]
        for prev in placed:
            other = working[prev]
            if not _boxes_overlap(box, other, gap=gap):
                continue
            box["y"] = int(other["y"]) + int(other["height"]) + gap
            max_y = canvas_h - int(box["height"]) - 24
            if box["y"] > max_y:
                box["y"] = max(24, max_y)
        box["x"] = max(0, min(int(box["x"]), canvas_w - int(box["width"])))
        box["y"] = max(0, min(int(box["y"]), canvas_h - int(box["height"])))
        working[key] = box
        placed.append(key)
    return working


def reflow_text_in_slot(
    text: str,
    *,
    role: str,
    slot: dict[str, int],
    canvas_w: int,
    canvas_h: int,
    density: str,
    format_preset: str,
    composition: str,
    align: str,
) -> tuple[str, int, dict[str, int]]:
    """Layout → group size → line breaks → font shrink (never tiny-first)."""
    max_w = max(40, int(slot.get("width") or int(canvas_w * 0.7)))
    max_h = max(24, int(slot.get("max_height") or slot.get("height") or int(canvas_h * 0.16)))
    min_size = min_readable_size(role, format_preset)
    if role == "headline":
        composed, font, height = apply_headline_typography(
            text,
            canvas_w=canvas_w,
            width=max_w,
            max_height=max_h,
            density=density,
            format_preset=format_preset,
            composition=composition,
        )
        font = max(min_size, font)
        geo = {
            "x": int(slot["x"]),
            "y": int(slot["y"]),
            "width": max_w,
            "height": min(max_h, max(height, int(round(font * LINE_HEIGHT)))),
        }
        return composed, font, geo

    prefs = hierarchy_font_prefs(role, canvas_w, density=density, format_preset=format_preset)
    font = max(min_size, prefs["preferred"])
    draft = {
        "type": "TEXT",
        "role": role,
        "content": text,
        "fontSize": font,
        "fontWeight": "bold" if role == "headline" else "normal",
        "align": align,
        "x": slot["x"],
        "y": slot["y"],
        "width": max_w,
        "height": max_h,
    }
    laid = auto_layout_text(
        draft,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        preferred_font=font,
        max_lines=1 if role in {"eyebrow", "brand"} else 3,
        max_width=max_w,
        max_height=max_h,
        keep_position=True,
    )
    if int(laid.get("fontSize") or font) < min_size:
        laid["fontSize"] = min_size
        _, measured, _ = measure_text_block(text, min_size, max_w, bold=False)
        laid["height"] = min(max_h, max(measured, int(round(min_size * LINE_HEIGHT))))
    return text, int(laid["fontSize"]), {
        "x": int(laid["x"]),
        "y": int(laid["y"]),
        "width": int(laid["width"]),
        "height": int(laid["height"]),
    }


def apply_blueprint_to_elements(
    elements: list[Any],
    *,
    blueprint: CompositionBlueprint,
    canvas_w: int,
    canvas_h: int,
    density: str = "LOW",
    format_preset: str = "square",
    composition: str = "",
    align: str = "left",
) -> list[Any]:
    """Place design-plan elements into blueprint slots, then collision-resolve."""
    slots = blueprint_slots(blueprint, canvas_w, canvas_h)
    protected = _protected_px(blueprint, canvas_w, canvas_h)
    gap = max(12, int(round(canvas_h * blueprint.grid.gutter / 100.0)))
    boxes: dict[str, dict[str, int]] = {}
    by_role: dict[str, Any] = {}
    for el in elements:
        role = getattr(el, "role", None) or (el.get("role") if isinstance(el, dict) else None)
        el_type = getattr(el, "type", None) or (el.get("type") if isinstance(el, dict) else None)
        key = str(role or "").lower()
        if str(el_type or "").upper() in {"BUTTON", "CTA"}:
            key = "cta"
        if str(el_type or "").upper() == "METRIC_GROUP":
            key = "metric_group"
        if key:
            by_role[key] = el

    for role, el in by_role.items():
        slot = slots.get(role)
        if slot is None and role == "body":
            slot = slots.get("headline")
        if slot is None:
            continue
        boxes[role] = {
            "x": int(slot["x"]),
            "y": int(slot["y"]),
            "width": int(slot["width"]),
            "height": int(slot.get("max_height") or slot.get("height") or 40),
        }

    boxes = resolve_group_collisions(
        boxes, canvas_w=canvas_w, canvas_h=canvas_h, protected=protected, gap=gap
    )

    next_elements: list[Any] = []
    for el in elements:
        is_dict = isinstance(el, dict)
        role = str((el.get("role") if is_dict else getattr(el, "role", "")) or "").lower()
        el_type = str((el.get("type") if is_dict else getattr(el, "type", "")) or "").upper()
        if el_type in {"BUTTON", "CTA"}:
            role = "cta"
        if el_type == "METRIC_GROUP":
            role = "metric_group"
        slot = boxes.get(role) or slots.get(role)
        if slot is None:
            next_elements.append(el)
            continue
        if el_type == "TEXT":
            text = str((el.get("content") if is_dict else getattr(el, "text", "")) or "")
            composed, font, geo = reflow_text_in_slot(
                text,
                role=role or "custom",
                slot={**slot, "max_height": slot.get("height", 40)},
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                density=density,
                format_preset=format_preset,
                composition=composition or blueprint.composition_family,
                align=align or blueprint.alignment,
            )
            if is_dict:
                out = dict(el)
                out.update(geo)
                out["content"] = composed
                out["fontSize"] = font
                out["align"] = align or blueprint.alignment
                next_elements.append(out)
            else:
                el.text = composed
                el.font_size = font
                el.x, el.y, el.width, el.height = geo["x"], geo["y"], geo["width"], geo["height"]
                el.align = align or blueprint.alignment
                next_elements.append(el)
        elif el_type in {"BUTTON", "CTA"}:
            draft = el if is_dict else {
                "type": "BUTTON",
                "label": getattr(el, "text", ""),
                "x": slot["x"],
                "y": slot["y"],
                "width": slot["width"],
                "height": max(36, int(slot["height"])),
            }
            laid = layout_cta_element(draft if is_dict else {**draft, **slot}, canvas_w=canvas_w, canvas_h=canvas_h, slot=slot, align=align)
            if is_dict:
                out = dict(el)
                out.update(laid)
                next_elements.append(out)
            else:
                el.x, el.y, el.width, el.height = laid["x"], laid["y"], laid["width"], laid["height"]
                next_elements.append(el)
        elif el_type == "METRIC_GROUP":
            element_layout = METRIC_LAYOUT_TO_ELEMENT.get(str(blueprint.metric_layout or ""), "horizontal")
            draft = el if is_dict else {
                "type": "METRIC_GROUP",
                "layout": element_layout,
                "metrics": getattr(el, "metrics", None) or [],
                "x": slot["x"],
                "y": slot["y"],
                "width": slot["width"],
                "height": slot["height"],
            }
            if is_dict:
                draft = dict(el)
                draft["layout"] = element_layout
            laid = layout_metric_group(draft, canvas_w=canvas_w, canvas_h=canvas_h, slot=slot)
            if is_dict:
                out = dict(el)
                out.update(laid)
                out["layout"] = element_layout
                next_elements.append(out)
            else:
                el.x, el.y, el.width, el.height = laid["x"], laid["y"], laid["width"], laid["height"]
                el.metric_layout = element_layout
                next_elements.append(el)
        else:
            next_elements.append(el)
    return next_elements


def reduce_density_if_needed(
    blueprint: CompositionBlueprint,
    elements: list[Any],
    *,
    canvas_h: int,
) -> tuple[CompositionBlueprint, list[Any]]:
    """If groups overflow the frame, drop tertiary (support/CTA) rather than tiny type."""
    text_h = 0
    for el in elements:
        el_type = getattr(el, "type", None) or (el.get("type") if isinstance(el, dict) else "")
        if str(el_type).upper() in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"}:
            text_h += int(getattr(el, "height", 0) or (el.get("height") if isinstance(el, dict) else 0) or 0)
    if text_h <= int(canvas_h * 0.52):
        return blueprint, elements
    dropped = []
    kept: list[Any] = []
    for el in elements:
        is_dict = isinstance(el, dict)
        role = str((el.get("role") if is_dict else getattr(el, "role", "")) or "")
        el_type = str((el.get("type") if is_dict else getattr(el, "type", "")) or "")
        if role == "body":
            dropped.append(role)
            continue
        kept.append(el)
    text_h2 = 0
    for el in kept:
        el_type = getattr(el, "type", None) or (el.get("type") if isinstance(el, dict) else "")
        if str(el_type).upper() in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"}:
            text_h2 += int(getattr(el, "height", 0) or (el.get("height") if isinstance(el, dict) else 0) or 0)
    if text_h2 > int(canvas_h * 0.52):
        next_kept: list[Any] = []
        for el in kept:
            is_dict = isinstance(el, dict)
            el_type = str((el.get("type") if is_dict else getattr(el, "type", "")) or "")
            role = str((el.get("role") if is_dict else getattr(el, "role", "")) or "")
            if el_type in {"BUTTON", "CTA"} and blueprint.visual_weight.dominant != "cta":
                dropped.append(role or el_type)
                continue
            next_kept.append(el)
        kept = next_kept
    if dropped:
        blueprint.decisions.append(f"density_reduced:{','.join(dropped)}")
        if "body" in dropped:
            blueprint.support_region = None
        if any(d in {"cta", "BUTTON", "CTA"} for d in dropped):
            blueprint.cta_region = None
            blueprint.cta_placement = "none"
    return blueprint, kept


def reflow_blueprint_for_format(
    blueprint: CompositionBlueprint,
    *,
    format_preset: str,
    plan: Any = None,
    profile: Any = None,
    metric_count: int = 0,
) -> CompositionBlueprint:
    """Format change: rebuild group relationships for the same family. Not a stretch."""
    from investhome_api.services.social_design_engine.composition_engine import build_composition_blueprint
    from investhome_api.services.social_design_engine.creative_plan import CreativePlan

    if not isinstance(plan, CreativePlan):
        return blueprint
    next_bp = build_composition_blueprint(
        plan=plan,
        profile=profile,
        format_preset=format_preset,
        instruction=blueprint.diversity_key,
        metric_count=metric_count,
        include_support=blueprint.support_region is not None,
        include_metrics=blueprint.metric_region is not None,
        include_cta=blueprint.cta_region is not None,
        include_brand=blueprint.brand_region is not None,
    )
    # Keep the chosen family; only reflow geometry.
    next_bp.composition_family = blueprint.composition_family
    next_bp.decisions = list(blueprint.decisions) + [f"reflow_format:{format_preset}"]
    next_bp.diversity_key = blueprint.diversity_key
    return next_bp


def canvas_size(format_preset: str) -> tuple[int, int]:
    return FORMAT_PRESETS.get(format_preset or "square", (1080, 1080))
