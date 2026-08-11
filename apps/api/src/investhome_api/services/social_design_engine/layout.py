"""Deterministic Layout Intelligence for Social Media Builder.

AI supplies content / hierarchy / style / visual intent.
Pixel geometry is owned here so ops stay inside format-canonical canvas space.
Shared constrain_element / resolve_layout is the single geometry path for
create, AI edit, and (via mirrored client helpers) manual move/resize.
"""

from __future__ import annotations

from typing import Any, Literal

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

# Collision priority: higher stays; lower moves. Headline > body > CTA > image.
ROLE_PRIORITY = {
    "headline": 100,
    "body": 80,
    "custom": 70,
    "cta": 60,
    "button": 60,
    "image": 40,
}

VisualLayoutIntent = Literal[
    "INCREASE_WHITESPACE",
    "REDUCE_TEXT_DENSITY",
    "EMPHASIZE_HEADLINE",
    "DEEMPHASIZE_BODY",
    "MOVE_TEXT_AWAY_FROM_SUBJECT",
    "INCREASE_IMAGE_PROMINENCE",
    "SIMPLIFY_LAYOUT",
]

VISUAL_LAYOUT_VOCAB: frozenset[str] = frozenset(
    {
        "INCREASE_WHITESPACE",
        "REDUCE_TEXT_DENSITY",
        "EMPHASIZE_HEADLINE",
        "DEEMPHASIZE_BODY",
        "MOVE_TEXT_AWAY_FROM_SUBJECT",
        "INCREASE_IMAGE_PROMINENCE",
        "SIMPLIFY_LAYOUT",
    }
)


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


def _finite_num(value: Any, default: float) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if n != n or n in (float("inf"), float("-inf")):  # NaN / Inf
        return default
    return n


def constrain_element(
    el: dict[str, Any],
    *,
    canvas_w: int,
    canvas_h: int,
    full_bleed: bool | None = None,
) -> dict[str, int]:
    """Single shared geometry clamp — AI + manual paths must use this."""
    el_type = str(el.get("type") or "").upper()
    if full_bleed is None:
        full_bleed = el_type == "IMAGE"
    is_button = el_type in {"BUTTON", "CTA"}

    if full_bleed:
        w = clamp_int(el.get("width"), 8, canvas_w, min(200, canvas_w))
        h = clamp_int(el.get("height"), 8, canvas_h, min(80, canvas_h))
        return {
            "x": clamp_int(el.get("x"), 0, max(0, canvas_w - w), 0),
            "y": clamp_int(el.get("y"), 0, max(0, canvas_h - h), 0),
            "width": w,
            "height": h,
        }

    if is_button:
        pad = 24
        max_w = max(8, canvas_w - pad * 2)
        max_h = max(8, canvas_h - pad * 2)
        w = clamp_int(el.get("width"), 8, max_w, min(200, max_w))
        h = clamp_int(el.get("height"), 8, max_h, min(48, max_h))
        return {
            "x": clamp_int(el.get("x"), pad, max(pad, canvas_w - w - pad), pad),
            "y": clamp_int(el.get("y"), pad, max(pad, canvas_h - h - pad), pad),
            "width": w,
            "height": h,
        }

    return clamp_safe_geometry(
        x=el.get("x"),
        y=el.get("y"),
        width=el.get("width"),
        height=el.get("height"),
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        full_bleed=False,
    )


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
) -> tuple[int, int, int]:
    """Return (line_count, pixel_height, content_width)."""
    lines = estimate_wrap_lines(text, font_size, max_width, bold=bold)
    if not lines:
        return 0, 0, 0
    height = int(round(len(lines) * font_size * line_height))
    char_w = max(1.0, font_size * _char_ratio(bold))
    content_w = int(round(max(len(line) for line in lines) * char_w))
    return len(lines), height, content_w


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
        lines, height, _ = measure_text_block(text, font, max_width, bold=bold)
        if lines <= max_lines and height <= max_height:
            return font, max(height, int(round(font * LINE_HEIGHT)))
        font -= 2
    lines, height, _ = measure_text_block(text, min_size, max_width, bold=bold)
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


def subject_safe_regions(canvas_w: int, canvas_h: int) -> dict[str, dict[str, int]]:
    """P0 heuristics (no CV): upper sky band vs mid/lower subject (building) band."""
    box = safe_content_box(canvas_w, canvas_h)
    sky_h = max(80, int(round(canvas_h * 0.28)))
    return {
        "sky": {
            "x": box["x"],
            "y": box["y"],
            "width": box["width"],
            "height": min(sky_h, box["height"]),
        },
        # Mid/lower band treated as likely subject/building — avoid covering.
        "subject": {
            "x": box["x"],
            "y": box["y"] + int(round(box["height"] * 0.32)),
            "width": box["width"],
            "height": max(40, int(round(box["height"] * 0.55))),
        },
    }


def auto_layout_text(
    el: dict[str, Any],
    *,
    canvas_w: int,
    canvas_h: int,
    preferred_font: int | None = None,
    max_lines: int | None = None,
    allow_grow_width: bool = True,
    allow_grow_height: bool = True,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_position: bool = True,
) -> dict[str, Any]:
    """
    Text auto-layout: measure → grow box if space → wrap → shrink font.
    Never silently clips: height always fits measured lines at chosen font.
    """
    role = str(el.get("role") or "custom").lower()
    if role not in {"headline", "body", "custom"}:
        role = "custom"
    prefs = role_font_prefs(role, canvas_w)
    box = safe_content_box(canvas_w, canvas_h)
    bold = str(el.get("fontWeight") or "").lower() == "bold" or role == "headline"
    content = str(el.get("content") or "")

    if max_lines is None:
        max_lines = 1 if role == "headline" and len(content) <= 28 else (3 if role == "headline" else 6)

    preferred = clamp_int(
        preferred_font if preferred_font is not None else el.get("fontSize"),
        prefs["min"],
        prefs["max"],
        prefs["preferred"],
    )

    cur_x = clamp_int(el.get("x"), box["x"], box["x"] + box["width"], box["x"])
    cur_y = clamp_int(el.get("y"), box["y"], box["y"] + box["height"], box["y"])
    cur_w = clamp_int(el.get("width"), 40, box["width"], min(box["width"], max(200, box["width"])))

    width_cap = min(box["width"], max_width) if max_width is not None else box["width"]
    # Remaining vertical room from current y (or full safe box).
    if max_height is not None:
        height_cap = max(int(round(preferred * LINE_HEIGHT)), max_height)
    else:
        height_cap = max(int(round(preferred * LINE_HEIGHT)), box["y"] + box["height"] - cur_y)

    font = preferred
    width = min(cur_w, width_cap)
    height = int(round(font * LINE_HEIGHT))
    x, y = cur_x, cur_y

    def _try(font_size: int, box_w: int) -> tuple[int, int, int, bool]:
        lines, h, content_w = measure_text_block(content, font_size, box_w, bold=bold)
        ok = lines <= max_lines and h <= height_cap and (max_lines > 1 or lines <= 1)
        return lines, h, content_w, ok

    # 1) Try preferred font at current width.
    lines, h, content_w, ok = _try(font, width)
    if ok:
        height = max(h, int(round(font * LINE_HEIGHT)))
        if allow_grow_height:
            height = min(height_cap, max(height, h))
    else:
        # 2) Grow width toward safe max (esp. one-line).
        if allow_grow_width and (max_lines == 1 or not ok):
            target_w = min(width_cap, max(width, content_w + int(round(font * 0.5)), int(round(box["width"] * 0.92))))
            # Binary-ish expand
            grow_w = width
            while grow_w < target_w:
                grow_w = min(target_w, grow_w + max(24, width // 6))
                lines, h, content_w, ok = _try(font, grow_w)
                if ok:
                    width = grow_w
                    height = max(h, int(round(font * LINE_HEIGHT)))
                    # Re-center or keep x inside safe box after width change
                    if not keep_position or str(el.get("align") or "center") == "center":
                        x = box["x"] + max(0, (box["width"] - width) // 2)
                    else:
                        x = min(x, box["x"] + box["width"] - width)
                        x = max(box["x"], x)
                    break
            if not ok and max_lines == 1:
                # One-line: expand to full safe width then shrink font
                width = width_cap
                if str(el.get("align") or "center") == "center":
                    x = box["x"] + max(0, (box["width"] - width) // 2)

        # 3) Wrap at max width (multi-line) — grow height.
        if not ok and max_lines > 1:
            width = min(width_cap, max(width, box["width"]))
            if str(el.get("align") or "center") == "center":
                x = box["x"] + max(0, (box["width"] - width) // 2)
            lines, h, content_w, ok = _try(font, width)
            if ok and allow_grow_height:
                height = min(height_cap, max(h, int(round(font * LINE_HEIGHT))))
            elif lines > 0 and h <= height_cap:
                height = min(height_cap, max(h, int(round(font * LINE_HEIGHT))))
                ok = lines <= max_lines

        # 4) Shrink font to largest valid size — never silent clip.
        if not ok:
            font, height = fit_font_size(
                content,
                max_width=width,
                max_height=height_cap,
                preferred=font,
                min_size=prefs["min"],
                max_size=prefs["max"],
                bold=bold,
                max_lines=max_lines,
            )
            lines, h, _ = measure_text_block(content, font, width, bold=bold)
            height = max(h, int(round(font * LINE_HEIGHT)))
            height = min(height_cap, height)

    geo = clamp_safe_geometry(
        x=x,
        y=y,
        width=width,
        height=max(8, height),
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
    draft = dict(el)
    draft["x"] = region["x"]
    draft["y"] = region["y"]
    draft["width"] = region["width"]
    draft["fontSize"] = preferred
    return auto_layout_text(
        draft,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        preferred_font=preferred,
        max_lines=4 if role == "headline" else 6,
        max_width=int(region["width"]),
        max_height=int(region.get("max_height") or region.get("height") or int(canvas_h * 0.2)),
        keep_position=True,
    )


def layout_cta_element(
    el: dict[str, Any],
    *,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, Any]:
    slots = social_layout_slots(canvas_w, canvas_h)
    region = slots["cta"]
    label = str(el.get("label") or "Learn more")
    prefs_w = int(region["width"])
    est_w = int(round(len(label) * region["height"] * 0.42 * 0.6 + region["height"]))
    width = clamp_int(est_w, 120, prefs_w, prefs_w)
    x = int(round((canvas_w - width) / 2))
    geo = constrain_element(
        {**el, "type": "BUTTON", "x": x, "y": region["y"], "width": width, "height": region["height"]},
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )
    out = dict(el)
    out.update(geo)
    out["type"] = "BUTTON"
    return out


def _boxes_overlap(a: dict[str, Any], b: dict[str, Any], gap: int = 0) -> bool:
    ax1 = int(_finite_num(a.get("x"), 0))
    ay1 = int(_finite_num(a.get("y"), 0))
    ax2 = ax1 + int(_finite_num(a.get("width"), 0))
    ay2 = ay1 + int(_finite_num(a.get("height"), 0))
    bx1 = int(_finite_num(b.get("x"), 0))
    by1 = int(_finite_num(b.get("y"), 0))
    bx2 = bx1 + int(_finite_num(b.get("width"), 0))
    by2 = by1 + int(_finite_num(b.get("height"), 0))
    return not (ax2 + gap <= bx1 or bx2 + gap <= ax1 or ay2 + gap <= by1 or by2 + gap <= ay1)


def _priority_for(el: dict[str, Any]) -> int:
    el_type = str(el.get("type") or "").upper()
    if el_type in {"BUTTON", "CTA"}:
        return ROLE_PRIORITY["cta"]
    if el_type == "IMAGE":
        return ROLE_PRIORITY["image"]
    role = str(el.get("role") or "custom").lower()
    return ROLE_PRIORITY.get(role, 50)


def resolve_collisions(
    elements: list[dict[str, Any]],
    *,
    canvas_w: int,
    canvas_h: int,
) -> list[dict[str, Any]]:
    """
    Deterministic overlap resolve: lower-priority element moves down (or shrinks).
    Headline grows → body down; body grows → CTA down; CTA at bottom → refit spacing.
    """
    box = safe_content_box(canvas_w, canvas_h)
    gap = max(12, int(round(canvas_h * 0.015)))
    working = [dict(e) for e in elements if isinstance(e, dict)]

    # Stack role order vertically when roles known.
    headline = next((e for e in working if e.get("type") == "TEXT" and e.get("role") == "headline"), None)
    body = next((e for e in working if e.get("type") == "TEXT" and e.get("role") == "body"), None)
    cta = next((e for e in working if e.get("type") in {"BUTTON", "CTA"}), None)

    if headline and body:
        min_body_y = int(headline["y"]) + int(headline["height"]) + gap
        if int(body["y"]) < min_body_y:
            body["y"] = min_body_y
            max_bottom = int(cta["y"]) - gap if cta else box["y"] + box["height"]
            body_max_h = max(int(round(int(body.get("fontSize") or 20) * LINE_HEIGHT)), max_bottom - int(body["y"]))
            fitted = auto_layout_text(
                body,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                preferred_font=int(body.get("fontSize") or 20),
                max_height=body_max_h,
                max_width=int(body.get("width") or box["width"]),
            )
            body.update(fitted)

    if body and cta:
        min_cta_y = int(body["y"]) + int(body["height"]) + gap
        target_y = max(int(cta["y"]), min_cta_y)
        max_cta_y = box["y"] + box["height"] - int(cta.get("height") or 40)
        if target_y > max_cta_y:
            # CTA at bottom: compress body / spacing to fit.
            overflow = target_y - max_cta_y
            body["y"] = max(box["y"], int(body["y"]) - overflow)
            if headline:
                min_body = int(headline["y"]) + int(headline["height"]) + gap
                if int(body["y"]) < min_body:
                    # Shrink headline height room by refitting with smaller max height
                    fitted_h = auto_layout_text(
                        headline,
                        canvas_w=canvas_w,
                        canvas_h=canvas_h,
                        preferred_font=int(headline.get("fontSize") or 28),
                        max_height=max(40, int(headline["height"]) - overflow // 2),
                    )
                    headline.update(fitted_h)
                    body["y"] = int(headline["y"]) + int(headline["height"]) + gap
            body_max_h = max(24, max_cta_y - gap - int(body["y"]))
            fitted_b = auto_layout_text(
                body,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                preferred_font=int(body.get("fontSize") or 20),
                max_height=body_max_h,
            )
            body.update(fitted_b)
            min_cta_y = int(body["y"]) + int(body["height"]) + gap
            target_y = min(max(min_cta_y, int(cta["y"])), max_cta_y)
        cta["y"] = target_y
        cta.update(constrain_element(cta, canvas_w=canvas_w, canvas_h=canvas_h))

    if headline and cta and not body:
        min_cta_y = int(headline["y"]) + int(headline["height"]) + gap
        cta["y"] = min(max(int(cta["y"]), min_cta_y), box["y"] + box["height"] - int(cta.get("height") or 40))
        cta.update(constrain_element(cta, canvas_w=canvas_w, canvas_h=canvas_h))

    # Generic pairwise: push lower-priority down.
    ordered = sorted(working, key=_priority_for, reverse=True)
    for i, hi in enumerate(ordered):
        for lo in ordered[i + 1 :]:
            if not _boxes_overlap(hi, lo, gap=gap):
                continue
            if _priority_for(hi) < _priority_for(lo):
                continue
            # Move lower element below higher
            new_y = int(hi["y"]) + int(hi["height"]) + gap
            max_y = box["y"] + box["height"] - int(lo.get("height") or 40)
            if new_y <= max_y:
                lo["y"] = new_y
            else:
                lo["y"] = max(box["y"], max_y)
            lo.update(constrain_element(lo, canvas_w=canvas_w, canvas_h=canvas_h))

    return working


def align_element_geometry(
    el: dict[str, Any],
    mode: str,
    *,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, Any]:
    """Shared alignment for AI ALIGN_ELEMENT and manual align menu."""
    out = dict(el)
    geo = constrain_element(out, canvas_w=canvas_w, canvas_h=canvas_h)
    out.update(geo)
    w = int(out["width"])
    h = int(out["height"])
    box = safe_content_box(canvas_w, canvas_h)
    m = (mode or "center").strip().lower()
    if m in {"left", "safe-left"}:
        out["x"] = box["x"] if m == "safe-left" or out.get("type") == "TEXT" else 0
        if out.get("type") == "TEXT":
            out["align"] = "left"
    elif m in {"right", "safe-right"}:
        out["x"] = box["x"] + box["width"] - w if m == "safe-right" or out.get("type") == "TEXT" else max(0, canvas_w - w)
        if out.get("type") == "TEXT":
            out["align"] = "right"
    elif m in {"center", "hcenter", "h-center"}:
        out["x"] = box["x"] + max(0, (box["width"] - w) // 2)
        if out.get("type") == "TEXT":
            out["align"] = "center"
    elif m in {"vcenter", "v-center"}:
        out["y"] = box["y"] + max(0, (box["height"] - h) // 2)
    elif m in {"safe-area", "safe"}:
        out["x"] = box["x"] + max(0, (box["width"] - w) // 2)
        out["y"] = max(box["y"], min(int(out["y"]), box["y"] + box["height"] - h))
        if out.get("type") == "TEXT":
            out["align"] = "center"
    out.update(constrain_element(out, canvas_w=canvas_w, canvas_h=canvas_h))
    return out


def apply_visual_layout_intent(
    post: dict[str, Any],
    intent: str,
) -> dict[str, Any]:
    """Map validated visual-language vocab → deterministic geometry/style tweaks."""
    name = str(intent or "").upper()
    if name not in VISUAL_LAYOUT_VOCAB:
        return post
    cw, ch = canvas_size_for_post(post)
    elements = [dict(e) for e in (post.get("elements") or []) if isinstance(e, dict)]
    box = safe_content_box(cw, ch)
    gap = max(16, int(round(ch * 0.02)))

    headline = next((e for e in elements if e.get("type") == "TEXT" and e.get("role") == "headline"), None)
    body = next((e for e in elements if e.get("type") == "TEXT" and e.get("role") == "body"), None)
    cta = next((e for e in elements if e.get("type") in {"BUTTON", "CTA"}), None)
    images = [e for e in elements if e.get("type") == "IMAGE"]

    if name == "INCREASE_WHITESPACE":
        if headline and body:
            body["y"] = int(headline["y"]) + int(headline["height"]) + gap * 2
        if body and cta:
            cta["y"] = min(
                box["y"] + box["height"] - int(cta.get("height") or 40),
                int(body["y"]) + int(body["height"]) + gap * 2,
            )
        if cta and not body and headline:
            cta["y"] = min(
                box["y"] + box["height"] - int(cta.get("height") or 40),
                int(headline["y"]) + int(headline["height"]) + gap * 2,
            )

    elif name == "REDUCE_TEXT_DENSITY":
        if body:
            fs = clamp_int(body.get("fontSize"), 12, 36, 20)
            body["fontSize"] = max(12, fs - 2)
            body.update(
                auto_layout_text(body, canvas_w=cw, canvas_h=ch, preferred_font=int(body["fontSize"]))
            )
        if headline:
            # Slightly more line room / not denser
            body_y = int(body["y"]) if body else box["y"] + box["height"]
            headline.update(
                auto_layout_text(
                    headline,
                    canvas_w=cw,
                    canvas_h=ch,
                    preferred_font=int(headline.get("fontSize") or 36),
                    max_height=max(40, body_y - int(headline["y"]) - gap),
                )
            )

    elif name == "EMPHASIZE_HEADLINE":
        if headline:
            prefs = role_font_prefs("headline", cw)
            next_fs = min(prefs["max"], clamp_int(headline.get("fontSize"), prefs["min"], prefs["max"], prefs["preferred"]) + 8)
            headline.update(
                auto_layout_text(headline, canvas_w=cw, canvas_h=ch, preferred_font=next_fs)
            )

    elif name == "DEEMPHASIZE_BODY":
        if body:
            prefs = role_font_prefs("body", cw)
            next_fs = max(prefs["min"], clamp_int(body.get("fontSize"), prefs["min"], prefs["max"], prefs["preferred"]) - 4)
            body["fontSize"] = next_fs
            body.update(auto_layout_text(body, canvas_w=cw, canvas_h=ch, preferred_font=next_fs))

    elif name in {"MOVE_TEXT_AWAY_FROM_SUBJECT", "SIMPLIFY_LAYOUT"}:
        regions = subject_safe_regions(cw, ch)
        sky = regions["sky"]
        if headline:
            headline["y"] = sky["y"] + max(0, int(round(sky["height"] * 0.15)))
            headline["x"] = sky["x"]
            headline["width"] = sky["width"]
            headline.update(
                auto_layout_text(
                    headline,
                    canvas_w=cw,
                    canvas_h=ch,
                    preferred_font=int(headline.get("fontSize") or 36),
                    max_height=max(40, sky["height"] - 16),
                    max_width=sky["width"],
                )
            )
        if body:
            base_y = int(headline["y"]) + int(headline["height"]) + gap if headline else sky["y"] + sky["height"] // 2
            body["y"] = min(base_y, sky["y"] + sky["height"])
            body["x"] = sky["x"]
            body["width"] = sky["width"]
            body.update(
                auto_layout_text(
                    body,
                    canvas_w=cw,
                    canvas_h=ch,
                    preferred_font=int(body.get("fontSize") or 20),
                    max_width=sky["width"],
                )
            )
        if name == "SIMPLIFY_LAYOUT" and body:
            # Slightly reduce body presence
            body["fontSize"] = max(14, int(body.get("fontSize") or 20) - 2)
            body.update(auto_layout_text(body, canvas_w=cw, canvas_h=ch, preferred_font=int(body["fontSize"])))

    elif name == "INCREASE_IMAGE_PROMINENCE":
        for img in images:
            target = min(cw, ch)
            img["width"] = min(cw, max(int(img.get("width") or target // 3), int(target * 0.42)))
            img["height"] = min(ch, max(int(img.get("height") or target // 3), int(target * 0.42)))
            img["x"] = max(0, (cw - int(img["width"])) // 2)
            img["y"] = max(0, (ch - int(img["height"])) // 2)
            img.update(constrain_element(img, canvas_w=cw, canvas_h=ch, full_bleed=True))
        # Nudge text toward sky so subject/image reads larger
        return apply_visual_layout_intent({**post, "elements": elements}, "MOVE_TEXT_AWAY_FROM_SUBJECT")

    post = dict(post)
    post["elements"] = resolve_collisions(elements, canvas_w=cw, canvas_h=ch)
    for el in post["elements"]:
        el.update(constrain_element(el, canvas_w=cw, canvas_h=ch))
    return post


def resolve_layout(
    post: dict[str, Any],
    *,
    refit_text: bool = True,
    text_hints: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Canonical layout pass used after AI edits, format change, and create.
    text_hints: optional {element_id: {preferred_font, max_lines, ...}}
    """
    cw, ch = canvas_size_for_post(post)
    post["width"] = cw
    post["height"] = ch
    elements = post.get("elements")
    if not isinstance(elements, list):
        post["elements"] = []
        return post

    hints = text_hints or {}
    next_elements: list[Any] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        el_type = str(el.get("type") or "").upper()
        if el_type == "TEXT" and refit_text:
            hid = str(el.get("id") or "")
            hint = hints.get(hid) or {}
            next_elements.append(
                auto_layout_text(
                    el,
                    canvas_w=cw,
                    canvas_h=ch,
                    preferred_font=hint.get("preferred_font"),
                    max_lines=hint.get("max_lines"),
                    allow_grow_width=hint.get("allow_grow_width", True),
                    allow_grow_height=hint.get("allow_grow_height", True),
                    keep_position=True,
                )
            )
        elif el_type in {"BUTTON", "CTA"}:
            geo = constrain_element(el, canvas_w=cw, canvas_h=ch)
            btn = dict(el)
            btn.update(geo)
            next_elements.append(btn)
        elif el_type == "IMAGE":
            geo = constrain_element(el, canvas_w=cw, canvas_h=ch, full_bleed=True)
            img = dict(el)
            img.update(geo)
            next_elements.append(img)
        else:
            next_elements.append(el)

    next_elements = resolve_collisions(next_elements, canvas_w=cw, canvas_h=ch)
    for el in next_elements:
        if isinstance(el, dict):
            el.update(constrain_element(el, canvas_w=cw, canvas_h=ch))

    post["elements"] = next_elements
    return post


def apply_layout_grammar(post: dict[str, Any]) -> dict[str, Any]:
    """
    Reposition role-based TEXT + CTA into the default social grammar.
    Cover/background stays full-bleed via coverAssetId (not an element).
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
            geo = constrain_element(el, canvas_w=cw, canvas_h=ch, full_bleed=True)
            img = dict(el)
            img.update(geo)
            next_elements.append(img)
        else:
            next_elements.append(el)

    post["elements"] = next_elements
    return resolve_layout(post, refit_text=False)


def reflow_for_format(post: dict[str, Any], preset: str) -> dict[str, Any]:
    """Format change: re-run constraints — do not mere-stretch coordinates."""
    if preset in FORMAT_PRESETS:
        w, h = FORMAT_PRESETS[preset]
        post["formatPreset"] = preset
        post["width"] = w
        post["height"] = h
    return apply_layout_grammar(post)


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
    x = int(_finite_num(el.get("x"), 0))
    y = int(_finite_num(el.get("y"), 0))
    w = int(_finite_num(el.get("width"), 0))
    h = int(_finite_num(el.get("height"), 0))
    return x >= mx and y >= my and x + w <= canvas_w - mx and y + h <= canvas_h - my


def strip_llm_geometry(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove free pixel geometry so deterministic layout owns placement."""
    out = dict(payload)
    for key in ("x", "y", "width", "height", "position"):
        out.pop(key, None)
    return out


def text_fits_without_clip(el: dict[str, Any]) -> bool:
    """Whether measured text height fits inside the element box at its fontSize."""
    if el.get("type") != "TEXT":
        return True
    font = clamp_int(el.get("fontSize"), 8, 200, 24)
    bold = str(el.get("fontWeight") or "").lower() == "bold" or el.get("role") == "headline"
    width = clamp_int(el.get("width"), 8, 4096, 200)
    height = clamp_int(el.get("height"), 8, 4096, 40)
    _, measured_h, _ = measure_text_block(str(el.get("content") or ""), font, width, bold=bold)
    return measured_h <= height + 2
