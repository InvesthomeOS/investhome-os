"""Deterministic social layout grammar, safe bounds, and text fitting.

AI supplies content / hierarchy / style intent. Pixel geometry is owned by
this module so ops stay inside format-canonical canvas space (e.g. 1080×1080).
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.social_design_engine.ops import FORMAT_PRESETS, clamp_int

# ~7% inset for text/CTA (spec: 5–8%). Background / full-bleed covers are exempt.
SAFE_MARGIN_RATIO = 0.07
LINE_HEIGHT = 1.2
# Average glyph width as a fraction of fontSize (deterministic, no browser measure).
AVG_CHAR_RATIO_NORMAL = 0.52
AVG_CHAR_RATIO_BOLD = 0.58

ROLE_FONT_DEFAULTS = {
    "headline": {"preferred_ratio": 0.055, "min": 22, "max": 72},
    "body": {"preferred_ratio": 0.028, "min": 14, "max": 36},
    "custom": {"preferred_ratio": 0.032, "min": 14, "max": 48},
}


def canvas_size_for_post(post: dict[str, Any]) -> tuple[int, int]:
    preset = str(post.get("formatPreset") or post.get("format_preset") or "square")
    if preset in FORMAT_PRESETS:
        return FORMAT_PRESETS[preset]
    w = clamp_int(post.get("width"), 1, 4096, 1080)
    h = clamp_int(post.get("height"), 1, 4096, 1080)
    return w, h


def safe_margin(canvas_w: int, canvas_h: int) -> tuple[int, int]:
    mx = max(24, int(round(canvas_w * SAFE_MARGIN_RATIO)))
    my = max(24, int(round(canvas_h * SAFE_MARGIN_RATIO)))
    return mx, my


def safe_content_box(canvas_w: int, canvas_h: int) -> dict[str, int]:
    mx, my = safe_margin(canvas_w, canvas_h)
    return {
        "x": mx,
        "y": my,
        "width": max(40, canvas_w - mx * 2),
        "height": max(40, canvas_h - my * 2),
    }


def clamp_safe_geometry(
    *,
    x: Any,
    y: Any,
    width: Any,
    height: Any,
    canvas_w: int,
    canvas_h: int,
    full_bleed: bool = False,
) -> dict[str, int]:
    """Clamp element box inside the artboard. Text/CTA use safe margins."""
    if full_bleed:
        w = clamp_int(width, 8, canvas_w, canvas_w)
        h = clamp_int(height, 8, canvas_h, canvas_h)
        return {
            "x": clamp_int(x, 0, max(0, canvas_w - w), 0),
            "y": clamp_int(y, 0, max(0, canvas_h - h), 0),
            "width": w,
            "height": h,
        }

    box = safe_content_box(canvas_w, canvas_h)
    max_w = box["width"]
    max_h = box["height"]
    w = clamp_int(width, 8, max_w, min(200, max_w))
    h = clamp_int(height, 8, max_h, min(80, max_h))
    min_x, min_y = box["x"], box["y"]
    max_x = box["x"] + box["width"] - w
    max_y = box["y"] + box["height"] - h
    return {
        "x": clamp_int(x, min_x, max(min_x, max_x), min_x),
        "y": clamp_int(y, min_y, max(min_y, max_y), min_y),
        "width": w,
        "height": h,
    }


def _char_ratio(bold: bool) -> float:
    return AVG_CHAR_RATIO_BOLD if bold else AVG_CHAR_RATIO_NORMAL


def estimate_wrap_lines(text: str, font_size: int, max_width: int, *, bold: bool = False) -> list[str]:
    """Word-wrap estimate using average glyph width (deterministic)."""
    content = " ".join(str(text or "").split())
    if not content:
        return []
    if font_size <= 0 or max_width <= 0:
        return [content]
    char_w = max(1.0, font_size * _char_ratio(bold))
    max_chars = max(1, int(max_width / char_w))
    words = content.split(" ")
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
            # Hard-break extremely long tokens
            while len(current) > max_chars:
                lines.append(current[:max_chars])
                current = current[max_chars:]
    lines.append(current)
    return lines


def measure_text_block(
    text: str,
    font_size: int,
    max_width: int,
    *,
    bold: bool = False,
    line_height: float = LINE_HEIGHT,
) -> tuple[int, int]:
    """Return (line_count, pixel_height)."""
    lines = estimate_wrap_lines(text, font_size, max_width, bold=bold)
    if not lines:
        return 0, 0
    height = int(round(len(lines) * font_size * line_height))
    return len(lines), height


def fit_font_size(
    text: str,
    *,
    max_width: int,
    max_height: int,
    preferred: int,
    min_size: int,
    max_size: int,
    bold: bool = False,
    max_lines: int = 6,
) -> tuple[int, int]:
    """Shrink font until wrapped text fits max_height / max_lines. Returns (fontSize, height)."""
    font = clamp_int(preferred, min_size, max_size, preferred)
    min_size = max(8, min_size)
    while font >= min_size:
        lines, height = measure_text_block(text, font, max_width, bold=bold)
        if lines <= max_lines and height <= max_height:
            return font, max(height, int(round(font * line_height_min(lines))))
        font -= 2
    lines, height = measure_text_block(text, min_size, max_width, bold=bold)
    return min_size, min(max_height, max(height, min_size))


def line_height_min(lines: int) -> float:
    return LINE_HEIGHT if lines > 0 else 1.0


def role_font_prefs(role: str, canvas_w: int) -> dict[str, int]:
    spec = ROLE_FONT_DEFAULTS.get(role, ROLE_FONT_DEFAULTS["custom"])
    preferred = max(spec["min"], int(round(canvas_w * spec["preferred_ratio"])))
    return {
        "preferred": preferred,
        "min": spec["min"],
        "max": spec["max"],
    }


def social_layout_slots(canvas_w: int, canvas_h: int) -> dict[str, dict[str, int]]:
    """
    Default AI social grammar (canonical format pixels):
      BG full-bleed (cover) → overlay → HEADLINE upper/middle → BODY below → CTA lower safe.
    """
    box = safe_content_box(canvas_w, canvas_h)
    content_w = box["width"]
    pad_x = box["x"]

    headline_y = int(round(canvas_h * 0.22))
    headline_max_h = int(round(canvas_h * 0.22))
    body_y = int(round(canvas_h * 0.46))
    body_max_h = int(round(canvas_h * 0.22))
    cta_h = max(36, int(round(canvas_h * 0.045)))
    cta_w = min(content_w, max(160, int(round(canvas_w * 0.38))))
    cta_y = min(box["y"] + box["height"] - cta_h, int(round(canvas_h * 0.88)))
    cta_x = int(round((canvas_w - cta_w) / 2))

    # Keep CTA inside safe box
    cta_y = max(box["y"], min(cta_y, box["y"] + box["height"] - cta_h))

    return {
        "headline": {
            "x": pad_x,
            "y": max(box["y"], headline_y),
            "width": content_w,
            "max_height": headline_max_h,
        },
        "body": {
            "x": pad_x,
            "y": max(box["y"], body_y),
            "width": content_w,
            "max_height": body_max_h,
        },
        "cta": {
            "x": cta_x,
            "y": cta_y,
            "width": cta_w,
            "height": cta_h,
        },
    }


def layout_text_element(
    el: dict[str, Any],
    *,
    canvas_w: int,
    canvas_h: int,
    slot: dict[str, int] | None = None,
) -> dict[str, Any]:
    role = str(el.get("role") or "custom").lower()
    if role not in {"headline", "body", "custom"}:
        role = "custom"
    slots = social_layout_slots(canvas_w, canvas_h)
    region = slot or slots.get(role) or slots["body"]
    prefs = role_font_prefs(role, canvas_w)
    preferred = clamp_int(el.get("fontSize"), prefs["min"], prefs["max"], prefs["preferred"])
    bold = str(el.get("fontWeight") or "").lower() == "bold" or role == "headline"
    content = str(el.get("content") or "")
    max_h = int(region.get("max_height") or region.get("height") or int(canvas_h * 0.2))
    font, height = fit_font_size(
        content,
        max_width=int(region["width"]),
        max_height=max_h,
        preferred=preferred,
        min_size=prefs["min"],
        max_size=prefs["max"],
        bold=bold,
        max_lines=4 if role == "headline" else 6,
    )
    geo = clamp_safe_geometry(
        x=region["x"],
        y=region["y"],
        width=region["width"],
        height=max(int(round(font * LINE_HEIGHT)), height),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        full_bleed=False,
    )
    out = dict(el)
    out.update(geo)
    out["fontSize"] = font
    out["role"] = role
    if role == "headline":
        out["fontWeight"] = "bold"
    return out


def layout_cta_element(
    el: dict[str, Any],
    *,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, Any]:
    slots = social_layout_slots(canvas_w, canvas_h)
    region = slots["cta"]
    label = str(el.get("label") or "Learn more")
    # Shrink width if label is short; grow toward slot width if long.
    prefs_w = int(region["width"])
    est_w = int(round(len(label) * region["height"] * 0.42 * 0.6 + region["height"]))
    width = clamp_int(est_w, 120, prefs_w, prefs_w)
    x = int(round((canvas_w - width) / 2))
    geo = clamp_safe_geometry(
        x=x,
        y=region["y"],
        width=width,
        height=region["height"],
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        full_bleed=False,
    )
    out = dict(el)
    out.update(geo)
    return out


def apply_layout_grammar(post: dict[str, Any]) -> dict[str, Any]:
    """
    Reposition role-based TEXT + CTA into the default social grammar.
    Cover/background stays full-bleed via coverAssetId (not an element).
    Non-role IMAGE elements stay, but are clamped full-bleed-safe inside canvas.
    """
    cw, ch = canvas_size_for_post(post)
    post["width"] = cw
    post["height"] = ch
    elements = post.get("elements")
    if not isinstance(elements, list):
        post["elements"] = []
        return post

    slots = social_layout_slots(cw, ch)
    next_elements: list[Any] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        el_type = str(el.get("type") or "").upper()
        if el_type == "TEXT":
            role = str(el.get("role") or "custom").lower()
            slot = slots.get(role) if role in {"headline", "body"} else None
            next_elements.append(layout_text_element(el, canvas_w=cw, canvas_h=ch, slot=slot))
        elif el_type in {"BUTTON", "CTA"}:
            next_elements.append(layout_cta_element(el, canvas_w=cw, canvas_h=ch))
        elif el_type == "IMAGE":
            geo = clamp_safe_geometry(
                x=el.get("x", 0),
                y=el.get("y", 0),
                width=el.get("width", min(cw, ch) // 3),
                height=el.get("height", min(cw, ch) // 3),
                canvas_w=cw,
                canvas_h=ch,
                full_bleed=True,
            )
            img = dict(el)
            img.update(geo)
            next_elements.append(img)
        else:
            next_elements.append(el)

    # Resolve vertical collisions: body under headline, CTA below body when needed.
    headline = next(
        (
            e
            for e in next_elements
            if isinstance(e, dict) and e.get("type") == "TEXT" and e.get("role") == "headline"
        ),
        None,
    )
    body = next(
        (
            e
            for e in next_elements
            if isinstance(e, dict) and e.get("type") == "TEXT" and e.get("role") == "body"
        ),
        None,
    )
    cta = next(
        (
            e
            for e in next_elements
            if isinstance(e, dict) and e.get("type") in {"BUTTON", "CTA"}
        ),
        None,
    )
    gap = max(12, int(round(ch * 0.015)))
    box = safe_content_box(cw, ch)
    if headline and body:
        min_body_y = int(headline["y"]) + int(headline["height"]) + gap
        if int(body["y"]) < min_body_y:
            body["y"] = min_body_y
            # Refit body into remaining space above CTA
            max_bottom = int(cta["y"]) - gap if cta else box["y"] + box["height"]
            body_max_h = max(int(round(body["fontSize"] * LINE_HEIGHT)), max_bottom - body["y"])
            fitted = layout_text_element(
                body,
                canvas_w=cw,
                canvas_h=ch,
                slot={
                    "x": body["x"],
                    "y": body["y"],
                    "width": body["width"],
                    "max_height": body_max_h,
                },
            )
            body.update(fitted)
    if body and cta:
        min_cta_y = int(body["y"]) + int(body["height"]) + gap
        target_y = max(int(cta["y"]), min_cta_y)
        cta["y"] = min(target_y, box["y"] + box["height"] - int(cta["height"]))
        geo = clamp_safe_geometry(
            x=cta.get("x", slots["cta"]["x"]),
            y=cta["y"],
            width=cta.get("width", slots["cta"]["width"]),
            height=cta.get("height", slots["cta"]["height"]),
            canvas_w=cw,
            canvas_h=ch,
            full_bleed=False,
        )
        cta.update(geo)

    # Final bounds pass
    for el in next_elements:
        if not isinstance(el, dict):
            continue
        el_type = str(el.get("type") or "").upper()
        full_bleed = el_type == "IMAGE"
        geo = clamp_safe_geometry(
            x=el.get("x", 0),
            y=el.get("y", 0),
            width=el.get("width", 100),
            height=el.get("height", 40),
            canvas_w=cw,
            canvas_h=ch,
            full_bleed=full_bleed,
        )
        el.update(geo)

    post["elements"] = next_elements
    return post


def element_within_bounds(
    el: dict[str, Any],
    canvas_w: int,
    canvas_h: int,
    *,
    margin_ratio: float = SAFE_MARGIN_RATIO,
) -> bool:
    """True when element box is fully inside the canvas (optional margin for text/CTA)."""
    el_type = str(el.get("type") or "").upper()
    mx = 0 if el_type == "IMAGE" else max(0, int(round(canvas_w * margin_ratio)))
    my = 0 if el_type == "IMAGE" else max(0, int(round(canvas_h * margin_ratio)))
    x = int(el.get("x") or 0)
    y = int(el.get("y") or 0)
    w = int(el.get("width") or 0)
    h = int(el.get("height") or 0)
    return x >= mx and y >= my and x + w <= canvas_w - mx and y + h <= canvas_h - my


def strip_llm_geometry(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove free pixel geometry so deterministic layout owns placement."""
    out = dict(payload)
    for key in ("x", "y", "width", "height", "position"):
        out.pop(key, None)
    return out
