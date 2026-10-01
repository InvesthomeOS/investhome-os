"""Phase 5.5B gates. Visual draft then V3 reconstruction. Production GPT Image = 0."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase5_5b_visual_draft_reconstruction import (
    WORKFLOW_ID_55B,
    generate_visual_draft_reconstruction_55b,
)
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.visual_composition_draft import (
    VERTICAL_HARMONY,
    draft_critic_pass,
    reconstruction_spec_from_structure,
    visible_logo_alpha_box,
)


def test_keeps_vertical_harmony_and_locked_assets() -> None:
    assert VERTICAL_HARMONY["concept_name"] == "Vertical Harmony"
    assert VERTICAL_HARMONY["id"] == "AD1"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2
    assert generate_visual_draft_reconstruction_55b


def test_draft_uses_image_model_reconstruction_does_not() -> None:
    import investhome_api.services.creative_director.phase5_5b_visual_draft_reconstruction as workflow
    import investhome_api.services.creative_director.visual_composition_draft as draft

    draft_src = inspect.getsource(draft.generate_visual_composition_draft)
    flow_src = inspect.getsource(workflow.generate_visual_draft_reconstruction_55b)
    module_src = inspect.getsource(workflow)
    assert "edit_image" in draft_src
    assert "images/generations" not in flow_src
    assert "VISUAL_DRAFT_NOT_GOOD_ENOUGH" in flow_src
    assert "art_plan=recon_spec.get(\"art_plan\")" in flow_src or "art_plan=" in flow_src
    assert "production reconstruction must not call GPT Image" in flow_src
    assert WORKFLOW_ID_55B in module_src
    assert "three new" not in module_src.lower()
    assert inspect.signature(compose_graphic_design_v3).parameters["art_plan"].default is None


def test_draft_critic_gate() -> None:
    weak = {key: 7 for key in (
        "professional_art_direction",
        "whole_canvas_composition",
        "image_design_integration",
        "typography_mass",
        "hierarchy",
        "commercial_storytelling",
        "brand_relationship",
        "cta_relationship",
        "premium_character",
        "reference_craft_transfer",
    )}
    weak.update({"TEXT_DUMP_FEEL": 1, "LISTING_FEEL": 1, "UI_FEEL": 1, "TEMPLATE_FEEL": 1, "CORNER_CLUSTER_FEEL": 1})
    assert draft_critic_pass(weak) is False
    strong = {key: 8 for key in weak}
    strong.update({"TEXT_DUMP_FEEL": 2, "LISTING_FEEL": 2, "UI_FEEL": 2, "TEMPLATE_FEEL": 3, "CORNER_CLUSTER_FEEL": 2})
    assert draft_critic_pass(strong) is True
    clustered = dict(strong)
    clustered["CORNER_CLUSTER_FEEL"] = 3
    assert draft_critic_pass(clustered) is False


def test_reconstruction_spec_reads_draft_geometry_not_blueprint() -> None:
    structure = {
        "boxes": {
            "headline": {"x": 0.06, "y": 0.04, "w": 0.36, "h": 0.16},
            "discount": {"x": 0.06, "y": 0.22, "w": 0.14, "h": 0.05},
            "price": {"x": 0.06, "y": 0.28, "w": 0.30, "h": 0.05},
            "cta": {"x": 0.06, "y": 0.36, "w": 0.22, "h": 0.02},
            "project_logo": {"x": 0.06, "y": 0.40, "w": 0.16, "h": 0.06},
        },
        "alignment_side": "left",
        "vertical_axis_x": 0.08,
    }
    spec = reconstruction_spec_from_structure(structure)
    plan = spec["art_plan"]
    assert spec["geometry_source"] == "visual_composition_draft"
    assert plan["typography"]["display_scale"] >= 0.06
    assert plan["territories"]["type_limit_y"] >= 0.36
    assert plan["logo"]["placement"] == "column_end"


def test_visible_logo_uses_alpha_not_container() -> None:
    from PIL import Image

    canvas = Image.new("RGBA", (200, 80), (0, 0, 0, 0))
    for x in range(20, 60):
        for y in range(10, 40):
            canvas.putpixel((x, y), (255, 255, 255, 255))
    tight = visible_logo_alpha_box(canvas, (0, 0, 200, 80))
    assert tight[2] - tight[0] < 200
    assert tight[3] - tight[1] <= 80
    assert (tight[2] - tight[0]) * (tight[3] - tight[1]) < 200 * 80
