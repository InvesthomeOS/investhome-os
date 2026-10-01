"""Phase 12.1 — approve ORNEK_00013 as an Investhome brand Premium Master. Scope-lock it.

Does not run Stage 4. Does not generate pixels. Does not treat this as The Temple.
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
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID, SELECTED_FILENAME
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    STAGE4_PROOF_SCOPE,
    is_production_premium_master,
    select_production_premium_master,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_12_1 = "phase12_1_production_master_approval_scope_lock"
STATUS = "PRODUCTION_PREMIUM_MASTER_APPROVED"
NEXT_PHASE = "STAGE 4.0 RETRY — INVESTHOME BRAND MASTER 4:5 → 9:16 STORY"
BRAND_ID = "INVESTHOME"
MASTER_TYPE_LABEL = "INVESTHOME BRAND PREMIUM MASTER"


def brand_master_scope() -> dict[str, Any]:
    return {
        "MASTER_SCOPE": "BRAND",
        "PROJECT_ID": None,
        "BRAND_ID": BRAND_ID,
        "CROSS_PROJECT_REUSE": False,
        "FORMAT_DERIVATIVES": "ALLOWED",
        "SEMANTIC_REVISIONS": "ALLOWED",
        "PROJECT_ASSET_SUBSTITUTION": "NOT ALLOWED",
        "may_be_used_for": [
            "Investhome brand campaigns",
            "Investhome corporate creatives",
            "compatible general Washington D.C. brand communication",
            "format derivatives of THIS approved campaign",
        ],
        "must_not_be_used_as": [
            "The Temple Premium Master",
            "UniLoft Premium Master",
            "another project's Premium Master",
        ],
        "rule": (
            "Approval of a DESIGN does not automatically approve that design as a "
            "template for other projects. BRAND MASTER and PROJECT MASTER are separate."
        ),
    }


def apply_brand_approval(master: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    scope = brand_master_scope()
    master["approval_status"] = "HUMAN_APPROVED"
    master["human_review"] = "APPROVED"
    master["pending_human_review"] = False
    master["router_eligible"] = True
    master["production_quality"] = True
    master["approved_at"] = now
    master["source"] = "INVESTHOME_APPROVED"
    master["source_category"] = "INVESTHOME_APPROVED"
    master["premium_master_type"] = MASTER_TYPE_LABEL
    master["master_scope"] = scope["MASTER_SCOPE"]
    master["project_id"] = None
    master["brand_id"] = BRAND_ID
    master["cross_project_reuse"] = False
    master["format_derivatives"] = "ALLOWED"
    master["semantic_revisions"] = "ALLOWED"
    master["project_asset_substitution"] = "NOT ALLOWED"
    master["temple_architecture"] = False
    master["visual_asset"] = SELECTED_ASSET_ID
    master["original_asset_id"] = SELECTED_ASSET_ID
    master["creative_tags"] = [
        "PRODUCTION_PREMIUM_MASTER",
        "INVESTHOME_BRAND",
        "HUMAN_APPROVED",
        "ORNEK_00013",
        "NOT_TEMPLE",
        "NOT_UNILOFT",
    ]
    master["note"] = (
        "HUMAN_APPROVED Investhome brand Premium Master. "
        "Not The Temple. Not UniLoft. Format derivatives and semantic revisions of THIS campaign are allowed. "
        "Do not substitute another project's assets into this master."
    )
    master["scope"] = scope
    return master


def generate_phase12_1_approve_lock(
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
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality40"] = list(blob.get("stage4_0_format_proof_tests") or [])
    preserved["quality120"] = list(blob.get("phase12_0_ingestion_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.1 requires ProjectCreativeMasterLibraryV1")
    if blob.get("premium_creative_product_model_locked") is not True:
        raise RuntimeError("Phase 12.1 requires Phase 11.12 product-model lock")

    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    pending = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.1 requires Masters 01–03 records to remain")
    if pending is None:
        raise RuntimeError("Phase 12.1 requires the Phase 12.0 pending production master")
    if str(pending.get("visual_asset") or pending.get("original_asset_id")) != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.1 refused to approve a different asset")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    auto_before = library.get("autonomous_premium_generation")
    quick_before = library.get("ai_quick_creative_status")
    role_before = library.get("masters_01_03_role")
    cover_before = blob.get("current_cover_asset_id") or original.get("current_cover_asset_id")

    apply_brand_approval(pending)

    library["phase12_1_status"] = STATUS
    library["approved_brand_premium_master_id"] = PRODUCTION_MASTER_ID
    library["pending_production_master_id"] = None
    library["the_temple_production_premium_master"] = "NOT AVAILABLE"
    library["stage4_0_status"] = "PAUSED — SOURCE NOW AVAILABLE FOR BRAND MASTER RETRY"
    library["stage4_proof_scope"] = STAGE4_PROOF_SCOPE
    library["stage4_source_master_id"] = PRODUCTION_MASTER_ID
    library["next_production_phase"] = NEXT_PHASE
    library["human_approved_premium_count"] = count_approved_premium(library)

    temple_pick = select_production_premium_master(library, project_id=TEMPLE_PROJECT_ID)
    brand_pick = select_production_premium_master(library, scope="BRAND", brand_id=BRAND_ID)
    if temple_pick is not None:
        raise RuntimeError("Phase 12.1 refused to let the brand master serve as The Temple Premium Master")
    if brand_pick is None or str(brand_pick.get("master_id")) != PRODUCTION_MASTER_ID:
        raise RuntimeError("Phase 12.1 expected the approved brand master to be selectable as BRAND")
    if pending.get("router_eligible") is not True or pending.get("approval_status") != "HUMAN_APPROVED":
        raise RuntimeError("Phase 12.1 expected HUMAN_APPROVED router-eligible brand master")
    if not is_production_premium_master(pending):
        raise RuntimeError("Phase 12.1 expected a production Premium Master after approval")
    if pending.get("project_id") is not None:
        raise RuntimeError("Phase 12.1 requires PROJECT_ID null on a brand master")
    if pending.get("cross_project_reuse") is not False:
        raise RuntimeError("Phase 12.1 requires CROSS_PROJECT_REUSE false")
    if pending.get("format_derivatives") != "ALLOWED" or pending.get("semantic_revisions") != "ALLOWED":
        raise RuntimeError("Phase 12.1 requires format derivatives and semantic revisions of THIS campaign")
    if pending.get("project_asset_substitution") != "NOT ALLOWED":
        raise RuntimeError("Phase 12.1 forbids substituting another project's assets into this master")
    if str(pending.get("visual_asset")) != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.1 refused to replace the original asset")
    if count_approved_premium(library) != 4:
        raise RuntimeError("Phase 12.1 expected four HUMAN_APPROVED premium masters (3 research proofs + 1 brand)")

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.1 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.1 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.1 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03_after.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 12.1 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.1 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.1 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.1 refused to change Master 03 visual")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Phase 12.1 refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Phase 12.1 refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Phase 12.1 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.1 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.1 refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.1 refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.1 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_0_status"] = library["stage4_0_status"]
    blob["stage4_proof_scope"] = STAGE4_PROOF_SCOPE
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["stage4_0_format_proof_tests"] = preserved.get("quality40")
    blob["phase12_0_ingestion_tests"] = preserved.get("quality120")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_1,
        "created_at": _now(),
        "status": STATUS,
        "master_id": PRODUCTION_MASTER_ID,
        "filename": SELECTED_FILENAME,
        "asset_id": SELECTED_ASSET_ID,
        "premium_master_type": MASTER_TYPE_LABEL,
        "human_approved": True,
        "router_eligible": True,
        "scope": brand_master_scope(),
        "the_temple_master_available": False,
        "stage_4_source_available": True,
        "stage_4_source": "INVESTHOME BRAND MASTER",
        "stage_4_proof_scope": STAGE4_PROOF_SCOPE,
        "stage_4_executed": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "cover_before": cover_before,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "language": language,
        "next": NEXT_PHASE,
        "temple_production_select": None if temple_pick is None else temple_pick.get("master_id"),
        "brand_production_select": brand_pick.get("master_id") if brand_pick else None,
    }
    tests = list(blob.get("phase12_1_approval_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase12_1_approval_tests"] = tests
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
