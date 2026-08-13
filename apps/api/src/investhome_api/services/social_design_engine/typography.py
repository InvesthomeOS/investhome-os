"""Typography intelligence — hierarchy, orphans, clipping, intentional breaks."""

from __future__ import annotations

import re
from typing import Any

from investhome_api.services.social_design_engine.layout import (
    LINE_HEIGHT,
    estimate_wrap_lines,
    measure_text_block,
    role_font_prefs,
)

DENSITY_HEADLINE_RATIO = {
    "MINIMAL": 0.078,
    "LOW": 0.068,
    "MEDIUM": 0.058,
    "DATA_RICH": 0.046,
    "sparse": 0.068,
    "moderate": 0.058,
    "dense": 0.046,
}

FORMAT_HEADLINE_SCALE = {
    "square": 1.0,
    "portrait": 0.96,
    "story": 0.88,
    "reelsCover": 0.88,
    "landscape": 0.92,
}

# Minimum readable sizes — reduce density before dropping below these.
MIN_READABLE = {
    "square": {"headline": 28, "body": 15, "eyebrow": 12, "brand": 11, "cta": 13, "custom": 14},
    "portrait": {"headline": 26, "body": 15, "eyebrow": 12, "brand": 11, "cta": 13, "custom": 14},
    "story": {"headline": 32, "body": 16, "eyebrow": 13, "brand": 12, "cta": 14, "custom": 15},
    "reelsCover": {"headline": 32, "body": 16, "eyebrow": 13, "brand": 12, "cta": 14, "custom": 15},
    "landscape": {"headline": 26, "body": 15, "eyebrow": 12, "brand": 11, "cta": 13, "custom": 14},
}

PROPER_NOUN_LOCKS = (
    "the temple",
    "columbia heights",
    "washington",
    "investhome",
)


def min_readable_size(role: str, format_preset: str) -> int:
    table = MIN_READABLE.get(format_preset, MIN_READABLE["square"])
    return int(table.get(role, table.get("custom", 14)))


def hierarchy_font_prefs(
    role: str,
    canvas_w: int,
    *,
    density: str = "LOW",
    format_preset: str = "square",
    composition: str = "",
) -> dict[str, int]:
    base = role_font_prefs(role, canvas_w)
    if role != "headline":
        if role == "body":
            scale = 0.9 if density in {"MINIMAL", "LOW", "sparse"} else 1.0
            preferred = max(base["min"], int(round(base["preferred"] * scale)))
            return {**base, "preferred": min(base["max"], preferred)}
        if role == "eyebrow":
            return {**base, "preferred": min(16, max(11, base["preferred"]))}
        return base
    ratio = DENSITY_HEADLINE_RATIO.get(density, 0.062)
    fmt = FORMAT_HEADLINE_SCALE.get(format_preset, 1.0)
    if composition in {"CENTER_STATEMENT", "IMAGE_DOMINANT"}:
        ratio = max(ratio, 0.07)
    if composition == "DATA_GRID":
        ratio = min(ratio, 0.05)
    preferred = max(base["min"], int(round(canvas_w * ratio * fmt)))
    max_size = 92 if composition in {"CENTER_STATEMENT", "IMAGE_DOMINANT", "STATEMENT_LAYOUT", "LUXURY_BRAND"} else base["max"]
    min_size = min_readable_size("headline", format_preset)
    return {
        "preferred": min(max_size, max(min_size, preferred)),
        "min": min_size,
        "max": max_size,
    }


def _protect_proper_nouns(text: str) -> str:
    """Keep locked phrases on one line so wraps never split 'The Temple' into 'The / formu'."""
    raw = text or ""
    locked = raw
    for phrase in PROPER_NOUN_LOCKS:
        pattern = re.compile(re.escape(phrase), re.I)
        locked = pattern.sub(lambda m: m.group(0).replace(" ", "\u00a0"), locked)
    return locked


def _restore_nbsp(text: str) -> str:
    return (text or "").replace("\u00a0", " ")


def prevent_orphan_words(text: str, *, max_width: int = 0, font_size: int = 0) -> str:
    """Avoid a single short word stranded on the last line of a headline."""
    raw = _restore_nbsp((text or "").strip())
    words = [w for w in re.split(r"\s+", raw.replace("\n", " ")) if w]
    if len(words) < 4:
        return raw
    if max_width > 0 and font_size > 0:
        protected = _protect_proper_nouns(raw.replace("\n", " "))
        lines = estimate_wrap_lines(protected, font_size, max_width, bold=True)
        lines = [_restore_nbsp(line) for line in lines]
        if len(lines) >= 2 and len(lines[-1].split()) == 1:
            return " ".join(words[:-2]) + "\n" + " ".join(words[-2:])
        if len(lines) >= 2 and len(lines[-1]) <= 4:
            return " ".join(words[:-2]) + "\n" + " ".join(words[-2:])
    if "\n" in raw:
        last_line = raw.split("\n")[-1].split()
        if len(last_line) == 1 or (last_line and len(last_line[-1]) <= 3):
            return " ".join(words[:-2]) + "\n" + " ".join(words[-2:])
        return raw
    last = words[-1]
    if len(last) <= 3 or last.lower() in {"the", "and", "for", "with", "from"}:
        words[-2] = f"{words[-2]}\n{words[-1]}"
        words.pop()
        return " ".join(words)
    return raw


def intentional_headline_breaks(
    text: str,
    *,
    composition: str,
    max_width: int,
    font_size: int,
) -> str:
    """Break when composition warrants — never force a two-line template."""
    raw = (text or "").strip()
    if not raw or "\n" in raw:
        return prevent_orphan_words(raw, max_width=max_width, font_size=font_size)
    words = [w for w in re.split(r"\s+", raw) if w]
    if len(words) < 3:
        return raw
    lines = estimate_wrap_lines(raw, font_size, max_width, bold=True)
    if composition in {
        "CENTER_STATEMENT",
        "IMAGE_DOMINANT",
        "TOP_LEFT_EDITORIAL",
        "ASYMMETRIC_EDITORIAL",
        "BOTTOM_LEFT_EDITORIAL",
        "STATEMENT_LAYOUT",
        "EDITORIAL_HERO",
        "LUXURY_BRAND",
        "LIFESTYLE_EDITORIAL",
    }:
        if 4 <= len(words) <= 8 and len(lines) == 1 and len(raw) >= 22:
            mid = len(words) // 2
            # Prefer breaking after a short function word.
            for idx in (mid, mid - 1, mid + 1):
                if 1 <= idx < len(words) - 1:
                    left = " ".join(words[:idx])
                    right = " ".join(words[idx:])
                    if 2 <= len(left.split()) and len(right.split()) >= 1:
                        return prevent_orphan_words(
                            f"{left}\n{right}", max_width=max_width, font_size=font_size
                        )
        if len(lines) >= 2:
            return prevent_orphan_words(raw, max_width=max_width, font_size=font_size)
    return prevent_orphan_words(raw, max_width=max_width, font_size=font_size)


def headline_max_lines(composition: str, text: str) -> int:
    if "\n" in (text or ""):
        return max(2, min(3, (text or "").count("\n") + 1))
    if composition in {"CENTER_STATEMENT", "IMAGE_DOMINANT", "TOP_LEFT_EDITORIAL"}:
        return 2
    if composition == "DATA_GRID":
        return 2
    return 2 if len(text or "") > 26 else 1


def fits_without_clip(
    text: str,
    *,
    font_size: int,
    width: int,
    height: int,
    bold: bool,
    max_lines: int,
) -> bool:
    lines, measured, _ = measure_text_block(text, font_size, width, bold=bold)
    if lines > max_lines:
        return False
    return measured <= height + int(round(font_size * 0.15))


def apply_headline_typography(
    text: str,
    *,
    canvas_w: int,
    width: int,
    max_height: int,
    density: str,
    format_preset: str,
    composition: str,
) -> tuple[str, int, int]:
    prefs = hierarchy_font_prefs(
        "headline",
        canvas_w,
        density=density,
        format_preset=format_preset,
        composition=composition,
    )
    font = prefs["preferred"]
    composed = intentional_headline_breaks(
        text, composition=composition, max_width=width, font_size=font
    )
    max_lines = headline_max_lines(composition, composed)
    while font >= prefs["min"]:
        if fits_without_clip(
            composed,
            font_size=font,
            width=width,
            height=max_height,
            bold=True,
            max_lines=max_lines,
        ):
            _, height, _ = measure_text_block(composed, font, width, bold=True)
            return composed, font, max(int(round(font * LINE_HEIGHT)), height)
        font -= 2
    _, height, _ = measure_text_block(composed, prefs["min"], width, bold=True)
    return composed, prefs["min"], min(max_height, max(height, int(round(prefs["min"] * LINE_HEIGHT))))
