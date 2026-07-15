"""Visual Design Studio business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from investhome_api.models.design_studio import DesignProject, DesignStatus, DesignType, DesignVersion
from investhome_api.models.document import Document, DocumentType
from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingElement, DrawingElementType
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.design_studio import (
    CompatibleSourceDocument,
    DesignProjectResponse,
    DesignSourceRegion,
    DesignSourceRegionsResponse,
)

COMPATIBLE_DOCUMENT_TYPES = frozenset(
    {
        DocumentType.ARCHITECTURAL_DRAWING.value,
        DocumentType.CONSTRUCTION_DRAWING.value,
        DocumentType.PROJECT_DOCUMENT.value,
        DocumentType.MARKETING_MATERIAL.value,
    }
)

DEFAULT_PALETTE = [
    "#E8D5B7",
    "#C4B5A0",
    "#A8C5DA",
    "#B5D4C8",
    "#D4C5E8",
    "#F5E6D3",
    "#D9E4EC",
    "#E8C4C4",
]


def json_safe_parameters(parameters: dict) -> dict:
    """Recursively coerce values for JSON column storage (UUID, datetime, etc.)."""

    def _convert(value):
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: _convert(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_convert(item) for item in value]
        return value

    return _convert(parameters)


def _get_project_or_404(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_document_or_404(document_id: UUID, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def get_design_project_or_404(
    design_project_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> DesignProject:
    design_project = db.scalar(
        select(DesignProject)
        .options(joinedload(DesignProject.versions))
        .where(DesignProject.id == design_project_id)
    )
    if design_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design project not found")
    if design_project.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design project not found")
    return design_project


def _resolve_drawing_analysis(
    db: Session,
    document: Document,
    drawing_analysis_id: UUID | None,
) -> DrawingAnalysis | None:
    if drawing_analysis_id is not None:
        analysis = db.get(DrawingAnalysis, drawing_analysis_id)
        if analysis is None or analysis.document_id != document.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Drawing analysis does not match document",
            )
        return analysis

    return db.scalar(select(DrawingAnalysis).where(DrawingAnalysis.document_id == document.id))


def _geometry_version(analysis: DrawingAnalysis | None) -> str | None:
    if analysis is None:
        return None
    return str(analysis.document_version_id)


def build_design_project_response(
    design_project: DesignProject,
    db: Session,
) -> DesignProjectResponse:
    project = db.get(Project, design_project.project_id)
    document = db.get(Document, design_project.document_id)
    creator = db.get(User, design_project.created_by_user_id) if design_project.created_by_user_id else None
    reviewer = db.get(User, design_project.reviewed_by_user_id) if design_project.reviewed_by_user_id else None

    versions = sorted(design_project.versions, key=lambda v: v.version_number)
    current_version = versions[-1].version_number if versions else None

    return DesignProjectResponse(
        id=design_project.id,
        project_id=design_project.project_id,
        document_id=design_project.document_id,
        document_version_id=design_project.document_version_id,
        drawing_analysis_id=design_project.drawing_analysis_id,
        title=design_project.title,
        description=design_project.description,
        design_type=design_project.design_type,
        status=design_project.status,
        source_geometry_version=design_project.source_geometry_version,
        created_by_user_id=design_project.created_by_user_id,
        created_at=design_project.created_at,
        updated_at=design_project.updated_at,
        archived_at=design_project.archived_at,
        review_comment=design_project.review_comment,
        review_submitted_at=design_project.review_submitted_at,
        reviewed_by_user_id=design_project.reviewed_by_user_id,
        reviewed_at=design_project.reviewed_at,
        project_name=project.project_name if project else None,
        document_title=document.title if document else None,
        created_by_name=creator.full_name if creator else None,
        reviewed_by_name=reviewer.full_name if reviewer else None,
        current_version_number=current_version,
        version_count=len(versions),
    )


def list_design_projects(
    db: Session,
    *,
    search: str | None = None,
    project_id: UUID | None = None,
    design_type: DesignType | None = None,
    status_filter: DesignStatus | None = None,
    include_archived: bool = False,
) -> list[DesignProjectResponse]:
    query = (
        select(DesignProject)
        .options(joinedload(DesignProject.versions))
        .order_by(DesignProject.updated_at.desc())
    )

    if not include_archived:
        query = query.where(DesignProject.archived_at.is_(None))

    if project_id is not None:
        query = query.where(DesignProject.project_id == project_id)

    if design_type is not None:
        query = query.where(DesignProject.design_type == design_type)

    if status_filter is not None:
        query = query.where(DesignProject.status == status_filter)

    if search:
        pattern = f"%{search.strip()}%"
        project_ids = db.scalars(
            select(Project.id).where(Project.project_name.ilike(pattern))
        ).all()
        document_ids = db.scalars(
            select(Document.id).where(Document.title.ilike(pattern))
        ).all()
        conditions = [DesignProject.title.ilike(pattern)]
        if project_ids:
            conditions.append(DesignProject.project_id.in_(project_ids))
        if document_ids:
            conditions.append(DesignProject.document_id.in_(document_ids))
        query = query.where(or_(*conditions))

    projects = db.scalars(query).unique().all()
    return [build_design_project_response(item, db) for item in projects]


def list_compatible_source_documents(
    db: Session,
    project_id: UUID,
) -> list[CompatibleSourceDocument]:
    _get_project_or_404(project_id, db)

    documents = db.scalars(
        select(Document)
        .where(
            Document.archived_at.is_(None),
            Document.document_type.in_(tuple(COMPATIBLE_DOCUMENT_TYPES)),
            or_(
                Document.project_id == project_id,
                Document.project_id.is_(None),
            ),
        )
        .order_by(Document.updated_at.desc())
    ).all()

    items: list[CompatibleSourceDocument] = []
    for document in documents:
        analysis = db.scalar(
            select(DrawingAnalysis).where(DrawingAnalysis.document_id == document.id)
        )
        has_rooms = False
        if analysis is not None:
            room_count = db.scalar(
                select(func.count())
                .select_from(DrawingElement)
                .where(
                    DrawingElement.analysis_id == analysis.id,
                    DrawingElement.element_type == DrawingElementType.ROOM.value,
                )
            )
            has_rooms = bool(room_count and room_count > 0)

        items.append(
            CompatibleSourceDocument(
                id=document.id,
                title=document.title,
                document_type=document.document_type.value,
                document_version_id=document.id,
                drawing_analysis_id=analysis.id if analysis else None,
                preview_status=analysis.preview_status if analysis else None,
                has_room_regions=has_rooms,
            )
        )
    return items


def create_design_project(
    db: Session,
    *,
    project_id: UUID,
    document_id: UUID,
    document_version_id: UUID | None,
    drawing_analysis_id: UUID | None,
    title: str,
    description: str | None,
    design_type: DesignType,
    actor: User | None,
) -> DesignProject:
    _get_project_or_404(project_id, db)
    document = _get_document_or_404(document_id, db)

    if document.document_type.value not in COMPATIBLE_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type is not compatible with design studio",
        )

    analysis = _resolve_drawing_analysis(db, document, drawing_analysis_id)
    version_id = document_version_id or document.id

    design_project = DesignProject(
        project_id=project_id,
        document_id=document_id,
        document_version_id=version_id,
        drawing_analysis_id=analysis.id if analysis else None,
        title=title,
        description=description,
        design_type=design_type,
        status=DesignStatus.DRAFT,
        source_geometry_version=_geometry_version(analysis),
        created_by_user_id=actor.id if actor else None,
    )
    db.add(design_project)
    db.flush()
    return design_project


def get_source_regions(db: Session, design_project: DesignProject) -> DesignSourceRegionsResponse:
    if design_project.drawing_analysis_id is None:
        return DesignSourceRegionsResponse(mode="basic_overlay", regions=[])

    elements = db.scalars(
        select(DrawingElement)
        .where(
            DrawingElement.analysis_id == design_project.drawing_analysis_id,
            DrawingElement.element_type == DrawingElementType.ROOM.value,
        )
        .order_by(DrawingElement.label)
    ).all()

    if not elements:
        return DesignSourceRegionsResponse(mode="basic_overlay", regions=[])

    regions = [
        DesignSourceRegion(
            id=str(element.id),
            label=element.label,
            element_type=element.element_type,
            has_geometry=bool(element.geometry_json),
        )
        for element in elements
    ]
    return DesignSourceRegionsResponse(mode="room_regions", regions=regions)


def next_version_number(db: Session, design_project_id: UUID) -> int:
    current = db.scalar(
        select(func.max(DesignVersion.version_number)).where(
            DesignVersion.design_project_id == design_project_id
        )
    )
    return (current or 0) + 1


def save_design_version(
    db: Session,
    design_project: DesignProject,
    *,
    design_parameters: dict,
    source_geometry_version: str | None,
    actor: User | None,
) -> DesignVersion:
    version = DesignVersion(
        design_project_id=design_project.id,
        version_number=next_version_number(db, design_project.id),
        source_geometry_version=source_geometry_version or design_project.source_geometry_version,
        design_parameters=json_safe_parameters(design_parameters),
        created_by_user_id=actor.id if actor else None,
    )
    db.add(version)
    design_project.updated_at = datetime.now(UTC)
    db.flush()
    return version


def build_default_design_parameters(mode: str, regions: list[DesignSourceRegion]) -> dict:
    if mode == "room_regions" and regions:
        return {
            "mode": "room_regions",
            "palette": "default",
            "regions": [
                {"id": region.id, "label": region.label, "color": DEFAULT_PALETTE[idx % len(DEFAULT_PALETTE)]}
                for idx, region in enumerate(regions)
            ],
            "backgroundColor": "#FFFFFF",
        }
    return {
        "mode": "basic_overlay",
        "palette": "default",
        "regions": [],
        "backgroundColor": "#F5F0E8",
    }
