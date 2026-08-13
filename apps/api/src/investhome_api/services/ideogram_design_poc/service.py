"""Ideogram POC orchestration: intelligence → remix → persist. Native SMB stays untouched."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.ideogram_design_poc import (
    IdeogramDesignRequest,
    IdeogramDesignResponse,
    IdeogramOutput,
    IdeogramProviderStatusResponse,
    IdeogramSourceImage,
)
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.creative_studio_generation.assets import validate_selected_assets
from investhome_api.services.creative_studio_generation.context import (
    assert_context_has_no_forbidden_media,
    build_generation_context,
    load_brand_context,
    sanitize_builder_context,
)
from investhome_api.services.ideogram_design_poc.brief import (
    build_shared_brief,
    render_variant_prompt,
    variant_specs,
)
from investhome_api.services.ideogram_design_poc.client import (
    download_remote_image,
    generate_creative,
    provider_call_count,
)
from investhome_api.services.ideogram_design_poc.config import (
    DEFAULT_IMAGE_WEIGHT,
    IDEOGRAM_GENERATE_ENDPOINT,
    IDEOGRAM_PROVIDER,
    IDEOGRAM_REMIX_ENDPOINT,
    POC_VARIANT_COUNT,
    provider_availability,
)
from investhome_api.services.ideogram_design_poc.persistence import (
    asset_url,
    persist_ideogram_image,
    sniff_image_content_type,
)
from investhome_api.services.ideogram_design_poc.source_image import (
    pick_source_asset,
    resolve_source_bytes,
)
from investhome_api.services.project_assistant.grounding import evaluate_grounding
from investhome_api.services.social_design_engine.campaign_intent import (
    apply_campaign_intent_to_generation_intent,
    classify_campaign_intent,
)
from investhome_api.services.social_design_engine.copy_director import (
    build_copy_package,
    copy_direction_to_dict,
)
from investhome_api.services.social_design_engine.creative_director import (
    creative_concept_to_dict,
    direct_creative,
)
from investhome_api.services.social_design_engine.generation import (
    campaign_facts_for_mode,
    classify_generation_intent,
    resolve_campaign_context_id,
)
from investhome_api.services.social_design_engine.marketing_strategist import (
    build_marketing_strategy,
    strategy_to_dict,
)
from investhome_api.services.social_design_engine.project_knowledge import (
    build_project_knowledge_package,
)
from investhome_api.services.social_design_engine.verified_facts import (
    build_campaign_intelligence,
    campaign_intelligence_to_dict,
    missing_facts_to_dicts,
)

logger = logging.getLogger(__name__)
DEFAULT_RETRIEVAL_LIMIT = 8


def get_ideogram_provider_status() -> IdeogramProviderStatusResponse:
    availability = provider_availability()
    return IdeogramProviderStatusResponse(
        available=availability.available,
        configured=availability.configured,
        enabled=availability.enabled,
        provider=IDEOGRAM_PROVIDER,
        model=availability.model,
        remix_endpoint=IDEOGRAM_REMIX_ENDPOINT,
        generate_endpoint=IDEOGRAM_GENERATE_ENDPOINT,
        reason=availability.reason,
    )


def _ensure_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found or inaccessible: {project_id}",
        )
    return project


def _unavailable_error(reason: str | None) -> HTTPException:
    if reason == "ideogram_disabled":
        message = "Ideogram POC is disabled (IDEOGRAM_ENABLED=false)."
    elif reason == "ideogram_api_key_missing":
        message = "Ideogram POC is unavailable: IDEOGRAM_API_KEY is not configured."
    else:
        message = "Ideogram provider is unavailable."
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)


def generate_ideogram_creatives(
    db: Session,
    user: User,
    body: IdeogramDesignRequest,
) -> IdeogramDesignResponse:
    started = time.perf_counter()
    settings = get_settings()
    availability = provider_availability(settings)
    if not availability.available:
        raise _unavailable_error(availability.reason)

    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instruction is required",
        )
    if body.aspect_ratio != "1:1":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ideogram POC supports Instagram Square 1:1 only.",
        )

    linked_project_id = body.linked_project_id
    project = _ensure_project(db, linked_project_id)
    draft_posts = [dict(p) for p in (body.draft.posts or []) if isinstance(p, dict)]
    selected_post_id = body.draft.selected_post_id
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
    campaign_context_id = resolve_campaign_context_id(
        mode="create",
        draft_posts=draft_posts,
        selected_post_id=selected_post_id,
    )
    generation_context_id = str(uuid4())
    campaign_facts = campaign_facts_for_mode(
        mode="create",
        instruction=instruction,
        selected_post=None,
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
    assert_context_has_no_forbidden_media(context)

    source_candidate = pick_source_asset(
        db,
        linked_project_id=linked_project_id,
        instruction=instruction,
        selected_asset_ids=list(body.selected_asset_ids or []),
    )
    source = resolve_source_bytes(
        db,
        linked_project_id=linked_project_id,
        candidate=source_candidate,
    )

    project_knowledge = build_project_knowledge_package(
        project=project,
        context=context,
        media_candidates=[source_candidate],
    )
    selected_asset_meta = {
        "asset_id": str(source.asset_id),
        "filename": source.filename,
        "folder_category": source.folder_category,
        "tags": list(source.tags or []),
    }
    campaign_intel = build_campaign_intelligence(
        intent=campaign_intent,
        knowledge=project_knowledge,
        campaign_facts=campaign_facts,
        selected_asset=selected_asset_meta,
        campaign_context_id=campaign_context_id,
    )
    if not campaign_intel.can_proceed:
        missing = ", ".join(
            f.key for f in campaign_intel.missing_relevant_facts if f.required
        ) or "required fact"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                campaign_intel.block_reason
                or f"Missing required campaign facts ({missing}). Provide the value(s) to continue."
            ),
        )

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
    creative = direct_creative(
        instruction=instruction,
        intent=gen_intent,
        context=context,
        campaign_facts=campaign_facts,
        asset=source_candidate,
        strategy=marketing_strategy,
        copy_package=copy_direction.package,
        campaign_intelligence=campaign_intel,
        campaign_intent_result=campaign_intent,
        sibling_posts=draft_posts,
    )

    shared_brief = build_shared_brief(
        project_name=project.project_name,
        instruction=instruction,
        intent=gen_intent,
        strategy=marketing_strategy,
        copy_direction=copy_direction,
        creative=creative,
        campaign_facts=campaign_facts,
        intel=campaign_intel,
        source_filename=source.filename,
        language=effective_language,
    )
    session_id = (body.session_id or "").strip() or str(uuid4())
    specs = list(variant_specs())
    if body.regenerate_variant:
        specs = [row for row in specs if row[0] == body.regenerate_variant]
        if not specs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown Ideogram variant.",
            )
    else:
        specs = specs[: max(1, min(body.count, POC_VARIANT_COUNT))]

    api_key = (settings.ideogram_api_key or "").strip()
    calls_before = provider_call_count()
    outputs: list[IdeogramOutput] = []
    warnings = list(context.warnings)
    source_tuple = (source.image_bytes, source.filename, source.content_type)

    for variant, art_name, art_brief in specs:
        prompt = render_variant_prompt(
            shared_brief,
            variant=variant,
            art_direction_name=art_name,
            art_direction_brief=art_brief,
        )
        remote = generate_creative(
            api_key=api_key,
            prompt=prompt,
            source_image=source_tuple,
            rendering_speed=availability.quality,
            image_weight=DEFAULT_IMAGE_WEIGHT,
            variant=variant,
        )
        image_bytes = download_remote_image(remote.url or "")
        content_type = sniff_image_content_type(image_bytes)
        generation_id = str(remote.seed) if remote.seed is not None else str(uuid4())
        asset = persist_ideogram_image(
            db,
            actor=user,
            linked_project_id=linked_project_id,
            content=image_bytes,
            content_type=content_type,
            variant=variant,
            session_id=session_id,
            provider_generation_id=generation_id,
            original_remote_url=remote.url or "",
            campaign_context_id=campaign_context_id,
            art_direction=art_name,
            brief_excerpt=str(shared_brief.get("objective") or ""),
        )
        outputs.append(
            IdeogramOutput(
                variant=variant,  # type: ignore[arg-type]
                art_direction=art_name,
                remote_url=None,
                local_asset_id=asset.id,
                local_asset_url=asset_url(asset.id),
                provider=IDEOGRAM_PROVIDER,
                provider_generation_id=generation_id,
                original_remote_url=remote.url,
                seed=remote.seed,
                resolution=remote.resolution,
                metadata={
                    "provider": IDEOGRAM_PROVIDER,
                    "provider_generation_id": generation_id,
                    "original_remote_url": remote.url,
                    "local_asset_id": str(asset.id),
                    "local_asset_path": asset.storage_key,
                    "project_id": str(linked_project_id),
                    "campaign_context_id": campaign_context_id,
                    "variant": variant,
                    "art_direction": art_name,
                    "created_at": asset.created_at.isoformat() if asset.created_at else None,
                    "source_asset_id": str(source.asset_id),
                    "source_filename": source.filename,
                    "brief": {
                        "objective": shared_brief.get("objective"),
                        "headline": (shared_brief.get("visible_copy") or {}).get("headline"),
                    },
                },
            )
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    call_count = provider_call_count() - calls_before
    logger.info(
        "ideogram_poc_session_complete",
        extra={
            "session_id": session_id,
            "project_id": str(linked_project_id),
            "variant_count": len(outputs),
            "provider_call_count": call_count,
            "latency_ms": latency_ms,
            "source_asset_id": str(source.asset_id),
        },
    )
    brief_payload: dict[str, Any] = {
        **shared_brief,
        "marketing_strategy": strategy_to_dict(marketing_strategy),
        "copy": copy_direction_to_dict(copy_direction),
        "creative_concept": creative_concept_to_dict(creative),
        "campaign_intelligence": campaign_intelligence_to_dict(campaign_intel),
        "missing_facts": missing_facts_to_dicts(campaign_intel.missing_relevant_facts),
        "builder_context_present": bool(builder_context),
    }
    return IdeogramDesignResponse(
        provider=IDEOGRAM_PROVIDER,
        model=availability.model,
        endpoint=IDEOGRAM_REMIX_ENDPOINT,
        session_id=session_id,
        linked_project_id=linked_project_id,
        campaign_context_id=campaign_context_id,
        generation_context_id=generation_context_id,
        aspect_ratio="1:1",
        source_image=IdeogramSourceImage(
            asset_id=source.asset_id,
            filename=source.filename,
            content_type=source.content_type,
            folder_category=source.folder_category,
            tags=list(source.tags or []),
        ),
        brief=brief_payload,
        outputs=outputs,
        warnings=warnings,
        provider_call_count=call_count,
        latency_ms=latency_ms,
    )
