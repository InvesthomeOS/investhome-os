"""Centralized SegmentFieldRegistry — typed fields, operators, permissions."""

from __future__ import annotations

from dataclasses import dataclass

MAX_RULE_DEPTH = 5
MAX_RULES_PER_GROUP = 20

TEXT_OPERATORS = ["equals", "not_equals", "contains", "not_contains", "starts_with", "is_empty", "is_not_empty"]
NUMBER_OPERATORS = ["equals", "not_equals", "gt", "gte", "lt", "lte", "between", "is_empty"]
DATE_OPERATORS = ["equals", "before", "after", "between", "last_n_days", "is_empty"]
ENUM_OPERATORS = ["equals", "not_equals", "in", "not_in"]
BOOLEAN_OPERATORS = ["is_true", "is_false", "is_empty"]
LOCATION_OPERATORS = ["in_region", "not_in_region", "within_radius", "is_empty"]
RELATIONSHIP_OPERATORS = ["has", "not_has", "count_gt", "count_lt"]
BEHAVIOR_OPERATORS = ["occurred", "not_occurred", "count_gt", "count_lt", "last_n_days"]


@dataclass(frozen=True)
class SegmentFieldDefinition:
    key: str
    label: str
    entity_type: str
    value_type: str
    operators: tuple[str, ...]
    permission: str | None
    data_source: str
    sensitive: bool = False


SEGMENT_FIELD_REGISTRY: list[SegmentFieldDefinition] = [
    SegmentFieldDefinition(
        "contact.email",
        "Contact Email",
        "contact",
        "text",
        tuple(TEXT_OPERATORS),
        "view",
        "crm_contacts",
    ),
    SegmentFieldDefinition(
        "contact.country",
        "Contact Country",
        "contact",
        "text",
        tuple(TEXT_OPERATORS),
        "view",
        "crm_contacts",
    ),
    SegmentFieldDefinition(
        "contact.consent_email",
        "Email Consent",
        "contact",
        "boolean",
        tuple(BOOLEAN_OPERATORS),
        "view_audience_consent",
        "crm_communication_preferences",
        sensitive=True,
    ),
    SegmentFieldDefinition(
        "contact.consent_sms",
        "SMS Consent",
        "contact",
        "boolean",
        tuple(BOOLEAN_OPERATORS),
        "view_audience_consent",
        "crm_communication_preferences",
        sensitive=True,
    ),
    SegmentFieldDefinition(
        "contact.do_not_contact",
        "Do Not Contact",
        "contact",
        "boolean",
        tuple(BOOLEAN_OPERATORS),
        "view_audience_consent",
        "crm_communication_preferences",
        sensitive=True,
    ),
    SegmentFieldDefinition(
        "company.industry",
        "Company Industry",
        "company",
        "text",
        tuple(TEXT_OPERATORS),
        "view_companies",
        "companies",
    ),
    SegmentFieldDefinition(
        "lead.status",
        "Lead Status",
        "lead",
        "enum",
        tuple(ENUM_OPERATORS),
        "view_leads",
        "leads",
    ),
    SegmentFieldDefinition(
        "lead.source",
        "Lead Source",
        "lead",
        "text",
        tuple(TEXT_OPERATORS),
        "view_leads",
        "leads",
    ),
    SegmentFieldDefinition(
        "marketing.campaign_id",
        "Campaign",
        "marketing",
        "relationship",
        tuple(RELATIONSHIP_OPERATORS),
        "view",
        "marketing_lead_contexts",
    ),
    SegmentFieldDefinition(
        "marketing.utm_source",
        "UTM Source",
        "marketing",
        "text",
        tuple(TEXT_OPERATORS),
        "view_attribution",
        "marketing_lead_contexts",
    ),
    SegmentFieldDefinition(
        "marketing.lead_score",
        "Marketing Lead Score",
        "marketing",
        "number",
        tuple(NUMBER_OPERATORS),
        "view_scores",
        "marketing_lead_contexts",
        sensitive=True,
    ),
    SegmentFieldDefinition(
        "marketing.last_engagement",
        "Last Engagement",
        "marketing",
        "date",
        tuple(DATE_OPERATORS),
        "view",
        "marketing_lead_contexts",
    ),
]


def get_field_registry(*, include_restricted: bool = False, user_permissions: set[str] | None = None) -> list[dict]:
    """Return field registry filtered by permissions."""
    result = []
    for field in SEGMENT_FIELD_REGISTRY:
        if field.sensitive and not include_restricted:
            if user_permissions and field.permission and field.permission not in user_permissions:
                continue
        result.append(
            {
                "key": field.key,
                "label": field.label,
                "entity_type": field.entity_type,
                "value_type": field.value_type,
                "operators": list(field.operators),
                "permission": field.permission,
                "data_source": field.data_source,
                "sensitive": field.sensitive,
            }
        )
    return result


def get_field_definition(field_key: str) -> SegmentFieldDefinition | None:
    for field in SEGMENT_FIELD_REGISTRY:
        if field.key == field_key:
            return field
    return None


def validate_rule_operator(field_key: str, operator: str) -> bool:
    field = get_field_definition(field_key)
    if field is None:
        return False
    return operator in field.operators
