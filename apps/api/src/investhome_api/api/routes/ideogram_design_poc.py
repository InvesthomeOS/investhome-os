"""Ideogram External Design AI POC routes — isolated from Native SMB design engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.ideogram_design_poc import (
    IdeogramDesignRequest,
    IdeogramDesignResponse,
    IdeogramProviderStatusResponse,
)
from investhome_api.services.ideogram_design_poc.service import (
    generate_ideogram_creatives,
    get_ideogram_provider_status,
)

router = APIRouter(tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.get(
    "/ai/creative-studio/social/ideogram/status",
    response_model=IdeogramProviderStatusResponse,
)
def ideogram_provider_status(
    _user: User = _cs_view,
) -> IdeogramProviderStatusResponse:
    """Availability only — never returns the API key."""
    return get_ideogram_provider_status()


@router.post(
    "/ai/creative-studio/social/ideogram/generate",
    response_model=IdeogramDesignResponse,
)
def ideogram_generate(
    body: IdeogramDesignRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> IdeogramDesignResponse:
    """Generate three distinct Ideogram remix options. Does not overwrite Native posts."""
    result = generate_ideogram_creatives(db, user, body)
    db.commit()
    return result
