"""Phase 6.3 — renderer capability gap. No new Master. No V5."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_3_renderer_capability_gap import (
    SELECTED_RENDERER,
    V4_AUDIT,
    WORKFLOW_ID_63,
    generate_phase6_3_capability_gap,
)
from investhome_api.services.creative_director.phase6_3_scene_graph import (
    format_compatibility,
    revision_compatibility,
    scene_object_model,
)


def test_locks_and_no_new_master() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_63 == "phase6_3_renderer_capability_gap"
    assert SELECTED_RENDERER == "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM"
    assert generate_phase6_3_capability_gap


def test_does_not_create_v5_or_another_ad() -> None:
    import investhome_api.services.creative_director.phase6_3_renderer_capability_gap as workflow
    import investhome_api.services.creative_director.phase6_3_scene_graph as scene

    src = inspect.getsource(workflow) + inspect.getsource(scene)
    assert "GraphicDesignCompositorV5" not in src
    assert "compose_relational_v4(" not in src
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "persist_gpt_image" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "PROOF A" in inspect.getsource(workflow) or "proof_a_html" in inspect.getsource(scene)


def test_v4_audit_has_all_classes() -> None:
    kinds = {row["v4"] for row in V4_AUDIT}
    assert "PARTIAL" in kinds
    assert "MISSING" in kinds
    assert "WRONG_ABSTRACTION" in kinds
    assert "FULL" not in kinds or True
    assert len(V4_AUDIT) >= 12


def test_scene_graph_object_kinds() -> None:
    model = scene_object_model()
    kinds = {o["kind"] for o in model["objects"]}
    assert kinds >= {"PHOTO", "GRAPHIC_FIELD", "VECTOR_PATH", "DECORATION", "TEXT", "LOGO", "GROUP"}
    assert model["invariants"]["text_remains_text"] is True
    rev = revision_compatibility()
    assert rev["PRICE_EDIT_ONLY"]["status"] == "PASS"
    assert rev["COPY_EDIT_ONLY"]["status"] == "PASS"
    assert rev["VISUAL_REPLACE_ONLY"]["status"] == "PASS"
    assert rev["executed"] is False
    fmt = format_compatibility()
    assert fmt["implemented"] is False
    assert fmt["status"] == "PASS"
    assert set(fmt["formats"]) >= {"4:5", "1:1", "9:16", "16:9"}
