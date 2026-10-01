"""Phase 12.2 — Premium Creative Family model lock. No artwork. No Story."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
    FAMILY_WIDE_REVISION,
    FORMAT_ADAPTATION,
    PRICE_EDIT_ONLY,
    VISUAL_REPLACE_ONLY,
    classify_production_intent,
    revision_router_contract,
    route_creative,
)
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID
from investhome_api.services.creative_director.phase12_1_approve_lock import BRAND_ID
from investhome_api.services.creative_director.phase12_2_family_lock import (
    STATUS,
    generate_phase12_2_family_lock,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    AUTONOMOUS_PREMIUM_FORMAT_DESIGN,
    FEED_PORTRAIT,
    LANDSCAPE,
    NEXT_PHASE,
    ORNEK_FAMILY_ID,
    SQUARE,
    STATUS_FORMAT_MISSING,
    STATUS_MODEL_READY,
    STATUS_STAGE41_FAIL,
    STORY_REEL,
    family_containing_master,
    lookup_format_master,
    ornek_00013_family,
    rejected_stage4_stories_in_family,
    required_regression_tests,
    resolve_family,
    route_family_wide_revision,
    route_format_request,
)
from investhome_api.services.creative_director.premium_creative_product_model import (
    ai_quick_creative_contract,
    premium_revision_contract,
    route_locked_creative_product,
)
from investhome_api.services.creative_director.project_creative_master_library import empty_library


def _brand_library() -> dict:
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    library["premium_creative_families"] = [ornek_00013_family()]
    return library


def test_ornek_00013_family_lookup() -> None:
    library = _brand_library()
    family = resolve_family(library, brand_id=BRAND_ID, family_id=ORNEK_FAMILY_ID)
    assert family is not None
    assert family["FAMILY_ID"] == ORNEK_FAMILY_ID
    assert family["family_type"] == "INVESTHOME BRAND"
    assert family["inventory"][FEED_PORTRAIT] == "HUMAN_APPROVED"
    assert family["inventory"][STORY_REEL] == "MISSING"
    assert family["inventory"][SQUARE] == "MISSING"
    assert family["inventory"][LANDSCAPE] == "MISSING"


def test_feed_master_is_human_approved() -> None:
    looked = lookup_format_master(ornek_00013_family(), FEED_PORTRAIT)
    assert looked["status"] == "HUMAN_APPROVED"
    assert looked["format_master_id"] == PRODUCTION_MASTER_ID
    assert looked["source_asset_id"] == SELECTED_ASSET_ID
    assert looked["family_member"] is True


def test_missing_premium_formats_are_not_fabricated() -> None:
    family = ornek_00013_family()
    library = _brand_library()
    for fmt, text in (
        (STORY_REEL, "Bunu Story yap."),
        (SQUARE, "Bunu 1:1 yap."),
        (LANDSCAPE, "Bunu 16:9 yap."),
    ):
        looked = lookup_format_master(family, fmt)
        assert looked["status"] == STATUS_FORMAT_MISSING
        assert looked["master"] is None
        routed = route_format_request(
            classified=classify_production_intent(text),
            library=library,
            brand_id=BRAND_ID,
            current_master_id=PRODUCTION_MASTER_ID,
        )
        assert routed["status"] == STATUS_FORMAT_MISSING
        assert routed["route"] == STATUS_FORMAT_MISSING
        assert routed["action"] == "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
        assert routed["regenerate"] is False
        assert routed["autonomous_premium_format_design"] is False


def test_rejected_stage4_stories_are_not_family_members() -> None:
    family = ornek_00013_family()
    assert rejected_stage4_stories_in_family(family) is False
    for slot in family["formats"].values():
        assert slot.get("revision") not in {"RETRY", "R1", "R2", "CLEAN", "R3", "STAGE4.1"}
        if slot["FORMAT"] != FEED_PORTRAIT:
            assert slot["family_member"] is False
            assert slot["FORMAT_MASTER_ID"] is None
    assert "Stage 4.1 Story" in family["rejected_not_members"]


def test_cross_project_reuse_is_blocked() -> None:
    library = _brand_library()
    assert resolve_family(library, project_id=TEMPLE_PROJECT_ID) is None
    assert resolve_family(library, project_id="uniloft-project") is None
    assert family_containing_master(library, "synthetic-premium-01") is None
    live = route_creative(
        user_text="Temple için reklam hazırla.",
        project_id=TEMPLE_PROJECT_ID,
        library=library,
    )
    assert live["selected_master_id"] != PRODUCTION_MASTER_ID


def test_stage_2_revision_router_preserved() -> None:
    contract = revision_router_contract()
    assert contract["PRICE_EDIT_ONLY"]["status"] == "PASS"
    assert contract["COPY_EDIT_ONLY"]["status"] == "PASS"
    assert contract["VISUAL_REPLACE_ONLY"]["status"] == "PASS"
    assert classify_production_intent("Fiyatı 750.000 USD yap.")["intent"] == PRICE_EDIT_ONLY
    assert classify_production_intent("Başlığı değiştir.")["intent"] == COPY_EDIT_ONLY
    assert classify_production_intent("Bu fotoğraf yerine diğer onaylı fotoğrafı kullan.")["intent"] == VISUAL_REPLACE_ONLY
    price = route_locked_creative_product("Fiyatı 750.000 USD yap.", current_master_id=PRODUCTION_MASTER_ID)
    assert price["route"] == "MASTER_DERIVED_REVISION"
    assert price["revision_intent"] == PRICE_EDIT_ONLY
    assert price["autonomous_premium"] is False
    doctrine = premium_revision_contract()
    assert doctrine["format_adaptation"]["status"] == "DISABLED"
    assert doctrine["family_wide_revision"]["status"] == "PRODUCTION READY"


def test_ai_quick_creative_preserved() -> None:
    quick = ai_quick_creative_contract()
    assert quick["status"] == "ACTIVE"
    assert quick["premium"] is False
    routed = route_locked_creative_product("Temple için hızlı creative yap", workflow="ai_quick_creative")
    assert routed["route"] == "AI_QUICK_CREATIVE"
    assert routed["premium"] is False


def test_family_wide_revision_routes_only_approved_formats() -> None:
    classified = classify_production_intent("Bu kampanyadaki fiyatı tüm formatlarda 750.000 USD yap.")
    assert classified["intent"] == FAMILY_WIDE_REVISION
    wide = route_family_wide_revision(
        classified=classified,
        library=_brand_library(),
        brand_id=BRAND_ID,
        current_master_id=PRODUCTION_MASTER_ID,
    )
    assert wide["route"] == FAMILY_WIDE_REVISION
    assert wide["action"] == "REVISE_EVERY_APPROVED_FORMAT_MASTER"
    assert wide["executed"] is False
    assert wide["uses_stage_2"] is True
    assert [item["format"] for item in wide["targets"]] == []
    assert any(item["format"] == FEED_PORTRAIT and item["reason"] == "SKIP_TARGET_NOT_PRESENT" for item in wide["skipped"])
    assert STORY_REEL in wide["missing_formats"]
    live = route_creative(
        user_text="Bu kampanyadaki fiyatı tüm formatlarda 750.000 USD yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=_brand_library(),
        current_master_id=PRODUCTION_MASTER_ID,
    )
    assert live["action"] == "REVISE_EVERY_APPROVED_FORMAT_MASTER"
    assert live["engine"] == "Stage2RevisionRouter"
    assert live["regenerate"] is False


def test_story_request_does_not_use_recomposer() -> None:
    classified = classify_production_intent("Bunu Story yap.")
    assert classified["intent"] == FORMAT_ADAPTATION
    result = route_creative(
        user_text="Bunu Story yap.",
        project_id=TEMPLE_PROJECT_ID,
        library=_brand_library(),
        current_master_id=PRODUCTION_MASTER_ID,
        derived_from_master=True,
    )
    assert result["route"] == STATUS_FORMAT_MISSING
    assert result["action"] == "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
    assert result["engine"] is None
    assert result["status"] == STATUS_FORMAT_MISSING
    locked = route_locked_creative_product(
        "Bunu Story yap.",
        library=_brand_library(),
        current_master_id=PRODUCTION_MASTER_ID,
    )
    assert locked["action"] == "SURFACE_PREMIUM_FORMAT_MASTER_MISSING"
    assert locked["status"] == STATUS_FORMAT_MISSING


def test_lock_workflow_does_not_generate_artwork() -> None:
    src = inspect.getsource(generate_phase12_2_family_lock)
    assert "persist_gpt_image" not in src
    assert "compose_story" not in src
    assert "execute_ornek_00013_story" not in src
    assert "openai" not in src.lower()
    assert "ideogram" not in src.lower()
    assert STATUS == STATUS_MODEL_READY
    assert "stage4_1_status" in src
    assert STATUS_STAGE41_FAIL == "PREMIUM_FORMAT_RECOMPOSITION_FAIL"
    assert AUTONOMOUS_PREMIUM_FORMAT_DESIGN == "DISABLED"
    assert NEXT_PHASE == "FIRST MULTI-FORMAT PRODUCTION CREATIVE FAMILY INGESTION"


def test_required_regression_bundle() -> None:
    tests = required_regression_tests()
    assert tests["ornek_00013_family_lookup"] == "PASS"
    assert tests["feed_4x5"] == "HUMAN_APPROVED master found"
    assert tests["story_9x16"] == STATUS_FORMAT_MISSING
    assert tests["square_1x1"] == STATUS_FORMAT_MISSING
    assert tests["landscape_16x9"] == STATUS_FORMAT_MISSING
    assert tests["rejected_stage4_stories_returned"] == "NO"
    assert tests["cross_project_reuse"] == "BLOCKED"
    assert tests["stage_2_revision_router_preserved"] == "PASS"
    assert tests["ai_quick_creative_preserved"] == "PASS"
