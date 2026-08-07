"""Creative Studio API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_studio import (
    CreativeStudioDocumentCreate,
    CreativeStudioDocumentListResponse,
    CreativeStudioDocumentResponse,
    CreativeStudioDraftUpdate,
    CreativeStudioProjectCreate,
    CreativeStudioProjectListResponse,
    CreativeStudioProjectResponse,
    CreativeStudioRestoreRequest,
    CreativeStudioRestoreResponse,
    CreativeStudioVersionCreate,
    CreativeStudioVersionListResponse,
    CreativeStudioVersionResponse,
)
from investhome_api.services import creative_studio_service as svc

router = APIRouter(prefix="/creative-studio", tags=["creative-studio"])

_cs_view = Depends(require_permission("creative_studio", "view"))
_cs_create = Depends(require_permission("creative_studio", "create"))
_cs_save_draft = Depends(require_permission("creative_studio", "save_draft"))
_cs_save_version = Depends(require_permission("creative_studio", "save_version"))
_cs_restore = Depends(require_permission("creative_studio", "restore"))


@router.post("/projects", response_model=CreativeStudioProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreativeStudioProjectCreate,
    db: Session = Depends(get_db),
    actor: User = _cs_create,
) -> CreativeStudioProjectResponse:
    project = svc.create_project(
        db,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        company_id=payload.company_id,
        linked_project_id=payload.linked_project_id,
        actor=actor,
    )
    db.commit()
    db.refresh(project)
    return svc.build_project_response(project, db)


@router.get("/projects", response_model=CreativeStudioProjectListResponse)
def list_projects(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioProjectListResponse:
    items = svc.list_projects(db, include_archived=include_archived)
    return CreativeStudioProjectListResponse(items=items, total=len(items))


@router.post(
    "/projects/{project_id}/documents",
    response_model=CreativeStudioDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    project_id: UUID,
    payload: CreativeStudioDocumentCreate,
    db: Session = Depends(get_db),
    actor: User = _cs_create,
) -> CreativeStudioDocumentResponse:
    project = svc.get_project_or_404(project_id, db)
    document = svc.create_document(
        db,
        project=project,
        title=payload.title,
        description=payload.description,
        document_type=payload.document_type,
        status=payload.status,
        language=payload.language,
        thumbnail_url=payload.thumbnail_url,
        draft_body_json=payload.draft_body_json,
        actor=actor,
    )
    db.commit()
    db.refresh(document)
    return svc.build_document_response(document)


@router.get("/projects/{project_id}/documents", response_model=CreativeStudioDocumentListResponse)
def list_documents(
    project_id: UUID,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioDocumentListResponse:
    svc.get_project_or_404(project_id, db, include_archived=True)
    items = svc.list_documents(db, project_id=project_id, include_archived=include_archived)
    return CreativeStudioDocumentListResponse(items=items, total=len(items))


@router.get("/documents/{document_id}", response_model=CreativeStudioDocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioDocumentResponse:
    document = svc.get_document_or_404(document_id, db, include_archived=True)
    return svc.build_document_response(document, include_draft=True)


@router.put("/documents/{document_id}/draft", response_model=CreativeStudioDocumentResponse)
def save_draft(
    document_id: UUID,
    payload: CreativeStudioDraftUpdate,
    db: Session = Depends(get_db),
    actor: User = _cs_save_draft,
) -> CreativeStudioDocumentResponse:
    document = svc.get_document_or_404(document_id, db)
    document = svc.save_draft(db, document, draft_body_json=payload.draft_body_json, actor=actor)
    db.commit()
    db.refresh(document)
    return svc.build_document_response(document)


@router.post(
    "/documents/{document_id}/versions",
    response_model=CreativeStudioVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    document_id: UUID,
    payload: CreativeStudioVersionCreate,
    db: Session = Depends(get_db),
    actor: User = _cs_save_version,
) -> CreativeStudioVersionResponse:
    document = svc.get_document_or_404(document_id, db)
    version = svc.create_version(
        db,
        document,
        body_json=payload.body_json,
        label=payload.label,
        summary=payload.summary,
        actor=actor,
    )
    db.commit()
    db.refresh(version)
    return svc.build_version_response(version, include_body=True)


@router.get("/documents/{document_id}/versions", response_model=CreativeStudioVersionListResponse)
def list_versions(
    document_id: UUID,
    include_body: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> CreativeStudioVersionListResponse:
    svc.get_document_or_404(document_id, db, include_archived=True)
    items = svc.list_versions(db, document_id, include_body=include_body)
    return CreativeStudioVersionListResponse(items=items, total=len(items))


@router.post(
    "/documents/{document_id}/versions/{version_id}/restore",
    response_model=CreativeStudioRestoreResponse,
)
def restore_version(
    document_id: UUID,
    version_id: UUID,
    payload: CreativeStudioRestoreRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = _cs_restore,
) -> CreativeStudioRestoreResponse:
    body = payload or CreativeStudioRestoreRequest()
    document = svc.get_document_or_404(document_id, db)
    document, new_version = svc.restore_version(
        db,
        document,
        version_id,
        create_version_flag=body.create_version,
        label=body.label,
        summary=body.summary,
        actor=actor,
    )
    db.commit()
    db.refresh(document)
    if new_version is not None:
        db.refresh(new_version)
    # Reload with versions for accurate version_count
    document = svc.get_document_or_404(document_id, db, include_archived=True)
    return CreativeStudioRestoreResponse(
        document=svc.build_document_response(document),
        new_version=svc.build_version_response(new_version, include_body=True) if new_version else None,
    )
