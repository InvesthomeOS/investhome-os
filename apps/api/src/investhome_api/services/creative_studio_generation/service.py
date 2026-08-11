"""Creative Studio shared generation orchestration.

Flow: linked_project_id → validate assets → hybrid search (project-scoped) →
structured context → LLMProvider → citations + confidence + warnings.
"""

from __future__ import annotations

import time
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_studio_generation import (
    CREATIVE_STUDIO_BUILDER_TYPES,
    CreativeStudioGenerateRequest,
    CreativeStudioGenerateResponse,
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
from investhome_api.services.creative_studio_generation.prompt_builder import build_creative_prompt
from investhome_api.services.project_assistant.grounding import evaluate_grounding
from investhome_api.services.project_assistant.llm_provider import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    LLMProviderConfigError,
    LLMProviderError,
    get_llm_provider,
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


def _normalize_builder_type(raw: str) -> str:
    value = (raw or "").strip().lower()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="builder_type is required",
        )
    if value not in CREATIVE_STUDIO_BUILDER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"invalid builder_type: {raw}. "
                f"Expected one of: {', '.join(sorted(CREATIVE_STUDIO_BUILDER_TYPES))}"
            ),
        )
    return value


def _audit(db: Session, user: User, *, entity_id: UUID, metadata: dict) -> None:
    safe = {
        k: v
        for k, v in metadata.items()
        if k
        not in {
            "api_key",
            "authorization",
            "prompt",
            "system",
            "user_prompt",
            "raw",
        }
    }
    log_activity(
        db,
        action=ActivityAction.VIEWED,
        entity_type=ActivityEntityType.PROJECT_AI,
        entity_id=entity_id,
        description_key="ai.creative_studio.generate",
        actor_user=user,
        source=ActivitySource.AI_SERVICE,
        metadata=safe,
        request_context=ActivityRequestContext(source=ActivitySource.AI_SERVICE),
    )


def generate_creative_content(
    db: Session,
    user: User,
    body: CreativeStudioGenerateRequest,
) -> CreativeStudioGenerateResponse:
    """
    Shared Creative Studio generation entrypoint.

    Mandatory linked_project_id. Retrieves only that project's indexed knowledge
    via hybrid_search. Validates selected assets are project-scoped.
    """
    started = time.perf_counter()
    settings = get_settings()

    linked_project_id = body.linked_project_id
    if linked_project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="linked_project_id is required",
        )

    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instruction is required",
        )

    builder_type = _normalize_builder_type(body.builder_type)
    project = _ensure_project(db, linked_project_id)
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
            builder=builder_type,
        )
        # If builder filter yields nothing, fall back to project-wide retrieval
        # (still strictly scoped to linked_project_id).
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    search_time_ms = int((time.perf_counter() - search_started) * 1000)

    # Isolation: every hit must belong to linked_project_id
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
        builder_type=builder_type,
        language=body.language,
        hits=hits if grounding.sufficient else [],
        selected_assets=selected_assets,
        brand_context=brand_context,
        extra_warnings=sanitize_warnings,
    )
    if not grounding.sufficient:
        if "insufficient_retrieved_content" not in context.warnings:
            context.warnings.append("insufficient_context")
        else:
            # Rename for API clarity when score floor fails with empty usable hits
            pass
        if grounding.top_score > 0 and "insufficient_context" not in context.warnings:
            context.warnings.append("insufficient_context")

    assert_context_has_no_forbidden_media(context)

    try:
        provider = get_llm_provider(settings)
    except LLMProviderConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    event_id = uuid4()
    asset_ids_used = [a.asset_id for a in selected_assets]
    # Also record retrieved asset ids that belong to this project
    for hit in hits:
        if hit.asset_id and hit.project_id == linked_project_id and hit.asset_id not in asset_ids_used:
            asset_ids_used.append(hit.asset_id)

    if not grounding.sufficient:
        content = grounding.message or INSUFFICIENT_EVIDENCE_MESSAGE
        latency_ms = int((time.perf_counter() - started) * 1000)
        warnings = list(dict.fromkeys(context.warnings + ["insufficient_context"]))
        _audit(
            db,
            user,
            entity_id=event_id,
            metadata={
                "kind": "creative_studio_generate",
                "linked_project_id": str(linked_project_id),
                "builder_type": builder_type,
                "instruction": instruction[:500],
                "provider": provider.name,
                "model": provider.model,
                "latency_ms": latency_ms,
                "search_time_ms": search_time_ms,
                "hit_count": len(hits),
                "asset_ids": [str(a) for a in asset_ids_used],
                "confidence": grounding.confidence,
                "grounded": False,
                "brand_available": brand_context.available,
                "warnings": warnings,
            },
        )
        return CreativeStudioGenerateResponse(
            generated_content=content,
            project_id=linked_project_id,
            builder_type=builder_type,
            asset_ids_used=asset_ids_used,
            citations=[],
            retrieval_confidence=grounding.confidence,
            warnings=warnings,
            brand_context=brand_context,
            grounded=False,
            provider=provider.name,
            model=provider.model,
            search_time_ms=search_time_ms,
            latency_ms=latency_ms,
            context=context,
        )

    max_prompt_chars = int(getattr(settings, "ai_assistant_max_prompt_chars", 14_000) or 14_000)
    prompt = build_creative_prompt(
        instruction=instruction,
        context=context,
        builder_context=builder_context,
        max_prompt_chars=max_prompt_chars,
    )

    try:
        llm = provider.generate(system=prompt.system, user=prompt.user)
        content = (llm.answer or "").strip() or INSUFFICIENT_EVIDENCE_MESSAGE
        grounded = True
        confidence = grounding.confidence
        citations = list(context.citations)
        if content.strip() == INSUFFICIENT_EVIDENCE_MESSAGE or prompt.chunk_count == 0:
            grounded = False
            confidence = min(confidence, 0.2)
            citations = []
            if "insufficient_context" not in context.warnings:
                context.warnings.append("insufficient_context")
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    except Exception:
        content = INSUFFICIENT_EVIDENCE_MESSAGE
        grounded = False
        confidence = 0.0
        citations = []
        llm = None
        if "insufficient_context" not in context.warnings:
            context.warnings.append("insufficient_context")

    latency_ms = int((time.perf_counter() - started) * 1000)
    warnings = list(dict.fromkeys(context.warnings))

    _audit(
        db,
        user,
        entity_id=event_id,
        metadata={
            "kind": "creative_studio_generate",
            "linked_project_id": str(linked_project_id),
            "builder_type": builder_type,
            "instruction": instruction[:500],
            "provider": getattr(llm, "provider", provider.name) if llm else provider.name,
            "model": getattr(llm, "model", provider.model) if llm else provider.model,
            "latency_ms": latency_ms,
            "search_time_ms": search_time_ms,
            "hit_count": len(hits),
            "asset_ids": [str(a) for a in asset_ids_used],
            "chunk_ids": [str(c.chunk_id) for c in citations],
            "confidence": confidence,
            "grounded": grounded,
            "brand_available": brand_context.available,
            "prompt_version": prompt.prompt_version,
            "prompt_truncated": prompt.truncated,
            "warnings": warnings,
        },
    )

    return CreativeStudioGenerateResponse(
        generated_content=content,
        project_id=linked_project_id,
        builder_type=builder_type,
        asset_ids_used=asset_ids_used,
        citations=citations,
        retrieval_confidence=confidence,
        warnings=warnings,
        brand_context=brand_context,
        grounded=grounded,
        provider=getattr(llm, "provider", provider.name) if llm else provider.name,
        model=getattr(llm, "model", provider.model) if llm else provider.model,
        search_time_ms=search_time_ms,
        latency_ms=latency_ms,
        context=context,
    )
