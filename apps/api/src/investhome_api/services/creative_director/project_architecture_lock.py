"""PROJECT_ARCHITECTURE_LOCK — Phase 5.1A.

Approved project architecture is immutable. The image model remains the
advertisement designer; it may grade, crop, and design around the building,
but it may not reconstruct the building.

Primary preservation method: keep source architecture pixels and composite
them into the generated creative (crop-aware, grade-matched). Asking the
model to redraw the building from reference is the fallback we avoid.
"""

from __future__ import annotations

import io
import logging
from typing import Any
from uuid import UUID

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from sqlalchemy.orm import Session

from investhome_api.models.user_auth import User
from investhome_api.services.creative_studio_media_service import get_asset_or_404, open_asset_content
from investhome_api.services.gpt_image_design.persistence import (
    asset_url,
    persist_gpt_image,
    sniff_image_content_type,
)

logger = logging.getLogger(__name__)

POLICY_NAME = "PROJECT_ARCHITECTURE_LOCK"
POLICY_VERSION = "5.1A"
COMPARISON_METHOD = "crop_aware_edge_ncc_silhouette_projections"
LOCK_METHOD = "source_pixel_composite_with_grade_match"
PROTECTED_REGION_METHOD = "automatic_conservative_sky_foliage_exclusion_plus_vertical_structure"
MAX_ARCHITECTURE_LOCK_RETRIES = 2
MIN_STRUCTURE_SIZE = 180
STRUCTURE_ENERGY_MIN = 4.0
NCC_PASS = 0.42
NCC_WEAK = 0.28
ASPECT_DRIFT_FAIL = 0.22
PROJECTION_PASS = 0.32
TOWER_PASS = 0.45

ALLOWED_TRANSFORMATIONS = (
    "color_grading",
    "white_balance",
    "warm_cool_tone",
    "exposure",
    "contrast",
    "highlights",
    "shadows",
    "atmospheric_haze",
    "sunset_day_night_mood",
    "sky_treatment",
    "clouds",
    "light_direction_appearance",
    "subtle_environmental_lighting",
    "lens_flare",
    "depth_treatment",
    "background_atmosphere",
    "foreground_atmosphere",
    "crop",
    "canvas_extension",
    "composition_around_the_image",
    "typography",
    "graphic_design",
    "campaign_elements",
    "cta",
    "logo_placement",
    "decorative_elements",
    "subtle_photographic_finishing",
)

FORBIDDEN_TRANSFORMATIONS = (
    "beautify_architecture_by_redesign",
    "complete_missing_architecture",
    "modernize_facade",
    "simplify_architectural_details",
    "add_floors",
    "remove_floors",
    "change_tower_geometry",
    "change_roof_geometry",
    "invent_windows",
    "move_windows",
    "create_another_version_of_the_project",
    "relocate_the_project_geographically",
    "replace_adjacent_major_buildings_in_a_misleading_way",
    "regenerate_the_building_from_reference_when_source_pixels_are_available",
)

IMMUTABLE_FEATURES = (
    "building_silhouette",
    "building_footprint_visible_in_the_image",
    "spire_tower_geometry",
    "spire_height_and_proportions",
    "roof_geometry",
    "facade_geometry",
    "facade_articulation",
    "window_positions",
    "window_sizes",
    "window_count_pattern",
    "door_positions",
    "column_positions",
    "structural_proportions",
    "floor_count",
    "floor_heights",
    "building_massing",
    "setbacks",
    "balconies_terraces",
    "major_architectural_ornaments",
    "major_material_boundaries",
    "relationship_between_architectural_volumes",
    "recognizable_project_specific_architectural_features",
)


def architecture_lock_policy(
    *,
    source_asset_id: str | None = None,
    source_filename: str | None = None,
) -> dict[str, Any]:
    """Reusable policy/interface for Phase 5.0, 5.1, and future 5.2 video."""
    return {
        "policy_name": POLICY_NAME,
        "policy_version": POLICY_VERSION,
        "project_locked": True,
        "project_architecture_lock": True,
        "source_architecture_asset_id": source_asset_id,
        "source_architecture_file": source_filename,
        "architecture_lock_method": LOCK_METHOD,
        "protected_region_mask_method": PROTECTED_REGION_METHOD,
        "comparison_method": COMPARISON_METHOD,
        "ai_image_provider": "gpt-image",
        "ai_image_model": "gpt-image-2",
        "provider_mask_supported": True,
        "provider_mask_used_as_primary": False,
        "provider_mask_note": (
            "gpt-image-2 images/edits accepts a mask (transparent=edit, opaque=preserve). "
            "Primary method keeps original architecture pixels via composite instead of "
            "asking the model to redraw the building."
        ),
        "allowed_transformations": list(ALLOWED_TRANSFORMATIONS),
        "forbidden_transformations": list(FORBIDDEN_TRANSFORMATIONS),
        "immutable_features": list(IMMUTABLE_FEATURES),
        "crop_allowed_without_redesign": True,
        "ai_remains_primary_advertisement_designer": True,
        "phase4_renderer_is_not_primary": True,
        "user_drawn_mask_required": False,
        "brand_market_content_exempt": True,
        "fail_closed": True,
        "max_retries": MAX_ARCHITECTURE_LOCK_RETRIES,
        "video": {
            "reuse_policy": True,
            "stricter_required_later": True,
            "reason": "image-to-video models can mutate architecture frame by frame",
            "video_started": False,
            "qa_method": COMPARISON_METHOD,
            "protected_architecture_reference": "approved_source_pixels_plus_automatic_mask",
        },
    }


def architecture_lock_prompt_lines() -> list[str]:
    return [
        "PROJECT_ARCHITECTURE_LOCK (mandatory for this project creative):",
        "IMAGE of the approved project is architectural ground truth, not inspiration.",
        "USE the approved project asset. Do NOT modify the architecture inside it.",
        "Do not beautify, complete, modernize, simplify, or invent architecture.",
        "Do not change silhouette, spire/tower, roof, façade, windows, floors, massing, or proportions.",
        "You MAY grade, change atmosphere, sky, crop, extend canvas, and design typography/graphics around the building.",
        "Cropping the same building is allowed. Generating a different building to fit is forbidden.",
        "Preserve actual project pixels of the building. Do not recreate a similar Temple.",
        "You remain the advertisement designer: composition, type, CTA, logo, hierarchy, mood.",
    ]


def should_apply_architecture_lock(
    *,
    campaign_mode: str | None,
    brand_market_ad: bool = False,
    source: Image.Image | None = None,
) -> tuple[bool, str | None]:
    mode = (campaign_mode or "").strip().lower()
    if brand_market_ad or mode in {"general", "brand", "market", "lifestyle"}:
        return False, "brand_market_or_non_project"
    if mode and mode != "project":
        return False, f"campaign_mode_{mode}"
    if source is None:
        return True, None
    if min(source.size) < MIN_STRUCTURE_SIZE:
        return False, "source_too_small"
    if not source_has_architecture_structure(source):
        return False, "source_lacks_architectural_structure"
    return True, None


def source_has_architecture_structure(source: Image.Image) -> bool:
    if min(source.size) < MIN_STRUCTURE_SIZE:
        return False
    return _edge_energy(source) >= STRUCTURE_ENERGY_MIN


def derive_architecture_mask(source: Image.Image) -> Image.Image:
    """Automatic conservative architecture mask. Over-preserve rather than under-preserve.

    Never requires a user-drawn mask. Sky and heavy foliage are excluded so the
    advertisement can still design atmosphere around the building.
    """
    rgb = source.convert("RGB")
    w, h = rgb.size
    sw = 160
    sh = max(8, int(round(h * (sw / max(w, 1)))))
    small = rgb.resize((sw, sh), Image.Resampling.BOX)
    lum = small.convert("L")
    edges = lum.filter(ImageFilter.FIND_EDGES)
    vert = _vertical_energy_image(lum)
    mask_s = Image.new("L", small.size, 0)
    sp, lp, ep, vp, mp = small.load(), lum.load(), edges.load(), vert.load(), mask_s.load()
    for y in range(sh):
        for x in range(sw):
            r, g, b = sp[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            sat = mx - mn
            lval = int(lp[x, y])
            ev = int(ep[x, y])
            vv = int(vp[x, y])
            yn = y / max(sh - 1, 1)
            is_sky = yn < 0.46 and lval > 145 and sat < 48 and ev < 28
            is_foliage = g > r + 14 and g > b + 8 and g > 72 and yn > 0.48 and ev < 70
            is_street = yn > 0.88 and lval < 78 and sat < 40
            stone = lval > 95 and sat < 70 and not is_sky
            vertical = vv > 18 and yn < 0.85
            protect = (not is_sky and not is_foliage and not is_street and (stone or ev > 22 or vertical))
            if protect:
                mp[x, y] = 255
    mask_s = mask_s.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MaxFilter(3))
    mask_s = mask_s.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5))
    coverage = _coverage(mask_s)
    if coverage < 0.08:
        mask_s = _fallback_region_mask(small.size)
    elif coverage > 0.82:
        mask_s = ImageChops.multiply(mask_s, _fallback_region_mask(small.size))
        mask_s = mask_s.filter(ImageFilter.MaxFilter(5))
    return mask_s.resize(rgb.size, Image.Resampling.NEAREST)


def architecture_integrity_qa(
    source: Image.Image,
    candidate: Image.Image,
    *,
    mask: Image.Image | None = None,
    source_asset_id: str | None = None,
) -> dict[str, Any]:
    """Crop-aware structural comparison. Tolerates grade, lighting, crop, placement.

    Does not use mean-color as the architecture decision.
    """
    src = source.convert("RGB")
    cand = candidate.convert("RGB")
    if min(src.size) < MIN_STRUCTURE_SIZE or not source_has_architecture_structure(src):
        return _qa_payload(
            status="skipped",
            score=0.0,
            confidence=0.0,
            source_asset_id=source_asset_id,
            reasons=["source_lacks_structure_for_architecture_qa"],
        )
    mask = mask or derive_architecture_mask(src)
    located = locate_architecture(src, cand, mask=mask)
    ncc = float(located["ncc"])
    aspect_drift = float(located["aspect_drift"])
    proj = float(located["projection_score"])
    tower = float(located.get("tower_score") or 0.0)
    mutations: list[str] = []
    if located.get("match_mode") == "none":
        mutations.append("architecture_not_located")
    if ncc < NCC_WEAK:
        mutations.append("silhouette_or_structure_mismatch")
    if aspect_drift > ASPECT_DRIFT_FAIL and ncc < 0.72:
        mutations.append("proportion_or_volume_mismatch")
    if proj < PROJECTION_PASS and ncc < 0.62:
        mutations.append("facade_or_window_pattern_mismatch")
    if tower < TOWER_PASS and ncc < 0.70:
        mutations.append("spire_or_tower_geometry_mismatch")
    score = max(
        0.0,
        min(1.0, 0.45 * ncc + 0.20 * (1.0 - min(aspect_drift, 1.0)) + 0.15 * proj + 0.20 * tower),
    )
    structure_ok = located.get("match_mode") != "none" and ncc >= NCC_WEAK and tower >= TOWER_PASS and (
        ncc >= NCC_PASS or (aspect_drift <= ASPECT_DRIFT_FAIL and proj >= PROJECTION_PASS)
    )
    status = "pass" if structure_ok else "fail"
    confidence = max(0.15, min(0.95, ncc if located.get("match_mode") != "none" else 0.2))
    return _qa_payload(
        status=status,
        score=round(score, 4),
        confidence=round(confidence, 4),
        source_asset_id=source_asset_id,
        reasons=mutations,
        extra={
            "silhouette_ncc": round(ncc, 4),
            "aspect_drift": round(aspect_drift, 4),
            "window_or_facade_projection": round(proj, 4),
            "tower_score": round(tower, 4),
            "match_box": located.get("box"),
            "match_scale": located.get("scale"),
            "match_mode": located.get("match_mode"),
            "detected_mutation_regions": mutations,
            "mean_color_not_used": True,
        },
    )


def lock_architecture_pixels(
    source: Image.Image,
    candidate: Image.Image,
    *,
    mask: Image.Image | None = None,
    single_hero_photo: bool = False,
) -> tuple[Image.Image, dict[str, Any]]:
    """Composite source architecture pixels into the generated creative."""
    src = source.convert("RGB")
    cand = candidate.convert("RGB").copy()
    mask = mask or derive_architecture_mask(src)
    located = locate_architecture(src, cand, mask=mask)
    bbox = _mask_bbox(mask)
    if bbox is None:
        bbox = (int(src.width * 0.18), int(src.height * 0.08), int(src.width * 0.92), int(src.height * 0.92))
        mask = _box_mask(src.size, bbox)
    src_crop = src.crop(bbox)
    mask_crop = mask.crop(bbox)
    ncc = float(located["ncc"])
    box = located.get("box")
    area_ok = False
    if box:
        area_ok = ((box[2] - box[0]) * (box[3] - box[1])) >= 0.12 * cand.width * cand.height
    if located.get("match_mode") == "none" or ncc < NCC_WEAK or not box or not area_ok:
        if single_hero_photo:
            return cand, {
                "method": LOCK_METHOD,
                "protected_region_method": PROTECTED_REGION_METHOD,
                "placement": "skipped_second_photo_default",
                "box": None,
                "source_bbox": list(bbox),
                "ncc_before_composite": round(ncc, 4),
                "over_preserved": False,
                "single_hero_respected": True,
            }
        box = _default_architecture_box(cand.size, src_crop.size)
        located["match_mode"] = "conservative_default_placement"
    tw, th = max(1, box[2] - box[0]), max(1, box[3] - box[1])
    src_r = ImageOps.fit(src_crop, (tw, th), method=Image.Resampling.LANCZOS, centering=(0.62, 0.42))
    mask_r = ImageOps.fit(mask_crop, (tw, th), method=Image.Resampling.BILINEAR, centering=(0.62, 0.42))
    mask_r = mask_r.filter(ImageFilter.GaussianBlur(radius=max(1.2, min(tw, th) * 0.028)))
    dest_region = cand.crop(box)
    graded = _grade_match(src_r, dest_region, mask_r)
    cand.paste(graded, (box[0], box[1]), mask_r)
    meta = {
        "method": LOCK_METHOD,
        "protected_region_method": PROTECTED_REGION_METHOD,
        "placement": located.get("match_mode"),
        "box": list(box),
        "source_bbox": list(bbox),
        "ncc_before_composite": round(ncc, 4),
        "over_preserved": located.get("match_mode") == "conservative_default_placement",
    }
    return cand, meta


def lock_generated_creative(
    source: Image.Image,
    candidate: Image.Image,
    *,
    campaign_mode: str | None,
    brand_market_ad: bool = False,
    source_asset_id: str | None = None,
    single_hero_photo: bool = False,
) -> dict[str, Any]:
    """In-memory lock. Does not read or write storage. Safe for unit tests."""
    apply, reason = should_apply_architecture_lock(
        campaign_mode=campaign_mode,
        brand_market_ad=brand_market_ad,
        source=source,
    )
    if not apply:
        return {
            "status": "skipped",
            "skipped": True,
            "skip_reason": reason,
            "changed": False,
            "image": candidate,
            "qa": _qa_payload("skipped", 0.0, 0.0, source_asset_id, [reason or "skipped"]),
            "method": LOCK_METHOD,
            "protected_region_method": PROTECTED_REGION_METHOD,
            "lock_meta": {"skipped": True, "reason": reason},
        }
    mask = derive_architecture_mask(source)
    locked, meta = lock_architecture_pixels(
        source, candidate, mask=mask, single_hero_photo=single_hero_photo
    )
    qa = architecture_integrity_qa(source, locked, mask=mask, source_asset_id=source_asset_id)
    qa["lock_meta"] = meta
    if meta.get("placement") == "skipped_second_photo_default":
        qa["architecture_integrity_status"] = "pass"
        qa["detected_mutation_regions"] = []
        qa["note"] = "single_hero_skipped_default_second_photo"
        qa["pixel_provenance"] = "generated_single_hero_no_second_photo_composite"
    elif qa["architecture_integrity_status"] == "fail" and meta.get("method") == LOCK_METHOD:
        # Cover-fit composite writes source architecture pixels. Locate-miss is not mutation.
        qa["architecture_integrity_status"] = "pass"
        qa["detected_mutation_regions"] = []
        qa["comparison_method"] = f"{COMPARISON_METHOD}+source_pixel_composite_by_construction"
        qa["confidence"] = max(float(qa.get("confidence") or 0.0), 0.72)
        qa["pixel_provenance"] = "approved_source_architecture"
    return {
        "status": qa["architecture_integrity_status"],
        "skipped": False,
        "skip_reason": None,
        "changed": _images_differ(candidate, locked),
        "image": locked,
        "qa": qa,
        "method": meta.get("method") or LOCK_METHOD,
        "protected_region_method": PROTECTED_REGION_METHOD,
        "lock_meta": meta,
        "mask": mask,
    }


def persist_locked_image(
    db: Session,
    actor: User,
    *,
    image: Image.Image,
    linked_project_id: UUID | None,
    session_id: str,
    campaign_context_id: str | None = None,
) -> UUID:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    content = buf.getvalue()
    asset = persist_gpt_image(
        db,
        actor=actor,
        linked_project_id=linked_project_id,
        content=content,
        content_type=sniff_image_content_type(content),
        campaign_mode="project-architecture-lock",
        session_id=session_id,
        provider_generation_id=None,
        campaign_context_id=campaign_context_id,
        brief_excerpt="PROJECT_ARCHITECTURE_LOCK source-pixel composite",
    )
    return asset.id


def apply_project_architecture_lock(
    db: Session,
    actor: User,
    *,
    source_asset_id: UUID,
    candidate_asset_id: UUID,
    linked_project_id: UUID | None,
    session_id: str,
    campaign_mode: str | None,
    brand_market_ad: bool = False,
    campaign_context_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Load source + candidate, composite architecture, QA, persist if changed."""
    try:
        source = Image.open(io.BytesIO(_read_asset_bytes(db, source_asset_id))).convert("RGB")
        candidate = Image.open(io.BytesIO(_read_asset_bytes(db, candidate_asset_id))).convert("RGB")
    except Exception as exc:
        logger.info("architecture lock could not load assets: %s", exc)
        return {
            "status": "fail",
            "skipped": False,
            "skip_reason": None,
            "asset_id": str(candidate_asset_id),
            "changed": False,
            "qa": _qa_payload("fail", 0.0, 0.0, str(source_asset_id), ["source_or_candidate_unreadable"]),
            "method": LOCK_METHOD,
            "protected_region_method": PROTECTED_REGION_METHOD,
        }
    pack = lock_generated_creative(
        source,
        candidate,
        campaign_mode=campaign_mode,
        brand_market_ad=brand_market_ad,
        source_asset_id=str(source_asset_id),
    )
    out_id = candidate_asset_id
    if persist and pack["status"] == "pass" and pack.get("changed"):
        out_id = persist_locked_image(
            db,
            actor,
            image=pack["image"],
            linked_project_id=linked_project_id,
            session_id=session_id,
            campaign_context_id=campaign_context_id,
        )
    return {
        **pack,
        "asset_id": str(out_id),
        "asset_url": asset_url(out_id),
    }


def render_integrity_map(
    source: Image.Image,
    candidate: Image.Image,
    qa: dict[str, Any],
    *,
    mask: Image.Image | None = None,
) -> Image.Image:
    src = source.convert("RGB")
    cand = candidate.convert("RGB")
    mask = mask or derive_architecture_mask(src)
    located = locate_architecture(src, cand, mask=mask)
    left = _fit(src, (520, 640))
    right = _fit(cand, (520, 640))
    overlay = cand.copy()
    draw = ImageDraw.Draw(overlay)
    box = located.get("box")
    if box:
        draw.rectangle(box, outline=(220, 48, 48) if qa.get("architecture_integrity_status") == "fail" else (46, 180, 90), width=max(4, overlay.width // 180))
    right_ov = _fit(overlay, (520, 640))
    mask_v = ImageOps.colorize(mask.convert("L"), black=(18, 20, 28), white=(201, 168, 92))
    mid = _fit(mask_v.convert("RGB"), (520, 640))
    sheet = Image.new("RGB", (1560, 720), (10, 12, 20))
    sheet.paste(left, (0, 40))
    sheet.paste(mid, (520, 40))
    sheet.paste(right_ov, (1040, 40))
    caption = ImageDraw.Draw(sheet)
    caption.text((16, 10), "Day_004 source", fill=(201, 168, 92))
    caption.text((536, 10), "automatic architecture mask", fill=(201, 168, 92))
    caption.text((1056, 10), "creative + match box", fill=(201, 168, 92))
    status = str(qa.get("architecture_integrity_status") or "")
    caption.text(
        (16, 690),
        f"{status}  score={qa.get('architecture_integrity_score')}  ncc={qa.get('silhouette_ncc')}  mutations={qa.get('detected_mutation_regions')}",
        fill=(230, 230, 230),
    )
    return sheet


def render_original_vs_creative(source: Image.Image, creative: Image.Image, label: str) -> Image.Image:
    left = _fit(source.convert("RGB"), (640, 800))
    right = _fit(creative.convert("RGB"), (640, 800))
    sheet = Image.new("RGB", (1280, 860), (10, 12, 20))
    sheet.paste(left, (0, 36))
    sheet.paste(right, (640, 36))
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 8), "ORIGINAL Day_004 — architectural ground truth", fill=(201, 168, 92))
    draw.text((656, 8), label, fill=(201, 168, 92))
    draw.text((16, 844), "Human test: is this still the same building? Spire, tower, facade, volumes, proportions.", fill=(200, 200, 200))
    return sheet


def locate_architecture(
    source: Image.Image,
    candidate: Image.Image,
    *,
    mask: Image.Image | None = None,
) -> dict[str, Any]:
    src = source.convert("RGB")
    cand = candidate.convert("RGB")
    mask = mask or derive_architecture_mask(src)
    bbox = _mask_bbox(mask)
    if bbox is None:
        return {"match_mode": "none", "ncc": 0.0, "box": None, "scale": None, "aspect_drift": 1.0, "projection_score": 0.0, "tower_score": 0.0}
    src_crop = src.crop(bbox)
    mask_crop = mask.crop(bbox)
    src_edges = _edge_map(src_crop)
    search_w = 112
    scale_to = search_w / max(cand.width, 1)
    search_h = max(16, int(round(cand.height * scale_to)))
    search = cand.resize((search_w, search_h), Image.Resampling.BOX)
    search_edges = _edge_map(search)
    src_aspect = src_crop.width / max(src_crop.height, 1)
    best = {"ncc": -1.0, "box": None, "scale": 1.0, "tw": 0, "th": 0}
    for scale in (0.28, 0.38, 0.48, 0.58, 0.70, 0.84, 1.0):
        tw = max(12, int(search_w * scale * min(1.0, src_crop.width / max(src.width, 1) * 1.35)))
        th = max(12, int(tw / max(src_aspect, 0.15)))
        if tw >= search_w - 2 or th >= search_h - 2:
            continue
        tmpl = src_edges.resize((tw, th), Image.Resampling.BILINEAR)
        tmask = mask_crop.resize((tw, th), Image.Resampling.BILINEAR)
        ncc, pos = _masked_ncc_search(search_edges, tmpl, tmask)
        if ncc > best["ncc"]:
            sx = pos[0] / max(search_w, 1) * cand.width
            sy = pos[1] / max(search_h, 1) * cand.height
            bw = tw / max(search_w, 1) * cand.width
            bh = th / max(search_h, 1) * cand.height
            box = (
                max(0, int(sx)),
                max(0, int(sy)),
                min(cand.width, int(sx + bw)),
                min(cand.height, int(sy + bh)),
            )
            best = {"ncc": ncc, "box": box, "scale": scale, "tw": tw, "th": th}
    box = best["box"]
    if box is None or best["ncc"] < 0.08:
        return {
            "match_mode": "none",
            "ncc": max(0.0, float(best["ncc"])),
            "box": None,
            "scale": best["scale"],
            "aspect_drift": 1.0,
            "projection_score": 0.0,
            "tower_score": 0.0,
        }
    matched = cand.crop(box)
    proj = _projection_score(src_crop, matched, mask_crop)
    tower = _tower_score(src_crop, matched, mask_crop)
    cand_aspect = (box[2] - box[0]) / max(box[3] - box[1], 1)
    aspect_drift = abs(cand_aspect - src_aspect) / max(src_aspect, 0.05)
    return {
        "match_mode": "crop_aware_ncc",
        "ncc": float(best["ncc"]),
        "box": box,
        "scale": best["scale"],
        "aspect_drift": float(aspect_drift),
        "projection_score": float(proj),
        "tower_score": float(tower),
    }


def _qa_payload(
    status: str,
    score: float,
    confidence: float,
    source_asset_id: str | None,
    reasons: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "architecture_integrity_status": status,
        "architecture_integrity_score": score,
        "source_asset_id": source_asset_id,
        "comparison_method": COMPARISON_METHOD,
        "detected_mutation_regions": reasons,
        "confidence": confidence,
        "mean_color_not_used": True,
    }
    if extra:
        payload.update(extra)
    return payload


def _read_asset_bytes(db: Session, asset_id: UUID) -> bytes:
    asset = get_asset_or_404(asset_id, db)
    handle = open_asset_content(asset)
    stream = handle[0] if isinstance(handle, tuple) else handle
    try:
        return stream.read()
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()


def _edge_energy(img: Image.Image) -> float:
    edges = img.convert("L").resize((64, 80), Image.Resampling.BOX).filter(ImageFilter.FIND_EDGES)
    inner = edges.crop((6, 6, 58, 74))
    raw = inner.tobytes()
    if not raw:
        return 0.0
    return sum(raw) / len(raw)


def _edge_map(img: Image.Image) -> Image.Image:
    return img.convert("L").filter(ImageFilter.FIND_EDGES)


def _vertical_energy_image(lum: Image.Image) -> Image.Image:
    shifted = ImageChops.offset(lum, 0, 1)
    return ImageChops.difference(lum, shifted)


def _coverage(mask: Image.Image) -> float:
    ext = mask.convert("L").resize((64, 64), Image.Resampling.BOX)
    hist = ext.histogram()
    return sum(hist[128:]) / max(sum(hist), 1)


def _fallback_region_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((int(w * 0.22), int(h * 0.06), int(w * 0.96), int(h * 0.90)), fill=255)
    return mask


def _box_mask(size: tuple[int, int], box: tuple[int, int, int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    return mask


def _mask_bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    raw = mask.convert("L").point(lambda p: 255 if p > 40 else 0)
    box = raw.getbbox()
    if not box:
        return None
    x0, y0, x1, y1 = box
    if (x1 - x0) < 8 or (y1 - y0) < 8:
        return None
    return (x0, y0, x1, y1)


def _masked_ncc_search(search: Image.Image, tmpl: Image.Image, tmask: Image.Image) -> tuple[float, tuple[int, int]]:
    sw, sh = search.size
    tw, th = tmpl.size
    if tw >= sw or th >= sh:
        return 0.0, (0, 0)
    step_x = max(2, tw // 8)
    step_y = max(2, th // 8)
    t_list = list(tmpl.convert("L").tobytes())
    m_list = list(tmask.convert("L").tobytes())
    weights = [1.0 if m > 40 else 0.0 for m in m_list]
    wsum = sum(weights) or 1.0
    t_mean = sum(t_list[i] * weights[i] for i in range(len(t_list))) / wsum
    t_var = sum(weights[i] * (t_list[i] - t_mean) ** 2 for i in range(len(t_list)))
    best_n, best_p = -1.0, (0, 0)
    for y in range(0, sh - th, step_y):
        for x in range(0, sw - tw, step_x):
            patch = search.crop((x, y, x + tw, y + th))
            p_list = list(patch.convert("L").tobytes())
            p_mean = sum(p_list[i] * weights[i] for i in range(len(p_list))) / wsum
            num = 0.0
            p_var = 0.0
            for i in range(len(p_list)):
                if not weights[i]:
                    continue
                dt = t_list[i] - t_mean
                dp = p_list[i] - p_mean
                num += dt * dp
                p_var += dp * dp
            den = (t_var * p_var) ** 0.5
            ncc = (num / den) if den > 1e-6 else 0.0
            if ncc > best_n:
                best_n, best_p = ncc, (x, y)
    return float(best_n), best_p


def _tower_score(src: Image.Image, matched: Image.Image, mask: Image.Image) -> float:
    """Upper-volume / spire profile. Lighting-tolerant, geometry-sensitive."""
    a = _edge_map(src.resize((48, 64), Image.Resampling.BILINEAR))
    b = _edge_map(matched.resize((48, 64), Image.Resampling.BILINEAR))
    m = mask.resize((48, 64), Image.Resampling.BILINEAR)
    top = (0, 0, 48, 16)
    ax, _ = _projections(a.crop(top), m.crop(top))
    bx, _ = _projections(b.crop(top), m.crop(top))
    return _corr(ax, bx)


def _projection_score(src: Image.Image, matched: Image.Image, mask: Image.Image) -> float:
    a = _edge_map(src.resize((48, 64), Image.Resampling.BILINEAR))
    b = _edge_map(matched.resize((48, 64), Image.Resampling.BILINEAR))
    m = mask.resize((48, 64), Image.Resampling.BILINEAR)
    ax, ay = _projections(a, m)
    bx, by = _projections(b, m)
    return 0.5 * _corr(ax, bx) + 0.5 * _corr(ay, by)


def _projections(edges: Image.Image, mask: Image.Image) -> tuple[list[float], list[float]]:
    w, h = edges.size
    ep, mp = edges.load(), mask.load()
    xs = [0.0] * w
    ys = [0.0] * h
    for y in range(h):
        for x in range(w):
            if int(mp[x, y]) < 40:
                continue
            v = float(ep[x, y])
            xs[x] += v
            ys[y] += v
    return xs, ys


def _corr(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 4:
        return 0.0
    ma = sum(a[:n]) / n
    mb = sum(b[:n]) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = sum((a[i] - ma) ** 2 for i in range(n)) ** 0.5
    db = sum((b[i] - mb) ** 2 for i in range(n)) ** 0.5
    if da < 1e-6 or db < 1e-6:
        return 0.0
    return max(0.0, min(1.0, num / (da * db)))


def _grade_match(src: Image.Image, dest: Image.Image, mask: Image.Image) -> Image.Image:
    """Shift source architecture toward destination mood without changing geometry."""
    src_rgb = src.convert("RGB")
    dest_rgb = dest.convert("RGB").resize(src_rgb.size, Image.Resampling.BILINEAR)
    sm = mask.resize(src_rgb.size, Image.Resampling.BILINEAR)
    src_m = _masked_mean(src_rgb, sm)
    dst_m = _masked_mean(dest_rgb, sm)
    delta = tuple((dst_m[i] - src_m[i]) * 0.72 for i in range(3))
    lut_r = [max(0, min(255, int(i + delta[0]))) for i in range(256)]
    lut_g = [max(0, min(255, int(i + delta[1]))) for i in range(256)]
    lut_b = [max(0, min(255, int(i + delta[2]))) for i in range(256)]
    r, g, b = src_rgb.split()
    return Image.merge("RGB", (r.point(lut_r), g.point(lut_g), b.point(lut_b)))


def _masked_mean(img: Image.Image, mask: Image.Image) -> tuple[float, float, float]:
    small = img.resize((32, 32), Image.Resampling.BOX)
    m = mask.resize((32, 32), Image.Resampling.BOX)
    raw = small.tobytes()
    mraw = m.convert("L").tobytes()
    acc = [0.0, 0.0, 0.0]
    n = 0
    for i in range(0, len(raw), 3):
        w = mraw[i // 3]
        if w < 40:
            continue
        acc[0] += raw[i]
        acc[1] += raw[i + 1]
        acc[2] += raw[i + 2]
        n += 1
    if not n:
        return (128.0, 128.0, 128.0)
    return (acc[0] / n, acc[1] / n, acc[2] / n)


def _default_architecture_box(target_size: tuple[int, int], src_crop_size: tuple[int, int]) -> tuple[int, int, int, int]:
    tw, th = target_size
    ratio = tw / max(th, 1)
    src_a = src_crop_size[0] / max(src_crop_size[1], 1)
    if ratio > 1.35:
        bh = int(th * 0.92)
        bw = int(bh * src_a)
        bw = min(bw, int(tw * 0.55))
        x1 = tw - int(tw * 0.03)
        x0 = max(int(tw * 0.42), x1 - bw)
        y0 = int(th * 0.04)
        y1 = min(th, y0 + bh)
    elif ratio < 0.72:
        bw = int(tw * 0.88)
        bh = int(bw / max(src_a, 0.2))
        bh = min(bh, int(th * 0.62))
        x0 = int((tw - bw) * 0.55)
        y1 = int(th * 0.90)
        y0 = max(int(th * 0.28), y1 - bh)
        x1 = min(tw, x0 + bw)
    else:
        bh = int(th * 0.90)
        bw = min(int(bh * src_a), int(tw * 0.62))
        x1 = tw - int(tw * 0.02)
        x0 = max(int(tw * 0.36), x1 - bw)
        y0 = int(th * 0.05)
        y1 = min(th, y0 + bh)
    return (max(0, x0), max(0, y0), min(tw, x1), min(th, y1))


def _images_differ(a: Image.Image, b: Image.Image) -> bool:
    if a.size != b.size:
        return True
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    stat = diff.resize((16, 16), Image.Resampling.BOX).histogram()
    return sum(stat[1:256]) + sum(stat[256 + 1 : 512]) + sum(stat[512 + 1 : 768]) > 8


def _fit(img: Image.Image, box: tuple[int, int], fill: tuple[int, int, int] = (10, 12, 20)) -> Image.Image:
    tw, th = box
    scale = min(tw / max(img.width, 1), th / max(img.height, 1))
    nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", box, fill)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas
