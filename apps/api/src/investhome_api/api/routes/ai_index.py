"""Read-only AI Index APIs + optional project reindex trigger."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.models.ai_index import AiDocument
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.ai_index import (
    AiDocumentListResponse,
    AiDocumentResponse,
    AiIndexReindexResponse,
)
from investhome_api.services.ai_index.pipeline import index_asset, reindex_project
from investhome_api.services.ai_index.queue import enqueue_project_ai_index
from investhome_api.services.google_drive.errors import GoogleDriveError
from investhome_api.services.google_drive.provider import get_google_drive_provider

router = APIRouter(tags=["ai-index"])

_cs_view = Depends(require_permission("creative_studio", "view"))
_cs_sync = Depends(require_permission("creative_studio", "sync_drive"))


def _project_or_404(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _to_response(doc: AiDocument) -> AiDocumentResponse:
    return AiDocumentResponse.model_validate(doc)


@router.get("/projects/{project_id}/ai-index", response_model=AiDocumentListResponse)
def list_project_ai_index(
    project_id: UUID,
    include_inactive: bool = Query(default=False),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> AiDocumentListResponse:
    _project_or_404(project_id, db)
    query = select(AiDocument).where(AiDocument.project_id == project_id)
    if not include_inactive:
        query = query.where(AiDocument.is_active.is_(True))
    if category:
        query = query.where(AiDocument.category == category.strip())
    items = list(db.scalars(query.order_by(AiDocument.updated_at.desc())).all())
    return AiDocumentListResponse(
        items=[_to_response(d) for d in items],
        total=len(items),
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/ai-index/assets/{asset_id}",
    response_model=AiDocumentResponse,
)
def get_project_asset_ai_document(
    project_id: UUID,
    asset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> AiDocumentResponse:
    _project_or_404(project_id, db)
    doc = db.scalar(
        select(AiDocument).where(
            AiDocument.project_id == project_id,
            AiDocument.asset_id == asset_id,
        )
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI document not found")
    return _to_response(doc)


@router.get(
    "/creative-studio/media/assets/{asset_id}/ai-document",
    response_model=AiDocumentResponse,
)
def get_asset_ai_document(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> AiDocumentResponse:
    asset = db.get(CreativeStudioMediaAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        # Still allow inactive AI docs for missing Drive files
        doc = db.scalar(select(AiDocument).where(AiDocument.asset_id == asset_id))
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        return _to_response(doc)
    doc = db.scalar(select(AiDocument).where(AiDocument.asset_id == asset_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI document not found")
    return _to_response(doc)


@router.post(
    "/projects/{project_id}/ai-index/reindex",
    response_model=AiIndexReindexResponse,
)
def reindex_project_ai_index(
    project_id: UUID,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _cs_sync,
) -> AiIndexReindexResponse:
    _project_or_404(project_id, db)
    settings = get_settings()
    if settings.ai_index_processing_sync:
        try:
            provider = get_google_drive_provider()
        except GoogleDriveError:
            provider = None
        except Exception:
            provider = None
        stats = reindex_project(db, project_id, provider=provider, force=force)
        db.commit()
        return AiIndexReindexResponse(
            project_id=project_id,
            queued=False,
            mode="sync",
            stats=stats,
        )

    enqueue_project_ai_index(project_id, force=force, db=db)
    return AiIndexReindexResponse(project_id=project_id, queued=True, mode="async", stats=None)


@router.post(
    "/creative-studio/media/assets/{asset_id}/ai-document/reindex",
    response_model=AiDocumentResponse,
)
def reindex_asset_ai_document(
    asset_id: UUID,
    force: bool = Query(default=True),
    db: Session = Depends(get_db),
    _user: User = _cs_sync,
) -> AiDocumentResponse:
    asset = db.get(CreativeStudioMediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    try:
        provider = get_google_drive_provider()
    except Exception:
        provider = None
    doc = index_asset(db, asset_id, provider=provider, force=force)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset not indexable")
    db.commit()
    db.refresh(doc)
    return _to_response(doc)
