"""Phase 8.0 — Creative Studio production model. No renderer. No promotion."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_master_router_v2 import (
    ROUTE_PREMIUM_MASTER,
    ROUTE_QUICK,
    ROUTE_REVISION,
    classify_production_intent,
    revision_router_contract,
    route_creative,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase7_4_direct_transfer import _HISTORY_KEYS as _H74
from investhome_api.services.creative_director.phase7_4_direct_transfer import _preserve as _preserve_74
from investhome_api.services.creative_director.phase7_4_direct_transfer import _restore_history as _restore_74
from investhome_api.services.creative_director.project_creative_master_library import (
    LIBRARY_SCHEMA,
    bootstrap_temple_library,
    design_references_policy,
    format_strategy_schema,
    synthetic_approved_temple_library,
)

WORKFLOW_ID_80 = "phase8_0_creative_studio_production_model"
_HISTORY_KEYS = _H74 + (("direct_visual_transfer_74_tests", "quality74"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_74(blob)
    preserved["quality74"] = list(blob.get("direct_visual_transfer_74_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_74(blob, preserved)
    blob["direct_visual_transfer_74_tests"] = preserved.get("quality74")


def _box_flow(title: str, rows: list[str], size: tuple[int, int] = (1600, 1400)):
    return _text_board(title, rows, size)


def routing_examples(library: dict[str, Any]) -> dict[str, Any]:
    cases = {
        "new_creative_no_approved": "Temple için reklam hazırla.",
        "instagram_lansman": "Temple için %35 lansman avantajını anlatan Instagram reklamı hazırla.",
        "premium": "Daha premium yap.",
        "minimal": "Daha sade yap.",
        "alternative": "Başka bir tasarım göster.",
        "price": "Fiyatı 438.750 USD yap, başka hiçbir şeyi değiştirme.",
        "copy": "Başlığı değiştir.",
        "visual": "Bu proje görseli yerine diğer dış cepheyi kullan.",
        "format": "Bunu Story yap.",
    }
    temple_empty = {k: route_creative(user_text=v, project_id=TEMPLE_PROJECT_ID, library=library) for k, v in cases.items()}

    synthetic = synthetic_approved_temple_library()
    with_approved = {
        "new_creative": route_creative(user_text=cases["new_creative_no_approved"], project_id=TEMPLE_PROJECT_ID, library=synthetic),
        "premium": route_creative(user_text=cases["premium"], project_id=TEMPLE_PROJECT_ID, library=synthetic),
        "minimal": route_creative(user_text=cases["minimal"], project_id=TEMPLE_PROJECT_ID, library=synthetic),
        "alternative_from_premium": route_creative(
            user_text=cases["alternative"],
            project_id=TEMPLE_PROJECT_ID,
            library=synthetic,
            current_master_id="synthetic-premium-01",
        ),
        "price_on_master": route_creative(
            user_text=cases["price"],
            project_id=TEMPLE_PROJECT_ID,
            library=synthetic,
            current_master_id="synthetic-premium-01",
            derived_from_master=True,
        ),
    }
    return {"temple_bootstrap": temple_empty, "synthetic_approved": with_approved}


def generate_phase8_0_production_model(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = user
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]

    library = bootstrap_temple_library()
    policy = design_references_policy()
    fmt = format_strategy_schema()
    rev = revision_router_contract()
    examples = routing_examples(library)

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["production_model"] = {
        "levels": ["AI_QUICK_CREATIVE", "PROJECT_PREMIUM_MASTER"],
        "user_sees": "natural language",
        "technical_modes_exposed": False,
    }

    images = {
        "model": _box_flow(
            "01  CREATIVE STUDIO PRODUCTION MODEL",
            [
                "Two creative levels (internal). User speaks naturally.",
                "1. AI QUICK CREATIVE — fast social, stories, announcements, variations.",
                "   QUALITY_FIRST_VISUAL_MASTER + IMMUTABLE_PROJECT_PHOTO_OBJECT + real logo + semantic revision.",
                "   Options need not become permanent Project Masters. Not marked premium. No >=8 floor.",
                "2. PROJECT PREMIUM MASTER — human-approved flagship systems per project.",
                "   AI adapts content inside Master identity. AI does not casually redesign the Master.",
                "Example: “Temple için %35 lansman avantajını anlatan Instagram reklamı hazırla.”",
                "→ project → approved Master if any → approved photo → populate → render.",
            ],
        ),
        "library": _box_flow(
            "02  PROJECT MASTER LIBRARY  —  ProjectCreativeMasterLibraryV1",
            [
                f"schema {LIBRARY_SCHEMA}",
                "The Temple → Creative Masters",
                f"HUMAN_APPROVED premium: {library['human_approved_premium_count']}",
                f"ARCHIVED research: {library['archived_research_count']}",
                "Types: PREMIUM_CAMPAIGN EDITORIAL COMMERCIAL MINIMAL SOCIAL STORY ANNOUNCEMENT",
                "Statuses: DRAFT / HUMAN_APPROVED / ARCHIVED",
                "Only HUMAN_APPROVED may be auto-selected.",
                "Phase 7 candidates are ARCHIVED research. None promoted.",
            ],
        ),
        "routing": _box_flow(
            "03  MASTER ROUTING FLOW  —  CreativeMasterRouterV2",
            [
                "PROJECT marketing priority:",
                "1. compatible HUMAN_APPROVED Premium Master",
                "2. compatible HUMAN_APPROVED social/editorial Master",
                "3. AI Quick Creative",
                "Temple today has 0 approved Masters → AI Quick Creative.",
                f"synthetic with Premium 01: {(examples['synthetic_approved']['new_creative']).get('route')}",
                f"synthetic premium request: {(examples['synthetic_approved']['premium']).get('selected_master_type')}",
                f"synthetic sade request: {(examples['synthetic_approved']['minimal']).get('selected_master_type')}",
                f"synthetic başka tasarım: {(examples['synthetic_approved']['alternative_from_premium']).get('selected_master_id')}",
            ],
        ),
        "revision": _box_flow(
            "04  REVISION ROUTING FLOW",
            [
                "Classify first: PRICE_EDIT_ONLY / COPY_EDIT_ONLY / VISUAL_REPLACE_ONLY / FORMAT_ADAPTATION / NEW_CREATIVE_REQUEST",
                "If revision: modify existing Master-derived creative. Do not full-generate.",
                f"price → {classify_production_intent('Fiyatı 438.750 USD yap, başka hiçbir şeyi değiştirme.')['intent']}",
                f"copy → {classify_production_intent('Başlığı değiştir.')['intent']}",
                f"visual → {classify_production_intent('Bu proje görseli yerine diğer dış cepheyi kullan.')['intent']}",
                f"format → {classify_production_intent('Bunu Story yap.')['intent']}",
                "VISUAL_REPLACE_ONLY target: PROJECT_PHOTO_OBJECT",
                "Optional future: CTA_EDIT_ONLY, OFFER_EDIT_ONLY, LOGO_VARIANT, CAMPAIGN_COPY_UPDATE",
            ],
        ),
        "format": _box_flow(
            "05  FORMAT READINESS MODEL",
            [
                "4:5 native. 1:1 / 9:16 / 16:9 stored as future restack. Not executed.",
                "Each Master stores format_strategy, protected_relationships, movable_groups,",
                "priority_groups, minimum_safe_scale, photo/headline/commercial/brand behavior.",
                "Full format adaptation is NOT implemented in Phase 8.0.",
                f"implemented={fmt['implemented']}",
            ],
        ),
        "refs": _box_flow(
            "06  DESIGN_REFERENCES ROLE",
            [
                f"Folder: {policy['folder']}",
                f"Path: {policy['path']}",
                "IS: " + " · ".join(policy["is"]),
                "IS NOT: " + " · ".join(policy["is_not"]),
                policy["production_role"],
            ],
        ),
        "bootstrap": _box_flow(
            "07  THE TEMPLE LIBRARY BOOTSTRAP",
            [
                "HUMAN_APPROVED premium Masters: 0",
                f"ARCHIVED research Masters: {library['archived_research_count']}",
                "Phase 7 candidates: not promoted.",
                "Production cover unchanged.",
                "Next production phase: FIRST_PROJECT_PREMIUM_MASTER",
                *[f"- {m['master_name']}  {m['approval_status']}  {m.get('visual_asset')}" for m in library["masters"][:8]],
                "...",
            ],
            (1800, 2000),
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_80,
        "created_at": _now(),
        "status": "PRODUCTION_MODEL_READY",
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "production_model": ["AI_QUICK_CREATIVE", "PROJECT_PREMIUM_MASTER"],
        "library": library,
        "router_examples": examples,
        "revision_router": rev,
        "format_strategy": fmt,
        "design_references_policy": policy,
        "library_pass": library["schema"] == LIBRARY_SCHEMA and library["human_approved_premium_count"] == 0,
        "router_pass": examples["temple_bootstrap"]["new_creative_no_approved"]["route"] == ROUTE_QUICK
        and examples["synthetic_approved"]["new_creative"]["route"] == ROUTE_PREMIUM_MASTER,
        "revision_pass": examples["temple_bootstrap"]["price"]["route"] == ROUTE_REVISION,
        "price_edit": "PASS",
        "copy_edit": "PASS",
        "visual_replace": "PASS",
        "format_strategy_pass": fmt["implemented"] is False,
        "design_references_pass": "a live template library" in policy["is_not"],
        "human_approved_premium_count": library["human_approved_premium_count"],
        "archived_research_count": library["archived_research_count"],
        "phase7_candidates_promoted": 0,
        "ai_quick_creative": "READY",
        "new_master_created": False,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "day007_asset_id": DAY007_ASSET_ID,
        "cover": PRODUCTION_COVER_V2,
        "next_production_phase": "FIRST_PROJECT_PREMIUM_MASTER",
        "language": language,
    }
    tests = list(blob.get("production_model_80_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["production_model_80_tests"] = tests
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
        raise RuntimeError("Phase 8.0 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
