"""Creative Studio shared AI generation API — Phase 1 foundation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_studio_generation import (
    CreativeStudioGenerateRequest,
    CreativeStudioGenerateResponse,
)
from investhome_api.services.creative_studio_generation.service import generate_creative_content

router = APIRouter(tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.post("/ai/creative-studio/generate", response_model=CreativeStudioGenerateResponse)
def creative_studio_generate(
    body: CreativeStudioGenerateRequest,
    db: Session = Depends(get_db),
    user: User = _cs_view,
) -> CreativeStudioGenerateResponse:
    """
    Shared Creative Studio generation endpoint for all builders.

    Requires linked_project_id. Retrieves project-scoped RAG only.
    Does not redesign builder UI — foundation layer only.
    """
    result = generate_creative_content(db, user, body)
    db.commit()
    return result
