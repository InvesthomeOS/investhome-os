"""Marketing asset library service — metadata only, references Documents storage."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.document import Document
from investhome_api.models.marketing import MarketingCampaign
from investhome_api.models.marketing_content_studio import (
    AssetRights,
    AssetRightsStatus,
    AssetUsageRecord,
    MarketingAsset,
    MarketingAssetFolder,
    MarketingAssetStatus,
    MarketingAssetType,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_analytics import MetricValue
from investhome_api.services.marketing.campaign_service import compute_pages

ASSET_FOLDERS = tuple(folder.value for folder in MarketingAssetFolder)
READY_STATUSES = {MarketingAssetStatus.READY, MarketingAssetStatus.ACTIVE}
AI_PREP_KEYS = ("language", "audience", "market", "property_type", "country", "city", "keywords")


def _normalize_status(value: str | None) -> MarketingAssetStatus | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "active":
        return MarketingAssetStatus.READY
    try:
        return MarketingAssetStatus(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {value}"
        ) from exc


def _normalize_folder(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    normalized = value.strip().lower()
    if normalized not in ASSET_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid folder: {value}. Allowed: {', '.join(ASSET_FOLDERS)}",
        )
    return normalized


def _normalize_ai_prep(value: dict | None) -> dict | None:
    if value is None:
        return None
    cleaned: dict = {}
    for key in AI_PREP_KEYS:
        if key not in value or value[key] is None:
            continue
        if key == "keywords":
            keywords = value[key]
            if isinstance(keywords, list):
                cleaned[key] = [str(item).strip() for item in keywords if str(item).strip()]
            elif isinstance(keywords, str) and keywords.strip():
                cleaned[key] = [part.strip() for part in keywords.split(",") if part.strip()]
        else:
            text = str(value[key]).strip()
            if text:
                cleaned[key] = text
    return cleaned or None


def _resolve_name(payload: dict) -> str | None:
    if payload.get("name"):
        return str(payload["name"]).strip() or None
    if payload.get("title"):
        return str(payload["title"]).strip() or None
    return None


def _to_summary(
    asset: MarketingAsset, *, project_name: str | None = None, campaign_name: str | None = None
) -> dict:
    status_value = asset.status.value
    if status_value == MarketingAssetStatus.ACTIVE.value:
        status_value = MarketingAssetStatus.READY.value
    return {
        "id": str(asset.id),
        "name": asset.name,
        "title": asset.name,
        "asset_type": asset.asset_type.value,
        "document_id": str(asset.document_id) if asset.document_id else None,
        "file_ref": asset.file_ref,
        "status": status_value,
        "folder": asset.folder,
        "project_id": str(asset.project_id) if asset.project_id else None,
        "campaign_id": str(asset.campaign_id) if asset.campaign_id else None,
        "project_name": project_name,
        "campaign_name": campaign_name,
        "rights_status": asset.rights_status.value,
        "tags": asset.tags or [],
        "thumbnail_document_id": str(asset.thumbnail_document_id)
        if asset.thumbnail_document_id
        else None,
        "uploaded_by": str(asset.created_by_user_id) if asset.created_by_user_id else None,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


def _to_detail(
    asset: MarketingAsset, *, project_name: str | None = None, campaign_name: str | None = None
) -> dict:
    return {
        **_to_summary(asset, project_name=project_name, campaign_name=campaign_name),
        "description": asset.description,
        "notes": asset.notes,
        "ai_prep": asset.ai_prep_json or {},
        "archived_at": asset.archived_at,
        "metadata_json": asset.metadata_json,
    }


def _load_link_names(
    db: Session, assets: list[MarketingAsset]
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    project_ids = {asset.project_id for asset in assets if asset.project_id}
    campaign_ids = {asset.campaign_id for asset in assets if asset.campaign_id}
    projects: dict[UUID, str] = {}
    campaigns: dict[UUID, str] = {}
    if project_ids:
        for row in db.scalars(select(Project).where(Project.id.in_(project_ids))).all():
            projects[row.id] = row.project_name
    if campaign_ids:
        for row in db.scalars(
            select(MarketingCampaign).where(MarketingCampaign.id.in_(campaign_ids))
        ).all():
            campaigns[row.id] = row.name
    return projects, campaigns


def get_asset(db: Session, asset_id: UUID, *, include_archived: bool = False) -> MarketingAsset:
    asset = db.get(MarketingAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if not include_archived and asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


def asset_detail(db: Session, asset: MarketingAsset) -> dict:
    projects, campaigns = _load_link_names(db, [asset])
    return _to_detail(
        asset,
        project_name=projects.get(asset.project_id) if asset.project_id else None,
        campaign_name=campaigns.get(asset.campaign_id) if asset.campaign_id else None,
    )


def list_assets(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    asset_type: str | None = None,
    rights_status: str | None = None,
    status_filter: str | None = None,
    folder: str | None = None,
    project_id: UUID | None = None,
    campaign_id: UUID | None = None,
    tag: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> tuple[list[dict], int]:
    query = select(MarketingAsset)
    if not include_archived:
        query = query.where(MarketingAsset.archived_at.is_(None))
    if asset_type:
        query = query.where(MarketingAsset.asset_type == asset_type)
    if rights_status:
        query = query.where(MarketingAsset.rights_status == rights_status)
    if status_filter:
        normalized = _normalize_status(status_filter)
        if normalized in READY_STATUSES:
            query = query.where(MarketingAsset.status.in_(list(READY_STATUSES)))
        else:
            query = query.where(MarketingAsset.status == normalized)
    if folder:
        query = query.where(MarketingAsset.folder == _normalize_folder(folder))
    if project_id:
        query = query.where(MarketingAsset.project_id == project_id)
    if campaign_id:
        query = query.where(MarketingAsset.campaign_id == campaign_id)
    if tag:
        tag_pattern = f"%{tag.strip()}%"
        query = query.where(cast(MarketingAsset.tags, String).ilike(tag_pattern))
    if search:
        pattern = f"%{search.strip()}%"
        query = (
            query.outerjoin(Project, Project.id == MarketingAsset.project_id)
            .outerjoin(MarketingCampaign, MarketingCampaign.id == MarketingAsset.campaign_id)
            .where(
                or_(
                    MarketingAsset.name.ilike(pattern),
                    MarketingAsset.description.ilike(pattern),
                    cast(MarketingAsset.tags, String).ilike(pattern),
                    MarketingAsset.folder.ilike(pattern),
                    cast(MarketingAsset.asset_type, String).ilike(pattern),
                    Project.project_name.ilike(pattern),
                    MarketingCampaign.name.ilike(pattern),
                )
            )
        )
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = list(
        db.scalars(
            query.order_by(MarketingAsset.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    projects, campaigns = _load_link_names(db, rows)
    items = [
        _to_summary(
            row,
            project_name=projects.get(row.project_id) if row.project_id else None,
            campaign_name=campaigns.get(row.campaign_id) if row.campaign_id else None,
        )
        for row in rows
    ]
    return items, total


def asset_summary_metrics(db: Session) -> list[MetricValue]:
    base = select(MarketingAsset).where(MarketingAsset.archived_at.is_(None))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    draft = (
        db.scalar(
            select(func.count()).select_from(
                base.where(MarketingAsset.status == MarketingAssetStatus.DRAFT).subquery()
            )
        )
        or 0
    )
    ready = (
        db.scalar(
            select(func.count()).select_from(
                base.where(MarketingAsset.status.in_(list(READY_STATUSES))).subquery()
            )
        )
        or 0
    )
    archived = (
        db.scalar(
            select(func.count()).select_from(
                select(MarketingAsset).where(MarketingAsset.archived_at.is_not(None)).subquery()
            )
        )
        or 0
    )
    linked_campaigns = (
        db.scalar(
            select(func.count()).select_from(
                base.where(MarketingAsset.campaign_id.is_not(None)).subquery()
            )
        )
        or 0
    )
    linked_projects = (
        db.scalar(
            select(func.count()).select_from(
                base.where(MarketingAsset.project_id.is_not(None)).subquery()
            )
        )
        or 0
    )
    now = datetime.now(UTC)
    evidence = {"source": "marketing_assets", "computed_from": "row_counts"}

    def metric(key: str, label: str, value: int) -> MetricValue:
        state = "ready" if total > 0 or key == "total_assets" else "empty"
        return MetricValue(
            key=key,
            label=label,
            state=state if value > 0 or key == "total_assets" else "empty",
            value=value,
            unit="count",
            freshness_at=now,
            evidence=evidence,
        )

    return [
        metric("total_assets", "Total assets", total),
        metric("draft_assets", "Draft", draft),
        metric("ready_assets", "Ready", ready),
        metric("archived_assets", "Archived", archived),
        metric("linked_to_campaigns", "Linked to campaigns", linked_campaigns),
        metric("linked_to_projects", "Linked to projects", linked_projects),
    ]


def create_asset_from_document(db: Session, *, payload: dict, actor: User) -> MarketingAsset:
    document_id = payload.get("document_id")
    if not document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="document_id is required"
        )
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    project_id = payload.get("project_id")
    campaign_id = payload.get("campaign_id")
    if project_id and db.get(Project, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if campaign_id and db.get(MarketingCampaign, campaign_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    thumbnail_document_id = payload.get("thumbnail_document_id")
    if thumbnail_document_id and db.get(Document, thumbnail_document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail document not found"
        )

    ai_prep = payload.get("ai_prep")
    if hasattr(ai_prep, "model_dump"):
        ai_prep = ai_prep.model_dump(exclude_none=True)

    status_value = _normalize_status(payload.get("status")) or MarketingAssetStatus.DRAFT
    asset = MarketingAsset(
        name=_resolve_name(payload) or document.title,
        asset_type=MarketingAssetType(payload.get("asset_type", "other")),
        document_id=document.id,
        file_ref=str(document.id),
        description=payload.get("description"),
        status=status_value,
        folder=_normalize_folder(payload.get("folder")),
        project_id=project_id,
        campaign_id=campaign_id,
        notes=payload.get("notes"),
        thumbnail_document_id=thumbnail_document_id,
        ai_prep_json=_normalize_ai_prep(ai_prep if isinstance(ai_prep, dict) else None),
        rights_status=AssetRightsStatus.UNKNOWN,
        tags=payload.get("tags") or [],
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(asset)
    db.flush()
    rights = AssetRights(asset_id=asset.id, status=AssetRightsStatus.UNKNOWN)
    db.add(rights)
    return asset


def asset_snapshot(asset: MarketingAsset) -> dict:
    return {
        "name": asset.name,
        "description": asset.description,
        "asset_type": asset.asset_type.value,
        "status": asset.status.value,
        "folder": asset.folder,
        "project_id": str(asset.project_id) if asset.project_id else None,
        "campaign_id": str(asset.campaign_id) if asset.campaign_id else None,
        "notes": asset.notes,
        "tags": asset.tags or [],
        "thumbnail_document_id": str(asset.thumbnail_document_id)
        if asset.thumbnail_document_id
        else None,
        "ai_prep": asset.ai_prep_json or {},
    }


def update_asset(
    db: Session, asset: MarketingAsset, *, payload: dict, actor: User
) -> MarketingAsset:
    if "title" in payload and "name" not in payload:
        payload = {**payload, "name": payload.get("title")}

    if "name" in payload and payload["name"] is not None:
        name = str(payload["name"]).strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
        asset.name = name

    if "description" in payload:
        asset.description = payload["description"]
    if "notes" in payload:
        asset.notes = payload["notes"]
    if "tags" in payload:
        asset.tags = payload["tags"] or []
    if "asset_type" in payload and payload["asset_type"] is not None:
        try:
            asset.asset_type = MarketingAssetType(payload["asset_type"])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid asset_type: {payload['asset_type']}",
            ) from exc
    if "status" in payload and payload["status"] is not None:
        asset.status = _normalize_status(payload["status"]) or asset.status
        if asset.status == MarketingAssetStatus.ARCHIVED and asset.archived_at is None:
            asset.archived_at = datetime.now(UTC)
        if asset.status != MarketingAssetStatus.ARCHIVED:
            asset.archived_at = None
    if "folder" in payload:
        asset.folder = _normalize_folder(payload.get("folder"))
    if "project_id" in payload:
        project_id = payload.get("project_id")
        if project_id and db.get(Project, project_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        asset.project_id = project_id
    if "campaign_id" in payload:
        campaign_id = payload.get("campaign_id")
        if campaign_id and db.get(MarketingCampaign, campaign_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        asset.campaign_id = campaign_id
    if "thumbnail_document_id" in payload:
        thumbnail_document_id = payload.get("thumbnail_document_id")
        if thumbnail_document_id and db.get(Document, thumbnail_document_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail document not found"
            )
        asset.thumbnail_document_id = thumbnail_document_id
    if "ai_prep" in payload:
        ai_prep = payload.get("ai_prep")
        if hasattr(ai_prep, "model_dump"):
            ai_prep = ai_prep.model_dump(exclude_none=True)
        asset.ai_prep_json = _normalize_ai_prep(ai_prep if isinstance(ai_prep, dict) else None)

    asset.updated_by_user_id = actor.id
    return asset


def link_campaign(
    db: Session, asset: MarketingAsset, *, campaign_id: UUID | None, actor: User
) -> MarketingAsset:
    return update_asset(db, asset, payload={"campaign_id": campaign_id}, actor=actor)


def link_project(
    db: Session, asset: MarketingAsset, *, project_id: UUID | None, actor: User
) -> MarketingAsset:
    return update_asset(db, asset, payload={"project_id": project_id}, actor=actor)


def archive_asset(db: Session, asset: MarketingAsset, *, actor: User) -> MarketingAsset:
    asset.status = MarketingAssetStatus.ARCHIVED
    asset.archived_at = datetime.now(UTC)
    asset.updated_by_user_id = actor.id
    return asset


def restore_asset(db: Session, asset: MarketingAsset, *, actor: User) -> MarketingAsset:
    asset.archived_at = None
    asset.status = MarketingAssetStatus.DRAFT
    asset.updated_by_user_id = actor.id
    return asset


def update_asset_rights(db: Session, asset: MarketingAsset, *, payload: dict) -> AssetRights:
    rights = db.scalar(select(AssetRights).where(AssetRights.asset_id == asset.id))
    if rights is None:
        rights = AssetRights(asset_id=asset.id)
        db.add(rights)
        db.flush()
    for field in (
        "license_type",
        "holder",
        "valid_from",
        "valid_until",
        "territory",
        "usage_restrictions",
        "attribution_required",
        "status",
    ):
        if field in payload:
            if field == "status":
                rights.status = AssetRightsStatus(payload[field])
                asset.rights_status = rights.status
            else:
                setattr(rights, field, payload[field])
    if rights.valid_until and rights.valid_until < datetime.now(UTC):
        rights.status = AssetRightsStatus.EXPIRED
        asset.rights_status = AssetRightsStatus.EXPIRED
    elif rights.status == AssetRightsStatus.UNKNOWN:
        asset.rights_status = AssetRightsStatus.UNKNOWN
    else:
        asset.rights_status = rights.status
    return rights


def check_rights_readiness(db: Session, asset: MarketingAsset) -> dict:
    rights = db.scalar(select(AssetRights).where(AssetRights.asset_id == asset.id))
    if rights is None or rights.status == AssetRightsStatus.UNKNOWN:
        return {
            "state": "blocked",
            "rights_status": AssetRightsStatus.UNKNOWN.value,
            "remediation": ["Rights status is unknown — cannot treat as cleared"],
        }
    if rights.status == AssetRightsStatus.EXPIRED:
        return {
            "state": "blocked",
            "rights_status": rights.status.value,
            "remediation": ["Rights have expired"],
        }
    if rights.status == AssetRightsStatus.RESTRICTED:
        return {
            "state": "blocked",
            "rights_status": rights.status.value,
            "remediation": ["Rights are restricted"],
        }
    if rights.status == AssetRightsStatus.CLEARED:
        return {"state": "ready", "rights_status": rights.status.value, "remediation": []}
    return {
        "state": "warning",
        "rights_status": rights.status.value,
        "remediation": ["Rights pending verification"],
    }


def record_asset_usage(
    db: Session,
    asset: MarketingAsset,
    *,
    entity_type: str,
    entity_id: UUID,
    usage_context: str | None,
    channel_id: UUID | None,
) -> AssetUsageRecord:
    record = AssetUsageRecord(
        asset_id=asset.id,
        entity_type=entity_type,
        entity_id=entity_id,
        usage_context=usage_context,
        channel_id=channel_id,
    )
    db.add(record)
    return record


def list_asset_usage(db: Session, asset_id: UUID) -> list[AssetUsageRecord]:
    return list(
        db.scalars(
            select(AssetUsageRecord)
            .where(AssetUsageRecord.asset_id == asset_id)
            .order_by(AssetUsageRecord.recorded_at.desc())
        ).all()
    )


def duplicate_asset(db: Session, asset: MarketingAsset, *, actor: User) -> MarketingAsset:
    if asset.document_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot duplicate asset without document reference",
        )
    duplicate = MarketingAsset(
        name=f"{asset.name} (Copy)",
        asset_type=asset.asset_type,
        document_id=asset.document_id,
        file_ref=asset.file_ref,
        description=asset.description,
        status=MarketingAssetStatus.DRAFT,
        folder=asset.folder,
        project_id=asset.project_id,
        campaign_id=asset.campaign_id,
        notes=asset.notes,
        thumbnail_document_id=asset.thumbnail_document_id,
        ai_prep_json=asset.ai_prep_json,
        rights_status=AssetRightsStatus.UNKNOWN,
        tags=list(asset.tags or []),
        metadata_json={"duplicated_from": str(asset.id)},
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(duplicate)
    db.flush()
    rights = db.scalar(select(AssetRights).where(AssetRights.asset_id == asset.id))
    new_rights = AssetRights(
        asset_id=duplicate.id,
        license_type=rights.license_type if rights else None,
        holder=rights.holder if rights else None,
        status=AssetRightsStatus.UNKNOWN,
    )
    db.add(new_rights)
    return duplicate


def export_assets_csv(
    db: Session,
    *,
    asset_type: str | None = None,
    status_filter: str | None = None,
    folder: str | None = None,
    project_id: UUID | None = None,
    campaign_id: UUID | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> str:
    items, _ = list_assets(
        db,
        page=1,
        page_size=10_000,
        asset_type=asset_type,
        status_filter=status_filter,
        folder=folder,
        project_id=project_id,
        campaign_id=campaign_id,
        search=search,
        include_archived=include_archived,
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "title",
            "asset_type",
            "status",
            "folder",
            "tags",
            "project_id",
            "project_name",
            "campaign_id",
            "campaign_name",
            "document_id",
            "rights_status",
            "uploaded_by",
            "created_at",
            "updated_at",
        ],
    )
    writer.writeheader()
    for item in items:
        writer.writerow(
            {
                "id": item["id"],
                "title": item["title"],
                "asset_type": item["asset_type"],
                "status": item["status"],
                "folder": item["folder"] or "",
                "tags": "|".join(item.get("tags") or []),
                "project_id": item["project_id"] or "",
                "project_name": item.get("project_name") or "",
                "campaign_id": item["campaign_id"] or "",
                "campaign_name": item.get("campaign_name") or "",
                "document_id": item["document_id"] or "",
                "rights_status": item["rights_status"],
                "uploaded_by": item.get("uploaded_by") or "",
                "created_at": item["created_at"].isoformat() if item.get("created_at") else "",
                "updated_at": item["updated_at"].isoformat() if item.get("updated_at") else "",
            }
        )
    return buffer.getvalue()


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }
