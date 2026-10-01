"""Phase 6.1 — Concept 3 reconstruction. Existing Master and cover unchanged."""

from __future__ import annotations

import inspect

from PIL import Image

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_relationship_system import groups_from_objects
from investhome_api.services.creative_director.graphic_field_engine import CONCEPT3_PRIMITIVES, apply_graphic_fields, field_spec, plan_fields
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    analyze_concept3_pixels,
)
from investhome_api.services.creative_director.phase6_1_concept3_production_master import (
    WORKFLOW_ID_61,
    generate_concept3_production_master_61,
)


def test_locks_and_identity() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert CONCEPT3_ASSET_ID == "5c2b06d4-9f61-4358-a21b-7d5f9a098093"
    assert WORKFLOW_ID_61 == "phase6_1_concept3_production_master"
    assert generate_concept3_production_master_61


def test_does_not_use_v4_layout_modes() -> None:
    import investhome_api.services.creative_director.phase6_1_concept3_compose as compose
    import investhome_api.services.creative_director.phase6_1_concept3_production_master as workflow

    src = inspect.getsource(compose)
    flow = inspect.getsource(workflow)
    for banned in ("compose_relational_v4", "edit_image", "generate_image"):
        assert banned not in src
        assert banned not in flow
    assert "compose_relational_v4" not in src
    assert "APPROVED_CONCEPT_3" in src
    assert "PENDING_HUMAN_COPY_APPROVAL" in src
    assert "STRUCTURED_MASTER_PENDING_HUMAN_REVIEW" in flow
    assert "promoted_to_master" in flow


def test_graphic_field_primitives_and_forbidden() -> None:
    for kind in CONCEPT3_PRIMITIVES:
        spec = field_spec(kind, role="concept3")
        assert spec["kind"] == kind
        assert spec["pill"] is False
        assert spec["card"] is False
    for kind in ("panel", "card", "pill", "button"):
        try:
            field_spec(kind)
        except ValueError:
            continue
        raise AssertionError(f"forbidden kind allowed: {kind}")
    image = Image.new("RGB", (200, 200), (20, 24, 30))
    hard = Image.new("L", (200, 200), 0)
    applied = apply_graphic_fields(image, {"layers": {"hard_protected": hard}}, "SKY_VEIL")
    assert applied["schema"] == "GraphicFieldEngineV1"
    kinds = " ".join(f["kind"] for f in plan_fields("SKY_VEIL"))
    assert "panel" not in kinds and "pill" not in kinds


def test_editorial_closure_group() -> None:
    objects = {
        "headline": {"bounds": {"x": 0.06, "y": 0.20, "w": 0.28, "h": 0.06}},
        "discount": {"bounds": {"x": 0.06, "y": 0.30, "w": 0.10, "h": 0.05}},
        "discount_label": {"bounds": {"x": 0.06, "y": 0.36, "w": 0.18, "h": 0.02}},
        "price": {"bounds": {"x": 0.06, "y": 0.40, "w": 0.20, "h": 0.04}},
        "unit_type": {"bounds": {"x": 0.06, "y": 0.46, "w": 0.14, "h": 0.03}},
        "project_logo": {"bounds": {"x": 0.06, "y": 0.04, "w": 0.10, "h": 0.06}},
        "cta": {"bounds": {"x": 0.06, "y": 0.70, "w": 0.18, "h": 0.04}},
        "editorial_closure": {"bounds": {"x": 0.22, "y": 0.90, "w": 0.56, "h": 0.04}},
    }
    groups = groups_from_objects(objects, mode="APPROVED_CONCEPT_3")
    ids = [g["group_id"] for g in groups]
    assert ids == ["BRAND_GROUP", "CAMPAIGN_GROUP", "OFFER_GROUP", "ACTION_GROUP", "EDITORIAL_CLOSURE_GROUP"]
    sky = groups_from_objects(
        {k: v for k, v in objects.items() if k != "editorial_closure"},
        mode="SKY_VEIL",
    )
    assert {g["group_id"] for g in sky} == {"CAMPAIGN_GROUP", "OFFER_GROUP", "BRAND_GROUP", "ACTION_GROUP"}


def test_pixel_analysis_schema() -> None:
    from PIL import ImageDraw

    image = Image.new("RGB", (1088, 1360), (180, 160, 120))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, 400, 1360), fill=(28, 30, 34))
    d.arc((-200, -40, 1400, 1400), start=100, end=260, fill=(201, 168, 92), width=3)
    mapped = analyze_concept3_pixels(image)
    assert mapped["schema"] == "ApprovedCreativeStructureMapV1"
    assert mapped["dark_field_geometry"]["polyline_x"]
    assert len(mapped["dark_field_geometry"]["polyline_x"]) == 48
