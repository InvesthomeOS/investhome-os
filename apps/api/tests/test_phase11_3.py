"""Phase 11.3 — Commercial Creative System Correction. No artwork. No Proof 03."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.campaign_reading_path_v1 import campaign_reading_path_schema, validate_reading_path
from investhome_api.services.creative_director.commercial_design_dna_v1 import commercial_design_dna_library
from investhome_api.services.creative_director.commercial_system_gate import (
    advertisement_vs_poster_test,
    commercial_system_gate,
    thumbnail_test,
    visual_idea_gate,
)
from investhome_api.services.creative_director.commercial_typography_system_v1 import commercial_typography_system
from investhome_api.services.creative_director.creative_critic_v3 import PREMIUM_FLOORS as V3_FLOORS
from investhome_api.services.creative_director.creative_critic_v3 import score_creative_v3
from investhome_api.services.creative_director.detached_commercial_lockup_detector import detect_detached_commercial_lockup
from investhome_api.services.creative_director.fresh_critic_v3 import proof_01_fresh_v3_would_fail, proof_02_fresh_v3_would_fail, score_fresh_critic_v3
from investhome_api.services.creative_director.idea_first_pipeline import PIPELINE_ID, idea_first_pipeline
from investhome_api.services.creative_director.integrated_campaign_concept import (
    RENDER_FLOORS,
    empty_integrated_concept,
    score_concept_evaluation,
    temple_current_campaign_hierarchy_evaluation,
    validate_campaign_skeleton,
    validate_integrated_concept,
)
from investhome_api.services.creative_director.integrated_campaign_pipeline import INTEGRATED_PIPELINE_ID, STEPS
from investhome_api.services.creative_director.numeric_art_direction import assign_numeric_functions
from investhome_api.services.creative_director.phase11_3_foundation import WORKFLOW_ID_11_3, generate_phase11_3_commercial_creative_system
from investhome_api.services.creative_director.stage3_canonical_pipeline import CANONICAL_PREMIUM_PATH, route_premium_generation
from investhome_api.services.creative_director.stage3_failure_learning_v2 import stage3_failure_learning_v2


def test_systemic_learning_is_narrow() -> None:
    learning = stage3_failure_learning_v2()
    assert learning["systemic_failure_identified"] is True
    assert "COMPLETE COMMERCIAL CAMPAIGN SYSTEMS" in learning["systemic_conclusion"]
    assert "art first" in learning["root_cause"]
    assert "GENERATE PROOF 03 in this phase" in learning["do_not"]
    assert learning["proof_01"]["preserved"] is True
    assert learning["proof_02"]["preserved"] is True


def test_commercial_dna_and_concept_floors() -> None:
    dna = commercial_design_dna_library()
    assert dna["status"] == "READY"
    assert dna["grade_a_count"] == 6
    assert "giant %35 badge" in dna["overcorrection_bans"]
    assert RENDER_FLOORS["COMMERCIAL_MECHANISM"] == 9
    assert RENDER_FLOORS["READING_PATH"] == 9
    weak = score_concept_evaluation({"VISUAL_MECHANISM": 9, "COMMERCIAL_MECHANISM": 7, "PUBLISHABILITY_POTENTIAL": 9})
    assert weak["pass"] is False
    assert "COMMERCIAL_MECHANISM" in weak["floor_failures"]
    unset = empty_integrated_concept()
    assert validate_integrated_concept(unset)["pass"] is False
    skeleton = validate_campaign_skeleton(
        {
            "elements": {
                "PRIMARY_HERO": {
                    "ROLE": "photo",
                    "VISUAL_WEIGHT": "dominant",
                    "RELATIONSHIP_TO_PHOTO": "is the photo",
                    "RELATIONSHIP_TO_NEXT_ELEMENT": "leads to message",
                    "WHY_IT_EXISTS_AT_THAT_POSITION_IN_THE_READING_PATH": "placed in available negative space",
                }
            }
        }
    )
    assert skeleton["pass"] is False


def test_gates_catch_proof_01_and_02() -> None:
    visual_ok = visual_idea_gate(
        visual_mechanism="historic stone fused to new brick",
        photography_participates=True,
        feels_designed_without_copy=True,
    )
    assert visual_ok["pass"] is True
    commercial_fail = commercial_system_gate(
        composition_stronger_with_copy=False,
        elements_have_intentional_relationships=False,
        occupies_leftover_space_only=True,
    )
    assert commercial_fail["pass"] is False
    lockup = detect_detached_commercial_lockup(
        lockup_is_independent_vertical_stack=True,
        would_work_on_another_photo_unchanged=True,
    )
    assert lockup["pass"] is False
    assert lockup["proof_01_would_fail"] is True
    assert lockup["proof_02_would_fail"] is True
    thumb = thumbnail_test(one_clear_visual_event=True, one_clear_message=True, one_clear_commercial_hook=False)
    assert thumb["pass"] is False
    poster = advertisement_vs_poster_test("POSTER + SALES INFORMATION")
    assert poster["pass"] is False
    ad = advertisement_vs_poster_test("DESIGNED ADVERTISEMENT")
    assert ad["pass"] is True
    assert proof_01_fresh_v3_would_fail()["pass"] is False
    assert proof_02_fresh_v3_would_fail()["pass"] is False
    assert score_fresh_critic_v3(
        {
            "PROFESSIONAL_CREATIVE_AGENCY": "YES",
            "CLEAR_VISUAL_IDEA": "YES",
            "PROJECT_SPECIFIC": "YES",
            "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
            "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
            "CLEAR_READING_PATH": "YES",
            "PERSUASIVE": "YES",
            "MEMORABLE_AFTER_TWO_SECONDS": "YES",
            "LOOKS_LIKE_TEMPLATE": "NO",
            "WOULD_PUBLISH": "YES",
        }
    )["pass"] is True


def test_canonical_path_and_no_artwork() -> None:
    assert idea_first_pipeline()["status"] == "SUPERSEDED"
    assert PIPELINE_ID == "STAGE3_IDEA_FIRST_PREMIUM_PIPELINE"
    assert CANONICAL_PREMIUM_PATH == INTEGRATED_PIPELINE_ID == "STAGE3_INTEGRATED_CAMPAIGN_PIPELINE"
    assert STEPS[13] == "RENDER"
    routed = route_premium_generation("The Temple için gerçekten premium, kreatif bir lansman reklamı hazırla.")
    assert routed["route"] == INTEGRATED_PIPELINE_ID
    assert routed["executed"] is False
    hierarchy = temple_current_campaign_hierarchy_evaluation()
    assert hierarchy["selected"] == "ARCHITECTURE_LED"
    assert hierarchy["rendered"] is False
    assert assign_numeric_functions(hierarchy="ARCHITECTURE_LED")["assignment"]["%35"] == "rhythmic_device"
    assert commercial_typography_system()["status"] == "READY"
    assert campaign_reading_path_schema()["status"] == "READY"
    assert validate_reading_path({"stages": {}})["pass"] is False
    scores = {axis: 9 for axis in V3_FLOORS}
    passed = score_creative_v3(
        scores,
        anti_template="PASS",
        visual_idea_gate="PASS",
        commercial_system_gate="PASS",
        detached_lockup="PASS",
        thumbnail="PASS",
        advertisement_vs_poster="PASS",
        project_reality="PASS",
    )
    assert passed["automated_pass"] is True
    low = dict(scores)
    low["COMMERCIAL_INTEGRATION"] = 7
    rejected = score_creative_v3(
        low,
        anti_template="PASS",
        visual_idea_gate="PASS",
        commercial_system_gate="PASS",
        detached_lockup="PASS",
        thumbnail="PASS",
        advertisement_vs_poster="PASS",
        project_reality="PASS",
    )
    assert rejected["automated_pass"] is False
    src = inspect.getsource(generate_phase11_3_commercial_creative_system)
    assert "persist_gpt_image" not in src
    assert "render_html_to_png" not in src
    assert "attach_format_child" not in src
    assert "add_master" not in src
    assert WORKFLOW_ID_11_3 == "phase11_3_commercial_creative_system"
