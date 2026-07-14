"""Demo document seed data with safe sample files."""

from __future__ import annotations

from datetime import date
from io import BytesIO

from sqlalchemy import select

from investhome_api.config.documents_config import initial_processing_status
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentLink,
    DocumentStatus,
    DocumentType,
    ProcessingStatus,
)
from investhome_api.models.project import Project
from investhome_api.services.document_service import create_document_analysis
from investhome_api.services.document_validation import compute_checksum, generate_storage_key
from investhome_api.services.storage import get_storage_provider, provider_enum


DEMO_DOCUMENTS: list[dict[str, object]] = [
    {
        "title": "The Temple Investor Presentation",
        "file_name": "temple-investor-presentation.txt",
        "content": b"Demo document -- The Temple mixed-use redevelopment investor overview.\n\nProject: The Temple\nLocation: 1610 Columbia Rd NW, Washington DC\nStatus: Construction\n\nThis is demo data only.",
        "document_type": DocumentType.PRESENTATION,
        "category": "Investor Materials",
        "project_code": "PRJ-TEMP-001",
        "confidentiality_level": ConfidentialityLevel.INTERNAL,
    },
    {
        "title": "UniLoft Project Summary",
        "file_name": "uniloft-project-summary.txt",
        "content": b"Demo document -- UniLoft adaptive reuse project summary.\n\nUnits: 48 loft-style apartments\nStatus: Leasing at 78%\n\nThis is demo data only.",
        "document_type": DocumentType.PROJECT_DOCUMENT,
        "category": "Project Summary",
        "project_code": "PRJ-UNIL-002",
        "confidentiality_level": ConfidentialityLevel.INTERNAL,
    },
    {
        "title": "309 H St Budget Spreadsheet",
        "file_name": "309h-budget.csv",
        "content": b"Category,Planned,Actual\nAcquisition,4200000,4200000\nRenovation,5600000,0\nContingency,980000,0\n",
        "document_type": DocumentType.SPREADSHEET,
        "category": "Budget",
        "project_code": "PRJ-309H-003",
        "confidentiality_level": ConfidentialityLevel.CONFIDENTIAL,
    },
    {
        "title": "The Campus Conceptual Plan",
        "file_name": "campus-conceptual-plan.txt",
        "content": b"Demo document -- The Campus two-parcel mixed-use conceptual plan.\n\nParcels: 3220 and 3224 Minnesota Ave NE\nUnits: 156\nStatus: Permitting\n\nThis is demo data only.",
        "document_type": DocumentType.ARCHITECTURAL_DRAWING,
        "category": "Conceptual",
        "project_code": "PRJ-CAMP-004",
        "confidentiality_level": ConfidentialityLevel.INTERNAL,
    },
    {
        "title": "1812 H Place Closing Checklist",
        "file_name": "1812h-closing-checklist.txt",
        "content": b"Demo document -- 1812 H Place NE closing checklist.\n\n[ ] Title insurance\n[ ] Final walkthrough\n[ ] Settlement statement review\n\nThis is demo data only.",
        "document_type": DocumentType.CLOSING_DOCUMENT,
        "category": "Closing",
        "project_code": "PRJ-1812H-005",
        "confidentiality_level": ConfidentialityLevel.CONFIDENTIAL,
    },
]


def _extension_from_name(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower()


def _mime_for_ext(ext: str) -> str:
    mapping = {
        "txt": "text/plain",
        "csv": "text/csv",
        "pdf": "application/pdf",
        "png": "image/png",
    }
    return mapping.get(ext, "application/octet-stream")


def seed_demo_documents() -> int:
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        return _seed_demo_documents(db)
    finally:
        db.close()


def _seed_demo_documents(db) -> int:
    existing = db.scalar(select(Document.id).where(Document.is_demo.is_(True)).limit(1))
    if existing is not None:
        return 0

    projects = {
        p.project_code: p
        for p in db.scalars(select(Project).where(Project.is_demo.is_(True))).all()
    }
    storage = get_storage_provider()
    created = 0

    for spec in DEMO_DOCUMENTS:
        project = projects.get(spec["project_code"])
        if project is None:
            continue

        file_name = str(spec["file_name"])
        content = spec["content"]
        if not isinstance(content, bytes):
            continue
        ext = _extension_from_name(file_name)
        stored_name, storage_key = generate_storage_key(ext)
        checksum = compute_checksum(content)
        storage.save(storage_key, BytesIO(content), content_length=len(content))

        document = Document(
            title=str(spec["title"]),
            original_file_name=file_name,
            stored_file_name=stored_name,
            file_extension=ext,
            mime_type=_mime_for_ext(ext),
            file_size=len(content),
            storage_provider=provider_enum(),
            storage_key=storage_key,
            checksum=checksum,
            document_type=spec["document_type"],
            category=str(spec.get("category")),
            status=DocumentStatus.ACTIVE,
            confidentiality_level=spec["confidentiality_level"],
            version_number=1,
            project_id=project.id,
            description=f"Demo document linked to {project.project_name}.",
            tags="demo",
            document_date=date(2026, 6, 1),
            is_latest_version=True,
            processing_status=initial_processing_status(ext),
            is_demo=True,
        )
        db.add(document)
        db.flush()
        create_document_analysis(db, document.id)
        db.add(
            DocumentLink(
                document_id=document.id,
                entity_type="project",
                entity_id=project.id,
                relationship_type="primary",
            )
        )
        created += 1

    if created:
        db.commit()
    return created
