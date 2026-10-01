"""Phase 5.9 — AI drafts reconstructed by V4. Existing Master unchanged."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.compositor_relational_v4 import compose_relational_v4
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import WORKFLOW_ID_58
from investhome_api.services.creative_director.phase5_9_ai_draft_structured_master import (
    WORKFLOW_ID_59,
    generate_ai_draft_structured_master_59,
    reconstruct_production_master_v4,
)
from investhome_api.services.creative_director.phase5_9_visual_draft import (
    DRAFT_THESES,
    advertising_photo_score,
    draft_critic_pass,
    infer_mode_from_structure,
    plan_from_structure,
    rank_drafts,
    select_advertising_photo,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.temple_exterior_catalog import is_temple_production_exterior


def test_locks_existing_masters() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRICE_R1_REVISION_ID == "9c93f0cb-4f4d-429b-bfd0-cfdd3c9e3f76"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_59 == "phase5_9_ai_draft_structured_master"
    assert WORKFLOW_ID_58 == "phase5_8_new_premium_master"
    assert generate_ai_draft_structured_master_59
    assert compose_relational_v4
    assert len(DRAFT_THESES) == 3
    modes = [item["reconstruction_mode"] for item in DRAFT_THESES]
    assert modes == ["SKY_VEIL", "GROUND_PLANE", "CORNER_INGRESS"]


def test_drafts_allowed_reconstruction_forbids_image_model() -> None:
    import investhome_api.services.creative_director.phase5_9_ai_draft_structured_master as workflow
    import investhome_api.services.creative_director.phase5_9_visual_draft as drafts

    src = inspect.getsource(workflow)
    recon = inspect.getsource(reconstruct_production_master_v4)
    assert "edit_image" in inspect.getsource(drafts)
    assert "edit_image" not in recon
    assert "generate_image" not in recon
    assert "compose_relational_v4" in src
    assert "GraphicDesignCompositorV5" not in src
    assert "must not call GPT Image" in recon
    assert "CANDIDATE_PENDING_HUMAN_REVIEW" in src
    assert "phase5_8_candidates_rejected" in src
    assert "promoted_to_master" in src


def test_photo_selection_prefers_advertising_pocket() -> None:
    catalog = [
        {"asset_id": "tight", "filename": "Day_005.jpg", "sky_area": 0.06, "hard_coverage": 0.72, "architecture_centroid_x": 0.5},
        {"asset_id": "open", "filename": "Day_007.jpg", "sky_area": 0.27, "hard_coverage": 0.49, "architecture_centroid_x": 0.60},
    ]
    chosen = select_advertising_photo(catalog)
    assert chosen["photo_asset_id"] == "open"
    assert advertising_photo_score(catalog[1]) > advertising_photo_score(catalog[0])
    assert is_temple_production_exterior("ORNEK_00013.jpg") is False


def test_weak_drafts_are_not_selected() -> None:
    weak = {"id": "A", "critic": {"pass": False, "AGENCY_CAMPAIGN_FEEL": 4}}
    strong = {"id": "B", "critic": {"pass": True, "AGENCY_CAMPAIGN_FEEL": 9, "ART_DIRECTION": 8, "ORIGINALITY": 8, "WHOLE_CANVAS_DESIGN": 8, "PHOTO_GRAPHIC_INTEGRATION": 8, "TYPOGRAPHIC_MASS": 8, "COMMERCIAL_STORYTELLING": 8, "VISUAL_RHYTHM": 8, "PREMIUM_CHARACTER": 8, "BRAND_PRESENCE": 8, "CTA_RELATIONSHIP": 8}}
    ranked = rank_drafts([weak, strong])
    assert [item["id"] for item in ranked] == ["B"]
    assert draft_critic_pass(strong["critic"]) is True
    assert draft_critic_pass(weak["critic"]) is False


def test_plan_from_structure_uses_v4_schema() -> None:
    structure = {
        "structure_id": "s1",
        "concept_name": "Sky Monument Editorial",
        "reconstruction_mode": "SKY_VEIL",
        "campaign_group": {"x": 0.07, "y": 0.05, "w": 0.4, "h": 0.12},
        "type_scale_ratios": {"headline": 0.09},
        "group_relationships": "CAMPAIGN CONNECTED_TO OFFER",
    }
    plan = plan_from_structure(structure, photo={"asset_id": "p", "filename": "Day_007.jpg"})
    assert plan["schema"] == "RelationalCompositionPlanV1"
    assert plan["reconstruction_mode"] == "SKY_VEIL"
    assert plan["origin"]["y"] == 0.05
    assert infer_mode_from_structure({"campaign_group": {"y": 0.66}}) == "GROUND_PLANE"
