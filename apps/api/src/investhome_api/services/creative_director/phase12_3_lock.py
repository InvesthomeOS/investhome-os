"""Phase 12.3 family assembly, boards, and campaign lock. No generation."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import _font
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
    FILE_1X1_VARIANT,
    FILE_4X5,
    FILE_9X16,
    GOLD,
    IVORY,
    MASTER_1X1_ID,
    MASTER_4X5_ID,
    MASTER_9X16_ID,
    MUTED,
    NAVY,
    PROJECT_NAME,
    SOURCE_CATEGORY,
    STATUS_PENDING,
    WORKFLOW_ID_12_3,
    _fit,
    _missing_tile,
    _sha,
    candidate_families,
    excluded_pools,
    load_ornek_catalog,
    semantic_map_1x1,
    semantic_map_4x5,
    semantic_map_9x16,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FAMILY_LOCKED_PROPERTIES,
    FAMILY_SCHEMA,
    FEED_PORTRAIT,
    FORMAT_MASTER_SCHEMA,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SQUARE,
    STORY_REEL,
    empty_format_slot,
    format_lock_map,
    format_relationship_map,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count


def _format_master(*, family_id: str, master_id: str, fmt: str, item: dict[str, Any], semantic: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": FORMAT_MASTER_SCHEMA,
        "FAMILY_ID": family_id,
        "FORMAT_MASTER_ID": master_id,
        "FORMAT": fmt,
        "DIMENSIONS": {"width": item["width"], "height": item["height"]},
        "SOURCE_ASSET_ID": item["asset_id"],
        "SOURCE_FILENAME": item["filename"],
        "SOURCE_SHA256": item["sha256"],
        "SOURCE_CATEGORY": SOURCE_CATEGORY,
        "APPROVAL_STATUS": "PENDING HUMAN REVIEW",
        "SEMANTIC_MAP": semantic,
        "LOCK_MAP": format_lock_map(fmt=fmt, approval="PENDING HUMAN REVIEW"),
        "RELATIONSHIP_MAP": format_relationship_map(family_id=family_id, fmt=fmt),
        "PROJECT_SCOPE": "UNILOFT",
        "BRAND_SCOPE": "INVESTHOME",
        "master_scope": "PROJECT",
        "cross_project_reuse": False,
        "router_eligible": False,
        "family_member": True,
        "byte_for_byte": True,
        "reconstructed": False,
        "rendered_replacement": False,
    }


def selected_family_record(catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    family_id = FAMILY_ID
    variant = catalog[FILE_1X1_VARIANT]
    formats = {
        FEED_PORTRAIT: _format_master(family_id=family_id, master_id=MASTER_4X5_ID, fmt=FEED_PORTRAIT, item=catalog[FILE_4X5], semantic=semantic_map_4x5()),
        STORY_REEL: _format_master(family_id=family_id, master_id=MASTER_9X16_ID, fmt=STORY_REEL, item=catalog[FILE_9X16], semantic=semantic_map_9x16()),
        SQUARE: _format_master(family_id=family_id, master_id=MASTER_1X1_ID, fmt=SQUARE, item=catalog[FILE_1X1], semantic=semantic_map_1x1()),
        LANDSCAPE: empty_format_slot(family_id=family_id, fmt=LANDSCAPE),
    }
    return {
        "schema": FAMILY_SCHEMA,
        "FAMILY_ID": family_id,
        "family_type": "UNILOFT PROJECT",
        "brand_id": "INVESTHOME",
        "project_id": None,
        "project_name": PROJECT_NAME,
        "cross_project_reuse": False,
        "campaign_name": CAMPAIGN_NAME,
        "approval_status": "PENDING HUMAN REVIEW",
        "router_eligible": False,
        "identity": {
            "CAMPAIGN_IDEA": "UniLoft last remaining units in Washington D.C. as a priced, early-delivery investment",
            "CAMPAIGN_COPY": {
                "price": "$357.000'dan başlayan fiyatlar",
                "rent": "2.650$ kira getirisi",
                "delivery": "2026 tapu teslim",
                "offer": "Planlandan 6 ay erken teslim / Sınırlı sayıda son daireler",
                "tagline": "YATIRIMA AÇILAN KAPI",
            },
            "BRAND_IDENTITY": "Investhome",
            "PROJECT_IDENTITY": "UniLoft Washington D.C.",
            "APPROVED_ASSET_SET": [ASSET_4X5, ASSET_9X16, ASSET_1X1],
            "COLOR_SYSTEM": {"navy": [40, 47, 56], "tan": [196, 164, 112], "ivory": [236, 230, 218]},
            "TYPOGRAPHIC_PERSONALITY": "bold sans commercial stack + circular offer devices",
            "GRAPHIC_LANGUAGE": "white/tan last-units circles over UniLoft photography; Investhome footer",
            "COMMERCIAL_MESSAGE": "$357.000 start / $2.650 rent / 2026 delivery / last units",
            "VISUAL_CHARACTER": "independently art-directed per format; shared UniLoft commercial flight",
        },
        "locked_properties": list(FAMILY_LOCKED_PROPERTIES),
        "formats": formats,
        "inventory": {FEED_PORTRAIT: "FOUND", STORY_REEL: "FOUND", SQUARE: "FOUND", LANDSCAPE: "MISSING"},
        "additional_not_masters": [
            {
                "filename": variant["filename"],
                "asset_id": variant["asset_id"],
                "format": SQUARE,
                "role": "second 1:1 of the same commercial flight; not the format master",
            }
        ],
        "rejected_not_members": [
            "Masters 01–03",
            "Stage 4.0 RETRY / R1 / R2 / CLEAN / R3",
            "Stage 4.1 Story",
            "AI Quick Creative experiments",
        ],
    }


def render_discovery_board(catalog: dict[str, dict[str, Any]], families: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1480), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "01  MULTI-FORMAT FAMILY DISCOVERY  —  existing Investhome campaigns, not generated", font=_font(18), fill=GOLD)
    draw.text((36, 46), "Max 5. Stage 4 Stories excluded. Different composition is expected. Similar branding is not enough.", font=_font(14), fill=MUTED)
    y = 84
    for family in families[:5]:
        draw.text((36, y), ("SELECTED  " if family["selected"] else "CANDIDATE  ") + family["campaign_family_name"], font=_font(16), fill=GOLD if family["selected"] else IVORY)
        draw.text((36, y + 24), family["project_or_brand"] + "   confidence " + str(family["same_campaign_confidence"]), font=_font(13), fill=MUTED)
        x = 36
        for fmt in (FEED_PORTRAIT, STORY_REEL, SQUARE, LANDSCAPE):
            rec = family["formats"].get(fmt)
            box = (430, 180)
            tile = _fit(catalog[rec["filename"]]["image"], box) if rec else _missing_tile(box)
            canvas.paste(tile, (x, y + 52))
            draw.text((x, y + 236), f"{fmt}  {'FOUND' if rec else 'MISSING'}", font=_font(13), fill=IVORY if rec else MUTED)
            x += 470
        y += 272
    return canvas


def render_family_board(
    catalog: dict[str, dict[str, Any]],
    *,
    title: str,
    subtitle: str,
    status_line: str | None = None,
) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    draw.text((36, 48), subtitle, font=_font(14), fill=MUTED)
    slots = (
        (FEED_PORTRAIT, FILE_4X5, (40, 88), (430, 860)),
        (STORY_REEL, FILE_9X16, (500, 88), (300, 860)),
        (SQUARE, FILE_1X1, (830, 88), (500, 500)),
        (LANDSCAPE, None, (1360, 88), (520, 292)),
    )
    for fmt, filename, origin, box in slots:
        tile = _fit(catalog[filename]["image"], box) if filename else _missing_tile(box)
        canvas.paste(tile, origin)
        draw.text((origin[0], origin[1] + box[1] + 12), f"{fmt}  {catalog[filename]['filename'] if filename else 'MISSING'}", font=_font(14), fill=IVORY if filename else MUTED)
    draw.text((830, 620), "16:9 is MISSING. Do not fabricate it.", font=_font(14), fill=MUTED)
    draw.text((36, 1000), f"4:5 {FILE_4X5}  |  9:16 {FILE_9X16}  |  1:1 {FILE_1X1}  |  16:9 MISSING", font=_font(13), fill=IVORY)
    draw.text(
        (36, 1028),
        status_line or "Byte-for-byte originals. PENDING HUMAN REVIEW. Not router eligible.",
        font=_font(13),
        fill=MUTED,
    )
    return canvas


def format_master_inventory(family: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for fmt in (FEED_PORTRAIT, STORY_REEL, SQUARE, LANDSCAPE):
        slot = family["formats"][fmt]
        rows.append(
            {
                "FORMAT": fmt,
                "STATUS": family["inventory"][fmt],
                "FORMAT_MASTER_ID": slot.get("FORMAT_MASTER_ID"),
                "SOURCE_ASSET_ID": slot.get("SOURCE_ASSET_ID"),
                "SOURCE_FILENAME": slot.get("SOURCE_FILENAME"),
                "DIMENSIONS": slot.get("DIMENSIONS"),
                "APPROVAL_STATUS": slot.get("APPROVAL_STATUS"),
                "ROUTER_ELIGIBLE": slot.get("router_eligible"),
                "BYTE_FOR_BYTE": slot.get("byte_for_byte"),
                "SOURCE_SHA256": slot.get("SOURCE_SHA256"),
            }
        )
    return {
        "schema": "PremiumFormatMasterInventoryV1",
        "FAMILY_ID": family["FAMILY_ID"],
        "formats": rows,
        "additional_not_masters": family.get("additional_not_masters") or [],
    }


def generate_phase12_3_family_ingest(
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
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.3 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.3 requires Masters 01–03 records to remain")
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
    families_before = json.loads(json.dumps(_jsonable(library.get("premium_creative_families") or []), default=str))
    ornek_before = next((item for item in families_before if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID), None)
    if ornek_before is None:
        raise RuntimeError("Phase 12.3 requires the ORNEK_00013 Creative Family to remain")
    ornek_inventory_before = dict(ornek_before.get("inventory") or {})

    catalog = load_ornek_catalog(db)
    for filename, asset_id, expected_format in (
        (FILE_4X5, ASSET_4X5, FEED_PORTRAIT),
        (FILE_9X16, ASSET_9X16, STORY_REEL),
        (FILE_1X1, ASSET_1X1, SQUARE),
    ):
        item = catalog.get(filename)
        if item is None or item["asset_id"] != asset_id:
            raise RuntimeError(f"Phase 12.3 could not load {filename}")
        if item["format"] != expected_format:
            raise RuntimeError(f"{filename} is not a native {expected_format} original")
        if _sha(_read_bytes(db, UUID(asset_id))) != item["sha256"]:
            raise RuntimeError(f"Phase 12.3 refused to mutate {filename}")
    families = candidate_families(catalog)
    selected = selected_family_record(catalog)
    kept: list[dict[str, Any]] = []
    for item in library.get("premium_creative_families") or []:
        if str(item.get("FAMILY_ID")) == FAMILY_ID:
            continue
        kept.append(item)
    ornek_after_keep = next((item for item in kept if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID), None)
    if ornek_after_keep is None:
        raise RuntimeError("Phase 12.3 refused to drop the ORNEK_00013 family")
    if dict(ornek_after_keep.get("inventory") or {}) != ornek_inventory_before:
        raise RuntimeError("Phase 12.3 refused to alter the ORNEK_00013 inventory")
    if str(ornek_after_keep.get("FAMILY_ID")) != ORNEK_FAMILY_ID:
        raise RuntimeError("Phase 12.3 refused to change ORNEK_00013 FAMILY_ID")
    kept.append(json.loads(json.dumps(_jsonable(selected), default=str)))
    library["premium_creative_families"] = kept
    library["pending_multiformat_family_id"] = FAMILY_ID
    library["phase12_3_status"] = STATUS_PENDING

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.3 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.3 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.3 refused to mutate Master 03")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.3 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.3 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.3 refused to change Master 03 visual")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None or parent.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.3 refused to keep ORNEK_00013 as the brand master visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Phase 12.3 must not create another approved Premium Master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Phase 12.3 refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Phase 12.3 refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Phase 12.3 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.3 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.3 refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.3 refused to change production cover")
    if selected["router_eligible"] is not False or selected["approval_status"] != "PENDING HUMAN REVIEW":
        raise RuntimeError("Phase 12.3 must not auto-activate the pending family")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.3 must not call GPT Image")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["phase12_2_family_lock_tests"] = preserved.get("quality122")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_3,
        "created_at": _now(),
        "PHASE": "12.3 FIRST MULTI-FORMAT PRODUCTION CREATIVE FAMILY",
        "status": STATUS_PENDING,
        "SELECTED FAMILY": CAMPAIGN_NAME,
        "PROJECT / BRAND": PROJECT_NAME,
        "FAMILY_ID": FAMILY_ID,
        "4:5": "FOUND",
        "9:16": "FOUND",
        "1:1": "FOUND",
        "16:9": "MISSING",
        "CREATIVES GENERATED": 0,
        "gpt_image_calls": provider_call_count(),
        "ideogram_calls": 0,
        "APPROVAL": "PENDING HUMAN REVIEW",
        "ROUTER ELIGIBLE": False,
        "ORNEK_00013_FAMILY_ID": ORNEK_FAMILY_ID,
        "ornek_inventory_unchanged": ornek_inventory_before,
        "excluded": excluded_pools(db),
        "candidates": json.loads(json.dumps(_jsonable(families), default=str)),
        "family": json.loads(json.dumps(_jsonable(selected), default=str)),
        "inventory": format_master_inventory(selected),
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "temple_project_id": TEMPLE_PROJECT_ID,
        "boards": {
            "discovery": render_discovery_board(catalog, families),
            "selected": render_family_board(
                catalog,
                title="03  SELECTED FAMILY  —  UniLoft last-units commercial flight",
                subtitle="Independently designed formats. PENDING HUMAN REVIEW. 16:9 MISSING. Not generated.",
            ),
            "review": render_family_board(
                catalog,
                title="07  HUMAN REVIEW  —  ARE THESE THE SAME PROFESSIONAL CAMPAIGN?",
                subtitle="4:5 | 9:16 | 1:1 | 16:9 MISSING. Layouts may differ. Identity must match. Do not activate yet.",
            ),
        },
    }
    tests = list(blob.get("phase12_3_family_ingest_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "boards"}), default=str)))
    blob["phase12_3_family_ingest_tests"] = tests
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
