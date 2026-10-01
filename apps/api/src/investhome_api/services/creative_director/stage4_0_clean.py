"""Stage 4.0 clean pass — exclusive semantic layers. Same R2 composition."""

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
from investhome_api.services.creative_director.phase10_2_replace import load_asset
from investhome_api.services.creative_director.phase10_3_finalize import preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID
from investhome_api.services.creative_director.phase12_1_approve_lock import BRAND_ID
from investhome_api.services.creative_director.premium_story_recomposer_v1 import render_mobile_preview
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.semantic_layer_exclusivity_v1 import refuse_if_unclean
from investhome_api.services.creative_director.stage4_0_r2_compose import compose_story_clean
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_40_CLEAN = "stage4_0_semantic_layer_exclusivity"
STATUS_CLEAN = "PREMIUM_STORY_CLEAN_PENDING_HUMAN_REVIEW"
STATUS_BUG = "PREMIUM_FORMAT_RENDER_BUG_REMAINS"
STORY_CHILD_CLEAN_ID = str(uuid5(NAMESPACE_URL, "investhome:brand-master:ornek-00013:format:9x16:stage4-0-clean"))


def generate_stage4_0_clean(
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
    preserved["quality40r"] = list(blob.get("stage4_0_retry_tests") or [])
    preserved["quality40r1"] = list(blob.get("stage4_0_r1_tests") or [])
    preserved["quality40r2"] = list(blob.get("stage4_0_r2_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Stage 4.0 clean requires ProjectCreativeMasterLibraryV1")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None:
        raise RuntimeError("Stage 4.0 clean requires the Investhome brand Premium Master")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Stage 4.0 clean requires Masters 01–03 records to remain")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    lock_before = blob.get("premium_creative_product_model_locked")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")
    parent_visual_before = parent.get("visual_asset")
    approved_count_before = count_approved_premium(library)

    original = load_asset(db, SELECTED_ASSET_ID)
    packed = compose_story_clean(original)
    refuse_if_unclean(packed["validation"])
    story = packed["story"]
    if packed["photo_pastes"] != 1:
        raise RuntimeError("Stage 4.0 clean must paste the photograph exactly once")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 clean must not call image generation")

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=None,
        content=_png(story),
        content_type="image/png",
        campaign_mode="investhome-brand-premium-story-9x16-clean",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="STAGE 4.0 CLEAN — exclusive semantic layers, R2 composition",
    )
    child_asset_id = str(asset.id)
    if child_asset_id in {SELECTED_ASSET_ID, APPROVED_ASSET_ID, APPROVED_ASSET_02, APPROVED_ASSET_03}:
        raise RuntimeError("Clean must not reuse a locked source asset id")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 clean must not call GPT Image")

    children = list(parent.get("format_children") or [])
    child_row = {
        "schema": "FormatAdaptationV1",
        "child_id": STORY_CHILD_CLEAN_ID,
        "parent_master_id": PRODUCTION_MASTER_ID,
        "parent_asset_id": SELECTED_ASSET_ID,
        "visual_asset": child_asset_id,
        "source_format": "4:5",
        "target_format": "9:16",
        "revision": "CLEAN",
        "status": STATUS_CLEAN,
        "is_premium_master": False,
        "router_eligible": False,
        "human_review": "PENDING",
        "auto_approved": False,
        "master_scope": "BRAND",
        "project_id": None,
        "brand_id": BRAND_ID,
        "photo": "ONE_CROP_ONE_SCALE_ONE_POSITION",
        "semantic_exclusivity": packed["validation"],
    }
    visual_before = parent.get("visual_asset")
    parent["format_children"] = [item for item in children if str(item.get("target_format")) != "9:16"] + [child_row]
    if parent.get("visual_asset") != visual_before:
        raise RuntimeError("Stage 4.0 clean refused to mutate the canonical visual_asset")

    library["stage4_0_status"] = STATUS_CLEAN
    library["stage4_story_child_id"] = STORY_CHILD_CLEAN_ID
    library["stage4_story_asset_id"] = child_asset_id
    library["next_production_phase"] = "WAIT FOR HUMAN VISUAL REVIEW"

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Stage 4.0 clean refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Stage 4.0 clean refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Stage 4.0 clean refused to mutate Master 03")
    if parent.get("visual_asset") != parent_visual_before:
        raise RuntimeError("Stage 4.0 clean mutated the brand master visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Stage 4.0 clean must not create another Premium Master")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Stage 4.0 clean refused to unlock the product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Stage 4.0 clean refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Stage 4.0 clean must not call GPT Image")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_0_status"] = STATUS_CLEAN
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["stage4_0_format_proof_tests"] = preserved.get("quality40")
    blob["stage4_0_retry_tests"] = preserved.get("quality40r")
    blob["stage4_0_r1_tests"] = preserved.get("quality40r1")
    blob["stage4_0_r2_tests"] = preserved.get("quality40r2")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_40_CLEAN,
        "created_at": _now(),
        "status": STATUS_CLEAN,
        "story_asset_id": child_asset_id,
        "story_child_id": STORY_CHILD_CLEAN_ID,
        "auto_approved": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "photo_pastes": 1,
        "validation": packed["validation"],
        "placements": packed["placements"],
        "boards": {
            "story": story,
            "mobile": render_mobile_preview(story),
        },
    }
    tests = list(blob.get("stage4_0_clean_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "boards"}), default=str)))
    blob["stage4_0_clean_tests"] = tests
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
