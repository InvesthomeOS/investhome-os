"""Editable Finished-Ad Design Spec — structured layers for SMB hydration.

AI Creative Director still owns design decisions via production_brief.
This module converts FINAL copy + assets into an editable Design Spec the OS
renders as real SMB layers — it does not invent campaign creative.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal
from uuid import UUID

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
) -> dict[str, Any]:
    """Emit Design Spec from FINAL production brief + locked assets.

    Layout is a deterministic premium price-campaign template derived from the
    brief (not free-form invention). Lifestyle / non-price intents omit price
    layers when copy is absent.
    """
    width, height = canvas_size_for_aspect(aspect_ratio, format_preset)
    final = production_brief.get("final_copy") if isinstance(production_brief.get("final_copy"), dict) else {}
    intent = _s(
        campaign_intent
        or production_brief.get("campaign_intent")
        or texts.get("campaign_mode"),
        "general_awareness",
    ).lower()

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
    badge = _s(texts.get("value_badge") or final.get("value_badge"))
    # Normalize "~25%" style to a short badge when percent-like
    badge_display = badge
    if badge and "%" in badge:
        # Prefer compact "%25" style for badge layer when present
        import re

        m = re.search(r"(\d+)\s*%", badge.replace("~", ""))
        if m:
            badge_display = f"%{m.group(1)}"
        elif badge.strip().startswith("~"):
            badge_display = badge.replace("lansman fiyat avantajı", "").strip() or badge
    cta = _s(texts.get("cta") or final.get("cta") or production_brief.get("cta"), "Detayları İncele")
    supporting = _supporting_list(production_brief, texts)

    margin = int(round(width * 0.07))
    content_w = width - margin * 2
    bg_id = str(master_background_asset_id)
    logo_id = str(logo_asset_id)

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
        },
        {
            "id": "logo",
            "type": "logo",
            "role": "logo",
            "asset_id": logo_id,
            "locked": False,
            "editable": True,
            "lock_aspect_ratio": True,
            "x": margin,
            "y": int(round(height * 0.045)),
            "width": int(round(width * 0.22)),
            "height": int(round(height * 0.07)),
            "z_index": 10,
            "opacity": 1.0,
        },
    ]

    y_cursor = int(round(height * 0.14))
    if headline:
        elements.append(
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": headline,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": y_cursor,
                "width": content_w,
                "height": int(round(height * 0.09)),
                "z_index": 20,
                "typography": {
                    "font_family": "serif",
                    "font_size": int(round(width * 0.072)),
                    "font_weight": "bold",
                    "align": "left",
                    "color": "#F7F3EB",
                    "line_height": 1.05,
                },
            }
        )
        y_cursor += int(round(height * 0.095))

    if subheadline and subheadline != headline:
        elements.append(
            {
                "id": "subheadline",
                "type": "text",
                "role": "subheadline",
                "content": subheadline,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": y_cursor,
                "width": content_w,
                "height": int(round(height * 0.06)),
                "z_index": 21,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.032)),
                    "font_weight": "medium",
                    "align": "left",
                    "color": "#E8E0D4",
                    "line_height": 1.25,
                },
            }
        )
        y_cursor += int(round(height * 0.065))

    if unit_label:
        elements.append(
            {
                "id": "unit-label",
                "type": "text",
                "role": "unit_label",
                "content": unit_label,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": int(round(height * 0.48)),
                "width": int(round(content_w * 0.55)),
                "height": int(round(height * 0.035)),
                "z_index": 22,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.028)),
                    "font_weight": "semibold",
                    "align": "left",
                    "color": "#D4C4A8",
                },
            }
        )

    price_y = int(round(height * 0.52))
    if old_price:
        elements.append(
            {
                "id": "old-price",
                "type": "text",
                "role": "old_price",
                "content": old_price,
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "x": margin,
                "y": price_y,
                "width": int(round(content_w * 0.45)),
                "height": int(round(height * 0.04)),
                "z_index": 23,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.034)),
                    "font_weight": "normal",
                    "align": "left",
                    "color": "#B8A990",
                    "text_decoration": "line-through",
                },
            }
        )
    if new_price:
        elements.append(
            {
                "id": "new-price",
                "type": "text",
                "role": "new_price",
                "content": new_price,
                "locked": False,
                "editable": True,
                "claim_sensitive": True,
                "x": margin,
                "y": price_y + int(round(height * 0.038)),
                "width": int(round(content_w * 0.55)),
                "height": int(round(height * 0.07)),
                "z_index": 24,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.078)),
                    "font_weight": "bold",
                    "align": "left",
                    "color": "#FFFFFF",
                },
            }
        )

    if badge_display and intent in {"price_campaign", "sales_offer", "launch", "launch_price"}:
        badge_w = int(round(width * 0.16))
        badge_h = int(round(height * 0.09))
        elements.append(
            {
                "id": "discount-badge",
                "type": "badge",
                "role": "discount_badge",
                "content": badge_display,
                "locked": False,
                "editable": True,
                "x": width - margin - badge_w,
                "y": int(round(height * 0.50)),
                "width": badge_w,
                "height": badge_h,
                "z_index": 25,
                "style": {
                    "background_color": "#C4A35A",
                    "text_color": "#1A1510",
                    "border_radius": int(round(badge_w * 0.5)),
                    "font_size": int(round(width * 0.042)),
                    "font_weight": "bold",
                    "align": "center",
                },
            }
        )

    support_y = int(round(height * 0.72))
    for idx, line in enumerate(supporting):
        elements.append(
            {
                "id": f"support-message-{idx + 1}",
                "type": "text",
                "role": "support_message",
                "content": line,
                "locked": False,
                "editable": True,
                "x": margin,
                "y": support_y + idx * int(round(height * 0.04)),
                "width": content_w,
                "height": int(round(height * 0.035)),
                "z_index": 26 + idx,
                "typography": {
                    "font_family": "sans",
                    "font_size": int(round(width * 0.026)),
                    "font_weight": "normal",
                    "align": "left",
                    "color": "#EDE6DA",
                },
            }
        )

    cta_w = int(round(width * 0.55))
    cta_h = int(round(height * 0.055))
    elements.append(
        {
            "id": "cta",
            "type": "cta",
            "role": "cta",
            "content": cta,
            "locked": False,
            "editable": True,
            "x": margin,
            "y": int(round(height * 0.88)),
            "width": cta_w,
            "height": cta_h,
            "z_index": 40,
            "style": {
                "background_color": "#F7F3EB",
                "text_color": "#1A1510",
                "border_color": "#F7F3EB",
                "border_radius": int(round(cta_h * 0.2)),
                "padding": int(round(cta_h * 0.25)),
                "font_size": int(round(width * 0.028)),
                "font_weight": "semibold",
                "align": "center",
            },
        }
    )

    return {
        "version": 1,
        "mode": "editable_finished_ad",
        "canvas": {
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "format_preset": format_preset,
        },
        "language": language,
        "campaign_intent": intent,
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

        if etype == "cta" or role == "cta":
            out.append(
                {
                    "id": eid or "cta",
                    "type": "BUTTON",
                    "label": _s(el.get("content") or el.get("label"), "CTA"),
                    "backgroundColor": _s(style.get("background_color"), "#F7F3EB"),
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
            # Badge as high-contrast TEXT (minimal — no shape editor)
            out.append(
                {
                    "id": eid or "discount-badge",
                    "type": "TEXT",
                    "role": "eyebrow",
                    "content": _s(el.get("content")),
                    "fontSize": int(style.get("font_size") or typo.get("font_size") or 36),
                    "fontWeight": _s(style.get("font_weight") or typo.get("font_weight"), "bold"),
                    "align": _s(style.get("align") or typo.get("align"), "center"),
                    "color": _s(style.get("text_color") or typo.get("color"), "#1A1510"),
                    "fontFamily": "sans",
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "zIndex": z,
                    "opacity": opacity if opacity is not None else 1.0,
                    "_designRole": "discount_badge",
                    "_badgeStyle": {
                        "backgroundColor": _s(style.get("background_color"), "#C4A35A"),
                        "borderRadius": int(style.get("border_radius") or 999),
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
