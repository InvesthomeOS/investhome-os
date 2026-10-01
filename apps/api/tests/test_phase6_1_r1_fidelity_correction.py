"""Phase 6.1-R1 — Concept 3 fidelity correction. Parent 6.1 unchanged."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.graphic_field_engine import field_spec
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_r1_compose import (
    PARENT_61_ASSET_ID,
    PARENT_61_SPEC_ID,
    R1_CROP_CANDIDATES,
    r1_field_specs,
)
from investhome_api.services.creative_director.phase6_1_r1_fidelity_correction import WORKFLOW_ID_61R1, generate_concept3_r1
from investhome_api.services.creative_director.phase6_1_concept3_compose import analyze_concept3_pixels
from PIL import Image, ImageDraw


def test_parent_and_locks() -> None:
    assert PARENT_61_ASSET_ID == "1173f9ef-1066-4388-8d1d-6893fed8a8b2"
    assert PARENT_61_SPEC_ID == "2c1f6b36-f0eb-490d-b312-8e70545ec85f"
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_61R1 == "phase6_1_r1_fidelity_correction"
    assert generate_concept3_r1
    assert len(R1_CROP_CANDIDATES) >= 12


def test_r1_does_not_use_generation_or_v4() -> None:
    import investhome_api.services.creative_director.phase6_1_r1_compose as compose
    import investhome_api.services.creative_director.phase6_1_r1_fidelity_correction as workflow

    src = inspect.getsource(compose) + inspect.getsource(workflow)
    for banned in ("compose_relational_v4", "edit_image", "generate_image"):
        assert banned not in src
    assert "PARENT_61_ASSET_ID" in inspect.getsource(workflow)
    assert "ALIRKEN" in inspect.getsource(compose)
    assert "KAZAN" in inspect.getsource(compose)
    assert "TARİHİN RUHU, GELECEĞİN DEĞERİ." in inspect.getsource(compose)
    assert "APPROVED" in inspect.getsource(compose)


def test_r1_arc_has_no_concentric_rings() -> None:
    image = Image.new("RGB", (1088, 1360), (40, 42, 48))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, 380, 1360), fill=(20, 22, 26))
    structure = analyze_concept3_pixels(image)
    kinds = [s["kind"] for s in r1_field_specs(structure)]
    assert "editorial_measurement_marks" not in kinds
    assert "elliptical_arc" not in kinds
    assert "curved_rule" in kinds
    assert "radial_tick_sequence" in kinds
    assert "precision_marker" in kinds
    assert "photo_overlay_field" in kinds
    field_spec("curved_rule")
    try:
        field_spec("panel")
    except ValueError:
        return
    raise AssertionError("panel allowed")
