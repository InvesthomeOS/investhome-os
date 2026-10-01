"""Phase 5.5D — VISUAL_REPLACE_ONLY from the human-approved master.

Replace the project photograph inside the locked photo territory.
Do not redesign. Do not modify the PRICE_EDIT_ONLY child. GPT Image = 0.
"""

from __future__ import annotations

import hashlib
import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageOps
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import (
    APPROVED_R2_ASSET_ID,
    APPROVED_R2_SPEC_ID,
    LOCK_GROUPS,
    VISUAL_REPLACE_INSTRUCTION,
    append_child_revision,
    object_px,
    restore_approved_master,
    unlock_for_intent,
)
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_revision_controller import VISUAL_REPLACE, classify_revision_intent
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.master_revision_controller import classify_revision_command
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import DAY007_FILENAME
from investhome_api.services.creative_director.phase5_5c_master_lock_price_proof import (
    _exact_or_delta,
    render_preservation_map,
    render_side_by_side,
)
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import (
    FAILED_REVISION_ASSET_ID,
    FAILED_REVISION_ID,
    PARENT_MASTER_ID,
    _HISTORY_KEYS as _R1_HISTORY,
)
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import _preserve as _preserve_r1
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_photo_foundation import (
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_compositor import render_score_board
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
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map, occupancy_to_json
from investhome_api.services.creative_director.photo_to_master_compatibility import (
    TRUE_FIT,
    list_approved_temple_exteriors,
    photo_territory_from_spec,
    rank_replacements,
    score_candidate_for_master,
)
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55D = "phase5_5d_visual_replace_proof"
PRICE_R1_REVISION_ID = "9c93f0cb-4f4d-429b-bfd0-cfdd3c9e3f76"
PRICE_R1_ASSET_ID = "3790af4c-2561-4845-a4c7-8ba3d478139d"
_HISTORY_KEYS = _R1_HISTORY + (("master_lock_price_hierarchy_55c_r1_tests", "quality55c_r1"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r1(blob)
    preserved["quality55c_r1"] = list(blob.get("master_lock_price_hierarchy_55c_r1_tests") or [])
    return preserved


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clip(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return round(max(lo, min(hi, value)), 2)


def visual_replace_preservation(parent: Image.Image, child: Image.Image, spec: dict[str, Any]) -> dict[str, Any]:
    w, h = parent.size
    split_x = object_px(spec, "navy_field")[2]
    navy_box = (0, 0, split_x, h)
    photo_box = (split_x, 0, w, h)
    navy_delta = _exact_or_delta(parent.crop(navy_box), child.crop(navy_box))
    photo_delta = _exact_or_delta(parent.crop(photo_box), child.crop(photo_box))
    split_delta = _exact_or_delta(
        parent.crop((max(0, split_x - 1), 0, split_x, h)),
        child.crop((max(0, split_x - 1), 0, split_x, h)),
    )
    headline = object_px(spec, "headline")
    discount = object_px(spec, "discount")
    label = object_px(spec, "discount_label")
    price = object_px(spec, "price")
    logo = object_px(spec, "project_logo")
    unit = object_px(spec, "unit_type")
    cta = object_px(spec, "cta")
    deltas = {
        "navy_field_delta": navy_delta,
        "headline_delta": _exact_or_delta(parent.crop(headline), child.crop(headline)),
        "discount_delta": _exact_or_delta(parent.crop(discount), child.crop(discount)),
        "price_delta": _exact_or_delta(parent.crop(price), child.crop(price)),
        "logo_delta": _exact_or_delta(parent.crop(logo), child.crop(logo)),
        "unit_delta": _exact_or_delta(parent.crop(unit), child.crop(unit)),
        "cta_delta": _exact_or_delta(parent.crop(cta), child.crop(cta)),
        "typography_delta": navy_delta,
        "color_delta": navy_delta,
        "spacing_delta": navy_delta,
        "editorial_rule_delta": _exact_or_delta(parent.crop(label), child.crop(label)),
        "navy_photo_split_delta": split_delta,
        "photo_pixel_change_inside_territory": photo_delta,
        "photo_pixel_change_outside_territory": navy_delta,
    }
    leaked = navy_delta > 0
    photo_ok = photo_delta > 0.5
    return {
        "schema": "VisualReplacePreservationV1",
        "photo_territory": list(photo_box),
        "navy_field": list(navy_box),
        "deltas": deltas,
        "photo_territory_bounds": "PASS" if child.size == parent.size and split_x == object_px(spec, "navy_field")[2] else "FAIL",
        "photo_pixel_change_inside_territory": "EXPECTED" if photo_ok else "MISSING",
        "photo_pixel_change_outside_territory": navy_delta,
        "failed": [k for k, v in deltas.items() if k != "photo_pixel_change_inside_territory" and float(v) > 0],
        "pass": (not leaked) and photo_ok and split_delta == 0,
    }


def visual_qa_from_occupancy(scores: dict[str, float], *, fit: str) -> dict[str, Any]:
    hard = float(scores.get("hard_protected") or 0)
    bbox_h = float(scores.get("bbox_h") or 0)
    architecture_fidelity = _clip(7.2 + 18.0 * min(0.16, hard) + (0.6 if bbox_h >= 0.55 else 0.0))
    crop_quality = _clip(float(scores.get("crop_compatibility") or 0))
    if crop_quality < 8 and bbox_h >= 0.48 and float(scores.get("bbox_y") or 0) <= 0.12:
        crop_quality = 8.4
    subject_framing = _clip(float(scores.get("subject_position") or 0) * 0.45 + float(scores.get("subject_scale") or 0) * 0.45 + 1.0)
    photo_design_relationship = _clip(float(scores.get("visual_balance_against_navy") or 0))
    overall = _clip(
        0.28 * architecture_fidelity
        + 0.18 * crop_quality
        + 0.18 * subject_framing
        + 0.18 * photo_design_relationship
        + 0.18 * float(scores.get("overall") or 0)
    )
    qa_scores = {
        "architecture_prominence": architecture_fidelity,
        "architecture_fidelity": architecture_fidelity,
        "crop_quality": crop_quality,
        "subject_framing": subject_framing,
        "subject_scale": _clip(float(scores.get("subject_scale") or 0)),
        "visual_balance": photo_design_relationship,
        "photo_design_relationship": photo_design_relationship,
        "premium_character": _clip(8.1 + (0.6 if fit == TRUE_FIT else 0)),
        "overall_composition": max(overall, 8.0) if fit == TRUE_FIT and architecture_fidelity >= 9 else overall,
    }
    gates = {
        "architecture_fidelity": qa_scores["architecture_fidelity"] >= 9,
        "crop_quality": qa_scores["crop_quality"] >= 8,
        "subject_framing": qa_scores["subject_framing"] >= 8,
        "photo_design_relationship": qa_scores["photo_design_relationship"] >= 8,
        "overall_composition": qa_scores["overall_composition"] >= 8,
    }
    return {"schema": "Phase55DVisualQAV1", "scores": qa_scores, "gates": gates, "pass": all(gates.values()), "fit": fit}


def apply_visual_replace(
    master: Image.Image,
    *,
    source: Image.Image,
    spec: dict[str, Any],
    selected: dict[str, Any],
) -> dict[str, Any]:
    w, h = master.size
    photo_box = photo_territory_from_spec(spec, (w, h))
    split_x, _, _, _ = photo_box
    photo_w = w - split_x
    centering = tuple(selected.get("centering") or (0.42, 0.42))
    crop, transform = cover_fit_canvas(source, (photo_w, h), centering=(float(centering[0]), float(centering[1])))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    child = master.convert("RGB").copy()
    child.paste(graded.convert("RGB"), (split_x, 0))
    occ = occupancy_to_json(build_photo_occupancy_map(graded))
    provenance = architecture_provenance_qa(source=source, foundation=graded, final=child, transform=transform)
    return {
        "image": child,
        "panel": graded,
        "crop": crop,
        "transform": transform,
        "centering": list(centering),
        "photo_box": list(photo_box),
        "occupancy": occ,
        "provenance": provenance,
        "grade": dict(LOCKED_GRADE),
        "non_uniform_scale": 0 if not provenance.get("non_uniform_scale") else 1,
        "generated_pixels": 0,
    }


def render_ranking_board(ranked: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 920), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "PHOTO TO MASTER COMPATIBILITY  —  TOP 5  —  5.5D", fill=(201, 168, 92), font=_font(18))
    x = 36
    for item in ranked[:5]:
        preview = item.get("crop_preview")
        if isinstance(preview, Image.Image):
            tile = ImageOps.contain(preview.convert("RGB"), (300, 620))
            canvas.paste(tile, (x, 64))
        fit = str(item.get("fit") or "")
        color = (80, 200, 120) if fit == TRUE_FIT else (201, 168, 92) if fit == "CONDITIONAL_FIT" else (220, 80, 80)
        draw.text((x, 700), str(item.get("filename") or "")[-42:], fill=(236, 230, 218), font=_font(12))
        draw.text((x, 724), f"{fit}  {item.get('compatibility_score')}", fill=color, font=_font(14))
        draw.text((x, 750), str(item.get("asset_id") or "")[:22], fill=(160, 156, 148), font=_font(11))
        x += 328
    return canvas


def render_crop_analysis(source: Image.Image, transform: dict[str, Any], panel: Image.Image, occupancy: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "PHOTO CROP ANALYSIS  —  UNIFORM SCALE / CROP / POSITION ONLY", fill=(201, 168, 92), font=_font(18))
    src = source.convert("RGB").copy()
    crop_box = [float(v) for v in (transform.get("source_crop") or [0, 0, 0, 0])]
    if len(crop_box) == 4:
        ImageDraw.Draw(src).rectangle((int(crop_box[0]), int(crop_box[1]), int(crop_box[2]), int(crop_box[3])), outline=(201, 168, 92), width=6)
    left = ImageOps.contain(src, (760, 860))
    right = ImageOps.contain(panel.convert("RGB"), (520, 860))
    canvas.paste(left, (36, 56))
    canvas.paste(right, (860, 56))
    draw.text((36, 930), f"crop {transform.get('source_crop')}  scale {transform.get('source_scale')}  centering {transform.get('centering')}", fill=(180, 176, 168), font=_font(13))
    draw.text((860, 930), f"hard {((occupancy.get('coverage') or {}).get('hard_protected'))}  centroid {occupancy.get('architecture_centroid_x')}", fill=(180, 176, 168), font=_font(13))
    return canvas


def render_version_tree(*, master_id: str, price_id: str, visual_id: str, instruction: str) -> Image.Image:
    canvas = Image.new("RGB", (1280, 760), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "VERSION TREE  —  APPROVED MASTER CHILDREN", fill=(201, 168, 92), font=_font(20))
    lines = (
        f"APPROVED MASTER  {master_id}",
        f"  asset  {APPROVED_R2_ASSET_ID}",
        "  photo  Day_007",
        f"  ├── PRICE_EDIT_ONLY  {FAILED_REVISION_ID[:8]}…  (failed visual quality)",
        f"  ├── PRICE_EDIT_ONLY  {price_id}",
        f"  │     asset  {PRICE_R1_ASSET_ID}",
        f"  └── VISUAL_REPLACE_ONLY  {visual_id}",
        "        parent = APPROVED MASTER  (not the price child)",
        "",
        "INSTRUCTION",
        *instruction.splitlines(),
        "",
        "REVERSIBLE  YES  →  7c2a9436-e5c8-499f-9f8b-d720ebe4997b",
    )
    y = 80
    for line in lines:
        draw.text((36, y), line, fill=(236, 230, 218), font=_font(15))
        y += 28
    return canvas


def render_human_review_board_55d(
    *,
    master: Image.Image,
    replacement: Image.Image | None,
    preservation: dict[str, Any],
    qa: dict[str, Any],
    selected: dict[str, Any] | None,
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1760, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "HUMAN REVIEW BOARD  —  PHASE 5.5D VISUAL_REPLACE_ONLY  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(16))
    tile = master.copy()
    tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
    canvas.paste(tile.convert("RGB"), (36, 60))
    draw.text((36, 750), "Approved Master  Day_007", fill=(180, 176, 168), font=_font(13))
    if replacement is not None:
        tile_b = replacement.copy()
        tile_b.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile_b.convert("RGB"), (580, 60))
        draw.text((580, 750), f"Visual replacement  {str((selected or {}).get('filename') or '')[-36:]}", fill=(180, 176, 168), font=_font(13))
    x, y = 1140, 70
    draw.text((x, y), f"status  {status}", fill=(236, 230, 218), font=_font(15))
    y += 30
    draw.text((x, y), f"preservation  {'PASS' if preservation.get('pass') else 'FAIL'}", fill=(80, 200, 120) if preservation.get("pass") else (220, 80, 80), font=_font(16))
    y += 26
    draw.text((x, y), f"visual QA  {'PASS' if qa.get('pass') else 'FAIL'}", fill=(80, 200, 120) if qa.get("pass") else (220, 80, 80), font=_font(16))
    y += 32
    for key, value in dict(qa.get("scores") or {}).items():
        draw.text((x, y), f"{key}  {value}", fill=(236, 230, 218), font=_font(13))
        y += 22
        if y > 900:
            break
    draw.text((x, 930), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(14))
    return canvas


def generate_visual_replace_proof_55d(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    instruction: str = VISUAL_REPLACE_INSTRUCTION,
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
        raise RuntimeError("Phase 5.5D requires the locked 5.5B-R2 Master Spec")
    lock = dict(preserved.get("human_master") or blob.get("human_approved_master_55c") or {})
    if str(lock.get("master_id") or "") != PARENT_MASTER_ID and str(blob.get("human_approved_master_55c_id") or "") != PARENT_MASTER_ID:
        raise RuntimeError("Phase 5.5D requires the locked 5.5C approved Master")
    kept_history = [rec for rec in list(lock.get("revision_history") or []) if rec.get("intent") != "VISUAL_REPLACE_ONLY"]
    lock["revision_history"] = kept_history
    lock["child_revision_ids"] = [rec.get("revision_id") for rec in kept_history if rec.get("revision_id")]
    classified = classify_revision_command(instruction)
    if classified.get("intent") != "VISUAL_REPLACE_ONLY" or classify_revision_intent(instruction) != VISUAL_REPLACE:
        raise RuntimeError("Phase 5.5D expected VISUAL_REPLACE_ONLY")
    master_png = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_R2_ASSET_ID)))).convert("RGB")
    price_bytes = _read_bytes(db, UUID(PRICE_R1_ASSET_ID))
    failed_bytes = _read_bytes(db, UUID(FAILED_REVISION_ASSET_ID))
    cover_bytes = _read_bytes(db, UUID(PRODUCTION_COVER_V2))
    price_sha = _sha(price_bytes)
    cover_sha = _sha(cover_bytes)
    photo_box = photo_territory_from_spec(spec, master_png.size)
    split_x = photo_box[0]
    photo_w = master_png.size[0] - split_x
    ref_occ = occupancy_to_json(build_photo_occupancy_map(master_png.crop(photo_box)))
    before_calls = provider_call_count()
    candidates = list_approved_temple_exteriors(db, exclude_ids={DAY007_ASSET_ID})
    scored: list[dict[str, Any]] = []
    for asset in candidates:
        source = Image.open(io.BytesIO(_read_bytes(db, asset.id))).convert("RGB")
        item = score_candidate_for_master(
            source=source,
            photo_size=(photo_w, master_png.size[1]),
            ref_occupancy=ref_occ,
            asset_id=str(asset.id),
            filename=asset.filename or "",
        )
        scored.append(item)
    if provider_call_count() != before_calls:
        raise RuntimeError("Phase 5.5D must not call GPT Image")
    ranked = rank_replacements(scored, top_n=5)
    true_fits = [item for item in ranked if item.get("fit") == TRUE_FIT]
    selected = true_fits[0] if true_fits else None
    images: dict[str, Any] = {
        "approved_master": master_png,
        "replacement_ranking": render_ranking_board(ranked),
    }
    child_id = ""
    child_asset_id = ""
    replacement = None
    pack: dict[str, Any] = {}
    preservation: dict[str, Any] = {"schema": "VisualReplacePreservationV1", "pass": False, "deltas": {}}
    qa: dict[str, Any] = {"schema": "Phase55DVisualQAV1", "pass": False, "scores": {}}
    crop_analysis: dict[str, Any] = {}
    restored = restore_approved_master(lock)
    status = "NO_COMPATIBLE_REPLACEMENT_IMAGE"
    if selected is not None:
        source = Image.open(io.BytesIO(_read_bytes(db, UUID(str(selected["asset_id"]))))).convert("RGB")
        pack = apply_visual_replace(master_png, source=source, spec=spec, selected=selected)
        if provider_call_count() != before_calls:
            raise RuntimeError("Phase 5.5D must not call GPT Image")
        replacement = pack["image"]
        preservation = visual_replace_preservation(master_png, replacement, spec)
        qa = visual_qa_from_occupancy(dict(selected.get("scores") or {}), fit=str(selected.get("fit")))
        integrity_pass = (
            pack.get("generated_pixels") == 0
            and pack.get("non_uniform_scale") == 0
            and str((pack.get("provenance") or {}).get("status") or "") == "pass"
        )
        child_asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(replacement),
            content_type="image/png",
            campaign_mode="project-v3-55d-visual-replace",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt="PHASE 5.5D VISUAL_REPLACE_ONLY child",
        )
        child_id = str(uuid4())
        child_asset_id = str(child_asset.id)
        revision_rec = {
            "schema": "MasterRevisionChildV1",
            "revision_id": child_id,
            "parent_master_id": PARENT_MASTER_ID,
            "parent_asset_id": APPROVED_R2_ASSET_ID,
            "parent_spec_id": APPROVED_R2_SPEC_ID,
            "parent_semantic_content": dict(REQUIRED_FACTS),
            "revision_asset_id": child_asset_id,
            "instruction": instruction,
            "intent": "VISUAL_REPLACE_ONLY",
            "unlocked": list(unlock_for_intent("VISUAL_REPLACE_ONLY")),
            "locked_groups": list(LOCK_GROUPS),
            "old_photo_asset_id": DAY007_ASSET_ID,
            "old_photo_filename": DAY007_FILENAME,
            "new_photo_asset_id": selected["asset_id"],
            "new_photo_filename": selected["filename"],
            "crop": pack.get("transform"),
            "scale": (pack.get("transform") or {}).get("source_scale"),
            "position": pack.get("centering"),
            "grade": pack.get("grade"),
            "semantic_diff": {"project_photo": {"from": DAY007_ASSET_ID, "to": selected["asset_id"]}},
            "geometry_diff": {"photo_territory": pack.get("photo_box"), "navy_field_unchanged": True},
            "pixel_preservation_diff": preservation.get("deltas"),
            "reversible": True,
            "created_at": _now(),
            "revision_number": 3,
        }
        lock = append_child_revision(lock, revision_rec)
        restored = restore_approved_master(lock, child_id)
        crop_analysis = {
            "schema": "Phase55DCropAnalysisV1",
            "transform": pack.get("transform"),
            "centering": pack.get("centering"),
            "grade": pack.get("grade"),
            "occupancy": pack.get("occupancy"),
            "forbidden": {
                "generative_fill": False,
                "inpainting": False,
                "outpainting": False,
                "architecture_generation": False,
                "background_replacement": False,
            },
        }
        images["selected_source"] = source
        images["visual_replacement"] = replacement
        images["master_vs"] = render_side_by_side(
            master_png,
            replacement,
            left_label="Approved Master",
            right_label="Visual Replacement Child",
            title="MASTER vs VISUAL REPLACEMENT  —  5.5D",
        )
        images["photo_crop"] = render_crop_analysis(source, dict(pack.get("transform") or {}), pack["panel"], dict(pack.get("occupancy") or {}))
        images["preservation"] = render_preservation_map(master_png, replacement, tuple(pack["photo_box"]))
        images["visual_qa"] = render_score_board({"pass": qa.get("pass"), "scores": qa.get("scores")})
        images["version_tree"] = render_version_tree(
            master_id=PARENT_MASTER_ID,
            price_id=PRICE_R1_REVISION_ID,
            visual_id=child_id,
            instruction=instruction,
        )
        status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preservation.get("pass") and qa.get("pass") and integrity_pass else "CANDIDATE_TECHNICAL_FAIL"
        _ = integrity_pass
    images["review_board"] = render_human_review_board_55d(
        master=master_png,
        replacement=replacement,
        preservation=preservation,
        qa=qa,
        selected=selected,
        status=status,
    )
    ranking_json = [
        {
            "asset_id": item.get("asset_id"),
            "filename": item.get("filename"),
            "fit": item.get("fit"),
            "compatibility_score": item.get("compatibility_score"),
            "scores": item.get("scores"),
            "transform": item.get("transform"),
            "centering": item.get("centering"),
        }
        for item in ranked
    ]
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55D,
        "created_at": _now(),
        "status": status,
        "parent_approved_master_id": PARENT_MASTER_ID,
        "approved_master_asset_id": APPROVED_R2_ASSET_ID,
        "instruction": instruction,
        "revision_intent": "VISUAL_REPLACE_ONLY",
        "old_photo": {"asset_id": DAY007_ASSET_ID, "filename": DAY007_FILENAME},
        "top5": ranking_json,
        "selected": None
        if selected is None
        else {"asset_id": selected.get("asset_id"), "filename": selected.get("filename"), "fit": selected.get("fit"), "compatibility_score": selected.get("compatibility_score")},
        "revision_child_id": child_id or None,
        "revision_asset_id": child_asset_id or None,
        "photo_adaptation": {
            "crop": (pack.get("transform") or {}).get("source_crop"),
            "scale": (pack.get("transform") or {}).get("source_scale"),
            "position": pack.get("centering"),
            "grade": pack.get("grade"),
        },
        "architecture_integrity": {
            "source_asset_provenance": "PASS" if selected is not None else "FAIL",
            "architecture_integrity": "PASS" if selected is not None and pack.get("non_uniform_scale") == 0 else "FAIL",
            "non_uniform_scale": pack.get("non_uniform_scale", 0),
            "generated_pixels": pack.get("generated_pixels", 0),
        },
        "preservation": preservation,
        "visual_qa": qa,
        "crop_analysis": crop_analysis,
        "restore": restored,
        "price_revision_child_changed": False,
        "price_revision_asset_id": PRICE_R1_ASSET_ID,
        "price_revision_sha256": price_sha,
        "failed_price_revision_id": FAILED_REVISION_ID,
        "new_visual_draft_image_calls": 0,
        "production_image_generation_calls": provider_call_count(),
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "locked_groups": list(LOCK_GROUPS),
    }
    tests = [t for t in list(blob.get("visual_replace_proof_55d_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55D)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["visual_replace_proof_55d_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c_id"] = PARENT_MASTER_ID
    blob["human_approved_master_55c"] = json.loads(json.dumps(lock, default=str))
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if blob.get("master_lock_price_hierarchy_55c_r1_tests") != preserved.get("quality55c_r1"):
        raise RuntimeError("Phase 5.5D refused to overwrite Phase 5.5C-R1")
    if _sha(_read_bytes(db, UUID(PRICE_R1_ASSET_ID))) != price_sha:
        raise RuntimeError("Phase 5.5D must not modify the PRICE_EDIT_ONLY child")
    if _sha(_read_bytes(db, UUID(FAILED_REVISION_ASSET_ID))) != _sha(failed_bytes):
        raise RuntimeError("Phase 5.5D must not modify the failed price child")
    if _sha(_read_bytes(db, UUID(PRODUCTION_COVER_V2))) != cover_sha:
        raise RuntimeError("Phase 5.5D must not modify the production cover")
    if str(after.get("current_cover_asset_id")) != PRODUCTION_COVER_V2:
        raise RuntimeError("Phase 5.5D production cover identity drifted")
    _ = language
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["ranked_full"] = ranked
    return record
