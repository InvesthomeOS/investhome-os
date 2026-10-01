"""Phase 8.2-R1 — typographic / commercial polish. DRAFT. No promotion."""

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
from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_QUICK, route_creative
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
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72
from investhome_api.services.creative_director.phase8_2_compose import render_pair
from investhome_api.services.creative_director.phase8_2_human_selected_master import (
    TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID,
    _format_strategy,
    build_semantic_spec,
)
from investhome_api.services.creative_director.phase8_2_human_selected_master import _HISTORY_KEYS as _H82
from investhome_api.services.creative_director.phase8_2_human_selected_master import _preserve as _preserve_82
from investhome_api.services.creative_director.phase8_2_human_selected_master import _restore_history as _restore_82
from investhome_api.services.creative_director.phase8_2_r1_compose import (
    DAY003_ASSET_ID,
    DAY003_FILENAME,
    PARENT_ASSET_ID_82,
    PARENT_MASTER_ID_82,
    crop_locked_day003,
    overlay_polish,
    preservation_validation,
    r1_plan,
    render_hierarchy_board,
    render_preservation_board,
    render_r1_type,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    bootstrap_temple_library,
    count_approved_premium,
    empty_master,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_82_R1 = "phase8_2_r1_premium_master_final_polish"
MASTER_NAME_R1 = "The Temple — Premium Campaign 01 — R1"
TEMPLE_PREMIUM_MASTER_01_R1_ID = str(
    uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-01:ornek-00001:r1")
)
_HISTORY_KEYS = _H82 + (("human_selected_premium_master_82_tests", "quality82"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_82(blob)
    preserved["quality82"] = list(blob.get("human_selected_premium_master_82_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_82(blob, preserved)
    blob["human_selected_premium_master_82_tests"] = preserved.get("quality82")


def _upsert_master(library: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    kept = [item for item in list(library.get("masters") or []) if str(item.get("master_id")) != str(master["master_id"])]
    library["masters"] = kept
    return add_master(library, master)


def generate_phase8_2_r1_premium_master_polish(
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
        library = bootstrap_temple_library()

    parent = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_ASSET_ID_82)))).convert("RGB")
    day003 = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    photo, transform = crop_locked_day003(day003)
    plan = r1_plan()
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    rendered = render_r1_type(photo=photo, logo_bytes=logo_bytes, plan=plan)
    r1_image = overlay_polish(parent, rendered, plan)
    validation = preservation_validation(parent, r1_image, plan)

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(r1_image),
        content_type="image/png",
        campaign_mode="project-premium-master-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 8.2-R1 THE TEMPLE PREMIUM CAMPAIGN 01 TYPOGRAPHIC POLISH DRAFT",
    )
    asset_id = str(asset.id)
    spec = build_semantic_spec(visual_asset_id=asset_id, photo_id=DAY003_ASSET_ID, plan=plan)
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_01_R1_ID
    spec["candidate_id"] = "PREMIUM_CAMPAIGN_01_R1"
    spec["parent_master_id"] = PARENT_MASTER_ID_82
    spec["polish"] = "typographic_commercial_hierarchy_only"
    revision = revision_readiness_72()
    revision["VISUAL_REPLACE_ONLY"]["note"] = (
        "Replace PROJECT_PHOTO_OBJECT then recalculate natural negative space, text territory, "
        "crop, and contrast. Do not swap pixels into the same crop."
    )
    fmt = _format_strategy()

    master_record = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_R1,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=asset_id,
        master_id=TEMPLE_PREMIUM_MASTER_01_R1_ID,
    )
    master_record["router_eligible"] = False
    master_record["human_selected_source"] = "ORNEK_00001.jpg"
    master_record["parent_master_id"] = PARENT_MASTER_ID_82
    master_record["parent_asset_id"] = PARENT_ASSET_ID_82
    master_record["semantic_spec"] = spec
    master_record["revision_contract"] = revision
    master_record["format_strategy"] = fmt
    master_record["photo_object_source"] = DAY003_ASSET_ID
    master_record["photo_compatibility"] = [DAY003_FILENAME]
    master_record["logo_asset_id"] = LOCKED_LOGO_ASSET_ID
    master_record["promoted"] = False
    master_record["research"] = False
    master_record["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00001", "R1"]
    master_record["campaign_tags"] = ["LANSMAN", "ALIRKEN_KAZAN"]
    _upsert_master(library, master_record)

    parent_row = next((item for item in library["masters"] if str(item.get("master_id")) == PARENT_MASTER_ID_82), None)
    if parent_row is None:
        raise RuntimeError("Phase 8.2-R1 requires the parent Premium Master")
    if str(master_record["master_id"]) == PARENT_MASTER_ID_82:
        raise RuntimeError("Phase 8.2-R1 must not overwrite the parent master_id")
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    router_check = route_creative(user_text="Temple için reklam hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    structural = (
        validation.get("OVERALL_MASTER_IDENTITY_PRESERVED") == "PASS"
        and master_record["approval_status"] == "DRAFT"
        and master_record["router_eligible"] is False
        and router_check["route"] == ROUTE_QUICK
        and provider_call_count() == 0
        and str(parent_row.get("visual_asset")) == PARENT_ASSET_ID_82
    )
    status = "PREMIUM_MASTER_FINAL_PENDING_HUMAN_APPROVAL" if structural else "PREMIUM_MASTER_NOT_READY"

    images = {
        "parent": parent,
        "r1": r1_image,
        "pair": render_pair(parent, r1_image, "PARENT  —  composition approved", "R1  —  typographic polish", "03  PARENT vs R1"),
        "hierarchy": render_hierarchy_board(r1_image, plan),
        "preservation": render_preservation_board(parent, r1_image, validation),
        "review": render_pair(
            parent,
            r1_image,
            "PARENT  9571efdf…",
            "THE TEMPLE — PREMIUM CAMPAIGN 01 — R1  DRAFT",
            "06  HUMAN REVIEW BOARD  —  final polish pending approval",
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_82_R1,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_R1,
        "master_id": TEMPLE_PREMIUM_MASTER_01_R1_ID,
        "asset_id": asset_id,
        "parent_master_id": PARENT_MASTER_ID_82,
        "parent_asset_id": PARENT_ASSET_ID_82,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "photo_asset_id": DAY003_ASSET_ID,
        "photo_filename": DAY003_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "composition_plan": plan,
        "semantic_spec": spec,
        "revision_contract": revision,
        "format_strategy": fmt,
        "preservation_validation": validation,
        "project_reality_validation": {
            "REAL_PROJECT_PHOTO": "PASS",
            "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
            "ARCHITECTURE_FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
            "REAL_TEMPLE_LOGO": "PASS",
            "DUPLICATE_TEMPLE_WORDMARK": "NO",
            "transform": transform,
        },
        "gpt_image_calls": provider_call_count(),
        "new_master_created": True,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "required_copy": {**REQUIRED_FACTS, "location": "WASHINGTON D.C.", "editorial": APPROVED_BOTTOM_COPY},
        "human_approval": "PENDING",
        "language": language,
        "router_check": router_check["route"],
    }
    tests = list(blob.get("premium_master_82_r1_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["premium_master_82_r1_tests"] = tests
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
        raise RuntimeError("Phase 8.2-R1 refused to change the approved technical Master")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
