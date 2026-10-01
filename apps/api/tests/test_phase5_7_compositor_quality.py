"""Phase 5.7 — compositor quality engines. No GPT Image. Existing Master unchanged."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.blueprint_render_fidelity import (
    apply_critic_calibration,
    blueprint_render_fidelity,
    craft_gap_report,
    detect_layout_faults,
    reference_craft_gap,
    score_calibration_render,
)
from investhome_api.services.creative_director.brand_cta_engines import compose_editorial_cta, integrate_brand
from investhome_api.services.creative_director.commercial_offer_composer import offer_layout, offer_layout_v2
from investhome_api.services.creative_director.compositor_relational_v4 import compose_relational_v4
from investhome_api.services.creative_director.creative_canvas_balance_v2 import creative_canvas_balance_v2
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_relationship_system import (
    compositional_gravity,
    graph_from_reference_map,
    groups_from_objects,
    reading_flow,
    relationship,
    temple_relationship_graph,
)
from investhome_api.services.creative_director.full_frame_architectural_family import full_frame_family_spec
from investhome_api.services.creative_director.graphic_field_engine import apply_graphic_fields, plan_fields
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_ASSET_ID, PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_7_compositor_quality import WORKFLOW_ID_57, generate_compositor_quality_57
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.premium_art_direction import apply_layout_fault_caps
from investhome_api.services.creative_director.reference_composition_map import build_reference_composition_map
from investhome_api.services.creative_director.typographic_composition_engine import compose_campaign_type
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID


def _occ(size: tuple[int, int] = (400, 500)) -> dict:
    w, h = size
    hard = Image.new("L", (w, h), 0)
    ImageDraw.Draw(hard).rectangle((int(w * 0.42), int(h * 0.22), int(w * 0.78), int(h * 0.78)), fill=200)
    sky = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sky).rectangle((0, 0, w, int(h * 0.28)), fill=180)
    return {
        "architecture_centroid_x": 0.58,
        "layers": {"hard_protected": hard, "collision_core": hard, "sky": sky},
    }


def _scattered() -> dict:
    return {
        "headline": {"bounds": {"x": 0.05, "y": 0.05, "w": 0.22, "h": 0.07}},
        "discount": {"bounds": {"x": 0.87, "y": 0.06, "w": 0.08, "h": 0.04}},
        "discount_label": {"bounds": {"x": 0.79, "y": 0.10, "w": 0.15, "h": 0.02}},
        "price": {"bounds": {"x": 0.05, "y": 0.20, "w": 0.16, "h": 0.04}},
        "unit_type": {"bounds": {"x": 0.05, "y": 0.25, "w": 0.10, "h": 0.02}},
        "project_logo": {"bounds": {"x": 0.72, "y": 0.20, "w": 0.16, "h": 0.07}},
        "cta": {"bounds": {"x": 0.05, "y": 0.92, "w": 0.18, "h": 0.03}},
    }


def _grouped() -> dict:
    return {
        "headline": {"bounds": {"x": 0.06, "y": 0.05, "w": 0.28, "h": 0.08}},
        "discount": {"bounds": {"x": 0.06, "y": 0.16, "w": 0.10, "h": 0.04}},
        "discount_label": {"bounds": {"x": 0.06, "y": 0.21, "w": 0.18, "h": 0.02}},
        "price": {"bounds": {"x": 0.06, "y": 0.24, "w": 0.20, "h": 0.04}},
        "project_logo": {"bounds": {"x": 0.30, "y": 0.16, "w": 0.14, "h": 0.05}},
        "unit_type": {"bounds": {"x": 0.06, "y": 0.30, "w": 0.12, "h": 0.02}},
        "cta": {"bounds": {"x": 0.06, "y": 0.34, "w": 0.18, "h": 0.02}},
    }


def test_locks_existing_masters() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRICE_R1_REVISION_ID == "9c93f0cb-4f4d-429b-bfd0-cfdd3c9e3f76"
    assert PRICE_R1_ASSET_ID == "3790af4c-2561-4845-a4c7-8ba3d478139d"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_57 == "phase5_7_compositor_quality"
    assert generate_compositor_quality_57


def test_no_gpt_image_or_master_overwrite() -> None:
    import investhome_api.services.creative_director.phase5_7_compositor_quality as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "must not call GPT Image" in src
    assert "existing_master_changed" in src
    assert "new_temple_master_created" in src
    assert "PARENT_MASTER_ID" in src


def test_reference_composition_map_is_geometry() -> None:
    image = Image.new("RGB", (200, 250), (30, 40, 50))
    ImageDraw.Draw(image).rectangle((10, 10, 80, 70), fill=(240, 240, 230))
    ImageDraw.Draw(image).rectangle((12, 80, 70, 120), fill=(220, 180, 80))
    cmap = build_reference_composition_map(image, filename="ORNEK_TEST.jpg")
    assert cmap["schema"] == "ReferenceCompositionMapV1"
    assert "dominant_compositional_axis" in cmap
    assert isinstance(cmap["center_of_visual_gravity"]["overall"], (list, tuple))
    assert "beautiful" not in str(cmap).lower()
    graph = graph_from_reference_map(cmap)
    assert graph["schema"] == "CreativeRelationshipGraphV1"
    assert graph["edges"]


def test_relationship_graph_and_groups() -> None:
    edge = relationship("BELONGS_TO", "price", "offer_group", strength=1.0, visual_reason="offer statement", preferred_distance=0.02, preferred_alignment="lockup")
    assert edge["collision_behavior"] == "KEEP_GROUP"
    graph = temple_relationship_graph(mode="SKY_VEIL")
    types = {e["relationship_type"] for e in graph["edges"]}
    assert "CONNECTED_TO" in types and "BALANCES" in types and "CLOSES" in types
    groups = groups_from_objects(_grouped(), mode="SKY_VEIL")
    ids = {g["group_id"] for g in groups}
    assert ids == {"CAMPAIGN_GROUP", "OFFER_GROUP", "BRAND_GROUP", "ACTION_GROUP"}
    offer = next(g for g in groups if g["group_id"] == "OFFER_GROUP")
    assert offer["maximum_separation"] <= 0.08
    assert "discount" in offer["children"] and "price" in offer["children"]


def test_gravity_and_reading_flow() -> None:
    grav = compositional_gravity(_occ(), _grouped())
    assert grav["schema"] == "CompositionalGravityEngineV1"
    assert grav["corner_fill_forbidden"] is True
    assert len(grav["overall_center_of_mass"]) == 2
    flow = reading_flow(_grouped())
    assert flow["schema"] == "CreativeReadingFlowV1"
    assert flow["rejected"] is False
    assert flow["commercial_islands"] is False
    island = reading_flow(_scattered())
    assert island["rejected"] is True or island["commercial_islands"] is True


def test_typographic_and_graphic_field() -> None:
    image = Image.new("RGB", (200, 200), (20, 24, 30))
    draw = ImageDraw.Draw(image)
    font = build_font_registry()
    from investhome_api.services.creative_director.creative_font_registry import font_for_role

    display = font_for_role(font, "DISPLAY_SERIF", 28)
    pack = compose_campaign_type(draw, origin=(10, 10), first="ALIRKEN", last="KAZAN", display=display, display_sm=display)
    assert pack["schema"] == "TypographicCompositionEngineV1"
    assert pack["text_as_visual_form"] is True
    fields = plan_fields("SKY_VEIL")
    kinds = " ".join(f["kind"] for f in fields)
    assert "panel" not in kinds and "pill" not in kinds and "card" not in kinds
    applied = apply_graphic_fields(image, _occ((200, 200)), "SKY_VEIL")
    assert applied["schema"] == "GraphicFieldEngineV1"
    assert applied["geometry_modified"] is False


def test_offer_v2_brand_cta() -> None:
    metrics = {
        "discount": {"width": 40, "height": 20, "text": "%35"},
        "discount_label": {"width": 80, "height": 8, "text": "LANSMAN AVANTAJI"},
        "price": {"width": 90, "height": 18, "text": "675.000 USD"},
    }
    v1 = offer_layout(
        origin=(20, 20),
        alignment="left",
        metrics={**metrics, "unit_type": {"width": 40, "height": 8}, "headline": {"width": 80, "height": 20}},
        spacing={},
        canvas=(400, 500),
        family_id="X",
    )
    assert v1["schema"] == "CommercialOfferComposerV1"
    v2 = offer_layout_v2(origin=(20, 80), metrics=metrics, canvas=(400, 500))
    assert v2["schema"] == "CommercialOfferComposerV2"
    assert v2["independent_objects"] is False
    assert v2["primary_commercial_anchor"] == "discount"
    brand = integrate_brand(
        campaign_bbox=(20, 20, 120, 60),
        offer_bbox=(20, 80, 160, 140),
        architecture_x=0.55,
        canvas=(400, 500),
        logo_size=(60, 24),
        mode="SKY_VEIL",
    )
    assert brand["find_free_rectangle"] is False
    assert brand["immutable_logo"] is True
    cta = compose_editorial_cta(
        offer_bbox=(20, 80, 160, 140),
        unit_size=(50, 10),
        cta_size=(80, 12),
        canvas=(400, 500),
        mode="SKY_VEIL",
    )
    assert cta["pill"] is False and cta["button_rectangle"] is False and cta["floating_ui"] is False


def test_canvas_balance_v2_roles() -> None:
    image = Image.new("RGB", (200, 300), (80, 90, 70))
    objects = _grouped()
    field = Image.new("L", (200, 300), 0)
    ImageDraw.Draw(field).rectangle((0, 0, 200, 90), fill=180)
    occ = _occ((200, 300))
    bal = creative_canvas_balance_v2(image, objects, field, occ, groups_from_objects(objects, mode="SKY_VEIL"))
    assert bal["schema"] == "CreativeCanvasBalanceV2"
    roles = {r["space_role"] for r in bal["regions"]}
    assert any(
        r in roles
        for r in (
            "ARCHITECTURE_PROTECTION",
            "HIERARCHY_SUPPORT",
            "VISUAL_PAUSE",
            "DEAD_SPACE",
            "CROP_BALANCE",
            "READING_FLOW",
            "BRAND_BREATHING",
        )
    )


def test_fidelity_and_craft_gap() -> None:
    groups = groups_from_objects(_grouped(), mode="SKY_VEIL")
    flow = reading_flow(_grouped())
    fid = blueprint_render_fidelity(_grouped(), groups, flow, field_mass=0.2, intended_mode="SKY_VEIL")
    assert fid["schema"] == "BlueprintRenderFidelityV1"
    assert fid["pass"] is True
    old = blueprint_render_fidelity(
        _scattered(),
        groups_from_objects(_scattered(), mode="SKY_VEIL"),
        reading_flow(_scattered()),
        field_mass=0.05,
        intended_mode="SKY_VEIL",
    )
    assert old["pass"] is False
    gap = craft_gap_report({"overall": 0.4, "group_cohesion": 0.4}, {"overall": 0.15, "group_cohesion": 0.12})
    assert gap["schema"] == "ReferenceCraftGapV1"
    assert gap["IMPROVEMENT"] > 0
    dummy = {
        "typographic_mass": 0.1,
        "graphic_mass": 0.1,
        "distance_related": 0.12,
        "dominant_compositional_axis": "vertical",
        "photo_type_interaction": "type_on_tonal_support",
        "negative_space_function": "protects_photo_mass",
    }
    ref_gap = reference_craft_gap([dummy], dummy)
    assert "overall" in ref_gap


def test_critic_calibration_caps_weak_layouts() -> None:
    faults = detect_layout_faults(_scattered(), field_mass=0.04, islands=True)
    assert "SCATTERED_ELEMENT_LAYOUT" in faults or "CORNER_DISTRIBUTION" in faults
    assert "FALSE_WHOLE_CANVAS_USAGE" in faults or "DETACHED_CTA" in faults
    scored = apply_critic_calibration(
        {"professional_art_direction": 8, "whole_canvas_composition": 8, "image_design_integration": 8},
        faults,
    )
    assert scored["calibration_capped"] is True
    assert scored["professional_art_direction"] <= 7
    assert scored["whole_canvas_composition"] <= 7
    assert scored["image_design_integration"] <= 7
    hooked = apply_layout_fault_caps(
        {"professional_art_direction": 9, "whole_canvas_composition": 9, "image_design_integration": 8},
        _scattered(),
        field_mass=0.04,
    )
    assert hooked["professional_art_direction"] <= 7
    clean = detect_layout_faults(_grouped(), field_mass=0.2)
    assert "SCATTERED_ELEMENT_LAYOUT" not in clean
    assert "DETACHED_CTA" not in clean


def test_group_first_compositor_does_not_scatter() -> None:
    photo = Image.new("RGB", (400, 500), (110, 120, 130))
    ImageDraw.Draw(photo).rectangle((180, 80, 320, 420), fill=(160, 150, 140))
    pack = compose_relational_v4(
        photo,
        occupancy=_occ((400, 500)),
        fonts=build_font_registry(),
        logo_rgba=Image.new("RGBA", (80, 40), (255, 255, 255, 255)),
        facts=None,
        art_plan={"schema": "RelationalCompositionPlanV1", "reconstruction_mode": "SKY_VEIL", "scale": 1.0},
        family=full_frame_family_spec(),
        scale=1.0,
    )
    assert pack["schema"] == "GraphicDesignCompositorV4"
    faults = detect_layout_faults(
        pack["objects"],
        field_mass=0.15,
        islands=bool((pack.get("reading_flow") or {}).get("commercial_islands")),
    )
    assert "SCATTERED_ELEMENT_LAYOUT" not in faults
    assert "CAPTION_ROW_LAYOUT" not in faults
    scores = score_calibration_render(pack["objects"], pack["groups_v2"], pack["reading_flow"], 0.15)
    assert scores["group_cohesion"] >= 8
    assert scores["reading_flow"] >= 8
