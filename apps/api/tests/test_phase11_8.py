"""Phase 11.8 tests — V2 capabilities, no campaign, no old compiler, proofs untouched."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID, hybrid_engine_v2_contract
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID
from investhome_api.services.creative_director.phase11_8_master import generate_phase11_8_engine_v2
from investhome_api.services.creative_director.project_object_extraction_v2 import CROP_BOX
from investhome_api.services.creative_director.responsive_commercial_hierarchy_v2 import hierarchy_layout, optical_engine_report


def test_engine_is_v2_and_experimental() -> None:
    contract = hybrid_engine_v2_contract()
    assert ENGINE_ID == "STAGE3_HYBRID_PREMIUM_ENGINE_V2"
    assert contract["canonical_stage3_router"] == "UNCHANGED"
    assert contract["status"] == "EXPERIMENTAL"
    assert "THE_LEDGER R2" in contract["does_not_generate"]


def test_same_day003_source() -> None:
    assert DAY003_ASSET_ID == "7346e259-f999-4fbb-a8d5-63708d4e0c81"
    assert CROP_BOX["width"] <= 0.50


def test_master_does_not_create_campaign_or_touch_old_compiler() -> None:
    src = inspect.getsource(generate_phase11_8_engine_v2)
    assert "phase11_4_compose" not in src
    assert "compose_hybrid_r1" not in src
    assert "compose_hybrid_proof" not in src
    assert "generate_non_project_field" not in src
    assert "add_master" not in src
    assert "attach_format_child" not in src


def test_hierarchy_optical_engine_rejects_tiny_cta() -> None:
    layout = hierarchy_layout()
    assert optical_engine_report(layout)["pass"] is True
    broken = dict(layout)
    broken["cta"] = dict(layout["cta"], size=11)
    assert optical_engine_report(broken)["pass"] is False
