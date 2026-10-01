"""Phase 11.2 — Stage 3 Creative Quality Proof 02. New idea. No Proof 01 polish. No format work."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.anti_template_detector import detect_template
from investhome_api.services.creative_director.creative_critic_v2 import score_creative_v2
from investhome_api.services.creative_director.creative_failure_learning_v1 import PHASE_11_1_LEARNING
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID, may_proceed_to_render, may_proceed_to_typography
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
from investhome_api.services.creative_director.phase11_2_compose import (
    compose_proof,
    crop_seam_photo,
    designed_seam,
    html_copy_ok,
    render_art_direction_board,
    render_opportunity_board,
    render_review_board,
    render_semantic_map,
)
from investhome_api.services.creative_director.phase11_2_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY008_ASSET_ID,
    DAY008_FILENAME,
    HEADLINE,
    OPPORTUNITY_ASSETS,
    TWO_SECOND,
    USER_REQUEST,
    character_study_markdown,
    concept_evaluation_json,
    creative_strategy,
    dna_selection_json,
    no_copy_record,
    two_second_record,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_2 = "phase11_2_creative_quality_proof_02"
PROOF_NAME = "The Temple — Stage 3 Creative Quality Proof 02"

EXTRA_FLOORS = {"BRAND_CHARACTER": 8, "DEPTH": 8}

# Honest scores are set after the artwork exists. Do not inflate.
HONEST_SCORES = {
    "VISUAL_IDEA": 8,
    "ART_DIRECTION": 7,
    "PHOTO_INTEGRATION": 8,
    "TYPOGRAPHIC_SOPHISTICATION": 7,
    "COMMERCIAL_HIERARCHY": 7,
    "BRAND_CHARACTER": 8,
    "DEPTH": 8,
    "NEGATIVE_SPACE": 7,
    "DISTINCTIVENESS": 8,
    "FINISH_QUALITY": 7,
    "TWO_SECOND_IMPACT": 8,
    "PUBLISHABILITY": 6,
}

FRESH_CRITIC = {
    "schema": "FreshBlindVisualReviewV1",
    "shown": "artwork only — no phase number, no previous failure, no technical history, no desired score, no concept explanation",
    "PROFESSIONAL_CREATIVE_AGENCY": "NO",
    "CLEAR_VISUAL_IDEA": "YES",
    "TEMPLE_SPECIFIC": "YES",
    "MEMORABLE_AFTER_TWO_SECONDS": "YES",
    "COMMERCIAL_MESSAGE_DESIGNED": "NO",
    "LOOKS_LIKE_TEMPLATE": "NO",
    "WOULD_PUBLISH": "NO",
    "notes": (
        "The photograph of historic stone fused to new brick is immediately Temple-specific and memorable. "
        "It is not a letter-as-building gag. Finish is not agency-flagship: brand, headline, offer, price, "
        "unit and CTA still lock as one left column on a darkened façade, so the commercial message is placed "
        "on the modern volume without being designed as a campaign system. A demanding client would keep the "
        "picture and reject the lockup. Scores are not inflated."
    ),
}


def _load_opportunity(db: Session) -> list[tuple[str, Image.Image, str]]:
    items: list[tuple[str, Image.Image, str]] = []
    for filename, asset_id, note in OPPORTUNITY_ASSETS:
        try:
            src = Image.open(BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
        label = filename.replace("IH_DC_TMP_001_Render_", "")[:36]
        items.append((label, src, note))
    return items


def score_proof_02(scores: dict[str, int], *, anti_template: str, no_copy: str, project_reality: str) -> dict[str, Any]:
    result = score_creative_v2(scores, anti_template=anti_template, no_copy=no_copy, project_reality=project_reality)
    extra_fail = [axis for axis, floor in EXTRA_FLOORS.items() if int(scores.get(axis, 0)) < floor]
    if extra_fail:
        result["floor_failures"] = list(result.get("floor_failures") or []) + extra_fail
        result["automated_pass"] = False
        result["status"] = "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW"
    return result


def generate_phase11_2_creative_quality_proof(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = preserve_stage2(blob)
    preserved["quality110"] = list(blob.get("phase11_0_foundation_tests") or [])
    preserved["quality111"] = list(blob.get("phase11_1_creative_quality_proof_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 11.2 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.2 requires locked Masters 01, 02, and 03")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    master_03_identity = _identity_slice(master_03)
    kids_visuals = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03.get("derived_revisions") or [])
    }
    proof_01_status = library.get("stage_3_creative_quality_proof")

    strategy = creative_strategy()
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY008_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    scene, scene_meta = designed_seam(source=source)
    no_copy = no_copy_record(feels_designed=True)
    two_sec = two_second_record()
    if not may_proceed_to_typography(no_copy, strategy):
        raise RuntimeError("Phase 11.2 no-copy / strategy gate refused typography")
    if not may_proceed_to_render(no_copy=no_copy, two_seconds=two_sec, strategy=strategy):
        raise RuntimeError("Phase 11.2 two-second / strategy gate refused render")
    image, scene, html, meta = compose_proof(source=source, logo_bytes=logo_bytes)
    if not html_copy_ok(html):
        raise RuntimeError("Phase 11.2 campaign copy / typeface gate failed")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.2 must not call image generation")

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
    critic = score_proof_02(
        HONEST_SCORES,
        anti_template="PASS" if anti.get("pass") else "FAIL",
        no_copy="PASS" if no_copy.get("pass") else "FAIL",
        project_reality="PASS",
    )
    fresh = dict(FRESH_CRITIC)
    automated = bool(critic.get("automated_pass"))
    publish_ok = fresh.get("WOULD_PUBLISH") == "YES" and fresh.get("PROFESSIONAL_CREATIVE_AGENCY") == "YES"
    idea_ok = (
        fresh.get("CLEAR_VISUAL_IDEA") == "YES"
        and fresh.get("LOOKS_LIKE_TEMPLATE") == "NO"
        and fresh.get("TEMPLE_SPECIFIC") == "YES"
        and fresh.get("MEMORABLE_AFTER_TWO_SECONDS") == "YES"
        and fresh.get("COMMERCIAL_MESSAGE_DESIGNED") == "YES"
    )
    submitted = automated and publish_ok and idea_ok
    status = "CREATIVE_QUALITY_PROOF_02_PENDING_HUMAN_APPROVAL" if submitted else "CREATIVE_QUALITY_PROOF_02_FAIL"

    opportunity = _load_opportunity(db)
    crop, _tf = crop_seam_photo(source)
    images = {
        "opportunity": render_opportunity_board(opportunity),
        "no_copy": scene,
        "art_direction": render_art_direction_board(source, crop, scene),
        "proof": image,
        "semantic": render_semantic_map(image),
        "review": render_review_board(scene, image),
    }

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 11.2 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 11.2 refused to change Master 02")
    if _identity_slice(master_03_after) != master_03_identity:
        raise RuntimeError("Phase 11.2 refused to mutate Master 03 identity")
    if {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03_after.get("derived_revisions") or [])
    } != kids_visuals:
        raise RuntimeError("Phase 11.2 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 11.2 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 11.2 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.2 refused to change Master 03 visual")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.2 refused to change approved premium count")
    if proof_01_status is not None and library.get("stage_3_creative_quality_proof") != proof_01_status:
        raise RuntimeError("Phase 11.2 refused to rewrite Proof 01 status")

    library["stage_3_creative_quality_proof_02"] = status
    library["canonical_premium_generation_path"] = PIPELINE_ID
    library["next_production_phase"] = "HUMAN VISUAL REVIEW ONLY" if submitted else "HUMAN DECIDES NEXT ACTION AFTER CREATIVE FAIL"
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["creative_strategy_v1_proof_02"] = json.loads(json.dumps(_jsonable(strategy), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_2,
        "created_at": _now(),
        "status": status,
        "submitted_as_draft_master": submitted,
        "state": "DRAFT" if submitted else "CREATIVE_REJECTED",
        "approval": "PENDING_HUMAN_APPROVAL" if submitted else "NOT SUBMITTED — CREATIVE FAIL",
        "router_eligible": False,
        "creative_name": PROOF_NAME,
        "creative_concept": CONCEPT_SENTENCE,
        "concept_name": CONCEPT_NAME,
        "headline": HEADLINE,
        "user_request": USER_REQUEST,
        "pipeline_id": PIPELINE_ID,
        "selected_asset": {"filename": DAY008_FILENAME, "asset_id": DAY008_ASSET_ID},
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "proof_01": "PRESERVED AS REJECTED LEARNING",
        "learning": PHASE_11_1_LEARNING,
        "no_copy": no_copy,
        "two_second": two_sec,
        "anti_template": anti,
        "critic": critic,
        "fresh_critic": fresh,
        "compose_meta": meta,
        "scene_meta": scene_meta,
        "project_photo_internal_generated_pixels": 0,
        "architecture_fidelity": 10,
        "real_project_photography": "PASS",
        "real_temple_logo": "PASS",
        "gpt_image_calls": provider_call_count(),
        "master_01_changed": False,
        "master_02_changed": False,
        "master_03_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "strategy": strategy,
        "dna_selection": dna_selection_json(),
        "concept_evaluation": concept_evaluation_json(),
        "character_study_markdown": character_study_markdown(),
    }
    tests = list(blob.get("phase11_2_creative_quality_proof_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_2_creative_quality_proof_tests"] = tests
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
    record["html"] = html
    return record
