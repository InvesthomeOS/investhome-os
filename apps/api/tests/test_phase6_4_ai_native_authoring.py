"""Phase 6.4 — AI-native structured authoring. No Master. No V5. GPT Image = 0."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_4_ai_native_authoring import (
    ARCHITECTURE,
    AUTHOR_TEMPERATURES,
    CRITIC_KEYS,
    FLOORS,
    SCENE_IDS,
    WORKFLOW_ID_64,
    generate_phase6_4_ai_native_authoring,
)
from investhome_api.services.creative_director.phase6_4_scene_v2 import (
    OBJECT_KINDS,
    SCENE_SCHEMA,
    bind_real_assets,
    compile_scene_html,
)


def test_locks_and_no_new_master() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_64 == "phase6_4_ai_native_structured_authoring"
    assert ARCHITECTURE == "AI_CREATIVE_SCENE_AUTHOR → SCENE_COMPILER → CHROMIUM"
    assert generate_phase6_4_ai_native_authoring
    assert SCENE_IDS == ("A", "B", "C")
    assert AUTHOR_TEMPERATURES["A"] != AUTHOR_TEMPERATURES["B"] != AUTHOR_TEMPERATURES["C"]


def test_schema_is_declarative_not_a_template() -> None:
    assert set(OBJECT_KINDS) == {
        "CANVAS",
        "PHOTO",
        "TEXT",
        "LOGO",
        "SVG_PATH",
        "GRAPHIC_FIELD",
        "DECORATION",
        "GROUP",
    }
    note = str(SCENE_SCHEMA.get("note") or "").lower()
    assert "does not prescribe" in note
    assert "layout families" in note


def test_does_not_reconstruct_or_create_master_or_gpt_image() -> None:
    import investhome_api.services.creative_director.phase6_4_ai_native_authoring as workflow
    import investhome_api.services.creative_director.phase6_4_scene_v2 as scene

    src = inspect.getsource(workflow) + inspect.getsource(scene)
    assert "GraphicDesignCompositorV5" not in src
    assert "compose_relational_v4(" not in src
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "new_master_created" in inspect.getsource(workflow)
    assert "AI_NATIVE_STRUCTURED_AUTHORING_READY" in inspect.getsource(workflow)
    compiler = inspect.getsource(compile_scene_html) + inspect.getsource(bind_real_assets)
    assert "rebalance(" not in compiler
    assert "creative_canvas_balance" not in compiler
    assert "cover_fit_canvas" not in compiler
    assert FLOORS["ARCHITECTURE_FIDELITY"] == 9
    assert set(CRITIC_KEYS) >= set(FLOORS)


def test_compiler_does_not_move_geometry() -> None:
    scene = {
        "objects": [
            {
                "id": "photo.day007",
                "kind": "PHOTO",
                "semantic": "project_photo",
                "geometry": {"x": 12, "y": 40, "w": 800, "h": 1000},
                "z_index": 0,
            }
        ]
    }
    bound = bind_real_assets(scene)
    geom = bound["objects"][0]["geometry"]
    assert geom == {"x": 12, "y": 40, "w": 800, "h": 1000}
    html = compile_scene_html(bound, photo_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert "left:12.00px" in html
    assert "top:40.00px" in html
    assert "c0afa1bf-b487-410c-be3d-91c31852550d" in str(bound["objects"][0].get("asset_id"))
    nested = {
        "objects": [
            {
                "id": "headline",
                "kind": "TEXT",
                "semantic": "headline",
                "geometry": {"x": 10, "y": 20, "w": 200, "h": 40},
                "render": {"text": "ALIRKEN KAZAN", "font": {"family": "Cormorant Garamond", "size": 48, "color": "#E3B873"}},
            }
        ]
    }
    html2 = compile_scene_html(nested, photo_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert "#E3B873" in html2
    assert "48px" in html2
    assert "ALIRKEN KAZAN" in html2
