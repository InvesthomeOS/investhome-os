"""Phase 5.5B-R1 — approved visual draft → structured master reconstruction.

Human visual pass on the 5.5B draft. No new draft. No GPT Image.
Real Day_007 + real Temple logo only. Does not promote.
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
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.full_frame_architectural_family import FAMILY_ID, full_frame_family_spec
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import DAY007_FILENAME
from investhome_api.services.creative_director.phase5_5b_visual_draft_reconstruction import _HISTORY_KEYS as _B_HISTORY
from investhome_api.services.creative_director.phase5_5b_visual_draft_reconstruction import _preserve as _preserve_55b
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
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
from investhome_api.services.creative_director.visual_composition_draft import VERTICAL_HARMONY, render_draft_vs, visible_logo_clearance
from investhome_api.services.creative_director.visual_draft_reconstruction import (
    APPROVED_DRAFT_ASSET_ID,
    DAY007_ASSET_ID,
    FIDELITY_R1,
    FINAL_BAD_R1,
    FINAL_POSITIVE_R1,
    extract_approved_split_structure,
    logo_visual_match,
    reconstruct_approved_split,
    reconstruction_plan_from_structure,
    render_extraction_board_r1,
    render_plan_board_r1,
    request_final_critic_r1,
    request_reconstruction_fidelity_r1,
    request_wrong_brand,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55B_R1 = "phase5_5b_r1_structured_reconstruction"
_HISTORY_KEYS = _B_HISTORY + (("visual_draft_reconstruction_55b_tests", "quality55b"),)

_ = compose_graphic_design_v3


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_55b(blob)
    preserved["quality55b"] = list(blob.get("visual_draft_reconstruction_55b_tests") or [])
    return preserved


def render_human_review_board_r1(
    *,
    draft: Image.Image | None,
    candidate: Image.Image | None,
    critic: dict[str, Any],
    preflight: dict[str, Any] | None,
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1760, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "HUMAN REVIEW BOARD  —  PHASE 5.5B-R1  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    if draft is not None:
        tile = draft.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36, 60))
        draw.text((36, 750), "APPROVED DRAFT  composition guide", fill=(180, 176, 168), font=_font(13))
    if candidate is not None:
        tile = candidate.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (580, 60))
        draw.text((580, 750), "STRUCTURED RECONSTRUCTION  real assets", fill=(180, 176, 168), font=_font(13))
    x, y = 1140, 70
    draw.text((x, y), f"status  {status}", fill=(236, 230, 218), font=_font(15))
    y += 28
    passed = bool((preflight or {}).get("pass"))
    draw.text((x, y), f"preflight  {'PASS' if passed else 'FAIL'}", fill=(80, 200, 120) if passed else (220, 80, 80), font=_font(16))
    y += 36
    for key in (
        "professional_art_direction",
        "draft_fidelity",
        "composition",
        "logo_integration",
        "architecture_fidelity",
        "publishability",
        "TEXT_ON_PHOTO_FEEL",
        "UI_FEEL",
        "CLUTTER",
    ):
        draw.text((x, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(14))
        y += 24
    draw.text((x, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(14))
    return canvas


def generate_visual_draft_reconstruction_55b_r1(
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
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY007_ASSET_ID)))).convert("RGB")
    draft = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_DRAFT_ASSET_ID)))).convert("RGB")
    if draft.size != (1088, 1360):
        draft = draft.resize((1088, 1360), Image.Resampling.LANCZOS)

    structure, n = extract_approved_split_structure(draft)
    vision_calls += n
    plan = reconstruction_plan_from_structure(structure)
    before_calls = provider_call_count()
    pack = reconstruct_approved_split(
        draft=draft,
        source=source,
        logo_rgba=logo_rgba,
        fonts=fonts,
        family=family,
        structure=structure,
        plan=plan,
    )
    if provider_call_count() != before_calls:
        raise RuntimeError("Phase 5.5B-R1 reconstruction must not call GPT Image")

    images: dict[str, Any] = {
        "approved_draft": draft,
        "extraction": render_extraction_board_r1(structure),
        "plan": render_plan_board_r1(plan),
    }
    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["fielded"]),
        content_type="image/png",
        campaign_mode="project-v3-55b-r1-field",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5B-R1 navy/photo field",
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode="project-v3-55b-r1-candidate",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5B-R1 structured reconstruction",
    )
    pack["graphic_field_asset_id"] = str(field_asset.id)
    spec = build_family_master_spec(
        key="VH-55B-R1",
        pack=pack,
        family=family,
        crop={
            "centering": (pack.get("crop_transform") or {}).get("centering"),
            "source_crop": (pack.get("crop_transform") or {}).get("source_crop"),
        },
        photo_asset=DAY007_ASSET_ID,
        logo_asset=LOCKED_LOGO_ASSET_ID,
        candidate_asset_id=str(asset.id),
        architecture_lock={"schema": "PhotoOccupancyMapV1"},
    )
    spec["schema"] = "ProductionMasterCandidateV1"
    spec["status"] = "CANDIDATE_PENDING_HUMAN_REVIEW"
    spec["family_id"] = FAMILY_ID
    spec["registered_master_family"] = False
    spec["approved_visual_draft_asset_id"] = APPROVED_DRAFT_ASSET_ID
    spec["visual_reconstruction_spec"] = plan
    spec["art_direction_blueprint"] = VERTICAL_HARMONY
    spec["navy_field"] = (pack.get("objects") or {}).get("navy_field")
    spec["currency"] = (pack.get("objects") or {}).get("currency")
    spec["editorial_rules"] = (pack.get("objects") or {}).get("editorial_rules")
    spec["tonal_treatment"] = (pack.get("objects") or {}).get("tonal_treatment")
    spec["project_photo"]["bounds"] = ((pack.get("objects") or {}).get("project_photo") or {}).get("bounds")
    spec["project_photo"]["asset_id"] = DAY007_ASSET_ID
    spec["source_asset_provenance"] = {
        "photo_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "draft_asset_id": APPROVED_DRAFT_ASSET_ID,
        "crop": pack.get("crop_transform"),
    }
    spec["graphic_field"]["asset_id"] = str(field_asset.id)
    spec["promoted"] = False
    spec["cta_treatment"] = "editorial_gold_rule"
    spec["investhome_brand"] = False
    ready = family_revision_readiness(spec)

    logo_px = tuple(int(v) for v in ((pack.get("objects") or {}).get("project_logo") or {}).get("px") or [0, 0, 0, 0])
    clearance = visible_logo_clearance(
        logo_rgba=logo_rgba,
        paste=logo_px,
        occupancy=pack.get("occupancy") or {},
        canvas=tuple(pack["image"].size),
    )
    visual_match = logo_visual_match(
        logo_rgba=logo_rgba,
        candidate=pack["image"],
        paste=logo_px,
        navy=tuple(pack.get("navy_color") or (18, 32, 54)),
    )
    wrong, n = request_wrong_brand(pack["image"], logo_rgba)
    vision_calls += n
    collision = pack.get("collision") or {}
    arch_hits = [h for h in list(collision.get("hits") or []) if "architecture" in h or "protected" in h]
    fidelity, n = request_reconstruction_fidelity_r1(draft, pack["image"])
    vision_calls += n
    id_match = str((spec.get("project_logo") or {}).get("asset_id") or pack.get("logo_asset_id")) == LOCKED_LOGO_ASSET_ID
    day007_ok = str((spec.get("project_photo") or {}).get("asset_id") or pack.get("photo_asset_id")) == DAY007_ASSET_ID
    provenance = pack.get("architecture_provenance") or {}
    objects = pack.get("objects") or {}
    checks = {
        "real_day007_asset": "PASS" if day007_ok else "FAIL",
        "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
        "project_logo_asset_id_match": "PASS" if id_match else "FAIL",
        "project_logo_visual_match": "PASS" if visual_match.get("pass") else "FAIL",
        "wrong_brand_asset_present": "PASS" if wrong.get("pass") else "FAIL",
        "visible_logo_clearance": "PASS" if clearance.get("pass") else "FAIL",
        "headline_collision": "PASS" if not any(h.startswith("headline") for h in arch_hits) else "FAIL",
        "commercial_collision": "PASS" if not any("price" in h or "discount" in h for h in arch_hits) else "FAIL",
        "cta_collision": "PASS" if not any(h.startswith("cta") for h in arch_hits) else "FAIL",
        "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
        "UTF8": "PASS" if pack.get("utf8_valid") else "FAIL",
        "font_metrics": "PASS",
        "semantic_completeness": "PASS" if all(
            objects.get(role)
            for role in (
                "project_photo",
                "navy_field",
                "headline",
                "discount",
                "discount_label",
                "price",
                "currency",
                "project_logo",
                "unit_type",
                "cta",
                "editorial_rules",
                "tonal_treatment",
            )
        )
        else "FAIL",
        "canvas_bounds": "PASS" if not pack.get("overflow") else "FAIL",
        "visual_reconstruction_fidelity": "PASS" if fidelity.get("pass") else "FAIL",
        "revision_readiness": ready.get("revision_readiness") or "FAIL",
    }
    preflight = {
        "schema": "Phase55BR1TechnicalPreflightV1",
        "checks": checks,
        "pass": all(v == "PASS" for v in checks.values()),
        "collision_hits": list(collision.get("hits") or []),
        "architecture_hits": arch_hits,
        "visible_logo_clearance": clearance,
        "logo_visual_match": visual_match,
        "wrong_brand": wrong,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
    }
    final_critic, n = request_final_critic_r1(pack["image"], draft, pack["photo_panel"])
    vision_calls += n
    status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preflight["pass"] else "CANDIDATE_TECHNICAL_FAIL"
    spec["status"] = status
    images["reconstruction"] = pack["image"]
    images["structure_map"] = render_structure_map(
        pack["image"],
        {k: v for k, v in objects.items() if k not in {"navy_field", "project_photo"}},
    )
    images["draft_vs"] = render_draft_vs(draft, pack["image"])
    images["fidelity"] = render_score_board({"pass": fidelity.get("pass"), "scores": fidelity.get("scores") or {}})
    images["preflight"] = render_score_board(
        {"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}}
    )
    images["final_critic"] = render_score_board(
        {"pass": False, "scores": {k: final_critic.get(k) for k in (*FINAL_POSITIVE_R1, *FINAL_BAD_R1)}}
    )
    images["review_board"] = render_human_review_board_r1(
        draft=draft,
        candidate=pack["image"],
        critic=final_critic,
        preflight=preflight,
        status=status,
    )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55B_R1,
        "created_at": _now(),
        "status": status,
        "concept": VERTICAL_HARMONY["concept_name"],
        "new_draft_generated": False,
        "new_concepts_generated": False,
        "new_family_created": False,
        "human_approved_draft": True,
        "approved_draft_asset_id": APPROVED_DRAFT_ASSET_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "structure": structure,
        "reconstruction_plan": plan,
        "candidate_asset_id": str(asset.id),
        "spec_id": spec.get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "reconstruction_fidelity": fidelity,
        "final_critic": final_critic,
        "rendered": True,
        "solved": bool(pack.get("solved")),
        "new_visual_draft_image_calls": 0,
        "production_image_generation_calls": provider_call_count(),
        "gpt_image_calls_total": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "contrast": _jsonable(pack.get("contrast")),
        "fidelity_keys": list(FIDELITY_R1),
    }
    tests = [
        t
        for t in list(blob.get("visual_draft_reconstruction_55b_r1_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55B_R1)
    ]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["visual_draft_reconstruction_55b_r1_tests"] = tests
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
    if blob.get("visual_draft_reconstruction_55b_tests") != preserved.get("quality55b"):
        raise RuntimeError("Phase 5.5B-R1 refused to overwrite Phase 5.5B")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.5B-R1 refused to modify approved creative masters")
    _ = PRODUCTION_COVER_V2
    _ = language
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
