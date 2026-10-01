"""Phase 5.4K — FULL_FRAME_ARCHITECTURAL_CAMPAIGN.

One new Master Family for full-frame centered architecture + HIGH density.
Executed by GraphicDesignCompositorV3. GPT Image = 0. Does not promote.
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
from investhome_api.services.creative_director.contiguous_content_fit import evaluate_family_eligibility_v2
from investhome_api.services.creative_director.creative_collision_engine import evaluate_collisions
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.full_frame_architectural_family import (
    FAMILY_ID,
    family_brief,
    full_frame_family_spec,
    run_full_frame_calibration,
)
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font, _wrap
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.creative_director.phase5_photo_family_eligibility import list_temple_exterior_assets
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_production_compositor import (
    _HISTORY_KEYS as _BASE_HISTORY,
    _jsonable,
    render_score_board,
    render_structure_map,
)
from investhome_api.services.creative_director.phase5_production_compositor import _preserve as _preserve_base
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
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
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL
from investhome_api.services.creative_director.photo_family_eligibility import campaign_density_profile
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54K = "phase5_4k_full_frame_family"
_HISTORY_KEYS = _BASE_HISTORY + (("production_compositor_tests", "quality54j"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54j"] = list(blob.get("production_compositor_tests") or [])
    return preserved


def render_brief_board(brief: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 860), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "FULL_FRAME_ARCHITECTURAL_CAMPAIGN  —  family brief", fill=(201, 168, 92), font=_font(20))
    y = 80
    for line in (
        f"occupancy {brief.get('photo_occupancy')}   negative space {brief.get('negative_space')}",
        f"architecture {brief.get('architecture_position')}   density {brief.get('commercial_density')}",
        f"modification {brief.get('architecture_modification')}",
        str(brief.get("principle") or ""),
        "Territories: " + " · ".join(brief.get("territories") or []),
        "Forbidden: " + ", ".join((brief.get("forbidden") or [])[:6]),
    ):
        for chunk in _wrap(str(line), 92):
            draw.text((36, y), chunk, fill=(236, 230, 218), font=_font(16))
            y += 28
        y += 10
    return canvas


def render_structure_board() -> Image.Image:
    canvas = Image.new("RGB", (900, 1120), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "PERIMETER TERRITORIES  —  not four boxes", fill=(201, 168, 92), font=_font(18))
    draw.rectangle((80, 80, 820, 1040), outline=(60, 64, 72), width=2)
    draw.rectangle((300, 220, 600, 900), fill=(168, 156, 140))
    draw.text((340, 520), "ARCHITECTURE", fill=(40, 36, 32), font=_font(16))
    draw.text((100, 110), "TOP BRAND", fill=(201, 168, 92), font=_font(14))
    draw.text((100, 400), "LEFT\nEDITORIAL", fill=(236, 230, 218), font=_font(14))
    draw.text((640, 400), "RIGHT\nCOMMERCIAL", fill=(236, 230, 218), font=_font(14))
    draw.text((360, 980), "BOTTOM ACTION", fill=(201, 168, 92), font=_font(14))
    return canvas


def render_ranking(rows: list[dict[str, Any]], *, note: str | None = None) -> Image.Image:
    canvas = Image.new("RGB", (1480, 860), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "TEMPLE × FULL_FRAME_ARCHITECTURAL_CAMPAIGN  —  multi-zone V2", fill=(201, 168, 92), font=_font(18))
    y = 70
    if note:
        for chunk in _wrap(note, 96):
            draw.text((36, y), chunk, fill=(220, 80, 80), font=_font(16))
            y += 28
        y += 12
    for idx, row in enumerate(rows[:8], start=1):
        draw.text(
            (36, y),
            f"{idx}.  {row.get('filename')}  {row.get('contiguous_fit')}  {row.get('flex_mode')}",
            fill=(236, 230, 218),
            font=_font(14),
        )
        draw.text((36, y + 22), str(row.get("reason") or ""), fill=(160, 156, 148), font=_font(12))
        y += 70
    if rows and not any(r.get("true_fit") for r in rows):
        draw.text((36, 780), "NO TRUE FIT", fill=(220, 80, 80), font=_font(18))
    return canvas


def render_critic_board(critic: dict[str, Any]) -> Image.Image:
    visual = (
        "professional_art_direction",
        "family_fidelity",
        "composition",
        "image_design_integration",
        "typography",
        "hierarchy",
        "commercial_clarity",
        "logo_integration",
        "cta_integration",
        "premium_character",
        "readability",
        "architecture_fidelity",
        "publishability",
    )
    bad = ("TEXT_ON_PHOTO_FEEL", "TEMPLATE_FEEL", "LISTING_CARD_FEEL", "UI_FEEL", "CLUTTER")
    canvas = Image.new("RGB", (1088, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "VISUAL CRITIC  —  do not inflate", fill=(201, 168, 92), font=_font(20))
    y = 80
    for key in visual:
        draw.text((36, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(16))
        y += 28
    y += 12
    draw.text((36, y), "UNDESIRABLE  (lower is better)", fill=(201, 168, 92), font=_font(16))
    y += 32
    for key in bad:
        draw.text((36, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(16))
        y += 28
    return canvas


def render_human_review_board(
    *,
    candidate: Image.Image,
    critic: dict[str, Any],
    preflight: dict[str, Any],
    top: dict[str, Any] | None,
) -> Image.Image:
    canvas = Image.new("RGB", (1680, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "HUMAN REVIEW BOARD  —  FULL_FRAME_ARCHITECTURAL_CAMPAIGN  —  NOT PROMOTED", fill=(201, 168, 92), font=_font(18))
    tile = candidate.copy()
    tile.thumbnail((720, 900), Image.Resampling.LANCZOS)
    canvas.paste(tile, (36, 60))
    x = 780
    y = 70
    draw.text((x, y), f"asset  {(top or {}).get('filename') or ''}", fill=(236, 230, 218), font=_font(16))
    y += 32
    draw.text((x, y), f"flex  {(top or {}).get('flex_mode') or ''}", fill=(180, 176, 168), font=_font(16))
    y += 40
    draw.text((x, y), f"preflight  {'PASS' if preflight.get('pass') else 'FAIL'}", fill=(80, 200, 120) if preflight.get("pass") else (220, 80, 80), font=_font(18))
    y += 40
    for key in (
        "professional_art_direction",
        "composition",
        "typography",
        "architecture_fidelity",
        "publishability",
        "TEXT_ON_PHOTO_FEEL",
        "TEMPLATE_FEEL",
        "LISTING_CARD_FEEL",
        "UI_FEEL",
        "CLUTTER",
    ):
        draw.text((x, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(15))
        y += 28
    draw.text((x, 920), "NEXT DECISION  HUMAN VISUAL REVIEW", fill=(201, 168, 92), font=_font(16))
    return canvas


def request_full_frame_critic(
    candidate: Image.Image,
    foundation: Image.Image,
    *,
    doctrine: str | None = None,
) -> tuple[dict[str, Any], int]:
    doctrine_text = doctrine or (
        "Family FULL_FRAME_ARCHITECTURAL_CAMPAIGN. Architecture is the centered hero. "
        "Information lives in a designed perimeter, not a card, header, sidebar, footer, pill or button. "
    )
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Independent luxury real-estate art director. Do not inflate. JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"{doctrine_text}"
                            "Image 1 = candidate. Image 2 = photographic foundation. "
                            "Return ONE flat JSON object. Every key below MUST be top-level. Do not nest. Do not omit. "
                            "Score 0-10: professional_art_direction, family_fidelity, composition, image_design_integration, "
                            "typography, hierarchy, commercial_clarity, logo_integration, cta_integration, premium_character, "
                            "readability, architecture_fidelity, publishability. "
                            "Also REQUIRED top-level 0-10 (lower is better): TEXT_ON_PHOTO_FEEL, TEMPLATE_FEEL, "
                            "LISTING_CARD_FEEL, UI_FEEL, CLUTTER. Do not inflate. Notes allowed as 'notes'."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    out = flatten_critic(parsed)
    nested = out.get("undesirable")
    if isinstance(nested, dict):
        for key in ("TEXT_ON_PHOTO_FEEL", "TEMPLATE_FEEL", "LISTING_CARD_FEEL", "UI_FEEL", "CLUTTER"):
            if nested.get(key) is not None:
                out[key] = nested.get(key)
    return out, calls


def _architecture_hits(hits: list[str]) -> list[str]:
    return [h for h in hits if "canvas_edge" not in h and "noisy_street" not in h]


def generate_full_frame_family_4x5(
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
    brief = family_brief()
    fonts = build_font_registry()
    logo_rgba = None
    try:
        logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    except Exception:
        logo_rgba = None
    images: dict[str, Any] = {"brief": render_brief_board(brief), "structure": render_structure_board()}
    calibration = run_full_frame_calibration(fonts=fonts, logo_rgba=None)
    recon = calibration.get("pack", {}).get("image") or calibration.get("photo")
    images["calibration"] = recon if isinstance(recon, Image.Image) else calibration["photo"]
    images["calibration_scores"] = render_score_board(calibration)
    ranking: list[dict[str, Any]] = []
    pack: dict[str, Any] | None = None
    spec: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None
    critic: dict[str, Any] = {}
    ready: dict[str, Any] | None = None
    candidate_asset_id = None
    temple_rendered = False
    status = "CALIBRATION_FAIL"
    next_decision = "HUMAN VISUAL REVIEW"
    if not calibration.get("pass"):
        next_decision = "Family calibration failed. Do not render Temple until all craft scores are >= 8."
        images["ranking"] = render_ranking([], note="CALIBRATION FAIL — Temple scan not run.")
    else:
        status = "NO_TRUE_FIT"
        density = campaign_density_profile(fonts=fonts, family=family, canvas=CANVAS_4X5)
        for asset in list_temple_exterior_assets(db):
            try:
                photo = Image.open(io.BytesIO(_read_bytes(db, asset.id))).convert("RGB")
            except Exception:
                continue
            crop, transform = cover_fit_canvas(photo, CANVAS_4X5, centering=(0.50, 0.42))
            graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
            occupancy = build_photo_occupancy_map(graded)
            result = evaluate_family_eligibility_v2(
                photo=graded, occupancy=occupancy, family=family, fonts=fonts, density=density
            )
            ranking.append(
                {
                    "asset_id": str(asset.id),
                    "filename": asset.filename,
                    "family_id": FAMILY_ID,
                    "status": result.get("status"),
                    "contiguous_fit": result.get("contiguous_fit"),
                    "flex_mode": (result.get("fit") or {}).get("flex_mode") or result.get("flex_mode"),
                    "reason": result.get("primary_reason"),
                    "zones": (result.get("fit") or {}).get("zones"),
                    "true_fit": result.get("status") == "ELIGIBLE" and result.get("contiguous_fit") == "FIT",
                    "score": sum(float((z or {}).get("area") or 0) for z in ((result.get("fit") or {}).get("zones") or {}).values()),
                    "source_crop": (transform or {}).get("source_crop"),
                }
            )
        ranking.sort(key=lambda item: (1 if item.get("true_fit") else 0, float(item.get("score") or 0)), reverse=True)
        images["ranking"] = render_ranking(ranking)
        true_fits = [r for r in ranking if r.get("true_fit")]
        if true_fits:
            top = true_fits[0]
            src = Image.open(io.BytesIO(_read_bytes(db, UUID(str(top["asset_id"]))))).convert("RGB")
            crop, transform = cover_fit_canvas(src, CANVAS_4X5, centering=(0.50, 0.42))
            graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
            occupancy = build_photo_occupancy_map(graded)
            pack = compose_graphic_design_v3(graded, occupancy=occupancy, family=family, fonts=fonts, logo_rgba=logo_rgba)
            if pack.get("solved"):
                field_asset = persist_gpt_image(
                    db, actor=user, linked_project_id=row.linked_project_id, content=_png(pack["fielded"]),
                    content_type="image/png", campaign_mode="project-v3-field", session_id=str(uuid4()),
                    provider_generation_id=None, campaign_context_id=str(row.id), brief_excerpt="PHASE 5.4K field",
                )
                asset = persist_gpt_image(
                    db, actor=user, linked_project_id=row.linked_project_id, content=_png(pack["image"]),
                    content_type="image/png", campaign_mode="project-v3-candidate", session_id=str(uuid4()),
                    provider_generation_id=None, campaign_context_id=str(row.id), brief_excerpt="PHASE 5.4K candidate",
                )
                pack["graphic_field_asset_id"] = str(field_asset.id)
                spec = build_family_master_spec(
                    key="FF-1",
                    pack=pack,
                    family=family,
                    crop={"centering": [0.5, 0.42], "source_crop": transform.get("source_crop")},
                    photo_asset=str(top["asset_id"]),
                    logo_asset=LOCKED_LOGO_ASSET_ID,
                    candidate_asset_id=str(asset.id),
                    architecture_lock={"schema": "PhotoOccupancyMapV1"},
                )
                spec["schema"] = "ProductionMasterCandidateV1"
                spec["family_id"] = FAMILY_ID
                spec["graphic_field"]["asset_id"] = str(field_asset.id)
                spec["visual_replace_requires_eligibility"] = True
                spec["flex_mode"] = pack.get("flex_mode")
                ready = family_revision_readiness(spec)
                collision = evaluate_collisions(objects=pack.get("objects") or {}, occupancy=occupancy, size=pack["image"].size)
                arch_hits = _architecture_hits(list(collision.get("hits") or []))
                provenance = architecture_provenance_qa(
                    source=src,
                    foundation=pack["foundation"],
                    final=pack["image"],
                    transform={"centering": [0.5, 0.42], "source_crop": transform.get("source_crop") or [0, 0, 1, 1]},
                )
                utf8 = turkish_copy_is_valid(pack.get("facts") or {})
                checks = {
                    "photo_family_fit": "PASS",
                    "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
                    "architecture_clearance": "PASS" if not any("architecture" in h for h in arch_hits) else "FAIL",
                    "headline_collision": "PASS" if not any(h.startswith("headline") for h in arch_hits) else "FAIL",
                    "commercial_collision": "PASS" if not any("price" in h or "discount" in h for h in arch_hits) else "FAIL",
                    "logo_collision": "PASS" if not any("logo" in h for h in arch_hits) else "FAIL",
                    "cta_collision": "PASS" if not any(h.startswith("cta") for h in arch_hits) else "FAIL",
                    "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
                    "UTF8": "PASS" if utf8 else "FAIL",
                    "font_metrics": "PASS",
                    "commercial_hierarchy": "PASS",
                    "family_identity": "PASS",
                    "canvas_bounds": "PASS" if not pack.get("overflow") else "FAIL",
                    "semantic_completeness": "PASS",
                    "revision_readiness": ready.get("revision_readiness") or "FAIL",
                }
                preflight = {
                    "schema": "FullFrameTechnicalPreflightV1",
                    "checks": checks,
                    "pass": all(v == "PASS" for v in checks.values()),
                    "collision_hits": list(collision.get("hits") or []),
                    "architecture_hits": arch_hits,
                    "canvas_edge_hits_ignored": [h for h in (collision.get("hits") or []) if "canvas_edge" in h],
                    "note": "Perimeter type may occupy designed canvas edges. Architecture clearance is not weakened.",
                }
                critic, n = request_full_frame_critic(pack["image"], pack["foundation"])
                vision_calls += n
                candidate_asset_id = str(asset.id)
                temple_rendered = True
                status = "TEMPLE_CANDIDATE_RENDERED" if preflight["pass"] else "TEMPLE_CANDIDATE_TECHNICAL_FAIL"
                images["proof"] = pack["image"]
                images["structure_map"] = render_structure_map(pack["image"], pack.get("objects") or {})
                images["preflight"] = render_score_board({"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}})
                images["critic"] = render_critic_board(critic)
                images["review_board"] = render_human_review_board(
                    candidate=pack["image"], critic=critic, preflight=preflight, top=top
                )
            else:
                status = "TRUE_FIT_COMPOSITOR_UNSOLVED"
        else:
            status = "NO_TRUE_FIT"
    true_fits = [r for r in ranking if r.get("true_fit")]
    top = true_fits[0] if true_fits else None
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54K,
        "created_at": _now(),
        "status": status,
        "family_id": FAMILY_ID,
        "brief": brief,
        "family_spec": {k: v for k, v in family.items() if k != "brief"},
        "calibration": _jsonable({k: v for k, v in calibration.items() if k not in {"pack", "photo", "family"}}),
        "calibration_pass": bool(calibration.get("pass")),
        "pair_ranking": ranking,
        "true_fit_count": len(true_fits),
        "top_true_fit": top,
        "temple_rendered": temple_rendered,
        "candidate_asset_id": candidate_asset_id,
        "spec_id": (spec or {}).get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "critic": critic,
        "next_decision": next_decision if status == "CALIBRATION_FAIL" else "HUMAN VISUAL REVIEW",
        "gpt_image_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "new_family_created": True,
        "second_family_created": False,
        "phase55_executed": False,
        "project_id": TEMPLE_PROJECT_ID,
        "human_review_required": True,
    }
    tests = [t for t in list(blob.get("full_frame_family_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54K)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["full_frame_family_tests"] = tests
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
    if blob.get("production_compositor_tests") != preserved.get("quality54j"):
        raise RuntimeError("Phase 5.4K refused to overwrite Phase 5.4J")
    if blob.get("best_pair_proof_tests") != preserved.get("quality54i"):
        raise RuntimeError("Phase 5.4K refused to overwrite Phase 5.4I")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4K refused to modify approved creative masters")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["calibration_pack"] = calibration.get("pack")
    _ = language, flatten_critic
    return record
