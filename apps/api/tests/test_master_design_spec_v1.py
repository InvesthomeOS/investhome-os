"""Master Design Spec v1 — extraction, validation, metadata-only persist."""

from __future__ import annotations

from investhome_api.services.creative_director.edit_map import (
    analyze_raster,
    build_edit_map,
    persist_edit_map,
    validate_edit_map,
)
from investhome_api.services.creative_director.master_design_spec import (
    FLEXIBLE_CONTENT,
    FLEXIBLE_LAYOUT,
    LOCKED_IDENTITY,
    PROJECT_ASSET_POLICY,
    REPLACEABLE_ASSET,
    SPEC_VERSION,
    build_master_design_spec,
    load_master_design_spec,
    persist_master_design_spec,
    snapshot_identity,
    validate_master_design_spec,
)
from test_edit_map_v1 import COVER_V2, LOGO, SOURCE_V2, _synthetic_temple_raster

PROJECT = "d50708cb-60b3-465a-8b16-6d30f802af8d"

COPY_CTX = {
    "production_brief": {
        "hero": "ALIRKEN KAZAN",
        "final_copy": {
            "headline": "ALIRKEN KAZAN",
            "supporting": "The Temple'da yerinizi lansman döneminde alın.",
            "unit": "2+1",
            "list_price": "675.000 USD",
            "value_badge": "%35 LANSMAN AVANTAJI",
            "cta": "PROJEYİ KEŞFET",
        },
    },
    "master_creative": {
        "project_id": PROJECT,
        "current_version": 2,
        "current_cover_asset_id": COVER_V2,
        "current_edit_map_id": "map-v2",
        "source_visual_asset_id": SOURCE_V2,
        "logo_asset_id": LOGO,
        "campaign_copy": {
            "headline": "ALIRKEN KAZAN",
            "cta": "PROJEYİ KEŞFET",
        },
        "revision_history": [{"version": 2}],
    },
    "current_cover_asset_id": COVER_V2,
    "current_edit_map_id": "map-v2",
    "latest_master_ad_asset_id": COVER_V2,
    "finished_ad_raster_asset_id": COVER_V2,
}


def _edit_map():
    im = _synthetic_temple_raster()
    layout = analyze_raster(im)
    edit_map = build_edit_map(
        layout,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        image=im,
    )
    validate_edit_map(
        edit_map,
        expected_cover_asset_id=COVER_V2,
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
        current_cover_asset_id=COVER_V2,
    )
    return im, layout, edit_map


def test_synthetic_spec_validates_and_captures_copy() -> None:
    im, layout, edit_map = _edit_map()
    spec = build_master_design_spec(
        ctx=COPY_CTX,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        project_id=PROJECT,
        edit_map=edit_map,
        layout=layout,
        image=im,
        source_version=2,
    )
    assert spec["validation_status"] == "pass", spec["validation"]
    assert spec["spec_version"] == SPEC_VERSION
    assert spec["source_cover_asset_id"] == COVER_V2
    assert spec["source_version"] == 2
    assert spec["project_asset_policy"] == PROJECT_ASSET_POLICY
    assert spec["provider_image_calls"] == 0
    assert spec["native_renderer_recipe"] is False
    assert spec["canvas"]["width"] == im.size[0]
    assert spec["canvas"]["height"] == im.size[1]
    assert spec["canvas"]["safe_margins"]["normalized"]
    elements = {e["semantic_role"]: e for e in spec["elements"]}
    assert elements["headline"]["exact_content"] == "ALIRKEN KAZAN"
    assert "Temple" in elements["supporting_copy"]["exact_content"]
    assert elements["unit_type"]["exact_content"] == "2+1"
    assert "675.000" in elements["list_price"]["exact_content"]
    assert "%35" in elements["discount"]["exact_content"]
    assert elements["cta"]["exact_content"] == "PROJEYİ KEŞFET"
    assert elements["list_price"]["geometry"]["normalized"]["x"] >= 0
    assert elements["headline"]["flexibility"]["content"] == LOCKED_IDENTITY
    assert elements["headline"]["flexibility"]["layout"] == FLEXIBLE_LAYOUT
    assert elements["list_price"]["flexibility"]["content"] == FLEXIBLE_CONTENT
    assert spec["flexibility_model"]["hero_source_asset"] == REPLACEABLE_ASSET
    assert spec["flexibility_model"]["logo_asset"] == LOCKED_IDENTITY
    assert spec["hero_treatment"]["architecture_lock"] is True
    groups = {g["id"]: g for g in spec["groups"]}
    assert "commercial_group" in groups
    assert groups["commercial_group"]["content_capacity"]["current_content_count"] == 3
    assert "raster-patch" in groups["commercial_group"]["content_capacity"]["growth_strategy"]
    assert spec["relationships"]
    assert spec["source_assets"]["hero_visual_asset_id"] == SOURCE_V2
    assert spec["source_assets"]["logo_asset_id"] == LOGO


def test_persist_does_not_change_cover_or_version() -> None:
    im, layout, edit_map = _edit_map()
    ctx = dict(COPY_CTX)
    ctx["master_creative"] = dict(COPY_CTX["master_creative"])
    persist_edit_map(ctx, edit_map)
    before = snapshot_identity(ctx)
    spec = build_master_design_spec(
        ctx=ctx,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        project_id=PROJECT,
        edit_map=edit_map,
        layout=layout,
        image=im,
        source_version=2,
    )
    persist_master_design_spec(ctx, spec)
    after = snapshot_identity(ctx)
    assert after == before
    assert after["current_version"] == 2
    assert after["current_cover_asset_id"] == COVER_V2
    sid, loaded = load_master_design_spec(ctx, cover_asset_id=COVER_V2)
    assert sid == spec["master_design_spec_id"]
    assert loaded["source_cover_asset_id"] == COVER_V2
    assert ctx["master_design_specs_by_cover"][COVER_V2] == sid


def test_validation_fails_when_headline_missing() -> None:
    im, layout, edit_map = _edit_map()
    ctx = {
        "production_brief": {"final_copy": {"cta": "PROJEYİ KEŞFET"}},
        "master_creative": {},
    }
    spec = build_master_design_spec(
        ctx=ctx,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        project_id=PROJECT,
        edit_map=edit_map,
        layout=layout,
        image=im,
        source_version=2,
    )
    assert spec["validation_status"] == "fail"
    assert any("headline" in f for f in spec["validation"]["failures"])


def test_wrong_cover_fails_validation() -> None:
    im, layout, edit_map = _edit_map()
    spec = build_master_design_spec(
        ctx=COPY_CTX,
        cover_asset_id=COVER_V2,
        source_visual_asset_id=SOURCE_V2,
        logo_asset_id=LOGO,
        project_id=PROJECT,
        edit_map=edit_map,
        layout=layout,
        image=im,
        source_version=2,
    )
    result = validate_master_design_spec(
        spec,
        expected_cover_asset_id="00000000-0000-0000-0000-000000000000",
        expected_source_visual_asset_id=SOURCE_V2,
        expected_logo_asset_id=LOGO,
        expected_project_id=PROJECT,
    )
    assert result["status"] == "fail"
    assert "cover_asset_id_mismatch" in result["failures"]
