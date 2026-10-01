"""GraphicDesignCompositor relational V4 — groups first, relationships, no corner scatter."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from investhome_api.services.creative_director.brand_cta_engines import compose_editorial_cta, integrate_brand
from investhome_api.services.creative_director.commercial_number_renderer import render_percent, render_price
from investhome_api.services.creative_director.commercial_offer_composer import measure_production_copy, measure_tracked, offer_layout_v2
from investhome_api.services.creative_director.creative_collision_engine import box_hits_hard, evaluate_collisions
from investhome_api.services.creative_director.creative_contrast_engine import evaluate_objects
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_font_registry import font_for_role
from investhome_api.services.creative_director.creative_relationship_system import (
    compositional_gravity,
    groups_from_objects,
    reading_flow,
    temple_relationship_graph,
)
from investhome_api.services.creative_director.full_frame_architectural_family import _paste_fitted_logo, _photographic_logo
from investhome_api.services.creative_director.graphic_field_engine import apply_graphic_fields
from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    GOLD,
    IVORY,
    _draw_tracked,
    _objects,
    turkish_copy_is_valid,
)
from investhome_api.services.creative_director.typographic_composition_engine import compose_campaign_type
from investhome_api.services.gpt_image_design.compose import _fit_logo


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


def compose_relational_v4(
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
    facts = _facts(facts)
    mode = str(art_plan.get("reconstruction_mode") or "SKY_VEIL")
    if mode not in {"SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS"}:
        mode = "SKY_VEIL"
    scale = float(scale or art_plan.get("scale") or 1.0)
    field = apply_graphic_fields(photo, occupancy, mode)
    fielded = field["image"]
    fills = {"fill": IVORY, "accent": GOLD, "number": IVORY}
    tokens = execution_tokens(family)
    canvas = fielded.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    arch_x = float(occupancy.get("architecture_centroid_x") or 0.55)

    def fsz(ratio: float, floor: int) -> int:
        return max(floor, int(h * ratio * scale))

    display = font_for_role(fonts, tokens["display_font"], fsz(0.052, 40))
    display_sm = font_for_role(fonts, tokens["display_font"], fsz(0.046, 34))
    discount_font = font_for_role(fonts, tokens["commercial_font"], fsz(0.044, 32))
    num_font = font_for_role(fonts, tokens["commercial_font"], fsz(0.034, 26))
    currency_font = font_for_role(fonts, tokens["body_font"], fsz(0.013, 12))
    label_font = font_for_role(fonts, tokens["body_font"], fsz(0.012, 11))
    unit_font = font_for_role(fonts, tokens["body_font"], fsz(0.011, 10))
    cta_font = font_for_role(fonts, "CTA", fsz(0.014, 12))
    first, last = (facts["headline"].split(" ", 1) + [""])[:2]
    metrics = measure_production_copy(fonts=fonts, family=family, canvas=(w, h), scale=scale)
    metrics["discount"]["width"], metrics["discount"]["height"] = measure_tracked(facts["discount"], discount_font, 8)
    metrics["discount_label"]["width"], metrics["discount_label"]["height"] = measure_tracked(facts["discount_label"], label_font, 180)
    metrics["price"]["width"], metrics["price"]["height"] = measure_tracked(facts["price"], num_font, 8)
    unit_w, unit_h = measure_tracked(facts["unit_type"], unit_font, 180)
    cta_w, cta_h = measure_tracked(facts["cta"], cta_font, 240)

    if arch_x < 0.42:
        ox = int(w * 0.58)
    else:
        ox = int(w * 0.055)
    if mode == "GROUND_PLANE":
        origin = (ox, int(h * 0.64))
        geometry = "paired_row"
    elif mode == "CORNER_INGRESS":
        origin = (ox if ox < w * 0.4 else int(w * 0.07), int(h * 0.20))
        geometry = "stacked_statement"
    else:
        origin = (ox, int(h * 0.046))
        geometry = "stacked_statement"
    hint = art_plan.get("origin") if isinstance(art_plan.get("origin"), dict) else {}
    if hint.get("x") is not None:
        ox = int(w * max(0.03, min(0.62, float(hint["x"]))))
    if hint.get("y") is not None:
        origin = (ox, int(h * max(0.02, min(0.72, float(hint["y"])))))
    else:
        origin = (ox, origin[1])

    campaign = compose_campaign_type(
        draw,
        origin=origin,
        first=first,
        last=last or first,
        display=display,
        display_sm=display_sm,
        fill=fills["fill"],
        accent=fills["accent"],
        tracking=float(tokens["display_tracking"]),
    )
    offer_origin = (campaign["headline"][0], campaign["headline"][3] + int(h * 0.022))
    offer = offer_layout_v2(origin=offer_origin, metrics=metrics, canvas=(w, h), geometry=geometry)
    rx0, ry0, rx1, ry1 = offer["rule_px"]
    draw.line((rx0, ry0, rx1, ry1), fill=fills["accent"], width=2)
    disc = render_percent(draw, origin=(offer["boxes"]["discount"][0], offer["boxes"]["discount"][1]), text=facts["discount"], font=discount_font, fill=fills["accent"], alignment="left")
    label = _draw_tracked(draw, (offer["boxes"]["discount_label"][0], offer["boxes"]["discount_label"][1]), facts["discount_label"], label_font, fills["fill"], tracking=180, anchor="lt")
    price = render_price(draw, origin=(offer["boxes"]["price"][0], offer["boxes"]["price"][1]), text=facts["price"], number_font=num_font, currency_font=currency_font, fill=fills["number"], alignment="left", tracking=8.0)
    offer_bbox = (
        min(disc[0], label[0], price[0], campaign["headline"][0]),
        min(disc[1], label[1], price[1]),
        max(disc[2], label[2], price[2]),
        max(disc[3], label[3], price[3]),
    )
    action = compose_editorial_cta(
        offer_bbox=offer_bbox,
        unit_size=(unit_w, unit_h),
        cta_size=(cta_w, cta_h),
        canvas=(w, h),
        mode="SKY_VEIL",
        alignment="left",
    )
    # Keep ACTION in the same column as the offer (never a detached bottom caption).
    unit = _draw_tracked(draw, (action["unit_px"][0], action["unit_px"][1]), facts["unit_type"], unit_font, fills["fill"], tracking=180, anchor="lt")
    cta = _draw_tracked(draw, (action["cta_px"][0], action["cta_px"][1]), facts["cta"], cta_font, fills["fill"], tracking=240, anchor="lt")
    draw.line(action["rule_px"][:2] + action["rule_px"][2:], fill=fills["accent"], width=1)

    lw, lh = int(w * 0.16), int(h * 0.06)
    brand = integrate_brand(
        campaign_bbox=campaign["headline"],
        offer_bbox=offer_bbox,
        architecture_x=arch_x,
        canvas=(w, h),
        logo_size=(lw, lh),
        mode="SKY_VEIL",
    )
    lx, ly, _lx1, _ly1 = brand["px"]
    fitted = _fit_logo(logo_rgba, lw, lh) if logo_rgba is not None else Image.new("RGBA", (max(1, lw), max(1, lh)))
    fw, fh = fitted.size
    if isinstance(hard, Image.Image) and box_hits_hard(hard, (lx, ly, lx + fw, ly + fh), min_pixels=12):
        lx = max(int(w * 0.05), offer_bbox[2] + int(w * 0.03))
        ly = offer_bbox[1]
        if box_hits_hard(hard, (lx, ly, lx + fw, ly + fh), min_pixels=12):
            lx = campaign["headline"][0]
            ly = cta[3] + int(h * 0.02)
    adapted = _photographic_logo(fitted, fielded, (lx, ly, lx + fw, ly + fh))
    logo_box = _paste_fitted_logo(canvas, adapted, lx, ly)
    boxes = {
        "headline": campaign["headline"],
        "discount": disc,
        "discount_label": label,
        "price": price,
        "unit_type": unit,
        "cta": cta,
        "logo": logo_box,
    }
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
    groups = groups_from_objects(objects, mode=mode)
    graph = temple_relationship_graph(mode=mode)
    gravity = compositional_gravity(occupancy, objects)
    flow = reading_flow(objects)
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
        "schema": "GraphicDesignCompositorV4",
        "solved": (not overflow) and bool(contrast_report.get("pass")) and utf8 and not hard_fail and not flow.get("rejected"),
        "fit": {"status": "FIT" if not hard_fail else "NO_FIT", "flex_mode": mode},
        "plan": art_plan,
        "image": final,
        "fielded": fielded,
        "field_mask": field["mask"],
        "graphic_fields": field.get("fields"),
        "foundation": photo,
        "objects": objects,
        "facts": facts,
        "fills": {k: list(v) for k, v in fills.items()},
        "contrast_treatments": [f["kind"] for f in field.get("fields") or []],
        "contrast": contrast_report,
        "utf8_valid": utf8,
        "overflow": overflow,
        "collision": collision,
        "flex_mode": mode,
        "reconstruction_mode": mode,
        "art_direction_plan": True,
        "real_logo": logo_rgba is not None,
        "split_panel": False,
        "groups": {g["group_id"]: g["children"] for g in groups},
        "groups_v2": groups,
        "relationship_graph": graph,
        "gravity": gravity,
        "reading_flow": flow,
        "offer_v2": {k: v for k, v in offer.items() if k != "boxes"},
        "brand_integration": {k: v for k, v in brand.items() if k != "px"},
        "cta_composer": {k: v for k, v in action.items() if "px" not in k},
        "typography": campaign,
        "canvas": list(canvas.size),
        "brand_anchor": dict(art_plan.get("brand_anchor") or {}),
    }


def reconstruct_reference_grammar(
    reference: Image.Image,
    cmap: dict[str, Any],
    *,
    fonts: dict[str, Any],
    family: dict[str, Any],
    logo_rgba: Image.Image | None,
    canvas: tuple[int, int] = (1088, 1360),
) -> dict[str, Any]:
    """Rebuild composition grammar with placeholders. Does not copy reference copy."""
    w, h = canvas
    photo = ImageOps.grayscale(reference.convert("RGB")).convert("RGB")
    photo = photo.resize((w, h), Image.Resampling.LANCZOS)
    photo = ImageEnhance.Brightness(photo).enhance(0.32)
    photo = photo.filter(ImageFilter.GaussianBlur(radius=12))
    occupancy = {
        "architecture_centroid_x": float((cmap.get("center_of_visual_gravity") or {}).get("photo", [0.55, 0.48])[0]),
        "layers": {
            "hard_protected": Image.new("L", (w, h), 0),
            "sky": Image.new("L", (w, h), 40),
        },
    }
    grav = cmap.get("center_of_visual_gravity") or {}
    photo_c = grav.get("photo") or [0.55, 0.48]
    ImageDraw.Draw(occupancy["layers"]["hard_protected"]).ellipse(
        (int(w * (photo_c[0] - 0.18)), int(h * (photo_c[1] - 0.22)), int(w * (photo_c[0] + 0.18)), int(h * (photo_c[1] + 0.28))),
        fill=180,
    )
    groups = list(cmap.get("primary_secondary_tertiary_groups") or [])
    axis = str(cmap.get("dominant_compositional_axis") or "vertical")
    mode = "GROUND_PLANE" if groups and float(groups[0].get("y") or 0) > 0.45 else "SKY_VEIL"
    if axis == "horizontal":
        mode = "GROUND_PLANE"
    plan = {"schema": "RelationalCompositionPlanV1", "reconstruction_mode": mode, "scale": 1.0, "calibration": True}
    pack = compose_relational_v4(
        photo,
        occupancy=occupancy,
        fonts=fonts,
        logo_rgba=logo_rgba,
        facts=_facts(None),
        art_plan=plan,
        family=family,
        scale=1.0,
    )
    pack["schema"] = "ReferenceGrammarReconstructionV1"
    pack["source_filename"] = cmap.get("filename")
    pack["source_axis"] = axis
    pack["placeholders"] = ["PHOTO", "HEADLINE", "OFFER", "LOGO", "CTA"]
    return pack
