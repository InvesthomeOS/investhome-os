"""PhotoToMasterCompatibilityV1 — replace a photo inside an existing master territory.

The Master already exists. Rank approved project exteriors for the locked
photo panel. Do not ask which design family fits the photo.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.creative_director.phase5_photo_foundation import cover_fit_canvas
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.photo_family_eligibility import is_approved_exterior_filename
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map, occupancy_to_json
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID

TRUE_FIT = "TRUE_FIT"
CONDITIONAL_FIT = "CONDITIONAL_FIT"
NO_FIT = "NO_FIT"

_SKIP_NAME_TOKENS = (
    "design_reference",
    "design-reference",
    "investhome_logo",
    "company",
    "stock",
    "ai_generat",
    "visual_draft",
    "draft_architecture",
)

_CENTER_X = (0.38, 0.42, 0.50, 0.58, 0.66, 0.74, 0.82, 0.88, 0.94)
_CENTER_Y = (0.34, 0.38, 0.42, 0.48)


def _clip(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return round(max(lo, min(hi, value)), 2)


def photo_territory_from_spec(spec: dict[str, Any], canvas: tuple[int, int] = (1088, 1360)) -> tuple[int, int, int, int]:
    w, h = canvas
    navy = dict(spec.get("navy_field") or {})
    px = navy.get("px")
    if isinstance(px, (list, tuple)) and len(px) == 4 and int(px[2]) > 8:
        split_x = int(px[2])
    else:
        bounds = dict(navy.get("bounds") or {})
        split_x = int(round(float(bounds.get("w") or 0.3438) * w))
    split_x = max(8, min(w - 8, split_x))
    return (split_x, 0, w, h)


def list_approved_temple_exteriors(db: Session, *, exclude_ids: set[str] | None = None) -> list[CreativeStudioMediaAsset]:
    blocked = {str(item) for item in (exclude_ids or set())}
    blocked.add(str(DAY007_ASSET_ID))
    rows = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == UUID(TEMPLE_PROJECT_ID),
                CreativeStudioMediaAsset.archived_at.is_(None),
                CreativeStudioMediaAsset.content_type.ilike("image/%"),
            )
        ).all()
    )
    chosen: list[CreativeStudioMediaAsset] = []
    for row in rows:
        name = (row.filename or "").lower()
        if str(row.id) in blocked:
            continue
        if any(tok in name for tok in _SKIP_NAME_TOKENS):
            continue
        if not is_approved_exterior_filename(row.filename, row.content_type):
            continue
        chosen.append(row)
    chosen.sort(key=lambda row: row.filename or "")
    return chosen


def _occupancy_scores(occ: dict[str, Any], *, ref: dict[str, Any] | None = None) -> dict[str, float]:
    coverage = dict(occ.get("coverage") or {})
    hard = float(coverage.get("hard_protected") or 0)
    sky = float(occ.get("sky_area") or 0)
    centroid = float(occ.get("architecture_centroid_x") or 0.5)
    region = dict((occ.get("regions") or {}).get("hard_protected") or {})
    bbox_h = float(region.get("h") or 0)
    bbox_w = float(region.get("w") or 0)
    bbox_y = float(region.get("y") or 0)
    bbox_x = float(region.get("x") or 0)
    ref_cov = dict((ref or {}).get("coverage") or {})
    ref_hard = float(ref_cov.get("hard_protected") or 0.22)
    ref_centroid = float((ref or {}).get("architecture_centroid_x") or 0.28)
    ref_region = dict(((ref or {}).get("regions") or {}).get("hard_protected") or {})
    ref_h = float(ref_region.get("h") or 0.72)

    architecture_visibility = _clip(10.0 * min(1.0, hard / 0.16))
    hero_quality = _clip(4.0 + 8.0 * min(1.0, bbox_h) * min(1.0, hard / 0.18))
    subject_scale = _clip(10.0 - 18.0 * abs(bbox_h - ref_h))
    subject_position = _clip(10.0 - 16.0 * abs(centroid - ref_centroid))
    vertical_composition = _clip(10.0 * min(1.0, bbox_h / 0.62))
    available_crop = _clip(10.0 if bbox_w >= 0.28 and bbox_h >= 0.40 else 6.0)
    clipped = bbox_y <= 0.01 and bbox_h >= 0.98
    crop_compatibility = _clip(9.4 if not clipped and bbox_h >= 0.48 else 6.2)
    visual_balance = _clip(
        10.0
        - 14.0 * abs(centroid - ref_centroid)
        - (1.2 if sky > 0.62 else 0.0)
        - (1.2 if hard < 0.08 else 0.0)
        + (0.4 if float(region.get("x") or 1) <= 0.22 else 0.0)
    )
    integrity = 10.0 if hard >= 0.06 and bbox_h >= 0.34 else 4.0
    disruption = abs(hard - ref_hard) + abs(centroid - ref_centroid) + abs(bbox_h - ref_h)
    least_disruption = _clip(10.0 - 8.0 * disruption)
    overall = _clip(
        0.16 * architecture_visibility
        + 0.12 * hero_quality
        + 0.12 * crop_compatibility
        + 0.10 * subject_scale
        + 0.10 * subject_position
        + 0.12 * vertical_composition
        + 0.10 * visual_balance
        + 0.08 * available_crop
        + 0.10 * least_disruption
    )
    return {
        "architecture_visibility": architecture_visibility,
        "hero_quality": hero_quality,
        "crop_compatibility": crop_compatibility,
        "subject_scale": subject_scale,
        "subject_position": subject_position,
        "vertical_composition": vertical_composition,
        "visual_balance_against_navy": visual_balance,
        "available_crop": available_crop,
        "architecture_integrity": integrity,
        "least_disruption": least_disruption,
        "overall": overall,
        "hard_protected": round(hard, 4),
        "sky_area": round(sky, 4),
        "centroid_x": round(centroid, 4),
        "bbox_h": round(bbox_h, 4),
        "bbox_w": round(bbox_w, 4),
        "bbox_x": round(bbox_x, 4),
        "bbox_y": round(bbox_y, 4),
    }


def _fit_status(scores: dict[str, float]) -> str:
    if (
        scores["overall"] >= 7.6
        and scores["architecture_visibility"] >= 7.0
        and scores["architecture_integrity"] >= 8.0
        and scores["vertical_composition"] >= 7.0
        and scores["crop_compatibility"] >= 7.0
        and scores["hard_protected"] >= 0.08
    ):
        return TRUE_FIT
    if scores["overall"] >= 6.2 and scores["hard_protected"] >= 0.05:
        return CONDITIONAL_FIT
    return NO_FIT


def crop_source_for_photo_territory(
    source: Image.Image,
    target: tuple[int, int],
    *,
    ref_occupancy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    probe = (max(160, target[0] // 2), max(320, target[1] // 2))
    ref_centroid = float((ref_occupancy or {}).get("architecture_centroid_x") or 0.28)
    best: dict[str, Any] | None = None
    for cx in _CENTER_X:
        for cy in _CENTER_Y:
            probe_crop, _ = cover_fit_canvas(source, probe, centering=(cx, cy))
            occ = build_photo_occupancy_map(probe_crop)
            scores = _occupancy_scores(occ, ref=ref_occupancy)
            centroid = float(scores.get("centroid_x") or 0.5)
            rank = (
                scores["overall"]
                + 2.2 * scores["visual_balance_against_navy"]
                + 0.3 * scores["least_disruption"]
                - 14.0 * abs(centroid - ref_centroid)
            )
            if best is None or rank > float(best["rank"]):
                best = {"centering": (cx, cy), "rank": rank, "probe_scores": scores, "probe_occupancy": occupancy_to_json(occ)}
    assert best is not None
    crop, transform = cover_fit_canvas(source, target, centering=best["centering"])
    occ = build_photo_occupancy_map(crop)
    scores = _occupancy_scores(occ, ref=ref_occupancy)
    return {
        "crop": crop,
        "transform": transform,
        "occupancy": occupancy_to_json(occ),
        "scores": scores,
        "fit": _fit_status(scores),
        "centering": list(best["centering"]),
        "rank": round(float(best["rank"]), 4),
    }


def score_candidate_for_master(
    *,
    source: Image.Image,
    photo_size: tuple[int, int],
    ref_occupancy: dict[str, Any] | None = None,
    asset_id: str,
    filename: str,
) -> dict[str, Any]:
    pack = crop_source_for_photo_territory(source, photo_size, ref_occupancy=ref_occupancy)
    scores = dict(pack["scores"])
    sx = float(pack["transform"].get("scale_x") or 0)
    sy = float(pack["transform"].get("scale_y") or 0)
    non_uniform = abs(sx - sy) > 1e-6
    scale = max(sx, sy)
    if scale > 1.35:
        scores["available_crop"] = _clip(10.0 - 7.0 * (scale - 1.35))
        scores["overall"] = _clip(float(scores["overall"]) - 1.2 * (scale - 1.35))
        pack["scores"] = scores
        pack["fit"] = _fit_status(scores)
    if non_uniform:
        pack["fit"] = NO_FIT
        scores["architecture_integrity"] = 0.0
    return {
        "schema": "PhotoToMasterCompatibilityV1",
        "asset_id": asset_id,
        "filename": filename,
        "fit": pack["fit"],
        "compatibility_score": scores["overall"],
        "scores": scores,
        "transform": pack["transform"],
        "centering": pack["centering"],
        "occupancy": pack["occupancy"],
        "non_uniform_scale": 1 if non_uniform else 0,
        "generated_pixels": 0,
        "crop_preview": pack["crop"],
        "grade": dict(LOCKED_GRADE),
    }


def rank_replacements(results: list[dict[str, Any]], *, top_n: int = 5) -> list[dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda item: (
            0 if item.get("fit") == TRUE_FIT else 1 if item.get("fit") == CONDITIONAL_FIT else 2,
            -float(item.get("compatibility_score") or 0),
        ),
    )
    return ranked[:top_n]
