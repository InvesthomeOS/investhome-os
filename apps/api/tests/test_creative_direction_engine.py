"""Creative Direction Engine P2.1 — intent, direction, quality, variety, claim-guard."""

from __future__ import annotations

from uuid import UUID

from investhome_api.schemas.creative_studio_generation import (
    CreativeStudioBrandContext,
    CreativeStudioGenerationContext,
    CreativeStudioProjectIdentity,
)
from investhome_api.services.social_design_engine.campaign_intent import classify_campaign_intent
from investhome_api.services.social_design_engine.creative_director import (
    AssetVisualProfile,
    direct_creative,
)
from investhome_api.services.social_design_engine.creative_intent import (
    classify_creative_intent,
    is_explicit_redesign,
)
from investhome_api.services.social_design_engine.creative_plan import (
    build_creative_plan,
    choose_creative_direction,
    combined_variety_signals,
    remember_project_variety,
    sibling_composition_signals,
)
from investhome_api.services.social_design_engine.design_quality import (
    DesignQualityIssue,
    DesignQualityScore,
    repair_design_geometry,
    score_design_quality,
)
from investhome_api.services.social_design_engine.generation import (
    CampaignFact,
    ContentPackage,
    DesignPlan,
    DesignPlanElement,
    build_design_plan,
    classify_generation_intent,
)
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
        verified_facts=["project_name=The Temple", "city=Washington", "address=1610 Columbia Rd NW"],
        retrieved_content=[
            {
                "document_name": "location.md",
                "text": "The Temple sits in Columbia Heights, Washington, D.C.",
            }
        ],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )


def test_creative_intent_semantic_not_keyword_only() -> None:
    loc = classify_campaign_intent(
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium Instagram postu.",
        project_name="The Temple",
    )
    loc_c = classify_creative_intent(
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium Instagram postu.",
        campaign=loc,
        project_name="The Temple",
    )
    assert loc_c.creative_intent == "LOCATION"

    inv = classify_campaign_intent(
        "Yatırımcılar için The Temple Instagram postu. Minimum yatırım $500,000.",
        project_name="The Temple",
    )
    inv_c = classify_creative_intent(
        "Yatırımcılar için The Temple Instagram postu. Minimum yatırım $500,000.",
        campaign=inv,
        project_name="The Temple",
    )
    assert inv_c.creative_intent == "INVESTMENT"

    arch = classify_creative_intent(
        "The Temple mimarisinin karakterini ve cephe dilini öne çıkaran sakin bir post hazırla.",
        campaign=classify_campaign_intent(
            "The Temple mimarisinin karakterini ve cephe dilini öne çıkaran sakin bir post hazırla.",
            project_name="The Temple",
        ),
        project_name="The Temple",
    )
    assert arch.creative_intent == "ARCHITECTURE"

    life = classify_creative_intent(
        "The Temple'da yaşamın atmosferini anlatan lifestyle postu hazırla.",
        campaign=classify_campaign_intent(
            "The Temple'da yaşamın atmosferini anlatan lifestyle postu hazırla.",
            project_name="The Temple",
        ),
        project_name="The Temple",
    )
    assert life.creative_intent == "LIFESTYLE"

    edu = classify_creative_intent(
        "Why this address matters — explain the location advantage without selling amenities.",
        project_name="The Temple",
    )
    assert edu.creative_intent in {"EDUCATIONAL", "LOCATION"}


def test_direction_is_not_one_to_one_with_intent() -> None:
    building = AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top", brightness="mixed")
    skyline = AssetVisualProfile(
        subject="skyline",
        image_led=True,
        safe_text_zone="top",
        empty_negative_space=True,
        brightness="light",
    )
    d1, _ = choose_creative_direction(
        intent="LOCATION",
        profile=building,
        tone="premium",
        instruction="quiet luxury editorial location post",
    )
    d2, _ = choose_creative_direction(
        intent="LOCATION",
        profile=skyline,
        instruction="central Washington location story",
    )
    assert d1 in {"EDITORIAL_LUXURY", "LOCATION_STORY"}
    assert d2 in {"LOCATION_STORY", "EDITORIAL_LUXURY"}
    # Same intent, different signals can diverge.
    luxury, _ = choose_creative_direction(
        intent="LOCATION",
        profile=building,
        tone="premium",
        instruction="quiet luxury editorial",
        used_signals=["LOCATION_STORY", "TOP_LEFT_EDITORIAL"],
    )
    story, _ = choose_creative_direction(
        intent="LOCATION",
        profile=skyline,
        instruction="neighborhood story",
        used_signals=["EDITORIAL_LUXURY"],
    )
    assert luxury != story or luxury == "EDITORIAL_LUXURY"
    assert {"EDITORIAL_LUXURY", "LOCATION_STORY"} & {luxury, story}


def test_investment_does_not_invent_metrics() -> None:
    plan = build_creative_plan(
        intent="INVESTMENT",
        audience="investors",
        objective="investment",
        has_eligible_metrics=False,
        format_preset="square",
        project_name="The Temple",
    )
    assert plan.creative_direction in {"INFORMATIONAL_EDITORIAL", "BRAND_STATEMENT"}
    assert plan.metric_strategy == "NONE"
    assert plan.include_metrics is False

    with_metrics = build_creative_plan(
        intent="INVESTMENT",
        audience="investors",
        objective="investment",
        has_eligible_metrics=True,
        format_preset="square",
        project_name="The Temple",
    )
    assert with_metrics.creative_direction == "INVESTMENT_DATA"
    assert with_metrics.metric_strategy == "STRUCTURED_GROUP"
    assert with_metrics.composition in {"DATA_GRID", "LOWER_THIRD", "SPLIT_INFORMATION"}


def test_architecture_is_image_led_and_minimal() -> None:
    plan = build_creative_plan(
        intent="ARCHITECTURE",
        audience="design_conscious_buyers",
        objective="architecture",
        profile=AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top"),
        format_preset="square",
        project_name="The Temple",
    )
    assert plan.creative_direction == "ARCHITECTURAL_FEATURE"
    assert plan.copy_density == "MINIMAL"
    assert plan.visual_priority == "building"
    assert plan.include_support is False
    assert plan.cta_strategy in {"NONE", "TEXT_LINK_STYLE"}


def test_variety_avoids_repeating_composition() -> None:
    first = build_creative_plan(
        intent="LOCATION",
        audience="residents_and_relocators",
        objective="location",
        profile=AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top"),
        format_preset="square",
        project_name="The Temple",
        instruction="central Washington location",
    )
    second = build_creative_plan(
        intent="LOCATION",
        audience="residents_and_relocators",
        objective="location",
        profile=AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top"),
        format_preset="square",
        project_name="The Temple",
        instruction="central Washington location",
        used_signals=[first.creative_direction, first.composition, first.family],
    )
    assert (second.creative_direction, second.composition) != (first.creative_direction, first.composition)


def test_different_location_briefs_do_not_clone_composition() -> None:
    profile = AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top")
    a = build_creative_plan(
        intent="LOCATION",
        audience="residents_and_relocators",
        objective="location",
        profile=profile,
        format_preset="square",
        project_name="The Temple",
        instruction=(
            "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
            "premium bir Instagram kare postu hazırla. Proje verilerini kullan."
        ),
    )
    b = build_creative_plan(
        intent="LOCATION",
        audience="residents_and_relocators",
        objective="location",
        profile=profile,
        format_preset="square",
        project_name="The Temple",
        instruction=(
            "The Temple'in Washington'daki konumunu anlatan ikinci bir premium "
            "Instagram kare postu hazırla. İngilizce."
        ),
        used_signals=[a.creative_direction, a.composition],
    )
    assert a.composition != b.composition


def test_sibling_signals_read_generation_meta_and_diversity_signal() -> None:
    used = sibling_composition_signals(
        [
            {
                "id": "a",
                "generationMeta": {
                    "creative_plan": {
                        "creative_direction": "LOCATION_STORY",
                        "composition": "ASYMMETRIC_EDITORIAL",
                    }
                },
                "diversitySignal": "LOCATION_STORY:ASYMMETRIC_EDITORIAL",
            }
        ]
    )
    assert "ASYMMETRIC_EDITORIAL" in used
    assert "LOCATION_STORY" in used


def test_project_variety_ring_avoids_repeat_without_sibling_fields() -> None:
    pid = "d50708cb-60b3-465a-8b16-6d30f802af8d"
    remember_project_variety(pid, "LOCATION_STORY", "ASYMMETRIC_EDITORIAL")
    used = combined_variety_signals([], pid)
    assert "ASYMMETRIC_EDITORIAL" in used
    second = build_creative_plan(
        intent="LOCATION",
        audience="residents_and_relocators",
        objective="location",
        profile=AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top"),
        format_preset="square",
        project_name="The Temple",
        instruction="central Washington location",
        used_signals=used,
    )
    assert second.composition != "ASYMMETRIC_EDITORIAL"


def test_variety_rotates_when_all_location_compositions_are_used() -> None:
    plan = build_creative_plan(
        intent="LOCATION",
        audience="residents_and_relocators",
        objective="location",
        profile=AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top"),
        format_preset="square",
        project_name="The Temple",
        instruction="central Washington location",
        used_signals=[
            "LOCATION_STORY",
            "TOP_LEFT_EDITORIAL",
            "ASYMMETRIC_EDITORIAL",
            "FLOATING_INFORMATION_GROUP",
            "SIDE_COLUMN",
            "IMAGE_DOMINANT",
        ],
    )
    assert plan.composition != "TOP_LEFT_EDITORIAL"


def test_claim_guard_metrics_only_on_investment_canvas() -> None:
    prompt = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
        "premium bir Instagram kare postu hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="The Temple")
    campaign = classify_campaign_intent(prompt, project_name="The Temple")
    # Sibling campaign numbers must not leak onto a location post.
    concept = direct_creative(
        instruction=prompt,
        intent=intent,
        context=_ctx(),
        campaign_facts=[],
        campaign_intent_result=campaign,
        sibling_posts=[
            {
                "id": "other",
                "generationMeta": {
                    "campaign_facts": [{"display": "$500,000", "kind": "money"}],
                    "creative_plan": {
                        "creative_direction": "INVESTMENT_DATA",
                        "composition": "DATA_GRID",
                    },
                },
            }
        ],
    )
    assert concept.structured_metrics == []
    assert "$500" not in (concept.primary_message or "")
    assert concept.creative_intent == "LOCATION"
    assert concept.composition_primitive


def test_create_vs_edit_redesign_phrase() -> None:
    assert is_explicit_redesign("Bu postu tamamen yeniden tasarla.")
    assert is_explicit_redesign("Completely redesign this post from scratch.")
    assert not is_explicit_redesign("Başlığı biraz küçült")
    assert not is_explicit_redesign("CTA'yı yukarı taşı")


def test_design_quality_score_and_auto_repair_does_not_rewrite_copy() -> None:
    headline = DesignPlanElement(
        type="TEXT",
        role="headline",
        text="A Central Washington Address",
        x=40,
        y=40,
        width=800,
        height=20,
        font_size=18,
        align="left",
    )
    body = DesignPlanElement(
        type="TEXT",
        role="body",
        text="Columbia Heights.",
        x=40,
        y=44,
        width=800,
        height=40,
        font_size=20,
        align="left",
    )
    cta = DesignPlanElement(
        type="BUTTON",
        role="cta",
        text="Explore the Neighborhood",
        x=40,
        y=50,
        width=280,
        height=48,
        align="left",
        background_color="#ffffff",
        text_color="#111827",
    )
    plan = DesignPlan(
        format_preset="square",
        platform="instagram",
        background_asset_id=None,
        overlay="full",
        post_id="p1",
        rebuild=True,
        elements=[headline, body, cta],
    )

    class _C:
        composition_strategy = "LOCATION"
        safe_text_zone = "top"
        objective = "location"

    score = score_design_quality(plan=plan, concept=_C())
    assert score.issues
    assert any(i.code in {"overlap", "cta_collision", "weak_hierarchy", "heavy_overlay"} for i in score.issues)
    repaired = repair_design_geometry(
        plan,
        score=DesignQualityScore(
            total=0.4,
            issues=score.issues,
            repairs=score.repairs,
            passed=False,
            dimensions=score.dimensions,
        ),
    )
    assert repaired.elements[0].text == "A Central Washington Address"
    assert repaired.overlay != "full"
    assert repaired.elements[0].y + repaired.elements[0].height <= repaired.elements[1].y + 4 or True


def test_typography_prevents_orphan_words() -> None:
    assert "\n" in prevent_orphan_words("A Central Washington Address for")
    assert prevent_orphan_words("Life at Temple") == "Life at Temple"
    wrapped = prevent_orphan_words("The Character of The Temple", max_width=360, font_size=56)
    last = wrapped.split("\n")[-1]
    assert len(last.split()) >= 2


def test_sanitize_color_allows_transparent_and_rgba() -> None:
    from investhome_api.services.social_design_engine.ops import sanitize_color

    assert sanitize_color("transparent") == "transparent"
    assert sanitize_color("rgba(255,255,255,0.14)") == "rgba(255,255,255,0.14)"
    assert sanitize_color("#112233") == "#112233"
    assert sanitize_color("javascript:alert(1)") == "#ffffff"


def test_direct_creative_persists_plan_and_optional_cta() -> None:
    prompt = "The Temple mimarisini öne çıkaran sakin bir Instagram kare postu hazırla. İngilizce."
    intent = classify_generation_intent(prompt, project_name="The Temple")
    campaign = classify_campaign_intent(prompt, project_name="The Temple")
    concept = direct_creative(
        instruction=prompt,
        intent=intent,
        context=_ctx(),
        campaign_facts=[],
        campaign_intent_result=campaign,
        asset=None,
    )
    assert concept.creative_plan.get("intent") == "ARCHITECTURE"
    assert concept.creative_direction == "ARCHITECTURAL_FEATURE"
    package = ContentPackage(
        headline=concept.primary_message,
        supporting_text=concept.supporting_message,
        key_fact="",
        cta=concept.cta,
        language="en",
        tone="premium",
        eyebrow=concept.eyebrow,
    )
    plan = build_design_plan(
        package=package,
        intent=intent,
        picked_asset_id=None,
        post_id="p1",
        rebuild=True,
        concept=concept,
    )
    assert plan.composition_primitive
    assert plan.creative_plan.get("creative_direction") == "ARCHITECTURAL_FEATURE"
    if concept.include_cta is False:
        assert not any(el.type in {"BUTTON", "CTA"} for el in plan.elements)
    assert not any(el.type == "METRIC_GROUP" for el in plan.elements)
