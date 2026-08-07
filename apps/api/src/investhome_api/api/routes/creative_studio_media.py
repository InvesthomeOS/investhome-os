"""Creative Studio Media Library API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_studio_media import (
    CreativeStudioMediaAssetListResponse,
    CreativeStudioMediaAssetResponse,
    CreativeStudioMediaAssetTagsUpdate,
    CreativeStudioMediaFolderCreate,
    CreativeStudioMediaFolderListResponse,
    CreativeStudioMediaFolderResponse,
)
from investhome_api.services import creative_studio_media_service as svc
from investhome_api.services.storage.factory import get_storage_provider

router = APIRouter(prefix="/creative-studio/media", tags=["creative-studio-media"])

_cs_view = Depends(require_permission("creative_studio", "view"))
_cs_create = Depends(require_permission("creative_studio", "create"))
_cs_update = Depends(require_permission("creative_studio", "update"))
_cs_archive = Depends(require_permission("creative_studio", "archive"))


@router.post("/folders", response_model=CreativeStudioMediaFolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: CreativeStudioMediaFolderCreate,
    db: Session = Depends(get_db),
    actor: User = _cs_create,
) -> CreativeStudioMediaFolderResponse:
    folder = svc.create_folder(
        db,
        name=payload.name,
        parent_id=payload.parent_id,
        company_id=payload.company_id,
        actor=actor,
    )
    db.commit()
    db.refresh(folder)
    return svc.build_folder_response(folder)


@router.get("/folders", response_model=CreativeStudioMediaFolderListResponse)
def list_folders(
    parent_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioMediaFolderListResponse:
    items = svc.list_folders(db, parent_id=parent_id, include_archived=include_archived)
    return CreativeStudioMediaFolderListResponse(items=items, total=len(items))


@router.post("/upload", response_model=CreativeStudioMediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    folder_id: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    company_id: str | None = Form(default=None),
    linked_project_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: User = _cs_create,
) -> CreativeStudioMediaAssetResponse:
    asset = await svc.upload_asset(
        db,
        file=file,
        actor=actor,
        folder_id=UUID(folder_id) if folder_id else None,
        tags_raw=tags,
        company_id=UUID(company_id) if company_id else None,
        linked_project_id=UUID(linked_project_id) if linked_project_id else None,
    )
    db.commit()
    db.refresh(asset)
    return svc.build_asset_response(asset)


@router.get("/assets", response_model=CreativeStudioMediaAssetListResponse)
def list_assets(
    folder_id: UUID | None = Query(default=None),
    tag: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioMediaAssetListResponse:
    items, total = svc.list_assets(
        db,
        folder_id=folder_id,
        tag=tag,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return CreativeStudioMediaAssetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=CreativeStudioMediaAssetListResponse)
def search_assets(
    q: str = Query(min_length=1),
    folder_id: UUID | None = Query(default=None),
    tag: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioMediaAssetListResponse:
    items, total = svc.search_assets(
        db,
        q=q,
        folder_id=folder_id,
        tag=tag,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return CreativeStudioMediaAssetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/assets/{asset_id}", response_model=CreativeStudioMediaAssetResponse)
def get_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioMediaAssetResponse:
    asset = svc.get_asset_or_404(asset_id, db, include_archived=True)
    return svc.build_asset_response(asset)


@router.patch("/assets/{asset_id}/tags", response_model=CreativeStudioMediaAssetResponse)
def update_asset_tags(
    asset_id: UUID,
    payload: CreativeStudioMediaAssetTagsUpdate,
    db: Session = Depends(get_db),
    _actor: User = _cs_update,
) -> CreativeStudioMediaAssetResponse:
    asset = svc.get_asset_or_404(asset_id, db)
    asset = svc.update_asset_tags(db, asset, payload.tags)
    db.commit()
    db.refresh(asset)
    return svc.build_asset_response(asset)


@router.delete("/assets/{asset_id}", response_model=CreativeStudioMediaAssetResponse)
def archive_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _actor: User = _cs_archive,
) -> CreativeStudioMediaAssetResponse:
    asset = svc.get_asset_or_404(asset_id, db)
    asset = svc.archive_asset(db, asset)
    db.commit()
    db.refresh(asset)
    return svc.build_asset_response(asset)


@router.get("/assets/{asset_id}/content")
def download_asset_content(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> StreamingResponse:
    """Auth-gated binary stream — mirrors Document Center download (no public URL)."""
    asset = svc.get_asset_or_404(asset_id, db, include_archived=True)
    storage = get_storage_provider()
    stream = storage.open(asset.storage_key)
    headers = {
        "Content-Disposition": f'inline; filename="{asset.filename}"',
    }
    return StreamingResponse(stream, media_type=asset.content_type, headers=headers)
