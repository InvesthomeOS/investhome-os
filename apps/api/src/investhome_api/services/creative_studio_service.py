"""Creative Studio business logic — projects, documents, drafts, versions."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from investhome_api.models.creative_studio import (
    CreativeStudioDocument,
    CreativeStudioDocumentStatus,
    CreativeStudioDocumentType,
    CreativeStudioDocumentVersion,
    CreativeStudioProject,
    CreativeStudioProjectStatus,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_studio import (
    CreativeStudioDocumentResponse,
    CreativeStudioProjectResponse,
    CreativeStudioVersionResponse,
)


def _json_safe(value: Any) -> Any:
    """Recursively coerce values for JSON column storage."""

    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def get_project_or_404(
    project_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> CreativeStudioProject:
    project = db.get(CreativeStudioProject, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creative Studio project not found")
    if project.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creative Studio project not found")
    return project


def get_document_or_404(
    document_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> CreativeStudioDocument:
    document = db.scalar(
        select(CreativeStudioDocument)
        .options(joinedload(CreativeStudioDocument.versions))
        .where(CreativeStudioDocument.id == document_id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creative Studio document not found")
    if document.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creative Studio document not found")
    return document


def build_project_response(project: CreativeStudioProject, db: Session) -> CreativeStudioProjectResponse:
    count = db.scalar(
        select(func.count())
        .select_from(CreativeStudioDocument)
        .where(
            CreativeStudioDocument.project_id == project.id,
            CreativeStudioDocument.archived_at.is_(None),
        )
    ) or 0
    return CreativeStudioProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        company_id=project.company_id,
        linked_project_id=project.linked_project_id,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archived_at=project.archived_at,
        document_count=count,
    )


def build_document_response(
    document: CreativeStudioDocument,
    *,
    include_draft: bool = True,
) -> CreativeStudioDocumentResponse:
    versions = getattr(document, "versions", None) or []
    return CreativeStudioDocumentResponse(
        id=document.id,
        project_id=document.project_id,
        title=document.title,
        description=document.description,
        document_type=document.document_type,
        status=document.status,
        language=document.language,
        thumbnail_url=document.thumbnail_url,
        draft_body_json=document.draft_body_json if include_draft else None,
        draft_updated_at=document.draft_updated_at,
        draft_updated_by_user_id=document.draft_updated_by_user_id,
        current_version_id=document.current_version_id,
        created_by_user_id=document.created_by_user_id,
        updated_by_user_id=document.updated_by_user_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        archived_at=document.archived_at,
        version_count=len(versions),
    )


def build_version_response(
    version: CreativeStudioDocumentVersion,
    *,
    include_body: bool = True,
) -> CreativeStudioVersionResponse:
    return CreativeStudioVersionResponse(
        id=version.id,
        document_id=version.document_id,
        version_number=version.version_number,
        label=version.label,
        summary=version.summary,
        body_json=version.body_json if include_body else None,
        created_by_user_id=version.created_by_user_id,
        created_at=version.created_at,
    )


def create_project(
    db: Session,
    *,
    name: str,
    description: str | None,
    status: CreativeStudioProjectStatus,
    company_id: UUID | None,
    linked_project_id: UUID | None,
    actor: User,
) -> CreativeStudioProject:
    if linked_project_id is not None:
        linked = db.get(Project, linked_project_id)
        if linked is None or linked.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked project not found")

    project = CreativeStudioProject(
        name=name.strip(),
        description=description,
        status=status,
        company_id=company_id,
        linked_project_id=linked_project_id,
        owner_id=actor.id,
    )
    db.add(project)
    db.flush()
    return project


def list_projects(
    db: Session,
    *,
    include_archived: bool = False,
) -> list[CreativeStudioProjectResponse]:
    query = select(CreativeStudioProject).order_by(CreativeStudioProject.updated_at.desc())
    if not include_archived:
        query = query.where(CreativeStudioProject.archived_at.is_(None))
    projects = db.scalars(query).all()
    return [build_project_response(item, db) for item in projects]


def create_document(
    db: Session,
    *,
    project: CreativeStudioProject,
    title: str,
    description: str | None,
    document_type: CreativeStudioDocumentType,
    status: CreativeStudioDocumentStatus,
    language: str | None,
    thumbnail_url: str | None,
    draft_body_json: dict[str, Any] | None,
    actor: User,
) -> CreativeStudioDocument:
    now = datetime.now(UTC)
    body = _json_safe(draft_body_json) if draft_body_json is not None else {}
    document = CreativeStudioDocument(
        project_id=project.id,
        title=title.strip(),
        description=description,
        document_type=document_type,
        status=status,
        language=language,
        thumbnail_url=thumbnail_url,
        draft_body_json=body,
        draft_updated_at=now,
        draft_updated_by_user_id=actor.id,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(document)
    db.flush()
    return document


def list_documents(
    db: Session,
    *,
    project_id: UUID,
    include_archived: bool = False,
) -> list[CreativeStudioDocumentResponse]:
    query = (
        select(CreativeStudioDocument)
        .options(joinedload(CreativeStudioDocument.versions))
        .where(CreativeStudioDocument.project_id == project_id)
        .order_by(CreativeStudioDocument.updated_at.desc())
    )
    if not include_archived:
        query = query.where(CreativeStudioDocument.archived_at.is_(None))
    documents = db.scalars(query).unique().all()
    return [build_document_response(item) for item in documents]


def save_draft(
    db: Session,
    document: CreativeStudioDocument,
    *,
    draft_body_json: dict[str, Any],
    actor: User,
) -> CreativeStudioDocument:
    """Update working draft only — does not create a version."""
    now = datetime.now(UTC)
    document.draft_body_json = _json_safe(draft_body_json)
    document.draft_updated_at = now
    document.draft_updated_by_user_id = actor.id
    document.updated_by_user_id = actor.id
    document.updated_at = now
    db.flush()
    return document


def _next_version_number(db: Session, document_id: UUID) -> int:
    latest = db.scalar(
        select(func.max(CreativeStudioDocumentVersion.version_number)).where(
            CreativeStudioDocumentVersion.document_id == document_id
        )
    )
    return (latest or 0) + 1


def create_version(
    db: Session,
    document: CreativeStudioDocument,
    *,
    body_json: dict[str, Any] | None,
    label: str | None,
    summary: str | None,
    actor: User,
) -> CreativeStudioDocumentVersion:
    """Snapshot draft (or provided body) into a new append-only version."""
    if body_json is not None:
        snapshot = _json_safe(body_json)
    else:
        snapshot = copy.deepcopy(document.draft_body_json) if document.draft_body_json is not None else {}

    version = CreativeStudioDocumentVersion(
        document_id=document.id,
        version_number=_next_version_number(db, document.id),
        label=label,
        summary=summary,
        body_json=snapshot,
        created_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()

    now = datetime.now(UTC)
    document.current_version_id = version.id
    document.updated_by_user_id = actor.id
    document.updated_at = now
    db.flush()
    return version


def list_versions(
    db: Session,
    document_id: UUID,
    *,
    include_body: bool = False,
) -> list[CreativeStudioVersionResponse]:
    versions = db.scalars(
        select(CreativeStudioDocumentVersion)
        .where(CreativeStudioDocumentVersion.document_id == document_id)
        .order_by(CreativeStudioDocumentVersion.version_number.desc())
    ).all()
    return [build_version_response(v, include_body=include_body) for v in versions]


def restore_version(
    db: Session,
    document: CreativeStudioDocument,
    version_id: UUID,
    *,
    create_version_flag: bool = True,
    label: str | None = None,
    summary: str | None = None,
    actor: User,
) -> tuple[CreativeStudioDocument, CreativeStudioDocumentVersion | None]:
    """Copy version body into draft. Never mutates old version rows.

    Optionally appends a NEW version from the restored content (default True).
    """
    target = db.get(CreativeStudioDocumentVersion, version_id)
    if target is None or target.document_id != document.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    restored_body = copy.deepcopy(target.body_json) if target.body_json is not None else {}
    now = datetime.now(UTC)
    document.draft_body_json = restored_body
    document.draft_updated_at = now
    document.draft_updated_by_user_id = actor.id
    document.updated_by_user_id = actor.id
    document.updated_at = now
    db.flush()

    new_version: CreativeStudioDocumentVersion | None = None
    if create_version_flag:
        new_version = create_version(
            db,
            document,
            body_json=restored_body,
            label=label or f"Restored from v{target.version_number}",
            summary=summary or f"Restored from version {target.version_number}",
            actor=actor,
        )
    return document, new_version
