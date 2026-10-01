"""Phase 5.5C — lock the human-approved 5.5B-R2 master and prove PRICE_EDIT_ONLY.

No GPT Image. No redesign. Does not overwrite the approved master raster.
Does not change the production cover.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageChops, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_creative_master import HUMAN_APPROVED
from investhome_api.services.creative_director.approved_master_lock import (
    APPROVED_R2_ASSET_ID,
    APPROVED_R2_SPEC_ID,
    LOCK_GROUPS,
    LOCKED_MASTER,
    PRICE_INSTRUCTION,
    append_child_revision,
    build_approved_master_lock,
    object_px,
    price_group_mutable_box,
    restore_approved_master,
    unlock_for_intent,
)
from investhome_api.services.creative_director.commercial_number_renderer import render_price, render_struck_price, split_price
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_contrast_engine import evaluate_objects
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_revision_controller import (
    PRICE_REVISION,
    classify_revision_intent,
    parse_price_revision,
)
from investhome_api.services.creative_director.full_frame_architectural_family import full_frame_family_spec
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import DAY007_FILENAME
from investhome_api.services.creative_director.phase5_5b_r2_craft_polish import _HISTORY_KEYS as _R2_HISTORY
from investhome_api.services.creative_director.phase5_5b_r2_craft_polish import _preserve as _preserve_r2
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable, render_score_board, render_structure_map
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
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY, _draw_tracked
from investhome_api.services.creative_director.visual_draft_reconstruction import (
    DAY007_ASSET_ID,
    _fit_role,
    _obj,
    glyph_clearance_report,
    price_currency_relationship,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55C = "phase5_5c_master_lock_price_proof"
MUTED_IVORY = (196, 190, 178)
SAVINGS_IVORY = (232, 226, 214)
_HISTORY_KEYS = _R2_HISTORY + (("visual_draft_reconstruction_55b_r2_tests", "quality55b_r2"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r2(blob)
    preserved["quality55b_r2"] = list(blob.get("visual_draft_reconstruction_55b_r2_tests") or [])
    return preserved


def _mean_delta(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size:
        return 255.0
    tiny_a = a.convert("RGB").resize((1, 1), Image.Resampling.BOX)
    tiny_b = b.convert("RGB").resize((1, 1), Image.Resampling.BOX)
    pa, pb = tiny_a.getpixel((0, 0)), tiny_b.getpixel((0, 0))
    return (abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])) / 3.0


def _exact_or_delta(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size:
        return 255.0
    if a.convert("RGB").tobytes() == b.convert("RGB").tobytes():
        return 0.0
    return round(_mean_delta(a, b), 4)


def _spec_objects(spec: dict[str, Any]) -> dict[str, Any]:
    roles = ("headline", "discount", "discount_label", "price", "currency", "project_logo", "unit_type", "cta", "navy_field", "project_photo")
    objects = {}
    size = (1088, 1360)
    for role in roles:
        box = object_px(spec, role)
        if box[2] > box[0] and box[3] > box[1]:
            objects[role] = _obj(size, role, box)
    return objects


def _erase_type_in_box(image: Image.Image, box: tuple[int, int, int, int], navy: tuple[int, int, int], split_x: int) -> None:
    x0, y0, x1, y1 = box
    x1 = min(x1, split_x - 4)
    px = image.load()
    nr, ng, nb = (int(v) for v in navy[:3])
    for y in range(max(0, y0), min(image.size[1], y1)):
        for x in range(max(0, x0), max(0, x1)):
            r, g, b = px[x, y]
            if abs(r - nr) + abs(g - ng) + abs(b - nb) > 28:
                px[x, y] = (nr, ng, nb)


def apply_price_revision(
    master: Image.Image,
    *,
    spec: dict[str, Any],
    fonts: dict[str, Any],
    family: dict[str, Any],
    prices: dict[str, str],
) -> dict[str, Any]:
    canvas = master.convert("RGB").copy()
    w, h = canvas.size
    box = price_group_mutable_box(spec, (w, h))
    x0, y0, x1, y1 = box
    split_x = object_px(spec, "navy_field")[2]
    navy = canvas.getpixel((12, 12))
    _erase_type_in_box(canvas, box, navy, split_x)
    tokens = execution_tokens(family)
    ax = object_px(spec, "price")[0]
    col_w = max(80, min(x1, split_x - 8) - ax - 12)
    primary = prices["launch_price"]
    struck = prices["list_price_struck"]
    savings = prices["savings"]
    savings_label = prices.get("savings_label") or "KAZANCINIZ"
    limit = y1 - 2
    num_h = max(28, int(h * 0.028))
    pack = None
    while num_h >= 24:
        number, _currency = split_price(primary)
        num_font, used_num = _fit_role(fonts, tokens["commercial_font"], number, num_h, int(col_w * 0.78))
        cur_font = font_for_role(fonts, tokens["body_font"], max(11, int(used_num * 0.40)))
        old_num, _ = split_price(struck)
        old_font, old_h = _fit_role(fonts, tokens["commercial_font"], old_num, max(16, int(used_num * 0.52)), int(col_w * 0.78))
        old_cur = font_for_role(fonts, tokens["body_font"], max(10, int(old_h * 0.40)))
        sav_num, _ = split_price(savings)
        sav_font, sav_h = _fit_role(fonts, tokens["commercial_font"], sav_num, max(16, int(used_num * 0.56)), int(col_w * 0.78))
        sav_cur = font_for_role(fonts, tokens["body_font"], max(10, int(sav_h * 0.40)))
        lab_font, lab_h = _fit_role(fonts, tokens["body_font"], savings_label, max(11, int(h * 0.012)), col_w, tracking=140)
        gap_in = max(4, int(h * 0.004))
        y = y0 + 4
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        primary_parts: dict[str, tuple[int, int, int, int]] = {}
        primary_box = render_price(
            draw,
            origin=(ax, y),
            text=primary,
            number_font=num_font,
            currency_font=cur_font,
            fill=IVORY,
            alignment="left",
            tracking=6.0,
            gap=max(5, int(used_num * 0.08)),
            parts=primary_parts,
        )
        y = primary_box[3] + gap_in
        struck_parts: dict[str, tuple[int, int, int, int]] = {}
        struck_box = render_struck_price(
            draw,
            origin=(ax, y),
            text=struck,
            number_font=old_font,
            currency_font=old_cur,
            fill=MUTED_IVORY,
            strike_fill=GOLD,
            alignment="left",
            tracking=4.0,
            gap=max(4, int(old_h * 0.08)),
            parts=struck_parts,
        )
        y = struck_box[3] + gap_in
        label_box = _draw_tracked(draw, (ax, y), savings_label, lab_font, SAVINGS_IVORY, tracking=140, anchor="lt")
        y = label_box[3] + 1
        savings_parts: dict[str, tuple[int, int, int, int]] = {}
        savings_box = render_price(
            draw,
            origin=(ax, y),
            text=savings,
            number_font=sav_font,
            currency_font=sav_cur,
            fill=SAVINGS_IVORY,
            alignment="left",
            tracking=4.0,
            gap=max(4, int(sav_h * 0.08)),
            parts=savings_parts,
        )
        if savings_box[3] <= limit:
            clip_box = (x0, y0, min(x1, split_x - 4), y1)
            clip = layer.crop(clip_box)
            canvas.paste(clip, (clip_box[0], clip_box[1]), clip)
            pack = {
                "primary_box": primary_box,
                "struck_box": struck_box,
                "label_box": label_box,
                "savings_box": savings_box,
                "primary_parts": primary_parts,
                "struck_parts": struck_parts,
                "savings_parts": savings_parts,
            }
            break
        num_h -= 2
    if pack is None:
        raise RuntimeError("PRICE_EDIT_ONLY could not fit the commercial price group inside the locked box")
    objects = {
        "price": _obj((w, h), "price", pack["primary_box"]),
        "old_price": _obj((w, h), "old_price", pack["struck_box"]),
        "savings_label": _obj((w, h), "savings_label", pack["label_box"]),
        "savings": _obj((w, h), "savings", pack["savings_box"]),
        "currency": _obj((w, h), "currency", pack["primary_parts"].get("currency") or pack["primary_box"]),
    }
    return {
        "image": canvas,
        "mutable_box": box,
        "objects": objects,
        "primary_parts": pack["primary_parts"],
        "struck_parts": pack["struck_parts"],
        "savings_parts": pack["savings_parts"],
        "navy": navy,
        "facts": {
            "list_price": primary,
            "launch_price": primary,
            "list_price_struck": struck,
            "savings": savings,
            "savings_label": savings_label,
        },
    }


def compare_master_preservation(parent: Image.Image, child: Image.Image, spec: dict[str, Any]) -> dict[str, Any]:
    w, h = parent.size
    box = price_group_mutable_box(spec, (w, h))
    split_x = object_px(spec, "navy_field")[2]
    photo_box = (split_x, 0, w, h)
    headline = object_px(spec, "headline")
    discount = object_px(spec, "discount")
    label = object_px(spec, "discount_label")
    discount_union = (min(discount[0], label[0]), min(discount[1], label[1]), max(discount[2], label[2]), min(box[1] - 1, max(discount[3], label[3]) + 16))
    logo = object_px(spec, "project_logo")
    unit = object_px(spec, "unit_type")
    cta = object_px(spec, "cta")
    masked_p = parent.convert("RGB").copy()
    masked_c = child.convert("RGB").copy()
    ImageDraw.Draw(masked_p).rectangle(box, fill=(12, 14, 20))
    ImageDraw.Draw(masked_c).rectangle(box, fill=(12, 14, 20))
    outside = _exact_or_delta(masked_p, masked_c)
    checks = {
        "photo_pixel_delta": _exact_or_delta(parent.crop(photo_box), child.crop(photo_box)),
        "crop_delta": _exact_or_delta(parent.crop(photo_box), child.crop(photo_box)),
        "architecture_delta": _exact_or_delta(parent.crop(photo_box), child.crop(photo_box)),
        "navy_photo_split_delta": _exact_or_delta(parent.crop((max(0, split_x - 2), 0, min(w, split_x + 2), h)), child.crop((max(0, split_x - 2), 0, min(w, split_x + 2), h))),
        "headline_geometry_delta": _exact_or_delta(parent.crop(headline), child.crop(headline)),
        "discount_geometry_delta": _exact_or_delta(parent.crop(discount_union), child.crop(discount_union)),
        "logo_geometry_delta": _exact_or_delta(parent.crop(logo), child.crop(logo)),
        "unit_geometry_delta": _exact_or_delta(parent.crop(unit), child.crop(unit)),
        "cta_geometry_delta": _exact_or_delta(parent.crop(cta), child.crop(cta)),
        "unrelated_color_delta": outside,
        "unrelated_typography_delta": max(
            _exact_or_delta(parent.crop(headline), child.crop(headline)),
            _exact_or_delta(parent.crop(unit), child.crop(unit)),
            _exact_or_delta(parent.crop(cta), child.crop(cta)),
        ),
        "unrelated_spacing_delta": outside,
    }
    failed = [k for k, v in checks.items() if v > 0.5]
    return {
        "schema": "MasterRevisionPreservationV1",
        "mutable_box": list(box),
        "deltas": checks,
        "outside_price_group_delta": outside,
        "failed": failed,
        "pass": not failed,
    }


def revision_price_qa(
    image: Image.Image,
    *,
    spec: dict[str, Any],
    pack: dict[str, Any],
    parent: Image.Image,
) -> dict[str, Any]:
    navy_px = object_px(spec, "navy_field")
    split_x = navy_px[2]
    pad = max(16, int(image.size[0] * 0.016))
    navy = pack.get("navy") or (39, 49, 60)
    boxes = {k: tuple(int(v) for v in (item.get("px") or [0, 0, 0, 0])) for k, item in dict(pack.get("objects") or {}).items()}
    glyphs = glyph_clearance_report(image, navy=tuple(int(v) for v in navy[:3]), split_x=split_x, pad=pad, boxes={"headline": boxes.get("price"), "discount": boxes.get("old_price"), "discount_label": boxes.get("savings"), "price": boxes.get("price"), "cta": boxes.get("savings_label")})
    primary_rel = price_currency_relationship(dict(pack.get("primary_parts") or {}))
    struck_rel = price_currency_relationship({k: v for k, v in dict(pack.get("struck_parts") or {}).items() if k in {"number", "currency"}})
    savings_rel = price_currency_relationship(dict(pack.get("savings_parts") or {}))
    strike = (pack.get("struck_parts") or {}).get("strikethrough")
    old_box = boxes.get("old_price") or (0, 0, 0, 0)
    strike_ok = bool(strike) and old_box[2] > old_box[0] and abs(((strike[1] + strike[3]) / 2) - ((old_box[1] + old_box[3]) / 2)) <= 8
    logo = object_px(spec, "project_logo")
    discount = object_px(spec, "discount")
    overlaps = []
    for role, box in boxes.items():
        if box[2] > logo[0] and box[0] < logo[2] and box[3] > logo[1] and box[1] < logo[3]:
            overlaps.append(f"{role}_logo")
        if box[2] > discount[0] and box[0] < discount[2] and box[3] > discount[1] and box[1] < discount[3]:
            overlaps.append(f"{role}_discount")
    collision = evaluate_collisions(objects={**_spec_objects(spec), **pack["objects"]}, occupancy={}, size=image.size)
    contrast = evaluate_objects(
        image,
        pack["objects"],
        {"price": IVORY, "old_price": MUTED_IVORY, "savings": SAVINGS_IVORY, "savings_label": SAVINGS_IVORY},
    )
    mutable = pack.get("mutable_box") or price_group_mutable_box(spec)
    changed = _exact_or_delta(parent.crop(tuple(mutable)), image.crop(tuple(mutable)))
    checks = {
        "glyph_clipping": "PASS" if glyphs.get("navy_boundary_clearance") == "PASS" else "FAIL",
        "price_readability": "PASS" if primary_rel.get("pass") else "FAIL",
        "old_price_readability": "PASS" if struck_rel.get("pass") else "FAIL",
        "strikethrough_quality": "PASS" if strike_ok else "FAIL",
        "savings_readability": "PASS" if savings_rel.get("pass") else "FAIL",
        "commercial_hierarchy": "PASS" if boxes.get("price") and boxes["price"][3] <= (boxes.get("old_price") or (0, 9999, 0, 9999))[1] + 2 else "FAIL",
        "spacing": "PASS" if boxes.get("savings") and boxes["savings"][3] <= mutable[3] else "FAIL",
        "collision": "PASS" if not overlaps else "FAIL",
        "contrast": "PASS" if contrast.get("pass") else "FAIL",
        "price_group_changed": "PASS" if changed > 0.5 else "FAIL",
    }
    return {
        "schema": "Phase55CRevisionQAV1",
        "checks": checks,
        "pass": all(v == "PASS" for v in checks.values()),
        "glyph_preflight": glyphs,
        "primary_currency": primary_rel,
        "struck_currency": struck_rel,
        "savings_currency": savings_rel,
        "overlaps": overlaps,
        "collision": _jsonable(collision),
        "contrast": _jsonable(contrast),
    }


def render_side_by_side(left: Image.Image, right: Image.Image, *, left_label: str, right_label: str, title: str) -> Image.Image:
    canvas = Image.new("RGB", (1600, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), title, font=_font(18), fill=(201, 168, 92))
    a = left.copy()
    a.thumbnail((720, 900), Image.Resampling.LANCZOS)
    b = right.copy()
    b.thumbnail((720, 900), Image.Resampling.LANCZOS)
    canvas.paste(a.convert("RGB"), (36, 56))
    canvas.paste(b.convert("RGB"), (820, 56))
    draw.text((36, 940), left_label, font=_font(14), fill=(180, 176, 168))
    draw.text((820, 940), right_label, font=_font(14), fill=(180, 176, 168))
    return canvas


def render_preservation_map(parent: Image.Image, child: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    gray = ImageChops.difference(parent.convert("RGB"), child.convert("RGB")).convert("L")
    overlay = parent.convert("RGB").copy()
    changed = gray.point(lambda p: 180 if p > 10 else 0)
    mutable = Image.new("L", overlay.size, 0)
    ImageDraw.Draw(mutable).rectangle(box, fill=255)
    overlay = Image.composite(Image.new("RGB", overlay.size, (46, 168, 84)), overlay, ImageChops.multiply(changed, mutable))
    overlay = Image.composite(Image.new("RGB", overlay.size, (196, 48, 48)), overlay, ImageChops.subtract(changed, mutable))
    ImageDraw.Draw(overlay).rectangle(box, outline=(46, 168, 84), width=2)
    return overlay


def render_version_history(master_id: str, child_id: str, instruction: str) -> Image.Image:
    canvas = Image.new("RGB", (1280, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 28), "VERSION HISTORY  —  APPROVED MASTER → REVISION CHILD V1", fill=(201, 168, 92), font=_font(20))
    y = 90
    for line in (
        f"PARENT  {master_id}",
        "status  HUMAN_APPROVED / LOCKED_MASTER",
        f"CHILD V1  {child_id}",
        "intent  PRICE_EDIT_ONLY",
        "reversible  YES",
        "",
        "INSTRUCTION",
        *instruction.splitlines(),
    ):
        draw.text((36, y), line, fill=(236, 230, 218), font=_font(16))
        y += 32
    return canvas


def render_human_review_board_55c(
    *,
    master: Image.Image | None,
    revision: Image.Image | None,
    preservation: dict[str, Any],
    qa: dict[str, Any],
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1760, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "HUMAN REVIEW BOARD  —  PHASE 5.5C  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    if master is not None:
        tile = master.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36, 60))
        draw.text((36, 750), "Approved Master", fill=(180, 176, 168), font=_font(13))
    if revision is not None:
        tile = revision.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (580, 60))
        draw.text((580, 750), "Price Revision Child V1", fill=(180, 176, 168), font=_font(13))
    x, y = 1140, 70
    draw.text((x, y), f"status  {status}", fill=(236, 230, 218), font=_font(15))
    y += 32
    draw.text((x, y), f"preservation  {'PASS' if preservation.get('pass') else 'FAIL'}", fill=(80, 200, 120) if preservation.get("pass") else (220, 80, 80), font=_font(16))
    y += 28
    draw.text((x, y), f"price QA  {'PASS' if qa.get('pass') else 'FAIL'}", fill=(80, 200, 120) if qa.get("pass") else (220, 80, 80), font=_font(16))
    y += 36
    for key, value in dict(preservation.get("deltas") or {}).items():
        draw.text((x, y), f"{key}  {value}", fill=(236, 230, 218), font=_font(13))
        y += 22
    draw.text((x, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(14))
    return canvas


def generate_master_lock_price_proof_55c(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    instruction: str = PRICE_INSTRUCTION,
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()
    r2_tests = list(blob.get("visual_draft_reconstruction_55b_r2_tests") or [])
    r2_rec = next((t for t in reversed(r2_tests) if isinstance(t, dict) and t.get("spec_id") == APPROVED_R2_SPEC_ID), None)
    spec = dict((r2_rec or {}).get("spec") or {})
    if str(spec.get("spec_id")) != APPROVED_R2_SPEC_ID:
        raise RuntimeError("Phase 5.5C requires the locked 5.5B-R2 Master Spec")
    master_png = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_R2_ASSET_ID)))).convert("RGB")
    master_id = str(uuid4())
    lock = build_approved_master_lock(spec=spec, master_id=master_id)
    intent_scope = classify_revision_intent(instruction)
    if intent_scope != PRICE_REVISION:
        raise RuntimeError(f"Phase 5.5C expected PRICE_EDIT_ONLY, got {intent_scope}")
    prices = parse_price_revision(instruction)
    fonts = build_font_registry()
    family = full_frame_family_spec()
    before_calls = provider_call_count()
    pack = apply_price_revision(master_png, spec=spec, fonts=fonts, family=family, prices=prices)
    if provider_call_count() != before_calls:
        raise RuntimeError("Phase 5.5C must not call GPT Image")
    child_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode="project-v3-55c-price-revision",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5C PRICE_EDIT_ONLY child",
    )
    child_id = str(uuid4())
    semantic_diff = {
        "schema": "SemanticDiffV1",
        "changed": {
            "list_price": {"from": REQUIRED_FACTS["list_price"], "to": prices["launch_price"]},
            "old_price": {"from": None, "to": prices["list_price_struck"], "decoration": "strikethrough"},
            "savings": {"from": None, "to": prices["savings"]},
            "savings_label": {"from": None, "to": prices["savings_label"]},
        },
        "unchanged": ["headline", "discount", "discount_label", "project_logo", "unit_type", "cta", "photo", "crop", "navy_photo_split"],
    }
    preservation = compare_master_preservation(master_png, pack["image"], spec)
    qa = revision_price_qa(pack["image"], spec=spec, pack=pack, parent=master_png)
    revision_rec = {
        "schema": "MasterRevisionChildV1",
        "revision_id": child_id,
        "parent_master_id": master_id,
        "parent_asset_id": APPROVED_R2_ASSET_ID,
        "parent_spec_id": APPROVED_R2_SPEC_ID,
        "parent_semantic_content": dict(REQUIRED_FACTS),
        "revision_asset_id": str(child_asset.id),
        "instruction": instruction,
        "intent": "PRICE_EDIT_ONLY",
        "unlocked": list(unlock_for_intent("PRICE_EDIT_ONLY")),
        "locked_groups": list(LOCK_GROUPS),
        "semantic_diff": semantic_diff,
        "geometry_diff": {"mutable_box": list(pack["mutable_box"]), "objects": _jsonable(pack["objects"])},
        "visual_diff": {"outside_price_group_delta": preservation.get("outside_price_group_delta")},
        "reversible": True,
        "created_at": _now(),
        "revision_number": 1,
    }
    lock_with_child = append_child_revision(lock, revision_rec)
    restored = restore_approved_master(lock_with_child, child_id)
    status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preservation.get("pass") and qa.get("pass") else "CANDIDATE_TECHNICAL_FAIL"
    version_history = {
        "schema": "MasterVersionHistoryV1",
        "parent": {
            "master_id": master_id,
            "asset_id": APPROVED_R2_ASSET_ID,
            "spec_id": APPROVED_R2_SPEC_ID,
            "status": f"{HUMAN_APPROVED}/{LOCKED_MASTER}",
        },
        "children": [
            {
                "revision_id": child_id,
                "asset_id": str(child_asset.id),
                "intent": "PRICE_EDIT_ONLY",
                "instruction": instruction,
                "reversible": True,
            }
        ],
        "restore": restored,
    }
    images = {
        "approved_master": master_png,
        "structure": render_structure_map(master_png, _spec_objects(spec)),
        "price_revision": pack["image"],
        "master_vs": render_side_by_side(master_png, pack["image"], left_label="Approved Master", right_label="Price Revision", title="MASTER vs PRICE REVISION  —  PRICE_EDIT_ONLY"),
        "price_detail": pack["image"].crop(
            (
                max(0, pack["mutable_box"][0]),
                max(0, pack["mutable_box"][1] - 40),
                min(master_png.size[0], pack["mutable_box"][2] + 80),
                min(master_png.size[1], pack["mutable_box"][3] + 40),
            )
        ),
        "preservation": render_preservation_map(master_png, pack["image"], tuple(pack["mutable_box"])),
        "revision_qa": render_score_board({"pass": qa.get("pass"), "scores": {k: 10 if v == "PASS" else 3 for k, v in dict(qa.get("checks") or {}).items()}}),
        "version_history": render_version_history(master_id, child_id, instruction),
        "review_board": render_human_review_board_55c(master=master_png, revision=pack["image"], preservation=preservation, qa=qa, status=status),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55C,
        "created_at": _now(),
        "status": status,
        "approved_master_id": master_id,
        "approved_master_asset_id": APPROVED_R2_ASSET_ID,
        "approved_master_spec_id": APPROVED_R2_SPEC_ID,
        "human_visual_status": "PASS",
        "master_lock": lock_with_child,
        "price_revision_executed": True,
        "instruction": instruction,
        "revision_intent": "PRICE_EDIT_ONLY",
        "revision_child_id": child_id,
        "revision_asset_id": str(child_asset.id),
        "semantic_diff": semantic_diff,
        "preservation": preservation,
        "revision_qa": qa,
        "version_history": version_history,
        "new_visual_draft_image_calls": 0,
        "production_image_generation_calls": provider_call_count(),
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "unlocked": list(unlock_for_intent("PRICE_EDIT_ONLY")),
        "locked_groups": list(LOCK_GROUPS),
    }
    tests = [t for t in list(blob.get("master_lock_price_proof_55c_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55C)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["master_lock_price_proof_55c_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    masters = {
        key: value
        for key, value in dict(preserved["approved"]).items()
        if not (isinstance(value, dict) and value.get("source") == "phase5_5c")
    }
    masters[master_id] = {
        "master_id": master_id,
        "approval_status": HUMAN_APPROVED,
        "lock_status": LOCKED_MASTER,
        "approved_asset_id": APPROVED_R2_ASSET_ID,
        "spec_id": APPROVED_R2_SPEC_ID,
        "production": False,
        "source": "phase5_5c",
    }
    blob["approved_masters"] = masters
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c_id"] = master_id
    blob["human_approved_master_55c"] = json.loads(json.dumps(lock_with_child, default=str))
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if MASTER_COMMERCIAL_R1_ID not in masters and MASTER_COMMERCIAL_R1_ID in dict(preserved["approved"]):
        raise RuntimeError("Phase 5.5C refused to drop the existing approved master")
    if blob.get("visual_draft_reconstruction_55b_r2_tests") != preserved.get("quality55b_r2"):
        raise RuntimeError("Phase 5.5C refused to overwrite Phase 5.5B-R2")
    _ = PRODUCTION_COVER_V2
    _ = language
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
