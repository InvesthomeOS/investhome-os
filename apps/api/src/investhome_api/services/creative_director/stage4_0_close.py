"""Stage 4.0 close — archive the failed Story proof. Lock recomposition doctrine.

Does not generate a Story. Does not create R4. Does not start Stage 4.1.
"""

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
from investhome_api.services.creative_director.premium_format_adapter_v1 import ADAPTER_ID
from investhome_api.services.creative_director.premium_format_recomposer_v1 import (
    ACTION,
    DEPRECATED_MODEL,
    NEXT_STAGE,
    RECOMPOSER_ID,
    STATUS,
    archived_story_proof,
    permanent_format_adaptation_rule,
    prepare_format_recomposition,
    preserved_technical_integrity,
    recomposer_contract,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_40_CLOSE = "stage4_0_close_format_adaptation_proof"
STAGE_LABEL = "4.0 PREMIUM FORMAT ADAPTATION PROOF"


def _reject_story_children(parent: dict[str, Any]) -> list[dict[str, Any]]:
    archive = archived_story_proof()
    updated = []
    for child in list(parent.get("format_children") or []):
        item = dict(child)
        if str(item.get("target_format")) == "9:16":
            item["status"] = "REJECTED"
            item["human_review"] = "REJECTED"
            item["auto_approved"] = False
            item["router_eligible"] = False
            item["is_premium_master"] = False
            item["design_quality"] = "FAIL"
            item["method"] = DEPRECATED_MODEL
            item["close_reason"] = "professionally weak compositional adaptation"
        updated.append(item)
    parent["format_children"] = updated
    parent["stage4_0_story_archive"] = archive
    return updated


def generate_stage4_0_close(
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
    preserved["quality40"] = list(blob.get("stage4_0_format_proof_tests") or [])
    preserved["quality40r"] = list(blob.get("stage4_0_retry_tests") or [])
    preserved["quality40r1"] = list(blob.get("stage4_0_r1_tests") or [])
    preserved["quality40r2"] = list(blob.get("stage4_0_r2_tests") or [])
    preserved["quality40c"] = list(blob.get("stage4_0_clean_tests") or [])
    preserved["quality40r3"] = list(blob.get("stage4_0_r3_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Stage 4.0 close requires ProjectCreativeMasterLibraryV1")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None:
        raise RuntimeError("Stage 4.0 close requires the Investhome brand Premium Master")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Stage 4.0 close requires Masters 01–03 records to remain")
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

    children = _reject_story_children(parent)
    prepared = prepare_format_recomposition(library, target_format="9:16", scope="BRAND", brand_id="INVESTHOME", execute=False)
    contract = recomposer_contract()
    archive = archived_story_proof()
    doctrine = permanent_format_adaptation_rule()
    integrity = preserved_technical_integrity()

    library["stage4_0_status"] = STATUS
    library["premium_format_adapter"] = ADAPTER_ID
    library["premium_format_adapter_composition_model"] = "DEPRECATED"
    library["premium_format_recomposer"] = RECOMPOSER_ID
    library["current_story"] = "REJECTED"
    library["stage4_0_story_archive"] = archive
    library["next_production_phase"] = NEXT_STAGE
    library["stage4_0_note"] = (
        "Stage 4.0 Story proof is closed. Technical fidelity passed. Design fidelity failed. "
        "Reposition model is deprecated. Next is Stage 4.1 one-shot 9:16 recomposition visual proof. "
        "Do not create R4. Do not generate another Story in this close."
    )

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Stage 4.0 close refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Stage 4.0 close refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Stage 4.0 close refused to mutate Master 03")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Stage 4.0 close refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Stage 4.0 close refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Stage 4.0 close refused to change Master 03 visual")
    if parent.get("visual_asset") != parent_visual_before:
        raise RuntimeError("Stage 4.0 close mutated the brand master visual")
    if parent.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Stage 4.0 close refused to keep ORNEK_00013 as the canonical visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Stage 4.0 close must not create another Premium Master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Stage 4.0 close refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Stage 4.0 close refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Stage 4.0 close refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Stage 4.0 close refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Stage 4.0 close refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Stage 4.0 close refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 close must not call GPT Image")
    if prepared.get("format_child") is not None:
        raise RuntimeError("Stage 4.0 close must not create a format child")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_0_status"] = STATUS
    blob["premium_format_recomposer"] = json.loads(json.dumps(_jsonable(contract), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["stage4_0_format_proof_tests"] = preserved.get("quality40")
    blob["stage4_0_retry_tests"] = preserved.get("quality40r")
    blob["stage4_0_r1_tests"] = preserved.get("quality40r1")
    blob["stage4_0_r2_tests"] = preserved.get("quality40r2")
    blob["stage4_0_clean_tests"] = preserved.get("quality40c")
    blob["stage4_0_r3_tests"] = preserved.get("quality40r3")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_40_CLOSE,
        "created_at": _now(),
        "STAGE": STAGE_LABEL,
        "status": STATUS,
        "TECHNICAL_FIDELITY": "PASS",
        "DESIGN_FIDELITY": "FAIL",
        "CURRENT_STORY": "REJECTED",
        "PREMIUM_FORMAT_ADAPTER": "REPOSITION MODEL DEPRECATED",
        "NEW_MODEL": RECOMPOSER_ID,
        "action": ACTION,
        "story_generated": False,
        "r4_created": False,
        "stage_4_1_executed": False,
        "format_child_created": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "rejected_children": [
            {"child_id": item.get("child_id"), "revision": item.get("revision"), "status": item.get("status")}
            for item in children
            if str(item.get("target_format")) == "9:16"
        ],
        "archive": archive,
        "doctrine": doctrine,
        "technical_integrity": integrity,
        "contract": contract,
        "prepared": prepared,
        "next": NEXT_STAGE,
    }
    tests = list(blob.get("stage4_0_close_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["stage4_0_close_tests"] = tests
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
