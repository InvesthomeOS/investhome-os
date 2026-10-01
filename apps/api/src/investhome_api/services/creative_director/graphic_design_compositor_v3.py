"""GraphicDesignCompositorV3 + RelationalCreativeLayoutSolverV1.

Executes Master Family craft. Not a creative director. Not a UI kit.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.contiguous_content_fit import contiguous_content_fit, family_safe_rect
from investhome_api.services.creative_director.creative_contrast_engine import evaluate_objects, solve_family_contrast
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.creative_spacing_engine import spacing_plan
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    GOLD,
    IVORY,
    _draw_tracked,
    _norm_box,
    _objects,
    _place_logo,
    turkish_copy_is_valid,
)


def _facts(custom: dict[str, str] | None) -> dict[str, str]:
    if custom:
        return dict(custom)
    return {
        "headline": REQUIRED_FACTS["headline"],
        "unit_type": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "price": REQUIRED_FACTS["list_price"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "cta": REQUIRED_FACTS["cta"],
    }


def _scale_candidates(family: dict[str, Any]) -> list[float]:
    tokens = execution_tokens(family)
    smin = float(tokens.get("scale_min") or 0.78)
    smax = float(tokens.get("scale_max") or 1.08)
    out: list[float] = []
    for raw in (smax, 1.0, 0.94, 0.88, 0.82, smin):
        value = round(max(smin, min(smax, float(raw))), 4)
        if value not in out:
            out.append(value)
    return out


def solve_relational_layout(
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    canvas: tuple[int, int],
    facts: dict[str, str],
    scale: float | None = None,
) -> dict[str, Any]:
    tokens = execution_tokens(family)
    safe = family_safe_rect(occupancy, family)
    chosen = scale
    fit: dict[str, Any] | None = None
    if chosen is None:
        for trial in _scale_candidates(family):
            candidate = contiguous_content_fit(
                occupancy=occupancy, family=family, fonts=fonts, safe=safe, canvas=canvas, scale=trial
            )
            if candidate.get("status") == "FIT":
                chosen = trial
                fit = candidate
                break
        if chosen is None:
            chosen = min(_scale_candidates(family))
    scale = float(chosen)
    space = spacing_plan(family, canvas, scale=scale)
    fit = fit or contiguous_content_fit(
        occupancy=occupancy, family=family, fonts=fonts, safe=safe, canvas=canvas, scale=scale
    )
    w, h = canvas
    alignment = str(tokens.get("alignment") or "right")
    x0 = int(float(safe.get("x") or 0.08) * w) + 8
    x1 = int((float(safe.get("x") or 0.08) + float(safe.get("w") or 0.3)) * w) - 8
    y = int(float(safe.get("y") or 0.06) * h) + 8
    y_limit = int((float(safe.get("y") or 0.06) + float(safe.get("h") or 0.4)) * h) - 8
    anchor_x = x1 if alignment == "right" else x0
    relationships = [
        "architecture_defines_forbidden_geometry",
        "DisplayGroup aligned with CommercialOfferGroup",
        "CommercialOfferGroup separated from CTAGroup by family rhythm",
        "BrandGroup shares an anchor with DisplayGroup",
    ]
    return {
        "schema": "RelationalCreativeLayoutSolverV1",
        "priority": [
            "architecture_safety",
            "family_identity",
            "readability",
            "hierarchy",
            "group_relationships",
            "contrast",
            "spacing_rhythm",
            "final_coordinates",
        ],
        "relationships": relationships,
        "safe": safe,
        "fit": fit,
        "tokens": tokens,
        "spacing": space,
        "anchor": {"x": anchor_x, "y": y, "alignment": alignment, "x0": x0, "x1": x1, "y_limit": y_limit},
        "scale": scale,
        "solved": fit.get("status") == "FIT",
        "facts": facts,
    }


def compose_graphic_design_v3(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str] | None = None,
    scale: float | None = None,
    polish: bool = False,
    lockup: bool = False,
    art_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    facts = _facts(facts)
    if art_plan and str(art_plan.get("schema") or "") == "RelationalCompositionPlanV1":
        from investhome_api.services.creative_director.compositor_relational_v4 import compose_relational_v4

        return compose_relational_v4(
            photo,
            occupancy=occupancy,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            art_plan=art_plan,
            family=family,
            scale=scale,
        )
    if art_plan and str(art_plan.get("schema") or "") == "StructuredPremiumPlanV1":
        return compose_premium_structured(
            photo,
            occupancy=occupancy,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            art_plan=art_plan,
            family=family,
            scale=scale,
        )
    if art_plan:
        return compose_from_structured_plan(
            photo,
            occupancy=occupancy,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            art_plan=art_plan,
            family=family,
            scale=scale,
        )
    if str(family.get("family_id") or "") == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN":
        from investhome_api.services.creative_director.full_frame_architectural_family import compose_full_frame_campaign

        return compose_full_frame_campaign(
            photo,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            scale=scale,
            polish=polish,
            lockup=lockup,
        )
    tokens = execution_tokens(family)
    plan = solve_relational_layout(
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        canvas=photo.size,
        facts=facts,
        scale=scale,
    )
    scale = float(plan.get("scale") or 1.0)
    region = plan["safe"]
    contrast = solve_family_contrast(photo, occupancy, family, region)
    fielded = contrast["image"]
    fills = contrast["fills"]
    if plan["fit"]["status"] != "FIT":
        return {
            "schema": "GraphicDesignCompositorV3",
            "solved": False,
            "fit": plan["fit"],
            "plan": {k: v for k, v in plan.items() if k != "tokens"},
            "image": fielded,
            "fielded": fielded,
            "foundation": photo,
            "objects": {},
            "facts": facts,
            "fills": {k: list(v) for k, v in fills.items()},
            "contrast_treatments": contrast.get("treatments"),
        }
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    space = plan["spacing"]["pixels"]
    alignment = plan["anchor"]["alignment"]
    ox = plan["anchor"]["x"]
    y = plan["anchor"]["y"]
    y_limit = plan["anchor"]["y_limit"]
    fill = fills["fill"]
    accent = fills["accent"]
    number = fills.get("number") or fill
    display_h = max(28, int(h * float(tokens["display_scale"]) * scale))
    support_h = max(13, int(h * float(tokens["commercial_label_scale"]) * scale))
    number_h = max(24, int(h * float(tokens["commercial_number_scale"]) * scale))
    cta_h = max(12, int(h * float(tokens["cta_scale_ratio"]) * scale))
    display = font_for_role(fonts, tokens["display_font"], display_h)
    display_gold = font_for_role(fonts, tokens["display_font"], int(display_h * 1.08))
    sans = font_for_role(fonts, tokens["body_font"], support_h)
    num_font = font_for_role(fonts, tokens["commercial_font"], number_h)
    currency_font = font_for_role(fonts, tokens["body_font"], max(14, int(number_h * 0.42)))
    discount_font = font_for_role(fonts, tokens["commercial_font"], max(20, int(number_h * 0.72)))
    cta_font = font_for_role(fonts, "CTA", cta_h)
    headline = facts["headline"]
    first, last = (headline.split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}

    b1 = _draw_tracked(draw, (ox, y), first, display, fill, tracking=float(tokens["display_tracking"]), anchor="rt" if alignment == "right" else "lt")
    y = b1[3] + int(space.get("headline_internal") or 8)
    last_fill = accent if tokens.get("split_last_line_gold") else fill
    b2 = _draw_tracked(draw, (ox, y), last or first, display_gold, last_fill, tracking=20, anchor="rt" if alignment == "right" else "lt")
    boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    y = b2[3] + int(space.get("headline_internal") or 8)
    if int(tokens.get("rule_weight") or 0) > 0:
        if alignment == "right":
            draw.line((b2[0], y, ox, y), fill=accent, width=int(tokens["rule_weight"]))
        else:
            draw.line((ox, y, b2[2], y), fill=accent, width=int(tokens["rule_weight"]))
        y += int(space.get("headline_to_unit") or 16)
    else:
        y += int(space.get("headline_to_unit") or 16)

    unit = _draw_tracked(draw, (ox, y), facts["unit_type"], sans, fill, tracking=160, anchor="rt" if alignment == "right" else "lt")
    boxes["unit_type"] = unit
    y = unit[3] + int(space.get("unit_to_commercial") or 14)
    price = render_price(
        draw,
        origin=(ox, y),
        text=facts["price"],
        number_font=num_font,
        currency_font=currency_font,
        fill=number,
        alignment=alignment,
    )
    boxes["price"] = price
    y = price[3] + int(space.get("price_to_advantage") or 10)
    disc = render_percent(draw, origin=(ox, y), text=facts["discount"], font=discount_font, fill=accent, alignment=alignment)
    boxes["discount"] = disc
    y = disc[3] + max(4, int(h * 0.006))
    label = _draw_tracked(draw, (ox, y), facts["discount_label"], sans, fill, tracking=180, anchor="rt" if alignment == "right" else "lt")
    boxes["discount_label"] = label
    y = label[3] + int(space.get("commercial_to_cta") or 24)
    cta = _draw_tracked(draw, (ox, y), facts["cta"], cta_font, fill, tracking=220, anchor="rt" if alignment == "right" else "lt")
    boxes["cta"] = cta
    y = cta[3] + int(space.get("logo_clear") or 18)
    bw, bh = int(w * float(tokens["logo_scale_ratio"])), int(h * 0.045)
    if alignment == "right":
        lx = ox - bw
    else:
        lx = ox
    ly = min(y, y_limit - bh) if y_limit > bh else y
    boxes["logo"] = _place_logo(canvas, logo_rgba, max(0, lx), max(0, ly), bw, bh)
    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=boxes["logo"],
    )
    final = canvas.convert("RGB")
    contrast_report = evaluate_objects(
        fielded,
        objects,
        {"headline": fill, "unit_type": fill, "price": number, "discount": accent, "discount_label": fill, "cta": fill},
    )
    utf8 = True
    if facts.get("cta") == REQUIRED_FACTS["cta"]:
        utf8 = turkish_copy_is_valid(facts)
    overflow = any(box[3] > y_limit + 12 or box[0] < plan["anchor"]["x0"] - 8 or box[2] > plan["anchor"]["x1"] + 8 for box in boxes.values())
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": (not overflow) and contrast_report.get("pass") and utf8,
        "fit": plan["fit"],
        "plan": {k: v for k, v in plan.items() if k not in {"tokens"}},
        "image": final,
        "fielded": fielded,
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": contrast.get("treatments"),
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "tokens": {k: v for k, v in tokens.items() if k != "primary_color"},
        "groups": {
            "DisplayGroup": ["headline"],
            "SupportingInfoGroup": ["unit_type"],
            "CommercialOfferGroup": ["price", "discount", "discount_label"],
            "CTAGroup": ["cta"],
            "BrandGroup": ["project_logo"],
        },
    }


def compose_from_structured_plan(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str],
    art_plan: dict[str, Any],
    family: dict[str, Any],
    scale: float | None = None,
) -> dict[str, Any]:
    """Execute an approved StructuredArtDirectionPlanV1. Does not invent the concept."""
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard, evaluate_collisions
    from investhome_api.services.creative_director.full_frame_architectural_family import (
        apply_architectural_edge_integration,
        _paste_fitted_logo,
        _photographic_logo,
    )
    from investhome_api.services.gpt_image_design.compose import _fit_logo

    scale = float(scale or art_plan.get("scale") or 1.0)
    side = str(art_plan.get("alignment") or "left")
    if side not in {"left", "right"}:
        side = "left"
    edge = apply_architectural_edge_integration(photo, occupancy, lockup_side=side)
    fielded = edge["image"]
    fills = {"fill": IVORY, "accent": GOLD, "number": IVORY}
    tokens = execution_tokens(family)
    space = spacing_plan(family, photo.size, scale=scale)["pixels"]
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    ty = dict(art_plan.get("typography") or {})
    right_align = side == "right"
    inset = int(w * float((art_plan.get("anchor") or {}).get("inset") or 0.055))
    ax = w - inset if right_align else inset
    anchor = "rt" if right_align else "lt"
    y = int(h * float((art_plan.get("anchor") or {}).get("y") or 0.028))
    y_limit = int(h * float((art_plan.get("territories") or {}).get("type_limit_y") or 0.20))
    display_h = max(26, int(h * float(ty.get("display_scale") or tokens["display_scale"]) * scale))
    discount_h = max(24, int(h * float(ty.get("discount_scale") or 0.042) * scale))
    number_h = max(26, int(h * float(ty.get("number_scale") or 0.040) * scale))
    label_h = max(11, int(h * float(ty.get("label_scale") or 0.012) * scale))
    unit_h = max(11, int(h * float(ty.get("unit_scale") or 0.011) * scale))
    cta_h = max(12, int(h * float(ty.get("cta_scale") or 0.016) * scale))
    display = font_for_role(fonts, tokens["display_font"], display_h)
    display_gold = font_for_role(fonts, tokens["display_font"], display_h)
    discount_font = font_for_role(fonts, tokens["commercial_font"], discount_h)
    num_font = font_for_role(fonts, tokens["commercial_font"], number_h)
    currency_font = font_for_role(fonts, tokens["body_font"], max(13, int(number_h * 0.38)))
    label_font = font_for_role(fonts, tokens["body_font"], label_h)
    unit_font = font_for_role(fonts, tokens["body_font"], unit_h)
    cta_font = font_for_role(fonts, "CTA", cta_h)
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}
    logo_spec = dict(art_plan.get("logo") or {})
    placement = str(logo_spec.get("placement") or "inward_signature")

    def rule(x0: int, x1: int, yy: int, width: int = 2) -> None:
        draw.line((min(x0, x1), yy, max(x0, x1), yy), fill=fills["accent"], width=width)

    b1 = _draw_tracked(draw, (ax, y), first, display, fills["fill"], tracking=float(tokens["display_tracking"]), anchor=anchor)
    y = b1[3] + max(2, int(space.get("headline_internal") or 4) // 2)
    b2 = _draw_tracked(draw, (ax, y), last or first, display_gold, fills["accent"], tracking=12, anchor=anchor)
    boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    rule_y = b2[3] + 5
    rule(b2[0], b2[2], rule_y, 2)

    bw, bh = int(w * float(logo_spec.get("w") or 0.11)), int(h * float(logo_spec.get("h") or 0.045))
    fitted = _fit_logo(logo_rgba, bw, bh) if logo_rgba is not None else Image.new("RGBA", (max(1, bw), max(1, bh)))
    fw, fh = fitted.size
    if placement == "inward_signature":
        gap = max(16, int(w * 0.014))
        if right_align:
            lx = boxes["headline"][0] - gap - fw
            if lx < int(w * 0.58):
                lx = int(w * 0.58)
        else:
            lx = boxes["headline"][2] + gap
            if lx + fw > int(w * 0.40):
                lx = max(boxes["headline"][2] + 8, int(w * 0.40) - fw)
        ly = boxes["headline"][1]
        adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fw, ly + fh))
        boxes["logo"] = _paste_fitted_logo(canvas, adapted, lx, ly)

    y = rule_y + 6
    disc = render_percent(draw, origin=(ax, y), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment=side)
    boxes["discount"] = disc
    y = disc[3] + 2
    label = _draw_tracked(draw, (ax, y), facts["discount_label"], label_font, fills["fill"], tracking=220, anchor=anchor)
    boxes["discount_label"] = label
    rule(min(disc[0], label[0]), max(disc[2], label[2]), disc[1] - 4, 1)
    y = label[3] + 4
    price = render_price(
        draw,
        origin=(ax, y),
        text=facts["price"],
        number_font=num_font,
        currency_font=currency_font,
        fill=fills["number"],
        alignment=side,
        tracking=8.0,
    )
    boxes["price"] = price
    y = price[3] + 4
    unit = _draw_tracked(draw, (ax, y), facts["unit_type"], unit_font, fills["fill"], tracking=200, anchor=anchor)
    boxes["unit_type"] = unit
    y = unit[3] + max(8, int(h * 0.007))
    cta = _draw_tracked(draw, (ax, y), facts["cta"], cta_font, fills["fill"], tracking=260, anchor=anchor)
    boxes["cta"] = cta
    rule(cta[0], cta[2], cta[1] - 7, 1)

    if "logo" not in boxes:
        lx = ax - fw if right_align else ax
        ly = min(cta[3] + 10, h - fh - 12)
        adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fw, ly + fh))
        boxes["logo"] = _paste_fitted_logo(canvas, adapted, lx, ly)

    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=boxes["logo"],
    )
    collision = evaluate_collisions(objects=objects, occupancy=occupancy, size=canvas.size)
    hard_mask = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    hard_fail = False
    if isinstance(hard_mask, Image.Image):
        hard_fail = any(box_hits_hard(hard_mask, box, min_pixels=12) for box in boxes.values())
    final = canvas.convert("RGB")
    contrast_report = evaluate_objects(
        fielded,
        objects,
        {
            "headline": fills["fill"],
            "unit_type": fills["fill"],
            "price": fills["number"],
            "discount": fills["accent"],
            "discount_label": fills["fill"],
            "cta": fills["fill"],
        },
    )
    utf8 = True
    if facts.get("cta") == REQUIRED_FACTS["cta"]:
        utf8 = turkish_copy_is_valid(facts)
    overflow = any(box[0] < -4 or box[2] > w + 4 or box[1] < -4 or box[3] > h + 4 for box in boxes.values())
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": (not overflow) and bool(contrast_report.get("pass")) and utf8 and not hard_fail,
        "fit": {"status": "FIT" if not hard_fail else "NO_FIT", "flex_mode": f"{side.upper()}_COMMERCIAL"},
        "plan": art_plan,
        "image": final,
        "fielded": fielded,
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": edge.get("treatments"),
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "collision": collision,
        "flex_mode": f"{side.upper()}_COMMERCIAL",
        "alignment": side,
        "lockup_side": side,
        "art_direction_plan": True,
        "real_logo": logo_rgba is not None,
        "groups": {
            "DisplayGroup": ["headline"],
            "SupportingInfoGroup": ["unit_type"],
            "CommercialOfferGroup": ["price", "discount", "discount_label"],
            "CTAGroup": ["cta"],
            "BrandGroup": ["project_logo"],
        },
        "canvas": list(canvas.size),
    }


def apply_premium_field(photo: Image.Image, occupancy: dict[str, Any], mode: str) -> dict[str, Any]:
    """Tonal fields that continue the photograph. Never a hard split column."""
    from PIL import ImageChops, ImageEnhance, ImageFilter

    from investhome_api.services.creative_director.creative_family_adapter import _ramp_horizontal, _ramp_vertical, _union_l

    src = photo.convert("RGB")
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    if not isinstance(hard, Image.Image):
        hard = Image.new("L", src.size, 0)
    size = src.size
    if mode == "SKY_VEIL":
        mask = _union_l(_ramp_vertical(size, 0.0, 0.30, 200, 0), _ramp_vertical(size, 0.84, 1.0, 0, 150))
        treatments = ["sky_veil", "ground_fade", "architecture_protected"]
        darken = 0.42
        blur = 28
    elif mode == "GROUND_PLANE":
        mask = _union_l(_ramp_vertical(size, 0.0, 0.16, 150, 0), _ramp_vertical(size, 0.70, 0.86, 0, 205))
        treatments = ["ground_plane_offer_field", "sky_readability_veil", "architecture_protected"]
        darken = 0.38
        blur = 32
    else:
        corner = ImageChops.multiply(_ramp_horizontal(size, 0.30, 0.62, 210, 0), _ramp_vertical(size, 0.26, 0.58, 210, 0))
        mask = _union_l(corner, _ramp_vertical(size, 0.88, 1.0, 0, 130))
        treatments = ["asymmetric_corner_ingress", "photographic_continuation", "architecture_protected"]
        darken = 0.40
        blur = 42
    mask = mask.filter(ImageFilter.GaussianBlur(radius=blur))
    protect = hard.convert("L").filter(ImageFilter.GaussianBlur(radius=10)).point(lambda v: int(255 - v * 0.88))
    mask = ImageChops.multiply(mask, protect)
    dark = ImageEnhance.Brightness(src).enhance(darken)
    fielded = Image.composite(dark, src, mask)
    return {"image": fielded, "mask": mask, "treatments": treatments, "mode": mode, "geometry_modified": False}


def compose_premium_structured(
    photo: Image.Image,
    *,
    occupancy: dict[str, Any],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    facts: dict[str, str],
    art_plan: dict[str, Any],
    family: dict[str, Any],
    scale: float | None = None,
) -> dict[str, Any]:
    """Execute StructuredPremiumPlanV1. Whole-canvas, not a split information panel."""
    from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard, evaluate_collisions
    from investhome_api.services.creative_director.full_frame_architectural_family import _paste_fitted_logo, _photographic_logo
    from investhome_api.services.gpt_image_design.compose import _fit_logo

    mode = str(art_plan.get("reconstruction_mode") or "SKY_VEIL")
    if mode not in {"SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS"}:
        mode = "SKY_VEIL"
    scale = float(scale or art_plan.get("scale") or 1.0)
    field = apply_premium_field(photo, occupancy, mode)
    fielded = field["image"]
    fills = {"fill": IVORY, "accent": GOLD, "number": IVORY}
    tokens = execution_tokens(family)
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")

    def fsz(ratio: float, floor: int) -> int:
        return max(floor, int(h * ratio * scale))

    display = font_for_role(fonts, tokens["display_font"], fsz(0.058, 42))
    display_sm = font_for_role(fonts, tokens["display_font"], fsz(0.052, 36))
    discount_font = font_for_role(fonts, tokens["commercial_font"], fsz(0.048, 34))
    num_font = font_for_role(fonts, tokens["commercial_font"], fsz(0.036, 28))
    currency_font = font_for_role(fonts, tokens["body_font"], fsz(0.014, 13))
    label_font = font_for_role(fonts, tokens["body_font"], fsz(0.013, 12))
    unit_font = font_for_role(fonts, tokens["body_font"], fsz(0.012, 11))
    cta_font = font_for_role(fonts, "CTA", fsz(0.015, 13))
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    boxes: dict[str, tuple[int, int, int, int]] = {}
    tracking = float(tokens["display_tracking"])

    def rule(x0: int, x1: int, yy: int, width: int = 2) -> None:
        draw.line((min(x0, x1), yy, max(x0, x1), yy), fill=fills["accent"], width=width)

    if mode == "SKY_VEIL":
        b1 = _draw_tracked(draw, (int(w * 0.055), int(h * 0.042)), first, display, fills["fill"], tracking=tracking, anchor="lt")
        b2 = _draw_tracked(draw, (int(w * 0.055), b1[3] + 4), last or first, display_sm, fills["accent"], tracking=8, anchor="lt")
        boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
        rule(b2[0], b2[2], b2[3] + 6, 2)
        disc = render_percent(draw, origin=(int(w * 0.945), int(h * 0.048)), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment="right")
        boxes["discount"] = disc
        label = _draw_tracked(draw, (int(w * 0.945), disc[3] + 4), facts["discount_label"], label_font, fills["fill"], tracking=220, anchor="rt")
        boxes["discount_label"] = label
        price = render_price(draw, origin=(int(w * 0.055), int(h * 0.195)), text=facts["price"], number_font=num_font, currency_font=currency_font, fill=fills["number"], alignment="left", tracking=8.0)
        boxes["price"] = price
        unit = _draw_tracked(draw, (int(w * 0.055), price[3] + 6), facts["unit_type"], unit_font, fills["fill"], tracking=200, anchor="lt")
        boxes["unit_type"] = unit
        cta = _draw_tracked(draw, (int(w * 0.055), int(h * 0.915)), facts["cta"], cta_font, fills["fill"], tracking=260, anchor="lt")
        boxes["cta"] = cta
        rule(cta[0], cta[2], cta[1] - 8, 1)
        lx, ly, bw, bh = int(w * 0.72), int(h * 0.20), int(w * 0.20), int(h * 0.07)
    elif mode == "GROUND_PLANE":
        b1 = _draw_tracked(draw, (int(w * 0.055), int(h * 0.038)), first, display, fills["fill"], tracking=tracking, anchor="lt")
        b2 = _draw_tracked(draw, (int(w * 0.055), b1[3] + 2), last or first, display_sm, fills["accent"], tracking=8, anchor="lt")
        boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
        rule(b2[0], b2[2], b2[3] + 6, 2)
        y_offer = int(h * 0.78)
        disc = render_percent(draw, origin=(int(w * 0.055), y_offer), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment="left")
        boxes["discount"] = disc
        label = _draw_tracked(draw, (disc[2] + int(w * 0.018), disc[1] + int(h * 0.012)), facts["discount_label"], label_font, fills["fill"], tracking=200, anchor="lt")
        boxes["discount_label"] = label
        price = render_price(draw, origin=(int(w * 0.42), y_offer), text=facts["price"], number_font=num_font, currency_font=currency_font, fill=fills["number"], alignment="left", tracking=8.0)
        boxes["price"] = price
        unit = _draw_tracked(draw, (price[2] + int(w * 0.02), price[1] + int(h * 0.012)), facts["unit_type"], unit_font, fills["fill"], tracking=180, anchor="lt")
        boxes["unit_type"] = unit
        cta = _draw_tracked(draw, (int(w * 0.945), int(h * 0.915)), facts["cta"], cta_font, fills["fill"], tracking=260, anchor="rt")
        boxes["cta"] = cta
        rule(cta[0], cta[2], cta[1] - 8, 1)
        lx, ly, bw, bh = int(w * 0.055), int(h * 0.68), int(w * 0.18), int(h * 0.065)
    else:
        ax = int(w * 0.06)
        b1 = _draw_tracked(draw, (ax, int(h * 0.05)), first, display, fills["fill"], tracking=tracking, anchor="lt")
        b2 = _draw_tracked(draw, (ax + int(w * 0.018), b1[3] + 2), last or first, display_sm, fills["accent"], tracking=8, anchor="lt")
        boxes["headline"] = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
        rule(b2[0], b2[2], b2[3] + 6, 2)
        disc = render_percent(draw, origin=(ax, b2[3] + int(h * 0.028)), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment="left")
        boxes["discount"] = disc
        label = _draw_tracked(draw, (ax + int(w * 0.012), disc[3] + 4), facts["discount_label"], label_font, fills["fill"], tracking=220, anchor="lt")
        boxes["discount_label"] = label
        price = render_price(draw, origin=(ax + int(w * 0.04), label[3] + int(h * 0.016)), text=facts["price"], number_font=num_font, currency_font=currency_font, fill=fills["number"], alignment="left", tracking=8.0)
        boxes["price"] = price
        unit = _draw_tracked(draw, (ax + int(w * 0.04), price[3] + 6), facts["unit_type"], unit_font, fills["fill"], tracking=200, anchor="lt")
        boxes["unit_type"] = unit
        cta = _draw_tracked(draw, (int(w * 0.06), int(h * 0.92)), facts["cta"], cta_font, fills["fill"], tracking=260, anchor="lt")
        boxes["cta"] = cta
        rule(cta[0], cta[2], cta[1] - 8, 1)
        lx, ly, bw, bh = int(w * 0.34), int(h * 0.36), int(w * 0.19), int(h * 0.07)

    fitted = _fit_logo(logo_rgba, bw, bh) if logo_rgba is not None else Image.new("RGBA", (max(1, bw), max(1, bh)))
    fw, fh = fitted.size
    adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fw, ly + fh))
    boxes["logo"] = _paste_fitted_logo(canvas, adapted, lx, ly)
    objects = _objects(
        canvas.size,
        headline=boxes["headline"],
        unit=boxes["unit_type"],
        price=boxes["price"],
        discount=boxes["discount"],
        label=boxes["discount_label"],
        cta=boxes["cta"],
        logo=boxes["logo"],
    )
    collision = evaluate_collisions(objects=objects, occupancy=occupancy, size=canvas.size)
    hard_fail = False
    if isinstance(hard, Image.Image):
        hard_fail = any(box_hits_hard(hard, box, min_pixels=18) for role, box in boxes.items() if role != "logo")
    final = canvas.convert("RGB")
    contrast_report = evaluate_objects(
        fielded,
        objects,
        {
            "headline": fills["fill"],
            "unit_type": fills["fill"],
            "price": fills["number"],
            "discount": fills["accent"],
            "discount_label": fills["fill"],
            "cta": fills["fill"],
        },
    )
    utf8 = turkish_copy_is_valid(facts) if facts.get("cta") == REQUIRED_FACTS["cta"] else True
    overflow = any(box[0] < -4 or box[2] > w + 4 or box[1] < -4 or box[3] > h + 4 for box in boxes.values())
    return {
        "schema": "GraphicDesignCompositorV3",
        "solved": (not overflow) and bool(contrast_report.get("pass")) and utf8 and not hard_fail,
        "fit": {"status": "FIT" if not hard_fail else "NO_FIT", "flex_mode": mode},
        "plan": art_plan,
        "image": final,
        "fielded": fielded,
        "field_mask": field["mask"],
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": field.get("treatments"),
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "collision": collision,
        "flex_mode": mode,
        "reconstruction_mode": mode,
        "art_direction_plan": True,
        "real_logo": logo_rgba is not None,
        "split_panel": False,
        "groups": {
            "DisplayGroup": ["headline"],
            "SupportingInfoGroup": ["unit_type"],
            "CommercialOfferGroup": ["price", "discount", "discount_label"],
            "CTAGroup": ["cta"],
            "BrandGroup": ["project_logo"],
        },
        "canvas": list(canvas.size),
        "brand_anchor": dict(art_plan.get("brand_anchor") or {}),
    }
