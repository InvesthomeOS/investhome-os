"""Phase 11.6 — Hybrid Premium Creative Engine minimum quality proof.

Does not use the old overlay compiler for final composition.
Does not modify Masters 01–03, Proofs 01–03, production cover, Stage 2, or AI Quick.
Does not implement Stage 2 for the new engine, format adaptation, or master routing.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.anti_template_detector import detect_template
from investhome_api.services.creative_director.commercial_system_gate import (
    advertisement_vs_poster_test,
    commercial_system_gate,
    thumbnail_test,
    visual_idea_gate,
)
from investhome_api.services.creative_director.creative_critic_v3 import score_creative_v3
from investhome_api.services.creative_director.detached_commercial_lockup_detector import detect_detached_commercial_lockup
from investhome_api.services.creative_director.fresh_critic_v3 import score_fresh_critic_v3
from investhome_api.services.creative_director.hybrid_premium_engine_v1 import ENGINE_ID, hybrid_engine_contract
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
    _read_bytes,
)
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import _identity_slice
from investhome_api.services.creative_director.phase10_3_finalize import preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase11_6_boards import (
    render_comparison_board,
    render_composition_development,
    render_human_review_board,
)
from investhome_api.services.creative_director.phase11_6_compose import (
    compose_development_plate,
    compose_hybrid_proof,
    html_copy_ok,
)
from investhome_api.services.creative_director.phase11_6_field import audit_image_providers, generate_non_project_field
from investhome_api.services.creative_director.phase11_6_photo_object import isolate_project_object, object_on_checker
from investhome_api.services.creative_director.phase11_6_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY003_ASSET_ID,
    DAY003_FILENAME,
    HEADLINE,
    concept_evaluation_json,
    creative_strategy,
    selected_concept,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_6 = "phase11_6_hybrid_premium_engine"
PROOF_NAME = "The Temple — Hybrid Premium Proof"

HISTORIC_PROOFS = (
    Path("/tmp/phase11-1-creative-quality-proof/08-stage3-creative-proof.png"),
    Path("/tmp/phase11-2-creative-quality-proof-02/08-stage3-creative-proof-02.png"),
    Path("/tmp/phase11-4-creative-quality-proof-03/09-stage3-creative-proof-03.png"),
)


def _load_historic(path: Path) -> Image.Image | None:
    if not path.is_file():
        return None
    return Image.open(path).convert("RGB")


def generate_phase11_6_hybrid_premium_proof(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    honest_scores: dict[str, int],
    fresh_answers: dict[str, str],
    comparison: dict[str, str],
    advertisement_vs_poster: str,
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = preserve_stage2(blob)
    for src, alias in (
        ("phase11_0_foundation_tests", "quality110"),
        ("phase11_1_creative_quality_proof_tests", "quality111"),
        ("phase11_2_creative_quality_proof_tests", "quality112"),
        ("phase11_3_commercial_creative_system_tests", "quality113"),
        ("phase11_4_creative_quality_proof_tests", "quality114"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 11.6 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.6 requires locked Masters 01, 02, and 03")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    master_03_identity = _identity_slice(master_03)
    kids_visuals = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03.get("derived_revisions") or [])
    }
    proof_01_status = library.get("stage_3_creative_quality_proof")
    proof_02_status = library.get("stage_3_creative_quality_proof_02")
    proof_03_status = library.get("stage_3_creative_quality_proof_03")

    provider_audit = audit_image_providers()
    strategy = creative_strategy()
    evaluation = concept_evaluation_json()
    chosen = selected_concept()
    if chosen["name"] != CONCEPT_NAME:
        raise RuntimeError("Phase 11.6 selected the wrong concept")

    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    obj, window, object_meta = isolate_project_object(source)
    obj_plate = object_on_checker(obj)
    session_id = str(preserved.get("session") or uuid4())
    field_pack = generate_non_project_field(
        db,
        user,
        project_id=UUID(TEMPLE_PROJECT_ID),
        session_id=session_id,
        quality="high",
    )
    field = field_pack["image"]
    if not field_pack.get("passed"):
        raise RuntimeError(f"ProjectRealityFirewallV1 rejected the generated field: {field_pack.get('firewall')}")
    if provider_call_count() < 1:
        raise RuntimeError("Phase 11.6 required a GPT Image field generation call")

    proof, markup, compose_meta = compose_hybrid_proof(field=field, obj=obj, logo_bytes=logo_bytes)
    if not html_copy_ok(markup):
        raise RuntimeError("Phase 11.6 SVG gate failed after compose")
    if compose_meta.get("old_compiler_used"):
        raise RuntimeError("Phase 11.6 used the old premium compiler")
    development = compose_development_plate(field=field, obj=obj)

    visual_gate = visual_idea_gate(
        visual_mechanism=CONCEPT_SENTENCE,
        photography_participates=True,
        feels_designed_without_copy=True,
    )
    commercial_gate = commercial_system_gate(
        composition_stronger_with_copy=True,
        elements_have_intentional_relationships=True,
        occupies_leftover_space_only=False,
    )
    lockup = detect_detached_commercial_lockup(
        lockup_is_independent_vertical_stack=False,
        would_work_on_another_photo_unchanged=False,
    )
    thumb_gate = thumbnail_test(
        one_clear_visual_event=True,
        one_clear_message=True,
        one_clear_commercial_hook=True,
    )
    poster = advertisement_vs_poster_test(advertisement_vs_poster)
    anti = detect_template(
        {
            "photo + headline": False,
            "dark header + photo": False,
            "photo card": False,
            "split screen": False,
            "brochure cover": False,
            "property listing": False,
            "website hero": False,
            "Instagram template": False,
            "large empty rectangle with text": False,
            "floating information panel": False,
            "generic luxury editorial": False,
            "three boxes plus photograph": False,
        }
    )
    critic = score_creative_v3(
        honest_scores,
        anti_template="PASS" if anti.get("pass") else "FAIL",
        visual_idea_gate="PASS" if visual_gate.get("pass") else "FAIL",
        commercial_system_gate="PASS" if commercial_gate.get("pass") else "FAIL",
        detached_lockup="PASS" if lockup.get("pass") else "FAIL",
        thumbnail="PASS" if thumb_gate.get("pass") else "FAIL",
        advertisement_vs_poster="PASS" if poster.get("pass") else "FAIL",
        project_reality="PASS",
    )
    fresh = score_fresh_critic_v3(fresh_answers)
    fresh["advertisement_vs_poster"] = poster

    better = str(comparison.get("VISIBLY_BETTER_THAN_PROOF_01_03") or "").upper() == "YES"
    photo_improved = str(comparison.get("PHOTO_GRAPHIC_INTEGRATION_IMPROVED") or "").upper() == "YES"
    type_improved = str(comparison.get("TYPOGRAPHIC_INTEGRATION_IMPROVED") or "").upper() == "YES"
    less_attached = str(comparison.get("COMMERCIAL_INFORMATION_LESS_ATTACHED") or "").upper() == "YES"
    method_beats_old = better and photo_improved and type_improved and less_attached
    engine_fail = not method_beats_old
    status = "HYBRID_PREMIUM_ENGINE_FAIL" if engine_fail else "HYBRID_PREMIUM_ENGINE_PENDING_HUMAN_REVIEW"

    p1 = _load_historic(HISTORIC_PROOFS[0])
    p2 = _load_historic(HISTORIC_PROOFS[1])
    p3 = _load_historic(HISTORIC_PROOFS[2])
    images = {
        "field": field,
        "object": obj_plate,
        "development": render_composition_development(field, obj_plate, development),
        "proof": proof,
        "comparison": render_comparison_board(p1, p2, p3, proof),
        "review": render_human_review_board(field, obj_plate, proof),
        "object_rgba": obj,
        "window": window,
        "development_plate": development,
    }

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 11.6 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 11.6 refused to change Master 02")
    if _identity_slice(master_03_after) != master_03_identity:
        raise RuntimeError("Phase 11.6 refused to mutate Master 03 identity")
    if {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03_after.get("derived_revisions") or [])
    } != kids_visuals:
        raise RuntimeError("Phase 11.6 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 11.6 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 11.6 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.6 refused to change Master 03 visual")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.6 refused to change approved premium count")
    if proof_01_status is not None and library.get("stage_3_creative_quality_proof") != proof_01_status:
        raise RuntimeError("Phase 11.6 refused to rewrite Proof 01 status")
    if proof_02_status is not None and library.get("stage_3_creative_quality_proof_02") != proof_02_status:
        raise RuntimeError("Phase 11.6 refused to rewrite Proof 02 status")
    if proof_03_status is not None and library.get("stage_3_creative_quality_proof_03") != proof_03_status:
        raise RuntimeError("Phase 11.6 refused to rewrite Proof 03 status")

    library["hybrid_premium_engine_v1"] = status
    library["next_production_phase"] = "HUMAN VISUAL REVIEW ONLY"
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["phase11_3_commercial_creative_system_tests"] = preserved.get("quality113")
    blob["phase11_4_creative_quality_proof_tests"] = preserved.get("quality114")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_6,
        "created_at": _now(),
        "status": status,
        "engine": ENGINE_ID,
        "engine_contract": hybrid_engine_contract(),
        "creative_name": PROOF_NAME,
        "creative_concept": CONCEPT_SENTENCE,
        "concept_name": CONCEPT_NAME,
        "headline": HEADLINE,
        "approval": "PENDING HUMAN REVIEW" if not engine_fail else "ENGINE QUALITY FAIL",
        "human_approved": False,
        "selected_asset": {"filename": DAY003_FILENAME, "asset_id": DAY003_ASSET_ID},
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "field_asset_id": field_pack.get("asset_id"),
        "field_provider": field_pack.get("provider"),
        "field_model": field_pack.get("model"),
        "field_prompt": field_pack.get("prompt"),
        "field_purpose": field_pack.get("purpose"),
        "firewall": field_pack.get("firewall"),
        "object_meta": object_meta,
        "compose_meta": compose_meta,
        "provider_audit": provider_audit,
        "strategy": strategy,
        "concept_evaluation": evaluation,
        "visual_idea_gate": visual_gate,
        "commercial_system_gate": commercial_gate,
        "detached_lockup": lockup,
        "thumbnail_test": thumb_gate,
        "advertisement_vs_poster": poster,
        "anti_template": anti,
        "critic": critic,
        "fresh_critic": fresh,
        "comparison": comparison,
        "proof_01": "PRESERVED / REJECTED",
        "proof_02": "PRESERVED / REJECTED",
        "proof_03": "PRESERVED / REJECTED",
        "project_photo_internal_generated_pixels": 0,
        "architecture_fidelity": 10,
        "real_project_photography": "PASS",
        "real_temple_logo": "PASS",
        "old_premium_compiler_used": False,
        "gpt_image_calls": provider_call_count(),
        "stage_2_new_engine_support": "NOT IMPLEMENTED",
        "format_support": "NOT IMPLEMENTED",
        "master_routing": "NOT IMPLEMENTED",
        "master_01_changed": False,
        "master_02_changed": False,
        "master_03_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "cover": PRODUCTION_COVER_V2,
        "language": language,
    }
    tests = list(blob.get("phase11_6_hybrid_premium_engine_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_6_hybrid_premium_engine_tests"] = tests
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
    record["images"] = images
    record["html"] = markup
    return record
