"""Phase 11.6 — Hybrid Premium Engine. Quality proof only. No format work. No old compiler."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.hybrid_premium_engine_v1 import ENGINE_ID, PIPELINE_STEPS
from investhome_api.services.creative_director.phase11_6_compose import html_copy_ok
from investhome_api.services.creative_director.phase11_6_master import generate_phase11_6_hybrid_premium_proof
from investhome_api.services.creative_director.phase11_6_strategy import (
    BANNED_MECHANISMS,
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    HEADLINE,
    concept_evaluation_json,
    selected_concept,
)
from investhome_api.services.creative_director.project_reality_firewall_v1 import evaluate_firewall
from investhome_api.services.creative_director.stage3_canonical_pipeline import CANONICAL_PREMIUM_PATH


def test_engine_id_and_pipeline() -> None:
    assert ENGINE_ID == "STAGE3_HYBRID_PREMIUM_ENGINE_V1"
    assert "NON_PROJECT_CREATIVE_FIELD_GENERATION" in PIPELINE_STEPS
    assert CANONICAL_PREMIUM_PATH != ENGINE_ID


def test_selected_concept_is_hybrid_not_rejected_proofs() -> None:
    assert CONCEPT_NAME == "THE_LEDGER"
    folded = CONCEPT_SENTENCE.casefold()
    assert "letter" not in folded
    assert "portal" not in folded
    assert "threshold" not in folded
    assert "seam" not in folded
    assert HEADLINE == "TAŞ TEMİNAT"
    evaluation = concept_evaluation_json()
    assert evaluation["rendered_alternatives"] is False
    assert len(evaluation["concepts"]) == 5
    assert selected_concept()["selected"] is True
    assert "Proof 03 threshold/portal campaign" in BANNED_MECHANISMS


def test_firewall_fail_closed() -> None:
    failed = evaluate_firewall({"mode": "unavailable", "flags": {}})
    assert failed["status"] == "FAIL"
    building = evaluate_firewall(
        {"mode": "vision", "flags": {"contains_building": True, "contains_interior": False}}
    )
    assert building["status"] == "FAIL"
    clean = evaluate_firewall(
        {
            "mode": "vision",
            "flags": {
                "contains_building": False,
                "contains_interior": False,
                "contains_exterior_architecture": False,
                "contains_project_logo": False,
                "contains_project_facts": False,
                "contains_readable_text": False,
                "contains_numbers": False,
                "contains_windows_or_facade": False,
                "contains_spire_or_tower": False,
            },
        }
    )
    assert clean["status"] == "PASS"


def test_svg_is_not_old_compiler() -> None:
    src = inspect.getsource(generate_phase11_6_hybrid_premium_proof)
    assert "phase11_4_compose" not in src
    assert "phase11_1_compose" not in src
    assert "phase11_2_compose" not in src
    assert "attach_format_child" not in src
    assert "add_master" not in src
    good = (
        "<svg data-semantic=\"project_photo\" data-semantic=\"creative_field\">"
        "TAŞ TEMİNAT THE TEMPLE WASHINGTON D.C. %35 LANSMAN AVANTAJI 675.000 USD "
        "2+1 DAİRE PROJEYİ KEŞFET TARİHİN RUHU, GELECEĞİN DEĞERİ.</svg>"
    )
    assert html_copy_ok(good) is True
    assert html_copy_ok("position:absolute " + good) is False
