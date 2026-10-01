"""Campaign design-surface primitives.

Capabilities, not templates. Surfaces may dissolve, feather, fade, and mask.
They must not become dashboard panels or opaque navy rectangles.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from investhome_api.services.gpt_image_design.editorial_compose import (
    apply_feathered_gradient_field,
    apply_local_blur_field,
    apply_local_tonal_field,
    apply_logo_ground,
    draw_rule,
    feathered_rect_mask,
)

SURFACE_TYPES = (
    "SOFT_CONTRAST_FIELD",
    "FEATHERED_COLOR_FIELD",
    "MULTI_STOP_GRADIENT",
    "EDITORIAL_SURFACE",
    "TYPOGRAPHIC_GROUND",
    "LOCAL_PHOTO_FADE",
    "SOFT_MASK",
    "RADIAL_MASK",
    "LINEAR_MASK",
    "DECORATIVE_RULE",
    "EDITORIAL_FRAME",
    "LIGHT_ACCENT",
    "SHADOW_FIELD",
    "LOCAL_BLUR_FIELD",
    "LOGO_GROUND",
    "CTA_GROUND",
    "FOREGROUND_GRAPHIC",
    "BACKGROUND_GRAPHIC",
    "COLOR_WASH",
)


def _hex(color: str | None, alpha: int = 255) -> tuple[int, int, int, int]:
    raw = (color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return (255, 255, 255, alpha)
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), max(0, min(255, alpha)))
    except ValueError:
        return (255, 255, 255, alpha)


def box_to_px(box: dict[str, float] | None, canvas: tuple[int, int]) -> tuple[int, int, int, int] | None:
    if not isinstance(box, dict):
        return None
    try:
        x = float(box.get("x", 0))
        y = float(box.get("y", 0))
        w = float(box.get("w", box.get("width", 0)))
        h = float(box.get("h", box.get("height", 0)))
    except (TypeError, ValueError):
        return None
    if w <= 0.01 or h <= 0.01:
        return None
    cw, ch = canvas
    x0 = int(round(max(0.0, min(1.0, x)) * cw))
    y0 = int(round(max(0.0, min(1.0, y)) * ch))
    x1 = int(round(max(0.0, min(1.0, x + w)) * cw))
    y1 = int(round(max(0.0, min(1.0, y + h)) * ch))
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def radial_mask(size: tuple[int, int], box: tuple[int, int, int, int], *, feather: float = 0.55) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    x0, y0, x1, y1 = box
    draw = ImageDraw.Draw(mask)
    draw.ellipse((x0, y0, x1, y1), fill=255)
    radius = max(8, int(min(x1 - x0, y1 - y0) * max(0.12, min(0.8, feather))))
    return mask.filter(ImageFilter.GaussianBlur(radius=radius))


def linear_mask(
    size: tuple[int, int],
    *,
    side: str,
    width_frac: float,
    power: float = 1.6,
) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    pixels = mask.load()
    if side in {"left", "right"}:
        span = max(8, int(w * max(0.12, min(0.55, width_frac))))
        for x in range(span):
            t = x / max(span - 1, 1)
            if side == "right":
                t = 1.0 - t
                px = w - span + x
            else:
                px = x
            a = int(255 * ((1.0 - t) ** power))
            for y in range(h):
                pixels[px, y] = a
    else:
        span = max(8, int(h * max(0.12, min(0.45, width_frac))))
        for y in range(span):
            t = y / max(span - 1, 1)
            if side == "bottom":
                t = 1.0 - t
                py = h - span + y
            else:
                py = y
            a = int(255 * ((1.0 - t) ** power))
            for x in range(w):
                pixels[x, py] = a
    return mask.filter(ImageFilter.GaussianBlur(radius=max(10, int(min(w, h) * 0.03))))


def apply_color_through_mask(
    image: Image.Image,
    mask: Image.Image,
    color: str,
    *,
    max_alpha: float,
) -> Image.Image:
    im = image.convert("RGBA")
    rgb = _hex(color, 255)[:3]
    overlay = Image.new("RGBA", im.size, (*rgb, 0))
    alpha = mask.point(lambda p: int(p * max(0.0, min(0.55, max_alpha))))
    overlay.putalpha(alpha)
    return Image.alpha_composite(im, overlay)


def apply_multi_stop_gradient(
    image: Image.Image,
    *,
    box: tuple[int, int, int, int],
    colors: list[str],
    alphas: list[float],
    direction: str = "vertical",
    feather: float = 0.5,
) -> Image.Image:
    im = image.convert("RGBA")
    x0, y0, x1, y1 = box
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    stops = list(zip(colors, alphas, strict=False)) or [("#0E1420", 0.18)]
    band = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    px = band.load()
    n = max(1, len(stops) - 1)
    for i in range(bw if direction == "horizontal" else bh):
        t = i / max((bw if direction == "horizontal" else bh) - 1, 1)
        idx = min(n - 1, int(t * n)) if n else 0
        local = (t * n) - idx
        c0, a0 = stops[idx]
        c1, a1 = stops[min(idx + 1, len(stops) - 1)]
        r0 = _hex(c0, 255)
        r1 = _hex(c1, 255)
        rgb = tuple(int(r0[k] + (r1[k] - r0[k]) * local) for k in range(3))
        a = int(255 * (a0 + (a1 - a0) * local))
        if direction == "horizontal":
            for y in range(bh):
                px[i, y] = (*rgb, a)
        else:
            for x in range(bw):
                px[x, i] = (*rgb, a)
    mask = feathered_rect_mask((bw, bh), (0, 0, bw, bh), feather=feather)
    r, g, b, a = band.split()
    band = Image.merge("RGBA", (r, g, b, ImageChops_multiply(a, mask)))
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    overlay.paste(band, (x0, y0), band)
    return Image.alpha_composite(im, overlay)


def ImageChops_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops

    return ImageChops.multiply(a, b)


def apply_local_photo_fade(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    darkness: float = 0.28,
    feather: float = 0.62,
) -> Image.Image:
    im = image.convert("RGB")
    darkened = ImageEnhance.Brightness(im).enhance(max(0.55, 1.0 - darkness))
    mask = feathered_rect_mask(im.size, box, feather=feather)
    return Image.composite(darkened, im, mask)


def apply_soft_contrast_field(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    contrast: float = 1.12,
    feather: float = 0.6,
) -> Image.Image:
    im = image.convert("RGB")
    boosted = ImageEnhance.Contrast(im).enhance(contrast)
    mask = feathered_rect_mask(im.size, box, feather=feather)
    return Image.composite(boosted, im, mask)


def apply_editorial_frame(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    color: str = "#C9A85C",
    width: int = 1,
    alpha: float = 0.45,
    inset: int = 0,
) -> Image.Image:
    im = image.convert("RGBA")
    draw = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    x0 += inset
    y0 += inset
    x1 -= inset
    y1 -= inset
    fill = _hex(color, int(255 * max(0.12, min(0.7, alpha))))
    draw.rectangle((x0, y0, x1, y1), outline=fill, width=max(1, width))
    return im


def apply_light_accent(
    image: Image.Image,
    *,
    x: int,
    y: int,
    length: int,
    color: str = "#C9A85C",
    vertical: bool = False,
) -> Image.Image:
    return draw_rule(image, x=x, y=y, length=length, color=color, width=1, vertical=vertical)


def apply_surface(image: Image.Image, spec: dict[str, Any], canvas: tuple[int, int]) -> Image.Image:
    kind = str(spec.get("type") or "").upper()
    box = box_to_px(spec.get("box"), canvas)
    color = str(spec.get("color") or "#0E1420")
    max_alpha = float(spec.get("max_alpha") or 0.22)
    feather = float(spec.get("feather") or 0.58)
    if kind in {"COLOR_WASH", "LINEAR_MASK", "BACKGROUND_GRAPHIC"}:
        side = str(spec.get("side") or "left")
        width_frac = float(spec.get("width_frac") or 0.28)
        mask = linear_mask(canvas, side=side, width_frac=width_frac)
        return apply_color_through_mask(image, mask, color, max_alpha=max_alpha)
    if kind == "RADIAL_MASK":
        if box is None:
            return image
        mask = radial_mask(canvas, box, feather=feather)
        return apply_color_through_mask(image, mask, color, max_alpha=max_alpha)
    if kind in {"FEATHERED_COLOR_FIELD", "EDITORIAL_SURFACE", "TYPOGRAPHIC_GROUND", "SOFT_MASK", "SHADOW_FIELD"}:
        if box is None:
            return image
        return apply_local_tonal_field(image, box, color=color, max_alpha=max_alpha, feather=feather)
    if kind == "SOFT_CONTRAST_FIELD":
        if box is None:
            return image
        return apply_soft_contrast_field(image, box, contrast=float(spec.get("contrast") or 1.1), feather=feather)
    if kind == "LOCAL_PHOTO_FADE":
        if box is None:
            return image
        return apply_local_photo_fade(image, box, darkness=float(spec.get("darkness") or 0.26), feather=feather)
    if kind == "LOCAL_BLUR_FIELD":
        if box is None:
            return image
        return apply_local_blur_field(
            image, box, radius=float(spec.get("radius") or 8), strength=float(spec.get("strength") or 0.35), feather=feather
        )
    if kind == "MULTI_STOP_GRADIENT":
        if box is None:
            return image
        colors = list(spec.get("colors") or [color, "#1A2433"])
        alphas = [float(a) for a in (spec.get("alphas") or [max_alpha, 0.04])]
        return apply_multi_stop_gradient(
            image, box=box, colors=colors, alphas=alphas, direction=str(spec.get("direction") or "vertical"), feather=feather
        )
    if kind == "DECORATIVE_RULE":
        x = int(spec.get("x") or 0)
        y = int(spec.get("y") or 0)
        if spec.get("box") and box:
            x, y = box[0], box[1]
            length = box[2] - box[0] if not spec.get("vertical") else box[3] - box[1]
        else:
            length = int(spec.get("length") or 120)
        return draw_rule(
            image,
            x=x,
            y=y,
            length=length,
            color=str(spec.get("color") or "#C9A85C"),
            width=int(spec.get("width") or 1),
            vertical=bool(spec.get("vertical")),
        )
    if kind == "LIGHT_ACCENT":
        if box is None:
            return image
        return apply_light_accent(image, x=box[0], y=box[1], length=box[2] - box[0], color=str(spec.get("color") or "#C9A85C"))
    if kind == "EDITORIAL_FRAME":
        if box is None:
            return image
        return apply_editorial_frame(image, box, color=str(spec.get("color") or "#C9A85C"), alpha=max_alpha)
    if kind == "LOGO_GROUND":
        if box is None:
            return image
        return apply_logo_ground(image, box, color=str(spec.get("color") or "#F4EFE6"), max_alpha=min(0.28, max_alpha or 0.2))
    if kind in {"CTA_GROUND", "FOREGROUND_GRAPHIC"}:
        if box is None:
            return image
        return apply_local_tonal_field(image, box, color=color, max_alpha=min(0.28, max_alpha), feather=max(0.55, feather))
    if kind == "COLOR_WASH":
        return apply_feathered_gradient_field(
            image,
            side=str(spec.get("side") or "left"),
            color=color,
            width_frac=float(spec.get("width_frac") or 0.3),
            max_alpha=max_alpha,
            feather=feather,
        )
    return image
