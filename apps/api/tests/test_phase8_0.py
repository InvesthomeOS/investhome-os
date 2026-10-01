"""Phase 8.0 — Creative Studio production model. Library + routing. No promotion."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
    FORMAT_ADAPTATION,
    NEW_CREATIVE_REQUEST,
    PRICE_EDIT_ONLY,
    ROUTE_PREMIUM_MASTER,
    ROUTE_QUICK,
    ROUTE_REVISION,
    VISUAL_REPLACE_ONLY,
    classify_production_intent,
    revision_router_contract,
    route_creative,
)
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72
from investhome_api.services.creative_director.phase8_0_production_model import WORKFLOW_ID_80, generate_phase8_0_production_model
from investhome_api.services.creative_director.project_creative_master_library import (
    LIBRARY_SCHEMA,
    MASTER_TYPES,
    add_master,
    approved_masters,
    bootstrap_temple_library,
    design_references_policy,
    empty_library,
    empty_master,
    format_strategy_schema,
    synthetic_approved_temple_library,
)


def test_locks() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PRODUCTION_DOCTRINE == "QUALITY_FIRST_VISUAL_MASTER"
    assert PROJECT_CREATIVE_RULE == "IMMUTABLE_PROJECT_PHOTO_OBJECT"
    assert WORKFLOW_ID_80 == "phase8_0_creative_studio_production_model"
    assert generate_phase8_0_production_model
    rev = revision_readiness_72()
    assert rev["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]


def test_temple_bootstrap_zero_approved() -> None:
    library = bootstrap_temple_library()
    assert library["schema"] == LIBRARY_SCHEMA
    assert library["human_approved_premium_count"] == 0
    assert library["archived_research_count"] == 12
    assert approved_masters(library, project_id=TEMPLE_PROJECT_ID) == []
    assert all(item["approval_status"] == "ARCHIVED" for item in library["masters"])
    assert all(item["router_eligible"] is False for item in library["masters"])
    assert all(item["promoted"] is False for item in library["masters"])
    assert library["ai_quick_creative"]["status"] == "READY"
    assert library["ai_quick_creative"]["premium"] is False
    assert library["ai_quick_creative"]["score_floor"] is None
    assert set(MASTER_TYPES) == {
        "PREMIUM_CAMPAIGN",
        "EDITORIAL",
        "COMMERCIAL",
        "MINIMAL",
        "SOCIAL",
        "STORY",
        "ANNOUNCEMENT",
    }


def test_project_without_approved_premium_master() -> None:
    library = bootstrap_temple_library()
    result = route_creative(
        user_text="Temple için reklam hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    assert result["route"] == ROUTE_QUICK
    assert result["regenerate"] is True
    assert result["selected_master_id"] is None
    assert result["user_visible_mode"] is None
    instagram = route_creative(
        user_text="Temple için %35 lansman avantajını anlatan Instagram reklamı hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    assert instagram["route"] == ROUTE_QUICK
    assert classify_production_intent(instagram["classified"]["user_text"])["intent"] == NEW_CREATIVE_REQUEST


def test_project_with_approved_premium_master() -> None:
    library = synthetic_approved_temple_library()
    result = route_creative(
        user_text="Temple için reklam hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    assert result["route"] == ROUTE_PREMIUM_MASTER
    assert result["selected_master_id"] == "synthetic-premium-01"
    assert result["selected_master_type"] == "PREMIUM_CAMPAIGN"
    assert result["regenerate"] is False
    assert result["action"] == "POPULATE_APPROVED_MASTER"
    assert result["internal"]["approval_state"] == "HUMAN_APPROVED"


def test_price_revision() -> None:
    text = "Fiyatı 438.750 USD yap, başka hiçbir şeyi değiştirme."
    classified = classify_production_intent(text)
    assert classified["intent"] == PRICE_EDIT_ONLY
    result = route_creative(
        user_text=text,
        project_id=TEMPLE_PROJECT_ID,
        library=synthetic_approved_temple_library(),
        current_master_id="synthetic-premium-01",
        derived_from_master=True,
    )
    assert result["route"] == ROUTE_REVISION
    assert result["revision_intent"] == PRICE_EDIT_ONLY
    assert result["regenerate"] is False
    assert result["action"] == "REVISE_EXISTING"


def test_copy_revision() -> None:
    text = "Başlığı değiştir."
    assert classify_production_intent(text)["intent"] == COPY_EDIT_ONLY
    result = route_creative(
        user_text=text,
        project_id=TEMPLE_PROJECT_ID,
        library=bootstrap_temple_library(),
        current_master_id="synthetic-premium-01",
        derived_from_master=True,
    )
    assert result["route"] == ROUTE_REVISION
    assert result["revision_intent"] == COPY_EDIT_ONLY
    assert result["regenerate"] is False


def test_visual_replace() -> None:
    text = "Bu proje görseli yerine diğer dış cepheyi kullan."
    assert classify_production_intent(text)["intent"] == VISUAL_REPLACE_ONLY
    result = route_creative(
        user_text=text,
        project_id=TEMPLE_PROJECT_ID,
        library=synthetic_approved_temple_library(),
        current_master_id="synthetic-premium-01",
        derived_from_master=True,
    )
    assert result["route"] == ROUTE_REVISION
    assert result["revision_intent"] == VISUAL_REPLACE_ONLY
    assert revision_readiness_72()["VISUAL_REPLACE_ONLY"]["allowed"] == ["PROJECT_PHOTO_OBJECT"]


def test_new_creative_request() -> None:
    classified = classify_production_intent("Temple için reklam hazırla.")
    assert classified["intent"] == NEW_CREATIVE_REQUEST
    assert classified["is_revision"] is False


def test_alternative_design_request() -> None:
    library = synthetic_approved_temple_library()
    first = route_creative(
        user_text="Başka bir tasarım göster.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
        current_master_id="synthetic-premium-01",
    )
    assert first["route"] == ROUTE_PREMIUM_MASTER
    assert first["selected_master_id"] == "synthetic-editorial-01"
    only = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    one = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="The Temple Premium Master 01",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        master_id="synthetic-premium-01",
    )
    one["router_eligible"] = True
    add_master(only, one)
    exhausted = route_creative(
        user_text="Başka bir tasarım göster.",
        project_id=TEMPLE_PROJECT_ID,
        library=only,
        current_master_id="synthetic-premium-01",
    )
    assert exhausted["route"] == ROUTE_QUICK
    assert "exhausted" in exhausted["reason"].lower()


def test_premium_request() -> None:
    classified = classify_production_intent("Daha premium yap.")
    assert classified["preference"] == "PREMIUM_CAMPAIGN"
    with_master = route_creative(
        user_text="Daha premium yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=synthetic_approved_temple_library(),
    )
    assert with_master["selected_master_type"] == "PREMIUM_CAMPAIGN"
    without = route_creative(
        user_text="Daha premium yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=bootstrap_temple_library(),
    )
    assert without["route"] == ROUTE_QUICK


def test_minimal_request() -> None:
    classified = classify_production_intent("Daha sade yap.")
    assert classified["preference"] == "MINIMAL"
    with_master = route_creative(
        user_text="Daha sade yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=synthetic_approved_temple_library(),
    )
    assert with_master["selected_master_type"] == "EDITORIAL"
    without = route_creative(
        user_text="Daha sade yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=bootstrap_temple_library(),
    )
    assert without["route"] == ROUTE_QUICK


def test_format_request_routing() -> None:
    classified = classify_production_intent("Bunu Story yap.")
    assert classified["intent"] == FORMAT_ADAPTATION
    assert classified["target_format"] == "9:16"
    result = route_creative(
        user_text="Bunu Story yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=synthetic_approved_temple_library(),
        current_master_id="synthetic-premium-01",
        derived_from_master=True,
    )
    assert result["route"] == "PREMIUM_FORMAT_MASTER_MISSING"
    assert result["action"] == "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
    assert result["engine"] is None
    assert result["status"] == "PREMIUM_FORMAT_MASTER_MISSING"
    assert result["regenerate"] is False
    assert format_strategy_schema()["implemented"] is False


def test_archived_research_never_auto_selected() -> None:
    library = bootstrap_temple_library()
    result = route_creative(
        user_text="Temple için reklam hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    assert result["route"] == ROUTE_QUICK
    archived_ids = {item["master_id"] for item in library["masters"]}
    assert result["selected_master_id"] not in archived_ids
    assert any(item["master_id"] == PARENT_MASTER_ID for item in library["masters"])


def test_design_references_policy_and_format_schema() -> None:
    policy = design_references_policy()
    assert policy["folder"] == CANONICAL_FOLDER_NAME == "DESIGN_REFERENCES"
    assert "a live template library" in policy["is_not"]
    assert "project asset source" in policy["is_not"]
    assert "automatic production layout source" in policy["is_not"]
    fmt = format_strategy_schema()
    assert fmt["implemented"] is False
    assert set(fmt["formats"]) == {"4:5", "1:1", "9:16", "16:9"}
    contract = revision_router_contract()
    assert contract["PRICE_EDIT_ONLY"]["status"] == "PASS"
    assert contract["executed"] is False


def test_no_renderer_or_promotion() -> None:
    import investhome_api.services.creative_director.creative_master_router_v2 as router
    import investhome_api.services.creative_director.phase8_0_production_model as workflow

    src = inspect.getsource(workflow) + inspect.getsource(router)
    assert "compose_relational_v4(" not in src
    assert "GraphicDesignCompositorV5" not in src
    assert "phase7_5" not in src
    assert "generate_around_photo" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "FIRST_PROJECT_PREMIUM_MASTER" in inspect.getsource(workflow)
