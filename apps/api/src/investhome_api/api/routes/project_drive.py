"""Google Drive mapping + manual sync + status endpoints (construction projects)."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.project import Project
from investhome_api.models.project_drive import ProjectDriveMapping
from investhome_api.models.user_auth import User
from investhome_api.schemas.google_drive import (
    DriveStatusResponse,
    DriveSyncResponse,
    ProjectDriveMappingResponse,
    ProjectDriveMappingUpsert,
)
from investhome_api.services.google_drive.errors import GoogleDriveConfigError, GoogleDriveError
from investhome_api.services.google_drive.provider import get_google_drive_provider
from investhome_api.services.google_drive.scanner import upsert_project_drive_mapping
from investhome_api.services.google_drive.sync_service import DriveSyncOrchestrator, get_drive_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["project-drive"])

_cs_view = Depends(require_permission("creative_studio", "view"))
_cs_sync = Depends(require_permission("creative_studio", "sync_drive"))


def _project_or_404(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _mapping_response(mapping: ProjectDriveMapping) -> ProjectDriveMappingResponse:
    return ProjectDriveMappingResponse.model_validate(mapping)


@router.get("/{project_id}/drive/mapping", response_model=ProjectDriveMappingResponse)
def get_drive_mapping(
    project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> ProjectDriveMappingResponse:
    _project_or_404(project_id, db)
    mapping = db.scalar(
        select(ProjectDriveMapping).where(
            ProjectDriveMapping.project_id == project_id,
            ProjectDriveMapping.archived_at.is_(None),
        )
    )
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive mapping not found")
    return _mapping_response(mapping)


@router.put("/{project_id}/drive/mapping", response_model=ProjectDriveMappingResponse)
def upsert_drive_mapping(
    project_id: UUID,
    payload: ProjectDriveMappingUpsert,
    db: Session = Depends(get_db),
    _user: User = _cs_sync,
) -> ProjectDriveMappingResponse:
    project = _project_or_404(project_id, db)
    provider = get_google_drive_provider()
    try:
        mapping = upsert_project_drive_mapping(
            db,
            project_id=project.id,
            drive_folder_id=payload.drive_folder_id,
            drive_sync_enabled=payload.drive_sync_enabled,
            provider=provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GoogleDriveConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except GoogleDriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc

    db.commit()
    db.refresh(mapping)
    return _mapping_response(mapping)


@router.get("/{project_id}/drive/status", response_model=DriveStatusResponse)
def get_project_drive_status(
    project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _cs_view,
) -> DriveStatusResponse:
    _project_or_404(project_id, db)
    payload = get_drive_status(db, project_id)
    return DriveStatusResponse.model_validate(payload)


@router.post("/{project_id}/drive/sync", response_model=DriveSyncResponse)
def sync_project_drive(
    project_id: UUID,
    dry_run: bool = Query(default=False),
    force_full: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _cs_sync,
) -> DriveSyncResponse:
    """Manual Drive → Media Library sync. ``dry_run=true`` reports diffs without DB writes."""
    project = _project_or_404(project_id, db)
    provider = get_google_drive_provider()
    orchestrator = DriveSyncOrchestrator(db, provider)
    try:
        summary = orchestrator.sync_project(
            project.id,
            dry_run=dry_run,
            force_full=force_full,
        )
    except GoogleDriveConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except GoogleDriveError as exc:
        logger.warning(
            "drive_sync_endpoint_failed",
            extra={"project_id": str(project_id), "code": getattr(exc, "code", None)},
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return DriveSyncResponse.model_validate(summary.to_dict())
