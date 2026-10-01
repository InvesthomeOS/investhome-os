"""Stage 4.0 tests — production-master gate, no Story from research proofs."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_MASTER_ID
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    STATUS_NO_PRODUCTION_MASTER,
    adapt_premium_master_to_format,
    is_production_premium_master,
    is_research_system_proof,
    research_proof_master_ids,
    select_production_premium_master,
    story_safe_zone_v1,
)
from investhome_api.services.creative_director.project_creative_master_library import add_master, empty_library, empty_master
from investhome_api.services.creative_director.stage4_0_proof import generate_stage4_0_format_proof


def test_masters_01_03_are_not_production_sources() -> None:
    library = empty_library(project_id="proj", project_name="The Temple")
    proof = empty_master(
        project_id="proj",
        master_name="The Temple — Premium Campaign 01",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        master_id=APPROVED_MASTER_ID,
    )
    proof["canonical_format"] = "4:5"
    add_master(library, proof)
    assert is_research_system_proof(proof) is True
    assert is_production_premium_master(proof) is False
    assert select_production_premium_master(library, project_id="proj") is None
    gated = adapt_premium_master_to_format(library, project_id="proj", execute=True)
    assert gated["status"] == STATUS_NO_PRODUCTION_MASTER
    assert gated["executed"] is False
    assert gated["format_child"] is None
    assert APPROVED_MASTER_ID in research_proof_master_ids()


def test_ingested_human_designer_master_is_production() -> None:
    library = empty_library(project_id="proj", project_name="The Temple")
    master = empty_master(
        project_id="proj",
        master_name="Temple production master",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
    )
    master["source"] = "HUMAN_DESIGNER"
    master["production_quality"] = True
    master["canonical_format"] = "4:5"
    add_master(library, master)
    selected = select_production_premium_master(library, project_id="proj")
    assert selected is not None
    assert selected["master_id"] == master["master_id"]
    assert is_research_system_proof(selected) is False


def test_story_safe_zone_is_not_a_taller_poster() -> None:
    zone = story_safe_zone_v1()
    assert zone["schema"] == "StorySafeZoneV1"
    assert zone["canvas"]["width"] / zone["canvas"]["height"] < 0.6
    assert "center the 4:5 composition inside 9:16" in zone["do_not"]
    well = zone["content_well"]
    assert well["y0"] >= zone["top_ui_territory"]["y1"]
    assert well["y1"] <= zone["bottom_ui_territory"]["y0"]


def test_proof_workflow_does_not_generate_artwork() -> None:
    src = inspect.getsource(generate_stage4_0_format_proof)
    assert "persist_gpt_image" not in src
    assert "render_svg_html_to_png" not in src
    assert "attach_format_child" not in src
    assert "add_master" not in src
    assert "STATUS_NO_PRODUCTION_MASTER" in src
