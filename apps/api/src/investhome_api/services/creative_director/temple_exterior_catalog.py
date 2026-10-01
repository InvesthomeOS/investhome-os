"""Approved The Temple exterior catalog for concept-led photo selection."""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import DAY007_ASSET_ID, DAY007_FILENAME
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, cover_fit_canvas
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import LOCKED_HERO_ASSET_ID, LOCKED_LOGO_ASSET_ID, TEMPLE_PROJECT_ID, _read_bytes
from investhome_api.services.creative_director.photo_family_eligibility import SKIP_EXTERIOR_TOKENS, is_approved_exterior_filename
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map

KNOWN_EXTERIORS = (
    (DAY007_ASSET_ID, DAY007_FILENAME),
    (LOCKED_HERO_ASSET_ID, "IH_DC_TMP_001_Render_Exterior_Day_004.jpg"),
)

KEEP_EXTRA = ("sunset", "render_exterior", "day_010", "day_003", "day_005")


def is_temple_production_exterior(filename: str, content_type: str = "") -> bool:
    name = (filename or "").lower()
    if "ornek" in name or "design_reference" in name:
        return False
    if is_approved_exterior_filename(filename, content_type):
        return True
    if any(tok in name for tok in SKIP_EXTERIOR_TOKENS):
        return False
    return any(tok in name for tok in KEEP_EXTRA)


def _centering_for_mode(mode: str) -> tuple[float, float]:
    if mode == "GROUND_PLANE":
        return (0.50, 0.52)
    if mode == "CORNER_INGRESS":
        return (0.48, 0.44)
    return (0.50, 0.38)


def load_temple_exteriors(db: Session) -> list[dict[str, Any]]:
    project = UUID(TEMPLE_PROJECT_ID)
    rows = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == project,
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
        ).all()
    )
    by_id = {str(row.id): row for row in rows}
    chosen: list[CreativeStudioMediaAsset] = []
    seen: set[str] = set()
    for asset_id, _name in KNOWN_EXTERIORS:
        row = by_id.get(asset_id)
        if row is not None and asset_id not in seen:
            chosen.append(row)
            seen.add(asset_id)
    for row in rows:
        aid = str(row.id)
        if aid in seen or aid == LOCKED_LOGO_ASSET_ID:
            continue
        if not is_temple_production_exterior(str(row.filename or ""), str(row.content_type or "")):
            continue
        chosen.append(row)
        seen.add(aid)
    catalog: list[dict[str, Any]] = []
    for row in chosen:
        try:
            source = Image.open(io.BytesIO(_read_bytes(db, row.id))).convert("RGB")
        except Exception:
            continue
        crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.50, 0.42))
        graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
        occupancy = build_photo_occupancy_map(graded)
        catalog.append(
            {
                "asset_id": str(row.id),
                "filename": str(row.filename or ""),
                "source": source,
                "preview": graded,
                "occupancy": occupancy,
                "transform": transform,
                "sky_area": float(occupancy.get("sky_area") or 0),
                "architecture_centroid_x": float(occupancy.get("architecture_centroid_x") or 0.5),
                "hard_coverage": float((occupancy.get("coverage") or {}).get("hard_protected") or 0),
            }
        )
    return catalog


def score_photo_for_mode(item: dict[str, Any], mode: str) -> float:
    sky = float(item.get("sky_area") or 0)
    hard = float(item.get("hard_coverage") or 0)
    cx = float(item.get("architecture_centroid_x") or 0.5)
    if mode == "SKY_VEIL":
        return sky * 1.4 + (1.0 - hard) * 0.3
    if mode == "GROUND_PLANE":
        return (1.0 - sky) * 0.8 + hard * 0.5
    side = abs(cx - 0.5)
    return 0.4 + side * 0.8 + sky * 0.3


def pick_photo_for_concept(
    catalog: list[dict[str, Any]],
    *,
    mode: str,
    used: set[str],
    requested_filename: str | None = None,
    requested_asset_id: str | None = None,
) -> dict[str, Any] | None:
    if not catalog:
        return None
    if requested_asset_id:
        for item in catalog:
            if item["asset_id"] == requested_asset_id:
                return item
    if requested_filename:
        needle = requested_filename.lower()
        for item in catalog:
            if needle in item["filename"].lower() or item["filename"].lower() in needle:
                unused = [it for it in catalog if it["asset_id"] not in used]
                best = max(unused or catalog, key=lambda it: score_photo_for_mode(it, mode))
                sky = float(item.get("sky_area") or 0)
                if mode == "SKY_VEIL" and sky < 0.10:
                    return best
                return item
    ranked = sorted(catalog, key=lambda it: (it["asset_id"] in used, -score_photo_for_mode(it, mode)))
    return ranked[0]


def crop_photo_for_mode(item: dict[str, Any], mode: str) -> tuple[Image.Image, Image.Image, dict[str, Any], dict[str, Any]]:
    centering = _centering_for_mode(mode)
    crop, transform = cover_fit_canvas(item["source"], CANVAS_4X5, centering=centering)
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = build_photo_occupancy_map(graded)
    transform = dict(transform)
    transform["centering"] = list(centering)
    return item["source"], graded, occupancy, transform
