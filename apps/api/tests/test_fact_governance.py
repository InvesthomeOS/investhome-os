"""Marketing-approved fact governance + financial claim guard."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.services.social_design_engine.campaign_intent import classify_campaign_intent
from investhome_api.services.social_design_engine.fact_governance import (
    CampaignContext,
    apply_conflicts_and_eligibility,
    is_marketing_eligible,
)
from investhome_api.services.social_design_engine.generation import extract_campaign_facts
from investhome_api.services.social_design_engine.project_knowledge import (
    build_project_knowledge_package,
)
from investhome_api.services.social_design_engine.verified_facts import (
    VerifiedFact,
    build_campaign_intelligence,
    build_verified_facts_from_knowledge,
    campaign_inputs_to_verified_facts,
    financial_metrics_from_verified,
)

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")


def _project_with_financials(**kwargs) -> Project:
    return Project(
        id=TEMPLE_PROJECT_ID,
        project_code="PRJ-T",
        project_name="Temple Residences",
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
        city="Washington",
        country="US",
        address="1610 Columbia Rd NW",
        projected_irr=kwargs.get("projected_irr", Decimal("19.5000")),
        projected_roi=kwargs.get("projected_roi", Decimal("27.8000")),
        equity_required=kwargs.get("equity_required", Decimal("14500000.00")),
    )


def _knowledge(project: Project | None = None, retrieved: list | None = None):
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )

    project = project or _project_with_financials()
    return build_project_knowledge_package(
        project=project,
        context=CreativeStudioGenerationContext(
            project_identity=CreativeStudioProjectIdentity(
                project_id=TEMPLE_PROJECT_ID,
                project_code="PRJ-T",
                project_name="Temple Residences",
                city="Washington",
                country="US",
            ),
            verified_facts=["project_name=Temple Residences", "city=Washington"],
            retrieved_content=retrieved
            or [
                {
                    "document_name": "invest.md",
                    "text": "Target return 19.5% vs alternate model 27.8%. Minimum ticket $1450K.",
                }
            ],
            selected_assets=[],
            citations=[],
            brand_context=CreativeStudioBrandContext(available=False, reason="none"),
            builder_type="social",
            language="en",
        ),
        media_candidates=[],
    )


def test_legacy_financial_requires_review_not_eligible() -> None:
    facts = build_verified_facts_from_knowledge(_knowledge())
    financials = [f for f in facts if f.is_financial]
    assert financials
    for fact in financials:
        if fact.key == "investment_narrative":
            continue
        assert fact.marketing_status == "requires_review"
        assert fact.derivation_type in {"canonical", "extracted"}
        decision = is_marketing_eligible(fact)
        assert decision.eligible is False
        assert "approved" not in decision.reason or "not" in decision.reason


def test_user_campaign_only_eligible_not_canonical() -> None:
    from investhome_api.services.social_design_engine.generation import CampaignFact

    user = campaign_inputs_to_verified_facts(
        [
            CampaignFact(label="campaign_money", display="$500,000", kind="money"),
            CampaignFact(label="campaign_percent", display="%14", kind="percent"),
            CampaignFact(label="campaign_duration", display="24 ay", kind="duration"),
        ]
    )
    assert user
    for fact in user:
        assert fact.marketing_status == "campaign_only"
        assert fact.derivation_type == "user_supplied"
        assert fact.is_campaign_scoped is True
        assert fact.campaign_scope == "current"
        assert is_marketing_eligible(fact).eligible is True
    knowledge = _knowledge()
    inv = str(knowledge.investment)
    assert "$500,000" not in inv
    assert "%14" not in inv
    assert "24 ay" not in inv


def test_conflict_blocks_both_eligible_returns() -> None:
    a = VerifiedFact(
        fact_id="a",
        category="investment",
        key="campaign_return",
        value="19.5%",
        display_value="19.5%",
        source="user_campaign_input",
        source_reference="user_prompt",
        confidence=1.0,
        verified=True,
        is_financial=True,
        is_campaign_scoped=True,
        visibility="public",
        marketing_status="campaign_only",
        derivation_type="user_supplied",
        campaign_scope="current",
    )
    b = VerifiedFact(
        fact_id="b",
        category="investment",
        key="target_return",
        value="27.8%",
        display_value="27.8%",
        source="user_campaign_input",
        source_reference="user_prompt",
        confidence=1.0,
        verified=True,
        is_financial=True,
        is_campaign_scoped=True,
        visibility="public",
        marketing_status="campaign_only",
        derivation_type="user_supplied",
        campaign_scope="current",
    )
    safe, trace, conflicts = apply_conflicts_and_eligibility([a, b], CampaignContext())
    assert "return" in conflicts
    assert not any(is_marketing_eligible(f).eligible for f in (a, b))
    assert all(not row["eligible"] for row in trace if row["is_financial"])
    assert safe == []


def test_unapproved_conflicting_returns_do_not_pick_a_winner() -> None:
    knowledge = _knowledge()
    intent = classify_campaign_intent(
        "The Temple için yatırımcı odaklı premium bir Instagram kare postu hazırla.",
        project_name="Temple Residences",
    )
    intel = build_campaign_intelligence(intent=intent, knowledge=knowledge, campaign_facts=[])
    assert intel.can_proceed is True
    public_fin = [f for f in intel.marketing_safe_facts if f.is_financial]
    assert public_fin == []
    blob = " ".join(f.display_value for f in intel.verified_campaign_facts)
    assert "19.5" not in blob
    assert "27.8" not in blob
    assert "1450" not in blob
    assert "14,500,000" not in blob
    metrics = financial_metrics_from_verified(
        intel.marketing_safe_facts, language="tr", instruction=intent.signals[0] if intent.signals else ""
    )
    assert metrics == []
    trace_blob = str(intel.claim_eligibility_trace)
    assert "requires_review" in trace_blob or "not_marketing_approved" in trace_blob or "verified_is_not" in trace_blob


def test_explicit_target_return_blocks_without_inventing() -> None:
    knowledge = _knowledge()
    intent = classify_campaign_intent(
        "The Temple'ın hedef getirisini öne çıkaran bir yatırım postu hazırla.",
        project_name="Temple Residences",
    )
    assert any(r.key == "target_return" and r.required for r in intent.explicit_fact_requests)
    intel = build_campaign_intelligence(intent=intent, knowledge=knowledge, campaign_facts=[])
    assert intel.can_proceed is False
    assert any(m.key == "target_return" and m.required for m in intel.missing_relevant_facts)
    assert intel.block_reason
    metrics = financial_metrics_from_verified(
        intel.marketing_safe_facts, language="tr", instruction="hedef getiri"
    )
    assert metrics == []


def test_explicit_campaign_metrics_are_marketing_safe() -> None:
    knowledge = _knowledge()
    prompt = (
        "The Temple için yatırımcı odaklı Instagram kare postu. "
        "Minimum yatırım: $500,000 Hedef getiri: %14 Yatırım süresi: 24 ay. İngilizce hazırla."
    )
    intent = classify_campaign_intent(prompt, project_name="Temple Residences")
    campaign = extract_campaign_facts(prompt)
    intel = build_campaign_intelligence(intent=intent, knowledge=knowledge, campaign_facts=campaign)
    assert intel.can_proceed is True
    displays = {f.display_value for f in intel.marketing_safe_facts if f.is_financial}
    assert any("500" in d for d in displays)
    assert any("14" in d for d in displays)
    assert any("24" in d for d in displays)
    assert not any("19.5" in d or "27.8" in d or "1450" in d for d in displays)
    assert "$500,000" not in str(knowledge.investment)
    metrics = financial_metrics_from_verified(
        intel.marketing_safe_facts, language="en", instruction=prompt
    )
    assert metrics
    metric_blob = " ".join(m.display_value for m in metrics)
    assert "19.5" not in metric_blob
    assert "27.8" not in metric_blob


def test_location_intent_no_financial_leak() -> None:
    knowledge = _knowledge()
    intent = classify_campaign_intent(
        "The Temple'ın Washington DC'deki merkezi lokasyon avantajını anlatan premium Instagram kare postu hazırla.",
        project_name="Temple Residences",
    )
    intel = build_campaign_intelligence(intent=intent, knowledge=knowledge, campaign_facts=[])
    assert intel.campaign_intent == "location"
    selected_fin = [f for f in intel.verified_campaign_facts if f.is_financial]
    assert selected_fin == []
    metrics = financial_metrics_from_verified(
        intel.verified_campaign_facts, language="tr", instruction="lokasyon"
    )
    assert metrics == []


def test_cd_and_metrics_cannot_see_blocked_facts() -> None:
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )
    from investhome_api.services.social_design_engine.campaign_intent import (
        apply_campaign_intent_to_generation_intent,
    )
    from investhome_api.services.social_design_engine.creative_director import direct_creative
    from investhome_api.services.social_design_engine.generation import classify_generation_intent
    from investhome_api.services.social_design_engine.marketing_strategist import build_marketing_strategy

    prompt = "The Temple için yatırımcı odaklı premium bir Instagram kare postu hazırla."
    knowledge = _knowledge()
    intent_c = classify_campaign_intent(prompt, project_name="Temple Residences")
    gen = apply_campaign_intent_to_generation_intent(
        intent_c,
        classify_generation_intent(prompt, project_name="Temple Residences"),
    )
    intel = build_campaign_intelligence(intent=intent_c, knowledge=knowledge, campaign_facts=[])
    ctx = CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name="Temple Residences",
            city="Washington",
            country="US",
        ),
        verified_facts=["project_name=Temple Residences", "city=Washington"],
        retrieved_content=[
            {
                "document_name": "invest.md",
                "text": "Investors are shown 19.5% and 27.8% target return with $1450K minimum.",
            }
        ],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )
    strategy = build_marketing_strategy(
        instruction=prompt,
        intent=gen,
        context=ctx,
        campaign_facts=[],
        campaign_intelligence=intel,
    )
    metrics = financial_metrics_from_verified(
        intel.marketing_safe_facts, language="en", instruction=prompt
    )
    concept = direct_creative(
        instruction=prompt,
        intent=gen,
        context=ctx,
        campaign_facts=[],
        strategy=strategy,
        structured_metrics=metrics,
        campaign_intelligence=intel,
    )
    blob = " ".join(
        [
            concept.primary_message,
            concept.supporting_message,
            concept.cta,
            concept.eyebrow,
            str(concept.structured_metrics),
            " ".join(f.text for f in concept.selected_facts),
        ]
    )
    assert "19.5" not in blob
    assert "27.8" not in blob
    assert "1450" not in blob
    assert concept.structured_metrics == []


def test_canonical_approved_flag_is_honored_not_mass_applied() -> None:
    knowledge = _knowledge()
    knowledge.investment["projected_roi_marketing_status"] = "approved"
    facts = build_verified_facts_from_knowledge(knowledge)
    roi = next(f for f in facts if f.key == "projected_roi")
    irr = next(f for f in facts if f.key == "projected_irr")
    assert roi.marketing_status == "approved"
    assert is_marketing_eligible(roi).eligible is True
    assert irr.marketing_status == "requires_review"
    assert is_marketing_eligible(irr).eligible is False
