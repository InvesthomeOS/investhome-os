"""Phase 6.3B — integrated Chromium craft. No new Master. A3 locked. No V5."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_3b_integrated_craft import (
    SELECTED_RENDERER,
    WORKFLOW_ID_63B,
    generate_phase6_3b_integrated_craft,
)
from investhome_api.services.creative_director.phase6_3b_scene import (
    A3_INTEGRATED,
    LOCKED_A3,
    TYPE_ROLES,
    TYPE_STUDIES,
    format_compatibility,
    revision_compatibility,
    structured_scene_validation,
)


def test_locks_and_no_new_master() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_63B == "phase6_3b_integrated_craft_proof"
    assert SELECTED_RENDERER == "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM"
    assert generate_phase6_3b_integrated_craft
    assert LOCKED_A3["id"] == "A3"
    assert A3_INTEGRATED["id"] == "A3-INTEGRATED"
    assert A3_INTEGRATED["blend"] == LOCKED_A3["blend"]


def test_does_not_create_v5_or_master_or_gpt_image() -> None:
    import investhome_api.services.creative_director.phase6_3b_integrated_craft as workflow
    import investhome_api.services.creative_director.phase6_3b_scene as scene

    src = inspect.getsource(workflow) + inspect.getsource(scene)
    assert "GraphicDesignCompositorV5" not in src
    assert "compose_relational_v4(" not in src
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "persist_gpt_image" not in src
    assert "CHROMIUM_INTEGRATED_CRAFT_READY" in inspect.getsource(workflow)
    assert "new_master_created" in inspect.getsource(workflow)
    assert LOCKED_A3["id"] == "A3"


def test_a3_geometry_locked() -> None:
    assert A3_INTEGRATED["blend"] == LOCKED_A3["blend"]
    assert A3_INTEGRATED.get("feather") == LOCKED_A3.get("feather")


def test_typography_system_roles_and_studies() -> None:
    assert list(TYPE_ROLES) == [
        "DISPLAY_HEADLINE",
        "OFFER_HERO",
        "OFFER_LABEL",
        "PRIMARY_PRICE",
        "UNIT_DESCRIPTOR",
        "CTA_LABEL",
        "EDITORIAL_CLOSURE",
    ]
    assert [s["id"] for s in TYPE_STUDIES] == ["T1", "T2", "T3", "T4"]
    scene = structured_scene_validation()
    kinds = {o["kind"] for o in scene["objects"]}
    assert kinds >= {"PHOTO", "GRAPHIC_FIELD", "VECTOR_PATH", "DECORATION", "TEXT", "LOGO", "GROUP"}
    assert scene["flattened_campaign_raster"] is False
    rev = revision_compatibility()
    assert rev["PRICE_EDIT_ONLY"]["status"] == "PASS"
    assert rev["COPY_EDIT_ONLY"]["status"] == "PASS"
    assert rev["VISUAL_REPLACE_ONLY"]["status"] == "PASS"
    assert rev["executed"] is False
    fmt = format_compatibility()
    assert fmt["implemented"] is False
    assert set(fmt["formats"]) >= {"4:5", "1:1", "9:16", "16:9"}
