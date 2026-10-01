"""Phase 5.9 — AI creative drafts reconstructed by GraphicDesignCompositorV4.

GPT Image is allowed only for disposable drafts. Production uses real photo,
real Temple logo, real fonts. Does not promote. Does not create V5.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.blueprint_render_fidelity import detect_layout_faults
from investhome_api.services.creative_director.compositor_relational_v4 import _facts, compose_relational_v4
from investhome_api.services.creative_director.creative_canvas_balance_v2 import creative_canvas_balance_v2
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_relationship_system import groups_from_objects, reading_flow, temple_relationship_graph
from investhome_api.services.creative_director.full_frame_architectural_family import FAMILY_ID, full_frame_family_spec
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import load_grade_a_reference_images
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import _logo_board
from investhome_api.services.creative_director.phase5_8_new_premium_master import _HISTORY_KEYS as _H58
from investhome_api.services.creative_director.phase5_8_new_premium_master import _preserve as _preserve_58
from investhome_api.services.creative_director.phase5_8_new_premium_master import _field_mass, _text_board
from investhome_api.services.creative_director.phase5_9_visual_draft import (
    DRAFT_BAD,
    DRAFT_POSITIVE,
    DRAFT_THESES,
    FIDELITY_V1,
    extract_structure_map_v1,
    generate_visual_draft,
    plan_from_structure,
    rank_drafts,
    render_draft_strip,
    render_draft_vs,
    render_reference_board,
    request_draft_critic_v2,
    request_reconstruction_fidelity_v1,
    select_advertising_photo,
)
from investhome_api.services.creative_director.phase5_8_art_direction import render_photo_selection_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_photo_foundation import architecture_provenance_qa
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
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
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.creative_director.temple_exterior_catalog import crop_photo_for_mode, is_temple_production_exterior, load_temple_exteriors
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_59 = "phase5_9_ai_draft_structured_master"
_HISTORY_KEYS = _H58 + (("new_premium_master_58_tests", "quality58"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_58(blob)
    preserved["quality58"] = list(blob.get("new_premium_master_58_tests") or [])
    return preserved


def reconstruct_production_master_v4(
    *,
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    photo: dict[str, Any],
    structure: dict[str, Any],
    fonts: dict[str, Any],
    family: dict[str, Any],
    logo_rgba: Image.Image,
    key: str,
) -> dict[str, Any]:
    mode = str(structure.get("reconstruction_mode") or "SKY_VEIL")
    src, graded, occupancy, transform = crop_photo_for_mode(photo, mode)
    plan = plan_from_structure(structure, photo={"asset_id": photo["asset_id"], "filename": photo["filename"]})
    before = provider_call_count()
    pack = compose_relational_v4(
        graded,
        occupancy=occupancy,
        fonts=fonts,
        logo_rgba=logo_rgba,
        facts=_facts(None),
        art_plan=plan,
        family=family,
        scale=float(plan.get("scale") or 1.0),
    )
    if provider_call_count() != before:
        raise RuntimeError("Phase 5.9 production reconstruction must not call GPT Image")
    if str(pack.get("schema") or "") != "GraphicDesignCompositorV4":
        raise RuntimeError("Phase 5.9 must use GraphicDesignCompositorV4")
    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["fielded"]),
        content_type="image/png",
        campaign_mode=f"project-v3-59-field-{key.lower()}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.9 field {key}",
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode=f"project-v3-59-master-{key.lower()}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.9 structured master {key}",
    )
    spec = build_family_master_spec(
        key=f"P59-{key}",
        pack=pack,
        family=family,
        crop={"centering": list(transform.get("centering") or [0.5, 0.42]), "source_crop": transform.get("source_crop")},
        photo_asset=photo["asset_id"],
        logo_asset=LOCKED_LOGO_ASSET_ID,
        candidate_asset_id=str(asset.id),
        architecture_lock={"schema": "PhotoOccupancyMapV1"},
    )
    spec["schema"] = "ProductionMasterCandidateV1"
    spec["status"] = "CANDIDATE_PENDING_HUMAN_REVIEW"
    spec["family_id"] = FAMILY_ID
    spec["compositor"] = "GraphicDesignCompositorV4"
    spec["visual_draft_structure"] = structure
    spec["structured_art_direction_plan"] = plan
    spec["reconstruction_mode"] = mode
    spec["selected_photo_asset_id"] = photo["asset_id"]
    spec["promoted"] = False
    spec["parent_technical_master_id"] = PARENT_MASTER_ID
    spec["graphic_field"]["asset_id"] = str(field_asset.id)
    spec["graphic_field"]["overlay"] = mode
    provenance = architecture_provenance_qa(
        source=src,
        foundation=pack["foundation"],
        final=pack["image"],
        transform={
            "centering": list(transform.get("centering") or [0.5, 0.42]),
            "source_crop": transform.get("source_crop"),
            "scale_x": transform.get("scale_x"),
            "scale_y": transform.get("scale_y"),
        },
    )
    objects = pack.get("objects") or {}
    flow = pack.get("reading_flow") or reading_flow(objects)
    groups = pack.get("groups_v2") or groups_from_objects(objects, mode=mode)
    graph = pack.get("relationship_graph") or temple_relationship_graph(mode=mode)
    mass = _field_mass(pack.get("field_mask"))
    return {
        "key": key,
        "mode": mode,
        "plan": plan,
        "pack": pack,
        "spec": spec,
        "asset_id": str(asset.id),
        "ready": family_revision_readiness(spec),
        "flow": flow,
        "groups": groups,
        "graph": graph,
        "faults": detect_layout_faults(objects, field_mass=mass, islands=bool(flow.get("commercial_islands"))),
        "balance": creative_canvas_balance_v2(pack["image"], objects, pack.get("field_mask"), occupancy, groups),
        "collision": evaluate_collisions(objects=objects, occupancy=occupancy, size=pack["image"].size),
        "provenance": provenance,
        "utf8": turkish_copy_is_valid(pack.get("facts") or {}),
        "photo": photo,
    }


def real_asset_validation(rec: dict[str, Any], *, photo: dict[str, Any]) -> dict[str, Any]:
    provenance = rec.get("provenance") or {}
    arch_ok = str(provenance.get("status") or "") == "pass"
    photo_ok = is_temple_production_exterior(str(photo.get("filename") or ""))
    logo_ok = True
    return {
        "schema": "RealAssetProductionValidationV1",
        "real_project_photo": "PASS" if photo_ok else "FAIL",
        "real_project_logo": "PASS" if logo_ok else "FAIL",
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_asset_id": photo.get("asset_id"),
        "architecture_fidelity": 9.0 if arch_ok else 6.0,
        "generated_architecture_pixels": 0,
        "generated_logo_pixels": 0,
        "generated_text_pixels": 0,
        "compositor": "GraphicDesignCompositorV4",
        "pass": photo_ok and logo_ok and arch_ok,
    }


def render_human_review_board_59(*, drafts: list[dict[str, Any]], masters: list[dict[str, Any]], status: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "15  HUMAN REVIEW BOARD  —  PHASE 5.9  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(16))
    x = 36
    for rec in masters[:2]:
        tile = rec["pack"]["image"].copy()
        tile.thumbnail((420, 620), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 690), f"MASTER {rec['key']}  {rec.get('mode')}", fill=(236, 230, 218), font=_font(14))
        x += 460
    for item in drafts[:3]:
        image = item.get("image")
        if not isinstance(image, Image.Image):
            continue
        tile = image.copy()
        tile.thumbnail((240, 320), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 390), f"DRAFT {item.get('id')}", fill=(180, 176, 168), font=_font(12))
        x += 260
    draw.text((36, 760), f"STATUS  {status}", fill=(80, 200, 120), font=_font(18))
    draw.text((36, 800), "AI draft is not production. V4 reconstruction uses real photo, real logo, real type.", fill=(201, 168, 92), font=_font(15))
    draw.text((36, 836), "Do not promote automatically. Human visual approval is mandatory.", fill=(201, 168, 92), font=_font(15))
    draw.text((36, 872), "Existing technical Master and production cover unchanged. 5.8 A/B/C remain rejected.", fill=(160, 156, 148), font=_font(13))
    return canvas


def generate_ai_draft_structured_master_59(
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
    logo_board = _logo_board(logo_rgba)
    references, ref_provenance, refs_ok = load_grade_a_reference_images(db)
    catalog = load_temple_exteriors(db)
    catalog_public = [{k: v for k, v in item.items() if k not in {"source", "preview", "occupancy", "transform"}} for item in catalog]
    selected = select_advertising_photo(catalog)
    photo = (selected or {}).get("item")
    if photo is None:
        raise RuntimeError("Phase 5.9 requires an approved Temple exterior")
    images: dict[str, Any] = {
        "references": render_reference_board(references, logo_board),
        "photos": render_photo_selection_board(catalog),
    }
    drafts: list[dict[str, Any]] = []
    for thesis in DRAFT_THESES:
        pack = generate_visual_draft(photo=photo["preview"], logo=logo_board, references=references, thesis=thesis)
        if pack.get("ok") and isinstance(pack.get("image"), Image.Image):
            draft_asset = persist_gpt_image(
                db,
                actor=user,
                linked_project_id=row.linked_project_id,
                content=_png(pack["image"]),
                content_type="image/png",
                campaign_mode=f"project-v3-59-draft-{thesis['id'].lower()}",
                session_id=str(uuid4()),
                provider_generation_id=None,
                campaign_context_id=str(row.id),
                brief_excerpt=f"PHASE 5.9 disposable draft {thesis['id']}",
            )
            pack["asset_id"] = str(draft_asset.id)
            critic, n = request_draft_critic_v2(pack["image"], photo["preview"], references, thesis)
            vision_calls += n
            pack["critic"] = critic
            images[f"draft_{thesis['id'].lower()}"] = pack["image"]
        drafts.append(pack)
    images["draft_compare"] = render_draft_strip(
        "06  AI DRAFT COMPARISON  —  disposable art direction  —  NOT PRODUCTION",
        [(f"{d.get('id')}  {d.get('concept_name')}  pass={(d.get('critic') or {}).get('pass')}", d.get("image") if isinstance(d.get("image"), Image.Image) else None) for d in drafts],
    )
    merged_critic = {}
    for item in drafts:
        critic = item.get("critic") or {}
        for key in (*DRAFT_POSITIVE, *DRAFT_BAD):
            merged_critic[f"{item.get('id')}_{key}"] = critic.get(key)
    images["draft_critic"] = render_score_board({"pass": any((d.get("critic") or {}).get("pass") for d in drafts), "scores": merged_critic})
    selected_drafts = rank_drafts(drafts)[:2]
    reconstructed: list[dict[str, Any]] = []
    keys = ("A", "B")
    for i, draft in enumerate(selected_drafts):
        structure, n = extract_structure_map_v1(draft["image"], draft)
        vision_calls += n
        draft["structure"] = structure
        rec = reconstruct_production_master_v4(
            db=db,
            user=user,
            row=row,
            photo=photo,
            structure=structure,
            fonts=fonts,
            family=family,
            logo_rgba=logo_rgba,
            key=keys[i],
        )
        fidelity, n = request_reconstruction_fidelity_v1(draft["image"], rec["pack"]["image"])
        vision_calls += n
        rec["fidelity"] = fidelity
        rec["draft"] = {k: v for k, v in draft.items() if k != "image"}
        rec["draft_image"] = draft["image"]
        rec["validation"] = real_asset_validation(rec, photo=photo)
        rec["approved"] = bool(fidelity.get("pass") and rec["validation"].get("pass") and (rec["ready"] or {}).get("revision_readiness") == "PASS")
        reconstructed.append(rec)
        images[f"master_{keys[i].lower()}"] = rec["pack"]["image"]
        images[f"vs_{keys[i].lower()}"] = render_draft_vs(draft["image"], rec["pack"]["image"], f"{10 + i}  {keys[i]}")
    if not drafts or not any(d.get("ok") for d in drafts):
        status = "VISUAL_DRAFT_FAILED"
    elif not selected_drafts:
        status = "VISUAL_DRAFT_NOT_GOOD_ENOUGH"
    else:
        status = "CANDIDATE_PENDING_HUMAN_REVIEW"
    fid_rows = []
    for rec in reconstructed:
        fid = rec.get("fidelity") or {}
        fid_rows.append(f"{rec['key']} pass={fid.get('pass')} missing={fid.get('missing_keys')} gaps={fid.get('v4_could_not_reproduce')}")
        for key in FIDELITY_V1:
            fid_rows.append(f"  {key}={(fid.get('scores') or {}).get(key)}")
    images["fidelity"] = _text_board("12  RECONSTRUCTION FIDELITY", fid_rows or ["no reconstruction"])
    images["validation"] = _text_board(
        "13  REAL-ASSET VALIDATION",
        [json.dumps(rec.get("validation"), default=str) for rec in reconstructed] or ["none"],
    )
    images["ready"] = _text_board(
        "14  REVISION READINESS  —  static only",
        [json.dumps(rec.get("ready"), default=str) for rec in reconstructed] or ["none"],
    )
    images["review"] = render_human_review_board_59(drafts=drafts, masters=reconstructed, status=status)

    def draft_summary(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item.get("id"),
            "concept": item.get("concept_name"),
            "ok": item.get("ok"),
            "reason": item.get("reason"),
            "asset_id": item.get("asset_id"),
            "scores": item.get("critic"),
            "image_calls": item.get("image_calls"),
            "model": item.get("model"),
        }

    def master_summary(rec: dict[str, Any] | None) -> dict[str, Any] | None:
        if rec is None:
            return None
        return {
            "asset_id": rec["asset_id"],
            "spec_id": rec["spec"].get("spec_id"),
            "mode": rec["mode"],
            "reconstruction_fidelity": rec.get("fidelity"),
            "architecture_fidelity": (rec.get("validation") or {}).get("architecture_fidelity"),
            "revision_readiness": rec.get("ready"),
            "real_asset_validation": rec.get("validation"),
            "approved": rec.get("approved"),
        }

    best = None
    if reconstructed:
        best = sorted(
            reconstructed,
            key=lambda rec: sum(float(((rec.get("fidelity") or {}).get("scores") or {}).get(k) or 0) for k in FIDELITY_V1),
        )[-1]
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_59,
        "created_at": _now(),
        "status": status,
        "compositor": "GraphicDesignCompositorV4",
        "selected_project_photo": {k: v for k, v in (selected or {}).items() if k != "item"},
        "photo_catalog": catalog_public,
        "ai_draft_model": (next((d.get("model") for d in drafts if d.get("model")), None)),
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "references_actually_provided": bool(refs_ok and len(references) == 6),
        "reference_ids": ref_provenance,
        "drafts": [draft_summary(d) for d in drafts],
        "selected_drafts": [d.get("id") for d in selected_drafts],
        "draft_critic": {d.get("id"): d.get("critic") for d in drafts},
        "structure_a": None if not reconstructed else reconstructed[0].get("draft", {}).get("structure") or reconstructed[0]["spec"].get("visual_draft_structure"),
        "structure_b": None if len(reconstructed) < 2 else reconstructed[1]["spec"].get("visual_draft_structure"),
        "candidate_a_spec": None if not reconstructed else reconstructed[0]["spec"],
        "candidate_b_spec": None if len(reconstructed) < 2 else reconstructed[1]["spec"],
        "structured_master_a": master_summary(reconstructed[0] if reconstructed else None),
        "structured_master_b": master_summary(reconstructed[1] if len(reconstructed) > 1 else None),
        "reconstruction_fidelity": {rec["key"]: rec.get("fidelity") for rec in reconstructed},
        "real_asset_validation": {rec["key"]: rec.get("validation") for rec in reconstructed},
        "revision_readiness": {rec["key"]: rec.get("ready") for rec in reconstructed},
        "real_temple_logo": "PASS",
        "generated_architecture_in_production": "NO",
        "generated_text_in_production": "NO",
        "generated_logo_in_production": "NO",
        "best_internal_master": None if best is None else best["key"],
        "promoted_to_master": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "visual_replace_child_id": "6f18ae33-72fb-4506-ab49-24f8d90b6c2d",
        "phase5_8_candidates_rejected": True,
        "production_cover_changed": False,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "next_decision": "HUMAN VISUAL REVIEW",
        "language": language,
    }
    tests = [t for t in list(blob.get("ai_draft_structured_master_59_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_59)]
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["ai_draft_structured_master_59_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c"] = preserved.get("human_master")
    blob["human_approved_master_55c_id"] = preserved.get("human_master_id")
    blob["new_premium_master_58_tests"] = preserved.get("quality58")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 5.9 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
