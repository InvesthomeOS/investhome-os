"""ReferenceCompositionMapV1 — measurable geometry from Grade-A reference pixels."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageStat


def _cov(mask: Image.Image, threshold: int = 80) -> float:
    hist = mask.convert("L").histogram()
    total = max(1, sum(hist))
    return round(sum(hist[threshold:]) / total, 4)


def _centroid(mask: Image.Image, threshold: int = 80) -> tuple[float, float]:
    small = mask.convert("L").resize((40, 50), Image.Resampling.BOX)
    px = small.load()
    acc_x = acc_y = wsum = 0.0
    for y in range(small.height):
        for x in range(small.width):
            v = int(px[x, y])
            if v < threshold:
                continue
            acc_x += x * v
            acc_y += y * v
            wsum += v
    if wsum <= 0:
        return 0.5, 0.5
    return round(acc_x / wsum / max(small.width - 1, 1), 4), round(acc_y / wsum / max(small.height - 1, 1), 4)


def _components(mask: Image.Image, *, threshold: int = 90, grid: tuple[int, int] = (24, 30)) -> list[dict[str, float]]:
    gw, gh = grid
    small = mask.convert("L").resize((gw, gh), Image.Resampling.BOX)
    px = small.load()
    seen = [[False] * gw for _ in range(gh)]
    groups: list[dict[str, float]] = []
    for y in range(gh):
        for x in range(gw):
            if seen[y][x] or int(px[x, y]) < threshold:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            cells: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < gw and 0 <= ny < gh and not seen[ny][nx] and int(px[nx, ny]) >= threshold:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if len(cells) < 4:
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            groups.append(
                {
                    "x": round(min(xs) / gw, 4),
                    "y": round(min(ys) / gh, 4),
                    "w": round((max(xs) + 1 - min(xs)) / gw, 4),
                    "h": round((max(ys) + 1 - min(ys)) / gh, 4),
                    "area": round(len(cells) / float(gw * gh), 4),
                    "cx": round((min(xs) + max(xs)) / 2 / gw, 4),
                    "cy": round((min(ys) + max(ys)) / 2 / gh, 4),
                }
            )
    groups.sort(key=lambda g: (-g["area"], g["y"], g["x"]))
    return groups[:8]


def _region_density(mask: Image.Image) -> dict[str, float]:
    w, h = mask.size
    out = {}
    labels = (("tl", 0, 0), ("tr", 1, 0), ("ml", 0, 1), ("mr", 1, 1), ("bl", 0, 2), ("br", 1, 2))
    for name, gx, gy in labels:
        box = (int(gx * w / 2), int(gy * h / 3), int((gx + 1) * w / 2), int((gy + 1) * h / 3))
        out[name] = _cov(mask.crop(box), 70)
    return out


def build_reference_composition_map(image: Image.Image, *, filename: str) -> dict[str, Any]:
    src = image.convert("RGB")
    w, h = src.size
    gray = src.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    dark = gray.point(lambda v: 255 if v < 70 else 0)
    bright_flat = gray.point(lambda v: 255 if v > 200 else 0)
    type_like = edges.point(lambda v: 255 if v > 40 else 0)
    photo_mass = edges.point(lambda v: 180 if 18 < v < 90 else 0)
    graphic_mass = Image.composite(dark, bright_flat.point(lambda v: 120 if v else 0), dark)
    vx = sum(ImageStat.Stat(edges.crop((x, 0, x + 1, h))).sum[0] for x in range(0, w, max(1, w // 32)))
    hy = sum(ImageStat.Stat(edges.crop((0, y, w, y + 1))).sum[0] for y in range(0, h, max(1, h // 40)))
    axis = "vertical" if vx >= hy else "horizontal"
    groups = _components(type_like)
    named = []
    roles = ("PRIMARY", "SECONDARY", "TERTIARY")
    for i, group in enumerate(groups[:3]):
        named.append({**group, "role": roles[i]})
    photo_c = _centroid(photo_mass, 40)
    type_c = _centroid(type_like, 40)
    graphic_c = _centroid(graphic_mass, 40)
    overall = (
        round((photo_c[0] * 0.5 + type_c[0] * 0.3 + graphic_c[0] * 0.2), 4),
        round((photo_c[1] * 0.5 + type_c[1] * 0.3 + graphic_c[1] * 0.2), 4),
    )
    distances = {}
    if len(named) >= 2:
        distances["primary_secondary"] = round(((named[0]["cx"] - named[1]["cx"]) ** 2 + (named[0]["cy"] - named[1]["cy"]) ** 2) ** 0.5, 4)
    if len(named) >= 3:
        distances["primary_tertiary"] = round(((named[0]["cx"] - named[2]["cx"]) ** 2 + (named[0]["cy"] - named[2]["cy"]) ** 2) ** 0.5, 4)
        distances["secondary_tertiary"] = round(((named[1]["cx"] - named[2]["cx"]) ** 2 + (named[1]["cy"] - named[2]["cy"]) ** 2) ** 0.5, 4)
    aligned = False
    if len(named) >= 2:
        aligned = abs(named[0]["x"] - named[1]["x"]) < 0.06 or abs(named[0]["cx"] - named[1]["cx"]) < 0.08
    reading = sorted(named, key=lambda g: (g["y"], g["x"]))
    return {
        "schema": "ReferenceCompositionMapV1",
        "filename": filename,
        "size": [w, h],
        "dominant_compositional_axis": axis,
        "visual_mass_map": _region_density(edges),
        "primary_secondary_tertiary_groups": named,
        "group_bounding_boxes": named,
        "relative_scale_ratios": {
            "primary_area": named[0]["area"] if named else 0,
            "secondary_over_primary": round((named[1]["area"] / max(named[0]["area"], 1e-6)), 4) if len(named) > 1 else 0,
        },
        "distance_related": distances.get("primary_secondary", 0),
        "distance_unrelated": distances.get("primary_tertiary", 0),
        "alignment_relationships": {"primary_secondary_edge_aligned": aligned},
        "overlap_relationships": {"primary_secondary_overlap": False},
        "edge_anchors": {
            "left": named[0]["x"] < 0.08 if named else False,
            "top": named[0]["y"] < 0.08 if named else False,
            "right": (named[0]["x"] + named[0]["w"]) > 0.88 if named else False,
            "bottom": (named[0]["y"] + named[0]["h"]) > 0.88 if named else False,
        },
        "typographic_mass": _cov(type_like, 40),
        "photo_mass": _cov(photo_mass, 40),
        "graphic_mass": _cov(graphic_mass, 80),
        "commercial_lockup_mass": named[1]["area"] if len(named) > 1 else 0,
        "logo_relationship": "secondary_group" if len(named) > 1 else "unresolved",
        "cta_relationship": "tertiary_or_closure" if len(named) > 2 else "unresolved",
        "negative_space_function": "protects_photo_mass" if photo_c[1] > 0.35 else "sky_pause",
        "visual_flow": "top_to_bottom" if axis == "vertical" else "left_to_right",
        "reading_order": [g["role"] for g in reading],
        "contrast_map": _region_density(type_like),
        "tonal_field_structure": {"dark_coverage": _cov(dark, 128), "bright_coverage": _cov(bright_flat, 128)},
        "decorative_graphic_role": "tonal_field_or_rule",
        "photo_type_interaction": "type_on_tonal_support" if _cov(dark, 128) > 0.12 else "type_on_photo",
        "information_density_by_region": _region_density(type_like),
        "center_of_visual_gravity": {"photo": photo_c, "type": type_c, "graphic": graphic_c, "overall": overall},
    }


def overlay_composition_map(image: Image.Image, cmap: dict[str, Any]) -> Image.Image:
    im = image.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    w, h = im.size
    colors = {"PRIMARY": (220, 180, 70), "SECONDARY": (80, 180, 220), "TERTIARY": (180, 90, 200)}
    for group in cmap.get("primary_secondary_tertiary_groups") or []:
        x0 = int(float(group["x"]) * w)
        y0 = int(float(group["y"]) * h)
        x1 = x0 + int(float(group["w"]) * w)
        y1 = y0 + int(float(group["h"]) * h)
        color = colors.get(str(group.get("role")), (200, 200, 200))
        draw.rectangle((x0, y0, x1, y1), outline=color, width=max(2, w // 400))
        draw.text((x0 + 4, y0 + 4), str(group.get("role") or ""), fill=color)
    g = (cmap.get("center_of_visual_gravity") or {}).get("overall") or [0.5, 0.5]
    cx, cy = int(float(g[0]) * w), int(float(g[1]) * h)
    draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 80, 80))
    return im
