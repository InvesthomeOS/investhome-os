"""Marketing asset library API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_content_studio import (
    AssetCampaignLink,
    AssetCreateFromDocument,
    AssetProjectLink,
    AssetRightsUpdate,
    AssetUpdate,
    AssetUsageCreate,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity
from investhome_api.services.marketing.asset_service import (
    ASSET_FOLDERS,
    archive_asset,
    asset_detail,
    asset_snapshot,
    asset_summary_metrics,
    check_rights_readiness,
    create_asset_from_document,
    duplicate_asset,
    export_assets_csv,
    get_asset,
    link_campaign,
    link_project,
    list_asset_usage,
    list_assets,
    paginate,
    record_asset_usage,
    restore_asset,
    update_asset,
    update_asset_rights,
)
from investhome_api.services.marketing.content_studio_serializers import rights_dict, usage_dict

router = APIRouter(prefix="/marketing/assets", tags=["marketing-assets"])

_VIEW = require_any_permission(("marketing", "view"), ("marketing", "manage_assets"))
_EDIT = require_permission("marketing", "manage_assets")
_EXPORT = require_any_permission(("marketing", "export"), ("marketing", "manage_assets"))


@router.get("/folders")
def list_folders(
    user: User = Depends(_VIEW),
) -> dict:
    return {"items": list(ASSET_FOLDERS)}


@router.get("/summary")
def assets_summary(
    db: Session = Depends(get_db),
    user: User = Depends(_VIEW),
) -> dict:
    metrics = asset_summary_metrics(db)
    return {"metrics": [metric.model_dump(mode="json") for metric in metrics]}


@router.get("/export")
def export_assets(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EXPORT),
    asset_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    folder: str | None = None,
    project_id: UUID | None = None,
    campaign_id: UUID | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> Response:
    csv_body = export_assets_csv(
        db,
        asset_type=asset_type,
        status_filter=status_filter,
        folder=folder,
        project_id=project_id,
        campaign_id=campaign_id,
        search=search,
        include_archived=include_archived,
    )
    log_activity(
        db,
        action=ActivityAction.EXPORTED,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=UUID("00000000-0000-0000-0000-000000000000"),
        description_key="marketing.asset.exported",
        actor_user=user,
        metadata={"row_count_hint": max(csv_body.count("\n") - 1, 0)},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="marketing-assets.csv"'},
    )


@router.get("")
def list_assets_route(
    db: Session = Depends(get_db),
    user: User = Depends(_VIEW),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    asset_type: str | None = None,
    rights_status: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    folder: str | None = None,
    project_id: UUID | None = None,
    campaign_id: UUID | None = None,
    tag: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> dict:
    items, total = list_assets(
        db,
        page=page,
        page_size=page_size,
        asset_type=asset_type,
        rights_status=rights_status,
        status_filter=status_filter,
        folder=folder,
        project_id=project_id,
        campaign_id=campaign_id,
        tag=tag,
        search=search,
        include_archived=include_archived,
    )
    return paginate(items, total, page, page_size)


@router.post("/from-document", status_code=status.HTTP_201_CREATED)
def create_from_document(
    body: AssetCreateFromDocument,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = create_asset_from_document(db, payload=body.model_dump(exclude_none=True), actor=user)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.created",
        actor=user,
        request=request,
        metadata={"document_id": str(asset.document_id) if asset.document_id else None},
    )
    db.commit()
    db.refresh(asset)
    return {"asset": asset_detail(db, asset)}


@router.get("/{asset_id}")
def get_asset_route(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_VIEW),
    include_archived: bool = False,
) -> dict:
    return asset_detail(db, get_asset(db, asset_id, include_archived=include_archived))


@router.put("/{asset_id}")
def update_asset_route(
    asset_id: UUID,
    body: AssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    before = asset_snapshot(asset)
    update_asset(db, asset, payload=body.model_dump(exclude_unset=True), actor=user)
    after = asset_snapshot(asset)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.updated",
        actor=user,
        before=before,
        after=after,
        request=request,
    )
    db.commit()
    db.refresh(asset)
    return {"asset": asset_detail(db, asset)}


@router.post("/{asset_id}/archive", status_code=status.HTTP_200_OK)
def archive_asset_route(
    asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    archive_asset(db, asset, actor=user)
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.archived",
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(asset)
    return {"asset": asset_detail(db, asset)}


@router.post("/{asset_id}/restore", status_code=status.HTTP_200_OK)
def restore_asset_route(
    asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    restore_asset(db, asset, actor=user)
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.restored",
        actor=user,
        request=request,
    )
    db.commit()
    db.refresh(asset)
    return {"asset": asset_detail(db, asset)}


@router.post("/{asset_id}/link-campaign", status_code=status.HTTP_200_OK)
def link_campaign_route(
    asset_id: UUID,
    body: AssetCampaignLink,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    before = asset_snapshot(asset)
    link_campaign(db, asset, campaign_id=body.campaign_id, actor=user)
    after = asset_snapshot(asset)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.campaign_linked",
        actor=user,
        before=before,
        after=after,
        request=request,
        metadata={"campaign_id": str(body.campaign_id) if body.campaign_id else None},
    )
    db.commit()
    db.refresh(asset)
    return {"asset": asset_detail(db, asset)}


@router.post("/{asset_id}/link-project", status_code=status.HTTP_200_OK)
def link_project_route(
    asset_id: UUID,
    body: AssetProjectLink,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    before = asset_snapshot(asset)
    link_project(db, asset, project_id=body.project_id, actor=user)
    after = asset_snapshot(asset)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.project_linked",
        actor=user,
        before=before,
        after=after,
        request=request,
        metadata={"project_id": str(body.project_id) if body.project_id else None},
    )
    db.commit()
    db.refresh(asset)
    return {"asset": asset_detail(db, asset)}


@router.get("/{asset_id}/rights")
def get_rights(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_VIEW),
) -> dict:
    from sqlalchemy import select

    from investhome_api.models.marketing_content_studio import AssetRights

    asset = get_asset(db, asset_id, include_archived=True)
    rights = db.scalar(select(AssetRights).where(AssetRights.asset_id == asset.id))
    return {
        "rights": rights_dict(rights) if rights else None,
        "rights_status": asset.rights_status.value,
    }


@router.put("/{asset_id}/rights")
def update_rights(
    asset_id: UUID,
    body: AssetRightsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    before = {"rights_status": asset.rights_status.value}
    rights = update_asset_rights(db, asset, payload=body.model_dump(exclude_unset=True))
    after = {"rights_status": asset.rights_status.value}
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=asset.id,
        description_key="marketing.asset.updated",
        actor=user,
        before=before,
        after=after,
        request=request,
    )
    db.commit()
    db.refresh(asset)
    return {"rights": rights_dict(rights), "asset": asset_detail(db, asset)}


@router.get("/{asset_id}/rights-readiness")
def rights_readiness(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_VIEW),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    return check_rights_readiness(db, asset)


@router.get("/{asset_id}/usage")
def asset_usage(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_VIEW),
) -> dict:
    get_asset(db, asset_id, include_archived=True)
    return {"items": [usage_dict(u) for u in list_asset_usage(db, asset_id)]}


@router.post("/{asset_id}/usage", status_code=status.HTTP_201_CREATED)
def record_usage(
    asset_id: UUID,
    body: AssetUsageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    record = record_asset_usage(
        db,
        asset,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        usage_context=body.usage_context,
        channel_id=body.channel_id,
    )
    db.commit()
    db.refresh(record)
    return {"usage": usage_dict(record)}


@router.post("/{asset_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_asset_route(
    asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_EDIT),
) -> dict:
    asset = get_asset(db, asset_id, include_archived=True)
    duplicate = duplicate_asset(db, asset, actor=user)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_CONTENT_ASSET,
        entity_id=duplicate.id,
        description_key="marketing.asset.created",
        actor=user,
        request=request,
        metadata={"duplicated_from": str(asset.id)},
    )
    db.commit()
    db.refresh(duplicate)
    return {"asset": asset_detail(db, duplicate)}
