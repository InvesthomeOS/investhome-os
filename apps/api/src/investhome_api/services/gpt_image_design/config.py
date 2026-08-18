"""GPT Image (OpenAI Images API) configuration — fail closed when AI_API_KEY is absent."""

from __future__ import annotations

from dataclasses import dataclass

from investhome_api.config.settings import Settings, get_settings

GPT_IMAGE_PROVIDER = "gpt-image"
OPENAI_IMAGE_PROVIDER = "openai-image"
GPT_IMAGE_PROVIDERS = frozenset({GPT_IMAGE_PROVIDER, OPENAI_IMAGE_PROVIDER})

# Verified from official OpenAI Images API docs (developers.openai.com, 2026):
# current GPT Image model alias is gpt-image-2 (snapshot gpt-image-2-2026-04-21).
DEFAULT_MODEL = "gpt-image-2"
EDITS_ENDPOINT_PATH = "/images/edits"
GENERATIONS_ENDPOINT_PATH = "/images/generations"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_QUALITY = "medium"
CALL_TIMEOUT_SECONDS = 180.0

# gpt-image-2 size constraints: edges multiples of 16, ratio <= 3:1, 655360–8294400 px.
# Instagram 4:5 1080x1350 is invalid (not multiples of 16) → nearest 4:5 1088x1360.
PRESET_TO_SIZE: dict[str, str] = {
    "square": "1024x1024",
    "carousel": "1024x1024",
    "portrait": "1088x1360",
    "landscape": "1920x1088",
    "story": "1088x1920",
    "reelsCover": "1088x1920",
}
ASPECT_TO_SIZE: dict[str, str] = {
    "1:1": "1024x1024",
    "4:5": "1088x1360",
    "16:9": "1920x1088",
    "9:16": "1088x1920",
}
PRESET_TO_ASPECT: dict[str, str] = {
    "square": "1:1",
    "carousel": "1:1",
    "portrait": "4:5",
    "landscape": "16:9",
    "story": "9:16",
    "reelsCover": "9:16",
}
CANVAS_FOR_PRESET: dict[str, tuple[int, int]] = {
    "square": (1080, 1080),
    "carousel": (1080, 1080),
    "portrait": (1080, 1350),
    "landscape": (1920, 1080),
    "story": (1080, 1920),
    "reelsCover": (1080, 1920),
}

# Fixed sizes for GPT Image models prior to gpt-image-2.
LEGACY_PRESET_TO_SIZE: dict[str, str] = {
    "square": "1024x1024",
    "carousel": "1024x1024",
    "portrait": "1024x1536",
    "landscape": "1536x1024",
    "story": "1024x1536",
    "reelsCover": "1024x1536",
}


@dataclass(frozen=True)
class GptImageAvailability:
    available: bool
    configured: bool
    enabled: bool
    model: str
    quality: str
    base_url: str
    reason: str | None = None


def _truthy_enabled(value: bool | str | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def resolve_model(raw: str | None) -> str:
    value = (raw or DEFAULT_MODEL).strip()
    return value or DEFAULT_MODEL


def resolve_quality(raw: str | None) -> str:
    value = (raw or DEFAULT_QUALITY).strip().lower()
    if value in {"low", "medium", "high", "auto"}:
        return value
    return DEFAULT_QUALITY


def resolve_base_url(settings: Settings) -> str:
    base = (getattr(settings, "ai_base_url", None) or "").strip() or DEFAULT_BASE_URL
    return base.rstrip("/")


def is_gpt_image_2(model: str) -> bool:
    return (model or "").strip().lower().startswith("gpt-image-2")


def resolve_size(*, model: str, format_preset: str | None, aspect_ratio: str | None) -> str:
    preset = (format_preset or "").strip() or "portrait"
    aspect = (aspect_ratio or "").strip() or PRESET_TO_ASPECT.get(preset, "4:5")
    if is_gpt_image_2(model):
        return PRESET_TO_SIZE.get(preset) or ASPECT_TO_SIZE.get(aspect) or "1088x1360"
    return LEGACY_PRESET_TO_SIZE.get(preset) or "1024x1536"


def canvas_for_preset(format_preset: str | None) -> tuple[int, int]:
    preset = (format_preset or "").strip() or "portrait"
    return CANVAS_FOR_PRESET.get(preset, (1080, 1350))


def openai_api_key(settings: Settings | None = None) -> str:
    """Reuse AI_API_KEY. Do not require OPENAI_API_KEY."""
    cfg = settings or get_settings()
    return (getattr(cfg, "ai_api_key", None) or "").strip()


def provider_availability(settings: Settings | None = None) -> GptImageAvailability:
    cfg = settings or get_settings()
    key = openai_api_key(cfg)
    enabled = _truthy_enabled(getattr(cfg, "gpt_image_enabled", True))
    model = resolve_model(getattr(cfg, "gpt_image_model", None))
    quality = resolve_quality(getattr(cfg, "gpt_image_quality", None))
    base_url = resolve_base_url(cfg)
    configured = bool(key)
    if not enabled:
        return GptImageAvailability(
            available=False,
            configured=configured,
            enabled=False,
            model=model,
            quality=quality,
            base_url=base_url,
            reason="gpt_image_disabled",
        )
    if not configured:
        return GptImageAvailability(
            available=False,
            configured=False,
            enabled=True,
            model=model,
            quality=quality,
            base_url=base_url,
            reason="ai_api_key_missing",
        )
    return GptImageAvailability(
        available=True,
        configured=True,
        enabled=True,
        model=model,
        quality=quality,
        base_url=base_url,
        reason=None,
    )
