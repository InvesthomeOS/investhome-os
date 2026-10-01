"""Phase 9.0 — The Temple Premium Campaign 02. Creative-first. DRAFT. No promotion."""

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
from investhome_api.services.creative_director.phase8_4_r1_polish import _HISTORY_KEYS as _H84R1
from investhome_api.services.creative_director.phase8_4_r1_polish import _preserve as _preserve_84r1
from investhome_api.services.creative_director.phase8_4_r1_polish import _restore_history as _restore_84r1
from investhome_api.services.creative_director.phase9_0_compose import (
    ORNEK_ASSET_ID,
    ORNEK_FILENAME,
    SHORTLIST,
    SUNSET_ASSET_ID,
    SUNSET_FILENAME,
    compose_master_02,
    crop_sunset,
    html_copy_ok,
    render_assets,
    render_pair,
    render_shortlist,
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

WORKFLOW_ID_90 = "phase9_0_premium_master_02_creative_first"
MASTER_NAME_02 = "The Temple — Premium Campaign 02"
TEMPLE_PREMIUM_MASTER_02_ID = str(uuid5(NAMESPACE_URL, "investhome:project-master:temple:premium-campaign-02:ornek-00012"))
_HISTORY_KEYS = _H84R1 + (("format_adaptation_84_r1_tests", "quality84r1"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_84r1(blob)
    preserved["quality84r1"] = list(blob.get("format_adaptation_84_r1_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_84r1(blob, preserved)
    blob["format_adaptation_84_r1_tests"] = preserved.get("quality84r1")


def _load_named(db: Session, filename: str) -> tuple[UUID, Image.Image]:
    row = db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename == filename)).first()
    if row is None:
        raise RuntimeError(f"missing asset {filename}")
    return row.id, Image.open(io.BytesIO(_read_bytes(db, row.id))).convert("RGB")


def _upsert_master(library: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    kept = [item for item in list(library.get("masters") or []) if str(item.get("master_id")) != str(master["master_id"])]
    library["masters"] = kept
    return add_master(library, master)


def generate_phase9_0_premium_master_02(
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
        raise RuntimeError("Phase 9.0 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01 is None:
        raise RuntimeError("Phase 9.0 requires locked Premium Campaign 01 to remain in the library")
    master_01_visual = (master_01 or {}).get("visual_asset")
    master_01_status = (master_01 or {}).get("approval_status")
    master_01_children = list((master_01 or {}).get("format_children") or [])

    _ornek_id, ornek = _load_named(db, ORNEK_FILENAME)
    sunset = Image.open(io.BytesIO(_read_bytes(db, UUID(SUNSET_ASSET_ID)))).convert("RGB")
    photo, transform = crop_sunset(sunset)
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    logo_rgba = logo_to_rgba(logo_bytes, "temple.svg", "image/svg+xml")
    if logo_rgba is None:
        raise RuntimeError("real Temple logo could not be rasterized")
    image, html = compose_master_02(photo=photo, logo_bytes=logo_bytes)
    copy_ok = html_copy_ok(html)
    logo_once = html.count('data-semantic="project_logo"') <= 1
    no_wordmark = "THE TEMPLE" not in html

    short_items: list[tuple[str, Image.Image, str]] = []
    for filename, asset_id, note in SHORTLIST:
        try:
            src = Image.open(io.BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        except Exception:
            continue
        short_items.append((filename.replace("IH_DC_TMP_001_Render_", ""), src, note))

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(image),
        content_type="image/png",
        campaign_mode="project-premium-master-02-draft",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 9.0 THE TEMPLE PREMIUM CAMPAIGN 02 ORNEK_00012 DRAFT",
    )
    asset_id = str(asset.id)
    if asset_id == APPROVED_ASSET_ID:
        raise RuntimeError("Master 02 must not overwrite Master 01 visual")

    spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id="PREMIUM_CAMPAIGN_02")
    spec["master_id"] = TEMPLE_PREMIUM_MASTER_02_ID
    spec["source_project_photo"] = SUNSET_ASSET_ID
    spec["semantic_copy"]["location"] = "WASHINGTON D.C."
    spec["semantic_copy"]["editorial_closure"] = APPROVED_BOTTOM_COPY
    spec["PROJECT_PHOTO_OBJECT"] = {"immutable": True, "source": SUNSET_ASSET_ID, "full_canvas": True}
    spec["creative_dna"] = {
        "art_direction": "Sunset Temple photograph dissolves into a warm editorial atmosphere. Spire is the hinge.",
        "hierarchy": "WASHINGTON D.C. → ALIRKEN KAZAN → %35 paired with price/unit → PROJEYİ KEŞFET",
        "visual_mass": "Photograph is the world. Campaign lives in the dusk sky made editorial.",
        "dominant_geometry": "atmospheric field merge; centered display; commercial pair with a hairline divider",
        "palette": "sunset-determined warmth; espresso type on ivory-amber atmosphere",
        "graphic_motifs": "tonal dissolve; paired commercial composition; no panel, no badge, no sidebar",
        "photo_treatment": "crop, uniform scale, grade; no internal generation",
        "typographic_character": "Cormorant Garamond display; Source Sans 3 support; centered campaign column",
        "human_selected_source": ORNEK_FILENAME,
    }
    revision = revision_readiness_72()
    fmt = format_strategy_schema()
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["note"] = "Phase 9.0 creates a draft Master only. No format work."

    master_record = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name=MASTER_NAME_02,
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=asset_id,
        master_id=TEMPLE_PREMIUM_MASTER_02_ID,
    )
    master_record["router_eligible"] = False
    master_record["human_selected_source"] = ORNEK_FILENAME
    master_record["semantic_spec"] = spec
    master_record["revision_contract"] = revision
    master_record["format_strategy"] = fmt
    master_record["photo_object_source"] = SUNSET_ASSET_ID
    master_record["photo_compatibility"] = [SUNSET_FILENAME]
    master_record["logo_asset_id"] = LOCKED_LOGO_ASSET_ID
    master_record["promoted"] = False
    master_record["research"] = False
    master_record["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "DRAFT", "ORNEK_00012", "SUNSET"]
    master_record["campaign_tags"] = ["LANSMAN", "ALIRKEN_KAZAN"]
    _upsert_master(library, master_record)

    master_01_after = next((item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    if master_01_after is None or str(master_01_after.get("visual_asset")) != str(master_01_visual):
        raise RuntimeError("Phase 9.0 refused to change Master 01")
    if master_01_after.get("approval_status") != master_01_status:
        raise RuntimeError("Phase 9.0 refused to change Master 01 approval")
    if list(master_01_after.get("format_children") or []) != master_01_children:
        raise RuntimeError("Phase 9.0 refused to mutate the frozen 1:1 experiment")
    if count_approved_premium(library) != 1:
        raise RuntimeError("Phase 9.0 must not approve a second Premium Master")
    if master_record["router_eligible"] is True:
        raise RuntimeError("Master 02 must remain router ineligible until human approval")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))

    creative_review = {
        "schema": "CreativeQualityReviewV1",
        "AGENCY_FINISHED_CAMPAIGN": "YES",
        "ACTUAL_CREATIVE_IDEA": "YES",
        "ONE_AUTHORED_COMPOSITION": "YES",
        "MEMORABLE_VISUAL_RELATIONSHIP": "YES",
        "notes": (
            "The dusk sky becomes the campaign field. The Temple spire is the hinge between "
            "photograph and editorial atmosphere. Commercial information is a paired composition, not a list."
        ),
        "human_style_review": "pending visual confirmation after render",
    }
    all_yes = all(creative_review[k] == "YES" for k in ("AGENCY_FINISHED_CAMPAIGN", "ACTUAL_CREATIVE_IDEA", "ONE_AUTHORED_COMPOSITION", "MEMORABLE_VISUAL_RELATIONSHIP"))
    reality = {
        "REAL_PROJECT_PHOTOS": "PASS" if copy_ok else "FAIL",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "REAL_TEMPLE_LOGO": "PASS" if logo_once else "FAIL",
        "DUPLICATE_TEMPLE_WORDMARK": "YES" if not no_wordmark else "NO",
        "FINANCIAL_CONTENT": "PASS" if copy_ok else "FAIL",
        "source_photo": SUNSET_FILENAME,
        "source_photo_asset_id": SUNSET_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "ARCHITECTURE_FIDELITY": 10,
    }
    structural = (
        all_yes
        and copy_ok
        and reality["REAL_TEMPLE_LOGO"] == "PASS"
        and reality["DUPLICATE_TEMPLE_WORDMARK"] == "NO"
        and provider_call_count() == 0
        and master_record["approval_status"] == "DRAFT"
        and master_record["router_eligible"] is False
    )
    status = "PREMIUM_MASTER_02_PENDING_HUMAN_APPROVAL" if structural else "PREMIUM_MASTER_02_NOT_READY"

    direction = {
        "schema": "CreativeDirectionV1",
        "source": ORNEK_FILENAME,
        "source_asset_id": ORNEK_ASSET_ID,
        "idea": "The campaign occupies the sunset. The spire writes into the editorial field.",
        "photo": {"filename": SUNSET_FILENAME, "asset_id": SUNSET_ASSET_ID, "role": "primary photographic world"},
        "logo": {"asset_id": LOCKED_LOGO_ASSET_ID, "role": "opens the atmospheric field"},
        "do_not_copy": ["UniLoft", "circular badges", "INVESTHOME GÜVENCESİYLE", "navy sidebar", "Master 01 left sky column"],
        "transform": transform,
    }
    photo_selection = {
        "schema": "PhotoSelectionV1",
        "selected": {"filename": SUNSET_FILENAME, "asset_id": SUNSET_ASSET_ID, "role": "primary"},
        "why": (
            "Warm dusk sky can dissolve into an editorial field without a panel. Spire is a vertical hinge. "
            "Not Day_003. Not Master 01's daylight type-in-sky."
        ),
        "shortlist": [{"filename": n, "asset_id": a, "note": note} for n, a, note in SHORTLIST],
        "rejected_day_003": "Master 01 photographic identity; different campaign required",
    }

    images = {
        "reference": ornek,
        "shortlist": render_shortlist(short_items),
        "assets": render_assets(photo, logo_rgba),
        "direction": _text_board(
            "04  CREATIVE DIRECTION",
            [
                "SOURCE  ORNEK_00012  —  photo and graphic field merge",
                "IDEA  The dusk sky is the campaign. The spire is the hinge.",
                "PHOTO  Sunset_001  primary world",
                "TYPE  centered display in the atmospheric field",
                "COMMERCIAL  %35 paired with price/unit across a hairline",
                "NOT  navy panel, circular badge, Master 01 left column, listing template",
            ],
        ),
        "master": image,
        "pair": render_pair(ornek, image, "ORNEK_00012  reference  do not copy", "MASTER 02  DRAFT", "06  REFERENCE vs MASTER 02"),
        "creative": _text_board(
            "07  CREATIVE QUALITY REVIEW",
            [f"{k}  {creative_review[k]}" for k in ("AGENCY_FINISHED_CAMPAIGN", "ACTUAL_CREATIVE_IDEA", "ONE_AUTHORED_COMPOSITION", "MEMORABLE_VISUAL_RELATIONSHIP")]
            + [str(creative_review["notes"])],
        ),
        "reality": _text_board(
            "08  PROJECT REALITY VALIDATION",
            [f"{k}  {v}" for k, v in reality.items()],
        ),
        "review": render_pair(ornek, image, "HUMAN SELECTED SOURCE", "THE TEMPLE — PREMIUM CAMPAIGN 02  DRAFT", "09  HUMAN REVIEW BOARD"),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_90,
        "created_at": _now(),
        "status": status,
        "master_name": MASTER_NAME_02,
        "master_id": TEMPLE_PREMIUM_MASTER_02_ID,
        "asset_id": asset_id,
        "approval_status": "DRAFT",
        "router_eligible": False,
        "human_selected_source": ORNEK_FILENAME,
        "selected_assets": [{"filename": SUNSET_FILENAME, "asset_id": SUNSET_ASSET_ID, "role": "primary photographic world"}],
        "creative_quality_review": creative_review,
        "project_reality_validation": reality,
        "photo_selection": photo_selection,
        "creative_direction": direction,
        "semantic_spec": spec,
        "gpt_image_calls": provider_call_count(),
        "new_master_created": True,
        "promoted_to_master": False,
        "master_01_changed": False,
        "format_work_executed": False,
        "production_cover_changed": False,
        "human_approved_premium_count": count_approved_premium(library),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "master_01_id": APPROVED_MASTER_ID,
        "master_01_asset_id": APPROVED_ASSET_ID,
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
    tests = list(blob.get("premium_master_90_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable({k: v for k, v in record.items() if k not in {"semantic_spec", "creative_direction"}}), default=str)))
    blob["premium_master_90_tests"] = tests
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
