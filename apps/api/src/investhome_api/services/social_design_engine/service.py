"""Social Media Builder AI Design Engine orchestration (Phase 1).

Flow: instruction → RAG (shared CS hybrid_search) → media candidates →
AI Design Planner (structured Design Ops) → validate → deterministic mutate →
return draft + metadata. Persistence stays on CS Document API (client).
"""

from __future__ import annotations

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
from investhome_api.services.social_design_engine.media import list_media_candidates, pick_best_asset
from investhome_api.services.social_design_engine.ops import normalize_raw_ops, validate_ops
from investhome_api.services.social_design_engine.planner import (
    build_design_prompt,
    build_heuristic_ops,
    parse_ops_from_llm,
)

DEFAULT_RETRIEVAL_LIMIT = 8


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


def _infer_mode(requested: str, posts: list[dict[str, Any]], instruction: str) -> str:
    mode = (requested or "create").strip().lower()
    if mode not in {"create", "edit"}:
        mode = "create"
    # Auto-edit when draft has posts and instruction looks like an edit
    instr = (instruction or "").lower()
    edit_hints = (
        "değiştir",
        "güncelle",
        "edit",
        "update",
        "move",
        "resize",
        "replace",
        "renk",
        "color",
        "taşı",
        "büyüt",
        "küçült",
        "ortala",
        "align",
        "arka plan",
        "background",
        "başlığı",
        "cta",
    )
    if mode == "create" and posts and any(h in instr for h in edit_hints):
        return "edit"
    if mode == "edit" and not posts:
        return "create"
    return mode


def generate_social_design(
    db: Session,
    user: User,
    body: SocialDesignRequest,
) -> SocialDesignResponse:
    started = time.perf_counter()
    settings = get_settings()

    linked_project_id = body.linked_project_id
    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="instruction is required")

    project = _ensure_project(db, linked_project_id)
    draft_posts = [dict(p) for p in (body.draft.posts or []) if isinstance(p, dict)]
    selected_post_id = body.draft.selected_post_id
    mode = _infer_mode(body.mode, draft_posts, instruction)

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
        language=body.language,
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
    )
    picked = pick_best_asset(media_candidates, require_image=True)
    if picked is None and "no_valid_project_media" not in context.warnings:
        context.warnings.append("no_valid_project_media")

    allowed_asset_ids: set[UUID] = {a.asset_id for a in selected_assets}
    allowed_asset_ids.update(c.asset_id for c in media_candidates)
    if picked:
        allowed_asset_ids.add(picked)

    try:
        provider = get_llm_provider(settings)
    except LLMProviderConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc

    max_prompt_chars = int(getattr(settings, "ai_assistant_max_prompt_chars", 14_000) or 14_000)
    system, user_prompt, prompt_version = build_design_prompt(
        instruction=instruction,
        mode=mode,
        linked_project_id=linked_project_id,
        context=context,
        draft_posts=draft_posts,
        selected_post_id=selected_post_id,
        media_candidates=media_candidates,
        builder_context=builder_context,
        max_prompt_chars=max_prompt_chars,
    )

    planner_name = "heuristic"
    raw_ops: list[dict[str, Any]] = []
    summary = ""
    llm = None

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
        planner_name = "heuristic"
        if summary == "ops_parse_failed" and "ops_parse_failed" not in context.warnings:
            context.warnings.append("ops_parse_failed")

    raw_ops = normalize_raw_ops(
        raw_ops,
        linked_project_id=linked_project_id,
        fallback_asset_id=picked,
        default_post_id=selected_post_id,
    )

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

    # If LLM ops all rejected, fall back to heuristic once
    if not accepted:
        fallback = build_heuristic_ops(
            instruction=instruction,
            mode=mode,
            linked_project_id=linked_project_id,
            context=context,
            draft_posts=draft_posts,
            selected_post_id=selected_post_id,
            picked_asset_id=picked,
        )
        accepted, rejected2 = validate_ops(
            fallback,
            linked_project_id=linked_project_id,
            posts=draft_posts,
            allowed_asset_ids=allowed_asset_ids,
        )
        rejected.extend(rejected2)
        planner_name = "heuristic"
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
