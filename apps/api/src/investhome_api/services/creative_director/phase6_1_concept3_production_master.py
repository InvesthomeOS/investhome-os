"""Phase 6.1 — Concept 3 high-fidelity structured production master.

Reconstructs the human-approved Concept 3. Does not generate a new concept.
Does not call GraphicDesignCompositorV4 layout modes. GPT Image = 0.
Does not promote. Does not modify existing masters or the production cover.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageOps
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_family_adapter import family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.graphic_field_engine import render_vector_fields
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font, _wrap
from investhome_api.services.creative_director.phase5_photo_foundation import architecture_provenance_qa
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
)
from investhome_api.services.creative_director.phase6_0_pure_creative_director import _HISTORY_KEYS as _H60
from investhome_api.services.creative_director.phase6_0_pure_creative_director import _preserve as _preserve_60
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CANVAS_4X5,
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    DAY007_FILENAME,
    DRAFT_BOTTOM_COPY,
    FIDELITY_FLOORS,
    analyze_concept3_pixels,
    compose_approved_concept3,
    geometric_fidelity,
    load_approved_concept3,
    load_day007,
    match_day007_crop,
    request_fidelity_and_quality,
    request_structure_vision,
)
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_61 = "phase6_1_concept3_production_master"
_HISTORY_KEYS = _H60 + (("pure_creative_director_60_tests", "quality60"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_60(blob)
    preserved["quality60"] = list(blob.get("pure_creative_director_60_tests") or [])
    return preserved


def _pair(left: Image.Image, right: Image.Image, title: str, captions: tuple[str, str]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), title, font=_font(18), fill=(201, 168, 92))
    for i, (image, cap) in enumerate(((left, captions[0]), (right, captions[1]))):
        tile = image.copy()
        tile.thumbnail((880, 980), Image.Resampling.LANCZOS)
        x = 36 + i * 940
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1050), cap[:72], font=_font(14), fill=(226, 222, 214))
    return canvas


def _overlay_structure(concept: Image.Image, structure: dict[str, Any]) -> Image.Image:
    image = concept.convert("RGBA")
    draw = ImageDraw.Draw(image)
    w, h = image.size
    poly = structure["dark_field_geometry"]["polyline_x"]
    pts = [(int(w * x), int(h * i / max(len(poly) - 1, 1))) for i, x in enumerate(poly)]
    if len(pts) >= 2:
        draw.line(pts, fill=(201, 168, 92, 220), width=3)
    colors = {
        "brand_group": (201, 168, 92, 180),
        "campaign_group": (244, 239, 228, 200),
        "offer_group": (180, 210, 230, 200),
        "action_group": (220, 180, 140, 200),
        "bottom_closure": (200, 200, 210, 200),
    }
    for key, box in (structure.get("groups") or {}).items():
        x0, y0 = int(box["x"] * w), int(box["y"] * h)
        x1, y1 = int((box["x"] + box["w"]) * w), int((box["y"] + box["h"]) * h)
        draw.rectangle((x0, y0, x1, y1), outline=colors.get(key, (255, 255, 255, 180)), width=2)
        draw.text((x0 + 6, y0 + 4), key.upper(), font=_font(14), fill=colors.get(key, (255, 255, 255, 200)))
    return image.convert("RGB")


def _score_board(title: str, scores: dict[str, Any], floors: dict[str, Any] | None = None) -> Image.Image:
    rows = [f"{k}: {scores.get(k)}  floor {floors.get(k, '-')}" for k in (floors or scores)]
    if not rows:
        rows = [f"{k}: {v}" for k, v in scores.items()]
    return _text_board(title, rows, size=(1280, 1600))


def build_production_spec(pack: dict[str, Any], crop: dict[str, Any], master_asset_id: str, field_asset_id: str) -> dict[str, Any]:
    objects = dict(pack.get("objects") or {})
    groups = []
    mutable = {
        "headline": ["COPY_EDIT_ONLY"],
        "unit_type": ["COPY_EDIT_ONLY"],
        "price": ["PRICE_EDIT_ONLY"],
        "discount": ["PRICE_EDIT_ONLY", "COPY_EDIT_ONLY"],
        "discount_label": ["COPY_EDIT_ONLY"],
        "cta": ["COPY_EDIT_ONLY"],
        "project_logo": ["LOGO_ONLY"],
        "editorial_closure": ["COPY_EDIT_ONLY"],
    }
    for role, item in objects.items():
        groups.append(
            {
                "role": role,
                "bounds": item.get("bounds"),
                "editable": role != "editorial_closure",
                "mutable_for": mutable.get(role, ["COPY_EDIT_ONLY"]),
                "copy_status": item.get("copy_status"),
            }
        )
    return {
        "schema": "ApprovedConcept3ProductionMasterSpecV1",
        "spec_id": str(uuid4()),
        "reconstruction_mode": "APPROVED_CONCEPT_3",
        "classified_as": None,
        "canvas": pack.get("canvas"),
        "project_photo": {
            "asset_id": DAY007_ASSET_ID,
            "filename": DAY007_FILENAME,
            "crop": crop,
            "z": 0,
            "bounds": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
        },
        "graphic_field": {
            "semantic_role": "graphic_field",
            "asset_id": field_asset_id,
            "locked_raster": True,
            "z": 1,
            "kind": "approved_concept_3_curved_editorial_field",
        },
        "project_logo": {
            "asset_id": LOCKED_LOGO_ASSET_ID,
            "ai_redrawn": False,
            "z": 3,
            "bounds": (objects.get("project_logo") or {}).get("bounds"),
        },
        "headline": {"text": REQUIRED_FACTS["headline"], "bounds": (objects.get("headline") or {}).get("bounds"), "z": 2},
        "unit_type": {"text": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}", "bounds": (objects.get("unit_type") or {}).get("bounds"), "z": 2},
        "price": {"text": REQUIRED_FACTS["list_price"], "bounds": (objects.get("price") or {}).get("bounds"), "z": 2},
        "discount": {"text": REQUIRED_FACTS["discount"], "bounds": (objects.get("discount") or {}).get("bounds"), "z": 2},
        "discount_label": {"text": REQUIRED_FACTS["discount_label"], "bounds": (objects.get("discount_label") or {}).get("bounds"), "z": 2},
        "cta": {"text": REQUIRED_FACTS["cta"], "bounds": (objects.get("cta") or {}).get("bounds"), "z": 2},
        "editorial_closure": {
            "text": None,
            "copy_status": "PENDING_HUMAN_COPY_APPROVAL",
            "draft_generated_copy": pack.get("draft_generated_copy") or DRAFT_BOTTOM_COPY,
            "bounds": (objects.get("editorial_closure") or {}).get("bounds"),
            "z": 2,
        },
        "typography": {"display": "Cormorant Garamond", "support": "Source Sans 3"},
        "grouping": {
            "BRAND_GROUP": ["project_logo", "brand_caption"],
            "CAMPAIGN_GROUP": ["headline"],
            "OFFER_GROUP": ["discount", "discount_label", "price", "unit_type"],
            "ACTION_GROUP": ["cta"],
            "EDITORIAL_CLOSURE_GROUP": ["editorial_closure"],
        },
        "source_asset": DAY007_ASSET_ID,
        "candidate_asset": master_asset_id,
        "editable_commercial_groups": groups,
        "promoted": False,
    }


def generate_concept3_production_master_61(
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

    concept = load_approved_concept3(db)
    if concept.size != CANVAS_4X5:
        concept = ImageOps.fit(concept, CANVAS_4X5, method=Image.Resampling.LANCZOS)
    source = load_day007(db)
    logo_rgba = logo_to_rgba(_read_logo(db), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    if logo_rgba is None:
        raise RuntimeError("Phase 6.1 requires the real Temple logo")
    fonts = build_font_registry()

    structure = analyze_concept3_pixels(concept)
    structure, n = request_structure_vision(concept, structure)
    vision_calls += n
    crop_match = match_day007_crop(concept, source)
    occupancy = build_photo_occupancy_map(crop_match["graded"])
    pack = compose_approved_concept3(
        crop_match["graded"],
        structure=structure,
        fonts=fonts,
        logo_rgba=logo_rgba,
        occupancy=occupancy,
    )
    field_only = pack["fielded"].convert("RGBA")
    field_only.alpha_composite(render_vector_fields(tuple(pack["canvas"]), pack["graphic_fields"]))
    field_only = field_only.convert("RGB")

    geom = geometric_fidelity(concept, pack["image"], pack["field_mask"])
    fidelity, n = request_fidelity_and_quality(concept, pack["image"])
    vision_calls += n
    fidelity["geometric"] = geom

    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.1 forbids GPT Image production calls")

    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(field_only),
        content_type="image/png",
        campaign_mode="project-v3-61-concept3-graphic-field",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 6.1 Concept 3 graphic field reconstruction",
    )
    master_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode="project-v3-61-concept3-production-master",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 6.1 Concept 3 structured production master — pending human review",
    )
    spec = build_production_spec(pack, crop_match["transform"], str(master_asset.id), str(field_asset.id))
    readiness = family_revision_readiness(spec)
    readiness["executed"] = False
    provenance = architecture_provenance_qa(
        source=source,
        foundation=pack["foundation"],
        final=pack["image"],
        transform=crop_match["transform"],
    )
    real_asset = {
        "schema": "RealAssetValidationV1",
        "REAL_DAY_007": "PASS" if DAY007_ASSET_ID == crop_match["source_asset_id"] else "FAIL",
        "REAL_TEMPLE_LOGO": "PASS" if LOCKED_LOGO_ASSET_ID and pack.get("real_logo") else "FAIL",
        "generated_architecture_pixels": 0,
        "generated_logo_pixels": 0,
        "generated_text_pixels": 0,
        "architecture_fidelity": 10 if provenance.get("status") == "pass" else 0,
        "architecture_provenance": provenance,
        "uniform_scale": True,
        "inpainting": False,
        "outpainting": False,
        "building_modification": False,
    }
    real_asset["pass"] = (
        real_asset["REAL_DAY_007"] == "PASS"
        and real_asset["REAL_TEMPLE_LOGO"] == "PASS"
        and real_asset["generated_architecture_pixels"] == 0
        and real_asset["architecture_fidelity"] >= 9
    )
    status = "STRUCTURED_MASTER_PENDING_HUMAN_REVIEW"
    images = {
        "concept": concept,
        "structure": _overlay_structure(concept, structure),
        "source": source.convert("RGB"),
        "crop": crop_match["graded"],
        "field": field_only,
        "master": pack["image"],
        "compare": _pair(concept, pack["image"], "07  CONCEPT 3 vs STRUCTURED PRODUCTION  —  not promoted", ("APPROVED CONCEPT 3", "STRUCTURED PRODUCTION MASTER")),
        "fidelity": _score_board("08  RECONSTRUCTION FIDELITY vs CONCEPT 3", fidelity.get("scores") or {}, FIDELITY_FLOORS),
        "assets": _text_board(
            "09  REAL-ASSET VALIDATION",
            [
                f"Day_007 {DAY007_ASSET_ID}  {real_asset['REAL_DAY_007']}",
                f"Temple logo {LOCKED_LOGO_ASSET_ID}  {real_asset['REAL_TEMPLE_LOGO']}",
                f"generated architecture pixels {real_asset['generated_architecture_pixels']}",
                f"generated logo pixels {real_asset['generated_logo_pixels']}",
                f"generated text pixels {real_asset['generated_text_pixels']}",
                f"architecture_fidelity {real_asset['architecture_fidelity']}",
                f"crop centering {crop_match['centering']}  ncc {crop_match['ncc']}",
            ],
        ),
        "revision": _text_board(
            "10  REVISION READINESS  —  static only, not executed",
            [f"{k}: {v}" for k, v in (readiness.get("checks") or {}).items()] + [f"overall {readiness.get('revision_readiness')}", "executed: NO"],
        ),
        "review": _pair(
            concept,
            pack["image"],
            f"11  HUMAN REVIEW BOARD  —  {status}",
            ("APPROVED CONCEPT 3", "STRUCTURED PRODUCTION  —  pending human review"),
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_61,
        "created_at": _now(),
        "status": status,
        "approved_creative_direction": "Concept 3",
        "concept3_asset_id": CONCEPT3_ASSET_ID,
        "source_photo": {"filename": DAY007_FILENAME, "asset_id": DAY007_ASSET_ID},
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "structured_master_asset_id": str(master_asset.id),
        "graphic_field_asset_id": str(field_asset.id),
        "master_spec_id": spec["spec_id"],
        "reconstruction_fidelity": fidelity,
        "real_asset_validation": real_asset,
        "revision_readiness": readiness,
        "bottom_editorial_copy": {
            "draft_generated_copy": pack.get("draft_generated_copy") or DRAFT_BOTTOM_COPY,
            "approval_status": "PENDING_HUMAN_COPY_APPROVAL",
            "rendered_on_master": False,
        },
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "promoted_to_master": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "visual_replace_child_id": "6f18ae33-72fb-4506-ab49-24f8d90b6c2d",
        "production_cover_changed": False,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "language": language,
        "classified_as": None,
        "v4_mode_used": False,
        "next_decision": "HUMAN VISUAL REVIEW",
        "structure": {k: structure.get(k) for k in structure if k not in {"vision"}},
        "photo_crop_match": {
            "centering": crop_match["centering"],
            "ncc": crop_match["ncc"],
            "transform": crop_match["transform"],
            "asset_id": DAY007_ASSET_ID,
            "filename": DAY007_FILENAME,
        },
        "graphic_field_spec": pack.get("graphic_fields"),
        "production_master_spec": spec,
        "compositor": pack.get("compositor"),
    }
    tests = [t for t in list(blob.get("concept3_production_master_61_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_61)]
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["concept3_production_master_61_tests"] = tests
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
    blob["ai_draft_structured_master_59_tests"] = preserved.get("quality59")
    blob["pure_creative_director_60_tests"] = preserved.get("quality60")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.1 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record


def _read_logo(db: Session) -> bytes:
    from investhome_api.services.creative_director.phase5_workflow import _read_bytes

    return _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
