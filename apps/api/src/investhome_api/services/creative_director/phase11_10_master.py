"""Phase 11.10 — AI-native premium master feasibility proof.

Does not modify Hybrid V1/V2, Proofs, Masters, cover, Stage 2, or the canonical pipeline.
Does not implement Stage 2, formats, or semantic revision maps.
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
from investhome_api.services.creative_director.fresh_critic_v4 import score_fresh_critic_v4
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
from investhome_api.services.creative_director.phase11_10_boards import (
    commercial_detail_board,
    grade_a_comparison_board,
    human_review_board,
    source_selection_board,
)
from investhome_api.services.creative_director.phase11_10_fidelity import architecture_fidelity_audit_v2, architecture_fidelity_board
from investhome_api.services.creative_director.phase11_10_generate import generate_ai_native_master
from investhome_api.services.creative_director.phase11_10_provider import provider_capability_audit
from investhome_api.services.creative_director.phase11_10_source import fit_source_4x5, mask_preview, source_pack
from investhome_api.services.creative_director.phase11_10_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY001_ASSET_ID,
    DAY001_CENTERING,
    DAY001_FILENAME,
    concept_evaluation_json,
)
from investhome_api.services.creative_director.phase11_10_text import apply_factual_text_repair, validate_campaign_text
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_10 = "phase11_10_ai_native_premium_feasibility"
RAW_REUSE = Path("/tmp/phase11-10-ai-native-premium-proof/05-raw-ai-master.png")
HYBRID_V2 = Path("/tmp/phase11-9-hybrid-v2-creative-proof/09-hybrid-v2-final.png")
LOCKED_PATHS = (
    Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png"),
    Path("/tmp/phase11-7-hybrid-finish/07-hybrid-premium-proof-r1.png"),
    Path("/tmp/phase11-9-hybrid-v2-creative-proof/09-hybrid-v2-final.png"),
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


def _assert_untouched(library, m1, m2, m3, kids, p1s, p2s, p3s) -> None:
    m1a = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    m2a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    m3a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(m1a), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 11.10 refused to change Master 01")
    if json.dumps(_jsonable(m2a), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 11.10 refused to change Master 02")
    if _identity_slice(m3a) != m3:
        raise RuntimeError("Phase 11.10 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (m3a.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 11.10 refused to mutate Stage 2 children")
    if str(m1a.get("visual_asset")) != APPROVED_ASSET_ID or str(m2a.get("visual_asset")) != APPROVED_ASSET_02 or str(m3a.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.10 refused to change master visuals")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.10 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Phase 11.10 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Phase 11.10 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Phase 11.10 refused to rewrite Proof 03")


def generate_phase11_10_ai_native(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    honest_scores: dict[str, int],
    fresh_answers: dict[str, str],
    vs_hybrid: str,
    experiment_class: str | None = None,
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
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 11.10 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.10 requires locked Masters 01–03")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s, p2s, p3s = library.get("stage_3_creative_quality_proof"), library.get("stage_3_creative_quality_proof_02"), library.get("stage_3_creative_quality_proof_03")
    locked_bytes = {str(path): path.read_bytes() if path.is_file() else None for path in LOCKED_PATHS}

    audit = provider_capability_audit()
    evaluation = concept_evaluation_json()
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY001_ASSET_ID)))).convert("RGB")
    fitted = fit_source_4x5(source, centering=DAY001_CENTERING)
    pack = source_pack(fitted)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))

    reused = False
    if RAW_REUSE.is_file():
        raw_image = Image.open(RAW_REUSE).convert("RGB")
        if raw_image.size != fitted.size:
            raw_image = raw_image.resize(fitted.size, Image.Resampling.LANCZOS)
        gen = {
            "image": raw_image,
            "asset_id": None,
            "provider": "gpt-image",
            "model": "reused",
            "quality": "high",
            "prompt": None,
            "method": "reused_raw_ai_master",
        }
        reused = True
    else:
        gen = generate_ai_native_master(
            db,
            user,
            project_id=UUID(TEMPLE_PROJECT_ID),
            session_id=str(preserved["session"]),
            source_png=pack["source_bytes"],
            mask_png=pack["mask_bytes"],
            logo_bytes=logo_bytes,
        )
    raw = gen["image"]
    text = validate_campaign_text(raw)
    final, repair = apply_factual_text_repair(raw, text)
    fidelity = architecture_fidelity_audit_v2(fitted, final)
    reality = bool(fidelity.get("pass"))
    floors = [axis for axis, floor in REQUIRED_SCORE_FLOORS.items() if int(honest_scores.get(axis, 0)) < floor]
    fresh = score_fresh_critic_v4(fresh_answers)
    quality = not floors and bool(fresh.get("pass"))
    if experiment_class is None:
        if quality and reality:
            experiment_class = "A"
        elif quality and not reality:
            experiment_class = "B"
        elif (not quality) and reality:
            experiment_class = "C"
        else:
            experiment_class = "D"
    status = "AI_NATIVE_PREMIUM_PENDING_HUMAN_REVIEW" if (quality and reality) else "AI_NATIVE_PREMIUM_FAIL"

    refs: dict[str, Image.Image] = {}
    for name, asset_id in GRADE_A_MEDIA.items():
        try:
            refs[name] = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
    hybrid = Image.open(HYBRID_V2).convert("RGB") if HYBRID_V2.is_file() else None
    thumb = final.resize((max(1, int(final.size[0] * 0.15)), max(1, int(final.size[1] * 0.15))), Image.Resampling.LANCZOS)
    images = {
        "source_board": source_selection_board(fitted, mask_preview(fitted, pack["protected"]), DAY001_FILENAME),
        "fitted": fitted,
        "mask": pack["protected"],
        "raw": raw,
        "final": final,
        "fidelity": architecture_fidelity_board(fitted, final, fidelity),
        "commercial": commercial_detail_board(final),
        "thumb": thumb,
        "comparison": grade_a_comparison_board(refs, hybrid, final),
        "review": human_review_board(final, thumb),
    }

    _assert_untouched(library, m1, m2, m3, kids, p1s, p2s, p3s)
    for path, payload in locked_bytes.items():
        p = Path(path)
        if payload is not None and p.is_file() and p.read_bytes() != payload:
            raise RuntimeError(f"Phase 11.10 refused to modify locked proof {p.name}")

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
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_10,
        "created_at": _now(),
        "status": status,
        "provider_audit": audit,
        "evaluation": evaluation,
        "concept": CONCEPT_NAME,
        "big_idea": CONCEPT_SENTENCE,
        "source": {"filename": DAY001_FILENAME, "asset_id": DAY001_ASSET_ID},
        "method": gen.get("method"),
        "reused_raw": reused,
        "gen": {"asset_id": gen.get("asset_id"), "model": gen.get("model"), "quality": gen.get("quality")},
        "text": text,
        "repair": repair,
        "fidelity": fidelity,
        "critic_scores": honest_scores,
        "floor_failures": floors,
        "fresh": fresh,
        "vs_hybrid": vs_hybrid,
        "experiment_class": experiment_class,
        "approval": "PENDING HUMAN REVIEW" if status == "AI_NATIVE_PREMIUM_PENDING_HUMAN_REVIEW" else "FEASIBILITY FAIL",
        "router_eligible": False,
        "canonical_pipeline": "UNCHANGED",
        "stage_2": "NOT IMPLEMENTED",
        "formats": "NOT IMPLEMENTED",
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
    }
    tests = list(blob.get("phase11_10_ai_native_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_10_ai_native_tests"] = tests
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
    return record
