"""Phase 10.0 — Stage 2 natural-language PRICE_ONLY child of locked Master 03.

Does not regenerate the Master. Does not mutate the locked parent visual.
"""

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
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
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
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r1_compose import PARENT_MASTER_03_ASSET
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03, CREATIVE_CONCEPT
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import _HISTORY_KEYS as _H91R2
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import _preserve as _preserve_r2
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import _restore_history as _restore_r2
from investhome_api.services.creative_director.phase10_0_parse import (
    NEW_PRICE,
    OLD_PRICE,
    REVISION_TYPE,
    USER_COMMAND,
    parse_price_only_command,
)
from investhome_api.services.creative_director.phase10_0_price_revise import (
    apply_price_only,
    render_parent_child,
    render_parse_board,
    render_pixel_diff,
    render_review_board,
    render_territory,
    render_validation_board,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_10 = "phase10_0_natural_language_price_revision"
CHILD_REVISION_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:temple:premium-03:price-750000-usd"))
PARENT_IDENTITY_KEYS = (
    "visual_asset",
    "approval_status",
    "master_state",
    "router_eligible",
    "version",
    "locked_identity",
    "creative_concept",
    "canonical_format",
)
_HISTORY_KEYS = _H91R2 + (("premium_master_91_r2_tests", "quality91r2"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r2(blob)
    preserved["quality91r2"] = list(blob.get("premium_master_91_r2_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_r2(blob, preserved)
    blob["premium_master_91_r2_tests"] = preserved.get("quality91r2")


def _identity_slice(master: dict[str, Any]) -> dict[str, Any]:
    return {key: json.loads(json.dumps(_jsonable(master.get(key)), default=str)) for key in PARENT_IDENTITY_KEYS}


def attach_derived_revision(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    revisions = [item for item in list(parent.get("derived_revisions") or []) if str(item.get("revision_id")) != str(child.get("revision_id"))]
    revisions.append(dict(child))
    parent["derived_revisions"] = revisions
    ids = [item for item in list(parent.get("child_revision_ids") or []) if item != child.get("revision_id")]
    if child.get("revision_id"):
        ids.append(child["revision_id"])
    parent["child_revision_ids"] = ids
    return parent


def generate_phase10_0_natural_language_price_revision(
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

    parsed = parse_price_only_command(USER_COMMAND, current_price=OLD_PRICE)
    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 10.0 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 10.0 requires locked Masters 01, 02, and 03")
    if str(master_03.get("visual_asset") or "") != APPROVED_ASSET_03:
        raise RuntimeError("Phase 10.0 must use the locked Master 03 R1 artwork")
    if master_03.get("approval_status") != "HUMAN_APPROVED" or master_03.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 10.0 requires Master 03 HUMAN_APPROVED LOCKED_MASTER")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    parent_identity_before = _identity_slice(master_03)
    parent_visual_before = str(master_03.get("visual_asset"))

    parent_img = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    child_img, compose_meta = apply_price_only(parent_img, old_value=OLD_PRICE, new_value=NEW_PRICE)
    delta = dict(compose_meta.get("pixel_delta") or {})
    outside = int(delta.get("outside_changed_pixels") or 0)

    child_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(child_img),
        content_type="image/png",
        campaign_mode="project-premium-master-03-price-revision-child",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 10.0 PRICE_ONLY CHILD OF LOCKED PREMIUM MASTER 03",
    )
    child_asset_id = str(child_asset.id)
    if child_asset_id in {APPROVED_ASSET_ID, APPROVED_ASSET_02, APPROVED_ASSET_03, PARENT_MASTER_03_ASSET}:
        raise RuntimeError("child revision must not overwrite a locked master asset")

    child_record = {
        "revision_id": CHILD_REVISION_ID,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_master_name": MASTER_NAME_03,
        "parent_asset_id": APPROVED_ASSET_03,
        "revision_type": REVISION_TYPE,
        "natural_language_instruction": USER_COMMAND,
        "old_value": OLD_PRICE,
        "new_value": NEW_PRICE,
        "visual_asset": child_asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "master_state": "CHILD_REVISION",
        "created_at": _now(),
        "creative_concept": CREATIVE_CONCEPT,
        "territory": compose_meta.get("territory"),
        "pixel_delta_outside": outside,
    }
    attach_derived_revision(master_03, child_record)
    if str(master_03.get("visual_asset")) != parent_visual_before:
        raise RuntimeError("Phase 10.0 refused to replace the locked parent visual")
    if _identity_slice(master_03) != parent_identity_before:
        raise RuntimeError("Phase 10.0 refused to mutate locked Master 03 identity")

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 10.0 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 10.0 refused to change Master 02")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 10.0 must not change locked Premium Master approvals")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 10.0 must not call image generation")
    if library.get("stage_1") != "COMPLETE":
        raise RuntimeError("Stage 1 must remain COMPLETE")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    parse_ok = parsed.get("pass") is True
    territory_ok = outside == 0 and int(delta.get("inside_changed_pixels") or 0) > 0
    structural = parse_ok and territory_ok and provider_call_count() == 0 and str(master_03_after.get("visual_asset")) == APPROVED_ASSET_03
    status = "NATURAL_LANGUAGE_PRICE_REVISION_PENDING_HUMAN_APPROVAL" if structural else "NATURAL_LANGUAGE_PRICE_REVISION_FAIL"

    validation = {
        "NATURAL_LANGUAGE_PARSE": "PASS" if parse_ok else "FAIL",
        "PRICE_TERRITORY_ONLY": "PASS" if territory_ok else "FAIL",
        "PIXEL_DELTA_OUTSIDE_PRICE_TERRITORY": outside,
        "ARCHITECTURE_FIDELITY": 10 if outside == 0 else "FAIL",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "LOGO_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "HEADLINE_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "OFFER_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "UNIT_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "CTA_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "CLOSURE_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "LOOKING_CHAMBER_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "GPT_IMAGE_CALLS": provider_call_count(),
        "PARENT_MASTER_CHANGED": "NO",
    }
    contract = {
        "schema": "PriceOnlyRevisionContractV1",
        "revision_type": REVISION_TYPE,
        "natural_language_instruction": USER_COMMAND,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_asset_id": APPROVED_ASSET_03,
        "child_revision_id": CHILD_REVISION_ID,
        "child_asset_id": child_asset_id,
        "old_value": OLD_PRICE,
        "new_value": NEW_PRICE,
        "creates_child_revision": True,
        "never_overwrite_canonical": True,
        "layout_adjusted": False,
        "executed": True,
        "territory": compose_meta.get("territory"),
        "method": compose_meta.get("method"),
    }
    images = {
        "parent": parent_img,
        "parse": render_parse_board(parsed),
        "territory": render_territory(parent_img, tuple(compose_meta["territory"])),
        "child": child_img,
        "pair": render_parent_child(parent_img, child_img),
        "diff": render_pixel_diff(parent_img, child_img),
        "validation": render_validation_board(
            [
                f"STATUS  {status}",
                f"PARSE  {validation['NATURAL_LANGUAGE_PARSE']}",
                f"PRICE TERRITORY ONLY  {validation['PRICE_TERRITORY_ONLY']}",
                f"PIXEL DELTA OUTSIDE  {outside}",
                f"GPT IMAGE CALLS  {provider_call_count()}",
                "PARENT MASTER CHANGED  NO",
                "CHILD  DRAFT  ROUTER INELIGIBLE",
                "FORMAT WORK  NOT EXECUTED",
            ]
        ),
        "review": render_review_board(parent_img, child_img, render_pixel_diff(parent_img, child_img)),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_10,
        "created_at": _now(),
        "status": status,
        "user_command": USER_COMMAND,
        "parent_master_name": MASTER_NAME_03,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_asset_id": APPROVED_ASSET_03,
        "child_revision_id": CHILD_REVISION_ID,
        "child_asset_id": child_asset_id,
        "revision_type": REVISION_TYPE,
        "old_price": OLD_PRICE,
        "new_price": NEW_PRICE,
        "parse": parsed,
        "compose": compose_meta,
        "contract": contract,
        "validation": validation,
        "gpt_image_calls": provider_call_count(),
        "parent_master_changed": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "stage_2_capability": "PRICE_ONLY",
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
        "editorial": APPROVED_BOTTOM_COPY,
        "language": language,
    }
    tests = list(blob.get("phase10_0_price_revision_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items()}), default=str)))
    blob["phase10_0_price_revision_tests"] = tests
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
    record["identity"] = {"before": before, "after": after}
    record["child_revision"] = child_record
    return record
