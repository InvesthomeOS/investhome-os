"""Phase 11.0 — Creative Quality Engine foundation. No new artwork. No Stage 3 proof."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.anti_template_detector import detect_template
from investhome_api.services.creative_director.creative_critic_v2 import PREMIUM_FLOORS, score_creative_v2
from investhome_api.services.creative_director.creative_design_dna_v2 import design_dna_library, grade_a_design_dna
from investhome_api.services.creative_director.creative_strategy_v1 import empty_creative_strategy, validate_creative_strategy
from investhome_api.services.creative_director.idea_first_pipeline import STEPS, no_copy_test, two_second_test
from investhome_api.services.creative_director.phase11_0_foundation import (
    WORKFLOW_ID_11_0,
    generate_phase11_0_creative_quality_foundation,
    lock_stage3_foundation,
    reference_library_audit,
)
from investhome_api.services.creative_director.project_photo_creative_profile import project_photo_profile_library
from investhome_api.services.creative_director.stage3_canonical_pipeline import (
    CANONICAL_PREMIUM_PATH,
    is_premium_new_request,
    route_premium_generation,
)


def test_grade_a_dna_is_concrete() -> None:
    records = grade_a_design_dna()
    assert len(records) == 6
    for item in records:
        assert item["schema"] == "CreativeDesignDNAV2"
        assert "premium" not in item["visual_idea"].casefold()[:12]
        assert item["memorable_gesture"]
        assert item["strength_score"] >= 7
        assert "UniLoft" in " ".join(item["forbidden_literal_copy"]) or "Uniloft" in str(item["forbidden_literal_copy"])
    lib = design_dna_library()
    assert lib["status"] == "READY"
    assert lib["coordinates_are_not_the_intelligence"] is True


def test_gates_and_critic() -> None:
    fail_copy = no_copy_test(visual_mechanism="a property photo with text", photography_participates=True, feels_designed_without_copy=True)
    assert fail_copy["pass"] is False
    ok_copy = no_copy_test(
        visual_mechanism="spire cuts a navy field as graphic material",
        photography_participates=True,
        feels_designed_without_copy=True,
    )
    assert ok_copy["pass"] is True
    assert two_second_test("a property photo with text")["pass"] is False
    assert two_second_test("the Temple spire cuts a designed field")["pass"] is True
    assert detect_template({"photo + headline": True})["pass"] is False
    assert detect_template({"photo + headline": True}, user_requested_format=True)["pass"] is True
    scores = {axis: 9 for axis in PREMIUM_FLOORS}
    scores["BRAND_CHARACTER"] = 9
    scores["DEPTH"] = 9
    scores["NEGATIVE_SPACE"] = 9
    result = score_creative_v2(scores, anti_template="PASS", no_copy="PASS", project_reality="PASS")
    assert result["status"] == "PENDING_HUMAN_APPROVAL"
    low = dict(scores)
    low["PUBLISHABILITY"] = 3
    rejected = score_creative_v2(low, anti_template="PASS", no_copy="PASS", project_reality="PASS")
    assert rejected["status"] == "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW"
    assert rejected["publishability"] == 3


def test_strategy_before_layout_and_canonical_route() -> None:
    unset = empty_creative_strategy()
    assert validate_creative_strategy(unset)["layout_allowed"] is False
    assert STEPS[0] == "UNDERSTAND_USER_INTENT"
    assert STEPS[10] == "RENDER"
    assert is_premium_new_request("The Temple için premium bir lansman reklamı hazırla.") is True
    routed = route_premium_generation("The Temple için premium bir lansman reklamı hazırla.")
    assert routed["route"] == CANONICAL_PREMIUM_PATH
    assert CANONICAL_PREMIUM_PATH == "STAGE3_INTEGRATED_CAMPAIGN_PIPELINE"
    assert routed["executed"] is False
    quick = route_premium_generation("Temple için hızlı creative yap", workflow="ai_quick_creative")
    assert quick["route"] == "AI_QUICK_CREATIVE"
    assert WORKFLOW_ID_11_0 == "phase11_0_creative_quality_engine_foundation"
    assert generate_phase11_0_creative_quality_foundation
    assert lock_stage3_foundation
    assert reference_library_audit()["grade_a_analyzed"] == 6
    assert project_photo_profile_library()["status"] == "READY"


def test_no_artwork_in_foundation() -> None:
    import investhome_api.services.creative_director.phase11_0_foundation as workflow

    src = inspect.getsource(workflow)
    assert "persist_gpt_image" not in src
    assert "render_html_to_png" not in src
    assert "attach_format_child" not in src
    assert "empty_master(" not in src
    assert "stage_3_executed" in src
