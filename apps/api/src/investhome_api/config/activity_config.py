"""Activity log configuration: sensitive fields and entity permission mapping."""

from investhome_api.models.activity import ActivityEntityType

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "hashed_password",
        "current_password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "jwt_secret",
        "account_number",
        "iban",
        "routing_number",
        "card_number",
        "cvv",
        "pin",
    }
)

SENSITIVE_PARTIAL_MATCH = frozenset({"password", "secret", "token", "api_key"})

ENTITY_RESOURCE_MAP: dict[ActivityEntityType, str] = {
    ActivityEntityType.USER: "users",
    ActivityEntityType.ROLE: "roles",
    ActivityEntityType.LEAD: "leads",
    ActivityEntityType.INVESTOR: "investors",
    ActivityEntityType.PROJECT: "projects",
    ActivityEntityType.FINANCIAL_ACCOUNT: "finance",
    ActivityEntityType.TRANSACTION: "finance",
    ActivityEntityType.PROJECT_BUDGET: "finance",
    ActivityEntityType.FUNDING_COMMITMENT: "finance",
    ActivityEntityType.PAYMENT_OBLIGATION: "finance",
    ActivityEntityType.DOCUMENT: "documents",
    ActivityEntityType.COMPANY: "company",
    ActivityEntityType.OFFICE: "offices",
    ActivityEntityType.DEPARTMENT: "organization",
    ActivityEntityType.TEAM: "organization",
    ActivityEntityType.BRAND: "brand",
    ActivityEntityType.DESIGN_PROJECT: "design",
    ActivityEntityType.BUILDING: "inventory",
    ActivityEntityType.FLOOR: "inventory",
    ActivityEntityType.INVENTORY_ASSET: "inventory",
    ActivityEntityType.INVENTORY_RESERVATION: "inventory",
    ActivityEntityType.INVENTORY_PRICE: "inventory",
    ActivityEntityType.INVENTORY_OWNERSHIP: "inventory",
    ActivityEntityType.INVENTORY_ASSIGNMENT: "inventory",
    ActivityEntityType.PRICE_CHANGE_REQUEST: "inventory",
    ActivityEntityType.SALES_OPPORTUNITY: "sales",
    ActivityEntityType.LEAD_QUALIFICATION: "sales",
    ActivityEntityType.SALES_PROPOSAL: "sales",
}

SECURITY_ENTITY_TYPES = frozenset(
    {
        ActivityEntityType.USER,
        ActivityEntityType.ROLE,
    }
)

RETENTION_POLICY_DAYS: int | None = None
