"""Phase 3.0B — MasterDesignSpecV1.1 visual fidelity + same-design reconstruction."""

from __future__ import annotations

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.master_design_spec import persist_master_design_spec, snapshot_identity
from investhome_api.services.creative_director.structured_reconstruction import reconstruct_from_spec, validate_render
from investhome_api.services.creative_director.visual_fidelity import (
    SCHEMA_V1_1,
    enrich_to_v1_1,
    list_available_fonts,
)
from test_structured_reconstruction import _v1

FORBIDDEN = ("438.750", "236.250", "LANSMAN FİYATI", "KAZANCINIZ")


def _source_and_logo():
    source = Image.new("RGB", (800, 1000), (70, 110, 150))
    draw = ImageDraw.Draw(source)
    draw.rectangle([180, 120, 620, 880], fill=(190, 175, 145))
    draw.rectangle([0, 0, 800, 180], fill=(120, 170, 210))
    logo = Image.new("RGBA", (120, 60), (230, 220, 200, 255))
    ImageDraw.Draw(logo).rectangle([8, 8, 112, 52], outline=(201, 168, 92), width=3)
    return source, logo


def test_enrich_does_not_mutate_parent_or_price_revise() -> None:
    cover, v1 = _v1()
    parent_id = v1["master_design_spec_id"]
    source, logo = _source_and_logo()
    v11 = enrich_to_v1_1(v1, reference=cover, source_visual=source, logo=logo)
    assert v1["master_design_spec_id"] == parent_id
    assert v1["schema"] == "MasterDesignSpecV1"
    assert v1.get("visual_fidelity_profile") is None
    assert v11["schema"] == SCHEMA_V1_1
    assert v11["spec_revision"] == "1.1"
    assert v11["spec_version"] == 1
    assert v11["parent_spec_id"] == parent_id
    assert v11["semantic_content_changed"] is False
    assert v11["preview_only"] is True
    assert v11["validation_status"] == "pass", v11.get("validation")
    blob = str(v11)
    for token in FORBIDDEN:
        assert token not in blob
    assert "675.000" in str(next(e for e in v11["elements"] if e["semantic_role"] == "list_price"))
    assert "2+1" in str(next(e for e in v11["elements"] if e["semantic_role"] == "unit_type"))
    profile = v11["visual_fidelity_profile"]
    for key in (
        "typography",
        "hero_treatment",
        "cta_treatment",
        "decorative_system",
        "color_treatment",
        "group_hierarchy",
        "precise_geometry",
        "render_relationships",
    ):
        assert key in profile
    hero = profile["hero_treatment"]
    assert hero["crop_rectangle_source"]
    assert hero["color_treatment"]["per_channel_gain"]
    fonts = profile["typography"]["selected_fonts"]
    assert fonts["headline_KAZAN"]["selected_font"]
    assert list_available_fonts()
    commercial = profile["group_hierarchy"]
    assert commercial["unit"]["value_content"] == "2+1"
    assert commercial["unit"]["label_content"] == "DAİRE"


def test_enrich_does_not_persist_as_current() -> None:
    cover, v1 = _v1()
    from test_master_design_spec_v1 import COPY_CTX

    ctx = dict(COPY_CTX)
    ctx["master_creative"] = dict(COPY_CTX["master_creative"])
    persist_master_design_spec(ctx, v1)
    before = snapshot_identity(ctx)
    current = ctx["current_master_design_spec_id"]
    source, logo = _source_and_logo()
    v11 = enrich_to_v1_1(v1, reference=cover, source_visual=source, logo=logo)
    after = snapshot_identity(ctx)
    assert after == before
    assert ctx["current_master_design_spec_id"] == current
    assert v11["master_design_spec_id"] not in (ctx.get("master_design_specs") or {})


def test_same_design_reconstruction_no_provider_no_price_revision() -> None:
    cover, v1 = _v1()
    source, logo = _source_and_logo()
    v11 = enrich_to_v1_1(v1, reference=cover, source_visual=source, logo=logo)
    preview, report = reconstruct_from_spec(v11, source_visual=source, logo=logo, reference_cover=cover)
    assert preview.size == (v11["canvas"]["width"], v11["canvas"]["height"])
    assert report["provider_image_calls"] == 0
    assert report["raster_surgery"] is False
    assert report["native_renderer"] is False
    assert report["reference_raster_used_as_output_background"] is False
    blob = " ".join(report["drawn_content"])
    assert "675.000" in blob
    assert "2+1" in blob
    assert "%35" in blob
    assert "ALIRKEN KAZAN" in blob
    for token in FORBIDDEN:
        assert token not in blob
    rendered = validate_render(preview, v11, report)
    assert rendered["status"] == "pass", rendered
    # Reconstruction must not be a copy of the approved raster.
    assert preview.tobytes() != cover.convert("RGB").resize(preview.size).tobytes()
