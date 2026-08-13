"""Official Ideogram 4.0 HTTP client (remix + generate). Never logs secrets."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from investhome_api.services.ideogram_design_poc.config import (
    CALL_TIMEOUT_SECONDS,
    IDEOGRAM_GENERATE_ENDPOINT,
    IDEOGRAM_REMIX_ENDPOINT,
    SQUARE_RESOLUTION,
)

logger = logging.getLogger(__name__)

_call_lock = threading.Lock()
_call_count = 0


def provider_call_count() -> int:
    with _call_lock:
        return _call_count


def reset_provider_call_count() -> None:
    global _call_count
    with _call_lock:
        _call_count = 0


def _bump_call_count(*, endpoint: str, variant: str | None = None) -> int:
    global _call_count
    with _call_lock:
        _call_count += 1
        n = _call_count
    logger.info(
        "ideogram_poc_provider_call",
        extra={
            "provider": "ideogram",
            "endpoint": endpoint,
            "variant": variant,
            "call_count": n,
        },
    )
    return n


def _safe_host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).netloc or None
    except Exception:
        return None


class IdeogramProviderError(HTTPException):
    """Recoverable Ideogram API failure — never a silent Native fallback."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(status_code=status_code, detail=message)


@dataclass
class IdeogramRemoteImage:
    url: str | None
    prompt: str | None
    resolution: str | None
    seed: int | None
    is_image_safe: bool
    raw: dict[str, Any] = field(default_factory=dict)


def _map_http_error(response: httpx.Response) -> IdeogramProviderError:
    code = response.status_code
    if code == 401:
        return IdeogramProviderError(
            status.HTTP_401_UNAUTHORIZED,
            "Ideogram authentication failed (401). Check IDEOGRAM_API_KEY.",
        )
    if code == 403:
        return IdeogramProviderError(
            status.HTTP_403_FORBIDDEN,
            "Ideogram refused the request (403).",
        )
    if code == 422:
        return IdeogramProviderError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Ideogram rejected the prompt or source image (422 safety/validation).",
        )
    if code == 429:
        return IdeogramProviderError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Ideogram rate limited this request (429). Retry later.",
        )
    if code == 400:
        return IdeogramProviderError(
            status.HTTP_400_BAD_REQUEST,
            "Ideogram validation failed (400).",
        )
    if code >= 500:
        return IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            f"Ideogram provider error ({code}).",
        )
    return IdeogramProviderError(
        status.HTTP_502_BAD_GATEWAY,
        f"Ideogram request failed ({code}).",
    )


def _parse_images(payload: dict[str, Any]) -> list[IdeogramRemoteImage]:
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    out: list[IdeogramRemoteImage] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        seed = row.get("seed")
        try:
            seed_i = int(seed) if seed is not None else None
        except (TypeError, ValueError):
            seed_i = None
        out.append(
            IdeogramRemoteImage(
                url=(str(row["url"]).strip() if row.get("url") else None),
                prompt=str(row["prompt"]) if row.get("prompt") else None,
                resolution=str(row["resolution"]) if row.get("resolution") else None,
                seed=seed_i,
                is_image_safe=bool(row.get("is_image_safe", True)),
                raw=row,
            )
        )
    return out


def remix_image(
    *,
    api_key: str,
    image_bytes: bytes,
    filename: str,
    content_type: str,
    text_prompt: str,
    rendering_speed: str,
    image_weight: int,
    resolution: str = SQUARE_RESOLUTION,
    variant: str | None = None,
    timeout: float = CALL_TIMEOUT_SECONDS,
) -> IdeogramRemoteImage:
    """POST /v1/ideogram-v4/remix — official Ideogram 4.0 remix."""
    _bump_call_count(endpoint="remix", variant=variant)
    files = {
        "image": (filename or "source.jpg", image_bytes, content_type or "image/jpeg"),
    }
    data = {
        "text_prompt": text_prompt,
        "image_weight": str(int(image_weight)),
        "resolution": resolution,
        "rendering_speed": rendering_speed,
    }
    headers = {"Api-Key": api_key}
    try:
        response = httpx.post(
            IDEOGRAM_REMIX_ENDPOINT,
            headers=headers,
            data=data,
            files=files,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise IdeogramProviderError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Ideogram remix timed out.",
        ) from exc
    except httpx.HTTPError as exc:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram remix network error.",
        ) from exc
    if response.status_code != 200:
        raise _map_http_error(response)
    try:
        payload = response.json()
    except ValueError as exc:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram remix returned a non-JSON body.",
        ) from exc
    images = _parse_images(payload if isinstance(payload, dict) else {})
    if not images:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram remix returned no images.",
        )
    chosen = images[0]
    if not chosen.is_image_safe or not chosen.url:
        raise IdeogramProviderError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Ideogram remix failed the safety check.",
        )
    logger.info(
        "ideogram_poc_remix_ok",
        extra={
            "variant": variant,
            "resolution": chosen.resolution,
            "remote_host": _safe_host(chosen.url),
        },
    )
    return chosen


def generate_image(
    *,
    api_key: str,
    text_prompt: str,
    rendering_speed: str,
    resolution: str = SQUARE_RESOLUTION,
    variant: str | None = None,
    timeout: float = CALL_TIMEOUT_SECONDS,
) -> IdeogramRemoteImage:
    """POST /v1/ideogram-v4/generate — text-to-image fallback when no source image exists."""
    _bump_call_count(endpoint="generate", variant=variant)
    data = {
        "text_prompt": text_prompt,
        "resolution": resolution,
        "rendering_speed": rendering_speed,
    }
    headers = {"Api-Key": api_key}
    try:
        response = httpx.post(
            IDEOGRAM_GENERATE_ENDPOINT,
            headers=headers,
            data=data,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise IdeogramProviderError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Ideogram generate timed out.",
        ) from exc
    except httpx.HTTPError as exc:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram generate network error.",
        ) from exc
    if response.status_code != 200:
        raise _map_http_error(response)
    try:
        payload = response.json()
    except ValueError as exc:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram generate returned a non-JSON body.",
        ) from exc
    images = _parse_images(payload if isinstance(payload, dict) else {})
    if not images:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram generate returned no images.",
        )
    chosen = images[0]
    if not chosen.is_image_safe or not chosen.url:
        raise IdeogramProviderError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Ideogram generate failed the safety check.",
        )
    return chosen


def download_remote_image(url: str, *, timeout: float = 60.0) -> bytes:
    """Download an ephemeral Ideogram URL immediately. Do not persist only the remote URL."""
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException as exc:
        raise IdeogramProviderError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Timed out downloading the Ideogram image.",
        ) from exc
    except httpx.HTTPError as exc:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Failed to download the Ideogram image.",
        ) from exc
    if response.status_code != 200 or not response.content:
        raise IdeogramProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Ideogram image download failed.",
        )
    return bytes(response.content)


def generate_creative(
    *,
    api_key: str,
    prompt: str,
    source_image: tuple[bytes, str, str] | None,
    rendering_speed: str,
    image_weight: int = 65,
    variant: str | None = None,
) -> IdeogramRemoteImage:
    """Conceptual: generateCreative({ prompt, sourceImage, aspectRatio, count })."""
    if source_image is not None:
        image_bytes, filename, content_type = source_image
        return remix_image(
            api_key=api_key,
            image_bytes=image_bytes,
            filename=filename,
            content_type=content_type,
            text_prompt=prompt,
            rendering_speed=rendering_speed,
            image_weight=image_weight,
            variant=variant,
        )
    return generate_image(
        api_key=api_key,
        text_prompt=prompt,
        rendering_speed=rendering_speed,
        variant=variant,
    )
