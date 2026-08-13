"""Design Quality evaluation + auto-repair.

Scores hierarchy, readability, composition, balance, contrast, spacing,
image_respect, brand_consistency. Repairs geometry without regenerating copy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from investhome_api.services.social_design_engine.layout import (
    LINE_HEIGHT,
    _boxes_overlap,
    element_within_bounds,
    measure_text_block,
    safe_content_box,
    subject_safe_regions,
)
from investhome_api.services.social_design_engine.ops import FORMAT_PRESETS

QUALITY_DIMENSIONS = (
    "hierarchy",
    "readability",
    "composition",
    "balance",
    "contrast",
    "spacing",
    "image_respect",
    "brand_consistency",
    "grid",
    "negative_space",
    "focal_respect",
    "grouping",
    "alignment",
    "typography",
    "margins",
    "collision",
    "cta_placement",
    "brand_lockup",
)


@dataclass
class DesignQualityIssue:
    code: str
    detail: str
    repair: str


@dataclass
class DesignQualityScore:
    total: float
    dimensions: dict[str, float] = field(default_factory=dict)
    issues: list[DesignQualityIssue] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "dimensions": dict(self.dimensions),
            "issues": [i.code for i in self.issues],
            "repairs": list(self.repairs),
            "passed": self.passed,
        }


def _el_box(el: Any) -> dict[str, Any]:
    return {
        "x": int(getattr(el, "x", 0) or 0),
        "y": int(getattr(el, "y", 0) or 0),
        "width": int(getattr(el, "width", 0) or 0),
        "height": int(getattr(el, "height", 0) or 0),
        "type": getattr(el, "type", ""),
        "role": getattr(el, "role", ""),
    }


def score_design_quality(
    *,
    plan: Any,
    concept: Any,
    creative_plan: Any | None = None,
    blueprint: Any | None = None,
) -> DesignQualityScore:
    dims = {k: 0.82 for k in QUALITY_DIMENSIONS}
    issues: list[DesignQualityIssue] = []
    w, h = FORMAT_PRESETS.get(getattr(plan, "format_preset", "square"), (1080, 1080))
    box = safe_content_box(w, h)
    regions = subject_safe_regions(w, h)
    subject = regions["subject"]
    elements = list(getattr(plan, "elements", None) or [])
    headline = next((e for e in elements if getattr(e, "role", "") == "headline"), None)
    body = next((e for e in elements if getattr(e, "role", "") == "body"), None)
    cta = next((e for e in elements if getattr(e, "role", "") in {"cta", "button"} or getattr(e, "type", "") in {"BUTTON", "CTA"}), None)
    metrics = next((e for e in elements if getattr(e, "type", "") == "METRIC_GROUP"), None)
    overlay = str(getattr(plan, "overlay", "") or "")
    composition = ""
    if creative_plan is not None:
        composition = str(getattr(creative_plan, "composition", "") or "")
        contrast = str(getattr(creative_plan, "contrast_strategy", "") or "")
        if contrast == "NONE" and overlay not in {"none", ""}:
            dims["contrast"] -= 0.15
            issues.append(DesignQualityIssue("heavy_overlay", overlay, "localize_overlay"))
        if contrast in {"DARK_GRADIENT", "SOFT_OVERLAY"} and overlay in {"gradient", "full", "heavy"}:
            dims["contrast"] -= 0.25
            issues.append(DesignQualityIssue("heavy_overlay", overlay, "localize_overlay"))

    if headline and body and headline.font_size and body.font_size:
        if headline.font_size < int(body.font_size * 1.45):
            dims["hierarchy"] -= 0.35
            issues.append(DesignQualityIssue("weak_hierarchy", "headline not dominant", "fix_hierarchy"))
        else:
            dims["hierarchy"] = min(1.0, dims["hierarchy"] + 0.08)
    if headline and (headline.font_size or 0) < 22:
        dims["readability"] -= 0.2
        issues.append(DesignQualityIssue("tiny_headline", str(headline.font_size), "fix_hierarchy"))
    if body and (body.font_size or 0) < 13:
        dims["readability"] -= 0.15
        issues.append(DesignQualityIssue("tiny_support", str(body.font_size), "fix_hierarchy"))

    for el in elements:
        if getattr(el, "type", "") in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"}:
            if not element_within_bounds(_el_box(el), w, h):
                dims["spacing"] -= 0.2
                issues.append(DesignQualityIssue("unsafe_edge", getattr(el, "role", ""), "clamp_safe"))
            right = el.x + el.width
            bottom = el.y + el.height
            if el.x < box["x"] - 4 or el.y < box["y"] - 4 or right > box["x"] + box["width"] + 8:
                dims["spacing"] -= 0.1
                issues.append(DesignQualityIssue("unsafe_edge", getattr(el, "role", ""), "clamp_safe"))
            if getattr(el, "type", "") == "TEXT" and el.font_size:
                _, measured, _ = measure_text_block(
                    getattr(el, "text", "") or "",
                    el.font_size,
                    el.width,
                    bold=getattr(el, "role", "") == "headline",
                )
                if measured > el.height + int(round((el.font_size or 16) * 0.2)):
                    dims["readability"] -= 0.2
                    issues.append(DesignQualityIssue("clipping", getattr(el, "role", ""), "grow_or_wrap"))

    for i, a in enumerate(elements):
        for b in elements[i + 1 :]:
            if getattr(a, "type", "") in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"} and getattr(
                b, "type", ""
            ) in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"}:
                if _boxes_overlap(_el_box(a), _el_box(b), gap=8):
                    dims["spacing"] -= 0.25
                    code = "cta_collision" if "cta" in {getattr(a, "role", ""), getattr(b, "role", "")} else "overlap"
                    issues.append(DesignQualityIssue(code, f"{a.role}/{b.role}", "resolve_overlap"))

    if cta and metrics and _boxes_overlap(_el_box(cta), _el_box(metrics), gap=12):
        dims["spacing"] -= 0.2
        issues.append(DesignQualityIssue("cta_collision", "cta/metrics", "resolve_overlap"))

    if metrics:
        if metrics.x + metrics.width > w - 24 or metrics.y + metrics.height > h - 24:
            dims["composition"] -= 0.2
            issues.append(DesignQualityIssue("metric_overflow", "metric_group", "clamp_safe"))

    if headline:
        hy = headline.y + headline.height // 2
        avoid_focal = True
        if creative_plan is not None:
            regions_plan = getattr(creative_plan, "text_regions", None)
            avoid_focal = bool(getattr(regions_plan, "avoid_focal", True)) if regions_plan else True
        if avoid_focal and subject["y"] <= hy <= subject["y"] + subject["height"]:
            zone = str(getattr(concept, "safe_text_zone", "top") or "top")
            if zone == "top" and headline.y > int(h * 0.28):
                dims["image_respect"] -= 0.3
                issues.append(DesignQualityIssue("focal_obstruction", "headline covers subject", "move_to_safe_zone"))
            if composition == "CENTER_STATEMENT" and getattr(creative_plan, "visual_priority", "") == "building":
                dims["image_respect"] -= 0.2
                issues.append(DesignQualityIssue("focal_obstruction", "center on building", "move_to_safe_zone"))

    text_h = sum(el.height for el in elements if getattr(el, "type", "") in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"})
    if text_h > int(h * 0.48):
        dims["balance"] -= 0.25
        issues.append(DesignQualityIssue("crowded", "text occupies too much frame", "reduce_density"))
    else:
        dims["balance"] = min(1.0, dims["balance"] + 0.05)

    if overlay in {"gradient", "full", "heavy"}:
        dims["contrast"] -= 0.35
        issues.append(DesignQualityIssue("heavy_overlay", overlay, "localize_overlay"))

    brand_ok = True
    if creative_plan is not None and getattr(creative_plan, "brand_treatment", "NONE") != "NONE":
        has_brand = any(getattr(e, "role", "") in {"eyebrow", "brand"} for e in elements)
        if not has_brand and getattr(creative_plan, "include_brand", False):
            brand_ok = False
            dims["brand_consistency"] -= 0.15
    if brand_ok:
        dims["brand_consistency"] = min(1.0, dims["brand_consistency"] + 0.05)

    dims.setdefault("grid", 0.82)
    dims.setdefault("negative_space", 0.82)
    dims.setdefault("focal_respect", 0.82)
    dims.setdefault("grouping", 0.82)
    dims.setdefault("alignment", 0.82)
    dims.setdefault("typography", 0.82)
    dims.setdefault("margins", 0.82)
    dims.setdefault("collision", 0.82)
    dims.setdefault("cta_placement", 0.82)
    dims.setdefault("brand_lockup", 0.82)
    if blueprint is not None:
        family = str(getattr(blueprint, "composition_family", "") or "")
        dims["grid"] = 0.88 if getattr(blueprint, "grid", None) else 0.5
        dims["negative_space"] = 0.86
        content = getattr(blueprint, "content_zone", None)
        if content is not None and getattr(content, "area", None) and content.area() > 62:
            dims["negative_space"] -= 0.28
            issues.append(DesignQualityIssue("crowded", "content zone too large", "reduce_density"))
        elif content is not None and content.area() < 8 and family not in {"IMAGE_DOMINANT", "ARCHITECTURAL_MINIMAL"}:
            dims["negative_space"] -= 0.1
        dims["focal_respect"] = 0.9
        headline_box = _el_box(headline) if headline else None
        focal = getattr(blueprint, "focal_region", None)
        if headline and headline_box and focal is not None:
            from investhome_api.services.social_design_engine.layout_solver import norm_to_px

            protected = norm_to_px(focal, w, h)
            if _boxes_overlap(headline_box, protected, gap=4) and family not in {"STATEMENT_LAYOUT", "LUXURY_BRAND"}:
                dims["focal_respect"] -= 0.35
                dims["image_respect"] -= 0.2
                issues.append(DesignQualityIssue("focal_obstruction", "headline covers focal", "move_to_safe_zone"))
        dims["grouping"] = 0.86 if getattr(blueprint, "groups", None) else 0.6
        dims["alignment"] = 0.88 if str(getattr(blueprint, "alignment", "left")) in {"left", "center", "right"} else 0.5
        dims["typography"] = dims.get("hierarchy", 0.8)
        dims["margins"] = dims.get("spacing", 0.8)
        dims["collision"] = 0.9 if not any(i.code in {"overlap", "cta_collision"} for i in issues) else 0.4
        dims["cta_placement"] = 0.86
        if cta and str(getattr(blueprint, "cta_placement", "")) == "none":
            dims["cta_placement"] -= 0.2
        dims["brand_lockup"] = dims.get("brand_consistency", 0.8)
        if family == "ARCHITECTURAL_MINIMAL" and headline and headline.y > int(h * 0.34):
            dims["focal_respect"] -= 0.2
            issues.append(DesignQualityIssue("focal_obstruction", "architecture type on building", "move_to_safe_zone"))
        if family == "INVESTMENT_GRID" and metrics:
            dims["grouping"] = min(1.0, dims["grouping"] + 0.08)
        if family == "LUXURY_BRAND" and headline and str(getattr(headline, "align", "")) == "center":
            dims["brand_lockup"] = min(1.0, dims["brand_lockup"] + 0.06)
    else:
        for extra in (
            "grid",
            "negative_space",
            "focal_respect",
            "grouping",
            "alignment",
            "typography",
            "margins",
            "collision",
            "cta_placement",
            "brand_lockup",
        ):
            dims.setdefault(extra, 0.78)

    for key in dims:
        dims[key] = max(0.0, min(1.0, round(dims[key], 3)))
    total = round(sum(dims.values()) / len(dims), 3)
    passed = total >= 0.62 and not any(
        i.code in {"clipping", "overlap", "cta_collision", "metric_overflow", "unsafe_edge"} for i in issues
    )
    return DesignQualityScore(
        total=total,
        dimensions=dims,
        issues=issues,
        repairs=[i.repair for i in issues],
        passed=passed,
    )


def repair_design_geometry(
    plan: Any,
    *,
    creative_plan: Any | None = None,
    blueprint: Any | None = None,
    score: DesignQualityScore,
) -> Any:
    """Fix clipping / collision / unsafe edges / CTA collision / metric overflow.

    Does not regenerate copy.
    """
    if not score.issues:
        return plan
    w, h = FORMAT_PRESETS.get(getattr(plan, "format_preset", "square"), (1080, 1080))
    box = safe_content_box(w, h)
    codes = {i.code for i in score.issues}
    elements = list(plan.elements)
    gap = max(12, int(round(h * 0.014)))

    def _clamp(el: Any) -> None:
        el.x = max(box["x"], min(el.x, box["x"] + box["width"] - max(24, el.width)))
        el.y = max(box["y"], min(el.y, box["y"] + box["height"] - max(16, el.height)))
        el.width = min(el.width, box["width"])
        el.height = min(el.height, box["height"])

    if codes & {"unsafe_edge", "clamp_safe", "metric_overflow"}:
        for el in elements:
            if getattr(el, "type", "") in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"}:
                _clamp(el)

    if "clipping" in codes or "grow_or_wrap" in codes:
        for el in elements:
            if getattr(el, "type", "") != "TEXT" or not el.font_size:
                continue
            _, measured, _ = measure_text_block(
                getattr(el, "text", "") or "",
                el.font_size,
                el.width,
                bold=getattr(el, "role", "") == "headline",
            )
            need = max(el.height, measured, int(round((el.font_size or 16) * LINE_HEIGHT)))
            el.height = min(need, box["y"] + box["height"] - el.y)

    if codes & {"overlap", "cta_collision", "resolve_overlap"}:
        ordered = sorted(
            [e for e in elements if getattr(e, "type", "") in {"TEXT", "BUTTON", "CTA", "METRIC_GROUP"}],
            key=lambda e: e.y,
        )
        cursor = box["y"]
        for el in ordered:
            if el.y < cursor:
                el.y = cursor
            _clamp(el)
            cursor = el.y + el.height + gap
        # If stack overflowed, pull CTA to bottom safe band.
        cta = next((e for e in ordered if getattr(e, "type", "") in {"BUTTON", "CTA"}), None)
        if cta:
            cta.y = min(cta.y, box["y"] + box["height"] - cta.height)
            for other in ordered:
                if other is cta:
                    continue
                if _boxes_overlap(_el_box(other), _el_box(cta), gap=8):
                    other.y = max(box["y"], cta.y - other.height - gap)

    if "focal_obstruction" in codes or "move_to_safe_zone" in codes:
        zone = "top"
        if blueprint is not None:
            kind = str(getattr(blueprint, "headline_region_kind", "") or "")
            if "bottom" in kind or kind == "lower_third":
                zone = "bottom"
            elif kind in {"left", "asymmetric_offset"}:
                zone = "left"
        elif creative_plan is not None:
            zone = str(getattr(creative_plan, "safe_text_zone", "top") or "top")
        headline = next((e for e in elements if getattr(e, "role", "") == "headline"), None)
        if headline is not None:
            if zone == "bottom":
                headline.y = max(headline.y, int(round(h * 0.62)))
            elif zone == "left":
                headline.x = box["x"]
                headline.y = min(headline.y, box["y"] + int(round(h * 0.10)))
            else:
                headline.y = min(headline.y, box["y"] + int(round(h * 0.06)))
            _clamp(headline)
        if blueprint is not None:
            from investhome_api.services.social_design_engine.layout_solver import apply_blueprint_to_elements

            try:
                elements = apply_blueprint_to_elements(
                    elements,
                    blueprint=blueprint,
                    canvas_w=w,
                    canvas_h=h,
                    format_preset=str(getattr(plan, "format_preset", "square") or "square"),
                    align=str(getattr(blueprint, "alignment", "left") or "left"),
                )
            except Exception:
                pass

    if "heavy_overlay" in codes or "localize_overlay" in codes:
        region = "top"
        if creative_plan is not None:
            region = str(getattr(creative_plan, "overlay_region", "top") or "top")
            plan.overlay = str(getattr(creative_plan, "overlay_strategy", "") or f"subtle-{region}")
        else:
            plan.overlay = f"localized-{region}"

    plan.elements = elements
    return plan


def evaluate_and_repair(
    *,
    plan: Any,
    concept: Any,
    creative_plan: Any | None = None,
    blueprint: Any | None = None,
) -> tuple[Any, DesignQualityScore]:
    score = score_design_quality(
        plan=plan, concept=concept, creative_plan=creative_plan, blueprint=blueprint
    )
    if score.passed:
        return plan, score
    repaired = repair_design_geometry(
        plan, creative_plan=creative_plan, blueprint=blueprint, score=score
    )
    final = score_design_quality(
        plan=repaired, concept=concept, creative_plan=creative_plan, blueprint=blueprint
    )
    final.repairs = list(dict.fromkeys(score.repairs + final.repairs))
    return repaired, final
