"""Editable Finished-Ad Design Spec — structured layers for SMB hydration.

AI Creative Director owns design via production_brief + Full Composition Plan.
This module encodes the SAME composition as editable primitives — editability is
a rendering property, not a simplified design style.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal
from uuid import UUID

from investhome_api.services.creative_director.composition_plan import build_composition_plan

RevisionRoute = Literal["LAYER_ONLY", "IMAGE_REQUIRED"]

# Ops that mutate overlay layers without re-rasterizing the photograph.
_LAYER_ONLY_TARGETS = frozenset(
    {"headline", "cta", "badge", "logo", "support_message", "price"}
)
_LAYER_ONLY_ACTIONS = frozenset(
    {
        "replace_text",
        "scale",
        "remove",
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
    }
)
_IMAGE_REQUIRED_TARGETS = frozenset({"background", "layout", "style", "overall"})

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


def _supporting_list(production_brief: dict[str, Any], texts: dict[str, str]) -> list[str]:
    raw = production_brief.get("supporting")
    out: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            line = _s(item)
            if line:
                out.append(line)
    if not out:
        support = _s(texts.get("supporting"))
        if support:
            out.append(support)
    return out[:2]


def _badge_display(badge: str) -> str:
    if not badge:
        return ""
    if "%" in badge:
        import re

        m = re.search(r"(\d+)\s*%", badge.replace("~", ""))
        if m:
            return f"%{m.group(1)}"
        if badge.strip().startswith("~"):
            return badge.replace("lansman fiyat avantajı", "").strip() or badge
    return badge


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

    # Price frame
    frame_y = int(round(height * 0.68))
    frame_h = int(round(height * 0.11))
    frame_w = int(round(content_w * 0.92))
    if copy["old_price"] or copy["new_price"]:
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
    if copy["old_price"]:
        elements.append(
            {
                "id": "old-price",
                "type": "text",
                "role": "old_price",
                "content": copy["old_price"],
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "x": margin + 16,
                "y": frame_y + int(frame_h * 0.28),
                "width": int(frame_w * 0.42),
                "height": int(frame_h * 0.4),
                "z_index": 24,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.036)),
                    "font_weight": "normal",
                    "align": "left",
                    "color": "#D4C4A8",
                    "text_decoration": "line-through",
                },
            }
        )
    if copy["new_price"]:
        elements.append(
            {
                "id": "new-price",
                "type": "text",
                "role": "new_price",
                "content": copy["new_price"],
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "x": margin + int(frame_w * 0.52),
                "y": frame_y + int(frame_h * 0.18),
                "width": int(frame_w * 0.44),
                "height": int(frame_h * 0.62),
                "z_index": 25,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.072)),
                    "font_weight": "bold",
                    "align": "left",
                    "color": "#C4A35A",
                },
            }
        )

    support_y = int(round(height * 0.81))
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
                "y": support_y + idx * int(round(height * 0.032)),
                "width": content_w,
                "height": int(round(height * 0.03)),
                "z_index": 26 + idx,
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
    if supporting:
        elements.append(
            {
                "id": "support-message-1",
                "type": "text",
                "role": "support_message",
                "content": supporting[0],
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.78)),
                "width": content_w,
                "height": int(round(height * 0.04)),
                "z_index": 26,
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

    copy = {
        "headline": headline,
        "subheadline": subheadline,
        "unit": unit_label,
        "old_price": old_price,
        "new_price": new_price,
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
    if family == "price_lower_third" or intent in {
        "price_campaign",
        "sales_offer",
        "launch",
        "launch_price",
    }:
        elements.extend(_build_price_elements(**builder_kwargs))
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
        "elements": elements,
    }


def design_spec_to_smb_elements(design_spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Design Spec → SMB SocialElement-shaped dicts for hydration."""
    out: list[dict[str, Any]] = []
    for el in design_spec.get("elements") or []:
        if not isinstance(el, dict):
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
                    "align": _s(style.get("align"), "center"),
                    "borderRadius": int(style.get("border_radius") or 8),
                    "padding": int(style.get("padding") or 12),
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
        if role in {"subheadline", "support_message", "unit_label", "old_price", "new_price"}:
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


def route_revision(
    *,
    instruction: str,
    revision_diff: Any,
    intents: list[str] | None = None,
) -> RevisionRoute:
    """Smart revision router: LAYER_ONLY (GPT=0) vs IMAGE_REQUIRED."""
    low = (instruction or "").replace("İ", "i").replace("I", "ı").lower()
    for phrase in _IMAGE_REQUIRED_PHRASES:
        if phrase in low:
            return "IMAGE_REQUIRED"

    intent_set = {str(i).upper() for i in (intents or [])}
    if intent_set & {"ASSET_CHANGE", "STYLE_CHANGE"} and not (
        intent_set <= {"COPY_CHANGE", "LAYOUT_CHANGE", "COMMERCIAL_EMPHASIS", "LANGUAGE_CHANGE", "SIMPLIFY"}
    ):
        # Pure ASSET/STYLE without copy-only → image path
        if "ASSET_CHANGE" in intent_set or (
            "STYLE_CHANGE" in intent_set and "COPY_CHANGE" not in intent_set and "LAYOUT_CHANGE" not in intent_set
        ):
            return "IMAGE_REQUIRED"

    ops = []
    if hasattr(revision_diff, "operations"):
        ops = list(revision_diff.operations or [])
    elif isinstance(revision_diff, dict):
        ops = list(revision_diff.get("operations") or [])

    if not ops:
        # Ambiguous visual language without structured ops → image path
        if any(tok in low for tok in ("görsel", "visual", "render", "interior", "sahne", "scene", "atmosfer")):
            return "IMAGE_REQUIRED"
        # Default copy-ish instruction with no ops still tries layer path only if clearly copy
        if any(tok in low for tok in ("başlık", "headline", "cta", "rozet", "badge", "logo", "yazı", "metin")):
            return "LAYER_ONLY"
        return "IMAGE_REQUIRED"

    for op in ops:
        target = getattr(op, "target", None) if not isinstance(op, dict) else op.get("target")
        action = getattr(op, "action", None) if not isinstance(op, dict) else op.get("action")
        target_s = str(target or "").lower()
        action_s = str(action or "").lower()
        if action_s in {"minimum_change", "preserve"}:
            continue
        if action_s == "tone_adjust" and target_s in _LAYER_ONLY_TARGETS | {"overall", "layout"}:
            # Soft tone stays on layers — never auto-grade background
            continue
        if target_s in _IMAGE_REQUIRED_TARGETS:
            return "IMAGE_REQUIRED"
        if target_s not in _LAYER_ONLY_TARGETS:
            return "IMAGE_REQUIRED"
        if action_s and action_s not in _LAYER_ONLY_ACTIONS:
            return "IMAGE_REQUIRED"
    return "LAYER_ONLY"


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
        "headline": ("headline",),
        "cta": ("cta",),
        "badge": ("discount-badge", "discount_badge", "badge"),
        "logo": ("logo",),
        "support_message": ("support-message-1", "support_message"),
        "subheadline": ("subheadline",),
    }.get(target, (target,))
    return _find_element(spec, *lookup)


def _scale_element(el: dict[str, Any], factor: float, *, aspect_lock: bool = True) -> None:
    factor = float(factor)
    cx = float(el.get("x", 0)) + float(el.get("width", 0)) / 2
    cy = float(el.get("y", 0)) + float(el.get("height", 0)) / 2
    nw = max(8, int(round(float(el.get("width", 0)) * factor)))
    if aspect_lock or el.get("lock_aspect_ratio"):
        nh = max(8, int(round(float(el.get("height", 0)) * factor)))
    else:
        nh = max(8, int(round(float(el.get("height", 0)) * factor)))
    el["width"] = nw
    el["height"] = nh
    el["x"] = int(round(cx - nw / 2))
    el["y"] = int(round(cy - nh / 2))
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

    def _priority_key(raw: Any) -> tuple[int, int]:
        if hasattr(raw, "model_dump"):
            op = raw.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(raw, dict):
            op = dict(raw)
        else:
            return (50, 0)
        action = str(op.get("action") or "").lower()
        # Lower key runs first: scale → geometry → text/color → remove
        if action == "scale":
            return (0, 0)
        if action in {"set_font_size"}:
            return (1, 0)
        if action in {"translate", "set_position", "align", "set_geometry"}:
            return (2, 0)
        if action in {"replace_text", "set_color", "tone_adjust"}:
            return (3, 0)
        if action in {"remove", "hide"}:
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
        scale_factor = op.get("scale_factor")
        element_id = op.get("element_id")
        el = _resolve_layer(spec, target, element_id if isinstance(element_id, str) else None)

        if action == "replace_text" and to_value and el is not None:
            el["content"] = str(to_value)
            if target == "price":
                el["claim_sensitive"] = True

        elif action == "scale" and scale_factor and el is not None:
            _scale_element(el, float(scale_factor), aspect_lock=True)

        elif action == "translate" and el is not None:
            dx = float(op.get("dx") or 0)
            dy = float(op.get("dy") or 0)
            el["x"] = int(round(float(el.get("x", 0)) + dx))
            el["y"] = int(round(float(el.get("y", 0)) + dy))

        elif action in {"set_position", "align", "set_geometry"} and el is not None:
            live_x = False
            live_y = False
            edge = str(op.get("align_edge") or "").lower()
            ref_name = str(op.get("reference_element") or "")

            if action == "align" and edge:
                ew = float(el.get("width") or 0)
                eh = float(el.get("height") or 0)
                if ref_name in {"canvas", "canvas_center"} or (
                    edge in {"centerx", "center"} and not ref_name
                ):
                    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
                    cw = float(canvas.get("width") or 1080)
                    el["x"] = int(round((cw - ew) / 2))
                    live_x = True
                else:
                    ref = _resolve_layer(spec, ref_name) if ref_name else None
                    if ref is not None:
                        rx = float(ref.get("x") or 0)
                        ry = float(ref.get("y") or 0)
                        rw = float(ref.get("width") or 0)
                        rh = float(ref.get("height") or 0)
                        if edge == "left":
                            el["x"] = int(round(rx))
                            live_x = True
                        elif edge == "right":
                            el["x"] = int(round(rx + rw - ew))
                            live_x = True
                        elif edge in {"centerx", "center"}:
                            el["x"] = int(round(rx + rw / 2 - ew / 2))
                            live_x = True
                        elif edge == "top":
                            el["y"] = int(round(ry))
                            live_y = True
                        elif edge == "bottom":
                            el["y"] = int(round(ry + rh - eh))
                            live_y = True

            # CTA below price: y = ref.bottom + dy
            if (
                action == "set_position"
                and ref_name
                and op.get("dy") is not None
                and op.get("y") is None
            ):
                ref = _resolve_layer(spec, ref_name)
                if ref is not None:
                    el["y"] = int(
                        round(
                            float(ref.get("y") or 0)
                            + float(ref.get("height") or 0)
                            + float(op["dy"])
                        )
                    )
                    live_y = True

            if op.get("x") is not None and not live_x:
                el["x"] = int(round(float(op["x"])))
            if op.get("y") is not None and not live_y:
                el["y"] = int(round(float(op["y"])))
            if op.get("width") is not None:
                el["width"] = max(8, int(round(float(op["width"]))))
            if op.get("height") is not None:
                el["height"] = max(8, int(round(float(op["height"]))))

        elif action == "set_font_size" and el is not None and op.get("font_size") is not None:
            fs = max(8, int(round(float(op["font_size"]))))
            typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
            typo["font_size"] = fs
            el["typography"] = typo
            style = el.get("style") if isinstance(el.get("style"), dict) else {}
            if style:
                style["font_size"] = fs
                el["style"] = style

        elif action == "set_color" and el is not None and op.get("color"):
            color = str(op["color"])
            if el.get("type") == "cta" or target == "cta":
                style = el.get("style") if isinstance(el.get("style"), dict) else {}
                style["background_color"] = color
                el["style"] = style
            else:
                typo = el.get("typography") if isinstance(el.get("typography"), dict) else {}
                typo["color"] = color
                el["typography"] = typo
                style = el.get("style") if isinstance(el.get("style"), dict) else {}
                if "background_color" in style or target == "badge":
                    style["background_color"] = color
                    el["style"] = style

        elif action in {"remove", "hide"}:
            remove_ids = {
                "headline": {"headline"},
                "cta": {"cta"},
                "badge": {"discount-badge", "badge"},
                "logo": {"logo"},
                "support_message": {"support-message-1", "support-message-2"},
                "price": {"old-price", "new-price"},
            }.get(target, set())
            if isinstance(element_id, str) and element_id:
                remove_ids = set(remove_ids) | {element_id.lower()}
            # hide old-price only when noted
            note = str(op.get("note") or "").lower()
            if "old-price" in note or element_id == "old-price":
                remove_ids = {"old-price"}
            if remove_ids:
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
