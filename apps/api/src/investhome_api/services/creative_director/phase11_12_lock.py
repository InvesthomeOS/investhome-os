"""Phase 11.12 — lock the Creative Studio product model. No artwork."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    _now,
    _phase5,
    _production_guard,
)
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import _identity_slice
from investhome_api.services.creative_director.phase10_3_finalize import preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase10_3_revision_doctrine import STAGE_2_STATUS
from investhome_api.services.creative_director.premium_creative_product_model import NEXT_STAGE, STATUS, product_model
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_12 = "phase11_12_premium_creative_product_model_lock"
NEXT_PHASE = NEXT_STAGE


def generate_phase11_12_product_lock(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = db, user
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = preserve_stage2(blob)
    for src, alias in (
        ("phase11_0_foundation_tests", "quality110"),
        ("phase11_1_creative_quality_proof_tests", "quality111"),
        ("phase11_2_creative_quality_proof_tests", "quality112"),
        ("phase11_3_commercial_creative_system_tests", "quality113"),
        ("phase11_4_creative_quality_proof_tests", "quality114"),
        ("phase11_6_hybrid_premium_engine_tests", "quality116"),
        ("phase11_7_hybrid_finish_tests", "quality117"),
        ("phase11_8_engine_v2_tests", "quality118"),
        ("phase11_9_hybrid_v2_creative_tests", "quality119"),
        ("phase11_10_ai_native_tests", "quality1110"),
        ("phase11_11_reference_guided_tests", "quality1111"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 11.12 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.12 requires locked Masters 01–03")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s = library.get("stage_3_creative_quality_proof")
    p2s = library.get("stage_3_creative_quality_proof_02")
    p3s = library.get("stage_3_creative_quality_proof_03")

    model = product_model()
    library["premium_creative_product_model"] = STATUS
    library["autonomous_premium_generation"] = "DISABLED"
    library["ai_quick_creative_status"] = "ACTIVE"
    library["ai_role"] = "PREMIUM_CREATIVE_OPERATOR"
    library["masters_01_03_role"] = "RESEARCH_SYSTEM_PROOF_NOT_QUALITY_BENCHMARK"
    library["next_production_phase"] = NEXT_PHASE
    library["note"] = (
        "Premium Creative Product Model is locked. "
        "Autonomous Premium generation is disabled. "
        "Masters 01–03 remain research/system proofs, not the quality benchmark. "
        "No new Temple creative was generated."
    )

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 11.12 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 11.12 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 11.12 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03_after.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 11.12 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 11.12 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 11.12 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.12 refused to change Master 03 visual")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.12 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Phase 11.12 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Phase 11.12 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Phase 11.12 refused to rewrite Proof 03")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.12 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["premium_creative_product_model_locked"] = True
    blob["autonomous_premium_generation"] = "DISABLED"
    blob["ai_quick_creative"] = "ACTIVE"
    blob["premium_creative_product_model"] = json.loads(json.dumps(_jsonable(model), default=str))
    blob["canonical_premium_generation_path"] = None
    blob["stage_3_executed"] = False
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["phase11_3_commercial_creative_system_tests"] = preserved.get("quality113")
    blob["phase11_4_creative_quality_proof_tests"] = preserved.get("quality114")
    blob["phase11_6_hybrid_premium_engine_tests"] = preserved.get("quality116")
    blob["phase11_7_hybrid_finish_tests"] = preserved.get("quality117")
    blob["phase11_8_engine_v2_tests"] = preserved.get("quality118")
    blob["phase11_9_hybrid_v2_creative_tests"] = preserved.get("quality119")
    blob["phase11_10_ai_native_tests"] = preserved.get("quality1110")
    blob["phase11_11_reference_guided_tests"] = preserved.get("quality1111")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_12,
        "created_at": _now(),
        "status": STATUS,
        "product_model": model,
        "new_creative_generated": False,
        "format_work_executed": False,
        "story_reel_video_executed": False,
        "live_creative_studio_executed": False,
        "research_paths": "ARCHIVED",
        "reusable_capabilities": "PRESERVED",
        "stage_2": STAGE_2_STATUS,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "next_phase": NEXT_PHASE,
        "language": language,
    }
    tests = list(blob.get("phase11_12_product_lock_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_12_product_lock_tests"] = tests
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["identity"] = {"before": before, "after": after}
    return record
