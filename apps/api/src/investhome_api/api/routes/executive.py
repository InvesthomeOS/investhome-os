"""Executive dashboard API routes."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.executive import (
    ExecutiveActivityResponse,
    ExecutiveAiInsightsResponse,
    ExecutiveApprovalsResponse,
    ExecutiveAttentionResponse,
    ExecutiveConstructionSnapshotResponse,
    ExecutiveDeadlinesResponse,
    ExecutiveFilters,
    ExecutiveFinancialOverviewResponse,
    ExecutiveInvestorOverviewResponse,
    ExecutiveLeadsPipelineResponse,
    ExecutiveProjectPortfolioResponse,
    ExecutiveSummaryResponse,
)
from investhome_api.services.executive_service import (
    build_activity_feed,
    build_ai_insights,
    build_approvals,
    build_attention_items,
    build_construction_snapshot,
    build_deadlines,
    build_executive_summary,
    build_financial_overview,
    build_investor_overview,
    build_leads_pipeline,
    build_project_portfolio,
)

router = APIRouter(
    prefix="/executive",
    tags=["executive"],
    dependencies=[Depends(require_permission("executive", "view"))],
)


def _default_date_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=29), today


def _parse_filters(
    date_from: date | None,
    date_to: date | None,
    project_id: UUID | None,
    assigned_to: str | None,
    currency: str | None,
) -> ExecutiveFilters:
    default_from, default_to = _default_date_range()
    parsed_from = date_from or default_from
    parsed_to = date_to or default_to
    if parsed_from > parsed_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be on or before date_to",
        )
    return ExecutiveFilters(
        date_from=parsed_from,
        date_to=parsed_to,
        project_id=project_id,
        assigned_to=assigned_to.strip() if assigned_to else None,
        currency=currency.upper() if currency else None,
    )


def _filter_depends(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    assigned_to: str | None = Query(default=None, max_length=255),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
) -> ExecutiveFilters:
    return _parse_filters(date_from, date_to, project_id, assigned_to, currency)


@router.get("/summary", response_model=ExecutiveSummaryResponse)
def get_executive_summary(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecutiveSummaryResponse:
    return build_executive_summary(db, filters, user)


@router.get("/attention", response_model=ExecutiveAttentionResponse)
def get_executive_attention(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveAttentionResponse:
    return build_attention_items(db, filters)


@router.get("/leads-pipeline", response_model=ExecutiveLeadsPipelineResponse)
def get_executive_leads_pipeline(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveLeadsPipelineResponse:
    return build_leads_pipeline(db, filters)


@router.get("/investor-overview", response_model=ExecutiveInvestorOverviewResponse)
def get_executive_investor_overview(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveInvestorOverviewResponse:
    return build_investor_overview(db, filters)


@router.get("/project-portfolio", response_model=ExecutiveProjectPortfolioResponse)
def get_executive_project_portfolio(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveProjectPortfolioResponse:
    return build_project_portfolio(db, filters)


@router.get("/financial-overview", response_model=ExecutiveFinancialOverviewResponse)
def get_executive_financial_overview(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveFinancialOverviewResponse:
    return build_financial_overview(db, filters)


@router.get("/deadlines", response_model=ExecutiveDeadlinesResponse)
def get_executive_deadlines(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveDeadlinesResponse:
    return build_deadlines(db, filters)


@router.get("/activity", response_model=ExecutiveActivityResponse)
def get_executive_activity(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecutiveActivityResponse:
    return build_activity_feed(db, filters, user)


@router.get("/approvals", response_model=ExecutiveApprovalsResponse)
def get_executive_approvals(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecutiveApprovalsResponse:
    return build_approvals(db, filters, user)


@router.get("/construction-snapshot", response_model=ExecutiveConstructionSnapshotResponse)
def get_executive_construction_snapshot(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
) -> ExecutiveConstructionSnapshotResponse:
    return build_construction_snapshot(db, filters)


@router.get("/ai-insights", response_model=ExecutiveAiInsightsResponse)
def get_executive_ai_insights(
    filters: ExecutiveFilters = Depends(_filter_depends),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecutiveAiInsightsResponse:
    return build_ai_insights(db, filters, user)
