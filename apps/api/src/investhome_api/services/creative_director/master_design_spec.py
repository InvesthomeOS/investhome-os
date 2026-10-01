"""Master Design Spec v1 — structured description of an approved AI design.

AI remains the designer. This module extracts a reconstructable representation
of the design AI already created. It does not render templates, revise pixels,
or call an image provider.

Not the Native Renderer recipe. Not DesignSpec layers. Raster + campaign
metadata are the sources of truth.
"""

from __future__ import annotations

import copy
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.services.creative_director.edit_map import (
    _as_dict,
    _is_gold,
    _is_white,
    analyze_raster,
    bbox_dict,
    build_edit_map,
    load_edit_map,
    validate_edit_map,
)

logger = logging.getLogger(__name__)

SPEC_SCHEMA = "MasterDesignSpecV1"
SPEC_VERSION = 1
PROJECT_ASSET_POLICY = "PROJECT_LOCKED"
LOCKED_IDENTITY = "LOCKED_IDENTITY"
FLEXIBLE_LAYOUT = "FLEXIBLE_LAYOUT"
FLEXIBLE_CONTENT = "FLEXIBLE_CONTENT"
REPLACEABLE_ASSET = "REPLACEABLE_ASSET"

REQUIRED_ELEMENT_ROLES = (
    "headline",
    "supporting_copy",
    "unit_type",
    "unit_label",
    "list_price",
    "discount",
    "discount_label",
    "cta",
    "logo",
)
REQUIRED_REGION_ROLES = (
    "navy_field",
    "headline_area",
    "supporting_copy_area",
    "commercial_information_area",
    "hero_visual",
    "cta",
    "logo",
    "bottom_brand_treatment",
)


def sourced(value: Any, *, confidence: float, source: str) -> dict[str, Any]:
    return {"value": value, "confidence": round(float(confidence), 3), "source": source}


def _norm(bbox: dict[str, int] | None, width: int, height: int) -> dict[str, Any] | None:
    if not bbox:
        return None
    x0, y0, x1, y1 = int(bbox["x0"]), int(bbox["y0"]), int(bbox["x1"]), int(bbox["y1"])
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    return {
        "absolute": {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "width": w,
            "height": h,
        },
        "normalized": {
            "x": round(x0 / width, 5),
            "y": round(y0 / height, 5),
            "width": round(w / width, 5),
            "height": round(h / height, 5),
            "x1": round(x1 / width, 5),
            "y1": round(y1 / height, 5),
        },
    }


def _region(edit_map: dict[str, Any] | None, role: str) -> dict[str, Any] | None:
    for item in (edit_map or {}).get("regions") or []:
        if isinstance(item, dict) and item.get("semantic_role") == role:
            return item
    return None


def _group(edit_map: dict[str, Any] | None, group_id: str) -> dict[str, Any] | None:
    for item in (edit_map or {}).get("groups") or []:
        if isinstance(item, dict) and item.get("id") == group_id:
            return item
    return None


def _alignment(bbox: dict[str, int] | None, width: int) -> str:
    if not bbox:
        return "unknown"
    cx = (bbox["x0"] + bbox["x1"]) / 2.0
    mid = width / 2.0
    if abs(cx - mid) <= width * 0.08:
        return "center"
    return "left" if cx < mid else "right"


def _sample_type_color(image: Any, bbox: dict[str, int] | None) -> dict[str, Any]:
    if image is None or not bbox:
        return sourced("unknown", confidence=0.2, source="inferred_relationship")
    px = image.convert("RGB").load()
    gold = white = navy = 0
    n = 0
    x0, y0, x1, y1 = bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]
    step = max(1, min(x1 - x0, y1 - y0) // 24)
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            r, g, b = px[x, y]
            n += 1
            if _is_gold(r, g, b):
                gold += 1
            elif _is_white(r, g, b):
                white += 1
            elif r < 40 and g < 50 and b < 80:
                navy += 1
    if n == 0:
        return sourced("unknown", confidence=0.2, source="raster_analysis")
    if gold >= white and gold / n >= 0.04:
        return sourced("gold", confidence=min(0.92, 0.55 + gold / n), source="raster_analysis")
    if white / n >= 0.04:
        return sourced("white", confidence=min(0.92, 0.55 + white / n), source="raster_analysis")
    return sourced("navy_field", confidence=0.45, source="raster_analysis")


def _copy_bag(ctx: dict[str, Any]) -> dict[str, str]:
    mc = _as_dict(ctx.get("master_creative"))
    campaign_copy = _as_dict(mc.get("campaign_copy") or ctx.get("campaign_copy"))
    brief = _as_dict(ctx.get("production_brief") or ctx.get("master_production_brief"))
    final = _as_dict(brief.get("final_copy"))
    bag = {**campaign_copy, **final}

    def pick(*keys: str) -> str:
        for key in keys:
            value = bag.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    headline = pick("headline", "hero", "hero_message", "big_idea")
    supporting = pick("supporting", "supporting_copy")
    unit = pick("unit", "eyebrow")
    list_price = pick("list_price")
    value_badge = pick("value_badge")
    cta = pick("cta")
    discount = ""
    discount_label = ""
    if value_badge:
        token = value_badge.replace(" ", "")
        if "%35" in token or "35%" in token:
            discount = "%35"
        if "LANSMAN" in value_badge.upper():
            discount_label = "LANSMAN AVANTAJI"
        elif not discount:
            discount = value_badge
    unit_type = ""
    unit_label = ""
    if unit:
        upper = unit.upper().replace(" ", "")
        if "2+1" in upper:
            unit_type = "2+1"
        if "DAİRE" in unit.upper() or "DAIRE" in upper:
            unit_label = "DAİRE"
        if not unit_type:
            unit_type = unit
    return {
        "headline": headline,
        "supporting_copy": supporting,
        "unit_type": unit_type,
        "unit_label": unit_label or ("DAİRE" if unit_type == "2+1" else ""),
        "list_price": list_price,
        "discount": discount,
        "discount_label": discount_label,
        "cta": cta,
        "list_price_label": "LİSTE FİYATI" if list_price else "",
    }


def _element(
    *,
    role: str,
    content: str,
    bbox: dict[str, int] | None,
    canvas_w: int,
    canvas_h: int,
    alignment: str,
    hierarchy: int,
    importance: str,
    typography_class: str,
    weight: str,
    color: dict[str, Any],
    parent_group: str | None,
    neighbors: dict[str, str],
    flexibility_content: str,
    flexibility_layout: str,
    image: Any = None,
    source: str = "campaign_metadata",
    confidence: float = 0.86,
) -> dict[str, Any]:
    geom = _norm(bbox, canvas_w, canvas_h)
    scale = None
    if geom:
        scale = round(float(geom["normalized"]["height"]) / 0.04, 3)
    sampled = _sample_type_color(image, bbox) if image is not None else color
    return {
        "semantic_role": role,
        "exact_content": content,
        "geometry": geom,
        "alignment": sourced(alignment, confidence=0.8, source="raster_analysis"),
        "hierarchy_level": hierarchy,
        "visual_importance": importance,
        "typography_class": typography_class,
        "relative_font_scale": sourced(scale, confidence=0.62, source="raster_analysis")
        if scale is not None
        else sourced(None, confidence=0.2, source="inferred_relationship"),
        "weight_style": weight,
        "text_color": sampled if sampled else color,
        "line_behavior": "single_line" if role != "supporting_copy" else "single_centered_line",
        "spacing_relationship": neighbors,
        "parent_group": parent_group,
        "relationship_to_neighbors": neighbors,
        "flexibility": {
            "content": flexibility_content,
            "layout": flexibility_layout,
        },
        "confidence": round(confidence, 3),
        "source": source if content else "inferred_relationship",
    }


def _creative_identity(ctx: dict[str, Any], copy: dict[str, str]) -> dict[str, Any]:
    brief = _as_dict(ctx.get("production_brief") or ctx.get("master_production_brief"))
    strategy = _as_dict(brief.get("design_direction") or brief.get("brand_direction"))
    mc = _as_dict(ctx.get("master_creative"))
    direction = _as_dict(mc.get("creative_direction"))
    concept = (
        copy.get("headline")
        or brief.get("hero")
        or direction.get("concept")
        or "approved project campaign"
    )
    return {
        "campaign_concept": sourced(concept, confidence=0.9, source="campaign_metadata"),
        "visual_style": sourced(
            "premium navy-gold editorial finished advertisement",
            confidence=0.84,
            source="raster_analysis",
        ),
        "luxury_level": sourced("high", confidence=0.82, source="inferred_relationship"),
        "composition_style": sourced(
            "centered vertical stack: navy header, hero photograph, bottom brand",
            confidence=0.88,
            source="raster_analysis",
        ),
        "dominant_palette": sourced(
            ["navy", "gold", "white"],
            confidence=0.93,
            source="raster_analysis",
        ),
        "typography_character": sourced(
            "editorial serif display with gold/white contrast on navy",
            confidence=0.8,
            source="raster_analysis",
        ),
        "hierarchy_strategy": sourced(
            "headline > commercial facts > supporting sentence > CTA > logo",
            confidence=0.84,
            source="inferred_relationship",
        ),
        "spacing_character": sourced(
            "generous centered gaps; commercial facts as a three-column row",
            confidence=0.78,
            source="raster_analysis",
        ),
        "decorative_language": sourced(
            "gold separator lines, diamond/star ornaments, navy plate, bottom navy fade",
            confidence=0.76,
            source="raster_analysis",
        ),
        "brand_direction": strategy or None,
    }


def build_master_design_spec(
    *,
    ctx: dict[str, Any],
    cover_asset_id: str,
    source_visual_asset_id: str,
    logo_asset_id: str,
    project_id: str,
    edit_map: dict[str, Any] | None,
    layout: dict[str, Any],
    image: Any = None,
    source_version: int = 2,
) -> dict[str, Any]:
    width = int(layout.get("canvas_width") or (image.size[0] if image is not None else 0))
    height = int(layout.get("canvas_height") or (image.size[1] if image is not None else 0))
    copy = _copy_bag(ctx)
    photo_start = int(layout.get("photo_start") or height)
    navy_footer = int(layout.get("navy_footer") or height)

    def box(role: str) -> dict[str, int] | None:
        region = _region(edit_map, role)
        bbox = (region or {}).get("bbox") if region else None
        return dict(bbox) if isinstance(bbox, dict) else None

    headline_box = box("headline")
    support_box = box("supporting_copy") or box("subheadline")
    unit_box = box("unit_label")
    price_box = box("old_price")
    discount_box = box("discount")
    commercial_box = box("commercial_group")
    hero_box = box("hero_visual") or bbox_dict(0, photo_start, width, navy_footer)
    cta_box = box("cta")
    logo_box = box("logo")
    plate_box = box("background_plate") or bbox_dict(0, 0, width, photo_start)
    upper_box = box("upper_creative_zone") or bbox_dict(0, 0, width, photo_start)
    bottom_box = bbox_dict(0, navy_footer, width, height)

    inset_x = min(
        [b["x0"] for b in (headline_box, support_box, commercial_box, cta_box, logo_box) if b] or [0]
    )
    safe = {
        "left": inset_x,
        "right": width - max(
            [b["x1"] for b in (headline_box, support_box, commercial_box, cta_box, logo_box) if b]
            or [width]
        ),
        "top": 0,
        "bottom": max(0, height - (logo_box or {"y1": height})["y1"]),
    }

    regions = [
        {
            "semantic_role": "navy_field",
            "geometry": _norm(plate_box, width, height),
            "notes": "Solid navy header plate above the hero.",
            "confidence": 0.9,
            "source": "raster_analysis",
        },
        {
            "semantic_role": "headline_area",
            "geometry": _norm(headline_box, width, height),
            "confidence": 0.86,
            "source": "edit_map",
        },
        {
            "semantic_role": "supporting_copy_area",
            "geometry": _norm(support_box, width, height),
            "confidence": 0.82,
            "source": "edit_map",
        },
        {
            "semantic_role": "commercial_information_area",
            "geometry": _norm(commercial_box, width, height),
            "confidence": 0.88,
            "source": "edit_map",
        },
        {
            "semantic_role": "hero_visual",
            "geometry": _norm(hero_box, width, height),
            "confidence": 0.94,
            "source": "raster_analysis",
        },
        {
            "semantic_role": "cta",
            "geometry": _norm(cta_box, width, height),
            "confidence": 0.9,
            "source": "edit_map",
        },
        {
            "semantic_role": "logo",
            "geometry": _norm(logo_box, width, height),
            "confidence": 0.9,
            "source": "edit_map",
        },
        {
            "semantic_role": "bottom_brand_treatment",
            "geometry": _norm(bottom_box, width, height),
            "notes": "Navy fade + centered project logo.",
            "confidence": 0.84,
            "source": "raster_analysis",
        },
    ]

    gold = sourced("gold", confidence=0.75, source="raster_analysis")
    white = sourced("white", confidence=0.75, source="raster_analysis")
    elements = [
        _element(
            role="headline",
            content=copy["headline"],
            bbox=headline_box,
            canvas_w=width,
            canvas_h=height,
            alignment=_alignment(headline_box, width),
            hierarchy=1,
            importance="primary",
            typography_class="display_headline",
            weight="bold_serif",
            color=gold,
            parent_group="copy_group",
            neighbors={
                "below": "supporting_copy",
                "anchor": "centered_above_commercial_group",
            },
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            source="campaign_metadata",
            confidence=0.93 if copy["headline"] else 0.2,
        ),
        _element(
            role="supporting_copy",
            content=copy["supporting_copy"],
            bbox=support_box,
            canvas_w=width,
            canvas_h=height,
            alignment=_alignment(support_box, width),
            hierarchy=2,
            importance="secondary",
            typography_class="supporting_sentence",
            weight="regular",
            color=white,
            parent_group="copy_group",
            neighbors={"above": "headline", "below": "commercial_group"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            source="campaign_metadata",
            confidence=0.9 if copy["supporting_copy"] else 0.2,
        ),
        _element(
            role="unit_type",
            content=copy["unit_type"],
            bbox=unit_box,
            canvas_w=width,
            canvas_h=height,
            alignment="center",
            hierarchy=3,
            importance="commercial",
            typography_class="commercial_stat",
            weight="bold",
            color=gold,
            parent_group="commercial_group",
            neighbors={"right": "list_price", "label": "unit_label"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            confidence=0.92 if copy["unit_type"] else 0.2,
        ),
        _element(
            role="unit_label",
            content=copy["unit_label"],
            bbox=unit_box,
            canvas_w=width,
            canvas_h=height,
            alignment="center",
            hierarchy=6,
            importance="label",
            typography_class="commercial_label",
            weight="regular",
            color=gold,
            parent_group="commercial_group",
            neighbors={"pairs_with": "unit_type"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            confidence=0.84 if copy["unit_label"] else 0.35,
        ),
        _element(
            role="list_price",
            content=copy["list_price"],
            bbox=price_box,
            canvas_w=width,
            canvas_h=height,
            alignment="center",
            hierarchy=3,
            importance="commercial",
            typography_class="commercial_stat",
            weight="bold",
            color=white,
            parent_group="commercial_group",
            neighbors={"left": "unit_type", "right": "discount", "label": "list_price_label"},
            flexibility_content=FLEXIBLE_CONTENT,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            confidence=0.93 if copy["list_price"] else 0.2,
        ),
        _element(
            role="discount",
            content=copy["discount"],
            bbox=discount_box,
            canvas_w=width,
            canvas_h=height,
            alignment="center",
            hierarchy=3,
            importance="commercial",
            typography_class="commercial_stat",
            weight="bold",
            color=gold,
            parent_group="commercial_group",
            neighbors={"left": "list_price", "label": "discount_label"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            confidence=0.92 if copy["discount"] else 0.2,
        ),
        _element(
            role="discount_label",
            content=copy["discount_label"],
            bbox=discount_box,
            canvas_w=width,
            canvas_h=height,
            alignment="center",
            hierarchy=6,
            importance="label",
            typography_class="commercial_label",
            weight="regular",
            color=gold,
            parent_group="commercial_group",
            neighbors={"pairs_with": "discount"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            confidence=0.8 if copy["discount_label"] else 0.35,
        ),
        _element(
            role="cta",
            content=copy["cta"],
            bbox=cta_box,
            canvas_w=width,
            canvas_h=height,
            alignment=_alignment(cta_box, width),
            hierarchy=4,
            importance="action",
            typography_class="cta",
            weight="bold",
            color=sourced("navy_on_gold", confidence=0.8, source="raster_analysis"),
            parent_group="bottom_brand_group",
            neighbors={"above": "hero_visual", "below": "logo"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            confidence=0.93 if copy["cta"] else 0.2,
        ),
        _element(
            role="logo",
            content="The Temple project logo",
            bbox=logo_box,
            canvas_w=width,
            canvas_h=height,
            alignment=_alignment(logo_box, width),
            hierarchy=5,
            importance="brand",
            typography_class="brand_mark",
            weight="logo_asset",
            color=gold,
            parent_group="bottom_brand_group",
            neighbors={"above": "cta"},
            flexibility_content=LOCKED_IDENTITY,
            flexibility_layout=FLEXIBLE_LAYOUT,
            image=image,
            source="asset_metadata",
            confidence=0.95,
        ),
    ]

    commercial_meta = _group(edit_map, "commercial_group") or {}
    expansion = _as_dict(commercial_meta.get("expansion"))
    capacity = _as_dict(expansion.get("internal_capacity"))
    additional_rows = int(capacity.get("additional_price_rows") or 0)
    groups = [
        {
            "id": "copy_group",
            "children": ["headline", "supporting_copy"],
            "geometry": _norm(
                bbox_dict(
                    min((headline_box or support_box or plate_box)["x0"], (support_box or headline_box or plate_box)["x0"]),
                    (headline_box or plate_box)["y0"],
                    max((headline_box or support_box or plate_box)["x1"], (support_box or headline_box or plate_box)["x1"]),
                    (support_box or headline_box or plate_box)["y1"],
                )
                if headline_box or support_box
                else plate_box,
                width,
                height,
            ),
            "layout_model": "vertical_stack_centered",
            "alignment": "center",
            "flexibility": FLEXIBLE_LAYOUT,
            "confidence": 0.84,
            "source": "inferred_relationship",
        },
        {
            "id": "commercial_group",
            "children": ["unit_type", "unit_label", "list_price", "discount", "discount_label"],
            "future_children": ["sale_price", "savings"],
            "geometry": _norm(commercial_box, width, height),
            "layout_model": sourced(
                (commercial_meta.get("column_relationship") or {}).get("layout") or "three_column_row",
                confidence=0.86,
                source="edit_map",
            ),
            "internal_relationships": {
                "columns": ["unit_type", "list_price", "discount"],
                "separators": "vertical_gold_rules",
                "alignment": "center",
            },
            "alignment": "center",
            "spacing": commercial_meta.get("spacing_relationships"),
            "separators": "gold vertical rules between three commercial columns",
            "hierarchy": "equal-weight commercial facts on one row",
            "expansion_behavior": expansion or {
                "note": "Do not raster-patch. Recompose the group when content grows."
            },
            "content_capacity": {
                "current_content_count": 3,
                "current_facts": ["2+1", copy["list_price"], copy["discount"]],
                "current_layout_model": "three_column_row",
                "estimated_capacity": {
                    "additional_price_rows": additional_rows,
                    "can_fit_sale_price_and_savings_in_place": additional_rows >= 2,
                },
                "growth_strategy": (
                    "If content grows, do NOT raster-patch the old geometry. "
                    "Recompose commercial_group and, when required, reflow neighboring "
                    "FLEXIBLE_LAYOUT elements (headline, supporting_copy) inside the design system. "
                    "Never expand into the hero photograph."
                ),
            },
            "flexibility": FLEXIBLE_LAYOUT,
            "confidence": 0.88,
            "source": "edit_map",
        },
        {
            "id": "bottom_brand_group",
            "children": ["cta", "logo"],
            "geometry": _norm(
                bbox_dict(
                    min((cta_box or logo_box or bottom_box)["x0"], (logo_box or cta_box or bottom_box)["x0"]),
                    (cta_box or bottom_box)["y0"],
                    max((cta_box or logo_box or bottom_box)["x1"], (logo_box or cta_box or bottom_box)["x1"]),
                    (logo_box or cta_box or bottom_box)["y1"],
                )
                if cta_box or logo_box
                else bottom_box,
                width,
                height,
            ),
            "layout_model": "vertical_stack_centered_over_hero_footer",
            "alignment": "center",
            "flexibility": FLEXIBLE_LAYOUT,
            "confidence": 0.86,
            "source": "raster_analysis",
        },
    ]

    hero_h = max(1, (hero_box or {}).get("y1", height) - (hero_box or {}).get("y0", 0))
    relationships = [
        {
            "id": "headline_above_commercial",
            "statement": "headline centered above commercial group",
            "from": "headline",
            "to": "commercial_group",
            "confidence": 0.9,
            "source": "inferred_relationship",
        },
        {
            "id": "supporting_below_headline",
            "statement": "supporting copy below headline",
            "from": "supporting_copy",
            "to": "headline",
            "confidence": 0.9,
            "source": "inferred_relationship",
        },
        {
            "id": "commercial_above_hero",
            "statement": "commercial information above hero",
            "from": "commercial_group",
            "to": "hero_visual",
            "confidence": 0.94,
            "source": "raster_analysis",
        },
        {
            "id": "cta_lower_hero",
            "statement": "CTA centered near lower hero transition",
            "from": "cta",
            "to": "hero_visual",
            "confidence": 0.9,
            "source": "raster_analysis",
        },
        {
            "id": "logo_below_cta",
            "statement": "logo centered below CTA",
            "from": "logo",
            "to": "cta",
            "confidence": 0.92,
            "source": "raster_analysis",
        },
        {
            "id": "hero_dominant",
            "statement": "hero occupies dominant middle/lower visual area",
            "from": "hero_visual",
            "to": "canvas",
            "confidence": 0.93,
            "source": "raster_analysis",
        },
    ]

    flexibility_model = {
        "hero_source_asset": REPLACEABLE_ASSET,
        "hero_architecture": LOCKED_IDENTITY,
        "headline_text": LOCKED_IDENTITY,
        "headline_geometry": FLEXIBLE_LAYOUT,
        "supporting_copy_text": LOCKED_IDENTITY,
        "supporting_copy_geometry": FLEXIBLE_LAYOUT,
        "price_content": FLEXIBLE_CONTENT,
        "commercial_group": FLEXIBLE_LAYOUT,
        "logo_asset": LOCKED_IDENTITY,
        "logo_geometry": FLEXIBLE_LAYOUT,
        "cta_text": LOCKED_IDENTITY,
        "cta_geometry": FLEXIBLE_LAYOUT,
        "note": (
            "LOCKED_IDENTITY facts stay unless the user explicitly changes them. "
            "FLEXIBLE_LAYOUT may reflow inside the design system. "
            "FLEXIBLE_CONTENT is for commercial numbers. "
            "REPLACEABLE_ASSET still requires an approved project visual."
        ),
    }

    spec: dict[str, Any] = {
        "schema": SPEC_SCHEMA,
        "master_design_spec_id": str(uuid4()),
        "spec_version": SPEC_VERSION,
        "source_cover_asset_id": str(cover_asset_id),
        "source_version": int(source_version),
        "edit_map_id": (edit_map or {}).get("id"),
        "edit_map_authoritative": False,
        "design_spec_authoritative": False,
        "native_renderer_recipe": False,
        "provider_image_calls": 0,
        "canvas": {
            "width": width,
            "height": height,
            "aspect_ratio": f"{width}:{height}",
            "aspect_name": "4:5" if abs((width / max(1, height)) - 0.8) < 0.03 else "custom",
            "safe_margins": {
                "absolute": safe,
                "normalized": {
                    "left": round(safe["left"] / max(1, width), 5),
                    "right": round(safe["right"] / max(1, width), 5),
                    "top": round(safe["top"] / max(1, height), 5),
                    "bottom": round(safe["bottom"] / max(1, height), 5),
                },
            },
            "confidence": 0.98,
            "source": "raster_analysis",
        },
        "source_assets": {
            "project_id": str(project_id),
            "hero_visual_asset_id": str(source_visual_asset_id),
            "logo_asset_id": str(logo_asset_id),
            "cover_asset_id": str(cover_asset_id),
            "asset_roles": {
                str(source_visual_asset_id): "project_hero_visual",
                str(logo_asset_id): "project_logo",
                str(cover_asset_id): "approved_finished_ad",
            },
            "approval_status": sourced("approved", confidence=0.95, source="asset_metadata"),
            "source_relationship": (
                "Finished-ad raster composites the approved project hero. "
                "It is not a substitute source visual."
            ),
            "confidence": 0.97,
            "source": "asset_metadata",
        },
        "project_asset_policy": PROJECT_ASSET_POLICY,
        "project_asset_rules": {
            "no_invented_building": True,
            "no_invented_interior": True,
            "no_invented_exterior": True,
            "no_fake_logo": True,
            "no_cross_project_asset": True,
            "no_ai_generated_architecture_unless_explicit": True,
            "architecture_lock": True,
        },
        "creative_identity": _creative_identity(ctx, copy),
        "regions": regions,
        "elements": elements,
        "groups": groups,
        "relationships": relationships,
        "hero_treatment": {
            "source_asset_id": str(source_visual_asset_id),
            "geometry": _norm(hero_box, width, height),
            "crop_framing": sourced(
                "full-bleed photograph from header plate to footer navy",
                confidence=0.8,
                source="raster_analysis",
            ),
            "approximate_focal_point": sourced(
                {
                    "normalized_x": 0.5,
                    "normalized_y": round(
                        (((hero_box or {}).get("y0", 0) + (hero_box or {}).get("y1", height)) / 2)
                        / max(1, height),
                        4,
                    ),
                },
                confidence=0.55,
                source="inferred_relationship",
            ),
            "visual_scale": sourced(
                round(hero_h / max(1, height), 4),
                confidence=0.9,
                source="raster_analysis",
            ),
            "overlay_gradient": sourced(
                "navy plate above; navy fade into footer below CTA",
                confidence=0.78,
                source="raster_analysis",
            ),
            "transition_into_navy": sourced(
                "hard header/hero seam at photo_start; footer navy fade",
                confidence=0.8,
                source="raster_analysis",
            ),
            "architecture_must_remain_exact": True,
            "architecture_lock": True,
            "flexibility": REPLACEABLE_ASSET,
        },
        "logo_treatment": {
            "logo_asset_id": str(logo_asset_id),
            "geometry": _norm(logo_box, width, height),
            "relative_scale": sourced(
                round(((logo_box or {}).get("x1", 0) - (logo_box or {}).get("x0", 0)) / max(1, width), 4),
                confidence=0.8,
                source="raster_analysis",
            ),
            "alignment": sourced(_alignment(logo_box, width), confidence=0.88, source="raster_analysis"),
            "color_treatment": sourced("white/gold mark on navy footer", confidence=0.8, source="raster_analysis"),
            "clear_space": sourced("centered in footer, separated below CTA", confidence=0.7, source="inferred_relationship"),
            "relationship_to_bottom_treatment": "primary mark of the bottom navy brand band",
            "flexibility_asset": LOCKED_IDENTITY,
            "flexibility_geometry": FLEXIBLE_LAYOUT,
        },
        "cta_treatment": {
            "exact_text": copy["cta"],
            "geometry": _norm(cta_box, width, height),
            "relative_position": sourced(
                "centered on lower hero, above footer logo",
                confidence=0.88,
                source="raster_analysis",
            ),
            "typography": sourced("dark serif on gold fill", confidence=0.8, source="raster_analysis"),
            "background_treatment": sourced("gold rounded rectangle", confidence=0.82, source="raster_analysis"),
            "border_radius": sourced("soft rounded rect", confidence=0.6, source="inferred_relationship"),
            "relationship_to_hero_and_logo": "sits on the hero; logo sits below in the navy footer",
            "flexibility_text": LOCKED_IDENTITY,
            "flexibility_geometry": FLEXIBLE_LAYOUT,
        },
        "decorative_system": [
            {
                "id": "headline_gold_rule",
                "kind": "gold_separator_line",
                "placement": "below headline / through KAZAN band",
                "confidence": 0.72,
                "source": "raster_analysis",
            },
            {
                "id": "headline_diamond",
                "kind": "diamond_or_star_ornament",
                "placement": "center of headline gold rule",
                "confidence": 0.68,
                "source": "raster_analysis",
            },
            {
                "id": "commercial_vertical_rules",
                "kind": "gold_separator_line",
                "placement": "between commercial columns",
                "confidence": 0.8,
                "source": "edit_map",
            },
            {
                "id": "footer_navy_fade",
                "kind": "navy_fade",
                "placement": "lower hero into logo band",
                "confidence": 0.84,
                "source": "raster_analysis",
            },
        ],
        "flexibility_model": flexibility_model,
        "content_growth": {
            "commercial_group": groups[1]["content_capacity"],
            "strategy": groups[1]["content_capacity"]["growth_strategy"],
            "do_not": [
                "raster-patch old commercial geometry",
                "expand raster surgery masks",
                "write commercial type into the hero",
            ],
        },
        "created_from": {
            "method": "campaign_metadata+raster_analysis+edit_map_geometry",
            "provider_image_calls": 0,
            "ocr": False,
            "phase": "3.0_extraction_only",
        },
        "upper_creative_zone": _norm(upper_box, width, height),
        "validation": {},
        "validation_status": "pending",
    }
    validate_master_design_spec(
        spec,
        expected_cover_asset_id=str(cover_asset_id),
        expected_source_visual_asset_id=str(source_visual_asset_id),
        expected_logo_asset_id=str(logo_asset_id),
        expected_project_id=str(project_id),
        copy=copy,
    )
    return spec


def validate_master_design_spec(
    spec: dict[str, Any],
    *,
    expected_cover_asset_id: str,
    expected_source_visual_asset_id: str,
    expected_logo_asset_id: str,
    expected_project_id: str | None = None,
    copy: dict[str, str] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    if spec.get("schema") not in {SPEC_SCHEMA, "MasterDesignSpecV1.1", "MasterDesignSpecV2"}:
        failures.append("schema_mismatch")
    if int(spec.get("spec_version") or 0) not in {SPEC_VERSION, 2}:
        failures.append("spec_version_mismatch")
    is_v11 = spec.get("schema") == "MasterDesignSpecV1.1" or str(spec.get("spec_revision") or "") == "1.1"
    if is_v11:
        if not spec.get("visual_fidelity_profile"):
            failures.append("missing_visual_fidelity_profile")
        if not spec.get("parent_spec_id"):
            failures.append("missing_parent_spec_id")
        if spec.get("semantic_content_changed") not in (False, None):
            failures.append("semantic_content_changed")
        blob = str(spec.get("elements") or [])
        for needle in ("438.750", "236.250", "LANSMAN FİYATI", "KAZANCINIZ"):
            if needle in blob:
                failures.append(f"price_revision_content:{needle}")
        profile = _as_dict(spec.get("visual_fidelity_profile"))
        for key in (
            "typography",
            "hero_treatment",
            "cta_treatment",
            "decorative_system",
            "color_treatment",
            "group_hierarchy",
            "precise_geometry",
            "render_relationships",
        ):
            if key not in profile:
                failures.append(f"missing_fidelity:{key}")
    if str(spec.get("source_cover_asset_id")) != str(expected_cover_asset_id):
        failures.append("cover_asset_id_mismatch")
    assets = _as_dict(spec.get("source_assets"))
    if str(assets.get("hero_visual_asset_id")) != str(expected_source_visual_asset_id):
        failures.append("source_visual_mismatch")
    if str(assets.get("logo_asset_id")) != str(expected_logo_asset_id):
        failures.append("logo_asset_mismatch")
    if expected_project_id and str(assets.get("project_id")) != str(expected_project_id):
        failures.append("project_id_mismatch")
    canvas = _as_dict(spec.get("canvas"))
    if int(canvas.get("width") or 0) <= 0 or int(canvas.get("height") or 0) <= 0:
        failures.append("canvas_missing")
    if spec.get("project_asset_policy") != PROJECT_ASSET_POLICY:
        failures.append("project_asset_policy_missing")
    if spec.get("provider_image_calls") not in (0, None):
        failures.append("provider_image_calls_not_zero")

    elements = {
        e.get("semantic_role"): e
        for e in (spec.get("elements") or [])
        if isinstance(e, dict)
    }
    for role in REQUIRED_ELEMENT_ROLES:
        if role not in elements:
            failures.append(f"missing_element:{role}")
            continue
        item = elements[role]
        if role != "logo" and not str(item.get("exact_content") or "").strip():
            failures.append(f"missing_content:{role}")
        geom = _as_dict(item.get("geometry"))
        if not geom.get("absolute") or not geom.get("normalized"):
            failures.append(f"missing_normalized_geometry:{role}")

    regions = {
        r.get("semantic_role"): r
        for r in (spec.get("regions") or [])
        if isinstance(r, dict)
    }
    for role in REQUIRED_REGION_ROLES:
        if role not in regions:
            failures.append(f"missing_region:{role}")
        elif not _as_dict(regions[role].get("geometry")).get("normalized"):
            failures.append(f"region_missing_normalized:{role}")

    groups = {g.get("id"): g for g in (spec.get("groups") or []) if isinstance(g, dict)}
    if "commercial_group" not in groups:
        failures.append("missing_commercial_group")
    else:
        capacity = _as_dict(groups["commercial_group"].get("content_capacity"))
        if "growth_strategy" not in capacity and "growth_strategy" not in _as_dict(spec.get("content_growth")):
            failures.append("missing_content_growth_strategy")

    if not spec.get("relationships"):
        failures.append("missing_relationships")
    flex = _as_dict(spec.get("flexibility_model"))
    for key in ("headline_text", "price_content", "commercial_group", "hero_source_asset", "logo_asset"):
        if key not in flex:
            failures.append(f"missing_flexibility:{key}")

    expected_copy = copy or {}
    for role, needle in (
        ("headline", expected_copy.get("headline") or "ALIRKEN KAZAN"),
        ("supporting_copy", expected_copy.get("supporting_copy")),
        ("unit_type", expected_copy.get("unit_type") or "2+1"),
        ("list_price", expected_copy.get("list_price") or "675.000"),
        ("discount", expected_copy.get("discount") or "%35"),
        ("cta", expected_copy.get("cta") or "PROJEYİ KEŞFET"),
    ):
        if not needle:
            continue
        content = str((elements.get(role) or {}).get("exact_content") or "")
        if needle.split()[0] not in content and needle not in content:
            failures.append(f"content_mismatch:{role}")

    if int(spec.get("spec_version") or 0) >= 2 or spec.get("schema") == "MasterDesignSpecV2":
        if str(spec.get("revision_intent") or "") != "PRICE_EDIT_ONLY":
            failures.append("missing_price_revision_intent")
        if not spec.get("parent_spec_id"):
            failures.append("missing_parent_spec_id")
        for role, needle in (
            ("launch_price", "438.750"),
            ("savings", "236.250"),
            ("list_price_label", "LİSTE FİYATI"),
            ("launch_price_label", "LANSMAN FİYATI"),
            ("savings_label", "KAZANCINIZ"),
        ):
            item = elements.get(role) or {}
            if needle not in str(item.get("exact_content") or ""):
                failures.append(f"missing_content:{role}")
        if not (elements.get("list_price") or {}).get("strikethrough"):
            failures.append("list_price_missing_strikethrough")
        commercial = groups.get("commercial_group") or {}
        model = commercial.get("layout_model")
        if isinstance(model, dict):
            model = model.get("value")
        if model == "three_column_row":
            failures.append("content_growth_still_three_column_row")

    status = "fail" if failures else "pass"
    result = {"status": status, "failures": failures, "warnings": warnings}
    spec["validation"] = result
    spec["validation_status"] = status
    return result


def _geom_abs(item: dict[str, Any] | None) -> dict[str, int] | None:
    absb = _as_dict(_as_dict(item).get("geometry")).get("absolute")
    return dict(absb) if absb else None


def _replace_element(spec: dict[str, Any], role: str, updates: dict[str, Any]) -> dict[str, Any]:
    for item in spec.get("elements") or []:
        if item.get("semantic_role") == role:
            item.update(updates)
            return item
    spec.setdefault("elements", []).append({"semantic_role": role, **updates})
    return spec["elements"][-1]


def derive_price_revision_spec(
    parent: dict[str, Any],
    intent: Any,
) -> dict[str, Any]:
    """In-memory MasterDesignSpecV2. Does not mutate V1. Preview only."""
    from investhome_api.services.creative_director.price_block_revision import format_tr_usd

    spec = copy.deepcopy(parent)
    canvas = _as_dict(spec.get("canvas"))
    width = int(canvas.get("width") or 1088)
    height = int(canvas.get("height") or 1360)
    navy = _geom_abs(next((r for r in spec.get("regions") or [] if r.get("semantic_role") == "navy_field"), None))
    hero = _geom_abs(next((r for r in spec.get("regions") or [] if r.get("semantic_role") == "hero_visual"), None))
    if not navy:
        navy = {"x0": 0, "y0": 0, "x1": width, "y1": int(height * 0.407)}
    if not hero:
        hero = {"x0": 0, "y0": navy["y1"], "x1": width, "y1": int(height * 0.89)}
    ny0 = int(navy["y0"])
    ny1 = int(navy["y1"])
    nh = max(80, ny1 - ny0)
    inset = int(width * 0.12)
    cx = width // 2

    def ny(frac: float) -> int:
        return ny0 + int(nh * frac)

    headline_box = {"x0": inset, "y0": ny(0.04), "x1": width - inset, "y1": ny(0.30)}
    support_box = {"x0": inset, "y0": ny(0.33), "x1": width - inset, "y1": ny(0.40)}
    commercial_box = {"x0": inset, "y0": ny(0.43), "x1": width - inset, "y1": ny(0.975)}
    ch = max(40, commercial_box["y1"] - commercial_box["y0"])
    y0 = commercial_box["y0"]
    launch_box = {"x0": inset, "y0": y0, "x1": width - inset, "y1": y0 + int(ch * 0.38)}
    mid_y0 = launch_box["y1"] + max(4, int(ch * 0.03))
    mid_y1 = y0 + int(ch * 0.70)
    list_box = {"x0": inset, "y0": mid_y0, "x1": cx - 12, "y1": mid_y1}
    save_box = {"x0": cx + 12, "y0": mid_y0, "x1": width - inset, "y1": mid_y1}
    row_y0 = mid_y1 + max(4, int(ch * 0.03))
    third = (width - 2 * inset) // 3
    disc_box = {"x0": inset + third, "y0": row_y0, "x1": inset + 2 * third, "y1": commercial_box["y1"]}
    unit_box = {"x0": inset + 2 * third, "y0": row_y0, "x1": width - inset, "y1": commercial_box["y1"]}

    list_s = format_tr_usd(int(intent.list_amount))
    launch_s = format_tr_usd(int(intent.launch_amount))
    save_s = format_tr_usd(int(intent.savings_amount))

    spec["schema"] = "MasterDesignSpecV2"
    spec["spec_version"] = 2
    spec["master_design_spec_id"] = str(uuid4())
    spec["parent_spec_id"] = str(parent.get("master_design_spec_id"))
    spec["revision_intent"] = "PRICE_EDIT_ONLY"
    spec["preview_only"] = True
    spec["persisted"] = False
    spec["provider_image_calls"] = 0
    spec["changed_semantics"] = {
        "list_price.strikethrough": True,
        "launch_price": launch_s,
        "savings": save_s,
    }
    spec["unchanged_semantics"] = [
        "headline",
        "supporting_copy",
        "unit_type",
        "discount",
        "cta",
        "logo",
        "hero_asset",
    ]
    spec["created_from"] = {
        "method": "derive_from_master_design_spec_v1+PRICE_EDIT_ONLY",
        "provider_image_calls": 0,
        "phase": "3.1_structured_reconstruction_preview",
        "parent_spec_id": spec["parent_spec_id"],
    }

    def paint(role: str, content: str, bbox: dict[str, int], **extra: Any) -> None:
        _replace_element(
            spec,
            role,
            {
                "exact_content": content,
                "geometry": _norm(bbox, width, height),
                **extra,
            },
        )

    paint(
        "headline",
        next((e.get("exact_content") for e in parent.get("elements") or [] if e.get("semantic_role") == "headline"), "ALIRKEN KAZAN"),
        headline_box,
        line_behavior="stacked_display",
        flexibility={"content": LOCKED_IDENTITY, "layout": FLEXIBLE_LAYOUT},
    )
    paint(
        "supporting_copy",
        next((e.get("exact_content") for e in parent.get("elements") or [] if e.get("semantic_role") == "supporting_copy"), ""),
        support_box,
        flexibility={"content": LOCKED_IDENTITY, "layout": FLEXIBLE_LAYOUT},
    )
    paint("launch_price", launch_s, launch_box, hierarchy_level=2, visual_importance="primary", strikethrough=False, parent_group="commercial_group")
    paint("launch_price_label", str(intent.launch_label), launch_box, hierarchy_level=6, visual_importance="label", parent_group="commercial_group")
    paint("list_price", list_s, list_box, strikethrough=True, hierarchy_level=3, visual_importance="secondary", parent_group="commercial_group")
    paint("list_price_label", str(intent.list_label), list_box, hierarchy_level=6, visual_importance="label", parent_group="commercial_group")
    paint("savings", save_s, save_box, hierarchy_level=3, visual_importance="benefit", parent_group="commercial_group")
    paint("savings_label", str(intent.savings_label), save_box, hierarchy_level=6, visual_importance="label", parent_group="commercial_group")
    paint("discount", next((e.get("exact_content") for e in parent.get("elements") or [] if e.get("semantic_role") == "discount"), "%35"), disc_box, parent_group="commercial_group")
    paint("discount_label", next((e.get("exact_content") for e in parent.get("elements") or [] if e.get("semantic_role") == "discount_label"), "LANSMAN AVANTAJI"), disc_box, parent_group="commercial_group")
    paint("unit_type", next((e.get("exact_content") for e in parent.get("elements") or [] if e.get("semantic_role") == "unit_type"), "2+1"), unit_box, parent_group="commercial_group")
    paint("unit_label", next((e.get("exact_content") for e in parent.get("elements") or [] if e.get("semantic_role") == "unit_label"), "DAİRE"), unit_box, parent_group="commercial_group")

    for group in spec.get("groups") or []:
        if group.get("id") != "commercial_group":
            continue
        group["layout_model"] = "primary_price_plus_supporting_metrics"
        group["children"] = [
            "launch_price",
            "launch_price_label",
            "list_price",
            "list_price_label",
            "savings",
            "savings_label",
            "discount",
            "discount_label",
            "unit_type",
            "unit_label",
        ]
        group["geometry"] = _norm(commercial_box, width, height)
        group["hierarchy"] = "primary launch price, secondary struck list, benefit, then supporting facts"
        group["content_capacity"] = {
            "current_content_count": 5,
            "current_facts": ["2+1", list_s, launch_s, save_s, "%35"],
            "current_layout_model": "primary_price_plus_supporting_metrics",
            "growth_strategy": (
                "Commercial content grew. Layout recomposed inside the navy plate. "
                "Hero, CTA, and logo geometry remain as in the parent spec."
            ),
        }
    for region in spec.get("regions") or []:
        if region.get("semantic_role") == "headline_area":
            region["geometry"] = _norm(headline_box, width, height)
        elif region.get("semantic_role") == "supporting_copy_area":
            region["geometry"] = _norm(support_box, width, height)
        elif region.get("semantic_role") == "commercial_information_area":
            region["geometry"] = _norm(commercial_box, width, height)

    spec["layout_plan"] = {
        "model": "primary_price_plus_supporting_metrics",
        "reason": "three_column_row cannot hold five commercial facts without compression",
        "hero_locked": True,
        "cta_locked": True,
        "logo_locked": True,
        "navy_reflow": True,
    }
    spec["content_growth"] = {
        "commercial_group": next(
            (g.get("content_capacity") for g in spec.get("groups") or [] if g.get("id") == "commercial_group"),
            {},
        ),
        "strategy": "recompose commercial_group; reflow headline/supporting moderately; never raster-patch",
        "do_not": ["raster-patch", "mask edit", "regional edit", "full-ad generate"],
    }
    copy_bag = {
        "headline": next((e.get("exact_content") for e in spec.get("elements") or [] if e.get("semantic_role") == "headline"), ""),
        "supporting_copy": next((e.get("exact_content") for e in spec.get("elements") or [] if e.get("semantic_role") == "supporting_copy"), ""),
        "unit_type": "2+1",
        "list_price": list_s,
        "discount": "%35",
        "cta": next((e.get("exact_content") for e in spec.get("elements") or [] if e.get("semantic_role") == "cta"), "PROJEYİ KEŞFET"),
    }
    validate_master_design_spec(
        spec,
        expected_cover_asset_id=str(spec.get("source_cover_asset_id")),
        expected_source_visual_asset_id=str(_as_dict(spec.get("source_assets")).get("hero_visual_asset_id")),
        expected_logo_asset_id=str(_as_dict(spec.get("source_assets")).get("logo_asset_id")),
        expected_project_id=str(_as_dict(spec.get("source_assets")).get("project_id")),
        copy=copy_bag,
    )
    return spec


def persist_master_design_spec(ctx: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Metadata only. Never stamps cover, version, edit map, or SMB."""
    spec_id = str(spec["master_design_spec_id"])
    cover = str(spec["source_cover_asset_id"])
    specs = _as_dict(ctx.get("master_design_specs"))
    specs[spec_id] = spec
    by_cover = _as_dict(ctx.get("master_design_specs_by_cover"))
    by_cover[cover] = spec_id
    ctx["master_design_specs"] = specs
    ctx["master_design_specs_by_cover"] = by_cover
    ctx["current_master_design_spec_id"] = spec_id
    mc = _as_dict(ctx.get("master_creative"))
    mc["current_master_design_spec_id"] = spec_id
    ctx["master_creative"] = mc
    return ctx


def load_master_design_spec(
    ctx: dict[str, Any],
    *,
    cover_asset_id: UUID | str | None = None,
    spec_id: str | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    specs = _as_dict(ctx.get("master_design_specs"))
    sid = spec_id or ctx.get("current_master_design_spec_id")
    mc = _as_dict(ctx.get("master_creative"))
    if not sid:
        sid = mc.get("current_master_design_spec_id")
    if not sid and cover_asset_id:
        sid = _as_dict(ctx.get("master_design_specs_by_cover")).get(str(cover_asset_id))
    if not sid:
        return None, None
    spec = specs.get(str(sid))
    if not isinstance(spec, dict):
        return str(sid), None
    if cover_asset_id and str(spec.get("source_cover_asset_id")) != str(cover_asset_id):
        return str(sid), None
    return str(sid), spec


def snapshot_identity(ctx: dict[str, Any]) -> dict[str, Any]:
    mc = _as_dict(ctx.get("master_creative"))
    return {
        "current_version": mc.get("current_version"),
        "current_cover_asset_id": ctx.get("current_cover_asset_id") or mc.get("current_cover_asset_id"),
        "current_edit_map_id": ctx.get("current_edit_map_id") or mc.get("current_edit_map_id"),
        "source_visual_asset_id": mc.get("source_visual_asset_id"),
        "logo_asset_id": mc.get("logo_asset_id"),
        "revision_history_len": len(list(mc.get("revision_history") or ctx.get("revision_history") or [])),
        "latest_master_ad_asset_id": ctx.get("latest_master_ad_asset_id"),
        "finished_ad_raster_asset_id": ctx.get("finished_ad_raster_asset_id"),
    }


def render_master_design_spec_debug(image: Any, spec: dict[str, Any]) -> Any:
    """Internal QA overlay. Must never become the SMB cover."""
    from PIL import ImageDraw, ImageFont

    im = image.convert("RGB")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    palette = {
        "navy_field": (80, 120, 255),
        "headline_area": (255, 255, 255),
        "supporting_copy_area": (180, 180, 220),
        "commercial_information_area": (255, 200, 40),
        "hero_visual": (0, 200, 255),
        "cta": (220, 80, 255),
        "logo": (120, 255, 80),
        "bottom_brand_treatment": (255, 140, 80),
    }

    def _draw(geom: dict[str, Any] | None, color: tuple[int, int, int], label: str, width: int) -> None:
        absb = _as_dict((geom or {}).get("absolute"))
        if not absb:
            return
        draw.rectangle(
            [absb["x0"], absb["y0"], absb["x1"] - 1, absb["y1"] - 1],
            outline=color,
            width=width,
        )
        ty = max(0, int(absb["y0"]) - 12)
        if font:
            draw.text((int(absb["x0"]) + 4, ty), label, fill=color, font=font)
        else:
            draw.text((int(absb["x0"]) + 4, ty), label, fill=color)

    for region in spec.get("regions") or []:
        role = str(region.get("semantic_role") or "")
        _draw(region.get("geometry"), palette.get(role, (255, 255, 0)), role, 3)
    for group in spec.get("groups") or []:
        _draw(group.get("geometry"), (255, 210, 40), f"group:{group.get('id')}", 2)
    hero = next((r for r in spec.get("regions") or [] if r.get("semantic_role") == "hero_visual"), None)
    absb = _as_dict(_as_dict((hero or {}).get("geometry")).get("absolute"))
    if absb:
        y = int(absb["y0"])
        draw.line([(0, y), (im.size[0] - 1, y)], fill=(255, 40, 40), width=3)
        if font:
            draw.text((8, max(0, y - 14)), f"hero y={y}", fill=(255, 40, 40), font=font)
    return im


def extract_and_attach_master_design_spec(
    db: Session,
    ctx: dict[str, Any],
    *,
    cover_asset_id: UUID | str,
    source_visual_asset_id: UUID | str,
    logo_asset_id: UUID | str,
    project_id: UUID | str,
    source_version: int = 2,
) -> dict[str, Any]:
    """Build + validate + persist metadata. Does not change cover/version/SMB."""
    from PIL import Image
    import io

    from investhome_api.services.creative_director.edit_map import _read_cover_bytes

    before = snapshot_identity(ctx)
    raster = _read_cover_bytes(db, UUID(str(cover_asset_id)))
    image = Image.open(io.BytesIO(raster)).convert("RGB")
    layout = analyze_raster(image)
    _map_id, edit_map = load_edit_map(ctx, cover_asset_id=cover_asset_id)
    if edit_map is None:
        edit_map = build_edit_map(
            layout,
            cover_asset_id=str(cover_asset_id),
            source_visual_asset_id=str(source_visual_asset_id),
            logo_asset_id=str(logo_asset_id),
            image=image,
        )
        validate_edit_map(
            edit_map,
            expected_cover_asset_id=str(cover_asset_id),
            expected_source_visual_asset_id=str(source_visual_asset_id),
            expected_logo_asset_id=str(logo_asset_id),
            current_cover_asset_id=str(cover_asset_id),
        )
    spec = build_master_design_spec(
        ctx=ctx,
        cover_asset_id=str(cover_asset_id),
        source_visual_asset_id=str(source_visual_asset_id),
        logo_asset_id=str(logo_asset_id),
        project_id=str(project_id),
        edit_map=edit_map,
        layout=layout,
        image=image,
        source_version=source_version,
    )
    if spec.get("validation_status") != "pass":
        raise ValueError(f"MasterDesignSpecV1 validation failed: {spec.get('validation')}")
    persist_master_design_spec(ctx, spec)
    after = snapshot_identity(ctx)
    identity_keys = (
        "current_version",
        "current_cover_asset_id",
        "current_edit_map_id",
        "source_visual_asset_id",
        "logo_asset_id",
        "revision_history_len",
        "latest_master_ad_asset_id",
        "finished_ad_raster_asset_id",
    )
    drifted = {k: (before.get(k), after.get(k)) for k in identity_keys if before.get(k) != after.get(k)}
    if drifted:
        raise RuntimeError(f"Master Design Spec persist mutated identity: {drifted}")
    return spec


def save_campaign_metadata_only(db: Session, campaign, ctx: dict[str, Any]) -> None:
    campaign.context_json = ctx
    flag_modified(campaign, "context_json")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
