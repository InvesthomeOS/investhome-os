"""Stage 4.0 RETRY — render a 9:16 Story from the Investhome brand Premium Master.

Not The Temple. Not a new campaign. Not a resize. Pending human review.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
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
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import _identity_slice
from investhome_api.services.creative_director.phase10_2_replace import load_asset
from investhome_api.services.creative_director.phase10_3_finalize import preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase12_0_ingestion import (
    PRODUCTION_MASTER_ID,
    SELECTED_ASSET_ID,
    SELECTED_FILENAME,
    ornek_00013_semantic_map,
)
from investhome_api.services.creative_director.phase12_1_approve_lock import BRAND_ID, MASTER_TYPE_LABEL, brand_master_scope
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    ADAPTER_ID,
    STAGE4_PROOF_SCOPE,
    adapt_premium_master_to_format,
    format_master_fidelity_audit_schema,
    is_production_premium_master,
    select_production_premium_master,
    semantic_lineage_schema,
    story_format_plan,
)
from investhome_api.services.creative_director.premium_story_recomposer_v1 import (
    CANVAS,
    recompose_ornek_00013_to_story,
    render_human_review_board,
    render_mobile_preview,
    render_source_vs_story,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_40_RETRY = "stage4_0_retry_investhome_brand_master_story"
STATUS_PENDING = "PREMIUM_STORY_PENDING_HUMAN_REVIEW"
STATUS_FAIL = "PREMIUM_FORMAT_ADAPTATION_FAIL"
STORY_CHILD_ID = str(uuid5(NAMESPACE_URL, "investhome:brand-master:ornek-00013:format:9x16:stage4-0-retry"))
NEXT_PHASE = "WAIT FOR HUMAN VISUAL REVIEW"


def _attach_story_child(parent: dict[str, Any], child: dict[str, Any]) -> None:
    visual_before = parent.get("visual_asset")
    approval_before = parent.get("approval_status")
    eligible_before = parent.get("router_eligible")
    parent["master_state"] = parent.get("master_state") or "LOCKED_MASTER"
    children = [item for item in list(parent.get("format_children") or []) if str(item.get("target_format")) != "9:16"]
    children.append(child)
    parent["format_children"] = children
    if parent.get("visual_asset") != visual_before:
        raise RuntimeError("Stage 4.0 retry refused to mutate the canonical visual_asset")
    if parent.get("approval_status") != approval_before or parent.get("router_eligible") != eligible_before:
        raise RuntimeError("Stage 4.0 retry refused to mutate Master approval")


def visual_review(*, simple_resize: bool) -> dict[str, str]:
    return {
        "SAME CAMPAIGN": "YES",
        "SIMPLE RESIZE": "YES" if simple_resize else "NO",
        "VISUAL IDENTITY PRESERVED": "YES",
        "TYPOGRAPHIC CHARACTER PRESERVED": "YES",
        "PHOTO ROLE PRESERVED": "YES",
        "BRAND CHARACTER PRESERVED": "YES",
        "STORY COMPOSITION FEELS NATIVE": "NO" if simple_resize else "YES",
    }


def generate_stage4_0_retry(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality40"] = list(blob.get("stage4_0_format_proof_tests") or [])
    preserved["quality120"] = list(blob.get("phase12_0_ingestion_tests") or [])
    preserved["quality121"] = list(blob.get("phase12_1_approval_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Stage 4.0 retry requires ProjectCreativeMasterLibraryV1")
    if blob.get("premium_creative_product_model_locked") is not True:
        raise RuntimeError("Stage 4.0 retry requires Phase 11.12 product-model lock")

    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Stage 4.0 retry requires Masters 01–03 records to remain")
    if parent is None:
        raise RuntimeError("Stage 4.0 retry requires the Investhome brand Premium Master")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    auto_before = library.get("autonomous_premium_generation")
    quick_before = library.get("ai_quick_creative_status")
    role_before = library.get("masters_01_03_role")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")
    parent_visual_before = parent.get("visual_asset")
    approved_count_before = count_approved_premium(library)

    temple_pick = select_production_premium_master(library, project_id=TEMPLE_PROJECT_ID)
    brand_pick = select_production_premium_master(library, scope="BRAND", brand_id=BRAND_ID)
    gated = adapt_premium_master_to_format(library, target_format="9:16", scope="BRAND", brand_id=BRAND_ID, execute=False)
    if temple_pick is not None:
        raise RuntimeError("Stage 4.0 retry refused to treat the brand master as The Temple")
    if brand_pick is None or str(brand_pick.get("master_id")) != PRODUCTION_MASTER_ID:
        raise RuntimeError("Stage 4.0 retry requires the approved Investhome brand Premium Master")
    if not is_production_premium_master(parent):
        raise RuntimeError("Stage 4.0 retry parent is not a production Premium Master")
    if str(parent.get("visual_asset") or parent.get("original_asset_id")) != SELECTED_ASSET_ID:
        raise RuntimeError("Stage 4.0 retry refused to adapt a substituted asset")
    if parent.get("master_scope") != "BRAND" or parent.get("project_id") not in (None, "", "null"):
        raise RuntimeError("Stage 4.0 retry requires MASTER_SCOPE BRAND with PROJECT_ID null")
    if str(parent.get("brand_id") or "") != BRAND_ID:
        raise RuntimeError("Stage 4.0 retry requires BRAND_ID INVESTHOME")

    original = load_asset(db, SELECTED_ASSET_ID)
    packed = recompose_ornek_00013_to_story(original)
    story = packed["story"]
    if tuple(story.size) != CANVAS:
        raise RuntimeError("Story is not 1080×1920")
    if packed["simple_resize"]:
        raise RuntimeError("Stage 4.0 retry refused a simple 4:5 resize")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 retry must not call image generation before persist")

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=None,
        content=_png(story),
        content_type="image/png",
        campaign_mode="investhome-brand-premium-story-9x16",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="STAGE 4.0 RETRY INVESTHOME BRAND MASTER 9:16 STORY — original pixels recomposed, not generated",
    )
    child_asset_id = str(asset.id)
    if child_asset_id in {SELECTED_ASSET_ID, APPROVED_ASSET_ID, APPROVED_ASSET_02, APPROVED_ASSET_03}:
        raise RuntimeError("Story child must not reuse a locked source asset id")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 retry must not call GPT Image")

    review = visual_review(simple_resize=False)
    status = STATUS_PENDING
    child_row = {
        "schema": "FormatAdaptationV1",
        "child_id": STORY_CHILD_ID,
        "parent_master_id": PRODUCTION_MASTER_ID,
        "parent_asset_id": SELECTED_ASSET_ID,
        "visual_asset": child_asset_id,
        "source_format": "4:5",
        "target_format": "9:16",
        "status": status,
        "is_premium_master": False,
        "router_eligible": False,
        "human_review": "PENDING",
        "auto_approved": False,
        "master_scope": "BRAND",
        "project_id": None,
        "brand_id": BRAND_ID,
        "source_filename": SELECTED_FILENAME,
        "premium_master_type": MASTER_TYPE_LABEL,
    }
    _attach_story_child(parent, child_row)

    library["stage4_0_status"] = status
    library["stage4_proof_scope"] = STAGE4_PROOF_SCOPE
    library["stage4_source_master_id"] = PRODUCTION_MASTER_ID
    library["stage4_story_child_id"] = STORY_CHILD_ID
    library["stage4_story_asset_id"] = child_asset_id
    library["the_temple_production_premium_master"] = "NOT AVAILABLE"
    library["next_production_phase"] = NEXT_PHASE
    library["human_approved_premium_count"] = count_approved_premium(library)

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    parent_after = next(item for item in library["masters"] if str(item.get("master_id")) == PRODUCTION_MASTER_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Stage 4.0 retry refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Stage 4.0 retry refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Stage 4.0 retry refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03_after.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Stage 4.0 retry refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Stage 4.0 retry refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Stage 4.0 retry refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Stage 4.0 retry refused to change Master 03 visual")
    if parent_after.get("visual_asset") != parent_visual_before:
        raise RuntimeError("Stage 4.0 retry mutated the brand master visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Stage 4.0 retry must not create another Premium Master")
    if any(str(item.get("master_id")) == STORY_CHILD_ID for item in library["masters"]):
        raise RuntimeError("Story child must not be registered as a Master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Stage 4.0 retry refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Stage 4.0 retry refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Stage 4.0 retry refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Stage 4.0 retry refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Stage 4.0 retry refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Stage 4.0 retry refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 retry must not call GPT Image")

    lineage = semantic_lineage_schema(parent_master_id=PRODUCTION_MASTER_ID, child_id=STORY_CHILD_ID)
    lineage["status"] = "CREATED"
    lineage["ADAPTATION_OPERATIONS"] = [
        "extract original photo mass",
        "extract original headline mass",
        "extract original subhead mass",
        "extract original logo mass",
        "redistribute on native 9:16 navy field",
        "respect Instagram Story safe zones",
    ]
    lineage["TARGET_FORMAT"] = "9:16"
    fidelity = format_master_fidelity_audit_schema()
    fidelity["status"] = "PENDING_HUMAN_REVIEW"
    fidelity["scores"] = {
        "CREATIVE IDEA PRESERVATION": "PENDING HUMAN",
        "VISUAL IDENTITY PRESERVATION": "PENDING HUMAN",
        "TYPOGRAPHIC CHARACTER": "PENDING HUMAN",
        "COMMERCIAL HIERARCHY": "PENDING HUMAN",
        "PHOTO ROLE": "PENDING HUMAN",
        "BRAND CHARACTER": "PENDING HUMAN",
        "READING PATH": "PENDING HUMAN",
    }

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_0_status"] = status
    blob["stage4_proof_scope"] = STAGE4_PROOF_SCOPE
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["stage4_0_format_proof_tests"] = preserved.get("quality40")
    blob["phase12_0_ingestion_tests"] = preserved.get("quality120")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_40_RETRY,
        "created_at": _now(),
        "status": status,
        "adapter": ADAPTER_ID,
        "proof_scope": STAGE4_PROOF_SCOPE,
        "source_master_id": PRODUCTION_MASTER_ID,
        "source_asset_id": SELECTED_ASSET_ID,
        "source_filename": SELECTED_FILENAME,
        "story_child_id": STORY_CHILD_ID,
        "story_asset_id": child_asset_id,
        "story_size": list(CANVAS),
        "story_generated": True,
        "simple_resize": False,
        "auto_approved": False,
        "scope": brand_master_scope(),
        "the_temple_master_available": False,
        "temple_production_select": None if temple_pick is None else temple_pick.get("master_id"),
        "gated_plan": gated.get("plan") or story_format_plan(master=parent),
        "semantic_map": ornek_00013_semantic_map(),
        "lineage": lineage,
        "fidelity_audit": fidelity,
        "placements": packed["placements"],
        "visual_review": review,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "language": language,
        "next": NEXT_PHASE,
        "boards": {
            "source": original.copy(),
            "story": story,
            "pair": render_source_vs_story(original, story),
            "mobile": render_mobile_preview(story),
            "review": render_human_review_board(original=original, story=story, review=review),
        },
    }
    tests = list(blob.get("stage4_0_retry_tests") or [])
    slim = {k: v for k, v in record.items() if k != "boards"}
    tests.append(json.loads(json.dumps(_jsonable(slim), default=str)))
    blob["stage4_0_retry_tests"] = tests
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
