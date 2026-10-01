"""Phase 12.0 tests — ingest existing Investhome creative, no generation, no auto-activation."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA
from investhome_api.services.creative_director.phase12_0_ingestion import (
    PRODUCTION_MASTER_ID,
    SELECTED_ASSET_ID,
    SELECTED_FILENAME,
    generate_phase12_0_ingestion,
    ornek_00013_semantic_map,
    source_record,
)
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_MASTER_ID


def test_selected_original_is_existing_ornek_not_research_master() -> None:
    assert SELECTED_FILENAME == "ORNEK_00013.jpg"
    assert SELECTED_ASSET_ID == GRADE_A_MEDIA["ORNEK_00013.jpg"]
    assert PRODUCTION_MASTER_ID != APPROVED_MASTER_ID
    record = source_record()
    assert record["ORIGINAL_ASSET_ID"] == SELECTED_ASSET_ID
    assert record["ORIGINAL_ASSET_MODIFIED"] is False
    assert record["APPROVAL_STATUS"] == "PENDING HUMAN REVIEW"


def test_semantic_map_follows_design_and_does_not_invent_price() -> None:
    semantic = ornek_00013_semantic_map()
    by_id = {item["id"]: item for item in semantic["territories"]}
    assert by_id["PROJECT_PHOTO"]["present"] is True
    assert by_id["HEADLINE"]["present"] is True
    assert by_id["LOGO"]["present"] is True
    assert by_id["PRICE"]["present"] is False
    assert by_id["UNIT"]["present"] is False
    assert by_id["CTA"]["present"] is False
    assert semantic["never_originate_design_from_map"] is True
    assert "The Temple" in (by_id["PROJECT_PHOTO"].get("note") or "")


def test_ingestion_workflow_does_not_generate_or_activate() -> None:
    src = inspect.getsource(generate_phase12_0_ingestion)
    assert "persist_gpt_image" not in src
    assert "render_svg_html_to_png" not in src
    assert "attach_format_child" not in src
    assert "router_eligible" in src
    assert "PAUSED" in src
    assert "PENDING HUMAN REVIEW" in src
