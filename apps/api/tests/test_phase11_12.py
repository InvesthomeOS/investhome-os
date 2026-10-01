"""Phase 11.12 tests — product-model lock, no artwork, autonomous premium disabled."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase11_12_lock import generate_phase11_12_product_lock
from investhome_api.services.creative_director.premium_creative_product_model import (
    STATUS,
    ai_quick_creative_contract,
    premium_master_ingestion_v1,
    premium_semantic_map_v1,
    research_archive_map,
    route_locked_creative_product,
)
from investhome_api.services.creative_director.project_creative_master_library import empty_library
from investhome_api.services.creative_director.stage3_canonical_pipeline import (
    CANONICAL_PREMIUM_PATH,
    maybe_refuse_legacy_premium_generation,
    route_premium_generation,
)


def test_two_modes_and_ingestion_after_design() -> None:
    quick = ai_quick_creative_contract()
    assert quick["status"] == "ACTIVE"
    assert quick["premium"] is False
    assert quick["never_silently_label_premium"] is True
    ingest = premium_master_ingestion_v1()
    assert ingest["never_force_design_from_map"] is True
    assert ingest["doctrine"][0] == "DESIGN FIRST"
    semantic = premium_semantic_map_v1()
    assert semantic["extracted"] == "AFTER the design exists"
    assert "PRICE" in {item["id"] for item in semantic["territories"]}
    archived = {item["id"] for item in research_archive_map()["paths"]}
    assert "STAGE3_HYBRID_PREMIUM_ENGINE_V2" in archived
    assert "AI_NATIVE_PREMIUM_EXPERIMENT" in archived
    assert research_archive_map()["delete_code"] is False


def test_locked_routing_does_not_fabricate_premium() -> None:
    empty = empty_library(project_id="proj", project_name="The Temple")
    missing = route_locked_creative_product(
        "Temple için premium lansman kampanyası hazırla.",
        library=empty,
        project_id="proj",
    )
    assert missing["route"] == "NO_APPROVED_PREMIUM_MASTER"
    assert missing["premium"] is False
    assert missing["do_not_fabricate_premium_status"] is True
    quick = route_locked_creative_product("Temple için hızlı creative yap", workflow="ai_quick_creative")
    assert quick["route"] == "AI_QUICK_CREATIVE"
    assert quick["premium"] is False
    price = route_locked_creative_product("Fiyatı 750.000 USD yap, başka hiçbir şeyi değiştirme.")
    assert price["route"] == "MASTER_DERIVED_REVISION"
    assert price["autonomous_premium"] is False


def test_autonomous_premium_refused_when_product_locked() -> None:
    historical = route_premium_generation("The Temple için premium bir lansman reklamı hazırla.")
    assert historical["route"] == CANONICAL_PREMIUM_PATH
    refusal = maybe_refuse_legacy_premium_generation(
        {"phase5": {"premium_creative_product_model_locked": True}},
        user_text="The Temple için premium bir lansman reklamı hazırla.",
    )
    assert refusal is not None
    assert refusal["status"] == "AUTONOMOUS_PREMIUM_GENERATION_DISABLED"
    assert refusal["canonical_path"] is None
    quick = maybe_refuse_legacy_premium_generation(
        {"phase5": {"premium_creative_product_model_locked": True}},
        user_text="Temple için hızlı creative yap",
        workflow="ai_quick_creative",
    )
    assert quick is None


def test_lock_workflow_does_not_generate_artwork() -> None:
    src = inspect.getsource(generate_phase11_12_product_lock)
    assert "persist_gpt_image" not in src
    assert "render_svg_html_to_png" not in src
    assert "add_master" not in src
    assert "attach_format_child" not in src
    assert STATUS == "PREMIUM_CREATIVE_PRODUCT_MODEL_LOCKED"
