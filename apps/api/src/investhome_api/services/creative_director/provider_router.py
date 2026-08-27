"""Provider Router — route AD/SOCIAL IMAGE to best connected image provider."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from investhome_api.config.settings import Settings, get_settings
from investhome_api.services.creative_director.orchestrator import assign_capabilities

# Future revision capabilities. Edit Map schema is OS-owned — providers may
# analyze or edit regions later, they do not own the map.
EDIT_MAP_PROVIDER_CAPABILITIES = (
    "generate_finished_ad",
    "analyze_design",
    "edit_region",
    "replace_hero",
    "adapt_format",
)


@dataclass
class ImageProductionRoute:
    """Resolved route for social/ad image production."""

    output_type: str
    capability: str
    provider_id: str | None
    available: bool
    missing: bool
    reason: str | None
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_ad_social_image(
    *,
    prefer_edit: bool = True,
    settings: Settings | None = None,
) -> ImageProductionRoute:
    """Pick image_edit (real asset remix) or image_generate for AD/SOCIAL IMAGE."""
    s = settings or get_settings()
    capability = "image_edit" if prefer_edit else "image_generate"
    plan = assign_capabilities([capability], settings=s)
    assignment = next((a for a in plan.assignments if a.capability == capability), None)
    if assignment is None or assignment.missing:
        reason = assignment.reason if assignment else f"No provider for {capability}"
        provider_id = assignment.provider_id if assignment else None
        return ImageProductionRoute(
            output_type="ad_social_image",
            capability=capability,
            provider_id=provider_id,
            available=False,
            missing=True,
            reason=reason,
        )
    model = None
    for row in plan.providers:
        if isinstance(row, dict) and row.get("provider_id") == assignment.provider_id:
            model = row.get("model")
            break
    return ImageProductionRoute(
        output_type="ad_social_image",
        capability=capability,
        provider_id=assignment.provider_id,
        available=True,
        missing=False,
        reason=None,
        model=model,
    )


def assert_image_provider_available(route: ImageProductionRoute) -> None:
    """Raise ValueError with explicit missing-provider message — no silent fallback."""
    if route.missing or not route.available:
        cap = route.capability
        pid = route.provider_id or "none"
        reason = route.reason or f"Image provider unavailable for {cap}"
        raise ValueError(f"Missing image provider for ad_social_image ({cap}): {pid} — {reason}")
