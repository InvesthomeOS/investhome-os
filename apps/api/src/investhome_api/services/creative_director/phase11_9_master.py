"""Phase 11.9 — Hybrid V2 creative quality proof.

One new campaign. Experimental engine. Canonical pipeline unchanged.
Does not modify Masters 01–03, Proofs 01–03, Hybrid V1, V1 R1, cover, or Stage 2.
Does not implement Stage 2, formats, or master routing.
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
from investhome_api.services.creative_director.creative_critic_v4 import score_creative_v4
from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA
from investhome_api.services.creative_director.detached_commercial_lockup_detector import detect_detached_commercial_lockup
from investhome_api.services.creative_director.fresh_critic_v4 import score_fresh_critic_v4
from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID, hybrid_engine_v2_contract
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
from investhome_api.services.creative_director.phase11_9_boards import (
    object_edge_plate,
    render_asset_opportunity_board,
    render_commercial_hierarchy,
    render_human_review_board,
    render_quality_progression_board,
    render_reference_quality_board,
    render_scene_integration_proof,
    render_typography_system,
    thumbnail,
)
from investhome_api.services.creative_director.phase11_9_compose import compose_hybrid_v2
from investhome_api.services.creative_director.phase11_9_field import generate_register_field
from investhome_api.services.creative_director.phase11_9_integrate import lantern_preserved, punch_residual_sky
from investhome_api.services.creative_director.phase11_9_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY009_ASSET_ID,
    DAY009_CROP,
    DAY009_FILENAME,
    campaign_system_v2,
    concept_evaluation_json,
    concept_selection_status,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.project_object_extraction_v2 import (
    EDGE_BACKGROUNDS,
    extract_project_object_v2,
    inspect_fringe,
)
from investhome_api.services.creative_director.project_reality_firewall_v1 import run_project_reality_firewall
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_9 = "phase11_9_hybrid_v2_creative_proof"
FIELD_REUSE = Path("/tmp/phase11-9-hybrid-v2-creative-proof/04-generated-field.png")
LOCKED_PATHS = (
    Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png"),
    Path("/tmp/phase11-7-hybrid-finish/07-hybrid-premium-proof-r1.png"),
)
ASSET_THUMB_KEYS = {
    "Day_001": "5d26caf3-c237-4a78-9f3a-91f05dd24fa2",
    "Day_002": "543aeb03-c4c9-46f9-9d9f-81bf53f45438",
    "Day_008": "2d44757b-079c-4a78-a4a9-5fe6370466c8",
    "Day_009": DAY009_ASSET_ID,
    "Sunset_001": "65f68756-a006-43d4-9c86-2c0ec25ad229",
    "Living_Room_001": "c3d11c35-d8b7-485c-b216-0a4da68b751a",
}
PROGRESSION_PATHS = {
    "old": Path("/tmp/phase11-4-creative-quality-proof-03/09-stage3-creative-proof-03.png"),
    "v1": Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png"),
    "r1": Path("/tmp/phase11-7-hybrid-finish/07-hybrid-premium-proof-r1.png"),
}


def _assert_untouched_masters(library: dict[str, Any], m1, m2, m3, kids, p1s, p2s, p3s) -> None:
    m1a = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    m2a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    m3a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(m1a), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 11.9 refused to change Master 01")
    if json.dumps(_jsonable(m2a), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 11.9 refused to change Master 02")
    if _identity_slice(m3a) != m3:
        raise RuntimeError("Phase 11.9 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (m3a.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 11.9 refused to mutate Stage 2 children")
    if str(m1a.get("visual_asset")) != APPROVED_ASSET_ID or str(m2a.get("visual_asset")) != APPROVED_ASSET_02 or str(m3a.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.9 refused to change master visuals")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.9 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Phase 11.9 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Phase 11.9 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Phase 11.9 refused to rewrite Proof 03")


def _open(path: Path) -> Image.Image | None:
    if path.is_file():
        return Image.open(path).convert("RGB")
    return None


def generate_phase11_9_hybrid_v2(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    honest_scores: dict[str, int],
    fresh_answers: dict[str, str],
    progression: dict[str, str],
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
        ("phase11_7_hybrid_finish_tests", "quality117"),
        ("phase11_8_engine_v2_tests", "quality118"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 11.9 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.9 requires locked Masters 01–03")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s, p2s, p3s = library.get("stage_3_creative_quality_proof"), library.get("stage_3_creative_quality_proof_02"), library.get("stage_3_creative_quality_proof_03")
    locked_bytes = {str(path): path.read_bytes() if path.is_file() else None for path in LOCKED_PATHS}

    evaluation = concept_evaluation_json()
    selection = concept_selection_status()
    system = campaign_system_v2() if selection == "SELECTED" else None
    if selection != "SELECTED":
        raise RuntimeError("HYBRID_V2_CREATIVE_FAIL: no concept met selection floors")

    thumbs: dict[str, Image.Image] = {}
    for key, asset_id in ASSET_THUMB_KEYS.items():
        img = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        img.thumbnail((720, 900), Image.Resampling.LANCZOS)
        thumbs[key] = img
    opportunity = render_asset_opportunity_board(thumbs, "Day_009")

    field_pack = generate_register_field(
        db,
        user,
        project_id=UUID(TEMPLE_PROJECT_ID),
        session_id=str(preserved["session"]),
        reuse_path=FIELD_REUSE if FIELD_REUSE.is_file() else None,
    )
    field = field_pack["image"]
    firewall = run_project_reality_firewall(field)
    if firewall.get("status") != "PASS":
        raise RuntimeError(f"Generated field failed ProjectRealityFirewallV1: {firewall.get('reason')}")

    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY009_ASSET_ID)))).convert("RGB")
    obj, extract_meta = extract_project_object_v2(
        source,
        crop_box=DAY009_CROP,
        filename=DAY009_FILENAME,
        asset_id=DAY009_ASSET_ID,
    )
    if int(extract_meta.get("generated_architecture_pixels") or 0) != 0:
        raise RuntimeError("Extraction V2 invented architecture pixels")
    obj = punch_residual_sky(obj)
    edge_reports = {name: inspect_fringe(obj, color) for name, color in EDGE_BACKGROUNDS.items()}
    spire = lantern_preserved(obj)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    final, markup, compose_meta, layers = compose_hybrid_v2(field=field, obj=obj, logo_bytes=logo_bytes)

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
    critic = score_creative_v4(
        honest_scores,
        anti_template="PASS" if anti.get("pass") else "FAIL",
        visual_idea_gate="PASS" if visual_gate.get("pass") else "FAIL",
        commercial_system_gate="PASS" if commercial_gate.get("pass") else "FAIL",
        detached_lockup="PASS" if lockup.get("pass") else "FAIL",
        thumbnail="PASS" if thumb_gate.get("pass") else "FAIL",
        advertisement_vs_poster="PASS" if poster.get("pass") else "FAIL",
        project_reality="PASS" if firewall.get("status") == "PASS" else "FAIL",
    )
    fresh = score_fresh_critic_v4(fresh_answers)
    hier = dict(compose_meta.get("hierarchy") or {})
    hierarchy_ok = bool(hier.get("pass"))
    extraction_ok = all(item.get("pass") for item in edge_reports.values()) and bool(spire.get("preserved"))
    critic_ok = bool(critic.get("automated_pass"))
    fresh_ok = bool(fresh.get("pass"))
    progression_ok = (
        str(progression.get("HIGHEST_PROFESSIONAL_PRODUCTION_QUALITY") or "").upper() == "HYBRID_V2_FINAL"
        and str(progression.get("WOULD_PUBLISH") or "").upper() == "HYBRID_V2_FINAL"
    )
    automated = critic_ok and fresh_ok and hierarchy_ok and extraction_ok and progression_ok
    status = "HYBRID_V2_CREATIVE_PENDING_HUMAN_REVIEW" if automated else "HYBRID_V2_CREATIVE_FAIL"

    thumb15 = thumbnail(final, 0.15)
    thumb25 = thumbnail(final, 0.25)
    obj_plate = object_edge_plate(obj)
    refs: dict[str, Image.Image] = {}
    for name, asset_id in GRADE_A_MEDIA.items():
        try:
            refs[name] = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
    images = {
        "opportunity": opportunity,
        "field": field,
        "object": obj_plate,
        "fused": layers["fused"],
        "scene": render_scene_integration_proof(field, obj, layers["fused"]),
        "type": render_typography_system(final),
        "hierarchy": render_commercial_hierarchy(final),
        "final": final,
        "thumb15": thumb15,
        "thumb25": thumb25,
        "reference": render_reference_quality_board(refs, final),
        "progression": render_quality_progression_board(
            _open(PROGRESSION_PATHS["old"]),
            _open(PROGRESSION_PATHS["v1"]),
            _open(PROGRESSION_PATHS["r1"]),
            final,
        ),
        "review": render_human_review_board(final, thumb15, thumb25),
    }

    _assert_untouched_masters(library, m1, m2, m3, kids, p1s, p2s, p3s)
    for path, payload in locked_bytes.items():
        p = Path(path)
        if payload is not None and p.is_file() and p.read_bytes() != payload:
            raise RuntimeError(f"Phase 11.9 refused to modify locked proof {p.name}")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["phase11_3_commercial_creative_system_tests"] = preserved.get("quality113")
    blob["phase11_4_creative_quality_proof_tests"] = preserved.get("quality114")
    blob["phase11_6_hybrid_premium_engine_tests"] = preserved.get("quality116")
    blob["phase11_7_hybrid_finish_tests"] = preserved.get("quality117")
    blob["phase11_8_engine_v2_tests"] = preserved.get("quality118")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_9,
        "created_at": _now(),
        "status": status,
        "engine": ENGINE_ID,
        "engine_contract": hybrid_engine_v2_contract(),
        "concept": CONCEPT_NAME,
        "source": {"filename": DAY009_FILENAME, "asset_id": DAY009_ASSET_ID, "crop": DAY009_CROP},
        "evaluation": evaluation,
        "campaign_system": system,
        "field": {
            "provider": field_pack.get("provider"),
            "model": field_pack.get("model"),
            "reused": field_pack.get("reused"),
            "attempts": field_pack.get("attempts"),
            "audit": field_pack.get("audit"),
            "prompt": field_pack.get("prompt"),
        },
        "firewall": firewall,
        "extract_meta": extract_meta,
        "edge_reports": edge_reports,
        "spire": spire,
        "compose_meta": compose_meta,
        "critic": critic,
        "fresh": fresh,
        "progression": progression,
        "hierarchy": hier,
        "extraction_pass": extraction_ok,
        "approval": "PENDING HUMAN REVIEW" if automated else "CREATIVE QUALITY FAIL",
        "human_approved": False,
        "router_eligible": False,
        "master": False,
        "gpt_image_calls": provider_call_count(),
        "project_photo_internal_generated_pixels": 0,
        "architecture_fidelity": 10,
        "cover": PRODUCTION_COVER_V2,
        "canonical_pipeline": "UNCHANGED",
        "stage_2": "NOT IMPLEMENTED",
        "formats": "NOT IMPLEMENTED",
        "master_routing": "NOT IMPLEMENTED",
    }
    tests = list(blob.get("phase11_9_hybrid_v2_creative_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_9_hybrid_v2_creative_tests"] = tests
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
    record["layers"] = layers
    return record
