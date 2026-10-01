"""Phase 5.4H — Photo-to-family eligibility gate.

Eligibility before preference. Does not invent families. Does not promote.
GPT Image calls = 0. Does not execute image replacement. Does not run 5.5.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.adaptive_composition_engine import compose_adaptive
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.family_composition_constraints import all_family_constraints
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import (
    APPROVED_R1_ASSET_ID,
    _HISTORY_KEYS as _BASE_HISTORY,
    _font,
    _preserve as _preserve_base,
    _wrap,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.photo_family_eligibility import (
    ALL_MASTER_FAMILIES,
    evaluate_all_families,
    evaluate_image_for_creative_use,
    family_compatibility_rules,
    is_approved_exterior_filename,
    rank_eligible_families,
)
from investhome_api.services.creative_director.photo_occupancy_map import occupancy_to_json, render_occupancy_map
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54H = "phase5_4h_photo_family_eligibility"
MAX_SUITABILITY_IMAGES = 12
_HISTORY_KEYS = _BASE_HISTORY + (
    ("creative_quality_tests", "quality54b"),
    ("creative_quality_r1_tests", "quality54b_r1"),
    ("generative_master_tests", "quality54c"),
    ("graphic_field_master_tests", "quality54e"),
    ("master_family_tests", "quality54f"),
    ("final_composition_tests", "quality54g"),
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54b"] = list(blob.get("creative_quality_tests") or [])
    preserved["quality54b_r1"] = list(blob.get("creative_quality_r1_tests") or [])
    preserved["quality54c"] = list(blob.get("generative_master_tests") or [])
    preserved["quality54e"] = list(blob.get("graphic_field_master_tests") or [])
    preserved["quality54f"] = list(blob.get("master_family_tests") or [])
    preserved["quality54g"] = list(blob.get("final_composition_tests") or [])
    return preserved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Image.Image):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if not str(k).startswith("_") and k not in {"layers", "occupancy", "foundation"}}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _library() -> dict[str, Any]:
    catalog = {name: seeded_reference_family(name) for name in GRADE_A_ORDER}
    return build_family_library(catalog)


def list_temple_exterior_assets(db: Session) -> list[CreativeStudioMediaAsset]:
    rows = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == UUID(TEMPLE_PROJECT_ID),
                CreativeStudioMediaAsset.archived_at.is_(None),
                CreativeStudioMediaAsset.content_type.ilike("image/%"),
            )
        ).all()
    )
    exteriors = [row for row in rows if is_approved_exterior_filename(row.filename, row.content_type)]
    hero = next((row for row in rows if str(row.id) == LOCKED_HERO_ASSET_ID), None)
    others = [row for row in exteriors if str(row.id) != LOCKED_HERO_ASSET_ID]
    others.sort(
        key=lambda row: (
            0 if "exterior" in (row.filename or "").lower() else 1,
            0 if "day_" in (row.filename or "").lower() else 1,
            row.filename or "",
        )
    )
    chosen: list[CreativeStudioMediaAsset] = []
    if hero is not None:
        chosen.append(hero)
    for row in others:
        if len(chosen) >= MAX_SUITABILITY_IMAGES:
            break
        chosen.append(row)
    return chosen


def render_composition_class(foundation: Image.Image, occupancy: dict[str, Any], composition: dict[str, Any]) -> Image.Image:
    board = render_occupancy_map(foundation, occupancy)
    draw = ImageDraw.Draw(board)
    draw.text((36, 910), "PROJECT PHOTO COMPOSITION CLASS", fill=(201, 168, 92), font=_font(16))
    draw.text((36, 936), str(composition.get("primary_class") or ""), fill=(236, 230, 218), font=_font(20))
    y = 970
    for trait in list(composition.get("traits") or []):
        draw.text((36, y), trait, fill=(180, 176, 168), font=_font(14))
        y += 22
        if y > 1040:
            break
    meas = dict(composition.get("measurements") or {})
    draw.text(
        (780, 910),
        f"sky {meas.get('sky_area')}  hard {meas.get('hard_protected')}  top {meas.get('top_band_height')}",
        fill=(180, 176, 168),
        font=_font(13),
    )
    return board.crop((0, 0, board.size[0], min(board.size[1], 1080)))


def render_eligibility_matrix(results: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1480, 820), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "FAMILY ELIGIBILITY MATRIX  —  eligibility before preference", fill=(201, 168, 92), font=_font(20))
    checks = (
        "required_negative_space",
        "commercial_space",
        "logo_space",
        "cta_space",
        "contrast",
        "family_identity",
        "architecture_clearance",
        "content_density",
    )
    x0 = 280
    for i, name in enumerate(checks):
        draw.text((x0 + i * 140, 70), name.replace("_", "\n"), fill=(160, 156, 148), font=_font(11))
    y = 140
    for item in results:
        status = str(item.get("status") or "")
        color = {"ELIGIBLE": (80, 200, 120), "CONDITIONALLY_ELIGIBLE": (201, 168, 92), "NOT_ELIGIBLE": (220, 80, 80)}.get(
            status, (180, 176, 168)
        )
        draw.text((36, y), str(item.get("family_id") or ""), fill=(236, 230, 218), font=_font(14))
        draw.text((36, y + 22), status, fill=color, font=_font(13))
        detail = dict(item.get("checks") or {})
        for i, name in enumerate(checks):
            ok = bool((detail.get(name) or {}).get("pass"))
            draw.text((x0 + i * 140, y), "PASS" if ok else "FAIL", fill=(80, 200, 120) if ok else (220, 80, 80), font=_font(13))
        reason = str(item.get("primary_reason") or "")
        for line in _wrap(reason, 88)[:2]:
            draw.text((36, y + 46), line, fill=(160, 156, 148), font=_font(12))
            y += 16
        y += 78
    return canvas


def render_density_profile(density: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 780), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 28), "CAMPAIGN DENSITY PROFILE", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 70), str(density.get("level") or ""), fill=(236, 230, 218), font=_font(36))
    draw.text((36, 122), f"semantic groups  {density.get('semantic_groups')}", fill=(180, 176, 168), font=_font(16))
    y = 170
    for unit in list(density.get("copy_units") or []):
        draw.text((36, y), str(unit), fill=(236, 230, 218), font=_font(18))
        y += 32
    lockup = dict(density.get("measured_lockup") or {})
    y += 20
    draw.text((36, y), "Measured lockup at production scale 1.0", fill=(201, 168, 92), font=_font(14))
    y += 28
    for key, value in lockup.items():
        draw.text((36, y), f"{key}  {value}", fill=(180, 176, 168), font=_font(14))
        y += 24
    draw.text((36, 720), "A family that supports only LOW cannot receive HIGH-density content.", fill=(160, 156, 148), font=_font(13))
    return canvas


def render_compatibility_rules(rules: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "FAMILY PHOTO COMPATIBILITY RULES", fill=(201, 168, 92), font=_font(20))
    y = 70
    for family_id, spec in dict(rules.get("families") or {}).items():
        draw.text((36, y), family_id, fill=(236, 230, 218), font=_font(16))
        y += 26
        req = spec.get("requires") or []
        text = "; ".join(req) if isinstance(req, list) else str(req)
        for line in _wrap(f"requires: {text}", 92):
            draw.text((52, y), line, fill=(180, 176, 168), font=_font(13))
            y += 20
        draw.text(
            (52, y),
            f"min field {spec.get('min_contiguous_width')} x {spec.get('min_contiguous_height')}   max density {spec.get('max_campaign_density')}",
            fill=(160, 156, 148),
            font=_font(13),
        )
        y += 40
    draw.text((36, 930), str(rules.get("note") or ""), fill=(160, 156, 148), font=_font(13))
    return canvas


def render_suitability_ranking(rows: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1480, 920), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "TEMPLE APPROVED EXTERIOR — CREATIVE SUITABILITY", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 58), "Best architectural render is not always the best advertising canvas. Read-only. No replacement.", fill=(160, 156, 148), font=_font(13))
    y = 96
    for idx, row in enumerate(rows[:8], start=1):
        suit = dict(row.get("suitability") or {})
        band = str(suit.get("band") or "")
        color = {"HIGH": (80, 200, 120), "MEDIUM": (201, 168, 92), "LOW": (220, 80, 80)}.get(band, (180, 176, 168))
        draw.text((36, y), f"{idx}.  {row.get('filename')}", fill=(236, 230, 218), font=_font(14))
        draw.text((36, y + 22), str(row.get("asset_id")), fill=(140, 136, 128), font=_font(12))
        draw.text((900, y), f"{band}  {suit.get('score')}", fill=color, font=_font(16))
        fams = ", ".join(suit.get("compatible_master_families") or []) or "none"
        draw.text((36, y + 42), f"{row.get('composition')}   families: {fams}", fill=(180, 176, 168), font=_font(13))
        y += 88
    return canvas


def render_decision_board(record: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 860), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "PHASE 5.4H DECISION BOARD", fill=(201, 168, 92), font=_font(22))
    status = str(record.get("status") or "")
    draw.text((36, 70), status, fill=(236, 230, 218), font=_font(28))
    lines = [
        f"Day_004 class  {record.get('day004_composition_class')}",
        f"Campaign density  {record.get('campaign_density')}",
        f"Eligible families  {record.get('eligible_count')}",
        f"Day_004 suitability  {record.get('day004_creative_suitability')}",
        f"NO_EXISTING_FAMILY_FITS  {'YES' if record.get('no_existing_family_fits') else 'NO'}",
        f"Missing family  {record.get('missing_family_requirement') or '—'}",
        f"GPT Image  {record.get('gpt_image_calls')}   Vision  {record.get('vision_calls')}",
        "Existing master changed  NO",
        "Production cover changed  NO",
        "Image replacement executed  NO",
        "New family created  NO",
    ]
    y = 130
    for line in lines:
        for chunk in _wrap(str(line), 88):
            draw.text((36, y), chunk, fill=(180, 176, 168), font=_font(16))
            y += 28
    return canvas


def render_eligible_proof(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1480, 820), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "ELIGIBLE FAMILY PROOF  —  rendered only because geometry fits", fill=(201, 168, 92), font=_font(18))
    x = 36
    for item in candidates:
        image = item.get("image")
        if not isinstance(image, Image.Image):
            continue
        tile = image.copy()
        tile.thumbnail((450, 560), Image.Resampling.LANCZOS)
        canvas.paste(tile, (x, 70))
        draw.text((x, 650), str(item.get("family_id") or ""), fill=(236, 230, 218), font=_font(14))
        x += 470
    return canvas


def generate_photo_family_eligibility_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]

    reset_provider_call_count()
    vision_calls = 0
    lock_failed: list[str] = []
    status = "FAIL_FAST_MISSING_HERO"
    images: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []
    library_blob = _library()
    fonts = build_font_registry()
    families = [family_by_id(library_blob, family_id) for family_id in ALL_MASTER_FAMILIES]
    eligibility: dict[str, Any] | None = None
    ranking: dict[str, Any] | None = None
    suitability_rows: list[dict[str, Any]] = []
    occupancy_json: dict[str, Any] | None = None
    density: dict[str, Any] | None = None

    try:
        source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
    except Exception as exc:
        lock_failed.append(f"HERO_UNREADABLE:{exc}")
        source = None

    if source is not None:
        # PHOTO ANALYSIS → FAMILY ELIGIBILITY
        eligibility = evaluate_all_families(source=source, families=families, fonts=fonts)
        occupancy_json = occupancy_to_json(dict(eligibility.get("occupancy") or {}))
        density = dict(eligibility.get("density") or {})
        foundation = eligibility.get("foundation")
        occupancy = dict(eligibility.get("occupancy") or {})
        # ELIGIBLE FAMILY RANKING  (preference only among families that already passed the gate)
        ranking = rank_eligible_families(
            library_blob,
            eligibility,
            photo=foundation if isinstance(foundation, Image.Image) else source,
            protection={"regions": {}},
        )
        images["composition"] = render_composition_class(
            foundation if isinstance(foundation, Image.Image) else source,
            occupancy,
            dict(eligibility.get("composition") or {}),
        )
        images["matrix"] = render_eligibility_matrix(list(eligibility.get("results") or []))
        images["density"] = render_density_profile(density)
        images["compatibility"] = render_compatibility_rules(family_compatibility_rules())

        assets = list_temple_exterior_assets(db)
        for asset in assets:
            try:
                raw = _read_bytes(db, asset.id)
                photo = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                continue
            pack = evaluate_image_for_creative_use(source=photo, families=families, fonts=fonts)
            suitability_rows.append(
                {
                    "asset_id": str(asset.id),
                    "filename": asset.filename,
                    "content_type": asset.content_type,
                    "is_day004": str(asset.id) == LOCKED_HERO_ASSET_ID,
                    "composition": (pack.get("composition") or {}).get("primary_class"),
                    "traits": (pack.get("composition") or {}).get("traits"),
                    "family_results": [
                        {"family_id": r.get("family_id"), "status": r.get("status"), "primary_reason": r.get("primary_reason")}
                        for r in list(pack.get("results") or [])
                    ],
                    "suitability": pack.get("suitability"),
                    "replacement_executed": False,
                }
            )
        suitability_rows.sort(key=lambda item: float((item.get("suitability") or {}).get("score") or 0), reverse=True)
        images["suitability"] = render_suitability_ranking(suitability_rows)

        eligible_ids = list(eligibility.get("eligible_family_ids") or [])
        if eligible_ids:
            logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
            logo_rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
            for family_id in eligible_ids:
                family = family_by_id(library_blob, family_id)
                pack = compose_adaptive(source=source, family=family, fonts=fonts, logo_rgba=logo_rgba)
                asset = persist_gpt_image(
                    db,
                    actor=user,
                    linked_project_id=row.linked_project_id,
                    content=_png(pack["image"]),
                    content_type="image/png",
                    campaign_mode="project-eligible-family-proof",
                    session_id=str(uuid4()),
                    provider_generation_id=None,
                    campaign_context_id=str(row.id),
                    brief_excerpt=f"PHASE 5.4H eligible proof {family_id}",
                )
                candidates.append(
                    {
                        "family_id": family_id,
                        "asset_id": str(asset.id),
                        "flex_mode": pack.get("flex_mode"),
                        "scale": pack.get("scale"),
                        "solved": pack.get("solved"),
                        "image": pack["image"],
                    }
                )
            images["proof"] = render_eligible_proof(candidates)
            status = "ELIGIBLE_FAMILIES_RENDERED"
        elif eligibility.get("no_existing_family_fits"):
            status = "NO_EXISTING_FAMILY_FITS"
        else:
            status = "NO_ELIGIBLE_FAMILY_NO_RENDER"

    gpt_calls = provider_call_count()
    top = suitability_rows[0] if suitability_rows else None
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54H,
        "created_at": _now(),
        "status": status,
        "eligibility_engine": "PhotoFamilyEligibilityEngineV1",
        "pipeline": ["PHOTO ANALYSIS", "FAMILY ELIGIBILITY", "ELIGIBLE FAMILY RANKING", "ADAPTIVE COMPOSITION"],
        "day004_composition_class": dict((eligibility or {}).get("composition") or {}).get("primary_class"),
        "day004_traits": dict((eligibility or {}).get("composition") or {}).get("traits"),
        "campaign_density": (density or {}).get("level") if density else None,
        "family_eligibility": [
            {
                "family_id": item.get("family_id"),
                "status": item.get("status"),
                "primary_reason": item.get("primary_reason"),
                "reasons": item.get("reasons"),
                "failed": item.get("failed"),
            }
            for item in list((eligibility or {}).get("results") or [])
        ],
        "eligible_count": int((eligibility or {}).get("eligible_count") or 0),
        "conditional_family_ids": list((eligibility or {}).get("conditional_family_ids") or []),
        "eligible_family_ids": list((eligibility or {}).get("eligible_family_ids") or []),
        "day004_creative_suitability": (eligibility or {}).get("day004_creative_suitability"),
        "no_existing_family_fits": bool((eligibility or {}).get("no_existing_family_fits")),
        "missing_family_requirement": (eligibility or {}).get("missing_family_requirement"),
        "eligible_ranking": _jsonable(ranking),
        "project_image_suitability": suitability_rows,
        "top_approved_temple_image": {
            "asset_id": (top or {}).get("asset_id"),
            "filename": (top or {}).get("filename"),
            "compatible_families": ((top or {}).get("suitability") or {}).get("compatible_master_families"),
            "reason": f"highest advertising-canvas score {((top or {}).get('suitability') or {}).get('score')} / {(top or {}).get('composition')}",
        }
        if top
        else None,
        "top5": [
            {
                "rank": i,
                "asset_id": item.get("asset_id"),
                "filename": item.get("filename"),
                "score": ((item.get("suitability") or {}).get("score")),
                "band": ((item.get("suitability") or {}).get("band")),
                "composition": item.get("composition"),
                "compatible_families": ((item.get("suitability") or {}).get("compatible_master_families")),
            }
            for i, item in enumerate(suitability_rows[:5], start=1)
        ],
        "candidates": [{k: v for k, v in item.items() if k != "image"} for item in candidates],
        "lock_failed": lock_failed,
        "generation_model": None,
        "gpt_image_calls": gpt_calls,
        "vision_calls": vision_calls,
        "live_routing_active": False,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "image_replacement_executed": False,
        "new_family_created": False,
        "project_id": TEMPLE_PROJECT_ID,
        "source_photo": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "phase55_executed": False,
        "formats_created": False,
        "video_started": False,
        "user_facing_template_picker": False,
        "family_constraints": all_family_constraints(),
        "family_compatibility": family_compatibility_rules(),
        "occupancy_map": occupancy_json,
        "density_profile": density,
        "composition": _jsonable((eligibility or {}).get("composition")),
    }
    images["decision"] = render_decision_board(record)
    tests = [
        t
        for t in list(blob.get("photo_family_eligibility_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54H)
    ]
    stored = json.loads(json.dumps(record, default=str))
    tests.append(stored)
    blob["photo_family_eligibility_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if blob.get("premium_commercial_r1_tests") != preserved["r1"]:
        raise RuntimeError("Phase 5.4H refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4H refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4H refused to modify approved creative masters")
    if blob.get("graphic_field_master_tests") != preserved.get("quality54e"):
        raise RuntimeError("Phase 5.4H refused to overwrite Phase 5.4E history")
    if blob.get("master_family_tests") != preserved.get("quality54f"):
        raise RuntimeError("Phase 5.4H refused to overwrite Phase 5.4F history")
    if blob.get("final_composition_tests") != preserved.get("quality54g"):
        raise RuntimeError("Phase 5.4H refused to overwrite Phase 5.4G history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4H refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library_blob
    record["candidate_images"] = candidates
    record["eligibility"] = _jsonable(eligibility)
    _ = language
    return record
