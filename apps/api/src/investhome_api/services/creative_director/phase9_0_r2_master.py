"""Phase 9.0-R2 — typographic completion of Premium Campaign 02. DRAFT. Not a new Master."""

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
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_compose import SUNSET_ASSET_ID, SUNSET_FILENAME
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r1_compose import CONCEPT, crop_sunset
from investhome_api.services.creative_director.phase9_0_r1_master import _HISTORY_KEYS as _H90R1
from investhome_api.services.creative_director.phase9_0_r1_master import _preserve as _preserve_90r1
from investhome_api.services.creative_director.phase9_0_r1_master import _restore_history as _restore_90r1
from investhome_api.services.creative_director.phase9_0_r2_compose import (
    PARENT_R1_ASSET,
    TYPE_PLAN,
    compose_master_02_r2,
    html_copy_ok,
    render_legibility,
    render_pair,
    render_type_plan,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_90_R2 = "phase9_0_r2_premium_master_02_editorial_completion"
_HISTORY_KEYS = _H90R1 + (("premium_master_90_r1_tests", "quality90r1"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_90r1(blob)
    preserved["quality90r1"] = list(blob.get("premium_master_90_r1_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_90r1(blob, preserved)
    blob["premium_master_90_r1_tests"] = preserved.get("quality90r1")


def generate_phase9_0_r2_premium_master_02(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    review: dict[str, str] | None = None,
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
        raise RuntimeError("Phase 9.0-R2 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01 is None:
        raise RuntimeError("Phase 9.0-R2 requires locked Premium Campaign 01")
    master_01_visual = master_01.get("visual_asset")
    master_01_status = master_01.get("approval_status")
    master_01_children = list(master_01.get("format_children") or [])

    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    if master_02 is None:
        raise RuntimeError("Phase 9.0-R2 requires existing Premium Campaign 02")
    r1_asset = str(master_02.get("visual_asset") or PARENT_R1_ASSET)
    if r1_asset != PARENT_R1_ASSET:
        raise RuntimeError("Phase 9.0-R2 expected the R1 visual as current Master 02")

    r1 = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_R1_ASSET)))).convert("RGB")
    sunset = Image.open(io.BytesIO(_read_bytes(db, UUID(SUNSET_ASSET_ID)))).convert("RGB")
    photo, transform = crop_sunset(sunset)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    image, scene, html = compose_master_02_r2(photo=photo, logo_bytes=logo_bytes)
    copy_ok = html_copy_ok(html)
    logo_once = html.count('data-semantic="project_logo"') <= 1

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(image),
        content_type="image/png",
        campaign_mode="project-premium-master-02-r2-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 9.0-R2 THE TEMPLE PREMIUM CAMPAIGN 02 EDITORIAL COMPLETION DRAFT",
    )
    asset_id = str(asset.id)
    if asset_id in {APPROVED_ASSET_ID, PARENT_R1_ASSET}:
        raise RuntimeError("R2 must not overwrite Master 01 or R1")

    history = list(master_02.get("visual_history") or [])
    history.append(
        {
            "asset_id": r1_asset,
            "human_review": "REJECTED",
            "reason": "creative concept approved; typography unfinished and compressed",
            "phase": "9.0-R1",
        }
    )
    master_02["visual_history"] = history
    master_02["visual_asset"] = asset_id
    master_02["approval_status"] = "DRAFT"
    master_02["router_eligible"] = False
    master_02["promoted"] = False
    master_02["version"] = int(master_02.get("version") or 1) + 1
    master_02["r2_typographic_plan"] = TYPE_PLAN
    master_02["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00012", "SUNSET", "R2"]

    master_01_after = next((item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01_after is None or str(master_01_after.get("visual_asset")) != str(master_01_visual):
        raise RuntimeError("Phase 9.0-R2 refused to change Master 01")
    if master_01_after.get("approval_status") != master_01_status:
        raise RuntimeError("Phase 9.0-R2 refused to change Master 01 approval")
    if list(master_01_after.get("format_children") or []) != master_01_children:
        raise RuntimeError("Phase 9.0-R2 refused to mutate the frozen 1:1 experiment")
    if count_approved_premium(library) != 1:
        raise RuntimeError("Phase 9.0-R2 must not approve a second Premium Master")
    if master_02["router_eligible"] is True:
        raise RuntimeError("Master 02 R2 must remain router ineligible")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    review_board = review or {
        "TYPOGRAPHIC_COLLISIONS": "PENDING",
        "EDITORIAL_FIELD_USED_INTENTIONALLY": "PENDING",
        "HEADLINE_HAS_AUTHORITY": "PENDING",
        "PCT35_HAS_COMMERCIAL_AUTHORITY": "PENDING",
        "PRICE_READABLE": "PENDING",
        "LOGO_BREATHES": "PENDING",
        "SPIRE_TYPE_RELATIONSHIP_INTENTIONAL": "PENDING",
        "CAMPAIGN_FEELS_FINISHED": "PENDING",
    }
    collisions = review_board.get("TYPOGRAPHIC_COLLISIONS") == "YES"
    reality = {
        "ARCHITECTURE_FIDELITY": 10,
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "REAL_TEMPLE_LOGO": "PASS" if logo_once else "FAIL",
        "FINANCIAL_COPY": "PASS" if copy_ok else "FAIL",
        "source_photo": SUNSET_FILENAME,
        "source_photo_asset_id": SUNSET_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "r1_kept": r1_asset,
    }
    status = "R2_FAIL" if collisions or not copy_ok else "PREMIUM_MASTER_02_R2_PENDING_HUMAN_APPROVAL"

    images = {
        "r1": r1,
        "plan": render_type_plan(scene),
        "r2": image,
        "pair": render_pair(r1, image, "R1  REJECTED TYPE", "R2  EDITORIAL COMPLETION  DRAFT", "04  R1 vs R2"),
        "legibility": render_legibility(image),
        "review": render_pair(r1, image, "R1  CONCEPT LOCKED  TYPE REJECTED", "R2  DRAFT", "06  HUMAN REVIEW BOARD"),
        "review_board": _text_board("HUMAN-STYLE FINAL REVIEW", [f"{k}  {v}" for k, v in review_board.items()]),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_90_R2,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_02,
        "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "asset_id": asset_id,
        "r1_asset_id": r1_asset,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "new_master_created": False,
        "creative_concept_changed": False,
        "typographic_plan": TYPE_PLAN,
        "human_style_review": review_board,
        "project_reality_validation": reality,
        "transform": transform,
        "gpt_image_calls": provider_call_count(),
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
        "concept": CONCEPT["concept_name"],
    }
    tests = list(blob.get("premium_master_90_r2_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["premium_master_90_r2_tests"] = tests
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
