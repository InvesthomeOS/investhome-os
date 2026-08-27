"""Bounded local recomposition — commercial_group only.

PRICE_EDIT_ONLY stays the semantic intent. When price occupancy grows
(1 slot → 3), OS asks the image provider for an edit_region call and then
composites the result back onto the current approved cover.

OS does not author the commercial design. Overlay / glyph / PRICE_BLOCK
stamping is not used on this path.
"""

from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from PIL import Image, ImageDraw, ImageFont

from investhome_api.services.creative_director.price_block_revision import (
    PriceBlockIntent,
    format_tr_usd,
)
from investhome_api.services.creative_director.provider_router import (
    assert_image_provider_available,
    route_ad_social_image,
)
from investhome_api.services.gpt_image_design.client import (
    decode_remote_image,
    edit_image,
    provider_call_count,
)
from investhome_api.services.gpt_image_design.config import (
    openai_api_key,
    provider_availability,
)

logger = logging.getLogger(__name__)

EXECUTION = "BOUNDED_LOCAL_RECOMPOSITION"
LOCKED_SOURCE_VISUAL_DAY_004 = "299bd265-a0ea-486d-866d-1947f103fd57"
COMMERCIAL_CHANGE_MIN_MAD = 4.0
MIN_TYPE_COMPONENT_H = 14
PROVIDER_FULL_REDESIGN_MAD = 42.0
EVIDENCE_DIR = Path(
    os.environ.get("BOUNDED_RECOMPOSE_EVIDENCE_DIR", "/tmp/bounded-local-recomposition-v2")
)
GHOST_UNCHANGED_MAX_RATIO = 0.35
GHOST_UNCHANGED_MIN_PIXELS = 24
OVERLAP_IOU = 0.38


def write_evidence_files(**files: bytes | None) -> str:
    """Internal debug dumps. Must never become the user-facing cover."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        if data:
            (EVIDENCE_DIR / name).write_bytes(data)
    return str(EVIDENCE_DIR)


def _dump_gates(payload: dict[str, Any], name: str = "gates.json") -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / name).write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )


def _fail_closed(message: str, **extra: Any) -> None:
    payload = {"message": message, **extra}
    _dump_gates(payload, "fail.json")
    logger.warning("bounded_recompose_fail %s", message)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=payload,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def region_by_role(edit_map: dict[str, Any], role: str) -> dict[str, Any] | None:
    for item in edit_map.get("regions") or []:
        if isinstance(item, dict) and item.get("semantic_role") == role:
            return item
    return None


def detect_price_content_growth(
    edit_map: dict[str, Any],
    intent: PriceBlockIntent,
) -> dict[str, Any]:
    """1 occupied price slot → 3 required slots is content growth, not text replace."""
    old_r = region_by_role(edit_map, "old_price")
    new_r = region_by_role(edit_map, "new_price")
    sav_r = region_by_role(edit_map, "savings_price")
    before = {
        "old_price": bool(old_r and old_r.get("occupied")),
        "new_price": bool(new_r and new_r.get("occupied")),
        "savings_price": bool(sav_r and sav_r.get("occupied")),
    }
    after = {
        "old_price": True,
        "new_price": intent.launch_amount is not None,
        "savings_price": intent.savings_amount is not None,
    }
    occupied_before = sum(1 for v in before.values() if v)
    occupied_after = sum(1 for v in after.values() if v)
    growth = occupied_after > occupied_before or (
        (not before["new_price"] and after["new_price"])
        or (not before["savings_price"] and after["savings_price"])
    )
    group = next(
        (
            g
            for g in (edit_map.get("groups") or [])
            if isinstance(g, dict) and g.get("id") == "commercial_group"
        ),
        {},
    )
    capacity = ((group.get("expansion") or {}).get("internal_capacity") or {})
    fits = int(capacity.get("additional_price_rows") or 0) >= (occupied_after - occupied_before)
    use_zone = bool(growth) and not fits
    return {
        "content_growth": bool(growth),
        "before": before,
        "after_request": after,
        "occupied_slots_before": occupied_before,
        "occupied_slots_after": occupied_after,
        "fits_current_geometry": fits,
        "execution": EXECUTION if growth else "in_place_price_edit",
        "mutable_region_role": "commercial_content_zone" if use_zone else "commercial_group",
        "content_growth_route": "commercial_content_zone" if use_zone else "commercial_group",
    }


def commercial_bbox(edit_map: dict[str, Any], *, content_growth: bool = False) -> dict[str, int]:
    if content_growth:
        region = region_by_role(edit_map, "commercial_content_zone")
        box = (region or {}).get("safe_bbox")
        if not box:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "BOUNDED_LOCAL_RECOMPOSITION fail-closed — "
                    "content growth requires commercial_content_zone.safe_bbox. "
                    "The smaller commercial_group region cannot be used."
                ),
            )
    else:
        region = region_by_role(edit_map, "commercial_group")
        box = (region or {}).get("safe_bbox")
        if not box:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "BOUNDED_LOCAL_RECOMPOSITION fail-closed — "
                    "Edit Map v1.1 commercial_group.safe_bbox is required. "
                    "The Phase 1 semantic bbox was not used."
                ),
            )
    return {
        "x0": int(box["x0"]),
        "y0": int(box["y0"]),
        "x1": int(box["x1"]),
        "y1": int(box["y1"]),
    }


def build_commercial_mask(size: tuple[int, int], bbox: dict[str, int]) -> bytes:
    """RGBA PNG: alpha 0 = editable (commercial_group), alpha 255 = preserve."""
    width, height = size
    mask = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    px = mask.load()
    x0, y0, x1, y1 = bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]
    for y in range(max(0, y0), min(height, y1)):
        for x in range(max(0, x0), min(width, x1)):
            px[x, y] = (0, 0, 0, 0)
    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    return buf.getvalue()


def render_mask_debug(cover: Image.Image, bbox: dict[str, int]) -> Image.Image:
    im = cover.convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, 0, im.size[0], im.size[1]], fill=(0, 0, 0, 110))
    draw.rectangle(
        [bbox["x0"], bbox["y0"], bbox["x1"] - 1, bbox["y1"] - 1],
        fill=(255, 200, 40, 80),
        outline=(255, 200, 40, 255),
        width=4,
    )
    composed = Image.alpha_composite(im, overlay).convert("RGB")
    d = ImageDraw.Draw(composed)
    d.text(
        (bbox["x0"] + 8, max(0, bbox["y0"] - 14)),
        "mutable: commercial_group.safe_bbox",
        fill=(255, 200, 40),
    )
    return composed


def build_region_edit_prompt(intent: PriceBlockIntent) -> str:
    list_s = format_tr_usd(intent.list_amount)
    launch_s = format_tr_usd(intent.launch_amount)
    save_s = format_tr_usd(intent.savings_amount)
    return "\n".join(
        [
            "BOUNDED LOCAL EDIT of the commercial information region only.",
            "The attached MASK marks the only pixels you may change (fully transparent = edit).",
            "Opaque mask pixels must remain identical to the source advertisement.",
            "",
            "Do NOT redesign the advertisement.",
            "Do NOT recreate the ad.",
            "Do NOT change the photograph / hero visual.",
            "Do NOT change the headline ALIRKEN / KAZAN.",
            "Do NOT change the subheadline.",
            "Do NOT change the gold CTA button or its text.",
            "Do NOT change The Temple logo.",
            "Do NOT expand the edit into the photograph below the mask (hero starts at the mask bottom).",
            "Do NOT change canvas size, global palette, or overall ad identity.",
            "",
            "Inside the masked commercial group, create a coherent LOCAL COMMERCIAL COMPOSITION.",
            "Do NOT keep the old three equal columns and squeeze extra lines into them.",
            "Do NOT simply stamp two extra text lines. Redesign the hierarchy inside the mask.",
            "You may change column widths, restack, move 2+1 and %35, redesign separators,",
            "and adjust type sizes moderately. Navy / gold / white only. Not a fixed template.",
            "",
            "Hierarchy (make this especially clear):",
            f"PRIMARY — {intent.launch_label}: {launch_s}",
            f"SECONDARY — {intent.list_label}: {list_s} with a clear strikethrough",
            f"IMPORTANT BENEFIT — {intent.savings_label}: {save_s}",
            "SUPPORT — %35 LANSMAN AVANTAJI and 2+1 DAİRE",
            "",
            "Required facts (do not invent others, no ROI / yield / extra discount):",
            "2+1",
            "DAİRE",
            f"{intent.list_label}: {list_s} — struck through",
            f"{intent.launch_label}: {launch_s}",
            f"{intent.savings_label}: {save_s}",
            "LANSMAN AVANTAJI",
            "%35",
            "",
            "Typography must stay readable and premium. No tiny emergency text, no overlapping copy,",
            "no duplicated prices, no ghost leftovers of the old stats, no generic spreadsheet table,",
            "no pasted-on patch. The block must look intentionally designed.",
        ]
    )


def _to_png_rgb(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _mean_abs_delta(a: Image.Image, b: Image.Image, bbox: dict[str, int] | None = None) -> float:
    ar = a.convert("RGB")
    br = b.convert("RGB")
    if ar.size != br.size:
        br = br.resize(ar.size, Image.Resampling.LANCZOS)
    w, h = ar.size
    if bbox:
        x0, y0, x1, y1 = bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]
        ar = ar.crop((x0, y0, x1, y1))
        br = br.crop((x0, y0, x1, y1))
        w, h = ar.size
    pa, pb = ar.load(), br.load()
    total = 0.0
    n = 0
    step = 2 if w * h > 200_000 else 1
    for y in range(0, h, step):
        for x in range(0, w, step):
            ra, ga, ba = pa[x, y]
            rb, gb, bb = pb[x, y]
            total += abs(ra - rb) + abs(ga - gb) + abs(ba - bb)
            n += 1
    return total / 3.0 / max(1, n)


def _mean_abs_delta_outside(a: Image.Image, b: Image.Image, hole: dict[str, int]) -> float:
    ar = a.convert("RGB")
    br = b.convert("RGB")
    if ar.size != br.size:
        br = br.resize(ar.size, Image.Resampling.LANCZOS)
    w, h = ar.size
    pa, pb = ar.load(), br.load()
    total = 0.0
    n = 0
    hx0, hy0, hx1, hy1 = hole["x0"], hole["y0"], hole["x1"], hole["y1"]
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if hx0 <= x < hx1 and hy0 <= y < hy1:
                continue
            ra, ga, ba = pa[x, y]
            rb, gb, bb = pb[x, y]
            total += abs(ra - rb) + abs(ga - gb) + abs(ba - bb)
            n += 1
    return total / 3.0 / max(1, n)


def compose_region(
    original: Image.Image,
    provider: Image.Image,
    bbox: dict[str, int],
) -> Image.Image:
    """OS compositor: provider pixels only inside commercial_group."""
    base = original.convert("RGB")
    src = provider.convert("RGB")
    if src.size != base.size:
        src = src.resize(base.size, Image.Resampling.LANCZOS)
    out = base.copy()
    crop = src.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))
    out.paste(crop, (bbox["x0"], bbox["y0"]))
    return out


def _type_components(crop: Image.Image) -> list[tuple[int, int, int, int]]:
    rgb = crop.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    seen = [[False] * w for _ in range(h)]
    boxes: list[tuple[int, int, int, int]] = []

    def is_type(x: int, y: int) -> bool:
        r, g, b = px[x, y]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        gold = r > 180 and g > 140 and b < 140
        white = (not gold) and lum >= 200
        return gold or white

    for y in range(h):
        for x in range(w):
            if seen[y][x] or not is_type(x, y):
                continue
            stack = [(x, y)]
            seen[y][x] = True
            minx = maxx = x
            miny = maxy = y
            count = 0
            while stack:
                cx, cy = stack.pop()
                count += 1
                minx, maxx = min(minx, cx), max(maxx, cx)
                miny, maxy = min(miny, cy), max(maxy, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and is_type(nx, ny):
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if count >= 18:
                boxes.append((minx, miny, maxx + 1, maxy + 1))
    return boxes


def readability_check(composed: Image.Image, bbox: dict[str, int]) -> dict[str, Any]:
    crop = composed.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))
    boxes = _type_components(crop)
    heights = [b[3] - b[1] for b in boxes]
    max_h = max(heights) if heights else 0
    tiny = sum(1 for hgt in heights if hgt < MIN_TYPE_COMPONENT_H)
    failures: list[str] = []
    if max_h < MIN_TYPE_COMPONENT_H:
        failures.append("unreadable_type_in_commercial_group")
    if boxes and tiny / max(1, len(boxes)) > 0.85 and max_h < 18:
        failures.append("tiny_emergency_typography")
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "component_count": len(boxes),
        "max_component_height": max_h,
        "tiny_component_ratio": round(tiny / max(1, len(boxes)), 3),
    }


def _token_present(crop: Image.Image, token: str) -> bool:
    """Advisory only. Never the sole accept/reject signal for price facts."""
    rgb = crop.convert("L")
    rgb.thumbnail((240, 240), Image.Resampling.BILINEAR)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22
        )
    except Exception:
        font = ImageFont.load_default()
    probe = Image.new("L", (220, 48), 0)
    ImageDraw.Draw(probe).text((2, 4), token, fill=255, font=font)
    pb = probe.getbbox()
    if not pb:
        return False
    glyph = probe.crop(pb)
    gw, gh = glyph.size
    cw, ch = rgb.size
    if gw >= cw or gh >= ch:
        return False
    gp = list(glyph.getdata())
    rp = rgb.load()
    best = 0.0
    for y in range(0, ch - gh, 4):
        for x in range(0, cw - gw, 4):
            hit = 0
            on = 0
            for yy in range(0, gh, 2):
                for xx in range(0, gw, 2):
                    if gp[yy * gw + xx] < 40:
                        continue
                    on += 1
                    if rp[x + xx, y + yy] > 170:
                        hit += 1
            if on and hit / on > best:
                best = hit / on
                if best >= 0.58:
                    return True
    return best >= 0.58


def _raster_type_confidence(crop: Image.Image) -> dict[str, Any]:
    boxes = _type_components(crop)
    heights = [b[3] - b[1] for b in boxes]
    large = [hgt for hgt in heights if hgt >= MIN_TYPE_COMPONENT_H]
    max_h = max(heights) if heights else 0
    # A restacked 3-slot commercial group has several distinct type masses.
    cluster_score = min(1.0, len(large) / 5.0)
    height_score = 1.0 if max_h >= 18 else (0.6 if max_h >= MIN_TYPE_COMPONENT_H else 0.0)
    confidence = round(0.65 * cluster_score + 0.35 * height_score, 3)
    return {
        "component_count": len(boxes),
        "large_component_count": len(large),
        "max_component_height": max_h,
        "confidence": confidence,
        "readable": max_h >= MIN_TYPE_COMPONENT_H and len(large) >= 2,
    }


def _provider_fact_hints(provider_trace: dict[str, Any] | None, intent: PriceBlockIntent) -> dict[str, Any]:
    blob = ""
    if isinstance(provider_trace, dict):
        for key in ("revised_prompt", "prompt", "text", "output_text"):
            val = provider_trace.get(key)
            if isinstance(val, str):
                blob += " " + val
    blob_l = blob.lower().replace(",", "").replace(".", "")
    hits = {
        "list": str(intent.list_amount) in blob_l or format_tr_usd(intent.list_amount).lower() in blob.lower(),
        "launch": str(intent.launch_amount) in blob_l or format_tr_usd(intent.launch_amount).lower() in blob.lower(),
        "savings": str(intent.savings_amount) in blob_l or format_tr_usd(intent.savings_amount).lower() in blob.lower(),
    }
    return {
        "available": bool(blob.strip()),
        "hits": hits,
        "confidence": round(sum(1 for v in hits.values() if v) / 3.0, 3) if blob.strip() else None,
    }


def fact_check(
    composed: Image.Image,
    bbox: dict[str, int],
    intent: PriceBlockIntent,
    *,
    provider_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Multi-signal commercial fact check. Glyph matching is advisory only."""
    crop = composed.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))
    requested = {
        "list": format_tr_usd(intent.list_amount),
        "launch": format_tr_usd(intent.launch_amount),
        "savings": format_tr_usd(intent.savings_amount),
        "strikethrough": bool(intent.list_strikethrough),
        "unit": "2+1",
        "discount": "%35",
    }
    requested_complete = bool(
        intent.list_amount and intent.launch_amount and intent.savings_amount
    )
    raster = _raster_type_confidence(crop)
    glyph = {
        "unit_2+1": _token_present(crop, "2+1"),
        "list_675": _token_present(crop, "675") or _token_present(crop, "675.000"),
        "launch_438": _token_present(crop, "438") or _token_present(crop, "438.750"),
        "savings_236": _token_present(crop, "236") or _token_present(crop, "236.250"),
        "discount_35": _token_present(crop, "%35") or _token_present(crop, "35"),
    }
    glyph_hits = sum(1 for v in glyph.values() if v)
    glyph_conf = round(glyph_hits / max(1, len(glyph)), 3)
    provider = _provider_fact_hints(provider_trace, intent)

    # Weighted confidence. Glyph matcher cannot veto a readable restack.
    parts = [0.45 if requested_complete else 0.0, 0.40 * raster["confidence"]]
    if provider["confidence"] is not None:
        parts.append(0.15 * provider["confidence"])
        parts.append(0.10 * glyph_conf)
    else:
        parts.append(0.15 * glyph_conf)
    confidence = round(sum(parts), 3)

    failures: list[str] = []
    if not requested_complete:
        failures.append("requested_facts_incomplete")
    if not raster["readable"]:
        failures.append("commercial_type_not_readable")
    status = "fail" if failures else "pass"
    if status == "pass" and confidence < 0.42:
        status = "fail"
        failures.append("insufficient_fact_confidence")
    return {
        "status": status,
        "confidence": confidence,
        "failures": failures,
        "warnings": [f"glyph_advisory_miss:{k}" for k, found in glyph.items() if not found],
        "strategy": {
            "primary": ["requested_facts", "raster_type_presence"],
            "secondary": ["provider_structured_hints"],
            "advisory_only": ["local_glyph_matcher"],
            "note": (
                "Glyph matcher is not source of truth. Missing glyph hits never "
                "alone declare price facts missing."
            ),
        },
        "signals": {
            "requested_facts": {"complete": requested_complete, "values": requested},
            "raster_type_presence": raster,
            "glyph_matcher_advisory": {"tokens": glyph, "confidence": glyph_conf},
            "provider_structured": provider,
        },
        "required": requested,
    }


def immutable_region_deltas(
    original: Image.Image, composed: Image.Image, edit_map: dict[str, Any]
) -> dict[str, Any]:
    roles = ("hero_visual", "headline", "subheadline", "cta", "logo")
    out: dict[str, Any] = {}
    for role in roles:
        region = region_by_role(edit_map, role)
        box = (region or {}).get("bbox") if region else None
        if not box:
            out[role] = {"status": "skip", "mad": None}
            continue
        mad = _mean_abs_delta(original, composed, box)
        out[role] = {"status": "pass" if mad < 0.51 else "fail", "mad": round(mad, 4)}
    return out


def _is_type_pixel(r: int, g: int, b: int) -> bool:
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    gold = r > 180 and g > 140 and b < 140
    white = (not gold) and lum >= 200
    return gold or white


def _tail_bands(edit_map: dict[str, Any], bbox: dict[str, int]) -> list[tuple[str, int, int]]:
    region = region_by_role(edit_map, "commercial_group") or {}
    semantic = region.get("semantic_bbox") or {}
    visual = region.get("visual_bbox") or {}
    bands: list[tuple[str, int, int]] = []
    if semantic and visual:
        if int(visual.get("y0") or bbox["y0"]) < int(semantic.get("y0") or bbox["y0"]):
            bands.append(
                ("upper_tail", int(visual["y0"]), int(semantic["y0"]))
            )
        if int(semantic.get("y1") or bbox["y1"]) < int(visual.get("y1") or bbox["y1"]):
            bands.append(
                ("lower_tail", int(semantic["y1"]), int(visual["y1"]))
            )
    if not bands:
        bands.append(("safe_region", bbox["y0"], bbox["y1"]))
    return bands


def ghost_check(
    original: Image.Image,
    composed: Image.Image,
    bbox: dict[str, int],
    edit_map: dict[str, Any],
) -> dict[str, Any]:
    """Reject leftover original commercial type, especially old glyph tails."""
    orig = original.convert("RGB")
    new = composed.convert("RGB")
    po, pn = orig.load(), new.load()
    bands = _tail_bands(edit_map, bbox)
    band_stats: list[dict[str, Any]] = []
    failures: list[str] = []
    for name, y0, y1 in bands:
        y0 = max(bbox["y0"], y0)
        y1 = min(bbox["y1"], y1)
        original_type = 0
        unchanged = 0
        for y in range(y0, y1):
            for x in range(bbox["x0"], bbox["x1"]):
                r, g, b = po[x, y]
                if not _is_type_pixel(r, g, b):
                    continue
                original_type += 1
                r2, g2, b2 = pn[x, y]
                if abs(r - r2) + abs(g - g2) + abs(b - b2) < 18:
                    unchanged += 1
        ratio = unchanged / max(1, original_type)
        stat = {
            "band": name,
            "y0": y0,
            "y1": y1,
            "original_type_pixels": original_type,
            "unchanged_type_pixels": unchanged,
            "unchanged_ratio": round(ratio, 3),
        }
        band_stats.append(stat)
        if original_type >= GHOST_UNCHANGED_MIN_PIXELS and ratio > GHOST_UNCHANGED_MAX_RATIO:
            failures.append(f"ghost_residual:{name}")
    below_hero = 0
    hero = region_by_role(edit_map, "hero_visual")
    hero_y = int((hero or {}).get("bbox", {}).get("y0") or bbox["y1"])
    if bbox["y1"] > hero_y:
        failures.append("safe_region_crosses_hero_boundary")
    for y in range(hero_y, min(orig.size[1], hero_y + 8)):
        for x in range(bbox["x0"], bbox["x1"]):
            r, g, b = pn[x, y]
            if _is_type_pixel(r, g, b):
                r0, g0, b0 = po[x, y]
                if abs(r - r0) + abs(g - g0) + abs(b - b0) > 30:
                    below_hero += 1
    if below_hero > 12:
        failures.append("commercial_pixels_below_hero_boundary")
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "bands": band_stats,
        "new_type_below_hero": below_hero,
        "hero_boundary_y": hero_y,
    }


def overlap_check(composed: Image.Image, bbox: dict[str, int]) -> dict[str, Any]:
    crop = composed.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))
    boxes = [b for b in _type_components(crop) if (b[3] - b[1]) >= 12 and (b[2] - b[0]) >= 12]
    overlaps = 0
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
            ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            inter = (ix1 - ix0) * (iy1 - iy0)
            area_a = max(1, (a[2] - a[0]) * (a[3] - a[1]))
            area_b = max(1, (b[2] - b[0]) * (b[3] - b[1]))
            iou = inter / float(area_a + area_b - inter)
            if iou > OVERLAP_IOU:
                overlaps += 1
    failures = ["overlapping_commercial_type"] if overlaps >= 3 else []
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "large_component_count": len(boxes),
        "overlap_pairs": overlaps,
    }


def visual_quality_gate(
    readability: dict[str, Any],
    overlap: dict[str, Any],
    ghost: dict[str, Any],
    facts: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    for block in (readability, overlap, ghost):
        failures.extend(list(block.get("failures") or []))
    if facts.get("status") == "fail":
        failures.extend(list(facts.get("failures") or ["facts_failed"]))
    max_h = int(readability.get("max_component_height") or 0)
    if max_h and max_h < 18:
        failures.append("commercial_hierarchy_too_small")
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "readability": readability.get("status"),
        "overlap": overlap.get("status"),
        "ghost": ghost.get("status"),
        "facts": facts.get("status"),
        "facts_confidence": facts.get("confidence"),
    }


def render_pixel_diff(
    original: Image.Image, composed: Image.Image, bbox: dict[str, int]
) -> Image.Image:
    """Gold = change inside safe region. Cyan = any change outside (should be none)."""
    orig = original.convert("RGB")
    new = composed.convert("RGB")
    w, h = orig.size
    out = Image.new("RGB", (w, h), (8, 10, 16))
    po, pn, pp = orig.load(), new.load(), out.load()
    for y in range(0, h, 1):
        for x in range(0, w, 1):
            r, g, b = po[x, y]
            r2, g2, b2 = pn[x, y]
            d = (abs(r - r2) + abs(g - g2) + abs(b - b2)) // 3
            inside = bbox["x0"] <= x < bbox["x1"] and bbox["y0"] <= y < bbox["y1"]
            if d < 4:
                pp[x, y] = (int(r * 0.25), int(g * 0.25), int(b * 0.28))
            elif inside:
                pp[x, y] = (min(255, 40 + d * 2), min(255, 30 + d), 8)
            else:
                pp[x, y] = (8, min(255, 40 + d), min(255, 40 + d * 2))
    draw = ImageDraw.Draw(out)
    draw.rectangle(
        [bbox["x0"], bbox["y0"], bbox["x1"] - 1, bbox["y1"] - 1],
        outline=(255, 200, 40),
        width=2,
    )
    return out


def execute_bounded_commercial_recomposition(
    *,
    cover_bytes: bytes,
    edit_map: dict[str, Any],
    intent: PriceBlockIntent,
    source_visual_asset_id: str,
    expected_source_visual_asset_id: str,
) -> tuple[bytes, dict[str, Any]]:
    if str(source_visual_asset_id) != str(expected_source_visual_asset_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "BOUNDED_LOCAL_RECOMPOSITION fail-closed — source visual is not Day_004."
                ),
                "source_visual_asset_id": str(source_visual_asset_id),
                "expected": str(expected_source_visual_asset_id),
            },
        )
    growth = detect_price_content_growth(edit_map, intent)
    if not growth["content_growth"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "PRICE_EDIT_ONLY on this master requires content growth "
                    "for bounded recomposition."
                ),
                "growth": growth,
            },
        )
    bbox = commercial_bbox(
        edit_map,
        content_growth=bool(growth.get("content_growth"))
        and not bool(growth.get("fits_current_geometry")),
    )
    original = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
    width, height = original.size
    if bbox["y1"] > height or bbox["x1"] > width:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="BOUNDED_LOCAL_RECOMPOSITION fail-closed — commercial bbox outside canvas.",
        )

    route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(route)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"BOUNDED_LOCAL_RECOMPOSITION fail-closed — edit_region unavailable. {exc}",
        ) from exc
    availability = provider_availability()
    if not availability.available:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="BOUNDED_LOCAL_RECOMPOSITION fail-closed — image edit provider unavailable.",
        )

    mask_png = build_commercial_mask((width, height), bbox)
    prompt = build_region_edit_prompt(intent)
    cover_png = _to_png_rgb(original)
    mask_dbg = render_mask_debug(original, bbox)
    mask_dbg_buf = io.BytesIO()
    mask_dbg.save(mask_dbg_buf, format="PNG")
    write_evidence_files(
        **{
            "before.png": cover_png,
            "mask.png": mask_png,
            "mask-debug.png": mask_dbg_buf.getvalue(),
        }
    )
    calls_before = provider_call_count()
    try:
        remote = edit_image(
            api_key=openai_api_key(),
            model=availability.model,
            prompt=prompt,
            images=[(cover_png, "current-approved-cover.png", "image/png")],
            size=f"{width}x{height}",
            quality=availability.quality,
            base_url=availability.base_url,
            variant="edit_region_commercial_group",
            mask=mask_png,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "BOUNDED_LOCAL_RECOMPOSITION fail-closed — provider could not "
                    "perform a bounded region edit. Full-ad generation was not used."
                ),
                "error": str(exc)[:300],
            },
        ) from exc
    calls = provider_call_count() - calls_before
    if calls != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "BOUNDED_LOCAL_RECOMPOSITION fail-closed — unexpected provider call count.",
                "provider_calls": calls,
            },
        )

    raw_bytes = decode_remote_image(remote)
    provider_im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    if provider_im.size != original.size:
        provider_im = provider_im.resize(original.size, Image.Resampling.LANCZOS)
    raw_buf = io.BytesIO()
    provider_im.save(raw_buf, format="PNG")
    write_evidence_files(**{"provider-regional.png": raw_buf.getvalue()})

    raw_outside = _mean_abs_delta_outside(original, provider_im, bbox)
    if raw_outside > PROVIDER_FULL_REDESIGN_MAD:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "BOUNDED_LOCAL_RECOMPOSITION fail-closed — provider changed pixels "
                    "outside the commercial group (full-ad redesign, not a region edit)."
                ),
                "outside_mask_mad": round(raw_outside, 3),
                "threshold": PROVIDER_FULL_REDESIGN_MAD,
                "provider_calls": calls,
            },
        )

    composed = compose_region(original, provider_im, bbox)
    composed_buf = io.BytesIO()
    composed.save(composed_buf, format="PNG")
    before_crop = original.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))
    after_crop = composed.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))
    bc, ac, df = io.BytesIO(), io.BytesIO(), io.BytesIO()
    before_crop.save(bc, format="PNG")
    after_crop.save(ac, format="PNG")
    render_pixel_diff(original, composed, bbox).save(df, format="PNG")
    write_evidence_files(
        **{
            "after-composed-candidate.png": composed_buf.getvalue(),
            "before-crop.png": bc.getvalue(),
            "after-crop.png": ac.getvalue(),
            "pixel-diff.png": df.getvalue(),
        }
    )
    composed_outside = _mean_abs_delta_outside(original, composed, bbox)
    commercial_mad = _mean_abs_delta(original, composed, bbox)
    if commercial_mad < COMMERCIAL_CHANGE_MIN_MAD:
        _fail_closed(
            "BOUNDED_LOCAL_RECOMPOSITION fail-closed — commercial group did not change.",
            commercial_mad=round(commercial_mad, 3),
        )

    locks = immutable_region_deltas(original, composed, edit_map)
    lock_failures = [k for k, v in locks.items() if v.get("status") == "fail"]
    if lock_failures or composed_outside >= 0.51:
        _fail_closed(
            "BOUNDED_LOCAL_RECOMPOSITION fail-closed — immutable region changed.",
            lock_failures=lock_failures,
            composed_outside_mad=round(composed_outside, 4),
            locks=locks,
        )

    read = readability_check(composed, bbox)
    ghost = ghost_check(original, composed, bbox, edit_map)
    overlap = overlap_check(composed, bbox)
    facts = fact_check(
        composed,
        bbox,
        intent,
        provider_trace={
            "prompt": prompt,
            "revised_prompt": getattr(remote, "revised_prompt", None),
        },
    )
    quality = visual_quality_gate(read, overlap, ghost, facts)
    _dump_gates(
        {
            "safe_bbox": bbox,
            "provider_calls": calls,
            "generate_calls": 0,
            "visual_replace_calls": 0,
            "preservation": {
                "raw_outside_mad": round(raw_outside, 4),
                "composed_outside_mad": round(composed_outside, 4),
                "commercial_mad": round(commercial_mad, 4),
                "locks": locks,
            },
            "readability": read,
            "ghost": ghost,
            "overlap": overlap,
            "facts": facts,
            "visual_quality": quality,
        }
    )
    if quality["status"] == "fail":
        reason = ", ".join(quality.get("failures") or ["visual_quality"])
        _fail_closed(
            f"BOUNDED_LOCAL_RECOMPOSITION fail-closed — {reason}.",
            visual_quality=quality,
            ghost=ghost,
            overlap=overlap,
            readability=read,
            facts=facts,
        )

    out_buf = io.BytesIO()
    composed.save(out_buf, format="PNG")
    write_evidence_files(**{"after.png": out_buf.getvalue()})

    trace = {
        "execution": EXECUTION,
        "intent": "PRICE_EDIT_ONLY",
        "content_growth": growth,
        "mutable_region": bbox,
        "mutable_region_role": growth.get("mutable_region_role"),
        "safe_bbox": bbox,
        "edit_map_version": edit_map.get("version"),
        "provider_capability": "edit_region",
        "provider_id": route.provider_id,
        "provider_model": availability.model,
        "provider_calls": calls,
        "generate_calls": 0,
        "visual_replace_calls": 0,
        "calls_before": calls_before,
        "prompt": prompt,
        "preservation": {
            "raw_outside_mad": round(raw_outside, 4),
            "composed_outside_mad": round(composed_outside, 4),
            "commercial_mad": round(commercial_mad, 4),
            "locks": locks,
        },
        "readability": read,
        "ghost": ghost,
        "overlap": overlap,
        "facts": facts,
        "visual_quality": quality,
        "source_visual_asset_id": str(source_visual_asset_id),
        "evidence_dir": str(EVIDENCE_DIR),
        "evidence": {
            "provider_png": raw_buf.getvalue(),
            "mask_debug_png": mask_dbg_buf.getvalue(),
            "before_crop_png": bc.getvalue(),
            "after_crop_png": ac.getvalue(),
            "pixel_diff_png": df.getvalue(),
        },
    }
    logger.info(
        "bounded_local_recomposition cover=%sx%s outside_raw=%.2f commercial_mad=%.2f calls=%s",
        width,
        height,
        raw_outside,
        commercial_mad,
        calls,
    )
    return out_buf.getvalue(), trace


def public_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Drop binary evidence before persisting campaign JSON."""
    return {k: v for k, v in trace.items() if k != "evidence"}
