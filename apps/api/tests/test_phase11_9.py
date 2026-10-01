"""Phase 11.9 tests — new campaign, V2 engine, no old compiler, proofs untouched."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_critic_v4 import PREMIUM_FLOORS, score_creative_v4
from investhome_api.services.creative_director.fresh_critic_v4 import REQUIRED, score_fresh_critic_v4
from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID
from investhome_api.services.creative_director.phase11_6_strategy import CONCEPT_NAME as LEDGER
from investhome_api.services.creative_director.phase11_9_compose import html_copy_ok
from investhome_api.services.creative_director.phase11_9_master import generate_phase11_9_hybrid_v2
from investhome_api.services.creative_director.phase11_9_strategy import (
    CONCEPT_NAME,
    DAY009_ASSET_ID,
    DAY009_CROP,
    SELECTION_FLOORS,
    concept_selection_status,
    hybrid_v2_concepts,
    selected_concept,
)


def test_engine_and_new_concept() -> None:
    assert ENGINE_ID == "STAGE3_HYBRID_PREMIUM_ENGINE_V2"
    assert CONCEPT_NAME == "THE_REGISTER"
    assert CONCEPT_NAME != LEDGER
    assert DAY009_ASSET_ID == "7696df34-0544-44b9-89f5-0d1b2523c412"
    assert DAY009_ASSET_ID != "7346e259-f999-4fbb-a8d5-63708d4e0c81"
    assert DAY009_CROP["width"] >= 0.50


def test_seven_concepts_one_selected() -> None:
    concepts = hybrid_v2_concepts()
    assert len(concepts) == 7
    assert sum(1 for item in concepts if item["selected"]) == 1
    assert concept_selection_status() == "SELECTED"
    chosen = selected_concept()
    for axis, floor in SELECTION_FLOORS.items():
        assert int(chosen["scores"][axis]) >= floor


def test_master_does_not_touch_old_compiler_or_promote() -> None:
    src = inspect.getsource(generate_phase11_9_hybrid_v2)
    assert "phase11_4_compose" not in src
    assert "compose_hybrid_r1" not in src
    assert "compose_hybrid_proof" not in src
    assert "add_master" not in src
    assert "attach_format_child" not in src
    assert "FIELD_PROMPT" not in src


def test_copy_gate_rejects_buttons_and_spine() -> None:
    good = (
        "<svg>MERTEBE THE TEMPLE WASHINGTON D.C. %35 LANSMAN AVANTAJI "
        "675.000 USD 2+1 DAİRE PROJEYİ KEŞFET TARİHİN RUHU, GELECEĞİN DEĞERİ.</svg>"
    )
    assert html_copy_ok(good) is True
    assert html_copy_ok(good.replace("<svg>", "<svg> rotate(90) ")) is False
    assert html_copy_ok(good.replace("<svg>", "<svg button ")) is False


def test_critic_v4_floors_and_no_inflation_path() -> None:
    assert PREMIUM_FLOORS["PUBLISHABILITY"] == 9
    assert PREMIUM_FLOORS["PHOTO_FIELD_RELATIONSHIP"] == 9
    low = {axis: 8 for axis in PREMIUM_FLOORS}
    result = score_creative_v4(
        low,
        anti_template="PASS",
        visual_idea_gate="PASS",
        commercial_system_gate="PASS",
        detached_lockup="PASS",
        thumbnail="PASS",
        advertisement_vs_poster="PASS",
        project_reality="PASS",
    )
    assert result["automated_pass"] is False
    assert result["status"] == "HYBRID_V2_CREATIVE_FAIL"
    assert result["router_eligible"] is False
    assert result["master"] is False


def test_fresh_v4_required_answers() -> None:
    assert REQUIRED["COMMERCIAL_INFORMATION_FEELS_ATTACHED"] == "NO"
    assert REQUIRED["TEMPLATE"] == "NO"
    assert REQUIRED["WOULD_PUBLISH"] == "YES"
    fail = score_fresh_critic_v4({key: "NO" for key in REQUIRED})
    assert fail["pass"] is False
