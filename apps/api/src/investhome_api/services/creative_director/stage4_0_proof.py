"""Stage 4.0 — Premium Format Adaptation foundation + Proof 01 gate.

Does not generate a Story from Masters 01–03.
Does not mutate the Phase 11.12 product model, production cover, or approved masters.

Proof scope after Phase 12.1 is INVESTHOME BRAND MASTER → STORY, not
THE TEMPLE PROJECT MASTER → STORY. This module's original gated run still
asks The Temple so the historical NO_PRODUCTION_MASTER result remains true:
The Temple still has no production Premium Master. Stage 4.0 RETRY is a
later phase and must select the brand master explicitly.
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
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
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
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    ADAPTER_ID,
    STATUS_NO_PRODUCTION_MASTER,
    adapt_premium_master_to_format,
    adapter_contract,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_40 = "stage4_0_premium_format_adaptation_foundation"
NEXT_WHEN_GATED = "INGEST PRODUCTION PREMIUM MASTER — THEN RETRY STAGE 4.0"


def generate_stage4_0_format_proof(
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
        ("phase11_12_product_lock_tests", "quality1112"),
        ("phase11_11_reference_guided_tests", "quality1111"),
        ("phase11_10_ai_native_tests", "quality1110"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Stage 4.0 requires ProjectCreativeMasterLibraryV1")
    if blob.get("premium_creative_product_model_locked") is not True:
        raise RuntimeError("Stage 4.0 requires Phase 11.12 product-model lock")

    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Stage 4.0 requires locked Masters 01–03 records to remain in place")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s = library.get("stage_3_creative_quality_proof")
    p2s = library.get("stage_3_creative_quality_proof_02")
    p3s = library.get("stage_3_creative_quality_proof_03")
    product_before = blob.get("premium_creative_product_model")
    lock_before = blob.get("premium_creative_product_model_locked")
    quick_before = library.get("ai_quick_creative_status")
    auto_before = library.get("autonomous_premium_generation")
    role_before = library.get("masters_01_03_role")

    adapted = adapt_premium_master_to_format(
        library,
        target_format="9:16",
        project_id=TEMPLE_PROJECT_ID,
        execute=True,
    )
    status = str(adapted.get("status") or STATUS_NO_PRODUCTION_MASTER)

    library["stage4_0_status"] = status
    library["premium_format_adapter"] = ADAPTER_ID
    if status == STATUS_NO_PRODUCTION_MASTER:
        library["next_production_phase"] = NEXT_WHEN_GATED
        library["stage4_0_note"] = (
            "No production Premium Master is available. "
            "Masters 01–03 were not used as the format-adaptation source. "
            "No Story child was generated."
        )

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Stage 4.0 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Stage 4.0 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Stage 4.0 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03_after.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Stage 4.0 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Stage 4.0 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Stage 4.0 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Stage 4.0 refused to change Master 03 visual")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Stage 4.0 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Stage 4.0 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Stage 4.0 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Stage 4.0 refused to rewrite Proof 03")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Stage 4.0 refused to change AI Quick Creative")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Stage 4.0 refused to change autonomous premium status")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Stage 4.0 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Stage 4.0 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Stage 4.0 refused to rewrite the Phase 11.12 product model")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 must not call image generation")
    if adapted.get("format_child") is not None:
        raise RuntimeError("Stage 4.0 must not attach a format child without a production master")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_0_premium_format_adaptation"] = json.loads(json.dumps(_jsonable(adapted), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase11_11_reference_guided_tests"] = preserved.get("quality1111")
    blob["phase11_10_ai_native_tests"] = preserved.get("quality1110")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_40,
        "created_at": _now(),
        "status": status,
        "adapter": adapter_contract(),
        "adaptation": adapted,
        "new_creative_generated": False,
        "format_child_created": False,
        "story_generated": False,
        "used_masters_01_03_as_source": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "language": language,
        "next": NEXT_WHEN_GATED if status == STATUS_NO_PRODUCTION_MASTER else "STAGE 4.1 — MULTI-FORMAT ADAPTATION",
    }
    tests = list(blob.get("stage4_0_format_proof_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["stage4_0_format_proof_tests"] = tests
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
