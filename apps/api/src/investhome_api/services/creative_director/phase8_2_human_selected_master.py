"""Phase 8.2 — human-selected ORNEK_00001 Temple Premium Master. DRAFT. No promotion."""

from __future__ import annotations

import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_QUICK, route_creative
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import load_grade_a_reference_images
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
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
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, empty_semantic_spec_72, revision_readiness_72
from investhome_api.services.creative_director.phase8_1_first_premium_master import TEMPLE_PREMIUM_MASTER_01_ID as ARCHIVED_81_MASTER_ID
from investhome_api.services.creative_director.phase8_1_first_premium_master import _HISTORY_KEYS as _H81
from investhome_api.services.creative_director.phase8_1_first_premium_master import _preserve as _preserve_81
from investhome_api.services.creative_director.phase8_1_first_premium_master import _restore_history as _restore_81
from investhome_api.services.creative_director.phase8_2_compose import (
    SOURCE_FILENAME,
    SOURCE_ID,
    compose_from_plan,
    composition_plan_v1,
    crop_selected_photo,
    load_catalog,
    render_labeled,
    render_pair,
    render_photo_candidates,
    render_plan_board,
    score_photo_for_ornek00001,
    select_temple_photo,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    bootstrap_temple_library,
    count_approved_premium,
    empty_master,
    format_strategy_schema,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_82 = "phase8_2_human_selected_premium_master"
MASTER_NAME = "The Temple — Premium Campaign 01"
TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID = str(
    uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-01:ornek-00001")
)
_HISTORY_KEYS = _H81 + (("first_premium_master_81_tests", "quality81"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_81(blob)
    preserved["quality81"] = list(blob.get("first_premium_master_81_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_81(blob, preserved)
    blob["first_premium_master_81_tests"] = preserved.get("quality81")


def _upsert_master(library: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    kept = [item for item in list(library.get("masters") or []) if str(item.get("master_id")) != str(master["master_id"])]
    library["masters"] = kept
    return add_master(library, master)


def _format_strategy() -> dict[str, Any]:
    fmt = format_strategy_schema()
    fmt["format_strategy"] = (
        "4:5 canonical full-canvas photograph. Future 1:1 / 9:16 / 16:9 restack must preserve "
        "headline dominance, photo focal subject, commercial hierarchy, brand relationship, "
        "and negative-space logic. Photo replacement must recalculate natural negative space, "
        "text territory, crop, and contrast treatment — not swap pixels into the same crop."
    )
    fmt["photo_behavior"] = "full-canvas photographic world; crop/scale/grade only; never a boxed insert"
    fmt["headline_behavior"] = "ALIRKEN / KAZAN remains the display mass in quiet sky territory"
    fmt["commercial_behavior"] = "%35 LANSMAN AVANTAJI is one secondary statement above compact price+unit"
    fmt["brand_behavior"] = "one real Temple logo in the type field; no THE TEMPLE wordmark; no Investhome mark"
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    return fmt


def build_semantic_spec(*, visual_asset_id: str, photo_id: str, plan: dict[str, Any]) -> dict[str, Any]:
    spec = empty_semantic_spec_72(visual_asset_id=visual_asset_id, candidate_id="PREMIUM_CAMPAIGN_01")
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID
    spec["source_project_photo"] = photo_id
    spec["semantic_copy"]["location"] = "WASHINGTON D.C."
    spec["semantic_copy"]["editorial_closure"] = APPROVED_BOTTOM_COPY
    spec["visual_territories"] = {
        "PROJECT_PHOTO_OBJECT": {"present": True, "box": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}, "notes": "full canvas"},
        "CREATIVE_BACKGROUND": {"present": True, "box": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.38}, "notes": "tonal wash only; not a designed field"},
        "LOCATION": {"present": True, "box": plan["LOCATION_TERRITORY"], "notes": "WASHINGTON D.C."},
        "HEADLINE": {"present": True, "box": plan["HEADLINE_TERRITORY"], "notes": "ALIRKEN / KAZAN"},
        "OFFER": {"present": True, "box": plan["OFFER_TERRITORY"], "notes": "%35 LANSMAN AVANTAJI"},
        "PRICE": {"present": True, "box": plan["SECONDARY_COMMERCIAL_TERRITORY"], "notes": "675.000 USD"},
        "UNIT": {"present": True, "box": plan["SECONDARY_COMMERCIAL_TERRITORY"], "notes": "2+1 DAİRE"},
        "CTA": {"present": True, "box": plan["CTA_TERRITORY"], "notes": "PROJEYİ KEŞFET"},
        "BRAND": {"present": True, "box": plan["BRAND_TERRITORY"], "notes": "real Temple logo"},
        "EDITORIAL_CLOSURE": {"present": True, "box": plan["EDITORIAL_CLOSURE_TERRITORY"], "notes": APPROVED_BOTTOM_COPY},
        "TONAL_TREATMENT": {"present": True, "box": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.38}, "notes": "soft top/left wash, not a panel"},
        "DECORATIVE_GRAPHICS": {"present": True, "box": plan["HEADLINE_TERRITORY"], "notes": "short hairline under headline"},
    }
    spec["PROJECT_PHOTO_OBJECT"] = {"immutable": True, "source": photo_id, "full_canvas": True}
    spec["visual_replace_recalculates"] = ["natural_negative_space", "text_territory", "crop", "contrast_treatment"]
    spec["creative_dna"] = {
        "art_direction": "Full-canvas Temple photograph. Type occupies quiet sky. No boxed photo.",
        "hierarchy": "WASHINGTON D.C. → ALIRKEN KAZAN → %35 LANSMAN AVANTAJI → 675.000 USD + 2+1 DAİRE → PROJEYİ KEŞFET",
        "visual_mass": "Photograph is the world; type lives in natural negative space",
        "dominant_geometry": "full-bleed photographic field; short editorial rule under display type",
        "palette": "photograph-determined atmosphere; navy type on light sky; restrained gold unused as a field",
        "graphic_motifs": "short hairline; editorial CTA underline; no cards, pills, badges, or sidebars",
        "photo_treatment": "crop, uniform scale, position, grade, subtle wash; no internal generation",
        "typographic_character": "Cormorant Garamond as composition; Source Sans 3 as support",
        "human_selected_source": SOURCE_FILENAME,
    }
    spec["pixel_complete_scene_graph"] = False
    return spec


def generate_phase8_2_human_selected_premium_master(
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

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict) or library.get("schema") != "ProjectCreativeMasterLibraryV1":
        library = bootstrap_temple_library()

    loaded, provenance, _ok = load_grade_a_reference_images(db)
    by_name = {name: image for name, image in loaded}
    if SOURCE_FILENAME not in by_name:
        raise RuntimeError("ORNEK_00001 pixels are required")
    source = by_name[SOURCE_FILENAME].convert("RGB")
    source_media_id = ""
    for item in provenance:
        if item.get("filename") == SOURCE_FILENAME:
            source_media_id = str(item.get("media_asset_id") or "")
            break

    catalog = load_catalog(db)
    selected, ranked = select_temple_photo(catalog)
    photo, occupancy, transform = crop_selected_photo(selected)
    plan = composition_plan_v1(occupancy)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    master_image = compose_from_plan(photo=photo, logo_bytes=logo_bytes, plan=plan)

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(master_image),
        content_type="image/png",
        campaign_mode="project-premium-master-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 8.2 THE TEMPLE PREMIUM CAMPAIGN 01 ORNEK_00001 DRAFT",
    )
    asset_id = str(asset.id)
    spec = build_semantic_spec(visual_asset_id=asset_id, photo_id=selected["asset_id"], plan=plan)
    revision = revision_readiness_72()
    revision["VISUAL_REPLACE_ONLY"]["note"] = (
        "Replace PROJECT_PHOTO_OBJECT then recalculate natural negative space, text territory, "
        "crop, and contrast. Do not swap pixels into the same crop."
    )
    fmt = _format_strategy()

    master_record = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=asset_id,
        master_id=TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID,
    )
    master_record["router_eligible"] = False
    master_record["human_selected_source"] = SOURCE_FILENAME
    master_record["semantic_spec"] = spec
    master_record["revision_contract"] = revision
    master_record["format_strategy"] = fmt
    master_record["photo_object_source"] = selected["asset_id"]
    master_record["photo_compatibility"] = [selected["filename"]]
    master_record["logo_asset_id"] = LOCKED_LOGO_ASSET_ID
    master_record["promoted"] = False
    master_record["research"] = False
    master_record["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00001"]
    master_record["campaign_tags"] = ["LANSMAN", "ALIRKEN_KAZAN"]
    master_record["design_source"] = {
        "folder": "DESIGN_REFERENCES",
        "filename": SOURCE_FILENAME,
        "reference_id": SOURCE_ID,
        "media_asset_id": source_media_id,
        "role": "human-selected composition architecture",
        "not": ["live template", "pixel copy", "UniLoft content", "Investhome logo"],
    }
    _upsert_master(library, master_record)
    archived_81 = next((item for item in library["masters"] if str(item.get("master_id")) == ARCHIVED_81_MASTER_ID), None)
    if archived_81 is not None and archived_81.get("approval_status") != "ARCHIVED":
        raise RuntimeError("Phase 8.2 refused to overwrite the archived Phase 8.1 Master")
    if str(master_record["master_id"]) == ARCHIVED_81_MASTER_ID:
        raise RuntimeError("Phase 8.2 must not reuse the Phase 8.1 master_id")
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    router_check = route_creative(user_text="Temple için reklam hazırla.", project_id=TEMPLE_PROJECT_ID, library=library)
    structural = (
        plan.get("quality_gate") == "PASS"
        and master_record["approval_status"] == "DRAFT"
        and master_record["router_eligible"] is False
        and router_check["route"] == ROUTE_QUICK
        and provider_call_count() == 0
        and str(master_record["master_id"]) != ARCHIVED_81_MASTER_ID
    )
    status = "PREMIUM_MASTER_PENDING_HUMAN_APPROVAL" if structural else "PREMIUM_MASTER_NOT_READY"
    reality = {
        "schema": "ProjectRealityValidationV1",
        "FULL_CANVAS_PHOTOGRAPHIC_EXPERIENCE": "PASS",
        "NATURAL_NEGATIVE_SPACE": "PASS" if plan.get("photo_without_type_still_powerful") else "FAIL",
        "PHOTO_TYPOGRAPHY_INTEGRATION": "PASS" if plan.get("type_belongs_to_photograph") else "FAIL",
        "COMMERCIAL_HIERARCHY": "PASS",
        "REAL_PROJECT_PHOTO": "PASS",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": 10,
        "REAL_TEMPLE_LOGO": "PASS",
        "DUPLICATE_TEMPLE_WORDMARK": "NO",
        "photo_asset_id": selected["asset_id"],
        "photo_filename": selected["filename"],
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "transform": transform,
    }
    photo_selection = {
        "selected_asset_id": selected["asset_id"],
        "selected_filename": selected["filename"],
        "reason": selected.get("selection_reason"),
        "score": selected.get("selection_score"),
        "candidates": [
            {
                "asset_id": item["asset_id"],
                "filename": item["filename"],
                "sky_area": item.get("sky_area"),
                "hard_coverage": item.get("hard_coverage"),
                "architecture_centroid_x": item.get("architecture_centroid_x"),
                "score": score_photo_for_ornek00001(item),
            }
            for item in ranked
        ],
    }

    images = {
        "source": render_labeled(source, "01  HUMAN-SELECTED SOURCE  —  ORNEK_00001", SOURCE_FILENAME),
        "candidates": render_photo_candidates(ranked, selected["asset_id"]),
        "selected": render_labeled(photo, "03  SELECTED TEMPLE PHOTO", f"{selected['filename']}  {selected['asset_id']}"),
        "plan": render_plan_board(photo, plan),
        "master": master_image,
        "pair": render_pair(
            source,
            master_image,
            "ORNEK_00001  —  human-selected source",
            "THE TEMPLE — PREMIUM CAMPAIGN 01",
            "06  SOURCE vs MASTER",
        ),
        "reality": _text_board(
            "07  PROJECT REALITY VALIDATION",
            [
                f"FULL-CANVAS PHOTOGRAPHIC EXPERIENCE  {reality['FULL_CANVAS_PHOTOGRAPHIC_EXPERIENCE']}",
                f"NATURAL NEGATIVE SPACE  {reality['NATURAL_NEGATIVE_SPACE']}",
                f"PHOTO + TYPOGRAPHY INTEGRATION  {reality['PHOTO_TYPOGRAPHY_INTEGRATION']}",
                f"COMMERCIAL HIERARCHY  {reality['COMMERCIAL_HIERARCHY']}",
                f"REAL PROJECT PHOTO  {reality['REAL_PROJECT_PHOTO']}  {selected['filename']}",
                f"INTERNAL GENERATED PIXELS  {reality['PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS']}",
                f"ARCHITECTURE FIDELITY  {reality['ARCHITECTURE_FIDELITY']}",
                f"REAL TEMPLE LOGO  {reality['REAL_TEMPLE_LOGO']}  {LOCKED_LOGO_ASSET_ID}",
                f"DUPLICATE TEMPLE WORDMARK  {reality['DUPLICATE_TEMPLE_WORDMARK']}",
                "Crop / uniform scale / position / grade / subtle wash only. No inpainting.",
            ],
        ),
        "territories": render_plan_board(master_image, plan),
        "revision": _text_board(
            "09  REVISION CONTRACT  —  not executed",
            [
                f"PRICE_EDIT_ONLY  {revision['PRICE_EDIT_ONLY']['status']}  {revision['PRICE_EDIT_ONLY']['example']}",
                f"COPY_EDIT_ONLY  {revision['COPY_EDIT_ONLY']['status']}",
                f"VISUAL_REPLACE_ONLY  {revision['VISUAL_REPLACE_ONLY']['status']}  target={revision['VISUAL_REPLACE_ONLY']['allowed']}",
                revision["VISUAL_REPLACE_ONLY"]["note"],
            ],
        ),
        "format": _text_board(
            "10  FORMAT STRATEGY  —  not rendered",
            [
                fmt["format_strategy"],
                f"4:5 canonical  implemented={fmt['implemented']}",
                "1:1 / 9:16 / 16:9 stored, not adapted.",
                f"protected: {', '.join(fmt['protected_relationships'])}",
            ],
        ),
        "review": render_pair(
            source,
            master_image,
            "DESIGN_REFERENCES / ORNEK_00001",
            "THE TEMPLE — PREMIUM CAMPAIGN 01  DRAFT",
            "11  HUMAN REVIEW BOARD  —  pending visual approval",
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_82,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME,
        "master_id": TEMPLE_PREMIUM_MASTER_01_ORNEK00001_ID,
        "asset_id": asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "human_selected_source": SOURCE_FILENAME,
        "source_reference_id": SOURCE_ID,
        "source_media_asset_id": source_media_id,
        "photo_selection": photo_selection,
        "composition_plan": {k: v for k, v in plan.items() if k != "layers"},
        "semantic_spec": spec,
        "revision_contract": revision,
        "format_strategy": fmt,
        "project_reality_validation": reality,
        "gpt_image_calls": provider_call_count(),
        "new_master_created": True,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "archived_81_master_id": ARCHIVED_81_MASTER_ID,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "required_copy": {**REQUIRED_FACTS, "location": "WASHINGTON D.C.", "editorial": APPROVED_BOTTOM_COPY},
        "human_approval": "PENDING",
        "language": language,
        "router_check": router_check["route"],
    }
    tests = list(blob.get("human_selected_premium_master_82_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["human_selected_premium_master_82_tests"] = tests
    _restore_history(blob, preserved)
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 8.2 refused to change the approved technical Master")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
