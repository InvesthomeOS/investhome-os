"""Phase 10.2 — VISUAL_REPLACE_ONLY on locked Master 03 Looking Chamber.

Replace Day_002 in the existing architectural reveal. Interior, type, logo,
and design geometry stay on the locked parent raster. GPT Image is not used.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import _read_bytes
from investhome_api.services.creative_director.phase9_0_compose import render_pair
from investhome_api.services.creative_director.phase9_1_r1_compose import (
    ARCHITECTURE_GRADE,
    H,
    W,
    interior_mask,
    reveal_mask,
)
from investhome_api.services.creative_director.phase10_0_price_revise import render_pixel_diff
from investhome_api.services.creative_director.phase10_2_parse import OLD_EXTERIOR_ASSET_ID, OLD_EXTERIOR_FILENAME
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

SELECTED_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_009.jpg"
SELECTED_ASSET_ID = "7696df34-0544-44b9-89f5-0d1b2523c412"
SELECTION_REASON = (
    "Monumental street-level view of the Temple spire — the architectural world "
    "a chamber looks toward. Full historic mass and vertical geometry, without "
    "reusing Day_002, Master 01 Day_003, Master 02 Sunset_001, or an aerial."
)

SHORTLIST = (
    ("IH_DC_TMP_001_Render_Exterior_Day_001.jpg", "5d26caf3-c237-4a78-9f3a-91f05dd24fa2", "street monument — considered"),
    ("IH_DC_TMP_001_Render_Exterior_Day_003.jpg", "7346e259-f999-4fbb-a8d5-63708d4e0c81", "Master 01 photo — not reused"),
    ("IH_DC_TMP_001_Render_Exterior_Day_004.jpg", "299bd265-a0ea-486d-866d-1947f103fd57", "aerial — not a chamber view"),
    ("IH_DC_TMP_001_Render_Exterior_Day_007.jpg", "c0afa1bf-b487-410c-be3d-91c31852550d", "aerial mass — not a chamber view"),
    ("IH_DC_TMP_001_Render_Exterior_Day_008.jpg", "2d44757b-079c-4a78-a4a9-5fe6370466c8", "low-angle plaza — runner-up"),
    (SELECTED_FILENAME, SELECTED_ASSET_ID, "SELECTED — monumental street-level spire"),
    ("IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg", "65f68756-a006-43d4-9c86-2c0ec25ad229", "Master 02 dusk — not reused"),
)

MASK_FLOOR = 8
CROP_XS = (0.00, 0.12, 0.24, 0.36, 0.50, 0.64, 0.78)
CROP_YS = (0.10, 0.20, 0.30, 0.42, 0.55)


def architecture_visible_mask() -> Image.Image:
    """Where the locked chamber shows architecture, not interior."""
    rev = reveal_mask()
    inter = interior_mask()
    vis = Image.new("L", (W, H), 0)
    rp, ip, vp = rev.load(), inter.load(), vis.load()
    for y in range(H):
        for x in range(W):
            vp[x, y] = (rp[x, y] * (255 - ip[x, y])) // 255
    return vis


def _luma(pixel: tuple[int, int, int]) -> int:
    return (299 * pixel[0] + 587 * pixel[1] + 114 * pixel[2]) // 1000


def score_reveal_crop(graded: Image.Image, vis: Image.Image) -> dict[str, float]:
    gp, mp = graded.convert("RGB").load(), vis.convert("L").load()
    sky = arch = n = 0
    xs: list[int] = []
    ys: list[int] = []
    for y in range(H):
        for x in range(W):
            if mp[x, y] < 64:
                continue
            n += 1
            r, g, b = gp[x, y]
            lum = _luma((r, g, b))
            if b > r + 12 and lum >= 145:
                sky += 1
            else:
                arch += 1
                xs.append(x)
                ys.append(y)
    n = max(n, 1)
    sky_f = sky / n
    arch_f = arch / n
    cx = (sum(xs) / len(xs) / W) if xs else 0.0
    cy = (sum(ys) / len(ys) / H) if ys else 0.0
    y_min = (min(ys) / H) if ys else 1.0
    y_max = (max(ys) / H) if ys else 0.0
    height = y_max - y_min
    score = (
        arch_f * 2.4
        + max(0.0, cx - 0.52) * 3.0
        + height * 1.2
        + (1.0 - abs(sky_f - 0.26)) * 0.7
        - (1.5 if sky_f > 0.52 else 0.0)
        - (2.0 if cx < 0.54 else 0.0)
        - (1.0 if y_min > 0.18 else 0.0)
    )
    return {
        "score": round(score, 4),
        "sky_in_reveal": round(sky_f, 4),
        "architecture_in_reveal": round(arch_f, 4),
        "centroid_x": round(cx, 4),
        "centroid_y": round(cy, 4),
        "vertical_span": round(height, 4),
    }


def choose_crop(source: Image.Image, vis: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    best: dict[str, Any] | None = None
    best_image: Image.Image | None = None
    tried: list[dict[str, Any]] = []
    for cx in CROP_XS:
        for cy in CROP_YS:
            crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(cx, cy))
            graded = apply_photographic_grade(crop, dict(ARCHITECTURE_GRADE))
            metrics = score_reveal_crop(graded, vis)
            record = {"centering": [cx, cy], "transform": transform, **metrics}
            tried.append(record)
            if best is None or metrics["score"] > best["score"]:
                best = record
                best_image = graded
    if best is None or best_image is None:
        raise RuntimeError("no exterior crop scored inside the locked reveal")
    best["tried_count"] = len(tried)
    best["layout_adjusted"] = best["centering"] != [0.66, 0.28]
    return best_image, best


def composite_reveal(parent: Image.Image, new_arch: Image.Image, vis: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    if parent.size != CANVAS_4X5 or new_arch.size != CANVAS_4X5:
        raise RuntimeError("photo replacement requires locked 4:5 canvas")
    child = parent.convert("RGB").copy()
    cp, np, mp = child.load(), new_arch.convert("RGB").load(), vis.convert("L").load()
    inside = 0
    outside = 0
    max_out = 0
    x0, y0, x1, y1 = vis.getbbox() or (0, 0, W, H)
    for y in range(H):
        for x in range(W):
            m = mp[x, y]
            if m < MASK_FLOOR:
                continue
            t = m / 255.0
            pr, pg, pb = cp[x, y]
            nr, ng, nb = np[x, y]
            cp[x, y] = (
                int(pr * (1.0 - t) + nr * t),
                int(pg * (1.0 - t) + ng * t),
                int(pb * (1.0 - t) + nb * t),
            )
            inside += 1
    # Recount outside precisely against original parent.
    pp = parent.convert("RGB").load()
    outside = 0
    max_out = 0
    sample: list[tuple[int, int]] = []
    for y in range(H):
        for x in range(W):
            if mp[x, y] >= MASK_FLOOR:
                continue
            d = max(abs(pp[x, y][i] - cp[x, y][i]) for i in range(3))
            if d:
                outside += 1
                max_out = max(max_out, d)
                if len(sample) < 8:
                    sample.append((x, y))
    delta = {
        "outside_changed_pixels": outside,
        "inside_changed_pixels": inside,
        "outside_max_channel_delta": max_out,
        "outside_sample": sample,
        "territory": [x0, y0, x1, y1],
        "pass": outside == 0 and max_out == 0,
    }
    return child, delta


def apply_exterior_replacement(parent: Image.Image, source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    vis = architecture_visible_mask()
    graded, crop_meta = choose_crop(source, vis)
    child, delta = composite_reveal(parent, graded, vis)
    box = tuple(delta["territory"])
    meta = {
        "old_asset": OLD_EXTERIOR_ASSET_ID,
        "old_filename": OLD_EXTERIOR_FILENAME,
        "new_asset": SELECTED_ASSET_ID,
        "new_filename": SELECTED_FILENAME,
        "selection_reason": SELECTION_REASON,
        "method": "locked_parent_raster + reveal_mask_composite",
        "territory": list(box),
        "crop": crop_meta,
        "pixel_delta": delta,
        "gpt_image_calls": 0,
        "project_photo_internal_generated_pixels": 0,
        "source": "LOCKED_MASTER_03",
        "interior_unchanged": delta["pass"],
    }
    meta["extras"] = {
        "vis": vis,
        "graded": graded,
        "source": source,
    }
    return child, meta


def render_labeled(image: Image.Image, title: str, size: tuple[int, int] = (1088, 1360)) -> Image.Image:
    canvas = Image.new("RGB", size, (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 36), title, font=_font(22), fill=GOLD)
    tile = image.copy()
    tile.thumbnail((992, 1180), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (48, 90))
    return canvas


def render_shortlist(items: list[tuple[str, Image.Image, bool]]) -> Image.Image:
    cols, rows = 4, 2
    cw, ch = 420, 520
    canvas = Image.new("RGB", (cols * cw + 48, rows * ch + 80), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "03  REAL TEMPLE EXTERIOR SHORTLIST  —  Day_002 excluded", font=_font(18), fill=GOLD)
    for i, (label, image, selected) in enumerate(items[:8]):
        r, c = divmod(i, cols)
        x, y = 24 + c * cw, 56 + r * ch
        tile = image.copy()
        tile.thumbnail((380, 430), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x + 8, y + 28))
        color = GOLD if selected else IVORY
        draw.text((x + 8, y + 6), label[:42], font=_font(14), fill=color)
        if selected:
            draw.rectangle([x, y + 24, x + tile.size[0] + 16, y + tile.size[1] + 32], outline=GOLD, width=3)
    return canvas


def render_crop_plan(source: Image.Image, crop_meta: dict[str, Any], graded: Image.Image, vis: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1760, 1180), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "05  REPLACEMENT CROP PLAN  —  design geometry locked, photo adapts", font=_font(18), fill=GOLD)
    src = source.copy()
    src.thumbnail((820, 980), Image.Resampling.LANCZOS)
    canvas.paste(src.convert("RGB"), (36, 56))
    box = crop_meta.get("transform", {}).get("source_crop") or [0, 0, source.size[0], source.size[1]]
    sx = src.size[0] / max(source.size[0], 1)
    sy = src.size[1] / max(source.size[1], 1)
    rect = [36 + box[0] * sx, 56 + box[1] * sy, 36 + box[2] * sx, 56 + box[3] * sy]
    draw.rectangle(rect, outline=GOLD, width=3)
    reveal = graded.convert("RGB").copy()
    overlay = Image.new("RGBA", reveal.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    mp = vis.convert("L").load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            if 8 <= mp[x, y] < 180:
                od.point((x, y), fill=(232, 196, 120, 90))
    reveal = Image.alpha_composite(reveal.convert("RGBA"), overlay).convert("RGB")
    reveal.thumbnail((820, 980), Image.Resampling.LANCZOS)
    canvas.paste(reveal, (900, 56))
    draw.text((36, 1100), "SOURCE + crop window", font=_font(16), fill=IVORY)
    draw.text((900, 1100), "4:5 COVER + locked reveal", font=_font(16), fill=IVORY)
    return canvas


def render_parent_vs_child(parent: Image.Image, child: Image.Image) -> Image.Image:
    return render_pair(
        parent,
        child,
        "PARENT  LOCKED  Day_002",
        "CHILD  DRAFT  Day_009",
        "07  PARENT vs CHILD",
    )


def render_review_board(parent: Image.Image, child: Image.Image, selected: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (14, 12, 10))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "09  HUMAN REVIEW BOARD  —  VISUAL_REPLACE_ONLY  DRAFT", font=_font(18), fill=GOLD)
    x = 36
    for label, image in (("LOCKED MASTER", parent), ("PHOTO REPLACEMENT CHILD", child), ("SELECTED Day_009", selected)):
        tile = image.copy()
        tile.thumbnail((580, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 920), label, font=_font(16), fill=IVORY)
        x += 620
    return canvas


def load_asset(db: Session, asset_id: str) -> Image.Image:
    return Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
