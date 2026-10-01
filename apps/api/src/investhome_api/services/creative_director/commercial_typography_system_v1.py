"""CommercialTypographySystemV1 — type as one system, not independently styled parts."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.typography_quality_engine import HARD_REJECTS, RULES

SCHEMA = "CommercialTypographySystemV1"

SYSTEM_JOBS = (
    "attention",
    "meaning",
    "commercial_priority",
    "brand_character",
    "rhythm",
    "contrast",
    "information_density",
)

ROLES = (
    "DISPLAY",
    "MESSAGE",
    "NUMERIC_HERO",
    "NUMERIC_SUPPORT",
    "UNIT",
    "CTA",
    "BRAND",
    "MICRO",
)


def commercial_typography_system() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "jobs": list(SYSTEM_JOBS),
        "roles": list(ROLES),
        "inherited_quality_rules": dict(RULES),
        "inherited_hard_rejects": list(HARD_REJECTS),
        "system_rule": (
            "Do not independently style headline, offer, price, and CTA and hope they match. "
            "One family logic, one contrast logic, one rhythm. Scale is assigned by commercial priority "
            "inside the campaign hierarchy, not by leftover box size."
        ),
        "headline_is_not_automatically_largest": (
            "Do not automatically make the headline the largest object. "
            "%35 or 675.000 USD may be the visual idea's primary type mass when the hierarchy is offer-led or price-led."
        ),
        "cta": "Typographic close of the reading path. Not a website button, pill, or filled rectangle.",
        "status": "READY",
    }


def commercial_typography_system_markdown() -> str:
    system = commercial_typography_system()
    lines = [
        "# 05 Commercial typography system",
        "",
        system["system_rule"],
        "",
        "## Jobs the system must solve",
        "",
    ]
    for job in system["jobs"]:
        lines.append(f"- {job}")
    lines.extend(["", "## Roles", ""])
    for role in system["roles"]:
        lines.append(f"- `{role}`")
    lines.extend(
        [
            "",
            "## Headline is not automatically largest",
            "",
            system["headline_is_not_automatically_largest"],
            "",
            "## CTA",
            "",
            system["cta"],
            "",
            "Independent styling of headline / offer / price / CTA is a fail.",
        ]
    )
    return "\n".join(lines) + "\n"
