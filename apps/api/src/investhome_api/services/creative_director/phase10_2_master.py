"""Phase 10.2 — VISUAL_REPLACE_ONLY child from locked Master 03.

Does not overwrite the parent, price/copy children, or other Masters.
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
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_compose import INTERIOR_ASSET_ID
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r1_compose import PARENT_MASTER_03_ASSET
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03, CREATIVE_CONCEPT
from investhome_api.services.creative_director.phase10_0_master import CHILD_REVISION_ID as PRICE_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_0_master import _identity_slice, attach_derived_revision
from investhome_api.services.creative_director.phase10_0_price_revise import render_pixel_diff
from investhome_api.services.creative_director.phase10_0_r1_master import CHILD_REVISION_R1_ID as PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase10_0_r1_master import REJECTED_CHILD_ASSET_ID as PRICE_REJECTED_ASSET_ID
from investhome_api.services.creative_director.phase10_1_master import CHILD_REVISION_ID as COPY_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_1_master import _preserve as _preserve_11
from investhome_api.services.creative_director.phase10_1_master import _restore_history as _restore_11
from investhome_api.services.creative_director.phase10_2_parse import (
    INTERIOR_ASSET_ID as LOCKED_INTERIOR_ID,
    OLD_EXTERIOR_ASSET_ID,
    OLD_EXTERIOR_FILENAME,
    REVISION_TYPE,
    TARGET_OBJECT,
    USER_COMMAND,
    parse_visual_replace_command,
)
from investhome_api.services.creative_director.phase10_2_replace import (
    SELECTED_ASSET_ID,
    SELECTED_FILENAME,
    SELECTION_REASON,
    SHORTLIST,
    apply_exterior_replacement,
    load_asset,
    render_crop_plan,
    render_labeled,
    render_parent_vs_child,
    render_review_board,
    render_shortlist,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_10_2 = "phase10_2_natural_language_photo_replacement"
CHILD_REVISION_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:temple:premium-03:exterior-day-009"))
PRICE_R1_ASSET_ID = "4e34d1a4-8c09-495a-b9f5-86a7ee0e5d23"
COPY_CHILD_ASSET_ID = "5530c586-e975-4cb7-afaa-ce9fffa92e53"
FORBIDDEN_ASSETS = frozenset(
    {
        APPROVED_ASSET_ID,
        APPROVED_ASSET_02,
        APPROVED_ASSET_03,
        PARENT_MASTER_03_ASSET,
        PRICE_REJECTED_ASSET_ID,
        PRICE_R1_ASSET_ID,
        COPY_CHILD_ASSET_ID,
        OLD_EXTERIOR_ASSET_ID,
        INTERIOR_ASSET_ID,
        LOCKED_INTERIOR_ID,
    }
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_11(blob)
    preserved["quality101"] = list(blob.get("phase10_1_copy_revision_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_11(blob, preserved)
    blob["phase10_1_copy_revision_tests"] = preserved.get("quality101")


def generate_phase10_2_photo_replacement(
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

    parsed = parse_visual_replace_command(USER_COMMAND)
    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 10.2 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 10.2 requires locked Masters 01, 02, and 03")
    if str(master_03.get("visual_asset") or "") != APPROVED_ASSET_03:
        raise RuntimeError("Phase 10.2 must render from the locked Master 03 artwork")
    if SELECTED_ASSET_ID == OLD_EXTERIOR_ASSET_ID:
        raise RuntimeError("Phase 10.2 must not keep Day_002")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    parent_identity_before = _identity_slice(master_03)
    parent_visual_before = str(master_03.get("visual_asset"))
    kids_before = json.loads(json.dumps(_jsonable(master_03.get("derived_revisions") or []), default=str))

    parent_img = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    current_ext = load_asset(db, OLD_EXTERIOR_ASSET_ID)
    selected_src = load_asset(db, SELECTED_ASSET_ID)
    child_img, compose_meta = apply_exterior_replacement(parent_img, selected_src)
    extras = dict(compose_meta.pop("extras") or {})
    delta = dict(compose_meta.get("pixel_delta") or {})
    outside = int(delta.get("outside_changed_pixels") or 0)
    territory = tuple(compose_meta["territory"])

    child_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(child_img),
        content_type="image/png",
        campaign_mode="project-premium-master-03-exterior-replacement",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 10.2 VISUAL_REPLACE_ONLY CHILD OF LOCKED PREMIUM MASTER 03",
    )
    child_asset_id = str(child_asset.id)
    if child_asset_id in FORBIDDEN_ASSETS:
        raise RuntimeError("Phase 10.2 must not overwrite locked masters, photos, or prior children")

    child_record = {
        "revision_id": CHILD_REVISION_ID,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_master_name": MASTER_NAME_03,
        "parent_asset_id": APPROVED_ASSET_03,
        "revision_type": REVISION_TYPE,
        "target_object": TARGET_OBJECT,
        "natural_language_instruction": USER_COMMAND,
        "old_asset": OLD_EXTERIOR_ASSET_ID,
        "new_asset": SELECTED_ASSET_ID,
        "old_filename": OLD_EXTERIOR_FILENAME,
        "new_filename": SELECTED_FILENAME,
        "visual_asset": child_asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "master_state": "CHILD_REVISION",
        "created_at": _now(),
        "creative_concept": CREATIVE_CONCEPT,
        "phase": "10.2",
        "territory": list(territory),
        "pixel_delta_outside": outside,
        "source_asset_id": APPROVED_ASSET_03,
    }
    attach_derived_revision(master_03, child_record)
    if str(master_03.get("visual_asset")) != parent_visual_before:
        raise RuntimeError("Phase 10.2 refused to replace the locked parent visual")
    if _identity_slice(master_03) != parent_identity_before:
        raise RuntimeError("Phase 10.2 refused to mutate locked Master 03 identity")
    kept = {str(item.get("revision_id")) for item in (master_03.get("derived_revisions") or [])}
    for required in (PRICE_CHILD_REVISION_ID, PRICE_R1_REVISION_ID, COPY_CHILD_REVISION_ID):
        if required not in kept:
            raise RuntimeError("Phase 10.2 must preserve existing derived revisions")
    if json.dumps(_jsonable(kids_before), default=str) != json.dumps(
        _jsonable([item for item in (master_03.get("derived_revisions") or []) if str(item.get("revision_id")) != CHILD_REVISION_ID]),
        default=str,
    ):
        raise RuntimeError("Phase 10.2 refused to mutate existing derived revisions")

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 10.2 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 10.2 refused to change Master 02")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 10.2 must not change locked Premium Master approvals")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 10.2 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    critic_board = critic or {
        "NEW_EXTERIOR_IS_REAL_TEMPLE_PHOTO": "PENDING",
        "EXTERIOR_ACTUALLY_CHANGED": "PENDING",
        "INTERIOR_UNCHANGED": "PENDING",
        "DESIGN_GEOMETRY_UNCHANGED": "PENDING",
        "TYPOGRAPHY_UNCHANGED": "PENDING",
        "LOGO_UNCHANGED": "PENDING",
        "LOOKING_CHAMBER_PRESERVED": "PENDING",
        "NEW_EXTERIOR_CROP_PROFESSIONAL": "PENDING",
        "TEMPLE_ARCHITECTURE_READABLE": "PENDING",
        "PHOTO_CARD_FEELING": "PENDING",
        "VISIBLE_MASK_COMPOSITING_DAMAGE": "PENDING",
        "UNRELATED_VISUAL_CHANGE": "PENDING",
    }
    visual_fail = (
        critic_board.get("NEW_EXTERIOR_IS_REAL_TEMPLE_PHOTO") == "NO"
        or critic_board.get("EXTERIOR_ACTUALLY_CHANGED") == "NO"
        or critic_board.get("INTERIOR_UNCHANGED") == "NO"
        or critic_board.get("DESIGN_GEOMETRY_UNCHANGED") == "NO"
        or critic_board.get("TYPOGRAPHY_UNCHANGED") == "NO"
        or critic_board.get("LOOKING_CHAMBER_PRESERVED") == "NO"
        or critic_board.get("NEW_EXTERIOR_CROP_PROFESSIONAL") == "NO"
        or critic_board.get("PHOTO_CARD_FEELING") == "YES"
        or critic_board.get("VISIBLE_MASK_COMPOSITING_DAMAGE") == "YES"
        or critic_board.get("UNRELATED_VISUAL_CHANGE") == "YES"
        or outside != 0
        or parsed.get("pass") is not True
    )
    status = "PROJECT_PHOTO_REPLACEMENT_VISUAL_FAIL" if visual_fail else "PROJECT_PHOTO_REPLACEMENT_PENDING_HUMAN_APPROVAL"

    short_items = []
    for filename, asset_id, note in SHORTLIST:
        img = load_asset(db, asset_id)
        short_items.append((f"{filename.replace('IH_DC_TMP_001_Render_Exterior_', '')}  {note}", img, asset_id == SELECTED_ASSET_ID))

    images = {
        "parent": parent_img,
        "current_exterior": render_labeled(current_ext, "02  CURRENT EXTERIOR  Day_002"),
        "shortlist": render_shortlist(short_items),
        "selected": render_labeled(selected_src, "04  SELECTED REPLACEMENT  Day_009"),
        "crop_plan": render_crop_plan(selected_src, compose_meta.get("crop") or {}, extras["graded"], extras["vis"]),
        "child": child_img,
        "pair": render_parent_vs_child(parent_img, child_img),
        "diff": render_pixel_diff(parent_img, child_img),
        "review": render_review_board(parent_img, child_img, selected_src),
        "graded": extras["graded"],
    }

    def _yn(key: str, yes: str = "PASS", no: str = "FAIL") -> str:
        val = critic_board.get(key, "PENDING")
        if val in {"YES", "PASS"}:
            return yes
        if val in {"NO", "FAIL"}:
            return no
        return "PENDING"

    validation = {
        "NATURAL_LANGUAGE_PARSE": "PASS" if parsed.get("pass") else "FAIL",
        "REAL_TEMPLE_REPLACEMENT": _yn("NEW_EXTERIOR_IS_REAL_TEMPLE_PHOTO"),
        "EXTERIOR_ACTUALLY_CHANGED": critic_board.get("EXTERIOR_ACTUALLY_CHANGED", "PENDING"),
        "INTERIOR_PRESERVED": "PASS" if outside == 0 and critic_board.get("INTERIOR_UNCHANGED") != "NO" else "FAIL",
        "DESIGN_GEOMETRY_PRESERVED": _yn("DESIGN_GEOMETRY_UNCHANGED"),
        "TYPOGRAPHY_PRESERVED": _yn("TYPOGRAPHY_UNCHANGED"),
        "LOGO_PRESERVED": _yn("LOGO_UNCHANGED"),
        "LOOKING_CHAMBER_PRESERVED": _yn("LOOKING_CHAMBER_PRESERVED"),
        "NEW_EXTERIOR_CROP": _yn("NEW_EXTERIOR_CROP_PROFESSIONAL"),
        "ARCHITECTURE_READABILITY": _yn("TEMPLE_ARCHITECTURE_READABLE"),
        "PHOTO_CARD_FEELING": critic_board.get("PHOTO_CARD_FEELING", "PENDING"),
        "VISIBLE_COMPOSITING_DAMAGE": critic_board.get("VISIBLE_MASK_COMPOSITING_DAMAGE", "PENDING"),
        "PIXEL_DELTA_OUTSIDE_EXTERIOR_TERRITORY": outside,
        "ARCHITECTURE_FIDELITY": 10 if SELECTED_ASSET_ID != OLD_EXTERIOR_ASSET_ID else "FAIL",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "GPT_IMAGE_CALLS": provider_call_count(),
        "PARENT_MASTER_CHANGED": "NO",
        "UNRELATED_VISUAL_CHANGE": critic_board.get("UNRELATED_VISUAL_CHANGE", "PENDING"),
    }
    contract = {
        "revision_type": REVISION_TYPE,
        "target_object": TARGET_OBJECT,
        "natural_language_instruction": USER_COMMAND,
        "source_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "source_asset_id": APPROVED_ASSET_03,
        "old_asset": OLD_EXTERIOR_ASSET_ID,
        "new_asset": SELECTED_ASSET_ID,
        "old_filename": OLD_EXTERIOR_FILENAME,
        "new_filename": SELECTED_FILENAME,
        "interior_asset_id": INTERIOR_ASSET_ID,
        "approval_status": "DRAFT",
        "router_eligible": False,
    }
    selection = {
        "selected_filename": SELECTED_FILENAME,
        "selected_asset_id": SELECTED_ASSET_ID,
        "reason": SELECTION_REASON,
        "shortlist": [{"filename": n, "asset_id": a, "note": note} for n, a, note in SHORTLIST],
        "rejected_current": OLD_EXTERIOR_ASSET_ID,
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_10_2,
        "created_at": _now(),
        "status": status,
        "user_command": USER_COMMAND,
        "parent_master_name": MASTER_NAME_03,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_asset_id": APPROVED_ASSET_03,
        "child_revision_id": CHILD_REVISION_ID,
        "child_asset_id": child_asset_id,
        "revision_type": REVISION_TYPE,
        "target_object": TARGET_OBJECT,
        "old_exterior": OLD_EXTERIOR_FILENAME,
        "old_asset_id": OLD_EXTERIOR_ASSET_ID,
        "new_exterior": SELECTED_FILENAME,
        "new_asset_id": SELECTED_ASSET_ID,
        "selection_reason": SELECTION_REASON,
        "parse": parsed,
        "contract": contract,
        "selection": selection,
        "compose": compose_meta,
        "critic": critic_board,
        "validation": validation,
        "gpt_image_calls": provider_call_count(),
        "parent_master_changed": False,
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
        "cover": PRODUCTION_COVER_V2,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "language": language,
    }
    tests = list(blob.get("phase10_2_photo_replacement_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase10_2_photo_replacement_tests"] = tests
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
