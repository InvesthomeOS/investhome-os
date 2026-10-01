"""Company workspace documents API routes."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.config.documents_config import is_previewable
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.company_workspace_document import (
    CompanyDocumentApprovalStep,
    CompanyDocumentCategory,
    CompanyDocumentRecordStatus,
    CompanyWorkspaceDocument,
    DocumentFolder,
)
from investhome_api.models.document import ConfidentialityLevel, Document, DocumentType
from investhome_api.models.user_auth import User
from investhome_api.schemas.company_workspace_document import (
    ApprovalDecisionRequest,
    ApprovalRequest,
    CompanyDocumentBulkActionRequest,
    CompanyDocumentCreate,
    CompanyDocumentExportResponse,
    CompanyDocumentListResponse,
    CompanyDocumentResponse,
    CompanyDocumentShareLinkCreate,
    CompanyDocumentShareLinkResponse,
    CompanyDocumentStorageSummary,
    CompanyDocumentUpdate,
    CompanyDocumentVersionResponse,
    DocumentFolderCreate,
    DocumentFolderResponse,
    DocumentFolderTreeResponse,
    DocumentFolderUpdate,
    LegalHoldCreate,
    LegalHoldResponse,
    MalwareScanResult,
    SignatureRequestCreate,
    TemplateGenerateRequest,
    TemplateGenerateResponse,
)
from investhome_api.services.activity_recorder import activity_context_from_request, log_entity_created, log_entity_updated
from investhome_api.services.activity_service import log_activity, snapshot_entity
from investhome_api.services.company_document_service import (
    build_folder_tree,
    build_list_query,
    create_approval_workflow,
    create_folder,
    create_share_link,
    create_signature_request,
    decide_approval_step,
    generate_from_template,
    get_folder_or_none,
    get_record_or_none,
    increment_share_download,
    malware_scan_stub,
    place_legal_hold,
    resolve_share_link,
    restore_version,
    seed_default_folders,
    serialize_record,
    sign_document,
    storage_summary,
    toggle_favorite,
    upload_company_document,
    upload_new_version,
    user_can_download_document,
    user_can_view_document,
    validate_folder_parent,
    verify_download_token,
    create_download_token,
)
from investhome_api.services.document_validation import content_stream, read_bytes_capped
from investhome_api.services.document_service import reject_unauthorized_sensitive_document_fields
from investhome_api.services.document_access_audit import (
    deny_document_access,
    record_document_access,
)
from investhome_api.services.storage import get_storage_provider

router = APIRouter(prefix="/company-documents", tags=["company-documents"])


def _value_error_http(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _get_record_or_404(db: Session, record_id: UUID) -> CompanyWorkspaceDocument:
    record = get_record_or_none(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.not_found")
    return record


def _to_response(db: Session, record: CompanyWorkspaceDocument, user: User, *, detail: bool = False) -> CompanyDocumentResponse:
    payload = serialize_record(db, record, user=user, include_versions=detail)
    return CompanyDocumentResponse.model_validate(payload)


def _audit(
    db: Session,
    *,
    request: Request,
    user: User,
    record: CompanyWorkspaceDocument,
    action: ActivityAction,
    description_key: str,
    metadata: dict | None = None,
) -> None:
    ctx = activity_context_from_request(request)
    log_activity(
        db,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=record.document_id,
        action=action,
        actor_user=user,
        description_key=description_key,
        metadata={
            "company_document_id": str(record.id),
            "document_number": record.document_number,
            "title": record.title,
            **(metadata or {}),
        },
        request_context=ctx,
    )


@router.get("/folders", response_model=DocumentFolderTreeResponse)
def list_folders(
    company_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DocumentFolderTreeResponse:
    folders = build_folder_tree(db, company_id)
    counts: dict[UUID, int] = {}
    for folder in folders:
        count = db.query(CompanyWorkspaceDocument).filter(
            CompanyWorkspaceDocument.folder_id == folder.id,
            CompanyWorkspaceDocument.deleted_at.is_(None),
        ).count()
        counts[folder.id] = count

    items = [
        DocumentFolderResponse.model_validate(
            {
                **folder.__dict__,
                "document_count": counts.get(folder.id, 0),
                "children": [],
            }
        )
        for folder in folders
        if folder.parent_folder_id is None
    ]
    return DocumentFolderTreeResponse(items=items, total=len(folders))


@router.post("/folders", response_model=DocumentFolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder_endpoint(
    payload: DocumentFolderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "create")),
) -> DocumentFolderResponse:
    try:
        folder = create_folder(
            db,
            company_id=payload.company_id,
            name=payload.name,
            parent_folder_id=payload.parent_folder_id,
            description=payload.description,
        )
        db.commit()
        db.refresh(folder)
        return DocumentFolderResponse.model_validate({**folder.__dict__, "document_count": 0, "children": []})
    except ValueError as exc:
        raise _value_error_http(exc) from exc


@router.put("/folders/{folder_id}", response_model=DocumentFolderResponse)
def update_folder_endpoint(
    folder_id: UUID,
    payload: DocumentFolderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> DocumentFolderResponse:
    folder = get_folder_or_none(db, folder_id)
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.folder_not_found")
    if payload.parent_folder_id is not None:
        try:
            validate_folder_parent(db, folder_id, payload.parent_folder_id)
        except ValueError as exc:
            raise _value_error_http(exc) from exc
        folder.parent_folder_id = payload.parent_folder_id
    if payload.name is not None:
        folder.name = payload.name
    if payload.description is not None:
        folder.description = payload.description
    db.commit()
    db.refresh(folder)
    return DocumentFolderResponse.model_validate({**folder.__dict__, "document_count": 0, "children": []})


@router.get("", response_model=CompanyDocumentListResponse)
def list_company_documents(
    company_id: UUID | None = Query(default=None),
    folder_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    category: CompanyDocumentCategory | None = Query(default=None),
    status_filter: CompanyDocumentRecordStatus | None = Query(default=None, alias="status"),
    view: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="updated_at"),
    sort_dir: str = Query(default="desc"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentListResponse:
    items, total, page, page_size, total_pages = build_list_query(
        db,
        company_id=company_id,
        folder_id=folder_id,
        search=search,
        category=category,
        status=status_filter,
        view=view,
        user_id=user.id,
        user=user,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    visible = [r for r in items if user_can_view_document(db, user, r)]
    return CompanyDocumentListResponse(
        items=[_to_response(db, r, user) for r in visible],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/recent", response_model=CompanyDocumentListResponse)
def list_recent_documents(
    company_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentListResponse:
    return list_company_documents(
        company_id=company_id,
        folder_id=None,
        search=None,
        category=None,
        status_filter=None,
        view="recent",
        page=page,
        page_size=page_size,
        sort_by="created_at",
        sort_dir="desc",
        db=db,
        user=user,
    )


@router.get("/expiring", response_model=CompanyDocumentListResponse)
def list_expiring_documents(
    company_id: UUID | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentListResponse:
    items, total, page, page_size, total_pages = build_list_query(
        db,
        company_id=company_id,
        view="expiring",
        expiring_within_days=days,
        user_id=user.id,
        page=page,
        page_size=page_size,
    )
    visible = [r for r in items if user_can_view_document(db, user, r)]
    return CompanyDocumentListResponse(
        items=[_to_response(db, r, user) for r in visible],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/storage-summary", response_model=CompanyDocumentStorageSummary)
def get_storage_summary(
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentStorageSummary:
    return CompanyDocumentStorageSummary.model_validate(storage_summary(db, company_id))


@router.get("/export", response_model=CompanyDocumentExportResponse)
def export_documents(
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentExportResponse:
    from datetime import UTC, datetime

    items, total, _, _, _ = build_list_query(db, company_id=company_id, page=1, page_size=1000)
    visible = [r for r in items if user_can_view_document(db, user, r)]
    return CompanyDocumentExportResponse(
        exported_at=datetime.now(UTC),
        count=len(visible),
        items=[_to_response(db, r, user, detail=True) for r in visible],
    )


@router.get("/{record_id}", response_model=CompanyDocumentResponse)
def get_company_document(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentResponse:
    record = _get_record_or_404(db, record_id)
    if not user_can_view_document(db, user, record):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="company_document.errors.forbidden")
    return _to_response(db, record, user, detail=True)


@router.post("/upload", response_model=CompanyDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    company_id: UUID = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    category: CompanyDocumentCategory = Form(default=CompanyDocumentCategory.OTHER),
    document_type: DocumentType = Form(default=DocumentType.OTHER),
    confidentiality_level: ConfidentialityLevel = Form(default=ConfidentialityLevel.INTERNAL),
    folder_id: UUID | None = Form(default=None),
    branch_id: UUID | None = Form(default=None),
    department_id: UUID | None = Form(default=None),
    tags: str | None = Form(default=None),
    expiration_date: date | None = Form(default=None),
    allow_duplicate: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "create")),
) -> CompanyDocumentResponse:
    content = await read_bytes_capped(file)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    try:
        record, is_dup = upload_company_document(
            db,
            user=user,
            company_id=company_id,
            file_content=content,
            original_file_name=file.filename or "upload",
            declared_mime=file.content_type,
            title=title,
            description=description,
            category=category,
            document_type=document_type,
            confidentiality_level=confidentiality_level,
            folder_id=folder_id,
            branch_id=branch_id,
            department_id=department_id,
            tags=tag_list,
            expiration_date=expiration_date,
            allow_duplicate=allow_duplicate,
        )
        _audit(db, request=request, user=user, record=record, action=ActivityAction.CREATED, description_key="activity.company_document.uploaded")
        db.commit()
        db.refresh(record)
        response = _to_response(db, record, user, detail=True)
        if is_dup:
            response.description = (response.description or "") + " [duplicate detected]"
        return response
    except ValueError as exc:
        raise _value_error_http(exc) from exc


@router.post("/bulk-upload", response_model=list[CompanyDocumentResponse], status_code=status.HTTP_201_CREATED)
async def bulk_upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    company_id: UUID = Form(...),
    folder_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "create")),
) -> list[CompanyDocumentResponse]:
    results: list[CompanyDocumentResponse] = []
    for upload in files:
        content = await read_bytes_capped(upload)
        try:
            record, _ = upload_company_document(
                db,
                user=user,
                company_id=company_id,
                file_content=content,
                original_file_name=upload.filename or "upload",
                declared_mime=upload.content_type,
                folder_id=folder_id,
            )
            _audit(db, request=request, user=user, record=record, action=ActivityAction.CREATED, description_key="activity.company_document.uploaded")
            results.append(_to_response(db, record, user))
        except ValueError:
            continue
    db.commit()
    return results


@router.put("/{record_id}", response_model=CompanyDocumentResponse)
def update_company_document(
    record_id: UUID,
    payload: CompanyDocumentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> CompanyDocumentResponse:
    record = _get_record_or_404(db, record_id)
    before = snapshot_entity(record)
    data = payload.model_dump(exclude_unset=True)
    reject_unauthorized_sensitive_document_fields(
        db,
        user,
        data,
        current_confidentiality=record.confidentiality_level,
        current_owner_id=record.owner_user_id,
    )
    if "tags" in data:
        from investhome_api.services.company_document_service import _tags_to_json

        data["tags_json"] = _tags_to_json(data.pop("tags"))
    for key, value in data.items():
        setattr(record, key, value)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=record.document_id,
        before=before,
        after=record,
        actor=user,
        description_key="activity.company_document.updated",
        request=request,
    )
    db.commit()
    db.refresh(record)
    return _to_response(db, record, user, detail=True)


@router.post("/{record_id}/versions", response_model=CompanyDocumentVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_version(
    record_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    version_notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> CompanyDocumentVersionResponse:
    record = _get_record_or_404(db, record_id)
    content = await read_bytes_capped(file)
    try:
        version = upload_new_version(
            db,
            user=user,
            record=record,
            file_content=content,
            original_file_name=file.filename or "upload",
            version_notes=version_notes,
            declared_mime=file.content_type,
        )
        _audit(db, request=request, user=user, record=record, action=ActivityAction.UPDATED, description_key="activity.company_document.version_uploaded")
        db.commit()
        db.refresh(version)
        return CompanyDocumentVersionResponse.model_validate(
            serialize_record(db, record, user=user, include_versions=True)["versions"][-1]
        )
    except ValueError as exc:
        raise _value_error_http(exc) from exc


@router.get("/{record_id}/versions", response_model=list[CompanyDocumentVersionResponse])
def list_versions(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> list[CompanyDocumentVersionResponse]:
    record = _get_record_or_404(db, record_id)
    if not user_can_view_document(db, user, record):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="company_document.errors.forbidden")
    payload = serialize_record(db, record, user=user, include_versions=True)
    return [CompanyDocumentVersionResponse.model_validate(v) for v in payload["versions"]]


@router.post("/{record_id}/restore-version/{version_id}", response_model=CompanyDocumentVersionResponse)
def restore_version_endpoint(
    record_id: UUID,
    version_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> CompanyDocumentVersionResponse:
    record = _get_record_or_404(db, record_id)
    try:
        version = restore_version(db, user=user, record=record, version_id=version_id)
        _audit(db, request=request, user=user, record=record, action=ActivityAction.UPDATED, description_key="activity.company_document.version_restored")
        db.commit()
        db.refresh(version)
        payload = serialize_record(db, record, user=user, include_versions=True)
        return CompanyDocumentVersionResponse.model_validate(payload["versions"][-1])
    except ValueError as exc:
        raise _value_error_http(exc) from exc


@router.get("/{record_id}/download")
def download_document(
    record_id: UUID,
    request: Request,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    record = _get_record_or_404(db, record_id)
    engine_doc = db.get(Document, record.document_id)
    if engine_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.file_not_found")
    if token:
        if not verify_download_token(token, record_id, user.id):
            deny_document_access(
                db,
                document=engine_doc,
                access_type="download",
                actor=user,
                request=request,
                module="company_documents",
                status_code=status.HTTP_403_FORBIDDEN,
                detail="company_document.errors.invalid_token",
                reason="invalid_token",
            )
    elif not user_can_download_document(db, user, record):
        deny_document_access(
            db,
            document=engine_doc,
            access_type="download",
            actor=user,
            request=request,
            module="company_documents",
            status_code=status.HTTP_403_FORBIDDEN,
            detail="company_document.errors.forbidden",
        )

    stream = get_storage_provider().open(engine_doc.storage_key)
    record_document_access(
        db,
        document=engine_doc,
        access_type="download",
        actor=user,
        request=request,
        module="company_documents",
    )
    db.commit()
    return StreamingResponse(
        stream,
        media_type=engine_doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{engine_doc.original_file_name}"'},
    )


@router.get("/{record_id}/preview")
def preview_document(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "download")),
) -> StreamingResponse:
    record = _get_record_or_404(db, record_id)
    engine_doc = db.get(Document, record.document_id)
    if not user_can_view_document(db, user, record):
        if engine_doc is not None:
            deny_document_access(
                db,
                document=engine_doc,
                access_type="preview",
                actor=user,
                request=request,
                module="company_documents",
                status_code=status.HTTP_403_FORBIDDEN,
                detail="company_document.errors.forbidden",
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="company_document.errors.forbidden")
    if engine_doc is None or not is_previewable(engine_doc.file_extension):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="documents.errors.preview_unavailable")
    stream = get_storage_provider().open(engine_doc.storage_key)
    record_document_access(
        db,
        document=engine_doc,
        access_type="preview",
        actor=user,
        request=request,
        module="company_documents",
    )
    db.commit()
    return StreamingResponse(stream, media_type=engine_doc.mime_type)


@router.get("/{record_id}/secure-link")
def get_secure_download_link(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "download")),
) -> dict:
    record = _get_record_or_404(db, record_id)
    if not user_can_download_document(db, user, record):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="company_document.errors.forbidden")
    token = create_download_token(record_id, user.id)
    return {"token": token, "expires_in_seconds": 300, "download_url": f"/company-documents/{record_id}/download?token={token}"}


@router.post("/{record_id}/share", response_model=CompanyDocumentShareLinkResponse, status_code=status.HTTP_201_CREATED)
def create_share_link_endpoint(
    record_id: UUID,
    payload: CompanyDocumentShareLinkCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "create")),
) -> CompanyDocumentShareLinkResponse:
    record = _get_record_or_404(db, record_id)
    link = create_share_link(
        db,
        record=record,
        user=user,
        expires_in_hours=payload.expires_in_hours,
        password=payload.password,
        max_downloads=payload.max_downloads,
    )
    _audit(db, request=request, user=user, record=record, action=ActivityAction.UPDATED, description_key="activity.company_document.shared")
    db.commit()
    db.refresh(link)
    return CompanyDocumentShareLinkResponse.model_validate(
        {**link.__dict__, "secure_url": f"/company-documents/shared/{link.token}"}
    )


@router.get("/shared/{token}/download")
def shared_download(
    token: str,
    request: Request,
    password: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    link = resolve_share_link(db, token, password)
    if link is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="company_document.errors.link_expired")
    record = get_record_or_none(db, link.workspace_document_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.not_found")
    engine_doc = db.get(Document, record.document_id)
    if engine_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.file_not_found")
    increment_share_download(db, link)
    record_document_access(
        db,
        document=engine_doc,
        access_type="download",
        actor=None,
        request=request,
        module="company_documents_share",
    )
    db.commit()
    stream = get_storage_provider().open(engine_doc.storage_key)
    return StreamingResponse(
        stream,
        media_type=engine_doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{engine_doc.original_file_name}"'},
    )


@router.post("/{record_id}/archive", response_model=CompanyDocumentResponse)
def archive_document(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "archive")),
) -> CompanyDocumentResponse:
    from datetime import UTC, datetime

    record = _get_record_or_404(db, record_id)
    record.archived_at = datetime.now(UTC)
    record.status = CompanyDocumentRecordStatus.ARCHIVED
    _audit(db, request=request, user=user, record=record, action=ActivityAction.ARCHIVED, description_key="activity.company_document.archived")
    db.commit()
    db.refresh(record)
    return _to_response(db, record, user)


@router.post("/{record_id}/restore", response_model=CompanyDocumentResponse)
def restore_document_endpoint(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "restore")),
) -> CompanyDocumentResponse:
    record = _get_record_or_404(db, record_id)
    record.archived_at = None
    record.deleted_at = None
    record.status = CompanyDocumentRecordStatus.ACTIVE
    _audit(db, request=request, user=user, record=record, action=ActivityAction.RESTORED, description_key="activity.company_document.restored")
    db.commit()
    db.refresh(record)
    return _to_response(db, record, user)


@router.post("/{record_id}/trash", response_model=CompanyDocumentResponse)
def trash_document(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "archive")),
) -> CompanyDocumentResponse:
    from datetime import UTC, datetime, timedelta

    record = _get_record_or_404(db, record_id)
    record.deleted_at = datetime.now(UTC)
    record.status = CompanyDocumentRecordStatus.TRASH
    record.retention_expires_at = datetime.now(UTC) + timedelta(days=30)
    _audit(db, request=request, user=user, record=record, action=ActivityAction.ARCHIVED, description_key="activity.company_document.trashed")
    db.commit()
    db.refresh(record)
    return _to_response(db, record, user)


@router.post("/bulk-action", response_model=dict)
def bulk_action(
    payload: CompanyDocumentBulkActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "update")),
) -> dict:
    from datetime import UTC, datetime, timedelta

    affected = 0
    for doc_id in payload.document_ids:
        record = get_record_or_none(db, doc_id)
        if record is None:
            continue
        if payload.action == "archive":
            record.archived_at = datetime.now(UTC)
            record.status = CompanyDocumentRecordStatus.ARCHIVED
        elif payload.action == "restore":
            record.archived_at = None
            record.deleted_at = None
            record.status = CompanyDocumentRecordStatus.ACTIVE
        elif payload.action == "trash":
            record.deleted_at = datetime.now(UTC)
            record.status = CompanyDocumentRecordStatus.TRASH
            record.retention_expires_at = datetime.now(UTC) + timedelta(days=30)
        elif payload.action == "favorite":
            toggle_favorite(db, record, user, True)
        elif payload.action == "unfavorite":
            toggle_favorite(db, record, user, False)
        affected += 1
    db.commit()
    return {"affected": affected, "action": payload.action}


@router.post("/{record_id}/favorite", response_model=CompanyDocumentResponse)
def favorite_document(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentResponse:
    record = _get_record_or_404(db, record_id)
    toggle_favorite(db, record, user, True)
    db.commit()
    return _to_response(db, record, user)


@router.delete("/{record_id}/favorite", response_model=CompanyDocumentResponse)
def unfavorite_document(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> CompanyDocumentResponse:
    record = _get_record_or_404(db, record_id)
    toggle_favorite(db, record, user, False)
    db.commit()
    return _to_response(db, record, user)


@router.post("/{record_id}/approval", response_model=CompanyDocumentResponse)
def request_approval(
    record_id: UUID,
    payload: ApprovalRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "approve")),
) -> CompanyDocumentResponse:
    record = _get_record_or_404(db, record_id)
    create_approval_workflow(db, record, user, payload.approver_user_ids)
    _audit(db, request=request, user=user, record=record, action=ActivityAction.UPDATED, description_key="activity.company_document.approval_requested")
    db.commit()
    db.refresh(record)
    return _to_response(db, record, user, detail=True)


@router.post("/approval-steps/{step_id}/approve", response_model=dict)
def approve_step(
    step_id: UUID,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "approve")),
) -> dict:
    step = db.get(CompanyDocumentApprovalStep, step_id)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.step_not_found")
    decide_approval_step(db, step, approved=True, comments=payload.comments)
    db.commit()
    return {"status": "approved"}


@router.post("/approval-steps/{step_id}/reject", response_model=dict)
def reject_step(
    step_id: UUID,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "approve")),
) -> dict:
    step = db.get(CompanyDocumentApprovalStep, step_id)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.step_not_found")
    decide_approval_step(db, step, approved=False, comments=payload.comments)
    db.commit()
    return {"status": "rejected"}


@router.post("/{record_id}/signature-requests", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_signature_request_endpoint(
    record_id: UUID,
    payload: SignatureRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "create")),
) -> dict:
    record = _get_record_or_404(db, record_id)
    req = create_signature_request(
        db,
        record,
        signer_user_id=payload.signer_user_id,
        signer_email=payload.signer_email,
        signer_name=payload.signer_name,
        message=payload.message,
    )
    db.commit()
    return {"id": str(req.id), "status": req.status.value}


@router.post("/signature-requests/{request_id}/sign", response_model=dict)
def sign_request_endpoint(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    from investhome_api.models.company_workspace_document import CompanyDocumentSignatureRequest

    req = db.get(CompanyDocumentSignatureRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_document.errors.signature_not_found")
    sign_document(db, req)
    db.commit()
    return {"status": "signed"}


@router.post("/{record_id}/legal-hold", response_model=LegalHoldResponse, status_code=status.HTTP_201_CREATED)
def create_legal_hold(
    record_id: UUID,
    payload: LegalHoldCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "manage")),
) -> LegalHoldResponse:
    record = _get_record_or_404(db, record_id)
    hold = place_legal_hold(db, record, user, payload.reason)
    db.commit()
    db.refresh(hold)
    return LegalHoldResponse.model_validate(hold)


@router.post("/templates/generate", response_model=TemplateGenerateResponse)
def generate_template(
    payload: TemplateGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "create")),
) -> TemplateGenerateResponse:
    try:
        result = generate_from_template(db, payload.template_id, payload.variables)
        return TemplateGenerateResponse.model_validate(result)
    except ValueError as exc:
        raise _value_error_http(exc) from exc


@router.post("/{record_id}/malware-scan", response_model=MalwareScanResult)
def scan_malware(
    record_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> MalwareScanResult:
    _get_record_or_404(db, record_id)
    return MalwareScanResult.model_validate(malware_scan_stub())
