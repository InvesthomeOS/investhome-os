"""Structured Golden Design v1 — persist semantic twin; MICRO_EDIT stays GPT=0."""

from __future__ import annotations

from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    build_design_spec,
    compose_layer_only_on_locked_raster,
    project_structured_design_data,
    route_revision,
)
from investhome_api.services.creative_director.revision_intelligence import (
    interpret_revision_plan,
    snapshot_elements,
)


def _lifestyle_brief() -> dict:
    return {
        "campaign_intent": "lifestyle",
        "hero": "Tarihi karakter, modern yaşam",
        "cta": "The Temple'ı Keşfet",
        "supporting": [
            "Gerçek interior, editoryal duruş.",
            "Az metin, güçlü kompozisyon.",
        ],
        "final_copy": {
            "headline": "Tarihi karakter, modern yaşam",
            "cta": "The Temple'ı Keşfet",
        },
        "design_direction": {"visual_mood": "editorial", "hierarchy": "headline_first"},
    }


def _lifestyle_texts() -> dict[str, str]:
    return {
        "headline": "Tarihi karakter, modern yaşam",
        "cta": "The Temple'ı Keşfet",
        "supporting": "Gerçek interior, editoryal duruş. · Az metin, güçlü kompozisyon.",
    }


def _spec() -> dict:
    return build_design_spec(
        production_brief=_lifestyle_brief(),
        texts=_lifestyle_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        finished_ad_raster_asset_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="lifestyle",
    )


def test_structured_projection_has_required_semantic_slots():
    spec = _spec()
    data = project_structured_design_data(spec, production_brief=_lifestyle_brief())
    present = set(data["present_slots"])
    assert data["version"] == 1
    assert data["visual_source_of_truth"] == "finished_ad_raster"
    assert data["rebuild_from_layers"] is False
    assert "background" in present
    assert "project-logo" in present
    assert "headline" in present
    assert "cta-primary" in present
    assert data["background_asset_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert data["logo_asset_id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert data["finished_ad_raster_asset_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    ids = {el["id"] for el in data["elements"]}
    assert {"background", "project-logo", "headline", "cta-primary"} <= ids


def test_legacy_headline_replace_stays_creative_recompose():
    spec = _spec()
    plan = interpret_revision_plan(
        instruction="Başlığı Zamansız Bir Yaşam yap.",
        design_spec=spec,
    )
    assert (
        route_revision(instruction="Başlığı Zamansız Bir Yaşam yap.", revision_diff=plan)
        == "CREATIVE_RECOMPOSE"
    )


def test_structured_headline_replace_is_micro_edit():
    spec = _spec()
    plan = interpret_revision_plan(
        instruction="Başlığı Zamansız Bir Yaşam yap.",
        design_spec=spec,
    )
    assert (
        route_revision(
            instruction="Başlığı Zamansız Bir Yaşam yap.",
            revision_diff=plan,
            has_structured_design=True,
        )
        == "MICRO_EDIT"
    )


def test_structured_logo_scale_is_micro_edit():
    spec = _spec()
    plan = interpret_revision_plan(instruction="Logoyu %20 küçült.", design_spec=spec)
    assert (
        route_revision(
            instruction="Logoyu %20 küçült.",
            revision_diff=plan,
            has_structured_design=True,
        )
        == "MICRO_EDIT"
    )


def test_structured_cta_hide_is_micro_edit():
    spec = _spec()
    plan = interpret_revision_plan(instruction="CTA'yı kaldır.", design_spec=spec)
    assert (
        route_revision(
            instruction="CTA'yı kaldır.",
            revision_diff=plan,
            has_structured_design=True,
        )
        == "MICRO_EDIT"
    )


def test_structured_cta_hide_keeps_element_and_covers_zone():
    spec = _spec()
    plan = interpret_revision_plan(instruction="CTA'yı kaldır.", design_spec=spec)
    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    cta = next(el for el in after["elements"] if str(el.get("id")) == "cta")
    assert cta.get("visible") is False
    layers = compose_layer_only_on_locked_raster(
        after_spec=after,
        before_snap=before,
        locked_raster_asset_id="raster-1",
    )
    assert not any(str(el.get("id") or "").startswith("hide-plate") for el in layers)
    assert any(str(el.get("id") or "") == "cta-zone-cover" for el in layers)


def test_structured_headline_compose_has_text_overlay_no_hide_plate():
    spec = _spec()
    plan = interpret_revision_plan(
        instruction="Başlığı Zamansız Bir Yaşam yap.",
        design_spec=spec,
    )
    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    headline = next(el for el in after["elements"] if str(el.get("id")) == "headline")
    assert "Zamansız Bir Yaşam" in str(headline.get("content") or "")
    layers = compose_layer_only_on_locked_raster(
        after_spec=after,
        before_snap=before,
        locked_raster_asset_id="raster-1",
    )
    assert not any(str(el.get("id") or "").startswith("hide-plate") for el in layers)
    texts = [el for el in layers if str(el.get("type") or "").upper() == "TEXT"]
    assert any(str(el.get("id") or "") == "headline" for el in texts)
