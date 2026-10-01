"""Phase 5.6 — premium creative master redesign.

Reference-grounded Visual Art Director. GraphicDesignCompositorV3 executes.
Does not overwrite the 5.5 technical Master, price child, or production cover.
GPT Image production calls = 0.
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
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.full_frame_architectural_family import FAMILY_ID, full_frame_family_spec
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import (
    DAY007_ASSET_ID,
    DAY007_FILENAME,
    load_grade_a_reference_images,
)
from investhome_api.services.creative_director.phase5_5c_master_lock_price_proof import render_side_by_side
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import (
    PRICE_R1_ASSET_ID,
    PRICE_R1_REVISION_ID,
    _HISTORY_KEYS as _D_HISTORY,
)
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import _preserve as _preserve_d
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable, render_score_board
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
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map, render_occupancy_map
from investhome_api.services.creative_director.premium_art_direction import (
    FINAL_BAD_V2,
    FINAL_POSITIVE_V2,
    MODES,
    creative_canvas_balance,
    final_critic_pass,
    infer_mode,
    rank_eligible,
    render_balance_board,
    render_blueprint_critic_board,
    render_blueprint_v2_board,
    render_craft_v2_board,
    request_premium_art_direction,
    request_premium_blueprint_critic,
    request_premium_final_critic,
    translate_premium_plan,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_56 = "phase5_6_premium_master_redesign"
LOCKED_CENTERING = (0.50, 0.42)
_HISTORY_KEYS = _D_HISTORY + (("visual_replace_proof_55d_tests", "quality55d"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_d(blob)
    preserved["quality55d"] = list(blob.get("visual_replace_proof_55d_tests") or [])
    preserved["human_master"] = dict(blob.get("human_approved_master_55c") or preserved.get("human_master") or {})
    preserved["human_master_id"] = blob.get("human_approved_master_55c_id") or preserved.get("human_master_id")
    return preserved


def _logo_board(logo_rgba: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (720, 420), (16, 18, 22))
    tile = logo_rgba.convert("RGBA")
    tile.thumbnail((560, 320), Image.Resampling.LANCZOS)
    canvas.paste(tile, ((720 - tile.size[0]) // 2, (420 - tile.size[1]) // 2), tile)
    return canvas


def render_human_review_board_56(
    *,
    candidate_a: Image.Image | None,
    candidate_b: Image.Image | None,
    status: str,
    eligible: int,
) -> Image.Image:
    canvas = Image.new("RGB", (1760, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "HUMAN REVIEW BOARD  —  PHASE 5.6 PREMIUM REDESIGN  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(16))
    if candidate_a is not None:
        tile = candidate_a.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36, 60))
        draw.text((36, 760), "Candidate A", fill=(180, 176, 168), font=_font(14))
    if candidate_b is not None:
        tile = candidate_b.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (580, 60))
        draw.text((580, 760), "Candidate B", fill=(180, 176, 168), font=_font(14))
    draw.text((1140, 80), f"status  {status}", fill=(236, 230, 218), font=_font(16))
    draw.text((1140, 120), f"eligible blueprints  {eligible}", fill=(180, 176, 168), font=_font(16))
    draw.text((1140, 170), "Existing 5.5 Master unchanged", fill=(80, 200, 120), font=_font(15))
    draw.text((1140, 200), "Price revision unchanged", fill=(80, 200, 120), font=_font(15))
    draw.text((1140, 230), "Production cover unchanged", fill=(80, 200, 120), font=_font(15))
    draw.text((1140, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(14))
    return canvas


def _render_candidate(
    *,
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    blueprint: dict[str, Any],
    mode: str,
    graded: Image.Image,
    occupancy: dict[str, Any],
    fonts: dict[str, Any],
    family: dict[str, Any],
    logo_rgba: Image.Image,
    src: Image.Image,
    transform: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    plan = translate_premium_plan(blueprint, mode=mode)
    pack = None
    for adj in (1.0, 0.92, 0.84):
        trial = json.loads(json.dumps(plan))
        trial["scale"] = adj
        candidate = compose_graphic_design_v3(
            graded,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            logo_rgba=logo_rgba,
            art_plan=trial,
            scale=adj,
        )
        pack = candidate
        plan = trial
        if candidate.get("solved"):
            break
    assert pack is not None
    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["fielded"]),
        content_type="image/png",
        campaign_mode=f"project-v3-56-field-{key.lower()}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.6 field {key}",
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode=f"project-v3-56-candidate-{key.lower()}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.6 candidate {key}",
    )
    spec = build_family_master_spec(
        key=f"P56-{key}",
        pack=pack,
        family=family,
        crop={"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop")},
        photo_asset=DAY007_ASSET_ID,
        logo_asset=LOCKED_LOGO_ASSET_ID,
        candidate_asset_id=str(asset.id),
        architecture_lock={"schema": "PhotoOccupancyMapV1"},
    )
    spec["schema"] = "ProductionMasterCandidateV1"
    spec["status"] = "CANDIDATE_PENDING_HUMAN_REVIEW"
    spec["family_id"] = FAMILY_ID
    spec["registered_master_family"] = False
    spec["art_director"] = "AIVisualArtDirectorV2"
    spec["art_direction_blueprint"] = blueprint
    spec["structured_art_direction_plan"] = plan
    spec["reconstruction_mode"] = mode
    spec["source_asset_provenance"] = {
        "photo_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "crop": {"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop")},
    }
    spec["graphic_field"]["asset_id"] = str(field_asset.id)
    spec["graphic_field"]["overlay"] = mode
    spec["promoted"] = False
    spec["parent_technical_master_id"] = PARENT_MASTER_ID
    ready = family_revision_readiness(spec)
    collision = evaluate_collisions(objects=pack.get("objects") or {}, occupancy=occupancy, size=pack["image"].size)
    provenance = architecture_provenance_qa(
        source=src,
        foundation=pack["foundation"],
        final=pack["image"],
        transform={
            "centering": list(LOCKED_CENTERING),
            "source_crop": transform.get("source_crop"),
            "scale_x": transform.get("scale_x"),
            "scale_y": transform.get("scale_y"),
        },
    )
    utf8 = turkish_copy_is_valid(pack.get("facts") or {})
    balance = creative_canvas_balance(pack["image"], pack.get("objects") or {}, pack.get("field_mask"), occupancy)
    pack["graphic_field_asset_id"] = str(field_asset.id)
    return {
        "key": key,
        "blueprint": blueprint,
        "mode": mode,
        "plan": plan,
        "pack": pack,
        "spec": spec,
        "asset_id": str(asset.id),
        "field_asset_id": str(field_asset.id),
        "ready": ready,
        "collision": collision,
        "provenance": provenance,
        "utf8": utf8,
        "balance": balance,
        "solved": bool(pack.get("solved")),
    }


def generate_premium_master_redesign_56(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()
    vision_calls = 0
    family = full_frame_family_spec()
    fonts = build_font_registry()
    logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    src = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY007_ASSET_ID)))).convert("RGB")
    crop, transform = cover_fit_canvas(src, CANVAS_4X5, centering=LOCKED_CENTERING)
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = build_photo_occupancy_map(graded)
    occupancy_board = render_occupancy_map(graded, occupancy)
    references, ref_provenance, refs_ok = load_grade_a_reference_images(db)
    director, n = request_premium_art_direction(
        day007=graded,
        logo=_logo_board(logo_rgba),
        references=references,
        occupancy_board=occupancy_board,
    )
    vision_calls += n
    blueprints = list(director.get("blueprints") or [])
    craft = dict(director.get("reference_craft") or {})
    used: set[str] = set()
    for i, item in enumerate(blueprints):
        mode = infer_mode(item, i, used)
        used.add(mode)
        item["reconstruction_mode"] = mode
    critic, n = request_premium_blueprint_critic(blueprints)
    vision_calls += n
    eligible = rank_eligible(blueprints)
    images: dict[str, Any] = {
        "craft": render_craft_v2_board(craft, references),
        "craft_blueprint": render_craft_v2_board(craft, references),
        "ad1": render_blueprint_v2_board(blueprints[0] if blueprints else {}, "03  BLUEPRINT 1"),
        "ad2": render_blueprint_v2_board(blueprints[1] if len(blueprints) > 1 else {}, "04  BLUEPRINT 2"),
        "ad3": render_blueprint_v2_board(blueprints[2] if len(blueprints) > 2 else {}, "05  BLUEPRINT 3"),
        "blueprint_critic": render_blueprint_critic_board(critic, blueprints),
    }
    rendered: list[dict[str, Any]] = []
    status = "NO_BLUEPRINT_AT_PRODUCTION_QUALITY"
    if len(eligible) >= 1:
        top = eligible[:2]
        keys = ("A", "B")
        before_calls = provider_call_count()
        for i, blueprint in enumerate(top):
            rec = _render_candidate(
                db=db,
                user=user,
                row=row,
                blueprint=blueprint,
                mode=str(blueprint.get("reconstruction_mode") or MODES[i]),
                graded=graded,
                occupancy=occupancy,
                fonts=fonts,
                family=family,
                logo_rgba=logo_rgba,
                src=src,
                transform=transform,
                key=keys[i],
            )
            if provider_call_count() != before_calls:
                raise RuntimeError("Phase 5.6 must not call GPT Image")
            critic_final, n = request_premium_final_critic(rec["pack"]["image"], graded, references, blueprint)
            vision_calls += n
            rec["final_critic"] = critic_final
            rec["critic_pass"] = final_critic_pass(critic_final, dead_space_score=float((rec["balance"] or {}).get("dead_space_score") or 99))
            rendered.append(rec)
            images[f"candidate_{keys[i].lower()}"] = rec["pack"]["image"]
        if len(rendered) == 2:
            images["comparison"] = render_side_by_side(
                rendered[0]["pack"]["image"],
                rendered[1]["pack"]["image"],
                left_label=f"A  {rendered[0]['blueprint'].get('concept_name')}",
                right_label=f"B  {rendered[1]['blueprint'].get('concept_name')}",
                title="CANDIDATE COMPARISON  —  5.6",
            )
        images["canvas_balance"] = render_balance_board(rendered[0]["balance"], rendered[0]["pack"]["image"])
        merged_scores = {}
        for rec in rendered:
            for key in (*FINAL_POSITIVE_V2, *FINAL_BAD_V2):
                merged_scores[f"{rec['key']}_{key}"] = (rec.get("final_critic") or {}).get(key)
        images["final_critic"] = render_score_board({"pass": any(r.get("critic_pass") for r in rendered), "scores": merged_scores})
        status = "CANDIDATE_PENDING_HUMAN_REVIEW"
    images["review_board"] = render_human_review_board_56(
        candidate_a=(rendered[0]["pack"]["image"] if rendered else None),
        candidate_b=(rendered[1]["pack"]["image"] if len(rendered) > 1 else None),
        status=status,
        eligible=len(eligible),
    )
    best = None
    if rendered:
        ranked = sorted(rendered, key=lambda rec: float(((rec.get("final_critic") or {}).get("professional_art_direction") or 0)))
        best = ranked[-1]
    cand_a = rendered[0] if rendered else None
    cand_b = rendered[1] if len(rendered) > 1 else None
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_56,
        "created_at": _now(),
        "status": status,
        "references_actually_provided": bool(refs_ok and len(references) == 6),
        "reference_ids": ref_provenance,
        "reference_craft": craft,
        "blueprints": blueprints,
        "blueprint_critic": critic,
        "eligible_blueprint_count": len(eligible),
        "candidate_a": None
        if cand_a is None
        else {
            "concept": cand_a["blueprint"].get("concept_name"),
            "mode": cand_a["mode"],
            "asset_id": cand_a["asset_id"],
            "spec_id": cand_a["spec"].get("spec_id"),
            "scores": cand_a.get("final_critic"),
            "revision_readiness": cand_a.get("ready"),
            "balance": cand_a.get("balance"),
        },
        "candidate_b": None
        if cand_b is None
        else {
            "concept": cand_b["blueprint"].get("concept_name"),
            "mode": cand_b["mode"],
            "asset_id": cand_b["asset_id"],
            "spec_id": cand_b["spec"].get("spec_id"),
            "scores": cand_b.get("final_critic"),
            "revision_readiness": cand_b.get("ready"),
            "balance": cand_b.get("balance"),
        },
        "candidate_a_spec": None if cand_a is None else cand_a["spec"],
        "candidate_b_spec": None if cand_b is None else cand_b["spec"],
        "best_internal_candidate": None if best is None else best["key"],
        "canvas_balance": None if cand_a is None else cand_a.get("balance"),
        "photo_asset_id": DAY007_ASSET_ID,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "gpt_image_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "price_revision_asset_id": PRICE_R1_ASSET_ID,
        "price_revision_child_changed": False,
        "production_cover_changed": False,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
    }
    tests = [t for t in list(blob.get("premium_master_redesign_56_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_56)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["premium_master_redesign_56_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c"] = preserved.get("human_master")
    blob["human_approved_master_55c_id"] = preserved.get("human_master_id")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if blob.get("visual_replace_proof_55d_tests") != preserved.get("quality55d"):
        raise RuntimeError("Phase 5.6 refused to overwrite Phase 5.5D")
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 5.6 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    _ = language
    _ = _jsonable
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
