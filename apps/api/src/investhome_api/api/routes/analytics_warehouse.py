"""G14 Data Platform API — admin-restricted warehouse governance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.analytics_warehouse import WhScheduledReport
from investhome_api.models.user_auth import User
from investhome_api.schemas.analytics_warehouse import (
    DqCheckOut,
    ExploreResponse,
    GovernedDatasetOut,
    IngestionRunOut,
    IngestionTriggerRequest,
    LineageEdgeOut,
    MetricCatalogOut,
    PlatformOverviewOut,
    ReconResponse,
    ScheduledReportCreate,
    ScheduledReportOut,
)
from investhome_api.services.analytics_warehouse import (
    get_platform_overview,
    list_governed_datasets,
    list_ingestion_runs,
    list_lineage,
    list_metric_catalog,
    reconcile_certified_subset,
    run_dq_suite,
    run_warehouse_ingestion,
)
from investhome_api.services.analytics_warehouse.platform import (
    explore_dataset,
    list_dq_results,
    log_export_audit,
)
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/analytics/warehouse", tags=["analytics-warehouse"])

_VIEW = Depends(require_permission("analytics", "view"))
_MANAGE = Depends(require_permission("analytics", "manage"))
_EXPORT = Depends(require_permission("analytics", "export"))


def _require_data_platform_admin(user: User) -> None:
    """Data-platform routes: analytics.manage OR users.manage (superadmin path)."""
    if user_has_permission(user, "analytics", "manage"):
        return
    if user_has_permission(user, "users", "manage"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="data_platform_admin_required")


@router.get("/overview", response_model=PlatformOverviewOut)
def warehouse_overview(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> dict:
    _require_data_platform_admin(user)
    raw = get_platform_overview(db)
    return {
        "schema_name": raw["schema"],
        "isolation": raw["isolation"],
        "oltp_queries_replaced": raw["oltp_queries_replaced"],
        "reporting_timezones": raw["reporting_timezones"],
        "supported_currencies": raw["supported_currencies"],
        "reporting_currencies": raw["reporting_currencies"],
        "last_run": raw["last_run"],
        "ingestion_counts": raw["ingestion_counts"],
        "metric_catalog": raw["metric_catalog"],
        "row_counts": raw["row_counts"],
        "cost_estimate_monthly_usd": raw["cost_estimate_monthly_usd"],
    }


@router.get("/ingestion-runs", response_model=list[IngestionRunOut])
def get_ingestion_runs(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[IngestionRunOut]:
    _require_data_platform_admin(user)
    return list_ingestion_runs(db, limit=limit)


@router.post("/ingestion-runs", response_model=IngestionRunOut, status_code=status.HTTP_201_CREATED)
def trigger_ingestion(
    body: IngestionTriggerRequest,
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> IngestionRunOut:
    _require_data_platform_admin(user)
    run = run_warehouse_ingestion(
        db,
        mode=body.mode,
        created_by=user.id,
        domains=body.domains,
    )
    return run


@router.get("/metric-catalog", response_model=list[MetricCatalogOut])
def get_metric_catalog(
    db: Session = Depends(get_db),
    user: User = _VIEW,
    certification: str | None = Query(default=None),
) -> list[MetricCatalogOut]:
    return list_metric_catalog(db, certification=certification)


@router.get("/lineage", response_model=list[LineageEdgeOut])
def get_lineage(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> list[LineageEdgeOut]:
    _require_data_platform_admin(user)
    return list_lineage(db)


@router.get("/data-quality", response_model=list[DqCheckOut])
def get_dq(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> list[DqCheckOut]:
    _require_data_platform_admin(user)
    return list_dq_results(db)


@router.post("/data-quality/run", response_model=list[DqCheckOut])
def run_dq(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> list[DqCheckOut]:
    _require_data_platform_admin(user)
    rows = run_dq_suite(db)
    db.commit()
    return rows


@router.get("/reconciliation", response_model=ReconResponse)
def get_reconciliation(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> ReconResponse:
    _require_data_platform_admin(user)
    return ReconResponse(**reconcile_certified_subset(db))


@router.get("/datasets", response_model=list[GovernedDatasetOut])
def get_datasets(
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> list[GovernedDatasetOut]:
    return list_governed_datasets(db)


@router.get("/explore/{dataset_key}", response_model=ExploreResponse)
def explore(
    dataset_key: str,
    db: Session = Depends(get_db),
    user: User = _VIEW,
    limit: int = Query(default=100, ge=1, le=500),
) -> ExploreResponse:
    ds_list = list_governed_datasets(db)
    ds = next((d for d in ds_list if d.dataset_key == dataset_key), None)
    if ds:
        # Enforce dataset permission pair resource:action
        perm = (ds.requires_permission or "analytics:view").split(":")
        if len(perm) == 2 and not user_has_permission(user, perm[0], perm[1]):
            if not user_has_permission(user, "analytics", "view"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="dataset_permission_denied")
    result = explore_dataset(db, dataset_key=dataset_key, limit=limit)
    if result.get("error") == "dataset_not_found_or_disabled":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return ExploreResponse(**result)


@router.post("/exports/audit", status_code=status.HTTP_201_CREATED)
def audit_export(
    dataset_key: str = Query(...),
    format: str = Query(default="csv"),
    metric_keys: str | None = Query(default=None),
    row_count: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = _EXPORT,
) -> dict:
    keys = [k.strip() for k in metric_keys.split(",") if k.strip()] if metric_keys else None
    row = log_export_audit(
        db,
        user_id=user.id,
        dataset_key=dataset_key,
        fmt=format,
        metric_keys=keys,
        row_count=row_count,
        permission_checked="analytics:export",
    )
    return {"id": str(row.id), "created_at": row.created_at.isoformat() if row.created_at else None}


@router.get("/scheduled-reports", response_model=list[ScheduledReportOut])
def list_scheduled(
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> list[ScheduledReportOut]:
    _require_data_platform_admin(user)
    return list(db.scalars(select(WhScheduledReport).order_by(WhScheduledReport.created_at.desc())).all())


@router.post("/scheduled-reports", response_model=ScheduledReportOut, status_code=status.HTTP_201_CREATED)
def create_scheduled(
    body: ScheduledReportCreate,
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> ScheduledReportOut:
    _require_data_platform_admin(user)
    # Only governed datasets
    allowed = {d.dataset_key for d in list_governed_datasets(db)}
    if body.dataset_key not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ungoverned_dataset")
    row = WhScheduledReport(
        name=body.name,
        dataset_key=body.dataset_key,
        metric_keys_json=body.metric_keys,
        cron_expr=body.cron_expr,
        format=body.format,
        recipients_json=body.recipients,
        enabled=body.enabled,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
