"""AI Marketing Assistant orchestration — generate, persist, usage, audit helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.document_intelligence import AIUsage
from investhome_api.models.marketing_ai import (
    MarketingAIOutput,
    MarketingAIOutputStatus,
    MarketingAIOutputType,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_ai_assistant import (
    ASSISTANT_MODES,
    CONTENT_DRAFT_TYPES,
    LANGUAGES,
    TONES,
    AssistantArchiveRequest,
    AssistantGenerateRequest,
    AssistantGenerateResponse,
    AssistantModeInfo,
    AssistantModesResponse,
    AssistantOutputListResponse,
    AssistantSaveRequest,
)
from investhome_api.services.activity_service import ActivityRequestContext, log_activity
from investhome_api.services.marketing.assistant_context import build_assistant_context
from investhome_api.services.marketing.assistant_guardrails import (
    check_generated_content,
    check_user_instruction,
    redact_unsafe_content,
)
from investhome_api.services.marketing.assistant_prompts import MODE_META, prompt_key_for_mode
from investhome_api.services.marketing.assistant_provider import generate_assistant_output, provider_status

RATE_LIMIT_PER_HOUR = 60
DUPLICATE_WINDOW_SECONDS = 30


def _serialize(row: MarketingAIOutput, *, action_links: list | None = None) -> AssistantGenerateResponse:
    structured = row.structured_output or {}
    safety_blocked = bool(structured.get("safety_blocked"))
    freshness_raw = (row.context_snapshot or {}).get("data_freshness_at")
    freshness: datetime | None = None
    if isinstance(freshness_raw, datetime):
        freshness = freshness_raw
    elif isinstance(freshness_raw, str):
        try:
            freshness = datetime.fromisoformat(freshness_raw.replace("Z", "+00:00"))
        except ValueError:
            freshness = None
    return AssistantGenerateResponse(
        id=row.id,
        output_type=row.output_type,
        status=row.status,
        title=row.title,
        language=row.language,
        generated_content=row.generated_content,
        structured_output=row.structured_output,
        data_sources=row.data_sources or [],
        data_warnings=list(row.data_warnings or []),
        assumptions=list(row.assumptions or []),
        safety_flags=list(row.safety_flags or []),
        safety_blocked=safety_blocked,
        safety_message=structured.get("safety_message"),
        model_provider=row.model_provider,
        model_name=row.model_name,
        prompt_key=row.prompt_key,
        prompt_version=row.prompt_version,
        token_usage=row.token_usage,
        action_links=action_links or structured.get("action_links") or [],
        data_freshness_at=freshness,
        organization_id=row.organization_id,
        project_id=row.project_id,
        campaign_id=row.campaign_id,
        asset_id=row.asset_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _audit(
    db: Session,
    user: User,
    *,
    description_key: str,
    entity_id: UUID,
    action: ActivityAction = ActivityAction.CREATED,
    metadata: dict | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.MARKETING_AI,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=user,
        source=ActivitySource.API,
        metadata=metadata,
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )


def _enforce_rate_limit(db: Session, user: User) -> None:
    since = datetime.now(UTC) - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(MarketingAIOutput)
        .where(
            MarketingAIOutput.created_by_user_id == user.id,
            MarketingAIOutput.created_at >= since,
        )
    )
    if (count or 0) >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI assistant rate limit exceeded. Try again later.",
        )


def _find_duplicate(db: Session, user: User, client_request_id: str | None) -> MarketingAIOutput | None:
    if not client_request_id:
        return None
    since = datetime.now(UTC) - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    return db.scalar(
        select(MarketingAIOutput)
        .where(
            MarketingAIOutput.created_by_user_id == user.id,
            MarketingAIOutput.client_request_id == client_request_id,
            MarketingAIOutput.created_at >= since,
        )
        .order_by(MarketingAIOutput.created_at.desc())
    )


def list_modes() -> AssistantModesResponse:
    available, name = provider_status()
    return AssistantModesResponse(
        modes=[
            AssistantModeInfo(
                key=m.key,
                prompt_key=m.prompt_key,
                label_key=m.label_key,
                requires_campaign=m.requires_campaign,
                requires_source_text=m.requires_source_text,
            )
            for m in MODE_META
        ],
        content_draft_types=list(CONTENT_DRAFT_TYPES),
        tones=list(TONES),
        languages=list(LANGUAGES),
        provider_available=available,
        provider_name=name,
    )


def generate(
    db: Session,
    user: User,
    payload: AssistantGenerateRequest,
) -> AssistantGenerateResponse:
    mode = payload.mode.strip()
    if mode not in ASSISTANT_MODES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid assistant mode")
    if mode == "campaign_analysis" and not payload.campaign_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="campaign_id required")
    if mode == "translation" and not (payload.source_text or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_text required")
    if payload.language not in LANGUAGES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported language")
    if payload.tone and payload.tone not in TONES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported tone")
    if payload.content_type and payload.content_type not in CONTENT_DRAFT_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported content_type")

    duplicate = _find_duplicate(db, user, payload.client_request_id)
    if duplicate is not None:
        return _serialize(duplicate)

    _enforce_rate_limit(db, user)

    guard = check_user_instruction(payload.user_instruction, language=payload.language)
    if guard.blocked:
        # Persist a refused draft for audit transparency — no provider call.
        row = MarketingAIOutput(
            organization_id=payload.organization_id,
            created_by_user_id=user.id,
            output_type=mode,
            status=MarketingAIOutputStatus.DRAFT.value,
            project_id=payload.project_id,
            campaign_id=payload.campaign_id,
            asset_id=payload.asset_ids[0] if payload.asset_ids else None,
            language=payload.language,
            title=f"Blocked: {mode}",
            input_summary=(payload.user_instruction or "")[:500],
            generated_content=guard.message or "Request blocked by safety guardrails.",
            structured_output={
                "safety_blocked": True,
                "safety_message": guard.message,
                "flags": guard.flags,
            },
            data_sources=[],
            data_warnings=["safety_blocked"],
            assumptions=[],
            safety_flags=guard.flags,
            model_provider="guardrails",
            model_name="safety-v1",
            prompt_key=prompt_key_for_mode(mode),
            prompt_version=None,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            client_request_id=payload.client_request_id,
            context_snapshot={"blocked": True},
        )
        db.add(row)
        db.flush()
        _audit(
            db,
            user,
            description_key="marketing.ai.assistant.generated",
            entity_id=row.id,
            metadata={"mode": mode, "blocked": True, "flags": guard.flags},
        )
        return _serialize(row)

    context = build_assistant_context(
        db,
        organization_id=payload.organization_id,
        project_id=payload.project_id,
        campaign_id=payload.campaign_id,
        asset_ids=payload.asset_ids,
        audience_id=payload.audience_id,
        language=payload.language,
        user_instruction=guard.sanitized_instruction,
        tone=payload.tone,
        channel=payload.channel,
        content_type=payload.content_type,
        length=payload.length,
        call_to_action=payload.call_to_action,
        source_text=payload.source_text,
        target_language=payload.target_language,
        adaptation_style=payload.adaptation_style,
    )

    try:
        result = generate_assistant_output(
            mode,
            context,
            language=payload.language,
            source_text=payload.source_text,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc

    if not result.provider_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider unavailable",
        )

    content = result.content
    content_guard = check_generated_content(content, language=payload.language)
    safety_flags = list(content_guard.flags)
    structured = dict(result.structured)
    if content_guard.blocked:
        content = redact_unsafe_content(content, content_guard.flags, language=payload.language)
        structured["safety_blocked"] = True
        structured["safety_message"] = content_guard.message
        structured["flags"] = content_guard.flags

    structured["action_links"] = result.action_links
    data_sources = context.get("data_sources") or []
    warnings = list(context.get("data_warnings") or [])
    if content_guard.blocked:
        warnings.append("generated_content_redacted")

    # Strip large nested dumps from persisted snapshot — keep allowlisted keys only.
    snapshot_keys = (
        "organization",
        "project_summary",
        "campaign_summary",
        "performance_summary",
        "selected_assets",
        "audience_summary",
        "language",
        "user_instruction",
        "data_warnings",
        "data_freshness_at",
    )
    snapshot = {k: context.get(k) for k in snapshot_keys}

    title = None
    if mode == "campaign_brief":
        title = (structured.get("campaign_name") or "Campaign brief")[:255]
    elif mode == "content_draft":
        title = f"Draft: {payload.content_type or 'content'}"[:255]
    else:
        title = mode.replace("_", " ").title()[:255]

    row = MarketingAIOutput(
        organization_id=payload.organization_id,
        created_by_user_id=user.id,
        output_type=mode,
        status=MarketingAIOutputStatus.DRAFT.value,
        project_id=payload.project_id
        or (
            UUID(str(context["project_summary"]["id"]))
            if context.get("project_summary") and context["project_summary"].get("id")
            else None
        ),
        campaign_id=payload.campaign_id,
        asset_id=payload.asset_ids[0] if payload.asset_ids else None,
        language=payload.language,
        title=title,
        input_summary=(payload.user_instruction or mode)[:500],
        generated_content=content,
        structured_output=structured,
        data_sources=data_sources,
        data_warnings=warnings,
        assumptions=result.assumptions,
        safety_flags=safety_flags,
        model_provider=result.provider,
        model_name=result.model,
        prompt_key=result.prompt_key,
        prompt_version=result.prompt_version,
        token_usage={
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "duration_ms": result.duration_ms,
        },
        client_request_id=payload.client_request_id,
        context_snapshot=snapshot,
    )
    db.add(row)
    db.flush()

    db.add(
        AIUsage(
            document_id=None,
            analysis_id=None,
            conversation_id=None,
            provider=result.provider,
            model_name=result.model,
            operation=f"marketing_assistant:{mode}",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            duration_ms=result.duration_ms,
            retry_count=0,
            estimated_cost_usd=None,
        )
    )

    audit_key = (
        "marketing.ai.assistant.regenerated"
        if payload.regenerate_of_id
        else "marketing.ai.assistant.generated"
    )
    _audit(
        db,
        user,
        description_key=audit_key,
        entity_id=row.id,
        metadata={
            "mode": mode,
            "regenerate_of_id": str(payload.regenerate_of_id) if payload.regenerate_of_id else None,
            "prompt_key": result.prompt_key,
            "provider": result.provider,
        },
    )
    return _serialize(row, action_links=result.action_links)


def list_outputs(
    db: Session,
    user: User,
    *,
    organization_id: UUID | None = None,
    output_type: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> AssistantOutputListResponse:
    query = select(MarketingAIOutput).where(MarketingAIOutput.created_by_user_id == user.id)
    if organization_id:
        query = query.where(MarketingAIOutput.organization_id == organization_id)
    if output_type:
        query = query.where(MarketingAIOutput.output_type == output_type)
    if status_filter:
        query = query.where(MarketingAIOutput.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingAIOutput.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AssistantOutputListResponse(
        items=[_serialize(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_output(db: Session, user: User, output_id: UUID) -> AssistantGenerateResponse:
    row = db.get(MarketingAIOutput, output_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI output not found")
    if row.created_by_user_id != user.id:
        # Org peers with view_ai can read within same org when organization_id matches.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this output")
    return _serialize(row)


def save_output(
    db: Session,
    user: User,
    output_id: UUID,
    payload: AssistantSaveRequest,
) -> AssistantGenerateResponse:
    row = db.get(MarketingAIOutput, output_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI output not found")
    if row.created_by_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to save this output")
    if row.status == MarketingAIOutputStatus.ARCHIVED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived outputs cannot be saved")
    if payload.title is not None:
        row.title = payload.title
    if payload.generated_content is not None:
        row.generated_content = payload.generated_content
    if payload.structured_output is not None:
        row.structured_output = payload.structured_output
    row.status = MarketingAIOutputStatus.SAVED.value
    row.updated_at = datetime.now(UTC)
    audit_key = (
        "marketing.ai.assistant.brief_saved"
        if row.output_type == MarketingAIOutputType.CAMPAIGN_BRIEF.value
        else "marketing.ai.assistant.saved"
    )
    _audit(
        db,
        user,
        description_key=audit_key,
        entity_id=row.id,
        action=ActivityAction.UPDATED,
        metadata={"output_type": row.output_type},
    )
    return _serialize(row)


def archive_output(
    db: Session,
    user: User,
    output_id: UUID,
    payload: AssistantArchiveRequest | None = None,
) -> AssistantGenerateResponse:
    row = db.get(MarketingAIOutput, output_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI output not found")
    if row.created_by_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to archive this output")
    row.status = MarketingAIOutputStatus.ARCHIVED.value
    row.updated_at = datetime.now(UTC)
    _audit(
        db,
        user,
        description_key="marketing.ai.assistant.archived",
        entity_id=row.id,
        action=ActivityAction.UPDATED,
        metadata={"reason": payload.reason if payload else None},
    )
    return _serialize(row)
