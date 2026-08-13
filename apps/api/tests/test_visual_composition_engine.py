"""Visual Composition Engine P2.2 — families, grid, grouping, collision, persistence."""

from __future__ import annotations

from uuid import UUID

from investhome_api.schemas.creative_studio_generation import (
    CreativeStudioBrandContext,
    CreativeStudioGenerationContext,
    CreativeStudioProjectIdentity,
)
from investhome_api.services.social_design_engine.composition_blueprint import (
    COMPOSITION_FAMILIES,
    composition_blueprint_from_dict,
    composition_blueprint_to_dict,
)
from investhome_api.services.social_design_engine.composition_engine import (
    analyze_image,
    build_composition_blueprint,
    choose_composition_family,
    choose_metric_composition,
)
from investhome_api.services.social_design_engine.creative_director import (
    AssetVisualProfile,
    direct_creative,
)
from investhome_api.services.social_design_engine.creative_intent import is_explicit_redesign
from investhome_api.services.social_design_engine.creative_plan import build_creative_plan
from investhome_api.services.social_design_engine.generation import (
    CampaignFact,
    ContentPackage,
    attach_generation_metadata,
    build_design_plan,
    build_generation_metadata,
    classify_generation_intent,
)
from investhome_api.services.social_design_engine.layout import apply_layout_grammar
from investhome_api.services.social_design_engine.layout_solver import (
    apply_blueprint_to_elements,
    blueprint_slots,
    resolve_group_collisions,
)
from investhome_api.services.social_design_engine.metrics import choose_metric_group_layout
from investhome_api.services.social_design_engine.typography import prevent_orphan_words

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")


def _ctx() -> CreativeStudioGenerationContext:
    return CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name="The Temple",
            city="Washington",
            country="US",
        ),
        verified_facts=["project_name=The Temple", "city=Washington"],
        retrieved_content=[],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )


def _plan(*, intent: str = "LOCATION", metrics: bool = False, **kwargs):
    return build_creative_plan(
        intent=intent,  # type: ignore[arg-type]
        audience="general",
        objective=intent.lower(),
        has_eligible_metrics=metrics,
        format_preset="square",
        project_name="The Temple",
        **kwargs,
    )


def test_families_are_not_one_to_one_with_intent() -> None:
    building = AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top", brightness="mixed")
    skyline = AssetVisualProfile(
        subject="skyline", image_led=True, empty_negative_space=True, brightness="light"
    )
    loc_a = _plan(intent="LOCATION", profile=building, instruction="quiet luxury editorial location")
    loc_b = _plan(intent="LOCATION", profile=skyline, instruction="open skyline location story")
    analysis_a = analyze_image(building)
    analysis_b = analyze_image(skyline)
    fam_a, _ = choose_composition_family(plan=loc_a, analysis=analysis_a, instruction="quiet luxury")
    fam_b, _ = choose_composition_family(
        plan=loc_b, analysis=analysis_b, instruction="open skyline", used_signals=[fam_a]
    )
    assert fam_a in COMPOSITION_FAMILIES
    assert fam_b in COMPOSITION_FAMILIES
    arch = _plan(
        intent="ARCHITECTURE",
        profile=building,
        instruction="restrained architectural feature",
    )
    fam_c, _ = choose_composition_family(plan=arch, analysis=analysis_a)
    assert fam_c in {"ARCHITECTURAL_MINIMAL", "IMAGE_DOMINANT", "LOWER_THIRD"}
    assert fam_c != fam_a or loc_a.creative_direction != arch.creative_direction


def test_architecture_does_not_place_headline_on_building_mass() -> None:
    building = AssetVisualProfile(subject="building", image_led=True, busy=False)
    plan = _plan(intent="ARCHITECTURE", profile=building)
    bp = build_composition_blueprint(plan=plan, profile=building, format_preset="square")
    assert bp.composition_family in {"ARCHITECTURAL_MINIMAL", "IMAGE_DOMINANT", "LOWER_THIRD"}
    mid = bp.headline_region.y + bp.headline_region.h / 2
    # Sky band, lower-third band, or a narrow side column — not a large centered stack on the facade.
    assert mid < 30 or mid > 62 or bp.headline_region.w <= 48


def test_investment_metrics_are_one_system_not_always_horizontal() -> None:
    plan = _plan(intent="INVESTMENT", metrics=True)
    layout, region = choose_metric_composition(
        family="INVESTMENT_GRID", metric_count=3, format_preset="square"
    )
    assert layout in {"2X2_GRID", "VERTICAL_STACK", "SIDE_PANEL"}
    assert layout != "HORIZONTAL_ROW"
    bp = build_composition_blueprint(
        plan=plan, format_preset="square", metric_count=3, include_metrics=True
    )
    assert bp.metric_region is not None
    assert bp.metric_layout in {"2X2_GRID", "VERTICAL_STACK", "HORIZONTAL_ROW", "FLOATING_GROUP", "SIDE_PANEL"}
    from investhome_api.services.social_design_engine.metrics import StructuredMetric

    metrics = [
        StructuredMetric(
            id="m1", type="currency", raw_value=500000, display_value="$500,000",
            label="Min", unit="USD", locale="en",
        ),
        StructuredMetric(
            id="m2", type="return", raw_value=14, display_value="14%",
            label="Yield", unit="%", locale="en",
        ),
        StructuredMetric(
            id="m3", type="duration", raw_value=24, display_value="24 mo",
            label="Term", unit="mo", locale="en",
        ),
    ]
    chosen = choose_metric_group_layout(
        metrics=metrics,
        format_preset="square",
        canvas_w=1080,
        available_width=840,
        family="INVESTMENT_GRID",
    )
    assert chosen in {"cards", "stacked", "horizontal"}


def test_grid_solver_uses_normalized_relationships() -> None:
    plan = _plan(intent="LOCATION")
    bp = build_composition_blueprint(plan=plan, format_preset="square")
    assert 5.0 <= bp.grid.margin_x <= 10.0
    assert bp.grid.columns == 12
    slots = blueprint_slots(bp, 1080, 1080)
    assert slots["headline"]["x"] >= 40
    assert slots["headline"]["x"] + slots["headline"]["width"] <= 1080 - 40
    story = build_composition_blueprint(plan=plan, format_preset="story")
    assert story.grid.margin_y >= bp.grid.margin_y


def test_grouping_and_collision_engine() -> None:
    boxes = {
        "headline": {"x": 80, "y": 80, "width": 600, "height": 120},
        "body": {"x": 80, "y": 100, "width": 500, "height": 80},
        "cta": {"x": 80, "y": 140, "width": 220, "height": 48},
    }
    resolved = resolve_group_collisions(boxes, canvas_w=1080, canvas_h=1080, gap=16)
    assert resolved["body"]["y"] >= resolved["headline"]["y"] + resolved["headline"]["height"]
    assert resolved["cta"]["y"] >= resolved["body"]["y"] + resolved["body"]["height"]
    protected = {"x": 200, "y": 300, "width": 600, "height": 400}
    overlapped = {"headline": {"x": 220, "y": 340, "width": 400, "height": 80}}
    moved = resolve_group_collisions(
        overlapped, canvas_w=1080, canvas_h=1080, protected=protected, gap=12
    )
    head = moved["headline"]
    hy = head["y"] + head["height"] // 2
    assert not (protected["y"] <= hy <= protected["y"] + protected["height"]) or head["y"] < protected["y"]


def test_reflow_prefers_layout_then_breaks_then_font() -> None:
    plan = _plan(intent="BRAND")
    bp = build_composition_blueprint(plan=plan, format_preset="square", include_cta=False)
    from investhome_api.services.social_design_engine.generation import DesignPlanElement

    elements = [
        DesignPlanElement(
            type="TEXT",
            role="headline",
            text="A Central Washington Address",
            x=40,
            y=40,
            width=400,
            height=40,
            font_size=72,
            align="left",
        )
    ]
    laid = apply_blueprint_to_elements(
        elements, blueprint=bp, canvas_w=1080, canvas_h=1080, density="LOW", format_preset="square"
    )
    assert laid[0].font_size >= 28
    assert laid[0].height >= laid[0].font_size


def test_claim_guard_metrics_stay_off_location_canvas() -> None:
    prompt = "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium Instagram postu."
    intent = classify_generation_intent(prompt, project_name="The Temple")
    concept = direct_creative(
        instruction=prompt,
        intent=intent,
        context=_ctx(),
        campaign_facts=[],
        sibling_posts=[
            {
                "generationMeta": {
                    "campaign_facts": [{"display": "$500,000", "kind": "money"}],
                    "composition_blueprint": {
                        "composition_family": "INVESTMENT_GRID",
                        "headline_region_kind": "lower_third",
                        "metric_region_kind": "grid_block",
                        "cta_placement": "lower_third",
                    },
                }
            }
        ],
    )
    assert concept.structured_metrics == []
    assert "$500" not in (concept.primary_message or "")
    assert concept.composition_blueprint.get("composition_family") != "INVESTMENT_GRID" or not concept.include_metrics


def test_create_vs_edit_redesign_phrase() -> None:
    assert is_explicit_redesign("Bu tasarımı tamamen yeniden düzenle.")
    assert is_explicit_redesign("Bu postu tamamen yeniden tasarla.")
    assert not is_explicit_redesign("Başlığı biraz küçült")


def test_blueprint_persists_and_is_not_recomputed_on_reload() -> None:
    plan = _plan(intent="LIFESTYLE")
    bp = build_composition_blueprint(plan=plan, format_preset="square")
    payload = composition_blueprint_to_dict(bp)
    restored = composition_blueprint_from_dict(payload)
    assert restored is not None
    assert restored.composition_family == bp.composition_family
    assert restored.headline_region.x == bp.headline_region.x
    post: dict = {"id": "p1", "elements": [{"type": "TEXT", "role": "headline", "x": 90, "y": 70, "width": 500, "height": 80}]}
    meta = build_generation_metadata(
        project_id=TEMPLE_PROJECT_ID,
        user_prompt="lifestyle",
        intent=classify_generation_intent("lifestyle post", project_name="The Temple"),
        campaign_facts=[],
        source_document_ids=[],
        selected_asset_ids=[],
        provider="test",
        model="test",
        composition_blueprint=payload,
    )
    attach_generation_metadata(post, meta=meta)
    assert post["compositionBlueprint"]["composition_family"] == bp.composition_family
    assert post["elements"][0]["x"] == 90
    post["geometryLocked"] = True
    apply_layout_grammar(post)
    assert post["elements"][0]["x"] == 90


def test_diversity_memory_rotates_family_and_regions() -> None:
    building = AssetVisualProfile(subject="building", image_led=True)
    first = build_composition_blueprint(
        plan=_plan(intent="LOCATION", profile=building, instruction="first location"),
        profile=building,
        format_preset="square",
        instruction="first location",
        project_id=str(TEMPLE_PROJECT_ID),
    )
    second = build_composition_blueprint(
        plan=_plan(intent="LOCATION", profile=building, instruction="second location post"),
        profile=building,
        format_preset="square",
        used_signals=first.diversity_tokens(),
        instruction="second location post",
        project_id=str(TEMPLE_PROJECT_ID),
    )
    assert first.diversity_key != second.diversity_key or first.composition_family != second.composition_family


def test_image_analysis_has_no_hardcoded_temple_coordinates() -> None:
    import inspect
    from investhome_api.services.social_design_engine import composition_engine as ce

    src = inspect.getsource(ce.analyze_image)
    assert "1610" not in src
    assert "Columbia Rd" not in src
    building = analyze_image(AssetVisualProfile(subject="building"))
    people = analyze_image(AssetVisualProfile(subject="people"))
    assert building.focal_region.y != people.focal_region.y or building.negative_space.y != people.negative_space.y


def test_split_ratios_are_constrained() -> None:
    plan = _plan(intent="EDUCATIONAL")
    bp = build_composition_blueprint(
        plan=plan, format_preset="landscape", include_support=True, include_metrics=False
    )
    if bp.composition_family == "SPLIT_LAYOUT":
        assert bp.split_ratio in {"30/70", "40/60", "50/50", None}


def test_design_plan_emits_blueprint_and_varied_geometry() -> None:
    loc = classify_generation_intent(
        "The Temple location in Washington DC premium Instagram post.",
        project_name="The Temple",
    )
    concept = direct_creative(
        instruction="The Temple location in Washington DC premium Instagram post.",
        intent=loc,
        context=_ctx(),
        campaign_facts=[],
    )
    package = ContentPackage(
        headline=concept.primary_message or "A Central Washington Address",
        supporting_text=concept.supporting_message,
        key_fact="",
        cta=concept.cta,
        language="en",
        tone="premium",
        eyebrow=concept.eyebrow,
    )
    plan = build_design_plan(
        package=package,
        intent=loc,
        picked_asset_id=None,
        post_id="p1",
        rebuild=False,
        concept=concept,
    )
    assert plan.composition_blueprint.get("composition_family")
    headline = next(el for el in plan.elements if el.role == "headline")
    assert headline.y < 400 or headline.y > 500
    inv = classify_generation_intent(
        "Investor post. Minimum yatırım $500,000 hedef getiri %14 süre 24 ay.",
        project_name="The Temple",
    )
    inv_concept = direct_creative(
        instruction="Investor post. Minimum yatırım $500,000 hedef getiri %14 süre 24 ay.",
        intent=inv,
        context=_ctx(),
        campaign_facts=[
            CampaignFact(label="min", display="$500,000", kind="money"),
            CampaignFact(label="yield", display="14%", kind="percent"),
            CampaignFact(label="term", display="24 months", kind="duration"),
        ],
    )
    inv_pkg = ContentPackage(
        headline=inv_concept.primary_message or "The Temple",
        supporting_text="",
        key_fact="",
        cta=inv_concept.cta,
        language="en",
        tone="premium",
        eyebrow=inv_concept.eyebrow,
    )
    inv_plan = build_design_plan(
        package=inv_pkg,
        intent=inv,
        picked_asset_id=None,
        post_id="p2",
        rebuild=False,
        concept=inv_concept,
        structured_metrics=inv_concept.structured_metrics,
    )
    assert any(el.type == "METRIC_GROUP" for el in inv_plan.elements)
    loc_h = next(el for el in plan.elements if el.role == "headline")
    inv_h = next(el for el in inv_plan.elements if el.role == "headline")
    assert (loc_h.y, loc_h.x) != (inv_h.y, inv_h.x) or plan.composition_family != inv_plan.composition_family


def test_line_break_does_not_orphan_short_tails() -> None:
    broken = prevent_orphan_words("The Temple formu", max_width=200, font_size=64)
    assert not broken.endswith("\nformu") or "Temple" in broken.split("\n")[-1]


def test_luxury_brand_on_building_uses_sky_not_facade() -> None:
    building = AssetVisualProfile(subject="building", image_led=True, brightness="mixed")
    plan = _plan(intent="BRAND", profile=building, instruction="luxury brand lockup")
    bp = build_composition_blueprint(
        plan=plan,
        profile=building,
        format_preset="square",
        include_cta=False,
        include_support=False,
        used_signals=["IMAGE_DOMINANT", "STATEMENT_LAYOUT"],
    )
    assert bp.composition_family == "LUXURY_BRAND"
    mid = bp.headline_region.y + bp.headline_region.h / 2
    assert mid < 32 or mid > 70
    assert bp.headline_region.w <= 72
    assert bp.alignment == "left"


def test_floating_data_three_metrics_use_wide_readable_band() -> None:
    skyline = AssetVisualProfile(
        subject="skyline", image_led=True, empty_negative_space=True, brightness="light"
    )
    plan = _plan(intent="INVESTMENT", metrics=True, profile=skyline)
    bp = build_composition_blueprint(
        plan=plan,
        profile=skyline,
        format_preset="square",
        metric_count=3,
        include_metrics=True,
        instruction="floating data investment",
        used_signals=["INVESTMENT_GRID", "LOWER_THIRD", "SPLIT_LAYOUT"],
    )
    assert bp.composition_family == "FLOATING_DATA"
    assert bp.metric_region is not None
    assert bp.metric_region.w >= 78
    assert bp.metric_region.y >= 60
    slots = blueprint_slots(bp, 1080, 1080)
    assert slots["metric_group"]["width"] >= 720
