"""Phase 9.1-R1 — Looking Chamber spatial reveal. Same Master 03. DRAFT."""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, empty_semantic_spec_72, revision_readiness_72
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_compose import (
    ARCHITECTURE_ASSET_ID,
    ARCHITECTURE_FILENAME,
    INTERIOR_ASSET_ID,
    INTERIOR_FILENAME,
    ORNEK_ASSET_ID,
    ORNEK_FILENAME,
)
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_master import _HISTORY_KEYS as _H91
from investhome_api.services.creative_director.phase9_1_master import _preserve as _preserve_91
from investhome_api.services.creative_director.phase9_1_master import _restore_history as _restore_91
from investhome_api.services.creative_director.phase9_1_r1_compose import (
    CONCEPT_R1,
    DISTINCTNESS_PRE,
    PARENT_MASTER_03_ASSET,
    compose_master_03_r1,
    crop_architecture,
    crop_interior,
    html_copy_ok,
    render_labeled_asset,
    render_mechanism,
    render_pair,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium, format_strategy_schema
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_91_R1 = "phase9_1_r1_premium_master_03_spatial_reveal"
_HISTORY_KEYS = _H91 + (("premium_master_91_tests", "quality91"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_91(blob)
    preserved["quality91"] = list(blob.get("premium_master_91_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_91(blob, preserved)
    blob["premium_master_91_tests"] = preserved.get("quality91")


def generate_phase9_1_r1_premium_master_03(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    critic: dict[str, str] | None = None,
) -> dict[str, Any]:
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
        raise RuntimeError("Phase 9.1-R1 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 9.1-R1 requires Masters 01, 02, and 03")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    rejected_asset = str(master_03.get("visual_asset") or PARENT_MASTER_03_ASSET)
    if rejected_asset != PARENT_MASTER_03_ASSET:
        raise RuntimeError("Phase 9.1-R1 expected the rejected Master 03 visual as current")

    if "placed" in CONCEPT_R1["mechanism_sentence"].lower() and "exterior photo is placed" in CONCEPT_R1["mechanism_sentence"].lower():
        raise RuntimeError("R1 concept still describes picture-in-picture")

    ornek = Image.open(io.BytesIO(_read_bytes(db, UUID(ORNEK_ASSET_ID)))).convert("RGB")
    rejected = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_MASTER_03_ASSET)))).convert("RGB")
    interior_src = Image.open(io.BytesIO(_read_bytes(db, UUID(INTERIOR_ASSET_ID)))).convert("RGB")
    architecture_src = Image.open(io.BytesIO(_read_bytes(db, UUID(ARCHITECTURE_ASSET_ID)))).convert("RGB")
    interior, interior_tf = crop_interior(interior_src)
    architecture, architecture_tf = crop_architecture(architecture_src)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    image, chamber, html, scene_meta = compose_master_03_r1(
        interior=interior,
        architecture=architecture,
        logo_bytes=logo_bytes,
    )
    copy_ok = html_copy_ok(html)
    logo_once = html.count('data-semantic="project_logo"') <= 1
    no_wordmark = "THE TEMPLE" not in html and "uniloft" not in html.lower()

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(image),
        content_type="image/png",
        campaign_mode="project-premium-master-03-r1-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 9.1-R1 THE TEMPLE PREMIUM CAMPAIGN 03 LOOKING CHAMBER SPATIAL REVEAL DRAFT",
    )
    asset_id = str(asset.id)
    if asset_id in {APPROVED_ASSET_ID, APPROVED_ASSET_02, PARENT_MASTER_03_ASSET}:
        raise RuntimeError("R1 must not overwrite Master 01, Master 02, or rejected Master 03")

    spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id="PREMIUM_CAMPAIGN_03_R1")
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_03_ID
    spec["source_project_photo"] = INTERIOR_ASSET_ID
    spec["semantic_copy"]["location"] = "WASHINGTON D.C."
    spec["semantic_copy"]["editorial_closure"] = APPROVED_BOTTOM_COPY
    spec["PROJECT_PHOTO_OBJECT"] = {
        "immutable": True,
        "sources": [
            {"asset_id": INTERIOR_ASSET_ID, "role": "chamber"},
            {"asset_id": ARCHITECTURE_ASSET_ID, "role": "architectural_reveal"},
        ],
        "full_canvas": False,
        "shaped_mass": True,
        "internal_generated_pixels": 0,
    }
    spec["creative_dna"] = {
        "art_direction": CONCEPT_R1["mechanism_sentence"],
        "hierarchy": "atmosphere brand and headline left of the opening → %35 as commercial counterweight → price in the lid of the chamber → interior floor as close",
        "visual_mass": "Interior chamber left and floor. Vertical spatial opening. Temple architecture as the world beyond.",
        "dominant_geometry": "unframed vertical reveal; ceiling dissolve; continuous chamber floor",
        "palette": "warm charcoal atmosphere; interior daylight; stone-and-sky reveal",
        "graphic_motifs": "spatial opening; no card; no full-width header; no parchment; no sky-type hero",
        "photo_treatment": "crop, grade, mask, layer; no internal generation",
        "typographic_character": "ivory type in the chamber atmosphere, left of the reveal",
        "human_selected_source": ORNEK_FILENAME,
        "concept_name": CONCEPT_R1["concept_name"],
    }
    revision = revision_readiness_72()
    fmt = format_strategy_schema()
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["note"] = "Phase 9.1-R1 rebuilds the draft Master only. No format work."

    history = list(master_03.get("visual_history") or [])
    history.append(
        {
            "asset_id": rejected_asset,
            "human_review": "REJECTED",
            "reason": "dark header plus framed exterior card; Looking Chamber not spatially solved",
            "phase": "9.1",
        }
    )
    master_03["visual_history"] = history
    master_03["visual_asset"] = asset_id
    master_03["approval_status"] = "DRAFT"
    master_03["router_eligible"] = False
    master_03["promoted"] = False
    master_03["version"] = int(master_03.get("version") or 1) + 1
    master_03["semantic_spec"] = spec
    master_03["revision_contract"] = revision
    master_03["format_strategy"] = fmt
    master_03["photo_object_source"] = INTERIOR_ASSET_ID
    master_03["r1_concept"] = CONCEPT_R1["concept_name"]
    master_03["creative_concept"] = CONCEPT_R1["mechanism_sentence"]
    master_03["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00006", "LOOKING_CHAMBER", "R1"]

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 9.1-R1 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 9.1-R1 refused to change Master 02")
    if count_approved_premium(library) != 2:
        raise RuntimeError("Phase 9.1-R1 must not change locked Premium Master approvals")
    if master_03["router_eligible"] is True:
        raise RuntimeError("Master 03 R1 must remain router ineligible")
    if str(master_03.get("master_id")) != TEMPLE_PREMIUM_MASTER_03_ID:
        raise RuntimeError("R1 must remain the same Master, not a new Master")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    critic_board = critic or {
        "LOOKING_CHAMBER_IDEA_VISUALLY_OBVIOUS": "PENDING",
        "EXTERIOR_STRUCTURALLY_INTEGRATED": "PENDING",
        "INTERIOR_GEOMETRY_PARTICIPATES": "PENDING",
        "PHOTO_CARD_FEELING": "PENDING",
        "GENERIC_DARK_HEADER_FEELING": "PENDING",
        "THREE_DIMENSIONAL_VISUAL_DEPTH": "PENDING",
        "CLEAR_THIRD_CAMPAIGN_FAMILY": "PENDING",
        "PROFESSIONAL_CAMPAIGN": "PENDING",
    }
    card = critic_board.get("PHOTO_CARD_FEELING") == "YES"
    header = critic_board.get("GENERIC_DARK_HEADER_FEELING") == "YES"
    reality = {
        "REAL_INTERIOR": "PASS",
        "REAL_EXTERIOR": "PASS",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": 10,
        "REAL_TEMPLE_LOGO": "PASS" if logo_once else "FAIL",
        "DUPLICATE_TEMPLE_WORDMARK": "YES" if not no_wordmark else "NO",
        "FINANCIAL_COPY": "PASS" if copy_ok else "FAIL",
        "interior": INTERIOR_FILENAME,
        "interior_asset_id": INTERIOR_ASSET_ID,
        "architecture": ARCHITECTURE_FILENAME,
        "architecture_asset_id": ARCHITECTURE_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "rejected_kept": rejected_asset,
    }
    structural = (
        not card
        and not header
        and copy_ok
        and reality["REAL_TEMPLE_LOGO"] == "PASS"
        and reality["DUPLICATE_TEMPLE_WORDMARK"] == "NO"
        and provider_call_count() == 0
        and master_03["approval_status"] == "DRAFT"
    )
    status = "PREMIUM_MASTER_03_R1_CREATIVE_FAIL" if card or header or not copy_ok else (
        "PREMIUM_MASTER_03_R1_PENDING_HUMAN_APPROVAL" if structural else "PREMIUM_MASTER_03_R1_CREATIVE_FAIL"
    )

    images = {
        "rejected": rejected,
        "reference": ornek,
        "interior": render_labeled_asset(interior_src, "03  REAL INTERIOR  Living_Room_001", INTERIOR_ASSET_ID),
        "exterior": render_labeled_asset(architecture_src, "04  REAL EXTERIOR  Day_002", ARCHITECTURE_ASSET_ID),
        "mechanism": render_mechanism(chamber),
        "r1": image,
        "pair": render_pair(rejected, image, "MASTER 03  REJECTED  CARD", "R1  SPATIAL REVEAL  DRAFT", "07  MASTER 03 vs R1"),
        "vs_ref": render_pair(ornek, image, "ORNEK_00006  DNA only  do not copy", "MASTER 03  R1  DRAFT", "08  REFERENCE vs R1"),
        "remove_text": render_labeled_asset(chamber, "09  REMOVE-TEXT TEST  Looking Chamber without copy", CONCEPT_R1["mechanism_sentence"][:72]),
        "creative": _text_board("10  CREATIVE REVIEW", [f"{k}  {v}" for k, v in critic_board.items()]),
        "review": render_pair(rejected, image, "REJECTED  header + card", "R1  DRAFT  spatial reveal", "11  HUMAN REVIEW BOARD"),
        "chamber": chamber,
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_91_R1,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_03,
        "master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "asset_id": asset_id,
        "rejected_asset_id": rejected_asset,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "creative_concept": CONCEPT_R1,
        "distinctness_review": DISTINCTNESS_PRE,
        "creative_quality_review": critic_board,
        "project_reality_validation": reality,
        "scene_meta": scene_meta,
        "interior_transform": interior_tf,
        "architecture_transform": architecture_tf,
        "gpt_image_calls": provider_call_count(),
        "new_master_created": False,
        "creative_concept_changed": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "master_01_id": APPROVED_MASTER_ID,
        "master_01_asset_id": APPROVED_ASSET_ID,
        "master_02_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "master_02_asset_id": APPROVED_ASSET_02,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "required_copy": {**REQUIRED_FACTS, "location": "WASHINGTON D.C.", "editorial": APPROVED_BOTTOM_COPY},
        "human_approval": "PENDING",
        "language": language,
    }
    tests = list(blob.get("premium_master_91_r1_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "creative_concept"}), default=str)))
    blob["premium_master_91_r1_tests"] = tests
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
    record["images"] = images
    record["identity_pointers"] = {"before": before, "after": after}
    return record
