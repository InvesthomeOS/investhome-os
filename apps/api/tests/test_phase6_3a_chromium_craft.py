"""Phase 6.3A — Chromium craft calibration. No new Master. No V5. Proof B locked."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_3a_chromium_craft import (
    SELECTED_RENDERER,
    WORKFLOW_ID_63A,
    generate_phase6_3a_chromium_craft,
)
from investhome_api.services.creative_director.phase6_3a_craft import (
    APERTURE_TREATMENTS,
    TYPE_TREATMENTS,
    format_compatibility,
    revision_compatibility,
    scene_graph_properties,
)


def test_locks_and_no_new_master() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_63A == "phase6_3a_chromium_craft_calibration"
    assert SELECTED_RENDERER == "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM"
    assert generate_phase6_3a_chromium_craft


def test_does_not_create_v5_or_master_or_gpt_image() -> None:
    import investhome_api.services.creative_director.phase6_3a_chromium_craft as workflow
    import investhome_api.services.creative_director.phase6_3a_craft as craft

    src = inspect.getsource(workflow) + inspect.getsource(craft)
    assert "GraphicDesignCompositorV5" not in src
    assert "compose_relational_v4(" not in src
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "persist_gpt_image" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "CHROMIUM_CRAFT_NOT_READY" in inspect.getsource(workflow)
    assert "CHROMIUM_CRAFT_READY_FOR_MASTER" in inspect.getsource(workflow)


def test_proof_b_imported_locked() -> None:
    import investhome_api.services.creative_director.phase6_3a_chromium_craft as workflow
    import investhome_api.services.creative_director.phase6_3a_craft as craft

    src = inspect.getsource(workflow) + inspect.getsource(craft)
    assert "from investhome_api.services.creative_director.phase6_3_scene_graph import proof_b_html" in inspect.getsource(workflow)
    assert "_arc_d" in inspect.getsource(craft)
    assert "_ticks_svg" in inspect.getsource(craft)
    assert "LOCKED PASS" in src
    assert "do not recalibrate" in src.lower() or "Not redesigned" in src


def test_calibration_counts_and_stop_rule() -> None:
    assert len(APERTURE_TREATMENTS) >= 6
    assert [s["id"] for s in APERTURE_TREATMENTS] == ["A1", "A2", "A3", "A4", "A5", "A6"]
    assert len(TYPE_TREATMENTS) >= 4
    assert [s["id"] for s in TYPE_TREATMENTS] == ["T1", "T2", "T3", "T4"]
    src = inspect.getsource(
        __import__(
            "investhome_api.services.creative_director.phase6_3a_chromium_craft",
            fromlist=["generate_phase6_3a_chromium_craft"],
        ).generate_phase6_3a_chromium_craft
    )
    assert "stop_at = \"APERTURE\"" in src or "stop_at = 'APERTURE'" in src
    assert "Typography not run" in inspect.getsource(
        __import__("investhome_api.services.creative_director.phase6_3a_chromium_craft", fromlist=["_empty_block"])
    ) or "aperture did not pass" in src.lower() or "Aperture failed" in src


def test_scene_graph_new_properties() -> None:
    model = scene_graph_properties()
    kinds = set(model["object_kinds"])
    assert kinds >= {"PHOTO", "GRAPHIC_FIELD", "VECTOR_PATH", "DECORATION", "TEXT", "LOGO", "GROUP"}
    props = set(model["rendering_properties"])
    assert props >= {
        "blend_mode",
        "mask_ref",
        "filter_ref",
        "gradient_ref",
        "clip_ref",
        "opacity",
        "z_index",
        "transform",
        "optical_offset",
        "typographic_role",
        "relationship_anchor",
    }
    assert model["invariants"]["text_remains_text"] is True
    assert model["invariants"]["proof_b_arc_locked"] is True
    assert model["invariants"]["no_pillow_predarkening"] is True
    rev = revision_compatibility()
    assert rev["PRICE_EDIT_ONLY"]["status"] == "PASS"
    assert rev["COPY_EDIT_ONLY"]["status"] == "PASS"
    assert rev["VISUAL_REPLACE_ONLY"]["status"] == "PASS"
    assert rev["executed"] is False
    fmt = format_compatibility()
    assert fmt["implemented"] is False
    assert fmt["status"] == "PASS"
    assert set(fmt["formats"]) >= {"4:5", "1:1", "9:16", "16:9"}
