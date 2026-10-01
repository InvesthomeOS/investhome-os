"""GraphicFieldEngineV1 — structured tonal fields, rules, guides. No panels/cards/pills."""

from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

FORBIDDEN = ("panel", "card", "pill", "button", "ui", "ornament")

CONCEPT3_PRIMITIVES = (
    "elliptical_arc",
    "partial_ellipse",
    "radial_tick_sequence",
    "curved_rule",
    "gradient_field",
    "feathered_tonal_field",
    "photo_overlay_field",
    "precision_marker",
    "editorial_measurement_marks",
    "curved_aperture",
    "masked_photo_overlay",
    "tonal_transition",
)

_TONAL_KINDS = {
    "linear_tonal_field",
    "feathered_image_transition",
    "depth_field",
    "directional_fade",
    "edge_gradient",
    "controlled_darkening_field",
    "transparent_editorial_plane",
    "gradient_field",
    "feathered_tonal_field",
    "photo_overlay_field",
    "curved_aperture",
    "masked_photo_overlay",
    "tonal_transition",
}

_VECTOR_KINDS = {
    "architectural_guide_line",
    "fine_rule",
    "elliptical_arc",
    "partial_ellipse",
    "radial_tick_sequence",
    "curved_rule",
    "precision_marker",
    "editorial_measurement_marks",
}


def field_spec(
    kind: str,
    *,
    axis: str = "vertical",
    start: float = 0.0,
    end: float = 0.28,
    strength: float = 0.42,
    role: str = "tonal_support",
    **extra: Any,
) -> dict[str, Any]:
    tokens = kind.lower().replace("-", "_").split("_")
    if any(token in FORBIDDEN for token in tokens):
        raise ValueError(f"forbidden graphic kind: {kind}")
    spec = {
        "kind": kind,
        "axis": axis,
        "start": start,
        "end": end,
        "strength": strength,
        "role": role,
        "editable": True,
        "giant_panel": False,
        "card": False,
        "pill": False,
    }
    spec.update(extra)
    return spec


def plan_fields(mode: str) -> list[dict[str, Any]]:
    if mode == "GROUND_PLANE":
        return [
            field_spec("linear_tonal_field", start=0.0, end=0.16, strength=0.32, role="sky_readability"),
            field_spec("linear_tonal_field", start=0.70, end=1.0, strength=0.40, role="ground_offer_plane"),
            field_spec("feathered_image_transition", start=0.62, end=0.74, strength=0.18, role="horizon_blend"),
            field_spec("architectural_guide_line", axis="vertical", start=0.18, end=0.72, strength=0.12, role="headline_to_ground"),
            field_spec("fine_rule", start=0.72, end=0.74, strength=0.2, role="lockup_bind"),
            field_spec("depth_field", start=0.0, end=1.0, strength=0.08, role="photographic_depth"),
        ]
    if mode == "CORNER_INGRESS":
        return [
            field_spec("directional_fade", axis="horizontal", start=0.0, end=0.42, strength=0.38, role="corner_ingress"),
            field_spec("edge_gradient", axis="vertical", start=0.0, end=0.22, strength=0.2, role="sky_edge"),
            field_spec("controlled_darkening_field", start=0.86, end=1.0, strength=0.28, role="base_weight"),
            field_spec("architectural_guide_line", axis="vertical", start=0.32, end=0.58, strength=0.1, role="architecture_tension"),
        ]
    return [
        field_spec("linear_tonal_field", start=0.0, end=0.30, strength=0.42, role="sky_veil"),
        field_spec("directional_fade", start=0.84, end=1.0, strength=0.28, role="ground_fade"),
        field_spec("feathered_image_transition", start=0.24, end=0.38, strength=0.16, role="veil_to_architecture"),
        field_spec("architectural_guide_line", axis="vertical", start=0.34, end=0.62, strength=0.1, role="spire_tension"),
        field_spec("transparent_editorial_plane", start=0.04, end=0.46, strength=0.12, role="type_support"),
        field_spec("depth_field", start=0.0, end=1.0, strength=0.08, role="photographic_depth"),
    ]


def apply_graphic_fields(photo: Image.Image, occupancy: dict[str, Any], mode: str) -> dict[str, Any]:
    from investhome_api.services.creative_director.creative_family_adapter import _ramp_horizontal, _ramp_vertical, _union_l

    src = photo.convert("RGB")
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    if not isinstance(hard, Image.Image):
        hard = Image.new("L", src.size, 0)
    size = src.size
    fields = plan_fields(mode)
    mask = Image.new("L", size, 0)
    for spec in fields:
        if spec["kind"] in {"architectural_guide_line", "fine_rule"}:
            continue
        if spec["axis"] == "horizontal":
            ramp = _ramp_horizontal(size, spec["start"], spec["end"], int(255 * spec["strength"]), 0)
        else:
            ramp = _ramp_vertical(size, spec["start"], spec["end"], int(255 * spec["strength"]), 0)
        mask = _union_l(mask, ramp)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=30))
    protect = hard.convert("L").filter(ImageFilter.GaussianBlur(radius=10)).point(lambda v: int(255 - v * 0.88))
    mask = ImageChops.multiply(mask, protect)
    darken = 0.40 if mode != "GROUND_PLANE" else 0.38
    dark = ImageEnhance.Brightness(src).enhance(darken)
    fielded = Image.composite(dark, src, mask)
    guides = [spec for spec in fields if spec["kind"] in {"architectural_guide_line", "fine_rule"}]
    return {
        "schema": "GraphicFieldEngineV1",
        "image": fielded,
        "mask": mask,
        "fields": fields,
        "guides": guides,
        "mode": mode,
        "geometry_modified": False,
        "forbidden": list(FORBIDDEN),
    }


def draw_guides(draw, *, canvas: tuple[int, int], guides: list[dict[str, Any]], color: tuple[int, int, int]) -> None:
    w, h = canvas
    for spec in guides:
        if spec["kind"] != "architectural_guide_line":
            continue
        if spec["axis"] == "vertical":
            x = int(w * float(spec["start"]))
            draw.line((x, int(h * 0.12), x, int(h * 0.72)), fill=(*color, 40) if False else color, width=1)
        else:
            y = int(h * float(spec["start"]))
            draw.line((int(w * 0.06), y, int(w * 0.94), y), fill=color, width=1)


def _smooth_series(values: list[float], span: int = 7) -> list[float]:
    if not values:
        return values
    out = list(values)
    n = len(out)
    radius = max(1, span // 2)
    for _ in range(2):
        nxt = out[:]
        for i in range(n):
            sl = out[max(0, i - radius) : min(n, i + radius + 1)]
            nxt[i] = sum(sl) / len(sl)
        out = nxt
    return out


def _polyline_xs(spec: dict[str, Any], height: int) -> list[float]:
    raw = spec.get("polyline_x") or spec.get("boundary_x") or []
    if not raw:
        start = float(spec.get("start") or 0.0)
        end = float(spec.get("end") or 0.42)
        return [start + (end - start) * (i / max(height - 1, 1)) for i in range(height)]
    pts = [max(0.0, min(1.0, float(v))) for v in raw]
    if len(pts) == height:
        return pts
    out = []
    last = max(len(pts) - 1, 1)
    for y in range(height):
        t = y / max(height - 1, 1) * last
        i = int(t)
        f = t - i
        a = pts[min(i, last)]
        b = pts[min(i + 1, last)]
        out.append(a + (b - a) * f)
    return out


def _mask_from_polyline(size: tuple[int, int], spec: dict[str, Any]) -> Image.Image:
    w, h = size
    xs = _polyline_xs(spec, h)
    strength = float(spec.get("strength") or 0.62)
    feather = float(spec.get("feather") or 0.10)
    peak = int(255 * max(0.05, min(1.0, strength)))
    feather_px = max(10, int(w * feather))
    sw, sh = max(64, w // 4), max(80, h // 4)
    small = Image.new("L", (sw, sh), 0)
    px = small.load()
    scale_x = w / sw
    scale_y = h / sh
    bleed = float(spec.get("bleed") or 0.28)
    for sy in range(sh):
        edge = xs[min(h - 1, int(sy * scale_y))] * sw
        for sx in range(sw):
            d = edge - sx
            if d >= feather_px / scale_x:
                px[sx, sy] = peak
            elif d > 0:
                px[sx, sy] = int(peak * (d * scale_x / feather_px))
            elif d > -feather_px / scale_x:
                px[sx, sy] = int(peak * bleed * (1.0 + d * scale_x / feather_px))
    mask = small.resize(size, Image.Resampling.BICUBIC)
    blur = int(spec.get("blur") or 22)
    return mask.filter(ImageFilter.GaussianBlur(radius=blur))


def _mask_from_ellipse(size: tuple[int, int], spec: dict[str, Any]) -> Image.Image:
    w, h = size
    cx = float(spec.get("cx") or 0.92) * w
    cy = float(spec.get("cy") or 0.50) * h
    rx = float(spec.get("rx") or 0.62) * w
    ry = float(spec.get("ry") or 0.88) * h
    strength = float(spec.get("strength") or 0.62)
    feather = float(spec.get("feather") or 0.08)
    peak = int(255 * max(0.05, min(1.0, strength)))
    feather_px = max(8, int(w * feather))
    sw, sh = max(64, w // 4), max(80, h // 4)
    small = Image.new("L", (sw, sh), 0)
    px = small.load()
    scx, scy = cx * sw / w, cy * sh / h
    srx, sry = max(1.0, rx * sw / w), max(1.0, ry * sh / h)
    sfeather = feather_px * sw / w
    for sy in range(sh):
        ny = (sy - scy) / sry
        if abs(ny) >= 1:
            edge = sw
        else:
            edge = scx - srx * math.sqrt(max(0.0, 1.0 - ny * ny))
        for sx in range(sw):
            d = edge - sx
            if d >= sfeather:
                px[sx, sy] = peak
            elif d > 0:
                px[sx, sy] = int(peak * (d / sfeather))
            elif d > -sfeather:
                px[sx, sy] = int(peak * 0.28 * (1.0 + d / sfeather))
    mask = small.resize(size, Image.Resampling.BICUBIC)
    return mask.filter(ImageFilter.GaussianBlur(radius=int(spec.get("blur") or 20)))


def _tonal_mask(size: tuple[int, int], spec: dict[str, Any]) -> Image.Image:
    kind = str(spec.get("kind") or "")
    if spec.get("polyline_x") or spec.get("boundary_x"):
        return _mask_from_polyline(size, spec)
    if kind in {
        "photo_overlay_field",
        "feathered_tonal_field",
        "gradient_field",
        "curved_aperture",
        "masked_photo_overlay",
        "tonal_transition",
    } and spec.get("cx") is not None:
        return _mask_from_ellipse(size, spec)
    from investhome_api.services.creative_director.creative_family_adapter import _ramp_horizontal, _ramp_vertical

    start = float(spec.get("start") or 0.0)
    end = float(spec.get("end") or 0.42)
    peak = int(255 * float(spec.get("strength") or 0.42))
    if spec.get("axis") == "horizontal":
        return _ramp_horizontal(size, start, end, peak, 0)
    return _ramp_vertical(size, start, end, peak, 0)


def apply_structured_field_specs(
    photo: Image.Image,
    occupancy: dict[str, Any] | None,
    fields: list[dict[str, Any]],
    *,
    charcoal: tuple[int, int, int] = (26, 28, 32),
    darken: float = 0.42,
    charcoal_mix: float = 0.38,
    protect_architecture: bool = False,
) -> dict[str, Any]:
    """Apply an explicit field list. Does not classify SKY_VEIL / sidebar modes."""
    src = photo.convert("RGB")
    size = src.size
    mask = Image.new("L", size, 0)
    from investhome_api.services.creative_director.creative_family_adapter import _union_l

    tonal = []
    vectors = []
    for spec in fields:
        kind = str(spec.get("kind") or "")
        tokens = kind.lower().replace("-", "_").split("_")
        if any(token in FORBIDDEN for token in tokens):
            raise ValueError(f"forbidden graphic kind: {kind}")
        if kind in _VECTOR_KINDS:
            vectors.append(spec)
            continue
        if kind not in _TONAL_KINDS and not (spec.get("polyline_x") or spec.get("boundary_x")):
            continue
        tonal.append(spec)
        mask = _union_l(mask, _tonal_mask(size, spec))
    if protect_architecture:
        hard = (occupancy or {}).get("layers", {}).get("hard_protected") if occupancy else None
        if isinstance(hard, Image.Image):
            protect = hard.convert("L").filter(ImageFilter.GaussianBlur(radius=10)).point(lambda v: int(255 - v * 0.88))
            mask = ImageChops.multiply(mask, protect)
    dark = ImageEnhance.Brightness(src).enhance(max(0.12, min(0.85, darken)))
    tint = Image.new("RGB", size, charcoal)
    mixed = Image.blend(dark, tint, max(0.0, min(1.0, charcoal_mix)))
    fielded = Image.composite(mixed, src, mask)
    return {
        "schema": "GraphicFieldEngineV1",
        "image": fielded,
        "mask": mask,
        "fields": list(fields),
        "guides": vectors,
        "mode": "APPROVED_CONCEPT_3",
        "geometry_modified": False,
        "forbidden": list(FORBIDDEN),
        "classified_as": None,
    }


def _arc_bbox(spec: dict[str, Any], size: tuple[int, int]) -> tuple[int, int, int, int]:
    w, h = size
    cx = float(spec.get("cx") or 0.92) * w
    cy = float(spec.get("cy") or 0.50) * h
    rx = float(spec.get("rx") or 0.62) * w
    ry = float(spec.get("ry") or 0.88) * h
    return (int(cx - rx), int(cy - ry), int(cx + rx), int(cy + ry))


def _polyline_points(spec: dict[str, Any], size: tuple[int, int]) -> list[tuple[int, int]]:
    w, h = size
    xs = spec.get("polyline_x") or spec.get("boundary_x") or []
    if not xs:
        return []
    n = len(xs)
    pts = []
    for i, x in enumerate(xs):
        y = int(h * i / max(n - 1, 1))
        pts.append((int(w * float(x)), y))
    return pts


def render_vector_fields(
    size: tuple[int, int],
    fields: list[dict[str, Any]],
    *,
    gold: tuple[int, int, int] = (201, 168, 92),
    ivory: tuple[int, int, int] = (244, 239, 228),
) -> Image.Image:
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = size
    ga = (*gold, 210)
    gf = (*gold, 90)
    for spec in fields:
        kind = str(spec.get("kind") or "")
        if kind in {"elliptical_arc", "partial_ellipse"}:
            bbox = _arc_bbox(spec, size)
            start = float(spec.get("arc_start") or 95)
            end = float(spec.get("arc_end") or 265)
            width = max(1, int(spec.get("stroke") or 2))
            draw.arc(bbox, start=start, end=end, fill=ga, width=width)
        elif kind == "curved_rule":
            pts = _polyline_points(spec, size)
            if len(pts) >= 2:
                draw.line(pts, fill=ga, width=max(1, int(spec.get("stroke") or 2)), joint="curve")
        elif kind == "radial_tick_sequence":
            pts = _polyline_points(spec, size)
            if len(pts) >= 4:
                count = int(spec.get("ticks") or 14)
                length = float(spec.get("tick_length") or 0.018) * min(w, h)
                step = max(1, (len(pts) - 1) // max(count, 1))
                for i in range(step, len(pts) - step, step):
                    p0, p1 = pts[max(0, i - 2)], pts[min(len(pts) - 1, i + 2)]
                    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                    mag = math.hypot(dx, dy) or 1.0
                    nx, ny = -dy / mag, dx / mag
                    if nx > 0:
                        nx, ny = -nx, -ny
                    inner = 1.0 if (i // step) % 3 else 1.65
                    draw.line(
                        (pts[i][0], pts[i][1], pts[i][0] + nx * length * inner, pts[i][1] + ny * length * inner),
                        fill=ga,
                        width=1,
                    )
                continue
            cx = float(spec.get("cx") or 0.92) * w
            cy = float(spec.get("cy") or 0.50) * h
            rx = float(spec.get("rx") or 0.62) * w
            ry = float(spec.get("ry") or 0.88) * h
            a0 = math.radians(float(spec.get("arc_start") or 110))
            a1 = math.radians(float(spec.get("arc_end") or 250))
            count = int(spec.get("ticks") or 14)
            length = float(spec.get("tick_length") or 0.018) * min(w, h)
            for i in range(count):
                t = i / max(count - 1, 1)
                ang = a0 + (a1 - a0) * t
                x = cx + rx * math.cos(ang)
                y = cy + ry * math.sin(ang)
                nx = rx * math.cos(ang)
                ny = ry * math.sin(ang)
                mag = math.hypot(nx, ny) or 1.0
                ux, uy = nx / mag, ny / mag
                inner = 1.0 if (i % 3) else 1.7
                draw.line(
                    (x - ux * length * 0.15, y - uy * length * 0.15, x + ux * length * inner, y + uy * length * inner),
                    fill=ga,
                    width=1,
                )
        elif kind == "editorial_measurement_marks":
            cx = float(spec.get("cx") or 0.92) * w
            cy = float(spec.get("cy") or 0.50) * h
            rx = float(spec.get("rx") or 0.62) * w
            ry = float(spec.get("ry") or 0.88) * h
            start = float(spec.get("arc_start") or 100)
            end = float(spec.get("arc_end") or 250)
            for scale in (0.82, 0.64, 0.46):
                bbox = (int(cx - rx * scale), int(cy - ry * scale), int(cx + rx * scale), int(cy + ry * scale))
                draw.arc(bbox, start=start, end=end, fill=gf, width=1)
        elif kind == "precision_marker":
            mx = float(spec.get("x") or 0.38) * w
            my = float(spec.get("y") or 0.42) * h
            r = float(spec.get("r") or 0.0065) * min(w, h)
            draw.ellipse((mx - r, my - r, mx + r, my + r), fill=(*ivory, 230), outline=ga, width=1)
    return overlay
