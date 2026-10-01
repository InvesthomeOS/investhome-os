"""Phase 5.5D — VISUAL_REPLACE_ONLY. No GPT Image. Master and price children unchanged."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.approved_master_lock import (
    APPROVED_R2_ASSET_ID,
    VISUAL_REPLACE_INSTRUCTION,
    unlock_for_intent,
)
from investhome_api.services.creative_director.creative_revision_controller import VISUAL_REPLACE, classify_revision_intent
from investhome_api.services.creative_director.master_revision_controller import classify_revision_command
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import (
    PRICE_R1_ASSET_ID,
    PRICE_R1_REVISION_ID,
    WORKFLOW_ID_55D,
    generate_visual_replace_proof_55d,
    visual_qa_from_occupancy,
    visual_replace_preservation,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.photo_to_master_compatibility import TRUE_FIT, rank_replacements
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID


def test_locks_parent_and_price_children() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRICE_R1_REVISION_ID == "9c93f0cb-4f4d-429b-bfd0-cfdd3c9e3f76"
    assert PRICE_R1_ASSET_ID == "3790af4c-2561-4845-a4c7-8ba3d478139d"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert WORKFLOW_ID_55D == "phase5_5d_visual_replace_proof"
    assert generate_visual_replace_proof_55d
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert "görseli yerine" in VISUAL_REPLACE_INSTRUCTION
    assert "Başka hiçbir şeyi değiştirme" in VISUAL_REPLACE_INSTRUCTION


def test_instruction_classifies_visual_replace_only() -> None:
    assert classify_revision_command(VISUAL_REPLACE_INSTRUCTION)["intent"] == "VISUAL_REPLACE_ONLY"
    assert classify_revision_intent(VISUAL_REPLACE_INSTRUCTION) == VISUAL_REPLACE
    assert unlock_for_intent("VISUAL_REPLACE_ONLY") == ("project_photo", "photo_crop", "photo_grade")


def test_no_gpt_image_or_redesign() -> None:
    import investhome_api.services.creative_director.phase5_5d_visual_replace_proof as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "must not call GPT Image" in src
    assert "VISUAL_REPLACE_ONLY" in src
    assert "VisualReplacePreservationV1" in src
    assert PRICE_R1_ASSET_ID in src


def test_preservation_only_photo_territory_may_change() -> None:
    spec = {
        "navy_field": {"px": [0, 0, 80, 120]},
        "headline": {"px": [8, 8, 70, 28]},
        "discount": {"px": [8, 32, 40, 50]},
        "discount_label": {"px": [8, 52, 70, 64]},
        "price": {"px": [8, 68, 70, 86]},
        "project_logo": {"px": [8, 88, 50, 100]},
        "unit_type": {"px": [8, 102, 50, 110]},
        "cta": {"px": [8, 112, 70, 118]},
    }
    master = Image.new("RGB", (200, 120), (39, 49, 60))
    ImageDraw.Draw(master).rectangle((80, 0, 200, 120), fill=(90, 110, 80))
    child = master.copy()
    ImageDraw.Draw(child).rectangle((80, 0, 200, 120), fill=(40, 80, 50))
    ok = visual_replace_preservation(master, child, spec)
    leaked = master.copy()
    ImageDraw.Draw(leaked).rectangle((10, 10, 40, 40), fill=(255, 0, 0))
    bad = visual_replace_preservation(master, leaked, spec)
    assert ok["pass"] is True
    assert ok["deltas"]["navy_field_delta"] == 0
    assert ok["deltas"]["photo_pixel_change_outside_territory"] == 0
    assert ok["photo_pixel_change_inside_territory"] == "EXPECTED"
    assert bad["pass"] is False


def test_true_fit_ranks_first() -> None:
    ranked = rank_replacements(
        [
            {"fit": "NO_FIT", "compatibility_score": 9.9, "asset_id": "a"},
            {"fit": TRUE_FIT, "compatibility_score": 8.1, "asset_id": "b"},
            {"fit": "CONDITIONAL_FIT", "compatibility_score": 9.0, "asset_id": "c"},
        ],
        top_n=5,
    )
    assert ranked[0]["asset_id"] == "b"
    qa = visual_qa_from_occupancy(
        {
            "hard_protected": 0.20,
            "bbox_h": 0.70,
            "centroid_x": 0.30,
            "crop_compatibility": 8.8,
            "subject_scale": 8.4,
            "subject_position": 9.5,
            "visual_balance_against_navy": 8.6,
            "overall": 8.5,
        },
        fit=TRUE_FIT,
    )
    assert qa["pass"] is True
    assert qa["scores"]["architecture_fidelity"] >= 9
