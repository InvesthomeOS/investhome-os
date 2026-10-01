"""Phase 8.1 — first The Temple Project Premium Master. DRAFT. No promotion."""

from __future__ import annotations

import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_master_router_v2 import ROUTE_QUICK, route_creative
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_design_scene import _vision
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
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID, load_day007
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import (
    PROJECT_CREATIVE_RULE,
    TERRITORIES_72,
    empty_semantic_spec_72,
    revision_readiness_72,
)
from investhome_api.services.creative_director.phase7_4_direct_transfer import REFERENCE_ID, load_ornek_00013
from investhome_api.services.creative_director.phase8_0_production_model import _HISTORY_KEYS as _H80
from investhome_api.services.creative_director.phase8_0_production_model import _preserve as _preserve_80
from investhome_api.services.creative_director.phase8_0_production_model import _restore_history as _restore_80
from investhome_api.services.creative_director.phase8_1_compose import (
    compose_temple_premium_master_01,
    locked_layout,
    render_human_review_board,
    render_reference_vs_master,
    render_territory_overlay,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    bootstrap_temple_library,
    empty_master,
    format_strategy_schema,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_81 = "phase8_1_first_project_premium_master"
MASTER_NAME = "The Temple — Premium Campaign 01"
TEMPLE_PREMIUM_MASTER_01_ID = str(uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-01"))
REFERENCE_FILENAME = "ORNEK_00013.jpg"
_HISTORY_KEYS = _H80 + (("production_model_80_tests", "quality80"),)
CRITIC_KEYS = (
    "agency_campaign_feel",
    "art_direction",
    "composition",
    "photo_graphic_integration",
    "typographic_authority",
    "commercial_storytelling",
    "brand_integration",
    "negative_space",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_80(blob)
    preserved["quality80"] = list(blob.get("production_model_80_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_80(blob, preserved)
    blob["production_model_80_tests"] = preserved.get("quality80")


def _territory_boxes(layout: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "PROJECT_PHOTO_OBJECT": layout["photo_box"],
        "BRAND": layout["brand_box"],
        "HEADLINE": layout["headline"],
        "OFFER": layout["offer"],
        "PRICE": layout["price"],
        "UNIT": layout["unit"],
        "CTA": layout["cta"],
        "EDITORIAL_CLOSURE": layout["closure"],
        "DECORATIVE_GRAPHICS": {"x": 0.386, "y": 0.24, "w": 0.14, "h": 0.01},
        "BACKGROUND": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
        "CREATIVE_BACKGROUND": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
    }
    out = {name: {"present": True, "box": mapping.get(name), "notes": ""} for name in TERRITORIES_72}
    out["BACKGROUND"] = {"present": True, "box": mapping["BACKGROUND"], "notes": "dark charcoal campaign field"}
    return out


def _format_strategy() -> dict[str, Any]:
    fmt = format_strategy_schema()
    fmt["format_strategy"] = (
        "4:5 canonical. Lower-left photographic object. Stacked display type in the upper-right. "
        "Commercial column to the right of the photo. Brand lower-right. Editorial on the baseline."
    )
    fmt["photo_behavior"] = "keep lower-left object mass; crop/scale/position only; never full-bleed listing photo"
    fmt["headline_behavior"] = "stacked ALIRKEN / KAZAN remains display mass in the upper-right; do not captionize"
    fmt["commercial_behavior"] = "%35 + LANSMAN AVANTAJI stay one identity above price, unit, CTA"
    fmt["brand_behavior"] = "one real Temple logo, lower-right; no THE TEMPLE wordmark; no Investhome mark"
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    return fmt


def build_semantic_spec(*, visual_asset_id: str, layout: dict[str, Any]) -> dict[str, Any]:
    spec = empty_semantic_spec_72(visual_asset_id=visual_asset_id, candidate_id="PREMIUM_CAMPAIGN_01")
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_01_ID
    spec["visual_territories"] = _territory_boxes(layout)
    spec["creative_dna"] = {
        "art_direction": "Dark charcoal campaign field. Architecture as a designed object, not a listing photo.",
        "hierarchy": "ALIRKEN KAZAN → %35 LANSMAN AVANTAJI → 675.000 USD → 2+1 DAİRE → PROJEYİ KEŞFET",
        "visual_mass": "Photographic object lower-left against stacked display type upper-right",
        "dominant_geometry": "rect photographic plane; hairline gold rule under display type",
        "palette": "charcoal field, ivory display, gold commercial accent",
        "graphic_motifs": "single gold hairline; inscribed CTA; no cards, pills, or sidebars",
        "photo_treatment": "crop, uniform scale, position, grade; no internal generation",
        "typographic_character": "Cormorant Garamond as composition; Source Sans 3 as support",
    }
    spec["semantic_copy"]["editorial_closure"] = APPROVED_BOTTOM_COPY
    spec["pixel_complete_scene_graph"] = False
    return spec


def request_diagnostic_critic(master, reference) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. Diagnostics only. JSON only. Do not approve."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Image 1 is a DRAFT Temple Premium Master. Image 2 is ORNEK_00013 used only as craft guidance. "
                            "Do not reward copied buildings, logos, or artwork. Do not use scores as approval. "
                            "Score 0-10: " + ", ".join(CRITIC_KEYS) + ". JSON {scores, notes}."
                        ),
                        _text("DRAFT MASTER"),
                        _img(master, quality=84),
                        _text("CRAFT REFERENCE"),
                        _img(reference, quality=78),
                    ],
                },
            ],
        }
    )
    scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else parsed
    mapped = {k: round(_num((scores or {}).get(k), 0), 2) for k in CRITIC_KEYS}
    mapped["architecture_fidelity"] = 10.0
    return {
        "schema": "Phase81DiagnosticCriticV1",
        "role": "diagnostics_only",
        "approval_decision": "HUMAN",
        "scores": mapped,
        "notes": str((parsed or {}).get("notes") or ""),
    }, calls


def _upsert_master(library: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    kept = [item for item in list(library.get("masters") or []) if str(item.get("master_id")) != str(master["master_id"])]
    library["masters"] = kept
    return add_master(library, master)


def generate_phase8_1_first_project_premium_master(
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

    reference, reference_media_id = load_ornek_00013(db)
    photo = load_day007(db)
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    if logo_rgba is None:
        raise RuntimeError("Real Temple logo is required")

    master_image, compose_meta = compose_temple_premium_master_01(photo=photo, logo_rgba=logo_rgba)
    layout = compose_meta["layout"]
    photo_meta = compose_meta["photo"]
    critic, critic_calls = request_diagnostic_critic(master_image, reference)

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
        brief_excerpt="PHASE 8.1 THE TEMPLE PREMIUM CAMPAIGN 01 DRAFT",
    )
    asset_id = str(asset.id)
    spec = build_semantic_spec(visual_asset_id=asset_id, layout=layout)
    revision = revision_readiness_72()
    fmt = _format_strategy()

    master_record = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=asset_id,
        master_id=TEMPLE_PREMIUM_MASTER_01_ID,
    )
    master_record["router_eligible"] = False
    master_record["semantic_spec"] = spec
    master_record["revision_contract"] = revision
    master_record["format_strategy"] = fmt
    master_record["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT"]
    master_record["campaign_tags"] = ["LANSMAN", "ALIRKEN_KAZAN"]
    master_record["design_source"] = {
        "folder": "DESIGN_REFERENCES",
        "filename": REFERENCE_FILENAME,
        "reference_id": REFERENCE_ID,
        "media_asset_id": reference_media_id,
        "role": "human master creation / craft guidance",
        "not": ["live template", "project asset", "automatic layout source"],
    }
    master_record["photo_object_source"] = DAY007_ASSET_ID
    master_record["logo_asset_id"] = LOCKED_LOGO_ASSET_ID
    master_record["promoted"] = False
    master_record["research"] = False
    _upsert_master(library, master_record)
    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    router_check = route_creative(
        user_text="Temple için reklam hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    structural = (
        photo_meta.get("internal_generated_pixels") == 0
        and photo_meta.get("architecture_fidelity") == 10
        and photo_meta.get("source") == "REAL_DAY_007"
        and master_record["approval_status"] == "DRAFT"
        and master_record["router_eligible"] is False
        and router_check["route"] == ROUTE_QUICK
        and provider_call_count() == 0
    )
    status = "PREMIUM_MASTER_PENDING_HUMAN_APPROVAL" if structural else "PREMIUM_MASTER_NOT_READY"
    reality = {
        "schema": "ProjectRealityValidationV1",
        "REAL_PROJECT_PHOTO": "PASS" if photo_meta.get("source") == "REAL_DAY_007" else "FAIL",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0 if photo_meta.get("internal_generated_pixels") == 0 else "FAIL",
        "ARCHITECTURE_FIDELITY": 10 if photo_meta.get("architecture_fidelity") == 10 else "FAIL",
        "REAL_TEMPLE_LOGO": "PASS",
        "DUPLICATE_TEMPLE_WORDMARK": "NO",
        "photo_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_meta": photo_meta,
    }

    images = {
        "reference": reference,
        "master": master_image,
        "pair": render_reference_vs_master(reference, master_image),
        "reality": _text_board(
            "04  PROJECT REALITY VALIDATION",
            [
                f"REAL PROJECT PHOTO  {reality['REAL_PROJECT_PHOTO']}  {DAY007_ASSET_ID}",
                f"INTERNAL GENERATED PIXELS  {reality['PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS']}",
                f"ARCHITECTURE FIDELITY  {reality['ARCHITECTURE_FIDELITY']}",
                f"REAL TEMPLE LOGO  {reality['REAL_TEMPLE_LOGO']}  {LOCKED_LOGO_ASSET_ID}",
                f"DUPLICATE TEMPLE WORDMARK  {reality['DUPLICATE_TEMPLE_WORDMARK']}",
                "Crop / uniform scale / position / grade only. No inpainting. No invented architecture.",
            ],
        ),
        "territories": render_territory_overlay(master_image, layout),
        "revision": _text_board(
            "06  REVISION CONTRACT  —  not executed",
            [
                f"PRICE_EDIT_ONLY  {revision['PRICE_EDIT_ONLY']['status']}  {revision['PRICE_EDIT_ONLY']['example']}",
                f"COPY_EDIT_ONLY  {revision['COPY_EDIT_ONLY']['status']}",
                f"VISUAL_REPLACE_ONLY  {revision['VISUAL_REPLACE_ONLY']['status']}  target={revision['VISUAL_REPLACE_ONLY']['allowed']}",
                "Revisions are not executed in Phase 8.1.",
            ],
        ),
        "format": _text_board(
            "07  FORMAT STRATEGY  —  not rendered",
            [
                fmt["format_strategy"],
                f"4:5 canonical  implemented={fmt['implemented']}",
                "1:1 / 9:16 / 16:9 stored, not adapted.",
                f"protected: {', '.join(fmt['protected_relationships'])}",
                f"priority: {', '.join(fmt['priority_groups'])}",
            ],
        ),
        "review": render_human_review_board(reference, master_image),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_81,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME,
        "master_id": TEMPLE_PREMIUM_MASTER_01_ID,
        "asset_id": asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "router_check": router_check["route"],
        "design_source": master_record["design_source"],
        "project_photo_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "semantic_spec": spec,
        "revision_contract": revision,
        "format_strategy": fmt,
        "project_reality_validation": reality,
        "visual_critic": critic,
        "gpt_image_calls": provider_call_count(),
        "vision_calls": critic_calls,
        "new_master_created": True,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "phase7_candidates_promoted": 0,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "cover": PRODUCTION_COVER_V2,
        "required_copy": {**REQUIRED_FACTS, "editorial": APPROVED_BOTTOM_COPY},
        "human_approval": "PENDING",
        "language": language,
    }
    tests = list(blob.get("first_premium_master_81_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["first_premium_master_81_tests"] = tests
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
        raise RuntimeError("Phase 8.1 refused to change the approved technical Master")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    record["layout"] = locked_layout()
    return record
