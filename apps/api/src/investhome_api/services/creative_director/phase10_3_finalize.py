"""Phase 10.3 — Stage 2 natural-language revision engine lock.

Human-approves the proven children. Does not regenerate pixels.
Does not modify locked Premium Masters. Does not start Stage 3.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
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
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03, CREATIVE_CONCEPT
from investhome_api.services.creative_director.phase10_0_master import CHILD_REVISION_ID as PRICE_REJECTED_REVISION_ID
from investhome_api.services.creative_director.phase10_0_master import _identity_slice
from investhome_api.services.creative_director.phase10_0_r1_master import CHILD_REVISION_R1_ID as PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase10_0_r1_master import REJECTED_CHILD_ASSET_ID as PRICE_REJECTED_ASSET_ID
from investhome_api.services.creative_director.phase10_1_master import CHILD_REVISION_ID as COPY_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_2_master import CHILD_REVISION_ID as PHOTO_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_2_master import COPY_CHILD_ASSET_ID
from investhome_api.services.creative_director.phase10_2_master import PRICE_R1_ASSET_ID
from investhome_api.services.creative_director.phase10_2_master import _preserve as _preserve_102
from investhome_api.services.creative_director.phase10_2_master import _restore_history as _restore_102
from investhome_api.services.creative_director.phase10_3_revision_doctrine import (
    NEXT_PHASE,
    REVISION_DOCTRINE,
    STAGE_2_STATUS,
    revision_doctrine,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_10_3 = "phase10_3_stage_2_natural_language_revision_lock"
PHOTO_CHILD_ASSET_ID = "004a0ad8-13f9-4977-b5b6-19f859eca613"
STAGE_1_STATUS = "COMPLETE"
CORE_CAPABILITIES = 3

PROVEN = (
    {
        "capability": "PRICE_REVISION",
        "revision_id": PRICE_R1_REVISION_ID,
        "visual_asset": PRICE_R1_ASSET_ID,
        "revision_type": "PRICE_ONLY",
        "command": "Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme.",
    },
    {
        "capability": "COPY_REVISION",
        "revision_id": COPY_CHILD_REVISION_ID,
        "visual_asset": COPY_CHILD_ASSET_ID,
        "revision_type": "HEADLINE_ONLY",
        "command": "ALIRKEN KAZAN başlığını ŞİMDİ YATIRIM ZAMANI olarak değiştir, başka hiçbir şeyi değiştirme.",
    },
    {
        "capability": "PROJECT_PHOTO_REPLACEMENT",
        "revision_id": PHOTO_CHILD_REVISION_ID,
        "visual_asset": PHOTO_CHILD_ASSET_ID,
        "revision_type": "VISUAL_REPLACE_ONLY",
        "command": "Sağdaki dış cephe görselini başka bir gerçek Temple dış cephe görseliyle değiştir, başka hiçbir şeyi değiştirme.",
    },
)


def preserve_stage2(blob: dict[str, Any]) -> dict[str, Any]:
    return _preserve(blob)


def restore_stage2(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_history(blob, preserved)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_102(blob)
    preserved["quality102"] = list(blob.get("phase10_2_photo_replacement_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_102(blob, preserved)
    blob["phase10_2_photo_replacement_tests"] = preserved.get("quality102")


def _find_child(parent: dict[str, Any], revision_id: str) -> dict[str, Any]:
    for item in parent.get("derived_revisions") or []:
        if str(item.get("revision_id")) == str(revision_id):
            return item
    raise RuntimeError(f"derived revision {revision_id} is missing")


def approve_child_revision(
    parent: dict[str, Any],
    *,
    revision_id: str,
    visual_asset: str,
) -> dict[str, Any]:
    child = _find_child(parent, revision_id)
    if str(child.get("visual_asset") or "") != str(visual_asset):
        raise RuntimeError("Phase 10.3 refused to replace a child visual")
    before = str(child.get("visual_asset"))
    child["approval_status"] = "HUMAN_APPROVED"
    child["human_review"] = "APPROVED"
    child["approved_at"] = child.get("approved_at") or _now()
    child["router_eligible"] = False
    if str(child.get("visual_asset")) != before:
        raise RuntimeError("Phase 10.3 refused to mutate a child visual asset")
    return child


def lock_stage_2_revision_engine(library: dict[str, Any]) -> dict[str, Any]:
    master_03 = next(
        (item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID),
        None,
    )
    if master_03 is None:
        raise RuntimeError("Phase 10.3 requires locked Premium Campaign 03")
    if str(master_03.get("visual_asset") or "") != APPROVED_ASSET_03:
        raise RuntimeError("Phase 10.3 refused to change Master 03 visual")
    if master_03.get("approval_status") != "HUMAN_APPROVED" or master_03.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 10.3 requires Master 03 HUMAN_APPROVED LOCKED_MASTER")

    approved = []
    for item in PROVEN:
        approved.append(approve_child_revision(master_03, revision_id=item["revision_id"], visual_asset=item["visual_asset"]))

    rejected = _find_child(master_03, PRICE_REJECTED_REVISION_ID)
    if str(rejected.get("visual_asset") or "") != PRICE_REJECTED_ASSET_ID:
        raise RuntimeError("Phase 10.3 refused to mutate the rejected price child")
    if rejected.get("approval_status") == "HUMAN_APPROVED":
        raise RuntimeError("Phase 10.3 refused to approve the rejected price child")
    rejected["human_review"] = "REJECTED"

    doctrine = revision_doctrine()
    library["stage_1"] = STAGE_1_STATUS
    library["stage_2"] = STAGE_2_STATUS
    library["stage_2_natural_language_revision"] = STAGE_2_STATUS
    library["stage_2_executed"] = True
    library["stage_3_executed"] = False
    library["price_revision"] = "HUMAN_APPROVED"
    library["copy_revision"] = "HUMAN_APPROVED"
    library["project_photo_replacement"] = "HUMAN_APPROVED"
    library["core_revision_capabilities"] = f"{CORE_CAPABILITIES}/{CORE_CAPABILITIES} HUMAN_APPROVED"
    library["natural_language_revision_doctrine"] = REVISION_DOCTRINE
    library["next_production_phase"] = NEXT_PHASE
    library["premium_creative_master_library"] = "COMPLETE"
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["note"] = (
        "Stage 2 Natural-Language Revision is COMPLETE. "
        "Price, copy, and project-photo replacement are HUMAN_APPROVED. "
        "Locked Premium Masters are unchanged. Stage 3 Creative Quality Engine is not executed."
    )
    library["revision_doctrine"] = doctrine
    return {
        "master_03": master_03,
        "approved_children": approved,
        "rejected_price_child": rejected,
        "doctrine": doctrine,
    }


def generate_phase10_3_stage_2_finalization(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = user
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 10.3 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 10.3 requires locked Masters 01, 02, and 03")
    if master_01.get("approval_status") != "HUMAN_APPROVED" or master_01.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 10.3 requires Master 01 HUMAN_APPROVED LOCKED_MASTER")
    if master_02.get("approval_status") != "HUMAN_APPROVED" or master_02.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 10.3 requires Master 02 HUMAN_APPROVED LOCKED_MASTER")
    if str(master_01.get("visual_asset") or "") != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 10.3 refused to change Master 01 visual")
    if str(master_02.get("visual_asset") or "") != APPROVED_ASSET_02:
        raise RuntimeError("Phase 10.3 refused to change Master 02 visual")

    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    parent_identity_before = _identity_slice(master_03)
    parent_visual_before = str(master_03.get("visual_asset"))
    kids_visuals_before = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03.get("derived_revisions") or [])
    }

    locked = lock_stage_2_revision_engine(library)
    approved_master = locked["master_03"]
    if str(approved_master.get("visual_asset")) != parent_visual_before or str(approved_master.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 10.3 refused to replace the locked parent visual")
    if _identity_slice(approved_master) != parent_identity_before:
        raise RuntimeError("Phase 10.3 refused to mutate locked Master 03 identity")
    kids_visuals_after = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (approved_master.get("derived_revisions") or [])
    }
    if kids_visuals_after != kids_visuals_before:
        raise RuntimeError("Phase 10.3 refused to regenerate or replace child visuals")

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 10.3 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 10.3 refused to change Master 02")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 10.3 must not change locked Premium Master approvals")
    if library.get("stage_3_executed") is not False:
        raise RuntimeError("Phase 10.3 must not execute Stage 3")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 10.3 must not call image generation")

    photo_child = _find_child(approved_master, PHOTO_CHILD_REVISION_ID)
    price_child = _find_child(approved_master, PRICE_R1_REVISION_ID)
    copy_child = _find_child(approved_master, COPY_CHILD_REVISION_ID)
    if photo_child.get("approval_status") != "HUMAN_APPROVED" or photo_child.get("router_eligible") is not False:
        raise RuntimeError("Phase 10.3 expected the photo replacement child HUMAN_APPROVED and not router eligible")
    if str(photo_child.get("visual_asset")) != PHOTO_CHILD_ASSET_ID:
        raise RuntimeError("Phase 10.3 must keep the existing 10.2 child raster")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["natural_language_revision_doctrine"] = json.loads(json.dumps(_jsonable(locked["doctrine"]), default=str))
    blob["stage_2_natural_language_revision"] = STAGE_2_STATUS
    blob["stage_3_executed"] = False

    structural = (
        library.get("stage_2") == STAGE_2_STATUS
        and library.get("stage_2_natural_language_revision") == STAGE_2_STATUS
        and library.get("stage_3_executed") is False
        and library.get("price_revision") == "HUMAN_APPROVED"
        and library.get("copy_revision") == "HUMAN_APPROVED"
        and library.get("project_photo_replacement") == "HUMAN_APPROVED"
        and photo_child.get("approval_status") == "HUMAN_APPROVED"
        and str(approved_master.get("visual_asset")) == APPROVED_ASSET_03
        and count_approved_premium(library) == 3
        and provider_call_count() == 0
    )
    status = "STAGE_2_NATURAL_LANGUAGE_REVISION_COMPLETE" if structural else "STAGE_2_NOT_READY"

    approved_revisions = [
        {
            "capability": item["capability"],
            "status": "HUMAN_APPROVED",
            "revision_id": item["revision_id"],
            "visual_asset": item["visual_asset"],
            "revision_type": item["revision_type"],
            "command": item["command"],
            "router_eligible": False,
            "visual_regenerated": False,
        }
        for item in PROVEN
    ]
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_10_3,
        "created_at": _now(),
        "status": status,
        "stage_1": STAGE_1_STATUS,
        "stage_2": STAGE_2_STATUS,
        "stage_2_natural_language_revision": STAGE_2_STATUS,
        "price_revision": "HUMAN_APPROVED",
        "copy_revision": "HUMAN_APPROVED",
        "project_photo_replacement": "HUMAN_APPROVED",
        "core_revision_capabilities": f"{CORE_CAPABILITIES}/{CORE_CAPABILITIES} HUMAN_APPROVED",
        "natural_language_routing": "LOCKED",
        "targeted_territory_reconstruction": "LOCKED",
        "local_responsive_copy_recomposition": "LOCKED",
        "real_project_photo_replacement": "LOCKED",
        "approved_master_immutability": "LOCKED",
        "project_reality_policy": "LOCKED",
        "revision_doctrine": REVISION_DOCTRINE,
        "doctrine": locked["doctrine"],
        "approved_revisions": approved_revisions,
        "photo_child_revision_id": PHOTO_CHILD_REVISION_ID,
        "photo_child_asset_id": PHOTO_CHILD_ASSET_ID,
        "price_r1_revision_id": PRICE_R1_REVISION_ID,
        "copy_child_revision_id": COPY_CHILD_REVISION_ID,
        "rejected_price_revision_id": PRICE_REJECTED_REVISION_ID,
        "visual_regenerated": False,
        "new_master_created": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "master_03_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "stage_3_executed": False,
        "gpt_image_calls": provider_call_count(),
        "human_approved_premium_count": count_approved_premium(library),
        "premium_creative_master_library": library.get("premium_creative_master_library"),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "master_01_id": APPROVED_MASTER_ID,
        "master_01_asset_id": APPROVED_ASSET_ID,
        "master_02_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "master_02_asset_id": APPROVED_ASSET_02,
        "master_03_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "master_03_asset_id": APPROVED_ASSET_03,
        "creative_concept": CREATIVE_CONCEPT,
        "cover": PRODUCTION_COVER_V2,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "next_phase": NEXT_PHASE,
        "language": language,
        "price_child_status": price_child.get("approval_status"),
        "copy_child_status": copy_child.get("approval_status"),
        "photo_child_status": photo_child.get("approval_status"),
    }
    tests = list(blob.get("phase10_3_stage_2_finalization_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase10_3_stage_2_finalization_tests"] = tests
    _restore_history(blob, preserved)
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
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
    record["approved_photo_child"] = json.loads(json.dumps(_jsonable(photo_child), default=str))
    record["library_state"] = {
        "premium_creative_master_library": library.get("premium_creative_master_library"),
        "human_approved_premium_count": count_approved_premium(library),
        "stage_1": library.get("stage_1"),
        "stage_2": library.get("stage_2"),
        "stage_2_natural_language_revision": library.get("stage_2_natural_language_revision"),
        "stage_3_executed": library.get("stage_3_executed"),
        "price_revision": library.get("price_revision"),
        "copy_revision": library.get("copy_revision"),
        "project_photo_replacement": library.get("project_photo_replacement"),
        "core_revision_capabilities": library.get("core_revision_capabilities"),
        "next_production_phase": library.get("next_production_phase"),
        "master_01": {
            "master_id": APPROVED_MASTER_ID,
            "approval_status": master_01_after.get("approval_status"),
            "master_state": master_01_after.get("master_state"),
            "visual_asset": master_01_after.get("visual_asset"),
        },
        "master_02": {
            "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
            "master_name": MASTER_NAME_02,
            "approval_status": master_02_after.get("approval_status"),
            "master_state": master_02_after.get("master_state"),
            "visual_asset": master_02_after.get("visual_asset"),
        },
        "master_03": {
            "master_id": TEMPLE_PREMIUM_MASTER_03_ID,
            "master_name": MASTER_NAME_03,
            "approval_status": approved_master.get("approval_status"),
            "master_state": approved_master.get("master_state"),
            "visual_asset": approved_master.get("visual_asset"),
            "creative_concept": CREATIVE_CONCEPT,
        },
    }
    return record
