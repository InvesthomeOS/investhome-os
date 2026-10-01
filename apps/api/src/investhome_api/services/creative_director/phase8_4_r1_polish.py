"""Phase 8.4-R1 — spatial polish of the 1:1 format child. CTA + editorial only."""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board, render_three_way
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
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
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_2_r1_compose import DAY003_ASSET_ID, DAY003_FILENAME
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID, APPROVED_MASTER_NAME
from investhome_api.services.creative_director.phase8_4_adapt import FORMAT_CHILD_1X1_ID
from investhome_api.services.creative_director.phase8_4_adapt import _HISTORY_KEYS as _H84
from investhome_api.services.creative_director.phase8_4_adapt import _preserve as _preserve_84
from investhome_api.services.creative_director.phase8_4_adapt import _restore_history as _restore_84
from investhome_api.services.creative_director.phase8_4_format_1x1 import CANVAS_1X1, crop_day003_1x1, render_format_pair, revision_readiness_1x1
from investhome_api.services.creative_director.phase8_4_r1_compose import (
    PARENT_CHILD_ASSET_84,
    PARENT_CHILD_ID_84,
    only_cta_editorial_changed,
    overlay_spatial_polish,
    parent_plan,
    preservation_validation,
    r1_identity,
    r1_plan,
    render_preservation_board,
    render_review_board,
    render_r1_type,
    render_spatial_board,
)
from investhome_api.services.creative_director.project_creative_master_library import attach_format_child, count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_84_R1 = "phase8_4_r1_format_child_spatial_polish"
FORMAT_CHILD_1X1_R1_ID = str(uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-01:format:1x1:r1"))
_HISTORY_KEYS = _H84 + (("format_adaptation_84_1x1_tests", "quality84"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_84(blob)
    preserved["quality84"] = list(blob.get("format_adaptation_84_1x1_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_84(blob, preserved)
    blob["format_adaptation_84_1x1_tests"] = preserved.get("quality84")


def generate_phase8_4_r1_format_child_spatial_polish(
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
        raise RuntimeError("Phase 8.4-R1 requires ProjectCreativeMasterLibraryV1")
    master = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master is None:
        raise RuntimeError("Phase 8.4-R1 requires locked Premium Campaign 01")
    if master.get("approval_status") != "HUMAN_APPROVED" or str(master.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 8.4-R1 refused to touch an unlocked or mutated canonical Master")
    children = list(master.get("format_children") or [])
    parent_child = next((c for c in children if str(c.get("child_id")) == PARENT_CHILD_ID_84 or str(c.get("target_format")) == "1:1"), None)
    if parent_child is None:
        raise RuntimeError("Phase 8.4-R1 requires the parent 1:1 format child")
    parent_asset = str(parent_child.get("visual_asset") or PARENT_CHILD_ASSET_84)
    if parent_asset != PARENT_CHILD_ASSET_84:
        raise RuntimeError("Phase 8.4-R1 expected the approved 1:1 parent asset")
    canonical_visual_before = master.get("visual_asset")
    eligible_before = master.get("router_eligible")

    canonical = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_ID)))).convert("RGB")
    parent = Image.open(io.BytesIO(_read_bytes(db, UUID(parent_asset)))).convert("RGB")
    if parent.size != CANVAS_1X1:
        raise RuntimeError("parent 1:1 is not 1088x1088")
    day003 = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    photo, transform = crop_day003_1x1(day003)
    old = parent_plan()
    plan = r1_plan()
    if not only_cta_editorial_changed(old, plan):
        raise RuntimeError("Phase 8.4-R1 may only change CTA and editorial territories")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    rendered, html = render_r1_type(photo=photo, logo_bytes=logo_bytes, plan=plan)
    r1_image = overlay_spatial_polish(parent, rendered, old_plan=old, new_plan=plan)
    validation = preservation_validation(parent, r1_image, old_plan=old, new_plan=plan)
    identity = r1_identity(html=html, square=r1_image, canonical=canonical, plan=plan, preservation=validation)
    revision = revision_readiness_1x1(parent_master_id=APPROVED_MASTER_ID, child_id=FORMAT_CHILD_1X1_R1_ID)

    scores = identity.get("scores") or {}
    score_ok = (
        int(scores.get("CAMPAIGN_IDENTITY") or 0) >= 9
        and int(scores.get("PHOTO_IDENTITY") or 0) >= 9
        and int(scores.get("HEADLINE_IDENTITY") or 0) >= 9
        and int(scores.get("COMMERCIAL_HIERARCHY") or 0) >= 8
        and int(scores.get("TYPOGRAPHIC_CHARACTER") or 0) >= 8
        and int(scores.get("BRAND_RELATIONSHIP") or 0) >= 9
        and int(scores.get("NEGATIVE_SPACE_LOGIC") or 0) >= 9
        and int(scores.get("WHOLE_CANVAS_FAMILY_RESEMBLANCE") or 0) >= 9
    )
    visual_ok = (
        identity.get("CTA_CLEAR") == "YES"
        and identity.get("EDITORIAL_CLOSURE_CLEAR") == "YES"
        and identity.get("LEFT_CAMPAIGN_COLUMN_COHESIVE") == "YES"
        and identity.get("TEXT_ON_BUSY_ARCHITECTURE") == "NO"
    )
    preserve_ok = validation.get("VISUAL_DELTA_OUTSIDE_CTA_EDITORIAL") == "PASS" and validation.get("ARCHITECTURE_FIDELITY") == 10
    gpt_ok = provider_call_count() == 0
    structural = score_ok and visual_ok and preserve_ok and gpt_ok
    status = "FORMAT_ADAPTATION_FINAL_PENDING_HUMAN_APPROVAL" if structural else "FORMAT_ADAPTATION_NOT_READY"

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(r1_image),
        content_type="image/png",
        campaign_mode="project-premium-format-child-1x1-r1",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 8.4-R1 THE TEMPLE PREMIUM CAMPAIGN 01 FORMAT CHILD 1:1 SPATIAL POLISH",
    )
    child_asset_id = str(asset.id)
    if child_asset_id in {APPROVED_ASSET_ID, PARENT_CHILD_ASSET_84}:
        raise RuntimeError("R1 must not overwrite canonical or parent 1:1 asset ids")

    history = list(master.get("format_child_history") or [])
    history.append({**parent_child, "superseded_by": FORMAT_CHILD_1X1_R1_ID, "human_review": "SUPERSEDED_BY_SPATIAL_R1"})
    master["format_child_history"] = history

    child_row = {
        "schema": "FormatAdaptationV1",
        "child_id": FORMAT_CHILD_1X1_R1_ID,
        "parent_master_id": APPROVED_MASTER_ID,
        "parent_asset_id": APPROVED_ASSET_ID,
        "parent_format_child_id": PARENT_CHILD_ID_84,
        "parent_format_child_asset": PARENT_CHILD_ASSET_84,
        "visual_asset": child_asset_id,
        "source_format": "4:5",
        "target_format": "1:1",
        "status": status,
        "is_premium_master": False,
        "polish": "spatial_cta_editorial_only",
        "project_photo_asset": DAY003_ASSET_ID,
        "logo_asset": LOCKED_LOGO_ASSET_ID,
        "revision_contract": revision.get("contract"),
        "composition_plan": plan,
    }
    attach_format_child(library, parent_master_id=APPROVED_MASTER_ID, child=child_row)
    master_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    if master_after.get("visual_asset") != canonical_visual_before:
        raise RuntimeError("Phase 8.4-R1 mutated the canonical visual_asset")
    if master_after.get("approval_status") != "HUMAN_APPROVED" or master_after.get("router_eligible") != eligible_before:
        raise RuntimeError("Phase 8.4-R1 mutated Master approval or router eligibility")
    if count_approved_premium(library) != 1:
        raise RuntimeError("Phase 8.4-R1 must not create a Premium Master")
    if any(str(item.get("master_id")) == FORMAT_CHILD_1X1_R1_ID for item in library["masters"]):
        raise RuntimeError("R1 1:1 child must not be registered as a Master")

    spec = {
        "schema": "FormatAdaptationV1",
        **child_row,
        "photo_crop_preserved": validation.get("PHOTO_CROP_PRESERVED"),
        "photo_transform": transform,
        "group_positions": {
            "CTA_TERRITORY": plan["CTA_TERRITORY"],
            "EDITORIAL_CLOSURE_TERRITORY": plan["EDITORIAL_CLOSURE_TERRITORY"],
        },
        "parent_group_positions": {
            "CTA_TERRITORY": old["CTA_TERRITORY"],
            "EDITORIAL_CLOSURE_TERRITORY": old["EDITORIAL_CLOSURE_TERRITORY"],
        },
        "identity_validation": identity,
        "preservation_validation": validation,
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": 10,
    }
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["format_adaptation_1x1_r1"] = json.loads(json.dumps(_jsonable(spec), default=str))

    images = {
        "parent": parent,
        "r1": r1_image,
        "pair": render_format_pair(parent, r1_image, "03  PARENT 1:1 vs R1  —  CTA + editorial only"),
        "three": render_three_way((("4:5 CANONICAL", canonical), ("1:1 PARENT", parent), ("1:1 R1", r1_image))),
        "spatial": render_spatial_board(r1_image, old, plan),
        "preservation": render_preservation_board(parent, r1_image, validation),
        "identity": _text_board(
            "07  IDENTITY + SPATIAL GATES",
            [
                f"STATUS  {status}",
                f"CTA_CLEAR  {identity.get('CTA_CLEAR')}",
                f"EDITORIAL_CLOSURE_CLEAR  {identity.get('EDITORIAL_CLOSURE_CLEAR')}",
                f"LEFT_CAMPAIGN_COLUMN_COHESIVE  {identity.get('LEFT_CAMPAIGN_COLUMN_COHESIVE')}",
                f"TEXT_ON_BUSY_ARCHITECTURE  {identity.get('TEXT_ON_BUSY_ARCHITECTURE')}",
                *[f"{k}  {v}" for k, v in scores.items()],
                f"delta_outside  {validation.get('mean_abs_delta_outside')}",
            ],
        ),
        "review": render_review_board(canonical=canonical, parent=parent, r1=r1_image, identity=identity, status=status),
        "canonical": canonical,
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_84_R1,
        "created_at": _now(),
        "status": status,
        "parent_master_id": APPROVED_MASTER_ID,
        "parent_master_name": APPROVED_MASTER_NAME,
        "parent_format_child_id": PARENT_CHILD_ID_84,
        "parent_format_child_asset": PARENT_CHILD_ASSET_84,
        "child_id": FORMAT_CHILD_1X1_R1_ID,
        "child_asset_id": child_asset_id,
        "source_photo": DAY003_FILENAME,
        "source_photo_asset_id": DAY003_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
        "identity": identity,
        "preservation_validation": validation,
        "revision_readiness": revision,
        "format_adaptation": spec,
        "human_approved_premium_count": count_approved_premium(library),
        "canonical_master_changed": False,
        "production_cover_changed": False,
        "gpt_image_calls": provider_call_count(),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "next_phase": "8.5 INTELLIGENT FORMAT ADAPTATION — 9:16",
        "language": language,
        "canonical_4x5_size": list(canonical.size) if canonical.size else None,
        "unused_4x5_check": canonical.size == CANVAS_4X5,
        "parent_child_id_lock": FORMAT_CHILD_1X1_ID,
    }
    tests = list(blob.get("format_adaptation_84_r1_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "format_adaptation"}), default=str)))
    blob["format_adaptation_84_r1_tests"] = tests
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
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 8.4-R1 refused to change the approved technical Master")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity_pointers"] = {"before": before, "after": after}
    return record
