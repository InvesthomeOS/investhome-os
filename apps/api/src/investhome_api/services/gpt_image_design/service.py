"""GPT Image orchestration for Social Media Builder. Native/Ideogram stay untouched."""

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
from investhome_api.schemas.gpt_image_design import (
    GptImageDesignRequest,
    GptImageDesignResponse,
    GptImageOutput,
    GptImageProviderStatusResponse,
    GptImageSourceImage,
)
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.creative_studio_generation.assets import validate_selected_assets
from investhome_api.services.creative_studio_generation.context import (
    assert_context_has_no_forbidden_media,
    build_generation_context,
    load_brand_context,
    sanitize_builder_context,
)
from investhome_api.services.gpt_image_design.brief import (
    build_shared_brief,
    refine_prompt_with_llm,
    render_general_prompt,
    render_project_edit_prompt,
)
from investhome_api.services.gpt_image_design.client import (
    decode_remote_image,
    edit_image,
    edits_url,
    generate_image,
    generations_url,
    provider_call_count,
)
from investhome_api.services.gpt_image_design.compose import (
    build_slot_plan,
    compose_final_layers,
)
from investhome_api.services.gpt_image_design.config import (
    GPT_IMAGE_PROVIDER,
    GPT_IMAGE_PROVIDERS,
    PRESET_TO_ASPECT,
    canvas_for_preset,
    openai_api_key,
    provider_availability,
    resolve_size,
)
from investhome_api.services.gpt_image_design.persistence import (
    asset_url,
    persist_gpt_image,
    sniff_image_content_type,
)
from investhome_api.services.gpt_image_design.source import (
    INVESHOME_GLOBAL_LOGO_MISSING,
    resolve_project_inputs,
)
from investhome_api.services.social_design_engine.fact_governance import (
    strip_ineligible_financial_claims,
    text_contains_ineligible_financial,
)
from investhome_api.services.project_assistant.grounding import evaluate_grounding
from investhome_api.services.social_design_engine.campaign_intent import (
    apply_campaign_intent_to_generation_intent,
    classify_campaign_intent,
    retrieval_query_for_campaign,
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


def _log_env_check(availability: Any) -> None:
    logger.info(
        "gpt_image_env_check GPT_IMAGE_ENABLED=%s AI_API_KEY_PRESENT=%s GPT_IMAGE_MODEL=%s",
        bool(availability.enabled),
        bool(availability.configured),
        availability.model,
    )


def get_gpt_image_provider_status() -> GptImageProviderStatusResponse:
    availability = provider_availability()
    _log_env_check(availability)
    return GptImageProviderStatusResponse(
        available=availability.available,
        configured=availability.configured,
        enabled=availability.enabled,
        provider=GPT_IMAGE_PROVIDER,
        model=availability.model,
        edits_endpoint=edits_url(availability.base_url),
        generate_endpoint=generations_url(availability.base_url),
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
    if reason == "gpt_image_disabled":
        message = "GPT Image is disabled (GPT_IMAGE_ENABLED=false). Native/Ideogram generation was not used."
    elif reason == "ai_api_key_missing":
        message = "GPT Image is unavailable: AI_API_KEY is not configured. Native/Ideogram generation was not used."
    else:
        message = "GPT Image provider is unavailable. Native/Ideogram generation was not used."
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)


def _format_from_request(body: GptImageDesignRequest) -> tuple[str, str]:
    ctx = body.builder_context if isinstance(body.builder_context, dict) else {}
    preset = (
        (body.format_preset or "").strip()
        or str(ctx.get("format_preset") or ctx.get("formatPreset") or "").strip()
        or "portrait"
    )
    aspect = (body.aspect_ratio or "").strip() or PRESET_TO_ASPECT.get(preset, "4:5")
    return preset, aspect


def generate_gpt_image_creatives(
    db: Session,
    user: User,
    body: GptImageDesignRequest,
) -> GptImageDesignResponse:
    started = time.perf_counter()
    settings = get_settings()
    availability = provider_availability(settings)
    _log_env_check(availability)
    design_provider = (getattr(body, "design_provider", None) or GPT_IMAGE_PROVIDER).strip().lower()
    if design_provider not in GPT_IMAGE_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPT Image generate requires design_provider=gpt-image. Native/Ideogram generation was not invoked.",
        )
    if not availability.available:
        raise _unavailable_error(availability.reason)

    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="instruction is required")

    campaign_mode = (body.campaign_mode or "project").strip().lower()
    if campaign_mode == "general":
        return _generate_general(
            db,
            user,
            body,
            instruction=instruction,
            availability=availability,
            started=started,
        )
    return _generate_project(
        db,
        user,
        body,
        instruction=instruction,
        availability=availability,
        started=started,
    )


def _generate_project(
    db: Session,
    user: User,
    body: GptImageDesignRequest,
    *,
    instruction: str,
    availability: Any,
    started: float,
) -> GptImageDesignResponse:
    linked_project_id = body.linked_project_id
    if linked_project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPT Image project mode requires linked_project_id.",
        )
    settings = get_settings()
    project = _ensure_project(db, linked_project_id)
    format_preset, aspect_ratio = _format_from_request(body)
    size = resolve_size(
        model=availability.model,
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,
    )
    canvas_w, canvas_h = canvas_for_preset(format_preset)
    format_label = f"Instagram {aspect_ratio}" if aspect_ratio == "4:5" else f"Social {aspect_ratio}"

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
    retrieval_query = retrieval_query_for_campaign(
        instruction,
        campaign_intent=campaign_intent.campaign_intent,
        city=project.city,
        country=getattr(project, "country", None),
        project_name=project.project_name,
    )
    try:
        hits = hybrid_search(
            db,
            query=retrieval_query,
            project_scope="single",
            project_id=linked_project_id,
            project_ids=None,
            limit=retrieval_limit,
            builder="social",
        )
        if not hits:
            hits = hybrid_search(
                db,
                query=retrieval_query,
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

    source, extras, design_refs, logo_notes, composition_warnings = resolve_project_inputs(
        db,
        linked_project_id=linked_project_id,
        instruction=instruction,
        selected_asset_ids=list(body.selected_asset_ids or []),
        project_name=project.project_name,
        project_code=getattr(project, "project_code", None),
    )
    logger.info(
        "gpt_image_project_source mode=edits project_id=%s asset_id=%s extra_images=%s "
        "filename=%s content_type=%s dimensions=%sx%s byte_size=%s composition_warnings=%s",
        linked_project_id,
        source.asset_id,
        [row.role for row in extras],
        source.filename,
        source.content_type,
        source.width,
        source.height,
        len(source.image_bytes),
        composition_warnings,
    )

    project_knowledge = build_project_knowledge_package(
        project=project,
        context=context,
        media_candidates=[],
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
        asset=None,
        strategy=marketing_strategy,
        copy_package=copy_direction.package,
        campaign_intelligence=campaign_intel,
        campaign_intent_result=campaign_intent,
        sibling_posts=draft_posts,
    )

    extra_roles = [row.role for row in extras]
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
        format_label=format_label,
        resolution=size,
        extra_image_roles=extra_roles,
        logo_notes=logo_notes,
        design_reference_names=[row.filename for row in design_refs],
    )
    logger.info(
        "gpt_image_brief project_id=%s user_campaign_facts=%s allowed_financial_tokens=%s "
        "blocked_financial_tokens=%s extra_image_roles=%s",
        linked_project_id,
        shared_brief.get("user_campaign_facts"),
        shared_brief.get("allowed_financial_tokens"),
        shared_brief.get("blocked_financial_tokens"),
        extra_roles,
    )
    prompt = render_project_edit_prompt(shared_brief)
    prompt = refine_prompt_with_llm(
        prompt,
        allowed=list(shared_brief.get("allowed_financial_tokens") or []),
        blocked=list(shared_brief.get("blocked_financial_tokens") or []),
    )
    session_id = (body.session_id or "").strip() or str(uuid4())
    endpoint = edits_url(availability.base_url)
    logger.info(
        "gpt_image_provider_plan provider=%s endpoint=%s model=%s mode=edits size=%s extra_images=%s",
        GPT_IMAGE_PROVIDER,
        endpoint,
        availability.model,
        size,
        extra_roles,
    )
    api_key = openai_api_key(settings)
    calls_before = provider_call_count()
    # GPT Image edits: architecture/composition photo only. Logos + text via OS Final Composition.
    edit_inputs = [
        (source.image_bytes, source.filename, source.content_type),
    ]
    remote = edit_image(
        api_key=api_key,
        model=availability.model,
        prompt=prompt,
        images=edit_inputs,
        size=size,
        quality=availability.quality,
        base_url=availability.base_url,
        variant="project",
    )
    base_image_bytes = decode_remote_image(remote)
    base_content_type = sniff_image_content_type(base_image_bytes)
    generation_id = str(uuid4())

    # Persist GPT visual base (editable cover) before OS composition.
    base_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=linked_project_id,
        content=base_image_bytes,
        content_type=base_content_type,
        campaign_mode="project-base",
        session_id=session_id,
        provider_generation_id=generation_id,
        campaign_context_id=campaign_context_id,
        brief_excerpt="gpt-image-base",
    )

    allowed_tokens = list(shared_brief.get("allowed_financial_tokens") or [])
    blocked_tokens = list(shared_brief.get("blocked_financial_tokens") or [])
    visible = dict(shared_brief.get("visible_copy") or {})
    for key in ("eyebrow", "headline", "supporting", "cta"):
        raw = str(visible.get(key) or "")
        cleaned = strip_ineligible_financial_claims(
            raw,
            allowed_tokens=allowed_tokens,
            blocked_tokens=blocked_tokens,
        )
        if text_contains_ineligible_financial(
            cleaned,
            allowed_tokens=allowed_tokens,
            blocked_tokens=blocked_tokens,
        ):
            cleaned = ""
        visible[key] = cleaned

    verified_lines: list[str] = []
    for row in shared_brief.get("user_campaign_facts") or []:
        label = str(row.get("label") or "").strip()
        value = str(row.get("value") or "").strip()
        if not value:
            continue
        line = f"{label}: {value}" if label else value
        line = strip_ineligible_financial_claims(
            line,
            allowed_tokens=allowed_tokens,
            blocked_tokens=blocked_tokens,
        )
        if line and not text_contains_ineligible_financial(
            line,
            allowed_tokens=allowed_tokens,
            blocked_tokens=blocked_tokens,
        ):
            verified_lines.append(line)
    for row in shared_brief.get("marketing_safe_facts") or []:
        if str(row.get("financial") or "").lower() == "yes":
            # Only surface financial verified data when Claim Guard already allowed the token.
            value = str(row.get("value") or "").strip()
            if not value or value not in allowed_tokens:
                continue
        label = str(row.get("label") or "").strip()
        value = str(row.get("value") or "").strip()
        if not value:
            continue
        line = f"{label}: {value}" if label else value
        line = strip_ineligible_financial_claims(
            line,
            allowed_tokens=allowed_tokens,
            blocked_tokens=blocked_tokens,
        )
        if line and not text_contains_ineligible_financial(
            line,
            allowed_tokens=allowed_tokens,
            blocked_tokens=blocked_tokens,
        ):
            verified_lines.append(line)
            break  # optional single verified line — don't force every slot

    slots = build_slot_plan(
        visible_copy=visible,
        verified_lines=verified_lines[:1],
        include_slogan=True,
    )
    composition = compose_final_layers(
        base_image_bytes,
        logos=extras,
        slots=slots,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        base_asset_id=base_asset.id,
    )
    for warn in composition.warnings:
        if warn not in composition_warnings:
            composition_warnings.append(warn)
    image_bytes = composition.png_bytes
    content_type = sniff_image_content_type(image_bytes)
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=linked_project_id,
        content=image_bytes,
        content_type=content_type,
        campaign_mode="project",
        session_id=session_id,
        provider_generation_id=generation_id,
        campaign_context_id=campaign_context_id,
        brief_excerpt=str(shared_brief.get("objective") or ""),
    )
    # Prefer original SVG/raster asset IDs on logo layers (not the rasterized compose buffer).
    composed_layers = list(composition.layers)
    outputs = [
        GptImageOutput(
            local_asset_id=asset.id,
            local_asset_url=asset_url(asset.id),
            provider=GPT_IMAGE_PROVIDER,
            provider_generation_id=generation_id,
            resolution=size,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            layers=composed_layers,
            composition_base_asset_id=base_asset.id,
            composition_warnings=list(composition_warnings),
            metadata={
                "provider": GPT_IMAGE_PROVIDER,
                "provider_generation_id": generation_id,
                "local_asset_id": str(asset.id),
                "local_asset_path": asset.storage_key,
                "composition_base_asset_id": str(base_asset.id),
                "project_id": str(linked_project_id),
                "campaign_context_id": campaign_context_id,
                "campaign_mode": "project",
                "created_at": asset.created_at.isoformat() if asset.created_at else None,
                "source_asset_id": str(source.asset_id),
                "source_filename": source.filename,
                "extra_image_roles": extra_roles,
                "extra_image_asset_ids": [str(row.asset_id) for row in extras],
                "composition_used_slots": list(composition.used_slots),
                "investhome_global_logo_found": not any(
                    INVESHOME_GLOBAL_LOGO_MISSING in w for w in composition_warnings
                ),
                "brief": {
                    "objective": shared_brief.get("objective"),
                    "headline": visible.get("headline"),
                },
            },
        )
    ]
    latency_ms = int((time.perf_counter() - started) * 1000)
    call_count = provider_call_count() - calls_before
    logger.info(
        "gpt_image_session_complete",
        extra={
            "provider": GPT_IMAGE_PROVIDER,
            "endpoint": endpoint,
            "model": availability.model,
            "session_id": session_id,
            "project_id": str(linked_project_id),
            "campaign_mode": "project",
            "provider_call_count": call_count,
            "latency_ms": latency_ms,
            "source_asset_id": str(source.asset_id),
            "http_status": 200,
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
        "prompt": prompt,
    }
    extra_payload = [
        GptImageSourceImage(
            asset_id=row.asset_id,
            filename=row.filename,
            content_type=row.content_type,
            folder_category=row.folder_category,
            tags=list(row.tags or []),
            role=row.role,
        )
        for row in extras
    ]
    return GptImageDesignResponse(
        provider=GPT_IMAGE_PROVIDER,
        model=availability.model,
        endpoint=endpoint,
        campaign_mode="project",
        session_id=session_id,
        linked_project_id=linked_project_id,
        campaign_context_id=campaign_context_id,
        generation_context_id=generation_context_id,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        source_image=GptImageSourceImage(
            asset_id=source.asset_id,
            filename=source.filename,
            content_type=source.content_type,
            folder_category=source.folder_category,
            tags=list(source.tags or []),
            role="source",
        ),
        extra_images=extra_payload,
        brief=brief_payload,
        outputs=outputs,
        warnings=[*list(context.warnings), *composition_warnings],
        provider_call_count=call_count,
        latency_ms=latency_ms,
    )


def _generate_general(
    db: Session,
    user: User,
    body: GptImageDesignRequest,
    *,
    instruction: str,
    availability: Any,
    started: float,
) -> GptImageDesignResponse:
    """Text-to-image infrastructure. SMB live test must not call this path."""
    format_preset, aspect_ratio = _format_from_request(body)
    size = resolve_size(
        model=availability.model,
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,
    )
    canvas_w, canvas_h = canvas_for_preset(format_preset)
    prompt = render_general_prompt(instruction=instruction, language=body.language)
    prompt = refine_prompt_with_llm(prompt, allowed=[], blocked=[])
    session_id = (body.session_id or "").strip() or str(uuid4())
    endpoint = generations_url(availability.base_url)
    settings = get_settings()
    api_key = openai_api_key(settings)
    calls_before = provider_call_count()
    remote = generate_image(
        api_key=api_key,
        model=availability.model,
        prompt=prompt,
        size=size,
        quality=availability.quality,
        base_url=availability.base_url,
        variant="general",
    )
    image_bytes = decode_remote_image(remote)
    content_type = sniff_image_content_type(image_bytes)
    generation_id = str(uuid4())
    generation_context_id = str(uuid4())
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=body.linked_project_id,
        content=image_bytes,
        content_type=content_type,
        campaign_mode="general",
        session_id=session_id,
        provider_generation_id=generation_id,
        campaign_context_id=None,
        brief_excerpt="investhome-general",
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    call_count = provider_call_count() - calls_before
    return GptImageDesignResponse(
        provider=GPT_IMAGE_PROVIDER,
        model=availability.model,
        endpoint=endpoint,
        campaign_mode="general",
        session_id=session_id,
        linked_project_id=body.linked_project_id,
        campaign_context_id=None,
        generation_context_id=generation_context_id,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        source_image=None,
        extra_images=[],
        brief={"prompt": prompt, "campaign_mode": "general"},
        outputs=[
            GptImageOutput(
                local_asset_id=asset.id,
                local_asset_url=asset_url(asset.id),
                provider=GPT_IMAGE_PROVIDER,
                provider_generation_id=generation_id,
                resolution=size,
                canvas_width=canvas_w,
                canvas_height=canvas_h,
                metadata={
                    "provider": GPT_IMAGE_PROVIDER,
                    "campaign_mode": "general",
                    "local_asset_id": str(asset.id),
                },
            )
        ],
        warnings=[],
        provider_call_count=call_count,
        latency_ms=latency_ms,
    )
