"""Golden Creative Revision Preservation v1 — MICRO_EDIT vs CREATIVE_RECOMPOSE."""

from __future__ import annotations

import io

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


def _layout_png(
    *,
    cta_left: bool,
    headline_top: bool,
    first_support: bool,
    remaining_support: bool,
    logo: bool,
    giant_headline: bool = False,
    logo_large: bool = False,
) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (300, 400), (40, 42, 48))
    draw = ImageDraw.Draw(img)
    draw.rectangle((90, 130, 210, 270), fill=(90, 88, 82))
    if giant_headline:
        draw.rectangle((12, 12, 270, 150), fill=(240, 236, 228))
    elif headline_top:
        draw.rectangle((18, 18, 180, 70), fill=(240, 236, 228))
    else:
        draw.rectangle((70, 150, 230, 210), fill=(240, 236, 228))
    if first_support:
        draw.rectangle((18, 88, 120, 118), fill=(200, 196, 188))
    if remaining_support:
        draw.rectangle((18, 168, 120, 198), fill=(200, 196, 188))
    if logo_large:
        draw.rectangle((210, 8, 294, 72), fill=(196, 163, 90))
    elif logo:
        draw.rectangle((230, 16, 286, 52), fill=(196, 163, 90))
    if cta_left:
        draw.rectangle((18, 350, 110, 386), fill=(20, 18, 16))
    else:
        draw.rectangle((190, 350, 282, 386), fill=(20, 18, 16))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_ACCEPT_DIFF = {
    "operations": [
        {"target": "headline", "action": "replace_text", "to_value": "Zamansız Bir Yaşam"},
        {"target": "support_message", "action": "remove"},
        {"target": "logo", "action": "scale", "to_value": "0.85"},
    ]
}


def test_composition_fidelity_rejects_cta_move():
    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    master = _layout_png(
        cta_left=True, headline_top=True, first_support=True, remaining_support=True, logo=True
    )
    moved = _layout_png(
        cta_left=False, headline_top=True, first_support=True, remaining_support=True, logo=True
    )
    result = compare_recompose_composition_fidelity(
        master_bytes=master,
        revised_bytes=moved,
        revision_diff={"operations": [{"target": "headline", "action": "replace_text"}]},
    )
    assert result["status"] == "fail"
    assert any("cta" in f for f in result["composition_failures"])


def test_composition_fidelity_allows_local_headline_and_support_delete():
    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    master = _layout_png(
        cta_left=True, headline_top=True, first_support=True, remaining_support=True, logo=True
    )
    revised = _layout_png(
        cta_left=True, headline_top=True, first_support=False, remaining_support=True, logo=True
    )
    result = compare_recompose_composition_fidelity(
        master_bytes=master,
        revised_bytes=revised,
        revision_diff=_ACCEPT_DIFF,
    )
    assert result["status"] == "pass", result["composition_failures"]


def test_composition_fidelity_rejects_headline_region_move():
    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    master = _layout_png(
        cta_left=True, headline_top=True, first_support=True, remaining_support=True, logo=True
    )
    moved = _layout_png(
        cta_left=True, headline_top=False, first_support=True, remaining_support=True, logo=True
    )
    result = compare_recompose_composition_fidelity(
        master_bytes=master,
        revised_bytes=moved,
        revision_diff={"operations": [{"target": "headline", "action": "replace_text"}]},
    )
    assert result["status"] == "fail"
    assert any("headline" in f for f in result["composition_failures"])


def test_visual_fidelity_rejects_unrequested_support_loss_and_giant_headline():
    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    master = _layout_png(
        cta_left=True, headline_top=True, first_support=True, remaining_support=True, logo=True
    )
    simplified = _layout_png(
        cta_left=True,
        headline_top=True,
        first_support=False,
        remaining_support=False,
        logo=True,
        giant_headline=True,
        logo_large=True,
    )
    result = compare_recompose_composition_fidelity(
        master_bytes=master,
        revised_bytes=simplified,
        revision_diff=_ACCEPT_DIFF,
    )
    assert result["status"] == "fail"
    failures = " ".join(result["composition_failures"])
    assert "supporting_text_disappeared" in failures or "headline_scale" in failures


def test_visual_fidelity_rejects_real_temple_bad_raster():
    from pathlib import Path

    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    fixtures = Path(__file__).resolve().parent / "fixtures" / "visual_fidelity"
    master = (fixtures / "temple_master.png").read_bytes()
    bad = (fixtures / "temple_bad_current.png").read_bytes()
    result = compare_recompose_composition_fidelity(
        master_bytes=master,
        revised_bytes=bad,
        revision_diff=_ACCEPT_DIFF,
    )
    assert result["status"] == "fail"
    assert result["visual_fidelity"] == "fail"
    assert result["composition_failures"]


def test_recompose_prompt_sends_master_as_visual_reference():
    from investhome_api.services.creative_director.revision import render_revision_production_prompt

    prompt = render_revision_production_prompt(
        revision_brief={
            "instruction": ACCEPTANCE_PROMPT,
            "intents": ["COPY_CHANGE"],
            "master_asset_id": "master-1",
            "master_source_asset_id": "source-1",
            "copy_overrides": {},
            "revision_diff": {"operations": [], "preserve": [], "forbidden_changes": []},
            "cumulative_operations": [],
            "production_brief_snapshot": {"hero": "Eviniz, Sığınak", "cta": "Detayları Keşfet"},
        },
        production_brief={"cta": "Detayları Keşfet", "final_copy": {"headline": "Eviniz, Sığınak"}},
        original_brief="The Temple",
        lifestyle=False,
    )
    assert "MASTER finished advertisement" in prompt
    assert "DO NOT DESIGN A NEW ADVERTISEMENT" in prompt
    assert "existing visual zone" in prompt
