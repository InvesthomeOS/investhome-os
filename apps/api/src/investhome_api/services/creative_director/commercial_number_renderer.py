"""CommercialNumberRendererV1 — 675.000 USD and %35 as designed graphic elements."""

from __future__ import annotations

from typing import Any

from PIL import ImageDraw, ImageFont

from investhome_api.services.creative_director.structured_typography_compositor_v2 import _draw_tracked


def split_price(text: str) -> tuple[str, str]:
    raw = (text or "").strip()
    if " " in raw:
        number, currency = raw.rsplit(" ", 1)
        return number, currency
    return raw, ""


def render_price(
    draw: ImageDraw.ImageDraw,
    *,
    origin: tuple[int, int],
    text: str,
    number_font: ImageFont.ImageFont,
    currency_font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    alignment: str,
    tracking: float = 8.0,
    gap: int | None = None,
    parts: dict[str, tuple[int, int, int, int]] | None = None,
) -> tuple[int, int, int, int]:
    number, currency = split_price(text)
    ox, y = origin
    num_box = _draw_tracked(
        draw,
        (ox, y),
        number,
        number_font,
        fill,
        tracking=tracking,
        anchor="rt" if alignment == "right" else "lt",
    )
    if parts is not None:
        parts["number"] = num_box
    if not currency:
        return num_box
    space = int(gap) if gap is not None else max(8, int(getattr(number_font, "size", 32) * 0.18))
    if alignment == "right":
        cur_x = num_box[0] - space
        cur_box = _draw_tracked(draw, (cur_x, num_box[3] - int(getattr(currency_font, "size", 18) * 0.92)), currency, currency_font, fill, tracking=40, anchor="rt")
    else:
        cur_x = num_box[2] + space
        baseline = num_box[3] - int(getattr(currency_font, "size", 18) * 0.88)
        cur_box = _draw_tracked(draw, (cur_x, baseline), currency, currency_font, fill, tracking=32, anchor="lt")
    if parts is not None:
        parts["currency"] = cur_box
    return (min(cur_box[0], num_box[0]), min(cur_box[1], num_box[1]), max(cur_box[2], num_box[2]), max(cur_box[3], num_box[3]))


def render_struck_price(
    draw: ImageDraw.ImageDraw,
    *,
    origin: tuple[int, int],
    text: str,
    number_font: ImageFont.ImageFont,
    currency_font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    strike_fill: tuple[int, int, int],
    alignment: str = "left",
    tracking: float = 6.0,
    gap: int | None = None,
    parts: dict[str, tuple[int, int, int, int]] | None = None,
) -> tuple[int, int, int, int]:
    box = render_price(
        draw,
        origin=origin,
        text=text,
        number_font=number_font,
        currency_font=currency_font,
        fill=fill,
        alignment=alignment,
        tracking=tracking,
        gap=gap,
        parts=parts,
    )
    mid = (box[1] + box[3]) // 2
    pad = 3
    draw.line((box[0] - pad, mid, box[2] + pad, mid), fill=strike_fill, width=2)
    if parts is not None:
        parts["strikethrough"] = (box[0] - pad, mid - 1, box[2] + pad, mid + 1)
    return box


def render_percent(
    draw: ImageDraw.ImageDraw,
    *,
    origin: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    alignment: str,
) -> tuple[int, int, int, int]:
    label = (text or "").strip()
    sign = ""
    digits = label
    if label.startswith("%"):
        sign, digits = "%", label[1:]
    elif label.endswith("%"):
        digits, sign = label[:-1], "%"
    ox, y = origin
    if not sign:
        return _draw_tracked(draw, (ox, y), label, font, fill, tracking=8, anchor="rt" if alignment == "right" else "lt")
    if alignment == "right":
        dig = _draw_tracked(draw, (ox, y), digits, font, fill, tracking=6, anchor="rt")
        sig = _draw_tracked(draw, (dig[0] - 2, y + int(getattr(font, "size", 32) * 0.06)), sign, font, fill, tracking=0, anchor="rt")
        return (min(sig[0], dig[0]), min(sig[1], dig[1]), max(sig[2], dig[2]), max(sig[3], dig[3]))
    sig = _draw_tracked(draw, (ox, y + int(getattr(font, "size", 32) * 0.06)), sign, font, fill, tracking=0, anchor="lt")
    dig = _draw_tracked(draw, (sig[2] + 2, y), digits, font, fill, tracking=6, anchor="lt")
    return (min(sig[0], dig[0]), min(sig[1], dig[1]), max(sig[2], dig[2]), max(sig[3], dig[3]))
