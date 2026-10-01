"""Phase 5.8 — new premium masters on V4. No GPT Image. Existing Master unchanged."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.compositor_relational_v4 import compose_relational_v4
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_ASSET_ID, PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_art_direction import (
    blueprint_v3_pass,
    fallback_blueprints,
    programmatic_bad,
    translate_relational_plan,
)
from investhome_api.services.creative_director.phase5_8_new_premium_master import WORKFLOW_ID_58, generate_new_premium_master_58
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.temple_exterior_catalog import is_temple_production_exterior, pick_photo_for_concept, score_photo_for_mode
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID


def test_locks_existing_masters() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRICE_R1_REVISION_ID == "9c93f0cb-4f4d-429b-bfd0-cfdd3c9e3f76"
    assert PRICE_R1_ASSET_ID == "3790af4c-2561-4845-a4c7-8ba3d478139d"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_58 == "phase5_8_new_premium_master"
    assert generate_new_premium_master_58
    assert compose_relational_v4


def test_no_gpt_image_or_v3_fallback() -> None:
    import investhome_api.services.creative_director.phase5_8_new_premium_master as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "compose_premium_structured" not in src
    assert "compose_relational_v4" in src
    assert "GraphicDesignCompositorV4" in src
    assert "must not call GPT Image" in src
    assert "existing_master_changed" in src
    assert "CANDIDATE_PENDING_HUMAN_REVIEW" in src
    assert "promoted_to_master" in src


def test_ornek_cannot_be_production_photo() -> None:
    assert is_temple_production_exterior("ORNEK_00013.jpg") is False
    assert is_temple_production_exterior("IH_DC_TMP_001_Render_Exterior_Day_007.jpg") is True
    assert is_temple_production_exterior("IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg") is True
    assert is_temple_production_exterior("IH_DC_TMP_001_Logo_Primary.svg") is False


def test_photo_picker_prefers_requested_and_unused() -> None:
    catalog = [
        {"asset_id": "a", "filename": "Day_007.jpg", "sky_area": 0.4, "hard_coverage": 0.3, "architecture_centroid_x": 0.55},
        {"asset_id": "b", "filename": "Day_004.jpg", "sky_area": 0.15, "hard_coverage": 0.5, "architecture_centroid_x": 0.5},
    ]
    picked = pick_photo_for_concept(catalog, mode="SKY_VEIL", used=set(), requested_filename="Day_004")
    assert picked["asset_id"] == "b"
    sky = pick_photo_for_concept(catalog, mode="SKY_VEIL", used={"b"})
    assert sky["asset_id"] == "a"
    assert score_photo_for_mode(catalog[0], "SKY_VEIL") > score_photo_for_mode(catalog[1], "SKY_VEIL")


def test_fallback_blueprints_are_three_distinct_modes() -> None:
    items = fallback_blueprints()
    modes = [i["reconstruction_mode"] for i in items]
    assert modes == ["SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS"]
    names = {i["concept_name"] for i in items}
    assert len(names) == 3
    for item in items:
        bad = programmatic_bad(item)
        assert bad["SPLIT_PANEL_FEEL"] <= 2
        assert bad["LISTING_CARD_FEEL"] <= 2
        assert bad["CAPTION_ROW_LAYOUT"] <= 2
        assert bad["TEMPLATE_FEEL"] <= 2
        from investhome_api.services.creative_director.phase5_8_art_direction import apply_blueprint_gate, locked_campaign_copy

        assert locked_campaign_copy(item)
        gated = apply_blueprint_gate(dict(item), source="structural_fallback")
        assert gated["critic_pass"] is True
        plan = translate_relational_plan(item, mode=item["reconstruction_mode"], photo={"asset_id": "x", "filename": "y"})
        assert plan["schema"] == "RelationalCompositionPlanV1"


def test_invented_copy_does_not_pass_empty_critic() -> None:
    from investhome_api.services.creative_director.phase5_8_art_direction import apply_blueprint_gate

    item = {
        "concept_name": "Modern Sanctum",
        "visual_thesis": "sacred spaces",
        "selected_project_photo": "Day_002",
        "campaign_group_role": "elevated",
        "offer_group_role": "integrated",
        "brand_role": "prominent",
        "action_role": "implied",
        "reconstruction_mode": "SKY_VEIL",
        "commercial_story": "Introducing a new era of sacred spaces.",
        "reading_flow": "top_to_bottom",
    }
    gated = apply_blueprint_gate(item, positives={}, source="structural")
    assert gated["critic_pass"] is False


def test_navy_column_blueprint_fails() -> None:
    bad = programmatic_bad({"visual_thesis": "photo on the right, navy column of information on the left"})
    assert bad["SPLIT_PANEL_FEEL"] > 2
    scores = {k: 9 for k in (
        "professional_art_direction",
        "reference_craft_transfer",
        "originality",
        "group_cohesion",
        "whole_canvas_composition",
        "architecture_integration",
        "typographic_composition",
        "commercial_storytelling",
        "brand_integration",
        "CTA_integration",
        "negative_space_quality",
        "visual_rhythm",
        "premium_character",
        "structured_feasibility",
    )}
    assert blueprint_v3_pass(scores, bad) is False
