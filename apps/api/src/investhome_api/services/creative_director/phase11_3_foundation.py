"""Phase 11.3 — Commercial Creative System Correction. No artwork. No Proof 03."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.campaign_reading_path_v1 import campaign_reading_path_schema
from investhome_api.services.creative_director.commercial_design_dna_v1 import commercial_design_dna_library
from investhome_api.services.creative_director.commercial_system_gate import commercial_system_gate_contract
from investhome_api.services.creative_director.commercial_typography_system_v1 import commercial_typography_system
from investhome_api.services.creative_director.creative_critic_v3 import critic_v3_contract
from investhome_api.services.creative_director.detached_commercial_lockup_detector import detached_commercial_lockup_detector_contract
from investhome_api.services.creative_director.fresh_critic_v3 import fresh_critic_v3_contract
from investhome_api.services.creative_director.integrated_campaign_concept import (
    integrated_campaign_concept_schema,
    temple_current_campaign_hierarchy_evaluation,
)
from investhome_api.services.creative_director.integrated_campaign_pipeline import INTEGRATED_PIPELINE_ID, integrated_campaign_pipeline
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.numeric_art_direction import numeric_art_direction_contract
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
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.stage3_canonical_pipeline import SUPERSEDED_PREMIUM_PATH, generation_path_audit
from investhome_api.services.creative_director.stage3_failure_learning_v2 import stage3_failure_learning_v2
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_3 = "phase11_3_commercial_creative_system"
NEXT_PHASE = "PHASE 11.4 — CREATIVE QUALITY PROOF 03"


def all_subsystems_ready() -> dict[str, str]:
    checks = {
        "COMMERCIAL_DESIGN_DNA": commercial_design_dna_library().get("status"),
        "INTEGRATED_CAMPAIGN_CONCEPT": integrated_campaign_concept_schema().get("status"),
        "CAMPAIGN_READING_PATH": campaign_reading_path_schema().get("status"),
        "COMMERCIAL_TYPOGRAPHY_SYSTEM": commercial_typography_system().get("status"),
        "NUMERIC_ART_DIRECTION": numeric_art_direction_contract().get("status"),
        "DETACHED_COMMERCIAL_LOCKUP_DETECTOR": detached_commercial_lockup_detector_contract().get("status"),
        "COMMERCIAL_SYSTEM_GATE": commercial_system_gate_contract().get("status"),
        "THUMBNAIL_TEST": "READY",
        "ADVERTISEMENT_VS_POSTER_TEST": "READY",
        "CREATIVE_CRITIC_V3": critic_v3_contract().get("status"),
        "FRESH_CRITIC_V3": fresh_critic_v3_contract().get("status"),
        "INTEGRATED_PIPELINE": integrated_campaign_pipeline().get("status"),
    }
    return {key: ("READY" if value in {"READY", "CANONICAL"} else "FAIL") for key, value in checks.items()}


def generate_phase11_3_commercial_creative_system(
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
    preserved["quality110"] = list(blob.get("phase11_0_foundation_tests") or [])
    preserved["quality111"] = list(blob.get("phase11_1_creative_quality_proof_tests") or [])
    preserved["quality112"] = list(blob.get("phase11_2_creative_quality_proof_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 11.3 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.3 requires locked Masters 01, 02, and 03")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    master_03_identity = _identity_slice(master_03)
    kids_visuals = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03.get("derived_revisions") or [])
    }
    proof_01_status = library.get("stage_3_creative_quality_proof")
    proof_02_status = library.get("stage_3_creative_quality_proof_02")

    subsystems = all_subsystems_ready()
    ready = all(value == "READY" for value in subsystems.values()) and count_approved_premium(library) == 3
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.3 must not call image generation")

    library["canonical_premium_generation_path"] = INTEGRATED_PIPELINE_ID
    library["superseded_premium_generation_path"] = SUPERSEDED_PREMIUM_PATH
    library["stage_3_commercial_creative_system"] = "READY" if ready else "FAIL"
    library["next_production_phase"] = NEXT_PHASE
    library["note"] = (
        "Stage 3 commercial creative system is locked. "
        "No new Temple advertisement was generated. Proof 01 and Proof 02 remain rejected learning."
    )

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 11.3 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 11.3 refused to change Master 02")
    if _identity_slice(master_03_after) != master_03_identity:
        raise RuntimeError("Phase 11.3 refused to mutate Master 03 identity")
    if {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03_after.get("derived_revisions") or [])
    } != kids_visuals:
        raise RuntimeError("Phase 11.3 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 11.3 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 11.3 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.3 refused to change Master 03 visual")
    if proof_01_status is not None and library.get("stage_3_creative_quality_proof") != proof_01_status:
        raise RuntimeError("Phase 11.3 refused to rewrite Proof 01 status")
    if proof_02_status is not None and library.get("stage_3_creative_quality_proof_02") != proof_02_status:
        raise RuntimeError("Phase 11.3 refused to rewrite Proof 02 status")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["canonical_premium_generation_path"] = INTEGRATED_PIPELINE_ID
    blob["superseded_premium_generation_path"] = SUPERSEDED_PREMIUM_PATH
    blob["integrated_campaign_pipeline"] = json.loads(json.dumps(_jsonable(integrated_campaign_pipeline()), default=str))
    blob["creative_critic_v3"] = json.loads(json.dumps(_jsonable(critic_v3_contract()), default=str))
    blob["commercial_design_dna_v1"] = json.loads(json.dumps(_jsonable(commercial_design_dna_library()), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    status = "COMMERCIAL_CREATIVE_SYSTEM_READY" if ready else "COMMERCIAL_CREATIVE_SYSTEM_FAIL"
    learning = stage3_failure_learning_v2()
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_3,
        "created_at": _now(),
        "status": status,
        "learning": learning,
        "subsystems": subsystems,
        "commercial_design_dna": commercial_design_dna_library(),
        "integrated_campaign_concept": integrated_campaign_concept_schema(),
        "campaign_reading_path": campaign_reading_path_schema(),
        "commercial_typography_system": commercial_typography_system(),
        "numeric_art_direction": numeric_art_direction_contract(),
        "detached_lockup": detached_commercial_lockup_detector_contract(),
        "commercial_system_gate": commercial_system_gate_contract(),
        "critic_v3": critic_v3_contract(),
        "fresh_critic_v3": fresh_critic_v3_contract(),
        "pipeline": integrated_campaign_pipeline(),
        "generation_path_audit": generation_path_audit(),
        "temple_hierarchy_evaluation": temple_current_campaign_hierarchy_evaluation(),
        "proof_01": "PRESERVED / REJECTED",
        "proof_02": "PRESERVED / REJECTED",
        "new_creative_generated": False,
        "proof_03_generated": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "master_03_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "stage_2": STAGE_2_STATUS,
        "stage_2_revision_compatibility": "PRESERVED",
        "canonical_premium_generation_path": INTEGRATED_PIPELINE_ID,
        "old_stage_3_pipeline": SUPERSEDED_PREMIUM_PATH,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "next_phase": NEXT_PHASE,
        "language": language,
    }
    tests = list(blob.get("phase11_3_commercial_creative_system_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_3_commercial_creative_system_tests"] = tests
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
        "canonical_premium_generation_path": library.get("canonical_premium_generation_path"),
        "superseded_premium_generation_path": library.get("superseded_premium_generation_path"),
        "stage_3_commercial_creative_system": library.get("stage_3_commercial_creative_system"),
        "stage_3_creative_quality_proof": library.get("stage_3_creative_quality_proof"),
        "stage_3_creative_quality_proof_02": library.get("stage_3_creative_quality_proof_02"),
        "human_approved_premium_count": count_approved_premium(library),
        "master_01_asset": master_01_after.get("visual_asset"),
        "master_02_asset": master_02_after.get("visual_asset"),
        "master_03_asset": master_03_after.get("visual_asset"),
    }
    return record
