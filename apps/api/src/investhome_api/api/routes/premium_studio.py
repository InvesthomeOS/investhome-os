"""Premium Campaigns — live Creative Studio API.

Does not use GPT Image revise. Does not fabricate missing Premium formats.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.premium_studio import (
    approve_premium_revision,
    download_premium_creative,
    get_premium_campaign,
    list_premium_campaigns,
    revert_premium_preview,
    revise_premium_campaign,
)

router = APIRouter(prefix="/ai/creative-studio/premium-campaigns", tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))


class PremiumReviseRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=4000)
    format: Literal["4:5", "9:16", "1:1", "16:9"] = "9:16"
    scope: Literal["selected", "campaign"] = "selected"


class PremiumFormatRequest(BaseModel):
    format: Literal["4:5", "9:16", "1:1", "16:9"] = "9:16"


@router.get("")
def list_campaigns(
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> dict:
    return list_premium_campaigns(db)


@router.get("/{family_id}")
def get_campaign(
    family_id: UUID,
    format: str | None = Query(default=None),
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> dict:
    return get_premium_campaign(db, str(family_id), format=format)


@router.post("/{family_id}/revise")
def revise_campaign(
    family_id: UUID,
    body: PremiumReviseRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> dict:
    return revise_premium_campaign(
        db,
        user,
        str(family_id),
        instruction=body.instruction,
        fmt=body.format,
        scope=body.scope,
    )


@router.post("/{family_id}/approve")
def approve_campaign(
    family_id: UUID,
    body: PremiumFormatRequest,
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> dict:
    return approve_premium_revision(db, str(family_id), fmt=body.format)


@router.post("/{family_id}/revert")
def revert_campaign(
    family_id: UUID,
    body: PremiumFormatRequest,
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> dict:
    return revert_premium_preview(db, str(family_id), fmt=body.format)


@router.get("/{family_id}/download")
def download_campaign(
    family_id: UUID,
    format: Literal["4:5", "9:16", "1:1"] = Query(default="9:16"),
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> StreamingResponse:
    stream, media_type, filename = download_premium_creative(db, str(family_id), fmt=format)
    safe = filename.replace('"', "")
    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe}"'},
    )
