"""Hızlı Tasarım — live AI Quick Creative API.

Does not create Premium campaign records. Does not auto-generate on GET.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.quick_studio import (
    approve_quick_creative,
    download_quick_creative,
    generate_quick_creative,
    get_quick_project,
    list_quick_projects,
    replace_quick_image,
    revise_quick_creative,
    vary_quick_creative,
)

router = APIRouter(prefix="/ai/creative-studio/quick", tags=["ai-creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))

FormatId = Literal["4:5", "9:16", "1:1", "16:9"]


class QuickGenerateRequest(BaseModel):
    project_id: UUID
    request: str = Field(..., min_length=1, max_length=8000)
    format: FormatId = "4:5"
    language: str = Field(default="tr", max_length=16)


class QuickReviseRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=8000)


class QuickReplaceImageRequest(BaseModel):
    photo_id: UUID


@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> dict:
    return list_quick_projects(db)


@router.get("/projects/{project_id}")
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> dict:
    return get_quick_project(db, project_id)


@router.post("/generate")
def generate(
    body: QuickGenerateRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> dict:
    result = generate_quick_creative(
        db,
        user,
        project_id=body.project_id,
        request=body.request,
        fmt=body.format,
        language=body.language,
    )
    db.commit()
    return result


@router.post("/{campaign_id}/revise")
def revise(
    campaign_id: UUID,
    body: QuickReviseRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> dict:
    result = revise_quick_creative(db, user, campaign_id, instruction=body.instruction)
    db.commit()
    return result


@router.post("/{campaign_id}/replace-image")
def replace_image(
    campaign_id: UUID,
    body: QuickReplaceImageRequest,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> dict:
    result = replace_quick_image(db, user, campaign_id, photo_id=str(body.photo_id))
    db.commit()
    return result


@router.post("/{campaign_id}/approve")
def approve(
    campaign_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> dict:
    result = approve_quick_creative(db, user, campaign_id)
    db.commit()
    return result


@router.post("/{campaign_id}/vary")
def vary(
    campaign_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    user: User = _cs_view,
) -> dict:
    result = vary_quick_creative(db, user, campaign_id)
    db.commit()
    return result


@router.get("/{campaign_id}/download")
def download(
    campaign_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    _user: User = _cs_view,
) -> StreamingResponse:
    stream, media_type, filename = download_quick_creative(db, campaign_id)
    safe = filename.replace('"', "")
    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe}"'},
    )
