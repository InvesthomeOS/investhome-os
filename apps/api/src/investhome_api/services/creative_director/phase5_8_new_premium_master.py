"""Phase 5.8 — new premium masters on GraphicDesignCompositorV4.

Concept chooses the approved Temple exterior. No V3 fallback. GPT Image = 0.
Does not promote. Does not modify existing masters.
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
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_ASSET_ID, PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import _logo_board
from investhome_api.services.creative_director.phase5_7_compositor_quality import _HISTORY_KEYS as _H57
from investhome_api.services.creative_director.phase5_7_compositor_quality import _preserve as _preserve_57
from investhome_api.services.creative_director.phase5_8_art_direction import (
    BAD_V3,
    BLUEPRINT_V3_FIELDS,
    FINAL_POSITIVE_V3,
    apply_blueprint_gate,
    fallback_blueprints,
    final_critic_v3_pass,
    measured_final_scores,
    merge_final_critic,
    render_photo_selection_board,
    request_blueprint_critic_v3,
    request_blueprints_v3,
    request_final_critic_v3,
    request_reference_craft_v3,
    translate_relational_plan,
)
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font, _wrap
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
from investhome_api.services.creative_director.premium_art_direction import (
    apply_layout_fault_caps,
    infer_mode,
    render_craft_v2_board,
)
from investhome_api.services.creative_director.reference_composition_map import build_reference_composition_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.creative_director.temple_exterior_catalog import crop_photo_for_mode, load_temple_exteriors, pick_photo_for_concept
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_58 = "phase5_8_new_premium_master"
_HISTORY_KEYS = _H57 + (("compositor_quality_57_tests", "quality57"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_57(blob)
    preserved["quality57"] = list(blob.get("compositor_quality_57_tests") or [])
    preserved["human_master"] = dict(blob.get("human_approved_master_55c") or preserved.get("human_master") or {})
    preserved["human_master_id"] = blob.get("human_approved_master_55c_id") or preserved.get("human_master_id")
    return preserved


def _field_mass(mask: Image.Image | None) -> float:
    if not isinstance(mask, Image.Image):
        return 0.0
    hist = mask.convert("L").histogram()
    return round(sum(hist[40:]) / max(1, sum(hist)), 4)


def _text_board(title: str, rows: list[str], size: tuple[int, int] = (1600, 2100)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), title, font=_font(22), fill=(232, 214, 170))
    y = 80
    for row in rows:
        for line in _wrap(str(row), 92):
            if y > size[1] - 36:
                return image
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 8
    return image


def render_three_way(rows: list[tuple[str, Image.Image | None]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "10  THREE-WAY COMPARISON  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    x = 36
    for label, image in rows[:3]:
        if image is not None:
            tile = image.copy()
            tile.thumbnail((580, 840), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 920), label[:48], fill=(180, 176, 168), font=_font(14))
        x += 620
    return canvas


def render_human_review_board_58(*, candidates: list[dict[str, Any]], status: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "15  HUMAN REVIEW BOARD  —  PHASE 5.8  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(16))
    x = 36
    for rec in candidates[:3]:
        tile = rec["pack"]["image"].copy()
        tile.thumbnail((520, 720), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 790), f"{rec['key']}  {rec['blueprint'].get('concept_name')}", fill=(236, 230, 218), font=_font(14))
        draw.text((x, 816), str((rec.get("photo") or {}).get("filename") or "")[:42], fill=(180, 176, 168), font=_font(12))
        x += 560
    draw.text((36, 860), f"STATUS  {status}", fill=(80, 200, 120), font=_font(18))
    draw.text((36, 896), "Do not promote automatically. Human visual approval is mandatory.", fill=(201, 168, 92), font=_font(16))
    draw.text((36, 932), "Existing technical Master and production cover unchanged.", fill=(160, 156, 148), font=_font(14))
    return canvas


def _render_one(
    *,
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    blueprint: dict[str, Any],
    photo: dict[str, Any],
    fonts: dict[str, Any],
    family: dict[str, Any],
    logo_rgba: Image.Image,
    key: str,
) -> dict[str, Any]:
    mode = str(blueprint.get("reconstruction_mode") or "SKY_VEIL")
    src, graded, occupancy, transform = crop_photo_for_mode(photo, mode)
    plan = translate_relational_plan(blueprint, mode=mode, photo=photo)
    pack = compose_relational_v4(
        graded,
        occupancy=occupancy,
        fonts=fonts,
        logo_rgba=logo_rgba,
        facts=_facts(None),
        art_plan=plan,
        family=family,
        scale=1.0,
    )
    if str(pack.get("schema") or "") != "GraphicDesignCompositorV4":
        raise RuntimeError("Phase 5.8 must use GraphicDesignCompositorV4")
    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["fielded"]),
        content_type="image/png",
        campaign_mode=f"project-v3-58-field-{key.lower()}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.8 field {key}",
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode=f"project-v3-58-candidate-{key.lower()}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.8 candidate {key}",
    )
    pack["graphic_field_asset_id"] = str(field_asset.id)
    spec = build_family_master_spec(
        key=f"P58-{key}",
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
    spec["art_direction_blueprint"] = blueprint
    spec["structured_art_direction_plan"] = plan
    spec["reconstruction_mode"] = mode
    spec["selected_photo_asset_id"] = photo["asset_id"]
    spec["selected_photo_filename"] = photo["filename"]
    spec["why_this_photo_supports_the_concept"] = blueprint.get("why_this_photo_supports_the_concept")
    spec["crop_strategy"] = blueprint.get("crop_strategy")
    spec["architecture_anchor"] = blueprint.get("architecture_anchor")
    spec["negative_space_opportunity"] = blueprint.get("negative_space_opportunity")
    spec["groups_v2"] = pack.get("groups_v2")
    spec["relationship_graph"] = pack.get("relationship_graph")
    spec["grouping"] = pack.get("groups") or spec.get("grouping")
    spec["promoted"] = False
    spec["parent_technical_master_id"] = PARENT_MASTER_ID
    spec["graphic_field"]["asset_id"] = str(field_asset.id)
    spec["graphic_field"]["overlay"] = mode
    ready = family_revision_readiness(spec)
    objects = pack.get("objects") or {}
    flow = pack.get("reading_flow") or reading_flow(objects)
    groups = pack.get("groups_v2") or groups_from_objects(objects, mode=mode)
    graph = pack.get("relationship_graph") or temple_relationship_graph(mode=mode)
    mass = _field_mass(pack.get("field_mask"))
    faults = detect_layout_faults(objects, field_mass=mass, islands=bool(flow.get("commercial_islands")))
    balance = creative_canvas_balance_v2(pack["image"], objects, pack.get("field_mask"), occupancy, groups)
    collision = evaluate_collisions(objects=objects, occupancy=occupancy, size=pack["image"].size)
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
    return {
        "key": key,
        "blueprint": blueprint,
        "mode": mode,
        "photo": {
            "asset_id": photo["asset_id"],
            "filename": photo["filename"],
            "why_this_photo_supports_the_concept": blueprint.get("why_this_photo_supports_the_concept"),
            "crop_strategy": blueprint.get("crop_strategy"),
            "architecture_anchor": blueprint.get("architecture_anchor"),
            "negative_space_opportunity": blueprint.get("negative_space_opportunity"),
        },
        "pack": pack,
        "spec": spec,
        "asset_id": str(asset.id),
        "ready": ready,
        "flow": flow,
        "groups": groups,
        "graph": graph,
        "faults": faults,
        "balance": balance,
        "collision": collision,
        "provenance": provenance,
        "utf8": turkish_copy_is_valid(pack.get("facts") or {}),
        "field_mass": mass,
        "graded": graded,
    }


def generate_new_premium_master_58(
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
    maps = [build_reference_composition_map(image, filename=name) for name, image in references]
    catalog = load_temple_exteriors(db)
    catalog_public = [{k: v for k, v in item.items() if k not in {"source", "preview", "occupancy", "transform"}} for item in catalog]
    craft, n = request_reference_craft_v3(references=references, maps=maps, logo=logo_board)
    vision_calls += n
    attempts: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    used_names: set[str] = set()
    used_modes: set[str] = set()
    fallback = fallback_blueprints()
    fallback_i = 0
    while len(eligible) < 3 and len(attempts) < 6:
        needed = min(3 if not attempts else max(1, 3 - len(eligible)), 6 - len(attempts))
        batch, n = request_blueprints_v3(
            craft=craft,
            maps=maps,
            photos=catalog,
            logo=logo_board,
            needed=needed,
            used_names=used_names,
            used_modes=used_modes,
        )
        vision_calls += n
        if not batch:
            batch = fallback[fallback_i : fallback_i + needed]
            fallback_i += needed
        for i, item in enumerate(batch):
            mode = infer_mode(item, len(attempts) + i, used_modes)
            item["reconstruction_mode"] = mode
            item["structured_reconstruction_plan"] = {"mode": mode}
        critic, n = request_blueprint_critic_v3(batch)
        vision_calls += n
        vision_scored = any(item.get("critic_source") == "vision" for item in batch)
        for item in batch:
            attempts.append(item)
            name = str(item.get("concept_name") or "")
            mode = str(item.get("reconstruction_mode") or "")
            if item.get("critic_pass") and mode not in used_modes:
                eligible.append(item)
                used_modes.add(mode)
                used_names.add(name)
            if len(attempts) >= 6 or len(eligible) >= 3:
                break
        if len(eligible) < 3 and not vision_scored:
            for item in fallback:
                if len(eligible) >= 3 or len(attempts) >= 6:
                    break
                mode = str(item.get("reconstruction_mode") or "")
                if mode in used_modes:
                    continue
                apply_blueprint_gate(item, source="structural_fallback")
                attempts.append(item)
                if item.get("critic_pass"):
                    eligible.append(item)
                    used_modes.add(mode)
                    used_names.add(str(item.get("concept_name") or ""))
            break
    images: dict[str, Any] = {
        "craft": render_craft_v2_board(craft, references),
        "photos": render_photo_selection_board(catalog),
        "ad1": _text_board("03  BLUEPRINT A", [f"{k}: {(eligible[0] if eligible else (attempts[0] if attempts else {})).get(k)}" for k in ("concept_name", "reconstruction_mode", "selected_project_photo", *BLUEPRINT_V3_FIELDS)]),
        "ad2": _text_board("04  BLUEPRINT B", [f"{k}: {(eligible[1] if len(eligible) > 1 else (attempts[1] if len(attempts) > 1 else {})).get(k)}" for k in ("concept_name", "reconstruction_mode", "selected_project_photo", *BLUEPRINT_V3_FIELDS)]),
        "ad3": _text_board("05  BLUEPRINT C", [f"{k}: {(eligible[2] if len(eligible) > 2 else (attempts[2] if len(attempts) > 2 else {})).get(k)}" for k in ("concept_name", "reconstruction_mode", "selected_project_photo", *BLUEPRINT_V3_FIELDS)]),
        "blueprint_compare": _text_board(
            "06  BLUEPRINT COMPARISON",
            [f"{item.get('id')}  {item.get('concept_name')}  mode={item.get('reconstruction_mode')}  pass={item.get('critic_pass')}  photo={item.get('selected_project_photo')}" for item in attempts]
            + [f"{key}: {(eligible[i] if i < len(eligible) else {}).get(key)}" for i in range(min(3, max(1, len(eligible)))) for key in BLUEPRINT_V3_FIELDS[:8]],
        ),
    }
    rendered: list[dict[str, Any]] = []
    used_photos: set[str] = set()
    keys = ("A", "B", "C")
    before_calls = provider_call_count()
    for i, blueprint in enumerate(eligible[:3]):
        photo = pick_photo_for_concept(
            catalog,
            mode=str(blueprint.get("reconstruction_mode") or "SKY_VEIL"),
            used=used_photos,
            requested_filename=str(blueprint.get("selected_project_photo") or ""),
            requested_asset_id=str(blueprint.get("selected_photo_asset_id") or ""),
        )
        if photo is None:
            continue
        used_photos.add(photo["asset_id"])
        rec = _render_one(
            db=db,
            user=user,
            row=row,
            blueprint=blueprint,
            photo=photo,
            fonts=fonts,
            family=family,
            logo_rgba=logo_rgba,
            key=keys[i],
        )
        if provider_call_count() != before_calls:
            raise RuntimeError("Phase 5.8 must not call GPT Image")
        critic_final, n = request_final_critic_v3(rec["pack"]["image"], rec["graded"], references, blueprint)
        vision_calls += n
        measured = measured_final_scores(
            faults=rec["faults"],
            balance=rec["balance"] or {},
            flow=rec["flow"] or {},
            provenance=rec["provenance"] or {},
            utf8=bool(rec["utf8"]),
        )
        critic_final = merge_final_critic(critic_final, measured)
        critic_final = apply_layout_fault_caps(
            critic_final,
            rec["pack"]["objects"],
            field_mass=rec["field_mass"],
            islands=bool(rec["flow"].get("commercial_islands")),
        )
        rec["final_critic"] = critic_final
        rec["critic_pass"] = final_critic_v3_pass(critic_final, dead_space_score=float((rec["balance"] or {}).get("dead_space_score") or 99))
        rec["penalties"] = critic_final.get("layout_faults") or rec["faults"]
        rendered.append(rec)
        images[f"candidate_{keys[i].lower()}"] = rec["pack"]["image"]
    status = "CANDIDATE_PENDING_HUMAN_REVIEW" if rendered else "NO_BLUEPRINT_AT_PRODUCTION_QUALITY"
    images["three_way"] = render_three_way([(f"{r['key']}  {r['blueprint'].get('concept_name')}", r["pack"]["image"]) for r in rendered] or [("none", None)])
    images["graphs"] = _text_board(
        "11  RELATIONSHIP GRAPHS",
        [
            f"{r['key']}  " + "; ".join(f"{e['source_element']} {e['relationship_type']} {e['target_element']}" for e in (r["graph"].get("edges") or [])[:8])
            for r in rendered
        ],
    )
    images["flow"] = _text_board(
        "12  READING FLOW",
        [f"{r['key']}  path={r['flow'].get('reading_path')}  islands={r['flow'].get('commercial_islands')}  rejected={r['flow'].get('rejected')}" for r in rendered],
    )
    images["balance"] = _text_board(
        "13  CANVAS BALANCE V2",
        [f"{r['key']}  dead={r['balance'].get('dead_space_score')}  roles={[c.get('space_role') for c in (r['balance'].get('regions') or [])]}" for r in rendered],
    )
    merged: dict[str, Any] = {}
    for rec in rendered:
        for key in (*FINAL_POSITIVE_V3, *BAD_V3):
            merged[f"{rec['key']}_{key}"] = (rec.get("final_critic") or {}).get(key)
    images["final_critic"] = render_score_board({"pass": any(r.get("critic_pass") for r in rendered), "scores": merged})
    images["review"] = render_human_review_board_58(candidates=rendered, status=status)
    if provider_call_count() != 0:
        raise RuntimeError("Phase 5.8 must not call GPT Image")
    best = None
    if rendered:
        best = sorted(rendered, key=lambda rec: float((rec.get("final_critic") or {}).get("professional_art_direction") or 0))[-1]

    def cand(rec: dict[str, Any] | None) -> dict[str, Any] | None:
        if rec is None:
            return None
        return {
            "concept": rec["blueprint"].get("concept_name"),
            "mode": rec["mode"],
            "project_photo": rec["photo"]["filename"],
            "selected_photo_asset_id": rec["photo"]["asset_id"],
            "asset_id": rec["asset_id"],
            "spec_id": rec["spec"].get("spec_id"),
            "scores": rec.get("final_critic"),
            "revision_readiness": rec.get("ready"),
            "penalties": rec.get("penalties"),
            "critic_pass": rec.get("critic_pass"),
        }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_58,
        "created_at": _now(),
        "status": status,
        "compositor": "GraphicDesignCompositorV4",
        "references_actually_provided": bool(refs_ok and len(references) == 6),
        "reference_ids": ref_provenance,
        "reference_craft": craft,
        "photo_catalog": catalog_public,
        "blueprint_attempts": len(attempts),
        "eligible_blueprint_count": len(eligible),
        "blueprints": attempts,
        "eligible_blueprints": eligible,
        "candidate_a": cand(rendered[0] if rendered else None),
        "candidate_b": cand(rendered[1] if len(rendered) > 1 else None),
        "candidate_c": cand(rendered[2] if len(rendered) > 2 else None),
        "candidate_a_spec": None if not rendered else rendered[0]["spec"],
        "candidate_b_spec": None if len(rendered) < 2 else rendered[1]["spec"],
        "candidate_c_spec": None if len(rendered) < 3 else rendered[2]["spec"],
        "relationship_graphs": [r["graph"] for r in rendered],
        "reading_flow": [r["flow"] for r in rendered],
        "canvas_balance": [r["balance"] for r in rendered],
        "final_critic": {r["key"]: r.get("final_critic") for r in rendered},
        "revision_readiness": {r["key"]: r.get("ready") for r in rendered},
        "critic_penalties": {r["key"]: r.get("penalties") for r in rendered},
        "best_internal_candidate": None if best is None else best["key"],
        "gpt_image_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "visual_replace_child_id": "6f18ae33-72fb-4506-ab49-24f8d90b6c2d",
        "production_cover_changed": False,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "next_decision": "HUMAN VISUAL REVIEW",
    }
    tests = [t for t in list(blob.get("new_premium_master_58_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_58)]
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["new_premium_master_58_tests"] = tests
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
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 5.8 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    _ = language
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
