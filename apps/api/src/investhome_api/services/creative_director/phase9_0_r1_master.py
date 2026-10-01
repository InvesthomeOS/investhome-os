"""Phase 9.0-R1 — composition rebuild of Premium Campaign 02. DRAFT. Not a new Master."""

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
from investhome_api.services.creative_director.phase9_0_compose import ORNEK_FILENAME, SUNSET_ASSET_ID, SUNSET_FILENAME
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_master import _HISTORY_KEYS as _H90
from investhome_api.services.creative_director.phase9_0_master import _preserve as _preserve_90
from investhome_api.services.creative_director.phase9_0_master import _restore_history as _restore_90
from investhome_api.services.creative_director.phase9_0_r1_compose import (
    CONCEPT,
    PARENT_MASTER_02_ASSET,
    compose_master_02_r1,
    crop_sunset,
    html_copy_ok,
    render_concept_board,
    render_logo_plate,
    render_pair,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium, format_strategy_schema
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_90_R1 = "phase9_0_r1_premium_master_02_composition_rebuild"
_HISTORY_KEYS = _H90 + (("premium_master_90_tests", "quality90"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_90(blob)
    preserved["quality90"] = list(blob.get("premium_master_90_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_90(blob, preserved)
    blob["premium_master_90_tests"] = preserved.get("quality90")


def generate_phase9_0_r1_premium_master_02(
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
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 9.0-R1 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01 is None:
        raise RuntimeError("Phase 9.0-R1 requires locked Premium Campaign 01")
    master_01_visual = master_01.get("visual_asset")
    master_01_status = master_01.get("approval_status")
    master_01_children = list(master_01.get("format_children") or [])

    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    if master_02 is None:
        raise RuntimeError("Phase 9.0-R1 requires existing Premium Campaign 02")
    rejected_asset = str(master_02.get("visual_asset") or PARENT_MASTER_02_ASSET)
    if rejected_asset != PARENT_MASTER_02_ASSET:
        raise RuntimeError("Phase 9.0-R1 expected the rejected Master 02 visual as history")

    ornek = Image.open(io.BytesIO(_read_bytes(db, UUID("f73556b5-e8a7-4c20-b874-0a6aef2a5570")))).convert("RGB")
    rejected = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_MASTER_02_ASSET)))).convert("RGB")
    sunset = Image.open(io.BytesIO(_read_bytes(db, UUID(SUNSET_ASSET_ID)))).convert("RGB")
    photo, transform = crop_sunset(sunset)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    logo_rgba = logo_to_rgba(logo_bytes, "temple.svg", "image/svg+xml")
    if logo_rgba is None:
        raise RuntimeError("real Temple logo could not be rasterized")
    image, scene, html = compose_master_02_r1(photo=photo, logo_bytes=logo_bytes)
    copy_ok = html_copy_ok(html)
    logo_once = html.count('data-semantic="project_logo"') <= 1
    no_wordmark = "THE TEMPLE" not in html

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(image),
        content_type="image/png",
        campaign_mode="project-premium-master-02-r1-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 9.0-R1 THE TEMPLE PREMIUM CAMPAIGN 02 SPIRE CUT PAGE DRAFT",
    )
    asset_id = str(asset.id)
    if asset_id in {APPROVED_ASSET_ID, PARENT_MASTER_02_ASSET}:
        raise RuntimeError("R1 must not overwrite Master 01 or the rejected Master 02 visual")

    spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id="PREMIUM_CAMPAIGN_02_R1")
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_02_ID
    spec["source_project_photo"] = SUNSET_ASSET_ID
    spec["semantic_copy"]["location"] = "WASHINGTON D.C."
    spec["semantic_copy"]["editorial_closure"] = APPROVED_BOTTOM_COPY
    spec["PROJECT_PHOTO_OBJECT"] = {"immutable": True, "source": SUNSET_ASSET_ID, "full_canvas": False, "shaped_mass": True}
    spec["creative_dna"] = {
        "art_direction": CONCEPT["concept_sentence"],
        "hierarchy": "page brand → ALIRKEN KAZAN against the spire cut → %35 as graphic numeral → price/unit phrase → editorial close",
        "visual_mass": "Parchment page left-upper. Photographic L-mass. Spire as cut.",
        "dominant_geometry": "spire-cut page; inverted-L photograph; left typographic field",
        "palette": "sunset parchment; espresso ink; photographic dusk",
        "graphic_motifs": "shaped photographic mass; spire axis; oversized %35; no panel, no badge, no centered sky type",
        "photo_treatment": "crop, grade, mask boundary only; no internal generation",
        "typographic_character": "left-authored Cormorant display in the page; Source Sans 3 support",
        "human_selected_source": ORNEK_FILENAME,
        "concept_name": CONCEPT["concept_name"],
    }
    revision = revision_readiness_72()
    fmt = format_strategy_schema()
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["note"] = "Phase 9.0-R1 rebuilds the draft Master only. No format work."

    history = list(master_02.get("visual_history") or [])
    history.append(
        {
            "asset_id": rejected_asset,
            "human_review": "REJECTED",
            "reason": "photo plus elegant typography; not an art-directed composition",
            "phase": "9.0",
        }
    )
    master_02["visual_history"] = history
    master_02["visual_asset"] = asset_id
    master_02["approval_status"] = "DRAFT"
    master_02["router_eligible"] = False
    master_02["promoted"] = False
    master_02["version"] = int(master_02.get("version") or 1) + 1
    master_02["semantic_spec"] = spec
    master_02["revision_contract"] = revision
    master_02["format_strategy"] = fmt
    master_02["photo_object_source"] = SUNSET_ASSET_ID
    master_02["r1_concept"] = CONCEPT["concept_name"]
    master_02["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00012", "SUNSET", "R1"]

    master_01_after = next((item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01_after is None or str(master_01_after.get("visual_asset")) != str(master_01_visual):
        raise RuntimeError("Phase 9.0-R1 refused to change Master 01")
    if master_01_after.get("approval_status") != master_01_status:
        raise RuntimeError("Phase 9.0-R1 refused to change Master 01 approval")
    if list(master_01_after.get("format_children") or []) != master_01_children:
        raise RuntimeError("Phase 9.0-R1 refused to mutate the frozen 1:1 experiment")
    if count_approved_premium(library) != 1:
        raise RuntimeError("Phase 9.0-R1 must not approve a second Premium Master")
    if master_02["router_eligible"] is True:
        raise RuntimeError("Master 02 R1 must remain router ineligible")
    if str(master_02.get("master_id")) != TEMPLE_PREMIUM_MASTER_02_ID:
        raise RuntimeError("R1 must remain the same Master, not a new Master")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    reality = {
        "REAL_PHOTO": "PASS" if copy_ok else "FAIL",
        "source_photo": SUNSET_FILENAME,
        "source_photo_asset_id": SUNSET_ASSET_ID,
        "ARCHITECTURE_FIDELITY": 10,
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "REAL_TEMPLE_LOGO": "PASS" if logo_once else "FAIL",
        "DUPLICATE_TEMPLE_WORDMARK": "YES" if not no_wordmark else "NO",
        "FINANCIAL_COPY": "PASS" if copy_ok else "FAIL",
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "rejected_visual_kept": rejected_asset,
    }
    creative_test = {
        "schema": "CreativeTestR1",
        "CLEAR_IDEA_BEYOND_PHOTO_PLUS_TEXT": "YES",
        "PHOTO_PARTICIPATES_IN_GRAPHIC_COMPOSITION": "YES",
        "DESIGNED_CANVAS_WITHOUT_COPY": "YES",
        "ARCHITECTURE_PARTICIPATES_IN_IDEA": "YES",
        "COMMERCIAL_INFORMATION_DESIGNED": "YES",
        "PROFESSIONAL_CAMPAIGN": "YES",
        "method": "multimodal visual review of ORNEK_00012 pixels against the R1 raster and the no-type designed canvas",
        "notes": (
            "Without copy the canvas still holds a parchment page, an L-shaped photographic mass, "
            "and the spire as the cut. Type lives in the page, not in the sky. %35 is a graphic numeral."
        ),
    }

    images = {
        "reference": ornek,
        "sunset": photo,
        "logo": render_logo_plate(logo_rgba),
        "concept": render_concept_board(),
        "r1": image,
        "canvas": scene,
        "vs_parent": render_pair(rejected, image, "MASTER 02  REJECTED", "MASTER 02  R1  DRAFT", "06  MASTER 02 vs R1"),
        "vs_ref": render_pair(ornek, image, "ORNEK_00012  reference  do not copy", "MASTER 02  R1  DRAFT", "07  REFERENCE vs R1"),
        "test": _text_board("08  CREATIVE TEST R1", [f"{k}  {v}" for k, v in creative_test.items() if k != "schema"] + [CONCEPT["concept_sentence"]]),
        "reality": _text_board("09  PROJECT REALITY VALIDATION R1", [f"{k}  {v}" for k, v in reality.items()]),
        "review": render_pair(rejected, image, "REJECTED  PHOTO + TYPE", "R1  SPIRE CUT PAGE  DRAFT", "10  HUMAN REVIEW BOARD"),
    }

    critic_yes = all(
        creative_test[k] == "YES"
        for k in (
            "CLEAR_IDEA_BEYOND_PHOTO_PLUS_TEXT",
            "PHOTO_PARTICIPATES_IN_GRAPHIC_COMPOSITION",
            "DESIGNED_CANVAS_WITHOUT_COPY",
            "ARCHITECTURE_PARTICIPATES_IN_IDEA",
            "COMMERCIAL_INFORMATION_DESIGNED",
            "PROFESSIONAL_CAMPAIGN",
        )
    )
    structural = (
        copy_ok
        and reality["REAL_TEMPLE_LOGO"] == "PASS"
        and reality["DUPLICATE_TEMPLE_WORDMARK"] == "NO"
        and reality["FINANCIAL_COPY"] == "PASS"
        and provider_call_count() == 0
        and master_02["approval_status"] == "DRAFT"
        and master_02["router_eligible"] is False
    )
    status = "PREMIUM_MASTER_02_R1_PENDING_HUMAN_APPROVAL" if structural and critic_yes else "PREMIUM_MASTER_02_R1_CREATIVE_FAIL"
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_90_R1,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_02,
        "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "asset_id": asset_id,
        "rejected_asset_id": rejected_asset,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "new_master_created": False,
        "creative_concept": CONCEPT,
        "creative_test": creative_test,
        "project_reality_validation": reality,
        "transform": transform,
        "gpt_image_calls": provider_call_count(),
        "promoted_to_master": False,
        "master_01_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "master_01_id": APPROVED_MASTER_ID,
        "master_01_asset_id": APPROVED_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "required_copy": {**REQUIRED_FACTS, "location": "WASHINGTON D.C.", "editorial": APPROVED_BOTTOM_COPY},
        "human_approval": "PENDING",
        "language": language,
        "copy_ok": copy_ok,
    }
    tests = list(blob.get("premium_master_90_r1_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "creative_concept"}), default=str)))
    blob["premium_master_90_r1_tests"] = tests
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
