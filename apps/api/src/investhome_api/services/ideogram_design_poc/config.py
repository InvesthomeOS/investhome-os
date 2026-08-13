"""Ideogram POC configuration — fail closed when the key is absent."""

from __future__ import annotations

from dataclasses import dataclass

from investhome_api.config.settings import Settings, get_settings

IDEOGRAM_PROVIDER = "ideogram"
IDEOGRAM_REMIX_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v4/remix"
IDEOGRAM_GENERATE_ENDPOINT = "https://api.ideogram.ai/v1/ideogram-v4/generate"
DEFAULT_MODEL = "V_4_0"
SQUARE_RESOLUTION = "1024x1024"
DEFAULT_IMAGE_WEIGHT = 65
POC_VARIANT_COUNT = 3
CALL_TIMEOUT_SECONDS = 120.0

# Art directions are style-only. Facts stay identical across A/B/C.
ART_DIRECTIONS: tuple[tuple[str, str, str], ...] = (
    (
        "A",
        "Editorial Luxury",
        "Editorial luxury magazine cover treatment: cinematic lighting, "
        "restrained serif/sans hierarchy, generous negative space, fashion-house "
        "real-estate advertising. Photography remains the hero.",
    ),
    (
        "B",
        "Institutional Investment",
        "Institutional investment creative: private-bank / family-office aesthetic, "
        "clean geometric type, calm confidence, precise eligible figures only, "
        "no retail hype, no clutter.",
    ),
    (
        "C",
        "Architectural Premium",
        "Architectural premium treatment: gallery-like composition, material texture, "
        "precise geometry, the real building massing stays recognizable, type in "
        "a quiet safe zone, no replacement architecture.",
    ),
)


@dataclass(frozen=True)
class IdeogramAvailability:
    available: bool
    configured: bool
    enabled: bool
    model: str
    quality: str
    reason: str | None = None


def _truthy_enabled(value: bool | str | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def resolve_quality(raw: str | None) -> str:
    value = (raw or "QUALITY").strip().upper()
    if value in {"QUALITY", "DEFAULT", "TURBO"}:
        return value
    return "QUALITY"


def resolve_model(raw: str | None) -> str:
    value = (raw or DEFAULT_MODEL).strip()
    return value or DEFAULT_MODEL


def provider_availability(settings: Settings | None = None) -> IdeogramAvailability:
    cfg = settings or get_settings()
    key = (getattr(cfg, "ideogram_api_key", None) or "").strip()
    enabled = _truthy_enabled(getattr(cfg, "ideogram_enabled", True))
    model = resolve_model(getattr(cfg, "ideogram_model", None))
    quality = resolve_quality(getattr(cfg, "ideogram_default_quality", None))
    configured = bool(key)
    if not enabled:
        return IdeogramAvailability(
            available=False,
            configured=configured,
            enabled=False,
            model=model,
            quality=quality,
            reason="ideogram_disabled",
        )
    if not configured:
        return IdeogramAvailability(
            available=False,
            configured=False,
            enabled=True,
            model=model,
            quality=quality,
            reason="ideogram_api_key_missing",
        )
    return IdeogramAvailability(
        available=True,
        configured=True,
        enabled=True,
        model=model,
        quality=quality,
        reason=None,
    )
