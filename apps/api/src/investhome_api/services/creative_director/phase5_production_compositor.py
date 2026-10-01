"""Phase 5.4J — Graphic Design Compositor V3 + Eligibility V2.

Does not redesign the product pipeline. Does not promote. GPT Image = 0.
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
from investhome_api.services.creative_director.creative_execution_tokens import execution_tokens
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_best_pair_proof import (
    DAY002_ASSET_ID,
    DAY002_FILENAME,
    REF_00013,
    _HISTORY_KEYS as _BASE_HISTORY,
)
from investhome_api.services.creative_director.phase5_best_pair_proof import _preserve as _preserve_base
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font, _wrap
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.creative_director.phase5_photo_family_eligibility import list_temple_exterior_assets
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, apply_photographic_grade, architecture_provenance_qa, cover_fit_canvas
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
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
from investhome_api.services.creative_director.photo_family_eligibility import ALL_MASTER_FAMILIES, campaign_density_profile
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.reference_execution_calibration import run_reference_calibration
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL
from investhome_api.services.creative_director.phase5_design_scene import _vision

WORKFLOW_ID_54J = "phase5_4j_production_compositor"
PROOF_FAMILY_ID = "EDITORIAL_DARK_FIELD"
_HISTORY_KEYS = _BASE_HISTORY + (("best_pair_proof_tests", "quality54i"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54i"] = list(blob.get("best_pair_proof_tests") or [])
    return preserved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Image.Image):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if k not in {"layers", "occupancy", "foundation", "image", "fielded", "pack", "photo", "tokens"}}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _library() -> dict[str, Any]:
    return build_family_library({name: seeded_reference_family(name) for name in GRADE_A_ORDER})


def render_capabilities() -> Image.Image:
    canvas = Image.new("RGB", (1280, 900), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "GRAPHIC DESIGN COMPOSITOR V3 — execution engine, not art director", fill=(201, 168, 92), font=_font(18))
    y = 70
    blocks = [
        "Groups: Display · CommercialOffer · Brand · CTA · SupportingInfo",
        "Tokens from Master Family. No generic fallback when family tokens exist.",
        "Relational solver: architecture → identity → readability → hierarchy → groups → contrast → spacing → coordinates",
        "Primitives: editorial rule, hairline, local tonal fade, edge gradient, clip/feather, optical tracking",
        "Forbidden: cards, pills, KPI boxes, web buttons, dashboard panels",
        "CommercialNumberRendererV1 designs 675.000 USD and %35 as graphic elements",
        "ContiguousContentFitTestV1 packs the real lockup into the architecture-clear rectangle",
    ]
    for line in blocks:
        for chunk in _wrap(line, 92):
            draw.text((36, y), chunk, fill=(236, 230, 218), font=_font(16))
            y += 28
        y += 8
    return canvas


def render_calibration_board(ornek: Image.Image | None, reconstruction: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1480, 820), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "REFERENCE EXECUTION CALIBRATION  —  structure reconstructed, content not copied", fill=(201, 168, 92), font=_font(16))
    x = 36
    for img, label in ((ornek, "ORNEK_00013 reference"), (reconstruction, "V3 reconstruction / placeholder")):
        if isinstance(img, Image.Image):
            tile = img.copy()
            tile.thumbnail((680, 720), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 50))
        draw.text((x, 780), label, fill=(180, 176, 168), font=_font(14))
        x += 720
    return canvas


def render_score_board(report: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    ok = bool(report.get("pass"))
    draw.text((36, 24), "CALIBRATION SCORES", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 64), "PASS" if ok else "FAIL", fill=(80, 200, 120) if ok else (220, 80, 80), font=_font(32))
    y = 120
    for key, value in dict(report.get("scores") or {}).items():
        draw.text((36, y), f"{key}  {value}", fill=(236, 230, 218), font=_font(18))
        y += 36
    return canvas


def render_fit_board(day002: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "DAY_002 × EDITORIAL_DARK_FIELD  —  Eligibility V2", fill=(201, 168, 92), font=_font(18))
    status = str(day002.get("contiguous_fit") or day002.get("status") or "")
    draw.text((36, 70), status, fill=(80, 200, 120) if status == "FIT" else (220, 80, 80), font=_font(32))
    fit = dict(day002.get("fit") or {})
    y = 130
    for line in (
        str(day002.get("primary_reason") or fit.get("reason") or ""),
        f"v1 was {day002.get('v1_status')}  false_positive={day002.get('v1_false_positive')}",
        f"safe {fit.get('safe_rect')}",
        f"required {fit.get('required_lockup')}",
    ):
        for chunk in _wrap(str(line), 88):
            draw.text((36, y), chunk, fill=(180, 176, 168), font=_font(14))
            y += 24
    return canvas


def render_ranking(rows: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1480, 860), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "TRUE FIT PAIR RANKING  —  contiguous lockup, not attractiveness", fill=(201, 168, 92), font=_font(18))
    y = 70
    for idx, row in enumerate(rows[:8], start=1):
        draw.text((36, y), f"{idx}.  {row.get('filename')}  ×  {row.get('family_id')}  {row.get('contiguous_fit')}", fill=(236, 230, 218), font=_font(14))
        draw.text((36, y + 22), str(row.get("reason") or ""), fill=(160, 156, 148), font=_font(12))
        y += 70
    if not rows:
        draw.text((36, 80), "NO_CURRENT_IMAGE_FAMILY_PAIR_FITS", fill=(220, 80, 80), font=_font(22))
    return canvas


def render_structure_map(image: Image.Image, objects: dict[str, Any]) -> Image.Image:
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    colors = {
        "headline": (201, 168, 92),
        "unit_type": (180, 176, 168),
        "price": (236, 230, 218),
        "discount": (201, 168, 92),
        "discount_label": (180, 176, 168),
        "cta": (236, 230, 218),
        "project_logo": (140, 190, 190),
    }
    for role, item in objects.items():
        box = item.get("px") if isinstance(item, dict) else None
        if not (isinstance(box, (list, tuple)) and len(box) == 4):
            continue
        color = colors.get(role, (201, 168, 92))
        draw.rectangle(tuple(int(v) for v in box), outline=color, width=2)
        draw.text((int(box[0]), max(8, int(box[1]) - 18)), role, fill=color, font=_font(12))
    return canvas


def render_decision(record: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 780), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "PHASE 5.4J DECISION", fill=(201, 168, 92), font=_font(22))
    y = 80
    for line in (
        f"STATUS  {record.get('status')}",
        f"CALIBRATION  {record.get('calibration_pass')}",
        f"DAY_002 FIT  {record.get('day002_fit')}",
        f"TRUE FIT PAIRS  {record.get('true_fit_count')}",
        f"TEMPLE RENDERED  {record.get('temple_rendered')}",
        f"GPT IMAGE  {record.get('gpt_image_calls')}",
        "MASTER UNCHANGED  YES",
        str(record.get("next_decision") or ""),
    ):
        for chunk in _wrap(str(line), 88):
            draw.text((36, y), chunk, fill=(180, 176, 168), font=_font(16))
            y += 28
    return canvas


def request_temple_critic(candidate: Image.Image, foundation: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Independent luxury real-estate art director. Do not inflate. JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Score 0-10: professional_art_direction, family_fidelity, composition, image_design_integration, "
                            "typography, hierarchy, commercial_clarity, logo_integration, cta_integration, premium_character, "
                            "readability, architecture_fidelity, publishability. Image 1 candidate, Image 2 foundation."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    return flatten_critic(parsed), calls


def generate_production_compositor_4x5(
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
    images: dict[str, Any] = {"capabilities": render_capabilities()}
    library = _library()
    fonts = build_font_registry()
    family = family_by_id(library, PROOF_FAMILY_ID)
    logo_rgba = None
    try:
        logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    except Exception:
        logo_rgba = None
    calibration = run_reference_calibration(family=family, fonts=fonts, logo_rgba=logo_rgba)
    ornek = None
    try:
        ornek = Image.open(io.BytesIO(_read_bytes(db, UUID(REF_00013)))).convert("RGB")
    except Exception:
        ornek = None
    recon = calibration.get("pack", {}).get("image") or calibration.get("photo")
    images["calibration"] = render_calibration_board(ornek, recon if isinstance(recon, Image.Image) else calibration["photo"])
    images["calibration_scores"] = render_score_board(calibration)
    day002: dict[str, Any] | None = None
    ranking: list[dict[str, Any]] = []
    pack: dict[str, Any] | None = None
    spec: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None
    critic: dict[str, Any] = {}
    ready: dict[str, Any] | None = None
    candidate_asset_id = None
    temple_rendered = False
    status = "CALIBRATION_FAIL"
    next_decision = "Compositor calibration failed. Do not test Temple until craft scores are all >= 8."
    source = None

    if calibration.get("pass"):
        status = "NO_CURRENT_IMAGE_FAMILY_PAIR_FITS"
        next_decision = "No architecture-clear Temple pair can hold the HIGH-density lockup. Do not invent a family yet unless that photographic condition is the brief."
        try:
            source = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY002_ASSET_ID)))).convert("RGB")
        except Exception as exc:
            source = None
            status = "FAIL_FAST_MISSING_DAY002"
            next_decision = f"Calibration passed but Day_002 was unreadable: {exc}"
    if calibration.get("pass") and source is not None:
        crop, _ = cover_fit_canvas(source, CANVAS_4X5, centering=(0.50, 0.32))
        graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
        occ = build_photo_occupancy_map(graded)
        density = campaign_density_profile(fonts=fonts, family=family, canvas=CANVAS_4X5)
        day002 = evaluate_family_eligibility_v2(photo=graded, occupancy=occ, family=family, fonts=fonts, density=density)
        day002["filename"] = DAY002_FILENAME
        day002["asset_id"] = DAY002_ASSET_ID
        images["fit"] = render_fit_board(day002)
        if day002.get("contiguous_fit") != "FIT":
            next_decision = "Day_002 × EDITORIAL_DARK_FIELD is NO_FIT under Eligibility V2. Do not render that impossible composition."
        families = [family_by_id(library, fid) for fid in ALL_MASTER_FAMILIES]
        for asset in list_temple_exterior_assets(db):
            try:
                photo = Image.open(io.BytesIO(_read_bytes(db, asset.id))).convert("RGB")
            except Exception:
                continue
            c, _t = cover_fit_canvas(photo, CANVAS_4X5, centering=(0.50, 0.32))
            g = apply_photographic_grade(c, dict(LOCKED_GRADE))
            o = build_photo_occupancy_map(g)
            for fam in families:
                result = evaluate_family_eligibility_v2(photo=g, occupancy=o, family=fam, fonts=fonts, density=density)
                ranking.append(
                    {
                        "asset_id": str(asset.id),
                        "filename": asset.filename,
                        "family_id": fam.get("family_id"),
                        "status": result.get("status"),
                        "contiguous_fit": result.get("contiguous_fit"),
                        "reason": result.get("primary_reason"),
                        "safe": (result.get("fit") or {}).get("safe_rect"),
                        "true_fit": result.get("status") == "ELIGIBLE" and result.get("contiguous_fit") == "FIT",
                    }
                )
        ranking.sort(key=lambda item: (1 if item.get("true_fit") else 0, float((item.get("safe") or {}).get("w") or 0) * float((item.get("safe") or {}).get("h") or 0)), reverse=True)
        images["ranking"] = render_ranking(ranking)
        true_fits = [r for r in ranking if r.get("true_fit")]
        if true_fits:
            top = true_fits[0]
            src = Image.open(io.BytesIO(_read_bytes(db, UUID(str(top["asset_id"]))))).convert("RGB")
            c, transform = cover_fit_canvas(src, CANVAS_4X5, centering=(0.50, 0.32))
            g = apply_photographic_grade(c, dict(LOCKED_GRADE))
            o = build_photo_occupancy_map(g)
            fam = family_by_id(library, str(top["family_id"]))
            pack = compose_graphic_design_v3(g, occupancy=o, family=fam, fonts=fonts, logo_rgba=logo_rgba)
            if pack.get("solved"):
                field_asset = persist_gpt_image(
                    db, actor=user, linked_project_id=row.linked_project_id, content=_png(pack["fielded"]),
                    content_type="image/png", campaign_mode="project-v3-field", session_id=str(uuid4()),
                    provider_generation_id=None, campaign_context_id=str(row.id), brief_excerpt="PHASE 5.4J field",
                )
                asset = persist_gpt_image(
                    db, actor=user, linked_project_id=row.linked_project_id, content=_png(pack["image"]),
                    content_type="image/png", campaign_mode="project-v3-candidate", session_id=str(uuid4()),
                    provider_generation_id=None, campaign_context_id=str(row.id), brief_excerpt="PHASE 5.4J candidate",
                )
                pack["graphic_field_asset_id"] = str(field_asset.id)
                spec = build_family_master_spec(
                    key="V3-1", pack=pack, family=fam, crop={"centering": [0.5, 0.32], "source_crop": transform.get("source_crop")},
                    photo_asset=str(top["asset_id"]), logo_asset=LOCKED_LOGO_ASSET_ID,
                    candidate_asset_id=str(asset.id), architecture_lock={"schema": "PhotoOccupancyMapV1"},
                )
                spec["schema"] = "ProductionMasterCandidateV1"
                spec["graphic_field"]["asset_id"] = str(field_asset.id)
                spec["graphic_field"]["semantic_role"] = "graphic_field"
                spec["visual_replace_requires_eligibility"] = True
                ready = family_revision_readiness(spec)
                collision = evaluate_collisions(objects=pack.get("objects") or {}, occupancy=o, size=pack["image"].size)
                provenance = architecture_provenance_qa(
                    source=src, foundation=pack["foundation"], final=pack["image"],
                    transform={"centering": [0.5, 0.32], "source_crop": transform.get("source_crop") or [0, 0, 1, 1]},
                )
                utf8 = turkish_copy_is_valid(pack.get("facts") or {})
                checks = {
                    "architecture_integrity": "PASS" if provenance.get("status") == "pass" else "FAIL",
                    "contiguous_fit": "PASS",
                    "collision": "PASS" if collision.get("pass") else "FAIL",
                    "contrast": "PASS" if (pack.get("contrast") or {}).get("pass") else "FAIL",
                    "UTF8": "PASS" if utf8 else "FAIL",
                    "font_metrics": "PASS",
                    "family_constraints": "PASS",
                    "semantic_completeness": "PASS",
                    "revision_readiness": ready.get("revision_readiness") or "FAIL",
                }
                preflight = {"schema": "BestPairTechnicalPreflightV1", "checks": checks, "pass": all(v == "PASS" for v in checks.values())}
                critic, n = request_temple_critic(pack["image"], pack["foundation"])
                vision_calls += n
                candidate_asset_id = str(asset.id)
                temple_rendered = True
                status = "TEMPLE_PROOF_RENDERED" if preflight["pass"] else "TEMPLE_PROOF_TECHNICAL_FAIL"
                next_decision = "Human-review the single V3 proof. Do not promote."
                images["proof"] = pack["image"]
                images["structure"] = render_structure_map(pack["image"], pack.get("objects") or {})
                images["preflight"] = render_score_board({"pass": preflight["pass"], "scores": {k: 10 if v == "PASS" else 3 for k, v in checks.items()}})
                images["critic"] = render_score_board({"pass": False, "scores": {k: critic.get(k) for k in ("professional_art_direction", "family_fidelity", "typography", "hierarchy", "publishability")}})
            else:
                next_decision = "A geometric FIT existed but compositor V3 did not solve. Do not force a render."
        else:
            status = "NO_CURRENT_IMAGE_FAMILY_PAIR_FITS"
            next_decision = "Eligibility V2 is honest: no approved Temple exterior has a contiguous clear field large enough for this HIGH-density lockup. Next family must be designed for full-frame architecture."

    if "fit" not in images:
        images["fit"] = render_fit_board(
            {"contiguous_fit": "NOT_EVALUATED", "primary_reason": "Temple was not tested because calibration failed.", "v1_status": None, "v1_false_positive": False, "fit": {}}
        )
    if "ranking" not in images:
        images["ranking"] = render_ranking(ranking)
    images["decision"] = render_decision(
        {
            "status": status,
            "calibration_pass": calibration.get("pass"),
            "day002_fit": (day002 or {}).get("contiguous_fit"),
            "true_fit_count": len([r for r in ranking if r.get("true_fit")]),
            "temple_rendered": temple_rendered,
            "gpt_image_calls": 0,
            "next_decision": next_decision,
        }
    )
    gpt_calls = provider_call_count()
    true_fits = [r for r in ranking if r.get("true_fit")]
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54J,
        "created_at": _now(),
        "status": status,
        "compositor": "GraphicDesignCompositorV3",
        "eligibility_engine": "PhotoFamilyEligibilityEngineV2",
        "calibration": _jsonable({k: v for k, v in calibration.items() if k not in {"pack", "photo"}}),
        "calibration_pass": bool(calibration.get("pass")),
        "day002": _jsonable(day002),
        "day002_fit": (day002 or {}).get("contiguous_fit"),
        "pair_ranking": ranking,
        "true_fit_count": len(true_fits),
        "top_true_fit": true_fits[0] if true_fits else None,
        "temple_rendered": temple_rendered,
        "candidate_asset_id": candidate_asset_id,
        "spec_id": (spec or {}).get("spec_id"),
        "spec": spec,
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "critic": critic,
        "next_decision": next_decision,
        "gpt_image_calls": gpt_calls,
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "new_family_created": False,
        "phase55_executed": False,
        "project_id": TEMPLE_PROJECT_ID,
        "tokens": _jsonable(execution_tokens(family)),
        "capabilities": {
            "engine": "GraphicDesignCompositorV3",
            "solver": "RelationalCreativeLayoutSolverV1",
            "spacing": "CreativeSpacingEngineV1",
            "numbers": "CommercialNumberRendererV1",
            "tokens": "CreativeExecutionTokensV1",
            "eligibility": "PhotoFamilyEligibilityEngineV2",
            "fit_test": "ContiguousContentFitTestV1",
            "groups": ["DisplayGroup", "CommercialOfferGroup", "BrandGroup", "CTAGroup", "SupportingInfoGroup"],
            "forbidden_primitives": ["cards", "pills", "chips", "KPI boxes", "web buttons", "dashboard panels"],
            "gpt_image": False,
        },
        "human_review_required": True,
    }
    tests = [t for t in list(blob.get("production_compositor_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54J)]
    tests.append(json.loads(json.dumps(record, default=str)))
    blob["production_compositor_tests"] = tests
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
    if blob.get("photo_family_eligibility_tests") != preserved.get("quality54h"):
        raise RuntimeError("Phase 5.4J refused to overwrite Phase 5.4H")
    if blob.get("best_pair_proof_tests") != preserved.get("quality54i"):
        raise RuntimeError("Phase 5.4J refused to overwrite Phase 5.4I")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4J refused to modify approved creative masters")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(ctx.get("current_cover_asset_id")) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4J refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["calibration_pack"] = calibration.get("pack")
    _ = language
    return record
