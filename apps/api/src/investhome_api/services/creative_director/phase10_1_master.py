"""Phase 10.1 — HEADLINE_ONLY child from locked Master 03.

Does not overwrite the parent, price-revision children, or other Masters.
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
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r1_compose import PARENT_MASTER_03_ASSET
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03, CREATIVE_CONCEPT
from investhome_api.services.creative_director.phase10_0_master import CHILD_REVISION_ID as PRICE_CHILD_REVISION_ID
from investhome_api.services.creative_director.phase10_0_master import _identity_slice, attach_derived_revision
from investhome_api.services.creative_director.phase10_0_r1_master import CHILD_REVISION_R1_ID as PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase10_0_r1_master import REJECTED_CHILD_ASSET_ID as PRICE_REJECTED_ASSET_ID
from investhome_api.services.creative_director.phase10_0_r1_master import _preserve as _preserve_r1
from investhome_api.services.creative_director.phase10_0_r1_master import _restore_history as _restore_r1
from investhome_api.services.creative_director.phase10_0_price_revise import render_pixel_diff
from investhome_api.services.creative_director.phase10_1_headline_revise import (
    apply_clean_headline_revision,
    render_25_preview,
    render_labeled_crop,
    render_parent_vs_child,
    render_review_board,
)
from investhome_api.services.creative_director.phase10_1_parse import (
    NEW_COPY,
    OLD_COPY,
    REVISION_TYPE,
    USER_COMMAND,
    parse_headline_only_command,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_10_1 = "phase10_1_natural_language_copy_revision"
CHILD_REVISION_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:temple:premium-03:headline-simdi-yatirim-zamani"))
PRICE_R1_ASSET_ID = "4e34d1a4-8c09-495a-b9f5-86a7ee0e5d23"
FORBIDDEN_ASSETS = frozenset(
    {
        APPROVED_ASSET_ID,
        APPROVED_ASSET_02,
        APPROVED_ASSET_03,
        PARENT_MASTER_03_ASSET,
        PRICE_REJECTED_ASSET_ID,
        PRICE_R1_ASSET_ID,
    }
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r1(blob)
    preserved["quality10r1"] = list(blob.get("phase10_0_r1_price_revision_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_r1(blob, preserved)
    blob["phase10_0_r1_price_revision_tests"] = preserved.get("quality10r1")


def generate_phase10_1_copy_revision(
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

    parsed = parse_headline_only_command(USER_COMMAND)
    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        raise RuntimeError("Phase 10.1 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 10.1 requires locked Masters 01, 02, and 03")
    if str(master_03.get("visual_asset") or "") != APPROVED_ASSET_03:
        raise RuntimeError("Phase 10.1 must render from the locked Master 03 artwork")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    parent_identity_before = _identity_slice(master_03)
    parent_visual_before = str(master_03.get("visual_asset"))
    kids_before = json.loads(json.dumps(_jsonable(master_03.get("derived_revisions") or []), default=str))

    parent_img = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_03)))).convert("RGB")
    child_img, compose_meta = apply_clean_headline_revision(parent_img, old_copy=OLD_COPY, new_copy=NEW_COPY)
    extras = dict(compose_meta.pop("extras") or {})
    residue = dict(compose_meta.get("residue") or {})
    delta = dict(compose_meta.get("pixel_delta") or {})
    glyphs = dict(compose_meta.get("turkish_glyphs") or {})
    outside = int(delta.get("outside_changed_pixels") or 0)
    territory = tuple(compose_meta["territory"])

    child_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(child_img),
        content_type="image/png",
        campaign_mode="project-premium-master-03-headline-revision",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 10.1 HEADLINE_ONLY CHILD OF LOCKED PREMIUM MASTER 03",
    )
    child_asset_id = str(child_asset.id)
    if child_asset_id in FORBIDDEN_ASSETS:
        raise RuntimeError("Phase 10.1 must not overwrite locked masters or price-revision children")

    child_record = {
        "revision_id": CHILD_REVISION_ID,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_master_name": MASTER_NAME_03,
        "parent_asset_id": APPROVED_ASSET_03,
        "revision_type": REVISION_TYPE,
        "natural_language_instruction": USER_COMMAND,
        "old_copy": OLD_COPY,
        "new_copy": NEW_COPY,
        "visual_asset": child_asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "master_state": "CHILD_REVISION",
        "created_at": _now(),
        "creative_concept": CREATIVE_CONCEPT,
        "phase": "10.1",
        "territory": list(territory),
        "pixel_delta_outside": outside,
        "source_asset_id": APPROVED_ASSET_03,
    }
    attach_derived_revision(master_03, child_record)
    if str(master_03.get("visual_asset")) != parent_visual_before:
        raise RuntimeError("Phase 10.1 refused to replace the locked parent visual")
    if _identity_slice(master_03) != parent_identity_before:
        raise RuntimeError("Phase 10.1 refused to mutate locked Master 03 identity")
    kept = {str(item.get("revision_id")) for item in (master_03.get("derived_revisions") or [])}
    if PRICE_CHILD_REVISION_ID not in kept or PRICE_R1_REVISION_ID not in kept:
        raise RuntimeError("Phase 10.1 must preserve existing price-revision children")
    if json.dumps(_jsonable(kids_before), default=str) != json.dumps(
        _jsonable([item for item in (master_03.get("derived_revisions") or []) if str(item.get("revision_id")) != CHILD_REVISION_ID]),
        default=str,
    ):
        raise RuntimeError("Phase 10.1 refused to mutate existing derived revisions")

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 10.1 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 10.1 refused to change Master 02")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 10.1 must not change locked Premium Master approvals")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 10.1 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    critic_board = critic or {
        "OLD_HEADLINE_COMPLETELY_REMOVED": "PENDING",
        "NEW_HEADLINE_FULLY_LEGIBLE": "PENDING",
        "TURKISH_GLYPHS_CORRECT": "PENDING",
        "TYPOGRAPHY_LOOKS_NATIVE_TO_MASTER": "PENDING",
        "HEADLINE_HIERARCHY_PRESERVED": "PENDING",
        "VISIBLE_PATCH_OR_MASK": "PENDING",
        "TEXT_COLLISIONS": "PENDING",
        "LOOKING_CHAMBER_PRESERVED": "PENDING",
        "UNRELATED_VISUAL_CHANGE": "PENDING",
    }
    patch = critic_board.get("VISIBLE_PATCH_OR_MASK") == "YES"
    collisions = critic_board.get("TEXT_COLLISIONS") == "YES"
    unrelated = critic_board.get("UNRELATED_VISUAL_CHANGE") == "YES"
    native_no = critic_board.get("TYPOGRAPHY_LOOKS_NATIVE_TO_MASTER") == "NO"
    visual_fail = (
        patch
        or collisions
        or unrelated
        or native_no
        or residue.get("pass") is not True
        or glyphs.get("pass") is not True
        or outside != 0
    )
    structural = parsed.get("pass") is True and residue.get("pass") is True and provider_call_count() == 0
    if visual_fail or not structural:
        status = "COPY_REVISION_VISUAL_FAIL"
    else:
        status = "COPY_REVISION_PENDING_HUMAN_APPROVAL"

    preview = render_25_preview(child_img)
    images = {
        "parent": parent_img,
        "original_territory": render_labeled_crop(
            extras["original_crop"].resize(
                (max(1, extras["original_crop"].size[0] * 2), max(1, extras["original_crop"].size[1] * 2)),
                Image.Resampling.NEAREST,
            ),
            "02  ORIGINAL HEADLINE TERRITORY  ALIRKEN / KAZAN",
        ),
        "clean_bg": extras["clean_full"],
        "new_headline": render_labeled_crop(
            extras["new_plate"].resize(
                (max(1, extras["new_plate"].size[0] * 2), max(1, extras["new_plate"].size[1] * 2)),
                Image.Resampling.NEAREST,
            ),
            "04  NEW HEADLINE RENDER  ŞİMDİ YATIRIM ZAMANI",
        ),
        "child": child_img,
        "pair": render_parent_vs_child(parent_img, child_img),
        "diff": render_pixel_diff(parent_img, child_img),
        "preview25": preview,
        "review": render_review_board(parent_img, child_img, preview),
        "clean_crop": extras["clean_crop"],
    }

    validation = {
        "NATURAL_LANGUAGE_PARSE": "PASS" if parsed.get("pass") else "FAIL",
        "OLD_HEADLINE_COMPLETELY_REMOVED": "YES" if residue.get("pass") else "NO",
        "CLEAN_BACKGROUND": "PASS" if residue.get("pass") else "FAIL",
        "NEW_HEADLINE_FULLY_LEGIBLE": critic_board.get("NEW_HEADLINE_FULLY_LEGIBLE", "PENDING"),
        "TURKISH_GLYPHS": "PASS" if glyphs.get("pass") and critic_board.get("TURKISH_GLYPHS_CORRECT") != "NO" else "FAIL",
        "TYPOGRAPHY_NATIVE_TO_MASTER": "PASS"
        if critic_board.get("TYPOGRAPHY_LOOKS_NATIVE_TO_MASTER") == "YES"
        else ("FAIL" if critic_board.get("TYPOGRAPHY_LOOKS_NATIVE_TO_MASTER") == "NO" else "PENDING"),
        "HEADLINE_HIERARCHY": "PASS" if critic_board.get("HEADLINE_HIERARCHY_PRESERVED") == "YES" else (
            "FAIL" if critic_board.get("HEADLINE_HIERARCHY_PRESERVED") == "NO" else "PENDING"
        ),
        "VISIBLE_PATCH": "YES" if patch else "NO",
        "TEXT_COLLISIONS": "YES" if collisions else "NO",
        "PIXEL_DELTA_OUTSIDE_HEADLINE_TERRITORY": outside,
        "LOOKING_CHAMBER_PRESERVED": "PASS" if outside == 0 and critic_board.get("LOOKING_CHAMBER_PRESERVED") != "NO" else "FAIL",
        "ARCHITECTURE_FIDELITY": 10 if outside == 0 else "FAIL",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "LOGO_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "OFFER_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "PRICE_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "CTA_PRESERVED": "PASS" if outside == 0 else "FAIL",
        "GPT_IMAGE_CALLS": provider_call_count(),
        "PARENT_MASTER_CHANGED": "NO",
        "UNRELATED_VISUAL_CHANGE": critic_board.get("UNRELATED_VISUAL_CHANGE", "PENDING"),
    }
    contract = {
        "revision_type": REVISION_TYPE,
        "natural_language_instruction": USER_COMMAND,
        "old_copy": OLD_COPY,
        "new_copy": NEW_COPY,
        "source_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "source_asset_id": APPROVED_ASSET_03,
        "preserve": [
            "Temple logo",
            "WASHINGTON D.C.",
            "%35 LANSMAN AVANTAJI",
            "675.000 USD",
            "2+1 DAİRE",
            "PROJEYİ KEŞFET",
            "TARİHİN RUHU, GELECEĞİN DEĞERİ.",
            "interior",
            "exterior",
            "Looking Chamber",
        ],
        "approval_status": "DRAFT",
        "router_eligible": False,
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_10_1,
        "created_at": _now(),
        "status": status,
        "user_command": USER_COMMAND,
        "parent_master_name": MASTER_NAME_03,
        "parent_master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "parent_asset_id": APPROVED_ASSET_03,
        "child_revision_id": CHILD_REVISION_ID,
        "child_asset_id": child_asset_id,
        "revision_type": REVISION_TYPE,
        "old_copy": OLD_COPY,
        "new_copy": NEW_COPY,
        "parse": parsed,
        "contract": contract,
        "compose": compose_meta,
        "critic": critic_board,
        "validation": validation,
        "gpt_image_calls": provider_call_count(),
        "parent_master_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "photo_replacement_executed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "master_01_id": APPROVED_MASTER_ID,
        "master_01_asset_id": APPROVED_ASSET_ID,
        "master_02_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "master_02_asset_id": APPROVED_ASSET_02,
        "price_child_revision_id": PRICE_CHILD_REVISION_ID,
        "price_r1_revision_id": PRICE_R1_REVISION_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "language": language,
    }
    tests = list(blob.get("phase10_1_copy_revision_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase10_1_copy_revision_tests"] = tests
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
