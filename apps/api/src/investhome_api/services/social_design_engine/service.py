"""Social Media Builder AI Design Engine orchestration (Phase 1).

Flow: instruction → RAG (shared CS hybrid_search) → media candidates →
AI Design Planner (structured Design Ops) → validate → deterministic mutate →
return draft + metadata. Persistence stays on CS Document API (client).
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.social_design_engine import (
    SocialDesignGenerationMeta,
    SocialDesignRejectedOp,
    SocialDesignRequest,
    SocialDesignResponse,
)
from investhome_api.services.activity_service import ActivityRequestContext, log_activity
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.creative_studio_generation.assets import validate_selected_assets
from investhome_api.services.creative_studio_generation.context import (
    assert_context_has_no_forbidden_media,
    build_generation_context,
    load_brand_context,
    sanitize_builder_context,
)
from investhome_api.services.project_assistant.grounding import evaluate_grounding
from investhome_api.services.project_assistant.llm_provider import (
    LLMProviderConfigError,
    LLMProviderError,
    get_llm_provider,
)
from investhome_api.services.social_design_engine.apply import apply_ops
from investhome_api.services.social_design_engine.generation import (
    asset_preference_tokens,
    attach_generation_metadata,
    build_content_package_prompt,
    build_design_plan,
    build_generation_metadata,
    campaign_facts_for_mode,
    classify_generation_intent,
    compose_ops_from_plan,
    enforce_campaign_facts,
    infer_design_mode,
    parse_content_package_from_llm,
    resolve_campaign_context_id,
    resolve_generation_post_id,
    sibling_inventory_for_create,
)
from investhome_api.services.social_design_engine.creative_director import (
    creative_concept_to_dict,
    direct_creative,
)
from investhome_api.services.social_design_engine.marketing_strategist import (
    build_marketing_strategy,
    strategy_from_dict,
    strategy_to_dict,
)
from investhome_api.services.social_design_engine.copy_director import (
    apply_copy_intelligence_edit,
    build_copy_package,
    classify_copy_intelligence_edit,
    content_package_to_copy_package,
    copy_direction_to_dict,
    copy_edit_ops,
    copy_package_to_content_package,
    score_copy_quality,
)
from investhome_api.services.social_design_engine.campaign_intent import (
    apply_campaign_intent_to_generation_intent,
    classify_campaign_intent,
)
from investhome_api.services.social_design_engine.creative_intent import is_explicit_redesign
from investhome_api.services.social_design_engine.design_quality import evaluate_and_repair as evaluate_design_quality
from investhome_api.services.social_design_engine.project_knowledge import (
    build_project_knowledge_package,
)
from investhome_api.services.social_design_engine.verified_facts import (
    build_campaign_intelligence,
    campaign_intelligence_to_dict,
    financial_metrics_from_verified,
    missing_facts_to_dicts,
    verified_facts_to_dicts,
)
from investhome_api.services.social_design_engine.localization import choose_investment_cta
from investhome_api.services.social_design_engine.metrics import (
    MetricGroup,
    campaign_facts_to_structured_metrics,
    metric_group_to_dict,
    structured_metrics_to_dicts,
)
from investhome_api.services.social_design_engine.intent import (
    apply_selected_element_targets,
    classify_edit_intents,
    default_target_from_builder_context,
    enrich_color_intents,
    filter_ops_for_copy_protection,
    build_ops_from_intent_plan,
)
from investhome_api.services.social_design_engine.media import list_media_candidates, pick_best_asset
from investhome_api.services.social_design_engine.ops import find_post, normalize_raw_ops, validate_ops
from investhome_api.services.social_design_engine.planner import (
    build_design_prompt,
    build_heuristic_ops,
    parse_ops_from_llm,
)

DEFAULT_RETRIEVAL_LIMIT = 8
logger = logging.getLogger(__name__)


def _ensure_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found or inaccessible: {project_id}",
        )
    return project


def _audit(db: Session, user: User, *, entity_id: UUID, metadata: dict) -> None:
    safe = {
        k: v
        for k, v in metadata.items()
        if k not in {"api_key", "authorization", "prompt", "system", "user_prompt", "raw"}
    }
    log_activity(
        db,
        action=ActivityAction.VIEWED,
        entity_type=ActivityEntityType.PROJECT_AI,
        entity_id=entity_id,
        description_key="ai.creative_studio.social_design",
        actor_user=user,
        source=ActivitySource.AI_SERVICE,
        metadata=safe,
        request_context=ActivityRequestContext(source=ActivitySource.AI_SERVICE),
    )


def _infer_mode(
    requested: str,
    posts: list[dict[str, Any]],
    instruction: str,
    *,
    explicit: bool = False,
) -> str:
    """CREATE vs EDIT. Explicit UI clicks are authoritative; NL is the fallback."""
    return infer_design_mode(instruction, posts, requested, explicit=explicit)


def generate_social_design(
    db: Session,
    user: User,
    body: SocialDesignRequest,
) -> SocialDesignResponse:
    started = time.perf_counter()
    settings = get_settings()
    design_provider = (getattr(body, "design_provider", None) or "native").strip().lower()
    if design_provider == "ideogram":
        logger.info(
            "social_design_provider_rejected",
            extra={
                "design_provider": design_provider,
                "reason": "ideogram_must_use_ideogram_endpoint",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "design_provider=ideogram cannot run on the Native Social Design "
                "endpoint. Native generation was not invoked."
            ),
        )
    logger.info(
        "social_design_provider_route",
        extra={"design_provider": design_provider or "native", "provider": "native"},
    )

    linked_project_id = body.linked_project_id
    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="instruction is required")

    project = _ensure_project(db, linked_project_id)
    draft_posts = [dict(p) for p in (body.draft.posts or []) if isinstance(p, dict)]
    selected_post_id = body.draft.selected_post_id
    mode = _infer_mode(
        body.mode,
        draft_posts,
        instruction,
        explicit=bool(getattr(body, "mode_explicit", False)),
    )
    gen_intent = classify_generation_intent(
        instruction,
        language=body.language,
        project_name=project.project_name,
    )
    campaign_intent = classify_campaign_intent(
        instruction,
        language=body.language,
        project_name=project.project_name,
    )
    gen_intent = apply_campaign_intent_to_generation_intent(campaign_intent, gen_intent)
    active_for_facts = find_post(draft_posts, selected_post_id) if selected_post_id else None
    if active_for_facts is None and draft_posts:
        active_for_facts = draft_posts[0]
    campaign_context_id = resolve_campaign_context_id(
        mode=mode,
        draft_posts=draft_posts,
        selected_post_id=selected_post_id,
    )
    generation_context_id = str(uuid4())
    # CREATE: current prompt only. EDIT: selected post's campaign inputs + current prompt.
    # Never harvest previous canvas text/metrics as campaign facts.
    campaign_facts = campaign_facts_for_mode(
        mode=mode,
        instruction=instruction,
        selected_post=active_for_facts if mode == "edit" else None,
    )
    structured_metrics = campaign_facts_to_structured_metrics(
        campaign_facts,
        language=gen_intent.language,
        instruction=instruction,
    )
    effective_language = gen_intent.language or body.language

    selected_assets = validate_selected_assets(
        db,
        linked_project_id=linked_project_id,
        selected_asset_ids=list(body.selected_asset_ids or []),
    )
    builder_context, sanitize_warnings = sanitize_builder_context(body.builder_context)

    retrieval_limit = min(
        max(
            1,
            int(
                getattr(settings, "ai_assistant_retrieval_limit", DEFAULT_RETRIEVAL_LIMIT)
                or DEFAULT_RETRIEVAL_LIMIT
            ),
        ),
        20,
    )
    min_score = float(getattr(settings, "ai_assistant_min_score", 0.12) or 0.12)

    search_started = time.perf_counter()
    try:
        hits = hybrid_search(
            db,
            query=instruction,
            project_scope="single",
            project_id=linked_project_id,
            project_ids=None,
            limit=retrieval_limit,
            builder="social",
        )
        if not hits:
            hits = hybrid_search(
                db,
                query=instruction,
                project_scope="single",
                project_id=linked_project_id,
                project_ids=None,
                limit=retrieval_limit,
            )
    except ProjectScopeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    search_time_ms = int((time.perf_counter() - search_started) * 1000)

    for hit in hits:
        if hit.project_id != linked_project_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="cross_project_retrieval_isolation_failure",
            )

    brand_context = load_brand_context(db, project_id=linked_project_id)
    grounding = evaluate_grounding(hits, min_score=min_score)
    context = build_generation_context(
        project=project,
        builder_type="social",
        language=effective_language,
        hits=hits if grounding.sufficient else [],
        selected_assets=selected_assets,
        brand_context=brand_context,
        extra_warnings=list(sanitize_warnings),
    )
    if not grounding.sufficient and "insufficient_context" not in context.warnings:
        context.warnings.append("insufficient_context")
    if not brand_context.available and "brand_context_unavailable" not in context.warnings:
        context.warnings.append("brand_context_unavailable")

    assert_context_has_no_forbidden_media(context)

    media_candidates = list_media_candidates(
        db,
        linked_project_id=linked_project_id,
        instruction=instruction,
        limit=24,
        preference_tokens=asset_preference_tokens(gen_intent.asset_preference),
    )
    picked = pick_best_asset(media_candidates, require_image=True)
    if picked is None and "no_valid_project_media" not in context.warnings:
        context.warnings.append("no_valid_project_media")

    # Project-Aware Campaign Intelligence (before Marketing Strategist)
    project_knowledge = build_project_knowledge_package(
        project=project,
        context=context,
        media_candidates=media_candidates,
    )
    picked_candidate_early = next((c for c in media_candidates if picked and c.asset_id == picked), None)
    selected_asset_meta = None
    if picked_candidate_early is not None:
        selected_asset_meta = {
            "asset_id": str(picked_candidate_early.asset_id),
            "filename": picked_candidate_early.filename,
            "folder_category": picked_candidate_early.folder_category,
            "tags": list(picked_candidate_early.tags or []),
        }
    campaign_intel = build_campaign_intelligence(
        intent=campaign_intent,
        knowledge=project_knowledge,
        campaign_facts=campaign_facts,
        selected_asset=selected_asset_meta,
        campaign_context_id=campaign_context_id,
    )
    # Structured Metrics: eligible marketing-safe facts + current campaign inputs ONLY.
    # Never query raw project/RAG financials independently.
    if not structured_metrics:
        structured_metrics = financial_metrics_from_verified(
            campaign_intel.marketing_safe_facts,
            language=gen_intent.language,
            instruction=instruction,
        )

    allowed_asset_ids: set[UUID] = {a.asset_id for a in selected_assets}
    allowed_asset_ids.update(c.asset_id for c in media_candidates)
    if picked:
        allowed_asset_ids.add(picked)

    # Prefer a different cover/image asset when user asks to replace ("başka …")
    active_for_intent = find_post(draft_posts, selected_post_id) if selected_post_id else None
    if active_for_intent is None and draft_posts:
        active_for_intent = draft_posts[0]
    selected_default = default_target_from_builder_context(builder_context, active_for_intent)
    intent_plan = enrich_color_intents(
        classify_edit_intents(instruction, default_target=selected_default),
        instruction,
    )
    intent_plan = apply_selected_element_targets(
        intent_plan,
        builder_context=builder_context,
        post=active_for_intent,
        instruction=instruction,
    )
    if mode == "edit" and any(i.intent == "REPLACE_IMAGE" for i in intent_plan.intents):
        current_cover = None
        active = active_for_intent
        if active is not None:
            current_cover = active.get("coverAssetId") or active.get("cover_asset_id")
            for el in active.get("elements") or []:
                if isinstance(el, dict) and el.get("type") == "IMAGE" and (el.get("assetId") or el.get("asset_id")):
                    current_cover = el.get("assetId") or el.get("asset_id")
                    break
        if current_cover is not None:
            for cand in media_candidates:
                if str(cand.asset_id) != str(current_cover) and (cand.content_type or "").startswith("image/"):
                    picked = cand.asset_id
                    allowed_asset_ids.add(picked)
                    break

    try:
        provider = get_llm_provider(settings)
    except LLMProviderConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc

    max_prompt_chars = int(getattr(settings, "ai_assistant_max_prompt_chars", 14_000) or 14_000)

    planner_name = "heuristic"
    raw_ops: list[dict[str, Any]] = []
    summary = ""
    llm = None
    intent_rejected: list[tuple[dict[str, Any], str]] = []
    content_package = None
    design_plan = None
    creative_concept = None
    validation_payload = None
    design_quality_payload = None
    marketing_strategy = None
    copy_direction = None
    campaign_intel_payload = campaign_intelligence_to_dict(campaign_intel)

    # -------- Missing required financial fact: do not invent; keep prior design intact --------
    if mode == "create" and not campaign_intel.can_proceed:
        warnings = list(dict.fromkeys(list(context.warnings) + ["missing_required_facts"]))
        for m in campaign_intel.missing_relevant_facts:
            if m.required:
                warnings.append(f"missing_fact:{m.key}")
        latency_ms = int((time.perf_counter() - started) * 1000)
        brand_status = "available" if brand_context.available else "unavailable_neutral_premium"
        gen_meta_payload = build_generation_metadata(
            project_id=linked_project_id,
            user_prompt=instruction,
            intent=gen_intent,
            campaign_facts=campaign_facts,
            source_document_ids=[],
            selected_asset_ids=[str(a.asset_id) for a in selected_assets]
            + ([str(picked)] if picked else []),
            provider=provider.name,
            model=provider.model,
            campaign_intelligence=campaign_intel_payload,
            verified_facts=verified_facts_to_dicts(campaign_intel.verified_campaign_facts),
            missing_facts=missing_facts_to_dicts(campaign_intel.missing_relevant_facts),
            campaign_context_id=campaign_context_id,
            generation_context_id=generation_context_id,
        )
        event_id = uuid4()
        _audit(
            db,
            user,
            entity_id=event_id,
            metadata={
                "kind": "creative_studio_social_design",
                "linked_project_id": str(linked_project_id),
                "mode": mode,
                "instruction": instruction[:500],
                "provider": provider.name,
                "model": provider.model,
                "planner": "campaign_intelligence_blocked",
                "ops_count": 0,
                "rejected_count": 0,
                "latency_ms": latency_ms,
                "search_time_ms": search_time_ms,
                "hit_count": len(hits),
                "warnings": warnings,
                "block_reason": campaign_intel.block_reason,
            },
        )
        meta = SocialDesignGenerationMeta(
            citations=list(context.citations),
            warnings=warnings,
            grounded=False,
            retrieval_confidence=min(grounding.confidence, 0.2),
            asset_ids_used=[a.asset_id for a in selected_assets] + ([picked] if picked else []),
            provider=provider.name,
            model=provider.model,
            brand_context=brand_context,
            brand_context_status=brand_status,
            search_time_ms=search_time_ms,
            latency_ms=latency_ms,
            mode=mode,  # type: ignore[arg-type]
            planner="campaign_intelligence_blocked",
            intents=[],
            intent_targets=[],
            applied_intents=[],
            rejected_reasons=[campaign_intel.block_reason or "missing_required_facts"],
            copy_protected=False,
            generated_by="social_design_engine",
            project_id=linked_project_id,
            user_prompt=instruction[:2000],
            generation_intent=gen_meta_payload.get("generation_intent"),
            source_document_ids=[],
            selected_asset_ids=[a.asset_id for a in selected_assets] + ([picked] if picked else []),
            generated_at=gen_meta_payload.get("generated_at"),
            content_package=None,
            design_plan=None,
            campaign_facts=gen_meta_payload.get("campaign_facts") or [],
            structured_metrics=[],
            metric_group=None,
            creative_concept=None,
            validation=None,
            marketing_strategy=None,
            copy_quality=None,
            headline_candidates=[],
            campaign_intelligence=campaign_intel_payload,
            verified_facts=gen_meta_payload.get("verified_facts") or [],
            missing_facts=gen_meta_payload.get("missing_facts") or [],
            campaign_context_id=campaign_context_id,
            generation_context_id=generation_context_id,
        )
        return SocialDesignResponse(
            linked_project_id=linked_project_id,
            mode=mode,  # type: ignore[arg-type]
            ops=[],
            rejected_ops=[],
            posts=draft_posts,
            selected_post_id=selected_post_id,
            media_candidates=media_candidates,
            meta=meta,
            generated_content=campaign_intel.block_reason
            or "Missing required campaign facts. Provide the value(s) to continue.",
        )

    copy_kind, copy_edit_meta = classify_copy_intelligence_edit(instruction)
    if copy_kind == "change_objective" and copy_edit_meta.get("objective"):
        gen_intent.marketing_objective = copy_edit_meta["objective"]  # type: ignore[assignment]
        if copy_edit_meta["objective"] == "investment":
            gen_intent.audience = "investors"
            gen_intent.asset_preference = "premium_hero"
            gen_intent.cta_hint = choose_investment_cta(gen_intent.language)
        if mode != "edit":
            mode = "create"

    # -------- EDIT: copy-intelligence (same strategy) — not a full regenerate --------
    if mode == "edit" and copy_kind not in {"none", "change_objective"}:
        active = find_post(draft_posts, selected_post_id) if selected_post_id else None
        if active is None and draft_posts:
            active = draft_posts[0]
        if active is not None:
            prev_meta = active.get("generationMeta") if isinstance(active.get("generationMeta"), dict) else {}
            marketing_strategy = strategy_from_dict(prev_meta.get("marketing_strategy"))
            if marketing_strategy is None:
                marketing_strategy = build_marketing_strategy(
                    instruction=str(prev_meta.get("user_prompt") or instruction),
                    intent=gen_intent,
                    context=context,
                    campaign_facts=campaign_facts,
                    campaign_intelligence=campaign_intel,
                )
            current_pkg = None
            prev_copy = prev_meta.get("content_package") if isinstance(prev_meta.get("content_package"), dict) else {}
            if prev_copy:
                from investhome_api.services.social_design_engine.generation import ContentPackage

                current_pkg = content_package_to_copy_package(
                    ContentPackage(
                        headline=str(prev_copy.get("headline") or ""),
                        supporting_text=str(prev_copy.get("supporting_text") or ""),
                        key_fact=str(prev_copy.get("key_fact") or ""),
                        cta=str(prev_copy.get("cta") or ""),
                        language=str(prev_copy.get("language") or gen_intent.language),
                        tone=str(prev_copy.get("tone") or gen_intent.tone),
                        eyebrow=str(prev_copy.get("eyebrow") or ""),
                    )
                )
            if current_pkg is None:
                headline_el = next(
                    (
                        e
                        for e in (active.get("elements") or [])
                        if isinstance(e, dict) and e.get("role") == "headline"
                    ),
                    None,
                )
                body_el = next(
                    (
                        e
                        for e in (active.get("elements") or [])
                        if isinstance(e, dict) and e.get("role") == "body"
                    ),
                    None,
                )
                cta_el = next(
                    (
                        e
                        for e in (active.get("elements") or [])
                        if isinstance(e, dict) and e.get("type") in {"BUTTON", "CTA"}
                    ),
                    None,
                )
                from investhome_api.services.social_design_engine.copy_director import CopyPackage as _CP

                current_pkg = _CP(
                    eyebrow="",
                    headline=str((headline_el or {}).get("content") or ""),
                    supporting_copy=str((body_el or {}).get("content") or ""),
                    cta=str((cta_el or {}).get("label") or ""),
                    language=gen_intent.language,
                    tone=gen_intent.tone,
                )
            copy_direction = apply_copy_intelligence_edit(
                kind=copy_kind,
                meta=copy_edit_meta,
                strategy=marketing_strategy,
                intent=gen_intent,
                campaign_facts=campaign_facts,
                current=current_pkg,
            )
            content_package = copy_package_to_content_package(copy_direction.package)
            if campaign_facts and marketing_strategy.objective == "investment":
                content_package = enforce_campaign_facts(content_package, campaign_facts)
            raw_ops = copy_edit_ops(
                package=copy_direction.package,
                post=active,
                linked_project_id=str(linked_project_id),
            )
            planner_name = "copy_intelligence"
            summary = f"Applied copy intelligence edit ({copy_kind})."
            intent_plan.allow_copy_rewrite = True
            intent_plan.allow_cta_rewrite = True
            intent_plan.structural_only = False

    # -------- GENERATION: Strategist → Copy Director → Creative Director → plan --------
    explicit_redesign = is_explicit_redesign(instruction)
    regenerate_selected = mode == "edit" and (
        copy_kind == "change_objective" or explicit_redesign
    )
    if mode == "create" or regenerate_selected:
        picked_candidate = next((c for c in media_candidates if picked and c.asset_id == picked), None)
        marketing_strategy = build_marketing_strategy(
            instruction=instruction,
            intent=gen_intent,
            context=context,
            campaign_facts=campaign_facts,
            campaign_intelligence=campaign_intel,
        )
        copy_direction = build_copy_package(
            strategy=marketing_strategy,
            intent=gen_intent,
            campaign_facts=campaign_facts,
        )
        creative_concept = direct_creative(
            instruction=instruction,
            intent=gen_intent,
            context=context,
            campaign_facts=campaign_facts,
            asset=picked_candidate,
            strategy=marketing_strategy,
            copy_package=copy_direction.package,
            structured_metrics=structured_metrics,
            campaign_intelligence=campaign_intel,
            campaign_intent_result=campaign_intent,
            sibling_posts=draft_posts if mode == "create" else None,
        )
        content_package = copy_package_to_content_package(copy_direction.package)
        content_package = enforce_campaign_facts(content_package, campaign_facts)
        try:
            c_system, c_user = build_content_package_prompt(
                instruction=instruction,
                intent=gen_intent,
                context=context,
                campaign_facts=campaign_facts,
                concept=creative_concept,
                strategy=marketing_strategy,
                copy_package=copy_direction.package,
                max_prompt_chars=max_prompt_chars,
            )
            llm = provider.generate(system=c_system, user=c_user, timeout_seconds=60.0)
            parsed_pkg = parse_content_package_from_llm(llm.answer or "")
            if parsed_pkg is not None:
                llm_copy = content_package_to_copy_package(parsed_pkg)
                quality = score_copy_quality(
                    llm_copy,
                    strategy=marketing_strategy,
                    campaign_facts=campaign_facts,
                )
                if quality.passed:
                    content_package = enforce_campaign_facts(parsed_pkg, campaign_facts)
                    copy_direction.package = content_package_to_copy_package(content_package)
                    copy_direction.quality = quality
                    plan_flags = getattr(creative_concept, "creative_plan", None) or {}
                    if not plan_flags.get("include_support", True):
                        content_package.supporting_text = ""
                        content_package.key_fact = ""
                    if not plan_flags.get("include_cta", True):
                        content_package.cta = ""
                    if not plan_flags.get("include_eyebrow", True):
                        content_package.eyebrow = ""
                    creative_concept.primary_message = content_package.headline
                    creative_concept.supporting_message = content_package.supporting_text
                    creative_concept.cta = content_package.cta
                    creative_concept.eyebrow = content_package.eyebrow
                    creative_concept.include_eyebrow = bool(content_package.eyebrow) and bool(
                        plan_flags.get("include_eyebrow", True)
                    )
                    creative_concept.include_support = bool(content_package.supporting_text) and bool(
                        plan_flags.get("include_support", True)
                    )
                    creative_concept.include_cta = bool(content_package.cta) and bool(
                        plan_flags.get("include_cta", True)
                    )
                    planner_name = "generation+llm"
                else:
                    planner_name = "generation"
                    context.warnings.append("copy_quality_rejected_llm")
                    logger.warning(
                        "social design LLM copy failed quality gate (%s); using Copy Director package",
                        ",".join(quality.reject_codes),
                    )
            else:
                planner_name = "generation"
                logger.warning(
                    "social design content package LLM parse failed; using Copy Director package"
                )
        except LLMProviderError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
        except Exception:
            logger.exception("social design content package LLM failed; using Copy Director heuristic")
            context.warnings.append("content_package_fallback")
            planner_name = "generation"

        if creative_concept is not None and content_package is not None:
            if not creative_concept.include_support:
                content_package.supporting_text = ""
                content_package.key_fact = ""
            if not creative_concept.include_cta:
                content_package.cta = ""
            if not creative_concept.include_eyebrow:
                content_package.eyebrow = ""
        post_id, rebuild = resolve_generation_post_id(draft_posts, selected_post_id, mode=mode)
        design_plan = build_design_plan(
            package=content_package,
            intent=gen_intent,
            picked_asset_id=picked,
            post_id=post_id,
            rebuild=rebuild,
            concept=creative_concept,
            structured_metrics=structured_metrics or getattr(creative_concept, "structured_metrics", None),
            metric_layout=getattr(creative_concept, "metric_group_layout", None),
        )
        from investhome_api.services.social_design_engine.validator import validate_and_repair

        content_package, design_plan, creative_concept, report = validate_and_repair(
            package=content_package,
            plan=design_plan,
            concept=creative_concept,
            intent=gen_intent,
            campaign_facts=campaign_facts,
        )
        from investhome_api.services.social_design_engine.composition_blueprint import (
            composition_blueprint_from_dict,
        )
        from investhome_api.services.social_design_engine.creative_plan import creative_plan_from_dict

        plan_model = creative_plan_from_dict(getattr(creative_concept, "creative_plan", None))
        blueprint_model = composition_blueprint_from_dict(
            getattr(design_plan, "composition_blueprint", None)
        )
        design_plan, quality_score = evaluate_design_quality(
            plan=design_plan,
            concept=creative_concept,
            creative_plan=plan_model,
            blueprint=blueprint_model,
        )
        validation_payload = {
            "passed": report.passed and quality_score.passed,
            "issues": [i.code for i in report.issues] + [i.code for i in quality_score.issues],
            "repairs": list(dict.fromkeys(report.repairs + quality_score.repairs)),
            "design_quality": quality_score.to_dict(),
        }
        if report.repairs or quality_score.repairs:
            context.warnings.append("creative_director_repaired")
        if quality_score.repairs:
            context.warnings.append("design_quality_repaired")
        design_quality_payload = quality_score.to_dict()
        raw_ops = compose_ops_from_plan(
            design_plan,
            linked_project_id=linked_project_id,
            instruction=instruction,
            campaign_context_id=campaign_context_id,
            generation_context_id=generation_context_id,
        )
        summary = "Generated complete social post from project knowledge."
        if any(
            m.key == "financial_metrics" and not m.required
            for m in campaign_intel.missing_relevant_facts
        ):
            context.warnings.append("investment_without_verified_metrics")
            if campaign_intel.qa_trace is not None:
                campaign_intel.qa_trace["adapted_non_metric_investment"] = True
                campaign_intel_payload = campaign_intelligence_to_dict(campaign_intel)

    planner_posts = sibling_inventory_for_create(draft_posts) if mode == "create" else draft_posts
    system, user_prompt, prompt_version = build_design_prompt(
        instruction=instruction,
        mode=mode,
        linked_project_id=linked_project_id,
        context=context,
        draft_posts=planner_posts,
        selected_post_id=selected_post_id if mode == "edit" else None,
        media_candidates=media_candidates,
        builder_context=builder_context,
        max_prompt_chars=max_prompt_chars,
    )

    # Structural-only EDIT: deterministic intent ops — skip LLM copy invention.
    if mode == "edit" and planner_name != "copy_intelligence" and intent_plan.structural_only and intent_plan.intents:
        active = find_post(draft_posts, selected_post_id) if selected_post_id else None
        if active is None and draft_posts:
            active = draft_posts[0]
        if active is not None:
            raw_ops = build_ops_from_intent_plan(
                plan=intent_plan,
                linked_project_id=str(linked_project_id),
                post=active,
                picked_asset_id=picked,
            )
            planner_name = "intent"
            summary = f"Applied {len(intent_plan.intent_names)} structural intent(s)."

    if not raw_ops:
        try:
            llm = provider.generate(system=system, user=user_prompt, timeout_seconds=60.0)
            parsed_ops, summary = parse_ops_from_llm(llm.answer or "")
            if parsed_ops:
                raw_ops = parsed_ops
                planner_name = "llm"
        except LLMProviderError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
        except Exception:
            context.warnings.append("design_planner_fallback")
            raw_ops = []

    if not raw_ops:
        raw_ops = build_heuristic_ops(
            instruction=instruction,
            mode=mode,
            linked_project_id=linked_project_id,
            context=context,
            draft_posts=draft_posts,
            selected_post_id=selected_post_id,
            picked_asset_id=picked,
        )
        planner_name = "heuristic" if planner_name != "intent" else planner_name
        if summary == "ops_parse_failed" and "ops_parse_failed" not in context.warnings:
            context.warnings.append("ops_parse_failed")

    raw_ops = normalize_raw_ops(
        raw_ops,
        linked_project_id=linked_project_id,
        fallback_asset_id=picked,
        default_post_id=selected_post_id
        if mode == "edit"
        else (design_plan.post_id if design_plan is not None else None),
    )

    # Copy-protection + structural filter (EDIT mode)
    raw_ops, intent_rejected = filter_ops_for_copy_protection(
        raw_ops,
        intent_plan,
        mode=mode,
    )
    # Strip internal intent markers before validation
    cleaned_ops: list[dict[str, Any]] = []
    for op in raw_ops:
        if not isinstance(op, dict):
            continue
        cleaned = dict(op)
        cleaned.pop("_intent", None)
        cleaned.pop("_target", None)
        cleaned_ops.append(cleaned)
    raw_ops = cleaned_ops

    # If LLM referenced assets outside candidates, allow only after remap to picked
    for op in raw_ops:
        payload = op.get("payload") if isinstance(op, dict) else None
        if not isinstance(payload, dict):
            continue
        aid = payload.get("asset_id")
        if aid is None:
            continue
        try:
            uid = UUID(str(aid))
        except (TypeError, ValueError):
            continue
        if uid not in allowed_asset_ids and picked is not None:
            payload["asset_id"] = str(picked)
            allowed_asset_ids.add(picked)

    accepted, rejected = validate_ops(
        raw_ops,
        linked_project_id=linked_project_id,
        posts=draft_posts,
        allowed_asset_ids=allowed_asset_ids,
    )
    rejected = list(intent_rejected) + list(rejected)

    # If LLM ops all rejected, fall back to heuristic / intent once
    if not accepted:
        if mode == "edit" and intent_plan.intents:
            active = find_post(draft_posts, selected_post_id) if selected_post_id else None
            if active is None and draft_posts:
                active = draft_posts[0]
            fallback = (
                build_ops_from_intent_plan(
                    plan=intent_plan,
                    linked_project_id=str(linked_project_id),
                    post=active,
                    picked_asset_id=picked,
                )
                if active is not None
                else []
            )
            fallback, intent_rej2 = filter_ops_for_copy_protection(fallback, intent_plan, mode=mode)
            for op in fallback:
                if isinstance(op, dict):
                    op.pop("_intent", None)
                    op.pop("_target", None)
            accepted, rejected2 = validate_ops(
                fallback,
                linked_project_id=linked_project_id,
                posts=draft_posts,
                allowed_asset_ids=allowed_asset_ids,
            )
            rejected.extend(intent_rej2)
            rejected.extend(rejected2)
            planner_name = "intent"
        else:
            if design_plan is not None:
                fallback = compose_ops_from_plan(
                    design_plan,
                    linked_project_id=linked_project_id,
                    instruction=instruction,
                    campaign_context_id=campaign_context_id,
                    generation_context_id=generation_context_id,
                )
                planner_name = "generation"
            else:
                fallback = build_heuristic_ops(
                    instruction=instruction,
                    mode=mode,
                    linked_project_id=linked_project_id,
                    context=context,
                    draft_posts=draft_posts,
                    selected_post_id=selected_post_id,
                    picked_asset_id=picked,
                )
                planner_name = "heuristic"
            fallback, intent_rej2 = filter_ops_for_copy_protection(fallback, intent_plan, mode=mode)
            for op in fallback:
                if isinstance(op, dict):
                    op.pop("_intent", None)
                    op.pop("_target", None)
            accepted, rejected2 = validate_ops(
                fallback,
                linked_project_id=linked_project_id,
                posts=draft_posts,
                allowed_asset_ids=allowed_asset_ids,
            )
            rejected.extend(intent_rej2)
            rejected.extend(rejected2)
        if "design_ops_all_rejected" not in context.warnings:
            context.warnings.append("design_ops_all_rejected")

    mutated_posts, new_selected = apply_ops(
        draft_posts,
        accepted,
        linked_project_id=linked_project_id,
        selected_post_id=selected_post_id,
    )

    asset_ids_used: list[UUID] = [a.asset_id for a in selected_assets]
    if picked and picked not in asset_ids_used:
        asset_ids_used.append(picked)
    for hit in hits:
        if hit.asset_id and hit.project_id == linked_project_id and hit.asset_id not in asset_ids_used:
            asset_ids_used.append(hit.asset_id)
    # Collect from applied ops
    for op in accepted:
        aid = op.payload.get("asset_id")
        if aid:
            try:
                uid = UUID(str(aid))
            except (TypeError, ValueError):
                continue
            if uid not in asset_ids_used:
                asset_ids_used.append(uid)

    brand_status = "available" if brand_context.available else "unavailable_neutral_premium"
    latency_ms = int((time.perf_counter() - started) * 1000)
    warnings = list(dict.fromkeys(context.warnings))
    grounded = grounding.sufficient and bool(accepted)
    confidence = grounding.confidence if grounded else min(grounding.confidence, 0.2)
    citations = list(context.citations) if grounded else []

    # Human-readable summary for legacy UI fields (not design text persistence)
    generated_content = summary.strip() if summary and summary not in {
        "insufficient_context",
        "ops_parse_failed",
    } else ""
    if not generated_content and accepted:
        generated_content = f"Applied {len(accepted)} design operation(s) ({mode})."

    source_document_ids: list[UUID] = []
    for cit in citations:
        if cit.document_id not in source_document_ids:
            source_document_ids.append(cit.document_id)
    selected_ids_meta: list[UUID] = list(asset_ids_used)
    copy_meta = copy_direction_to_dict(copy_direction) if copy_direction is not None else {}
    gen_meta_payload = build_generation_metadata(
        project_id=linked_project_id,
        user_prompt=instruction,
        intent=gen_intent,
        campaign_facts=campaign_facts,
        source_document_ids=[str(i) for i in source_document_ids],
        selected_asset_ids=[str(i) for i in selected_ids_meta],
        provider=getattr(llm, "provider", provider.name) if llm else provider.name,
        model=getattr(llm, "model", provider.model) if llm else provider.model,
        content_package=content_package,
        design_plan=design_plan,
        creative_concept=creative_concept_to_dict(creative_concept) if creative_concept else None,
        creative_plan=(
            getattr(creative_concept, "creative_plan", None)
            if creative_concept
            else None
        ),
        composition_blueprint=(
            getattr(design_plan, "composition_blueprint", None) if design_plan is not None else None
        ),
        design_quality=design_quality_payload,
        validation=validation_payload,
        marketing_strategy=strategy_to_dict(marketing_strategy) if marketing_strategy is not None else None,
        copy_quality=copy_meta.get("copy_quality"),
        headline_candidates=copy_meta.get("headline_candidates") or [],
        structured_metrics=structured_metrics_to_dicts(structured_metrics),
        metric_group=metric_group_to_dict(
            MetricGroup(
                layout=getattr(creative_concept, "metric_group_layout", "horizontal")
                if creative_concept
                else "horizontal",
                metrics=structured_metrics,
            )
        )
        if structured_metrics
        else None,
        campaign_intelligence=campaign_intel_payload,
        verified_facts=verified_facts_to_dicts(campaign_intel.verified_campaign_facts),
        missing_facts=missing_facts_to_dicts(campaign_intel.missing_relevant_facts),
        campaign_context_id=campaign_context_id,
        generation_context_id=generation_context_id,
    )
    if accepted:
        target_id = str(new_selected or selected_post_id or "")
        attached = False
        for post in mutated_posts:
            if target_id and str(post.get("id") or "") != target_id:
                continue
            if mode == "create" or planner_name == "copy_intelligence" or regenerate_selected:
                attach_generation_metadata(post, meta=gen_meta_payload)
            else:
                if campaign_context_id and not (
                    post.get("campaignContextId") or post.get("campaign_context_id")
                ):
                    post["campaignContextId"] = campaign_context_id
                    post["campaign_context_id"] = campaign_context_id
                stamp = gen_meta_payload.get("generated_at")
                if isinstance(stamp, str) and stamp:
                    post["updatedAt"] = stamp
            attached = True
            break
        if not attached and mutated_posts and (
            mode == "create" or planner_name == "copy_intelligence"
        ):
            attach_generation_metadata(
                mutated_posts[-1] if mode == "create" else mutated_posts[0],
                meta=gen_meta_payload,
            )

    event_id = uuid4()
    _audit(
        db,
        user,
        entity_id=event_id,
        metadata={
            "kind": "creative_studio_social_design",
            "linked_project_id": str(linked_project_id),
            "mode": mode,
            "instruction": instruction[:500],
            "provider": getattr(llm, "provider", provider.name) if llm else provider.name,
            "model": getattr(llm, "model", provider.model) if llm else provider.model,
            "planner": planner_name,
            "prompt_version": prompt_version,
            "ops_count": len(accepted),
            "rejected_count": len(rejected),
            "latency_ms": latency_ms,
            "search_time_ms": search_time_ms,
            "hit_count": len(hits),
            "asset_ids": [str(a) for a in asset_ids_used],
            "confidence": confidence,
            "grounded": grounded,
            "brand_available": brand_context.available,
            "brand_context_status": brand_status,
            "warnings": warnings,
        },
    )

    meta = SocialDesignGenerationMeta(
        citations=citations,
        warnings=warnings,
        grounded=grounded,
        retrieval_confidence=confidence,
        asset_ids_used=asset_ids_used,
        provider=getattr(llm, "provider", provider.name) if llm else provider.name,
        model=getattr(llm, "model", provider.model) if llm else provider.model,
        brand_context=brand_context,
        brand_context_status=brand_status,
        search_time_ms=search_time_ms,
        latency_ms=latency_ms,
        mode=mode,  # type: ignore[arg-type]
        planner=planner_name,
        intents=intent_plan.intent_names,
        intent_targets=intent_plan.targets,
        applied_intents=[str(op.op) for op in accepted],
        rejected_reasons=[reason for _, reason in rejected][:40],
        copy_protected=mode == "edit" and not intent_plan.allow_copy_rewrite,
        generated_by="social_design_engine" if mode == "create" or planner_name == "copy_intelligence" else None,
        project_id=linked_project_id,
        user_prompt=instruction[:2000] if mode == "create" or planner_name == "copy_intelligence" else None,
        generation_intent=gen_meta_payload.get("generation_intent") if mode == "create" or planner_name == "copy_intelligence" else None,
        source_document_ids=source_document_ids,
        selected_asset_ids=selected_ids_meta,
        generated_at=gen_meta_payload.get("generated_at") if mode == "create" or planner_name == "copy_intelligence" else None,
        content_package=gen_meta_payload.get("content_package") if mode == "create" or planner_name == "copy_intelligence" else None,
        design_plan=gen_meta_payload.get("design_plan") if mode == "create" else None,
        campaign_facts=gen_meta_payload.get("campaign_facts") or [],
        structured_metrics=gen_meta_payload.get("structured_metrics") or [],
        metric_group=gen_meta_payload.get("metric_group"),
        creative_concept=gen_meta_payload.get("creative_concept") if mode == "create" or regenerate_selected else None,
        creative_plan=gen_meta_payload.get("creative_plan") if mode == "create" or regenerate_selected else None,
        composition_blueprint=gen_meta_payload.get("composition_blueprint")
        if mode == "create" or regenerate_selected
        else None,
        design_quality=gen_meta_payload.get("design_quality") if mode == "create" or regenerate_selected else None,
        validation=gen_meta_payload.get("validation") if mode == "create" or regenerate_selected else None,
        marketing_strategy=gen_meta_payload.get("marketing_strategy") if mode == "create" or planner_name == "copy_intelligence" else None,
        copy_quality=gen_meta_payload.get("copy_quality") if mode == "create" or planner_name == "copy_intelligence" else None,
        headline_candidates=gen_meta_payload.get("headline_candidates") or [],
        campaign_intelligence=gen_meta_payload.get("campaign_intelligence"),
        verified_facts=gen_meta_payload.get("verified_facts") or [],
        missing_facts=gen_meta_payload.get("missing_facts") or [],
        campaign_context_id=campaign_context_id,
        generation_context_id=generation_context_id,
    )

    return SocialDesignResponse(
        linked_project_id=linked_project_id,
        mode=mode,  # type: ignore[arg-type]
        ops=accepted,
        rejected_ops=[
            SocialDesignRejectedOp(op=raw, reason=reason) for raw, reason in rejected
        ],
        posts=mutated_posts,
        selected_post_id=new_selected,
        media_candidates=media_candidates,
        meta=meta,
        generated_content=generated_content,
    )
