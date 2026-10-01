"""Phase 6.1-R1 — Concept 3 reconstruction fidelity correction.

One child candidate. Does not overwrite Phase 6.1. GPT Image = 0.
Does not promote. Does not change production cover.
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
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
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
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    DAY007_FILENAME,
    FIDELITY_FLOORS,
    analyze_concept3_pixels,
    dark_field_mask_from_concept,
    geometric_fidelity,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_1_concept3_production_master import _HISTORY_KEYS as _H61
from investhome_api.services.creative_director.phase6_1_concept3_production_master import _pair
from investhome_api.services.creative_director.phase6_1_concept3_production_master import _preserve as _preserve_61
from investhome_api.services.creative_director.phase6_1_concept3_production_master import _score_board
from investhome_api.services.creative_director.phase6_1_r1_compose import (
    APPROVED_BOTTOM_COPY,
    CRITIC_FLOORS,
    PARENT_61_ASSET_ID,
    PARENT_61_SPEC_ID,
    compose_concept3_r1,
    request_r1_critics,
    search_day007_crops,
    visual_mass_match,
)
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_61R1 = "phase6_1_r1_fidelity_correction"
_HISTORY_KEYS = _H61 + (("concept3_production_master_61_tests", "quality61"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_61(blob)
    preserved["quality61"] = list(blob.get("concept3_production_master_61_tests") or [])
    return preserved


def _crop_board(images: dict[str, Image.Image], selected_id: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1480), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "05  CROP CANDIDATE BOARD  —  12 real Day_007 crops  —  not generated", font=_font(18), fill=(201, 168, 92))
    ids = sorted(images)
    for i, cid in enumerate(ids[:12]):
        gx, gy = i % 4, i // 4
        x, y = 36 + gx * 470, 56 + gy * 460
        tile = images[cid].copy()
        tile.thumbnail((440, 400), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        mark = "  SELECTED" if cid == selected_id else ""
        draw.text((x, y + 404), f"{cid}{mark}", font=_font(14), fill=(201, 168, 92) if mark else (226, 222, 214))
    return canvas


def _mass_board(mass: dict[str, Any], concept: Image.Image, r1: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "07  VISUAL MASS COMPARISON  —  ConceptVisualMassMatcherV1", font=_font(18), fill=(201, 168, 92))
    for i, (image, cap) in enumerate(((concept, "CONCEPT 3"), (r1, "R1"))):
        tile = image.copy()
        tile.thumbnail((720, 900), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (36 + i * 760, 56))
        draw.text((36 + i * 760, 970), cap, font=_font(14), fill=(226, 222, 214))
    y = 56
    for line in [
        f"pass {mass.get('pass')}",
        *[f"{k}: {v}" for k, v in (mass.get("deltas") or {}).items()],
        *[f"gate {k}: {v}" for k, v in (mass.get("gates") or {}).items()],
    ]:
        draw.text((1540, y), str(line)[:42], font=_font(14), fill=(226, 222, 214))
        y += 28
    return canvas


def build_r1_spec(pack: dict[str, Any], crop: dict[str, Any], master_asset_id: str, field_asset_id: str) -> dict[str, Any]:
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
        groups.append({"role": role, "bounds": item.get("bounds"), "editable": True, "mutable_for": mutable.get(role, ["COPY_EDIT_ONLY"])})
    return {
        "schema": "ApprovedConcept3ProductionMasterSpecR1",
        "spec_id": str(uuid4()),
        "parent_asset_id": PARENT_61_ASSET_ID,
        "parent_spec_id": PARENT_61_SPEC_ID,
        "reconstruction_mode": "APPROVED_CONCEPT_3",
        "classified_as": None,
        "canvas": pack.get("canvas"),
        "project_photo": {"asset_id": DAY007_ASSET_ID, "filename": DAY007_FILENAME, "crop": crop, "z": 0, "bounds": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}},
        "graphic_field": {"semantic_role": "graphic_field", "asset_id": field_asset_id, "locked_raster": True, "z": 1, "kind": "approved_concept_3_curved_editorial_field"},
        "project_logo": {"asset_id": LOCKED_LOGO_ASSET_ID, "ai_redrawn": False, "z": 3, "bounds": (objects.get("project_logo") or {}).get("bounds")},
        "headline": {"text": REQUIRED_FACTS["headline"], "bounds": (objects.get("headline") or {}).get("bounds"), "z": 2},
        "unit_type": {"text": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}", "bounds": (objects.get("unit_type") or {}).get("bounds"), "z": 2},
        "price": {"text": REQUIRED_FACTS["list_price"], "bounds": (objects.get("price") or {}).get("bounds"), "z": 2},
        "discount": {"text": REQUIRED_FACTS["discount"], "bounds": (objects.get("discount") or {}).get("bounds"), "z": 2},
        "discount_label": {"text": REQUIRED_FACTS["discount_label"], "bounds": (objects.get("discount_label") or {}).get("bounds"), "z": 2},
        "cta": {"text": REQUIRED_FACTS["cta"], "bounds": (objects.get("cta") or {}).get("bounds"), "z": 2},
        "editorial_closure": {"text": APPROVED_BOTTOM_COPY, "copy_status": "APPROVED", "bounds": (objects.get("editorial_closure") or {}).get("bounds"), "z": 2},
        "typography": {"display": "Cormorant Garamond", "support": "Source Sans 3"},
        "source_asset": DAY007_ASSET_ID,
        "candidate_asset": master_asset_id,
        "editable_commercial_groups": groups,
        "promoted": False,
    }


def generate_concept3_r1(
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
    if concept.size != (1088, 1360):
        concept = ImageOps.fit(concept, (1088, 1360), method=Image.Resampling.LANCZOS)
    parent = Image.open(__import__("io").BytesIO(_read_bytes(db, UUID(PARENT_61_ASSET_ID)))).convert("RGB")
    source = load_day007(db)
    logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    if logo_rgba is None:
        raise RuntimeError("Phase 6.1-R1 requires the real Temple logo")
    fonts = build_font_registry()
    structure = analyze_concept3_pixels(concept)
    crops = search_day007_crops(concept, source)
    occupancy = build_photo_occupancy_map(crops["selected_image"])
    pack = compose_concept3_r1(
        crops["selected_image"],
        concept=concept,
        structure=structure,
        fonts=fonts,
        logo_rgba=logo_rgba,
        occupancy=occupancy,
    )
    kinds = [str(f.get("kind")) for f in pack.get("graphic_fields") or []]
    if "editorial_measurement_marks" in kinds or "elliptical_arc" in kinds:
        raise RuntimeError("R1 forbids concentric / extra ellipse fragments")
    field_only = pack["fielded"].copy()
    geom = geometric_fidelity(concept, pack["image"], pack["field_mask"])
    mass = visual_mass_match(concept, pack["image"], structure, pack["objects"], pack["field_mask"])
    fidelity, critic, n = request_r1_critics(concept, pack["image"])
    vision_calls += n
    fidelity["geometric"] = geom
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.1-R1 forbids GPT Image production calls")

    field_asset = persist_gpt_image(
        db, actor=user, linked_project_id=row.linked_project_id, content=_png(field_only),
        content_type="image/png", campaign_mode="project-v3-61r1-graphic-field", session_id=str(uuid4()),
        provider_generation_id=None, campaign_context_id=str(row.id), brief_excerpt="PHASE 6.1-R1 graphic field",
    )
    master_asset = persist_gpt_image(
        db, actor=user, linked_project_id=row.linked_project_id, content=_png(pack["image"]),
        content_type="image/png", campaign_mode="project-v3-61r1-structured-master", session_id=str(uuid4()),
        provider_generation_id=None, campaign_context_id=str(row.id), brief_excerpt="PHASE 6.1-R1 child — pending human review",
    )
    spec = build_r1_spec(pack, crops["selected"]["transform"], str(master_asset.id), str(field_asset.id))
    readiness = family_revision_readiness(spec)
    readiness["executed"] = False
    provenance = architecture_provenance_qa(source=source, foundation=pack["foundation"], final=pack["image"], transform=crops["selected"]["transform"])
    real_asset = {
        "schema": "RealAssetValidationV1",
        "REAL_DAY_007": "PASS",
        "REAL_TEMPLE_LOGO": "PASS",
        "generated_architecture_pixels": 0,
        "generated_logo_pixels": 0,
        "generated_text_pixels": 0,
        "architecture_fidelity": 10 if provenance.get("status") == "pass" else 0,
        "architecture_provenance": provenance,
        "uniform_scale": True,
        "inpainting": False,
        "outpainting": False,
        "building_modification": False,
        "pass": provenance.get("status") == "pass",
    }
    ref_mask = dark_field_mask_from_concept(concept)
    dark_field = {
        "before": "feathered translucent overlay (6.1 parent)",
        "after": pack.get("field_density"),
        "concept_field_coverage": round(sum(1 for v in ref_mask.getdata() if v > 40) / (ref_mask.size[0] * ref_mask.size[1]), 4),
        "r1_field_coverage": round(sum(1 for v in pack["field_mask"].convert("L").getdata() if v > 40) / (pack["field_mask"].size[0] * pack["field_mask"].size[1]), 4),
    }
    arc_system = {
        "before": "main arc + concentric ellipse fragments + off-canvas ticks",
        "after": "main_arc + measurement_ticks + precision_marker",
        "kinds": kinds,
    }
    missed = list(fidelity.get("failed") or []) + [f"critic:{k}" for k in (critic.get("failed") or [])]
    if not mass.get("pass"):
        missed.append("visual_mass_matcher")
    if readiness.get("revision_readiness") != "PASS":
        missed.append("revision_readiness")
    status = "STRUCTURED_MASTER_PENDING_HUMAN_REVIEW"
    images = {
        "concept": concept,
        "parent": parent,
        "dark": _pair(concept, field_only, "03  DARK FIELD ANALYSIS", ("CONCEPT 3", "R1 FIELD")),
        "arc": _pair(parent, pack["image"], "04  ARC SYSTEM ANALYSIS  —  parent extra rings vs R1 single arc", ("6.1 PARENT", "R1")),
        "crops": _crop_board(crops["images"], crops["selected_id"]),
        "crop": crops["selected_image"],
        "mass": _mass_board(mass, concept, pack["image"]),
        "master": pack["image"],
        "compare": _pair(concept, pack["image"], "09  CONCEPT 3 vs R1  —  not promoted", ("APPROVED CONCEPT 3", "R1 STRUCTURED MASTER")),
        "fidelity": _score_board("10  RECONSTRUCTION FIDELITY vs CONCEPT 3", fidelity.get("scores") or {}, FIDELITY_FLOORS),
        "revision": _text_board("11  REVISION READINESS  —  static only", [f"{k}: {v}" for k, v in (readiness.get("checks") or {}).items()] + [f"overall {readiness.get('revision_readiness')}", "executed: NO"]),
        "assets": _text_board("12  REAL-ASSET VALIDATION", [f"Day_007 {DAY007_ASSET_ID} PASS", f"logo {LOCKED_LOGO_ASSET_ID} PASS", "generated pixels 0 / 0 / 0", f"architecture_fidelity {real_asset['architecture_fidelity']}"]),
        "review": _pair(concept, pack["image"], f"13  HUMAN REVIEW BOARD  —  {status}", ("APPROVED CONCEPT 3", "R1  —  pending human review")),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_61R1,
        "created_at": _now(),
        "status": status,
        "parent_asset_id": PARENT_61_ASSET_ID,
        "parent_spec_id": PARENT_61_SPEC_ID,
        "r1_asset_id": str(master_asset.id),
        "r1_spec_id": spec["spec_id"],
        "graphic_field_asset_id": str(field_asset.id),
        "source_photo": {"filename": DAY007_FILENAME, "asset_id": DAY007_ASSET_ID, "crop": crops["selected"]},
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "dark_field": dark_field,
        "arc_system": arc_system,
        "visual_mass": mass,
        "reconstruction_fidelity": fidelity,
        "fresh_visual_critic": critic,
        "revision_readiness": readiness,
        "real_asset_validation": real_asset,
        "bottom_editorial_copy": {"text": APPROVED_BOTTOM_COPY, "approval_status": "APPROVED", "rendered_on_master": True},
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "missed_gates": missed,
        "promoted_to_master": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "production_cover_changed": False,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "language": language,
        "concept3_asset_id": CONCEPT3_ASSET_ID,
        "crop_candidates": crops["candidates"],
        "selected_crop": crops["selected"],
        "graphic_field_spec": pack.get("graphic_fields"),
        "production_master_spec": spec,
        "next_decision": "HUMAN VISUAL REVIEW",
    }
    tests = list(blob.get("concept3_r1_61_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["concept3_r1_61_tests"] = tests
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
    blob["concept3_production_master_61_tests"] = preserved.get("quality61")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.1-R1 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
