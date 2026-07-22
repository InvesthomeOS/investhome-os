"""Marketing analytics API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_analytics import (
    DashboardLayoutCreate,
    DashboardLayoutResponse,
    DashboardLayoutUpdate,
    DashboardSavedViewCreate,
    DashboardSavedViewResponse,
    DashboardSavedViewUpdate,
    MarketingDashboardFilters,
    MarketingExecutiveDashboardResponse,
    MarketingHealthResponse,
    MarketingKPIsResponse,
    MarketingTimeFilter,
    MarketingWidgetsResponse,
)
from investhome_api.services.activity_service import ActivityRequestContext, log_activity
from investhome_api.services.marketing.analytics_service import (
    build_executive_dashboard,
    build_funnel,
    build_kpis,
    compute_attribution_health,
    compute_data_health,
    compute_health,
    compute_tracking_health,
    create_layout,
    create_saved_view,
    delete_layout,
    delete_saved_view,
    fetch_executive_alerts,
    fetch_recommendations,
    get_dashboard_widgets,
    get_layout,
    get_saved_view,
    list_layouts,
    list_saved_views,
    update_layout,
    update_saved_view,
)

router = APIRouter(prefix="/marketing/analytics", tags=["marketing-analytics"])


def _parse_filters(
    campaign_id: UUID | None = None,
    project_id: UUID | None = None,
    property_id: UUID | None = None,
    country: str | None = None,
    region: str | None = None,
    language: str | None = None,
    audience_id: UUID | None = None,
    segment_id: UUID | None = None,
    channel_id: UUID | None = None,
    source_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    team_id: UUID | None = None,
    lead_type: str | None = None,
) -> MarketingDashboardFilters:
    return MarketingDashboardFilters(
        campaign_id=campaign_id,
        project_id=project_id,
        property_id=property_id,
        country=country,
        region=region,
        language=language,
        audience_id=audience_id,
        segment_id=segment_id,
        channel_id=channel_id,
        source_id=source_id,
        owner_user_id=owner_user_id,
        team_id=team_id,
        lead_type=lead_type,
    )


def _parse_time_filter(
    preset: str = "last_30_days",
    timezone: str = "UTC",
) -> MarketingTimeFilter:
    return MarketingTimeFilter(preset=preset, timezone=timezone)


def _audit_dashboard_view(
    db: Session,
    user: User,
    *,
    description_key: str,
    entity_id: UUID,
    action: ActivityAction = ActivityAction.VIEWED,
    metadata: dict | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.MARKETING_DASHBOARD,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=user,
        source=ActivitySource.API,
        metadata=metadata,
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )


@router.get("/executive", response_model=MarketingExecutiveDashboardResponse)
def get_executive_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
    preset: str = Query("last_30_days"),
    timezone: str = Query("UTC"),
    campaign_id: UUID | None = None,
    channel_id: UUID | None = None,
    source_id: UUID | None = None,
) -> MarketingExecutiveDashboardResponse:
    time_filter = _parse_time_filter(preset, timezone)
    filters = _parse_filters(campaign_id=campaign_id, channel_id=channel_id, source_id=source_id)
    result = build_executive_dashboard(db, user, time_filter=time_filter, filters=filters)
    _audit_dashboard_view(
        db,
        user,
        description_key="marketing.analytics.executive.viewed",
        entity_id=user.id,
        metadata={"dashboard": "executive"},
    )
    db.commit()
    return result


@router.get("/kpis", response_model=MarketingKPIsResponse)
def get_marketing_kpis(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
    preset: str = Query("last_30_days"),
    timezone: str = Query("UTC"),
    campaign_id: UUID | None = None,
) -> MarketingKPIsResponse:
    time_filter = _parse_time_filter(preset, timezone)
    filters = _parse_filters(campaign_id=campaign_id)
    return MarketingKPIsResponse(
        kpis=build_kpis(db, user, time_filter=time_filter, filters=filters),
        time_filter=time_filter,
        filters=filters,
    )


@router.get("/health", response_model=MarketingHealthResponse)
def get_marketing_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
) -> MarketingHealthResponse:
    result = compute_health(db, user)
    db.commit()
    return result


@router.get("/health/tracking", response_model=MarketingHealthResponse)
def get_tracking_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
) -> MarketingHealthResponse:
    return compute_tracking_health(db, user)


@router.get("/health/attribution", response_model=MarketingHealthResponse)
def get_attribution_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_attribution")),
) -> MarketingHealthResponse:
    return compute_attribution_health(db, user)


@router.get("/health/data", response_model=MarketingHealthResponse)
def get_data_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
) -> MarketingHealthResponse:
    return compute_data_health(db, user)


@router.get("/funnel")
def get_marketing_funnel(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
    preset: str = Query("last_30_days"),
    timezone: str = Query("UTC"),
):
    time_filter = _parse_time_filter(preset, timezone)
    filters = _parse_filters()
    return build_funnel(db, user, time_filter=time_filter, filters=filters)


@router.get("/widgets", response_model=MarketingWidgetsResponse)
def get_dashboard_widgets_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
    dashboard_key: str = Query("executive"),
    preset: str = Query("last_30_days"),
    timezone: str = Query("UTC"),
) -> MarketingWidgetsResponse:
    time_filter = _parse_time_filter(preset, timezone)
    filters = _parse_filters()
    return get_dashboard_widgets(db, user, dashboard_key=dashboard_key, time_filter=time_filter, filters=filters)


@router.get("/alerts")
def get_executive_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
):
    return {"items": fetch_executive_alerts(db)}


@router.get("/recommendations")
def get_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view")),
):
    return {"items": fetch_recommendations(db)}


@router.get("/layouts", response_model=list[DashboardLayoutResponse])
def get_dashboard_layouts(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
    dashboard_key: str | None = None,
) -> list[DashboardLayoutResponse]:
    return list_layouts(db, user.id, dashboard_key=dashboard_key)


@router.post("/layouts", response_model=DashboardLayoutResponse, status_code=201)
def post_dashboard_layout(
    payload: DashboardLayoutCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "export_analytics")),
) -> DashboardLayoutResponse:
    result = create_layout(db, user, payload)
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.MARKETING_DASHBOARD,
        entity_id=result.id,
        description_key="marketing.analytics.layout.created",
        actor_user=user,
        source=ActivitySource.API,
        metadata={"action": "layout_created", "name": payload.name},
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )
    db.commit()
    return result


@router.put("/layouts/{layout_id}", response_model=DashboardLayoutResponse)
def put_dashboard_layout(
    layout_id: UUID,
    payload: DashboardLayoutUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "export_analytics")),
) -> DashboardLayoutResponse:
    layout = get_layout(db, layout_id)
    if layout.owner_user_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Not authorized to modify this layout")
    result = update_layout(db, layout, payload)
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.MARKETING_DASHBOARD,
        entity_id=layout_id,
        description_key="marketing.analytics.layout.updated",
        actor_user=user,
        source=ActivitySource.API,
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )
    db.commit()
    return result


@router.delete("/layouts/{layout_id}", status_code=204)
def remove_dashboard_layout(
    layout_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "export_analytics")),
) -> None:
    layout = get_layout(db, layout_id)
    if layout.owner_user_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Not authorized to delete this layout")
    delete_layout(db, layout)
    db.commit()


@router.get("/saved-views", response_model=list[DashboardSavedViewResponse])
def get_dashboard_saved_views(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
    dashboard_key: str | None = None,
) -> list[DashboardSavedViewResponse]:
    return list_saved_views(db, user.id, dashboard_key=dashboard_key)


@router.post("/saved-views", response_model=DashboardSavedViewResponse, status_code=201)
def post_dashboard_saved_view(
    payload: DashboardSavedViewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
) -> DashboardSavedViewResponse:
    result = create_saved_view(db, user, payload)
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.MARKETING_DASHBOARD,
        entity_id=result.id,
        description_key="marketing.analytics.saved_view.created",
        actor_user=user,
        source=ActivitySource.API,
        metadata={"name": payload.name},
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )
    db.commit()
    return result


@router.put("/saved-views/{view_id}", response_model=DashboardSavedViewResponse)
def put_dashboard_saved_view(
    view_id: UUID,
    payload: DashboardSavedViewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
) -> DashboardSavedViewResponse:
    view = get_saved_view(db, view_id)
    if view.user_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Not authorized to modify this saved view")
    result = update_saved_view(db, view, payload)
    db.commit()
    return result


@router.delete("/saved-views/{view_id}", status_code=204)
def remove_dashboard_saved_view(
    view_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_dashboard")),
) -> None:
    view = get_saved_view(db, view_id)
    if view.user_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Not authorized to delete this saved view")
    delete_saved_view(db, view)
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=ActivityEntityType.MARKETING_DASHBOARD,
        entity_id=view_id,
        description_key="marketing.analytics.saved_view.deleted",
        actor_user=user,
        source=ActivitySource.API,
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )
    db.commit()
