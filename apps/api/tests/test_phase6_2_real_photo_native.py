"""Phase 6.2 — Concept 3 language on real Day_007. Not a 6.1 R2."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.graphic_field_engine import CONCEPT3_PRIMITIVES, field_spec
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_concept3_compose import CONCEPT3_ASSET_ID, DAY007_ASSET_ID
from investhome_api.services.creative_director.phase6_2_compose import (
    APPROVED_BOTTOM_COPY,
    NATIVE_MODE,
    native_field_specs,
)
from investhome_api.services.creative_director.phase6_2_real_photo_native import WORKFLOW_ID_62, generate_phase6_2_native_composition


def test_locks_and_identity() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert CONCEPT3_ASSET_ID == "5c2b06d4-9f61-4358-a21b-7d5f9a098093"
    assert WORKFLOW_ID_62 == "phase6_2_real_photo_native_composition"
    assert generate_phase6_2_native_composition
    assert NATIVE_MODE == "DAY007_NATIVE_APERTURE"
    assert APPROVED_BOTTOM_COPY == "TARİHİN RUHU, GELECEĞİN DEĞERİ."


def test_does_not_use_templates_or_generation() -> None:
    import investhome_api.services.creative_director.phase6_2_compose as compose
    import investhome_api.services.creative_director.phase6_2_real_photo_native as workflow

    src = inspect.getsource(compose) + inspect.getsource(workflow)
    for banned in ("compose_relational_v4(", "edit_image", "generate_image"):
        assert banned not in src
    assert "mode=\"SKY_VEIL\"" not in src
    assert "mode=\"GROUND_PLANE\"" not in src
    assert "mode=\"CORNER_INGRESS\"" not in src
    assert "NATIVE_COMPOSITION_PENDING_HUMAN_REVIEW" in inspect.getsource(workflow)
    assert "promoted_to_master" in inspect.getsource(workflow)
    assert "auto_polished" in inspect.getsource(workflow)
    assert "concept3_r1_61_tests" in inspect.getsource(workflow)


def test_native_field_is_curved_aperture_not_sidebar() -> None:
    mapped = {"spire_axis": 0.64, "spire_top": 0.14, "possible_arc_trajectories": {
        "A_spire_edge": "edge", "B_sky_crown": "crown", "C_ground_rise": "rise"
    }}
    kinds = {s["kind"] for s in native_field_specs("A", mapped, production=True)}
    assert "curved_aperture" in kinds
    assert "curved_rule" in kinds
    assert "radial_tick_sequence" in kinds
    assert "precision_marker" in kinds
    for extra in ("curved_aperture", "masked_photo_overlay", "tonal_transition"):
        assert extra in CONCEPT3_PRIMITIVES
        spec = field_spec(extra, role="native")
        assert spec["kind"] == extra
        assert spec["pill"] is False
    try:
        field_spec("panel")
    except ValueError:
        return
    raise AssertionError("panel allowed")


def test_three_sketches_differ() -> None:
    mapped = {"spire_axis": 0.66, "spire_top": 0.12, "possible_arc_trajectories": {
        "A_spire_edge": "edge", "B_sky_crown": "crown", "C_ground_rise": "rise"
    }}
    a = native_field_specs("A", mapped, production=False)
    b = native_field_specs("B", mapped, production=False)
    c = native_field_specs("C", mapped, production=False)
    pa = next(s["polyline_x"] for s in a if s["kind"] == "curved_aperture")
    pb = next(s["polyline_x"] for s in b if s["kind"] == "curved_aperture")
    pc = next(s["polyline_x"] for s in c if s["kind"] == "curved_aperture")
    assert pa != pb != pc
    assert pa[0] != pc[-1] or pb[0] != pc[0]
