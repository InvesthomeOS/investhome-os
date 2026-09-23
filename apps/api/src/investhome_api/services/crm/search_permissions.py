"""CRM search permission gates."""

from __future__ import annotations

from investhome_api.models.user_auth import User
from investhome_api.services.permission_service import is_super_admin, user_has_permission

CRM_SEARCH_ENTITY_TYPES = frozenset(
    {
        "crm_contact",
        "crm_company",
        "crm_relationship",
        "crm_activity",
        "crm_communication",
        "crm_task",
        "sales_opportunity",
        "investor",
        "project",
        "inventory_asset",
        "financial_transaction",
        "document",
    }
)

ENTITY_PERMISSION_MAP: dict[str, tuple[str, str]] = {
    "crm_contact": ("crm", "read"),
    "crm_company": ("crm", "view_companies"),
    "crm_relationship": ("crm", "read"),
    "crm_activity": ("crm", "view_activities"),
    "crm_communication": ("crm", "read"),
    "crm_task": ("crm", "manage_tasks"),
    "sales_opportunity": ("sales", "view"),
    "investor": ("investors", "view"),
    "project": ("projects", "view"),
    "inventory_asset": ("inventory", "view"),
    "financial_transaction": ("finance", "view"),
    "document": ("documents", "view"),
}


def can_use_global_search(user: User) -> bool:
    return user_has_permission(user, "crm", "use_global_search") or user_has_permission(user, "crm", "read")


def can_use_advanced_search(user: User) -> bool:
    return user_has_permission(user, "crm", "advanced_search") or user_has_permission(user, "crm", "read")


def can_view_suggestions(user: User) -> bool:
    return user_has_permission(user, "crm", "view_suggestions") or user_has_permission(user, "crm", "read")


def can_manage_saved_searches(user: User) -> bool:
    return user_has_permission(user, "crm", "manage_saved_searches") or user_has_permission(user, "crm", "read")


def can_share_saved_searches(user: User) -> bool:
    return user_has_permission(user, "crm", "share_saved_searches")


def can_create_search_alerts(user: User) -> bool:
    return user_has_permission(user, "crm", "create_search_alerts")


def can_search_archived(user: User) -> bool:
    return user_has_permission(user, "crm", "search_archived")


def can_search_restricted(user: User) -> bool:
    return user_has_permission(user, "crm", "search_restricted")


def can_search_communication_content(user: User) -> bool:
    return user_has_permission(user, "crm", "search_communication_content")


def can_search_financial_content(user: User) -> bool:
    return user_has_permission(user, "crm", "search_financial_content") or user_has_permission(user, "crm", "view_financial")


def can_search_compliance_content(user: User) -> bool:
    return user_has_permission(user, "crm", "search_compliance_content") or user_has_permission(user, "crm", "view_compliance")


def can_export_search_results(user: User) -> bool:
    return user_has_permission(user, "crm", "export_search_results") or user_has_permission(user, "crm", "export")


def can_view_search_analytics(user: User) -> bool:
    return user_has_permission(user, "crm", "view_search_analytics")


def can_use_natural_language_search(user: User) -> bool:
    return user_has_permission(user, "crm", "natural_language_search")


def allowed_entity_types(user: User) -> set[str]:
    if is_super_admin(user):
        return set(CRM_SEARCH_ENTITY_TYPES)
    allowed: set[str] = set()
    for entity_type in CRM_SEARCH_ENTITY_TYPES:
        resource, action = ENTITY_PERMISSION_MAP.get(entity_type, ("crm", "read"))
        if user_has_permission(user, resource, action) or user_has_permission(user, "crm", "read"):
            if entity_type == "crm_company" and not user_has_permission(user, "crm", "view_companies"):
                if not user_has_permission(user, "crm", "read"):
                    continue
            if entity_type == "crm_communication" and not can_search_communication_content(user):
                continue
            if entity_type == "financial_transaction" and not can_search_financial_content(user):
                continue
            allowed.add(entity_type)
    return allowed
