"""GPT Image Social Media Builder visual engine routes — isolated from Native/Ideogram."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.gpt_image_design import (
    GptImageDesignRequest,
    GptImageDesignResponse,
    GptImageProviderStatusResponse,
)
from investhome_api.services.gpt_image_design.config import GPT_IMAGE_PROVIDERS
from investhome_api.services.gpt_image_design.service import (
    generate_gpt_image_creatives,
    get_gpt_image_provider_status,
)

router = APIRouter(tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.get(
    "/ai/creative-studio/social/gpt-image/status",
    response_model=GptImageProviderStatusResponse,
)
def gpt_image_provider_status(
    _user: User = _cs_view,
) -> GptImageProviderStatusResponse:
    """Availability only — never returns the API key."""
    return get_gpt_image_provider_status()


@router.post(
    "/ai/creative-studio/social/gpt-image/generate",
    response_model=GptImageDesignResponse,
)
def gpt_image_generate(
    body: GptImageDesignRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> GptImageDesignResponse:
    """PROJECT MODE edits a real project photo. Does not fall back to Native or Ideogram."""
    if (getattr(body, "design_provider", None) or "gpt-image") not in GPT_IMAGE_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPT Image generate requires design_provider=gpt-image.",
        )
    result = generate_gpt_image_creatives(db, user, body)
    db.commit()
    return result
