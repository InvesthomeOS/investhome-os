"""Phase 8.3 — approve and lock the first The Temple Project Premium Master.

No new pixels. No cover change. No R2.
"""

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
from investhome_api.services.creative_director.creative_master_router_v2 import (
    PRICE_EDIT_ONLY,
    ROUTE_PREMIUM_MASTER,
    ROUTE_QUICK,
    ROUTE_REVISION,
    VISUAL_REPLACE_ONLY,
    route_creative,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
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
    _read_bytes,
)
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_1_first_premium_master import TEMPLE_PREMIUM_MASTER_01_ID as ARCHIVED_81_MASTER_ID
from investhome_api.services.creative_director.phase8_2_r1_compose import (
    DAY003_ASSET_ID,
    DAY003_FILENAME,
    LOCKED_CENTERING,
    LOCKED_GRADE,
    PARENT_ASSET_ID_82,
    PARENT_MASTER_ID_82,
)
from investhome_api.services.creative_director.phase8_2_r1_polish import TEMPLE_PREMIUM_MASTER_01_R1_ID
from investhome_api.services.creative_director.phase8_2_r1_polish import _HISTORY_KEYS as _H82R1
from investhome_api.services.creative_director.phase8_2_r1_polish import _preserve as _preserve_82r1
from investhome_api.services.creative_director.phase8_2_r1_polish import _restore_history as _restore_82r1
from investhome_api.services.creative_director.project_creative_master_library import (
    approve_and_lock_master,
    archive_superseded_draft,
    bootstrap_temple_library,
    count_approved_premium,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_83 = "phase8_3_approve_lock_first_premium_master"
APPROVED_MASTER_NAME = "The Temple — Premium Campaign 01"
APPROVED_MASTER_ID = TEMPLE_PREMIUM_MASTER_01_R1_ID
APPROVED_ASSET_ID = "a6c87a3c-835e-4e8b-9179-b247720fe61b"
_HISTORY_KEYS = _H82R1 + (("premium_master_82_r1_tests", "quality82r1"),)

LOCKED_IDENTITY = {
    "photo_filename": DAY003_FILENAME,
    "photo_asset_id": DAY003_ASSET_ID,
    "photo_crop_centering": list(LOCKED_CENTERING),
    "photo_grade": dict(LOCKED_GRADE),
    "logo_asset_id": LOCKED_LOGO_ASSET_ID,
    "headline": "ALIRKEN / KAZAN",
    "offer": "%35 LANSMAN AVANTAJI",
    "price_unit": "675.000 USD + 2+1 DAİRE",
    "cta": "PROJEYİ KEŞFET",
    "editorial_closure": "TARİHİN RUHU, GELECEĞİN DEĞERİ.",
    "typographic_system": "Cormorant Garamond + Source Sans 3",
    "composition_source": "ORNEK_00001",
    "project_creative_rule": PROJECT_CREATIVE_RULE,
    "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
}


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_82r1(blob)
    preserved["quality82r1"] = list(blob.get("premium_master_82_r1_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_82r1(blob, preserved)
    blob["premium_master_82_r1_tests"] = preserved.get("quality82r1")


def smoke_routing(library: dict[str, Any]) -> dict[str, Any]:
    cases = (
        ("premium_ad", "Temple için premium reklam hazırla.", ROUTE_PREMIUM_MASTER, None),
        ("lansman_ad", "Temple için %35 lansman avantajı reklamı hazırla.", ROUTE_PREMIUM_MASTER, None),
        ("price", "Fiyatı değiştir.", ROUTE_REVISION, PRICE_EDIT_ONLY),
        ("visual", "Başka dış cephe görselini kullan.", ROUTE_REVISION, VISUAL_REPLACE_ONLY),
        ("alternative", "Bambaşka bir tasarım göster.", ROUTE_QUICK, None),
    )
    results = []
    all_pass = True
    for key, text, expected_route, expected_intent in cases:
        routed = route_creative(user_text=text, project_id=TEMPLE_PROJECT_ID, library=library)
        ok = routed["route"] == expected_route
        if expected_route == ROUTE_PREMIUM_MASTER:
            ok = ok and str(routed.get("selected_master_id")) == APPROVED_MASTER_ID
            ok = ok and routed.get("selected_master_name") == APPROVED_MASTER_NAME
        if expected_intent:
            ok = ok and routed.get("revision_intent") == expected_intent
        if expected_route == ROUTE_REVISION:
            ok = ok and routed.get("regenerate") is False
            ok = ok and routed.get("internal", {}).get("creates_child_revision") is True
            ok = ok and routed.get("internal", {}).get("never_overwrite_canonical") is True
        if expected_route == ROUTE_QUICK:
            ok = ok and routed.get("selected_master_id") is None
        results.append(
            {
                "key": key,
                "request": text,
                "expected_route": expected_route,
                "actual_route": routed.get("route"),
                "selected_master_id": routed.get("selected_master_id"),
                "selected_master_name": routed.get("selected_master_name"),
                "revision_intent": routed.get("revision_intent"),
                "pass": ok,
            }
        )
        all_pass = all_pass and ok
    return {"schema": "Phase83SmokeRoutingV1", "cases": results, "pass": all_pass}


def generate_phase8_3_approve_lock_first_premium_master(
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
        library = bootstrap_temple_library()

    approved = approve_and_lock_master(
        library,
        master_id=APPROVED_MASTER_ID,
        asset_id=APPROVED_ASSET_ID,
        master_name=APPROVED_MASTER_NAME,
        lock=LOCKED_IDENTITY,
    )
    if any(str(item.get("master_id")) == PARENT_MASTER_ID_82 for item in library.get("masters") or []):
        archive_superseded_draft(library, master_id=PARENT_MASTER_ID_82, superseded_by=APPROVED_MASTER_ID)
    archived_81 = next((item for item in library["masters"] if str(item.get("master_id")) == ARCHIVED_81_MASTER_ID), None)
    if archived_81 is not None and archived_81.get("approval_status") != "ARCHIVED":
        raise RuntimeError("Phase 8.3 refused to un-archive the rejected Phase 8.1 Master")
    if str(approved.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 8.3 refused to replace the approved visual")
    draft_r1 = [
        item
        for item in library["masters"]
        if str(item.get("master_id")) == APPROVED_MASTER_ID and item.get("approval_status") == "DRAFT"
    ]
    if draft_r1:
        raise RuntimeError("obsolete DRAFT of the approved R1 remains")
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    routing = smoke_routing(library)
    premium_ok = all(case["pass"] for case in routing["cases"] if case["expected_route"] == ROUTE_PREMIUM_MASTER)
    revision_ok = all(case["pass"] for case in routing["cases"] if case["expected_route"] == ROUTE_REVISION)
    alt_ok = all(case["pass"] for case in routing["cases"] if case["key"] == "alternative")
    fmt = approved.get("format_strategy") or {}
    format_ok = fmt.get("canonical_format") == "4:5" and fmt.get("implemented") is False and fmt.get("rendered_adaptations") is False
    structural = (
        approved["approval_status"] == "HUMAN_APPROVED"
        and approved["master_state"] == "LOCKED_MASTER"
        and approved["router_eligible"] is True
        and count_approved_premium(library) == 1
        and routing["pass"]
        and provider_call_count() == 0
        and format_ok
    )
    status = "FIRST_PROJECT_PREMIUM_MASTER_APPROVED" if structural else "PREMIUM_MASTER_NOT_READY"

    master_png = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_ID)))).convert("RGB")
    library_rows = [
        f"{item.get('approval_status')}  {item.get('master_type')}  {item.get('master_name')}  {item.get('master_id')}"
        for item in library.get("masters") or []
        if item.get("approval_status") in {"HUMAN_APPROVED", "DRAFT"}
        or str(item.get("master_id")) in {APPROVED_MASTER_ID, PARENT_MASTER_ID_82, ARCHIVED_81_MASTER_ID}
    ]
    images = {
        "approved": master_png,
        "library": _text_board(
            "02  MASTER LIBRARY STATE",
            [
                f"HUMAN_APPROVED PREMIUM MASTERS  {count_approved_premium(library)}",
                f"APPROVED  {APPROVED_MASTER_NAME}  {APPROVED_MASTER_ID}",
                f"ASSET  {APPROVED_ASSET_ID}",
                f"STATE  {approved.get('master_state')}  router_eligible={approved.get('router_eligible')}",
                f"8.1 rejected  {ARCHIVED_81_MASTER_ID}  {(archived_81 or {}).get('approval_status')}",
                f"8.2 parent draft  {PARENT_MASTER_ID_82}  superseded",
                *library_rows[:16],
            ],
        ),
        "router": _text_board(
            "03  ROUTER VALIDATION  —  smoke only, no assets created",
            [f"{c['key']}  {c['expected_route']}  actual={c['actual_route']}  {'PASS' if c['pass'] else 'FAIL'}  {c['request']}" for c in routing["cases"]],
        ),
        "revision": _text_board(
            "04  REVISION ROUTING  —  child revisions, never overwrite canonical",
            [
                f"PRICE  {approved['revision_contract']['PRICE_EDIT_ONLY']['status']}  child={approved['revision_contract']['PRICE_EDIT_ONLY']['creates_child_revision']}",
                f"COPY  {approved['revision_contract']['COPY_EDIT_ONLY']['status']}",
                f"VISUAL REPLACE  {approved['revision_contract']['VISUAL_REPLACE_ONLY']['status']}  target={approved['revision_contract']['VISUAL_REPLACE_ONLY']['allowed']}",
                "Fiyatı değiştir → MASTER_DERIVED_REVISION / PRICE_EDIT_ONLY",
                "Başka dış cephe görselini kullan → VISUAL_REPLACE_ONLY / PROJECT_PHOTO_OBJECT",
                f"revision smoke  {'PASS' if revision_ok else 'FAIL'}",
            ],
        ),
        "format": _text_board(
            "05  FORMAT READINESS  —  not rendered",
            [
                f"canonical  {fmt.get('canonical_format')}",
                "4:5 CANONICAL  1:1 READY  9:16 READY  16:9 READY",
                f"implemented={fmt.get('implemented')}  adaptations={fmt.get('rendered_adaptations')}",
                str(fmt.get("next_phase")),
            ],
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_83,
        "created_at": _now(),
        "status": status,
        "master_name": APPROVED_MASTER_NAME,
        "master_id": APPROVED_MASTER_ID,
        "asset_id": APPROVED_ASSET_ID,
        "approval_status": approved["approval_status"],
        "master_state": approved["master_state"],
        "router_eligible": approved["router_eligible"],
        "canonical_format": "4:5",
        "human_approved_premium_count": count_approved_premium(library),
        "locked_identity": LOCKED_IDENTITY,
        "revision_contract": approved.get("revision_contract"),
        "format_strategy": fmt,
        "router_validation": routing,
        "premium_routing": "PASS" if premium_ok and alt_ok else "FAIL",
        "revision_routing": "PASS" if revision_ok else "FAIL",
        "format_readiness": "PASS" if format_ok else "FAIL",
        "gpt_image_calls": provider_call_count(),
        "new_master_created": False,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "next_phase": "8.4 INTELLIGENT FORMAT ADAPTATION — 1:1",
        "language": language,
    }
    tests = list(blob.get("approve_lock_premium_master_83_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["approve_lock_premium_master_83_tests"] = tests
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
        raise RuntimeError("Phase 8.3 refused to change the approved technical Master")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    record["approved_master"] = json.loads(json.dumps(_jsonable(approved), default=str))
    record["library_state"] = {
        "human_approved_premium_count": count_approved_premium(library),
        "approved_master_id": APPROVED_MASTER_ID,
        "archived_81": (archived_81 or {}).get("approval_status"),
        "next_production_phase": library.get("next_production_phase"),
    }
    return record
