"""Editable Finished-Ad Design Spec — structured layers for SMB hydration.

AI Creative Director owns design via production_brief + Full Composition Plan.
This module encodes the SAME composition as editable primitives — editability is
a rendering property, not a simplified design style.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Literal
from uuid import UUID

from investhome_api.services.creative_director.composition_plan import build_composition_plan

RevisionRoute = Literal[
    "LAYER_ONLY",
    "MICRO_EDIT",
    "CREATIVE_RECOMPOSE",
    "IMAGE_REQUIRED",
    "VISUAL_REPLACE_ONLY",
    "PRICE_EDIT_ONLY",
    "BOUNDED_LOCAL_RECOMPOSITION",
]

# Ops that mutate overlay layers without re-rasterizing the photograph.
_LAYER_ONLY_TARGETS = frozenset(
    {
        "headline",
        "cta",
        "badge",
        "logo",
        "support_message",
        "price",
        "subheadline",
        "eyebrow",
        "top_small_description",
        "primary_headline",
        "left_feature_texts",
        "feature_text",
    }
)
_LAYER_ONLY_ACTIONS = frozenset(
    {
        "replace_text",
        "scale",
        "resize",
        "remove",
        "delete",
        "preserve",
        "minimum_change",
        "translate",
        "set_position",
        "align",
        "set_font_size",
        "set_color",
        "hide",
        "set_geometry",
        "tone_adjust",
        "improve_readability",
    }
)
_IMAGE_REQUIRED_TARGETS = frozenset({"background", "layout", "style", "overall"})
_MICRO_EDIT_TARGETS = frozenset({"logo", "cta", "badge"})
_MICRO_EDIT_ACTIONS = frozenset(
    {
        "scale",
        "resize",
        "replace_text",
        "translate",
        "set_position",
        "align",
        "set_geometry",
        "preserve",
        "minimum_change",
    }
)
_STRUCTURED_MICRO_TARGETS = frozenset(
    {
        "logo",
        "cta",
        "badge",
        "headline",
        "primary_headline",
        "support_message",
        "left_feature_texts",
        "feature_text",
        "price",
        "old-price",
        "new-price",
        "savings-price",
        "discount-badge",
        "unit-label",
    }
)
_STRUCTURED_MICRO_ACTIONS = _MICRO_EDIT_ACTIONS | frozenset(
    {
        "hide",
        "remove",
        "delete",
        "set_font_size",
        "set_color",
    }
)
_COPY_REBALANCE_TARGETS = frozenset(
    {
        "headline",
        "primary_headline",
        "support_message",
        "left_feature_texts",
        "feature_text",
        "top_small_description",
        "subheadline",
        "eyebrow",
        "price",
    }
)
_FURNITURE_IMAGE_PHRASES = (
    "başka interior",
    "baska interior",
    "koltuğu değiştir",
    "koltugu degistir",
    "koltuğu degistir",
    "koltuğu kaldır",
    "koltugu kaldir",
    "arka plandaki koltuğu",
    "arka plandaki koltugu",
    "yeni sahne",
    "new scene",
    "mimari",
    "architectural",
)

_IMAGE_REQUIRED_PHRASES = (
    "başka interior",
    "baska interior",
    "koltuğu değiştir",
    "koltugu degistir",
    "koltuğu degistir",
    "koltuğu kaldır",
    "koltugu kaldir",
    "arka plandaki koltuğu",
    "arka plandaki koltugu",
    "yeni sahne",
    "new scene",
    "arka planı değiştir",
    "arka plani degistir",
    "background change",
    "change the background",
    "farklı render",
    "farkli render",
    "gorseli degistir",
    "görseli değiştir",
    "mimari",
    "architectural",
)


def canvas_size_for_aspect(aspect_ratio: str, format_preset: str) -> tuple[int, int]:
    """Canonical SMB canvas sizes used by finished-ad / portrait export."""
    ar = (aspect_ratio or "4:5").strip()
    preset = (format_preset or "portrait").strip().lower()
    if ar == "9:16" or preset in {"story", "reelscover", "reels_cover"}:
        return 1080, 1920
    if ar == "16:9" or preset == "landscape":
        return 1920, 1080
    if ar == "1:1" or preset == "square":
        return 1080, 1080
    # Default Instagram 4:5 portrait
    return 1080, 1350


def _s(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _split_supporting_blob(value: Any) -> list[str]:
    """Split persisted supporting copy into left-feature lines. Never invent text."""
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_split_supporting_blob(item))
        return parts
    blob = _s(value)
    if not blob:
        return []
    normalized = blob.replace("•", "\n").replace(" · ", "\n").replace("·", "\n").replace("|", "\n")
    return [p.strip(" -–—") for p in normalized.split("\n") if p.strip(" -–—")]


def collect_supporting_lines(
    *sources: Any,
    headline: str = "",
    limit: int = 2,
) -> list[str]:
    """Unique supporting lines from existing metadata. Never invent copy."""
    out: list[str] = []
    headline_key = _s(headline).strip().lower()
    seen: set[str] = set()
    for source in sources:
        for line in _split_supporting_blob(source):
            key = line.strip().lower()
            if not key or key == headline_key or key in seen:
                continue
            seen.add(key)
            out.append(line)
            if len(out) >= limit:
                return out
    return out[:limit]


def _supporting_list(production_brief: dict[str, Any], texts: dict[str, str]) -> list[str]:
    """Collect up to two real supporting lines from campaign/spec metadata."""
    final = production_brief.get("final_copy") if isinstance(production_brief.get("final_copy"), dict) else {}
    strategy = (
        production_brief.get("message_strategy")
        if isinstance(production_brief.get("message_strategy"), dict)
        else {}
    )
    cd_strategy = (
        production_brief.get("cd_strategy")
        if isinstance(production_brief.get("cd_strategy"), dict)
        else {}
    )
    return collect_supporting_lines(
        texts.get("supporting_callouts"),
        texts.get("supporting_messages"),
        final.get("supporting_callouts"),
        production_brief.get("supporting"),
        production_brief.get("supporting_messages"),
        strategy.get("supporting_messages"),
        cd_strategy.get("supporting_messages"),
        texts.get("feature_callouts"),
        production_brief.get("feature_callouts"),
        texts.get("supporting"),
        final.get("supporting"),
        final.get("supporting_messages"),
        headline=_s(texts.get("headline") or final.get("headline") or production_brief.get("hero")),
        limit=2,
    )


def hydrate_supporting_copy(
    *,
    texts: dict[str, Any],
    production_brief: dict[str, Any] | None = None,
    campaign_copy: dict[str, Any] | None = None,
    strategy: dict[str, Any] | None = None,
    ctx: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind campaign/strategy supporting lines onto texts + brief before spec assembly."""
    texts_out = dict(texts or {})
    brief_out = dict(production_brief or {})
    if isinstance(strategy, dict) and strategy.get("supporting_messages"):
        brief_out["cd_strategy"] = strategy
    merged = collect_supporting_lines(
        (ctx or {}).get("supporting_callouts") if isinstance(ctx, dict) else None,
        texts_out.get("supporting_callouts"),
        texts_out.get("supporting_messages"),
        brief_out.get("supporting"),
        brief_out.get("supporting_messages"),
        (campaign_copy or {}).get("supporting_messages") if isinstance(campaign_copy, dict) else None,
        (strategy or {}).get("supporting_messages") if isinstance(strategy, dict) else None,
        texts_out.get("supporting"),
        headline=_s(texts_out.get("headline") or brief_out.get("hero")),
        limit=2,
    )
    if merged:
        texts_out["supporting_callouts"] = "|".join(merged)
    return texts_out, brief_out


def stamp_editable_text_targets(spec: dict[str, Any]) -> dict[str, Any]:
    """Refresh compact semantic metadata from the live spec elements."""
    out = dict(spec or {})
    elements = [el for el in (out.get("elements") or []) if isinstance(el, dict)]
    out["editable_text_targets"] = _editable_text_targets(elements)
    return out


_EDITABLE_COPY_IDS = frozenset(
    {
        "unit-label",
        "subheadline",
        "eyebrow",
        "top-description",
        "headline",
        "support-message-1",
        "support-message-2",
        "feature-1",
        "feature-2",
    }
)


def _editable_text_targets(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact semantic metadata so LAYER_ONLY revise does not have to guess missing copy."""
    out: list[dict[str, Any]] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        eid = _s(el.get("id"))
        role = _s(el.get("role")).lower()
        if eid.lower() not in _EDITABLE_COPY_IDS and role not in {
            "headline",
            "support_message",
            "subheadline",
            "unit_label",
            "eyebrow",
        }:
            continue
        typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
        style = el.get("style") if isinstance(el.get("style"), dict) else {}
        out.append(
            {
                "id": eid,
                "role": el.get("role") or role,
                "content": _s(el.get("content")),
                "x": int(el.get("x") or 0),
                "y": int(el.get("y") or 0),
                "width": int(el.get("width") or 0),
                "height": int(el.get("height") or 0),
                "font_size": int(typo.get("font_size") or style.get("font_size") or 0),
            }
        )
    return out


_STRUCTURED_ID_ALIASES = {
    "master_background": "background",
    "logo": "project-logo",
    "cta": "cta-primary",
}

_STRUCTURED_REQUIRED_SLOTS = (
    "background",
    "project-logo",
    "headline",
    "support-message-1",
    "support-message-2",
    "cta-primary",
)
_STRUCTURED_FINANCIAL_SLOTS = (
    "old-price",
    "new-price",
    "savings-price",
    "discount-badge",
    "unit-label",
)


def project_structured_design_data(
    spec: dict[str, Any] | None,
    *,
    production_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact semantic twin of the Golden raster. Not a new designer — edit/export metadata."""
    spec = spec if isinstance(spec, dict) else {}
    brief = production_brief if isinstance(production_brief, dict) else {}
    elements_out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for el in spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        raw_id = _s(el.get("id"))
        if not raw_id:
            continue
        semantic_id = _STRUCTURED_ID_ALIASES.get(raw_id.lower(), raw_id)
        if semantic_id in seen:
            continue
        seen.add(semantic_id)
        role = _s(el.get("role")) or semantic_id
        typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
        style = el.get("style") if isinstance(el.get("style"), dict) else {}
        elements_out.append(
            {
                "id": semantic_id,
                "source_element_id": raw_id,
                "role": role,
                "content": _s(el.get("content") or el.get("text") or el.get("label")),
                "visible": el.get("visible") is not False,
                "locked": bool(el.get("locked")),
                "asset_id": el.get("asset_id") or el.get("assetId"),
                "geometry": {
                    "x": int(el.get("x") or 0),
                    "y": int(el.get("y") or 0),
                    "width": int(el.get("width") or 0),
                    "height": int(el.get("height") or 0),
                    "z_index": int(el.get("z_index") or el.get("zIndex") or 0),
                },
                "alignment": _s(typo.get("align") or style.get("align") or el.get("align")),
                "typography": {
                    "font_family": typo.get("font_family") or style.get("font_family"),
                    "font_size": typo.get("font_size") or style.get("font_size") or el.get("font_size"),
                    "font_weight": typo.get("font_weight") or style.get("font_weight"),
                    "color": typo.get("color") or style.get("color") or el.get("color"),
                    "line_height": typo.get("line_height") or style.get("line_height"),
                },
                "opacity": el.get("opacity") if el.get("opacity") is not None else 1.0,
            }
        )
    present = {e["id"] for e in elements_out}
    financial = bool(present & set(_STRUCTURED_FINANCIAL_SLOTS)) or _s(brief.get("campaign_intent")).startswith(
        "price"
    )
    required = list(_STRUCTURED_REQUIRED_SLOTS)
    if financial:
        required.extend(_STRUCTURED_FINANCIAL_SLOTS)
    return {
        "version": 1,
        "mode": "structured_golden_design",
        "visual_source_of_truth": "finished_ad_raster",
        "rebuild_from_layers": False,
        "finished_ad_raster_asset_id": spec.get("finished_ad_raster_asset_id"),
        "background_asset_id": spec.get("master_background_asset_id"),
        "logo_asset_id": spec.get("logo_asset_id"),
        "locked_facts": {
            "approved_claims": brief.get("approved_claims") or [],
            "cta": brief.get("cta") or _as_brief_cta(brief),
            "language": spec.get("language") or brief.get("language"),
        },
        "required_slots": required,
        "present_slots": sorted(present),
        "missing_slots": [s for s in required if s not in present],
        "elements": elements_out,
        "visual_zones": spec.get("composition") if isinstance(spec.get("composition"), dict) else {},
        "typography_hierarchy": [
            {
                "id": e["id"],
                "font_size": (e.get("typography") or {}).get("font_size"),
                "font_weight": (e.get("typography") or {}).get("font_weight"),
            }
            for e in elements_out
            if e.get("id") in {"headline", "support-message-1", "support-message-2", "cta-primary"}
        ],
        "palette": {
            "visual_mood": (brief.get("design_direction") or {}).get("visual_mood")
            if isinstance(brief.get("design_direction"), dict)
            else None,
            "hierarchy": (brief.get("design_direction") or {}).get("hierarchy")
            if isinstance(brief.get("design_direction"), dict)
            else None,
        },
        "source_background_asset_id": spec.get("master_background_asset_id"),
        "project_logo_asset_id": spec.get("logo_asset_id"),
    }


GOLDEN_NATIVE_V1_LAYER_IDS = ("master_background", "logo", "headline", "cta")
GOLDEN_NATIVE_V1_REQUIRED_SLOTS = ("background", "project-logo", "headline", "cta-primary")
_NATIVE_CREAM = "#F4EFE6"
_NATIVE_WARM_WHITE = "#F7F3EC"
_NATIVE_MUTED_GOLD = "#C4A35A"
_NATIVE_CHARCOAL = "#2A241C"


def is_golden_native_v1(value: Any) -> bool:
    """True when campaign/spec is the 4-layer Golden Native Renderer v1 POC."""
    if not isinstance(value, dict):
        return False
    mode = _s(value.get("mode") or value.get("production_mode") or value.get("renderer"))
    return mode == "golden_native_v1"


def project_golden_native_structured_data(
    spec: dict[str, Any] | None,
    *,
    production_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Semantic twin for native v1 — only the four real layers, rebuild from layers."""
    data = project_structured_design_data(spec, production_brief=production_brief)
    present = set(data.get("present_slots") or [])
    required = list(GOLDEN_NATIVE_V1_REQUIRED_SLOTS)
    data["version"] = 1
    data["mode"] = "golden_native_v1"
    data["visual_source_of_truth"] = "native_layers"
    data["rebuild_from_layers"] = True
    data["required_slots"] = required
    data["missing_slots"] = [s for s in required if s not in present]
    return data


def _as_brief_cta(brief: dict[str, Any]) -> str:
    final = brief.get("final_copy") if isinstance(brief.get("final_copy"), dict) else {}
    return _s(brief.get("cta") or final.get("cta"))


def _badge_display(badge: str) -> str:
    if not badge:
        return ""
    if "%" in badge:
        m = re.search(r"%\s*(\d+)|(\d+)\s*%", badge.replace("~", ""))
        if m:
            return f"%{m.group(1) or m.group(2)}"
        if badge.strip().startswith("~"):
            return badge.replace("lansman fiyat avantajı", "").strip() or badge
    return badge


def _tr_usd_display(raw: str) -> str:
    """Normalize money copy to '675.000 USD' for editable commercial layers."""
    text = (raw or "").strip()
    if not text:
        return ""
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return text
    try:
        amount = int(digits)
    except ValueError:
        return text
    if amount < 1000:
        return text
    grouped = f"{amount:,}".replace(",", ".")
    return f"{grouped} USD"


def _strikethrough_shape(text_el: dict[str, Any]) -> dict[str, Any]:
    """Thin gold bar through a price TEXT box — visible without SMB CSS changes."""
    x = int(text_el.get("x") or 0)
    y = int(text_el.get("y") or 0)
    w = max(8, int(text_el.get("width") or 0))
    h = max(8, int(text_el.get("height") or 0))
    line_h = max(3, int(round(h * 0.07)))
    eid = _s(text_el.get("id")) or "old-price"
    return {
        "id": f"{eid}-strikethrough",
        "type": "rectangle",
        "role": "strikethrough",
        "locked": False,
        "editable": True,
        "visible": True,
        "x": x,
        "y": y + int(round(h * 0.48)) - line_h // 2,
        "width": w,
        "height": line_h,
        "z_index": int(text_el.get("z_index") or 24) + 1,
        "opacity": 1.0,
        "style": {
            "fill": "#C4A35A",
            "shape_kind": "rect",
        },
    }


def _upsert_strikethrough(spec: dict[str, Any], text_el: dict[str, Any]) -> None:
    shape = _strikethrough_shape(text_el)
    elements = spec.get("elements")
    if not isinstance(elements, list):
        return
    sid = str(shape["id"])
    for idx, el in enumerate(elements):
        if isinstance(el, dict) and _s(el.get("id")) == sid:
            elements[idx] = shape
            return
    elements.append(shape)


def _logo_geometry(
    *,
    width: int,
    height: int,
    margin: int,
    placement: str,
    scale: float,
) -> dict[str, int]:
    lw = int(round(width * float(scale or 0.2)))
    lh = int(round(height * 0.065))
    y = int(round(height * 0.04))
    if placement == "top_center":
        x = int(round((width - lw) / 2))
    else:
        x = margin
    return {"x": x, "y": y, "width": lw, "height": lh}


def _append_gradient(
    elements: list[dict[str, Any]],
    *,
    eid: str,
    y: int,
    h: int,
    width: int,
    fill: str,
    z_index: int = 5,
) -> None:
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
            "z_index": z_index,
            "opacity": 1.0,
            "style": {"fill": fill, "shape_kind": "rect"},
        }
    )


def _build_price_elements(
    *,
    width: int,
    height: int,
    margin: int,
    content_w: int,
    logo_id: str,
    copy: dict[str, str],
    supporting: list[str],
    plan: dict[str, Any],
    revision_engine_v2: bool = False,
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    _append_gradient(
        elements,
        eid="overlay-bottom-dark",
        y=int(height * 0.46),
        h=int(height * 0.54),
        width=width,
        fill=(
            "linear-gradient(to top, rgba(8,6,4,0.94) 0%, rgba(8,6,4,0.72) 28%, "
            "rgba(8,6,4,0.38) 58%, transparent 100%)"
        ),
        z_index=5,
    )
    logo = _logo_geometry(
        width=width,
        height=height,
        margin=margin,
        placement=str((plan.get("logo") or {}).get("placement") or "top_left"),
        scale=float((plan.get("logo") or {}).get("scale") or 0.20),
    )
    elements.append(
        {
            "id": "logo",
            "type": "logo",
            "role": "logo",
            "asset_id": logo_id,
            "locked": False,
            "editable": True,
            "lock_aspect_ratio": True,
            **logo,
            "z_index": 10,
            "opacity": 1.0,
        }
    )

    if copy["badge"]:
        badge_w = int(round(width * 0.18))
        badge_h = int(round(height * 0.10))
        elements.append(
            {
                "id": "discount-badge",
                "type": "badge",
                "role": "discount_badge",
                "content": copy["badge"],
                "locked": False,
                "editable": True,
                "x": width - margin - badge_w,
                "y": int(round(height * 0.08)),
                "width": badge_w,
                "height": badge_h,
                "z_index": 12,
                "style": {
                    "background_color": "rgba(20,16,12,0.82)",
                    "text_color": "#C4A35A",
                    "border_color": "#C4A35A",
                    "border_radius": int(round(badge_w * 0.5)),
                    "font_size": int(round(width * 0.036)),
                    "font_weight": "bold",
                    "align": "center",
                },
            }
        )

    # Eyebrow pill + label
    eyebrow = copy["unit"] or copy["subheadline"]
    if eyebrow:
        pill_w = int(round(min(content_w * 0.72, width * 0.62)))
        pill_h = int(round(height * 0.038))
        pill_y = int(round(height * 0.48))
        elements.append(
            {
                "id": "eyebrow-pill",
                "type": "shape",
                "role": "eyebrow_frame",
                "locked": False,
                "editable": True,
                "x": margin,
                "y": pill_y,
                "width": pill_w,
                "height": pill_h,
                "z_index": 18,
                "style": {
                    "fill": "transparent",
                    "border_color": "#C4A35A",
                    "border_width": 1,
                    "border_radius": int(pill_h * 0.5),
                    "shape_kind": "rect",
                },
            }
        )
        elements.append(
            {
                "id": "unit-label",
                "type": "text",
                "role": "unit_label",
                "content": eyebrow.upper() if len(eyebrow) < 48 else eyebrow,
                "locked": False,
                "editable": True,
                "x": margin + 12,
                "y": pill_y,
                "width": pill_w - 24,
                "height": pill_h,
                "z_index": 19,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.022)),
                    "font_weight": "semibold",
                    "align": "left",
                    "color": "#C4A35A",
                    "letter_spacing": 0.08,
                },
            }
        )

    if copy["headline"]:
        elements.append(
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": copy["headline"],
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.535)),
                "width": content_w,
                "height": int(round(height * 0.09)),
                "z_index": 20,
                "typography": {
                    "font_family": "serif",
                    "font_size": int(round(width * 0.078)),
                    "font_weight": "bold",
                    "align": "left",
                    "color": "#F7F3EB",
                    "line_height": 1.05,
                },
            }
        )

    if copy["subheadline"] and copy["subheadline"] != copy["headline"] and copy["subheadline"] != eyebrow:
        elements.append(
            {
                "id": "subheadline",
                "type": "text",
                "role": "subheadline",
                "content": copy["subheadline"],
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.62)),
                "width": content_w,
                "height": int(round(height * 0.05)),
                "z_index": 21,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.028)),
                    "font_weight": "medium",
                    "align": "left",
                    "color": "#E8E0D4",
                    "line_height": 1.25,
                },
            }
        )

    # Price frame — CD recipe geometry; v2 keeps list price unstruck until revision.
    frame_y = int(round(height * 0.68))
    frame_h = int(round(height * 0.16 if revision_engine_v2 else height * 0.11))
    frame_w = int(round(content_w * 0.92))
    old_price = _tr_usd_display(copy["old_price"]) if revision_engine_v2 else copy["old_price"]
    new_price = _tr_usd_display(copy["new_price"]) if revision_engine_v2 else copy["new_price"]
    savings_price = _tr_usd_display(copy.get("savings_price") or "")
    has_price_stack = bool(old_price or new_price or revision_engine_v2)
    if has_price_stack:
        elements.append(
            {
                "id": "price-frame",
                "type": "rectangle",
                "role": "price_frame",
                "locked": False,
                "editable": True,
                "x": margin,
                "y": frame_y,
                "width": frame_w,
                "height": frame_h,
                "z_index": 22,
                "style": {
                    "fill": "rgba(12,10,8,0.22)",
                    "border_color": "#C4A35A",
                    "border_width": 1,
                    "border_radius": 4,
                    "shape_kind": "rect",
                },
            }
        )
        if not revision_engine_v2:
            elements.append(
                {
                    "id": "price-divider",
                    "type": "divider",
                    "role": "divider",
                    "locked": False,
                    "editable": True,
                    "x": margin + int(frame_w * 0.48),
                    "y": frame_y + int(frame_h * 0.22),
                    "width": 2,
                    "height": int(frame_h * 0.56),
                    "z_index": 23,
                    "style": {"fill": "#C4A35A", "shape_kind": "line"},
                }
            )
    if old_price or revision_engine_v2:
        old_typo: dict[str, Any] = {
            "font_family": "sans",
            "font_size": int(round(width * 0.036)),
            "font_weight": "normal",
            "align": "left",
            "color": "#D4C4A8",
        }
        if not revision_engine_v2:
            old_typo["text_decoration"] = "line-through"
        elements.append(
            {
                "id": "old-price",
                "type": "text",
                "role": "old_price",
                "content": old_price,
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "visible": bool(old_price),
                "x": margin + 16,
                "y": frame_y + int(frame_h * (0.10 if revision_engine_v2 else 0.28)),
                "width": int(frame_w * (0.90 if revision_engine_v2 else 0.42)),
                "height": int(frame_h * (0.28 if revision_engine_v2 else 0.4)),
                "z_index": 24,
                "typography": old_typo,
            }
        )
    if new_price or revision_engine_v2:
        elements.append(
            {
                "id": "new-price",
                "type": "text",
                "role": "new_price",
                "content": new_price,
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "visible": bool(new_price) and not revision_engine_v2,
                "x": margin + (16 if revision_engine_v2 else int(frame_w * 0.52)),
                "y": frame_y + int(frame_h * (0.38 if revision_engine_v2 else 0.18)),
                "width": int(frame_w * (0.90 if revision_engine_v2 else 0.44)),
                "height": int(frame_h * (0.32 if revision_engine_v2 else 0.62)),
                "z_index": 25,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * (0.048 if revision_engine_v2 else 0.072))),
                    "font_weight": "bold",
                    "align": "left",
                    "color": "#C4A35A",
                },
            }
        )
    if revision_engine_v2:
        elements.append(
            {
                "id": "savings-price",
                "type": "text",
                "role": "savings_price",
                "content": f"Kazancınız {savings_price}" if savings_price else "",
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "visible": bool(savings_price),
                "x": margin + 16,
                "y": frame_y + int(frame_h * 0.72),
                "width": int(frame_w * 0.90),
                "height": int(frame_h * 0.24),
                "z_index": 26,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.028)),
                    "font_weight": "medium",
                    "align": "left",
                    "color": "#E8E0D4",
                },
            }
        )

    support_y = int(round(height * (0.85 if revision_engine_v2 else 0.81)))
    for idx, line in enumerate(supporting[:2]):
        elements.append(
            {
                "id": f"support-message-{idx + 1}",
                "type": "text",
                "role": "support_message",
                "content": line,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": support_y + idx * int(round(height * 0.028)),
                "width": content_w,
                "height": int(round(height * 0.026)),
                "z_index": 28 + idx,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.024)),
                    "font_weight": "normal",
                    "align": "left",
                    "color": "#EDE6DA",
                },
            }
        )

    cta_w = int(round(width * float((plan.get("cta") or {}).get("width_pct") or 0.62)))
    cta_h = int(round(height * 0.052))
    elements.append(
        {
            "id": "cta",
            "type": "cta",
            "role": "cta",
            "content": copy["cta"],
            "locked": False,
            "editable": True,
            "x": margin,
            "y": int(round(height * 0.90)),
            "width": cta_w,
            "height": cta_h,
            "z_index": 40,
            "style": {
                "background_color": "#C4A35A",
                "text_color": "#1A1510",
                "border_color": "#C4A35A",
                "border_radius": int(round(cta_h * 0.35)),
                "padding": int(round(cta_h * 0.22)),
                "font_size": int(round(width * 0.026)),
                "font_weight": "semibold",
                "align": "center",
            },
        }
    )
    return elements


def _build_location_elements(
    *,
    width: int,
    height: int,
    margin: int,
    content_w: int,
    logo_id: str,
    copy: dict[str, str],
    supporting: list[str],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    _append_gradient(
        elements,
        eid="overlay-top-dark",
        y=0,
        h=int(height * 0.26),
        width=width,
        fill=(
            "linear-gradient(to bottom, rgba(8,6,4,0.62) 0%, rgba(8,6,4,0.22) 60%, transparent 100%)"
        ),
        z_index=4,
    )
    _append_gradient(
        elements,
        eid="overlay-mid-left",
        y=int(height * 0.40),
        h=int(height * 0.32),
        width=int(width * 0.58),
        fill=(
            "linear-gradient(to right, rgba(8,6,4,0.38) 0%, rgba(8,6,4,0.12) 65%, transparent 100%)"
        ),
        z_index=5,
    )
    logo = _logo_geometry(
        width=width,
        height=height,
        margin=margin,
        placement="top_center",
        scale=float((plan.get("logo") or {}).get("scale") or 0.18),
    )
    elements.append(
        {
            "id": "logo",
            "type": "logo",
            "role": "logo",
            "asset_id": logo_id,
            "locked": False,
            "editable": True,
            "lock_aspect_ratio": True,
            **logo,
            "z_index": 10,
            "opacity": 1.0,
        }
    )

    eyebrow = copy["subheadline"] or copy["unit"]
    if eyebrow:
        pill_w = int(round(min(width * 0.78, content_w)))
        pill_h = int(round(height * 0.036))
        pill_x = int(round((width - pill_w) / 2))
        pill_y = int(round(height * 0.14))
        elements.append(
            {
                "id": "eyebrow-pill",
                "type": "shape",
                "role": "eyebrow_frame",
                "x": pill_x,
                "y": pill_y,
                "width": pill_w,
                "height": pill_h,
                "z_index": 18,
                "editable": True,
                "style": {
                    "fill": "transparent",
                    "border_color": "#C4A35A",
                    "border_width": 1,
                    "border_radius": int(pill_h * 0.5),
                    "shape_kind": "rect",
                },
            }
        )
        elements.append(
            {
                "id": "subheadline",
                "type": "text",
                "role": "subheadline",
                "content": eyebrow.upper(),
                "locked": False,
                "editable": True,
                "x": pill_x + 10,
                "y": pill_y,
                "width": pill_w - 20,
                "height": pill_h,
                "z_index": 19,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.020)),
                    "font_weight": "semibold",
                    "align": "center",
                    "color": "#C4A35A",
                },
            }
        )

    if copy["headline"]:
        elements.append(
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": copy["headline"],
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.22)),
                "width": content_w,
                "height": int(round(height * 0.14)),
                "z_index": 20,
                "typography": {
                    "font_family": "serif",
                    "font_size": int(round(width * 0.074)),
                    "font_weight": "bold",
                    "align": "center",
                    "color": "#FFFFFF",
                    "line_height": 1.08,
                },
            }
        )

    if supporting:
        elements.append(
            {
                "id": "support-divider",
                "type": "divider",
                "role": "divider",
                "x": margin,
                "y": int(round(height * 0.50)),
                "width": int(content_w * 0.42),
                "height": 2,
                "z_index": 21,
                "editable": True,
                "style": {"fill": "#C4A35A", "shape_kind": "line"},
            }
        )
    for idx, line in enumerate(supporting[:2]):
        elements.append(
            {
                "id": f"support-message-{idx + 1}",
                "type": "text",
                "role": "support_message",
                "content": line,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * (0.53 + idx * 0.055))),
                "width": int(content_w * 0.55),
                "height": int(round(height * 0.045)),
                "z_index": 22 + idx,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.026)),
                    "font_weight": "normal",
                    "align": "left",
                    "color": "#F7F3EB",
                },
            }
        )

    cta_w = int(round(width * float((plan.get("cta") or {}).get("width_pct") or 0.48)))
    cta_h = int(round(height * 0.05))
    elements.append(
        {
            "id": "cta",
            "type": "cta",
            "role": "cta",
            "content": copy["cta"],
            "locked": False,
            "editable": True,
            "x": margin,
            "y": int(round(height * 0.88)),
            "width": cta_w,
            "height": cta_h,
            "z_index": 40,
            "style": {
                "background_color": "#C4A35A",
                "text_color": "#1A1510",
                "border_radius": int(round(cta_h * 0.35)),
                "padding": int(round(cta_h * 0.22)),
                "font_size": int(round(width * 0.026)),
                "font_weight": "semibold",
                "align": "center",
            },
        }
    )
    return elements


def _build_lifestyle_elements(
    *,
    width: int,
    height: int,
    margin: int,
    content_w: int,
    logo_id: str,
    copy: dict[str, str],
    supporting: list[str],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    _append_gradient(
        elements,
        eid="overlay-top-light",
        y=0,
        h=int(height * 0.36),
        width=width,
        fill=(
            "linear-gradient(to bottom, rgba(245,240,232,0.94) 0%, rgba(245,240,232,0.62) 48%, "
            "transparent 100%)"
        ),
        z_index=4,
    )
    _append_gradient(
        elements,
        eid="overlay-bottom-dark",
        y=int(height * 0.70),
        h=int(height * 0.30),
        width=width,
        fill=(
            "linear-gradient(to top, rgba(12,10,8,0.82) 0%, rgba(12,10,8,0.40) 55%, transparent 100%)"
        ),
        z_index=5,
    )
    logo = _logo_geometry(
        width=width,
        height=height,
        margin=margin,
        placement="top_center",
        scale=float((plan.get("logo") or {}).get("scale") or 0.17),
    )
    elements.append(
        {
            "id": "logo",
            "type": "logo",
            "role": "logo",
            "asset_id": logo_id,
            "locked": False,
            "editable": True,
            "lock_aspect_ratio": True,
            **logo,
            "z_index": 10,
            "opacity": 1.0,
        }
    )

    eyebrow = copy["subheadline"] or copy["unit"]
    if eyebrow:
        elements.append(
            {
                "id": "subheadline",
                "type": "text",
                "role": "subheadline",
                "content": eyebrow.upper(),
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.125)),
                "width": content_w,
                "height": int(round(height * 0.035)),
                "z_index": 18,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.020)),
                    "font_weight": "semibold",
                    "align": "center",
                    "color": "#8A7355",
                    "letter_spacing": 0.12,
                },
            }
        )

    if copy["headline"]:
        elements.append(
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": copy["headline"],
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.17)),
                "width": content_w,
                "height": int(round(height * 0.18)),
                "z_index": 20,
                "typography": {
                    "font_family": "serif",
                    "font_size": int(round(width * 0.064)),
                    "font_weight": "bold",
                    "align": "center",
                    "color": "#2A241C",
                    "line_height": 1.12,
                },
            }
        )

    n = max(1, min(3, len(supporting) or 1))
    col_w = int(content_w / n)
    base_y = int(round(height * 0.76))
    for idx, line in enumerate(supporting[:3]):
        cx = margin + idx * col_w
        elements.append(
            {
                "id": f"feature-dot-{idx + 1}",
                "type": "shape",
                "role": "icon",
                "x": cx + int(col_w / 2) - 5,
                "y": base_y,
                "width": 10,
                "height": 10,
                "z_index": 25,
                "editable": True,
                "style": {
                    "fill": "#C4A35A",
                    "border_radius": 999,
                    "shape_kind": "rect",
                },
            }
        )
        elements.append(
            {
                "id": f"support-message-{idx + 1}",
                "type": "text",
                "role": "support_message",
                "content": line,
                "locked": False,
                "editable": True,
                "x": cx + 6,
                "y": base_y + 18,
                "width": col_w - 12,
                "height": int(round(height * 0.055)),
                "z_index": 26 + idx,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.022)),
                    "font_weight": "normal",
                    "align": "center",
                    "color": "#F7F3EB",
                },
            }
        )

    cta_w = int(round(width * float((plan.get("cta") or {}).get("width_pct") or 0.46)))
    cta_h = int(round(height * 0.048))
    elements.append(
        {
            "id": "cta",
            "type": "cta",
            "role": "cta",
            "content": copy["cta"],
            "locked": False,
            "editable": True,
            "x": int(round((width - cta_w) / 2)),
            "y": int(round(height * 0.90)),
            "width": cta_w,
            "height": cta_h,
            "z_index": 40,
            "style": {
                "background_color": "#C4A35A",
                "text_color": "#1A1510",
                "border_radius": int(round(cta_h * 0.45)),
                "padding": int(round(cta_h * 0.22)),
                "font_size": int(round(width * 0.024)),
                "font_weight": "semibold",
                "align": "center",
            },
        }
    )
    return elements


def _build_brand_elements(
    *,
    width: int,
    height: int,
    margin: int,
    content_w: int,
    logo_id: str,
    copy: dict[str, str],
    supporting: list[str],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    _append_gradient(
        elements,
        eid="overlay-soft-vignette",
        y=0,
        h=height,
        width=width,
        fill=(
            "linear-gradient(to bottom, rgba(8,6,4,0.45) 0%, transparent 28%, transparent 72%, "
            "rgba(8,6,4,0.55) 100%)"
        ),
        z_index=4,
    )
    logo = _logo_geometry(
        width=width,
        height=height,
        margin=margin,
        placement="top_center",
        scale=float((plan.get("logo") or {}).get("scale") or 0.24),
    )
    elements.append(
        {
            "id": "logo",
            "type": "logo",
            "role": "logo",
            "asset_id": logo_id,
            "locked": False,
            "editable": True,
            "lock_aspect_ratio": True,
            **logo,
            "z_index": 10,
            "opacity": 1.0,
        }
    )
    if copy["headline"]:
        elements.append(
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": copy["headline"],
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.18)),
                "width": content_w,
                "height": int(round(height * 0.12)),
                "z_index": 20,
                "typography": {
                    "font_family": "serif",
                    "font_size": int(round(width * 0.062)),
                    "font_weight": "bold",
                    "align": "center",
                    "color": "#F7F3EB",
                    "line_height": 1.1,
                },
            }
        )
    support_y = int(round(height * 0.78))
    support_h = int(round(height * 0.04))
    for idx, line in enumerate(supporting[:2]):
        elements.append(
            {
                "id": f"support-message-{idx + 1}",
                "type": "text",
                "role": "support_message",
                "content": line,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": support_y + idx * int(round(height * 0.045)),
                "width": content_w,
                "height": support_h,
                "z_index": 26 + idx,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.026)),
                    "font_weight": "normal",
                    "align": "center",
                    "color": "#E8E0D4",
                },
            }
        )
    cta_w = int(round(width * float((plan.get("cta") or {}).get("width_pct") or 0.44)))
    cta_h = int(round(height * 0.048))
    elements.append(
        {
            "id": "cta",
            "type": "cta",
            "role": "cta",
            "content": copy["cta"],
            "locked": False,
            "editable": True,
            "x": int(round((width - cta_w) / 2)),
            "y": int(round(height * 0.90)),
            "width": cta_w,
            "height": cta_h,
            "z_index": 40,
            "style": {
                "background_color": "#C4A35A",
                "text_color": "#1A1510",
                "border_radius": int(round(cta_h * 0.4)),
                "font_size": int(round(width * 0.024)),
                "font_weight": "semibold",
                "align": "center",
            },
        }
    )
    return elements


def build_design_spec(
    *,
    production_brief: dict[str, Any],
    texts: dict[str, str],
    master_background_asset_id: UUID | str,
    logo_asset_id: UUID | str,
    finished_ad_raster_asset_id: UUID | str | None = None,
    aspect_ratio: str = "4:5",
    format_preset: str = "portrait",
    language: str = "tr",
    campaign_intent: str | None = None,
    composition_plan: dict[str, Any] | None = None,
    revision_engine_v2: bool = False,
) -> dict[str, Any]:
    """Emit Design Spec from composition plan + FINAL brief (intent-specific layout)."""
    width, height = canvas_size_for_aspect(aspect_ratio, format_preset)
    final = production_brief.get("final_copy") if isinstance(production_brief.get("final_copy"), dict) else {}
    intent = _s(
        campaign_intent
        or production_brief.get("campaign_intent")
        or texts.get("campaign_mode"),
        "general_awareness",
    ).lower()

    plan = composition_plan or build_composition_plan(
        campaign_intent=intent,
        production_brief=production_brief,
        texts=texts,
        design_direction=production_brief.get("design_direction")
        if isinstance(production_brief.get("design_direction"), dict)
        else None,
        message_strategy=production_brief.get("message_strategy")
        if isinstance(production_brief.get("message_strategy"), dict)
        else None,
        aspect_ratio=aspect_ratio,
        language=language,
    )

    headline = _s(texts.get("headline") or final.get("headline") or production_brief.get("hero"))
    subheadline = _s(
        texts.get("hero")
        or production_brief.get("hero")
        or texts.get("sales_hook")
        or final.get("eyebrow")
    )
    unit_label = _s(texts.get("unit") or final.get("unit") or texts.get("eyebrow") or final.get("eyebrow"))
    old_price = _s(texts.get("list_price") or final.get("list_price"))
    new_price = _s(texts.get("offer_price") or final.get("offer_price"))
    badge = _badge_display(_s(texts.get("value_badge") or final.get("value_badge")))
    cta = _s(texts.get("cta") or final.get("cta") or production_brief.get("cta"), "Detayları İncele")
    supporting = _supporting_list(production_brief, texts)

    # Premium simplicity: lifestyle/location keep 0–1 supporting in primary stack when sparse
    density = str(plan.get("content_density") or "medium")
    if density == "sparse":
        supporting = supporting[:2]

    margin = int(round(width * float((plan.get("safe_margins") or {}).get("x_pct") or 0.07)))
    content_w = width - margin * 2
    bg_id = str(master_background_asset_id)
    logo_id = str(logo_asset_id)

    savings_price = _s(texts.get("savings") or final.get("savings"))
    copy = {
        "headline": headline,
        "subheadline": subheadline,
        "unit": unit_label,
        "old_price": old_price,
        "new_price": new_price,
        "savings_price": savings_price,
        "badge": badge,
        "cta": cta,
    }

    elements: list[dict[str, Any]] = [
        {
            "id": "master_background",
            "type": "image",
            "role": "background",
            "asset_id": bg_id,
            "locked": True,
            "editable": False,
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "z_index": 0,
            "opacity": 1.0,
            "treatment": plan.get("image") or {},
        }
    ]

    family = str(plan.get("layout_family") or "")
    builder_kwargs = dict(
        width=width,
        height=height,
        margin=margin,
        content_w=content_w,
        logo_id=logo_id,
        copy=copy,
        supporting=supporting,
        plan=plan,
    )
    use_price_stack = (
        revision_engine_v2
        and bool(copy["old_price"] or copy["badge"] or copy["new_price"])
    ) or family == "price_lower_third" or intent in {
        "price_campaign",
        "sales_offer",
        "launch",
        "launch_price",
    }
    if use_price_stack:
        elements.extend(
            _build_price_elements(**builder_kwargs, revision_engine_v2=revision_engine_v2)
        )
    elif family == "location_place_led" or intent == "location":
        elements.extend(_build_location_elements(**builder_kwargs))
    elif family == "lifestyle_editorial" or intent in {"lifestyle", "amenities"}:
        elements.extend(_build_lifestyle_elements(**builder_kwargs))
    else:
        elements.extend(_build_brand_elements(**builder_kwargs))

    return {
        "version": 2,
        "mode": "editable_finished_ad",
        "canvas": {
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "format_preset": format_preset,
        },
        "language": language,
        "campaign_intent": intent,
        "composition_plan": plan,
        "composition": {
            "focal_zone": (plan.get("focal_point") or {}).get("zone"),
            "text_zones": (plan.get("zones") or {}).get("text_safe"),
            "safe_margins": plan.get("safe_margins"),
            "alignment_system": plan.get("alignment_system"),
            "layout_family": plan.get("layout_family"),
        },
        "background": {
            "asset_id": bg_id,
            "crop": (plan.get("image") or {}).get("crop", "cover"),
            "position": (plan.get("image") or {}).get("position", "center"),
            "treatment": (plan.get("image") or {}).get("treatment"),
        },
        "master_background_asset_id": bg_id,
        "logo_asset_id": logo_id,
        "finished_ad_raster_asset_id": str(finished_ad_raster_asset_id)
        if finished_ad_raster_asset_id
        else None,
        "locked_background": True,
        "revision_engine_v2": bool(revision_engine_v2),
        "elements": elements,
        "editable_text_targets": _editable_text_targets(elements),
    }


def _native_cover_crop(image: Any, canvas_w: int, canvas_h: int) -> Any:
    """Match SMB object-fit: cover; object-position: center."""
    src_w, src_h = image.size
    if src_w <= 0 or src_h <= 0 or canvas_w <= 0 or canvas_h <= 0:
        return image
    target_ratio = canvas_w / canvas_h
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = max(1, int(round(src_h * target_ratio)))
        left = max(0, (src_w - new_w) // 2)
        image = image.crop((left, 0, left + new_w, src_h))
    elif src_ratio < target_ratio:
        new_h = max(1, int(round(src_w / target_ratio)))
        top = max(0, (src_h - new_h) // 2)
        image = image.crop((0, top, src_w, top + new_h))
    return image.resize((canvas_w, canvas_h))


def analyze_native_photograph(
    image_bytes: bytes | None,
    *,
    canvas_width: int,
    canvas_height: int,
) -> dict[str, Any]:
    """Read the locked interior before placing type — no fifth layer, no GPT Image."""
    empty = {
        "available": False,
        "visual_focal_point": {"x": 0.50, "y": 0.52},
        "negative_space": [],
        "bright_regions": [],
        "dark_regions": [],
        "furniture_building_focal": {"x": 0.22, "y": 0.34, "width": 0.56, "height": 0.36},
        "safe_headline_zone": {"x": 0.07, "y": 0.08, "width": 0.50, "height": 0.28},
        "safe_logo_zone": {"x": 0.72, "y": 0.045, "width": 0.21, "height": 0.08},
        "safe_cta_zone": {"x": 0.07, "y": 0.86, "width": 0.40, "height": 0.08},
        "do_not_cover": [{"role": "furniture_focal", "x": 0.22, "y": 0.34, "width": 0.56, "height": 0.36}],
        "headline_ink": _NATIVE_CHARCOAL,
        "headline_align": "left",
        "headline_family": "serif",
    }
    if not image_bytes:
        return empty
    try:
        from io import BytesIO

        from PIL import Image, ImageFilter, ImageStat
    except Exception:
        return empty
    try:
        src = Image.open(BytesIO(image_bytes)).convert("RGB")
        framed = _native_cover_crop(src, canvas_width, canvas_height)
        gray = framed.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        cols, rows = 8, 10
        cell_w = canvas_width / cols
        cell_h = canvas_height / rows
        grid: list[list[dict[str, float]]] = []
        lum_all: list[float] = []
        edge_all: list[float] = []
        for r in range(rows):
            row: list[dict[str, float]] = []
            for c in range(cols):
                box = (
                    int(c * cell_w),
                    int(r * cell_h),
                    int((c + 1) * cell_w),
                    int((r + 1) * cell_h),
                )
                lum = float(ImageStat.Stat(gray.crop(box)).mean[0])
                edge = float(ImageStat.Stat(edges.crop(box)).mean[0])
                std = float(ImageStat.Stat(gray.crop(box)).stddev[0])
                row.append({"lum": lum, "edge": edge, "std": std})
                lum_all.append(lum)
                edge_all.append(edge)
            grid.append(row)
        mean_lum = sum(lum_all) / max(len(lum_all), 1)
        mean_edge = sum(edge_all) / max(len(edge_all), 1)
        bright: list[dict[str, float]] = []
        dark: list[dict[str, float]] = []
        negative: list[dict[str, float]] = []
        focal_cells: list[tuple[int, int]] = []
        view_cells: list[tuple[int, int]] = []
        for r in range(rows):
            for c in range(cols):
                cell = grid[r][c]
                nx, ny = c / cols, r / rows
                nw, nh = 1 / cols, 1 / rows
                rec = {"x": nx, "y": ny, "width": nw, "height": nh, "lum": cell["lum"], "edge": cell["edge"]}
                if cell["lum"] >= 168:
                    bright.append(rec)
                if cell["lum"] <= 102:
                    dark.append(rec)
                if cell["edge"] < mean_edge * 0.72 and cell["std"] < 38:
                    negative.append(rec)
                in_mid = 0.22 <= ny <= 0.78 and 0.12 <= nx <= 0.88
                if in_mid and cell["edge"] > mean_edge * 1.28:
                    focal_cells.append((c, r))
                # Bright, quiet upper-center = windows / sky — do not cover the view.
                if (
                    ny < 0.48
                    and 0.22 <= nx <= 0.72
                    and cell["lum"] >= 188
                    and cell["edge"] < mean_edge * 0.85
                ):
                    view_cells.append((c, r))

        def _bbox(cells: list[tuple[int, int]]) -> dict[str, float] | None:
            if not cells:
                return None
            cs = [c for c, _r in cells]
            rs = [r for _c, r in cells]
            x0, x1 = min(cs) / cols, (max(cs) + 1) / cols
            y0, y1 = min(rs) / rows, (max(rs) + 1) / rows
            return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}

        focal_box = _bbox(focal_cells) or {"x": 0.22, "y": 0.34, "width": 0.56, "height": 0.36}
        view_box = _bbox(view_cells)
        do_not_cover: list[dict[str, Any]] = [{"role": "furniture_building_focal", **focal_box}]
        if view_box:
            do_not_cover.append({"role": "window_or_view", **view_box})

        protected = set(focal_cells) | set(view_cells)

        def _region_ok(c0: int, c1: int, r0: int, r1: int) -> dict[str, float]:
            vals: list[dict[str, float]] = []
            hit = 0
            total = 0
            for r in range(r0, r1):
                for c in range(c0, c1):
                    total += 1
                    vals.append(grid[r][c])
                    if (c, r) in protected:
                        hit += 1
            lum = sum(v["lum"] for v in vals) / max(len(vals), 1)
            edge = sum(v["edge"] for v in vals) / max(len(vals), 1)
            return {
                "lum": lum,
                "edge": edge,
                "protected_frac": hit / max(total, 1),
            }

        candidates = [
            ("top_left", 0, 4, 0, 3, 1.20),
            ("upper_left", 0, 4, 1, 4, 1.12),
            ("top_right_type", 4, 8, 0, 3, 0.72),
            ("lower_left", 0, 4, 6, 9, 1.00),
            ("lower_third_left", 0, 5, 7, 10, 0.88),
        ]
        scored: list[tuple[float, str, dict[str, float]]] = []
        for name, c0, c1, r0, r1, bias in candidates:
            stats = _region_ok(c0, c1, r0, r1)
            # Prefer quiet, unprotected negative space. Bright walls are OK (charcoal ink).
            score = bias * (1.0 - stats["protected_frac"]) * (1.15 if stats["edge"] < mean_edge else 0.75)
            if stats["protected_frac"] > 0.55:
                continue
            scored.append((score, name, stats))
        scored.sort(key=lambda row: row[0], reverse=True)
        if scored:
            _score, zone_name, zone_stats = scored[0]
        else:
            zone_name, zone_stats = "top_left", _region_ok(0, 4, 0, 3)

        zone_boxes = {
            "top_left": {"x": 0.065, "y": 0.07, "width": 0.50, "height": 0.30},
            "upper_left": {"x": 0.065, "y": 0.10, "width": 0.50, "height": 0.28},
            "top_right_type": {"x": 0.44, "y": 0.07, "width": 0.50, "height": 0.28},
            "lower_left": {"x": 0.065, "y": 0.58, "width": 0.52, "height": 0.24},
            "lower_third_left": {"x": 0.065, "y": 0.66, "width": 0.54, "height": 0.22},
        }
        headline_zone = dict(zone_boxes.get(zone_name) or zone_boxes["top_left"])
        ink = _NATIVE_CREAM if zone_stats["lum"] < 128 else _NATIVE_CHARCOAL
        align = "left" if "right" not in zone_name else "right"

        if "left" in zone_name:
            right_top = _region_ok(6, 8, 0, 2)
            right_lower = _region_ok(6, 8, 1, 3)
            logo_y = 0.045
            if right_top["lum"] > 170 and right_lower["lum"] + 8 < right_top["lum"]:
                logo_y = 0.09
            logo_zone = {
                "x": 0.70,
                "y": logo_y,
                "width": 0.23,
                "height": 0.08,
                "lum": min(right_top["lum"], right_lower["lum"]),
            }
        else:
            left_top = _region_ok(0, 2, 0, 2)
            left_lower = _region_ok(0, 2, 1, 3)
            logo_y = 0.045
            if left_top["lum"] > 170 and left_lower["lum"] + 8 < left_top["lum"]:
                logo_y = 0.09
            logo_zone = {
                "x": 0.065,
                "y": logo_y,
                "width": 0.23,
                "height": 0.08,
                "lum": min(left_top["lum"], left_lower["lum"]),
            }

        floor = _region_ok(0, 8, 8, 10)
        cta_y = 0.875 if floor["protected_frac"] < 0.45 else 0.82
        cta_zone = {
            "x": headline_zone["x"],
            "y": cta_y,
            "width": 0.38,
            "height": 0.055,
        }

        brightest = max(lum_all) if lum_all else mean_lum
        darkest = min(lum_all) if lum_all else mean_lum
        return {
            "available": True,
            "canvas": {"width": canvas_width, "height": canvas_height},
            "mean_luminance": round(mean_lum, 1),
            "mean_edge": round(mean_edge, 1),
            "brightest": round(brightest, 1),
            "darkest": round(darkest, 1),
            "visual_focal_point": {
                "x": round(focal_box["x"] + focal_box["width"] / 2, 3),
                "y": round(focal_box["y"] + focal_box["height"] / 2, 3),
            },
            "negative_space": negative[:12],
            "bright_regions": bright[:12],
            "dark_regions": dark[:12],
            "furniture_building_focal": focal_box,
            "window_or_view": view_box,
            "safe_headline_zone": headline_zone,
            "safe_logo_zone": logo_zone,
            "safe_cta_zone": cta_zone,
            "do_not_cover": do_not_cover,
            "headline_zone_name": zone_name,
            "headline_zone_luminance": round(zone_stats["lum"], 1),
            "headline_ink": ink,
            "headline_align": align,
            "headline_family": "serif",
        }
    except Exception:
        return empty


def _norm_to_px(zone: dict[str, Any], width: int, height: int) -> dict[str, int]:
    return {
        "x": int(round(float(zone.get("x") or 0) * width)),
        "y": int(round(float(zone.get("y") or 0) * height)),
        "width": int(round(float(zone.get("width") or 0.4) * width)),
        "height": int(round(float(zone.get("height") or 0.2) * height)),
    }


def _rects_overlap(a: dict[str, int], b: dict[str, int], *, pad: int = 12) -> bool:
    return not (
        a["x"] + a["width"] + pad < b["x"]
        or b["x"] + b["width"] + pad < a["x"]
        or a["y"] + a["height"] + pad < b["y"]
        or b["y"] + b["height"] + pad < a["y"]
    )


def _editorial_headline_breaks(text: str) -> str:
    """CD owns line breaks — editorial stack, not one long centered line."""
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return raw
    if "\n" in raw:
        return "\n".join(line.strip() for line in raw.split("\n") if line.strip())
    words = raw.split()
    if len(words) <= 1:
        return raw
    if len(words) <= 3:
        return "\n".join(words)
    # 4+ words: 2–3 lines by running width, prefer a short last line.
    target = max(2, min(3, (len(words) + 1) // 2))
    lines: list[list[str]] = [[] for _ in range(target)]
    lengths = [0] * target
    idx = 0
    for word in words:
        if idx < target - 1 and lengths[idx] >= max(8, len(raw) / target):
            idx += 1
        lines[idx].append(word)
        lengths[idx] += len(word) + 1
    return "\n".join(" ".join(part) for part in lines if part)


def _editorial_cta_copy(cta: str) -> str:
    label = (cta or "").strip() or "Detayları İncele"
    if not label.endswith("→"):
        return f"{label} →"
    return label


def _native_art_direction_boxes(
    *,
    width: int,
    height: int,
    margin: int,
    analysis: dict[str, Any],
    headline_lines: int,
) -> dict[str, Any]:
    """Place the 4 layers from photograph analysis, not a fixed Instagram template."""
    headline_zone = analysis.get("safe_headline_zone") if isinstance(analysis.get("safe_headline_zone"), dict) else {}
    logo_zone = analysis.get("safe_logo_zone") if isinstance(analysis.get("safe_logo_zone"), dict) else {}
    cta_zone = analysis.get("safe_cta_zone") if isinstance(analysis.get("safe_cta_zone"), dict) else {}
    align = _s(analysis.get("headline_align"), "left")
    ink = _s(analysis.get("headline_ink"), _NATIVE_CHARCOAL)
    family = _s(analysis.get("headline_family"), "serif")

    if headline_lines >= 3:
        font_size = int(round(width * 0.076))
        line_height = 1.05
        letter_spacing = 0.4
    elif headline_lines == 2:
        font_size = int(round(width * 0.068))
        line_height = 1.08
        letter_spacing = 0.6
    else:
        font_size = int(round(width * 0.058))
        line_height = 1.12
        letter_spacing = 0.8

    headline = _norm_to_px(headline_zone, width, height)
    headline["x"] = max(margin, min(headline["x"], width - margin - 80))
    headline["width"] = max(int(width * 0.42), min(headline["width"], int(width * 0.56)))
    if align == "right":
        headline["x"] = max(margin, width - margin - headline["width"])
    else:
        headline["x"] = margin if headline["x"] > margin + 24 else headline["x"]
        headline["x"] = max(margin, headline["x"])
    headline["height"] = max(int(round(font_size * line_height * headline_lines * 1.16)), int(height * 0.16))
    headline["y"] = max(int(height * 0.045), min(headline["y"], int(height * 0.72)))

    logo_scale = 0.118
    logo_w = int(round(width * logo_scale))
    logo_h = int(round(height * 0.046))
    logo = _norm_to_px(logo_zone, width, height)
    logo["width"] = logo_w
    logo["height"] = logo_h
    if align == "left":
        logo["x"] = width - margin - logo_w
    else:
        logo["x"] = margin
    logo["y"] = max(int(height * 0.038), min(logo["y"], int(height * 0.12)))
    if _rects_overlap(logo, headline, pad=16):
        logo["y"] = max(margin, headline["y"] - logo_h - int(height * 0.02))
        if _rects_overlap(logo, headline, pad=16):
            logo["y"] = min(int(height * 0.12), headline["y"] + headline["height"] + int(height * 0.02))

    cta_w = int(round(width * 0.34))
    cta_h = int(round(height * 0.038))
    cta = _norm_to_px(cta_zone, width, height)
    cta["width"] = cta_w
    cta["height"] = cta_h
    cta["x"] = headline["x"] if align != "right" else max(margin, headline["x"] + headline["width"] - cta_w)
    cta["y"] = max(int(height * 0.78), min(int(round((cta_zone.get("y") or 0.875) * height)), height - margin - cta_h))
    if _rects_overlap(cta, headline, pad=20):
        cta["y"] = min(height - margin - cta_h, headline["y"] + headline["height"] + int(height * 0.04))
    if _rects_overlap(cta, logo, pad=12):
        cta["y"] = min(height - margin - cta_h, max(cta["y"], logo["y"] + logo["height"] + 16))

    return {
        "headline": headline,
        "logo": logo,
        "cta": cta,
        "align": align,
        "ink": ink,
        "family": family,
        "font_size": font_size,
        "line_height": line_height,
        "letter_spacing": letter_spacing,
        "logo_scale": logo_scale,
    }


def build_golden_native_v1_spec(
    *,
    production_brief: dict[str, Any],
    texts: dict[str, str],
    master_background_asset_id: UUID | str,
    logo_asset_id: UUID | str,
    aspect_ratio: str = "4:5",
    format_preset: str = "portrait",
    language: str = "tr",
    campaign_intent: str | None = None,
    composition_plan: dict[str, Any] | None = None,
    image_bytes: bytes | None = None,
    image_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Proof-of-concept Design Spec: exactly 4 real layers. Renderer applies CD recipe only.

    Layers: BACKGROUND (approved interior IMAGE), HEADLINE (TEXT), PROJECT LOGO (IMAGE),
    CTA (editable button). No supporting copy, badge, price, icon, or overlay wash.
    Art direction v2 places those four layers from a photograph reading.
    """
    width, height = canvas_size_for_aspect(aspect_ratio, format_preset)
    final = production_brief.get("final_copy") if isinstance(production_brief.get("final_copy"), dict) else {}
    intent = _s(
        campaign_intent
        or production_brief.get("campaign_intent")
        or texts.get("campaign_mode"),
        "lifestyle",
    ).lower()

    plan = composition_plan or build_composition_plan(
        campaign_intent=intent,
        production_brief=production_brief,
        texts=texts,
        design_direction=production_brief.get("design_direction")
        if isinstance(production_brief.get("design_direction"), dict)
        else None,
        message_strategy=production_brief.get("message_strategy")
        if isinstance(production_brief.get("message_strategy"), dict)
        else None,
        aspect_ratio=aspect_ratio,
        language=language,
    )

    headline_src = _s(texts.get("headline") or final.get("headline") or production_brief.get("hero"))
    headline = _editorial_headline_breaks(headline_src)
    cta = _editorial_cta_copy(
        _s(texts.get("cta") or final.get("cta") or production_brief.get("cta"), "Detayları İncele")
    )
    margin = int(round(width * 0.065))
    bg_id = str(master_background_asset_id)
    logo_id = str(logo_asset_id)

    analysis = image_analysis if isinstance(image_analysis, dict) else None
    if analysis is None or not analysis.get("available"):
        computed = analyze_native_photograph(
            image_bytes,
            canvas_width=width,
            canvas_height=height,
        )
        if analysis is None or computed.get("available"):
            analysis = computed
    analysis = analysis or analyze_native_photograph(None, canvas_width=width, canvas_height=height)

    boxes = _native_art_direction_boxes(
        width=width,
        height=height,
        margin=margin,
        analysis=analysis,
        headline_lines=max(1, headline.count("\n") + 1),
    )
    headline_box = boxes["headline"]
    logo_geo = boxes["logo"]
    cta_box = boxes["cta"]
    headline_color = boxes["ink"]
    headline_align = boxes["align"]
    headline_family = boxes["family"]
    headline_size = boxes["font_size"]
    line_height = boxes["line_height"]
    letter_spacing = boxes["letter_spacing"]

    image_plan = plan.get("image") if isinstance(plan.get("image"), dict) else {}
    headline_placement = str(analysis.get("headline_zone_name") or "top_left")
    logo_placement = "top_right" if headline_align == "left" else "top_left"
    cta_placement = "bottom_left" if headline_align != "right" else "bottom_right"

    recipe = {
        "renderer": "golden_native_v1",
        "art_direction": "v2_image_aware",
        "background_asset_id": bg_id,
        "crop": image_plan.get("crop") or "cover",
        "position": image_plan.get("position") or "center",
        "headline": {
            "text": headline,
            "placement": headline_placement,
            "width": headline_box["width"],
            "x": headline_box["x"],
            "y": headline_box["y"],
            "max_width": headline_box["width"],
            "font_size": headline_size,
            "font_weight": "bold",
            "font_family": headline_family,
            "line_height": line_height,
            "letter_spacing": letter_spacing,
            "align": headline_align,
            "color": headline_color,
            "contrast_treatment": "ink_from_zone_luminance",
        },
        "logo": {
            "asset_id": logo_id,
            "placement": logo_placement,
            "scale": boxes["logo_scale"],
            "object_fit": "contain",
            "plate": None,
            **logo_geo,
        },
        "cta": {
            "text": cta,
            "placement": cta_placement,
            "style": "minimal_outlined",
            "cta_style": "MINIMAL_BUTTON",
            **cta_box,
            "background_color": "transparent",
            "text_color": _NATIVE_MUTED_GOLD,
            "align": headline_align,
        },
        "margins": {"x": margin, "x_pct": 0.065},
        "palette": {
            "headline": headline_color,
            "cream": _NATIVE_CREAM,
            "warm_white": _NATIVE_WARM_WHITE,
            "muted_gold": _NATIVE_MUTED_GOLD,
            "charcoal": _NATIVE_CHARCOAL,
            "cta_fill": "transparent",
            "cta_text": _NATIVE_MUTED_GOLD,
            "visual_mood": (
                (production_brief.get("design_direction") or {})
                if isinstance(production_brief.get("design_direction"), dict)
                else {}
            ).get("visual_mood"),
        },
    }

    elements: list[dict[str, Any]] = [
        {
            "id": "master_background",
            "type": "image",
            "role": "background",
            "asset_id": bg_id,
            "locked": True,
            "editable": False,
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "z_index": 0,
            "opacity": 1.0,
            "treatment": {
                "crop": recipe["crop"],
                "position": recipe["position"],
            },
        },
        {
            "id": "logo",
            "type": "logo",
            "role": "logo",
            "asset_id": logo_id,
            "locked": False,
            "editable": True,
            "lock_aspect_ratio": True,
            **logo_geo,
            "z_index": 10,
            "opacity": 1.0,
        },
        {
            "id": "headline",
            "type": "text",
            "role": "headline",
            "content": headline,
            "locked": False,
            "editable": True,
            "x": headline_box["x"],
            "y": headline_box["y"],
            "width": headline_box["width"],
            "height": headline_box["height"],
            "z_index": 20,
            "typography": {
                "font_family": headline_family,
                "font_size": headline_size,
                "font_weight": "bold",
                "align": headline_align,
                "color": headline_color,
                "line_height": line_height,
                "letter_spacing": letter_spacing,
            },
        },
        {
            "id": "cta",
            "type": "cta",
            "role": "cta",
            "content": cta,
            "locked": False,
            "editable": True,
            "x": cta_box["x"],
            "y": cta_box["y"],
            "width": cta_box["width"],
            "height": cta_box["height"],
            "z_index": 40,
            "style": {
                "background_color": "transparent",
                "text_color": _NATIVE_MUTED_GOLD,
                "border_radius": 4,
                "padding": 8,
                "font_size": int(round(width * 0.018)),
                "font_weight": "semibold",
                "font_family": "sans",
                "align": headline_align,
                "cta_style": "MINIMAL_BUTTON",
            },
        },
    ]

    return {
        "version": 1,
        "mode": "golden_native_v1",
        "renderer": "golden_native_v1",
        "art_direction": "v2_image_aware",
        "canvas": {
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "format_preset": format_preset,
        },
        "language": language,
        "campaign_intent": intent,
        "composition_plan": plan,
        "image_analysis": {
            "available": bool(analysis.get("available")),
            "visual_focal_point": analysis.get("visual_focal_point"),
            "furniture_building_focal": analysis.get("furniture_building_focal"),
            "window_or_view": analysis.get("window_or_view"),
            "safe_headline_zone": analysis.get("safe_headline_zone"),
            "safe_logo_zone": analysis.get("safe_logo_zone"),
            "safe_cta_zone": analysis.get("safe_cta_zone"),
            "do_not_cover": analysis.get("do_not_cover"),
            "headline_zone_name": analysis.get("headline_zone_name"),
            "headline_zone_luminance": analysis.get("headline_zone_luminance"),
            "headline_ink": analysis.get("headline_ink"),
            "mean_luminance": analysis.get("mean_luminance"),
        },
        "creative_director_recipe": recipe,
        "composition": {
            "focal_zone": (plan.get("focal_point") or {}).get("zone"),
            "text_zones": (plan.get("zones") or {}).get("text_safe"),
            "safe_margins": plan.get("safe_margins"),
            "alignment_system": headline_align,
            "layout_family": "image_aware_editorial",
        },
        "background": {
            "asset_id": bg_id,
            "crop": recipe["crop"],
            "position": recipe["position"],
            "treatment": image_plan.get("treatment"),
        },
        "master_background_asset_id": bg_id,
        "logo_asset_id": logo_id,
        "finished_ad_raster_asset_id": None,
        "locked_background": True,
        "elements": elements,
        "editable_text_targets": _editable_text_targets(elements),
    }


_KICKER_IDS = {"unit-label", "subheadline", "eyebrow", "top-description"}
_KICKER_ROLES = {"subheadline", "unit_label", "eyebrow"}


def ensure_revision_overlay_targets(
    spec: dict[str, Any],
    *,
    production_brief: dict[str, Any],
    texts: dict[str, str],
) -> dict[str, Any]:
    """Raster-only campaigns reconstruct a spec that may omit the kicker / left features.

    LAYER_ONLY ops for the real SMB prompt bind those layers. If they are missing,
    delete/resize become no-ops and unit tests on a hand-built spec still pass.
    """
    elements = [el for el in (spec.get("elements") or []) if isinstance(el, dict)]
    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
    width = int(canvas.get("width") or 1080)
    height = int(canvas.get("height") or 1350)
    margin = int(round(width * 0.07))
    final = production_brief.get("final_copy") if isinstance(production_brief.get("final_copy"), dict) else {}
    kicker_text = _s(
        texts.get("unit")
        or final.get("unit")
        or final.get("eyebrow")
        or final.get("subheadline")
        or texts.get("sales_hook")
    )
    supporting = _supporting_list(production_brief, texts)
    persisted_targets = [
        rec
        for rec in (spec.get("editable_text_targets") or [])
        if isinstance(rec, dict) and rec.get("id")
    ]
    persisted_by_id = {_s(rec.get("id")).lower(): rec for rec in persisted_targets}
    for rec in persisted_targets:
        rid = _s(rec.get("id")).lower()
        content = _s(rec.get("content"))
        if rid in {"support-message-1", "feature-1", "support-message-2", "feature-2"} and content:
            if content not in supporting:
                supporting.append(content)
    supporting = supporting[:2]

    has_kicker = any(
        _s(el.get("id")).lower() in _KICKER_IDS or _s(el.get("role")).lower() in _KICKER_ROLES
        for el in elements
    )
    feature_els = [
        el
        for el in elements
        if _s(el.get("id")).lower().startswith(("feature-", "support-message"))
        or _s(el.get("role")).lower() == "support_message"
    ]
    ids = {_s(el.get("id")).lower() for el in elements}

    headline_copy = _s(texts.get("headline") or final.get("headline") or production_brief.get("hero"))
    if kicker_text and headline_copy and kicker_text.strip().lower() == headline_copy.strip().lower():
        # Never inject a kicker that duplicates the headline ("Eviniz, Sığınak" ×2).
        kicker_text = ""

    if kicker_text and not has_kicker:
        pill_h = int(round(height * 0.036))
        elements.append(
            {
                "id": "unit-label",
                "type": "text",
                "role": "unit_label",
                "content": kicker_text,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.12)),
                "width": int(round(width * 0.72)),
                "height": pill_h,
                "z_index": 19,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.022)),
                    "font_weight": "medium",
                    "align": "left",
                    "color": "#C4A35A",
                },
            }
        )
        ids.add("unit-label")

    feature_y0 = int(round(height * 0.42))
    sm1 = next(
        (
            el
            for el in elements
            if _s(el.get("id")).lower() in {"support-message-1", "feature-1"}
        ),
        None,
    )
    for idx, line in enumerate(supporting[:2]):
        fid = f"support-message-{idx + 1}"
        already = next(
            (
                el
                for el in feature_els
                if _s(el.get("id")).lower() in {fid, f"feature-{idx + 1}"}
            ),
            None,
        )
        if already:
            continue
        if fid in ids or f"feature-{idx + 1}" in ids:
            continue
        persisted = persisted_by_id.get(fid) or persisted_by_id.get(f"feature-{idx + 1}")
        x = margin
        y = feature_y0 + idx * int(round(height * 0.055))
        w = int(round(width * 0.48))
        h = int(round(height * 0.045))
        font = int(round(width * 0.024))
        if persisted:
            x = int(persisted.get("x") or x)
            y = int(persisted.get("y") or y)
            w = int(persisted.get("width") or w)
            h = int(persisted.get("height") or h)
            font = int(persisted.get("font_size") or font)
            line = _s(persisted.get("content")) or line
        elif idx == 1 and sm1:
            x = int(sm1.get("x") or x)
            w = int(sm1.get("width") or w)
            h = int(sm1.get("height") or h)
            y = int(sm1.get("y") or 0) + int(sm1.get("height") or h) + int(round(height * 0.012))
            typo = sm1.get("typography") if isinstance(sm1.get("typography"), dict) else {}
            font = int(typo.get("font_size") or font)
        elements.append(
            {
                "id": fid,
                "type": "text",
                "role": "support_message",
                "content": line,
                "locked": False,
                "editable": True,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "z_index": 26 + idx,
                "typography": {
                    "font_family": "sans",
                    "font_size": font,
                    "font_weight": "normal",
                    "align": "left",
                    "color": "#E8E0D4",
                },
            }
        )
        ids.add(fid)

    spec = dict(spec)
    spec["elements"] = elements
    spec["editable_text_targets"] = _editable_text_targets(elements)
    return spec


_RASTER_COPY_IDS = frozenset(
    {
        "unit-label",
        "subheadline",
        "eyebrow",
        "top-description",
        "headline",
        "support-message-1",
        "support-message-2",
        "feature-1",
        "feature-2",
    }
)
_RASTER_COPY_ROLES = frozenset(
    {
        "subheadline",
        "unit_label",
        "eyebrow",
        "headline",
        "support_message",
    }
)
_FORBIDDEN_RASTER_OVERLAY_IDS = frozenset(
    {"master_background", "logo", "cta", "img-finished-ad", "background-gpt-image"}
)


def _is_raster_copy_element(eid: str, el: dict[str, Any]) -> bool:
    low = str(eid).lower()
    role = _s(el.get("role")).lower()
    etype = _s(el.get("type")).lower()
    if low in _FORBIDDEN_RASTER_OVERLAY_IDS or role in {"logo", "background", "cta"}:
        return False
    return (
        low in _RASTER_COPY_IDS
        or role in _RASTER_COPY_ROLES
        or (etype in {"text"} and low not in _FORBIDDEN_RASTER_OVERLAY_IDS)
    )


def _copy_fingerprint(el: dict[str, Any] | None) -> tuple[Any, ...]:
    if not isinstance(el, dict):
        return ()
    typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
    style = el.get("style") if isinstance(el.get("style"), dict) else {}
    return (
        _s(el.get("content") or el.get("text") or el.get("label")),
        int(typo.get("font_size") or style.get("font_size") or el.get("font_size") or 0),
        int(el.get("x") or 0),
        int(el.get("y") or 0),
        int(el.get("width") or 0),
        int(el.get("height") or 0),
        el.get("visible") is not False,
    )


def _semantic_copy_id(eid: str, role: str) -> str:
    low = str(eid).lower()
    role_l = str(role).lower()
    if low in _KICKER_IDS or role_l in {"subheadline", "unit_label", "eyebrow"}:
        return "kicker"
    if low in {"support-message-1", "feature-1"}:
        return "feature-1"
    if low in {"support-message-2", "feature-2"}:
        return "feature-2"
    if low == "headline" or role_l == "headline":
        return "headline"
    return low


def _zone_cover_layer(eid: str, el: dict[str, Any], *, z_index: int = 60) -> dict[str, Any]:
    """Cover baked pixels for a hidden/moved overlay without banned hide-plate ids."""
    w = max(int(el.get("width") or 0), 8)
    h = max(int(el.get("height") or 0), 8)
    pad = 8
    return _json_safe_layer(
        {
            "id": f"{eid}-zone-cover",
            "type": "SHAPE",
            "fill": "rgba(8,6,4,0.88)",
            "shapeKind": "rect",
            "borderRadius": 4,
            "x": max(0, int(el.get("x") or 0) - pad),
            "y": max(0, int(el.get("y") or 0) - pad),
            "width": w + pad * 2,
            "height": h + pad * 2,
            "zIndex": z_index,
            "opacity": 1,
            "_designRole": "zone_cover",
        }
    )


def _json_safe_layer(row: dict[str, Any]) -> dict[str, Any]:
    """Drop nulls and coerce geometry so the SMB client can render every overlay."""
    out: dict[str, Any] = {}
    for key, val in row.items():
        if val is None:
            continue
        if key in {"x", "y", "width", "height", "zIndex", "fontSize", "borderRadius"}:
            try:
                out[key] = int(round(float(val)))
            except (TypeError, ValueError):
                continue
        else:
            out[key] = val
    return out


def compose_layer_only_on_locked_raster(
    *,
    after_spec: dict[str, Any],
    before_snap: dict[str, dict[str, Any]],
    locked_raster_asset_id: str,
) -> list[dict[str, Any]]:
    """LAYER_ONLY overlays on the SELECTED finished raster.

    The photograph, baked logo, and baked CTA stay in the raster pixels.
    Overlay only mutated/deleted copy. Unchanged baked text is left alone so
    one semantic element stays one visible element.
    """
    del locked_raster_asset_id  # cover is the raster on the client; do not emit a 2nd photo
    after_by_id: dict[str, dict[str, Any]] = {}
    for el in after_spec.get("elements") or []:
        if isinstance(el, dict) and el.get("id"):
            after_by_id[_s(el.get("id")).lower()] = el

    changed_copy_ids: set[str] = set()
    for eid, el in before_snap.items():
        if not _is_raster_copy_element(str(eid), el):
            continue
        low = str(eid).lower()
        after_el = after_by_id.get(low)
        if after_el is None or after_el.get("visible") is False:
            changed_copy_ids.add(low)
        elif _copy_fingerprint(el) != _copy_fingerprint(after_el):
            changed_copy_ids.add(low)

    layers: list[dict[str, Any]] = []
    # MICRO_EDIT never emits banned hide-plates. Replacement TEXT sits on the locked raster.
    smb = design_spec_to_smb_elements(after_spec)
    seen_semantic: set[str] = set()
    seen_copy: set[str] = set()
    for el in smb:
        if not isinstance(el, dict):
            continue
        eid = _s(el.get("id")).lower()
        etype = _s(el.get("type")).upper()
        role = _s(el.get("role")).lower()
        if eid not in changed_copy_ids:
            continue
        if eid in _FORBIDDEN_RASTER_OVERLAY_IDS or role in {"logo", "background", "cta"}:
            continue
        if etype in {"IMAGE", "BUTTON"}:
            continue
        if etype == "SHAPE" and eid.startswith("hide-plate-"):
            continue
        if etype != "TEXT":
            continue
        semantic = _semantic_copy_id(eid, role)
        copy = _s(el.get("content") or el.get("text") or el.get("label")).strip().lower()
        # Distinct feature ids are distinct messages. Do not drop support-message-2
        # just because copy collides with support-message-1 after language lock.
        if semantic in seen_semantic:
            continue
        if copy and copy in seen_copy and semantic not in {"feature-1", "feature-2", "headline"}:
            continue
        seen_semantic.add(semantic)
        if copy:
            seen_copy.add(copy)
        row = dict(el)
        row["zIndex"] = max(int(row.get("zIndex") or 0), 50)
        layers.append(_json_safe_layer(row))
    # MICRO_EDIT: overlay mutated logo / CTA / badge without hide-plates.
    for el in smb:
        if not isinstance(el, dict):
            continue
        eid = _s(el.get("id")).lower()
        role = _s(el.get("role")).lower()
        etype = _s(el.get("type")).upper()
        before_el = before_snap.get(eid) or before_snap.get(_s(el.get("id")))
        after_el = after_by_id.get(eid)
        if not before_el or not after_el:
            continue
        if _copy_fingerprint(before_el) == _copy_fingerprint(after_el):
            continue
        if eid == "logo" or role == "logo" or etype == "LOGO":
            row = dict(el)
            row["type"] = "IMAGE" if etype not in {"IMAGE", "LOGO"} else el.get("type")
            row["zIndex"] = max(int(row.get("zIndex") or 0), 70)
            layers.append(_json_safe_layer(row))
        elif eid == "cta" or role == "cta" or etype == "BUTTON":
            row = dict(el)
            row["zIndex"] = max(int(row.get("zIndex") or 0), 70)
            layers.append(_json_safe_layer(row))
        elif eid in {"discount-badge", "badge"} or role in {"discount_badge", "badge"}:
            row = dict(el)
            row["zIndex"] = max(int(row.get("zIndex") or 0), 70)
            layers.append(_json_safe_layer(row))
    # Hidden CTA / logo: cover baked pixels. Do not use hide-plate ids (artifact guard).
    for eid, el in before_snap.items():
        low = str(eid).lower()
        role = _s(el.get("role")).lower()
        if low not in {"cta", "logo"} and role not in {"cta", "logo"}:
            continue
        after_el = after_by_id.get(low)
        hidden = after_el is None or after_el.get("visible") is False
        if hidden:
            layers.append(_zone_cover_layer(low, el, z_index=65))
    present_ids = {_s(el.get("id")).lower() for el in layers if isinstance(el, dict)}
    sm2_smb = next(
        (
            el
            for el in smb
            if isinstance(el, dict) and _s(el.get("id")).lower() in {"support-message-2", "feature-2"}
        ),
        None,
    )
    sm1_layer = next(
        (
            el
            for el in layers
            if isinstance(el, dict)
            and _s(el.get("id")).lower() in {"support-message-1", "feature-1"}
            and _s(el.get("type")).upper() == "TEXT"
        ),
        None,
    )
    if (
        "support-message-2" not in present_ids
        and "feature-2" not in present_ids
        and ("support-message-2" in changed_copy_ids or "feature-2" in changed_copy_ids)
    ):
        row = dict(sm2_smb) if isinstance(sm2_smb, dict) else (dict(sm1_layer) if isinstance(sm1_layer, dict) else None)
        if row is not None:
            row["id"] = "support-message-2"
            row["type"] = "TEXT"
            row["role"] = "body"
            if sm2_smb is None and sm1_layer is not None:
                row["y"] = int(sm1_layer.get("y") or 0) + int(sm1_layer.get("height") or 0) + 16
            row["zIndex"] = max(int(row.get("zIndex") or 0), 50)
            layers.append(_json_safe_layer(row))
    return [_json_safe_layer(el) if isinstance(el, dict) else el for el in layers]


def design_spec_to_smb_elements(design_spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Design Spec → SMB SocialElement-shaped dicts for hydration."""
    out: list[dict[str, Any]] = []
    for el in design_spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        if el.get("visible") is False:
            continue
        eid = _s(el.get("id"))
        etype = _s(el.get("type")).lower()
        role = _s(el.get("role"))
        x = int(el.get("x") or 0)
        y = int(el.get("y") or 0)
        w = int(el.get("width") or 0)
        h = int(el.get("height") or 0)
        z = int(el.get("z_index") or el.get("zIndex") or 0)
        locked = bool(el.get("locked"))
        opacity = el.get("opacity")
        typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
        style = el.get("style") if isinstance(el.get("style"), dict) else {}

        if etype in {"image", "logo"} or role in {"background", "logo"}:
            smb_role = "background" if role == "background" or eid == "master_background" else "logo"
            out.append(
                {
                    "id": eid or ("master_background" if smb_role == "background" else "logo"),
                    "type": "IMAGE",
                    "role": smb_role,
                    "assetId": el.get("asset_id") or el.get("assetId"),
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "zIndex": z,
                    "lockAspectRatio": bool(el.get("lock_aspect_ratio", smb_role == "logo")),
                    "opacity": opacity if opacity is not None else 1.0,
                    "objectFit": "cover" if smb_role == "background" else "contain",
                    "_locked": locked,
                    "_designRole": role or smb_role,
                }
            )
            continue

        if etype in {"gradient", "overlay", "shape", "rectangle", "line", "divider"} or role in {
            "overlay",
            "eyebrow_frame",
            "price_frame",
            "divider",
            "icon",
        }:
            fill = _s(style.get("fill") or style.get("background_color"), "rgba(8,6,4,0.5)")
            shape_kind = _s(style.get("shape_kind"), "rect")
            if etype in {"line", "divider"} or role == "divider":
                shape_kind = "line"
            border_radius = int(style.get("border_radius") or 0)
            out.append(
                {
                    "id": eid or f"shape-{z}",
                    "type": "SHAPE",
                    "fill": fill,
                    "shapeKind": shape_kind if shape_kind in {"rect", "line", "accent"} else "rect",
                    "borderRadius": border_radius,
                    "x": x,
                    "y": y,
                    "width": max(1, w),
                    "height": max(1, h),
                    "zIndex": z,
                    "opacity": opacity if opacity is not None else 1.0,
                    "_designRole": role or etype,
                    "_borderColor": style.get("border_color"),
                    "_borderWidth": style.get("border_width"),
                }
            )
            continue

        if etype == "cta" or role == "cta":
            out.append(
                {
                    "id": eid or "cta",
                    "type": "BUTTON",
                    "label": _s(el.get("content") or el.get("label"), "CTA"),
                    "backgroundColor": _s(style.get("background_color"), "#C4A35A"),
                    "textColor": _s(style.get("text_color"), "#1A1510"),
                    "fontSize": int(style.get("font_size") or 28),
                    "fontWeight": _s(style.get("font_weight"), "semibold"),
                    "fontFamily": _s(style.get("font_family")) or None,
                    "align": _s(style.get("align"), "center"),
                    "borderRadius": int(style.get("border_radius") or 8),
                    "padding": int(style.get("padding") or 12),
                    "ctaStyle": _s(style.get("cta_style")) or None,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "zIndex": z,
                    "opacity": opacity if opacity is not None else 1.0,
                    "_designRole": "cta",
                }
            )
            continue

        if etype == "badge" or role in {"discount_badge", "badge"}:
            # Badge as SHAPE backplate + TEXT for editability
            bg = _s(style.get("background_color"), "rgba(20,16,12,0.82)")
            br = int(style.get("border_radius") or 999)
            out.append(
                {
                    "id": f"{eid or 'discount-badge'}-plate",
                    "type": "SHAPE",
                    "fill": bg,
                    "shapeKind": "rect",
                    "borderRadius": br,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "zIndex": z,
                    "opacity": opacity if opacity is not None else 1.0,
                    "_designRole": "badge_plate",
                }
            )
            out.append(
                {
                    "id": eid or "discount-badge",
                    "type": "TEXT",
                    "role": "eyebrow",
                    "content": _s(el.get("content")),
                    "fontSize": int(style.get("font_size") or typo.get("font_size") or 36),
                    "fontWeight": _s(style.get("font_weight") or typo.get("font_weight"), "bold"),
                    "align": _s(style.get("align") or typo.get("align"), "center"),
                    "color": _s(style.get("text_color") or typo.get("color"), "#C4A35A"),
                    "fontFamily": "sans",
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "zIndex": z + 1,
                    "opacity": opacity if opacity is not None else 1.0,
                    "_designRole": "discount_badge",
                    "_badgeStyle": {
                        "backgroundColor": bg,
                        "borderRadius": br,
                    },
                }
            )
            continue

        # Default: text
        text_role = "headline" if role in {"headline", "primary"} else "body"
        if role in {"subheadline", "support_message", "unit_label", "old_price", "new_price", "savings_price"}:
            text_role = "body" if role != "headline" else "headline"
        if role == "headline":
            text_role = "headline"
        out.append(
            {
                "id": eid or f"text-{z}",
                "type": "TEXT",
                "role": text_role,
                "content": _s(el.get("content")),
                "fontSize": int(typo.get("font_size") or 28),
                "fontWeight": _s(typo.get("font_weight"), "normal"),
                "align": _s(typo.get("align"), "left"),
                "color": _s(typo.get("color"), "#FFFFFF"),
                "fontFamily": _s(typo.get("font_family"), "sans"),
                "lineHeight": typo.get("line_height"),
                "letterSpacing": typo.get("letter_spacing"),
                "textDecoration": typo.get("text_decoration") or None,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "zIndex": z,
                "opacity": opacity if opacity is not None else 1.0,
                "_designRole": role or "text",
                "_textDecoration": typo.get("text_decoration"),
            }
        )
    return out


def is_micro_edit_route(route: str | None) -> bool:
    return str(route or "") in {"LAYER_ONLY", "MICRO_EDIT"}


def is_provider_revision_route(route: str | None) -> bool:
    return str(route or "") in {"CREATIVE_RECOMPOSE", "IMAGE_REQUIRED", "VISUAL_REPLACE_ONLY"}


def _op_field(op: Any, name: str) -> Any:
    if isinstance(op, dict):
        return op.get(name)
    return getattr(op, name, None)


def _op_scale_delta(op: Any) -> float:
    raw = _op_field(op, "scale_factor")
    if raw is None:
        raw = _op_field(op, "value")
    try:
        return abs(float(raw) - 1.0)
    except (TypeError, ValueError):
        return 0.0


def route_revision(
    *,
    instruction: str,
    revision_diff: Any,
    intents: list[str] | None = None,
    has_structured_design: bool = False,
) -> RevisionRoute:
    """Golden Creative router: MICRO_EDIT vs CREATIVE_RECOMPOSE vs IMAGE_REQUIRED.

    MICRO_EDIT is GPT=0 layer/property edit. With structured_design_data, headline
    copy, CTA hide, and local logo/CTA geometry stay MICRO_EDIT. New composition,
    new photograph, or simplify still CREATIVE_RECOMPOSE. LAYER_ONLY remains a
    compatibility alias of MICRO_EDIT.
    """
    try:
        from investhome_api.services.creative_director.revision_intelligence_v3 import (
            extract_working_instruction,
        )

        working, _ = extract_working_instruction(instruction)
    except Exception:
        working = instruction
    try:
        from investhome_api.services.creative_director.master_revision_controller import (
            classify_revision_command,
        )

        classified = classify_revision_command(instruction or working)
        intent = classified.get("intent")
        if intent == "VISUAL_REPLACE_ONLY":
            return "VISUAL_REPLACE_ONLY"
        if intent == "PRICE_EDIT_ONLY":
            return "PRICE_EDIT_ONLY"
    except Exception:
        pass
    low = (working or instruction or "").replace("İ", "i").replace("I", "ı").lower()
    for phrase in _FURNITURE_IMAGE_PHRASES:
        if phrase in low:
            return "IMAGE_REQUIRED"
    for phrase in _IMAGE_REQUIRED_PHRASES:
        if phrase in low:
            return "CREATIVE_RECOMPOSE"

    intent_set = {str(i).upper() for i in (intents or [])}
    if "SIMPLIFY" in intent_set or any(
        tok in low for tok in ("daha sade", "sadeleştir", "sadelestir", "simplify", "basitleştir")
    ):
        return "CREATIVE_RECOMPOSE"
    if "ASSET_CHANGE" in intent_set:
        return "CREATIVE_RECOMPOSE"
    if "STYLE_CHANGE" in intent_set and "COPY_CHANGE" not in intent_set and "LAYOUT_CHANGE" not in intent_set:
        return "CREATIVE_RECOMPOSE"

    ops: list[Any] = []
    if hasattr(revision_diff, "operations"):
        ops = list(revision_diff.operations or [])
    elif isinstance(revision_diff, dict):
        ops = list(revision_diff.get("operations") or [])

    mutating = [
        op
        for op in ops
        if str(_op_field(op, "action") or "").lower() not in {"minimum_change", "preserve"}
    ]
    if not mutating:
        if any(tok in low for tok in ("görsel", "visual", "render", "interior", "sahne", "scene", "atmosfer")):
            return "CREATIVE_RECOMPOSE"
        if has_structured_design and any(
            tok in low
            for tok in (
                "başlık",
                "baslik",
                "headline",
                "cta",
                "logo",
                "rozet",
                "badge",
            )
        ):
            return "MICRO_EDIT"
        if any(tok in low for tok in ("başlık", "baslik", "headline")):
            return "CREATIVE_RECOMPOSE"
        if any(tok in low for tok in ("cta", "rozet", "badge", "logo")):
            return "MICRO_EDIT"
        return "CREATIVE_RECOMPOSE"

    micro_targets = _STRUCTURED_MICRO_TARGETS if has_structured_design else _MICRO_EDIT_TARGETS
    micro_actions = _STRUCTURED_MICRO_ACTIONS if has_structured_design else _MICRO_EDIT_ACTIONS
    micro_ok = True
    for op in mutating:
        target_s = str(_op_field(op, "target") or "").lower()
        action_s = str(_op_field(op, "action") or "").lower()
        if action_s in {"delete", "remove", "hide"}:
            if not (
                has_structured_design
                and target_s in {"cta", "support_message", "badge", "left_feature_texts", "feature_text"}
            ):
                micro_ok = False
                break
        if target_s in _IMAGE_REQUIRED_TARGETS:
            micro_ok = False
            break
        if not has_structured_design and target_s in _COPY_REBALANCE_TARGETS:
            micro_ok = False
            break
        if not has_structured_design and action_s in {"set_font_size", "improve_readability", "tone_adjust"}:
            micro_ok = False
            break
        if action_s == "replace_text" and target_s != "cta":
            if not (
                has_structured_design
                and target_s in {
                    "headline",
                    "primary_headline",
                    "support_message",
                    "price",
                }
            ):
                micro_ok = False
                break
        if target_s not in micro_targets:
            micro_ok = False
            break
        if action_s not in micro_actions:
            micro_ok = False
            break
        if target_s == "logo" and action_s in {"scale", "resize"} and _op_scale_delta(op) > 0.35:
            micro_ok = False
            break
        if target_s == "cta" and action_s in {"scale", "resize"} and _op_scale_delta(op) > 0.25:
            micro_ok = False
            break
        if target_s == "badge" and action_s in {"scale", "resize"} and _op_scale_delta(op) > 0.35:
            micro_ok = False
            break
    if micro_ok:
        return "MICRO_EDIT"
    return "CREATIVE_RECOMPOSE"


def _find_element(spec: dict[str, Any], *ids_or_roles: str) -> dict[str, Any] | None:
    elements = spec.get("elements")
    if not isinstance(elements, list):
        return None
    wanted = {x.lower() for x in ids_or_roles if x}
    for el in elements:
        if not isinstance(el, dict):
            continue
        if _s(el.get("id")).lower() in wanted or _s(el.get("role")).lower() in wanted:
            return el
    return None


def _resolve_layer(spec: dict[str, Any], target: str, element_id: str | None = None) -> dict[str, Any] | None:
    if element_id:
        found = _find_element(spec, element_id)
        if found is not None:
            return found
    if target == "price":
        # Prefer offer/new price over struck old-price for relational anchors
        return _find_element(spec, "new-price", "new_price") or _find_element(
            spec, "old-price", "old_price"
        )
    lookup = {
        "headline": ("headline", "primary_headline", "text-headline"),
        "primary_headline": ("headline", "primary_headline", "text-headline"),
        "cta": ("cta", "cta-primary"),
        "badge": ("discount-badge", "discount_badge", "badge"),
        "logo": ("logo", "logo-project"),
        "support_message": ("support-message-1", "support_message"),
        "left_feature_texts": ("feature-1", "feature-2", "support-message-1", "support-message-2"),
        "feature_text": ("feature-1", "feature-2", "feature-3"),
        "subheadline": ("subheadline",),
        "eyebrow": ("eyebrow", "unit-label"),
        "top_small_description": ("subheadline", "unit-label", "eyebrow", "top-description"),
    }.get(target, (target,))
    return _find_element(spec, *lookup)


def _resolve_layers(
    spec: dict[str, Any],
    target: str,
    element_id: str | None = None,
    element_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[int] = set()
    ids: list[str] = []
    if element_ids:
        ids.extend(str(i) for i in element_ids if i)
    if element_id:
        ids.append(str(element_id))
    for eid in ids:
        el = _find_element(spec, eid)
        if el is not None and id(el) not in seen:
            seen.add(id(el))
            found.append(el)
    if found:
        return found
    if target in {"left_feature_texts", "feature_text"}:
        for el in spec.get("elements") or []:
            if not isinstance(el, dict):
                continue
            eid = _s(el.get("id")).lower()
            role = _s(el.get("role")).lower()
            if eid.startswith("feature-") or role == "support_message":
                if id(el) not in seen:
                    seen.add(id(el))
                    found.append(el)
        if found:
            return found
    el = _resolve_layer(spec, target, element_id)
    return [el] if el is not None else []


def _hex_luminance(color: str) -> float | None:
    raw = (color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return None
    try:
        r = int(raw[0:2], 16) / 255.0
        g = int(raw[2:4], 16) / 255.0
        b = int(raw[4:6], 16) / 255.0
    except ValueError:
        return None
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _improve_readability(el: dict[str, Any]) -> None:
    typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
    style = el.get("style") if isinstance(el.get("style"), dict) else {}
    weight = str(typo.get("font_weight") or style.get("font_weight") or "normal").lower()
    bump = {"normal": "semibold", "regular": "semibold", "medium": "bold", "semibold": "bold", "semi-bold": "bold"}
    next_w = bump.get(weight, "bold")
    if typo or el.get("type") in {"text", "TEXT"}:
        typo["font_weight"] = next_w
        el["typography"] = typo
    if style:
        style["font_weight"] = next_w
        el["style"] = style
    color = str(typo.get("color") or style.get("text_color") or "")
    lum = _hex_luminance(color)
    if lum is None:
        return
    # Light type on photography → white; dark type → ink. Always increase contrast.
    new_color = "#FFFFFF" if lum >= 0.45 else "#1A1510"
    if typo:
        typo["color"] = new_color
        el["typography"] = typo
    if "text_color" in style:
        style["text_color"] = new_color
        el["style"] = style


def _read_font_size(el: dict[str, Any]) -> float | None:
    for bag_key in ("typography", "style"):
        bag = el.get(bag_key) if isinstance(el.get(bag_key), dict) else None
        if bag and bag.get("font_size") is not None:
            try:
                return float(bag["font_size"])
            except (TypeError, ValueError):
                continue
    return None


def _scale_from_original(el: dict[str, Any], original: dict[str, Any], factor: float) -> None:
    """Apply relative scale against the pre-op metrics so duplicate ops cannot compound."""
    factor = float(factor)
    el["width"] = max(8, int(round(float(original["width"]) * factor)))
    el["height"] = max(8, int(round(float(original["height"]) * factor)))
    orig_fs = original.get("font_size")
    if orig_fs:
        new_fs = max(10, int(round(float(orig_fs) * factor)))
        for bag_key in ("style", "typography"):
            bag = el.get(bag_key) if isinstance(el.get(bag_key), dict) else None
            if not isinstance(bag, dict):
                continue
            if bag.get("font_size") is not None or orig_fs:
                bag = dict(bag)
                bag["font_size"] = new_fs
                el[bag_key] = bag


def _scale_element(el: dict[str, Any], factor: float, *, aspect_lock: bool = True) -> None:
    factor = float(factor)
    nw = max(8, int(round(float(el.get("width", 0)) * factor)))
    if aspect_lock or el.get("lock_aspect_ratio"):
        nh = max(8, int(round(float(el.get("height", 0)) * factor)))
    else:
        nh = max(8, int(round(float(el.get("height", 0)) * factor)))
    el["width"] = nw
    el["height"] = nh
    for bag_key in ("style", "typography"):
        bag = el.get(bag_key) if isinstance(el.get(bag_key), dict) else None
        if bag and bag.get("font_size"):
            bag["font_size"] = max(10, int(round(float(bag["font_size"]) * factor)))
            el[bag_key] = bag


def apply_layer_operations(
    design_spec: dict[str, Any],
    operations: list[Any],
) -> dict[str, Any]:
    """Apply LAYER_ONLY revision ops onto a design_spec copy. No provider calls.

    Scale runs before translate/align so geometric finals win after size changes.
    """
    spec = deepcopy(design_spec)
    elements = list(spec.get("elements") or [])
    spec["elements"] = elements
    original_metrics: dict[str, dict[str, Any]] = {}
    for el0 in elements:
        if isinstance(el0, dict) and el0.get("id"):
            original_metrics[str(el0["id"])] = {
                "width": float(el0.get("width") or 0),
                "height": float(el0.get("height") or 0),
                "font_size": _read_font_size(el0),
            }

    def _priority_key(raw: Any) -> tuple[int, int]:
        if hasattr(raw, "model_dump"):
            op = raw.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(raw, dict):
            op = dict(raw)
        else:
            return (50, 0)
        action = str(op.get("action") or "").lower()
        # Lower key runs first: scale → geometry → text/color → remove
        if action in {"scale", "resize"}:
            return (0, 0)
        if action in {"set_font_size"}:
            return (1, 0)
        if action in {"translate", "set_position", "align", "set_geometry"}:
            return (2, 0)
        if action in {"replace_text", "set_color", "tone_adjust", "improve_readability"}:
            return (3, 0)
        if action in {"remove", "hide", "delete"}:
            return (4, 0)
        return (5, 0)

    ordered = sorted(list(operations or []), key=_priority_key)

    for raw in ordered:
        if hasattr(raw, "model_dump"):
            op = raw.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(raw, dict):
            op = dict(raw)
        else:
            continue
        target = str(op.get("target") or "").lower()
        action = str(op.get("action") or "").lower()
        to_value = op.get("to") if op.get("to") is not None else op.get("to_value")
        scale_factor = op.get("scale_factor") or op.get("value")
        element_id = op.get("element_id")
        raw_ids = op.get("element_ids")
        element_ids = [str(i) for i in raw_ids] if isinstance(raw_ids, list) else None
        layers = _resolve_layers(
            spec,
            target,
            element_id if isinstance(element_id, str) else None,
            element_ids,
        )
        el = layers[0] if layers else None

        if action == "replace_text" and to_value:
            if not layers and str(element_id or "").lower() == "savings-price":
                anchor = _find_element(spec, "new-price", "new_price") or _find_element(
                    spec, "old-price", "old_price"
                )
                if anchor is not None:
                    created = {
                        "id": "savings-price",
                        "type": "text",
                        "role": "savings_price",
                        "content": "",
                        "locked": False,
                        "editable": True,
                        "claim_sensitive": True,
                        "visible": False,
                        "x": int(anchor.get("x") or 0),
                        "y": int(anchor.get("y") or 0) + int(anchor.get("height") or 40) + 8,
                        "width": int(anchor.get("width") or 400),
                        "height": int(round(int(anchor.get("height") or 40) * 0.7)),
                        "z_index": int(anchor.get("z_index") or 25) + 1,
                        "typography": {
                            "font_family": "sans",
                            "font_size": int(
                                round(
                                    float(
                                        ((anchor.get("typography") or {}) or {}).get("font_size")
                                        or 28
                                    )
                                    * 0.62
                                )
                            ),
                            "font_weight": "medium",
                            "align": "left",
                            "color": "#E8E0D4",
                        },
                    }
                    spec.setdefault("elements", []).append(created)
                    layers = [created]
            for layer in layers:
                eid = _s(layer.get("id")).lower()
                content = str(to_value)
                note = str(op.get("note") or "").lower()
                if eid == "savings-price" or "savings" in note:
                    low = content.lower()
                    if "kazanc" not in low:
                        content = f"Kazancınız {content}"
                layer["content"] = content
                layer["visible"] = True
                if target == "price":
                    layer["claim_sensitive"] = True
                if eid == "old-price" and (
                    "strikethrough" in note or "line-through" in note or "çiz" in note
                ):
                    typo = dict(layer.get("typography") or {})
                    typo["text_decoration"] = "line-through"
                    layer["typography"] = typo
                    _upsert_strikethrough(spec, layer)

        elif action in {"scale", "resize"} and scale_factor:
            for layer in layers:
                key = str(layer.get("id") or "")
                baseline = original_metrics.get(key)
                if baseline:
                    _scale_from_original(layer, baseline, float(scale_factor))
                else:
                    _scale_element(layer, float(scale_factor), aspect_lock=True)

        elif action == "translate":
            dx = float(op.get("dx") or 0)
            dy = float(op.get("dy") or 0)
            for layer in layers:
                layer["x"] = int(round(float(layer.get("x", 0)) + dx))
                layer["y"] = int(round(float(layer.get("y", 0)) + dy))

        elif action in {"set_position", "align", "set_geometry"} and el is not None:
            for layer in layers:
                live_x = False
                live_y = False
                edge = str(op.get("align_edge") or "").lower()
                ref_name = str(op.get("reference_element") or "")

                if action == "align" and edge:
                    ew = float(layer.get("width") or 0)
                    eh = float(layer.get("height") or 0)
                    if ref_name in {"canvas", "canvas_center"} or (
                        edge in {"centerx", "center"} and not ref_name
                    ):
                        canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
                        cw = float(canvas.get("width") or 1080)
                        layer["x"] = int(round((cw - ew) / 2))
                        live_x = True
                    else:
                        ref = _resolve_layer(spec, ref_name) if ref_name else None
                        if ref is not None:
                            rx = float(ref.get("x") or 0)
                            ry = float(ref.get("y") or 0)
                            rw = float(ref.get("width") or 0)
                            rh = float(ref.get("height") or 0)
                            if edge == "left":
                                layer["x"] = int(round(rx))
                                live_x = True
                            elif edge == "right":
                                layer["x"] = int(round(rx + rw - ew))
                                live_x = True
                            elif edge in {"centerx", "center"}:
                                layer["x"] = int(round(rx + rw / 2 - ew / 2))
                                live_x = True
                            elif edge == "top":
                                layer["y"] = int(round(ry))
                                live_y = True
                            elif edge == "bottom":
                                layer["y"] = int(round(ry + rh - eh))
                                live_y = True

                if (
                    action == "set_position"
                    and ref_name
                    and op.get("dy") is not None
                    and op.get("y") is None
                ):
                    ref = _resolve_layer(spec, ref_name)
                    if ref is not None:
                        layer["y"] = int(
                            round(
                                float(ref.get("y") or 0)
                                + float(ref.get("height") or 0)
                                + float(op["dy"])
                            )
                        )
                        live_y = True

                if op.get("x") is not None and not live_x:
                    layer["x"] = int(round(float(op["x"])))
                if op.get("y") is not None and not live_y:
                    layer["y"] = int(round(float(op["y"])))
                if op.get("width") is not None:
                    layer["width"] = max(8, int(round(float(op["width"]))))
                if op.get("height") is not None:
                    layer["height"] = max(8, int(round(float(op["height"]))))

        elif action == "set_font_size" and op.get("font_size") is not None:
            fs = max(8, int(round(float(op["font_size"]))))
            for layer in layers:
                typo = layer.get("typography") if isinstance(layer.get("typography"), dict) else {}
                typo["font_size"] = fs
                layer["typography"] = typo
                style = layer.get("style") if isinstance(layer.get("style"), dict) else {}
                if style:
                    style["font_size"] = fs
                    layer["style"] = style

        elif action == "set_color" and op.get("color"):
            color = str(op["color"])
            for layer in layers:
                if layer.get("type") == "cta" or target == "cta":
                    style = layer.get("style") if isinstance(layer.get("style"), dict) else {}
                    style["background_color"] = color
                    layer["style"] = style
                else:
                    typo = layer.get("typography") if isinstance(layer.get("typography"), dict) else {}
                    typo["color"] = color
                    layer["typography"] = typo
                    style = layer.get("style") if isinstance(layer.get("style"), dict) else {}
                    if "background_color" in style or target == "badge":
                        style["background_color"] = color
                        layer["style"] = style

        elif action == "improve_readability":
            for layer in layers:
                _improve_readability(layer)

        elif action in {"remove", "hide", "delete"}:
            default_ids = {
                "headline": {"headline"},
                "primary_headline": {"headline"},
                "cta": {"cta"},
                "badge": {"discount-badge", "badge"},
                "logo": {"logo"},
                "support_message": {"support-message-1", "support-message-2"},
                "left_feature_texts": {
                    "feature-1",
                    "feature-2",
                    "support-message-1",
                    "support-message-2",
                },
                "top_small_description": {
                    "subheadline",
                    "unit-label",
                    "eyebrow",
                    "top-description",
                    "eyebrow-pill",
                },
                "price": {"old-price", "new-price", "savings-price"},
            }.get(target, set())
            # Prefer geometrically resolved layers. Literal element_ids from a
            # unit-test spec (top-description / feature-1) must not skip the
            # reconstructed SMB ids (unit-label / support-message-*).
            remove_ids = {_s(layer.get("id")).lower() for layer in layers if layer.get("id")}
            if element_ids:
                remove_ids |= {str(i).lower() for i in element_ids if i}
            elif isinstance(element_id, str) and element_id:
                remove_ids |= {_s(element_id).lower()}
            if not remove_ids:
                remove_ids = set(default_ids)
            note = str(op.get("note") or "").lower()
            if "old-price" in note or element_id == "old-price":
                remove_ids = {"old-price"}
            if any(
                i in {"unit-label", "subheadline", "eyebrow", "top-description"} for i in remove_ids
            ):
                remove_ids.add("eyebrow-pill")
            if target in {"top_small_description", "subheadline", "eyebrow"}:
                remove_ids -= {
                    "support-message-1",
                    "support-message-2",
                    "support-message-3",
                    "feature-1",
                    "feature-2",
                    "feature-3",
                }
            hide_in_place = action == "hide" or target in {"cta", "logo", "badge"}
            if hide_in_place:
                for e in spec["elements"]:
                    if isinstance(e, dict) and _s(e.get("id")).lower() in remove_ids:
                        e["visible"] = False
            elif remove_ids:
                spec["elements"] = [
                    e
                    for e in spec["elements"]
                    if not isinstance(e, dict) or _s(e.get("id")).lower() not in remove_ids
                ]

    return spec


def assemble_editable_design(
    *,
    production_brief: dict[str, Any],
    texts: dict[str, str],
    master_background_asset_id: UUID | str,
    logo_asset_id: UUID | str,
    finished_ad_raster_asset_id: UUID | str | None = None,
    aspect_ratio: str = "4:5",
    format_preset: str = "portrait",
    language: str = "tr",
    campaign_intent: str | None = None,
    revision_engine_v2: bool = False,
) -> dict[str, Any]:
    """Composition plan → design spec → quality critic (one revise) → geometry check."""
    from investhome_api.services.creative_director.composition_critic import (
        critique_composition,
        fix_geometry_once,
        geometry_check_design_spec,
        revise_design_spec_once,
    )

    intent = _s(
        campaign_intent or production_brief.get("campaign_intent") or texts.get("campaign_mode"),
        "general_awareness",
    )
    plan = build_composition_plan(
        campaign_intent=intent,
        production_brief=production_brief,
        texts=texts,
        design_direction=production_brief.get("design_direction")
        if isinstance(production_brief.get("design_direction"), dict)
        else None,
        message_strategy=production_brief.get("message_strategy")
        if isinstance(production_brief.get("message_strategy"), dict)
        else None,
        aspect_ratio=aspect_ratio,
        language=language,
    )
    spec = build_design_spec(
        production_brief=production_brief,
        texts=texts,
        master_background_asset_id=master_background_asset_id,
        logo_asset_id=logo_asset_id,
        finished_ad_raster_asset_id=finished_ad_raster_asset_id,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        language=language,
        campaign_intent=intent,
        composition_plan=plan,
        revision_engine_v2=revision_engine_v2,
    )
    critique = critique_composition(composition_plan=plan, design_spec=spec)
    if critique.get("status") == "fail":
        spec = revise_design_spec_once(
            design_spec=spec, composition_plan=plan, critique=critique
        )
        critique = critique_composition(composition_plan=plan, design_spec=spec)
        critique["fixed_once"] = True
    geometry = geometry_check_design_spec(spec)
    if geometry.get("status") != "pass":
        spec = fix_geometry_once(spec, geometry)
        geometry = geometry_check_design_spec(spec)
        geometry["fixed_once"] = True
    layers = design_spec_to_smb_elements(spec)
    return {
        "composition_plan": plan,
        "design_spec": spec,
        "quality_critique": critique,
        "geometry_check": geometry,
        "editable_layers": layers,
    }


def sync_production_brief_from_spec(
    production_brief: dict[str, Any],
    design_spec: dict[str, Any],
) -> dict[str, Any]:
    """Keep final_copy aligned after layer-only edits."""
    pb = deepcopy(production_brief)
    final = dict(pb.get("final_copy") or {})
    mapping = {
        "headline": "headline",
        "cta": "cta",
        "new-price": "offer_price",
        "old-price": "list_price",
        "savings-price": "savings",
        "discount-badge": "value_badge",
        "unit-label": "unit",
    }
    for el in design_spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        eid = _s(el.get("id")).lower()
        content = _s(el.get("content"))
        if not content:
            continue
        key = mapping.get(eid)
        if key:
            final[key] = content
            if key == "headline":
                pb["hero"] = content
            if key == "cta":
                pb["cta"] = content
    pb["final_copy"] = final
    return pb
