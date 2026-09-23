"""CRM workspace API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.config.documents_config import LINK_ENTITY_TYPES
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm import (
    CrmDashboardResponse,
    CrmTagAssignRequest,
    CrmTagCreate,
    CrmTagDetail,
    CrmTagListResponse,
    CrmTagStatusRequest,
    CrmTagUpdate,
)
from investhome_api.schemas.crm_agreements import CrmDocumentVisibilityRequest
from investhome_api.schemas.crm_documents import (
    CrmDocumentFeedResponse,
    CrmDocumentHubVisibilityRequest,
    CrmDocumentHubVisibilityResponse,
)
from investhome_api.schemas.document import DocumentLinkResponse
from investhome_api.services.crm.agreement_service import set_document_surface_hidden
from investhome_api.services.crm.document_feed import list_document_feed, set_document_hub_hidden
from investhome_api.services.crm.tag_service import (
    TagConflictError,
    TagNotFoundError,
    assign_tag,
    create_tag,
    get_tag,
    list_tags,
    set_tag_status,
    update_tag,
)
from investhome_api.services.crm_dashboard_service import build_crm_dashboard
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm", tags=["crm"])


def _require_crm_read():
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(user, "crm", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency


@router.get("/dashboard", response_model=CrmDashboardResponse)
def get_crm_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmDashboardResponse:
    return build_crm_dashboard(db, user)


@router.get("/tags", response_model=CrmTagListResponse)
def list_crm_tags(
    search: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmTagListResponse:
    del user
    return list_tags(db, search=search, status=status)


@router.post("/tags", response_model=CrmTagDetail, status_code=status.HTTP_201_CREATED)
def create_crm_tag(
    body: CrmTagCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmTagDetail:
    try:
        return create_tag(db, body, actor=user)
    except TagConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/tags/{tag_id}", response_model=CrmTagDetail)
def get_crm_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmTagDetail:
    del user
    try:
        return get_tag(db, tag_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/tags/{tag_id}", response_model=CrmTagDetail)
def patch_crm_tag(
    tag_id: UUID,
    body: CrmTagUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmTagDetail:
    try:
        return update_tag(db, tag_id, body, actor=user)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TagConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/tags/{tag_id}/deactivate", response_model=CrmTagDetail)
def deactivate_crm_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmTagDetail:
    try:
        return set_tag_status(db, tag_id, "inactive", actor=user)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/tags/{tag_id}/activate", response_model=CrmTagDetail)
def activate_crm_tag(
    tag_id: UUID,
    body: CrmTagStatusRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmTagDetail:
    del body
    try:
        return set_tag_status(db, tag_id, "active", actor=user)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/document-visibility", response_model=DocumentLinkResponse)
def post_document_visibility(
    body: CrmDocumentVisibilityRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> DocumentLinkResponse:
    del user
    if body.entity_type not in LINK_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")
    try:
        link = set_document_surface_hidden(
            db,
            document_id=body.document_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            hidden=body.hidden,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    db.refresh(link)
    return DocumentLinkResponse.model_validate(link)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.get("/documents/feed", response_model=CrmDocumentFeedResponse)
def get_crm_document_feed(
    search: str | None = Query(default=None),
    person: str | None = Query(default=None),
    project_group: str | None = Query(default=None),
    unit: str | None = Query(default=None),
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
    visibility: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmDocumentFeedResponse:
    del user
    body = list_document_feed(
        db,
        search=search,
        person=person,
        project_group=project_group,
        unit=unit,
        category=category,
        source=source,
        visibility=visibility,
        scope=scope,
        date_from=_parse_iso(date_from),
        date_to=_parse_iso(date_to),
        page=page,
        page_size=page_size,
    )
    body.request_id = get_request_id() or ""
    return body


@router.post("/documents/{document_id}/hub-visibility", response_model=CrmDocumentHubVisibilityResponse)
def post_crm_document_hub_visibility(
    document_id: UUID,
    body: CrmDocumentHubVisibilityRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmDocumentHubVisibilityResponse:
    del user
    try:
        document, updated = set_document_hub_hidden(db, document_id, body.hidden)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return CrmDocumentHubVisibilityResponse(
        id=document.id,
        hidden=body.hidden,
        updated_links=updated,
        request_id=get_request_id() or "",
    )
