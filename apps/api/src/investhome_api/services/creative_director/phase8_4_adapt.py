"""Phase 8.4 — create the 1:1 format child of Temple Premium Campaign 01.

Canonical 4:5 Master is unchanged. Not a new Premium Master. GPT Image = 0.
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
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
    render_html_to_png,
)
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
from investhome_api.services.creative_director.phase8_2_r1_compose import DAY003_ASSET_ID, DAY003_FILENAME, LOCKED_CENTERING
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID, APPROVED_MASTER_NAME
from investhome_api.services.creative_director.phase8_3_approve_lock import _HISTORY_KEYS as _H83
from investhome_api.services.creative_director.phase8_3_approve_lock import _preserve as _preserve_83
from investhome_api.services.creative_director.phase8_3_approve_lock import _restore_history as _restore_83
from investhome_api.services.creative_director.phase8_4_format_1x1 import (
    CANVAS_1X1,
    S,
    build_format_adaptation_v1,
    crop_day003_1x1,
    identity_validation,
    plan_1x1,
    render_crop_analysis,
    render_format_pair,
    render_human_review_board,
    render_recomposition,
    revision_readiness_1x1,
    source_crop_rect,
    square_html,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    attach_format_child,
    count_approved_premium,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_84 = "phase8_4_intelligent_format_adaptation_1x1"
FORMAT_CHILD_1X1_ID = str(uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-01:format:1x1"))
_HISTORY_KEYS = _H83 + (("approve_lock_premium_master_83_tests", "quality83"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_83(blob)
    preserved["quality83"] = list(blob.get("approve_lock_premium_master_83_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_83(blob, preserved)
    blob["approve_lock_premium_master_83_tests"] = preserved.get("quality83")


def generate_phase8_4_format_adaptation_1x1(
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
        raise RuntimeError("Phase 8.4 requires ProjectCreativeMasterLibraryV1 from Phase 8.3")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if parent is None:
        raise RuntimeError("Phase 8.4 requires locked Premium Campaign 01")
    if parent.get("approval_status") != "HUMAN_APPROVED" or parent.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 8.4 refused to adapt an unlocked Master")
    if str(parent.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 8.4 refused to adapt from a mutated canonical visual")
    parent_visual_before = parent.get("visual_asset")
    parent_eligible_before = parent.get("router_eligible")

    canonical = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_ID)))).convert("RGB")
    if canonical.size != CANVAS_4X5:
        raise RuntimeError("canonical 4:5 visual is not 1088x1360")
    day003 = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    photo, transform = crop_day003_1x1(day003)
    plan = plan_1x1()
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    html = square_html(
        photo_uri=_jpeg_data_uri(photo, quality=92),
        logo_markup=inline_logo_svg(logo_bytes),
        font_css=font_face_css(build_font_registry()),
        plan=plan,
    )
    square = render_html_to_png(html, width=S, height=S).convert("RGB")
    if square.size != CANVAS_1X1:
        raise RuntimeError("1:1 adaptation is not 1088x1088")

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(square),
        content_type="image/png",
        campaign_mode="project-premium-format-child-1x1",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 8.4 THE TEMPLE PREMIUM CAMPAIGN 01 FORMAT CHILD 1:1",
    )
    child_asset_id = str(asset.id)
    if child_asset_id == APPROVED_ASSET_ID:
        raise RuntimeError("1:1 child must not reuse the canonical asset id")

    spec = build_format_adaptation_v1(
        child_id=FORMAT_CHILD_1X1_ID,
        parent_master_id=APPROVED_MASTER_ID,
        parent_asset_id=APPROVED_ASSET_ID,
        child_asset_id=child_asset_id,
        photo_transform=transform,
        source_size=day003.size,
        plan=plan,
    )
    identity = identity_validation(html=html, square=square, canonical=canonical, plan=plan)
    revision = revision_readiness_1x1(parent_master_id=APPROVED_MASTER_ID, child_id=FORMAT_CHILD_1X1_ID)
    family_yes = identity.get("SAME_CAMPAIGN_FAMILY") == "YES"
    publishable_yes = identity.get("INDEPENDENTLY_PUBLISHABLE_1X1") == "YES"
    scores = identity.get("scores") or {}
    scores_ok = all(int(v) >= 8 for v in scores.values())
    arch_ok = identity.get("ARCHITECTURE_FIDELITY") == 10
    gpt_ok = provider_call_count() == 0
    structural = family_yes and publishable_yes and scores_ok and arch_ok and gpt_ok
    status = "FORMAT_ADAPTATION_PENDING_HUMAN_APPROVAL" if structural else "FORMAT_ADAPTATION_NOT_READY"
    spec["status"] = status
    spec["identity_validation"] = identity
    spec["revision_readiness"] = revision

    child_row = {
        "schema": "FormatAdaptationV1",
        "child_id": FORMAT_CHILD_1X1_ID,
        "parent_master_id": APPROVED_MASTER_ID,
        "parent_asset_id": APPROVED_ASSET_ID,
        "visual_asset": child_asset_id,
        "source_format": "4:5",
        "target_format": "1:1",
        "status": status,
        "is_premium_master": False,
        "project_photo_asset": DAY003_ASSET_ID,
        "logo_asset": LOCKED_LOGO_ASSET_ID,
        "revision_contract": revision.get("contract"),
    }
    attach_format_child(library, parent_master_id=APPROVED_MASTER_ID, child=child_row)
    parent_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    if parent_after.get("visual_asset") != parent_visual_before:
        raise RuntimeError("Phase 8.4 mutated the canonical visual_asset")
    if parent_after.get("approval_status") != "HUMAN_APPROVED" or parent_after.get("router_eligible") != parent_eligible_before:
        raise RuntimeError("Phase 8.4 mutated Master approval or router eligibility")
    if count_approved_premium(library) != 1:
        raise RuntimeError("Phase 8.4 must not create a second Premium Master")
    if any(str(item.get("master_id")) == FORMAT_CHILD_1X1_ID for item in library["masters"]):
        raise RuntimeError("1:1 child must not be registered as a Master")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["format_adaptation_1x1"] = json.loads(json.dumps(_jsonable(spec), default=str))

    crop_45 = source_crop_rect(day003.size, CANVAS_4X5, LOCKED_CENTERING)
    crop_11 = source_crop_rect(day003.size, CANVAS_1X1, tuple(transform.get("centering") or (0.42, 0.50)))
    images = {
        "canonical": canonical,
        "square": square,
        "pair": render_format_pair(canonical, square, "03  SIDE-BY-SIDE  —  4:5 canonical vs 1:1 format child"),
        "crop": render_crop_analysis(day003, crop_45, crop_11),
        "recomposition": render_recomposition(square, plan),
        "identity": _text_board(
            "06  IDENTITY VALIDATION",
            [
                f"STATUS  {status}",
                f"ARCHITECTURE_FIDELITY  {identity.get('ARCHITECTURE_FIDELITY')}",
                f"SAME_CAMPAIGN_FAMILY  {identity.get('SAME_CAMPAIGN_FAMILY')}",
                f"INDEPENDENTLY_PUBLISHABLE_1X1  {identity.get('INDEPENDENTLY_PUBLISHABLE_1X1')}",
                *[f"{k}  {v}" for k, v in scores.items()],
            ],
        ),
        "revision": _text_board(
            "07  REVISION READINESS  —  lineage to canonical Master",
            [
                f"PARENT  {APPROVED_MASTER_ID}",
                f"CHILD  {FORMAT_CHILD_1X1_ID}",
                f"PRICE  {revision.get('PRICE_EDIT_ONLY')}",
                f"COPY  {revision.get('COPY_EDIT_ONLY')}",
                f"VISUAL REPLACE  {revision.get('VISUAL_REPLACE_ONLY')}  PROJECT_PHOTO_OBJECT",
                "creates_child_revision  TRUE",
                "never_overwrite_canonical  TRUE",
                "executed  FALSE",
            ],
        ),
        "review": render_human_review_board(canonical=canonical, square=square, identity=identity, status=status),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_84,
        "created_at": _now(),
        "status": status,
        "parent_master_id": APPROVED_MASTER_ID,
        "parent_asset_id": APPROVED_ASSET_ID,
        "parent_master_name": APPROVED_MASTER_NAME,
        "child_id": FORMAT_CHILD_1X1_ID,
        "child_asset_id": child_asset_id,
        "source_photo": DAY003_FILENAME,
        "source_photo_asset_id": DAY003_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": identity.get("ARCHITECTURE_FIDELITY"),
        "identity": identity,
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
    }
    tests = list(blob.get("format_adaptation_84_1x1_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "format_adaptation"}), default=str)))
    blob["format_adaptation_84_1x1_tests"] = tests
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
        raise RuntimeError("Phase 8.4 refused to change the approved technical Master")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity_pointers"] = {"before": before, "after": after}
    return record
