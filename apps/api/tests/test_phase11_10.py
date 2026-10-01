"""Phase 11.10 tests — feasibility only, no Hybrid V3, proofs untouched."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase11_10_master import REQUIRED_SCORE_FLOORS, generate_phase11_10_ai_native
from investhome_api.services.creative_director.phase11_10_provider import provider_capability_audit
from investhome_api.services.creative_director.phase11_10_strategy import CONCEPT_NAME, DAY001_ASSET_ID, ai_native_concepts


def test_not_hybrid_v3_and_new_source() -> None:
    assert CONCEPT_NAME != "THE_REGISTER"
    assert CONCEPT_NAME != "THE_LEDGER"
    assert DAY001_ASSET_ID == "5d26caf3-c237-4a78-9f3a-91f05dd24fa2"
    assert DAY001_ASSET_ID != "7696df34-0544-44b9-89f5-0d1b2523c412"
    assert len(ai_native_concepts()) == 5
    assert sum(1 for item in ai_native_concepts() if item["selected"]) == 1


def test_provider_uses_edits_not_generations() -> None:
    audit = provider_capability_audit()
    assert audit["edits"]["suitable_for_this_proof"] is True
    assert audit["generations"]["suitable_for_this_proof"] is False
    assert audit["edits"]["mask"]["supported"] is True


def test_master_does_not_promote_or_touch_hybrid() -> None:
    src = inspect.getsource(generate_phase11_10_ai_native)
    assert "compose_hybrid_v2" not in src
    assert "compose_hybrid_r1" not in src
    assert "phase11_4_compose" not in src
    assert "add_master" not in src
    assert "attach_format_child" not in src


def test_quality_floors_are_nine() -> None:
    assert REQUIRED_SCORE_FLOORS["PUBLISHABILITY"] == 9
    assert REQUIRED_SCORE_FLOORS["ART_DIRECTION"] == 9
