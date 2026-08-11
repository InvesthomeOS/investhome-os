"""Social Media Builder AI Design Engine API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.social_design_engine import SocialDesignRequest, SocialDesignResponse
from investhome_api.services.social_design_engine.service import generate_social_design

router = APIRouter(tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.post(
    "/ai/creative-studio/social/design",
    response_model=SocialDesignResponse,
)
def creative_studio_social_design(
    body: SocialDesignRequest,
    db: Session = Depends(get_db),
    user: User = _cs_view,
) -> SocialDesignResponse:
    """
    AI Design Engine for Social Media Builder only.

    NL create/edit → structured Design Ops → validate → mutate draft.
    Reuses Creative Studio RAG + LLMProvider. Does not write documents
    (client persists via Creative Studio Document API).
    """
    result = generate_social_design(db, user, body)
    db.commit()
    return result
