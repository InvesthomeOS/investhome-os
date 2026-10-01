"""Phase 5.5C-R1 — price-group visual hierarchy correction.

Preservation engine unchanged. Only the commercial price group is reflowed.
No GPT Image. Does not overwrite the approved Master.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import (
    APPROVED_R2_ASSET_ID,
    APPROVED_R2_SPEC_ID,
    LOCK_GROUPS,
    PRICE_INSTRUCTION,
    append_child_revision,
    object_px,
    price_group_mutable_box,
    restore_approved_master,
    unlock_for_intent,
)
from investhome_api.services.creative_director.commercial_number_renderer import render_price, render_struck_price, split_price
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_font_registry import build_font_registry, font_for_role
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_revision_controller import PRICE_REVISION, classify_revision_intent, parse_price_revision
from investhome_api.services.creative_director.full_frame_architectural_family import full_frame_family_spec
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_master_lock_price_proof import (
    MUTED_IVORY,
    SAVINGS_IVORY,
    WORKFLOW_ID_55C,
    _HISTORY_KEYS as _C_HISTORY,
    _erase_type_in_box,
    _preserve as _preserve_c,
    compare_master_preservation,
    render_human_review_board_55c,
    render_preservation_map,
    render_side_by_side,
)
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable, render_score_board
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
    _text_width,
    glyph_clearance_report,
    price_currency_relationship,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55C_R1 = "phase5_5c_r1_price_hierarchy"
PARENT_MASTER_ID = "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
FAILED_REVISION_ID = "997695c6-15f8-4edd-9146-f649c7554155"
FAILED_REVISION_ASSET_ID = "b9345b34-585d-4981-94f4-bda39fb6331b"
_HISTORY_KEYS = _C_HISTORY + (("master_lock_price_proof_55c_tests", "quality55c"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_c(blob)
    preserved["quality55c"] = list(blob.get("master_lock_price_proof_55c_tests") or [])
    preserved["human_master"] = dict(blob.get("human_approved_master_55c") or {})
    preserved["human_master_id"] = blob.get("human_approved_master_55c_id")
    return preserved


def _box_h(box: tuple[int, int, int, int]) -> int:
    return max(1, int(box[3]) - int(box[1]))


def _box_union(*boxes: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    xs0, ys0, xs1, ys1 = zip(*boxes)
    return (min(xs0), min(ys0), max(xs1), max(ys1))


def commercial_ink_mass(image: Image.Image, box: tuple[int, int, int, int], navy: tuple[int, int, int]) -> int:
    x0, y0, x1, y1 = (int(v) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(image.size[0], x1), min(image.size[1], y1)
    if x1 <= x0 or y1 <= y0:
        return 0
    px = image.convert("RGB").load()
    nr, ng, nb = (int(v) for v in navy[:3])
    count = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            if abs(r - nr) + abs(g - ng) + abs(b - nb) > 28:
                count += 1
    return count


def commercial_group_mass_preservation(
    master: Image.Image,
    revised: Image.Image,
    *,
    original_box: tuple[int, int, int, int],
    primary_box: tuple[int, int, int, int],
    navy: tuple[int, int, int],
) -> dict[str, Any]:
    original_mass = commercial_ink_mass(master, original_box, navy)
    primary_mass = commercial_ink_mass(revised, primary_box, navy)
    ratio = (primary_mass / original_mass) if original_mass else 0.0
    return {
        "schema": "CommercialGroupMassPreservationV1",
        "original_price_box": list(original_box),
        "primary_price_box": list(primary_box),
        "original_ink_px": original_mass,
        "primary_ink_px": primary_mass,
        "primary_price_mass_ratio": round(ratio, 4),
        "pass": ratio >= 0.85,
    }


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int], pad: int = 0) -> bool:
    return a[0] < b[2] - pad and b[0] < a[2] - pad and a[1] < b[3] - pad and b[1] < a[3] - pad


def apply_price_hierarchy(
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
    original_price = object_px(spec, "price")
    original_currency = object_px(spec, "currency")
    original_union = _box_union(original_price, original_currency) if original_currency[2] > original_currency[0] else original_price
    _erase_type_in_box(canvas, box, navy, split_x)
    tokens = execution_tokens(family)
    ax = original_price[0]
    col_w = max(120, min(x1, split_x - 10) - ax - 10)
    primary = prices["launch_price"]
    struck = prices["list_price_struck"]
    savings = prices["savings"]
    savings_label = prices.get("savings_label") or "KAZANCINIZ"
    orig_h = max(46, _box_h(original_price))
    floor = max(40, int(orig_h * 0.85))
    pack = None
    primary_size = orig_h
    while primary_size >= floor:
        number, _ = split_price(primary)
        num_font, used = _fit_role(fonts, tokens["commercial_font"], number, primary_size, col_w)
        if used < floor:
            primary_size -= 1
            continue
        cur_font = font_for_role(fonts, tokens["body_font"], max(13, int(used * 0.42)))
        old_target = max(24, int(used * 0.55))
        old_num, _ = split_price(struck)
        old_font, old_h = _fit_role(fonts, tokens["commercial_font"], old_num, old_target, col_w)
        old_cur = font_for_role(fonts, tokens["body_font"], max(12, int(old_h * 0.42)))
        sav_target = max(22, int(used * 0.48))
        sav_num, _ = split_price(savings)
        sav_font, sav_h = _fit_role(fonts, tokens["commercial_font"], sav_num, sav_target, int(col_w * 0.62))
        sav_cur = font_for_role(fonts, tokens["body_font"], max(12, int(sav_h * 0.42)))
        lab_font, lab_h = _fit_role(fonts, tokens["body_font"], savings_label, max(13, int(h * 0.014)), col_w, tracking=70)
        gap_ab = max(6, int(h * 0.006))
        gap_bc = max(8, int(h * 0.007))
        probe = Image.new("RGBA", (w, 160), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        probe_box = render_price(
            probe_draw,
            origin=(ax, 40),
            text=primary,
            number_font=num_font,
            currency_font=cur_font,
            fill=IVORY,
            alignment="left",
            tracking=6.0,
            gap=max(6, int(used * 0.08)),
        )
        ink_top_offset = probe_box[1] - 40
        y = (y0 + 8) - ink_top_offset
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
            gap=max(6, int(used * 0.08)),
            parts=primary_parts,
        )
        y = primary_box[3] + gap_ab
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
            gap=max(5, int(old_h * 0.08)),
            parts=struck_parts,
        )
        y = struck_box[3] + gap_bc
        savings_parts: dict[str, tuple[int, int, int, int]] = {}
        label_w = int(_text_width(lab_font, savings_label, tracking=70, size=lab_h))
        amount_w = int(_text_width(sav_font, sav_num, tracking=4.0, size=sav_h)) + 48
        one_line = label_w + 12 + amount_w <= col_w
        if one_line:
            lab = _draw_tracked(draw, (ax, y + max(0, sav_h - lab_h - 4)), savings_label, lab_font, SAVINGS_IVORY, tracking=70, anchor="lt")
            savings_box = render_price(
                draw,
                origin=(lab[2] + max(10, int(used * 0.16)), y),
                text=savings,
                number_font=sav_font,
                currency_font=sav_cur,
                fill=IVORY,
                alignment="left",
                tracking=4.0,
                gap=max(5, int(sav_h * 0.08)),
                parts=savings_parts,
            )
            savings_union = _box_union(lab, savings_box)
            label_box = lab
        else:
            lab = _draw_tracked(draw, (ax, y), savings_label, lab_font, SAVINGS_IVORY, tracking=70, anchor="lt")
            y = lab[3] + 2
            savings_box = render_price(
                draw,
                origin=(ax, y),
                text=savings,
                number_font=sav_font,
                currency_font=sav_cur,
                fill=IVORY,
                alignment="left",
                tracking=4.0,
                gap=max(5, int(sav_h * 0.08)),
                parts=savings_parts,
            )
            savings_union = _box_union(lab, savings_box)
            label_box = lab
        if (
            savings_union[3] <= y1 - 2
            and primary_box[2] <= split_x - 16
            and struck_box[2] <= split_x - 16
            and savings_union[2] <= split_x - 16
        ):
            clip_box = (x0, y0, min(x1, split_x - 4), y1)
            clip = layer.crop(clip_box)
            canvas.paste(clip, (clip_box[0], clip_box[1]), clip)
            pack = {
                "primary_box": primary_box,
                "struck_box": struck_box,
                "label_box": label_box,
                "savings_box": savings_box,
                "savings_union": savings_union,
                "primary_parts": primary_parts,
                "struck_parts": struck_parts,
                "savings_parts": savings_parts,
                "one_line_savings": one_line,
                "primary_size": used,
                "old_size": old_h,
                "savings_size": sav_h,
                "label_size": lab_h,
            }
            break
        primary_size -= 1
    if pack is None:
        raise RuntimeError("PRICE hierarchy could not fit inside the locked price group")
    objects = {
        "price": _obj((w, h), "price", pack["primary_box"]),
        "old_price": _obj((w, h), "old_price", pack["struck_box"]),
        "savings": _obj((w, h), "savings", pack["savings_union"]),
        "currency": _obj((w, h), "currency", pack["primary_parts"].get("currency") or pack["primary_box"]),
    }
    mass = commercial_group_mass_preservation(
        master,
        canvas,
        original_box=original_union,
        primary_box=pack["primary_box"],
        navy=navy,
    )
    return {
        "image": canvas,
        "mutable_box": box,
        "objects": objects,
        "primary_parts": pack["primary_parts"],
        "struck_parts": pack["struck_parts"],
        "savings_parts": pack["savings_parts"],
        "label_box": pack["label_box"],
        "one_line_savings": pack["one_line_savings"],
        "sizes": {k: pack[k] for k in ("primary_size", "old_size", "savings_size", "label_size")},
        "navy": navy,
        "mass": mass,
        "original_price_box": original_union,
        "facts": {
            "list_price": primary,
            "launch_price": primary,
            "list_price_struck": struck,
            "savings": savings,
            "savings_label": savings_label,
        },
    }


def hierarchy_qa(image: Image.Image, *, spec: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    navy_px = object_px(spec, "navy_field")
    split_x = navy_px[2]
    pad = max(16, int(image.size[0] * 0.016))
    navy = pack.get("navy") or (39, 49, 60)
    boxes = {k: tuple(int(v) for v in (item.get("px") or [0, 0, 0, 0])) for k, item in dict(pack.get("objects") or {}).items()}
    mutable = tuple(pack.get("mutable_box") or price_group_mutable_box(spec))
    glyphs = glyph_clearance_report(
        image,
        navy=tuple(int(v) for v in navy[:3]),
        split_x=split_x,
        pad=pad,
        boxes={
            "headline": boxes.get("price"),
            "discount": boxes.get("old_price"),
            "discount_label": boxes.get("savings"),
            "price": boxes.get("price"),
            "cta": boxes.get("currency"),
        },
    )
    primary_rel = price_currency_relationship(dict(pack.get("primary_parts") or {}))
    struck_rel = price_currency_relationship({k: v for k, v in dict(pack.get("struck_parts") or {}).items() if k in {"number", "currency"}})
    savings_rel = price_currency_relationship(dict(pack.get("savings_parts") or {}))
    sizes = dict(pack.get("sizes") or {})
    strike = (pack.get("struck_parts") or {}).get("strikethrough")
    old_box = boxes.get("old_price") or (0, 0, 0, 0)
    strike_ok = bool(strike) and old_box[2] > old_box[0] and abs(((strike[1] + strike[3]) / 2) - ((old_box[1] + old_box[3]) / 2)) <= 8
    logo = object_px(spec, "project_logo")
    discount = object_px(spec, "discount")
    label = object_px(spec, "discount_label")
    internal_hit = _overlaps(boxes.get("price") or (0, 0, 0, 0), boxes.get("old_price") or (0, 0, 0, 0), pad=2) or _overlaps(
        boxes.get("old_price") or (0, 0, 0, 0), boxes.get("savings") or (0, 0, 0, 0), pad=2
    )
    outside = []
    for role, b in boxes.items():
        if role == "currency":
            continue
        if b[1] < mutable[1] - 1 or b[3] > mutable[3] + 1 or b[0] < mutable[0] or b[2] > mutable[2]:
            outside.append(role)
        if _overlaps(b, logo) or _overlaps(b, discount) or _overlaps(b, label):
            outside.append(f"{role}_locked")
    mass = dict(pack.get("mass") or {})
    readability = {
        "primary_price_readability": "PASS" if sizes.get("primary_size", 0) >= 40 and primary_rel.get("pass") else "FAIL",
        "old_price_readability": "PASS" if sizes.get("old_size", 0) >= 22 and struck_rel.get("pass") else "FAIL",
        "savings_readability": "PASS" if sizes.get("savings_size", 0) >= 20 and sizes.get("label_size", 0) >= 13 and savings_rel.get("pass") else "FAIL",
        "currency_readability": "PASS" if primary_rel.get("pass") and struck_rel.get("pass") and savings_rel.get("pass") else "FAIL",
    }
    checks = {
        "primary_price_clipping": "PASS" if glyphs.get("role_clear", {}).get("headline") else "FAIL",
        "old_price_clipping": "PASS" if glyphs.get("role_clear", {}).get("discount") else "FAIL",
        "savings_clipping": "PASS" if glyphs.get("role_clear", {}).get("discount_label") else "FAIL",
        "price_internal_collision": "PASS" if not internal_hit else "FAIL",
        "strikethrough_alignment": "PASS" if strike_ok else "FAIL",
        "price_group_bounds": "PASS" if not outside else "FAIL",
        "primary_price_mass_ratio": "PASS" if mass.get("pass") else "FAIL",
        **readability,
    }
    return {
        "schema": "Phase55CR1PriceHierarchyQAV1",
        "checks": checks,
        "pass": all(v == "PASS" for v in checks.values()),
        "glyph_preflight": glyphs,
        "mass": mass,
        "sizes": sizes,
        "one_line_savings": pack.get("one_line_savings"),
        "outside": outside,
        "primary_currency": primary_rel,
        "struck_currency": struck_rel,
        "savings_currency": savings_rel,
    }


def generate_price_hierarchy_55c_r1(
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
        raise RuntimeError("Phase 5.5C-R1 requires the locked 5.5B-R2 Master Spec")
    lock = dict(preserved.get("human_master") or blob.get("human_approved_master_55c") or {})
    if str(lock.get("master_id") or "") != PARENT_MASTER_ID and str(blob.get("human_approved_master_55c_id") or "") != PARENT_MASTER_ID:
        raise RuntimeError("Phase 5.5C-R1 requires the locked 5.5C approved Master")
    master_png = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_R2_ASSET_ID)))).convert("RGB")
    failed_png = Image.open(io.BytesIO(_read_bytes(db, UUID(FAILED_REVISION_ASSET_ID)))).convert("RGB")
    if classify_revision_intent(instruction) != PRICE_REVISION:
        raise RuntimeError("Phase 5.5C-R1 expected PRICE_EDIT_ONLY")
    prices = parse_price_revision(instruction)
    fonts = build_font_registry()
    family = full_frame_family_spec()
    before_calls = provider_call_count()
    pack = apply_price_hierarchy(master_png, spec=spec, fonts=fonts, family=family, prices=prices)
    if provider_call_count() != before_calls:
        raise RuntimeError("Phase 5.5C-R1 must not call GPT Image")
    child_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode="project-v3-55c-r1-price-hierarchy",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5C-R1 PRICE hierarchy correction",
    )
    child_id = str(uuid4())
    preservation = compare_master_preservation(master_png, pack["image"], spec)
    qa = hierarchy_qa(pack["image"], spec=spec, pack=pack)
    revision_rec = {
        "schema": "MasterRevisionChildV1",
        "revision_id": child_id,
        "parent_master_id": PARENT_MASTER_ID,
        "parent_asset_id": APPROVED_R2_ASSET_ID,
        "parent_spec_id": APPROVED_R2_SPEC_ID,
        "parent_semantic_content": dict(REQUIRED_FACTS),
        "revision_asset_id": str(child_asset.id),
        "instruction": instruction,
        "intent": "PRICE_EDIT_ONLY",
        "correction_of": FAILED_REVISION_ID,
        "unlocked": list(unlock_for_intent("PRICE_EDIT_ONLY")),
        "locked_groups": list(LOCK_GROUPS),
        "geometry_diff": {"mutable_box": list(pack["mutable_box"]), "objects": _jsonable(pack["objects"])},
        "visual_diff": {"outside_price_group_delta": preservation.get("outside_price_group_delta")},
        "mass": pack.get("mass"),
        "reversible": True,
        "created_at": _now(),
        "revision_number": 2,
    }
    lock_with_child = append_child_revision(lock, revision_rec)
    restored = restore_approved_master(lock_with_child, child_id)
    status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preservation.get("pass") and qa.get("pass") else "CANDIDATE_TECHNICAL_FAIL"
    images = {
        "approved_master": master_png,
        "failed": failed_png,
        "corrected": pack["image"],
        "price_detail": pack["image"].crop(
            (
                max(0, pack["mutable_box"][0]),
                max(0, pack["mutable_box"][1] - 48),
                min(master_png.size[0], pack["mutable_box"][2] + 90),
                min(master_png.size[1], pack["mutable_box"][3] + 48),
            )
        ),
        "master_vs": render_side_by_side(master_png, pack["image"], left_label="Approved Master", right_label="Corrected Price Revision", title="MASTER vs CORRECTED PRICE REVISION  —  5.5C-R1"),
        "preservation": render_preservation_map(master_png, pack["image"], tuple(pack["mutable_box"])),
        "readability": render_score_board({"pass": qa.get("pass"), "scores": {k: 10 if v == "PASS" else 3 for k, v in dict(qa.get("checks") or {}).items()}}),
        "review_board": render_human_review_board_55c(master=master_png, revision=pack["image"], preservation=preservation, qa=qa, status=status),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55C_R1,
        "created_at": _now(),
        "status": status,
        "parent_approved_master_id": PARENT_MASTER_ID,
        "approved_master_asset_id": APPROVED_R2_ASSET_ID,
        "failed_revision_id": FAILED_REVISION_ID,
        "failed_revision_asset_id": FAILED_REVISION_ASSET_ID,
        "revision_child_id": child_id,
        "revision_asset_id": str(child_asset.id),
        "instruction": instruction,
        "revision_intent": "PRICE_EDIT_ONLY",
        "preservation": preservation,
        "revision_qa": qa,
        "mass": pack.get("mass"),
        "sizes": pack.get("sizes"),
        "one_line_savings": pack.get("one_line_savings"),
        "restore": restored,
        "new_visual_draft_image_calls": 0,
        "production_image_generation_calls": provider_call_count(),
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "locked_groups": list(LOCK_GROUPS),
    }
    tests = [t for t in list(blob.get("master_lock_price_hierarchy_55c_r1_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55C_R1)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["master_lock_price_hierarchy_55c_r1_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c_id"] = PARENT_MASTER_ID
    blob["human_approved_master_55c"] = json.loads(json.dumps(lock_with_child, default=str))
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if blob.get("master_lock_price_proof_55c_tests") != preserved.get("quality55c"):
        raise RuntimeError("Phase 5.5C-R1 refused to overwrite Phase 5.5C")
    _ = PRODUCTION_COVER_V2
    _ = language
    _ = WORKFLOW_ID_55C
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record

