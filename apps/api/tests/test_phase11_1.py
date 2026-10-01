"""Phase 11.1 — Creative Quality Proof. Honest fail is allowed. No format work."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_critic_v2 import PREMIUM_FLOORS, score_creative_v2
from investhome_api.services.creative_director.phase11_1_compose import html_copy_ok
from investhome_api.services.creative_director.phase11_1_master import FRESH_CRITIC, HONEST_SCORES, WORKFLOW_ID_11_1, generate_phase11_1_creative_quality_proof
from investhome_api.services.creative_director.phase11_1_strategy import (
    BANNED_MASTER_PHOTOS,
    CONCEPT_SENTENCE,
    DAY008_FILENAME,
    HEADLINE,
    creative_strategy,
)
from investhome_api.services.creative_director.stage3_canonical_pipeline import maybe_refuse_legacy_premium_generation, route_premium_generation, CANONICAL_PREMIUM_PATH


def test_strategy_and_fourth_idea() -> None:
    strategy = creative_strategy()
    assert "spire" in strategy["visual_idea"].casefold() or "İ" in strategy["visual_idea"]
    assert HEADLINE == "TARİH"
    assert DAY008_FILENAME not in BANNED_MASTER_PHOTOS
    assert "TYPE IN SKY" in strategy["not_reused"]
    assert CONCEPT_SENTENCE.count(".") >= 1
    assert "elegant premium" not in CONCEPT_SENTENCE.casefold()
    assert "luxury editorial" not in CONCEPT_SENTENCE.casefold()


def test_honest_scores_do_not_inflate_a_fail() -> None:
    result = score_creative_v2(HONEST_SCORES, anti_template="PASS", no_copy="PASS", project_reality="PASS")
    assert result["automated_pass"] is False
    assert result["status"] == "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW"
    assert HONEST_SCORES["PUBLISHABILITY"] < PREMIUM_FLOORS["PUBLISHABILITY"]
    assert HONEST_SCORES["PHOTO_INTEGRATION"] < PREMIUM_FLOORS["PHOTO_INTEGRATION"]
    assert FRESH_CRITIC["WOULD_PUBLISH"] == "NO"
    assert FRESH_CRITIC["PROFESSIONAL_CREATIVE_AGENCY"] == "NO"


def test_html_copy_gate_and_canonical_path() -> None:
    html = (
        "<html><body>TAR >H</p> %35 LANSMAN AVANTAJI 675.000 USD 2+1 DAİRE "
        "PROJEYİ KEŞFET TARİHİN RUHU, GELECEĞİN DEĞERİ. WASHINGTON D.C.</body></html>"
    )
    assert html_copy_ok(html) is True
    routed = route_premium_generation("The Temple için gerçekten premium, kreatif bir lansman reklamı hazırla.")
    assert routed["route"] == CANONICAL_PREMIUM_PATH
    assert CANONICAL_PREMIUM_PATH == "STAGE3_INTEGRATED_CAMPAIGN_PIPELINE"
    refusal = maybe_refuse_legacy_premium_generation(
        {"phase5": {"stage3_premium_generation_locked": True, "stage_3_executed": True}},
        user_text="The Temple için premium bir lansman reklamı hazırla.",
    )
    assert refusal and refusal["refuse"] is True
    assert WORKFLOW_ID_11_1 == "phase11_1_creative_quality_proof"
    src = inspect.getsource(generate_phase11_1_creative_quality_proof)
    assert "attach_format_child" not in src
    assert "persist_gpt_image" not in src
    assert "add_master" not in src
