from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from investhome_api.api.exception_handlers import register_exception_handlers
from investhome_api.api.routes import (
    activity,
    ai_index,
    ai_search,
    analytics_bi,
    analytics_warehouse,
    auth,
    automation_center,
    branches,
    canva_oauth,
    companies,
    company_documents,
    company_foundation,
    creative_director,
    creative_studio,
    creative_studio_generation,
    creative_studio_media,
    crm,
    crm_activities,
    crm_agreements,
    crm_bitrix,
    crm_communications,
    crm_live_communications,
    crm_companies,
    crm_contacts,
    crm_leads,
    crm_matches,
    crm_relationships,
    crm_reports,
    crm_search,
    departments,
    design_studio,
    document_intelligence,
    documents,
    drawing_intelligence,
    executive,
    finance,
    gpt_image_design,
    health,
    ideogram_design_poc,
    inventory,
    inventory_assignment,
    inventory_ownership,
    inventory_pricing,
    inventory_reservations,
    investors,
    knowledge,
    lead_qualification,
    leads,
    marketing,
    marketing_ai,
    marketing_analytics,
    marketing_assets,
    marketing_attribution,
    marketing_audiences,
    marketing_automation,
    marketing_brand,
    marketing_campaigns,
    marketing_channel,
    marketing_content,
    marketing_conversions,
    marketing_email,
    marketing_forms,
    marketing_landing_pages,
    marketing_lead_capture,
    marketing_leads,
    marketing_performance,
    marketing_segments,
    marketing_sms,
    marketing_social,
    marketing_sources,
    marketing_submissions,
    marketing_templates,
    marketing_webhooks,
    marketing_whatsapp,
    meta,
    notifications,
    platform,
    project_assistant,
    project_budgets,
    project_costs,
    project_drive,
    projects,
    roles,
    sales_inventory_matching,
    sales_opportunities,
    sales_proposals,
    sales_readiness,
    search,
    security_center,
    social_design_engine,
    users,
    work_items,
)
from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import configure_logging
from investhome_api.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.enable_openapi else None,
        redoc_url="/redoc" if settings.enable_openapi else None,
        openapi_url="/openapi.json" if settings.enable_openapi else None,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(security_center.users_security_router)
    app.include_router(security_center.router)
    app.include_router(platform.router)
    app.include_router(canva_oauth.router)
    app.include_router(roles.router)
    app.include_router(roles.permissions_router)
    app.include_router(leads.router)
    app.include_router(lead_qualification.router)
    app.include_router(sales_opportunities.router)
    app.include_router(sales_inventory_matching.router)
    app.include_router(sales_proposals.router)
    app.include_router(sales_readiness.router)
    app.include_router(work_items.router)
    app.include_router(investors.router)
    app.include_router(projects.router)
    app.include_router(project_drive.router)
    app.include_router(project_budgets.router)
    app.include_router(project_costs.router)
    app.include_router(finance.router)
    app.include_router(activity.router)
    app.include_router(automation_center.router)
    app.include_router(notifications.router)
    app.include_router(search.router)
    app.include_router(documents.router)
    app.include_router(document_intelligence.router)
    app.include_router(knowledge.router)
    app.include_router(drawing_intelligence.router)
    app.include_router(executive.router)
    app.include_router(analytics_bi.router)
    app.include_router(analytics_warehouse.router)
    app.include_router(companies.router)
    app.include_router(branches.router)
    app.include_router(departments.router)
    app.include_router(company_documents.router)
    app.include_router(company_foundation.router)
    app.include_router(design_studio.router)
    app.include_router(creative_studio.router)
    app.include_router(creative_studio_media.router)
    app.include_router(ai_index.router)
    app.include_router(ai_search.router)
    app.include_router(project_assistant.router)
    app.include_router(creative_studio_generation.router)
    app.include_router(social_design_engine.router)
    app.include_router(ideogram_design_poc.router)
    app.include_router(gpt_image_design.router)
    app.include_router(creative_director.router)
    app.include_router(inventory.router)
    app.include_router(inventory_pricing.prices_router)
    app.include_router(inventory_pricing.requests_router)
    app.include_router(inventory_reservations.router)
    app.include_router(inventory_ownership.ownership_router)
    app.include_router(inventory_ownership.transfers_router)
    app.include_router(inventory_assignment.assignments_router)
    app.include_router(inventory_assignment.requests_router)
    app.include_router(crm.router)
    app.include_router(crm_contacts.router)
    app.include_router(crm_leads.router)
    app.include_router(crm_matches.router)
    app.include_router(crm_agreements.router)
    app.include_router(crm_bitrix.router)
    app.include_router(crm_companies.router)
    app.include_router(crm_relationships.router)
    app.include_router(crm_reports.router)
    app.include_router(crm_activities.router)
    app.include_router(crm_communications.router)
    app.include_router(crm_live_communications.router)
    app.include_router(crm_search.router)
    app.include_router(marketing.router)
    app.include_router(marketing_analytics.router)
    app.include_router(marketing_campaigns.router)
    app.include_router(marketing_audiences.router)
    app.include_router(marketing_segments.router)
    app.include_router(marketing_leads.router)
    app.include_router(marketing_sources.router)
    app.include_router(marketing_content.router)
    app.include_router(marketing_assets.router)
    app.include_router(marketing_brand.router)
    app.include_router(marketing_templates.router)
    app.include_router(marketing_channel.router)
    app.include_router(marketing_social.router)
    app.include_router(marketing_email.router)
    app.include_router(marketing_whatsapp.router)
    app.include_router(marketing_sms.router)
    app.include_router(marketing_landing_pages.router)
    app.include_router(marketing_forms.router)
    app.include_router(marketing_submissions.router)
    app.include_router(marketing_submissions.public_router)
    app.include_router(marketing_lead_capture.router)
    app.include_router(marketing_conversions.router)
    app.include_router(marketing_conversions.attribution_router)
    app.include_router(marketing_attribution.router)
    app.include_router(marketing_performance.router)
    app.include_router(marketing_ai.router)
    app.include_router(marketing_automation.router)
    app.include_router(marketing_webhooks.router)
    app.include_router(marketing_webhooks.domains_router)

    return app


app = create_app()
