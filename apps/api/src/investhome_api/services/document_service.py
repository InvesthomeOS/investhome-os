"""Document business logic, permissions, and version management."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.config.documents_config import (
    RELATED_MODULE_ENTITY_TYPES,
    is_previewable,
)
from investhome_api.config.settings import get_settings
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentAnalysis,
    DocumentFileKind,
    DocumentLink,
    DocumentStatus,
    DocumentVisibility,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.document import (
    DocumentMetricValue,
    DocumentStorageFileItem,
    DocumentTypeCount,
    DocumentWorkspaceOverviewResponse,
)
from investhome_api.services.permission_service import is_super_admin, user_has_permission
from investhome_api.services.storage import get_storage_provider


def _auth_bypass() -> bool:
    return not get_settings().auth_enabled


def user_can_view_document(user: User, document: Document) -> bool:
    if _auth_bypass():
        return True
    if is_super_admin(user):
        return True
    if not user_has_permission(user, "documents", "view"):
        return False
    if document.visibility == DocumentVisibility.PRIVATE and (
        document.owner_user_id != user.id and document.uploaded_by_user_id != user.id
    ):
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
        conditions.append(
            Document.confidentiality_level == ConfidentialityLevel.HIGHLY_CONFIDENTIAL
        )
    return or_(*conditions)


def visibility_filter(user: User):
    """PRIVATE docs visible only to owner/uploader; TEAM/ORGANIZATION to viewers."""
    if _auth_bypass() or is_super_admin(user):
        return True
    return or_(
        Document.visibility != DocumentVisibility.PRIVATE,
        Document.owner_user_id == user.id,
        Document.uploaded_by_user_id == user.id,
    )


def _apply_access_filters(query, count_query, user: User):
    conf_filter = confidentiality_filter(user)
    if conf_filter is not True:
        query = query.where(conf_filter)
        count_query = count_query.where(conf_filter)
    vis_filter = visibility_filter(user)
    if vis_filter is not True:
        query = query.where(vis_filter)
        count_query = count_query.where(vis_filter)
    return query, count_query


def build_list_query(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    document_type: str | None = None,
    file_kind: str | None = None,
    folder: str | None = None,
    tags: str | None = None,
    visibility: str | None = None,
    category: str | None = None,
    project_id: UUID | None = None,
    investor_id: UUID | None = None,
    lead_id: UUID | None = None,
    transaction_id: UUID | None = None,
    company_id: UUID | None = None,
    campaign_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    uploaded_by_user_id: UUID | None = None,
    status_filter: str | None = None,
    confidentiality: str | None = None,
    without_relation: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    related_module: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    include_hidden: bool = True,
    include_archived: bool = False,
    latest_only: bool = True,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Document], int]:
    can_view = (
        _auth_bypass()
        or is_super_admin(user)
        or user_has_permission(user, "documents", "view")
    )
    if not can_view:
        return [], 0

    query = select(Document).options(selectinload(Document.links))
    count_query = select(func.count()).select_from(Document)
    query, count_query = _apply_access_filters(query, count_query, user)

    if not include_archived:
        query = query.where(Document.archived_at.is_(None))
        count_query = count_query.where(Document.archived_at.is_(None))

    if latest_only:
        query = query.where(Document.is_latest_version.is_(True))
        count_query = count_query.where(Document.is_latest_version.is_(True))

    if search:
        pattern = f"%{search.strip()}%"
        token = search.strip().lower()
        owner_match = select(User.id).where(User.full_name.ilike(pattern))
        parts = [
            Document.title.ilike(pattern),
            Document.original_file_name.ilike(pattern),
            Document.category.ilike(pattern),
            Document.description.ilike(pattern),
            Document.notes.ilike(pattern),
            Document.tags.ilike(pattern),
            Document.owner_user_id.in_(owner_match),
            Document.uploaded_by_user_id.in_(owner_match),
            Document.id.in_(
                select(DocumentLink.document_id).where(DocumentLink.entity_type.ilike(pattern))
            ),
        ]
        if token:
            parts.extend(
                [
                    Document.folder == token,
                    Document.file_kind == token,
                    Document.file_extension == token.lstrip("."),
                ]
            )
        search_cond = or_(*parts)
        query = query.where(search_cond)
        count_query = count_query.where(search_cond)

    if document_type:
        query = query.where(Document.document_type == document_type)
        count_query = count_query.where(Document.document_type == document_type)
    if file_kind:
        query = query.where(Document.file_kind == file_kind)
        count_query = count_query.where(Document.file_kind == file_kind)
    if folder:
        query = query.where(Document.folder == folder)
        count_query = count_query.where(Document.folder == folder)
    if tags:
        tag_pattern = f"%{tags.strip()}%"
        query = query.where(Document.tags.ilike(tag_pattern))
        count_query = count_query.where(Document.tags.ilike(tag_pattern))
    if visibility:
        query = query.where(Document.visibility == visibility)
        count_query = count_query.where(Document.visibility == visibility)
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
    if company_id:
        query = query.where(Document.company_id == company_id)
        count_query = count_query.where(Document.company_id == company_id)
    if owner_user_id:
        query = query.where(Document.owner_user_id == owner_user_id)
        count_query = count_query.where(Document.owner_user_id == owner_user_id)
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
    if created_from:
        created_from_dt = (
            created_from
            if isinstance(created_from, datetime)
            else datetime.combine(created_from, datetime.min.time(), tzinfo=UTC)
        )
        query = query.where(Document.created_at >= created_from_dt)
        count_query = count_query.where(Document.created_at >= created_from_dt)
    if created_to:
        created_to_dt = (
            created_to
            if isinstance(created_to, datetime)
            else datetime.combine(created_to, datetime.max.time(), tzinfo=UTC)
        )
        query = query.where(Document.created_at <= created_to_dt)
        count_query = count_query.where(Document.created_at <= created_to_dt)

    if related_module:
        module_key = related_module.strip().lower()
        entity_types = RELATED_MODULE_ENTITY_TYPES.get(module_key)
        if entity_types:
            link_subq = select(DocumentLink.document_id).where(
                DocumentLink.entity_type.in_(tuple(entity_types))
            )
            direct_conds = []
            if module_key == "project":
                direct_conds.append(Document.project_id.is_not(None))
            elif module_key == "investor":
                direct_conds.append(Document.investor_id.is_not(None))
            elif module_key == "lead":
                direct_conds.append(Document.lead_id.is_not(None))
            elif module_key == "financial_record":
                direct_conds.append(Document.transaction_id.is_not(None))
            elif module_key == "company":
                direct_conds.append(Document.company_id.is_not(None))
            if direct_conds:
                module_cond = or_(Document.id.in_(link_subq), *direct_conds)
            else:
                module_cond = Document.id.in_(link_subq)
            query = query.where(module_cond)
            count_query = count_query.where(module_cond)

    if campaign_id:
        campaign_types = ("campaign", "marketing_campaign")
        link_subq = select(DocumentLink.document_id).where(
            DocumentLink.entity_type.in_(campaign_types),
            DocumentLink.entity_id == campaign_id,
        )
        query = query.where(Document.id.in_(link_subq))
        count_query = count_query.where(Document.id.in_(link_subq))

    if without_relation is True:
        has_link = exists(select(DocumentLink.id).where(DocumentLink.document_id == Document.id))
        no_direct = and_(
            Document.project_id.is_(None),
            Document.investor_id.is_(None),
            Document.lead_id.is_(None),
            Document.transaction_id.is_(None),
        )
        query = query.where(no_direct, ~has_link)
        count_query = count_query.where(no_direct, ~has_link)

    if entity_type and entity_id:
        link_entity_types = [entity_type]
        if entity_type == "campaign":
            link_entity_types.append("marketing_campaign")
        elif entity_type == "marketing_campaign":
            link_entity_types.append("campaign")
        link_filters = [
            DocumentLink.entity_type.in_(link_entity_types),
            DocumentLink.entity_id == entity_id,
        ]
        if not include_hidden:
            link_filters.append(DocumentLink.hidden_from_view.is_(False))
        link_subq = select(DocumentLink.document_id).where(*link_filters)
        direct_conds = []
        if entity_type == "project":
            direct_conds.append(Document.project_id == entity_id)
        elif entity_type == "investor":
            direct_conds.append(Document.investor_id == entity_id)
        elif entity_type == "lead":
            direct_conds.append(Document.lead_id == entity_id)
        elif entity_type == "transaction":
            direct_conds.append(Document.transaction_id == entity_id)
        elif entity_type == "company":
            direct_conds.append(Document.company_id == entity_id)
        if direct_conds:
            entity_cond = or_(Document.id.in_(link_subq), *direct_conds)
        else:
            entity_cond = Document.id.in_(link_subq)
        query = query.where(entity_cond)
        count_query = count_query.where(entity_cond)

    sort_column = {
        "title": Document.title,
        "document_type": Document.document_type,
        "file_kind": Document.file_kind,
        "folder": Document.folder,
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


def restore_document_version(
    db: Session,
    *,
    latest: Document,
    target: Document,
    actor: User,
    version_notes: str | None = None,
) -> Document:
    """Create a new latest version by copying bytes from a previous version in the chain."""
    if target.id == latest.id and latest.is_latest_version:
        return latest

    storage = get_storage_provider()
    try:
        stream = storage.open(target.storage_key)
        content = stream.read()
        stream.close()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        ) from exc

    from investhome_api.config.documents_config import infer_file_kind, initial_processing_status
    from investhome_api.services.document_validation import (
        compute_checksum,
        content_stream,
        generate_storage_key,
    )
    from investhome_api.services.storage import provider_enum

    mark_previous_versions_superseded(db, latest)
    stored_name, storage_key = generate_storage_key(target.file_extension)
    storage.save(storage_key, content_stream(content), content_length=len(content))
    file_kind = getattr(target, "file_kind", None) or infer_file_kind(target.file_extension)

    new_version = Document(
        title=latest.title,
        original_file_name=target.original_file_name,
        stored_file_name=stored_name,
        file_extension=target.file_extension,
        mime_type=target.mime_type,
        file_size=len(content),
        storage_provider=provider_enum(),
        storage_key=storage_key,
        checksum=compute_checksum(content),
        document_type=latest.document_type,
        category=latest.category,
        folder=latest.folder,
        file_kind=file_kind,
        status=DocumentStatus.ACTIVE,
        visibility=latest.visibility,
        confidentiality_level=latest.confidentiality_level,
        version_number=latest.version_number + 1,
        parent_document_id=latest.id,
        uploaded_by_user_id=actor.id,
        owner_user_id=getattr(latest, "owner_user_id", None) or actor.id,
        company_id=getattr(latest, "company_id", None),
        project_id=latest.project_id,
        investor_id=latest.investor_id,
        lead_id=latest.lead_id,
        transaction_id=latest.transaction_id,
        description=latest.description,
        notes=getattr(latest, "notes", None),
        tags=latest.tags,
        document_date=latest.document_date,
        expiration_date=latest.expiration_date,
        is_latest_version=True,
        processing_status=initial_processing_status(target.file_extension),
        version_notes=version_notes
        or f"Restored from version {target.version_number}",
        download_count=0,
        preview_count=0,
        is_demo=latest.is_demo,
    )
    db.add(new_version)
    db.flush()
    create_document_analysis(db, new_version.id)

    # Re-attach links from latest onto the restored version
    for link in list(latest.links or []):
        db.add(
            DocumentLink(
                document_id=new_version.id,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                relationship_type=link.relationship_type,
            )
        )
    return new_version


def _active_base_filters(user: User):
    conf = confidentiality_filter(user)
    vis = visibility_filter(user)
    return conf, vis


def build_workspace_overview(db: Session, user: User) -> DocumentWorkspaceOverviewResponse:
    can_view = (
        _auth_bypass()
        or is_super_admin(user)
        or user_has_permission(user, "documents", "view")
    )
    if not can_view:
        denied = DocumentMetricValue(
            value=None,
            available=False,
            reason="permission_restricted",
        )
        return DocumentWorkspaceOverviewResponse(
            total=denied,
            storage_used_bytes=denied,
            recent_uploads=denied,
            most_viewed=denied,
            archived=denied,
            without_relation=denied,
            most_used_types=[],
            documents_by_type=[],
            largest_files=[],
            most_viewed_files=[],
        )

    active_count_q = select(func.count()).select_from(Document).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_(None),
    )
    dummy = select(Document)
    dummy, active_count_q = _apply_access_filters(dummy, active_count_q, user)
    total = db.scalar(active_count_q) or 0

    storage_q = select(func.coalesce(func.sum(Document.file_size), 0)).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_(None),
    )
    dummy_s = select(Document)
    dummy_s, storage_q = _apply_access_filters(dummy_s, storage_q, user)
    storage_used = int(db.scalar(storage_q) or 0)

    recent_since = datetime.now(UTC) - timedelta(days=7)
    recent_q = active_count_q.where(Document.created_at >= recent_since)
    recent = db.scalar(recent_q) or 0

    archived_count_q = select(func.count()).select_from(Document).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_not(None),
    )
    dummy_a = select(Document)
    dummy_a, archived_count_q = _apply_access_filters(dummy_a, archived_count_q, user)
    archived = db.scalar(archived_count_q) or 0

    has_link = exists(select(DocumentLink.id).where(DocumentLink.document_id == Document.id))
    without_q = select(func.count()).select_from(Document).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_(None),
        Document.project_id.is_(None),
        Document.investor_id.is_(None),
        Document.lead_id.is_(None),
        Document.transaction_id.is_(None),
        ~has_link,
    )
    dummy_w = select(Document)
    dummy_w, without_q = _apply_access_filters(dummy_w, without_q, user)
    without_relation = db.scalar(without_q) or 0

    conf, vis = _active_base_filters(user)
    type_q = (
        select(Document.file_kind, func.count())
        .where(Document.is_latest_version.is_(True), Document.archived_at.is_(None))
        .group_by(Document.file_kind)
        .order_by(func.count().desc())
        .limit(12)
    )
    if conf is not True:
        type_q = type_q.where(conf)
    if vis is not True:
        type_q = type_q.where(vis)
    type_rows = db.execute(type_q).all()

    most_used: list[DocumentTypeCount] = []
    for row in type_rows:
        kind = row[0] if isinstance(row[0], DocumentFileKind) else DocumentFileKind(str(row[0]))
        most_used.append(DocumentTypeCount(file_kind=kind, count=int(row[1])))

    largest_q = (
        select(Document)
        .where(Document.is_latest_version.is_(True), Document.archived_at.is_(None))
        .order_by(Document.file_size.desc())
        .limit(5)
    )
    if conf is not True:
        largest_q = largest_q.where(conf)
    if vis is not True:
        largest_q = largest_q.where(vis)
    largest_docs = list(db.scalars(largest_q).all())
    largest_files = [
        DocumentStorageFileItem(
            id=doc.id,
            title=doc.title,
            file_size=doc.file_size,
            file_kind=doc.file_kind
            if isinstance(doc.file_kind, DocumentFileKind)
            else DocumentFileKind(str(doc.file_kind)),
            preview_count=int(getattr(doc, "preview_count", 0) or 0),
            download_count=int(getattr(doc, "download_count", 0) or 0),
        )
        for doc in largest_docs
    ]

    views_expr = func.coalesce(Document.preview_count, 0) + func.coalesce(
        Document.download_count, 0
    )
    viewed_total_q = select(func.coalesce(func.sum(views_expr), 0)).where(
        Document.is_latest_version.is_(True),
        Document.archived_at.is_(None),
    )
    dummy_v = select(Document)
    dummy_v, viewed_total_q = _apply_access_filters(dummy_v, viewed_total_q, user)
    viewed_total = int(db.scalar(viewed_total_q) or 0)

    most_viewed_q = (
        select(Document)
        .where(
            Document.is_latest_version.is_(True),
            Document.archived_at.is_(None),
            views_expr > 0,
        )
        .order_by(views_expr.desc(), Document.updated_at.desc())
        .limit(5)
    )
    if conf is not True:
        most_viewed_q = most_viewed_q.where(conf)
    if vis is not True:
        most_viewed_q = most_viewed_q.where(vis)
    most_viewed_docs = list(db.scalars(most_viewed_q).all())
    most_viewed_files = [
        DocumentStorageFileItem(
            id=doc.id,
            title=doc.title,
            file_size=doc.file_size,
            file_kind=doc.file_kind
            if isinstance(doc.file_kind, DocumentFileKind)
            else DocumentFileKind(str(doc.file_kind)),
            preview_count=int(getattr(doc, "preview_count", 0) or 0),
            download_count=int(getattr(doc, "download_count", 0) or 0),
        )
        for doc in most_viewed_docs
    ]

    most_viewed_metric = (
        DocumentMetricValue(value=viewed_total, available=True)
        if viewed_total > 0 or most_viewed_files
        else DocumentMetricValue(
            value=None,
            available=False,
            reason="no_view_data",
        )
    )

    return DocumentWorkspaceOverviewResponse(
        total=DocumentMetricValue(value=total, available=True),
        storage_used_bytes=DocumentMetricValue(value=storage_used, available=True),
        recent_uploads=DocumentMetricValue(value=recent, available=True),
        most_viewed=most_viewed_metric,
        archived=DocumentMetricValue(value=archived, available=True),
        without_relation=DocumentMetricValue(value=without_relation, available=True),
        most_used_types=most_used,
        documents_by_type=most_used,
        largest_files=largest_files,
        most_viewed_files=most_viewed_files,
    )


def export_documents_metadata_csv(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    document_type: str | None = None,
    file_kind: str | None = None,
    folder: str | None = None,
    include_archived: bool = False,
) -> tuple[str, int]:
    items, _total = build_list_query(
        db,
        user,
        search=search,
        document_type=document_type,
        file_kind=file_kind,
        folder=folder,
        include_archived=include_archived,
        page=1,
        page_size=5000,
        latest_only=True,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "title",
            "original_file_name",
            "file_extension",
            "mime_type",
            "file_size",
            "document_type",
            "file_kind",
            "folder",
            "status",
            "visibility",
            "confidentiality_level",
            "tags",
            "owner_user_id",
            "uploaded_by_user_id",
            "company_id",
            "project_id",
            "investor_id",
            "lead_id",
            "created_at",
            "updated_at",
            "archived_at",
        ]
    )
    for doc in items:
        writer.writerow(
            [
                str(doc.id),
                doc.title,
                doc.original_file_name,
                doc.file_extension,
                doc.mime_type,
                doc.file_size,
                getattr(doc.document_type, "value", doc.document_type),
                getattr(doc.file_kind, "value", doc.file_kind),
                getattr(doc.folder, "value", doc.folder),
                getattr(doc.status, "value", doc.status),
                getattr(doc.visibility, "value", doc.visibility),
                doc.confidentiality_level.value
                if hasattr(doc.confidentiality_level, "value")
                else doc.confidentiality_level,
                doc.tags or "",
                str(doc.owner_user_id) if doc.owner_user_id else "",
                str(doc.uploaded_by_user_id) if doc.uploaded_by_user_id else "",
                str(doc.company_id) if doc.company_id else "",
                str(doc.project_id) if doc.project_id else "",
                str(doc.investor_id) if doc.investor_id else "",
                str(doc.lead_id) if doc.lead_id else "",
                doc.created_at.isoformat() if doc.created_at else "",
                doc.updated_at.isoformat() if doc.updated_at else "",
                doc.archived_at.isoformat() if doc.archived_at else "",
            ]
        )
    return buffer.getvalue(), len(items)


def _document_bitrix_file_id(document: Document) -> str | None:
    tags = str(getattr(document, "tags", None) or "")
    marker = "bitrix_file:"
    if marker in tags:
        return tags.split(marker, 1)[1].split(",")[0].strip() or None
    raw = getattr(document, "notes", None)
    if isinstance(raw, dict):
        value = str(raw.get("bitrix_file_id") or "").strip()
        return value or None
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            value = str(parsed.get("bitrix_file_id") or "").strip()
            return value or None
    return None


def enrich_response(
    document: Document,
    *,
    uploader_name: str | None = None,
    owner_name: str | None = None,
    related_label: str | None = None,
) -> dict:
    folder = getattr(document, "folder", None)
    file_kind = getattr(document, "file_kind", None)
    visibility = getattr(document, "visibility", None)
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
        "folder": getattr(folder, "value", folder or "general"),
        "file_kind": getattr(file_kind, "value", file_kind or "other"),
        "status": document.status,
        "visibility": getattr(visibility, "value", visibility or "organization"),
        "confidentiality_level": document.confidentiality_level,
        "version_number": document.version_number,
        "parent_document_id": document.parent_document_id,
        "uploaded_by_user_id": document.uploaded_by_user_id,
        "uploaded_by_name": uploader_name,
        "owner_user_id": getattr(document, "owner_user_id", None),
        "owner_name": owner_name or uploader_name,
        "company_id": getattr(document, "company_id", None),
        "project_id": document.project_id,
        "investor_id": document.investor_id,
        "lead_id": document.lead_id,
        "transaction_id": document.transaction_id,
        "description": document.description,
        "notes": getattr(document, "notes", None),
        "tags": document.tags,
        "document_date": document.document_date,
        "expiration_date": document.expiration_date,
        "is_latest_version": document.is_latest_version,
        "processing_status": document.processing_status,
        "version_notes": document.version_notes,
        "download_count": int(getattr(document, "download_count", 0) or 0),
        "preview_count": int(getattr(document, "preview_count", 0) or 0),
        "is_previewable": is_previewable(document.file_extension),
        "hidden_from_view": any(getattr(link, "hidden_from_view", False) for link in (document.links or [])),
        "bitrix_file_id": _document_bitrix_file_id(document),
        "related_record_label": related_label,
        "is_demo": document.is_demo,
        "archived_at": document.archived_at,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "links": document.links if document.links else [],
    }
    return data
