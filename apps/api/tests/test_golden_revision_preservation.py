"""Golden Creative Revision Preservation v1 — MICRO_EDIT vs CREATIVE_RECOMPOSE."""

from __future__ import annotations

from investhome_api.services.creative_director.design_spec import (
    compose_layer_only_on_locked_raster,
    route_revision,
)
from investhome_api.services.creative_director.revision import (
    apply_revision_ops_to_working_brief,
    golden_revision_artifact_guard,
)
from investhome_api.services.creative_director.revision_intelligence import (
    interpret_revision_plan,
    snapshot_elements,
)

from test_ai_revision_intelligence_v3 import SELECTED_DESIGN_PROMPT, _smb_real_spec


ACCEPTANCE_PROMPT = (
    "Başlığı 'Zamansız Bir Yaşam' yap.\n"
    "Soldaki ilk açıklamayı kaldır.\n"
    "Logoyu %15 küçült.\n"
    "Arka planı, CTA'yı, diğer metinleri ve renkleri değiştirme."
)
MICRO_PROMPT = "Logoyu %10 küçült. Başka hiçbir şeyi değiştirme."


def test_acceptance_prompt_routes_creative_recompose():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction=ACCEPTANCE_PROMPT, design_spec=spec)
    route = route_revision(
        instruction=ACCEPTANCE_PROMPT,
        revision_diff=plan,
        intents=["COPY_CHANGE", "LAYOUT_CHANGE"],
    )
    assert route == "CREATIVE_RECOMPOSE"


def test_headline_replace_is_creative_recompose():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(
        instruction="Başlığı 'Zamansız Bir Yaşam' yap.",
        design_spec=spec,
    )
    assert route_revision(instruction="Başlığı 'Zamansız Bir Yaşam' yap.", revision_diff=plan) == (
        "CREATIVE_RECOMPOSE"
    )


def test_hierarchy_delete_and_headline_scale_is_recompose():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction=SELECTED_DESIGN_PROMPT, design_spec=spec)
    assert (
        route_revision(instruction=SELECTED_DESIGN_PROMPT, revision_diff=plan)
        == "CREATIVE_RECOMPOSE"
    )


def test_logo_only_is_micro_edit():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction=MICRO_PROMPT, design_spec=spec)
    assert route_revision(instruction=MICRO_PROMPT, revision_diff=plan) == "MICRO_EDIT"


def test_cta_text_only_is_micro_edit():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction="CTA'yı Detayları İncele yap.", design_spec=spec)
    assert (
        route_revision(instruction="CTA'yı Detayları İncele yap.", revision_diff=plan) == "MICRO_EDIT"
    )


def test_simplify_is_creative_recompose():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction="Tasarımı daha sade yap.", design_spec=spec)
    assert (
        route_revision(
            instruction="Tasarımı daha sade yap.",
            revision_diff=plan,
            intents=["SIMPLIFY"],
        )
        == "CREATIVE_RECOMPOSE"
    )


def test_micro_edit_compose_has_no_hide_plate():
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction=MICRO_PROMPT, design_spec=spec)
    from investhome_api.services.creative_director.design_spec import apply_layer_operations

    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    layers = compose_layer_only_on_locked_raster(
        after_spec=after,
        before_snap=before,
        locked_raster_asset_id="raster-1",
    )
    assert not any(str(el.get("id") or "").startswith("hide-plate") for el in layers)
    assert not any(el.get("_designRole") == "revision_hide_plate" for el in layers)


def test_artifact_guard_rejects_hide_plate():
    guard = golden_revision_artifact_guard(
        editable_layers=[
            {
                "id": "hide-plate-headline",
                "type": "SHAPE",
                "fill": "rgba(12,10,8,0.94)",
                "_designRole": "revision_hide_plate",
            }
        ],
        interior_before="a",
        interior_after="a",
        logo_before="b",
        logo_after="b",
        background_requested=False,
    )
    assert guard["status"] == "fail"
    assert "black_hide_plate" in guard["failures"]


def test_working_brief_applies_headline_and_drops_first_support():
    master = {
        "hero": "Eviniz, Sığınak",
        "cta": "Detayları Keşfet",
        "supporting": ["Prime location in DC.", "Stunning architectural design."],
        "final_copy": {"headline": "Eviniz, Sığınak", "cta": "Detayları Keşfet"},
    }
    spec = _smb_real_spec()
    plan = interpret_revision_plan(instruction=ACCEPTANCE_PROMPT, design_spec=spec)
    out = apply_revision_ops_to_working_brief(master_brief=master, ops=list(plan.operations))
    assert out["final_copy"]["headline"] == "Zamansız Bir Yaşam"
    assert out["supporting"] == ["Stunning architectural design."]
    assert abs(float(out.get("logo_scale") or 1) - 0.85) < 0.02
