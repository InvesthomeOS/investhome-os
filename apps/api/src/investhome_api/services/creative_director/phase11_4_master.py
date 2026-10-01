"""Phase 11.4 — Stage 3 Creative Quality Proof 03. Integrated campaign. Honest fail allowed. No R1. No format work."""

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
from investhome_api.services.creative_director.commercial_system_gate import (
    advertisement_vs_poster_test,
    commercial_system_gate,
    thumbnail_test,
)
from investhome_api.services.creative_director.creative_critic_v3 import score_creative_v3
from investhome_api.services.creative_director.detached_commercial_lockup_detector import detect_detached_commercial_lockup
from investhome_api.services.creative_director.fresh_critic_v3 import score_fresh_critic_v3
from investhome_api.services.creative_director.integrated_campaign_pipeline import INTEGRATED_PIPELINE_ID
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
from investhome_api.services.creative_director.phase11_4_compose import (
    compose_proof,
    crop_threshold_photo,
    designed_threshold,
    html_copy_ok,
    render_art_direction_board,
    render_commercial_system_board,
    render_opportunity_board,
    render_review_board,
    render_semantic_map,
    render_thumbnail_board,
)
from investhome_api.services.creative_director.phase11_4_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY009_ASSET_ID,
    DAY009_FILENAME,
    HEADLINE,
    HIERARCHY,
    OPPORTUNITY_ASSETS,
    USER_REQUEST,
    campaign_skeleton,
    concept_evaluation_json,
    concept_passes_render_floors,
    creative_strategy,
    dna_selection_json,
    integrated_concept_record,
    numeric_direction,
    reading_path,
    selected_concept,
    visual_idea_record,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.stage3_failure_learning_v2 import stage3_failure_learning_v2
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_4 = "phase11_4_creative_quality_proof_03"
PROOF_NAME = "The Temple — Stage 3 Creative Quality Proof 03"

# Honest scores from the rendered candidate. Do not inflate.
HONEST_SCORES = {
    "VISUAL_IDEA": 8,
    "ART_DIRECTION": 7,
    "PHOTO_INTEGRATION": 8,
    "TYPOGRAPHIC_SOPHISTICATION": 7,
    "COMMERCIAL_INTEGRATION": 7,
    "COMMERCIAL_HIERARCHY": 7,
    "READING_PATH": 7,
    "BRAND_CHARACTER": 8,
    "DEPTH": 8,
    "NEGATIVE_SPACE": 7,
    "DISTINCTIVENESS": 8,
    "FINISH_QUALITY": 7,
    "TWO_SECOND_IMPACT": 8,
    "PERSUASIVE_POWER": 6,
    "PUBLISHABILITY": 6,
}

FRESH_ANSWERS = {
    "PROFESSIONAL_CREATIVE_AGENCY": "NO",
    "CLEAR_VISUAL_IDEA": "YES",
    "PROJECT_SPECIFIC": "YES",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "NO",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "YES",
    "CLEAR_READING_PATH": "NO",
    "PERSUASIVE": "NO",
    "MEMORABLE_AFTER_TWO_SECONDS": "YES",
    "LOOKS_LIKE_TEMPLATE": "NO",
    "WOULD_PUBLISH": "NO",
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


def generate_phase11_4_creative_quality_proof(
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
    preserved["quality112"] = list(blob.get("phase11_2_creative_quality_proof_tests") or [])
    preserved["quality113"] = list(blob.get("phase11_3_commercial_creative_system_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 11.4 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.4 requires locked Masters 01, 02, and 03")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    master_03_identity = _identity_slice(master_03)
    kids_visuals = {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03.get("derived_revisions") or [])
    }
    proof_01_status = library.get("stage_3_creative_quality_proof")
    proof_02_status = library.get("stage_3_creative_quality_proof_02")

    evaluation = concept_evaluation_json()
    chosen = selected_concept()
    if "Day_009" not in str(chosen.get("project_photo_role")):
        raise RuntimeError("Phase 11.4 refused to auto-reuse Day_008")
    if not concept_passes_render_floors(chosen):
        raise RuntimeError("Phase 11.4 concept failed render floors — stop without rendering")

    strategy = creative_strategy()
    concept = integrated_concept_record()
    skeleton = campaign_skeleton()
    path = reading_path()
    visual_gate = visual_idea_record(feels_designed=True)
    commercial_gate = commercial_system_gate(
        composition_stronger_with_copy=False,
        elements_have_intentional_relationships=True,
        occupies_leftover_space_only=True,
    )
    lockup = detect_detached_commercial_lockup(
        lockup_is_independent_vertical_stack=False,
        would_work_on_another_photo_unchanged=False,
    )
    thumb_gate = thumbnail_test(
        one_clear_visual_event=True,
        one_clear_message=False,
        one_clear_commercial_hook=False,
    )
    poster = advertisement_vs_poster_test("POSTER + SALES INFORMATION")

    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY009_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    scene, scene_meta = designed_threshold(source=source)
    image, scene, html, meta = compose_proof(source=source, logo_bytes=logo_bytes)
    if not html_copy_ok(html):
        raise RuntimeError("Phase 11.4 campaign copy / typeface gate failed")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.4 must not call image generation")

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
        HONEST_SCORES,
        anti_template="PASS" if anti.get("pass") else "FAIL",
        visual_idea_gate="PASS" if visual_gate.get("pass") else "FAIL",
        commercial_system_gate="PASS" if commercial_gate.get("pass") else "FAIL",
        detached_lockup="PASS" if lockup.get("pass") else "FAIL",
        thumbnail="PASS" if thumb_gate.get("pass") else "FAIL",
        advertisement_vs_poster="PASS" if poster.get("pass") else "FAIL",
        project_reality="PASS",
    )
    fresh = score_fresh_critic_v3(FRESH_ANSWERS)
    fresh["advertisement_vs_poster"] = poster
    fresh["notes"] = (
        "Day_009 doorway crop is immediately Temple-specific and memorable. It is not Proof 01's letter "
        "and not Proof 02's left column. Brand, headline, offer, price, unit and CTA are spatially split, "
        "but they still sit on the photograph as overlaid sales information — cornice wash plus portal type "
        "plus corner footers. The artwork does not become a designed advertisement. Scores are not inflated."
    )
    automated = bool(critic.get("automated_pass"))
    publish_ok = fresh.get("pass") is True
    submitted = automated and publish_ok
    status = "CREATIVE_QUALITY_PROOF_03_PENDING_HUMAN_APPROVAL" if submitted else "CREATIVE_QUALITY_PROOF_03_FAIL"

    opportunity = _load_opportunity(db)
    crop, _tf = crop_threshold_photo(source)
    images = {
        "opportunity": render_opportunity_board(opportunity),
        "no_copy": scene,
        "commercial_system": render_commercial_system_board(scene, image),
        "art_direction": render_art_direction_board(source, crop, scene),
        "proof": image,
        "thumbnail": render_thumbnail_board(image),
        "semantic": render_semantic_map(image),
        "review": render_review_board(scene, image),
    }

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 11.4 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 11.4 refused to change Master 02")
    if _identity_slice(master_03_after) != master_03_identity:
        raise RuntimeError("Phase 11.4 refused to mutate Master 03 identity")
    if {
        str(item.get("revision_id")): str(item.get("visual_asset"))
        for item in (master_03_after.get("derived_revisions") or [])
    } != kids_visuals:
        raise RuntimeError("Phase 11.4 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 11.4 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 11.4 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.4 refused to change Master 03 visual")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.4 refused to change approved premium count")
    if proof_01_status is not None and library.get("stage_3_creative_quality_proof") != proof_01_status:
        raise RuntimeError("Phase 11.4 refused to rewrite Proof 01 status")
    if proof_02_status is not None and library.get("stage_3_creative_quality_proof_02") != proof_02_status:
        raise RuntimeError("Phase 11.4 refused to rewrite Proof 02 status")

    library["stage_3_creative_quality_proof_03"] = status
    library["canonical_premium_generation_path"] = INTEGRATED_PIPELINE_ID
    library["next_production_phase"] = "HUMAN VISUAL REVIEW ONLY" if submitted else "HUMAN DECIDES NEXT ACTION AFTER CREATIVE FAIL"
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["creative_strategy_v1_proof_03"] = json.loads(json.dumps(_jsonable(strategy), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["phase11_3_commercial_creative_system_tests"] = preserved.get("quality113")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_4,
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
        "hierarchy": HIERARCHY,
        "user_request": USER_REQUEST,
        "pipeline_id": INTEGRATED_PIPELINE_ID,
        "selected_asset": {"filename": DAY009_FILENAME, "asset_id": DAY009_ASSET_ID},
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "proof_01": "PRESERVED / REJECTED",
        "proof_02": "PRESERVED / REJECTED",
        "learning": stage3_failure_learning_v2(),
        "visual_idea_gate": visual_gate,
        "commercial_system_gate": commercial_gate,
        "detached_lockup": lockup,
        "thumbnail_test": thumb_gate,
        "advertisement_vs_poster": poster,
        "anti_template": anti,
        "critic": critic,
        "fresh_critic": fresh,
        "compose_meta": meta,
        "scene_meta": scene_meta,
        "numeric_art_direction": numeric_direction(),
        "campaign_skeleton": skeleton,
        "reading_path": path,
        "integrated_concept": concept,
        "project_photo_internal_generated_pixels": 0,
        "architecture_fidelity": 10,
        "real_project_photography": "PASS",
        "real_temple_logo": "PASS",
        "stage_2_revision_compatibility": "PASS" if submitted else "NOT TESTED DUE TO CREATIVE FAIL",
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
        "concept_evaluation": evaluation,
        "exact_failure": None if submitted else (
            "THE_THRESHOLD is a Temple-specific architectural idea and it is not a left information column, "
            "but commercial type still overlays the photograph (cornice wash, portal numeral, corner footers) "
            "instead of becoming one designed advertisement. Commercial system gate FAIL. "
            "Advertisement vs poster: POSTER + SALES INFORMATION. Publishability 6."
        ),
    }
    tests = list(blob.get("phase11_4_creative_quality_proof_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_4_creative_quality_proof_tests"] = tests
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
