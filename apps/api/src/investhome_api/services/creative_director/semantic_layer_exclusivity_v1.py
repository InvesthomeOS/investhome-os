"""Semantic layer exclusivity for format adaptation.

Every semantic role may render exactly once. Source-position typography that
was captured inside a photo crop is obsolete and must be removed before composite.
Preserved from Stage 4.0 Story tests. Mandatory for PremiumFormatRecomposerV1.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Iterable

from PIL import Image, ImageFilter

FINAL_SEMANTIC_ROLES = ("PROJECT_PHOTO", "HEADLINE", "BODY_COPY", "HIGHLIGHT", "LOGO")


def is_gold(r: int, g: int, b: int) -> bool:
    return r > 148 and 108 < g < 214 and b < 155 and r > b + 22


def is_typography(r: int, g: int, b: int, *, min_lum: int = 198) -> bool:
    lum = (r + g + b) / 3.0
    sat = max(r, g, b) - min(r, g, b)
    return is_gold(r, g, b) or (lum >= min_lum and sat < 60)


def _frac_contains(box: dict[str, float], fx: float, fy: float, *, pad: float = 0.012) -> bool:
    return (
        box["x"] - pad <= fx <= box["x"] + box["w"] + pad
        and box["y"] - pad <= fy <= box["y"] + box["h"] + pad
    )


def strip_source_typography_from_photo(
    original: Image.Image,
    photo: Image.Image,
    photo_box: dict[str, float],
    type_boxes: Iterable[dict[str, float]],
    navy: tuple[int, int, int],
) -> Image.Image:
    """Erase source-position type that rode along inside the PROJECT_PHOTO crop.

    Architecture pixels stay. White/gold glyphs that belong to HEADLINE / BODY /
    HIGHLIGHT / LOGO are replaced with the designed navy so the photo remains
    one opaque object and those roles cannot render a second time.
    """
    photo = photo.convert("RGBA")
    src = original.convert("RGB")
    ow, oh = original.size
    pw, ph = photo.size
    crop_x = photo_box["x"] * ow
    crop_y = photo_box["y"] * oh
    crop_w = photo_box["w"] * ow
    crop_h = photo_box["h"] * oh
    boxes = [box for box in type_boxes if box]
    pix = photo.load()
    src_px = src.load()
    nr, ng, nb = navy
    mask = Image.new("L", (pw, ph), 0)
    mp = mask.load()
    for y in range(ph):
        for x in range(pw):
            sx = int(crop_x + (x + 0.5) * crop_w / max(1, pw))
            sy = int(crop_y + (y + 0.5) * crop_h / max(1, ph))
            if not (0 <= sx < ow and 0 <= sy < oh):
                continue
            fx, fy = sx / ow, sy / oh
            if not any(_frac_contains(box, fx, fy) for box in boxes):
                continue
            r, g, b, a = pix[x, y]
            sr, sg, sb = src_px[sx, sy]
            if is_typography(r, g, b, min_lum=170) or is_typography(sr, sg, sb, min_lum=170):
                mp[x, y] = 255
            elif fy >= 0.42:
                # Body / highlight / logo field is navy. Never keep source glyphs here.
                mp[x, y] = 255
    # Swallow anti-aliased glyph halos so source letters cannot remain as ghosts.
    mask = mask.filter(ImageFilter.MaxFilter(9))
    mp = mask.load()
    for y in range(ph):
        for x in range(pw):
            if mp[x, y] == 0:
                continue
            sx = int(crop_x + (x + 0.5) * crop_w / max(1, pw))
            sy = int(crop_y + (y + 0.5) * crop_h / max(1, ph))
            if not (0 <= sx < ow and 0 <= sy < oh):
                continue
            fx, fy = sx / ow, sy / oh
            if not any(_frac_contains(box, fx, fy, pad=0.02) for box in boxes):
                continue
            pix[x, y] = (nr, ng, nb, 255)
    return photo


def _placement_rect(placement: dict[str, Any]) -> tuple[int, int, int, int]:
    x, y = placement["xy"]
    w, h = placement["size"]
    return (int(x), int(y), int(x + w), int(y + h))


def _centroid_in_rects(cx: float, cy: float, rects: list[tuple[int, int, int, int]], *, pad: int = 16) -> bool:
    for x0, y0, x1, y1 in rects:
        if x0 - pad <= cx <= x1 + pad and y0 - pad <= cy <= y1 + pad:
            return True
    return False


def orphan_text_fragment_count(
    story: Image.Image,
    type_placements: dict[str, dict[str, Any]],
    navy: tuple[int, int, int],
    *,
    photo_placement: dict[str, Any] | None = None,
    min_pixels: int = 140,
    max_pixels: int = 8000,
) -> int:
    """Count type-like blobs that are not inside the final active type rects.

    Photographic highlights inside PROJECT_PHOTO are ignored, except in the
    right overlap band where source typography used to leak into the photo crop.
    """
    rgb = story.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    nr, ng, nb = navy
    rects = [_placement_rect(item) for item in type_placements.values()]
    photo_rect = _placement_rect(photo_placement) if photo_placement else None
    seen = [[False] * w for _ in range(h)]
    orphans = 0
    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                continue
            r, g, b = px[x, y]
            if abs(r - nr) <= 28 and abs(g - ng) <= 28 and abs(b - nb) <= 28:
                seen[y][x] = True
                continue
            if not is_typography(r, g, b, min_lum=210):
                continue
            q = deque([(x, y)])
            seen[y][x] = True
            n = 0
            sx = sy = 0
            while q:
                cx, cy = q.popleft()
                n += 1
                sx += cx
                sy += cy
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < w and 0 <= ny < h) or seen[ny][nx]:
                        continue
                    rr, gg, bb = px[nx, ny]
                    if is_typography(rr, gg, bb, min_lum=210):
                        seen[ny][nx] = True
                        q.append((nx, ny))
                    else:
                        seen[ny][nx] = True
            if n < min_pixels or n > max_pixels:
                continue
            cx, cy = sx / n, sy / n
            if _centroid_in_rects(cx, cy, rects):
                continue
            if photo_rect is not None and _centroid_in_rects(cx, cy, [photo_rect], pad=0):
                continue
            orphans += 1
    return orphans


def validate_semantic_exclusivity(
    *,
    story: Image.Image,
    placements: dict[str, dict[str, Any]],
    navy: tuple[int, int, int],
    photo_pastes: int,
    layer_roles: list[str],
) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    for role in layer_roles:
        role_counts[role] = role_counts.get(role, 0) + 1
    duplication = sum(max(0, count - 1) for count in role_counts.values())
    type_placements = {
        key: placements[key]
        for key in ("HEADLINE", "SUBHEAD", "LASTLINE", "HIGHLIGHT", "LOGO")
        if key in placements
    }
    orphans = orphan_text_fragment_count(
        story,
        type_placements,
        navy,
        photo_placement=placements.get("PHOTO"),
    )
    photo_objects = int(photo_pastes)
    if photo_objects != 1:
        duplication += 1
    if orphans:
        duplication += orphans
    report = {
        "SEMANTIC_LAYER_DUPLICATION_COUNT": duplication,
        "ORPHAN_TEXT_FRAGMENT_COUNT": orphans,
        "SOURCE_TYPE_LEAKAGE": orphans,
        "PHOTO_OBJECT_COUNT": photo_objects,
        "layer_roles": layer_roles,
        "role_counts": role_counts,
        "pass": duplication == 0 and orphans == 0 and photo_objects == 1,
    }
    return report


def refuse_if_unclean(report: dict[str, Any]) -> None:
    if not report.get("pass"):
        raise RuntimeError(
            "PREMIUM_FORMAT_RENDER_BUG_REMAINS "
            f"duplication={report.get('SEMANTIC_LAYER_DUPLICATION_COUNT')} "
            f"orphans={report.get('ORPHAN_TEXT_FRAGMENT_COUNT')} "
            f"photos={report.get('PHOTO_OBJECT_COUNT')}"
        )
