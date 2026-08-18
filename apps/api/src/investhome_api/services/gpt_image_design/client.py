"""Official OpenAI Images API client (edits + generations). Never logs secrets."""

from __future__ import annotations

import base64
import logging
import threading
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from investhome_api.services.gpt_image_design.config import (
    CALL_TIMEOUT_SECONDS,
    DEFAULT_BASE_URL,
    EDITS_ENDPOINT_PATH,
    GENERATIONS_ENDPOINT_PATH,
    is_gpt_image_2,
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
        "gpt_image_provider_call",
        extra={
            "provider": "gpt-image",
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


class GptImageProviderError(HTTPException):
    """Recoverable GPT Image API failure — never a silent Native/Ideogram fallback."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(status_code=status_code, detail=message)


@dataclass
class GptImageRemote:
    b64_json: str | None
    url: str | None
    revised_prompt: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    def image_bytes(self) -> bytes:
        if self.b64_json:
            try:
                return base64.b64decode(self.b64_json)
            except Exception as exc:
                raise GptImageProviderError(
                    status.HTTP_502_BAD_GATEWAY,
                    "GPT Image returned invalid base64 image data.",
                ) from exc
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image returned no image bytes.",
        )


def edits_url(base_url: str) -> str:
    return f"{(base_url or DEFAULT_BASE_URL).rstrip('/')}{EDITS_ENDPOINT_PATH}"


def generations_url(base_url: str) -> str:
    return f"{(base_url or DEFAULT_BASE_URL).rstrip('/')}{GENERATIONS_ENDPOINT_PATH}"


def _provider_error_excerpt(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    err = payload.get("error")
    if isinstance(err, dict):
        message = err.get("message") or err.get("code") or err.get("type")
        if isinstance(message, str) and message.strip():
            text = message.strip()
            if "api-key" in text.lower() or "api_key" in text.lower() or "sk-" in text.lower():
                return (err.get("code") or err.get("type") or "provider_error")[:180]
            return text[:180]
    for key in ("message", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:180]
    return ""


def _map_http_error(response: httpx.Response) -> GptImageProviderError:
    code = response.status_code
    excerpt = _provider_error_excerpt(response)
    suffix = f" {excerpt}" if excerpt else ""
    if code == 401:
        return GptImageProviderError(
            status.HTTP_401_UNAUTHORIZED,
            "GPT Image authentication failed (401). Check AI_API_KEY.",
        )
    if code == 402:
        return GptImageProviderError(
            status.HTTP_402_PAYMENT_REQUIRED,
            "GPT Image payment required (402). Native/Ideogram generation was not used."
            f"{suffix}",
        )
    if code == 403:
        return GptImageProviderError(
            status.HTTP_403_FORBIDDEN,
            f"GPT Image refused the request (403).{suffix} Native/Ideogram generation was not used.",
        )
    if code == 422:
        return GptImageProviderError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"GPT Image rejected the prompt or source image (422).{suffix}",
        )
    if code == 429:
        return GptImageProviderError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "GPT Image rate limited this request (429). Retry later. "
            "Native/Ideogram generation was not used.",
        )
    if code == 400:
        return GptImageProviderError(
            status.HTTP_400_BAD_REQUEST,
            f"GPT Image validation failed (400).{suffix}",
        )
    if code >= 500:
        return GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            f"GPT Image provider error ({code}). Native/Ideogram generation was not used.{suffix}",
        )
    return GptImageProviderError(
        status.HTTP_502_BAD_GATEWAY,
        f"GPT Image request failed ({code}). Native/Ideogram generation was not used.{suffix}",
    )


def _parse_images(payload: dict[str, Any]) -> list[GptImageRemote]:
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    out: list[GptImageRemote] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        b64 = row.get("b64_json")
        url = row.get("url")
        out.append(
            GptImageRemote(
                b64_json=str(b64).strip() if b64 else None,
                url=str(url).strip() if url else None,
                revised_prompt=str(row["revised_prompt"]) if row.get("revised_prompt") else None,
                raw=row,
            )
        )
    return out


def edit_image(
    *,
    api_key: str,
    model: str,
    prompt: str,
    images: list[tuple[bytes, str, str]],
    size: str,
    quality: str,
    base_url: str = DEFAULT_BASE_URL,
    variant: str | None = None,
    timeout: float = CALL_TIMEOUT_SECONDS,
) -> GptImageRemote:
    """POST /v1/images/edits — official multi-image edit. Project mode only."""
    if not images:
        raise GptImageProviderError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "GPT Image project mode requires a real project source image. "
            "Text-to-image was not used. Native/Ideogram generation was not used.",
        )
    endpoint = edits_url(base_url)
    _bump_call_count(endpoint=endpoint, variant=variant)
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for image_bytes, filename, content_type in images:
        files.append(
            (
                "image[]",
                (
                    filename or "source.png",
                    image_bytes,
                    content_type or "image/png",
                ),
            )
        )
    data: dict[str, str] = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": "1",
    }
    if not is_gpt_image_2(model):
        data["input_fidelity"] = "high"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = httpx.post(
            endpoint,
            headers=headers,
            data=data,
            files=files,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise GptImageProviderError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "GPT Image edit timed out. Native/Ideogram generation was not used.",
        ) from exc
    except httpx.HTTPError as exc:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image edit network error. Native/Ideogram generation was not used.",
        ) from exc
    logger.info(
        "gpt_image_http_result provider=gpt-image endpoint=%s mode=edits variant=%s http_status=%s",
        endpoint,
        variant,
        response.status_code,
    )
    if response.status_code != 200:
        raise _map_http_error(response)
    try:
        payload = response.json()
    except ValueError as exc:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image edit returned a non-JSON body.",
        ) from exc
    images_out = _parse_images(payload if isinstance(payload, dict) else {})
    if not images_out:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image edit returned no images. Native/Ideogram generation was not used.",
        )
    chosen = images_out[0]
    if not chosen.b64_json and not chosen.url:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image edit returned an empty image payload.",
        )
    logger.info(
        "gpt_image_edit_ok",
        extra={
            "provider": "gpt-image",
            "endpoint": endpoint,
            "mode": "edits",
            "variant": variant,
            "http_status": 200,
            "model": model,
            "size": size,
            "input_image_count": len(images),
            "remote_host": _safe_host(chosen.url),
            "has_b64": bool(chosen.b64_json),
        },
    )
    return chosen


def generate_image(
    *,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    quality: str,
    base_url: str = DEFAULT_BASE_URL,
    variant: str | None = None,
    timeout: float = CALL_TIMEOUT_SECONDS,
) -> GptImageRemote:
    """POST /v1/images/generations — general Investhome text-to-image. Not a project fallback."""
    endpoint = generations_url(base_url)
    _bump_call_count(endpoint=endpoint, variant=variant)
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(endpoint, headers=headers, json=payload, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise GptImageProviderError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "GPT Image generate timed out. Native/Ideogram generation was not used.",
        ) from exc
    except httpx.HTTPError as exc:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image generate network error. Native/Ideogram generation was not used.",
        ) from exc
    logger.info(
        "gpt_image_http_result provider=gpt-image endpoint=%s mode=generations variant=%s http_status=%s",
        endpoint,
        variant,
        response.status_code,
    )
    if response.status_code != 200:
        raise _map_http_error(response)
    try:
        body = response.json()
    except ValueError as exc:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image generate returned a non-JSON body.",
        ) from exc
    images_out = _parse_images(body if isinstance(body, dict) else {})
    if not images_out:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image generate returned no images.",
        )
    chosen = images_out[0]
    if not chosen.b64_json and not chosen.url:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image generate returned an empty image payload.",
        )
    return chosen


def download_remote_image(url: str, *, timeout: float = 60.0) -> bytes:
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException as exc:
        raise GptImageProviderError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Timed out downloading the GPT Image result.",
        ) from exc
    except httpx.HTTPError as exc:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "Failed to download the GPT Image result.",
        ) from exc
    if response.status_code != 200 or not response.content:
        raise GptImageProviderError(
            status.HTTP_502_BAD_GATEWAY,
            "GPT Image result download failed.",
        )
    return bytes(response.content)


def decode_remote_image(remote: GptImageRemote) -> bytes:
    if remote.b64_json:
        return remote.image_bytes()
    if remote.url:
        return download_remote_image(remote.url)
    raise GptImageProviderError(
        status.HTTP_502_BAD_GATEWAY,
        "GPT Image returned no image bytes.",
    )
