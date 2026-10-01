"""Generic editorial rendering tools for AI art-direction execution.

These are compositor capabilities, not templates and not Temple-specific coordinates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from investhome_api.services.gpt_image_design.compose import (
    _SERIF_BOLD,
    _SERIF_REGULAR,
    _SANS_BOLD,
    _SANS_REGULAR,
    logo_to_rgba,
    resolve_turkish_font,
)
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage


def inspect_font_inventory() -> dict[str, Any]:
    """Report fonts actually present. Do not claim a premium face that is missing."""
    groups = {
        "serif_bold": list(_SERIF_BOLD),
        "serif_regular": list(_SERIF_REGULAR),
        "sans_bold": list(_SANS_BOLD),
        "sans_regular": list(_SANS_REGULAR),
    }
    present: dict[str, list[str]] = {}
    chosen: dict[str, str | None] = {}
    for name, paths in groups.items():
        found = [p for p in paths if Path(p).is_file()]
        present[name] = found
        chosen[name] = found[0] if found else None
    display = chosen.get("serif_bold") or chosen.get("serif_regular") or chosen.get("sans_bold")
    supporting = chosen.get("sans_regular") or chosen.get("sans_bold")
    return {
        "present": present,
        "display_face": display,
        "supporting_face": supporting,
        "premium_foundry_face": False,
        "limitation": (
            "Container inventory is Liberation/DejaVu (and Windows Georgia if present). "
            "No licensed display foundry typeface is installed."
        ),
    }


def _hex_rgba(color: str | None, alpha: int = 255) -> tuple[int, int, int, int]:
    raw = (color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return (255, 255, 255, alpha)
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), max(0, min(255, alpha)))
    except ValueError:
        return (255, 255, 255, alpha)


def _clamp_box(box: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    w, h = size
    x0 = max(0, min(w, x0))
    x1 = max(0, min(w, x1))
    y0 = max(0, min(h, y0))
    y1 = max(0, min(h, y1))
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return x0, y0, x1, y1


def feathered_rect_mask(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    *,
    feather: float = 0.45,
) -> Image.Image:
    """Soft-edged rectangle. Not a hard panel."""
    w, h = size
    x0, y0, x1, y1 = _clamp_box(box, size)
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    inner = Image.new("L", (bw, bh), 255)
    fx = max(1, int(bw * max(0.08, min(0.85, feather))))
    fy = max(1, int(bh * max(0.08, min(0.85, feather))))
    for i in range(fx):
        a = int(255 * (i / fx))
        ImageDraw.Draw(inner).line((i, 0, i, bh), fill=a)
        ImageDraw.Draw(inner).line((bw - 1 - i, 0, bw - 1 - i, bh), fill=a)
    for i in range(fy):
        a = int(255 * (i / fy))
        ImageDraw.Draw(inner).line((0, i, bw, i), fill=min(inner.getpixel((min(bw // 2, bw - 1), i)), a))
        ImageDraw.Draw(inner).line((0, bh - 1 - i, bw, bh - 1 - i), fill=a)
    inner = inner.filter(ImageFilter.GaussianBlur(radius=max(6, min(fx, fy) * 0.35)))
    mask = Image.new("L", (w, h), 0)
    mask.paste(inner, (x0, y0))
    return mask


def apply_feathered_gradient_field(
    image: Image.Image,
    *,
    side: str,
    color: str,
    width_frac: float,
    max_alpha: float,
    feather: float,
) -> Image.Image:
    """Edge tonal field that dissolves into the photograph. Not an opaque rectangle."""
    im = image.convert("RGBA")
    w, h = im.size
    span = int(w * max(0.18, min(0.48, width_frac)))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rgb = _hex_rgba(color, 255)[:3]
    pixels = overlay.load()
    power = 1.35 + (1.0 - max(0.2, min(0.9, feather)))
    if side in {"left", "right"}:
        for x in range(span):
            t = x / max(span - 1, 1)
            if side == "right":
                t = 1.0 - (x / max(span - 1, 1))
                px = w - span + x
            else:
                px = x
            alpha = int(255 * max_alpha * ((1.0 - t) ** power))
            if alpha <= 0:
                continue
            for y in range(h):
                pixels[px, y] = (*rgb, alpha)
    elif side == "top":
        span_h = int(h * max(0.16, min(0.42, width_frac)))
        for y in range(span_h):
            t = y / max(span_h - 1, 1)
            alpha = int(255 * max_alpha * ((1.0 - t) ** power))
            if alpha <= 0:
                continue
            for x in range(w):
                pixels[x, y] = (*rgb, alpha)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(8, int(min(w, h) * 0.03))))
    return Image.alpha_composite(im, overlay)


def apply_local_blur_field(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: float = 10.0,
    strength: float = 0.4,
    feather: float = 0.5,
) -> Image.Image:
    im = image.convert("RGBA")
    blurred = im.filter(ImageFilter.GaussianBlur(radius=max(2.0, radius)))
    mask = feathered_rect_mask(im.size, box, feather=feather)
    mask = mask.point(lambda p: int(p * max(0.0, min(1.0, strength))))
    return Image.composite(blurred, im, mask)


def apply_local_tonal_field(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    color: str,
    max_alpha: float,
    feather: float = 0.55,
) -> Image.Image:
    im = image.convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    fill = _hex_rgba(color, int(255 * max(0.0, min(0.55, max_alpha))))
    x0, y0, x1, y1 = _clamp_box(box, im.size)
    ImageDraw.Draw(overlay).rectangle((x0, y0, x1, y1), fill=fill)
    mask = feathered_rect_mask(im.size, (x0, y0, x1, y1), feather=feather)
    overlay.putalpha(mask.point(lambda p: int(p * fill[3] / 255)))
    return Image.alpha_composite(im, overlay)


def apply_logo_ground(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    color: str = "#F4EFE6",
    max_alpha: float = 0.28,
) -> Image.Image:
    pad = 18
    x0, y0, x1, y1 = box
    return apply_local_tonal_field(
        image,
        (x0 - pad, y0 - pad, x1 + pad, y1 + pad),
        color=color,
        max_alpha=max_alpha,
        feather=0.72,
    )


def draw_rule(
    image: Image.Image,
    *,
    x: int,
    y: int,
    length: int,
    color: str,
    width: int = 1,
    vertical: bool = False,
) -> Image.Image:
    im = image.convert("RGBA")
    draw = ImageDraw.Draw(im)
    fill = _hex_rgba(color, 210)
    if vertical:
        draw.line((x, y, x, y + length), fill=fill, width=max(1, width))
    else:
        draw.line((x, y, x + length, y), fill=fill, width=max(1, width))
    return im


def draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.ImageFont,
    xy: tuple[int, int],
    fill: tuple[int, int, int, int],
    tracking_em: float = 0.0,
    align: str = "left",
    max_width: int | None = None,
) -> tuple[int, int]:
    if not text:
        return 0, 0
    size = max(8, int(getattr(font, "size", 24) or 24))
    extra = tracking_em * size
    widths = []
    for ch in text:
        bbox = font.getbbox(ch)
        widths.append(max(1, bbox[2] - bbox[0]))
    total = int(sum(widths) + extra * max(0, len(text) - 1))
    x, y = xy
    if align == "center" and max_width:
        x = x + max(0, (max_width - total) // 2)
    elif align == "right" and max_width:
        x = x + max(0, max_width - total)
    cursor = x
    for ch, cw in zip(text, widths, strict=False):
        draw.text((int(cursor), y), ch, font=font, fill=fill, anchor="lt")
        cursor += cw + extra
    ascent, descent = font.getmetrics()
    return total, max(1, ascent + descent)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def chan(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    l1, l2 = relative_luminance(a), relative_luminance(b)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


def region_mean_rgb(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    x0, y0, x1, y1 = _clamp_box(box, image.size)
    crop = image.convert("RGB").crop((x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)))
    small = crop.resize((16, 16), Image.Resampling.BOX)
    pixels = list(small.getdata())
    n = max(1, len(pixels))
    return (
        int(sum(p[0] for p in pixels) / n),
        int(sum(p[1] for p in pixels) / n),
        int(sum(p[2] for p in pixels) / n),
    )


def boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int], margin: int = 0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + margin <= bx0 or bx1 + margin <= ax0 or ay1 + margin <= by0 or by1 + margin <= ay0
    )


def overlap_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)


def paste_logo(
    image: Image.Image,
    logo: ResolvedSourceImage,
    box: tuple[int, int, int, int],
) -> tuple[Image.Image, dict[str, Any]]:
    im = image.convert("RGBA")
    x0, y0, x1, y1 = _clamp_box(box, im.size)
    rgba = logo_to_rgba(logo.image_bytes, logo.filename, logo.content_type)
    if rgba is None:
        return im, {"placed": False, "reason": "unreadable"}
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    src = rgba.convert("RGBA")
    bbox = src.getbbox()
    if bbox:
        src = src.crop(bbox)
    scale = min(bw / max(src.width, 1), bh / max(src.height, 1))
    nw = max(1, int(round(src.width * scale)))
    nh = max(1, int(round(src.height * scale)))
    fitted = src.resize((nw, nh), Image.Resampling.LANCZOS)
    im.alpha_composite(fitted, (x0, y0))
    return im, {"placed": True, "x": x0, "y": y0, "width": nw, "height": nh, "asset_id": str(logo.asset_id)}


def opaque_panel_coverage(image: Image.Image, original: Image.Image, alpha_threshold: int = 140) -> float:
    """Share of pixels that look like a hard overlay rather than a dissolve."""
    a = image.convert("RGB").resize((64, 80), Image.Resampling.BOX)
    b = original.convert("RGB").resize((64, 80), Image.Resampling.BOX)
    pa, pb = list(a.getdata()), list(b.getdata())
    hard = 0
    for ca, cb in zip(pa, pb, strict=False):
        delta = abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]) + abs(ca[2] - cb[2])
        if delta > alpha_threshold:
            hard += 1
    return hard / max(len(pa), 1)
