"""Allowlisted context builder for AI Marketing Assistant — no unrestricted DB access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingAudience, MarketingCampaign
from investhome_api.models.marketing_content_studio import MarketingAsset
from investhome_api.models.project import Project
from investhome_api.schemas.marketing_performance import PerformanceFilters
from investhome_api.services.marketing.asset_service import AI_PREP_KEYS
from investhome_api.services.marketing.campaign_performance_service import (
    get_campaign_performance_detail,
    get_channel_performance,
    get_performance_overview,
    list_campaign_performance,
)

# Approved project fields only — never invent financial projections as marketing facts.
APPROVED_PROJECT_FIELDS = (
    "id",
    "project_code",
    "project_name",
    "city",
    "state",
    "country",
    "address",
    "project_type",
    "development_type",
    "project_status",
    "development_stage",
    "total_units",
    "residential_units",
    "commercial_units",
    "description",
    "target_completion_date",
    "currency",
)

# Explicitly excluded from AI context (private / inventable risk).
EXCLUDED_PROJECT_FIELDS = (
    "acquisition_price",
    "land_cost",
    "construction_budget",
    "soft_cost_budget",
    "total_development_cost",
    "current_project_value",
    "projected_sale_value",
    "equity_required",
    "equity_raised",
    "debt_amount",
    "loan_to_cost",
    "projected_revenue",
    "projected_profit",
    "projected_roi",
    "projected_irr",
    "notes",
)


def _enum_val(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _metric_dict(metric: Any) -> dict[str, Any]:
    if metric is None:
        return {"value": None, "state": "unavailable", "reason": "missing"}
    return {
        "value": metric.value,
        "state": getattr(metric, "state", "ready"),
        "reason": getattr(metric, "reason", None),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return _enum_val(value)


def _project_summary(project: Project) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    missing: list[str] = []
    for field in APPROVED_PROJECT_FIELDS:
        value = getattr(project, field, None)
        summary[field] = _json_safe(value)
        if value is None and field in {
            "city",
            "country",
            "project_type",
            "description",
            "target_completion_date",
            "total_units",
        }:
            missing.append(field)
    summary["_excluded_fields_note"] = (
        "Private financial projections and investor fields are not included in AI context."
    )
    summary["_missing_approved_fields"] = missing
    return summary


def _campaign_summary(campaign: MarketingCampaign) -> dict[str, Any]:
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "code": campaign.code,
        "status": _enum_val(campaign.status),
        "objective": _enum_val(campaign.objective),
        "campaign_type": _enum_val(campaign.campaign_type),
        "primary_channel": _enum_val(getattr(campaign, "primary_channel", None)),
        "company_id": str(campaign.company_id) if campaign.company_id else None,
        "target_project_id": str(campaign.target_project_id) if campaign.target_project_id else None,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "budget_amount": str(campaign.budget_amount) if campaign.budget_amount is not None else None,
        "budget_currency": campaign.budget_currency,
        "description": campaign.description,
        "tags": campaign.tags,
    }


def _asset_summary(asset: MarketingAsset) -> dict[str, Any]:
    ai_prep = asset.ai_prep_json or {}
    prep = {k: ai_prep.get(k) for k in AI_PREP_KEYS if ai_prep.get(k) is not None}
    return {
        "id": str(asset.id),
        "name": asset.name,
        "description": asset.description,
        "tags": asset.tags,
        "asset_type": _enum_val(asset.asset_type),
        "status": _enum_val(asset.status),
        "project_id": str(asset.project_id) if asset.project_id else None,
        "campaign_id": str(asset.campaign_id) if asset.campaign_id else None,
        "ai_prep": prep,
        "document_id": str(asset.document_id) if asset.document_id else None,
        # Metadata only — no image understanding.
        "image_understanding": False,
    }


def _audience_summary(audience: MarketingAudience) -> dict[str, Any]:
    return {
        "id": str(audience.id),
        "name": audience.name,
        "description": audience.description,
        "source": _enum_val(getattr(audience, "source", None)),
        "status": _enum_val(getattr(audience, "status", None)),
    }


def _assert_org_access(entity_company_id: UUID | None, organization_id: UUID | None) -> None:
    if organization_id is None or entity_company_id is None:
        return
    if entity_company_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Context entity is outside the selected organization",
        )


def build_assistant_context(
    db: Session,
    *,
    organization_id: UUID | None = None,
    project_id: UUID | None = None,
    campaign_id: UUID | None = None,
    asset_ids: list[UUID] | None = None,
    audience_id: UUID | None = None,
    language: str = "en",
    user_instruction: str | None = None,
    tone: str | None = None,
    channel: str | None = None,
    content_type: str | None = None,
    length: str | None = None,
    call_to_action: str | None = None,
    source_text: str | None = None,
    target_language: str | None = None,
    adaptation_style: str | None = None,
) -> dict[str, Any]:
    """Build allowlisted context payload. Validates ownership / org isolation."""

    warnings: list[str] = []
    sources: list[dict[str, Any]] = []
    context: dict[str, Any] = {
        "organization": {"id": str(organization_id)} if organization_id else {},
        "project_summary": None,
        "campaign_summary": None,
        "performance_summary": None,
        "selected_assets": [],
        "audience_summary": None,
        "language": language,
        "target_language": target_language,
        "tone": tone,
        "channel": channel,
        "content_type": content_type,
        "length": length,
        "call_to_action": call_to_action,
        "adaptation_style": adaptation_style,
        "source_text_present": bool(source_text),
        "user_instruction": user_instruction,
        "data_warnings": warnings,
        "data_freshness_at": datetime.now(UTC).isoformat(),
    }

    campaign: MarketingCampaign | None = None
    if campaign_id:
        campaign = db.get(MarketingCampaign, campaign_id)
        if campaign is None or campaign.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        _assert_org_access(campaign.company_id, organization_id)
        context["campaign_summary"] = _campaign_summary(campaign)
        sources.append(
            {
                "kind": "campaign",
                "label": campaign.name,
                "entity_id": str(campaign.id),
                "detail": f"status={_enum_val(campaign.status)}",
            }
        )
        if campaign.budget_amount is None:
            warnings.append("campaign_budget_missing")
        if campaign.target_project_id is None and not project_id:
            warnings.append("campaign_project_unlinked")

    resolved_project_id = project_id or (campaign.target_project_id if campaign else None)
    if resolved_project_id:
        project = db.get(Project, resolved_project_id)
        if project is None or project.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        _assert_org_access(project.company_id, organization_id)
        summary = _project_summary(project)
        context["project_summary"] = summary
        sources.append(
            {
                "kind": "project",
                "label": project.project_name,
                "entity_id": str(project.id),
                "detail": f"code={project.project_code}",
            }
        )
        for missing in summary.get("_missing_approved_fields") or []:
            warnings.append(f"project_field_missing:{missing}")

    filters = PerformanceFilters(
        company_id=organization_id,
        campaign_id=campaign_id,
        project_id=resolved_project_id,
    )
    overview = get_performance_overview(db, filters=filters)
    context["performance_summary"] = {
        "total_campaigns": _metric_dict(overview.total_campaigns),
        "active_campaigns": _metric_dict(overview.active_campaigns),
        "total_budget": _metric_dict(overview.total_budget),
        "total_spend": _metric_dict(overview.total_spend),
        "total_leads": _metric_dict(overview.total_leads),
        "qualified_leads": _metric_dict(overview.qualified_leads),
        "converted_leads": _metric_dict(overview.converted_leads),
        "avg_cpl": _metric_dict(overview.avg_cpl),
        "avg_conversion_rate": _metric_dict(overview.avg_conversion_rate),
        "campaigns_requiring_attention": _metric_dict(overview.campaigns_requiring_attention),
        "currency": overview.currency,
        "source": "campaign_performance_service.get_performance_overview",
    }
    sources.append(
        {
            "kind": "performance",
            "label": "Centralized marketing performance overview",
            "entity_id": None,
            "detail": "Consumed from reporting service — not recalculated in AI layer",
        }
    )

    if campaign is not None:
        detail = get_campaign_performance_detail(db, campaign)
        context["campaign_performance"] = detail.model_dump(mode="json") if hasattr(detail, "model_dump") else detail
        sources.append(
            {
                "kind": "campaign_performance",
                "label": "Campaign performance detail",
                "entity_id": str(campaign.id),
                "detail": "campaign_performance_service.get_campaign_performance_detail",
            }
        )

    # Top campaigns for summary modes (centralized list — no separate AI math).
    perf_list = list_campaign_performance(db, filters=filters, page=1, page_size=10)
    context["campaign_performance_list"] = [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in perf_list.items
    ]

    channel_perf = get_channel_performance(db, filters=filters)
    context["channel_performance"] = channel_perf.model_dump(mode="json") if hasattr(channel_perf, "model_dump") else channel_perf

    selected_assets: list[dict[str, Any]] = []
    for asset_id in asset_ids or []:
        asset = db.get(MarketingAsset, asset_id)
        if asset is None or asset.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset not found: {asset_id}")
        if campaign_id and asset.campaign_id and asset.campaign_id != campaign_id:
            warnings.append(f"asset_campaign_mismatch:{asset_id}")
        if organization_id and asset.campaign_id:
            linked = db.get(MarketingCampaign, asset.campaign_id)
            if linked:
                _assert_org_access(linked.company_id, organization_id)
        selected_assets.append(_asset_summary(asset))
        sources.append(
            {
                "kind": "asset",
                "label": asset.name,
                "entity_id": str(asset.id),
                "detail": "metadata_only",
            }
        )
    context["selected_assets"] = selected_assets

    if audience_id:
        audience = db.get(MarketingAudience, audience_id)
        if audience is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience not found")
        context["audience_summary"] = _audience_summary(audience)
        sources.append(
            {
                "kind": "audience",
                "label": audience.name,
                "entity_id": str(audience.id),
                "detail": "aggregate_metadata",
            }
        )

    if overview.total_leads.value in (None, 0) and overview.total_leads.state != "ready":
        warnings.append("lead_metrics_limited")
    if overview.total_spend.state != "ready":
        warnings.append("spend_data_limited")

    context["data_warnings"] = warnings
    context["data_sources"] = sources
    return context
