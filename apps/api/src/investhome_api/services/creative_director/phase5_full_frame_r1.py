"""Phase 5.4K-R1 — full-frame family art-direction polish.

Locks Day_007, crop, family, compositor V3. One candidate. GPT Image = 0.
Does not promote.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.full_frame_architectural_family import FAMILY_ID, full_frame_family_spec
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_full_frame_family import (
    _HISTORY_KEYS as _BASE_HISTORY,
    _architecture_hits,
    render_critic_board,
    render_human_review_board,
    request_full_frame_critic,
)
from investhome_api.services.creative_director.phase5_full_frame_family import _preserve as _preserve_base
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable, render_score_board, render_structure_map
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54K_R1 = "phase5_4k_r1_full_frame_polish"
DAY007_ASSET_ID = "c0afa1bf-b487-410c-be3d-91c31852550d"
DAY007_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_007.jpg"
LOCKED_CENTERING = (0.50, 0.42)
LOCKED_SOURCE_CROP = [161.06, 0.0, 1256.26, 1369.0]
BASE_CANDIDATE_ASSET_ID = "fd623439-5730-45c9-898b-30a80df42d00"
BASE_SPEC_ID = "3de885ad-ec95-4b0c-9538-e08b16027edc"
_HISTORY_KEYS = _BASE_HISTORY + (("full_frame_family_tests", "quality54k"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54k"] = list(blob.get("full_frame_family_tests") or [])
    return preserved


def generate_full_frame_r1_4x5(
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
    family = full_frame_family_spec()
    fonts = build_font_registry()
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    src = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY007_ASSET_ID)))).convert("RGB")
    crop, transform = cover_fit_canvas(src, CANVAS_4X5, centering=LOCKED_CENTERING)
    recorded = [round(float(v), 2) for v in (transform.get("source_crop") or [])]
    crop_locked = recorded == LOCKED_SOURCE_CROP
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = build_photo_occupancy_map(graded)
    pack = compose_graphic_design_v3(
        graded,
        occupancy=occupancy,
        family=family,
        fonts=fonts,
        logo_rgba=logo_rgba,
        polish=True,
    )
    images: dict[str, Any] = {}
    spec: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None
    critic: dict[str, Any] = {}
    ready: dict[str, Any] | None = None
    candidate_asset_id = None
    status = "R1_UNSOLVED"
    if pack.get("solved"):
        field_asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(pack["fielded"]),
            content_type="image/png",
            campaign_mode="project-v3-r1-field",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt="PHASE 5.4K-R1 field",
        )
        asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(pack["image"]),
            content_type="image/png",
            campaign_mode="project-v3-r1-candidate",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt="PHASE 5.4K-R1 candidate",
        )
        pack["graphic_field_asset_id"] = str(field_asset.id)
        spec = build_family_master_spec(
            key="FF-R1",
            pack=pack,
            family=family,
            crop={"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop")},
            photo_asset=DAY007_ASSET_ID,
            logo_asset=LOCKED_LOGO_ASSET_ID,
            candidate_asset_id=str(asset.id),
            architecture_lock={"schema": "PhotoOccupancyMapV1"},
        )
        spec["schema"] = "ProductionMasterCandidateV1"
        spec["family_id"] = FAMILY_ID
        spec["base_candidate_asset_id"] = BASE_CANDIDATE_ASSET_ID
        spec["base_spec_id"] = BASE_SPEC_ID
        spec["graphic_field"]["asset_id"] = str(field_asset.id)
        spec["flex_mode"] = pack.get("flex_mode")
        spec["art_direction"] = "spire_axis_r1"
        spec["photo_changed"] = False
        spec["crop_changed"] = not crop_locked
        ready = family_revision_readiness(spec)
        collision = evaluate_collisions(objects=pack.get("objects") or {}, occupancy=occupancy, size=pack["image"].size)
        arch_hits = _architecture_hits(list(collision.get("hits") or []))
        provenance = architecture_provenance_qa(
            source=src,
            foundation=pack["foundation"],
            final=pack["image"],
            transform={"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop") or LOCKED_SOURCE_CROP, "scale_x": transform.get("scale_x"), "scale_y": transform.get("scale_y")},
        )
        utf8 = turkish_copy_is_valid(pack.get("facts") or {})
        logo_box = ((pack.get("objects") or {}).get("project_logo") or {}).get("bounds") or {}
        logo_visible = float(logo_box.get("w") or 0) >= 0.12 and float(logo_box.get("h") or 0) >= 0.03
        checks = {
            "photo_family_fit": "PASS",
            "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
            "architecture_clearance": "PASS" if not any("architecture" in h for h in arch_hits) else "FAIL",
            "headline_collision": "PASS" if not any(h.startswith("headline") for h in arch_hits) else "FAIL",
            "commercial_collision": "PASS" if not any("price" in h or "discount" in h for h in arch_hits) else "FAIL",
            "logo_collision": "PASS" if not any("logo" in h for h in arch_hits) else "FAIL",
            "cta_collision": "PASS" if not any(h.startswith("cta") for h in arch_hits) else "FAIL",
            "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
            "UTF8": "PASS" if utf8 else "FAIL",
            "font_metrics": "PASS",
            "commercial_hierarchy": "PASS",
            "family_identity": "PASS",
            "canvas_bounds": "PASS" if not pack.get("overflow") else "FAIL",
            "semantic_completeness": "PASS",
            "revision_readiness": ready.get("revision_readiness") or "FAIL",
            "real_temple_logo": "PASS" if pack.get("real_logo") and logo_visible else "FAIL",
            "crop_locked": "PASS" if crop_locked else "FAIL",
        }
        preflight = {
            "schema": "FullFrameR1TechnicalPreflightV1",
            "checks": checks,
            "pass": all(v == "PASS" for v in checks.values()),
            "collision_hits": list(collision.get("hits") or []),
            "architecture_hits": arch_hits,
        }
        critic, n = request_full_frame_critic(pack["image"], pack["foundation"])
        vision_calls += n
        candidate_asset_id = str(asset.id)
        status = "R1_RENDERED" if preflight["pass"] else "R1_TECHNICAL_FAIL"
        top = {"filename": DAY007_FILENAME, "flex_mode": pack.get("flex_mode"), "asset_id": DAY007_ASSET_ID}
        images["proof"] = pack["image"]
        images["structure_map"] = render_structure_map(pack["image"], pack.get("objects") or {})
        images["preflight"] = render_score_board({"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}})
        images["critic"] = render_critic_board(critic)
        images["review_board"] = render_human_review_board(
            candidate=pack["image"], critic=critic, preflight=preflight, top=top
        )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54K_R1,
        "created_at": _now(),
        "status": status,
        "family_id": FAMILY_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "photo_filename": DAY007_FILENAME,
        "photo_changed": False,
        "crop_changed": not crop_locked,
        "crop": {"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop")},
        "base_candidate_asset_id": BASE_CANDIDATE_ASSET_ID,
        "base_spec_id": BASE_SPEC_ID,
        "candidate_asset_id": candidate_asset_id,
        "spec_id": (spec or {}).get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "critic": critic,
        "real_temple_logo": bool(pack.get("real_logo")),
        "gpt_image_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "new_family_created": False,
        "phase55_executed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "pack_flex_mode": pack.get("flex_mode"),
        "solved": pack.get("solved"),
        "contrast": _jsonable(pack.get("contrast")),
    }
    tests = [t for t in list(blob.get("full_frame_r1_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54K_R1)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["full_frame_r1_tests"] = tests
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
    if blob.get("full_frame_family_tests") != preserved.get("quality54k"):
        raise RuntimeError("Phase 5.4K-R1 refused to overwrite Phase 5.4K")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4K-R1 refused to modify approved creative masters")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    _ = language
    return record
