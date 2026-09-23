"""Structured query parser for CRM field-specific search syntax."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


FIELD_ALIASES = {
    "type": "entity_type",
    "company": "company_name",
    "owner": "owner",
    "status": "status",
    "tag": "tag",
    "channel": "channel",
    "has": "has",
    "is": "is",
}

RELATIVE_DATE_PATTERN = re.compile(r"^([<>]=?)(\d+)([dwmhy])$")
FIELD_PATTERN = re.compile(
    r'(\w+):(?:"([^"]+)"|([^\s]+))',
)


@dataclass
class ParsedFieldFilter:
    field: str
    operator: str
    value: str


@dataclass
class ParsedSearchQuery:
    free_text: str = ""
    field_filters: list[ParsedFieldFilter] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _parse_relative_date(value: str) -> tuple[str, datetime | None]:
    match = RELATIVE_DATE_PATTERN.match(value.strip())
    if not match:
        return "eq", None
    op, amount, unit = match.groups()
    amount_int = int(amount)
    delta_map = {"d": timedelta(days=1), "w": timedelta(weeks=1), "m": timedelta(days=30), "h": timedelta(hours=1), "y": timedelta(days=365)}
    delta = delta_map.get(unit, timedelta(days=1)) * amount_int
    cutoff = datetime.now(UTC) - delta
    return op, cutoff


def _parse_numeric(value: str) -> tuple[str, str | float]:
    if value.startswith((">=", "<=", ">", "<")):
        for op in (">=", "<=", ">", "<"):
            if value.startswith(op):
                return op, value[len(op):]
    if value.startswith("="):
        return "eq", value[1:]
    return "contains", value


def parse_structured_search_query(query: str) -> ParsedSearchQuery:
    """Parse field-specific syntax: type:investor, company:\"World Bank\", last_contact:<30d."""
    result = ParsedSearchQuery()
    if not query or not query.strip():
        return result

    remaining = query.strip()
    for match in FIELD_PATTERN.finditer(query):
        raw_field = match.group(1).lower()
        value = match.group(2) or match.group(3) or ""
        canonical = FIELD_ALIASES.get(raw_field, raw_field)

        if raw_field == "type":
            result.entity_types.append(value.lower())
            remaining = remaining.replace(match.group(0), " ", 1)
            continue

        if raw_field in ("last_contact", "updated", "created"):
            op, cutoff = _parse_relative_date(value)
            if cutoff is None:
                result.errors.append(f"Invalid date expression: {raw_field}:{value}")
            else:
                result.field_filters.append(ParsedFieldFilter(field=raw_field, operator=op, value=cutoff.isoformat()))
            remaining = remaining.replace(match.group(0), " ", 1)
            continue

        if raw_field in ("investment_capacity", "score", "amount"):
            op, num_val = _parse_numeric(value)
            try:
                float(num_val)
            except ValueError:
                result.errors.append(f"Invalid numeric value: {raw_field}:{value}")
            else:
                result.field_filters.append(ParsedFieldFilter(field=raw_field, operator=op, value=str(num_val)))
            remaining = remaining.replace(match.group(0), " ", 1)
            continue

        if canonical not in FIELD_ALIASES.values() and raw_field not in FIELD_ALIASES:
            result.warnings.append(f"Unknown field prefix: {raw_field}")

        result.field_filters.append(ParsedFieldFilter(field=canonical, operator="eq", value=value))
        remaining = remaining.replace(match.group(0), " ", 1)

    result.free_text = " ".join(remaining.split())
    return result


def parsed_to_dict(parsed: ParsedSearchQuery) -> dict:
    return {
        "free_text": parsed.free_text,
        "entity_types": parsed.entity_types,
        "field_filters": [
            {"field": f.field, "operator": f.operator, "value": f.value}
            for f in parsed.field_filters
        ],
        "errors": parsed.errors,
        "warnings": parsed.warnings,
    }
