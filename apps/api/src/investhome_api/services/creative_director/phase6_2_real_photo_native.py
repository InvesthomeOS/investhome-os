"""Phase 6.2 — Concept 3 design language × real Day_007 native composition.

New candidate branch. Not an R2 of 6.1 / 6.1-R1. GPT Image = 0.
Does not promote. Does not change the production cover.
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
    CANVAS_4X5,
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    DAY007_FILENAME,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_1_concept3_production_master import _pair, _score_board
from investhome_api.services.creative_director.phase6_1_r1_fidelity_correction import _HISTORY_KEYS as _H61R1
from investhome_api.services.creative_director.phase6_1_r1_fidelity_correction import _preserve as _preserve_61r1
from investhome_api.services.creative_director.phase6_2_compose import (
    APPROVED_BOTTOM_COPY,
    FINAL_FLOORS,
    NATIVE_MODE,
    build_real_photo_composition_map,
    build_transfer_plan,
    choose_native_day007_crop,
    compose_day007_native,
    render_composition_map,
    render_sketch_comparison,
    render_transfer_plan,
    request_final_critic,
    request_sketch_critic,
)
from investhome_api.services.creative_director.photo_occupancy_map import occupancy_to_json
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_62 = "phase6_2_real_photo_native_composition"
_HISTORY_KEYS = _H61R1 + (("concept3_r1_61_tests", "quality61r1"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_61r1(blob)
    preserved["quality61r1"] = list(blob.get("concept3_r1_61_tests") or [])
    return preserved


def _triple(a: Image.Image, b: Image.Image, c: Image.Image, title: str, captions: tuple[str, str, str]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), title, font=_font(18), fill=(201, 168, 92))
    for i, (image, cap) in enumerate(((a, captions[0]), (b, captions[1]), (c, captions[2]))):
        tile = image.copy()
        tile.thumbnail((580, 740), Image.Resampling.LANCZOS)
        x = 36 + i * 620
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 820), cap[:64], font=_font(14), fill=(226, 222, 214))
    return canvas


def build_native_spec(pack: dict[str, Any], crop: dict[str, Any], master_asset_id: str, field_asset_id: str) -> dict[str, Any]:
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
        "schema": "Phase62NativeMasterSpecV1",
        "spec_id": str(uuid4()),
        "parent_phase": "6.0 Concept 3 design language",
        "not_child_of": ["6.1", "6.1-R1"],
        "reconstruction_mode": NATIVE_MODE,
        "classified_as": None,
        "template_mode": None,
        "composition_name": pack.get("composition_name"),
        "sketch_id": pack.get("sketch_id"),
        "canvas": pack.get("canvas"),
        "project_photo": {"asset_id": DAY007_ASSET_ID, "filename": DAY007_FILENAME, "crop": crop, "z": 0, "bounds": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}},
        "graphic_field": {"semantic_role": "graphic_field", "asset_id": field_asset_id, "locked_raster": True, "z": 1, "kind": "day007_curved_editorial_aperture"},
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
        "engines": pack.get("engines"),
        "promoted": False,
    }


def generate_phase6_2_native_composition(
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
    logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    if logo_rgba is None:
        raise RuntimeError("Phase 6.2 requires the real Temple logo")
    fonts = build_font_registry()

    crops = choose_native_day007_crop(source)
    photo = crops["selected_image"]
    occupancy = crops["selected_occupancy"]
    mapped = build_real_photo_composition_map(photo, occupancy)
    plan = build_transfer_plan(mapped)

    sketches: dict[str, dict[str, Any]] = {}
    sketch_images: dict[str, Image.Image] = {}
    for key in ("A", "B", "C"):
        pack = compose_day007_native(
            photo,
            mapped=mapped,
            sketch_id=key,
            fonts=fonts,
            logo_rgba=logo_rgba,
            occupancy=occupancy,
            production=False,
        )
        sketches[key] = pack
        sketch_images[key] = pack["image"]

    critic, n = request_sketch_critic(concept, photo, sketch_images)
    vision_calls += n
    selected = critic["selected"]
    if selected not in sketches:
        raise RuntimeError("Phase 6.2 critic must select sketch A, B, or C")

    final_pack = compose_day007_native(
        photo,
        mapped=mapped,
        sketch_id=selected,
        fonts=fonts,
        logo_rgba=logo_rgba,
        occupancy=occupancy,
        production=True,
    )
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.2 forbids GPT Image production calls")

    field_only = final_pack["fielded"].copy()
    final_critic, n = request_final_critic(concept, photo, final_pack["image"])
    vision_calls += n
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.2 forbids GPT Image production calls")

    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(field_only),
        content_type="image/png",
        campaign_mode="project-v3-62-graphic-field",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 6.2 native Day_007 graphic field",
    )
    master_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(final_pack["image"]),
        content_type="image/png",
        campaign_mode="project-v3-62-native-master",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 6.2 Concept 3 language × real Day_007 — pending human review",
    )
    spec = build_native_spec(final_pack, crops["selected"]["transform"], str(master_asset.id), str(field_asset.id))
    readiness = family_revision_readiness(spec)
    readiness["executed"] = False
    provenance = architecture_provenance_qa(
        source=source,
        foundation=final_pack["foundation"],
        final=final_pack["image"],
        transform=crops["selected"]["transform"],
    )
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
        "generated_architecture": 0,
        "generated_logo": 0,
        "generated_text": 0,
        "pass": provenance.get("status") == "pass",
    }
    status = "NATIVE_COMPOSITION_PENDING_HUMAN_REVIEW"
    missed = list(final_critic.get("failed") or [])
    if readiness.get("revision_readiness") != "PASS":
        missed.append("revision_readiness")
    if not real_asset["pass"]:
        missed.append("real_asset_validation")

    critic_rows = []
    for key in ("A", "B", "C"):
        scores = ((critic.get("sketches") or {}).get(key) or {}).get("scores") or {}
        critic_rows.append(f"SKETCH {key}  selected={key == selected}")
        critic_rows.extend([f"  {k}: {v}" for k, v in scores.items()])
    critic_rows.append(f"SELECTED {selected}")
    critic_rows.append(str(critic.get("reason") or "")[:180])

    images = {
        "concept": concept,
        "photo": photo,
        "map": render_composition_map(photo, mapped, occupancy),
        "plan": render_transfer_plan(concept, photo, plan),
        "sketch_a": sketch_images["A"],
        "sketch_b": sketch_images["B"],
        "sketch_c": sketch_images["C"],
        "compare": render_sketch_comparison(concept, photo, sketch_images),
        "sketch_critic": _text_board("09  SKETCH CRITIC  —  one selected, not averaged", critic_rows, size=(1280, 1600)),
        "master": final_pack["image"],
        "vs_concept": _pair(concept, final_pack["image"], "11  CONCEPT 3 vs FINAL  —  campaign family, not pixel match", ("APPROVED CONCEPT 3", f"6.2 {selected} PRODUCTION")),
        "vs_photo": _pair(photo, final_pack["image"], "12  REAL PHOTO vs FINAL  —  Day_007 geometry is authoritative", ("REAL DAY_007", "6.2 NATIVE MASTER")),
        "final_critic": _score_board("13  FINAL VISUAL CRITIC  —  same campaign family?", final_critic.get("scores") or {}, FINAL_FLOORS),
        "revision": _text_board(
            "14  REVISION READINESS  —  static only, not executed",
            [f"{k}: {v}" for k, v in (readiness.get("checks") or {}).items()] + [f"overall {readiness.get('revision_readiness')}", "executed: NO"],
        ),
        "assets": _text_board(
            "15  REAL-ASSET VALIDATION",
            [
                f"Day_007 {DAY007_ASSET_ID} PASS",
                f"logo {LOCKED_LOGO_ASSET_ID} PASS",
                "generated architecture / logo / text = 0 / 0 / 0",
                f"architecture_fidelity {real_asset['architecture_fidelity']}",
            ],
        ),
        "review": _triple(
            concept,
            photo,
            final_pack["image"],
            f"16  HUMAN REVIEW BOARD  —  {status}",
            ("CONCEPT 3 LANGUAGE", "REAL DAY_007", f"SELECTED {selected} FINAL"),
        ),
    }
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_62,
        "created_at": _now(),
        "status": status,
        "approved_campaign_direction": "Concept 3",
        "concept3_asset_id": CONCEPT3_ASSET_ID,
        "real_photo": {"filename": DAY007_FILENAME, "asset_id": DAY007_ASSET_ID, "crop": crops["selected"]},
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "selected_sketch": selected,
        "sketch_scores": {k: (critic.get("sketches") or {}).get(k) for k in ("A", "B", "C")},
        "sketch_critic": critic,
        "candidate_asset_id": str(master_asset.id),
        "master_spec_id": spec["spec_id"],
        "graphic_field_asset_id": str(field_asset.id),
        "composition_name": final_pack.get("composition_name"),
        "reconstruction_mode": NATIVE_MODE,
        "final_visual_critic": final_critic,
        "revision_readiness": readiness,
        "real_asset_validation": real_asset,
        "real_photo_composition_map": {k: v for k, v in mapped.items() if k != "occupancy"},
        "occupancy": occupancy_to_json(occupancy),
        "creative_direction_transfer_plan": plan,
        "selected_master_spec": spec,
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
        "r1_created": False,
        "auto_polished": False,
        "next_decision": "HUMAN VISUAL REVIEW",
    }
    tests = list(blob.get("real_photo_native_62_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["real_photo_native_62_tests"] = tests
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
    blob["concept3_r1_61_tests"] = preserved.get("quality61r1")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.2 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
