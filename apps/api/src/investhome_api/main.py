from investhome_api.api.exception_handlers import register_exception_handlers
from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import configure_logging
from investhome_api.middleware.request_id import RequestIdMiddleware
from investhome_api.api.routes import activity, auth, company_foundation, design_studio, document_intelligence, documents, drawing_intelligence, executive, finance, health, inventory, inventory_assignment, inventory_ownership, inventory_pricing, inventory_reservations, investors, lead_qualification, leads, meta, notifications, projects, roles, sales_inventory_matching, sales_opportunities, search, users
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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
    app.include_router(roles.router)
    app.include_router(roles.permissions_router)
    app.include_router(leads.router)
    app.include_router(lead_qualification.router)
    app.include_router(sales_opportunities.router)
    app.include_router(sales_inventory_matching.router)
    app.include_router(investors.router)
    app.include_router(projects.router)
    app.include_router(finance.router)
    app.include_router(activity.router)
    app.include_router(notifications.router)
    app.include_router(search.router)
    app.include_router(documents.router)
    app.include_router(document_intelligence.router)
    app.include_router(drawing_intelligence.router)
    app.include_router(executive.router)
    app.include_router(company_foundation.router)
    app.include_router(design_studio.router)
    app.include_router(inventory.router)
    app.include_router(inventory_pricing.prices_router)
    app.include_router(inventory_pricing.requests_router)
    app.include_router(inventory_reservations.router)
    app.include_router(inventory_ownership.ownership_router)
    app.include_router(inventory_ownership.transfers_router)
    app.include_router(inventory_assignment.assignments_router)
    app.include_router(inventory_assignment.requests_router)

    return app


app = create_app()
