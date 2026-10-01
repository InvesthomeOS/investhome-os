"""Phase 9.1-R2 — human-approve and lock Premium Campaign 03.

Status / library finalization only. No new pixels. No Stage 2. No format work.
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
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_compose import (
    ARCHITECTURE_ASSET_ID,
    ARCHITECTURE_FILENAME,
    INTERIOR_ASSET_ID,
    INTERIOR_FILENAME,
    ORNEK_FILENAME,
)
from investhome_api.services.creative_director.phase9_1_master import MASTER_NAME_03, TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r1_compose import (
    ARCHITECTURE_CENTERING,
    ARCHITECTURE_GRADE,
    CEILING_FADE,
    CONCEPT_R1,
    INTERIOR_CENTERING,
    INTERIOR_GRADE,
    OPEN_BOT_X,
    OPEN_FLOOR,
    OPEN_TOP_X,
    PARENT_MASTER_03_ASSET,
)
from investhome_api.services.creative_director.phase9_1_r1_master import _HISTORY_KEYS as _H91R1
from investhome_api.services.creative_director.phase9_1_r1_master import _preserve as _preserve_91r1
from investhome_api.services.creative_director.phase9_1_r1_master import _restore_history as _restore_91r1
from investhome_api.services.creative_director.project_creative_master_library import (
    activate_locked_revision_contract,
    count_approved_premium,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_91_R2 = "phase9_1_r2_premium_master_03_human_approval"
CREATIVE_CONCEPT = "LOOKING_CHAMBER"
APPROVED_ASSET_03 = "7ccf1c4b-26b8-4356-a774-a60e61d5687a"
FORBIDDEN_ASSETS = frozenset({PARENT_MASTER_03_ASSET, APPROVED_ASSET_ID, APPROVED_ASSET_02})
NEXT_PHASE = "STAGE 2 — NATURAL-LANGUAGE REVISION"
STAGE_1_STATUS = "COMPLETE"
_HISTORY_KEYS = _H91R1 + (("premium_master_91_r1_tests", "quality91r1"),)

LOCKED_IDENTITY_03 = {
    "interior_filename": INTERIOR_FILENAME,
    "interior_asset_id": INTERIOR_ASSET_ID,
    "architecture_filename": ARCHITECTURE_FILENAME,
    "architecture_asset_id": ARCHITECTURE_ASSET_ID,
    "interior_crop_centering": list(INTERIOR_CENTERING),
    "architecture_crop_centering": list(ARCHITECTURE_CENTERING),
    "interior_grade": dict(INTERIOR_GRADE),
    "architecture_grade": dict(ARCHITECTURE_GRADE),
    "open_top_x": OPEN_TOP_X,
    "open_bot_x": OPEN_BOT_X,
    "open_floor": OPEN_FLOOR,
    "ceiling_fade": CEILING_FADE,
    "logo_asset_id": LOCKED_LOGO_ASSET_ID,
    "headline": "ALIRKEN / KAZAN",
    "offer": "%35 LANSMAN AVANTAJI",
    "price_unit": "675.000 USD + 2+1 DAİRE",
    "cta": "PROJEYİ KEŞFET",
    "editorial_closure": APPROVED_BOTTOM_COPY,
    "location": "WASHINGTON D.C.",
    "typographic_system": "Cormorant Garamond + Source Sans 3",
    "composition_source": ORNEK_FILENAME,
    "creative_concept": CREATIVE_CONCEPT,
    "concept_name": CONCEPT_R1["concept_name"],
    "looking_chamber_mechanism": CONCEPT_R1["mechanism_sentence"],
    "project_creative_rule": PROJECT_CREATIVE_RULE,
    "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
}

REALITY = {
    "REAL_INTERIOR": "PASS",
    "REAL_EXTERIOR": "PASS",
    "ARCHITECTURE_FIDELITY": 10,
    "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
    "REAL_TEMPLE_LOGO": "PASS",
    "FINANCIAL_COPY": "PASS",
}


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_91r1(blob)
    preserved["quality91r1"] = list(blob.get("premium_master_91_r1_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_91r1(blob, preserved)
    blob["premium_master_91_r1_tests"] = preserved.get("quality91r1")


def _history_assets(master: dict[str, Any]) -> set[str]:
    return {str(item.get("asset_id")) for item in (master.get("visual_history") or []) if item.get("asset_id")}


def lock_premium_campaign_03(
    library: dict[str, Any],
    *,
    asset_id: str,
) -> dict[str, Any]:
    if str(asset_id) in FORBIDDEN_ASSETS:
        raise RuntimeError("refused to approve a rejected Master 03 or another Master's visual")
    if str(asset_id) != APPROVED_ASSET_03:
        raise RuntimeError("approved asset must be the R1 artwork for 06-premium-master-03-r1.png")
    found = None
    for item in library.get("masters") or []:
        if str(item.get("master_id")) != TEMPLE_PREMIUM_MASTER_03_ID:
            continue
        found = item
        break
    if found is None:
        raise RuntimeError("Premium Campaign 03 is not in ProjectCreativeMasterLibraryV1")
    if str(found.get("visual_asset") or "") != APPROVED_ASSET_03:
        raise RuntimeError("Master 03 current visual is not the approved R1 artwork")
    history = _history_assets(found)
    if PARENT_MASTER_03_ASSET not in history:
        raise RuntimeError("rejected original Master 03 visual is missing from history")
    rev = activate_locked_revision_contract()
    visual = dict(rev.get("VISUAL_REPLACE_ONLY") or {})
    visual["preserve"] = "Premium Campaign 03 identity"
    rev["VISUAL_REPLACE_ONLY"] = visual
    now = _now()
    found["approval_status"] = "HUMAN_APPROVED"
    found["human_review"] = "APPROVED"
    found["master_state"] = "LOCKED_MASTER"
    found["router_eligible"] = True
    found["approved_at"] = now
    found["canonical_format"] = "4:5"
    found["master_name"] = MASTER_NAME_03
    found["promoted"] = False
    found["visual_asset"] = APPROVED_ASSET_03
    found["locked_identity"] = LOCKED_IDENTITY_03
    found["revision_contract"] = rev
    found["creative_concept"] = CREATIVE_CONCEPT
    found["r1_concept"] = CREATIVE_CONCEPT
    fmt = dict(found.get("format_strategy") or {})
    fmt["canonical_format"] = "4:5"
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["note"] = "Canonical 4:5 locked. Format adaptation is not executed in Phase 9.1-R2. Stage 2 is not executed."
    found["format_strategy"] = fmt
    found["creative_tags"] = [
        "PREMIUM_CAMPAIGN",
        "THE_TEMPLE",
        "HUMAN_APPROVED",
        "LOCKED_MASTER",
        "ORNEK_00006",
        "LOOKING_CHAMBER",
        "R1",
    ]
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["creative_family_count"] = count_approved_premium(library)
    library["premium_creative_master_library"] = "COMPLETE"
    library["stage_1"] = STAGE_1_STATUS
    library["stage_2_executed"] = False
    library["next_production_phase"] = NEXT_PHASE
    library["note"] = (
        "Stage 1 Premium Creative Master Library is complete: Masters 01, 02, and 03 are "
        "HUMAN_APPROVED LOCKED_MASTER. Stage 2 Natural-Language Revision is not executed."
    )
    return found


def generate_phase9_1_r2_approve_lock_premium_master_03(
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
        raise RuntimeError("Phase 9.1-R2 requires ProjectCreativeMasterLibraryV1")

    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None:
        raise RuntimeError("Phase 9.1-R2 requires locked Premium Campaign 01")
    if master_02 is None:
        raise RuntimeError("Phase 9.1-R2 requires locked Premium Campaign 02")
    if master_03 is None:
        raise RuntimeError("Phase 9.1-R2 requires existing Premium Campaign 03")
    if master_01.get("approval_status") != "HUMAN_APPROVED" or master_01.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 9.1-R2 requires Master 01 HUMAN_APPROVED LOCKED_MASTER")
    if master_02.get("approval_status") != "HUMAN_APPROVED" or master_02.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("Phase 9.1-R2 requires Master 02 HUMAN_APPROVED LOCKED_MASTER")
    if str(master_02.get("visual_asset") or "") != APPROVED_ASSET_02:
        raise RuntimeError("Phase 9.1-R2 refused to change Master 02 visual")
    master_01_snapshot = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snapshot = json.loads(json.dumps(_jsonable(master_02), default=str))
    if str(master_03.get("visual_asset") or "") in FORBIDDEN_ASSETS:
        raise RuntimeError("refused to register the rejected original Master 03 as approved")
    if str(master_03.get("visual_asset") or "") != APPROVED_ASSET_03:
        raise RuntimeError("Phase 9.1-R2 expected the R1 artwork as current Master 03 visual")
    version_before = master_03.get("version")
    visual_before = str(master_03.get("visual_asset") or "")

    approved = lock_premium_campaign_03(library, asset_id=visual_before)
    if str(approved.get("visual_asset")) != APPROVED_ASSET_03 or str(approved.get("visual_asset")) != visual_before:
        raise RuntimeError("Phase 9.1-R2 refused to replace the approved R1 visual")
    if approved.get("version") != version_before:
        raise RuntimeError("Phase 9.1-R2 must not bump version via regeneration")

    master_01_after = next((item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02_after = next((item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snapshot, default=str):
        raise RuntimeError("Phase 9.1-R2 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snapshot, default=str):
        raise RuntimeError("Phase 9.1-R2 refused to change Master 02")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 9.1-R2 expected three HUMAN_APPROVED Premium Masters")
    if approved["router_eligible"] is not True:
        raise RuntimeError("approved Master 03 must be router eligible")
    if library.get("premium_creative_master_library") != "COMPLETE":
        raise RuntimeError("Stage 1 library must be marked COMPLETE")
    if library.get("stage_2_executed") is not False:
        raise RuntimeError("Phase 9.1-R2 must not execute Stage 2")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 9.1-R2 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    history = _history_assets(approved)
    fmt = approved.get("format_strategy") or {}
    format_ok = fmt.get("implemented") is False and fmt.get("rendered_adaptations") is False
    structural = (
        approved["approval_status"] == "HUMAN_APPROVED"
        and approved["master_state"] == "LOCKED_MASTER"
        and approved["router_eligible"] is True
        and str(approved["visual_asset"]) == APPROVED_ASSET_03
        and PARENT_MASTER_03_ASSET in history
        and APPROVED_ASSET_03 not in history
        and format_ok
        and provider_call_count() == 0
        and library.get("premium_creative_master_library") == "COMPLETE"
        and count_approved_premium(library) == 3
    )
    status = "PREMIUM_MASTER_03_HUMAN_APPROVED" if structural else "PREMIUM_MASTER_03_NOT_READY"

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_91_R2,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_03,
        "master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "asset_id": APPROVED_ASSET_03,
        "approval_status": approved["approval_status"],
        "master_state": approved["master_state"],
        "router_eligible": approved["router_eligible"],
        "creative_concept": CREATIVE_CONCEPT,
        "creative_concept_changed": False,
        "visual_regenerated": False,
        "rejected_master_03_history_preserved": PARENT_MASTER_03_ASSET in history,
        "locked_identity": LOCKED_IDENTITY_03,
        "revision_contract": approved.get("revision_contract"),
        "format_strategy": fmt,
        "project_reality_validation": REALITY,
        "gpt_image_calls": provider_call_count(),
        "new_master_created": False,
        "master_04_created": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "stage_1": STAGE_1_STATUS,
        "stage_2_executed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "creative_family_count": library.get("creative_family_count"),
        "premium_creative_master_library": library.get("premium_creative_master_library"),
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
        "next_phase": NEXT_PHASE,
        "language": language,
    }
    tests = list(blob.get("premium_master_91_r2_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["premium_master_91_r2_tests"] = tests
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
        "premium_creative_master_library": library.get("premium_creative_master_library"),
        "human_approved_premium_count": count_approved_premium(library),
        "creative_family_count": library.get("creative_family_count"),
        "stage_1": library.get("stage_1"),
        "stage_2_executed": library.get("stage_2_executed"),
        "master_01": {
            "master_id": APPROVED_MASTER_ID,
            "master_name": master_01_after.get("master_name"),
            "approval_status": master_01_after.get("approval_status"),
            "master_state": master_01_after.get("master_state"),
            "visual_asset": master_01_after.get("visual_asset"),
            "router_eligible": master_01_after.get("router_eligible"),
        },
        "master_02": {
            "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
            "master_name": MASTER_NAME_02,
            "approval_status": master_02_after.get("approval_status"),
            "master_state": master_02_after.get("master_state"),
            "visual_asset": master_02_after.get("visual_asset"),
            "router_eligible": master_02_after.get("router_eligible"),
        },
        "master_03": {
            "master_id": TEMPLE_PREMIUM_MASTER_03_ID,
            "master_name": MASTER_NAME_03,
            "approval_status": approved.get("approval_status"),
            "master_state": approved.get("master_state"),
            "visual_asset": approved.get("visual_asset"),
            "router_eligible": approved.get("router_eligible"),
            "creative_concept": CREATIVE_CONCEPT,
        },
        "next_production_phase": library.get("next_production_phase"),
    }
    return record
