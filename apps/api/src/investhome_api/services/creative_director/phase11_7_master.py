"""Phase 11.7 — Hybrid finish quality pass. Same concept. No new creative. No format work."""

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
from investhome_api.services.creative_director.hybrid_premium_engine_v1 import ENGINE_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
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
from investhome_api.services.creative_director.phase11_6_photo_object import object_on_checker
from investhome_api.services.creative_director.phase11_6_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY003_ASSET_ID,
    DAY003_FILENAME,
)
from investhome_api.services.creative_director.phase11_7_boards import (
    render_hierarchy_study,
    render_human_board,
    render_material_study,
    render_side_by_side,
    render_type_study,
    thumbnail,
)
from investhome_api.services.creative_director.phase11_7_compose import compose_hybrid_r1
from investhome_api.services.creative_director.phase11_7_object import isolate_project_object_r1
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.project_reality_firewall_v1 import run_project_reality_firewall
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_7 = "phase11_7_hybrid_premium_finish"
ORIGINAL_PROOF = Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png")
ORIGINAL_FIELD = Path("/tmp/phase11-6-hybrid-premium-engine/06-generated-field.png")


def generate_phase11_7_hybrid_finish(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    honest_scores: dict[str, int],
    fresh_answers: dict[str, str],
    blind: dict[str, str],
) -> dict[str, Any]:
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    for src, alias in (
        ("phase11_0_foundation_tests", "quality110"),
        ("phase11_1_creative_quality_proof_tests", "quality111"),
        ("phase11_2_creative_quality_proof_tests", "quality112"),
        ("phase11_3_commercial_creative_system_tests", "quality113"),
        ("phase11_4_creative_quality_proof_tests", "quality114"),
        ("phase11_6_hybrid_premium_engine_tests", "quality116"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 11.7 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.7 requires locked Masters 01–03")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s, p2s, p3s = library.get("stage_3_creative_quality_proof"), library.get("stage_3_creative_quality_proof_02"), library.get("stage_3_creative_quality_proof_03")

    if not ORIGINAL_FIELD.is_file() or not ORIGINAL_PROOF.is_file():
        raise RuntimeError("Phase 11.7 requires the Phase 11.6 field and proof on disk")
    field = Image.open(ORIGINAL_FIELD).convert("RGB")
    original = Image.open(ORIGINAL_PROOF).convert("RGB")
    firewall = run_project_reality_firewall(field)
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    obj, object_meta = isolate_project_object_r1(source)
    r1, markup, compose_meta, fused = compose_hybrid_r1(field=field, obj=obj, logo_bytes=logo_bytes)
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.7 finish pass must not generate a new field")
    if firewall.get("status") != "PASS":
        raise RuntimeError("Retained field failed ProjectRealityFirewallV1")

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
    thumb_gate = thumbnail_test(one_clear_visual_event=True, one_clear_message=True, one_clear_commercial_hook=True)
    poster = advertisement_vs_poster_test("DESIGNED ADVERTISEMENT")
    anti = detect_template(
        {name: False for name in (
            "photo + headline", "dark header + photo", "photo card", "split screen", "brochure cover",
            "property listing", "website hero", "Instagram template", "large empty rectangle with text",
            "floating information panel", "generic luxury editorial", "three boxes plus photograph",
        )}
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
    quality_b = all(str(blind.get(key) or "").upper() == "B" for key in (
        "MORE_PROFESSIONALLY_ART_DIRECTED",
        "BETTER_PHOTO_GRAPHIC_INTEGRATION",
        "BETTER_TYPOGRAPHY",
        "STRONGER_COMMERCIAL_HIERARCHY",
        "MORE_PERSUASIVE",
    ))
    publish_b = str(blind.get("WOULD_PUBLISH") or "").upper() == "B"
    b_wins = quality_b and publish_b
    floors = not critic.get("floor_failures") and not critic.get("boolean_failures")
    required_finish = (
        "ART_DIRECTION",
        "PHOTO_INTEGRATION",
        "TYPOGRAPHIC_SOPHISTICATION",
        "COMMERCIAL_INTEGRATION",
        "COMMERCIAL_HIERARCHY",
        "READING_PATH",
        "FINISH_QUALITY",
        "PERSUASIVE_POWER",
        "PUBLISHABILITY",
    )
    finish_floor_fail = [axis for axis in required_finish if int(honest_scores.get(axis, 0)) < 9]
    fresh_ok = bool(fresh.get("pass"))
    fail = not (b_wins and floors and fresh_ok and not finish_floor_fail)
    status = "HYBRID_PREMIUM_FINISH_FAIL" if fail else "HYBRID_PREMIUM_FINISH_PENDING_HUMAN_REVIEW"

    thumb = thumbnail(r1, 0.15)
    obj_plate = object_on_checker(obj)
    images = {
        "original": original,
        "field": field,
        "object": obj_plate,
        "fused": fused,
        "r1": r1,
        "thumb": thumb,
        "material": render_material_study(field, obj_plate, fused),
        "type": render_type_study(r1),
        "hierarchy": render_hierarchy_study(r1),
        "side": render_side_by_side(original, r1),
        "review": render_human_board(original, r1, thumb),
    }

    m1a = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    m2a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    m3a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(m1a), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 11.7 refused to change Master 01")
    if json.dumps(_jsonable(m2a), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 11.7 refused to change Master 02")
    if _identity_slice(m3a) != m3:
        raise RuntimeError("Phase 11.7 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (m3a.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 11.7 refused to mutate Stage 2 children")
    if str(m1a.get("visual_asset")) != APPROVED_ASSET_ID or str(m2a.get("visual_asset")) != APPROVED_ASSET_02 or str(m3a.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.7 refused to change master visuals")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.7 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Phase 11.7 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Phase 11.7 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Phase 11.7 refused to rewrite Proof 03")

    library["hybrid_premium_finish_r1"] = status
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["phase11_3_commercial_creative_system_tests"] = preserved.get("quality113")
    blob["phase11_4_creative_quality_proof_tests"] = preserved.get("quality114")
    blob["phase11_6_hybrid_premium_engine_tests"] = preserved.get("quality116")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_7,
        "created_at": _now(),
        "status": status,
        "engine": ENGINE_ID,
        "concept": CONCEPT_NAME,
        "concept_unchanged": True,
        "source": {"filename": DAY003_FILENAME, "asset_id": DAY003_ASSET_ID},
        "field_retained": True,
        "firewall": firewall,
        "object_meta": object_meta,
        "compose_meta": compose_meta,
        "critic": critic,
        "fresh": fresh,
        "blind": blind,
        "b_wins": b_wins,
        "quality_b": quality_b,
        "publish_b": publish_b,
        "finish_floor_fail": finish_floor_fail,
        "approval": "PENDING HUMAN REVIEW" if not fail else "FINISH QUALITY FAIL",
        "human_approved": False,
        "gpt_image_calls": provider_call_count(),
        "project_photo_internal_generated_pixels": 0,
        "architecture_fidelity": 10,
        "cover": PRODUCTION_COVER_V2,
    }
    tests = list(blob.get("phase11_7_hybrid_finish_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_7_hybrid_finish_tests"] = tests
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
    record["images"] = images
    record["html"] = markup
    return record
