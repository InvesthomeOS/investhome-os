"""Phase 11.4 — Creative Quality Proof 03. Integrated campaign. Honest fail is allowed. No format work. No R1."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_critic_v3 import PREMIUM_FLOORS, score_creative_v3
from investhome_api.services.creative_director.integrated_campaign_concept import RENDER_FLOORS
from investhome_api.services.creative_director.integrated_campaign_pipeline import INTEGRATED_PIPELINE_ID
from investhome_api.services.creative_director.phase11_4_compose import html_copy_ok
from investhome_api.services.creative_director.phase11_4_master import (
    FRESH_ANSWERS,
    HONEST_SCORES,
    WORKFLOW_ID_11_4,
    generate_phase11_4_creative_quality_proof,
)
from investhome_api.services.creative_director.phase11_4_strategy import (
    BANNED_DEVICES,
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY009_FILENAME,
    HEADLINE,
    HEADLINE_LINE_1,
    HIERARCHY,
    concept_evaluation_json,
    concept_passes_render_floors,
    creative_strategy,
    selected_concept,
)
from investhome_api.services.creative_director.stage3_canonical_pipeline import CANONICAL_PREMIUM_PATH


def test_does_not_revise_proof_01_or_02() -> None:
    strategy = creative_strategy()
    assert strategy["proof_01"] == "PRESERVED / REJECTED"
    assert strategy["proof_02"] == "PRESERVED / REJECTED"
    assert "Day_008 automatic reuse" in BANNED_DEVICES
    assert "PHOTO + LEFT COLUMN" in BANNED_DEVICES


def test_new_integrated_concept_uses_day_009() -> None:
    assert CONCEPT_NAME == "THE_THRESHOLD"
    assert "letter" not in CONCEPT_SENTENCE.casefold()
    assert "TARİH" not in HEADLINE
    assert HEADLINE_LINE_1 == "GİRİNCE"
    assert HIERARCHY == "ARCHITECTURE_LED"
    chosen = selected_concept()
    assert "Day_009" in chosen["project_photo_role"]
    assert "Day_008" not in chosen["project_photo_role"]
    assert DAY009_FILENAME == creative_strategy()["selected_real_assets"][0]["filename"]
    assert chosen["scores"]["COMMERCIAL_MECHANISM"] >= 9
    assert concept_passes_render_floors(chosen) is True
    evaluation = concept_evaluation_json()
    assert evaluation["r1_created"] is False
    assert evaluation["rendered_alternatives"] is False
    assert evaluation["day_008_automatically_reused"] is False
    rejected = [item for item in evaluation["concepts"] if not item["selected"]]
    assert len(rejected) == 6
    for axis, floor in RENDER_FLOORS.items():
        assert chosen["scores"][axis] >= floor


def test_honest_scores_may_fail() -> None:
    result = score_creative_v3(
        HONEST_SCORES,
        anti_template="PASS",
        visual_idea_gate="PASS",
        commercial_system_gate="FAIL",
        detached_lockup="PASS",
        thumbnail="FAIL",
        advertisement_vs_poster="FAIL",
        project_reality="PASS",
    )
    assert result["human_approval"] == "REQUIRED"
    assert result["automated_pass"] is False
    floors = dict(PREMIUM_FLOORS)
    if any(HONEST_SCORES[axis] < floor for axis, floor in floors.items() if axis in HONEST_SCORES):
        assert result["automated_pass"] is False
    assert FRESH_ANSWERS["WOULD_PUBLISH"] == "NO"
    assert FRESH_ANSWERS["COMMERCIAL_MESSAGE_PART_OF_IDEA"] == "NO"


def test_html_copy_gate_pipeline_and_no_format_work() -> None:
    html = (
        "<html><body>GİRİNCE EV %35 LANSMAN AVANTAJI 675.000 USD 2+1 DAİRE "
        "PROJEYİ KEŞFET TARİHİN RUHU, GELECEĞİN DEĞERİ. WASHINGTON D.C.</body></html>"
    )
    assert html_copy_ok(html) is True
    assert html_copy_ok(html.replace("GİRİNCE", "TARİH")) is False
    src = inspect.getsource(generate_phase11_4_creative_quality_proof)
    assert "attach_format_child" not in src
    assert "persist_gpt_image" not in src
    assert "add_master" not in src
    assert WORKFLOW_ID_11_4 == "phase11_4_creative_quality_proof_03"
    assert CANONICAL_PREMIUM_PATH == INTEGRATED_PIPELINE_ID == "STAGE3_INTEGRATED_CAMPAIGN_PIPELINE"
