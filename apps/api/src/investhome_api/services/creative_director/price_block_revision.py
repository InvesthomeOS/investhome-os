"""PRICE_BLOCK_ONLY revision — parse NL and locally edit the price zone.

Never regenerates the full finished_ad. Baked prices are patched only inside
the detected price bbox; unmentioned pixels must stay identical.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, status

from investhome_api.schemas.creative_director import RevisionOperation


_AMOUNT_RE = re.compile(
    r"(\d{1,3}(?:[.\s]\d{3})+|\d{3,})(?:\s*(?:USD|\$))?",
    re.IGNORECASE,
)
_GOLD = (196, 163, 90)
_WHITE = (245, 241, 234)
_LABEL = (232, 224, 210)


def _normalize_tr(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def format_tr_usd(amount: int) -> str:
    raw = f"{amount:,}".replace(",", ".")
    return f"{raw} USD"


def parse_tr_amount(token: str) -> int | None:
    digits = re.sub(r"[^\d]", "", token or "")
    if not digits:
        return None
    try:
        value = int(digits)
    except ValueError:
        return None
    if value < 1000 or value > 99_999_999:
        return None
    return value


@dataclass
class PriceBlockIntent:
    list_amount: int
    launch_amount: int
    savings_amount: int
    list_strikethrough: bool = True
    list_label: str = "LİSTE FİYATI"
    launch_label: str = "LANSMAN FİYATI"
    savings_label: str = "KAZANCINIZ"
    scope: str = "PRICE_BLOCK_ONLY"
    raw_amounts: list[int] = field(default_factory=list)

    def operations(self) -> list[RevisionOperation]:
        ops = [
            RevisionOperation(
                target="price",
                action="replace_text",
                element_id="old-price",
                **{"from": None, "to": format_tr_usd(self.list_amount)},
                note="strikethrough list price",
                priority="exact_numeric",
                semantic_target="old_price",
            ),
            RevisionOperation(
                target="price",
                action="replace_text",
                element_id="new-price",
                **{"to": format_tr_usd(self.launch_amount)},
                note="launch price",
                priority="exact_numeric",
                semantic_target="new_price",
            ),
            RevisionOperation(
                target="price",
                action="replace_text",
                element_id="savings-price",
                **{"to": format_tr_usd(self.savings_amount)},
                note="savings under launch price",
                priority="exact_numeric",
                semantic_target="price",
            ),
        ]
        return ops

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "old_price": format_tr_usd(self.list_amount),
            "old_price_strikethrough": self.list_strikethrough,
            "new_price": format_tr_usd(self.launch_amount),
            "new_price_label": self.launch_label,
            "savings": format_tr_usd(self.savings_amount),
            "savings_label": self.savings_label,
            "list_label": self.list_label,
        }


def parse_price_block(instruction: str) -> PriceBlockIntent | None:
    """Semantic price-block intent from natural Turkish. None if not this command."""
    raw = instruction or ""
    low = _normalize_tr(raw)
    if not any(tok in low for tok in ("fiyat", "usd", "lansman", "kazanc")):
        return None
    if not any(tok in low for tok in ("üzerini çiz", "ustunu ciz", "üstü çiz", "strikethrough", "liste")):
        if "lansman fiyat" not in low and "kazanc" not in low:
            return None
    amounts: list[int] = []
    for match in _AMOUNT_RE.finditer(raw):
        value = parse_tr_amount(match.group(1))
        if value is not None and value not in amounts:
            amounts.append(value)
    if len(amounts) < 2:
        return None
    list_amount = amounts[0]
    launch_amount = amounts[1]
    savings_amount = amounts[2] if len(amounts) >= 3 else max(0, list_amount - launch_amount)
    strikethrough = any(
        tok in low
        for tok in ("üzerini çiz", "ustunu ciz", "üstü çiz", "ustu ciz", "strikethrough", "çiz")
    )
    return PriceBlockIntent(
        list_amount=list_amount,
        launch_amount=launch_amount,
        savings_amount=savings_amount,
        list_strikethrough=strikethrough or True,
        raw_amounts=amounts,
    )


def is_baked_price_ad(ctx: dict[str, Any] | None) -> bool:
    """Finished-ad raster is the visual source — price glyphs live in pixels."""
    ctx = ctx or {}
    if ctx.get("golden_native_v1") is True:
        return False
    mode = str(ctx.get("production_mode") or "")
    if mode in {"golden_native_v1", "editable_finished_ad"}:
        spec = ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else {}
        ids = {
            str(el.get("id") or "").lower()
            for el in (spec.get("elements") or [])
            if isinstance(el, dict)
        }
        if "old-price" in ids and "new-price" in ids:
            return False
    return True


def _load_font(size: int, *, bold: bool = False, serif: bool = False):
    from PIL import ImageFont

    if serif:
        names = (
            "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf",
            "LiberationSerif-Bold.ttf" if bold else "LiberationSerif-Regular.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        )
    else:
        names = (
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
        )
    roots = (
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/truetype/liberation/",
        "/usr/share/fonts/TTF/",
    )
    for root in roots:
        for name in names:
            try:
                return ImageFont.truetype(f"{root}{name}", size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _spec_price_box(spec: dict[str, Any] | None, intent: PriceBlockIntent) -> tuple[int, int, int, int] | None:
    if not isinstance(spec, dict):
        return None
    hits: list[tuple[int, int, int, int]] = []
    needles = (
        str(intent.list_amount),
        format_tr_usd(intent.list_amount),
        "675.000",
        "liste",
        "fiyat",
    )
    for el in spec.get("elements") or []:
        if not isinstance(el, dict):
            continue
        content = str(el.get("content") or "").lower()
        eid = str(el.get("id") or "").lower()
        role = str(el.get("role") or "").lower()
        if not any(n.lower() in content or n.lower() in eid or n.lower() in role for n in needles):
            if eid not in {"old-price", "new-price", "price-frame"} and "price" not in role:
                continue
        x = int(el.get("x") or 0)
        y = int(el.get("y") or 0)
        w = int(el.get("width") or 0)
        h = int(el.get("height") or 0)
        if w > 8 and h > 8:
            hits.append((x, y, x + w, y + h))
    if not hits:
        return None
    x0 = min(b[0] for b in hits)
    y0 = min(b[1] for b in hits)
    x1 = max(b[2] for b in hits)
    y1 = max(b[3] for b in hits)
    return x0, y0, x1, y1


def locate_price_zone(
    image: Any,
    *,
    spec: dict[str, Any] | None,
    intent: PriceBlockIntent,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    """Return (draw_box, glyph_box). Knockout stays on glyphs; typeset uses draw_box."""
    from PIL import Image

    assert isinstance(image, Image.Image)
    width, height = image.size
    spec_box = _spec_price_box(spec, intent)
    if spec_box is not None:
        sx0, sy0, sx1, sy1 = spec_box
        if (sx1 - sx0) * (sy1 - sy0) > 0.12 * width * height:
            spec_box = None

    rgb = image.convert("RGB")
    pixels = rgb.load()
    y0 = int(height * 0.87)
    y1 = int(height * 0.995)
    x0 = int(width * 0.28)
    x1 = int(width * 0.62)
    xs: list[int] = []
    ys: list[int] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = pixels[x, y]
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            if luma < 220:
                continue
            if _is_gold(r, g, b):
                continue
            xs.append(x)
            ys.append(y)
    if len(xs) < 80:
        if spec_box is not None:
            found = spec_box
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "PRICE_BLOCK_ONLY fail-closed — baked list price zone not found.",
                    "scope": "PRICE_BLOCK_ONLY",
                },
            )
    else:
        found = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        if spec_box is not None:
            found = (
                min(found[0], spec_box[0]),
                min(found[1], spec_box[1]),
                max(found[2], spec_box[2]),
                max(found[3], spec_box[3]),
            )
    gx0 = max(0, found[0] - 16)
    gy0 = max(0, found[1] - 56)
    gx1 = min(width, found[2] + 16)
    gy1 = min(height, found[3] + 18)
    glyph = (gx0, gy0, gx1, gy1)
    return _expand_zone(found, width, height), glyph


def _expand_zone(
    box: tuple[int, int, int, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    pad_x = max(8, int(width * 0.012))
    found_h = max(8, y1 - y0)
    needed_h = max(found_h + 48, int(height * 0.195))
    y1 = min(height - 1, y1 + 36)
    y0 = max(int(height * 0.74), y1 - needed_h)
    x0 = max(int(width * 0.26), x0 - pad_x)
    x1 = min(int(width * 0.66), x1 + pad_x)
    area = (x1 - x0) * (y1 - y0)
    if area > 0.22 * width * height:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "PRICE_BLOCK_ONLY fail-closed — price zone too large to edit safely.",
                "scope": "PRICE_BLOCK_ONLY",
            },
        )
    return x0, y0, x1, y1


def _is_gold(r: int, g: int, b: int) -> bool:
    return r > 180 and g > 140 and b < 140


def _knockout_bright_glyphs(image: Any, box: tuple[int, int, int, int]) -> None:
    """Inpaint the original glyph rectangle from left/right floor — not a flat plate."""
    x0, y0, x1, y1 = box
    px = image.load()
    width, height = image.size

    def _pix(x: int, y: int):
        x = min(max(0, x), width - 1)
        y = min(max(0, y), height - 1)
        return px[x, y]

    for y in range(y0, y1):
        left = _pix(x0 - 3, y)
        right = _pix(x1 + 2, y)
        span = max(1, x1 - x0)
        lr, lg, lb = left[:3]
        rr, rg, rb = right[:3]
        for x in range(x0, x1):
            t = (x - x0) / span
            fill = (
                int(lr * (1 - t) + rr * t),
                int(lg * (1 - t) + rg * t),
                int(lb * (1 - t) + rb * t),
            )
            pix = px[x, y]
            if len(pix) == 4:
                px[x, y] = fill + (pix[3],)
            else:
                px[x, y] = fill


def _draw_price_block(image: Any, box: tuple[int, int, int, int], intent: PriceBlockIntent) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box
    zone_w = max(8, x1 - x0)
    zone_h = max(8, y1 - y0)
    cx = (x0 + x1) // 2
    max_text_w = zone_w - 10

    def _fonts(scale: float):
        return (
            _load_font(max(12, int(zone_h * 0.068 * scale))),
            _load_font(max(16, int(zone_h * 0.118 * scale)), bold=True, serif=True),
            _load_font(max(18, int(zone_h * 0.145 * scale)), bold=True, serif=True),
            _load_font(max(16, int(zone_h * 0.118 * scale)), bold=True, serif=True),
        )

    scale = 1.0
    lines: list[tuple[str, Any, tuple[int, int, int], bool]] = []
    heights: list[int] = []
    for _ in range(8):
        label_font, list_font, launch_font, savings_font = _fonts(scale)
        lines = [
            (intent.list_label, label_font, _LABEL, False),
            (format_tr_usd(intent.list_amount), list_font, _WHITE, intent.list_strikethrough),
            (intent.launch_label, label_font, _LABEL, False),
            (format_tr_usd(intent.launch_amount), launch_font, _GOLD, False),
            (intent.savings_label, label_font, _LABEL, False),
            (format_tr_usd(intent.savings_amount), savings_font, _GOLD, False),
        ]
        heights = []
        too_wide = False
        for text, font, _color, _strike in lines:
            bbox = draw.textbbox((0, 0), text, font=font)
            heights.append(bbox[3] - bbox[1])
            if (bbox[2] - bbox[0]) > max_text_w:
                too_wide = True
        gap = max(2, int(zone_h * 0.014 * scale))
        total_h = sum(heights) + gap * (len(lines) - 1)
        if not too_wide and total_h <= zone_h - 8:
            break
        scale *= 0.88

    gap = max(2, int(zone_h * 0.014 * scale))
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = y0 + max(4, (zone_h - total_h) // 2)
    for (text, font, color, strike), h in zip(lines, heights, strict=True):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = max(x0 + 2, min(cx - tw // 2, x1 - tw - 2))
        draw.text((x, y), text, font=font, fill=color)
        if strike:
            ly = y + int(h * 0.55)
            x_line0 = max(x0 + 2, x - 2)
            x_line1 = min(x1 - 3, x + tw + 2)
            draw.line((x_line0, ly, x_line1, ly), fill=color, width=max(2, h // 10))
        y += h + gap


def apply_local_price_zone(
    source_bytes: bytes,
    *,
    spec: dict[str, Any] | None,
    intent: PriceBlockIntent,
) -> tuple[bytes, dict[str, Any]]:
    """Patch only the price zone. Outside pixels must remain identical."""
    from PIL import Image

    original = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    working = original.copy()
    draw_box, glyph_box = locate_price_zone(working, spec=spec, intent=intent)
    x0, y0, x1, y1 = draw_box
    crop = working.crop((x0, y0, x1, y1))
    gx0 = max(0, glyph_box[0] - x0)
    gy0 = max(0, glyph_box[1] - y0)
    gx1 = min(crop.size[0], glyph_box[2] - x0)
    gy1 = min(crop.size[1], glyph_box[3] - y0)
    if gx1 > gx0 + 4 and gy1 > gy0 + 4:
        _knockout_bright_glyphs(crop, (gx0, gy0, gx1, gy1))
    _draw_price_block(crop, (0, 0, crop.size[0], crop.size[1]), intent)
    working.paste(crop, (x0, y0))

    orig_px = original.load()
    new_px = working.load()
    width, height = original.size
    leaked = 0
    for y in range(height):
        for x in range(width):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            if orig_px[x, y] != new_px[x, y]:
                leaked += 1
    if leaked > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "PRICE_BLOCK_ONLY fail-closed — edit leaked outside the price zone. "
                    "Existing finished-ad was not persisted."
                ),
                "leaked_pixels": leaked,
                "scope": "PRICE_BLOCK_ONLY",
            },
        )
    out = io.BytesIO()
    working.convert("RGB").save(out, format="PNG", optimize=True)
    trace = {
        "scope": "PRICE_BLOCK_ONLY",
        "baked": True,
        "zone": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "glyph_zone": {"x0": glyph_box[0], "y0": glyph_box[1], "x1": glyph_box[2], "y1": glyph_box[3]},
        "provider_calls": 0,
        "method": "local_price_zone_knockout_typeset",
        "intent": intent.to_dict(),
    }
    return out.getvalue(), trace
