"""Resolve a real project hero image for Ideogram remix. No Unsplash / fakes."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_studio_media_service import (
    get_asset_or_404,
    open_asset_content,
)
from investhome_api.services.social_design_engine.generation import asset_preference_tokens
from investhome_api.services.social_design_engine.media import (
    list_media_candidates,
    pick_best_asset,
)

AERIAL_EXTERIOR_TOKENS = (
    asset_preference_tokens("premium_hero")
    | asset_preference_tokens("aerial")
    | asset_preference_tokens("exterior")
)


@dataclass(frozen=True)
class ResolvedSourceImage:
    asset_id: UUID
    filename: str
    content_type: str
    folder_category: str | None
    tags: list[str]
    image_bytes: bytes


def _candidate_for(
    candidates: list[SocialDesignMediaCandidate],
    asset_id: UUID,
) -> SocialDesignMediaCandidate | None:
    return next((c for c in candidates if c.asset_id == asset_id), None)


def pick_source_asset(
    db: Session,
    *,
    linked_project_id: UUID,
    instruction: str,
    selected_asset_ids: list[UUID] | None = None,
) -> SocialDesignMediaCandidate:
    selected = [aid for aid in (selected_asset_ids or []) if aid]
    candidates = list_media_candidates(
        db,
        linked_project_id=linked_project_id,
        instruction=instruction,
        limit=24,
        preference_tokens=AERIAL_EXTERIOR_TOKENS,
    )
    picked: UUID | None = None
    if selected:
        allowed = {c.asset_id for c in candidates}
        for aid in selected:
            if aid in allowed:
                picked = aid
                break
        if picked is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected source image is not a valid project media asset.",
            )
    if picked is None:
        picked = pick_best_asset(candidates, require_image=True)
    if picked is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No real project image is available for Ideogram remix.",
        )
    candidate = _candidate_for(candidates, picked)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No real project image is available for Ideogram remix.",
        )
    ctype = (candidate.content_type or "").lower()
    if not ctype.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ideogram remix requires a real project image, not a document.",
        )
    return candidate


def resolve_source_bytes(
    db: Session,
    *,
    linked_project_id: UUID,
    candidate: SocialDesignMediaCandidate,
) -> ResolvedSourceImage:
    asset: CreativeStudioMediaAsset = get_asset_or_404(candidate.asset_id, db)
    if asset.linked_project_id != linked_project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found",
        )
    stream, media_type = open_asset_content(asset, linked_project_id=linked_project_id)
    try:
        payload = stream.read()
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project source image could not be read for Ideogram remix.",
        )
    filename = candidate.filename or asset.filename or "project.jpg"
    content_type = media_type or candidate.content_type or asset.content_type or "image/jpeg"
    lower = filename.lower()
    if not lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
        if "png" in content_type:
            filename = f"{filename}.png"
        elif "webp" in content_type:
            filename = f"{filename}.webp"
        else:
            filename = f"{filename}.jpg"
    return ResolvedSourceImage(
        asset_id=asset.id,
        filename=filename,
        content_type=content_type,
        folder_category=candidate.folder_category,
        tags=list(candidate.tags or []),
        image_bytes=payload,
    )
