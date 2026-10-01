"""CreativeCollisionEngineV1 — actual rendered geometry vs occupancy silhouette."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.structured_typography_compositor_v2 import _overlap_px


def _px(item: dict[str, Any] | None) -> tuple[int, int, int, int] | None:
    if not item:
        return None
    raw = item.get("px")
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        return tuple(int(v) for v in raw)
    return None


def hard_pixels_in_box(mask: Image.Image, box: tuple[int, int, int, int], *, threshold: int = 160) -> int:
    x0, y0, x1, y1 = box
    pad = 3
    x0, y0, x1, y1 = x0 + pad, y0 + pad, x1 - pad, y1 - pad
    w, h = mask.size
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return 0
    crop = mask.convert("L").crop((x0, y0, x1, y1))
    # Downsample so this is deterministic and fast.
    sample = crop.resize((max(1, crop.size[0] // 4), max(1, crop.size[1] // 4)), Image.Resampling.BOX)
    hist = sample.histogram()
    return int(sum(hist[threshold:]))


def box_hits_hard(mask: Image.Image, box: tuple[int, int, int, int], *, min_pixels: int = 14) -> bool:
    return hard_pixels_in_box(mask, box) >= min_pixels


def objects_hit_hard_occupancy(objects: dict[str, dict[str, Any]], occupancy_l: Image.Image) -> bool:
    mask = occupancy_l.convert("L")
    for role, item in objects.items():
        if role == "project_logo":
            continue
        px = _px(item)
        if px and box_hits_hard(mask, px):
            return True
    return False


def box_hits_canvas_edge(box: tuple[int, int, int, int], size: tuple[int, int], *, margin: float = 0.028) -> bool:
    w, h = size
    mx, my = int(margin * w), int(margin * h)
    return box[0] < mx or box[1] < my or box[2] > w - mx or box[3] > h - int(margin * 0.6 * h)


def evaluate_collisions(
    *,
    objects: dict[str, dict[str, Any]],
    occupancy: dict[str, Any],
    size: tuple[int, int],
    family_allows_architecture_text: bool = False,
) -> dict[str, Any]:
    hard = (occupancy.get("layers") or {}).get("collision_core") or (occupancy.get("layers") or {}).get("hard_protected")
    street = (occupancy.get("layers") or {}).get("street")
    hits: list[str] = []
    details: list[dict[str, Any]] = []
    boxes = {role: _px(item) for role, item in objects.items()}
    if isinstance(hard, Image.Image):
        for role, box in boxes.items():
            if not box:
                continue
            if role != "project_logo" and box_hits_hard(hard, box):
                if not (family_allows_architecture_text and role in {"discount_label"}):
                    hits.append(f"{role}_vs_protected_architecture")
                    details.append({"role": role, "vs": "hard_protected", "pixels": hard_pixels_in_box(hard, box)})
            if role == "project_logo" and box_hits_hard(hard, box, min_pixels=12):
                hits.append("logo_vs_protected_architecture")
    headline = boxes.get("headline")
    logo = boxes.get("project_logo")
    if headline and logo and _overlap_px(headline, logo):
        hits.append("headline_vs_logo")
    price = boxes.get("price")
    if headline and price and _overlap_px(headline, price):
        hits.append("headline_vs_price")
    for role, box in boxes.items():
        if box and box_hits_canvas_edge(box, size):
            hits.append(f"{role}_vs_canvas_edge")
    cta = boxes.get("cta")
    if cta and isinstance(street, Image.Image) and box_hits_hard(street, cta, min_pixels=10):
        hits.append("cta_vs_noisy_street")
    # Internal type overlaps except the designed commercial pair.
    commercial = [boxes.get("price"), boxes.get("discount"), boxes.get("discount_label")]
    for role in ("headline", "unit_type", "cta"):
        a = boxes.get(role)
        if not a:
            continue
        for other, b in boxes.items():
            if other == role or not b or other == "project_logo":
                continue
            if role in {"headline"} and other in {"unit_type", "price", "discount", "discount_label", "cta"}:
                if _overlap_px(a, b):
                    hits.append(f"{role}_vs_{other}")
            if role == "cta" and other in {"headline", "price"} and _overlap_px(a, b):
                hits.append(f"{role}_vs_{other}")
    _ = commercial
    unique = sorted(set(hits))
    return {
        "schema": "CreativeCollisionEngineV1",
        "hits": unique,
        "details": details,
        "pass": not unique,
        "recompose_required": bool(unique),
        "geometry": "occupancy_silhouette",
        "note": "SPIRE rectangles are not collision geometry.",
    }


def render_collision_proof(
    photo: Image.Image,
    occupancy: dict[str, Any],
    objects_by_key: list[tuple[str, dict[str, dict[str, Any]]]],
) -> Image.Image:
    canvas = Image.new("RGB", (1680, 620), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "COLLISION PROOF  —  rendered type vs HARD occupancy, not the fat SPIRE box", fill=(201, 168, 92))
    x = 24
    hard = (occupancy.get("layers") or {}).get("hard_protected")
    for key, objects in objects_by_key:
        tile = photo.convert("RGB").resize((360, 450), Image.Resampling.LANCZOS)
        td = ImageDraw.Draw(tile)
        sx, sy = 360 / photo.size[0], 450 / photo.size[1]
        if isinstance(hard, Image.Image):
            red = Image.new("RGB", tile.size, (200, 40, 40))
            m = hard.resize(tile.size, Image.Resampling.BILINEAR).point(lambda v: 90 if v > 40 else 0)
            tile = Image.composite(red, tile, m)
            td = ImageDraw.Draw(tile)
        for role, item in objects.items():
            px = _px(item)
            if not px:
                continue
            box = (int(px[0] * sx), int(px[1] * sy), int(px[2] * sx), int(px[3] * sy))
            color = (80, 220, 140) if role == "project_logo" else (240, 230, 180)
            td.rectangle(box, outline=color, width=2)
        canvas.paste(tile, (x, 50))
        draw.text((x, 510), key, fill=(236, 230, 218))
        x += 380
    return canvas
