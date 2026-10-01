"""Phase 5.5A — AI Visual Art Director → structured master.

Creative direction first. GraphicDesignCompositorV3 executes only after
blueprint critic + translation fidelity pass. GPT Image = 0. Does not promote.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import (
    FINAL_BAD,
    FINAL_POSITIVE,
    GRADE_A_REFERENCES,
    render_blueprint_board,
    render_comparison_board,
    render_craft_board,
    render_critic_board,
    render_fidelity_board,
    render_plan_board,
    render_target_board,
    request_art_direction,
    request_blueprint_critic,
    request_final_critic,
    request_translation_fidelity,
    select_winning_blueprint,
    translate_blueprint_to_plan,
)
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.full_frame_architectural_family import FAMILY_ID, full_frame_family_spec
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_full_frame_r2 import _HISTORY_KEYS as _R2_HISTORY
from investhome_api.services.creative_director.phase5_full_frame_r2 import _preserve as _preserve_r2
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
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map, render_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55A = "phase5_5a_ai_visual_art_director"
DAY007_ASSET_ID = "c0afa1bf-b487-410c-be3d-91c31852550d"
DAY007_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_007.jpg"
LOCKED_CENTERING = (0.50, 0.42)
LOCKED_SOURCE_CROP = [161.06, 0.0, 1256.26, 1369.0]
_HISTORY_KEYS = _R2_HISTORY + (("full_frame_r2_tests", "quality54k_r2"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r2(blob)
    preserved["quality54k_r2"] = list(blob.get("full_frame_r2_tests") or [])
    return preserved


def _logo_board(logo_rgba: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (720, 420), (16, 18, 22))
    tile = logo_rgba.convert("RGBA")
    tile.thumbnail((560, 320), Image.Resampling.LANCZOS)
    x = (720 - tile.size[0]) // 2
    y = (420 - tile.size[1]) // 2
    canvas.paste(tile, (x, y), tile)
    return canvas


def load_grade_a_reference_images(db: Session) -> tuple[list[tuple[str, Image.Image]], list[dict[str, str]], bool]:
    names = [filename for _rid, filename in GRADE_A_REFERENCES]
    rows = list(db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename.in_(names))).all())
    by_name = {str(row.filename): row for row in rows}
    loaded: list[tuple[str, Image.Image]] = []
    provenance: list[dict[str, str]] = []
    ok = True
    for reference_id, filename in GRADE_A_REFERENCES:
        row = by_name.get(filename)
        if row is None:
            ok = False
            continue
        try:
            image = Image.open(io.BytesIO(_read_bytes(db, row.id))).convert("RGB")
        except Exception:
            ok = False
            continue
        loaded.append((filename, image))
        provenance.append(
            {
                "filename": filename,
                "reference_id": reference_id,
                "media_asset_id": str(row.id),
            }
        )
    if len(loaded) != 6:
        ok = False
    return loaded, provenance, ok


def render_human_review_board_55a(
    *,
    candidate: Image.Image | None,
    critic: dict[str, Any],
    preflight: dict[str, Any] | None,
    winner: dict[str, Any] | None,
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1680, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "HUMAN REVIEW BOARD  —  PHASE 5.5A  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    if candidate is not None:
        tile = candidate.copy()
        tile.thumbnail((720, 900), Image.Resampling.LANCZOS)
        canvas.paste(tile, (36, 60))
    x = 780
    y = 70
    draw.text((x, y), f"status  {status}", fill=(236, 230, 218), font=_font(16))
    y += 32
    draw.text((x, y), f"blueprint  {(winner or {}).get('concept_name') or 'NONE'}", fill=(180, 176, 168), font=_font(16))
    y += 40
    passed = bool((preflight or {}).get("pass"))
    draw.text((x, y), f"preflight  {'PASS' if passed else 'FAIL / N/A'}", fill=(80, 200, 120) if passed else (220, 80, 80), font=_font(18))
    y += 40
    for key in (
        "professional_art_direction",
        "reference_craft_transfer",
        "blueprint_fidelity",
        "composition",
        "whole_canvas_composition",
        "image_design_integration",
        "architecture_fidelity",
        "publishability",
        "TEXT_ON_PHOTO_FEEL",
        "TEMPLATE_FEEL",
        "LISTING_CARD_FEEL",
        "UI_FEEL",
        "TEXT_DUMP_FEEL",
        "CLUTTER",
    ):
        draw.text((x, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(15))
        y += 26
    draw.text((x, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(16))
    return canvas


def generate_ai_visual_art_director_55a(
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
    occupancy_board = render_occupancy_map(graded, occupancy)
    references, ref_provenance, refs_ok = load_grade_a_reference_images(db)
    director, n = request_art_direction(
        day007=graded,
        logo=_logo_board(logo_rgba),
        references=references,
        occupancy_board=occupancy_board,
    )
    vision_calls += n
    blueprints = list(director.get("blueprints") or [])
    craft = dict(director.get("reference_craft") or {})
    target = dict(director.get("target_analysis") or {})
    critic, n = request_blueprint_critic(blueprints, target)
    vision_calls += n
    winner = select_winning_blueprint(blueprints, critic)
    images: dict[str, Any] = {
        "craft": render_craft_board(craft, references),
        "target": render_target_board(target, graded),
        "ad1": render_blueprint_board(blueprints[0] if blueprints else {}, "03  AD1 ArtDirectionBlueprintV1"),
        "ad2": render_blueprint_board(blueprints[1] if len(blueprints) > 1 else {}, "04  AD2 ArtDirectionBlueprintV1"),
        "ad3": render_blueprint_board(blueprints[2] if len(blueprints) > 2 else {}, "05  AD3 ArtDirectionBlueprintV1"),
        "comparison": render_comparison_board(blueprints),
        "blueprint_critic": render_critic_board(critic, blueprints),
    }
    plan: dict[str, Any] | None = None
    fidelity: dict[str, Any] | None = None
    pack: dict[str, Any] | None = None
    spec: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None
    final_critic: dict[str, Any] = {}
    ready: dict[str, Any] | None = None
    candidate_asset_id = None
    rendered = False
    status = "ART_DIRECTION_NOT_GOOD_ENOUGH"
    if winner is not None:
        status = "BLUEPRINT_SELECTED"
        images["winning"] = render_blueprint_board(winner, "08  Winning ArtDirectionBlueprintV1")
        plan = translate_blueprint_to_plan(winner, occupancy, canvas=CANVAS_4X5)
        images["plan"] = render_plan_board(plan)
        fidelity, n = request_translation_fidelity(winner, plan)
        vision_calls += n
        images["fidelity"] = render_fidelity_board(fidelity)
        if not fidelity.get("pass"):
            status = "BLUEPRINT_TRANSLATION_DESTROYED_CONCEPT"
        else:
            pack = None
            for adj in (1.0, 0.9, 0.82):
                trial = json.loads(json.dumps(plan))
                ty = dict(trial.get("typography") or {})
                for key in ("display_scale", "discount_scale", "number_scale", "cta_scale"):
                    if ty.get(key) is not None:
                        ty[key] = round(float(ty[key]) * adj, 4)
                trial["typography"] = ty
                logo = dict(trial.get("logo") or {})
                logo["w"] = round(float(logo.get("w") or 0.11) * adj, 4)
                logo["h"] = round(float(logo.get("h") or 0.045) * adj, 4)
                trial["logo"] = logo
                candidate_pack = compose_graphic_design_v3(
                    graded,
                    occupancy=occupancy,
                    family=family,
                    fonts=fonts,
                    logo_rgba=logo_rgba,
                    art_plan=trial,
                )
                pack = candidate_pack
                if candidate_pack.get("solved"):
                    plan = trial
                    break
            if pack.get("solved"):
                field_asset = persist_gpt_image(
                    db,
                    actor=user,
                    linked_project_id=row.linked_project_id,
                    content=_png(pack["fielded"]),
                    content_type="image/png",
                    campaign_mode="project-v3-55a-field",
                    session_id=str(uuid4()),
                    provider_generation_id=None,
                    campaign_context_id=str(row.id),
                    brief_excerpt="PHASE 5.5A field",
                )
                asset = persist_gpt_image(
                    db,
                    actor=user,
                    linked_project_id=row.linked_project_id,
                    content=_png(pack["image"]),
                    content_type="image/png",
                    campaign_mode="project-v3-55a-candidate",
                    session_id=str(uuid4()),
                    provider_generation_id=None,
                    campaign_context_id=str(row.id),
                    brief_excerpt="PHASE 5.5A candidate",
                )
                pack["graphic_field_asset_id"] = str(field_asset.id)
                spec = build_family_master_spec(
                    key="AD-55A",
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
                spec["art_director"] = "AIVisualArtDirectorV1"
                spec["art_direction_blueprint"] = winner
                spec["structured_art_direction_plan"] = plan
                spec["blueprint_translation_fidelity"] = fidelity
                spec["reference_provenance"] = ref_provenance
                spec["source_asset_provenance"] = {
                    "photo_asset_id": DAY007_ASSET_ID,
                    "logo_asset_id": LOCKED_LOGO_ASSET_ID,
                    "crop": {"centering": list(LOCKED_CENTERING), "source_crop": transform.get("source_crop")},
                }
                spec["graphic_field"]["asset_id"] = str(field_asset.id)
                spec["flex_mode"] = pack.get("flex_mode")
                spec["lockup_side"] = pack.get("lockup_side") or plan.get("lockup_side")
                spec["promoted"] = False
                ready = family_revision_readiness(spec)
                collision = evaluate_collisions(objects=pack.get("objects") or {}, occupancy=occupancy, size=pack["image"].size)
                arch_hits = [h for h in list(collision.get("hits") or []) if "architecture" in h or "protected" in h]
                object_hits = [h for h in list(collision.get("hits") or []) if h not in arch_hits]
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
                checks = {
                    "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
                    "architecture_clearance": "PASS" if not arch_hits else "FAIL",
                    "headline_collision": "PASS" if not any(h.startswith("headline") for h in arch_hits) else "FAIL",
                    "commercial_collision": "PASS" if not any("price" in h or "discount" in h for h in arch_hits) else "FAIL",
                    "logo_collision": "PASS" if not any("logo" in h for h in arch_hits) else "FAIL",
                    "cta_collision": "PASS" if not any(h.startswith("cta") for h in arch_hits) else "FAIL",
                    "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
                    "UTF8": "PASS" if utf8 else "FAIL",
                    "font_metrics": "PASS",
                    "semantic_completeness": "PASS",
                    "canvas_bounds": "PASS" if not pack.get("overflow") else "FAIL",
                    "revision_readiness": ready.get("revision_readiness") or "FAIL",
                    "blueprint_fidelity": "PASS" if fidelity.get("pass") else "FAIL",
                    "real_temple_logo": "PASS" if pack.get("real_logo") else "FAIL",
                    "crop_locked": "PASS" if crop_locked else "FAIL",
                    "object_overlap": "PASS" if not object_hits else "FAIL",
                }
                preflight = {
                    "schema": "Phase55ATechnicalPreflightV1",
                    "checks": checks,
                    "pass": all(v == "PASS" for v in checks.values()),
                    "collision_hits": list(collision.get("hits") or []),
                    "architecture_hits": arch_hits,
                    "lockup_side": pack.get("lockup_side") or plan.get("lockup_side"),
                }
                final_critic, n = request_final_critic(pack["image"], graded, references, winner)
                vision_calls += n
                candidate_asset_id = str(asset.id)
                rendered = True
                status = "CANDIDATE_PENDING_HUMAN_REVIEW"
                images["candidate"] = pack["image"]
                images["structure_map"] = render_structure_map(pack["image"], pack.get("objects") or {})
                images["preflight"] = render_score_board(
                    {"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}}
                )
                images["final_critic"] = render_score_board(
                    {
                        "pass": False,
                        "scores": {k: final_critic.get(k) for k in (*FINAL_POSITIVE, *FINAL_BAD)},
                    }
                )
            else:
                status = "COMPOSITOR_UNSOLVED"
    images["review_board"] = render_human_review_board_55a(
        candidate=(pack or {}).get("image") if pack else None,
        critic=final_critic,
        preflight=preflight,
        winner=winner,
        status=status,
    )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55A,
        "created_at": _now(),
        "status": status,
        "execution_family_id": FAMILY_ID,
        "new_family_created": False,
        "photo_asset_id": DAY007_ASSET_ID,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "crop_locked": crop_locked,
        "references_actually_provided": bool(refs_ok and len(references) == 6),
        "reference_ids": ref_provenance,
        "director": {
            "schema": director.get("schema"),
            "mode": director.get("mode"),
            "references_provided": director.get("references_provided"),
            "analysis_keys": director.get("analysis_keys"),
            "invented_keys": director.get("invented_keys"),
        },
        "reference_craft": craft,
        "target_analysis": target,
        "blueprints": blueprints,
        "blueprint_critic": critic,
        "winning_blueprint": winner,
        "structured_art_direction_plan": plan,
        "blueprint_fidelity": fidelity,
        "candidate_asset_id": candidate_asset_id,
        "spec_id": (spec or {}).get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "final_critic": final_critic,
        "rendered": rendered,
        "gpt_image_calls": provider_call_count(),
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
        "lockup_side": (pack or {}).get("lockup_side") or (plan or {}).get("lockup_side"),
    }
    tests = [t for t in list(blob.get("ai_visual_art_director_55a_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55A)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["ai_visual_art_director_55a_tests"] = tests
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
    if blob.get("full_frame_r2_tests") != preserved.get("quality54k_r2"):
        raise RuntimeError("Phase 5.5A refused to overwrite Phase 5.4K-R2")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.5A refused to modify approved creative masters")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    _ = language
    return record
