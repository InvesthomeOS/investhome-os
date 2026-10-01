"""Stage 4.0 close — recomposition doctrine and routing. No Story. No R4."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import (
    FORMAT_ADAPTATION,
    classify_production_intent,
    revision_router_contract,
    route_creative,
)
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.premium_creative_product_model import (
    premium_revision_contract,
    route_locked_creative_product,
    routing_model,
)
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    ADAPTER_ID,
    COMPOSITION_STATUS,
    REPLACED_BY,
    adapter_contract,
)
from investhome_api.services.creative_director.premium_format_recomposer_v1 import (
    ACTION,
    NEXT_STAGE,
    RECOMPOSER_ID,
    STATUS,
    archived_story_proof,
    permanent_format_adaptation_rule,
    prepare_format_recomposition,
    preserved_technical_integrity,
    recomposer_contract,
)
from investhome_api.services.creative_director.project_creative_master_library import (
    empty_library,
    synthetic_approved_temple_library,
)
from investhome_api.services.creative_director.stage4_0_close import generate_stage4_0_close


def test_reposition_model_is_deprecated() -> None:
    contract = adapter_contract()
    assert contract["schema"] == ADAPTER_ID
    assert contract["composition_status"] == "DEPRECATED"
    assert COMPOSITION_STATUS == "DEPRECATED"
    assert contract["replaced_by"] == RECOMPOSER_ID == REPLACED_BY


def test_recomposer_locks_identity_not_coordinates() -> None:
    rule = permanent_format_adaptation_rule()
    assert rule["must_not_mean"] == "resize + reposition semantic layers"
    assert rule["DESIGN_IDENTITY"] == "LOCKED"
    assert rule["LAYOUT_COORDINATES"] == "NOT LOCKED"
    assert "campaign idea" in rule["lock_from_master"]
    assert "copy" in rule["lock_from_master"]
    assert "composition" in rule["allow_target_format_art_direction"]
    assert "layout geometry" in rule["allow_target_format_art_direction"]
    assert "PIXEL POSITION FIDELITY" in rule["fidelity"]["NOT_REQUIRED"]
    assert "CONTENT FIDELITY" in rule["fidelity"]["STRICT"]
    assert "invent imagery" in rule["do_not"]


def test_technical_gates_are_preserved() -> None:
    gates = preserved_technical_integrity()
    assert gates["PHOTO_OBJECT_COUNT"] == 1
    assert gates["SEMANTIC_LAYER_DUPLICATION_COUNT"] == 0
    assert gates["ORPHAN_TEXT_FRAGMENT_COUNT"] == 0
    assert "ONE PHOTO OBJECT" in gates["gates"]
    assert "NO SOURCE-TYPE LEAKAGE" in gates["gates"]


def test_story_archive_rejects_all_revisions() -> None:
    archive = archived_story_proof()
    assert archive["current_story"] == "REJECTED"
    assert archive["technical_fidelity"] == "PASS"
    assert archive["design_fidelity"] == "FAIL"
    assert archive["do_not_create"] == "R4"
    by_rev = {item["revision"]: item["status"] for item in archive["revisions"]}
    assert by_rev["R1"] == "REJECTED"
    assert by_rev["R2"] == "REJECTED"
    assert by_rev["CLEAN"] == "REJECTED"
    assert by_rev["R3"] == "REJECTED"


def test_recomposer_does_not_execute_story() -> None:
    contract = recomposer_contract()
    assert contract["schema"] == RECOMPOSER_ID
    assert contract["executed"] is False
    assert contract["story_generated"] is False
    assert contract["status"] == STATUS
    assert contract["next"] == NEXT_STAGE
    prepared = prepare_format_recomposition(empty_library(project_id="proj", project_name="x"), execute=False)
    assert prepared["executed"] is False
    assert prepared["format_child"] is None
    try:
        prepare_format_recomposition(empty_library(project_id="proj", project_name="x"), execute=True)
        raise AssertionError("Stage 4.0 must refuse execution")
    except RuntimeError as exc:
        assert "must not execute a Story in Stage 4.0" in str(exc)


def test_format_request_does_not_route_to_recomposer() -> None:
    classified = classify_production_intent("Bunu Story yap.")
    assert classified["intent"] == FORMAT_ADAPTATION
    result = route_creative(
        user_text="Bunu Story yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=synthetic_approved_temple_library(),
        current_master_id="synthetic-premium-01",
        derived_from_master=True,
    )
    assert result["route"] == "PREMIUM_FORMAT_MASTER_MISSING"
    assert result["action"] == "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
    assert result["action"] != ACTION
    assert result["engine"] is None
    assert result["regenerate"] is False
    assert result["executed"] is False
    locked = route_locked_creative_product("Bunu Story yap.", current_master_id="synthetic-premium-01")
    assert locked["action"] == "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
    assert locked.get("engine") != RECOMPOSER_ID
    assert locked["revision_intent"] == FORMAT_ADAPTATION
    product = routing_model()
    story = product["when_suitable_approved_premium_master_exists"]["Bunu Story yap."]
    assert "PREMIUM_FORMAT_MASTER_MISSING" in story
    assert RECOMPOSER_ID not in story
    rev = premium_revision_contract()["format_adaptation"]
    assert rev["status"] == "DISABLED"
    assert rev["engine"] == "PremiumCreativeFamilyV1"
    assert RECOMPOSER_ID in rev["archived"]
    contract = revision_router_contract()
    assert contract["FORMAT_ADAPTATION"]["engine"] == "PremiumCreativeFamilyV1"
    assert contract["FORMAT_ADAPTATION"]["on_missing"] == "PREMIUM_FORMAT_MASTER_MISSING"
    assert contract["FORMAT_ADAPTATION"]["autonomous_design"] is False


def test_close_workflow_does_not_generate_or_start_41() -> None:
    src = inspect.getsource(generate_stage4_0_close)
    assert "persist_gpt_image" not in src
    assert "compose_story" not in src
    assert "openai" not in src.lower()
    assert "generate_stage4_1" not in src
    assert "r4_created" in src
    assert STATUS == "FORMAT_ADAPTATION_METHOD_REQUIRES_RECOMPOSITION"
    assert NEXT_STAGE.startswith("STAGE 4.1")
