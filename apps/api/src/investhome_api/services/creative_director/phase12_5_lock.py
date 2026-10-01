"""Phase 12.5 — family-wide PRICE_ONLY children. Originals stay immutable.

Does not generate creatives. Does not invent a 4:5 price plate. Does not
fabricate 16:9. Does not auto-approve children. No GPT Image. No Ideogram.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_master_router_v2 import (
    FAMILY_WIDE_REVISION,
    classify_production_intent,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
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
from investhome_api.services.creative_director.phase10_0_master import _identity_slice, attach_derived_revision
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
    GOLD,
    IVORY,
    MASTER_1X1_ID,
    MASTER_4X5_ID,
    MASTER_9X16_ID,
    MUTED,
    NAVY,
    PROJECT_NAME,
    _fit,
    _sha,
    load_ornek_catalog,
)
from investhome_api.services.creative_director.phase12_4_approve_lock import (
    PHASE_12_5_COMMAND,
    UNILOFT_PROJECT_ID,
)
from investhome_api.services.creative_director.phase12_5_price_revise import (
    NEW_VALUE,
    OLD_VALUE,
    apply_feed_price_revision,
    apply_square_price_revision,
    apply_story_price_revision,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SQUARE,
    STORY_REEL,
    route_family_wide_revision,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_12_5 = "phase12_5_family_wide_natural_language_revision_proof"
REVISION_TYPE = "PRICE_ONLY"
STATUS_PENDING = "FAMILY_WIDE_REVISION_PENDING_HUMAN_REVIEW"
STATUS_FAIL = "FAMILY_WIDE_REVISION_FAIL"
CHILD_9X16_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:uniloft-last-units-357k:9x16:price-375000"))
CHILD_1X1_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:uniloft-last-units-357k:1x1:price-375000"))


def _slot_identity(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "FORMAT_MASTER_ID": slot.get("FORMAT_MASTER_ID"),
        "SOURCE_ASSET_ID": slot.get("SOURCE_ASSET_ID"),
        "SOURCE_FILENAME": slot.get("SOURCE_FILENAME"),
        "SOURCE_SHA256": slot.get("SOURCE_SHA256"),
        "APPROVAL_STATUS": slot.get("APPROVAL_STATUS"),
        "router_eligible": slot.get("router_eligible"),
        "production_status": slot.get("production_status"),
        "DIMENSIONS": slot.get("DIMENSIONS"),
        "SEMANTIC_MAP": slot.get("SEMANTIC_MAP"),
    }


def _child_record(
    *,
    revision_id: str,
    parent_master_id: str,
    parent_asset_id: str,
    fmt: str,
    filename: str,
    visual_asset: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "revision_id": revision_id,
        "FAMILY_ID": FAMILY_ID,
        "PARENT_FORMAT_MASTER_ID": parent_master_id,
        "parent_asset_id": parent_asset_id,
        "revision_type": REVISION_TYPE,
        "OLD_VALUE": OLD_VALUE,
        "NEW_VALUE": NEW_VALUE,
        "visual_asset": visual_asset,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "master_state": "CHILD_REVISION",
        "format": fmt,
        "source_filename": filename,
        "natural_language_instruction": PHASE_12_5_COMMAND,
        "created_at": _now(),
        "phase": "12.5",
        "territory": meta.get("territory"),
        "pixel_delta_outside": int((meta.get("pixel_delta") or {}).get("outside_changed_pixels") or 0),
        "compose": {k: v for k, v in meta.items() if k != "runs"},
    }


def _persist_child(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    image: Image.Image,
    *,
    fmt: str,
) -> str:
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(image),
        content_type="image/png",
        campaign_mode=f"uniloft-family-wide-price-revision-{fmt.replace(':', 'x')}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 12.5 FAMILY-WIDE PRICE_ONLY CHILD. DO NOT OVERWRITE FORMAT MASTER.",
    )
    return str(asset.id)


def render_before_after(
    before: Image.Image,
    after: Image.Image,
    *,
    title: str,
    subtitle: str,
    tile: tuple[int, int],
) -> Image.Image:
    canvas = Image.new("RGB", (80 + tile[0] * 2 + 40, 120 + tile[1]), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    draw.text((36, 48), subtitle, font=_font(14), fill=MUTED)
    canvas.paste(_fit(before, tile), (36, 80))
    canvas.paste(_fit(after, tile), (56 + tile[0], 80))
    draw.text((36, 88 + tile[1]), "BEFORE", font=_font(14), fill=IVORY)
    draw.text((56 + tile[0], 88 + tile[1]), "AFTER", font=_font(14), fill=IVORY)
    return canvas


def render_family_before_after_board(
    feed_b: Image.Image,
    feed_a: Image.Image,
    story_b: Image.Image,
    story_a: Image.Image,
    square_b: Image.Image,
    square_a: Image.Image,
    *,
    feed_status: str,
    story_status: str,
    square_status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (3200, 1680), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "07  FAMILY-WIDE PRICE REVISION  —  357.000 → 375.000  HUMAN REVIEW", font=_font(22), fill=GOLD)
    draw.text(
        (36, 52),
        "4:5 BEFORE | AFTER     9:16 BEFORE | AFTER     1:1 BEFORE | AFTER     16:9 SKIPPED — MASTER MISSING",
        font=_font(16),
        fill=MUTED,
    )
    columns = (
        ("4:5  ORNEK_00012", feed_b, feed_a, feed_status, (36, 100), (460, 575)),
        ("9:16  ORNEK_00005", story_b, story_a, story_status, (1080, 100), (310, 551)),
        ("1:1  ORNEK_00003", square_b, square_a, square_status, (1860, 100), (460, 460)),
    )
    for label, before, after, status, origin, box in columns:
        x, y = origin
        canvas.paste(_fit(before, box), (x, y))
        canvas.paste(_fit(after, box), (x + box[0] + 16, y))
        draw.text((x, y + box[1] + 14), f"{label}  BEFORE", font=_font(16), fill=IVORY)
        draw.text((x + box[0] + 16, y + box[1] + 14), "AFTER", font=_font(16), fill=IVORY)
        color = GOLD if status == "PASS" else (220, 90, 80)
        draw.text((x, y + box[1] + 42), status, font=_font(18), fill=color)
    draw.text((36, 1580), "Original masters unchanged. Children DRAFT. Do not activate. GPT Image 0. Ideogram 0.", font=_font(14), fill=MUTED)
    draw.text((36, 1610), f"FAMILY {FAMILY_ID}   PRICE_ONLY   {CAMPAIGN_NAME}", font=_font(13), fill=IVORY)
    return canvas


def render_mobile_preview(story: Image.Image, square: Image.Image, feed: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1080, 1920), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "08  MOBILE PREVIEW  —  9:16 PRICE_ONLY DRAFT", font=_font(18), fill=GOLD)
    canvas.paste(_fit(story, (420, 748)), (40, 80))
    canvas.paste(_fit(square, (420, 420)), (520, 80))
    canvas.paste(_fit(feed, (420, 525)), (520, 520))
    draw.text((40, 840), "9:16 AFTER", font=_font(14), fill=IVORY)
    draw.text((520, 508), "1:1 AFTER", font=_font(14), fill=IVORY)
    draw.text((520, 1054), "4:5 UNCHANGED  PRICE ABSENT", font=_font(14), fill=MUTED)
    draw.text((40, 1840), "Do not activate children. Wait for human visual review.", font=_font(14), fill=MUTED)
    return canvas


def generate_phase12_5_family_wide_revision(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality121"] = list(blob.get("phase12_1_approval_tests") or [])
    preserved["quality122"] = list(blob.get("phase12_2_family_lock_tests") or [])
    preserved["quality123"] = list(blob.get("phase12_3_family_ingest_tests") or [])
    preserved["quality124"] = list(blob.get("phase12_4_family_approval_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.5 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.5 requires Masters 01–03 records to remain")
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
        raise RuntimeError("Phase 12.5 requires the ORNEK_00013 Creative Family to remain")
    ornek_inventory_before = dict(ornek_before.get("inventory") or {})
    family = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == FAMILY_ID),
        None,
    )
    if family is None:
        raise RuntimeError("Phase 12.5 requires the UniLoft Last Units family")
    if str(family.get("approval_status")) != "HUMAN_APPROVED" or family.get("router_eligible") is not True:
        raise RuntimeError("Phase 12.5 requires an ACTIVE HUMAN_APPROVED family")

    classified = classify_production_intent(PHASE_12_5_COMMAND)
    if classified.get("intent") != FAMILY_WIDE_REVISION:
        raise RuntimeError("Phase 12.5 command must classify as FAMILY_WIDE_REVISION")
    wide = route_family_wide_revision(
        classified=classified,
        library=library,
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
    )
    if [item["format"] for item in wide.get("targets") or []] != [FEED_PORTRAIT, STORY_REEL, SQUARE]:
        raise RuntimeError("Phase 12.5 family-wide targets must be 4:5, 9:16, 1:1")
    if LANDSCAPE not in (wide.get("missing_formats") or []):
        raise RuntimeError("Phase 12.5 must skip missing 16:9")

    catalog = load_ornek_catalog(db)
    sha_before = {}
    parents: dict[str, Image.Image] = {}
    identities = {}
    for fmt, filename, asset_id, master_id in (
        (FEED_PORTRAIT, FILE_4X5, ASSET_4X5, MASTER_4X5_ID),
        (STORY_REEL, FILE_9X16, ASSET_9X16, MASTER_9X16_ID),
        (SQUARE, FILE_1X1, ASSET_1X1, MASTER_1X1_ID),
    ):
        item = catalog.get(filename)
        if item is None or item["asset_id"] != asset_id:
            raise RuntimeError(f"Phase 12.5 could not load {filename}")
        raw = _read_bytes(db, UUID(asset_id))
        live = _sha(raw)
        slot = family["formats"][fmt]
        if str(slot.get("SOURCE_SHA256")) != live or live != item["sha256"]:
            raise RuntimeError(f"Phase 12.5 refused to start from a mutated {filename}")
        if str(slot.get("FORMAT_MASTER_ID")) != master_id or str(slot.get("SOURCE_ASSET_ID")) != asset_id:
            raise RuntimeError(f"Phase 12.5 refused to retarget {fmt}")
        sha_before[filename] = live
        parents[fmt] = Image.open(io.BytesIO(raw)).convert("RGB")
        identities[fmt] = json.loads(json.dumps(_jsonable(_slot_identity(slot)), default=str))

    feed_child, feed_meta = apply_feed_price_revision(parents[FEED_PORTRAIT])
    story_child, story_meta = apply_story_price_revision(parents[STORY_REEL])
    square_child, square_meta = apply_square_price_revision(parents[SQUARE])
    if feed_child is not None:
        raise RuntimeError("Phase 12.5 must not invent a 4:5 PRICE plate")
    story_outside = int((story_meta.get("pixel_delta") or {}).get("outside_changed_pixels", -1))
    square_outside = int((square_meta.get("pixel_delta") or {}).get("outside_changed_pixels", -1))
    if story_outside != 0 or square_outside != 0:
        raise RuntimeError("Phase 12.5 unrelated visual delta is not zero")

    story_asset_id = _persist_child(db, user, row, story_child, fmt=STORY_REEL)
    square_asset_id = _persist_child(db, user, row, square_child, fmt=SQUARE)
    forbidden = {ASSET_4X5, ASSET_9X16, ASSET_1X1, APPROVED_ASSET_ID, APPROVED_ASSET_02, APPROVED_ASSET_03, SELECTED_ASSET_ID}
    if story_asset_id in forbidden or square_asset_id in forbidden:
        raise RuntimeError("Phase 12.5 refused to overwrite an approved original")

    attach_derived_revision(
        family["formats"][STORY_REEL],
        _child_record(
            revision_id=CHILD_9X16_ID,
            parent_master_id=MASTER_9X16_ID,
            parent_asset_id=ASSET_9X16,
            fmt=STORY_REEL,
            filename=FILE_9X16,
            visual_asset=story_asset_id,
            meta=story_meta,
        ),
    )
    attach_derived_revision(
        family["formats"][SQUARE],
        _child_record(
            revision_id=CHILD_1X1_ID,
            parent_master_id=MASTER_1X1_ID,
            parent_asset_id=ASSET_1X1,
            fmt=SQUARE,
            filename=FILE_1X1,
            visual_asset=square_asset_id,
            meta=square_meta,
        ),
    )

    feed_status = "SKIPPED_TARGET_NOT_PRESENT"
    story_status = "PASS" if story_outside == 0 else "FAIL"
    square_status = "PASS" if square_outside == 0 else "FAIL"
    children_ok = 2
    overall = STATUS_FAIL
    if feed_status == "PASS" and story_status == "PASS" and square_status == "PASS" and children_ok == 3:
        overall = STATUS_PENDING

    family["phase12_5_status"] = overall
    family["phase12_5_executed"] = True
    family["phase12_5_auto_approved"] = False
    library["phase12_5_status"] = overall
    library["next_production_phase"] = "HUMAN VISUAL REVIEW ONLY"

    for fmt, filename, asset_id, _master_id in (
        (FEED_PORTRAIT, FILE_4X5, ASSET_4X5, MASTER_4X5_ID),
        (STORY_REEL, FILE_9X16, ASSET_9X16, MASTER_9X16_ID),
        (SQUARE, FILE_1X1, ASSET_1X1, MASTER_1X1_ID),
    ):
        slot = family["formats"][fmt]
        ident = json.loads(json.dumps(_jsonable(_slot_identity(slot)), default=str))
        if ident != identities[fmt]:
            raise RuntimeError(f"Phase 12.5 mutated the {fmt} format master identity")
        live = _sha(_read_bytes(db, UUID(asset_id)))
        if live != sha_before[filename]:
            raise RuntimeError(f"Phase 12.5 mutated original {filename}")
    if family["formats"][LANDSCAPE].get("FORMAT_MASTER_ID") is not None:
        raise RuntimeError("Phase 12.5 fabricated 16:9")
    if family["formats"][STORY_REEL].get("router_eligible") is not True:
        raise RuntimeError("Phase 12.5 must keep parent 9:16 router eligible")
    kids_story = family["formats"][STORY_REEL].get("derived_revisions") or []
    kids_square = family["formats"][SQUARE].get("derived_revisions") or []
    if any(item.get("approval_status") == "HUMAN_APPROVED" for item in kids_story + kids_square):
        raise RuntimeError("Phase 12.5 must not auto-approve revision children")
    if any(item.get("router_eligible") for item in kids_story + kids_square):
        raise RuntimeError("Phase 12.5 children must not be router eligible")

    ornek_after = next(item for item in library["premium_creative_families"] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID)
    if dict(ornek_after.get("inventory") or {}) != ornek_inventory_before:
        raise RuntimeError("Phase 12.5 refused to alter the ORNEK_00013 inventory")
    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.5 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.5 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.5 refused to mutate Master 03")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.5 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.5 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.5 refused to change Master 03 visual")
    parent = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == PRODUCTION_MASTER_ID), None)
    if parent is None or parent.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.5 refused to keep ORNEK_00013 as the brand master visual")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Phase 12.5 must not create another library Premium Master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Phase 12.5 refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Phase 12.5 refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Phase 12.5 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.5 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.5 refused to rewrite the Phase 11.12 product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.5 refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.5 must not call GPT Image")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["phase12_2_family_lock_tests"] = preserved.get("quality122")
    blob["phase12_3_family_ingest_tests"] = preserved.get("quality123")
    blob["phase12_4_family_approval_tests"] = preserved.get("quality124")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    lineage = {
        "schema": "FamilyWideRevisionLineageV1",
        "FAMILY_ID": FAMILY_ID,
        "command": PHASE_12_5_COMMAND,
        "classified_intent": FAMILY_WIDE_REVISION,
        "REVISION_TYPE": REVISION_TYPE,
        "OLD_VALUE": OLD_VALUE,
        "NEW_VALUE": NEW_VALUE,
        "children": [
            {
                "format": STORY_REEL,
                "revision_id": CHILD_9X16_ID,
                "PARENT_FORMAT_MASTER_ID": MASTER_9X16_ID,
                "parent_asset_id": ASSET_9X16,
                "visual_asset": story_asset_id,
                "approval_status": "DRAFT",
                "router_eligible": False,
            },
            {
                "format": SQUARE,
                "revision_id": CHILD_1X1_ID,
                "PARENT_FORMAT_MASTER_ID": MASTER_1X1_ID,
                "parent_asset_id": ASSET_1X1,
                "visual_asset": square_asset_id,
                "approval_status": "DRAFT",
                "router_eligible": False,
            },
        ],
        "skipped": [
            {"format": FEED_PORTRAIT, "reason": feed_meta.get("reason"), "PARENT_FORMAT_MASTER_ID": MASTER_4X5_ID},
            {"format": LANDSCAPE, "reason": "MASTER MISSING"},
        ],
        "original_masters_modified": False,
        "auto_approved": False,
    }
    delta = {
        "schema": "FamilyWideRevisionDeltaV1",
        "UNRELATED_VISUAL_DELTA": 0 if story_outside == 0 and square_outside == 0 else "FAIL",
        "formats": {
            FEED_PORTRAIT: feed_meta.get("pixel_delta"),
            STORY_REEL: story_meta.get("pixel_delta"),
            SQUARE: square_meta.get("pixel_delta"),
            LANDSCAPE: {"skipped": True, "reason": "MASTER MISSING"},
        },
        "original_sha256": sha_before,
        "original_sha256_after": {
            FILE_4X5: _sha(_read_bytes(db, UUID(ASSET_4X5))),
            FILE_9X16: _sha(_read_bytes(db, UUID(ASSET_9X16))),
            FILE_1X1: _sha(_read_bytes(db, UUID(ASSET_1X1))),
        },
    }
    images = {
        "feed_after": parents[FEED_PORTRAIT],
        "story_after": story_child,
        "square_after": square_child,
        "feed_pair": render_before_after(
            parents[FEED_PORTRAIT],
            parents[FEED_PORTRAIT],
            title="04  4:5 BEFORE | AFTER  —  PRICE ABSENT  FAIL",
            subtitle="ORNEK_00012 has no $357.000 plate. Not invented. Original unchanged.",
            tile=(640, 800),
        ),
        "story_pair": render_before_after(
            parents[STORY_REEL],
            story_child,
            title="05  9:16 BEFORE | AFTER  —  PRICE_ONLY  357.000 → 375.000",
            subtitle="Native glyph swap on ORNEK_00005. Surrounding wording preserved.",
            tile=(420, 748),
        ),
        "square_pair": render_before_after(
            parents[SQUARE],
            square_child,
            title="06  1:1 BEFORE | AFTER  —  PRICE_ONLY  357.000 → 375.000",
            subtitle="Native glyph swap on ORNEK_00003. %40 pill / rent / badges unchanged.",
            tile=(640, 640),
        ),
        "family_board": render_family_before_after_board(
            parents[FEED_PORTRAIT],
            parents[FEED_PORTRAIT],
            parents[STORY_REEL],
            story_child,
            parents[SQUARE],
            square_child,
            feed_status=feed_status,
            story_status=story_status,
            square_status=square_status,
        ),
        "mobile": render_mobile_preview(story_child, square_child, parents[FEED_PORTRAIT]),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_5,
        "created_at": _now(),
        "PHASE": "12.5 FAMILY-WIDE NATURAL LANGUAGE REVISION PROOF",
        "status": overall,
        "command": PHASE_12_5_COMMAND,
        "REVISION_TYPE": REVISION_TYPE,
        "OLD_VALUE": OLD_VALUE,
        "NEW_VALUE": NEW_VALUE,
        "FAMILY_ID": FAMILY_ID,
        "FAMILY": CAMPAIGN_NAME,
        "PROJECT / BRAND": PROJECT_NAME,
        "4:5": feed_status,
        "9:16": story_status,
        "1:1": square_status,
        "16:9": "SKIPPED — MASTER MISSING",
        "ORIGINAL MASTERS MODIFIED": "NO",
        "REVISION CHILDREN": f"{children_ok} / FAIL",
        "UNRELATED VISUAL DELTA": 0,
        "GPT IMAGE CALLS": provider_call_count(),
        "IDEOGRAM CALLS": 0,
        "APPROVAL": "PENDING HUMAN REVIEW",
        "classified": classified,
        "route": {**wide, "executed": True, "territory": REVISION_TYPE},
        "feed_meta": feed_meta,
        "story_meta": {k: v for k, v in story_meta.items() if k != "runs"},
        "square_meta": {k: v for k, v in square_meta.items() if k != "runs"},
        "lineage": lineage,
        "delta": delta,
        "child_9x16_asset": story_asset_id,
        "child_1x1_asset": square_asset_id,
        "ORNEK_00013_FAMILY_ID": ORNEK_FAMILY_ID,
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "temple_project_id": TEMPLE_PROJECT_ID,
        "images": images,
    }
    tests_log = list(blob.get("phase12_5_family_wide_revision_tests") or [])
    tests_log.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "images"}), default=str)))
    blob["phase12_5_family_wide_revision_tests"] = tests_log
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
