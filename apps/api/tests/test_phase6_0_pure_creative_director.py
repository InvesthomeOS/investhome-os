"""Phase 6.0 — pure creative director. No reconstruction. Existing Master unchanged."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_0_creative import (
    MAX_IMAGE_CALLS,
    image_artist_prompt,
    resolve_photo,
)
from investhome_api.services.creative_director.phase6_0_pure_creative_director import (
    WORKFLOW_ID_60,
    generate_pure_creative_director_60,
)


def test_locks_and_identity() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_60 == "phase6_0_pure_creative_director"
    assert generate_pure_creative_director_60
    assert MAX_IMAGE_CALLS == 6


def test_creative_stage_has_no_production_architecture() -> None:
    import investhome_api.services.creative_director.phase6_0_creative as creative
    import investhome_api.services.creative_director.phase6_0_pure_creative_director as workflow

    src = inspect.getsource(creative)
    flow = inspect.getsource(workflow)
    for banned in (
        "GraphicDesignCompositorV4",
        "CreativeRelationshipGraph",
        "PRICE_EDIT_ONLY",
        "COPY_EDIT_ONLY",
        "VISUAL_REPLACE_ONLY",
        "sky veil",
        "SKY_VEIL",
        "GROUND_PLANE",
        "CORNER_INGRESS",
        "compose_relational_v4",
    ):
        assert banned not in src
    assert "compose_relational_v4" not in flow
    assert "edit_image" in src
    assert "reconstruction_executed" in flow
    assert "CONCEPTS_PENDING_HUMAN_REVIEW" in flow
    prompt = image_artist_prompt({"visual_idea": "an iconic monument", "creative_brief": "make it memorable"})
    assert "Avoid generic real-estate listing templates and ordinary website-style layouts." in prompt
    assert "sidebar" not in prompt.lower()
    assert "lockup" not in prompt.lower()


def test_photo_resolver_prefers_unused() -> None:
    catalog = [
        {"asset_id": "a", "filename": "Day_007.jpg", "sky_area": 0.4, "architecture_centroid_x": 0.6},
        {"asset_id": "b", "filename": "Day_004.jpg", "sky_area": 0.3, "architecture_centroid_x": 0.6},
        {"asset_id": "c", "filename": "Sunset_001.jpg", "sky_area": 0.0, "architecture_centroid_x": 0.5},
    ]
    first = resolve_photo(catalog, "Day_004", set())
    assert first["asset_id"] == "b"
    second = resolve_photo(catalog, "Day_004", {"b"})
    assert second["asset_id"] != "b"
    unused = resolve_photo(catalog, "", {"a", "b"})
    assert unused["asset_id"] == "c"
