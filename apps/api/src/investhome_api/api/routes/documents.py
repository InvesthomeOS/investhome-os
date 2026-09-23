"""Document Center API routes."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.config.documents_config import (
    FILE_KIND_DOCUMENT_TYPE,
    LINK_ENTITY_TYPES,
    RELATED_MODULE_KEYS,
    infer_file_kind,
    initial_processing_status,
    is_previewable,
)
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentLink,
    DocumentStatus,
    DocumentType,
    DocumentVisibility,
    DocumentWorkspaceFolder,
    ProcessingStatus,
)
from investhome_api.models.finance import FinanceTransaction
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.document import (
    DocumentBatchUploadResponse,
    DocumentExportResponse,
    DocumentLinkCreate,
    DocumentLinkResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResult,
    DocumentVersionListResponse,
    DocumentVersionResponse,
    DocumentWorkspaceOverviewResponse,
)
from investhome_api.services.activity_recorder import (
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.document_service import (
    archive_document,
    build_list_query,
    build_workspace_overview,
    create_document_analysis,
    enrich_response,
    export_documents_metadata_csv,
    get_document_or_404,
    get_version_chain,
    mark_previous_versions_superseded,
    restore_document,
    restore_document_version,
    user_can_download_document,
)
from investhome_api.services.document_validation import (
    compute_checksum,
    content_stream,
    generate_storage_key,
    read_and_validate_upload,
)
from investhome_api.services.notification_hooks import (
    notify_document_uploaded_confidential,
    notify_document_version_uploaded,
)
from investhome_api.services.storage import get_storage_provider, provider_enum
from investhome_api.services.document_intelligence.queue import enqueue_document_processing
from investhome_api.services.drawing_intelligence.config import should_process_as_drawing
from investhome_api.services.drawing_intelligence.queue import enqueue_drawing_processing

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENT_ACTIVITY_FIELDS = [
    "title",
    "document_type",
    "category",
    "category_code",
    "folder",
    "status",
    "visibility",
    "confidentiality_level",
    "owner_user_id",
    "company_id",
    "description",
    "notes",
    "tags",
    "document_date",
    "expiration_date",
    "review_status",
    "legal_hold",
    "publish_to_website",
]


def _resolve_uploader_name(db: Session, user_id: UUID | None) -> str | None:
    if user_id is None:
        return None
    uploader = db.get(User, user_id)
    return uploader.full_name if uploader else None


def _resolve_related_label(db: Session, document: Document) -> str | None:
    if document.project_id:
        project = db.get(Project, document.project_id)
        if project:
            return project.project_name
    if document.investor_id:
        investor = db.get(Investor, document.investor_id)
        if investor:
            return investor.full_name
    if document.lead_id:
        lead = db.get(Lead, document.lead_id)
        if lead:
            return lead.full_name
    if document.transaction_id:
        txn = db.get(FinanceTransaction, document.transaction_id)
        if txn:
            return txn.description or txn.reference_number
    return None


def _content_disposition(disposition: str, filename: str) -> str:
    cleaned = (filename or "document").replace('"', "").replace("\r", "").replace("\n", "")
    ascii_name = cleaned.encode("ascii", "replace").decode("ascii").replace("?", "_") or "document"
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(cleaned)}"


def _to_response(db: Session, document: Document) -> DocumentResponse:
    uploader_name = _resolve_uploader_name(db, document.uploaded_by_user_id)
    owner_id = getattr(document, "owner_user_id", None) or document.uploaded_by_user_id
    owner_name = _resolve_uploader_name(db, owner_id) if owner_id != document.uploaded_by_user_id else uploader_name
    return DocumentResponse.model_validate(
        enrich_response(
            document,
            uploader_name=uploader_name,
            owner_name=owner_name,
            related_label=_resolve_related_label(db, document),
        )
    )


def _parse_optional_uuid(value: str | None) -> UUID | None:
    if not value or value.strip() == "":
        return None
    return UUID(value)


def _parse_optional_date(value: str | None) -> date | None:
    if not value or value.strip() == "":
        return None
    return date.fromisoformat(value)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    search: str | None = Query(default=None, max_length=255),
    document_type: DocumentType | None = Query(default=None),
    file_kind: str | None = Query(default=None, max_length=30),
    folder: DocumentWorkspaceFolder | None = Query(default=None),
    tags: str | None = Query(default=None, max_length=255),
    visibility: DocumentVisibility | None = Query(default=None),
    category: str | None = Query(default=None, max_length=120),
    project_id: UUID | None = Query(default=None),
    investor_id: UUID | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    transaction_id: UUID | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    uploaded_by_user_id: UUID | None = Query(default=None),
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    confidentiality: ConfidentialityLevel | None = Query(default=None),
    without_relation: bool | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    related_module: str | None = Query(default=None, max_length=40),
    entity_type: str | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    latest_only: bool = Query(default=True),
    sort_by: str = Query(default="updated_at"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DocumentListResponse:
    if related_module and related_module not in RELATED_MODULE_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid related_module")
    items, total = build_list_query(
        db,
        user,
        search=search,
        document_type=document_type.value if document_type else None,
        file_kind=file_kind,
        folder=folder.value if folder else None,
        tags=tags,
        visibility=visibility.value if visibility else None,
        category=category,
        project_id=project_id,
        investor_id=investor_id,
        lead_id=lead_id,
        transaction_id=transaction_id,
        company_id=company_id,
        campaign_id=campaign_id,
        owner_user_id=owner_user_id,
        uploaded_by_user_id=uploaded_by_user_id,
        status_filter=status_filter.value if status_filter else None,
        confidentiality=confidentiality.value if confidentiality else None,
        without_relation=without_relation,
        date_from=date_from,
        date_to=date_to,
        created_from=created_from,
        created_to=created_to,
        related_module=related_module,
        entity_type=entity_type,
        entity_id=entity_id,
        include_archived=include_archived,
        latest_only=latest_only,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return DocumentListResponse(
        items=[_to_response(db, doc) for doc in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/overview", response_model=DocumentWorkspaceOverviewResponse)
def documents_workspace_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DocumentWorkspaceOverviewResponse:
    return build_workspace_overview(db, user)


@router.get("/export", response_model=DocumentExportResponse)
def export_documents_metadata(
    search: str | None = Query(default=None, max_length=255),
    document_type: DocumentType | None = Query(default=None),
    file_kind: str | None = Query(default=None, max_length=30),
    folder: DocumentWorkspaceFolder | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "export")),
) -> DocumentExportResponse:
    csv_text, row_count = export_documents_metadata_csv(
        db,
        user,
        search=search,
        document_type=document_type.value if document_type else None,
        file_kind=file_kind,
        folder=folder.value if folder else None,
        include_archived=include_archived,
    )
    return DocumentExportResponse(
        filename="documents-metadata.csv",
        content_type="text/csv",
        row_count=row_count,
        csv=csv_text,
    )


@router.get("/by-entity/{entity_type}/{entity_id}", response_model=DocumentListResponse)
def list_documents_by_entity(
    entity_type: str,
    entity_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DocumentListResponse:
    if entity_type not in LINK_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")
    items, total = build_list_query(
        db,
        user,
        entity_type=entity_type,
        entity_id=entity_id,
        include_hidden=include_hidden,
        page=page,
        page_size=page_size,
    )
    responses = []
    for doc in items:
        item = _to_response(db, doc)
        hidden = any(
            link.entity_type == entity_type
            and link.entity_id == entity_id
            and getattr(link, "hidden_from_view", False)
            for link in (doc.links or [])
        )
        responses.append(item.model_copy(update={"hidden_from_view": hidden}))
    return DocumentListResponse(
        items=responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DocumentResponse:
    document = get_document_or_404(db, document_id, user)
    return _to_response(db, document)


@router.post("/upload", response_model=DocumentBatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    title: str | None = Form(default=None),
    document_type: DocumentType = Form(default=DocumentType.OTHER),
    category: str | None = Form(default=None),
    folder: DocumentWorkspaceFolder = Form(default=DocumentWorkspaceFolder.GENERAL),
    visibility: DocumentVisibility = Form(default=DocumentVisibility.ORGANIZATION),
    project_id: str | None = Form(default=None),
    investor_id: str | None = Form(default=None),
    lead_id: str | None = Form(default=None),
    transaction_id: str | None = Form(default=None),
    company_id: str | None = Form(default=None),
    owner_user_id: str | None = Form(default=None),
    confidentiality_level: ConfidentialityLevel = Form(default=ConfidentialityLevel.INTERNAL),
    document_date: str | None = Form(default=None),
    expiration_date: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    description: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "create")),
) -> DocumentBatchUploadResponse:
    storage = get_storage_provider()
    results: list[DocumentUploadResult] = []

    for index, file in enumerate(files):
        file_name = file.filename or f"upload-{index}"
        try:
            content, ext, mime_type, original_name, file_size = await read_and_validate_upload(file)
            doc_title = title or original_name.rsplit(".", 1)[0]
            if len(files) > 1 and title:
                doc_title = f"{title} ({original_name})"

            stored_name, storage_key = generate_storage_key(ext)
            checksum = compute_checksum(content)
            storage.save(storage_key, content_stream(content), content_length=file_size)

            file_kind = infer_file_kind(ext)
            resolved_type = document_type
            if resolved_type == DocumentType.OTHER:
                resolved_type = FILE_KIND_DOCUMENT_TYPE.get(file_kind, DocumentType.OTHER)

            owner_id = _parse_optional_uuid(owner_user_id) or actor.id

            document = Document(
                title=doc_title,
                original_file_name=original_name,
                stored_file_name=stored_name,
                file_extension=ext,
                mime_type=mime_type,
                file_size=file_size,
                storage_provider=provider_enum(),
                storage_key=storage_key,
                checksum=checksum,
                document_type=resolved_type,
                category=category,
                folder=folder,
                file_kind=file_kind,
                status=DocumentStatus.ACTIVE,
                visibility=visibility,
                confidentiality_level=confidentiality_level,
                version_number=1,
                uploaded_by_user_id=actor.id,
                owner_user_id=owner_id,
                company_id=_parse_optional_uuid(company_id),
                project_id=_parse_optional_uuid(project_id),
                investor_id=_parse_optional_uuid(investor_id),
                lead_id=_parse_optional_uuid(lead_id),
                transaction_id=_parse_optional_uuid(transaction_id),
                description=description,
                notes=notes,
                tags=tags,
                document_date=_parse_optional_date(document_date),
                expiration_date=_parse_optional_date(expiration_date),
                is_latest_version=True,
                processing_status=initial_processing_status(ext, resolved_type.value),
            )
            db.add(document)
            db.flush()
            create_document_analysis(db, document.id)

            _sync_direct_links(db, document)
            log_entity_created(
                db,
                entity_type=ActivityEntityType.DOCUMENT,
                entity_id=document.id,
                description_key="activity.document.uploaded",
                actor=actor,
                metadata={"title": document.title, "file_name": original_name},
                request=request,
                is_demo=document.is_demo,
            )

            if confidentiality_level == ConfidentialityLevel.HIGHLY_CONFIDENTIAL:
                notify_document_uploaded_confidential(db, document=document, actor=actor)

            db.commit()
            db.refresh(document)
            doc_type = document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type)
            if should_process_as_drawing(document.file_extension, doc_type):
                document.processing_status = ProcessingStatus.QUEUED
                db.commit()
                enqueue_drawing_processing(document.id)
            elif document.processing_status == ProcessingStatus.UPLOADED:
                document.processing_status = ProcessingStatus.QUEUED
                if document.analysis:
                    document.analysis.processing_status = ProcessingStatus.QUEUED.value
                db.commit()
                enqueue_document_processing(document.id)
            results.append(
                DocumentUploadResult(
                    success=True,
                    document=_to_response(db, document),
                    file_name=file_name,
                )
            )
        except HTTPException as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            results.append(DocumentUploadResult(success=False, file_name=file_name, error=detail))
        except Exception:
            db.rollback()
            results.append(
                DocumentUploadResult(
                    success=False,
                    file_name=file_name,
                    error="documents.errors.upload_failed",
                )
            )

    return DocumentBatchUploadResponse(results=results)


def _sync_direct_links(db: Session, document: Document) -> None:
    mappings = [
        ("project", document.project_id),
        ("investor", document.investor_id),
        ("lead", document.lead_id),
        ("transaction", document.transaction_id),
    ]
    for entity_type, entity_id in mappings:
        primary_links = list(
            db.scalars(
                select(DocumentLink).where(
                    DocumentLink.document_id == document.id,
                    DocumentLink.entity_type == entity_type,
                    DocumentLink.relationship_type == "primary",
                )
            ).all()
        )
        for link in primary_links:
            if entity_id is None or link.entity_id != entity_id:
                db.delete(link)
        if entity_id:
            existing = db.scalar(
                select(DocumentLink).where(
                    DocumentLink.document_id == document.id,
                    DocumentLink.entity_type == entity_type,
                    DocumentLink.entity_id == entity_id,
                )
            )
            if not existing:
                db.add(
                    DocumentLink(
                        document_id=document.id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        relationship_type="primary",
                    )
                )


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "update")),
) -> DocumentResponse:
    document = get_document_or_404(db, document_id, actor)
    before = snapshot_entity(document, DOCUMENT_ACTIVITY_FIELDS)
    previous_title = document.title
    previous_folder = getattr(document, "folder", None)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(document, key, value)
    _sync_direct_links(db, document)

    description_key = "activity.document.updated"
    if "title" in updates and updates["title"] != previous_title:
        description_key = "activity.document.renamed"
    elif "folder" in updates and updates["folder"] != previous_folder:
        description_key = "activity.document.moved"

    from investhome_api.services.activity_recorder import log_activity

    if description_key in {"activity.document.renamed", "activity.document.moved"}:
        log_activity(
            db,
            action=ActivityAction.UPDATED,
            entity_type=ActivityEntityType.DOCUMENT,
            entity_id=document.id,
            description_key=description_key,
            actor_user=actor,
            metadata={
                "title": document.title,
                "previous_title": previous_title,
                "folder": getattr(document.folder, "value", document.folder),
                "previous_folder": getattr(previous_folder, "value", previous_folder),
            },
            request_context=None,
            is_demo=document.is_demo,
        )
    else:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.DOCUMENT,
            entity_id=document.id,
            description_key=description_key,
            actor=actor,
            before=before,
            after=snapshot_entity(document, DOCUMENT_ACTIVITY_FIELDS),
            request=request,
            is_demo=document.is_demo,
        )
    db.commit()
    db.refresh(document)
    return _to_response(db, document)


@router.post("/{document_id}/versions", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_new_version(
    document_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    version_notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "update")),
) -> DocumentResponse:
    previous = get_document_or_404(db, document_id, actor)
    if not previous.is_latest_version:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documents.errors.not_latest_version")

    content, ext, mime_type, original_name, file_size = await read_and_validate_upload(file)
    storage = get_storage_provider()
    stored_name, storage_key = generate_storage_key(ext)
    checksum = compute_checksum(content)
    storage.save(storage_key, content_stream(content), content_length=file_size)

    mark_previous_versions_superseded(db, previous)

    new_version = Document(
        title=previous.title,
        original_file_name=original_name,
        stored_file_name=stored_name,
        file_extension=ext,
        mime_type=mime_type,
        file_size=file_size,
        storage_provider=provider_enum(),
        storage_key=storage_key,
        checksum=checksum,
        document_type=previous.document_type,
        category=previous.category,
        folder=getattr(previous, "folder", DocumentWorkspaceFolder.GENERAL),
        file_kind=infer_file_kind(ext),
        status=DocumentStatus.ACTIVE,
        visibility=getattr(previous, "visibility", DocumentVisibility.ORGANIZATION),
        confidentiality_level=previous.confidentiality_level,
        version_number=previous.version_number + 1,
        parent_document_id=previous.id,
        uploaded_by_user_id=actor.id,
        owner_user_id=getattr(previous, "owner_user_id", None) or actor.id,
        company_id=getattr(previous, "company_id", None),
        project_id=previous.project_id,
        investor_id=previous.investor_id,
        lead_id=previous.lead_id,
        transaction_id=previous.transaction_id,
        description=previous.description,
        notes=getattr(previous, "notes", None),
        tags=previous.tags,
        document_date=previous.document_date,
        expiration_date=previous.expiration_date,
        is_latest_version=True,
        processing_status=initial_processing_status(ext, previous.document_type.value),
        version_notes=version_notes,
        is_demo=previous.is_demo,
    )
    db.add(new_version)
    db.flush()
    create_document_analysis(db, new_version.id)

    for link in previous.links:
        db.add(
            DocumentLink(
                document_id=new_version.id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                relationship_type=link.relationship_type,
            )
        )

    from investhome_api.services.activity_recorder import log_activity

    log_activity(
        db,
        action=ActivityAction.FILE_UPLOADED,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=new_version.id,
        description_key="activity.document.version_uploaded",
        actor_user=actor,
        metadata={
            "title": new_version.title,
            "version_number": new_version.version_number,
            "previous_version_id": str(previous.id),
        },
        request_context=None,
        is_demo=new_version.is_demo,
    )

    if previous.project_id:
        notify_document_version_uploaded(db, document=new_version, actor=actor)

    db.commit()
    db.refresh(new_version)
    doc_type = new_version.document_type.value if hasattr(new_version.document_type, "value") else str(new_version.document_type)
    if should_process_as_drawing(new_version.file_extension, doc_type):
        new_version.processing_status = ProcessingStatus.QUEUED
        db.commit()
        enqueue_drawing_processing(new_version.id)
    elif new_version.processing_status == ProcessingStatus.UPLOADED:
        new_version.processing_status = ProcessingStatus.QUEUED
        if new_version.analysis:
            new_version.analysis.processing_status = ProcessingStatus.QUEUED.value
        db.commit()
        enqueue_document_processing(new_version.id)
    return _to_response(db, new_version)


@router.get("/{document_id}/versions", response_model=DocumentVersionListResponse)
def list_versions(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
) -> DocumentVersionListResponse:
    document = get_document_or_404(db, document_id, user)
    versions = get_version_chain(db, document)
    current = max((v.version_number for v in versions), default=document.version_number)
    items = [
        DocumentVersionResponse(
            id=v.id,
            version_number=v.version_number,
            title=v.title,
            original_file_name=v.original_file_name,
            file_size=v.file_size,
            uploaded_by_user_id=v.uploaded_by_user_id,
            uploaded_by_name=_resolve_uploader_name(db, v.uploaded_by_user_id),
            version_notes=v.version_notes,
            is_latest_version=v.is_latest_version,
            created_at=v.created_at,
        )
        for v in versions
    ]
    return DocumentVersionListResponse(current_version=current, items=items)


@router.post(
    "/{document_id}/versions/{version_id}/restore",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def restore_version_endpoint(
    document_id: UUID,
    version_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "update")),
) -> DocumentResponse:
    document = get_document_or_404(db, document_id, actor)
    if not document.is_latest_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="documents.errors.not_latest_version",
        )
    chain = get_version_chain(db, document)
    target = next((item for item in chain if item.id == version_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    new_version = restore_document_version(
        db,
        latest=document,
        target=target,
        actor=actor,
    )
    from investhome_api.services.activity_recorder import log_activity

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=new_version.id,
        description_key="activity.document.version_restored",
        actor_user=actor,
        metadata={
            "title": new_version.title,
            "version_number": new_version.version_number,
            "restored_from_version_id": str(target.id),
            "restored_from_version_number": target.version_number,
        },
        request_context=None,
        is_demo=new_version.is_demo,
    )
    db.commit()
    db.refresh(new_version)
    return _to_response(db, new_version)


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
):
    document = get_document_or_404(db, document_id, user)
    if not user_can_download_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Download not permitted")

    storage = get_storage_provider()
    try:
        stream = storage.open(document.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from investhome_api.services.activity_recorder import activity_context_from_request, log_activity

    document.download_count = int(getattr(document, "download_count", 0) or 0) + 1
    log_activity(
        db,
        action=ActivityAction.EXPORTED,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key="activity.document.downloaded",
        actor_user=user,
        metadata={"title": document.title, "confidentiality": document.confidentiality_level.value},
        request_context=activity_context_from_request(request),
        is_demo=document.is_demo,
    )
    db.commit()

    headers = {"Content-Disposition": _content_disposition("attachment", document.original_file_name)}
    return StreamingResponse(stream, media_type=document.mime_type, headers=headers)


@router.get("/{document_id}/preview")
def preview_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents", "view")),
):
    document = get_document_or_404(db, document_id, user)
    if not user_can_download_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Download not permitted")
    if not is_previewable(document.file_extension):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="documents.errors.preview_unavailable")

    storage = get_storage_provider()
    try:
        stream = storage.open(document.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    document.preview_count = int(getattr(document, "preview_count", 0) or 0) + 1
    db.commit()

    headers = {"Content-Disposition": _content_disposition("inline", document.original_file_name)}
    return StreamingResponse(stream, media_type=document.mime_type, headers=headers)


@router.delete("/{document_id}", response_model=DocumentResponse)
def delete_document_endpoint(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "delete")),
) -> DocumentResponse:
    """Soft-delete via archive — aligns with documents.delete without a second storage stack."""
    document = get_document_or_404(db, document_id, actor, include_archived=True)
    if document.archived_at is None:
        archive_document(db, document)
        log_entity_archived(
            db,
            entity_type=ActivityEntityType.DOCUMENT,
            entity_id=document.id,
            description_key="activity.document.deleted",
            actor=actor,
            metadata={"title": document.title, "via": "soft_delete"},
            request=request,
            is_demo=document.is_demo,
        )
        db.commit()
        db.refresh(document)
    return _to_response(db, document)


@router.post("/{document_id}/archive", response_model=DocumentResponse)
def archive_document_endpoint(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "archive")),
) -> DocumentResponse:
    document = get_document_or_404(db, document_id, actor, include_archived=True)
    if document.archived_at is not None:
        return _to_response(db, document)
    archive_document(db, document)
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key="activity.document.archived",
        actor=actor,
        metadata={"title": document.title},
        request=request,
        is_demo=document.is_demo,
    )
    db.commit()
    db.refresh(document)
    return _to_response(db, document)


@router.post("/{document_id}/restore", response_model=DocumentResponse)
def restore_document_endpoint(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "archive")),
) -> DocumentResponse:
    document = get_document_or_404(db, document_id, actor, include_archived=True)
    if document.archived_at is None:
        return _to_response(db, document)
    restore_document(db, document)
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key="activity.document.restored",
        actor=actor,
        metadata={"title": document.title},
        request=request,
        is_demo=document.is_demo,
    )
    db.commit()
    db.refresh(document)
    return _to_response(db, document)


@router.post("/{document_id}/links", response_model=DocumentLinkResponse, status_code=status.HTTP_201_CREATED)
def link_document(
    document_id: UUID,
    payload: DocumentLinkCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "update")),
) -> DocumentLinkResponse:
    if payload.entity_type not in LINK_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")
    document = get_document_or_404(db, document_id, actor)
    existing = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == document.id,
            DocumentLink.entity_type == payload.entity_type,
            DocumentLink.entity_id == payload.entity_id,
        )
    )
    if existing:
        return DocumentLinkResponse.model_validate(existing)

    link = DocumentLink(
        document_id=document.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        relationship_type=payload.relationship_type,
    )
    db.add(link)

    if payload.entity_type == "project":
        document.project_id = payload.entity_id
    elif payload.entity_type == "investor":
        document.investor_id = payload.entity_id
    elif payload.entity_type == "lead":
        document.lead_id = payload.entity_id
    elif payload.entity_type in {"transaction", "financial_record"}:
        document.transaction_id = payload.entity_id
    elif payload.entity_type in {"company", "crm_company"}:
        document.company_id = payload.entity_id

    from investhome_api.services.activity_recorder import log_activity

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key="activity.document.linked",
        actor_user=actor,
        metadata={
            "title": document.title,
            "entity_type": payload.entity_type,
            "entity_id": str(payload.entity_id),
        },
        request_context=None,
        is_demo=document.is_demo,
    )
    db.commit()
    db.refresh(link)
    return DocumentLinkResponse.model_validate(link)


@router.delete("/{document_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_document(
    document_id: UUID,
    link_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("documents", "update")),
) -> None:
    document = get_document_or_404(db, document_id, actor)
    link = db.scalar(
        select(DocumentLink).where(
            DocumentLink.id == link_id,
            DocumentLink.document_id == document.id,
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    from investhome_api.services.activity_recorder import log_activity

    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key="activity.document.unlinked",
        actor_user=actor,
        metadata={
            "title": document.title,
            "entity_type": link.entity_type,
            "entity_id": str(link.entity_id),
        },
        request_context=None,
        is_demo=document.is_demo,
    )
    if link.entity_type == "project" and document.project_id == link.entity_id:
        document.project_id = None
    elif link.entity_type == "investor" and document.investor_id == link.entity_id:
        document.investor_id = None
    elif link.entity_type == "lead" and document.lead_id == link.entity_id:
        document.lead_id = None
    elif (
        link.entity_type in {"transaction", "financial_record"}
        and document.transaction_id == link.entity_id
    ):
        document.transaction_id = None
    elif (
        link.entity_type in {"company", "crm_company"}
        and document.company_id == link.entity_id
    ):
        document.company_id = None
    db.delete(link)
    db.commit()
