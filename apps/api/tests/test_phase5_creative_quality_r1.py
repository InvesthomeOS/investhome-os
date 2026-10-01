"""Phase 5.4B-R1 — reference-grounded director gates."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.generative_creative_director_v2 import (
    assign_moodboards,
    audit_phase54b_reference_influence,
    markup_forbidden_reasons,
)
from investhome_api.services.creative_director.phase5_creative_quality_r1 import (
    WORKFLOW_ID_54B_R1,
    generate_creative_quality_r1_4x5,
)


def test_white_card_and_bottom_dump_are_forbidden() -> None:
    card = "<div style='position:absolute;background-color:rgba(255,255,255,0.7);border-radius:10px'>x</div>"
    dump = "<div style='position:absolute;bottom:20px;left:20px'>x</div><a href='#'>CTA</a>"
    assert "translucent_white_information_rectangle" in markup_forbidden_reasons(card)
    assert "floating_property_card" in markup_forbidden_reasons(card)
    assert "bottom_left_information_dump" in markup_forbidden_reasons(dump)
    assert "web_style_cta" in markup_forbidden_reasons(dump)
    clean = "<div style='position:absolute;top:80px;right:64px;width:420px'><h1>ALIRKEN KAZAN</h1></div>"
    assert markup_forbidden_reasons(clean) == []


def test_moodboards_are_not_identical() -> None:
    retrieved = [{"reference_id": f"r{i}", "filename": f"ORNEK_{i:05d}.jpg"} for i in range(8)]
    boards = assign_moodboards(retrieved)
    sets = {tuple(x.get("reference_id") for x in boards[k]["references"]) for k in ("A2", "B2", "C2")}
    assert len(sets) == 3
    assert all(len(boards[k]["references"]) == 4 for k in ("A2", "B2", "C2"))
    assert "composition" in boards["A2"]["roles"]


def test_54b_audit_reports_lost_reference_influence() -> None:
    audit = audit_phase54b_reference_influence(
        [
            {
                "key": "B",
                "reference_influences": ["negative space"],
                "markup": "<div style='background-color:rgba(255,255,255,0.7);border-radius:10px'>x</div>",
            }
        ],
        retrieved=[{"dna": {"REUSABLE_PRINCIPLES": ["balance"]}}],
    )
    assert audit["schema"] == "ReferenceInfluenceAuditV1"
    assert audit["status"] == "REFERENCES_REDUCED_TO_GENERIC_TEXT_THEN_LOST"
    assert audit["rows"]
    assert audit["rows"][0]["result"] == "FAILURE"


def test_r1_modules_do_not_use_gpt_image_as_designer() -> None:
    import investhome_api.services.creative_director.phase5_creative_quality_r1 as prod
    import investhome_api.services.creative_director.generative_creative_director_v2 as director

    assert "generate_image" not in inspect.getsource(prod)
    assert "edit_image" not in inspect.getsource(prod)
    assert WORKFLOW_ID_54B_R1 in inspect.getsource(prod)
    assert "request_composition_blueprint" in inspect.getsource(director)
    assert generate_creative_quality_r1_4x5.__name__ == "generate_creative_quality_r1_4x5"
