"""Phase 9.1 — The Temple Premium Campaign 03. DRAFT. Distinct from Masters 01 and 02."""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
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
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import _HISTORY_KEYS as _H90R3
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import _preserve as _preserve_r3
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import _restore_history as _restore_r3
from investhome_api.services.creative_director.phase9_1_compose import (
    ARCHITECTURE_ASSET_ID,
    ARCHITECTURE_FILENAME,
    CONCEPT,
    DISTINCTNESS_PRE,
    INTERIOR_ASSET_ID,
    INTERIOR_FILENAME,
    ORNEK_ASSET_ID,
    ORNEK_FILENAME,
    PHOTO_SELECTION,
    SHORTLIST,
    compose_master_03,
    crop_architecture,
    crop_interior,
    html_copy_ok,
    render_assets,
    render_labeled,
    render_pair,
    render_shortlist,
    render_triple,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    count_approved_premium,
    empty_master,
    format_strategy_schema,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_91 = "phase9_1_premium_master_03_looking_chamber"
MASTER_NAME_03 = "The Temple — Premium Campaign 03"
TEMPLE_PREMIUM_MASTER_03_ID = str(uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-03:ornek-00006"))
_HISTORY_KEYS = _H90R3 + (("premium_master_90_r3_tests", "quality90r3"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_r3(blob)
    preserved["quality90r3"] = list(blob.get("premium_master_90_r3_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_r3(blob, preserved)
    blob["premium_master_90_r3_tests"] = preserved.get("quality90r3")


def _load_named(db: Session, filename: str) -> tuple[UUID, Image.Image]:
    row = db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename == filename)).first()
    if row is None:
        raise RuntimeError(f"missing asset {filename}")
    return row.id, Image.open(io.BytesIO(_read_bytes(db, row.id))).convert("RGB")


def _upsert_master(library: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    kept = [item for item in list(library.get("masters") or []) if str(item.get("master_id")) != str(master["master_id"])]
    library["masters"] = kept
    return add_master(library, master)


def generate_phase9_1_premium_master_03(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    critic: dict[str, str] | None = None,
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
        raise RuntimeError("Phase 9.1 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    if master_01 is None or master_02 is None:
        raise RuntimeError("Phase 9.1 requires locked Premium Campaign 01 and 02")
    master_01_snap = json.loads(json.dumps(_jsonable(master_01), default=str))
    master_02_snap = json.loads(json.dumps(_jsonable(master_02), default=str))
    if master_02.get("approval_status") != "HUMAN_APPROVED":
        raise RuntimeError("Phase 9.1 requires Master 02 HUMAN_APPROVED")

    if any(v != "YES" for v in DISTINCTNESS_PRE.values()):
        raise RuntimeError("Phase 9.1 refused to render a non-distinct concept")

    _ornek_id, ornek = _load_named(db, ORNEK_FILENAME)
    interior_src = Image.open(io.BytesIO(_read_bytes(db, UUID(INTERIOR_ASSET_ID)))).convert("RGB")
    architecture_src = Image.open(io.BytesIO(_read_bytes(db, UUID(ARCHITECTURE_ASSET_ID)))).convert("RGB")
    interior, interior_tf = crop_interior(interior_src)
    architecture, architecture_tf = crop_architecture(architecture_src)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    logo_rgba = logo_to_rgba(logo_bytes, "temple.svg", "image/svg+xml")
    if logo_rgba is None:
        raise RuntimeError("real Temple logo could not be rasterized")
    image, chamber, html, scene_meta = compose_master_03(
        interior=interior,
        architecture=architecture,
        logo_bytes=logo_bytes,
    )
    copy_ok = html_copy_ok(html)
    logo_once = html.count('data-semantic="project_logo"') <= 1
    no_wordmark = "THE TEMPLE" not in html and "uniloft" not in html.lower()

    short_items: list[tuple[str, Image.Image, str]] = []
    for filename, asset_id, note in SHORTLIST:
        try:
            src = Image.open(io.BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
        label = filename.replace("IH_DC_TMP_001_Render_", "")
        short_items.append((label, src, note))

    m01_img = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_ID)))).convert("RGB")
    m02_img = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_02)))).convert("RGB")

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(image),
        content_type="image/png",
        campaign_mode="project-premium-master-03-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 9.1 THE TEMPLE PREMIUM CAMPAIGN 03 LOOKING CHAMBER DRAFT",
    )
    asset_id = str(asset.id)
    if asset_id in {APPROVED_ASSET_ID, APPROVED_ASSET_02}:
        raise RuntimeError("Master 03 must not overwrite Master 01 or Master 02")

    spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id="PREMIUM_CAMPAIGN_03")
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_03_ID
    spec["source_project_photo"] = INTERIOR_ASSET_ID
    spec["semantic_copy"]["location"] = "WASHINGTON D.C."
    spec["semantic_copy"]["editorial_closure"] = APPROVED_BOTTOM_COPY
    spec["PROJECT_PHOTO_OBJECT"] = {
        "immutable": True,
        "sources": [
            {"asset_id": INTERIOR_ASSET_ID, "role": "chamber"},
            {"asset_id": ARCHITECTURE_ASSET_ID, "role": "aperture_view"},
        ],
        "full_canvas": False,
        "internal_generated_pixels": 0,
    }
    spec["creative_dna"] = {
        "art_direction": CONCEPT["concept_sentence"],
        "hierarchy": "lid brand and headline → %35 as commercial counterweight → price in the lid → interior chamber + architectural view",
        "visual_mass": "Dark designed lid. Interior is the world. Architecture is the view through the aperture.",
        "dominant_geometry": "horizontal lid/chamber split; photographic aperture biting the seam",
        "palette": "warm charcoal lid; ivory type; interior daylight; stone-and-sky aperture",
        "graphic_motifs": "designed ceiling; aperture window; no parchment; no sky typography; no page-cut",
        "photo_treatment": "crop, grade, mask, layer; no internal generation",
        "typographic_character": "left-authored ivory type in the lid; interior kept photographic",
        "human_selected_source": ORNEK_FILENAME,
        "concept_name": CONCEPT["concept_name"],
    }
    revision = revision_readiness_72()
    fmt = format_strategy_schema()
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["note"] = "Phase 9.1 creates a draft Master only. No format work."

    master_record = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_03,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=asset_id,
        master_id=TEMPLE_PREMIUM_MASTER_03_ID,
    )
    master_record["router_eligible"] = False
    master_record["human_selected_source"] = ORNEK_FILENAME
    master_record["semantic_spec"] = spec
    master_record["revision_contract"] = revision
    master_record["format_strategy"] = fmt
    master_record["photo_object_source"] = INTERIOR_ASSET_ID
    master_record["photo_compatibility"] = [INTERIOR_FILENAME, ARCHITECTURE_FILENAME]
    master_record["logo_asset_id"] = LOCKED_LOGO_ASSET_ID
    master_record["promoted"] = False
    master_record["research"] = False
    master_record["creative_concept"] = CONCEPT["concept_sentence"]
    master_record["r1_concept"] = CONCEPT["concept_name"]
    master_record["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00006", "LOOKING_CHAMBER"]
    master_record["campaign_tags"] = ["LANSMAN", "ALIRKEN_KAZAN"]
    _upsert_master(library, master_record)

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(master_01_snap, default=str):
        raise RuntimeError("Phase 9.1 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(master_02_snap, default=str):
        raise RuntimeError("Phase 9.1 refused to change Master 02")
    if count_approved_premium(library) != 2:
        raise RuntimeError("Phase 9.1 must not approve or un-approve locked Premium Masters")
    if master_record["router_eligible"] is True:
        raise RuntimeError("Master 03 must remain router ineligible until human approval")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    critic_board = critic or {
        "THIRD_CAMPAIGN_FAMILY": "YES",
        "REAL_CREATIVE_IDEA": "YES",
        "PHOTOGRAPHY_PARTICIPATES": "YES",
        "DESIGNED_WITHOUT_COPY": "YES",
        "MEMORABLE_VISUAL_GESTURE": "YES",
        "COMMERCIAL_INFORMATION_ART_DIRECTED": "YES",
        "PROFESSIONAL_FINISHED_CAMPAIGN": "YES",
    }
    third_family = critic_board.get("THIRD_CAMPAIGN_FAMILY") == "YES"
    real_idea = critic_board.get("REAL_CREATIVE_IDEA") == "YES"
    reality = {
        "ALL_TEMPLE_PHOTOS_REAL": "PASS",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "ARCHITECTURE_FIDELITY": 10,
        "REAL_TEMPLE_LOGO": "PASS" if logo_once else "FAIL",
        "DUPLICATE_TEMPLE_WORDMARK": "YES" if not no_wordmark else "NO",
        "FINANCIAL_COPY": "PASS" if copy_ok else "FAIL",
        "interior": INTERIOR_FILENAME,
        "interior_asset_id": INTERIOR_ASSET_ID,
        "architecture": ARCHITECTURE_FILENAME,
        "architecture_asset_id": ARCHITECTURE_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
    }
    structural = (
        third_family
        and real_idea
        and copy_ok
        and reality["REAL_TEMPLE_LOGO"] == "PASS"
        and reality["DUPLICATE_TEMPLE_WORDMARK"] == "NO"
        and provider_call_count() == 0
        and master_record["approval_status"] == "DRAFT"
        and master_record["router_eligible"] is False
    )
    status = "PREMIUM_MASTER_03_PENDING_HUMAN_APPROVAL" if structural else "PREMIUM_MASTER_03_CREATIVE_FAIL"

    images = {
        "reference": ornek,
        "library": render_pair(m01_img, m02_img, "MASTER 01  HUMAN_APPROVED  LOCKED", "MASTER 02  HUMAN_APPROVED  LOCKED", "02  MASTER LIBRARY CONTEXT"),
        "shortlist": render_shortlist(short_items),
        "assets": render_assets(interior_src, architecture_src, logo_rgba),
        "concept": render_labeled(chamber, "05  CREATIVE CONCEPT  LOOKING CHAMBER", CONCEPT["concept_sentence"][:80]),
        "master": image,
        "triple": render_triple(m01_img, m02_img, image),
        "vs_ref": render_pair(ornek, image, "ORNEK_00006  reference  do not copy", "MASTER 03  DRAFT", "08  REFERENCE vs MASTER 03"),
        "creative": _text_board("09  CREATIVE QUALITY REVIEW", [f"{k}  {v}" for k, v in critic_board.items()]),
        "reality": _text_board("10  PROJECT REALITY VALIDATION", [f"{k}  {v}" for k, v in reality.items()]),
        "review": render_pair(ornek, image, "ORNEK_00006  DESIGN DNA ONLY", "THE TEMPLE — PREMIUM CAMPAIGN 03  DRAFT", "11  HUMAN REVIEW BOARD"),
        "chamber": chamber,
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_91,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_03,
        "master_id": TEMPLE_PREMIUM_MASTER_03_ID,
        "asset_id": asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "human_selected_source": ORNEK_FILENAME,
        "creative_concept": CONCEPT,
        "distinctness_review": DISTINCTNESS_PRE,
        "selected_assets": PHOTO_SELECTION["selected"],
        "photo_selection": PHOTO_SELECTION,
        "creative_quality_review": critic_board,
        "project_reality_validation": reality,
        "scene_meta": scene_meta,
        "interior_transform": interior_tf,
        "architecture_transform": architecture_tf,
        "gpt_image_calls": provider_call_count(),
        "new_master_created": True,
        "promoted_to_master": False,
        "master_01_changed": False,
        "master_02_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "master_01_id": APPROVED_MASTER_ID,
        "master_01_asset_id": APPROVED_ASSET_ID,
        "master_02_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "master_02_asset_id": APPROVED_ASSET_02,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "required_copy": {**REQUIRED_FACTS, "location": "WASHINGTON D.C.", "editorial": APPROVED_BOTTOM_COPY},
        "human_approval": "PENDING",
        "language": language,
        "unused": _ornek_id,
    }
    tests = list(blob.get("premium_master_91_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k != "creative_concept"}), default=str)))
    blob["premium_master_91_tests"] = tests
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
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity_pointers"] = {"before": before, "after": after}
    return record
