"""Phase 12.5-R1 — lock family-wide revision result. Approve PRICE children.

Does not generate pixels. Does not invent a 4:5 price. Does not fabricate 16:9.
Does not start Phase 12.6. Original format masters stay byte-for-byte immutable.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
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
from investhome_api.services.creative_director.phase10_3_finalize import approve_child_revision, preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import (
    ASSET_1X1,
    ASSET_4X5,
    ASSET_9X16,
    CAMPAIGN_NAME,
    FAMILY_ID,
    FILE_1X1,
    FILE_4X5,
    FILE_9X16,
    MASTER_1X1_ID,
    MASTER_4X5_ID,
    MASTER_9X16_ID,
    PROJECT_NAME,
    _sha,
    load_ornek_catalog,
)
from investhome_api.services.creative_director.phase12_4_approve_lock import PHASE_12_5_COMMAND, UNILOFT_PROJECT_ID
from investhome_api.services.creative_director.phase12_5_lock import CHILD_1X1_ID, CHILD_9X16_ID, REVISION_TYPE, _slot_identity
from investhome_api.services.creative_director.phase12_5_price_revise import NEW_VALUE, OLD_VALUE
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    ENGINE_PRODUCTION_READY,
    FAIL,
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    PARTIAL_SUCCESS,
    SKIP_FORMAT_MASTER_MISSING,
    SKIP_TARGET_NOT_PRESENT,
    SQUARE,
    STATUS_FAMILY_WIDE_PARTIAL,
    STORY_REEL,
    family_wide_revision_contract,
    family_wide_user_confirmation,
    score_family_wide_revision,
)
from investhome_api.services.creative_director.premium_creative_product_model import premium_revision_contract
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_12_5_R1 = "phase12_5_r1_family_wide_revision_result_lock"
NEXT_PHASE = "12.6 FAMILY-WIDE COPY REVISION PROOF"
CHILD_9X16_ASSET = "cecd49ce-cae5-45bd-a5f0-a09da6469894"
CHILD_1X1_ASSET = "b23be5d0-ce7b-45dc-8434-cb8efc3cc7fb"
APPROVED_SOURCES = (
    (FEED_PORTRAIT, FILE_4X5, ASSET_4X5, MASTER_4X5_ID),
    (STORY_REEL, FILE_9X16, ASSET_9X16, MASTER_9X16_ID),
    (SQUARE, FILE_1X1, ASSET_1X1, MASTER_1X1_ID),
)


def format_results() -> list[dict[str, Any]]:
    return [
        {
            "format": FEED_PORTRAIT,
            "source": FILE_4X5,
            "outcome": SKIP_TARGET_NOT_PRESENT,
            "applicable": False,
            "note": "Approved creative does not contain PRICE. Not invented. Not modified.",
        },
        {
            "format": STORY_REEL,
            "source": FILE_9X16,
            "outcome": "REVISED",
            "applicable": True,
            "approval_status": "HUMAN_APPROVED",
            "OLD_VALUE": OLD_VALUE,
            "NEW_VALUE": NEW_VALUE,
            "unrelated_visual_delta": 0,
        },
        {
            "format": SQUARE,
            "source": FILE_1X1,
            "outcome": "REVISED",
            "applicable": True,
            "approval_status": "HUMAN_APPROVED",
            "OLD_VALUE": OLD_VALUE,
            "NEW_VALUE": NEW_VALUE,
            "unrelated_visual_delta": 0,
        },
        {
            "format": LANDSCAPE,
            "source": None,
            "outcome": SKIP_FORMAT_MASTER_MISSING,
            "applicable": False,
            "note": "Format master missing. Not fabricated.",
        },
    ]


def generate_phase12_5_r1_revision_lock(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = user
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality121"] = list(blob.get("phase12_1_approval_tests") or [])
    preserved["quality122"] = list(blob.get("phase12_2_family_lock_tests") or [])
    preserved["quality123"] = list(blob.get("phase12_3_family_ingest_tests") or [])
    preserved["quality124"] = list(blob.get("phase12_4_family_approval_tests") or [])
    preserved["quality125"] = list(blob.get("phase12_5_family_wide_revision_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.5-R1 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.5-R1 requires Masters 01–03 records to remain")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")
    approved_count_before = count_approved_premium(library)
    ornek_before = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID),
        None,
    )
    if ornek_before is None:
        raise RuntimeError("Phase 12.5-R1 requires the ORNEK_00013 Creative Family to remain")
    ornek_inventory_before = dict(ornek_before.get("inventory") or {})
    family = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == FAMILY_ID),
        None,
    )
    if family is None:
        raise RuntimeError("Phase 12.5-R1 requires the UniLoft Last Units family")

    catalog = load_ornek_catalog(db)
    sha_before = {}
    identities = {}
    for fmt, filename, asset_id, master_id in APPROVED_SOURCES:
        item = catalog.get(filename)
        if item is None or item["asset_id"] != asset_id:
            raise RuntimeError(f"Phase 12.5-R1 could not load {filename}")
        live = _sha(_read_bytes(db, UUID(asset_id)))
        slot = family["formats"][fmt]
        if str(slot.get("SOURCE_SHA256")) != live or live != item["sha256"]:
            raise RuntimeError(f"Phase 12.5-R1 refused to start from a mutated {filename}")
        if str(slot.get("FORMAT_MASTER_ID")) != master_id or str(slot.get("SOURCE_ASSET_ID")) != asset_id:
            raise RuntimeError(f"Phase 12.5-R1 refused to retarget {fmt}")
        sha_before[filename] = live
        identities[fmt] = json.loads(json.dumps(_jsonable(_slot_identity(slot)), default=str))

    feed_kids = list(family["formats"][FEED_PORTRAIT].get("derived_revisions") or [])
    if feed_kids:
        raise RuntimeError("Phase 12.5-R1 must not create or keep a 4:5 revision child")
    if family["formats"][LANDSCAPE].get("FORMAT_MASTER_ID") is not None:
        raise RuntimeError("Phase 12.5-R1 fabricated 16:9")
    if family["formats"][LANDSCAPE].get("derived_revisions"):
        raise RuntimeError("Phase 12.5-R1 must not create a 16:9 child")

    story_child = approve_child_revision(
        family["formats"][STORY_REEL],
        revision_id=CHILD_9X16_ID,
        visual_asset=CHILD_9X16_ASSET,
    )
    square_child = approve_child_revision(
        family["formats"][SQUARE],
        revision_id=CHILD_1X1_ID,
        visual_asset=CHILD_1X1_ASSET,
    )
    if story_child.get("router_eligible") is not False or square_child.get("router_eligible") is not False:
        raise RuntimeError("Phase 12.5-R1 children must not replace the format master in the router")
    if str(story_child.get("visual_asset")) != CHILD_9X16_ASSET or str(square_child.get("visual_asset")) != CHILD_1X1_ASSET:
        raise RuntimeError("Phase 12.5-R1 refused to replace child visuals")
    if str(story_child.get("PARENT_FORMAT_MASTER_ID")) != MASTER_9X16_ID:
        raise RuntimeError("Phase 12.5-R1 9:16 child lost its parent format master")
    if str(square_child.get("PARENT_FORMAT_MASTER_ID")) != MASTER_1X1_ID:
        raise RuntimeError("Phase 12.5-R1 1:1 child lost its parent format master")

    members = format_results()
    result = score_family_wide_revision(members)
    if result != PARTIAL_SUCCESS:
        raise RuntimeError("Phase 12.5-R1 expected PARTIAL_SUCCESS")
    if result == FAIL:
        raise RuntimeError("A legitimate SKIP must not produce FAIL")

    confirmation = family_wide_user_confirmation(territory="PRICE", revised_count=2, language=language)
    family["phase12_5_status"] = STATUS_FAMILY_WIDE_PARTIAL
    family["phase12_5_human_review"] = "APPROVED"
    family["phase12_5_result"] = PARTIAL_SUCCESS
    family["family_wide_revision_engine"] = ENGINE_PRODUCTION_READY
    family["last_family_wide_revision"] = {
        "command": PHASE_12_5_COMMAND,
        "REVISION_TYPE": REVISION_TYPE,
        "result": PARTIAL_SUCCESS,
        "human_review": "APPROVED",
        "members": members,
        "user_facing": confirmation,
        "never_invent_missing_semantic": True,
    }
    library["phase12_5_status"] = STATUS_FAMILY_WIDE_PARTIAL
    library["family_wide_revision_engine"] = ENGINE_PRODUCTION_READY
    library["family_wide_revision_result_model"] = family_wide_revision_contract()
    library["next_production_phase"] = NEXT_PHASE
    library["phase12_6_executed"] = False

    for fmt, filename, asset_id, _master_id in APPROVED_SOURCES:
        slot = family["formats"][fmt]
        ident = json.loads(json.dumps(_jsonable(_slot_identity(slot)), default=str))
        if ident != identities[fmt]:
            raise RuntimeError(f"Phase 12.5-R1 mutated the {fmt} format master identity")
        live = _sha(_read_bytes(db, UUID(asset_id)))
        if live != sha_before[filename]:
            raise RuntimeError(f"Phase 12.5-R1 mutated original {filename}")
    if family["formats"][FEED_PORTRAIT].get("derived_revisions"):
        raise RuntimeError("Phase 12.5-R1 created a 4:5 child")
    ornek_after = next(item for item in library["premium_creative_families"] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID)
    if dict(ornek_after.get("inventory") or {}) != ornek_inventory_before:
        raise RuntimeError("Phase 12.5-R1 refused to alter the ORNEK_00013 inventory")
    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.5-R1 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.5-R1 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.5-R1 refused to mutate Master 03")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.5-R1 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.5-R1 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.5-R1 refused to change Master 03 visual")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None or parent.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.5-R1 refused to keep ORNEK_00013 as the brand master visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Phase 12.5-R1 must not create another library Premium Master")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.5-R1 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.5-R1 refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.5-R1 refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.5-R1 must not call GPT Image")
    if library.get("phase12_6_executed") is not False:
        raise RuntimeError("Phase 12.5-R1 must not execute Phase 12.6")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["phase12_2_family_lock_tests"] = preserved.get("quality122")
    blob["phase12_3_family_ingest_tests"] = preserved.get("quality123")
    blob["phase12_4_family_approval_tests"] = preserved.get("quality124")
    blob["phase12_5_family_wide_revision_tests"] = preserved.get("quality125")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    revision_contract = premium_revision_contract()
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_5_R1,
        "created_at": _now(),
        "PHASE": "12.5 FAMILY-WIDE NATURAL LANGUAGE REVISION PROOF",
        "status": STATUS_FAMILY_WIDE_PARTIAL,
        "HUMAN REVIEW": "APPROVED",
        "9:16 REVISION": "APPROVED",
        "1:1 REVISION": "APPROVED",
        "4:5": SKIP_TARGET_NOT_PRESENT,
        "16:9": SKIP_FORMAT_MASTER_MISSING,
        "UNRELATED VISUAL DELTA": 0,
        "ORIGINAL MASTERS MODIFIED": "NO",
        "FAMILY-WIDE REVISION ENGINE": ENGINE_PRODUCTION_READY,
        "result": PARTIAL_SUCCESS,
        "command": PHASE_12_5_COMMAND,
        "FAMILY_ID": FAMILY_ID,
        "FAMILY": CAMPAIGN_NAME,
        "PROJECT / BRAND": PROJECT_NAME,
        "PROJECT_ID": UNILOFT_PROJECT_ID,
        "user_facing": confirmation,
        "members": members,
        "approved_children": [
            {
                "format": STORY_REEL,
                "revision_id": CHILD_9X16_ID,
                "PARENT_FORMAT_MASTER_ID": MASTER_9X16_ID,
                "visual_asset": CHILD_9X16_ASSET,
                "approval_status": story_child.get("approval_status"),
                "router_eligible": story_child.get("router_eligible"),
            },
            {
                "format": SQUARE,
                "revision_id": CHILD_1X1_ID,
                "PARENT_FORMAT_MASTER_ID": MASTER_1X1_ID,
                "visual_asset": CHILD_1X1_ASSET,
                "approval_status": square_child.get("approval_status"),
                "router_eligible": square_child.get("router_eligible"),
            },
        ],
        "result_model": family_wide_revision_contract(),
        "revision_contract": revision_contract["family_wide_revision"],
        "immutability": {
            "byte_for_byte": True,
            "sha256": sha_before,
            "4x5_child_created": False,
            "16x9_child_created": False,
            "ornek_00013_inventory_unchanged": ornek_inventory_before,
        },
        "NEXT": NEXT_PHASE,
        "PHASE_12_6_EXECUTED": False,
        "gpt_image_calls": provider_call_count(),
        "ideogram_calls": 0,
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "temple_project_id": TEMPLE_PROJECT_ID,
    }
    tests_log = list(blob.get("phase12_5_r1_revision_lock_tests") or [])
    tests_log.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase12_5_r1_revision_lock_tests"] = tests_log
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
