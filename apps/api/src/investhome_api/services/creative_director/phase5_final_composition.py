"""Phase 5.4G — Adaptive composition engine. Photo-aware family executions.

Not a new master-creation architecture. Recompose EDITORIAL_DARK_FIELD,
TYPE_IN_PLANE, and SKY_EDITORIAL around Day_004 occupancy.

GPT Image calls = 0. Does not promote. Does not touch master, cover, or 5.5.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.adaptive_composition_engine import compose_adaptive, occupancy_aware_crop
from investhome_api.services.creative_director.commercial_offer_composer import render_commercial_proof
from investhome_api.services.creative_director.creative_collision_engine import render_collision_proof
from investhome_api.services.creative_director.creative_contrast_engine import render_contrast_map
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_family_router import rank_families
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import (
    attach_media_library_mapping,
    build_reference_library,
    index_design_references_folder,
    locate_design_references,
)
from investhome_api.services.creative_director.family_composition_constraints import (
    PROOF_FAMILIES,
    all_family_constraints,
    render_constraint_map,
)
from investhome_api.services.creative_director.graphic_field_director import architecture_protection_mask_v2
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import (
    APPROVED_R1_ASSET_ID,
    _HISTORY_KEYS as _BASE_HISTORY,
    _font,
    _preserve as _preserve_base,
    _wrap,
)
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_photo_foundation import architecture_provenance_qa
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_creative import (
    HEURISTIC_PROTECTION,
    _jpeg_b64,
    request_protection_map,
)
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
from investhome_api.services.creative_director.photo_occupancy_map import (
    occupancy_to_json,
    render_occupancy_map,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_54G = "phase5_4g_final_composition"
_HISTORY_KEYS = _BASE_HISTORY + (
    ("creative_quality_tests", "quality54b"),
    ("creative_quality_r1_tests", "quality54b_r1"),
    ("generative_master_tests", "quality54c"),
    ("graphic_field_master_tests", "quality54e"),
    ("master_family_tests", "quality54f"),
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54b"] = list(blob.get("creative_quality_tests") or [])
    preserved["quality54b_r1"] = list(blob.get("creative_quality_r1_tests") or [])
    preserved["quality54c"] = list(blob.get("generative_master_tests") or [])
    preserved["quality54e"] = list(blob.get("graphic_field_master_tests") or [])
    preserved["quality54f"] = list(blob.get("master_family_tests") or [])
    return preserved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Image.Image):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if not str(k).startswith("_") and k not in {"layers", "occupancy"}}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def flatten_critic(parsed: dict[str, Any] | None) -> dict[str, Any]:
    parsed = dict(parsed or {})
    if parsed.get("professional_art_direction") is not None:
        parsed["mode"] = "vision"
        return parsed
    for key in ("Image 1", "candidate", "adaptation", "scores"):
        inner = parsed.get(key)
        if isinstance(inner, dict) and inner.get("professional_art_direction") is not None:
            out = dict(inner)
            out["mode"] = "vision"
            out["notes"] = parsed.get("notes") or inner.get("notes")
            return out
    parsed["mode"] = "unavailable"
    return parsed


def request_composition_critic(*, candidate: Image.Image, foundation: Image.Image, family_id: str) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Independent luxury real-estate art director. Score the FINAL compositor output. Do not inflate. JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Family {family_id}. Image 1 = Temple adaptive composition. Image 2 = Day_004 foundation. "
                            "Scores 0-10: professional_art_direction, family_fidelity, composition, "
                            "image_design_integration, typography, hierarchy, commercial_clarity, logo_integration, "
                            "cta_integration, premium_character, readability, architecture_fidelity, publishability. "
                            "Also: spire_collision, unreadable, listing_card, dashboard, malformed_turkish, "
                            "architecture_modified, notes. Visual scores must not invent technical facts."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    return flatten_critic(parsed), calls


def hard_reject_54g(*, preflight: dict[str, Any], pack: dict[str, Any], critic: dict[str, Any]) -> list[str]:
    reasons = [f"preflight_{k}" for k, v in dict(preflight.get("checks") or {}).items() if v != "PASS"]
    if critic.get("listing_card"):
        reasons.append("listing_card_appearance")
    if critic.get("dashboard"):
        reasons.append("dashboard_appearance")
    if critic.get("malformed_turkish") and not turkish_copy_is_valid(pack.get("facts") or {}):
        reasons.append("malformed_turkish")
    if critic.get("architecture_modified") and not preflight.get("architecture_pixels_unchanged"):
        reasons.append("architecture_modification")
    if critic.get("spire_collision") and (preflight.get("collision") or {}).get("pass"):
        pass
    elif critic.get("spire_collision") and not (preflight.get("collision") or {}).get("pass"):
        reasons.append("text_spire_collision")
    return sorted(set(reasons))


def render_three_way(candidates: list[dict[str, Any]]) -> Image.Image:
    tiles = []
    for item in candidates:
        im = item.get("image")
        if not isinstance(im, Image.Image):
            continue
        resized = im.copy().resize((360, 450), Image.Resampling.LANCZOS)
        bar = 56
        tile = Image.new("RGB", (resized.width, resized.height + bar), (12, 14, 20))
        tile.paste(resized, (0, bar))
        ImageDraw.Draw(tile).text((12, 10), f"{item.get('key')}  {item.get('family_id')}", fill=(201, 168, 92), font=_font(13))
        ImageDraw.Draw(tile).text((12, 30), f"flex {item.get('flex_mode')}  preflight {item.get('technical_preflight')}", fill=(180, 176, 168), font=_font(12))
        tiles.append(tile)
    if not tiles:
        return Image.new("RGB", (1088, 400), (12, 14, 20))
    gap = 20
    out = Image.new("RGB", (sum(t.width for t in tiles) + gap * (len(tiles) + 1), tiles[0].height + 40), (12, 14, 20))
    x = gap
    for tile in tiles:
        out.paste(tile, (x, 20))
        x += tile.width + gap
    return out


def render_revision_board(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "REVISION READINESS  —  VISUAL_REPLACE uses graphic_field", fill=(201, 168, 92), font=_font(20))
    y = 80
    for item in candidates:
        ready = dict((item.get("revision_readiness_detail") or {}).get("checks") or {})
        spec = dict(item.get("spec") or {})
        field = dict(spec.get("graphic_field") or {})
        draw.text((36, y), f"{item.get('key')}  {item.get('family_id')}", fill=(236, 230, 218), font=_font(18))
        y += 28
        draw.text(
            (36, y),
            f"PRICE={ready.get('PRICE_EDIT_ONLY')}  COPY={ready.get('COPY_EDIT_ONLY')}  VISUAL={ready.get('VISUAL_REPLACE_ONLY')}",
            fill=(180, 176, 168),
            font=_font(16),
        )
        y += 24
        draw.text(
            (36, y),
            f"graphic_field asset={field.get('asset_id')}  role={field.get('semantic_role')}  overlay={field.get('overlay')}",
            fill=(160, 156, 148),
            font=_font(14),
        )
        y += 48
    draw.text((36, y), "No PRICE / COPY / VISUAL commands were executed.", fill=(201, 168, 92), font=_font(14))
    return canvas


def render_human_board(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "HUMAN REVIEW BOARD — 5.4G ADAPTIVE COMPOSITION", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 52), "GPT IMAGE 0. TECHNICAL PASS ≠ VISUAL APPROVAL. DO NOT PROMOTE.", fill=(236, 230, 218), font=_font(16))
    x = 36
    for item in candidates:
        im = item.get("image")
        if isinstance(im, Image.Image):
            tile = im.copy().resize((380, 475), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 90))
        critic = dict(item.get("critic") or {})
        draw.text((x, 578), f"{item.get('key')} {item.get('family_id')}", fill=(236, 230, 218), font=_font(14))
        draw.text((x, 600), f"flex {item.get('flex_mode')}", fill=(180, 176, 168), font=_font(13))
        draw.text(
            (x, 622),
            f"tech {item.get('technical_preflight')}  art {critic.get('professional_art_direction')}  pub {critic.get('publishability')}",
            fill=(180, 176, 168),
            font=_font(13),
        )
        draw.text((x, 644), "PENDING HUMAN REVIEW", fill=(201, 168, 92), font=_font(14))
        x += 410
    draw.text((36, 700), "Approved master and production cover were not modified.", fill=(180, 176, 168), font=_font(14))
    draw.text((36, 726), "Phase 5.5 was not executed. Vision scores do not override occupancy collision or UTF-8 facts.", fill=(180, 176, 168), font=_font(14))
    return canvas


def generate_final_composition_4x5(
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
    location = locate_design_references(db)
    if location.get("found") and (location.get("folder") or {}).get("drive_folder_id"):
        index_result = index_design_references_folder(db, location)
        location = attach_media_library_mapping(db, location)
        location["index_result"] = index_result

    vision_calls = 0
    lock_failed: list[str] = []
    status = "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    images: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []
    library_blob: dict[str, Any] | None = None
    ranking: dict[str, Any] | None = None
    occupancy_blob: dict[str, Any] | None = None
    occupancy_json: dict[str, Any] | None = None
    specs: list[dict[str, Any]] = []
    provenance: dict[str, Any] | None = None
    preflight_report: list[dict[str, Any]] = []

    if location.get("found"):
        ref_library = build_reference_library(db, location)
        if int(ref_library.get("image_count") or 0) <= 0:
            lock_failed.append("DESIGN_REFERENCES_EMPTY")
            status = "FAIL_FAST_EMPTY_DESIGN_REFERENCES"
        else:
            catalog = {name: seeded_reference_family(name) for name in GRADE_A_ORDER}
            library_blob = build_family_library(catalog)
            fonts = build_font_registry()
            source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
            logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
            logo_rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
            probe_family = family_by_id(library_blob, "SKY_EDITORIAL")
            probe, _crop, occupancy_blob = occupancy_aware_crop(source, probe_family)
            occupancy_json = occupancy_to_json(occupancy_blob)
            protection, calls = request_protection_map(probe)
            vision_calls += calls
            if not (protection.get("regions") or {}).get("SPIRE"):
                protection = {"schema": "ProtectedArchitectureMapV1", "regions": dict(HEURISTIC_PROTECTION), "mode": "heuristic"}
            protection["occupancy_hard_l"] = (occupancy_blob.get("layers") or {}).get("hard_protected")
            mask = architecture_protection_mask_v2(probe, protection)
            ranking = rank_families(library_blob, photo=probe, protection=protection, commercial_density=6)
            images["occupancy"] = render_occupancy_map(probe, occupancy_blob)
            images["constraints"] = render_constraint_map(list((library_blob or {}).get("families") or []))
            for idx, family_id in enumerate(PROOF_FAMILIES, start=1):
                family = family_by_id(library_blob, family_id)
                pack = compose_adaptive(
                    source=source,
                    family=family,
                    fonts=fonts,
                    logo_rgba=logo_rgba,
                    protection=protection,
                )
                field_asset = persist_gpt_image(
                    db,
                    actor=user,
                    linked_project_id=row.linked_project_id,
                    content=_png(pack["fielded"]),
                    content_type="image/png",
                    campaign_mode="project-adaptive-graphic-field",
                    session_id=str(uuid4()),
                    provider_generation_id=None,
                    campaign_context_id=str(row.id),
                    brief_excerpt=f"PHASE 5.4G G-F{idx} graphic_field {family_id}",
                )
                pack["graphic_field_asset_id"] = str(field_asset.id)
                asset = persist_gpt_image(
                    db,
                    actor=user,
                    linked_project_id=row.linked_project_id,
                    content=_png(pack["image"]),
                    content_type="image/png",
                    campaign_mode="project-adaptive-composition-candidate",
                    session_id=str(uuid4()),
                    provider_generation_id=None,
                    campaign_context_id=str(row.id),
                    brief_excerpt=f"PHASE 5.4G G-F{idx} {family_id}",
                )
                spec = build_family_master_spec(
                    key=f"G-F{idx}",
                    pack=pack,
                    family=family,
                    crop=pack["crop"],
                    photo_asset=LOCKED_HERO_ASSET_ID,
                    logo_asset=LOCKED_LOGO_ASSET_ID,
                    candidate_asset_id=str(asset.id),
                    architecture_lock=mask,
                )
                spec["graphic_field"]["asset_id"] = str(field_asset.id)
                spec["graphic_field"]["semantic_role"] = "graphic_field"
                spec["adaptive_plan"] = {
                    "flex_mode": pack.get("flex_mode"),
                    "scale": pack.get("scale"),
                    "alignment": pack.get("alignment"),
                    "solved": pack.get("solved"),
                    "iterations": pack.get("iterations"),
                }
                ready = family_revision_readiness(spec)
                critic, n = request_composition_critic(
                    candidate=pack["image"], foundation=pack["foundation"], family_id=family_id
                )
                vision_calls += n
                preflight = dict(pack.get("preflight") or {})
                rejects = hard_reject_54g(preflight=preflight, pack=pack, critic=critic)
                technical = "PASS" if preflight.get("pass") else "FAIL"
                arch_pass = bool(preflight.get("architecture_pixels_unchanged")) and (
                    (preflight.get("checks") or {}).get("architecture_clearance") == "PASS"
                )
                item = {
                    "key": f"G-F{idx}",
                    "family_id": family_id,
                    "flex_mode": pack.get("flex_mode"),
                    "scale": pack.get("scale"),
                    "asset_id": str(asset.id),
                    "graphic_field_asset_id": str(field_asset.id),
                    "spec_id": spec["spec_id"],
                    "spec": spec,
                    "revision_readiness": ready["revision_readiness"],
                    "revision_readiness_detail": ready,
                    "technical_preflight": technical,
                    "architecture_fidelity": "PASS" if arch_pass else "FAIL",
                    "solved": pack.get("solved"),
                    "iterations": pack.get("iterations"),
                    "solve_history": pack.get("solve_history"),
                    "preflight": {k: v for k, v in preflight.items() if k not in {"collision", "contrast"}},
                    "collision": preflight.get("collision"),
                    "contrast": preflight.get("contrast"),
                    "critic": critic,
                    "hard_reject": rejects,
                    "internally_rejected": not bool(preflight.get("pass")),
                    "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
                    "image": pack["image"],
                    "foundation": pack["foundation"],
                    "fielded": pack["fielded"],
                    "objects": pack.get("objects"),
                    "facts": pack.get("facts"),
                    "occupancy": pack.get("occupancy"),
                }
                candidates.append(item)
                specs.append(spec)
                preflight_report.append(
                    {
                        "key": item["key"],
                        "family_id": family_id,
                        "flex_mode": pack.get("flex_mode"),
                        "checks": preflight.get("checks"),
                        "pass": preflight.get("pass"),
                        "iterations": pack.get("iterations"),
                        "solved": pack.get("solved"),
                    }
                )
            occupancy_for_art = candidates[0].get("occupancy") if candidates else occupancy_blob
            if candidates:
                images["contrast"] = render_contrast_map(
                    candidates[0]["fielded"],
                    dict(candidates[0].get("contrast") or {}),
                    dict(candidates[0].get("objects") or {}),
                )
                images["comparison"] = render_three_way(candidates)
                images["collision"] = render_collision_proof(
                    candidates[0]["foundation"],
                    occupancy_for_art or {},
                    [(str(c.get("key")), dict(c.get("objects") or {})) for c in candidates],
                )
                proof = Image.new("RGB", (1280, 780), (12, 14, 20))
                px = 20
                for c in candidates:
                    tile = render_commercial_proof(c["image"], dict(c.get("objects") or {}), str(c.get("key")))
                    tile.thumbnail((400, 220), Image.Resampling.LANCZOS)
                    proof.paste(tile, (px, 40))
                    px += 420
                ImageDraw.Draw(proof).text((20, 10), "COMMERCIAL GROUP PROOF", fill=(201, 168, 92), font=_font(18))
                images["commercial"] = proof
                images["revision"] = render_revision_board(candidates)
                images["human_board"] = render_human_board(candidates)
                provenance = architecture_provenance_qa(
                    source=source,
                    foundation=candidates[0]["foundation"],
                    final=candidates[0]["image"],
                    transform={"centering": list((candidates[0].get("spec") or {}).get("project_photo", {}).get("crop", {}).get("centering") or [0.55, 0.3]), "source_crop": (0, 0, 1, 1)},
                )
            status = "CANDIDATES_PENDING_HUMAN_REVIEW"
    else:
        lock_failed.append("DESIGN_REFERENCES_NOT_FOUND")

    gpt_calls = provider_call_count()
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54G,
        "created_at": _now(),
        "status": status,
        "adaptive_composition_engine": "AdaptiveCompositionEngineV1",
        "contrast_engine": "CreativeContrastEngineV1",
        "collision_engine": "CreativeCollisionEngineV1",
        "commercial_offer_composer": "CommercialOfferComposerV1",
        "known_bug_fixes": {
            "family_field_mismatch": "normalized to graphic_field",
            "turkish_false_positive": "compositor UTF-8 facts override critic",
            "architecture_overlap_disagreement": "occupancy silhouette is source of truth",
        },
        "router_ranking": _jsonable(ranking),
        "generation_model": None,
        "gpt_image_calls": gpt_calls,
        "vision_calls": vision_calls,
        "candidates": [{k: v for k, v in item.items() if k not in {"image", "foundation", "fielded", "occupancy", "objects"}} for item in candidates],
        "lock_failed": lock_failed,
        "live_routing_active": False,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "project_id": TEMPLE_PROJECT_ID,
        "source_photo": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "provenance_qa": provenance,
        "phase55_executed": False,
        "price_revision_executed": False,
        "copy_revision_executed": False,
        "visual_replace_executed": False,
        "formats_created": False,
        "video_started": False,
        "publishing_started": False,
        "user_facing_template_picker": False,
        "technical_preflight": preflight_report,
        "family_constraints": all_family_constraints(),
        "occupancy_map": occupancy_json,
    }
    tests = [
        t
        for t in list(blob.get("final_composition_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54G)
    ]
    stored = json.loads(json.dumps(record, default=str))
    tests.append(stored)
    blob["final_composition_tests"] = tests
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
        raise RuntimeError("Phase 5.4G refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4G refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4G refused to modify approved creative masters")
    if blob.get("graphic_field_master_tests") != preserved.get("quality54e"):
        raise RuntimeError("Phase 5.4G refused to overwrite Phase 5.4E history")
    if blob.get("master_family_tests") != preserved.get("quality54f"):
        raise RuntimeError("Phase 5.4G refused to overwrite Phase 5.4F history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4G refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library_blob
    record["specs"] = specs
    record["candidate_images"] = candidates
    record["ranking"] = ranking
    record["occupancy"] = occupancy_blob
    _ = language
    return record
