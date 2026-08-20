"""Creative Director service — campaign brief + context (no image generation)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorCampaignRequest,
    CreativeDirectorCampaignResponse,
    CreativeDirectorReviseRequest,
)
from investhome_api.services.creative_director.brief import (
    generate_creative_strategy,
    parse_emphasis_words,
)
from investhome_api.services.creative_director.orchestrator import (
    assign_capabilities,
    infer_required_capabilities,
)
from investhome_api.services.creative_director.generate_ad import adapt_final_turkish_texts
from investhome_api.services.creative_director.pricing import build_pricing_claims, extract_unit_codes
from investhome_api.services.creative_director.production_brief import build_production_brief
from investhome_api.services.creative_director.quality_lock.design_direction import build_design_direction
from investhome_api.services.creative_director.quality_lock.intent import (
    classify_cd_campaign_intent,
    is_visual_lifestyle_intent,
)
from investhome_api.services.creative_director.quality_lock.message_strategy import build_message_strategy
from investhome_api.services.creative_director.quality_lock.simplicity import (
    apply_simplicity_caps,
    simplicity_caps_for_intent,
)
from investhome_api.services.creative_director.research import research_project_drive
from investhome_api.services.social_design_engine.generation import extract_campaign_facts
from investhome_api.services.social_design_engine.fact_governance import CampaignContext
from investhome_api.services.social_design_engine.verified_facts import (
    campaign_inputs_to_verified_facts,
)
from investhome_api.services.social_design_engine.fact_governance import apply_conflicts_and_eligibility


def _project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or getattr(project, "archived_at", None) is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _claim_guard_trace(
    *,
    brief: str,
    campaign_id: str,
) -> list[dict[str, Any]]:
    """Reuse Claim Guard eligibility for user-supplied campaign money/percent tokens."""
    facts = extract_campaign_facts(brief)
    verified = campaign_inputs_to_verified_facts(facts, campaign_context_id=campaign_id)
    ctx = CampaignContext(
        campaign_intent="unit_launch",
        current_campaign_id=campaign_id,
        user_supplied_keys=frozenset(f.key for f in verified),
    )
    _, trace, _ = apply_conflicts_and_eligibility(verified, ctx)
    return list(trace)


def _build_brief_response(
    *,
    campaign: CreativeDirectorCampaign,
    strategy: dict[str, Any],
    research: dict[str, Any],
    pricing: dict[str, Any],
    orchestration: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    selected_assets = []
    if research.get("selected_interior"):
        selected_assets.append(research["selected_interior"])
    brand_assets = []
    if research.get("selected_logo"):
        brand_assets.append(research["selected_logo"])

    claims = list(pricing.get("claims") or [])
    # Merge claim-guard eligibility rows under claims for transparency.
    guard = (campaign.context_json or {}).get("claim_eligibility_trace") or []

    return {
        "campaign_id": str(campaign.id),
        "project_id": str(campaign.linked_project_id),
        "mode": mode,
        "language": (campaign.context_json or {}).get("language"),
        "objective": strategy.get("objective"),
        "audience": strategy.get("audience"),
        "big_idea": strategy.get("big_idea") or strategy.get("concept"),
        "concept": strategy.get("concept"),
        "hero_message": strategy.get("hero_message"),
        "supporting_messages": strategy.get("supporting_messages") or [],
        "emphasis": parse_emphasis_words(
            campaign.original_brief,
            strategy.get("emphasis") or [],
        ),
        "sales_hook": strategy.get("sales_hook"),
        "offer": strategy.get("offer") or (pricing.get("price_presentation") or {}).get("copy"),
        "pricing": pricing.get("price_presentation"),
        "value_proposition": strategy.get("value_proposition"),
        "proof_points": strategy.get("proof_points") or [],
        "cta": strategy.get("cta"),
        "first_2_seconds": strategy.get("first_2_seconds"),
        "thinking_notes": strategy.get("thinking_notes"),
        "visual_direction": strategy.get("visual_direction"),
        "composition_direction": strategy.get("composition_direction"),
        "typography_direction": strategy.get("typography_direction"),
        "color_direction": strategy.get("color_direction"),
        "selected_assets": selected_assets,
        "brand_assets": brand_assets,
        "tone": strategy.get("tone"),
        "formats": strategy.get("formats") or [],
        "claims": claims,
        "approved_claims": [c for c in claims if c.get("verified")],
        "blocked_claims": [
            t
            for t in guard
            if isinstance(t, dict) and (t.get("eligible") is False or t.get("rejection_reason"))
        ],
        "claim_eligibility_trace": guard,
        "required_capabilities": orchestration.get("required_capabilities") or [],
        "capability_assignments": orchestration.get("assignments") or [],
        "missing_capabilities": orchestration.get("missing_capabilities") or [],
        "provider_registry": orchestration.get("providers") or [],
        "drive_sources": research.get("drive_sources") or [],
        "unit_research": research.get("unit_mentions") or [],
        "pricing_honesty": pricing.get("honesty"),
        "recommended_outputs": strategy.get("recommended_outputs") or [],
        "required_assets": strategy.get("required_assets") or [],
        "required_project_data": strategy.get("required_project_data") or [],
        "warnings": research.get("warnings") or [],
        "generated_assets": (campaign.context_json or {}).get("generated_assets") or [],
        "output_history": (campaign.context_json or {}).get("output_history") or [],
        "image_generation_performed": bool(
            (campaign.context_json or {}).get("image_generation_performed")
        ),
        "production_brief": (campaign.context_json or {}).get("production_brief") or {},
        "campaign_intent": (campaign.context_json or {}).get("campaign_intent"),
        "message_strategy": (campaign.context_json or {}).get("message_strategy") or {},
        "design_direction": (campaign.context_json or {}).get("design_direction") or {},
        "simplicity_director": (campaign.context_json or {}).get("simplicity_director") or {},
    }


def create_campaign(
    db: Session,
    user: User,
    body: CreativeDirectorCampaignRequest,
) -> CreativeDirectorCampaignResponse:
    """Create Campaign Context + structured Creative Brief. NO image generation."""
    project = _project_or_404(db, body.project_id)
    mode = (body.mode or "project").strip().lower()
    if mode not in {"project", "general"}:
        mode = "project"
    brief = (body.brief or "").strip()
    if not brief:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="brief is required")

    unit_codes = extract_unit_codes(brief)
    # Early price-pair detection so research can prefer sales-hero frames.
    pricing_preview = build_pricing_claims(brief=brief, drive_prices={"units": {}})
    has_price_pair = bool(
        (pricing_preview.get("price_presentation") or {}).get("list")
        and (pricing_preview.get("price_presentation") or {}).get("offer")
    )
    quality_intent = classify_cd_campaign_intent(
        brief,
        language=body.language,
        project_name=project.project_name,
        project_knowledge=" ".join(
            p for p in (project.city, project.state, project.address or "", project.project_name) if p
        ),
        has_price_pair=has_price_pair,
    )

    research_pkg = research_project_drive(
        db,
        project=project,
        brief=brief,
        mode=mode,
        unit_codes=unit_codes,
        campaign_intent=quality_intent.campaign_intent,
    )
    research = research_pkg.to_dict()

    # Drive price hints from unit research (presence only — do not invent amounts).
    drive_prices: dict[str, Any] = {"units": {}}
    for um in research_pkg.unit_mentions:
        code = um.get("unit_code")
        if code:
            drive_prices["units"][str(code)] = {
                "found": um.get("found_in_drive"),
                "source_reference": "rag_hybrid_search",
            }

    pricing = build_pricing_claims(brief=brief, drive_prices=drive_prices)
    # Re-classify if pricing confirms a list→offer pair the preview missed.
    if (pricing.get("price_presentation") or {}).get("list") and (
        pricing.get("price_presentation") or {}
    ).get("offer"):
        quality_intent = classify_cd_campaign_intent(
            brief,
            language=body.language,
            project_name=project.project_name,
            project_knowledge=" ".join(
                p for p in (project.city, project.state, project.address or "", project.project_name) if p
            ),
            has_price_pair=True,
        )

    formats_hint = ["instagram_feed"]
    required_caps = infer_required_capabilities(brief=brief, mode=mode, formats=formats_hint)
    # Foundation sprint: document video if asked; always report missing stubs honestly.
    if body.include_video_capability:
        if "video_generate" not in required_caps:
            required_caps.append("video_generate")
    orchestration = assign_capabilities(required_caps).to_dict()

    strategy = generate_creative_strategy(
        user_brief=brief,
        project={
            "id": str(project.id),
            "name": project.project_name,
            "code": project.project_code,
            "city": project.city,
            "state": project.state,
            "country": project.country,
            "address": project.address,
        },
        research_summary=research,
        pricing=pricing,
        mode=mode,
    )

    campaign = CreativeDirectorCampaign(
        linked_project_id=project.id,
        created_by_user_id=getattr(user, "id", None),
        mode=mode,
        original_brief=brief,
        context_json={},
        status="draft",
    )
    db.add(campaign)
    db.flush()

    guard_trace = _claim_guard_trace(brief=brief, campaign_id=str(campaign.id))
    brief_payload = _build_brief_response(
        campaign=campaign,
        strategy=strategy,
        research=research,
        pricing=pricing,
        orchestration=orchestration,
        mode=mode,
    )
    # Attach guard after build helper (needs campaign id).
    brief_payload["claim_eligibility_trace"] = guard_trace
    brief_payload["blocked_claims"] = [
        t
        for t in guard_trace
        if isinstance(t, dict) and (t.get("eligible") is False or t.get("rejection_reason"))
    ]

    language = (body.language or quality_intent.language or "tr")
    lifestyle = is_visual_lifestyle_intent(quality_intent.campaign_intent) or not pricing.get(
        "list_price"
    )
    texts = adapt_final_turkish_texts(
        language=language,
        strategy=strategy,
        campaign_copy={
            "big_idea": strategy.get("big_idea") or strategy.get("concept"),
            "hero_message": strategy.get("hero_message"),
            "supporting_messages": strategy.get("supporting_messages"),
            "sales_hook": strategy.get("sales_hook"),
            "cta": strategy.get("cta"),
            "offer": strategy.get("offer"),
            "value_proposition": strategy.get("value_proposition"),
            "emphasis": strategy.get("emphasis"),
        },
        pricing=pricing,
        approved_claims=pricing.get("claims") or [],
        original_brief=brief,
        lifestyle=lifestyle,
    )
    caps = simplicity_caps_for_intent(quality_intent.campaign_intent)
    has_price = bool(
        (pricing.get("price_presentation") or {}).get("list")
        and (pricing.get("price_presentation") or {}).get("offer")
    )
    simplicity = apply_simplicity_caps(
        supporting_messages=strategy.get("supporting_messages") or [],
        caps=caps,
        include_price_block=has_price,
    )
    message_strategy = build_message_strategy(
        campaign_intent=quality_intent.campaign_intent,
        strategy=strategy,
        campaign_copy={
            "big_idea": strategy.get("big_idea") or strategy.get("concept"),
            "hero_message": strategy.get("hero_message"),
            "supporting_messages": simplicity.get("supporting_messages"),
            "sales_hook": strategy.get("sales_hook"),
            "cta": strategy.get("cta"),
            "offer": strategy.get("offer"),
        },
        pricing=pricing,
        texts=texts,
    )
    design_direction = build_design_direction(
        campaign_intent=quality_intent.campaign_intent,
        strategy=strategy,
        density=caps.density_label,
        language=language,
    )
    production_brief = build_production_brief(
        ctx={
            "selected_assets": brief_payload["selected_assets"],
            "campaign_intent": quality_intent.campaign_intent,
        },
        strategy=strategy,
        campaign_copy={
            "big_idea": strategy.get("big_idea") or strategy.get("concept"),
            "hero_message": strategy.get("hero_message"),
            "supporting_messages": simplicity.get("supporting_messages"),
            "sales_hook": strategy.get("sales_hook"),
            "cta": strategy.get("cta"),
            "offer": strategy.get("offer"),
        },
        pricing=pricing,
        texts=texts,
        approved_claims=pricing.get("claims") or [],
        blocked_claims=brief_payload.get("blocked_claims") or [],
        interior_meta=research.get("selected_interior") or {},
        logo_meta=research.get("selected_logo") or {},
        language=language,
        aspect_ratio="4:5",
        format_preset="portrait",
        message_strategy=message_strategy.to_dict(),
        design_direction=design_direction.to_dict(),
        simplicity_director=simplicity,
        campaign_intent=quality_intent.campaign_intent,
    )

    context = {
        "original_user_brief": brief,
        "language": language,
        "campaign_intent": quality_intent.campaign_intent,
        "legacy_campaign_intent": quality_intent.legacy_campaign_intent,
        "quality_intent": quality_intent.to_dict(),
        "message_strategy": message_strategy.to_dict(),
        "design_direction": design_direction.to_dict(),
        "simplicity_director": simplicity,
        "cd_strategy": strategy,
        "production_brief": production_brief,
        "approved_claims": brief_payload.get("approved_claims") or pricing.get("claims") or [],
        "blocked_claims": brief_payload.get("blocked_claims") or [],
        "claim_eligibility_trace": guard_trace,
        "selected_assets": brief_payload["selected_assets"],
        "selected_logo": research.get("selected_logo"),
        "campaign_copy": {
            "big_idea": brief_payload.get("big_idea"),
            "hero_message": brief_payload.get("hero_message"),
            "supporting_messages": simplicity.get("supporting_messages")
            or brief_payload.get("supporting_messages"),
            "sales_hook": brief_payload.get("sales_hook"),
            "cta": brief_payload.get("cta"),
            "offer": brief_payload.get("offer"),
            "value_proposition": brief_payload.get("value_proposition"),
            "emphasis": brief_payload.get("emphasis"),
        },
        "visual_direction": brief_payload.get("visual_direction"),
        "audience": brief_payload.get("audience"),
        "offer": brief_payload.get("offer"),
        "cta": brief_payload.get("cta"),
        "pricing": pricing,
        "drive_research": research,
        "orchestration": orchestration,
        "generated_assets": [],
        "output_history": [],
        "revision_history": [],
        "image_generation_performed": False,
    }
    campaign.context_json = context
    brief_payload["campaign_intent"] = quality_intent.campaign_intent
    brief_payload["message_strategy"] = message_strategy.to_dict()
    brief_payload["design_direction"] = design_direction.to_dict()
    brief_payload["simplicity_director"] = simplicity
    brief_payload["production_brief"] = production_brief
    db.flush()

    return CreativeDirectorCampaignResponse(
        campaign_id=campaign.id,
        project_id=project.id,
        brief=brief_payload,
        campaign_context=context,
    )


def get_campaign(db: Session, campaign_id: UUID) -> CreativeDirectorCampaignResponse:
    row = db.get(CreativeDirectorCampaign, campaign_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    ctx = row.context_json or {}
    strategy = ctx.get("cd_strategy") or {}
    research = ctx.get("drive_research") or {}
    pricing = ctx.get("pricing") or {}
    orchestration = ctx.get("orchestration") or {}
    brief_payload = _build_brief_response(
        campaign=row,
        strategy=strategy,
        research=research,
        pricing=pricing,
        orchestration=orchestration,
        mode=row.mode,
    )
    brief_payload["claim_eligibility_trace"] = ctx.get("claim_eligibility_trace") or []
    return CreativeDirectorCampaignResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        brief=brief_payload,
        campaign_context=ctx,
    )


def revise_campaign_stub(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorReviseRequest,
) -> CreativeDirectorCampaignResponse:
    """Stub for natural-language revision — stores instruction; does not re-run production."""
    _ = user
    row = db.get(CreativeDirectorCampaign, campaign_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    ctx = dict(row.context_json or {})
    history = list(ctx.get("revision_history") or [])
    history.append(
        {
            "instruction": (body.instruction or "").strip(),
            "status": "accepted_stub",
            "note": "Revision applied to context log only; full CD re-plan comes in a later sprint.",
        }
    )
    ctx["revision_history"] = history
    if body.instruction:
        ctx["latest_revision_instruction"] = body.instruction.strip()
    row.context_json = ctx
    db.flush()
    return get_campaign(db, campaign_id)
