"""LLMProvider abstraction — OpenAI / Azure OpenAI / local mock (deterministic grounded).

Provider selection is settings-driven via ``get_llm_provider``.

Explicit local / mock aliases (deterministic, offline, tests):
  ``mock``, ``local``, ``fake``, ``hash``, ``heuristic``

External providers (``openai``, ``azure`` / ``azure_openai``) are fail-closed:
missing/blank API key or incomplete Azure config raises ``LLMProviderConfigError``.
There is no silent OpenAI → mock fallback.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from investhome_api.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I couldn't find enough verified project information."
)

# Explicit offline / test providers only — never selected implicitly for openai/azure.
LOCAL_PROVIDER_ALIASES = frozenset({"mock", "local", "fake", "hash", "heuristic"})


class LLMProviderError(Exception):
    """Base class for LLM provider failures (config or request)."""

    def __init__(
        self,
        message: str,
        *,
        category: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.provider = provider
        self.model = model
        self.message = message


class LLMProviderConfigError(LLMProviderError):
    """Fail-closed configuration error — do not fall back to mock."""


class LLMProviderRequestError(LLMProviderError):
    """Upstream LLM request failure (auth, HTTP, transport)."""


@dataclass(frozen=True)
class LLMResult:
    answer: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, *, system: str, user: str, timeout_seconds: float = 45.0) -> LLMResult:
        """Generate a grounded answer. Must not invent facts beyond the prompt."""

    @property
    @abstractmethod
    def model(self) -> str: ...


class LocalGroundedLLMProvider(LLMProvider):
    """
    Deterministic local/fake provider for tests and offline use.

    Builds answers only from injected evidence chunks in the user prompt.
    Never fabricates when evidence markers are missing or empty.
    """

    name = "local"

    def __init__(self, *, model: str = "local-grounded-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def generate(self, *, system: str, user: str, timeout_seconds: float = 45.0) -> LLMResult:
        _ = system, timeout_seconds
        if "CONTENT_PACKAGE_JSON" in (user or "") or "CONTENT_PACKAGE_JSON" in (system or ""):
            answer = _local_content_package_answer(user)
            return LLMResult(
                answer=answer,
                provider=self.name,
                model=self._model,
                input_tokens=max(1, (len(system) + len(user)) // 4),
                output_tokens=max(1, len(answer) // 4),
                raw={"grounded": True, "mode": "mock", "kind": "content_package"},
            )
        # Social Design Engine asks for structured Design Ops JSON.
        if "DESIGN_OPS_JSON" in (user or "") or "DESIGN_OPS_JSON" in (system or ""):
            answer = _local_design_ops_answer(user)
            return LLMResult(
                answer=answer,
                provider=self.name,
                model=self._model,
                input_tokens=max(1, (len(system) + len(user)) // 4),
                output_tokens=max(1, len(answer) // 4),
                raw={"grounded": True, "mode": "mock", "kind": "design_ops"},
            )

        chunks = _extract_evidence_chunks(user)
        if not chunks:
            answer = INSUFFICIENT_EVIDENCE_MESSAGE
        else:
            # Deterministic grounded answer: lead with first chunk snippet + cite refs.
            lead = chunks[0]
            snippet = _clip(lead["text"], 420)
            refs = []
            for c in chunks[:5]:
                refs.append(
                    f"[{c.get('document_name') or 'document'} / chunk {c.get('chunk_order', '?')}]"
                )
            answer = (
                f"According to verified project documents: {snippet}\n\n"
                f"Sources: {', '.join(refs)}"
            )
        return LLMResult(
            answer=answer,
            provider=self.name,
            model=self._model,
            input_tokens=max(1, (len(system) + len(user)) // 4),
            output_tokens=max(1, len(answer) // 4),
            raw={"grounded": bool(chunks), "chunk_count": len(chunks), "mode": "mock"},
        )


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def model(self) -> str:
        return self._model

    def generate(self, *, system: str, user: str, timeout_seconds: float = 45.0) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
        }
        if "CONTENT_PACKAGE_JSON" in (user or "") or "CONTENT_PACKAGE_JSON" in (system or ""):
            payload["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                category = "invalid_api_key"
                message = (
                    "OpenAI authentication failed: AI_API_KEY is missing or invalid "
                    f"(HTTP {status_code})"
                )
            else:
                category = "upstream_http_error"
                message = f"OpenAI request failed with HTTP {status_code}"
            _log_provider_event(
                "llm_provider_request_failed",
                level=logging.ERROR,
                provider=self.name,
                model=self._model,
                mode="real",
                category=category,
            )
            raise LLMProviderRequestError(
                message,
                category=category,
                provider=self.name,
                model=self._model,
            ) from exc
        except httpx.RequestError as exc:
            _log_provider_event(
                "llm_provider_request_failed",
                level=logging.ERROR,
                provider=self.name,
                model=self._model,
                mode="real",
                category="transport_error",
            )
            raise LLMProviderRequestError(
                "OpenAI request failed due to a network/transport error",
                category="transport_error",
                provider=self.name,
                model=self._model,
            ) from exc

        data = response.json()
        message = (data.get("choices") or [{}])[0].get("message", {}) if isinstance(data, dict) else {}
        text = _message_content_text(message)
        usage = data.get("usage") or {} if isinstance(data, dict) else {}
        return LLMResult(
            answer=text.strip() or INSUFFICIENT_EVIDENCE_MESSAGE,
            provider=self.name,
            model=self._model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw={"id": data.get("id") if isinstance(data, dict) else None, "mode": "real"},
        )


class AzureOpenAILLMProvider(LLMProvider):
    name = "azure_openai"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._deployment = deployment
        self._api_version = api_version
        self._model = deployment

    @property
    def model(self) -> str:
        return self._model

    def generate(self, *, system: str, user: str, timeout_seconds: float = 45.0) -> LLMResult:
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}/chat/completions"
            f"?api-version={self._api_version}"
        )
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
        }
        if "CONTENT_PACKAGE_JSON" in (user or "") or "CONTENT_PACKAGE_JSON" in (system or ""):
            payload["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={"api-key": self._api_key, "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                category = "invalid_api_key"
                message = (
                    "Azure OpenAI authentication failed: AI_API_KEY is missing or invalid "
                    f"(HTTP {status_code})"
                )
            else:
                category = "upstream_http_error"
                message = f"Azure OpenAI request failed with HTTP {status_code}"
            _log_provider_event(
                "llm_provider_request_failed",
                level=logging.ERROR,
                provider=self.name,
                model=self._model,
                mode="real",
                category=category,
            )
            raise LLMProviderRequestError(
                message,
                category=category,
                provider=self.name,
                model=self._model,
            ) from exc
        except httpx.RequestError as exc:
            _log_provider_event(
                "llm_provider_request_failed",
                level=logging.ERROR,
                provider=self.name,
                model=self._model,
                mode="real",
                category="transport_error",
            )
            raise LLMProviderRequestError(
                "Azure OpenAI request failed due to a network/transport error",
                category="transport_error",
                provider=self.name,
                model=self._model,
            ) from exc

        data = response.json()
        message = (data.get("choices") or [{}])[0].get("message", {}) if isinstance(data, dict) else {}
        text = _message_content_text(message)
        usage = data.get("usage") or {} if isinstance(data, dict) else {}
        return LLMResult(
            answer=text.strip() or INSUFFICIENT_EVIDENCE_MESSAGE,
            provider=self.name,
            model=self._model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw={"id": data.get("id") if isinstance(data, dict) else None, "mode": "real"},
        )


_EVIDENCE_BLOCK_RE = re.compile(
    r"---\s*EVIDENCE_START\s*---\s*(.*?)\s*---\s*EVIDENCE_END\s*---",
    re.DOTALL | re.IGNORECASE,
)


def _local_design_ops_answer(user_prompt: str) -> str:
    """Deterministic Design Ops JSON for local/mock provider (no fabricated media)."""
    # Empty ops → design service falls back to heuristic with real media candidates.
    # Returning empty keeps local provider from inventing Asset IDs.
    _ = user_prompt
    return json.dumps(
        {
            "ops": [],
            "summary": "local_provider_defers_to_heuristic",
        },
        ensure_ascii=False,
    )


def _local_content_package_answer(user_prompt: str) -> str:
    """Echo Copy Director / Creative Director copy — never invent project facts."""
    payload: dict[str, Any] = {}
    raw = user_prompt or ""
    start = raw.find("{")
    if start >= 0:
        try:
            payload, _ = json.JSONDecoder().raw_decode(raw, start)
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    copy_pkg = payload.get("final_copy_package") if isinstance(payload.get("final_copy_package"), dict) else {}
    concept = payload.get("creative_concept") if isinstance(payload.get("creative_concept"), dict) else {}
    identity = payload.get("project_identity") if isinstance(payload.get("project_identity"), dict) else {}
    headline = str(
        copy_pkg.get("headline")
        or concept.get("primary_message")
        or identity.get("project_name")
        or "Project"
    ).strip()
    supporting = str(copy_pkg.get("supporting_text") or concept.get("supporting_message") or "").strip()
    cta = str(copy_pkg.get("cta") or concept.get("cta") or "Schedule a private tour").strip()
    eyebrow = str(copy_pkg.get("eyebrow") or "").strip()
    if not eyebrow:
        eyebrow = str(concept.get("eyebrow") or "").strip() if concept.get("include_eyebrow") else ""
    return json.dumps(
        {
            "eyebrow": eyebrow,
            "headline": headline,
            "supporting_text": supporting,
            "cta": cta,
            "language": str(payload.get("language") or "en"),
            "tone": str(concept.get("tone") or copy_pkg.get("tone") or "premium"),
        },
        ensure_ascii=False,
    )


def _clip(text: str, n: int) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def _message_content_text(message: Any) -> str:
    """Normalize chat-completions message.content (string or content parts)."""
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return ""


def _extract_evidence_chunks(user_prompt: str) -> list[dict[str, Any]]:
    """Parse JSON evidence block injected by the prompt builder."""
    match = _EVIDENCE_BLOCK_RE.search(user_prompt or "")
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw or raw in {"[]", "null", "None"}:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(item)
    return out


def _normalize_api_key(raw: str | None) -> str | None:
    key = (raw or "").strip()
    return key or None


def _log_provider_event(
    event: str,
    *,
    level: int = logging.INFO,
    provider: str | None,
    model: str | None,
    mode: str,
    category: str,
    requested: str | None = None,
) -> None:
    """Observability without secrets, headers, or full private prompts."""
    extra: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "mode": mode,
        "category": category,
    }
    if requested is not None:
        extra["requested"] = requested
    logger.log(level, event, extra=extra)


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Settings-driven LLM resolution.

    Local/mock aliases return ``LocalGroundedLLMProvider``.
    ``openai`` / ``azure_openai`` require a valid ``AI_API_KEY`` (and Azure endpoint
    fields). Misconfiguration raises ``LLMProviderConfigError`` — never silent mock.
    Business logic must call this — never import OpenAI/Azure clients elsewhere.
    """
    settings = settings or get_settings()
    provider = (settings.ai_provider or "local").strip().lower()
    model = (settings.ai_model or "local-grounded-v1").strip() or "local-grounded-v1"
    api_key = _normalize_api_key(settings.ai_api_key)

    if provider in LOCAL_PROVIDER_ALIASES:
        local_model = model if model.startswith("local") else "local-grounded-v1"
        selected = LocalGroundedLLMProvider(model=local_model)
        _log_provider_event(
            "llm_provider_selected",
            provider=selected.name,
            model=selected.model,
            mode="mock",
            category="explicit_local",
            requested=provider,
        )
        return selected

    if provider == "openai":
        if not api_key:
            _log_provider_event(
                "llm_provider_config_error",
                level=logging.ERROR,
                provider="openai",
                model=model,
                mode="real",
                category="missing_api_key",
                requested=provider,
            )
            raise LLMProviderConfigError(
                "AI_PROVIDER=openai requires a non-empty AI_API_KEY "
                "(set in .env or the process environment). "
                "Refusing silent mock fallback.",
                category="missing_api_key",
                provider="openai",
                model=model,
            )
        resolved_model = model if not model.startswith("local") else "gpt-4o-mini"
        base = settings.ai_base_url or "https://api.openai.com/v1"
        selected = OpenAILLMProvider(
            api_key=api_key,
            model=resolved_model,
            base_url=base,
        )
        _log_provider_event(
            "llm_provider_selected",
            provider=selected.name,
            model=selected.model,
            mode="real",
            category="configured",
            requested=provider,
        )
        return selected

    if provider in {"azure", "azure_openai"}:
        endpoint = (settings.ai_azure_endpoint or "").strip() or None
        deployment = (settings.ai_azure_deployment or model or "").strip() or None
        if not api_key:
            _log_provider_event(
                "llm_provider_config_error",
                level=logging.ERROR,
                provider="azure_openai",
                model=model,
                mode="real",
                category="missing_api_key",
                requested=provider,
            )
            raise LLMProviderConfigError(
                "AI_PROVIDER=azure_openai requires a non-empty AI_API_KEY. "
                "Refusing silent mock fallback.",
                category="missing_api_key",
                provider="azure_openai",
                model=model,
            )
        if not endpoint or not deployment:
            _log_provider_event(
                "llm_provider_config_error",
                level=logging.ERROR,
                provider="azure_openai",
                model=model,
                mode="real",
                category="azure_misconfigured",
                requested=provider,
            )
            raise LLMProviderConfigError(
                "AI_PROVIDER=azure_openai requires AI_AZURE_ENDPOINT and "
                "AI_AZURE_DEPLOYMENT (or AI_MODEL). Refusing silent mock fallback.",
                category="azure_misconfigured",
                provider="azure_openai",
                model=model,
            )
        selected = AzureOpenAILLMProvider(
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            api_version=settings.ai_azure_api_version,
        )
        _log_provider_event(
            "llm_provider_selected",
            provider=selected.name,
            model=selected.model,
            mode="real",
            category="configured",
            requested=provider,
        )
        return selected

    _log_provider_event(
        "llm_provider_config_error",
        level=logging.ERROR,
        provider=provider,
        model=model,
        mode="unknown",
        category="unknown_provider",
        requested=provider,
    )
    raise LLMProviderConfigError(
        f"Unknown AI_PROVIDER={provider!r}. "
        f"Use openai, azure_openai, or an explicit local alias: "
        f"{', '.join(sorted(LOCAL_PROVIDER_ALIASES))}.",
        category="unknown_provider",
        provider=provider,
        model=model,
    )
