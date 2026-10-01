"""Phase 13.0 FINAL — production lock. No artwork. No proof chain."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase13_0_final_lock import (
    APPROVED_ROUTE,
    NEXT_PRODUCT_WORK,
    NON_PRODUCTION_FORMAT_ENGINES,
    PRODUCT_STATUS,
    ROUTING_STATUS,
    STATUS,
    UI_STATUS,
    live_creative_studio_lock,
)
from investhome_api.services.creative_director.premium_creative_product_model import (
    next_stage_roadmap,
    premium_revision_contract,
    product_model,
    research_archive_map,
    research_conclusion,
)
from investhome_api.services.creative_director.premium_format_recomposer_v1 import archived_story_proof
from investhome_api.services.creative_director.premium_studio import plan_studio_revision, revise_premium_campaign


def test_live_creative_studio_is_production_locked() -> None:
    lock = live_creative_studio_lock()
    assert lock["status"] == STATUS == "LIVE_CREATIVE_STUDIO_PRODUCTION_LOCKED"
    assert lock["ui"] == UI_STATUS == "HUMAN_APPROVED"
    assert lock["premium_campaigns"] == PRODUCT_STATUS == "PRODUCTION_READY"
    assert lock["natural_language_revision"] == PRODUCT_STATUS
    assert lock["family_wide_revision"] == PRODUCT_STATUS
    assert lock["download"] == PRODUCT_STATUS
    assert lock["routing"] == ROUTING_STATUS == "ACTIVE"
    assert lock["approved_route"] == APPROVED_ROUTE
    assert lock["ai_quick_creative"] == "PRESERVED"
    assert lock["next"] == NEXT_PRODUCT_WORK
    assert lock["require_additional_proof_before_product_work"] is False
    assert lock["new_creative_generated"] is False
    assert "13.1 proof" in lock["do_not_create"]


def test_product_model_points_next_work_to_ai_quick_creative() -> None:
    roadmap = next_stage_roadmap()
    model = product_model()
    assert roadmap["next"] == NEXT_PRODUCT_WORK
    assert roadmap["live_creative_studio"]["status"] == STATUS
    assert roadmap["stage_4_1"]["production_route"] is False
    assert model["live_creative_studio"]["routing"] == "ACTIVE"
    assert premium_revision_contract()["format_adaptation"]["production_route"] is False
    assert "13.1 proof" in research_conclusion()["do_not_create"]


def test_rejected_story_adaptation_is_off_production_route() -> None:
    archive = {item["id"]: item for item in research_archive_map()["paths"]}
    story = archive["PREMIUM_STORY_RECOMPOSER_EXPERIMENT"]
    recomposer = archive["PREMIUM_FORMAT_RECOMPOSER_AUTONOMOUS"]
    assert story["production_route"] is False
    assert story["status"] == "NON_PRODUCTION"
    assert recomposer["production_route"] is False
    assert archived_story_proof()["production_route"] is False
    studio = inspect.getsource(plan_studio_revision) + inspect.getsource(revise_premium_campaign)
    for engine in NON_PRODUCTION_FORMAT_ENGINES:
        assert engine not in studio
    assert "persist_gpt_image" not in inspect.getsource(plan_studio_revision)
