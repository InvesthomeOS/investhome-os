"""Phase 5.5C-R1 — price hierarchy correction. No GPT Image. Master raster unchanged."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID, PRICE_INSTRUCTION
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import (
    FAILED_REVISION_ASSET_ID,
    FAILED_REVISION_ID,
    PARENT_MASTER_ID,
    WORKFLOW_ID_55C_R1,
    commercial_group_mass_preservation,
    generate_price_hierarchy_55c_r1,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2


def test_locks_parent_and_failed_revision() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert FAILED_REVISION_ID == "997695c6-15f8-4edd-9146-f649c7554155"
    assert FAILED_REVISION_ASSET_ID == "b9345b34-585d-4981-94f4-bda39fb6331b"
    assert WORKFLOW_ID_55C_R1 == "phase5_5c_r1_price_hierarchy"
    assert generate_price_hierarchy_55c_r1
    assert "438.750" in PRICE_INSTRUCTION
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"


def test_no_gpt_image_or_master_overwrite() -> None:
    import investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "must not call GPT Image" in src
    assert "PRICE_EDIT_ONLY" in src
    assert "CommercialGroupMassPreservationV1" in src
    assert "one_line" in src


def test_mass_ratio_requires_085() -> None:
    navy = (40, 50, 60)
    master = Image.new("RGB", (200, 120), navy)
    ImageDraw.Draw(master).rectangle((10, 10, 90, 50), fill=(240, 240, 230))
    weak = Image.new("RGB", (200, 120), navy)
    ImageDraw.Draw(weak).rectangle((10, 10, 30, 20), fill=(240, 240, 230))
    strong = Image.new("RGB", (200, 120), navy)
    ImageDraw.Draw(strong).rectangle((10, 10, 88, 48), fill=(240, 240, 230))
    failed = commercial_group_mass_preservation(master, weak, original_box=(10, 10, 90, 50), primary_box=(10, 10, 30, 20), navy=navy)
    passed = commercial_group_mass_preservation(master, strong, original_box=(10, 10, 90, 50), primary_box=(10, 10, 88, 48), navy=navy)
    assert failed["pass"] is False
    assert passed["pass"] is True
    assert passed["primary_price_mass_ratio"] >= 0.85
