"""Phase 12.6 — family-wide COPY_ONLY children from original format masters.

Does not generate creatives. Does not use $375.000 price-revision children
as parents. Does not fabricate 16:9. Does not auto-approve. No GPT Image.
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
    COPY_EDIT_ONLY,
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
from investhome_api.services.creative_director.phase12_4_approve_lock import UNILOFT_PROJECT_ID
from investhome_api.services.creative_director.phase12_5_lock import (
    CHILD_1X1_ID as PRICE_CHILD_1X1_ID,
)
from investhome_api.services.creative_director.phase12_5_lock import (
    CHILD_9X16_ID as PRICE_CHILD_9X16_ID,
)
from investhome_api.services.creative_director.phase12_5_lock import _slot_identity
from investhome_api.services.creative_director.phase12_5_r1_lock import CHILD_1X1_ASSET as PRICE_CHILD_1X1_ASSET
from investhome_api.services.creative_director.phase12_5_r1_lock import CHILD_9X16_ASSET as PRICE_CHILD_9X16_ASSET
from investhome_api.services.creative_director.phase12_6_copy_revise import (
    NEW_COPY,
    OLD_COPY,
    apply_feed_copy_revision,
    apply_square_copy_revision,
    apply_story_copy_revision,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SKIP_FORMAT_MASTER_MISSING,
    SQUARE,
    STORY_REEL,
    route_family_wide_revision,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_12_6 = "phase12_6_family_wide_copy_revision_proof"
REVISION_TYPE = "COPY_ONLY"
STATUS_PENDING = "FAMILY_WIDE_COPY_REVISION_PENDING_HUMAN_REVIEW"
STATUS_FAIL = "FAMILY_WIDE_COPY_REVISION_FAIL"
PHASE_12_6_COMMAND = (
    "Bu kampanyadaki 'Son Daireler!' mesajını 'Son Fırsatlar!' olarak değiştir, başka hiçbir şeyi değiştirme."
)
CHILD_4X5_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:uniloft-last-units-357k:4x5:copy-son-firsatlar"))
CHILD_9X16_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:uniloft-last-units-357k:9x16:copy-son-firsatlar"))
CHILD_1X1_ID = str(uuid5(NAMESPACE_URL, "investhome:nl-revision:uniloft-last-units-357k:1x1:copy-son-firsatlar"))
ORIGINAL_PARENTS = (ASSET_4X5, ASSET_9X16, ASSET_1X1)
PRICE_CHILDREN = (PRICE_CHILD_9X16_ASSET, PRICE_CHILD_1X1_ASSET, PRICE_CHILD_9X16_ID, PRICE_CHILD_1X1_ID)


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
        "OLD_VALUE": OLD_COPY,
        "NEW_VALUE": NEW_COPY,
        "visual_asset": visual_asset,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "master_state": "CHILD_REVISION",
        "format": fmt,
        "source_filename": filename,
        "natural_language_instruction": PHASE_12_6_COMMAND,
        "created_at": _now(),
        "phase": "12.6",
        "territory": meta.get("territory"),
        "pixel_delta_outside": int((meta.get("pixel_delta") or {}).get("outside_changed_pixels") or 0),
        "compose": {k: v for k, v in meta.items() if k not in {"type_mask"}},
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
        campaign_mode=f"uniloft-family-wide-copy-revision-{fmt.replace(':', 'x')}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 12.6 FAMILY-WIDE COPY_ONLY CHILD. DO NOT OVERWRITE FORMAT MASTER.",
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
    canvas = Image.new("RGB", (80 + tile[0] * 2 + 40, 140 + tile[1]), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), title, font=_font(18), fill=GOLD)
    draw.text((36, 48), subtitle, font=_font(14), fill=MUTED)
    canvas.paste(_fit(before, tile), (36, 80))
    canvas.paste(_fit(after, tile), (56 + tile[0], 80))
    draw.text((36, 88 + tile[1]), "BEFORE", font=_font(14), fill=IVORY)
    draw.text((56 + tile[0], 88 + tile[1]), "AFTER", font=_font(14), fill=IVORY)
    return canvas


def _zoom_badge(image: Image.Image, meta: dict[str, Any], box: tuple[int, int]) -> Image.Image:
    circle = meta.get("circle") or {}
    bbox = circle.get("bbox")
    if not bbox:
        W, H = image.size
        bbox = (int(0.15 * W), int(0.35 * H), int(0.7 * W), int(0.75 * H))
    pad = max(12, int((bbox[2] - bbox[0]) * 0.12))
    crop = image.crop(
        (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(image.size[0], bbox[2] + pad),
            min(image.size[1], bbox[3] + pad),
        )
    )
    return _fit(crop, box)


def render_family_before_after_board(
    feed_b: Image.Image,
    feed_a: Image.Image,
    story_b: Image.Image,
    story_a: Image.Image,
    square_b: Image.Image,
    square_a: Image.Image,
    *,
    feed_meta: dict[str, Any],
    story_meta: dict[str, Any],
    square_meta: dict[str, Any],
    feed_status: str,
    story_status: str,
    square_status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (3840, 2480), NAVY)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "04  FAMILY-WIDE COPY REVISION  —  Son Daireler! → Son Fırsatlar!  HUMAN REVIEW", font=_font(22), fill=GOLD)
    draw.text(
        (36, 52),
        "4:5 BEFORE | AFTER     9:16 BEFORE | AFTER     1:1 BEFORE | AFTER     16:9 SKIPPED — FORMAT MASTER MISSING",
        font=_font(16),
        fill=MUTED,
    )
    columns = (
        ("4:5  ORNEK_00012", feed_b, feed_a, feed_status, feed_meta, (36, 96), (520, 650)),
        ("9:16  ORNEK_00005", story_b, story_a, story_status, story_meta, (1160, 96), (320, 569)),
        ("1:1  ORNEK_00003", square_b, square_a, square_status, square_meta, (1940, 96), (520, 520)),
    )
    for label, before, after, status, meta, origin, box in columns:
        x, y = origin
        canvas.paste(_fit(before, box), (x, y))
        canvas.paste(_fit(after, box), (x + box[0] + 16, y))
        draw.text((x, y + box[1] + 12), f"{label}  BEFORE", font=_font(16), fill=IVORY)
        draw.text((x + box[0] + 16, y + box[1] + 12), "AFTER", font=_font(16), fill=IVORY)
        color = GOLD if status == "PASS" else (220, 90, 80)
        draw.text((x, y + box[1] + 40), status, font=_font(18), fill=color)
        zx, zy = x, 860
        zbox = (box[0], box[0])
        canvas.paste(_zoom_badge(before, meta, zbox), (zx, zy))
        canvas.paste(_zoom_badge(after, meta, zbox), (zx + box[0] + 16, zy))
        draw.text((zx, zy + zbox[1] + 10), "BADGE BEFORE", font=_font(14), fill=MUTED)
        draw.text((zx + box[0] + 16, zy + zbox[1] + 10), "BADGE AFTER", font=_font(14), fill=IVORY)
    miss = Image.new("RGB", (520, 292), (28, 30, 36))
    md = ImageDraw.Draw(miss)
    md.rectangle((8, 8, 511, 283), outline=(70, 72, 80), width=2)
    md.text((90, 120), "16:9  SKIPPED_FORMAT_MASTER_MISSING", font=_font(16), fill=MUTED)
    md.text((150, 156), "Do not fabricate a landscape master.", font=_font(14), fill=MUTED)
    canvas.paste(miss, (3180, 96))
    draw.text((36, 2320), "Original HUMAN_APPROVED masters unchanged. Parents are ORNEK_00012 / 00005 / 00003 — not $375 children.", font=_font(14), fill=MUTED)
    draw.text((36, 2352), "Children DRAFT. Do not auto-approve. GPT Image 0. Ideogram 0. COPY_ONLY.", font=_font(14), fill=MUTED)
    draw.text((36, 2384), f"FAMILY {FAMILY_ID}   {CAMPAIGN_NAME}", font=_font(13), fill=IVORY)
    draw.text((36, 2416), "WAIT FOR HUMAN VISUAL REVIEW. NO NEXT TEST.", font=_font(16), fill=GOLD)
    return canvas


def generate_phase12_6_family_wide_copy_revision(
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
    preserved["quality125"] = list(blob.get("phase12_5_family_wide_revision_tests") or [])
    preserved["quality125r1"] = list(blob.get("phase12_5_r1_revision_lock_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.6 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.6 requires Masters 01–03 records to remain")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")
    approved_count_before = count_approved_premium(library)
    ornek_before = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID),
        None,
    )
    if ornek_before is None:
        raise RuntimeError("Phase 12.6 requires the ORNEK_00013 Creative Family to remain")
    ornek_inventory_before = dict(ornek_before.get("inventory") or {})
    family = next(
        (item for item in library.get("premium_creative_families") or [] if str(item.get("FAMILY_ID")) == FAMILY_ID),
        None,
    )
    if family is None:
        raise RuntimeError("Phase 12.6 requires the UniLoft Last Units family")
    if str(family.get("approval_status")) != "HUMAN_APPROVED" or family.get("router_eligible") is not True:
        raise RuntimeError("Phase 12.6 requires an ACTIVE HUMAN_APPROVED family")

    classified = classify_production_intent(PHASE_12_6_COMMAND)
    if classified.get("intent") != FAMILY_WIDE_REVISION:
        raise RuntimeError("Phase 12.6 command must classify as FAMILY_WIDE_REVISION")
    if classified.get("family_wide_territory") != COPY_EDIT_ONLY:
        raise RuntimeError("Phase 12.6 command must classify as COPY_EDIT_ONLY")
    wide = route_family_wide_revision(
        classified=classified,
        library=library,
        family_id=FAMILY_ID,
        project_id=UNILOFT_PROJECT_ID,
        target_phrase=OLD_COPY,
    )
    if [item["format"] for item in wide.get("targets") or []] != [FEED_PORTRAIT, STORY_REEL, SQUARE]:
        raise RuntimeError("Phase 12.6 applicable targets must be 4:5, 9:16, 1:1")
    if LANDSCAPE not in (wide.get("missing_formats") or []):
        raise RuntimeError("Phase 12.6 must skip missing 16:9")

    catalog = load_ornek_catalog(db)
    sha_before = {}
    parents: dict[str, Image.Image] = {}
    identities = {}
    parent_assets = {
        FEED_PORTRAIT: ASSET_4X5,
        STORY_REEL: ASSET_9X16,
        SQUARE: ASSET_1X1,
    }
    for fmt, filename, asset_id, master_id in (
        (FEED_PORTRAIT, FILE_4X5, ASSET_4X5, MASTER_4X5_ID),
        (STORY_REEL, FILE_9X16, ASSET_9X16, MASTER_9X16_ID),
        (SQUARE, FILE_1X1, ASSET_1X1, MASTER_1X1_ID),
    ):
        if asset_id in PRICE_CHILDREN or asset_id not in ORIGINAL_PARENTS:
            raise RuntimeError("Phase 12.6 refused a $375.000 price-revision child as parent")
        item = catalog.get(filename)
        if item is None or item["asset_id"] != asset_id:
            raise RuntimeError(f"Phase 12.6 could not load original {filename}")
        raw = _read_bytes(db, UUID(asset_id))
        live = _sha(raw)
        slot = family["formats"][fmt]
        if str(slot.get("SOURCE_SHA256")) != live or live != item["sha256"]:
            raise RuntimeError(f"Phase 12.6 refused to start from a mutated {filename}")
        if str(slot.get("FORMAT_MASTER_ID")) != master_id or str(slot.get("SOURCE_ASSET_ID")) != asset_id:
            raise RuntimeError(f"Phase 12.6 refused to retarget {fmt} away from the original master")
        sha_before[filename] = live
        parents[fmt] = Image.open(io.BytesIO(raw)).convert("RGB")
        identities[fmt] = json.loads(json.dumps(_jsonable(_slot_identity(slot)), default=str))

    feed_child, feed_meta = apply_feed_copy_revision(parents[FEED_PORTRAIT])
    story_child, story_meta = apply_story_copy_revision(parents[STORY_REEL])
    square_child, square_meta = apply_square_copy_revision(parents[SQUARE])
    if feed_child is None or story_child is None or square_child is None:
        raise RuntimeError("Phase 12.6 expected Son Daireler! on 4:5, 9:16, and 1:1")
    outsides = [
        int((feed_meta.get("pixel_delta") or {}).get("outside_changed_pixels", -1)),
        int((story_meta.get("pixel_delta") or {}).get("outside_changed_pixels", -1)),
        int((square_meta.get("pixel_delta") or {}).get("outside_changed_pixels", -1)),
    ]
    if any(value != 0 for value in outsides):
        raise RuntimeError("Phase 12.6 unrelated visual delta is not zero")

    feed_asset_id = _persist_child(db, user, row, feed_child, fmt=FEED_PORTRAIT)
    story_asset_id = _persist_child(db, user, row, story_child, fmt=STORY_REEL)
    square_asset_id = _persist_child(db, user, row, square_child, fmt=SQUARE)
    forbidden = {
        ASSET_4X5,
        ASSET_9X16,
        ASSET_1X1,
        APPROVED_ASSET_ID,
        APPROVED_ASSET_02,
        APPROVED_ASSET_03,
        SELECTED_ASSET_ID,
        PRICE_CHILD_9X16_ASSET,
        PRICE_CHILD_1X1_ASSET,
    }
    if {feed_asset_id, story_asset_id, square_asset_id} & forbidden:
        raise RuntimeError("Phase 12.6 refused to overwrite an approved original or a price child")
    if feed_asset_id in PRICE_CHILDREN or story_asset_id in PRICE_CHILDREN or square_asset_id in PRICE_CHILDREN:
        raise RuntimeError("Phase 12.6 children must not reuse $375.000 assets")

    attach_derived_revision(
        family["formats"][FEED_PORTRAIT],
        _child_record(
            revision_id=CHILD_4X5_ID,
            parent_master_id=MASTER_4X5_ID,
            parent_asset_id=ASSET_4X5,
            fmt=FEED_PORTRAIT,
            filename=FILE_4X5,
            visual_asset=feed_asset_id,
            meta=feed_meta,
        ),
    )
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

    feed_status = "PASS" if outsides[0] == 0 else "FAIL"
    story_status = "PASS" if outsides[1] == 0 else "FAIL"
    square_status = "PASS" if outsides[2] == 0 else "FAIL"
    landscape_status = SKIP_FORMAT_MASTER_MISSING
    overall = STATUS_PENDING if {feed_status, story_status, square_status} == {"PASS"} else STATUS_FAIL

    family["phase12_6_status"] = overall
    family["phase12_6_executed"] = True
    family["phase12_6_auto_approved"] = False
    library["phase12_6_executed"] = True
    library["phase12_6_status"] = overall
    library["next_production_phase"] = "HUMAN VISUAL REVIEW ONLY"

    for fmt, filename, asset_id, _master_id in (
        (FEED_PORTRAIT, FILE_4X5, ASSET_4X5, MASTER_4X5_ID),
        (STORY_REEL, FILE_9X16, ASSET_9X16, MASTER_9X16_ID),
        (SQUARE, FILE_1X1, ASSET_1X1, MASTER_1X1_ID),
    ):
        slot = family["formats"][fmt]
        ident = json.loads(json.dumps(_jsonable(_slot_identity(slot)), default=str))
        if ident != identities[fmt]:
            raise RuntimeError(f"Phase 12.6 mutated the {fmt} format master identity")
        live = _sha(_read_bytes(db, UUID(asset_id)))
        if live != sha_before[filename]:
            raise RuntimeError(f"Phase 12.6 mutated original {filename}")
        if str(slot.get("SOURCE_ASSET_ID")) in PRICE_CHILDREN:
            raise RuntimeError("Phase 12.6 replaced an original master with a $375 child")
    if family["formats"][LANDSCAPE].get("FORMAT_MASTER_ID") is not None:
        raise RuntimeError("Phase 12.6 fabricated 16:9")
    kids = []
    for fmt in (FEED_PORTRAIT, STORY_REEL, SQUARE):
        kids.extend(family["formats"][fmt].get("derived_revisions") or [])
    copy_kids = [item for item in kids if item.get("revision_id") in {CHILD_4X5_ID, CHILD_9X16_ID, CHILD_1X1_ID}]
    if any(item.get("approval_status") == "HUMAN_APPROVED" for item in copy_kids):
        raise RuntimeError("Phase 12.6 must not auto-approve revision children")
    if any(item.get("router_eligible") for item in copy_kids):
        raise RuntimeError("Phase 12.6 children must not be router eligible")
    if any(str(item.get("parent_asset_id")) in {PRICE_CHILD_9X16_ASSET, PRICE_CHILD_1X1_ASSET} for item in copy_kids):
        raise RuntimeError("Phase 12.6 parents must be original format masters")

    ornek_after = next(item for item in library["premium_creative_families"] if str(item.get("FAMILY_ID")) == ORNEK_FAMILY_ID)
    if dict(ornek_after.get("inventory") or {}) != ornek_inventory_before:
        raise RuntimeError("Phase 12.6 refused to alter the ORNEK_00013 inventory")
    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.6 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.6 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.6 refused to mutate Master 03")
    if count_approved_premium(library) != approved_count_before:
        raise RuntimeError("Phase 12.6 must not create another library Premium Master")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.6 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.6 refused to rewrite the product model")
    if (blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")) != cover_before:
        raise RuntimeError("Phase 12.6 refused to change production cover")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.6 must not call GPT Image")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["phase12_1_approval_tests"] = preserved.get("quality121")
    blob["phase12_2_family_lock_tests"] = preserved.get("quality122")
    blob["phase12_3_family_ingest_tests"] = preserved.get("quality123")
    blob["phase12_4_family_approval_tests"] = preserved.get("quality124")
    blob["phase12_5_family_wide_revision_tests"] = preserved.get("quality125")
    blob["phase12_5_r1_revision_lock_tests"] = preserved.get("quality125r1")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    lineage = {
        "schema": "FamilyWideCopyRevisionLineageV1",
        "FAMILY_ID": FAMILY_ID,
        "command": PHASE_12_6_COMMAND,
        "classified_intent": FAMILY_WIDE_REVISION,
        "REVISION_TYPE": REVISION_TYPE,
        "OLD_VALUE": OLD_COPY,
        "NEW_VALUE": NEW_COPY,
        "parents_are_original_masters": True,
        "parents_are_price_revision_children": False,
        "parent_assets": parent_assets,
        "children": [
            {
                "format": FEED_PORTRAIT,
                "revision_id": CHILD_4X5_ID,
                "PARENT_FORMAT_MASTER_ID": MASTER_4X5_ID,
                "parent_asset_id": ASSET_4X5,
                "visual_asset": feed_asset_id,
                "approval_status": "DRAFT",
                "router_eligible": False,
            },
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
        "skipped": [{"format": LANDSCAPE, "reason": SKIP_FORMAT_MASTER_MISSING}],
        "original_masters_modified": False,
        "auto_approved": False,
    }
    delta = {
        "schema": "FamilyWideCopyRevisionDeltaV1",
        "UNRELATED_VISUAL_DELTA": 0,
        "formats": {
            FEED_PORTRAIT: feed_meta.get("pixel_delta"),
            STORY_REEL: story_meta.get("pixel_delta"),
            SQUARE: square_meta.get("pixel_delta"),
            LANDSCAPE: {"skipped": True, "reason": SKIP_FORMAT_MASTER_MISSING},
        },
        "original_sha256": sha_before,
        "original_sha256_after": {
            FILE_4X5: _sha(_read_bytes(db, UUID(ASSET_4X5))),
            FILE_9X16: _sha(_read_bytes(db, UUID(ASSET_9X16))),
            FILE_1X1: _sha(_read_bytes(db, UUID(ASSET_1X1))),
        },
        "price_revision_children_not_used_as_parents": True,
    }
    images = {
        "feed_pair": render_before_after(
            parents[FEED_PORTRAIT],
            feed_child,
            title="01  4:5 BEFORE | AFTER  —  COPY_ONLY  Son Daireler! → Son Fırsatlar!",
            subtitle="ORNEK_00012 original master. Independent last-units badge reconstruction.",
            tile=(720, 900),
        ),
        "story_pair": render_before_after(
            parents[STORY_REEL],
            story_child,
            title="02  9:16 BEFORE | AFTER  —  COPY_ONLY  Son Daireler! → Son Fırsatlar!",
            subtitle="ORNEK_00005 original master. $357.000 and early-delivery circle preserved.",
            tile=(480, 854),
        ),
        "square_pair": render_before_after(
            parents[SQUARE],
            square_child,
            title="03  1:1 BEFORE | AFTER  —  COPY_ONLY  Son Daireler! → Son Fırsatlar!",
            subtitle="ORNEK_00003 original master. $357.000 / %40 / rent preserved.",
            tile=(720, 720),
        ),
        "family_board": render_family_before_after_board(
            parents[FEED_PORTRAIT],
            feed_child,
            parents[STORY_REEL],
            story_child,
            parents[SQUARE],
            square_child,
            feed_meta=feed_meta,
            story_meta=story_meta,
            square_meta=square_meta,
            feed_status=feed_status,
            story_status=story_status,
            square_status=square_status,
        ),
        "feed_after": feed_child,
        "story_after": story_child,
        "square_after": square_child,
        "feed_before": parents[FEED_PORTRAIT],
        "story_before": parents[STORY_REEL],
        "square_before": parents[SQUARE],
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_6,
        "created_at": _now(),
        "PHASE": "12.6 FAMILY-WIDE COPY REVISION PROOF",
        "status": overall,
        "command": PHASE_12_6_COMMAND,
        "REVISION_TYPE": REVISION_TYPE,
        "OLD_VALUE": OLD_COPY,
        "NEW_VALUE": NEW_COPY,
        "FAMILY_ID": FAMILY_ID,
        "FAMILY": CAMPAIGN_NAME,
        "PROJECT / BRAND": PROJECT_NAME,
        "4:5": feed_status,
        "9:16": story_status,
        "1:1": square_status,
        "16:9": landscape_status,
        "ORIGINAL MASTERS MODIFIED": "NO",
        "UNRELATED VISUAL DELTA": 0,
        "GPT IMAGE CALLS": provider_call_count(),
        "IDEOGRAM CALLS": 0,
        "APPROVAL": "PENDING HUMAN REVIEW",
        "classified": classified,
        "route": {**wide, "executed": True, "territory": REVISION_TYPE},
        "feed_meta": {k: v for k, v in feed_meta.items() if k != "type_mask"},
        "story_meta": {k: v for k, v in story_meta.items() if k != "type_mask"},
        "square_meta": {k: v for k, v in square_meta.items() if k != "type_mask"},
        "lineage": lineage,
        "delta": delta,
        "child_4x5_asset": feed_asset_id,
        "child_9x16_asset": story_asset_id,
        "child_1x1_asset": square_asset_id,
        "ORNEK_00013_FAMILY_ID": ORNEK_FAMILY_ID,
        "cover": PRODUCTION_COVER_V2,
        "language": language,
        "temple_project_id": TEMPLE_PROJECT_ID,
        "images": images,
    }
    tests_log = list(blob.get("phase12_6_family_copy_revision_tests") or [])
    tests_log.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "images"}), default=str)))
    blob["phase12_6_family_copy_revision_tests"] = tests_log
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
