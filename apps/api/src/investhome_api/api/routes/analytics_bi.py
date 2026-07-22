"""Business Intelligence aggregation API — Product Polish P9."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.analytics_bi import (
    BiAlertThresholdCreate,
    BiAlertThresholdOut,
    BiDomainResponse,
    BiFilters,
    BiOverviewResponse,
    BiSavedReportCreate,
    BiSavedReportOut,
    BiSavedReportUpdate,
    DataQualityResponse,
    MetricDefinitionOut,
)
from investhome_api.services import analytics_bi_service as service

router = APIRouter(prefix="/analytics", tags=["business-intelligence"])

_VIEW = Depends(require_permission("analytics", "view"))
_EXPORT = Depends(require_permission("analytics", "export"))
_MANAGE = Depends(require_permission("analytics", "manage"))


def _default_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=29), today


def _parse_filters(
    date_from: date | None,
    date_to: date | None,
    comparison: str,
    workspace: str | None,
    project_id: UUID | None,
    assigned_to: str | None,
    lead_source: str | None,
    investor_id: UUID | None,
    campaign_id: UUID | None,
    currency: str | None,
    status_filter: str | None,
    preset: str | None,
) -> BiFilters:
    default_from, default_to = _default_range()
    today = date.today()
    if preset == "today":
        date_from, date_to = today, today
    elif preset == "7d":
        date_from, date_to = today - timedelta(days=6), today
    elif preset == "30d":
        date_from, date_to = today - timedelta(days=29), today
    elif preset == "quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        date_from, date_to = date(today.year, quarter_month, 1), today
    elif preset == "ytd":
        date_from, date_to = date(today.year, 1, 1), today

    parsed_from = date_from or default_from
    parsed_to = date_to or default_to
    if parsed_from > parsed_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be on or before date_to",
        )
    return BiFilters(
        date_from=parsed_from,
        date_to=parsed_to,
        comparison="previous_period" if comparison == "previous_period" else "none",
        workspace=workspace,
        project_id=project_id,
        assigned_to=assigned_to.strip() if assigned_to else None,
        lead_source=lead_source,
        investor_id=investor_id,
        campaign_id=campaign_id,
        currency=currency.upper() if currency else None,
        status=status_filter,
        preset=preset,
    )


def _filter_depends(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    comparison: str = Query(default="previous_period"),
    workspace: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    assigned_to: str | None = Query(default=None, max_length=255),
    lead_source: str | None = Query(default=None, max_length=255),
    investor_id: UUID | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    status_filter: str | None = Query(default=None, alias="status", max_length=64),
    preset: str | None = Query(default=None),
) -> BiFilters:
    return _parse_filters(
        date_from,
        date_to,
        comparison,
        workspace,
        project_id,
        assigned_to,
        lead_source,
        investor_id,
        campaign_id,
        currency,
        status_filter,
        preset,
    )


@router.get("/metrics", response_model=list[MetricDefinitionOut])
def list_metric_registry(
    domain: str | None = Query(default=None),
    _user: User = _VIEW,
) -> list[MetricDefinitionOut]:
    return service.registry_payload(domain=domain)


@router.get("/overview", response_model=BiOverviewResponse)
def get_bi_overview(
    filters: BiFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> BiOverviewResponse:
    return service.build_overview(db, user, filters)


@router.get("/domains/{domain}", response_model=BiDomainResponse)
def get_bi_domain(
    domain: str,
    filters: BiFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> BiDomainResponse:
    allowed = {
        "executive",
        "sales",
        "marketing",
        "investor",
        "finance",
        "project",
        "website",
        "operational",
    }
    if domain not in allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown domain")
    return service.build_domain(db, user, domain, filters)


@router.get("/data-quality", response_model=DataQualityResponse)
def get_data_quality(
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> DataQualityResponse:
    return service.build_data_quality(db, user)


@router.get("/saved-reports", response_model=list[BiSavedReportOut])
def list_saved_reports(
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> list[BiSavedReportOut]:
    return service.list_saved_reports(db, user)


@router.post("/saved-reports", response_model=BiSavedReportOut, status_code=201)
def create_saved_report(
    payload: BiSavedReportCreate,
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> BiSavedReportOut:
    try:
        return service.create_saved_report(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/saved-reports/{report_id}", response_model=BiSavedReportOut)
def update_saved_report(
    report_id: UUID,
    payload: BiSavedReportUpdate,
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> BiSavedReportOut:
    try:
        return service.update_saved_report(db, user, report_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/saved-reports/{report_id}", status_code=204)
def delete_saved_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    user: User = _VIEW,
) -> Response:
    try:
        service.delete_saved_report(db, user, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed") from exc
    return Response(status_code=204)


@router.get("/alert-thresholds", response_model=list[BiAlertThresholdOut])
def list_alert_thresholds(
    db: Session = Depends(get_db),
    _user: User = _VIEW,
) -> list[BiAlertThresholdOut]:
    return service.list_alert_thresholds(db)


@router.post("/alert-thresholds", response_model=BiAlertThresholdOut, status_code=201)
def create_alert_threshold(
    payload: BiAlertThresholdCreate,
    db: Session = Depends(get_db),
    user: User = _MANAGE,
) -> BiAlertThresholdOut:
    try:
        return service.create_alert_threshold(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/export")
def export_bi(
    format: str = Query(default="csv"),
    domain: str = Query(default="executive"),
    metric_keys: list[str] = Query(default=[]),
    filters: BiFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = _EXPORT,
) -> Response:
    if format not in {"csv", "xlsx", "pdf", "print"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format")
    # xlsx/pdf/print fall back to CSV payload with honest metadata — full binary writers can follow
    csv_text = service.export_metrics_csv(db, user, filters, metric_keys)
    if format == "csv":
        media = "text/csv; charset=utf-8"
        filename = f"bi_{domain}.csv"
    elif format == "print":
        media = "text/plain; charset=utf-8"
        filename = f"bi_{domain}.txt"
    else:
        # Honest fallback: return CSV bytes labeled for requested format until binary exporters land
        media = "text/csv; charset=utf-8"
        filename = f"bi_{domain}.{format}.csv"
    return Response(
        content=csv_text,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Format": format,
            "X-Export-Domain": domain,
        },
    )
