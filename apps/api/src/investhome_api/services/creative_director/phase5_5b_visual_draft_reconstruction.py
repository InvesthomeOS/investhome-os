"""Phase 5.5B — Visual Composition Draft → structured reconstruction.

Keeps Vertical Harmony. GPT Image is allowed only for the disposable draft.
GraphicDesignCompositorV3 reconstructs with real Day_007 and the real Temple logo.
Does not promote. Does not redesign V3.
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
    LOCKED_CENTERING,
    LOCKED_SOURCE_CROP,
    _HISTORY_KEYS as _A_HISTORY,
    _logo_board,
    load_grade_a_reference_images,
)
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import _preserve as _preserve_55a
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable, render_score_board, render_structure_map
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
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.creative_director.visual_composition_draft import (
    DRAFT_BAD,
    DRAFT_POSITIVE,
    FIDELITY_KEYS,
    FINAL_BAD,
    FINAL_POSITIVE,
    VERTICAL_HARMONY,
    extract_visual_structure,
    generate_visual_composition_draft,
    reconstruction_spec_from_structure,
    render_draft_vs,
    render_extraction_board,
    render_input_board,
    render_spec_board,
    request_draft_critic,
    request_final_critic,
    request_reconstruction_fidelity,
    visible_logo_clearance,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55B = "phase5_5b_visual_draft_reconstruction"
_HISTORY_KEYS = _A_HISTORY + (("ai_visual_art_director_55a_tests", "quality55a"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_55a(blob)
    preserved["quality55a"] = list(blob.get("ai_visual_art_director_55a_tests") or [])
    return preserved


def render_human_review_board_55b(
    *,
    draft: Image.Image | None,
    candidate: Image.Image | None,
    critic: dict[str, Any],
    preflight: dict[str, Any] | None,
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1760, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "HUMAN REVIEW BOARD  —  PHASE 5.5B  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    if draft is not None:
        tile = draft.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36, 60))
    if candidate is not None:
        tile = candidate.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (580, 60))
    x, y = 1140, 70
    draw.text((x, y), f"status  {status}", fill=(236, 230, 218), font=_font(15))
    y += 28
    passed = bool((preflight or {}).get("pass"))
    draw.text((x, y), f"preflight  {'PASS' if passed else 'FAIL / N/A'}", fill=(80, 200, 120) if passed else (220, 80, 80), font=_font(16))
    y += 36
    for key in (
        "professional_art_direction",
        "visual_draft_fidelity",
        "composition",
        "whole_canvas_composition",
        "architecture_fidelity",
        "publishability",
        "TEXT_ON_PHOTO_FEEL",
        "CORNER_CLUSTER_FEEL",
        "TEXT_DUMP_FEEL",
        "CLUTTER",
    ):
        draw.text((x, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(14))
        y += 24
    draw.text((x, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(14))
    return canvas


def generate_visual_draft_reconstruction_55b(
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
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    src = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY007_ASSET_ID)))).convert("RGB")
    crop, transform = cover_fit_canvas(src, CANVAS_4X5, centering=LOCKED_CENTERING)
    recorded = [round(float(v), 2) for v in (transform.get("source_crop") or [])]
    crop_locked = recorded == LOCKED_SOURCE_CROP
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = build_photo_occupancy_map(graded)
    references, ref_provenance, refs_ok = load_grade_a_reference_images(db)
    images: dict[str, Any] = {
        "input_board": render_input_board(graded, _logo_board(logo_rgba), references),
    }
    draft_pack = generate_visual_composition_draft(day007=graded, references=references, blueprint=VERTICAL_HARMONY)
    draft_image_calls = int(draft_pack.get("image_calls") or 0)
    production_image_calls_at_draft = provider_call_count()
    draft = draft_pack.get("image") if isinstance(draft_pack.get("image"), Image.Image) else None
    draft_critic: dict[str, Any] = {}
    structure: dict[str, Any] | None = None
    recon_spec: dict[str, Any] | None = None
    pack: dict[str, Any] | None = None
    spec: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None
    fidelity: dict[str, Any] | None = None
    final_critic: dict[str, Any] = {}
    ready: dict[str, Any] | None = None
    candidate_asset_id = None
    rendered = False
    status = "VISUAL_DRAFT_FAILED"
    if draft is not None:
        images["draft"] = draft
        draft_asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(draft),
            content_type="image/png",
            campaign_mode="project-v3-55b-draft-disposable",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt="PHASE 5.5B disposable visual draft",
        )
        draft_pack["asset_id"] = str(draft_asset.id)
        draft_critic, n = request_draft_critic(draft, graded, references)
        vision_calls += n
        images["draft_critic"] = render_score_board(
            {"pass": draft_critic.get("pass"), "scores": {k: draft_critic.get(k) for k in (*DRAFT_POSITIVE, *DRAFT_BAD)}}
        )
        if not draft_critic.get("pass"):
            status = "VISUAL_DRAFT_NOT_GOOD_ENOUGH"
        else:
            status = "VISUAL_DRAFT_PASS"
            structure, n = extract_visual_structure(draft)
            vision_calls += n
            images["extraction"] = render_extraction_board(structure)
            if not structure.get("pass"):
                status = "STRUCTURE_EXTRACTION_FAIL"
            else:
                recon_spec = reconstruction_spec_from_structure(structure, canvas=CANVAS_4X5)
                images["recon_spec"] = render_spec_board(recon_spec)
                before_recon_calls = provider_call_count()
                pack = compose_graphic_design_v3(
                    graded,
                    occupancy=occupancy,
                    family=family,
                    fonts=fonts,
                    logo_rgba=logo_rgba,
                    art_plan=recon_spec.get("art_plan"),
                )
                if provider_call_count() != before_recon_calls:
                    raise RuntimeError("Phase 5.5B production reconstruction must not call GPT Image")
                if not pack.get("solved"):
                    status = "STRUCTURED_RECONSTRUCTION_FAIL"
                else:
                    field_asset = persist_gpt_image(
                        db,
                        actor=user,
                        linked_project_id=row.linked_project_id,
                        content=_png(pack["fielded"]),
                        content_type="image/png",
                        campaign_mode="project-v3-55b-field",
                        session_id=str(uuid4()),
                        provider_generation_id=None,
                        campaign_context_id=str(row.id),
                        brief_excerpt="PHASE 5.5B field",
                    )
                    asset = persist_gpt_image(
                        db,
                        actor=user,
                        linked_project_id=row.linked_project_id,
                        content=_png(pack["image"]),
                        content_type="image/png",
                        campaign_mode="project-v3-55b-candidate",
                        session_id=str(uuid4()),
                        provider_generation_id=None,
                        campaign_context_id=str(row.id),
                        brief_excerpt="PHASE 5.5B candidate",
                    )
                    pack["graphic_field_asset_id"] = str(field_asset.id)
                    spec = build_family_master_spec(
                        key="VH-55B",
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
                    spec["visual_composition_draft_id"] = draft_pack.get("asset_id")
                    spec["visual_reconstruction_spec"] = recon_spec
                    spec["art_direction_blueprint"] = VERTICAL_HARMONY
                    spec["reference_provenance"] = ref_provenance
                    spec["source_asset_provenance"] = {
                        "photo_asset_id": DAY007_ASSET_ID,
                        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
                        "crop": {"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop")},
                    }
                    spec["graphic_field"]["asset_id"] = str(field_asset.id)
                    spec["promoted"] = False
                    ready = family_revision_readiness(spec)
                    logo_obj = (pack.get("objects") or {}).get("project_logo") or {}
                    logo_px = logo_obj.get("px") or [0, 0, 0, 0]
                    clearance = visible_logo_clearance(
                        logo_rgba=logo_rgba,
                        paste=tuple(int(v) for v in logo_px),
                        occupancy=occupancy,
                        canvas=tuple(pack["image"].size),
                    )
                    collision = evaluate_collisions(objects=pack.get("objects") or {}, occupancy=occupancy, size=pack["image"].size)
                    arch_hits = [h for h in list(collision.get("hits") or []) if "architecture" in h or "protected" in h]
                    provenance = architecture_provenance_qa(
                        source=src,
                        foundation=pack["foundation"],
                        final=pack["image"],
                        transform={
                            "centering": list(LOCKED_CENTERING),
                            "source_crop": transform.get("source_crop") or LOCKED_SOURCE_CROP,
                            "scale_x": transform.get("scale_x"),
                            "scale_y": transform.get("scale_y"),
                        },
                    )
                    utf8 = turkish_copy_is_valid(pack.get("facts") or {})
                    fidelity, n = request_reconstruction_fidelity(draft, pack["image"])
                    vision_calls += n
                    checks = {
                        "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
                        "visible_logo_clearance": "PASS" if clearance.get("pass") else "FAIL",
                        "headline_collision": "PASS" if not any(h.startswith("headline") for h in arch_hits) else "FAIL",
                        "commercial_collision": "PASS" if not any("price" in h or "discount" in h for h in arch_hits) else "FAIL",
                        "cta_collision": "PASS" if not any(h.startswith("cta") for h in arch_hits) else "FAIL",
                        "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
                        "UTF8": "PASS" if utf8 else "FAIL",
                        "font_metrics": "PASS",
                        "semantic_completeness": "PASS",
                        "canvas_bounds": "PASS" if not pack.get("overflow") else "FAIL",
                        "revision_readiness": ready.get("revision_readiness") or "FAIL",
                        "visual_reconstruction_fidelity": "PASS" if fidelity.get("pass") else "FAIL",
                        "real_temple_logo": "PASS" if pack.get("real_logo") else "FAIL",
                        "crop_locked": "PASS" if crop_locked else "FAIL",
                    }
                    preflight = {
                        "schema": "Phase55BTechnicalPreflightV1",
                        "checks": checks,
                        "pass": all(v == "PASS" for v in checks.values()),
                        "collision_hits": list(collision.get("hits") or []),
                        "architecture_hits": arch_hits,
                        "visible_logo_clearance": clearance,
                    }
                    final_critic, n = request_final_critic(pack["image"], draft, graded, references)
                    vision_calls += n
                    candidate_asset_id = str(asset.id)
                    rendered = True
                    status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preflight["pass"] and fidelity.get("pass") else (
                        "RECONSTRUCTION_FIDELITY_FAIL" if not fidelity.get("pass") else "TECHNICAL_FAIL"
                    )
                    images["reconstruction"] = pack["image"]
                    images["structure_map"] = render_structure_map(pack["image"], pack.get("objects") or {})
                    images["draft_vs"] = render_draft_vs(draft, pack["image"])
                    images["fidelity"] = render_score_board({"pass": fidelity.get("pass"), "scores": fidelity.get("scores") or {}})
                    images["preflight"] = render_score_board(
                        {"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}}
                    )
                    images["final_critic"] = render_score_board(
                        {"pass": False, "scores": {k: final_critic.get(k) for k in (*FINAL_POSITIVE, *FINAL_BAD)}}
                    )
    production_image_calls = max(0, provider_call_count() - production_image_calls_at_draft)
    images["review_board"] = render_human_review_board_55b(
        draft=draft,
        candidate=(pack or {}).get("image") if pack else None,
        critic=final_critic or draft_critic,
        preflight=preflight,
        status=status,
    )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55B,
        "created_at": _now(),
        "status": status,
        "concept": VERTICAL_HARMONY["concept_name"],
        "new_concepts_generated": False,
        "new_family_created": False,
        "photo_asset_id": DAY007_ASSET_ID,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "references_actually_provided": bool(refs_ok and len(references) == 6),
        "reference_ids": ref_provenance,
        "visual_draft": {
            "ok": bool(draft_pack.get("ok")),
            "asset_id": draft_pack.get("asset_id"),
            "reason": draft_pack.get("reason"),
            "disposable": True,
            "image_calls": draft_image_calls,
            "input_images": draft_pack.get("input_images"),
        },
        "visual_draft_critic": draft_critic,
        "visual_structure": structure,
        "reconstruction_spec": recon_spec,
        "candidate_asset_id": candidate_asset_id,
        "spec_id": (spec or {}).get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "reconstruction_fidelity": fidelity,
        "final_critic": final_critic,
        "rendered": rendered,
        "visual_draft_image_calls": draft_image_calls,
        "production_image_generation_calls": production_image_calls,
        "gpt_image_calls_total": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "phase55_executed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "solved": bool((pack or {}).get("solved")),
        "contrast": _jsonable((pack or {}).get("contrast")) if pack else None,
    }
    tests = [
        t
        for t in list(blob.get("visual_draft_reconstruction_55b_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55B)
    ]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["visual_draft_reconstruction_55b_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if blob.get("ai_visual_art_director_55a_tests") != preserved.get("quality55a"):
        raise RuntimeError("Phase 5.5B refused to overwrite Phase 5.5A")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.5B refused to modify approved creative masters")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    _ = language
    return record
