"""Centralized marketing content status transitions."""

from __future__ import annotations

from fastapi import HTTPException, status

VALID_CONTENT_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "idea": {"requested", "archived"},
    "requested": {"briefing", "idea", "archived"},
    "briefing": {"draft", "requested", "archived"},
    "draft": {"in_production", "briefing", "archived"},
    "in_production": {"internal_review", "draft", "archived"},
    "internal_review": {
        "pending_brand_review",
        "pending_legal_review",
        "pending_compliance_review",
        "pending_approval",
        "in_production",
        "archived",
    },
    "pending_brand_review": {"pending_legal_review", "pending_compliance_review", "pending_approval", "internal_review", "archived"},
    "pending_legal_review": {"pending_compliance_review", "pending_approval", "internal_review", "archived"},
    "pending_compliance_review": {"pending_approval", "internal_review", "archived"},
    "pending_approval": {"approved", "internal_review", "archived"},
    "approved": {"scheduled", "published", "archived"},
    "scheduled": {"published", "approved", "archived"},
    "published": {"expired", "archived"},
    "expired": {"archived", "draft"},
    "archived": {"draft", "idea"},
}


def validate_content_status_transition(current: str, target: str) -> None:
    allowed = VALID_CONTENT_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed and current != target:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot transition content from '{current}' to '{target}'. "
                f"Allowed: {', '.join(sorted(allowed)) or 'none'}"
            ),
        )


def get_allowed_content_transitions(current: str) -> list[str]:
    return sorted(VALID_CONTENT_STATUS_TRANSITIONS.get(current, set()))


PUBLISHABLE_STATUSES = frozenset({"approved", "scheduled"})
