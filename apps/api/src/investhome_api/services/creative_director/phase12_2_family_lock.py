"""Phase 12.2 — lock Premium Creative Family. Close Stage 4.1. No artwork."""

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
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    NEXT_PHASE,
    ORNEK_FAMILY_ID,
    STATUS_MODEL_READY,
    STATUS_STAGE41_FAIL,
    archived_format_research,
    ornek_00013_family,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_12_2 = "phase12_2_premium_creative_family_model_lock"
STATUS = STATUS_MODEL_READY


def generate_phase12_2_family_lock(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = db, user
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality121"] = list(blob.get("phase12_1_approval_tests") or [])
    preserved["quality40c"] = list(blob.get("stage4_0_close_tests") or [])
    preserved["quality41"] = list(blob.get("stage4_1_recomposition_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.2 requires ProjectCreativeMasterLibraryV1")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None:
        raise RuntimeError("Phase 12.2 requires the Investhome brand Premium Master")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.2 requires Masters 01–03 records to remain")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")
    parent_visual_before = parent.get("visual_asset")
    approved_count_before = count_approved_premium(library)
    auto_before = library.get("autonomous_premium_generation")
    quick_before = library.get("ai_quick_creative_status")
    role_before = library.get("masters_01_03_role")

    family = ornek_00013_family()
    archive = archived_format_research()
    parent["family_id"] = ORNEK_FAMILY_ID
    parent["family_member"] = True
    parent["format"] = "4:5"
    children = []
    for child in list(parent.get("format_children") or []):
        item = dict(child)
        if str(item.get("target_format")) == "9:16":
            item["status"] = "REJECTED"
            item["human_review"] = "REJECTED"
            item["router_eligible"] = False
            item["family_member"] = False
            item["close_status"] = STATUS_STAGE41_FAIL
        children.append(item)
    parent["format_children"] = children

    library["premium_creative_families"] = [family]
    library["premium_creative_family_id"] = ORNEK_FAMILY_ID
    library["stage4_1_status"] = STATUS_STAGE41_FAIL
    library["autonomous_premium_format_design"] = "DISABLED"
    library["archived_premium_format_research"] = archive
    library["next_production_phase"] = NEXT_PHASE
    library["stage4_1_note"] = (
        "Stage 4.1 one-shot Story is rejected. Technical integrity passed. Design quality failed. "
        "PremiumFormatRecomposerV1 is not used for autonomous production Premium format creation."
    )

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.2 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.2 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.2 refused to mutate Master 03")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.2 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.2 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.2 refused to change Master 03 visual")
    if parent.get("visual_asset") != parent_visual_before:
        raise RuntimeError("Phase 12.2 mutated the brand master visual")
    if parent.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.2 refused to keep ORNEK_00013 as the canonical visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Phase 12.2 must not create another Premium Master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Phase 12.2 refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Phase 12.2 refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Phase 12.2 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.2 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.2 refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.2 refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.2 must not call GPT Image")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_1_status"] = STATUS_STAGE41_FAIL
    blob["premium_creative_family_model"] = STATUS
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["stage4_0_close_tests"] = preserved.get("quality40c")
    blob["stage4_1_recomposition_tests"] = preserved.get("quality41")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_2,
        "created_at": _now(),
        "PHASE": "12.2 PREMIUM CREATIVE FAMILY MODEL LOCK",
        "status": STATUS,
        "PREMIUM_MODEL": "HUMAN_APPROVED_CREATIVE_FAMILY",
        "AUTONOMOUS_PREMIUM_FORMAT_DESIGN": "DISABLED",
        "stage_4_1": STATUS_STAGE41_FAIL,
        "family_id": ORNEK_FAMILY_ID,
        "family": family,
        "archive": archive,
        "story_generated": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "next": NEXT_PHASE,
    }
    tests = list(blob.get("phase12_2_family_lock_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase12_2_family_lock_tests"] = tests
    ctx = dict(original_ctx)
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
