"""Anti-template detector. Explicit rejection of default campaign layouts."""

from __future__ import annotations

from typing import Any

BANNED_TEMPLATES = (
    "photo + headline",
    "dark header + photo",
    "photo card",
    "split screen",
    "brochure cover",
    "property listing",
    "website hero",
    "Instagram template",
    "large empty rectangle with text",
    "floating information panel",
    "generic luxury editorial",
    "three boxes plus photograph",
)


def detect_template(flags: dict[str, bool] | None = None, *, user_requested_format: bool = False) -> dict[str, Any]:
    hits = [name for name, on in (flags or {}).items() if on and name in BANNED_TEMPLATES]
    if user_requested_format:
        return {
            "schema": "AntiTemplateDetectorV1",
            "pass": True,
            "hits": hits,
            "overridden_by_explicit_user_format": True,
        }
    return {
        "schema": "AntiTemplateDetectorV1",
        "pass": not hits,
        "hits": hits,
        "overridden_by_explicit_user_format": False,
        "action_if_fail": "CREATIVE_REJECTED_BEFORE_HUMAN_REVIEW",
    }


def anti_template_rules() -> dict[str, Any]:
    return {
        "schema": "AntiTemplateRulesV1",
        "banned_templates": list(BANNED_TEMPLATES),
        "unless": "the user explicitly requests that format",
        "status": "READY",
    }
