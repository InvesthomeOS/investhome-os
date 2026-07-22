"""Campaign performance metrics and report rollups — Sprint 8A3."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead
from investhome_api.models.marketing import CampaignBudgetAllocation, MarketingCampaign, MarketingCampaignStatus
from investhome_api.models.marketing_lead_attribution import MarketingLeadAttribution
from investhome_api.models.project import Project
from investhome_api.models.sales import CLOSED_OPPORTUNITY_STAGES, OpportunityStage, SalesOpportunity
from investhome_api.schemas.marketing_performance import (
    CampaignLeadBreakdownItem,
    CampaignLeadBreakdownResponse,
    CampaignPerformanceDetail,
    CampaignPerformanceListResponse,
    CampaignPerformanceMetrics,
    ChannelPerformanceItem,
    ChannelPerformanceResponse,
    MarketingPerformanceOverview,
    PerformanceFilters,
    PerformanceMetricValue,
    ProjectPerformanceItem,
    ProjectPerformanceResponse,
)
from investhome_api.services.marketing.lead_status_mapping import (
    AttributionLeadStatus,
    is_qualified_status,
    resolve_lead_attribution_status,
)


def _ready(value: Decimal | int | float | str | None) -> PerformanceMetricValue:
    return PerformanceMetricValue(value=value, state="ready")


def _unavailable(reason: str) -> PerformanceMetricValue:
    return PerformanceMetricValue(value=None, state="unavailable", reason=reason)


def _empty(reason: str = "no_data") -> PerformanceMetricValue:
    return PerformanceMetricValue(value=None, state="empty", reason=reason)


def _ratio(numerator: Decimal | int | float, denominator: Decimal | int | float) -> Decimal | None:
    den = Decimal(str(denominator))
    if den == 0:
        return None
    return Decimal(str(numerator)) / den


def _pct(numerator: int, denominator: int) -> PerformanceMetricValue:
    ratio = _ratio(numerator, denominator)
    if ratio is None:
        return _unavailable("division_by_zero")
    return _ready(float(round(ratio * 100, 2)))


def _cost_per(spend: Decimal | None, count: int) -> PerformanceMetricValue:
    if spend is None:
        return _unavailable("no_spend_data")
    if count <= 0:
        return _unavailable("division_by_zero")
    return _ready(float(round(spend / Decimal(count), 2)))


def _roi(revenue: Decimal | None, spend: Decimal | None) -> PerformanceMetricValue:
    if spend is None:
        return _unavailable("no_spend_data")
    if revenue is None:
        return _unavailable("no_revenue_data")
    if spend == 0:
        return _unavailable("division_by_zero")
    return _ready(float(round((revenue - spend) / spend, 4)))


def _campaign_spent(db: Session, campaign_id: UUID) -> Decimal | None:
    has_rows = db.scalar(
        select(func.count()).select_from(CampaignBudgetAllocation).where(
            CampaignBudgetAllocation.campaign_id == campaign_id
        )
    )
    if not has_rows:
        return None
    total = db.scalar(
        select(func.coalesce(func.sum(CampaignBudgetAllocation.spent_amount), 0)).where(
            CampaignBudgetAllocation.campaign_id == campaign_id
        )
    )
    return Decimal(str(total or 0))


def _batch_spent(db: Session, campaign_ids: list[UUID]) -> dict[UUID, Decimal | None]:
    if not campaign_ids:
        return {}
    counts = dict(
        db.execute(
            select(CampaignBudgetAllocation.campaign_id, func.count())
            .where(CampaignBudgetAllocation.campaign_id.in_(campaign_ids))
            .group_by(CampaignBudgetAllocation.campaign_id)
        ).all()
    )
    totals = dict(
        db.execute(
            select(
                CampaignBudgetAllocation.campaign_id,
                func.coalesce(func.sum(CampaignBudgetAllocation.spent_amount), 0),
            )
            .where(CampaignBudgetAllocation.campaign_id.in_(campaign_ids))
            .group_by(CampaignBudgetAllocation.campaign_id)
        ).all()
    )
    result: dict[UUID, Decimal | None] = {}
    for cid in campaign_ids:
        if not counts.get(cid):
            result[cid] = None
        else:
            result[cid] = Decimal(str(totals.get(cid, 0)))
    return result


def _apply_campaign_filters(query, filters: PerformanceFilters):
    query = query.where(MarketingCampaign.archived_at.is_(None))
    if filters.campaign_id:
        query = query.where(MarketingCampaign.id == filters.campaign_id)
    if filters.project_id:
        query = query.where(
            or_(
                MarketingCampaign.target_project_id == filters.project_id,
                cast_json_contains_project(filters.project_id),
            )
        )
    if filters.campaign_type:
        query = query.where(MarketingCampaign.campaign_type == filters.campaign_type)
    if filters.owner_user_id:
        query = query.where(MarketingCampaign.owner_user_id == filters.owner_user_id)
    if filters.status:
        query = query.where(MarketingCampaign.status == filters.status)
    if filters.company_id:
        query = query.where(MarketingCampaign.company_id == filters.company_id)
    return query


def cast_json_contains_project(project_id: UUID):
    """Match project_ids JSON array containing the project id string."""
    from sqlalchemy import String, cast

    return cast(MarketingCampaign.project_ids, String).ilike(f'%"{project_id}"%')


def _attributions_for_campaigns(
    db: Session,
    campaign_ids: list[UUID],
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[MarketingLeadAttribution]:
    if not campaign_ids:
        return []
    query = select(MarketingLeadAttribution).where(
        MarketingLeadAttribution.campaign_id.in_(campaign_ids)
    )
    if date_from is not None:
        query = query.where(
            or_(
                MarketingLeadAttribution.first_touch_at >= date_from,
                MarketingLeadAttribution.created_at >= date_from,
            )
        )
    if date_to is not None:
        query = query.where(
            or_(
                MarketingLeadAttribution.first_touch_at <= date_to,
                MarketingLeadAttribution.created_at <= date_to,
            )
        )
    return list(db.scalars(query).all())


def _opportunity_stats(
    db: Session, lead_ids: list[UUID]
) -> tuple[dict[UUID, list[SalesOpportunity]], dict[str, Decimal | None]]:
    if not lead_ids:
        return {}, {"estimated": None, "confirmed": None, "open": 0, "won": 0, "lost": 0}

    opps = list(
        db.scalars(
            select(SalesOpportunity).where(
                SalesOpportunity.lead_id.in_(lead_ids),
                SalesOpportunity.archived_at.is_(None),
            )
        ).all()
    )
    by_lead: dict[UUID, list[SalesOpportunity]] = defaultdict(list)
    open_count = won_count = lost_count = 0
    estimated_total = Decimal("0")
    confirmed_total = Decimal("0")
    has_estimated = False
    has_confirmed = False

    for opp in opps:
        if opp.lead_id is None:
            continue
        by_lead[opp.lead_id].append(opp)
        if opp.stage == OpportunityStage.WON:
            won_count += 1
            if opp.expected_revenue is not None:
                confirmed_total += Decimal(str(opp.expected_revenue))
                has_confirmed = True
        elif opp.stage in {OpportunityStage.LOST, OpportunityStage.DORMANT, OpportunityStage.CANCELLED}:
            lost_count += 1
        elif opp.stage not in CLOSED_OPPORTUNITY_STAGES:
            open_count += 1
            if opp.expected_revenue is not None:
                estimated_total += Decimal(str(opp.expected_revenue))
                has_estimated = True

    return by_lead, {
        "estimated": estimated_total if has_estimated else None,
        "confirmed": confirmed_total if has_confirmed else None,
        "open": open_count,
        "won": won_count,
        "lost": lost_count,
    }


def compute_campaign_metrics(
    db: Session,
    campaign: MarketingCampaign,
    *,
    attributions: list[MarketingLeadAttribution] | None = None,
    spent: Decimal | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> CampaignPerformanceMetrics:
    if attributions is None:
        attributions = _attributions_for_campaigns(
            db, [campaign.id], date_from=date_from, date_to=date_to
        )
    if spent is None:
        spent = _campaign_spent(db, campaign.id)

    lead_ids = [a.lead_id for a in attributions]
    status_counts: dict[str, int] = defaultdict(int)
    new_leads = qualified = converted = 0

    if lead_ids:
        leads = {lead.id: lead for lead in db.scalars(select(Lead).where(Lead.id.in_(lead_ids))).all()}
        for attrib in attributions:
            lead = leads.get(attrib.lead_id)
            if lead is None:
                continue
            status = resolve_lead_attribution_status(db, attrib.lead_id)
            status_counts[status] += 1
            if status == AttributionLeadStatus.NEW:
                new_leads += 1
            if is_qualified_status(status):
                qualified += 1
            if status == AttributionLeadStatus.CONVERTED:
                converted += 1

    _, opp_stats = _opportunity_stats(db, lead_ids)
    total_leads = len(attributions)
    planned = campaign.budget_amount

    estimated_revenue = opp_stats["estimated"]
    confirmed_revenue = opp_stats["confirmed"]

    primary_channel = None
    if campaign.primary_channel is not None:
        primary_channel = (
            campaign.primary_channel.value
            if hasattr(campaign.primary_channel, "value")
            else str(campaign.primary_channel)
        )

    return CampaignPerformanceMetrics(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        campaign_type=campaign.campaign_type.value if campaign.campaign_type else None,
        primary_channel=primary_channel,
        status=campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status),
        target_project_id=campaign.target_project_id,
        owner_user_id=campaign.owner_user_id,
        planned_budget=_ready(float(planned)) if planned is not None else _empty("no_budget_data"),
        actual_spend=_ready(float(spent)) if spent is not None else _empty("no_spend_data"),
        total_leads=_ready(total_leads),
        new_leads=_ready(new_leads),
        qualified_leads=_ready(qualified),
        converted_leads=_ready(converted),
        open_opportunities=_ready(int(opp_stats["open"])),
        won_opportunities=_ready(int(opp_stats["won"])),
        lost_opportunities=_ready(int(opp_stats["lost"])),
        conversion_rate=_pct(converted, total_leads) if total_leads else _unavailable("no_leads"),
        cpl=_cost_per(spent, total_leads),
        cpql=_cost_per(spent, qualified),
        cpc=_cost_per(spent, converted),
        estimated_revenue=(
            _ready(float(estimated_revenue)) if estimated_revenue is not None else _unavailable("no_revenue_data")
        ),
        confirmed_revenue=(
            _ready(float(confirmed_revenue)) if confirmed_revenue is not None else _unavailable("no_revenue_data")
        ),
        estimated_roi=_roi(estimated_revenue, spent),
        confirmed_roi=_roi(confirmed_revenue, spent),
    )


def list_campaign_performance(
    db: Session,
    *,
    filters: PerformanceFilters | None = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> CampaignPerformanceListResponse:
    filters = filters or PerformanceFilters()
    query = _apply_campaign_filters(select(MarketingCampaign), filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    campaigns = list(
        db.scalars(
            query.order_by(MarketingCampaign.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    campaign_ids = [c.id for c in campaigns]
    spent_map = _batch_spent(db, campaign_ids)
    attributions = _attributions_for_campaigns(
        db, campaign_ids, date_from=filters.date_from, date_to=filters.date_to
    )
    by_campaign: dict[UUID, list[MarketingLeadAttribution]] = defaultdict(list)
    for row in attributions:
        if row.campaign_id:
            by_campaign[row.campaign_id].append(row)

    items = [
        compute_campaign_metrics(
            db,
            campaign,
            attributions=by_campaign.get(campaign.id, []),
            spent=spent_map.get(campaign.id),
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        for campaign in campaigns
    ]

    if sort_by:
        reverse = sort_dir != "asc"

        def sort_key(item: CampaignPerformanceMetrics):
            metric = getattr(item, sort_by, None)
            if isinstance(metric, PerformanceMetricValue):
                return (metric.value is None, metric.value or 0)
            return (False, metric or "")

        items.sort(key=sort_key, reverse=reverse)

    return CampaignPerformanceListResponse(items=items, page=page, page_size=page_size, total=total)


def get_campaign_performance_detail(
    db: Session,
    campaign: MarketingCampaign,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> CampaignPerformanceDetail:
    attributions = _attributions_for_campaigns(
        db, [campaign.id], date_from=date_from, date_to=date_to
    )
    metrics = compute_campaign_metrics(
        db, campaign, attributions=attributions, date_from=date_from, date_to=date_to
    )

    status_breakdown: dict[str, int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)
    utm_counts: dict[str, int] = defaultdict(int)
    trend: dict[str, int] = defaultdict(int)

    lead_ids = [a.lead_id for a in attributions]
    leads = {
        lead.id: lead
        for lead in db.scalars(select(Lead).where(Lead.id.in_(lead_ids))).all()
    } if lead_ids else {}

    recent: list[CampaignLeadBreakdownItem] = []
    for attrib in sorted(attributions, key=lambda a: a.created_at, reverse=True):
        lead = leads.get(attrib.lead_id)
        status = resolve_lead_attribution_status(db, attrib.lead_id) if lead else AttributionLeadStatus.NEW
        status_breakdown[status] += 1
        source = attrib.attribution_source
        source_key = source.value if hasattr(source, "value") else str(source or "other")
        source_counts[source_key] += 1
        utm_key = attrib.utm_source or "unassigned"
        utm_counts[utm_key] += 1
        day = (attrib.first_touch_at or attrib.created_at).date().isoformat()
        trend[day] += 1
        if len(recent) < 10 and lead is not None:
            recent.append(
                CampaignLeadBreakdownItem(
                    lead_id=lead.id,
                    full_name=lead.full_name,
                    email=lead.email,
                    status=lead.status.value if hasattr(lead.status, "value") else str(lead.status),
                    attribution_status=status,
                    attribution_source=source_key,
                    utm_source=attrib.utm_source,
                    first_touch_at=attrib.first_touch_at,
                    converted_at=attrib.converted_at,
                    created_at=attrib.created_at,
                )
            )

    spent = metrics.actual_spend.value
    budget = metrics.planned_budget.value
    return CampaignPerformanceDetail(
        metrics=metrics,
        lead_trend=[{"date": day, "leads": count} for day, count in sorted(trend.items())],
        status_breakdown=dict(status_breakdown),
        spend_vs_budget={
            "planned": str(budget) if budget is not None else None,
            "spent": str(spent) if spent is not None else None,
            "remaining": (
                str(Decimal(str(budget)) - Decimal(str(spent)))
                if budget is not None and spent is not None
                else None
            ),
        },
        top_sources=[{"source": k, "count": v} for k, v in sorted(source_counts.items(), key=lambda x: -x[1])],
        utm_breakdown=[{"utm_source": k, "count": v} for k, v in sorted(utm_counts.items(), key=lambda x: -x[1])],
        recent_leads=recent,
    )


def get_campaign_lead_breakdown(
    db: Session,
    campaign_id: UUID,
    *,
    page: int = 1,
    page_size: int = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> CampaignLeadBreakdownResponse:
    attributions = _attributions_for_campaigns(
        db, [campaign_id], date_from=date_from, date_to=date_to
    )
    total = len(attributions)
    status_breakdown: dict[str, int] = defaultdict(int)
    slice_rows = attributions[(page - 1) * page_size : page * page_size]
    lead_ids = [a.lead_id for a in attributions]
    leads = {
        lead.id: lead
        for lead in db.scalars(select(Lead).where(Lead.id.in_(lead_ids))).all()
    } if lead_ids else {}

    items: list[CampaignLeadBreakdownItem] = []
    for attrib in attributions:
        status = resolve_lead_attribution_status(db, attrib.lead_id)
        status_breakdown[status] += 1

    for attrib in slice_rows:
        lead = leads.get(attrib.lead_id)
        if lead is None:
            continue
        source = attrib.attribution_source
        source_key = source.value if hasattr(source, "value") else str(source or "other")
        items.append(
            CampaignLeadBreakdownItem(
                lead_id=lead.id,
                full_name=lead.full_name,
                email=lead.email,
                status=lead.status.value if hasattr(lead.status, "value") else str(lead.status),
                attribution_status=resolve_lead_attribution_status(db, lead.id),
                attribution_source=source_key,
                utm_source=attrib.utm_source,
                first_touch_at=attrib.first_touch_at,
                converted_at=attrib.converted_at,
                created_at=attrib.created_at,
            )
        )

    return CampaignLeadBreakdownResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        status_breakdown=dict(status_breakdown),
    )


def build_performance_overview(
    db: Session,
    *,
    filters: PerformanceFilters | None = None,
) -> MarketingPerformanceOverview:
    """Alias used by workspace overview and routes."""
    return get_performance_overview(db, filters=filters)


def get_performance_overview(
    db: Session,
    *,
    filters: PerformanceFilters | None = None,
) -> MarketingPerformanceOverview:
    filters = filters or PerformanceFilters()
    query = _apply_campaign_filters(select(MarketingCampaign), filters)
    campaigns = list(db.scalars(query).all())
    campaign_ids = [c.id for c in campaigns]
    active = sum(1 for c in campaigns if c.status == MarketingCampaignStatus.ACTIVE)
    spent_map = _batch_spent(db, campaign_ids)
    attributions = _attributions_for_campaigns(
        db, campaign_ids, date_from=filters.date_from, date_to=filters.date_to
    )

    budget_values = [c.budget_amount for c in campaigns if c.budget_amount is not None]
    spend_values = [v for v in spent_map.values() if v is not None]
    total_spend = sum(spend_values, Decimal("0")) if spend_values else None

    qualified = converted = 0
    for attrib in attributions:
        status = resolve_lead_attribution_status(db, attrib.lead_id)
        if is_qualified_status(status):
            qualified += 1
        if status == AttributionLeadStatus.CONVERTED:
            converted += 1

    total_leads = len(attributions)
    attention = sum(
        1
        for c in campaigns
        if c.status == MarketingCampaignStatus.ACTIVE
        and (
            c.budget_amount is None
            or spent_map.get(c.id) is None
            or (c.budget_amount is not None and spent_map.get(c.id) is not None and spent_map[c.id] > c.budget_amount)
        )
    )

    currency = next((c.budget_currency for c in campaigns if c.budget_currency), None)
    avg_cpl = _cost_per(total_spend, total_leads)
    avg_conversion = _pct(converted, total_leads) if total_leads else _unavailable("no_leads")

    return MarketingPerformanceOverview(
        total_campaigns=_ready(len(campaigns)),
        active_campaigns=_ready(active),
        total_budget=_ready(float(sum(budget_values, Decimal("0")))) if budget_values else _empty("no_budget_data"),
        total_spend=_ready(float(total_spend)) if total_spend is not None else _empty("no_spend_data"),
        total_leads=_ready(total_leads),
        qualified_leads=_ready(qualified),
        converted_leads=_ready(converted),
        avg_cpl=avg_cpl,
        avg_conversion_rate=avg_conversion,
        campaigns_requiring_attention=_ready(attention),
        currency=currency,
    )


def get_channel_performance(
    db: Session,
    *,
    filters: PerformanceFilters | None = None,
) -> ChannelPerformanceResponse:
    filters = filters or PerformanceFilters()
    campaigns = list(db.scalars(_apply_campaign_filters(select(MarketingCampaign), filters)).all())
    campaign_ids = [c.id for c in campaigns]
    spent_map = _batch_spent(db, campaign_ids)
    attributions = _attributions_for_campaigns(
        db, campaign_ids, date_from=filters.date_from, date_to=filters.date_to
    )
    by_campaign: dict[UUID, list[MarketingLeadAttribution]] = defaultdict(list)
    for row in attributions:
        if row.campaign_id:
            by_campaign[row.campaign_id].append(row)

    groups: dict[str, dict] = defaultdict(
        lambda: {"campaign_count": 0, "spend": None, "leads": 0, "qualified": 0, "conversions": 0}
    )

    for campaign in campaigns:
        channel = "UNASSIGNED"
        if campaign.primary_channel is not None:
            raw = (
                campaign.primary_channel.value
                if hasattr(campaign.primary_channel, "value")
                else str(campaign.primary_channel)
            )
            channel = str(raw).upper()
        elif campaign.campaign_type is not None:
            raw = (
                campaign.campaign_type.value
                if hasattr(campaign.campaign_type, "value")
                else str(campaign.campaign_type)
            )
            channel = str(raw).upper()
        group = groups[channel]
        group["campaign_count"] += 1
        spent = spent_map.get(campaign.id)
        if spent is not None:
            group["spend"] = (group["spend"] or Decimal("0")) + spent
        for attrib in by_campaign.get(campaign.id, []):
            group["leads"] += 1
            status = resolve_lead_attribution_status(db, attrib.lead_id)
            if is_qualified_status(status):
                group["qualified"] += 1
            if status == AttributionLeadStatus.CONVERTED:
                group["conversions"] += 1

    items = []
    for channel, data in sorted(groups.items()):
        spend = data["spend"]
        leads = data["leads"]
        conversions = data["conversions"]
        items.append(
            ChannelPerformanceItem(
                channel=channel,
                campaign_count=data["campaign_count"],
                spend=_ready(float(spend)) if spend is not None else _empty("no_spend_data"),
                leads=_ready(leads),
                qualified_leads=_ready(data["qualified"]),
                conversions=_ready(conversions),
                cpl=_cost_per(spend, leads),
                conversion_rate=_pct(conversions, leads) if leads else _unavailable("no_leads"),
            )
        )
    return ChannelPerformanceResponse(items=items)


def get_project_performance(
    db: Session,
    *,
    filters: PerformanceFilters | None = None,
) -> ProjectPerformanceResponse:
    filters = filters or PerformanceFilters()
    campaigns = list(db.scalars(_apply_campaign_filters(select(MarketingCampaign), filters)).all())
    campaign_ids = [c.id for c in campaigns]
    spent_map = _batch_spent(db, campaign_ids)
    attributions = _attributions_for_campaigns(
        db, campaign_ids, date_from=filters.date_from, date_to=filters.date_to
    )
    by_campaign: dict[UUID, list[MarketingLeadAttribution]] = defaultdict(list)
    for row in attributions:
        if row.campaign_id:
            by_campaign[row.campaign_id].append(row)

    project_ids = {c.target_project_id for c in campaigns if c.target_project_id}
    projects = {
        p.id: p
        for p in db.scalars(select(Project).where(Project.id.in_(project_ids))).all()
    } if project_ids else {}

    groups: dict[UUID | None, dict] = defaultdict(
        lambda: {
            "campaign_count": 0,
            "spend": None,
            "leads": 0,
            "qualified": 0,
            "conversions": 0,
            "name": "Unassigned",
        }
    )

    for campaign in campaigns:
        key = campaign.target_project_id
        group = groups[key]
        group["campaign_count"] += 1
        if key and key in projects:
            group["name"] = projects[key].project_name
        elif key is None:
            group["name"] = "Unassigned"
        spent = spent_map.get(campaign.id)
        if spent is not None:
            group["spend"] = (group["spend"] or Decimal("0")) + spent
        for attrib in by_campaign.get(campaign.id, []):
            group["leads"] += 1
            status = resolve_lead_attribution_status(db, attrib.lead_id)
            if is_qualified_status(status):
                group["qualified"] += 1
            if status == AttributionLeadStatus.CONVERTED:
                group["conversions"] += 1

    items = []
    for project_id, data in sorted(groups.items(), key=lambda x: (x[0] is not None, str(x[0] or ""))):
        spend = data["spend"]
        leads = data["leads"]
        conversions = data["conversions"]
        items.append(
            ProjectPerformanceItem(
                project_id=project_id,
                project_name=data["name"],
                campaign_count=data["campaign_count"],
                spend=_ready(float(spend)) if spend is not None else _empty("no_spend_data"),
                leads=_ready(leads),
                qualified_leads=_ready(data["qualified"]),
                conversions=_ready(conversions),
                cpl=_cost_per(spend, leads),
                conversion_rate=_pct(conversions, leads) if leads else _unavailable("no_leads"),
            )
        )
    return ProjectPerformanceResponse(items=items)


def export_performance_csv(
    db: Session,
    *,
    report_type: str,
    filters: PerformanceFilters | None = None,
) -> str:
    filters = filters or PerformanceFilters()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if report_type == "campaign":
        data = list_campaign_performance(db, filters=filters, page=1, page_size=10_000)
        writer.writerow(
            [
                "campaign_id",
                "campaign_name",
                "campaign_type",
                "primary_channel",
                "status",
                "planned_budget",
                "actual_spend",
                "total_leads",
                "qualified_leads",
                "converted_leads",
                "conversion_rate",
                "cpl",
                "cpql",
                "cpc",
                "estimated_revenue",
                "confirmed_revenue",
                "estimated_roi",
                "confirmed_roi",
            ]
        )
        for item in data.items:
            writer.writerow(
                [
                    item.campaign_id,
                    item.campaign_name,
                    item.campaign_type,
                    item.primary_channel,
                    item.status,
                    item.planned_budget.value,
                    item.actual_spend.value,
                    item.total_leads.value,
                    item.qualified_leads.value,
                    item.converted_leads.value,
                    item.conversion_rate.value,
                    item.cpl.value,
                    item.cpql.value,
                    item.cpc.value,
                    item.estimated_revenue.value,
                    item.confirmed_revenue.value,
                    item.estimated_roi.value,
                    item.confirmed_roi.value,
                ]
            )
    elif report_type == "channel":
        data = get_channel_performance(db, filters=filters)
        writer.writerow(
            ["channel", "campaign_count", "spend", "leads", "qualified_leads", "conversions", "cpl", "conversion_rate"]
        )
        for item in data.items:
            writer.writerow(
                [
                    item.channel,
                    item.campaign_count,
                    item.spend.value,
                    item.leads.value,
                    item.qualified_leads.value,
                    item.conversions.value,
                    item.cpl.value,
                    item.conversion_rate.value,
                ]
            )
    elif report_type == "project":
        data = get_project_performance(db, filters=filters)
        writer.writerow(
            [
                "project_id",
                "project_name",
                "campaign_count",
                "spend",
                "leads",
                "qualified_leads",
                "conversions",
                "cpl",
                "conversion_rate",
            ]
        )
        for item in data.items:
            writer.writerow(
                [
                    item.project_id,
                    item.project_name,
                    item.campaign_count,
                    item.spend.value,
                    item.leads.value,
                    item.qualified_leads.value,
                    item.conversions.value,
                    item.cpl.value,
                    item.conversion_rate.value,
                ]
            )
    elif report_type == "lead_attribution":
        query = select(MarketingLeadAttribution)
        if filters.campaign_id:
            query = query.where(MarketingLeadAttribution.campaign_id == filters.campaign_id)
        if filters.company_id:
            query = query.where(MarketingLeadAttribution.company_id == filters.company_id)
        if filters.date_from:
            query = query.where(MarketingLeadAttribution.created_at >= filters.date_from)
        if filters.date_to:
            query = query.where(MarketingLeadAttribution.created_at <= filters.date_to)
        rows = list(db.scalars(query.order_by(MarketingLeadAttribution.created_at.desc())).all())
        writer.writerow(
            [
                "lead_id",
                "campaign_id",
                "attribution_source",
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_term",
                "utm_content",
                "first_touch_at",
                "converted_at",
                "attribution_status",
                "created_at",
            ]
        )
        for row in rows:
            source = row.attribution_source
            source_key = source.value if hasattr(source, "value") else str(source)
            writer.writerow(
                [
                    row.lead_id,
                    row.campaign_id,
                    source_key,
                    row.utm_source,
                    row.utm_medium,
                    row.utm_campaign,
                    row.utm_term,
                    row.utm_content,
                    row.first_touch_at.isoformat() if row.first_touch_at else None,
                    row.converted_at.isoformat() if row.converted_at else None,
                    resolve_lead_attribution_status(db, row.lead_id),
                    row.created_at.isoformat() if row.created_at else None,
                ]
            )
    else:
        raise ValueError(f"Unsupported report type: {report_type}")

    return buffer.getvalue()


def attributed_lead_count(db: Session, campaign_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(MarketingLeadAttribution).where(
                MarketingLeadAttribution.campaign_id == campaign_id
            )
        )
        or 0
    )
