"""LLMProvider abstraction — OpenAI / Azure OpenAI / Local (deterministic grounded)."""

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
            raw={"grounded": bool(chunks), "chunk_count": len(chunks)},
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
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
        }
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        usage = data.get("usage") or {}
        return LLMResult(
            answer=text.strip() or INSUFFICIENT_EVIDENCE_MESSAGE,
            provider=self.name,
            model=self._model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw={"id": data.get("id")},
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
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                url,
                headers={"api-key": self._api_key, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        usage = data.get("usage") or {}
        return LLMResult(
            answer=text.strip() or INSUFFICIENT_EVIDENCE_MESSAGE,
            provider=self.name,
            model=self._model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw={"id": data.get("id")},
        )


_EVIDENCE_BLOCK_RE = re.compile(
    r"---\s*EVIDENCE_START\s*---\s*(.*?)\s*---\s*EVIDENCE_END\s*---",
    re.DOTALL | re.IGNORECASE,
)


def _clip(text: str, n: int) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


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


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Settings-driven LLM resolution.

    Falls back to local grounded provider when no API key / misconfigured Azure.
    Business logic must call this — never import OpenAI/Azure clients elsewhere.
    """
    settings = settings or get_settings()
    provider = (settings.ai_provider or "local").strip().lower()
    model = settings.ai_model or "local-grounded-v1"

    if provider in {"local", "fake", "hash", "heuristic"}:
        return LocalGroundedLLMProvider(model=model if model.startswith("local") else "local-grounded-v1")

    api_key = settings.ai_api_key
    if not api_key:
        logger.info("llm_provider_fallback_local", extra={"requested": provider})
        return LocalGroundedLLMProvider()

    if provider in {"openai"}:
        base = settings.ai_base_url or "https://api.openai.com/v1"
        return OpenAILLMProvider(
            api_key=api_key,
            model=model if not model.startswith("local") else "gpt-4o-mini",
            base_url=base,
        )

    if provider in {"azure", "azure_openai"}:
        endpoint = settings.ai_azure_endpoint
        deployment = settings.ai_azure_deployment or model
        if not endpoint or not deployment:
            logger.warning("azure_llm_misconfigured_fallback_local")
            return LocalGroundedLLMProvider()
        return AzureOpenAILLMProvider(
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            api_version=settings.ai_azure_api_version,
        )

    logger.warning("unknown_llm_provider_fallback_local", extra={"provider": provider})
    return LocalGroundedLLMProvider()
