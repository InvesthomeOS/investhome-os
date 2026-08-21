"""Creative Director API — campaign brief + context + finished-ad generate/revise."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorCampaignRequest,
    CreativeDirectorCampaignResponse,
    CreativeDirectorGenerateAdRequest,
    CreativeDirectorGenerateAdResponse,
    CreativeDirectorRecomposeAdRequest,
    CreativeDirectorReviseAdResponse,
    CreativeDirectorReviseRequest,
)
from investhome_api.services.creative_director.generate_ad import (
    generate_ad_from_campaign,
    recompose_ad_from_campaign,
)
from investhome_api.services.creative_director.revision import (
    redo_campaign_revision,
    revise_ad_from_campaign,
    undo_campaign_revision,
)
from investhome_api.services.creative_director.service import (
    create_campaign,
    get_campaign,
)

router = APIRouter(tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.post(
    "/ai/creative-studio/campaigns",
    response_model=CreativeDirectorCampaignResponse,
)
def create_creative_director_campaign(
    body: CreativeDirectorCampaignRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> CreativeDirectorCampaignResponse:
    """Creative Director thinks the campaign and returns a structured brief.

    Does NOT generate images. Persists Campaign Context for later builders.
    """
    result = create_campaign(db, user, body)
    db.commit()
    return result


@router.get(
    "/ai/creative-studio/campaigns/{campaign_id}",
    response_model=CreativeDirectorCampaignResponse,
)
def get_creative_director_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> CreativeDirectorCampaignResponse:
    return get_campaign(db, campaign_id)


@router.post(
    "/ai/creative-studio/campaigns/{campaign_id}/revise",
    response_model=CreativeDirectorReviseAdResponse,
)
def revise_creative_director_campaign(
    campaign_id: UUID,
    body: CreativeDirectorReviseRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> CreativeDirectorReviseAdResponse:
    """Revise from immutable master_asset_id + cumulative ops (not prior revision raster)."""
    result = revise_ad_from_campaign(db, user, campaign_id, body)
    db.commit()
    return result


@router.post(
    "/ai/creative-studio/campaigns/{campaign_id}/undo-revision",
    response_model=CreativeDirectorReviseAdResponse,
)
def undo_creative_director_revision(
    campaign_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> CreativeDirectorReviseAdResponse:
    """Undo — move revision cursor back to a prior final_asset_id (0 provider calls)."""
    result = undo_campaign_revision(db, user, campaign_id)
    db.commit()
    return result


@router.post(
    "/ai/creative-studio/campaigns/{campaign_id}/redo-revision",
    response_model=CreativeDirectorReviseAdResponse,
)
def redo_creative_director_revision(
    campaign_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> CreativeDirectorReviseAdResponse:
    """Redo — move revision cursor forward to a saved final_asset_id (0 provider calls)."""
    result = redo_campaign_revision(db, user, campaign_id)
    db.commit()
    return result


@router.post(
    "/ai/creative-studio/campaigns/{campaign_id}/recompose",
    response_model=CreativeDirectorGenerateAdResponse,
)
def recompose_creative_director_ad(
    campaign_id: UUID,
    body: CreativeDirectorRecomposeAdRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> CreativeDirectorGenerateAdResponse:
    """Regenerate OS layers from an existing GPT Image background — zero provider calls."""
    result = recompose_ad_from_campaign(db, user, campaign_id, body)
    db.commit()
    return result


@router.post(
    "/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
    response_model=CreativeDirectorGenerateAdResponse,
)
def generate_creative_director_ad(
    campaign_id: UUID,
    body: CreativeDirectorGenerateAdRequest | None = None,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> CreativeDirectorGenerateAdResponse:
    """Approved Campaign Context → finished-ad image production (default) or OS compose."""
    result = generate_ad_from_campaign(
        db,
        user,
        campaign_id,
        body or CreativeDirectorGenerateAdRequest(),
    )
    db.commit()
    return result
