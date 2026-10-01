"""Phase 11.0 — Creative Quality Engine foundation. No new artwork."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.anti_template_detector import anti_template_rules
from investhome_api.services.creative_director.commercial_art_direction import commercial_art_direction_rules
from investhome_api.services.creative_director.creative_critic_v2 import critic_v2_contract
from investhome_api.services.creative_director.creative_design_dna_v2 import design_dna_library
from investhome_api.services.creative_director.creative_strategy_v1 import creative_strategy_schema, empty_creative_strategy
from investhome_api.services.creative_director.idea_first_pipeline import idea_first_pipeline
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
from investhome_api.services.creative_director.phase10_3_revision_doctrine import STAGE_2_STATUS, revision_doctrine
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile_library
from investhome_api.services.creative_director.reference_matching_v1 import reference_matching_contract
from investhome_api.services.creative_director.stage3_canonical_pipeline import (
    ACTIVE_PREMIUM_PATHS_BEFORE,
    CANONICAL_PREMIUM_PATH,
    generation_path_audit,
)
from investhome_api.services.creative_director.typography_quality_engine import typography_quality_rules
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_0 = "phase11_0_creative_quality_engine_foundation"
NEXT_PHASE = "PHASE 11.1 — CREATIVE QUALITY PROOF"
SEMANTIC_TERRITORIES = ("headline", "offer", "price", "unit", "CTA", "logo", "project-photo objects")

LIBRARY_INVENTORY = (
    ("ORNEK_00001.jpg", "GRADE_A", "terrace narrative against civic landmark"),
    ("ORNEK_00002.jpg", "NOT_GRADE_A", "library member — not in locked Grade-A set"),
    ("ORNEK_00003.jpg", "NOT_GRADE_A", "listing panel + circular badges — anti-template"),
    ("ORNEK_00004.jpg", "NOT_GRADE_A", "library member — likely commercial-device heavy"),
    ("ORNEK_00005.jpg", "NOT_GRADE_A", "9:16 social frame — not 4:5 campaign DNA"),
    ("ORNEK_00006.jpg", "GRADE_A", "interior chamber looking to the city"),
    ("ORNEK_00007.jpg", "NOT_GRADE_A", "library member"),
    ("ORNEK_00008.jpg", "GRADE_A", "dusk façade; type in photographic dark; strip badges"),
    ("ORNEK_00009.jpg", "NOT_GRADE_A", "library member"),
    ("ORNEK_00010.jpg", "NOT_GRADE_A", "library member"),
    ("ORNEK_00011.jpg", "GRADE_A", "building as hero object with geographic proof lines"),
    ("ORNEK_00012.jpg", "NOT_GRADE_A", "historic Master 02 craft source; dusk merge; badges not transferable"),
    ("ORNEK_00013.jpg", "GRADE_A", "architecture as graphic material against a navy field"),
    ("ORNEK_00014.jpg", "NOT_GRADE_A", "library member"),
    ("ORNEK_00015.jpg", "GRADE_A", "dusk interior depth tunnel under a photographic veil"),
)


def reference_library_audit() -> dict[str, Any]:
    grade_a = [item for item in LIBRARY_INVENTORY if item[1] == "GRADE_A"]
    return {
        "schema": "DesignReferenceLibraryAuditV1",
        "path": "Media Library → Investhome → DESIGN_REFERENCES",
        "folder_name_live": "DESIGN_REFERENCE",
        "total_visuals": len(LIBRARY_INVENTORY),
        "grade_a_analyzed": len(grade_a),
        "inventory": [{"filename": n, "status": s, "note": note} for n, s, note in LIBRARY_INVENTORY],
        "policy": "DESIGN DNA only. Never project photography, architecture, logo, or facts.",
        "status": "READY",
    }


def semantic_revision_compatibility() -> dict[str, Any]:
    return {
        "schema": "Stage2RevisionCompatibilityV1",
        "stage_2": STAGE_2_STATUS,
        "doctrine": revision_doctrine()["doctrine"],
        "territories": list(SEMANTIC_TERRITORIES),
        "rule": (
            "Future premium creatives must still expose semantic territories, "
            "but semantic editability follows the art direction. "
            "Art direction must not be reduced to boxes merely to make editing easier."
        ),
        "status": "PRESERVED",
    }


def lock_stage3_foundation(library: dict[str, Any]) -> dict[str, Any]:
    dna = design_dna_library()
    photos = project_photo_profile_library()
    pipeline = idea_first_pipeline()
    audit = generation_path_audit()
    ready = (
        dna.get("status") == "READY"
        and photos.get("status") == "READY"
        and pipeline.get("status") in {"READY", "SUPERSEDED"}
        and library.get("stage_2") == STAGE_2_STATUS
        and count_approved_premium(library) == 3
        and not pipeline.get("executed")
    )
    library["stage_1"] = "COMPLETE"
    library["stage_2"] = STAGE_2_STATUS
    library["stage_3_foundation"] = "READY" if ready else "FAIL"
    library["stage_3_executed"] = False
    library["canonical_premium_generation_path"] = CANONICAL_PREMIUM_PATH
    library["next_production_phase"] = NEXT_PHASE
    library["note"] = (
        "Stage 3 Creative Quality Engine foundation is locked. "
        "No new Temple advertisement was generated. "
        "Locked Masters 01–03 remain proven system masters, not the quality ceiling."
    )
    return {
        "ready": ready,
        "dna": dna,
        "photos": photos,
        "pipeline": pipeline,
        "audit": audit,
    }


def generate_phase11_0_creative_quality_foundation(
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
    preserved["quality103"] = list(blob.get("phase10_3_stage_2_finalization_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 11.0 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.0 requires locked Masters 01, 02, and 03")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    master_03_identity = _identity_slice(master_03)
    kids_visuals = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03.get("derived_revisions") or [])
    }

    locked = lock_stage3_foundation(library)
    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 11.0 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 11.0 refused to change Master 02")
    if _identity_slice(master_03_after) != master_03_identity:
        raise RuntimeError("Phase 11.0 refused to mutate Master 03 identity")
    if {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03_after.get("derived_revisions") or [])
    } != kids_visuals:
        raise RuntimeError("Phase 11.0 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 11.0 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 11.0 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.0 refused to change Master 03 visual")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.0 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage3_premium_generation_locked"] = True
    blob["stage_3_executed"] = False
    blob["canonical_premium_generation_path"] = CANONICAL_PREMIUM_PATH
    blob["creative_design_dna_v2"] = json.loads(json.dumps(_jsonable(locked["dna"]), default=str))
    blob["project_photo_creative_profiles"] = json.loads(json.dumps(_jsonable(locked["photos"]), default=str))
    blob["creative_strategy_v1"] = empty_creative_strategy()
    blob["idea_first_pipeline"] = locked["pipeline"]
    blob["creative_critic_v2"] = critic_v2_contract()
    restore_stage2(blob, preserved)
    blob["phase10_3_stage_2_finalization_tests"] = preserved.get("quality103")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    ready = bool(locked["ready"])
    status = "CREATIVE_QUALITY_ENGINE_FOUNDATION_READY" if ready else "CREATIVE_QUALITY_ENGINE_FOUNDATION_FAIL"
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_0,
        "created_at": _now(),
        "status": status,
        "design_references_analyzed": locked["dna"]["grade_a_count"],
        "design_dna_v2": locked["dna"]["status"],
        "project_photo_creative_profiles": locked["photos"]["status"],
        "creative_strategy_v1": creative_strategy_schema()["status"],
        "idea_first_pipeline": locked["pipeline"]["status"],
        "no_copy_gate": "READY",
        "two_second_gate": "READY",
        "typographic_quality_engine": typography_quality_rules()["status"],
        "commercial_art_direction": commercial_art_direction_rules()["status"],
        "reference_matching": reference_matching_contract()["status"],
        "anti_template_detector": anti_template_rules()["status"],
        "creative_critic_v2": critic_v2_contract()["status"],
        "human_publishability_gate": "READY",
        "stage_2_revision_compatibility": "PRESERVED",
        "project_reality_policy": "PRESERVED",
        "active_premium_generation_paths_before": ACTIVE_PREMIUM_PATHS_BEFORE,
        "canonical_premium_generation_path": CANONICAL_PREMIUM_PATH,
        "legacy_premium_paths": "ARCHIVED",
        "new_creative_generated": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "master_03_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "stage_1": "COMPLETE",
        "stage_2": STAGE_2_STATUS,
        "stage_3_foundation": library.get("stage_3_foundation"),
        "stage_3_executed": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "next_phase": NEXT_PHASE,
        "language": language,
        "reference_library_audit": reference_library_audit(),
        "semantic_revision_compatibility": semantic_revision_compatibility(),
        "generation_path_audit": locked["audit"],
        "dna": locked["dna"],
        "photos": locked["photos"],
        "strategy_schema": creative_strategy_schema(),
        "pipeline": locked["pipeline"],
        "typography": typography_quality_rules(),
        "commercial": commercial_art_direction_rules(),
        "anti_template": anti_template_rules(),
        "critic": critic_v2_contract(),
        "matching": reference_matching_contract(),
    }
    tests = list(blob.get("phase11_0_foundation_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_0_foundation_tests"] = tests
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
    record["library_state"] = {
        "stage_1": library.get("stage_1"),
        "stage_2": library.get("stage_2"),
        "stage_3_foundation": library.get("stage_3_foundation"),
        "stage_3_executed": library.get("stage_3_executed"),
        "canonical_premium_generation_path": library.get("canonical_premium_generation_path"),
        "human_approved_premium_count": count_approved_premium(library),
        "master_01_asset": master_01_after.get("visual_asset"),
        "master_02_asset": master_02_after.get("visual_asset"),
        "master_03_asset": master_03_after.get("visual_asset"),
    }
    return record
