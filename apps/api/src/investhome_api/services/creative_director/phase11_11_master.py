"""Phase 11.11 — reference-guided premium reconstruction proof.

Uses STAGE3_HYBRID_PREMIUM_ENGINE_V2 capabilities. Does not modify Hybrid V2.
Does not modify Masters, Proofs, cover, Stage 2, or the canonical pipeline.
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
from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA
from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID
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
from investhome_api.services.creative_director.phase11_11_audit import reference_similarity_audit
from investhome_api.services.creative_director.phase11_11_boards import (
    comparison_board,
    human_review_board,
    reconstruction_development,
    reference_selection_board,
    temple_asset_match_board,
)
from investhome_api.services.creative_director.phase11_11_compose import compose_reference_guided
from investhome_api.services.creative_director.phase11_11_field import generate_void_field
from investhome_api.services.creative_director.phase11_11_match import (
    DAY008_ASSET_ID,
    DAY008_CROP,
    DAY008_FILENAME,
    temple_asset_match,
)
from investhome_api.services.creative_director.phase11_11_select import SELECTED_FILENAME, reference_score_table
from investhome_api.services.creative_director.phase11_11_structure import (
    commercial_role_map,
    reference_design_structure,
    transferable_dna,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.project_object_extraction_v2 import extract_project_object_v2, spire_preserved
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_11 = "phase11_11_reference_guided_premium_proof"
FIELD_REUSE = Path("/tmp/phase11-11-reference-guided-proof/field.png")
HYBRID_V2 = Path("/tmp/phase11-9-hybrid-v2-creative-proof/09-hybrid-v2-final.png")
LOCKED_PATHS = (
    Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png"),
    Path("/tmp/phase11-7-hybrid-finish/07-hybrid-premium-proof-r1.png"),
    Path("/tmp/phase11-9-hybrid-v2-creative-proof/09-hybrid-v2-final.png"),
    Path("/tmp/phase11-10-ai-native-premium-proof/07-final-ai-native-master.png"),
)

REQUIRED_SCORE_FLOORS = {
    "ART_DIRECTION": 9,
    "PHOTO_INTEGRATION": 9,
    "TYPOGRAPHIC_SOPHISTICATION": 9,
    "COMMERCIAL_INTEGRATION": 9,
    "COMMERCIAL_HIERARCHY": 9,
    "FINISH_QUALITY": 9,
    "PERSUASIVE_POWER": 9,
    "PUBLISHABILITY": 9,
}

ASSET_THUMB_KEYS = {
    "Day_001": "5d26caf3-c237-4a78-9f3a-91f05dd24fa2",
    "Day_002": "543aeb03-c4c9-46f9-9d9f-81bf53f45438",
    "Day_008": DAY008_ASSET_ID,
    "Day_009": "7696df34-0544-44b9-89f5-0d1b2523c412",
    "Sunset_001": "65f68756-a006-43d4-9c86-2c0ec25ad229",
    "Living_Room_001": "c3d11c35-d8b7-485c-b216-0a4da68b751a",
}


def _assert_untouched(library: dict[str, Any], m1, m2, m3, kids, p1s, p2s, p3s) -> None:
    m1a = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    m2a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    m3a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(m1a), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 11.11 refused to change Master 01")
    if json.dumps(_jsonable(m2a), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 11.11 refused to change Master 02")
    if _identity_slice(m3a) != m3:
        raise RuntimeError("Phase 11.11 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (m3a.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 11.11 refused to mutate Stage 2 children")
    if str(m1a.get("visual_asset")) != APPROVED_ASSET_ID or str(m2a.get("visual_asset")) != APPROVED_ASSET_02 or str(m3a.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.11 refused to change master visuals")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.11 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Phase 11.11 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Phase 11.11 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Phase 11.11 refused to rewrite Proof 03")


def generate_phase11_11_reference_guided(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    honest_scores: dict[str, int],
    fresh_answers: dict[str, str],
    vs_hybrid: str,
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
        ("phase11_9_hybrid_v2_creative_tests", "quality119"),
        ("phase11_10_ai_native_tests", "quality1110"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 11.11 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.11 requires locked Masters 01–03")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s, p2s, p3s = library.get("stage_3_creative_quality_proof"), library.get("stage_3_creative_quality_proof_02"), library.get("stage_3_creative_quality_proof_03")
    locked_bytes = {str(path): path.read_bytes() if path.is_file() else None for path in LOCKED_PATHS}

    scores_table = reference_score_table()
    structure = reference_design_structure()
    dna = transferable_dna()
    match = temple_asset_match()
    roles = commercial_role_map()

    thumbs: dict[str, Image.Image] = {}
    for key, asset_id in ASSET_THUMB_KEYS.items():
        img = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        img.thumbnail((720, 900), Image.Resampling.LANCZOS)
        thumbs[key] = img

    refs: dict[str, Image.Image] = {}
    for name, asset_id in GRADE_A_MEDIA.items():
        try:
            refs[name] = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue

    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY008_ASSET_ID)))).convert("RGB")
    obj, extract_meta = extract_project_object_v2(
        source,
        crop_box=DAY008_CROP,
        filename=DAY008_FILENAME,
        asset_id=DAY008_ASSET_ID,
    )
    spire = spire_preserved(obj)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))

    field_pack = generate_void_field(
        db,
        user,
        project_id=UUID(TEMPLE_PROJECT_ID),
        session_id=str(preserved["session"]),
        reuse_path=FIELD_REUSE if FIELD_REUSE.is_file() else None,
    )
    FIELD_REUSE.parent.mkdir(parents=True, exist_ok=True)
    FIELD_REUSE.write_bytes(field_pack["bytes"])

    final, markup, meta, layers = compose_reference_guided(
        field=field_pack["image"],
        obj=obj,
        logo_bytes=logo_bytes,
    )

    sw, sh = source.size
    box = DAY008_CROP
    crop = source.crop(
        (
            int(sw * box["left"]),
            int(sh * box["top"]),
            int(sw * (box["left"] + box["width"])),
            int(sh * (box["top"] + box["height"])),
        )
    )

    similarity = reference_similarity_audit(
        reference=refs.get(SELECTED_FILENAME) or final,
        final=final,
        markup=markup,
    )

    generated_project_pixels = int(extract_meta.get("generated_architecture_pixels") or 0)
    # Fringe/halo is a finish defect. Invented architecture would be a reality fail.
    architecture_fidelity = 10 if generated_project_pixels == 0 else "FAIL"
    project_reality = bool(field_pack.get("passed")) and generated_project_pixels == 0
    floors = [axis for axis, floor in REQUIRED_SCORE_FLOORS.items() if int(honest_scores.get(axis) or 0) < floor]
    quality = not floors
    dna_pass = similarity.get("TRANSFERABLE_DNA") == "CLEAR" and similarity.get("SIGNATURE_ELEMENT_COPYING") == "NO"
    fresh = {
        "schema": "Phase1111FreshBlindReview",
        "shown": "final artwork only",
        "answers": {key: str(value).upper() for key, value in (fresh_answers or {}).items()},
    }
    hier = dict(meta.get("hierarchy") or {})
    test_15 = bool(hier.get("identity_15") and hier.get("hook_15") and hier.get("action_cue_15"))
    test_25 = bool(hier.get("price_25") and hier.get("unit_25") and hier.get("cta_25"))

    status = (
        "REFERENCE_GUIDED_PREMIUM_PENDING_HUMAN_REVIEW"
        if quality and project_reality and dna_pass
        else "REFERENCE_GUIDED_PREMIUM_FAIL"
    )
    approval = "PENDING HUMAN REVIEW" if status == "REFERENCE_GUIDED_PREMIUM_PENDING_HUMAN_REVIEW" else "CREATIVE QUALITY FAIL"

    hybrid = Image.open(HYBRID_V2).convert("RGB") if HYBRID_V2.is_file() else None
    thumb15 = final.resize((max(1, int(final.size[0] * 0.15)), max(1, int(final.size[1] * 0.15))), Image.Resampling.LANCZOS)
    thumb25 = final.resize((max(1, int(final.size[0] * 0.25)), max(1, int(final.size[1] * 0.25))), Image.Resampling.LANCZOS)
    images = {
        "selection": reference_selection_board(refs, SELECTED_FILENAME),
        "match": temple_asset_match_board(thumbs, "Day_008"),
        "development": reconstruction_development(
            refs.get(SELECTED_FILENAME),
            crop,
            obj,
            field_pack["image"],
            layers["fused"],
        ),
        "final": final,
        "thumb15": thumb15,
        "thumb25": thumb25,
        "comparison": comparison_board(refs.get(SELECTED_FILENAME), hybrid, final),
        "review": human_review_board(final, thumb15),
        "field": field_pack["image"],
        "object": obj,
        "crop": crop,
    }

    _assert_untouched(library, m1, m2, m3, kids, p1s, p2s, p3s)
    for path, payload in locked_bytes.items():
        p = Path(path)
        if payload is not None and p.is_file() and p.read_bytes() != payload:
            raise RuntimeError(f"Phase 11.11 refused to modify locked proof {p.name}")

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
    blob["phase11_9_hybrid_v2_creative_tests"] = preserved.get("quality119")
    blob["phase11_10_ai_native_tests"] = preserved.get("quality1110")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_11,
        "created_at": _now(),
        "status": status,
        "engine": ENGINE_ID,
        "scores_table": scores_table,
        "structure": structure,
        "dna": dna,
        "match": match,
        "roles": roles,
        "extract": extract_meta,
        "spire": spire,
        "field": {
            "passed": field_pack.get("passed"),
            "model": field_pack.get("model"),
            "attempts": field_pack.get("attempts"),
            "firewall": field_pack.get("firewall"),
        },
        "compose": {
            "optical": meta.get("optical"),
            "hierarchy": hier,
            "generated_architecture_pixels": meta.get("generated_architecture_pixels"),
        },
        "similarity": similarity,
        "critic_scores": honest_scores,
        "floor_failures": floors,
        "fresh": fresh,
        "vs_hybrid": vs_hybrid,
        "project_reality": "PASS" if project_reality else "FAIL",
        "architecture_fidelity": architecture_fidelity,
        "project_internal_generated_pixels": generated_project_pixels,
        "real_temple_logo": "PASS",
        "test_15": "PASS" if test_15 else "FAIL",
        "test_25": "PASS" if test_25 else "FAIL",
        "approval": approval,
        "router_eligible": False,
        "master": False,
        "canonical_pipeline": "UNCHANGED",
        "stage_2": "NOT IMPLEMENTED",
        "formats": "NOT IMPLEMENTED",
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
    }
    tests = list(blob.get("phase11_11_reference_guided_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_11_reference_guided_tests"] = tests
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
    record["markup"] = markup
    return record
