"""Document business logic, permissions, and version management."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.config.documents_config import is_previewable
from investhome_api.config.settings import get_settings
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentAnalysis,
    DocumentLink,
    DocumentStatus,
    ProcessingStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.permission_service import is_super_admin, user_has_permission


def _auth_bypass() -> bool:
    return not get_settings().auth_enabled


def user_can_view_document(user: User, document: Document) -> bool:
    if _auth_bypass():
        return True
    if is_super_admin(user):
        return True
    if not user_has_permission(user, "documents", "view"):
        return False
    if document.confidentiality_level == ConfidentialityLevel.HIGHLY_CONFIDENTIAL:
        return user_has_permission(user, "documents", "view_highly_confidential")
    if document.confidentiality_level == ConfidentialityLevel.CONFIDENTIAL:
        return user_has_permission(user, "documents", "view_confidential")
    return True


def user_can_download_document(user: User, document: Document) -> bool:
    if not user_can_view_document(user, document):
        return False
    if _auth_bypass() or is_super_admin(user):
        return True
    return user_has_permission(user, "documents", "download")


def user_can_view_analysis(user: User, document: Document) -> bool:
    if not user_can_view_document(user, document):
        return False
    if _auth_bypass() or is_super_admin(user):
        return True
    if document.confidentiality_level in {
        ConfidentialityLevel.CONFIDENTIAL,
        ConfidentialityLevel.HIGHLY_CONFIDENTIAL,
    }:
        return user_has_permission(user, "documents", "view_sensitive_analysis")
    return user_has_permission(user, "documents", "view_analysis")


def user_can_reprocess_document(user: User, document: Document) -> bool:
    if not user_can_view_document(user, document):
        return False
    if _auth_bypass() or is_super_admin(user):
        return True
    return user_has_permission(user, "documents", "reprocess")


def user_can_ask_document(user: User, document: Document) -> bool:
    if not user_can_view_analysis(user, document):
        return False
    if _auth_bypass() or is_super_admin(user):
        return True
    return user_has_permission(user, "documents", "ask")


def user_can_export_analysis(user: User, document: Document) -> bool:
    if not user_can_view_analysis(user, document):
        return False
    if _auth_bypass() or is_super_admin(user):
        return True
    return user_has_permission(user, "documents", "export_analysis")


def _require_view(user: User, document: Document) -> None:
    if not user_can_view_document(user, document):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


def _require_download(user: User, document: Document) -> None:
    if not user_can_download_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Download not permitted")


def get_document_or_404(
    db: Session,
    document_id: UUID,
    user: User,
    *,
    include_archived: bool = False,
) -> Document:
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.links), selectinload(Document.analysis))
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    _require_view(user, document)
    return document


def get_root_document_id(document: Document, db: Session) -> UUID:
    current = document
    seen: set[UUID] = set()
    while current.parent_document_id and current.parent_document_id not in seen:
        seen.add(current.id)
        parent = db.get(Document, current.parent_document_id)
        if parent is None:
            break
        current = parent
    return current.id


def get_version_chain(db: Session, document: Document) -> list[Document]:
    root_id = get_root_document_id(document, db)
    root = db.get(Document, root_id)
    if root is None:
        return [document]

    versions: list[Document] = [root]
    pending = [root_id]
    while pending:
        pid = pending.pop(0)
        children = list(
            db.scalars(select(Document).where(Document.parent_document_id == pid)).all()
        )
        for child in children:
            versions.append(child)
            pending.append(child.id)

    versions.sort(key=lambda d: d.version_number)
    return versions


def confidentiality_filter(user: User):
    """SQLAlchemy filter for documents user can see."""
    if _auth_bypass() or is_super_admin(user):
        return True
    if not user_has_permission(user, "documents", "view"):
        return False
    conditions = [
        Document.confidentiality_level == ConfidentialityLevel.PUBLIC,
        Document.confidentiality_level == ConfidentialityLevel.INTERNAL,
    ]
    if user_has_permission(user, "documents", "view_confidential"):
        conditions.append(Document.confidentiality_level == ConfidentialityLevel.CONFIDENTIAL)
    if user_has_permission(user, "documents", "view_highly_confidential"):
        conditions.append(Document.confidentiality_level == ConfidentialityLevel.HIGHLY_CONFIDENTIAL)
    return or_(*conditions)


def build_list_query(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    document_type: str | None = None,
    category: str | None = None,
    project_id: UUID | None = None,
    investor_id: UUID | None = None,
    lead_id: UUID | None = None,
    transaction_id: UUID | None = None,
    uploaded_by_user_id: UUID | None = None,
    status_filter: str | None = None,
    confidentiality: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    include_archived: bool = False,
    latest_only: bool = True,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Document], int]:
    if not _auth_bypass() and not is_super_admin(user) and not user_has_permission(user, "documents", "view"):
        return [], 0

    query = select(Document).options(selectinload(Document.links))
    count_query = select(func.count()).select_from(Document)

    conf_filter = confidentiality_filter(user)
    if conf_filter is not True:
        query = query.where(conf_filter)
        count_query = count_query.where(conf_filter)

    if not include_archived:
        query = query.where(Document.archived_at.is_(None))
        count_query = count_query.where(Document.archived_at.is_(None))

    if latest_only:
        query = query.where(Document.is_latest_version.is_(True))
        count_query = count_query.where(Document.is_latest_version.is_(True))

    if search:
        pattern = f"%{search.strip()}%"
        search_cond = or_(
            Document.title.ilike(pattern),
            Document.original_file_name.ilike(pattern),
            Document.category.ilike(pattern),
            Document.description.ilike(pattern),
            Document.tags.ilike(pattern),
        )
        query = query.where(search_cond)
        count_query = count_query.where(search_cond)

    if document_type:
        query = query.where(Document.document_type == document_type)
        count_query = count_query.where(Document.document_type == document_type)
    if category:
        query = query.where(Document.category.ilike(f"%{category.strip()}%"))
        count_query = count_query.where(Document.category.ilike(f"%{category.strip()}%"))
    if project_id:
        query = query.where(Document.project_id == project_id)
        count_query = count_query.where(Document.project_id == project_id)
    if investor_id:
        query = query.where(Document.investor_id == investor_id)
        count_query = count_query.where(Document.investor_id == investor_id)
    if lead_id:
        query = query.where(Document.lead_id == lead_id)
        count_query = count_query.where(Document.lead_id == lead_id)
    if transaction_id:
        query = query.where(Document.transaction_id == transaction_id)
        count_query = count_query.where(Document.transaction_id == transaction_id)
    if uploaded_by_user_id:
        query = query.where(Document.uploaded_by_user_id == uploaded_by_user_id)
        count_query = count_query.where(Document.uploaded_by_user_id == uploaded_by_user_id)
    if status_filter:
        query = query.where(Document.status == status_filter)
        count_query = count_query.where(Document.status == status_filter)
    if confidentiality:
        query = query.where(Document.confidentiality_level == confidentiality)
        count_query = count_query.where(Document.confidentiality_level == confidentiality)
    if date_from:
        date_val = date_from.date() if hasattr(date_from, "date") else date_from
        query = query.where(Document.document_date >= date_val)
        count_query = count_query.where(Document.document_date >= date_val)
    if date_to:
        date_val = date_to.date() if hasattr(date_to, "date") else date_to
        query = query.where(Document.document_date <= date_val)
        count_query = count_query.where(Document.document_date <= date_val)

    if entity_type and entity_id:
        link_subq = select(DocumentLink.document_id).where(
            DocumentLink.entity_type == entity_type,
            DocumentLink.entity_id == entity_id,
        )
        direct_conds = []
        if entity_type == "project":
            direct_conds.append(Document.project_id == entity_id)
        elif entity_type == "investor":
            direct_conds.append(Document.investor_id == entity_id)
        elif entity_type == "lead":
            direct_conds.append(Document.lead_id == entity_id)
        elif entity_type == "transaction":
            direct_conds.append(Document.transaction_id == entity_id)
        entity_cond = or_(Document.id.in_(link_subq), *direct_conds) if direct_conds else Document.id.in_(link_subq)
        query = query.where(entity_cond)
        count_query = count_query.where(entity_cond)

    sort_column = {
        "title": Document.title,
        "document_type": Document.document_type,
        "status": Document.status,
        "file_size": Document.file_size,
        "document_date": Document.document_date,
        "updated_at": Document.updated_at,
        "created_at": Document.created_at,
        "version_number": Document.version_number,
    }.get(sort_by, Document.updated_at)

    if sort_dir == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = db.scalar(count_query) or 0
    offset = max(0, (page - 1) * page_size)
    items = list(db.scalars(query.offset(offset).limit(page_size)).all())
    return items, total


def create_document_analysis(db: Session, document_id: UUID) -> DocumentAnalysis:
    analysis = DocumentAnalysis(
        document_id=document_id,
        document_version_id=document_id,
        classification_status="pending",
    )
    db.add(analysis)
    return analysis


def mark_previous_versions_superseded(db: Session, previous_latest: Document) -> None:
    previous_latest.is_latest_version = False
    if previous_latest.status == DocumentStatus.ACTIVE:
        previous_latest.status = DocumentStatus.SUPERSEDED


def archive_document(db: Session, document: Document) -> None:
    document.archived_at = datetime.now(UTC)
    document.status = DocumentStatus.ARCHIVED


def restore_document(db: Session, document: Document) -> None:
    document.archived_at = None
    if document.status == DocumentStatus.ARCHIVED:
        document.status = DocumentStatus.ACTIVE


def enrich_response(document: Document, *, uploader_name: str | None = None, related_label: str | None = None) -> dict:
    data = {
        "id": document.id,
        "title": document.title,
        "original_file_name": document.original_file_name,
        "stored_file_name": document.stored_file_name,
        "file_extension": document.file_extension,
        "mime_type": document.mime_type,
        "file_size": document.file_size,
        "storage_provider": document.storage_provider,
        "checksum": document.checksum,
        "document_type": document.document_type,
        "category": document.category,
        "status": document.status,
        "confidentiality_level": document.confidentiality_level,
        "version_number": document.version_number,
        "parent_document_id": document.parent_document_id,
        "uploaded_by_user_id": document.uploaded_by_user_id,
        "uploaded_by_name": uploader_name,
        "project_id": document.project_id,
        "investor_id": document.investor_id,
        "lead_id": document.lead_id,
        "transaction_id": document.transaction_id,
        "description": document.description,
        "tags": document.tags,
        "document_date": document.document_date,
        "expiration_date": document.expiration_date,
        "is_latest_version": document.is_latest_version,
        "processing_status": document.processing_status,
        "version_notes": document.version_notes,
        "is_previewable": is_previewable(document.file_extension),
        "related_record_label": related_label,
        "is_demo": document.is_demo,
        "archived_at": document.archived_at,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "links": document.links if document.links else [],
    }
    return data
