"""CreativeContrastEngineV1 — family-approved fills from measured background luminance."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageStat

from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, INK, IVORY, _hex

MIN_RATIO_DISPLAY = 3.0
MIN_RATIO_SUPPORT = 3.2
MIN_RATIO_DISCOUNT = 3.5


def _rel_lum(rgb: tuple[int, int, int]) -> float:
    def chan(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    lighter = max(_rel_lum(fg), _rel_lum(bg))
    darker = min(_rel_lum(fg), _rel_lum(bg))
    return (lighter + 0.05) / (darker + 0.05)


def sample_background(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    x0, y0, x1, y1 = (int(v) for v in box)
    w, h = image.size
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return (128, 128, 128)
    crop = image.convert("RGB").crop((x0, y0, x1, y1)).resize((24, 16), Image.Resampling.BOX)
    stats = ImageStat.Stat(crop)
    return int(stats.mean[0]), int(stats.mean[1]), int(stats.mean[2])


def approved_fills(family_id: str, bg: tuple[int, int, int], family: dict[str, Any] | None = None) -> dict[str, tuple[int, int, int]]:
    typo = dict((family or {}).get("typography") or {})
    ivory = _hex(str(typo.get("text_hex") or ""), IVORY)
    from investhome_api.services.creative_director.creative_contrast_engine import contrast_ratio as _cr

    gold = _hex(str(typo.get("accent_hex") or ""), GOLD)
    ink = _hex(str(typo.get("ink_hex") or ""), INK)
    luma = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]
    if family_id == "SKY_EDITORIAL":
        fill = ink if luma >= 118 else ivory
        accent = gold if _cr(gold, bg) >= 3.5 else fill
        return {"fill": fill, "accent": accent, "number": fill}
    fill = ivory if luma < 140 else ink
    accent = gold if _cr(gold, bg) >= 3.5 else fill
    return {"fill": fill, "accent": accent, "number": fill}


def evaluate_group(
    image: Image.Image,
    *,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    role: str,
) -> dict[str, Any]:
    bg = sample_background(image, box)
    ratio = round(contrast_ratio(color, bg), 3)
    minimum = MIN_RATIO_DISCOUNT if role in {"discount", "cta"} else MIN_RATIO_SUPPORT if role in {"unit_type", "discount_label"} else MIN_RATIO_DISPLAY
    luma = round(0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2], 1)
    return {
        "role": role,
        "bg": list(bg),
        "bg_luma": luma,
        "fg": list(color),
        "ratio": ratio,
        "minimum": minimum,
        "pass": ratio >= minimum,
    }


def evaluate_objects(
    image: Image.Image,
    objects: dict[str, dict[str, Any]],
    colors: dict[str, tuple[int, int, int]],
) -> dict[str, Any]:
    reports = []
    for role, item in objects.items():
        if role == "project_logo":
            continue
        px = item.get("px")
        if not (isinstance(px, (list, tuple)) and len(px) == 4):
            continue
        color = colors.get(role) or colors.get("fill") or IVORY
        reports.append(evaluate_group(image, box=tuple(int(v) for v in px), color=color, role=role))
    failed = [r["role"] for r in reports if not r["pass"]]
    return {
        "schema": "CreativeContrastEngineV1",
        "groups": reports,
        "failed": failed,
        "pass": not failed,
        "recompose_required": bool(failed),
    }


def solve_family_contrast(
    photo: Image.Image,
    occupancy: dict[str, Any],
    family: dict[str, Any],
    region: dict[str, float],
) -> dict[str, Any]:
    """Solve contrast with family-approved treatments. Not a random text rectangle."""
    from investhome_api.services.creative_director.adaptive_composition_engine import _apply_local_plane, _apply_sky_wash
    from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens

    tokens = execution_tokens(family)
    family_id = str(family.get("family_id") or "")
    w, h = photo.size
    sample = (
        int(float(region.get("x") or 0.08) * w),
        int(float(region.get("y") or 0.06) * h),
        int((float(region.get("x") or 0.08) + min(0.2, float(region.get("w") or 0.2))) * w),
        int((float(region.get("y") or 0.06) + 0.10) * h),
    )
    bg = sample_background(photo, sample)
    luma = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]
    treatments: list[str] = []
    fielded = photo.convert("RGB")
    fills = approved_fills(family_id, bg, family)
    if family_id == "EDITORIAL_DARK_FIELD" and luma > 108:
        fielded = _apply_local_plane(fielded, occupancy, region)
        treatments.append("local_tonal_fade")
        bg = sample_background(fielded, sample)
        fills = approved_fills(family_id, bg, family)
        treatments.append("typography_color_variant")
    elif family_id == "SKY_EDITORIAL" and luma < 118:
        wash = tokens["primary_color"] if False else (232, 226, 214)
        fielded = _apply_sky_wash(fielded, occupancy, wash)
        treatments.append("edge_gradient")
        fills = approved_fills(family_id, sample_background(fielded, sample), family)
    elif family_id == "FULL_FRAME_ARCHITECTURAL_CAMPAIGN":
        from investhome_api.services.creative_director.full_frame_architectural_family import apply_architectural_edge_integration

        edge = apply_architectural_edge_integration(photo, occupancy)
        fielded = edge["image"]
        treatments.extend(list(edge.get("treatments") or []))
        fills = approved_fills(family_id, sample_background(fielded, sample), family)
    elif luma > 140 and family_id != "SKY_EDITORIAL":
        fielded = _apply_local_plane(fielded, occupancy, region)
        treatments.append("controlled_image_darkening")
        fills = approved_fills(family_id, sample_background(fielded, sample), family)
    else:
        treatments.append("typography_color_variant")
    return {"image": fielded, "fills": fills, "treatments": treatments, "bg": list(bg)}


def render_contrast_map(image: Image.Image, report: dict[str, Any], objects: dict[str, dict[str, Any]]) -> Image.Image:
    src = image.convert("RGB").resize((544, 680), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1200, 760), (12, 14, 20))
    canvas.paste(src, (24, 48))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 14), "CONTRAST MAP  —  failure triggers recomposition", fill=(201, 168, 92))
    sx, sy = 544 / image.size[0], 680 / image.size[1]
    by_role = {g["role"]: g for g in report.get("groups") or []}
    for role, item in objects.items():
        px = item.get("px")
        if not (isinstance(px, (list, tuple)) and len(px) == 4):
            continue
        box = (24 + int(px[0] * sx), 48 + int(px[1] * sy), 24 + int(px[2] * sx), 48 + int(px[3] * sy))
        group = by_role.get(role) or {}
        color = (80, 200, 120) if group.get("pass") else (220, 70, 70)
        draw.rectangle(box, outline=color, width=2)
    y = 48
    for group in report.get("groups") or []:
        mark = "PASS" if group.get("pass") else "FAIL"
        draw.text(
            (590, y),
            f"{group.get('role')}  {mark}  {group.get('ratio')}  luma {group.get('bg_luma')}",
            fill=(80, 200, 120) if group.get("pass") else (220, 90, 80),
        )
        y += 28
    return canvas
