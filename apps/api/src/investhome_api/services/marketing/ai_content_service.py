"""AI content generation contracts — unavailable when no provider configured."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.marketing_content_studio import AIContentGenerationRecord, AIGenerationStatus
from investhome_api.models.user_auth import User


def ai_provider_available() -> bool:
    settings = get_settings()
    return bool(getattr(settings, "marketing_ai_provider", None))


def request_ai_generation(
    db: Session,
    *,
    content_id: UUID | None,
    version_id: UUID | None,
    prompt: str,
    context_json: dict | None,
    actor: User,
) -> AIContentGenerationRecord:
    if not ai_provider_available():
        record = AIContentGenerationRecord(
            content_id=content_id,
            version_id=version_id,
            prompt=prompt,
            context_json=context_json,
            provider=None,
            status=AIGenerationStatus.UNAVAILABLE,
            requested_by_user_id=actor.id,
            metadata_json={"message": "AI provider not configured"},
        )
        db.add(record)
        return record
    record = AIContentGenerationRecord(
        content_id=content_id,
        version_id=version_id,
        prompt=prompt,
        context_json=context_json,
        provider=get_settings().marketing_ai_provider,
        status=AIGenerationStatus.PENDING_REVIEW,
        output_json=None,
        requested_by_user_id=actor.id,
        metadata_json={"requires_review": True},
    )
    db.add(record)
    return record


def review_ai_generation(
    db: Session, record: AIContentGenerationRecord, *, approved: bool, actor: User
) -> AIContentGenerationRecord:
    if record.status == AIGenerationStatus.UNAVAILABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI generation unavailable — no provider")
    if record.status not in {AIGenerationStatus.PENDING_REVIEW, AIGenerationStatus.PENDING}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Record is not pending review")
    from datetime import UTC, datetime

    record.status = AIGenerationStatus.APPROVED if approved else AIGenerationStatus.REJECTED
    record.reviewed_by_user_id = actor.id
    record.reviewed_at = datetime.now(UTC)
    return record
