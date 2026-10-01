"""Phase 5.5A gates. Art direction first. No GPT Image. No new family."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.ai_visual_art_director import (
    GRADE_A_REFERENCES,
    blueprint_critic_pass,
    concept_executable_by_v3,
    select_winning_blueprint,
)
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import (
    DAY007_ASSET_ID,
    LOCKED_CENTERING,
    LOCKED_SOURCE_CROP,
    WORKFLOW_ID_55A,
    generate_ai_visual_art_director_55a,
)
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2


def test_locks_day007_logo_and_grade_a_refs() -> None:
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert LOCKED_CENTERING == (0.50, 0.42)
    assert LOCKED_SOURCE_CROP == [161.06, 0.0, 1256.26, 1369.0]
    ids = {item[0] for item in GRADE_A_REFERENCES}
    assert ids == {
        "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57",
        "3a3c4832-a8c1-5a43-a518-d895ee78fbe1",
        "15e71ec3-ff92-5604-84aa-2582510d0615",
        "b57f0ba1-3cc7-583c-98a8-c4330a7e4cdd",
        "a1046460-04ad-5ef1-bd42-88042c4d9760",
        "1d0e8a8e-03e9-5ba1-bf25-b61c523ed6d2",
    }


def test_no_image_generation_in_director_or_workflow() -> None:
    import investhome_api.services.creative_director.ai_visual_art_director as director
    import investhome_api.services.creative_director.phase5_5a_ai_visual_art_director as workflow

    for source in (inspect.getsource(director), inspect.getsource(workflow)):
        assert "edit_image" not in source
        assert "generate_image" not in source
        assert "images/generations" not in source
    assert WORKFLOW_ID_55A in inspect.getsource(workflow)
    assert "ART_DIRECTION_NOT_GOOD_ENOUGH" in inspect.getsource(workflow)
    assert "art_plan=" in inspect.getsource(workflow)
    assert PRODUCTION_COVER_V2
    assert generate_ai_visual_art_director_55a
    assert "load_grade_a_reference_images" in inspect.getsource(workflow)


def test_art_plan_defaults_off() -> None:
    assert inspect.signature(compose_graphic_design_v3).parameters["art_plan"].default is None


def test_director_sends_actual_reference_pixels() -> None:
    import investhome_api.services.creative_director.ai_visual_art_director as director

    source = inspect.getsource(director.request_art_direction)
    module = inspect.getsource(director)
    assert "_img(" in source
    assert "Grade-A DESIGN_REFERENCE pixels" in source
    for _asset, filename in GRADE_A_REFERENCES:
        assert filename in module


def test_critic_gate_rejects_weak_and_risky_blueprints() -> None:
    weak = {key: 7 for key in (
        "originality",
        "reference_craft_understanding",
        "photo_integration",
        "architectural_respect",
        "visual_hierarchy",
        "commercial_storytelling",
        "brand_integration",
        "cta_integration",
        "premium_character",
        "whole_canvas_composition",
        "production_feasibility",
    )}
    weak.update({"listing_layout_risk": 1, "template_risk": 1, "text_dump_risk": 1, "UI_risk": 1})
    assert blueprint_critic_pass(weak) is False
    strong = {key: 8 for key in weak}
    strong.update({"listing_layout_risk": 1, "template_risk": 2, "text_dump_risk": 1, "UI_risk": 1})
    assert blueprint_critic_pass(strong) is True
    risky = dict(strong)
    risky["listing_layout_risk"] = 3
    assert blueprint_critic_pass(risky) is False
    blueprints = [
        {"id": "AD1", "critic_pass": False, "critic_scores": weak},
        {"id": "AD2", "critic_pass": False, "critic_scores": risky},
        {"id": "AD3", "critic_pass": False, "critic_scores": {}},
    ]
    assert select_winning_blueprint(blueprints, {"winner_id": "AD1"}) is None


def test_anti_pattern_mentions_in_not_copied_do_not_block_execution() -> None:
    ok, _reason = concept_executable_by_v3(
        {
            "one_sentence_idea": "A left-sky editorial signature balanced against the spire.",
            "visual_axis": "aligned to the left sky edge",
            "deliberately_not_copied": "no card, pill, badge, listing dump or split left/right ads",
        }
    )
    assert ok is True
    blocked, _reason = concept_executable_by_v3(
        {
            "one_sentence_idea": "A brochure stack of six commercial rows on a card.",
            "visual_axis": "dashboard",
        }
    )
    assert blocked is False


def test_workflow_does_not_compose_before_gates() -> None:
    import investhome_api.services.creative_director.phase5_5a_ai_visual_art_director as workflow

    source = inspect.getsource(workflow.generate_ai_visual_art_director_55a)
    compose_at = source.find("compose_graphic_design_v3")
    critic_at = source.find("select_winning_blueprint")
    fidelity_at = source.find('if not fidelity.get("pass")')
    assert 0 <= critic_at < compose_at
    assert 0 <= fidelity_at < compose_at
    assert '"promoted_to_master": False' in source
