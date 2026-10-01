"""Phase 5.5B-R2 — craft polish of the approved structured reconstruction.

No new draft. No GPT Image. Real Day_007 + real Temple logo. Does not promote.
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
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import DAY007_FILENAME
from investhome_api.services.creative_director.phase5_5b_r1_structured_reconstruction import _HISTORY_KEYS as _R1_HISTORY
from investhome_api.services.creative_director.phase5_5b_r1_structured_reconstruction import _preserve as _preserve_r1
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
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
from investhome_api.services.creative_director.visual_composition_draft import VERTICAL_HARMONY, render_draft_vs, visible_logo_clearance
from investhome_api.services.creative_director.visual_draft_reconstruction import (
    APPROVED_DRAFT_ASSET_ID,
    DAY007_ASSET_ID,
    FIDELITY_R2,
    FINAL_BAD_R1,
    FINAL_POSITIVE_R1,
    extract_approved_split_structure,
    logo_visual_match,
    reconstruct_r2_craft,
    reconstruction_plan_from_structure,
    render_r1_vs_r2,
    request_final_critic_r1,
    request_reconstruction_fidelity_r2,
    request_wrong_brand,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_55B_R2 = "phase5_5b_r2_craft_polish"
R1_CANDIDATE_ASSET_ID = "abe022be-33b5-4236-a610-012ca20af267"
R1_SPEC_ID = "fa6def09-3f7c-4151-a912-2a3cb66e6dab"
_HISTORY_KEYS = _R1_HISTORY + (("visual_draft_reconstruction_55b_r1_tests", "quality55b_r1"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r1(blob)
    preserved["quality55b_r1"] = list(blob.get("visual_draft_reconstruction_55b_r1_tests") or [])
    return preserved


def render_human_review_board_r2(
    *,
    r1: Image.Image | None,
    r2: Image.Image | None,
    critic: dict[str, Any],
    preflight: dict[str, Any] | None,
    status: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1760, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "HUMAN REVIEW BOARD  —  PHASE 5.5B-R2  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    if r1 is not None:
        tile = r1.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36, 60))
        draw.text((36, 750), "R1  structure", fill=(180, 176, 168), font=_font(13))
    if r2 is not None:
        tile = r2.copy()
        tile.thumbnail((520, 680), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (580, 60))
        draw.text((580, 750), "R2  craft polish", fill=(180, 176, 168), font=_font(13))
    x, y = 1140, 70
    draw.text((x, y), f"status  {status}", fill=(236, 230, 218), font=_font(15))
    y += 28
    passed = bool((preflight or {}).get("pass"))
    draw.text((x, y), f"preflight  {'PASS' if passed else 'FAIL'}", fill=(80, 200, 120) if passed else (220, 80, 80), font=_font(16))
    y += 36
    for key in (
        "professional_art_direction",
        "typography",
        "draft_fidelity",
        "logo_integration",
        "cta_integration",
        "readability",
        "TEXT_DUMP_FEEL",
        "CLUTTER",
    ):
        draw.text((x, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(14))
        y += 24
    draw.text((x, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(14))
    return canvas


def generate_craft_polish_55b_r2(
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
    r1 = Image.open(io.BytesIO(_read_bytes(db, UUID(R1_CANDIDATE_ASSET_ID)))).convert("RGB")
    if draft.size != (1088, 1360):
        draft = draft.resize((1088, 1360), Image.Resampling.LANCZOS)
    structure, n = extract_approved_split_structure(draft)
    vision_calls += n
    plan = reconstruction_plan_from_structure(structure)
    plan["craft"] = "r2"
    plan["base_r1_asset_id"] = R1_CANDIDATE_ASSET_ID
    plan["base_r1_spec_id"] = R1_SPEC_ID
    before_calls = provider_call_count()
    pack = reconstruct_r2_craft(
        draft=draft,
        source=source,
        logo_rgba=logo_rgba,
        fonts=fonts,
        family=family,
        structure=structure,
        plan=plan,
    )
    if provider_call_count() != before_calls:
        raise RuntimeError("Phase 5.5B-R2 must not call GPT Image")

    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["fielded"]),
        content_type="image/png",
        campaign_mode="project-v3-55b-r2-field",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5B-R2 navy/photo field",
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode="project-v3-55b-r2-candidate",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5B-R2 craft polish",
    )
    pack["graphic_field_asset_id"] = str(field_asset.id)
    spec = build_family_master_spec(
        key="VH-55B-R2",
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
    spec["base_r1_asset_id"] = R1_CANDIDATE_ASSET_ID
    spec["base_r1_spec_id"] = R1_SPEC_ID
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
        "r1_asset_id": R1_CANDIDATE_ASSET_ID,
        "crop": pack.get("crop_transform"),
    }
    spec["graphic_field"]["asset_id"] = str(field_asset.id)
    spec["promoted"] = False
    spec["cta_treatment"] = "editorial_gold_rule"
    spec["investhome_brand"] = False
    spec["craft"] = "r2"
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
    fidelity, n = request_reconstruction_fidelity_r2(draft, r1, pack["image"])
    vision_calls += n
    glyphs = dict(pack.get("glyph_preflight") or {})
    price_rel = dict(pack.get("price_currency") or {})
    collision = pack.get("collision") or {}
    arch_hits = [h for h in list(collision.get("hits") or []) if "architecture" in h or "protected" in h]
    provenance = pack.get("architecture_provenance") or {}
    objects = pack.get("objects") or {}
    checks = {
        "real_day007_asset": "PASS" if str((spec.get("project_photo") or {}).get("asset_id")) == DAY007_ASSET_ID else "FAIL",
        "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
        "project_logo_asset_id_match": "PASS" if str((spec.get("project_logo") or {}).get("asset_id")) == LOCKED_LOGO_ASSET_ID else "FAIL",
        "project_logo_visual_match": "PASS" if visual_match.get("pass") else "FAIL",
        "wrong_brand_asset_present": "PASS" if wrong.get("pass") else "FAIL",
        "visible_logo_clearance": "PASS" if clearance.get("pass") else "FAIL",
        "headline_glyph_clipping": glyphs.get("headline_glyph_clipping") or "FAIL",
        "commercial_glyph_clipping": glyphs.get("commercial_glyph_clipping") or "FAIL",
        "price_currency_relationship": "PASS" if price_rel.get("pass") else "FAIL",
        "minimum_readability": "PASS" if pack.get("minimum_readability") else "FAIL",
        "navy_boundary_clearance": glyphs.get("navy_boundary_clearance") or "FAIL",
        "headline_collision": "PASS" if not any(h.startswith("headline") for h in arch_hits) else "FAIL",
        "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
        "UTF8": "PASS" if pack.get("utf8_valid") else "FAIL",
        "semantic_completeness": "PASS" if all(objects.get(role) for role in ("headline", "discount", "price", "currency", "project_logo", "cta", "navy_field")) else "FAIL",
        "canvas_bounds": "PASS" if not pack.get("overflow") else "FAIL",
        "visual_reconstruction_fidelity": "PASS" if fidelity.get("pass") else "FAIL",
        "revision_readiness": ready.get("revision_readiness") or "FAIL",
    }
    preflight = {
        "schema": "Phase55BR2TechnicalPreflightV1",
        "checks": checks,
        "pass": all(v == "PASS" for v in checks.values()),
        "glyph_preflight": glyphs,
        "price_currency": price_rel,
        "visible_logo_clearance": clearance,
        "logo_visual_match": visual_match,
        "wrong_brand": wrong,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "headline_clipping": 0 if glyphs.get("headline_glyph_clipping") == "PASS" else 1,
    }
    final_critic, n = request_final_critic_r1(pack["image"], draft, pack["photo_panel"])
    vision_calls += n
    status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preflight["pass"] else "CANDIDATE_TECHNICAL_FAIL"
    spec["status"] = status
    images = {
        "r1": r1,
        "approved_draft": draft,
        "reconstruction": pack["image"],
        "r1_vs_r2": render_r1_vs_r2(r1, pack["image"]),
        "draft_vs": render_draft_vs(draft, pack["image"]),
        "glyph": render_score_board({"pass": glyphs.get("navy_boundary_clearance") == "PASS", "scores": {k: 10 if glyphs.get(k) == "PASS" else 3 for k in ("headline_glyph_clipping", "commercial_glyph_clipping", "navy_boundary_clearance")}}),
        "fidelity": render_score_board({"pass": fidelity.get("pass"), "scores": fidelity.get("scores") or {}}),
        "preflight": render_score_board({"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}}),
        "final_critic": render_score_board({"pass": False, "scores": {k: final_critic.get(k) for k in (*FINAL_POSITIVE_R1, *FINAL_BAD_R1)}}),
        "review_board": render_human_review_board_r2(r1=r1, r2=pack["image"], critic=final_critic, preflight=preflight, status=status),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55B_R2,
        "created_at": _now(),
        "status": status,
        "new_draft_generated": False,
        "new_concepts_generated": False,
        "base_r1_asset_id": R1_CANDIDATE_ASSET_ID,
        "base_r1_spec_id": R1_SPEC_ID,
        "photo_asset_id": DAY007_ASSET_ID,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "candidate_asset_id": str(asset.id),
        "spec_id": spec.get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "reconstruction_fidelity": fidelity,
        "final_critic": final_critic,
        "structure": structure,
        "reconstruction_plan": plan,
        "new_visual_draft_image_calls": 0,
        "production_image_generation_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "project_id": TEMPLE_PROJECT_ID,
        "contrast": _jsonable(pack.get("contrast")),
        "fidelity_keys": list(FIDELITY_R2),
        "headline_display_px": pack.get("headline_display_px"),
        "headline_tracking": pack.get("headline_tracking"),
        "split_x": pack.get("split_x"),
    }
    tests = [
        t
        for t in list(blob.get("visual_draft_reconstruction_55b_r2_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55B_R2)
    ]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["visual_draft_reconstruction_55b_r2_tests"] = tests
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
    if blob.get("visual_draft_reconstruction_55b_r1_tests") != preserved.get("quality55b_r1"):
        raise RuntimeError("Phase 5.5B-R2 refused to overwrite Phase 5.5B-R1")
    _ = PRODUCTION_COVER_V2
    _ = language
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
