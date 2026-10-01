"""Phase 11.2 — Creative Quality Proof 02. New idea. Honest fail is allowed. No format work. No R1."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_critic_v2 import PREMIUM_FLOORS, score_creative_v2
from investhome_api.services.creative_director.creative_failure_learning_v1 import PHASE_11_1_LEARNING
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID
from investhome_api.services.creative_director.phase11_2_compose import html_copy_ok
from investhome_api.services.creative_director.phase11_2_master import (
    EXTRA_FLOORS,
    FRESH_CRITIC,
    HONEST_SCORES,
    WORKFLOW_ID_11_2,
    generate_phase11_2_creative_quality_proof,
    score_proof_02,
)
from investhome_api.services.creative_director.phase11_2_strategy import (
    BANNED_DEVICES,
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY008_FILENAME,
    HEADLINE,
    HEADLINE_LINE_1,
    concept_evaluation_json,
    creative_strategy,
    selected_concept,
)


def test_learning_does_not_reinterpret_proof_01() -> None:
    assert PHASE_11_1_LEARNING["source_status"] == "CREATIVE_REJECTED"
    assert PHASE_11_1_LEARNING["incorrect_generalization"].startswith("architecture should never")
    assert "ENTIRE campaign system" in PHASE_11_1_LEARNING["correct_generalization"]
    assert "REVISE UNTIL PASS" in PHASE_11_1_LEARNING["not_system_behavior"]
    assert "CREATE R1" in PHASE_11_1_LEARNING["do_not"]


def test_new_idea_is_not_proof_01() -> None:
    strategy = creative_strategy()
    assert CONCEPT_NAME == "THE_SEAM"
    assert "letter" not in CONCEPT_SENTENCE.casefold()
    assert "TARİH" not in HEADLINE
    assert HEADLINE_LINE_1 == "İKİ ÇAĞ"
    assert "architecture as a letter" in BANNED_DEVICES
    assert "LOOKING CHAMBER" in strategy["not_reused"]
    assert DAY008_FILENAME == strategy["selected_real_assets"][0]["filename"]
    chosen = selected_concept()
    assert chosen["scores"]["PUBLISHABILITY_POTENTIAL"] >= 9
    assert chosen["campaign_system_test"] is True
    evaluation = concept_evaluation_json()
    assert evaluation["r1_created"] is False
    assert evaluation["not_shown_as_ABC"] is True
    rejected = [item for item in evaluation["concepts"] if not item["selected"]]
    assert len(rejected) == 6


def test_honest_scores_may_fail() -> None:
    result = score_proof_02(HONEST_SCORES, anti_template="PASS", no_copy="PASS", project_reality="PASS")
    assert result["human_approval"] == "REQUIRED"
    assert EXTRA_FLOORS["DEPTH"] == 8
    floors = {**PREMIUM_FLOORS, **EXTRA_FLOORS}
    if any(HONEST_SCORES[axis] < floor for axis, floor in floors.items()):
        assert result["automated_pass"] is False
    inflated = {axis: 10 for axis in HONEST_SCORES}
    passed = score_creative_v2(inflated, anti_template="PASS", no_copy="PASS", project_reality="PASS")
    assert passed["automated_pass"] is True
    assert FRESH_CRITIC["schema"] == "FreshBlindVisualReviewV1"


def test_html_copy_gate_and_no_format_work() -> None:
    html = (
        "<html><body>İKİ ÇAĞ BİR ADRES %35 LANSMAN AVANTAJI 675.000 USD 2+1 DAİRE "
        "PROJEYİ KEŞFET TARİHİN RUHU, GELECEĞİN DEĞERİ. WASHINGTON D.C.</body></html>"
    )
    assert html_copy_ok(html) is True
    assert html_copy_ok(html.replace("İKİ ÇAĞ", "TARİH")) is False
    src = inspect.getsource(generate_phase11_2_creative_quality_proof)
    assert "attach_format_child" not in src
    assert "persist_gpt_image" not in src
    assert "add_master" not in src
    assert WORKFLOW_ID_11_2 == "phase11_2_creative_quality_proof_02"
    assert PIPELINE_ID == "STAGE3_IDEA_FIRST_PREMIUM_PIPELINE"
