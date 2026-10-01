"""Phase 12.4 — approve and activate the UniLoft Last Units Premium Creative Family.

Does not generate pixels. Does not fabricate 16:9. Does not execute the price revision.
Does not alter the ORNEK_00013 family. Approved source assets stay byte-for-byte immutable.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_master_router_v2 import (
    FAMILY_WIDE_REVISION,
    classify_production_intent,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import _identity_slice
from investhome_api.services.creative_director.phase10_3_finalize import preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import (
    ASSET_1X1,
    ASSET_4X5,
    ASSET_9X16,
    CAMPAIGN_NAME,
    FAMILY_ID,
    FILE_1X1,
    FILE_4X5,
    FILE_9X16,
    MASTER_1X1_ID,
    MASTER_4X5_ID,
    MASTER_9X16_ID,
    PROJECT_NAME,
    _sha,
    load_ornek_catalog,
)
from investhome_api.services.creative_director.phase12_3_lock import format_master_inventory, render_family_board
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SKIP_TARGET_NOT_PRESENT,
    SQUARE,
    STATUS_FORMAT_MISSING,
    STORY_REEL,
    format_lock_map,
    lookup_format_master,
    resolve_family,
    route_family_wide_revision,
    route_format_request,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_12_4 = "phase12_4_first_production_premium_creative_family_approval"
STATUS = "PRODUCTION_PREMIUM_CREATIVE_FAMILY_APPROVED"
NEXT_PHASE = "12.5 FAMILY-WIDE NATURAL LANGUAGE REVISION PROOF"
UNILOFT_PROJECT_ID = "139a19cd-91a6-4d09-bc95-82bf0284154c"
UNILOFT_PROJECT_CODE = "PRJ-UNIL-002"
UNILOFT_PROJECT_NAME = "UniLoft"
PROJECT_SCOPE = "UNILOFT"
BRAND_ID = "INVESTHOME"
PHASE_12_5_COMMAND = (
    "Bu kampanyadaki 357.000 USD başlangıç fiyatını 375.000 USD yap, başka hiçbir şeyi değiştirme."
)
APPROVED_SOURCES = (
    (FEED_PORTRAIT, FILE_4X5, ASSET_4X5, MASTER_4X5_ID),
    (STORY_REEL, FILE_9X16, ASSET_9X16, MASTER_9X16_ID),
    (SQUARE, FILE_1X1, ASSET_1X1, MASTER_1X1_ID),
)

IDENTITY_LOCK = {
    "CAMPAIGN_IDENTITY": "LOCKED",
    "PROJECT_IDENTITY": PROJECT_SCOPE,
    "BRAND_IDENTITY": BRAND_ID,
    "APPROVED_IMAGERY": "LOCKED",
    "LOGOS": "LOCKED",
    "COMMERCIAL_MESSAGE_FAMILY": "LOCKED",
    "COLOR_SYSTEM": "LOCKED",
    "TYPOGRAPHIC_PERSONALITY": "LOCKED",
    "GRAPHIC_LANGUAGE": "LOCKED",
    "EACH_FORMAT_OWNS_COMPOSITION": True,
    "NO_FORMAT_DERIVES_LAYOUT_FROM_ANOTHER": True,
}

DO_NOT_CHANGE_IN_12_5 = (
    "photos",
    "headline",
    "delivery date",
    "rent",
    "last-units messaging",
    "logos",
    "colors",
    "composition",
    "other copy",
)


def family_identity_lock() -> dict[str, Any]:
    return {
        "schema": "PremiumCreativeFamilyIdentityLockV1",
        "FAMILY_ID": FAMILY_ID,
        "PROJECT": PROJECT_SCOPE,
        "PROJECT_ID": UNILOFT_PROJECT_ID,
        "PROJECT_CODE": UNILOFT_PROJECT_CODE,
        "PROJECT_NAME": UNILOFT_PROJECT_NAME,
        "BRAND": BRAND_ID,
        "locks": dict(IDENTITY_LOCK),
        "approved_format_masters": {
            FEED_PORTRAIT: FILE_4X5,
            STORY_REEL: FILE_9X16,
            SQUARE: FILE_1X1,
        },
        LANDSCAPE: "MISSING",
        "do_not_fabricate_16x9": True,
    }


def _price_territory(slot: dict[str, Any]) -> dict[str, Any]:
    territories = ((slot.get("SEMANTIC_MAP") or {}).get("territories") or [])
    price = next((item for item in territories if item.get("id") == "PRICE"), None)
    present = bool(price and price.get("present"))
    return {
        "format": slot.get("FORMAT"),
        "FORMAT_MASTER_ID": slot.get("FORMAT_MASTER_ID"),
        "SOURCE_FILENAME": slot.get("SOURCE_FILENAME"),
        "PRICE_present": present,
        "copy": None if not price else price.get("copy"),
        "BOUNDARY": None if not price else price.get("BOUNDARY"),
        "apply_independently": True,
        "do_not_derive_from_sibling": True,
        "do_not_invent_if_absent": not present,
    }


def apply_human_approval(family: dict[str, Any], *, approved_at: str | None = None) -> dict[str, Any]:
    if str(family.get("FAMILY_ID")) != FAMILY_ID:
        raise RuntimeError("Phase 12.4 can only approve the UniLoft Last Units family")
    now = approved_at or _now()
    family["approval_status"] = "HUMAN_APPROVED"
    family["human_review"] = "APPROVED"
    family["router_eligible"] = True
    family["production_status"] = "ACTIVE"
    family["approved_at"] = now
    family["family_type"] = "UNILOFT PROJECT"
    family["brand_id"] = BRAND_ID
    family["project_id"] = UNILOFT_PROJECT_ID
    family["project_code"] = UNILOFT_PROJECT_CODE
    family["project_name"] = PROJECT_NAME
    family["PROJECT_SCOPE"] = PROJECT_SCOPE
    family["cross_project_reuse"] = False
    family["identity_lock"] = dict(IDENTITY_LOCK)
    family["immutable_originals"] = True
    family["future_edit"] = "CREATE_REVISION_CHILD"
    family["overwrite_approved_masters"] = False
    formats = family.get("formats") or {}
    for fmt, filename, asset_id, master_id in APPROVED_SOURCES:
        slot = formats.get(fmt)
        if not isinstance(slot, dict):
            raise RuntimeError(f"Phase 12.4 expected a {fmt} format master")
        if str(slot.get("SOURCE_FILENAME")) != filename:
            raise RuntimeError(f"Phase 12.4 refused to approve a different {fmt} source")
        if str(slot.get("SOURCE_ASSET_ID")) != asset_id:
            raise RuntimeError(f"Phase 12.4 refused to approve a different {fmt} asset")
        if str(slot.get("FORMAT_MASTER_ID")) != master_id:
            raise RuntimeError(f"Phase 12.4 refused to change the {fmt} FORMAT_MASTER_ID")
        slot["APPROVAL_STATUS"] = "HUMAN_APPROVED"
        slot["router_eligible"] = True
        slot["production_status"] = "ACTIVE"
        slot["family_member"] = True
        slot["approved_at"] = now
        slot["PROJECT_SCOPE"] = PROJECT_SCOPE
        slot["BRAND_SCOPE"] = BRAND_ID
        slot["project_id"] = UNILOFT_PROJECT_ID
        slot["immutable"] = True
        slot["overwrite_forbidden"] = True
        slot["future_edit"] = "CREATE_REVISION_CHILD"
        slot["LOCK_MAP"] = {
            **format_lock_map(fmt=fmt, approval="HUMAN_APPROVED"),
            **dict(IDENTITY_LOCK),
            "composition": "OWNED_BY_THIS_FORMAT",
            "layout_geometry": "OWNED_BY_THIS_FORMAT",
            "do_not_rebuild_from_another_format": True,
        }
    landscape = formats.get(LANDSCAPE)
    if not isinstance(landscape, dict) or landscape.get("FORMAT_MASTER_ID") is not None:
        raise RuntimeError("Phase 12.4 must keep 16:9 MISSING")
    landscape["APPROVAL_STATUS"] = "MISSING"
    landscape["router_eligible"] = False
    landscape["production_status"] = "MISSING"
    landscape["family_member"] = False
    family["inventory"] = {
        FEED_PORTRAIT: "HUMAN_APPROVED",
        STORY_REEL: "HUMAN_APPROVED",
        SQUARE: "HUMAN_APPROVED",
        LANDSCAPE: "MISSING",
    }
    return family


def family_wide_revision_ready(family: dict[str, Any]) -> dict[str, Any]:
    classified = classify_production_intent(PHASE_12_5_COMMAND)
    wide = route_family_wide_revision(
        classified=classified,
        library={"premium_creative_families": [family]},
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
    )
    prices = [
        _price_territory(family["formats"][fmt])
        for fmt in (FEED_PORTRAIT, STORY_REEL, SQUARE)
    ]
    return {
        "schema": "FamilyWideRevisionReadyV1",
        "status": "READY",
        "executed": False,
        "command": PHASE_12_5_COMMAND,
        "classified_intent": classified.get("intent"),
        "expected_intent": FAMILY_WIDE_REVISION,
        "FAMILY_ID": FAMILY_ID,
        "apply_independently_to": [FEED_PORTRAIT, STORY_REEL, SQUARE],
        "price_territories": prices,
        "route": wide,
        "do_not_change": list(DO_NOT_CHANGE_IN_12_5),
        "do_not_derive_one_format_from_another": True,
        "do_not_fabricate_16x9": True,
        "approved_masters_remain_immutable": True,
        "note": (
            "Phase 12.4 does not execute this revision. Phase 12.5 must edit each format's own "
            "PRICE territory. ORNEK_00012 currently has no $357.000 PRICE plate; do not invent one."
        ),
    }


def routing_tests(family: dict[str, Any], library: dict[str, Any]) -> dict[str, Any]:
    looked = {
        fmt: lookup_format_master(family, fmt)
        for fmt in (FEED_PORTRAIT, STORY_REEL, SQUARE, LANDSCAPE)
    }
    resolved = resolve_family(library, family_id=FAMILY_ID)
    by_project = resolve_family(library, project_id=UNILOFT_PROJECT_ID)
    by_scope = resolve_family(library, project_id=PROJECT_SCOPE)
    temple = resolve_family(library, project_id=TEMPLE_PROJECT_ID)
    brand = resolve_family(library, brand_id=BRAND_ID)
    feed = route_format_request(
        classified={"target_format": FEED_PORTRAIT, "intent": "FORMAT_ADAPTATION"},
        library=library,
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
    )
    story = route_format_request(
        classified=classify_production_intent("Bunu Story yap."),
        library=library,
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
        current_master_id=MASTER_4X5_ID,
    )
    square = route_format_request(
        classified=classify_production_intent("Bunu 1:1 yap."),
        library=library,
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
    )
    landscape = route_format_request(
        classified=classify_production_intent("Bunu 16:9 yap."),
        library=library,
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
    )
    wide = family_wide_revision_ready(family)
    return {
        "schema": "Phase124RoutingTestsV1",
        "family_lookup": "PASS" if resolved and str(resolved.get("FAMILY_ID")) == FAMILY_ID else "FAIL",
        "family_lookup_by_project": "PASS" if by_project and str(by_project.get("FAMILY_ID")) == FAMILY_ID else "FAIL",
        "family_lookup_by_scope": "PASS" if by_scope and str(by_scope.get("FAMILY_ID")) == FAMILY_ID else "FAIL",
        "temple_does_not_receive_uniloft_family": "PASS" if temple is None else "FAIL",
        "brand_lookup_still_ornek": "PASS" if brand and str(brand.get("FAMILY_ID")) == ORNEK_FAMILY_ID else "FAIL",
        "feed_4x5": {
            "status": looked[FEED_PORTRAIT]["status"],
            "format_master_id": looked[FEED_PORTRAIT].get("format_master_id"),
            "source_asset_id": looked[FEED_PORTRAIT].get("source_asset_id"),
            "source_filename": FILE_4X5,
            "route": feed["route"],
            "selected_master_id": feed.get("selected_master_id"),
            "source_filename_routed": feed.get("source_filename"),
        },
        "story_9x16": {
            "status": looked[STORY_REEL]["status"],
            "format_master_id": looked[STORY_REEL].get("format_master_id"),
            "source_asset_id": looked[STORY_REEL].get("source_asset_id"),
            "source_filename": FILE_9X16,
            "route": story["route"],
            "selected_master_id": story.get("selected_master_id"),
            "source_filename_routed": story.get("source_filename"),
        },
        "square_1x1": {
            "status": looked[SQUARE]["status"],
            "format_master_id": looked[SQUARE].get("format_master_id"),
            "source_asset_id": looked[SQUARE].get("source_asset_id"),
            "source_filename": FILE_1X1,
            "route": square["route"],
            "selected_master_id": square.get("selected_master_id"),
            "source_filename_routed": square.get("source_filename"),
        },
        "landscape_16x9": {
            "status": looked[LANDSCAPE]["status"],
            "route": landscape["route"],
            "selected_master_id": landscape.get("selected_master_id"),
        },
        "family_wide_revision_ready": wide["status"],
        "family_wide_revision_executed": wide["executed"],
        "family_wide_targets": [item["format"] for item in wide["route"]["targets"]],
        "family_wide_missing": wide["route"]["missing_formats"],
    }


def generate_phase12_4_family_approval(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = user
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality121"] = list(blob.get("phase12_1_approval_tests") or [])
    preserved["quality122"] = list(blob.get("phase12_2_family_lock_tests") or [])
    preserved["quality123"] = list(blob.get("phase12_3_family_ingest_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.4 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.4 requires Masters 01–03 records to remain")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")
    approved_count_before = count_approved_premium(library)
    auto_before = library.get("autonomous_premium_generation")
    quick_before = library.get("ai_quick_creative_status")
    role_before = library.get("masters_01_03_role")
    ornek_before = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID),
        None,
    )
    if ornek_before is None:
        raise RuntimeError("Phase 12.4 requires the ORNEK_00013 Creative Family to remain")
    ornek_inventory_before = dict(ornek_before.get("inventory") or {})
    pending = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == FAMILY_ID),
        None,
    )
    if pending is None:
        raise RuntimeError("Phase 12.4 requires the Phase 12.3 UniLoft family to exist")
    if str(pending.get("approval_status")) != "PENDING HUMAN REVIEW":
        raise RuntimeError("Phase 12.4 expected PENDING HUMAN REVIEW before approval")

    catalog = load_ornek_catalog(db)
    sha_before = {}
    for fmt, filename, asset_id, _master_id in APPROVED_SOURCES:
        item = catalog.get(filename)
        if item is None or item["asset_id"] != asset_id:
            raise RuntimeError(f"Phase 12.4 could not load {filename}")
        live = _sha(_read_bytes(db, UUID(asset_id)))
        if live != item["sha256"]:
            raise RuntimeError(f"Phase 12.4 refused to mutate {filename}")
        slot = pending["formats"][fmt]
        if str(slot.get("SOURCE_SHA256")) != live:
            raise RuntimeError(f"Phase 12.4 refused to change the ingested {filename} bytes")
        sha_before[filename] = live

    semantic_before = {
        fmt: json.dumps(_jsonable(pending["formats"][fmt].get("SEMANTIC_MAP")), default=str)
        for fmt, _filename, _asset_id, _master_id in APPROVED_SOURCES
    }
    apply_human_approval(pending)
    library["phase12_4_status"] = STATUS
    library["pending_multiformat_family_id"] = None
    library["production_uniloft_family_id"] = FAMILY_ID
    library["next_production_phase"] = NEXT_PHASE

    ornek_after = next(item for item in library["premium_creative_families"] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID)
    approved = next(item for item in library["premium_creative_families"] if str(item.get("FAMILY_ID")) == FAMILY_ID)
    if dict(ornek_after.get("inventory") or {}) != ornek_inventory_before:
        raise RuntimeError("Phase 12.4 refused to alter the ORNEK_00013 inventory")
    if str(ornek_after.get("FAMILY_ID")) != ORNEK_FAMILY_ID:
        raise RuntimeError("Phase 12.4 refused to change ORNEK_00013 FAMILY_ID")
    if approved.get("production_status") != "ACTIVE" or approved.get("router_eligible") is not True:
        raise RuntimeError("Phase 12.4 expected an ACTIVE router-eligible family")
    if approved["inventory"][LANDSCAPE] != "MISSING" or approved["formats"][LANDSCAPE].get("FORMAT_MASTER_ID") is not None:
        raise RuntimeError("Phase 12.4 fabricated 16:9")
    for fmt, filename, asset_id, master_id in APPROVED_SOURCES:
        slot = approved["formats"][fmt]
        if slot.get("APPROVAL_STATUS") != "HUMAN_APPROVED" or slot.get("router_eligible") is not True:
            raise RuntimeError(f"Phase 12.4 expected {fmt} HUMAN_APPROVED")
        if str(slot.get("SOURCE_FILENAME")) != filename or str(slot.get("SOURCE_ASSET_ID")) != asset_id:
            raise RuntimeError(f"Phase 12.4 moved the {fmt} original")
        if str(slot.get("FORMAT_MASTER_ID")) != master_id:
            raise RuntimeError(f"Phase 12.4 changed the {fmt} FORMAT_MASTER_ID")
        if json.dumps(_jsonable(slot.get("SEMANTIC_MAP")), default=str) != semantic_before[fmt]:
            raise RuntimeError(f"Phase 12.4 mutated the {fmt} semantic map")
        live = _sha(_read_bytes(db, UUID(asset_id)))
        if live != sha_before[filename] or live != slot.get("SOURCE_SHA256"):
            raise RuntimeError(f"Phase 12.4 mutated {filename}")

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.4 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.4 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.4 refused to mutate Master 03")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.4 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.4 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.4 refused to change Master 03 visual")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None or parent.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.4 refused to keep ORNEK_00013 as the brand master visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Phase 12.4 must not create another library Premium Master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Phase 12.4 refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Phase 12.4 refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Phase 12.4 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.4 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.4 refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.4 refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.4 must not call GPT Image")

    tests = routing_tests(approved, library)
    ready = family_wide_revision_ready(approved)
    if tests["family_lookup"] != "PASS":
        raise RuntimeError("Phase 12.4 family lookup failed")
    if tests["feed_4x5"]["source_filename_routed"] != FILE_4X5 or tests["feed_4x5"]["selected_master_id"] != MASTER_4X5_ID:
        raise RuntimeError("Phase 12.4 feed routing did not return ORNEK_00012")
    if tests["story_9x16"]["source_filename_routed"] != FILE_9X16 or tests["story_9x16"]["selected_master_id"] != MASTER_9X16_ID:
        raise RuntimeError("Phase 12.4 story routing did not return ORNEK_00005")
    if tests["square_1x1"]["source_filename_routed"] != FILE_1X1 or tests["square_1x1"]["selected_master_id"] != MASTER_1X1_ID:
        raise RuntimeError("Phase 12.4 square routing did not return ORNEK_00003")
    if tests["landscape_16x9"]["status"] != STATUS_FORMAT_MISSING or tests["landscape_16x9"]["route"] != STATUS_FORMAT_MISSING:
        raise RuntimeError("Phase 12.4 must surface PREMIUM_FORMAT_MASTER_MISSING for 16:9")
    if ready["executed"] is not False or ready["classified_intent"] != FAMILY_WIDE_REVISION:
        raise RuntimeError("Phase 12.4 must prepare but not execute family-wide revision")
    if [item["format"] for item in ready["route"]["targets"]] != [STORY_REEL, SQUARE]:
        raise RuntimeError("Phase 12.4 PRICE family-wide targets must be 9:16 and 1:1")
    skipped_feed = next((item for item in ready["route"].get("skipped") or [] if item.get("format") == FEED_PORTRAIT), None)
    if skipped_feed is None or skipped_feed.get("reason") != SKIP_TARGET_NOT_PRESENT:
        raise RuntimeError("Phase 12.4 must skip 4:5 PRICE as TARGET_NOT_PRESENT")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["phase12_2_family_lock_tests"] = preserved.get("quality122")
    blob["phase12_3_family_ingest_tests"] = preserved.get("quality123")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    immutability = {
        "schema": "ApprovedFormatMasterImmutabilityV1",
        "byte_for_byte": True,
        "reconstructed": False,
        "rendered_replacement": False,
        "overwrite_approved_masters": False,
        "future_edit": "CREATE_REVISION_CHILD",
        "sha256": sha_before,
        "semantic_maps_unchanged": True,
        "ornek_00013_inventory_unchanged": ornek_inventory_before,
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_4,
        "created_at": _now(),
        "PHASE": "12.4 FIRST PRODUCTION PREMIUM CREATIVE FAMILY APPROVAL",
        "status": STATUS,
        "SELECTED FAMILY": CAMPAIGN_NAME,
        "PROJECT / BRAND": PROJECT_NAME,
        "FAMILY_ID": FAMILY_ID,
        "PROJECT_ID": UNILOFT_PROJECT_ID,
        "4:5": "HUMAN_APPROVED / ACTIVE",
        "9:16": "HUMAN_APPROVED / ACTIVE",
        "1:1": "HUMAN_APPROVED / ACTIVE",
        "16:9": "MISSING",
        "APPROVAL": "HUMAN_APPROVED",
        "ROUTER ELIGIBLE": True,
        "PRODUCTION_STATUS": "ACTIVE",
        "FAMILY-WIDE REVISION": "READY",
        "NEXT": NEXT_PHASE,
        "CREATIVES GENERATED": 0,
        "gpt_image_calls": provider_call_count(),
        "ideogram_calls": 0,
        "price_revision_executed": False,
        "ORNEK_00013_FAMILY_ID": ORNEK_FAMILY_ID,
        "ornek_inventory_unchanged": ornek_inventory_before,
        "family": json.loads(json.dumps(_jsonable(approved), default=str)),
        "inventory": format_master_inventory(approved),
        "identity_lock": family_identity_lock(),
        "routing_tests": tests,
        "family_wide_revision_ready": ready,
        "immutability": immutability,
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "temple_project_id": TEMPLE_PROJECT_ID,
        "boards": {
            "approved": render_family_board(
                catalog,
                title="07  APPROVED PRODUCTION FAMILY  —  HUMAN_APPROVED / ACTIVE",
                subtitle="4:5 | 9:16 | 1:1 HUMAN_APPROVED. 16:9 MISSING. Router eligible. Do not fabricate 16:9.",
                status_line="Byte-for-byte originals remain immutable. Router eligible. 12.5 price revision is NOT executed.",
            ),
        },
    }
    tests_log = list(blob.get("phase12_4_family_approval_tests") or [])
    tests_log.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "boards"}), default=str)))
    blob["phase12_4_family_approval_tests"] = tests_log
    ctx = dict(original_ctx)
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
    return record
