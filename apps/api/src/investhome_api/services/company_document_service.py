"""Company workspace document service — extends the central Document Engine."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import BinaryIO
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from investhome_api.config.documents_config import (
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
    DEFAULT_MAX_UPLOAD_BYTES,
    initial_processing_status,
)
from investhome_api.models.company import Company
from investhome_api.models.company_workspace_document import (
    ApprovalStepStatus,
    CompanyDocumentApprovalStep,
    CompanyDocumentApprovalWorkflow,
    CompanyDocumentCategory,
    CompanyDocumentFavorite,
    CompanyDocumentLegalHold,
    CompanyDocumentPermission,
    CompanyDocumentRecordStatus,
    CompanyDocumentRetentionPolicy,
    CompanyDocumentShareLink,
    CompanyDocumentSignatureRequest,
    CompanyDocumentTemplate,
    CompanyDocumentVersion,
    CompanyWorkspaceDocument,
    DocumentFolder,
    SignatureRequestStatus,
)
from investhome_api.models.document import ConfidentialityLevel, Document, DocumentLink, DocumentStatus, DocumentType
from investhome_api.models.user_auth import User
from investhome_api.services.auth_service import hash_password, verify_password
from fastapi import HTTPException
from investhome_api.config.settings import get_settings
from investhome_api.services.document_validation import (
    compute_checksum,
    extract_extension,
    generate_storage_key,
    sanitize_filename,
    validate_extension,
    validate_mime_type,
)
from investhome_api.services.permission_service import is_super_admin, user_has_permission
from investhome_api.services.storage import get_storage_provider, provider_enum

@dataclass
class _UploadValidation:
    ok: bool
    extension: str = ""
    mime_type: str = ""
    error: str | None = None


def _validate_upload_bytes(original_file_name: str, file_content: bytes) -> _UploadValidation:
    result = _UploadValidation(ok=False)
    settings = get_settings()
    max_bytes = settings.document_max_upload_bytes or DEFAULT_MAX_UPLOAD_BYTES
    if len(file_content) == 0:
        result.error = "documents.errors.empty_file"
        return result
    if len(file_content) > max_bytes:
        result.error = "documents.errors.file_too_large"
        return result
    original_name = sanitize_filename(original_file_name)
    ext = extract_extension(original_name)
    try:
        validate_extension(ext)
        mime_type = validate_mime_type(ext, None)
    except HTTPException:
        result.error = "documents.errors.unsupported_type"
        return result
    if ext not in ALLOWED_EXTENSIONS or ext in BLOCKED_EXTENSIONS:
        result.error = "documents.errors.unsupported_type"
        return result
    result.ok = True
    result.extension = ext
    result.mime_type = mime_type
    return result


DEFAULT_FOLDER_SEEDS = (
    ("General", "general"),
    ("Legal", "legal"),
    ("HR", "hr"),
    ("Finance", "finance"),
    ("Compliance", "compliance"),
    ("Contracts", "contracts"),
    ("Policies", "policies"),
)


def _tags_to_json(tags: list[str] | None) -> str | None:
    if not tags:
        return None
    return json.dumps(tags)


def _tags_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _generate_document_number(db: Session) -> str:
    year = datetime.now(UTC).year
    prefix = f"CD-{year}-"
    count = db.scalar(
        select(func.count()).select_from(CompanyWorkspaceDocument).where(
            CompanyWorkspaceDocument.document_number.like(f"{prefix}%")
        )
    )
    return f"{prefix}{(count or 0) + 1:05d}"


def _folder_ancestors(db: Session, folder_id: UUID) -> set[UUID]:
    ancestors: set[UUID] = set()
    current_id: UUID | None = folder_id
    while current_id is not None:
        if current_id in ancestors:
            break
        ancestors.add(current_id)
        folder = db.get(DocumentFolder, current_id)
        if folder is None:
            break
        current_id = folder.parent_folder_id
    return ancestors


def validate_folder_parent(db: Session, folder_id: UUID, new_parent_id: UUID | None) -> None:
    if new_parent_id is None:
        return
    if folder_id == new_parent_id:
        msg = "company_document.errors.circular_folder"
        raise ValueError(msg)
    ancestors = _folder_ancestors(db, new_parent_id)
    if folder_id in ancestors:
        msg = "company_document.errors.circular_folder"
        raise ValueError(msg)


def seed_default_folders(db: Session, company_id: UUID) -> list[DocumentFolder]:
    existing = db.scalars(select(DocumentFolder).where(DocumentFolder.company_id == company_id)).all()
    if existing:
        return list(existing)
    folders: list[DocumentFolder] = []
    for index, (name, slug) in enumerate(DEFAULT_FOLDER_SEEDS):
        folder = DocumentFolder(
            company_id=company_id,
            name=name,
            slug=slug,
            is_system=True,
            sort_order=index,
        )
        db.add(folder)
        folders.append(folder)
    db.flush()
    return folders


def get_folder_or_none(db: Session, folder_id: UUID) -> DocumentFolder | None:
    return db.get(DocumentFolder, folder_id)


def create_folder(
    db: Session,
    *,
    company_id: UUID,
    name: str,
    parent_folder_id: UUID | None = None,
    description: str | None = None,
) -> DocumentFolder:
    if parent_folder_id is not None:
        parent = get_folder_or_none(db, parent_folder_id)
        if parent is None or parent.company_id != company_id:
            msg = "company_document.errors.folder_not_found"
            raise ValueError(msg)
    slug = name.lower().replace(" ", "-")[:255]
    folder = DocumentFolder(
        company_id=company_id,
        parent_folder_id=parent_folder_id,
        name=name,
        slug=slug,
        description=description,
    )
    db.add(folder)
    db.flush()
    return folder


def build_folder_tree(db: Session, company_id: UUID) -> list[DocumentFolder]:
    seed_default_folders(db, company_id)
    folders = db.scalars(
        select(DocumentFolder)
        .where(DocumentFolder.company_id == company_id, DocumentFolder.archived_at.is_(None))
        .order_by(DocumentFolder.sort_order, DocumentFolder.name)
    ).all()
    return list(folders)


def user_can_view_document(db: Session, user: User, record: CompanyWorkspaceDocument) -> bool:
    if is_super_admin(user):
        return True
    if not user_has_permission(user, "documents", "view"):
        return False
    level = record.confidentiality_level
    if level == ConfidentialityLevel.CONFIDENTIAL and not user_has_permission(user, "documents", "view_confidential"):
        return False
    if level == ConfidentialityLevel.HIGHLY_CONFIDENTIAL and not user_has_permission(
        user, "documents", "view_highly_confidential"
    ):
        return False
    explicit = db.scalars(
        select(CompanyDocumentPermission).where(
            CompanyDocumentPermission.workspace_document_id == record.id,
            or_(CompanyDocumentPermission.user_id == user.id, CompanyDocumentPermission.role_code.isnot(None)),
        )
    ).all()
    if explicit:
        return any(perm.can_view for perm in explicit if perm.user_id == user.id)
    return True


def user_can_download_document(db: Session, user: User, record: CompanyWorkspaceDocument) -> bool:
    if not user_can_view_document(db, user, record):
        return False
    if is_super_admin(user):
        return True
    if not user_has_permission(user, "documents", "download"):
        return False
    explicit = db.scalars(
        select(CompanyDocumentPermission).where(
            CompanyDocumentPermission.workspace_document_id == record.id,
            CompanyDocumentPermission.user_id == user.id,
        )
    ).all()
    if explicit:
        return any(perm.can_download for perm in explicit)
    return True


def _create_engine_document(
    db: Session,
    *,
    title: str,
    original_file_name: str,
    ext: str,
    mime_type: str,
    file_size: int,
    checksum: str,
    storage_key: str,
    stored_file_name: str,
    document_type: DocumentType,
    confidentiality_level: ConfidentialityLevel,
    uploaded_by_user_id: UUID | None,
    description: str | None = None,
    tags_json: str | None = None,
    expiration_date: date | None = None,
) -> Document:
    provider = get_storage_provider()
    document = Document(
        title=title,
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        file_extension=ext,
        mime_type=mime_type,
        file_size=file_size,
        storage_provider=provider_enum(),
        storage_key=storage_key,
        checksum=checksum,
        document_type=document_type,
        confidentiality_level=confidentiality_level,
        uploaded_by_user_id=uploaded_by_user_id,
        description=description,
        tags=tags_json,
        expiration_date=expiration_date,
        processing_status=initial_processing_status(ext, document_type.value),
    )
    db.add(document)
    db.flush()
    return document


def _sync_document_link(db: Session, document_id: UUID, entity_type: str, entity_id: UUID) -> None:
    existing = db.scalar(
        select(DocumentLink).where(
            DocumentLink.document_id == document_id,
            DocumentLink.entity_type == entity_type,
            DocumentLink.entity_id == entity_id,
        )
    )
    if existing is None:
        db.add(DocumentLink(document_id=document_id, entity_type=entity_type, entity_id=entity_id))


def find_duplicate_by_checksum(db: Session, company_id: UUID, checksum: str) -> CompanyWorkspaceDocument | None:
    return db.scalar(
        select(CompanyWorkspaceDocument)
        .join(Document, CompanyWorkspaceDocument.document_id == Document.id)
        .where(
            CompanyWorkspaceDocument.company_id == company_id,
            Document.checksum == checksum,
            CompanyWorkspaceDocument.deleted_at.is_(None),
        )
    )


def upload_company_document(
    db: Session,
    *,
    user: User,
    company_id: UUID,
    file_content: bytes,
    original_file_name: str,
    title: str | None = None,
    description: str | None = None,
    category: CompanyDocumentCategory = CompanyDocumentCategory.OTHER,
    document_type: DocumentType = DocumentType.OTHER,
    confidentiality_level: ConfidentialityLevel = ConfidentialityLevel.INTERNAL,
    folder_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    team_id: UUID | None = None,
    employee_user_id: UUID | None = None,
    tags: list[str] | None = None,
    effective_date: date | None = None,
    expiration_date: date | None = None,
    renewal_date: date | None = None,
    owner_user_id: UUID | None = None,
    allow_duplicate: bool = False,
) -> tuple[CompanyWorkspaceDocument, bool]:
    """Returns (record, is_duplicate). Raises ValueError on validation failure."""
    company = db.get(Company, company_id)
    if company is None:
        msg = "company_document.errors.company_not_found"
        raise ValueError(msg)

    validated = _validate_upload_bytes(original_file_name, file_content)
    if not validated.ok:
        msg = validated.error or "company_document.errors.invalid_upload"
        raise ValueError(msg)

    checksum = compute_checksum(file_content)
    if not allow_duplicate:
        duplicate = find_duplicate_by_checksum(db, company_id, checksum)
        if duplicate is not None:
            return duplicate, True

    ext = validated.extension
    stored_name, storage_key = generate_storage_key(ext)
    provider = get_storage_provider()
    from io import BytesIO

    provider.save(storage_key, BytesIO(file_content), content_length=len(file_content))

    doc_title = title or original_file_name.rsplit(".", 1)[0]
    tags_json = _tags_to_json(tags)
    engine_doc = _create_engine_document(
        db,
        title=doc_title,
        original_file_name=sanitize_filename(original_file_name),
        ext=ext,
        mime_type=validated.mime_type,
        file_size=len(file_content),
        checksum=checksum,
        storage_key=storage_key,
        stored_file_name=stored_name,
        document_type=document_type,
        confidentiality_level=confidentiality_level,
        uploaded_by_user_id=user.id,
        description=description,
        tags_json=tags_json,
        expiration_date=expiration_date,
    )
    _sync_document_link(db, engine_doc.id, "company", company_id)

    record = CompanyWorkspaceDocument(
        document_number=_generate_document_number(db),
        title=doc_title,
        description=description,
        category=category,
        document_type=document_type,
        confidentiality_level=confidentiality_level,
        company_id=company_id,
        branch_id=branch_id,
        department_id=department_id,
        team_id=team_id,
        employee_user_id=employee_user_id,
        folder_id=folder_id,
        owner_user_id=owner_user_id or user.id,
        document_id=engine_doc.id,
        current_version_number=1,
        tags_json=tags_json,
        effective_date=effective_date,
        expiration_date=expiration_date,
        renewal_date=renewal_date,
        created_by_user_id=user.id,
    )
    db.add(record)
    db.flush()

    version = CompanyDocumentVersion(
        workspace_document_id=record.id,
        document_id=engine_doc.id,
        version_number=1,
        checksum=checksum,
        file_size=len(file_content),
        original_file_name=original_file_name,
        uploaded_by_user_id=user.id,
        is_current=True,
    )
    db.add(version)
    db.flush()
    return record, False


def upload_new_version(
    db: Session,
    *,
    user: User,
    record: CompanyWorkspaceDocument,
    file_content: bytes,
    original_file_name: str,
    version_notes: str | None = None,
) -> CompanyDocumentVersion:
    validated = _validate_upload_bytes(original_file_name, file_content)
    if not validated.ok:
        msg = validated.error or "company_document.errors.invalid_upload"
        raise ValueError(msg)

    checksum = compute_checksum(file_content)
    ext = validated.extension
    stored_name, storage_key = generate_storage_key(ext)
    provider = get_storage_provider()
    from io import BytesIO

    provider.save(storage_key, BytesIO(file_content), content_length=len(file_content))

    new_version_number = record.current_version_number + 1
    engine_doc = _create_engine_document(
        db,
        title=record.title,
        original_file_name=sanitize_filename(original_file_name),
        ext=ext,
        mime_type=validated.mime_type,
        file_size=len(file_content),
        checksum=checksum,
        storage_key=storage_key,
        stored_file_name=stored_name,
        document_type=record.document_type,
        confidentiality_level=record.confidentiality_level,
        uploaded_by_user_id=user.id,
        description=record.description,
        tags_json=record.tags_json,
        expiration_date=record.expiration_date,
    )
    engine_doc.parent_document_id = record.document_id
    engine_doc.version_number = new_version_number
    engine_doc.is_latest_version = True

    old_engine = db.get(Document, record.document_id)
    if old_engine:
        old_engine.is_latest_version = False
        old_engine.status = DocumentStatus.SUPERSEDED

    for ver in record.versions:
        ver.is_current = False

    record.document_id = engine_doc.id
    record.current_version_number = new_version_number
    record.updated_at = datetime.now(UTC)

    version = CompanyDocumentVersion(
        workspace_document_id=record.id,
        document_id=engine_doc.id,
        version_number=new_version_number,
        version_notes=version_notes,
        checksum=checksum,
        file_size=len(file_content),
        original_file_name=original_file_name,
        uploaded_by_user_id=user.id,
        is_current=True,
    )
    db.add(version)
    db.flush()
    return version


def restore_version(
    db: Session,
    *,
    user: User,
    record: CompanyWorkspaceDocument,
    version_id: UUID,
) -> CompanyDocumentVersion:
    target = db.get(CompanyDocumentVersion, version_id)
    if target is None or target.workspace_document_id != record.id:
        msg = "company_document.errors.version_not_found"
        raise ValueError(msg)
    if target.is_current:
        return target

    source_doc = db.get(Document, target.document_id)
    if source_doc is None:
        msg = "company_document.errors.version_not_found"
        raise ValueError(msg)

    stream = get_storage_provider().open(source_doc.storage_key)
    content = stream.read()
    stream.close()
    return upload_new_version(
        db,
        user=user,
        record=record,
        file_content=content,
        original_file_name=target.original_file_name,
        version_notes=f"Restored from version {target.version_number}",
    )


def build_list_query(
    db: Session,
    *,
    company_id: UUID | None = None,
    folder_id: UUID | None = None,
    search: str | None = None,
    category: CompanyDocumentCategory | None = None,
    status: CompanyDocumentRecordStatus | None = None,
    view: str | None = None,
    user_id: UUID | None = None,
    user: User | None = None,
    expiring_within_days: int | None = None,
    include_deleted: bool = False,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
):
    query = select(CompanyWorkspaceDocument).options(joinedload(CompanyWorkspaceDocument.versions))

    if not include_deleted:
        if view == "trash":
            query = query.where(CompanyWorkspaceDocument.deleted_at.isnot(None))
        else:
            query = query.where(CompanyWorkspaceDocument.deleted_at.is_(None))

    if company_id:
        query = query.where(CompanyWorkspaceDocument.company_id == company_id)
    if folder_id:
        query = query.where(CompanyWorkspaceDocument.folder_id == folder_id)
    if category:
        query = query.where(CompanyWorkspaceDocument.category == category)
    if status:
        query = query.where(CompanyWorkspaceDocument.status == status)

    if user is not None and not is_super_admin(user):
        allowed_levels = [ConfidentialityLevel.PUBLIC, ConfidentialityLevel.INTERNAL]
        if user_has_permission(user, "documents", "view_confidential"):
            allowed_levels.append(ConfidentialityLevel.CONFIDENTIAL)
        if user_has_permission(user, "documents", "view_highly_confidential"):
            allowed_levels.append(ConfidentialityLevel.HIGHLY_CONFIDENTIAL)
        query = query.where(CompanyWorkspaceDocument.confidentiality_level.in_(allowed_levels))
    if view == "archived":
        query = query.where(CompanyWorkspaceDocument.archived_at.isnot(None))
    elif view == "recent":
        cutoff = datetime.now(UTC) - timedelta(days=30)
        query = query.where(CompanyWorkspaceDocument.created_at >= cutoff)
    elif view == "expiring":
        today = date.today()
        horizon = today + timedelta(days=expiring_within_days or 30)
        query = query.where(
            CompanyWorkspaceDocument.expiration_date.isnot(None),
            CompanyWorkspaceDocument.expiration_date <= horizon,
            CompanyWorkspaceDocument.expiration_date >= today,
        )
    elif view == "favorites" and user_id:
        query = query.join(CompanyDocumentFavorite).where(CompanyDocumentFavorite.user_id == user_id)
    elif view == "shared":
        query = query.join(CompanyDocumentShareLink).where(CompanyDocumentShareLink.revoked_at.is_(None))

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                CompanyWorkspaceDocument.title.ilike(pattern),
                CompanyWorkspaceDocument.document_number.ilike(pattern),
                CompanyWorkspaceDocument.description.ilike(pattern),
            )
        )

    sort_column = getattr(CompanyWorkspaceDocument, sort_by, CompanyWorkspaceDocument.updated_at)
    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    offset = (page - 1) * page_size
    items = db.scalars(query.offset(offset).limit(page_size)).unique().all()
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    return items, total or 0, page, page_size, total_pages


def get_record_or_none(db: Session, record_id: UUID) -> CompanyWorkspaceDocument | None:
    return db.scalar(
        select(CompanyWorkspaceDocument)
        .options(
            joinedload(CompanyWorkspaceDocument.versions),
            joinedload(CompanyWorkspaceDocument.permissions),
            joinedload(CompanyWorkspaceDocument.share_links),
            joinedload(CompanyWorkspaceDocument.approval_workflows).joinedload(
                CompanyDocumentApprovalWorkflow.steps
            ),
            joinedload(CompanyWorkspaceDocument.signature_requests),
            joinedload(CompanyWorkspaceDocument.legal_holds),
        )
        .where(CompanyWorkspaceDocument.id == record_id)
    )


def serialize_record(
    db: Session,
    record: CompanyWorkspaceDocument,
    *,
    user: User | None = None,
    include_versions: bool = False,
) -> dict:
    engine_doc = db.get(Document, record.document_id)
    company = db.get(Company, record.company_id)
    owner = db.get(User, record.owner_user_id) if record.owner_user_id else None
    creator = db.get(User, record.created_by_user_id) if record.created_by_user_id else None
    folder = get_folder_or_none(db, record.folder_id) if record.folder_id else None

    is_favorited = False
    if user:
        fav = db.scalar(
            select(CompanyDocumentFavorite).where(
                CompanyDocumentFavorite.workspace_document_id == record.id,
                CompanyDocumentFavorite.user_id == user.id,
            )
        )
        is_favorited = fav is not None

    has_legal_hold = any(h.is_active for h in record.legal_holds) if record.legal_holds else False

    payload = {
        "id": record.id,
        "document_number": record.document_number,
        "title": record.title,
        "description": record.description,
        "category": record.category,
        "document_type": record.document_type,
        "confidentiality_level": record.confidentiality_level,
        "status": record.status,
        "company_id": record.company_id,
        "branch_id": record.branch_id,
        "department_id": record.department_id,
        "team_id": record.team_id,
        "employee_user_id": record.employee_user_id,
        "folder_id": record.folder_id,
        "related_record_type": record.related_record_type,
        "related_record_id": record.related_record_id,
        "owner_user_id": record.owner_user_id,
        "document_id": record.document_id,
        "current_version_number": record.current_version_number,
        "tags": _tags_from_json(record.tags_json),
        "effective_date": record.effective_date,
        "expiration_date": record.expiration_date,
        "renewal_date": record.renewal_date,
        "is_favorited": is_favorited,
        "created_by_user_id": record.created_by_user_id,
        "created_by_name": creator.full_name if creator else None,
        "owner_name": owner.full_name if owner else None,
        "folder_name": folder.name if folder else None,
        "company_name": company.company_name if company else None,
        "file_name": engine_doc.original_file_name if engine_doc else None,
        "file_size": engine_doc.file_size if engine_doc else None,
        "file_extension": engine_doc.file_extension if engine_doc else None,
        "mime_type": engine_doc.mime_type if engine_doc else None,
        "checksum": engine_doc.checksum if engine_doc else None,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "archived_at": record.archived_at,
        "deleted_at": record.deleted_at,
        "retention_expires_at": record.retention_expires_at,
        "has_legal_hold": has_legal_hold,
        "versions": [],
        "permissions": [],
        "share_links": [],
        "approval_workflows": [],
        "signature_requests": [],
    }

    if include_versions and record.versions:
        for ver in record.versions:
            uploader = db.get(User, ver.uploaded_by_user_id) if ver.uploaded_by_user_id else None
            payload["versions"].append(
                {
                    "id": ver.id,
                    "version_number": ver.version_number,
                    "version_notes": ver.version_notes,
                    "checksum": ver.checksum,
                    "file_size": ver.file_size,
                    "original_file_name": ver.original_file_name,
                    "uploaded_by_user_id": ver.uploaded_by_user_id,
                    "uploaded_by_name": uploader.full_name if uploader else None,
                    "is_current": ver.is_current,
                    "created_at": ver.created_at,
                    "document_id": ver.document_id,
                }
            )

    if record.permissions:
        payload["permissions"] = [
            {
                "id": p.id,
                "user_id": p.user_id,
                "role_code": p.role_code,
                "can_view": p.can_view,
                "can_download": p.can_download,
                "can_share": p.can_share,
                "can_edit": p.can_edit,
                "inherit_from_folder": p.inherit_from_folder,
            }
            for p in record.permissions
        ]

    return payload


def create_share_link(
    db: Session,
    *,
    record: CompanyWorkspaceDocument,
    user: User,
    expires_in_hours: int = 72,
    password: str | None = None,
    max_downloads: int | None = None,
) -> CompanyDocumentShareLink:
    token = secrets.token_urlsafe(32)
    link = CompanyDocumentShareLink(
        workspace_document_id=record.id,
        token=token,
        password_hash=hash_password(password) if password else None,
        expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
        max_downloads=max_downloads,
        created_by_user_id=user.id,
    )
    db.add(link)
    db.flush()
    return link


def resolve_share_link(
    db: Session,
    token: str,
    password: str | None = None,
) -> CompanyDocumentShareLink | None:
    link = db.scalar(select(CompanyDocumentShareLink).where(CompanyDocumentShareLink.token == token))
    if link is None:
        return None
    if link.revoked_at is not None:
        return None
    expires_at = link.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        return None
    if link.max_downloads is not None and link.download_count >= link.max_downloads:
        return None
    if link.password_hash and not (password and verify_password(password, link.password_hash)):
        return None
    return link


def increment_share_download(db: Session, link: CompanyDocumentShareLink) -> None:
    link.download_count += 1
    db.flush()


def create_download_token(record_id: UUID, user_id: UUID, ttl_seconds: int = 300) -> str:
    """Short-lived signed download token (HMAC stub — production should use JWT)."""
    import hashlib
    import hmac

    from investhome_api.config.settings import get_settings

    settings = get_settings()
    secret = settings.jwt_secret.encode()
    expires = int((datetime.now(UTC) + timedelta(seconds=ttl_seconds)).timestamp())
    payload = f"{record_id}:{user_id}:{expires}"
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}:{sig}"


def verify_download_token(token: str, record_id: UUID, user_id: UUID) -> bool:
    import hashlib
    import hmac

    from investhome_api.config.settings import get_settings

    try:
        parts = token.split(":")
        if len(parts) != 4:
            return False
        rid, uid, expires_str, sig = parts
        if UUID(rid) != record_id or UUID(uid) != user_id:
            return False
        if int(expires_str) < int(datetime.now(UTC).timestamp()):
            return False
        secret = get_settings().jwt_secret.encode()
        payload = f"{rid}:{uid}:{expires_str}"
        expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(sig, expected)
    except (ValueError, TypeError):
        return False


def storage_summary(db: Session, company_id: UUID | None = None) -> dict:
    query = select(CompanyWorkspaceDocument).where(CompanyWorkspaceDocument.deleted_at.is_(None))
    if company_id:
        query = query.where(CompanyWorkspaceDocument.company_id == company_id)
    records = db.scalars(query).all()
    total_bytes = 0
    by_category: dict[str, int] = {}
    expiring_soon = 0
    in_trash = 0
    archived = 0
    today = date.today()
    horizon = today + timedelta(days=30)

    for record in records:
        by_category[record.category.value] = by_category.get(record.category.value, 0) + 1
        engine_doc = db.get(Document, record.document_id)
        if engine_doc:
            total_bytes += engine_doc.file_size
        if record.expiration_date and today <= record.expiration_date <= horizon:
            expiring_soon += 1
        if record.archived_at:
            archived += 1

    trash_count = db.scalar(
        select(func.count()).select_from(CompanyWorkspaceDocument).where(
            CompanyWorkspaceDocument.deleted_at.isnot(None),
            *([CompanyWorkspaceDocument.company_id == company_id] if company_id else []),
        )
    )

    return {
        "total_documents": len(records),
        "total_bytes": total_bytes,
        "by_category": by_category,
        "expiring_soon": expiring_soon,
        "in_trash": trash_count or 0,
        "archived": archived,
    }


def toggle_favorite(db: Session, record: CompanyWorkspaceDocument, user: User, favorited: bool) -> None:
    existing = db.scalar(
        select(CompanyDocumentFavorite).where(
            CompanyDocumentFavorite.workspace_document_id == record.id,
            CompanyDocumentFavorite.user_id == user.id,
        )
    )
    if favorited and existing is None:
        db.add(CompanyDocumentFavorite(workspace_document_id=record.id, user_id=user.id))
    elif not favorited and existing:
        db.delete(existing)
    db.flush()


def create_approval_workflow(
    db: Session,
    record: CompanyWorkspaceDocument,
    user: User,
    approver_user_ids: list[UUID],
) -> CompanyDocumentApprovalWorkflow:
    workflow = CompanyDocumentApprovalWorkflow(
        workspace_document_id=record.id,
        requested_by_user_id=user.id,
        status="pending",
    )
    db.add(workflow)
    db.flush()
    for index, approver_id in enumerate(approver_user_ids, start=1):
        db.add(
            CompanyDocumentApprovalStep(
                workflow_id=workflow.id,
                step_order=index,
                approver_user_id=approver_id,
            )
        )
    record.status = CompanyDocumentRecordStatus.PENDING_APPROVAL
    db.flush()
    return workflow


def decide_approval_step(
    db: Session,
    step: CompanyDocumentApprovalStep,
    *,
    approved: bool,
    comments: str | None = None,
) -> None:
    step.status = ApprovalStepStatus.APPROVED if approved else ApprovalStepStatus.REJECTED
    step.comments = comments
    step.decided_at = datetime.now(UTC)
    workflow = db.get(CompanyDocumentApprovalWorkflow, step.workflow_id)
    if workflow is None:
        return
    record = db.get(CompanyWorkspaceDocument, workflow.workspace_document_id)
    if not approved:
        workflow.status = "rejected"
        if record:
            record.status = CompanyDocumentRecordStatus.REJECTED
        workflow.completed_at = datetime.now(UTC)
        return
    pending = db.scalars(
        select(CompanyDocumentApprovalStep).where(
            CompanyDocumentApprovalStep.workflow_id == workflow.id,
            CompanyDocumentApprovalStep.status == ApprovalStepStatus.PENDING,
        )
    ).all()
    if not pending:
        workflow.status = "approved"
        workflow.completed_at = datetime.now(UTC)
        if record:
            record.status = CompanyDocumentRecordStatus.APPROVED
    db.flush()


def create_signature_request(
    db: Session,
    record: CompanyWorkspaceDocument,
    *,
    signer_user_id: UUID | None = None,
    signer_email: str | None = None,
    signer_name: str | None = None,
    message: str | None = None,
) -> CompanyDocumentSignatureRequest:
    req = CompanyDocumentSignatureRequest(
        workspace_document_id=record.id,
        signer_user_id=signer_user_id,
        signer_email=signer_email,
        signer_name=signer_name,
        message=message,
        status=SignatureRequestStatus.PENDING,
    )
    db.add(req)
    db.flush()
    return req


def sign_document(db: Session, req: CompanyDocumentSignatureRequest) -> None:
    req.status = SignatureRequestStatus.SIGNED
    req.signed_at = datetime.now(UTC)
    db.flush()


def place_legal_hold(db: Session, record: CompanyWorkspaceDocument, user: User, reason: str) -> CompanyDocumentLegalHold:
    hold = CompanyDocumentLegalHold(
        workspace_document_id=record.id,
        reason=reason,
        placed_by_user_id=user.id,
        is_active=True,
    )
    db.add(hold)
    db.flush()
    return hold


def generate_from_template(db: Session, template_id: UUID, variables: dict[str, str]) -> dict:
    template = db.get(CompanyDocumentTemplate, template_id)
    if template is None:
        msg = "company_document.errors.template_not_found"
        raise ValueError(msg)
    return {
        "status": "stub",
        "message": "Template generation is a Phase 2 feature. Variables received but document not created.",
        "document_id": None,
    }


def malware_scan_stub() -> dict:
    return {
        "status": "passed",
        "scanned_at": datetime.now(UTC),
        "message": "Malware scanning is not yet integrated. This stub always returns passed.",
    }
