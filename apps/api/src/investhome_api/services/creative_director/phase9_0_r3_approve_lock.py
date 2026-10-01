"""Phase 9.0-R3 — human-approve and lock Premium Campaign 02.

Status / library finalization only. No new pixels. No Master 03. No format work.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
)
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_compose import CENTERING, GRADE, ORNEK_FILENAME, SUNSET_ASSET_ID, SUNSET_FILENAME
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r1_compose import CITY_TOP, CONCEPT, PAGE_RIGHT, PARENT_MASTER_02_ASSET, SPIRE_X
from investhome_api.services.creative_director.phase9_0_r2_compose import PARENT_R1_ASSET
from investhome_api.services.creative_director.phase9_0_r2_master import _HISTORY_KEYS as _H90R2
from investhome_api.services.creative_director.phase9_0_r2_master import _preserve as _preserve_90r2
from investhome_api.services.creative_director.phase9_0_r2_master import _restore_history as _restore_90r2
from investhome_api.services.creative_director.project_creative_master_library import (
    activate_locked_revision_contract,
    count_approved_premium,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_90_R3 = "phase9_0_r3_premium_master_02_human_approval"
CREATIVE_CONCEPT = "THE TEMPLE RISES THROUGH THE EDITORIAL PAGE"
APPROVED_ASSET_02 = "48819baf-c2a9-43e0-9c27-a55deb15efdd"
FORBIDDEN_ASSETS = frozenset({PARENT_MASTER_02_ASSET, PARENT_R1_ASSET, APPROVED_ASSET_ID})
NEXT_PHASE = "9.1 PREMIUM MASTER 03"
_HISTORY_KEYS = _H90R2 + (("premium_master_90_r2_tests", "quality90r2"),)

LOCKED_IDENTITY_02 = {
    "photo_filename": SUNSET_FILENAME,
    "photo_asset_id": SUNSET_ASSET_ID,
    "photo_crop_centering": list(CENTERING),
    "photo_grade": dict(GRADE),
    "logo_asset_id": LOCKED_LOGO_ASSET_ID,
    "headline": "ALIRKEN / KAZAN",
    "offer": "%35 LANSMAN AVANTAJI",
    "price_unit": "675.000 USD + 2+1 DAİRE",
    "cta": "PROJEYİ KEŞFET",
    "editorial_closure": "TARİHİN RUHU, GELECEĞİN DEĞERİ.",
    "typographic_system": "Cormorant Garamond + Source Sans 3",
    "composition_source": ORNEK_FILENAME,
    "creative_concept": CREATIVE_CONCEPT,
    "concept_name": CONCEPT["concept_name"],
    "spire_x": SPIRE_X,
    "page_right": PAGE_RIGHT,
    "city_top": CITY_TOP,
    "project_creative_rule": PROJECT_CREATIVE_RULE,
    "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
}


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_90r2(blob)
    preserved["quality90r2"] = list(blob.get("premium_master_90_r2_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_90r2(blob, preserved)
    blob["premium_master_90_r2_tests"] = preserved.get("quality90r2")


def _history_assets(master: dict[str, Any]) -> set[str]:
    return {str(item.get("asset_id")) for item in (master.get("visual_history") or []) if item.get("asset_id")}


def _premium_campaign_03_exists(library: dict[str, Any]) -> bool:
    for item in library.get("masters") or []:
        name = str(item.get("master_name") or "")
        if "Premium Campaign 03" in name or "Premium Master 03" in name:
            return True
    return False


def lock_premium_campaign_02(
    library: dict[str, Any],
    *,
    asset_id: str,
) -> dict[str, Any]:
    if str(asset_id) in FORBIDDEN_ASSETS:
        raise RuntimeError("refused to approve a rejected Master 02 or Master 01 visual")
    if str(asset_id) != APPROVED_ASSET_02:
        raise RuntimeError("approved asset must be the R2 artwork for 03-premium-master-02-r2.png")
    found = None
    for item in library.get("masters") or []:
        if str(item.get("master_id")) != TEMPLE_PREMIUM_MASTER_02_ID:
            continue
        found = item
        break
    if found is None:
        raise RuntimeError("Premium Campaign 02 is not in ProjectCreativeMasterLibraryV1")
    if str(found.get("visual_asset") or "") != APPROVED_ASSET_02:
        raise RuntimeError("Master 02 current visual is not the approved R2 artwork")
    history = _history_assets(found)
    if PARENT_MASTER_02_ASSET not in history:
        raise RuntimeError("rejected original Master 02 visual is missing from history")
    if PARENT_R1_ASSET not in history:
        raise RuntimeError("R1 visual is missing from history")
    rev = activate_locked_revision_contract()
    visual = dict(rev.get("VISUAL_REPLACE_ONLY") or {})
    visual["preserve"] = "Premium Campaign 02 identity"
    rev["VISUAL_REPLACE_ONLY"] = visual
    now = _now()
    found["approval_status"] = "HUMAN_APPROVED"
    found["human_review"] = "APPROVED"
    found["master_state"] = "LOCKED_MASTER"
    found["router_eligible"] = True
    found["approved_at"] = now
    found["canonical_format"] = "4:5"
    found["master_name"] = MASTER_NAME_02
    found["promoted"] = False
    found["visual_asset"] = APPROVED_ASSET_02
    found["locked_identity"] = LOCKED_IDENTITY_02
    found["revision_contract"] = rev
    found["creative_concept"] = CREATIVE_CONCEPT
    found["r1_concept"] = CONCEPT["concept_name"]
    fmt = dict(found.get("format_strategy") or {})
    fmt["canonical_format"] = "4:5"
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["note"] = "Canonical 4:5 locked. Format adaptation is not executed in Phase 9.0-R3."
    found["format_strategy"] = fmt
    found["creative_tags"] = [
        "PREMIUM_CAMPAIGN",
        "THE_TEMPLE",
        "HUMAN_APPROVED",
        "LOCKED_MASTER",
        "ORNEK_00012",
        "SUNSET",
        "R2",
        "SPIRE_CUT_PAGE",
    ]
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["next_production_phase"] = NEXT_PHASE
    library["note"] = (
        "Premium Campaign 01 and Premium Campaign 02 are HUMAN_APPROVED LOCKED_MASTER. "
        "Master 03 is not created."
    )
    return found


def generate_phase9_0_r3_approve_lock_premium_master_02(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = user
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
        raise RuntimeError("Phase 9.0-R3 requires ProjectCreativeMasterLibraryV1")

    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01 is None:
        raise RuntimeError("Phase 9.0-R3 requires locked Premium Campaign 01")
    master_01_snapshot = json.loads(json.dumps(_jsonable(master_01), default=str))

    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    if master_02 is None:
        raise RuntimeError("Phase 9.0-R3 requires existing Premium Campaign 02")
    if str(master_02.get("visual_asset") or "") in FORBIDDEN_ASSETS:
        raise RuntimeError("refused to register the rejected original Master 02 or R1 as approved")
    if _premium_campaign_03_exists(library):
        raise RuntimeError("Phase 9.0-R3 must not find or create Master 03")
    version_before = master_02.get("version")
    visual_before = str(master_02.get("visual_asset") or "")

    approved = lock_premium_campaign_02(library, asset_id=visual_before)
    if str(approved.get("visual_asset")) != APPROVED_ASSET_02 or str(approved.get("visual_asset")) != visual_before:
        raise RuntimeError("Phase 9.0-R3 refused to replace the approved R2 visual")
    if approved.get("version") != version_before:
        raise RuntimeError("Phase 9.0-R3 must not bump version via regeneration")

    master_01_after = next((item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snapshot, default=str):
        raise RuntimeError("Phase 9.0-R3 refused to change Master 01")
    if _premium_campaign_03_exists(library):
        raise RuntimeError("Phase 9.0-R3 refused to create Master 03")
    if count_approved_premium(library) != 2:
        raise RuntimeError("Phase 9.0-R3 expected two HUMAN_APPROVED Premium Masters")
    if approved["router_eligible"] is not True:
        raise RuntimeError("approved Master 02 must be router eligible")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 9.0-R3 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    history = _history_assets(approved)
    fmt = approved.get("format_strategy") or {}
    format_ok = fmt.get("implemented") is False and fmt.get("rendered_adaptations") is False
    structural = (
        approved["approval_status"] == "HUMAN_APPROVED"
        and approved["master_state"] == "LOCKED_MASTER"
        and approved["router_eligible"] is True
        and str(approved["visual_asset"]) == APPROVED_ASSET_02
        and PARENT_MASTER_02_ASSET in history
        and PARENT_R1_ASSET in history
        and APPROVED_ASSET_02 not in history
        and format_ok
        and provider_call_count() == 0
    )
    status = "PREMIUM_MASTER_02_HUMAN_APPROVED" if structural else "PREMIUM_MASTER_02_NOT_READY"

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_90_R3,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_02,
        "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "asset_id": APPROVED_ASSET_02,
        "approval_status": approved["approval_status"],
        "master_state": approved["master_state"],
        "router_eligible": approved["router_eligible"],
        "creative_concept": CREATIVE_CONCEPT,
        "creative_concept_changed": False,
        "visual_regenerated": False,
        "rejected_master_02_history_preserved": PARENT_MASTER_02_ASSET in history,
        "r1_history_preserved": PARENT_R1_ASSET in history,
        "locked_identity": LOCKED_IDENTITY_02,
        "revision_contract": approved.get("revision_contract"),
        "format_strategy": fmt,
        "gpt_image_calls": provider_call_count(),
        "new_master_created": False,
        "master_03_created": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "master_01_changed": False,
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
        "next_phase": NEXT_PHASE,
        "language": language,
    }
    tests = list(blob.get("premium_master_90_r3_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["premium_master_90_r3_tests"] = tests
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
    record["identity"] = {"before": before, "after": after}
    record["approved_master"] = json.loads(json.dumps(_jsonable(approved), default=str))
    record["library_state"] = {
        "human_approved_premium_count": count_approved_premium(library),
        "master_01": {
            "master_id": APPROVED_MASTER_ID,
            "approval_status": master_01_after.get("approval_status"),
            "master_state": master_01_after.get("master_state"),
            "visual_asset": master_01_after.get("visual_asset"),
            "router_eligible": master_01_after.get("router_eligible"),
        },
        "master_02": {
            "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
            "approval_status": approved.get("approval_status"),
            "master_state": approved.get("master_state"),
            "visual_asset": approved.get("visual_asset"),
            "router_eligible": approved.get("router_eligible"),
        },
        "master_03": "NOT CREATED",
        "next_production_phase": library.get("next_production_phase"),
    }
    return record
