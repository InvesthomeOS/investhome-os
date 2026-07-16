"""Global search configuration."""

from investhome_api.config.activity_config import ENTITY_RESOURCE_MAP as ACTIVITY_ENTITY_RESOURCE_MAP
from investhome_api.config.notification_config import ENTITY_RESOURCE_MAP as NOTIFICATION_ENTITY_RESOURCE_MAP

# Supported entity types for universal search.
SEARCH_ENTITY_TYPES = frozenset(
    {
        "lead",
        "investor",
        "project",
        "financial_transaction",
        "financial_account",
        "funding_commitment",
        "payment_obligation",
        "user",
        "notification",
        "activity",
        "document",
        "office",
        "department",
        "team",
        "brand_asset",
        "design_project",
        "style_preset",
        "material_package",
        "furniture_item",
        "design_version",
        "building",
        "floor",
        "inventory_asset",
        "inventory_reservation",
        "price_change_request",
        "sales_opportunity",
        "sales_shortlist",
        "sales_inventory_match",
        "sales_proposal",
        "work_item",
    }
)

# Future entity types (UI may show as disabled filters).
FUTURE_SEARCH_ENTITY_TYPES = frozenset(
    {
        "unit",
        "construction",
        "email",
    }
)

ENTITY_PERMISSION_RESOURCE: dict[str, str] = {
    "lead": "leads",
    "investor": "investors",
    "project": "projects",
    "financial_transaction": "finance",
    "financial_account": "finance",
    "funding_commitment": "finance",
    "payment_obligation": "finance",
    "user": "users",
    "notification": "notifications",
    "activity": "activity",
    "document": "documents",
    "office": "offices",
    "department": "organization",
    "team": "organization",
    "brand_asset": "brand",
    "design_project": "design",
    "style_preset": "design",
    "material_package": "design",
    "furniture_item": "design",
    "design_version": "design",
    "building": "inventory",
    "floor": "inventory",
    "inventory_asset": "inventory",
    "inventory_reservation": "inventory",
    "price_change_request": "inventory",
    "sales_opportunity": "sales",
    "sales_shortlist": "sales",
    "sales_inventory_match": "sales",
    "sales_proposal": "sales",
    "work_item": "work",
}

ENTITY_LINK_MODULES: dict[str, str] = {
    "lead": "leads",
    "investor": "investors",
    "project": "projects",
    "financial_transaction": "finance",
    "financial_account": "finance",
    "funding_commitment": "finance",
    "payment_obligation": "finance",
    "user": "admin/users",
    "notification": "dashboard",
    "activity": "activity",
    "document": "documents",
    "office": "settings",
    "department": "settings",
    "team": "settings",
    "brand_asset": "settings",
    "design_project": "design",
    "style_preset": "design",
    "material_package": "design",
    "furniture_item": "design",
    "design_version": "design",
    "building": "inventory",
    "floor": "inventory",
    "inventory_asset": "inventory",
    "inventory_reservation": "inventory",
    "price_change_request": "inventory",
    "sales_opportunity": "sales",
    "sales_shortlist": "sales",
    "sales_inventory_match": "sales",
    "sales_proposal": "sales",
    "work_item": "sales/follow-up",
}

FINANCE_TAB_BY_ENTITY: dict[str, str] = {
    "financial_transaction": "transactions",
    "financial_account": "accounts",
    "funding_commitment": "funding",
    "payment_obligation": "payments",
}

DEFAULT_PER_ENTITY_LIMIT = 8
DEFAULT_TOTAL_LIMIT = 50
MIN_QUERY_LENGTH = 1

__all__ = [
    "SEARCH_ENTITY_TYPES",
    "FUTURE_SEARCH_ENTITY_TYPES",
    "ENTITY_PERMISSION_RESOURCE",
    "ENTITY_LINK_MODULES",
    "FINANCE_TAB_BY_ENTITY",
    "ACTIVITY_ENTITY_RESOURCE_MAP",
    "NOTIFICATION_ENTITY_RESOURCE_MAP",
    "DEFAULT_PER_ENTITY_LIMIT",
    "DEFAULT_TOTAL_LIMIT",
    "MIN_QUERY_LENGTH",
]
