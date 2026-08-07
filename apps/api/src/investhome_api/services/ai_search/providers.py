"""EmbeddingProvider abstraction — OpenAI / Azure / Local (deterministic)."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from investhome_api.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜäöüÄÖÜ0-9]{2,}")


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    provider: str
    dimensions: int


class EmbeddingProvider(ABC):
    name: str

    @abstractmethod
    def embed(self, texts: list[str]) -> EmbeddingResult:
        """Batch-embed texts. Implementations must not mutate Drive / originals."""

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return vec
    return [v / norm for v in vec]


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic feature-hash embeddings — no network, works offline / tests."""

    name = "local"

    def __init__(self, *, model: str = "local-hash-v1", dimensions: int = 64) -> None:
        self._model = model
        self._dimensions = max(8, dimensions)

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> EmbeddingResult:
        vectors = [self._embed_one(t) for t in texts]
        return EmbeddingResult(
            vectors=vectors,
            model=self._model,
            provider=self.name,
            dimensions=self._dimensions,
        )

    def _embed_one(self, text: str) -> list[float]:
        dims = self._dimensions
        vec = [0.0] * dims
        tokens = _TOKEN_RE.findall((text or "").lower())
        if not tokens:
            # Stable non-zero vector for empty-ish text
            digest = hashlib.sha256((text or "").encode("utf-8")).digest()
            for i in range(dims):
                vec[i] = ((digest[i % len(digest)] / 255.0) * 2.0) - 1.0
            return _l2_normalize(vec)

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            vec[idx] += sign * weight
        return _l2_normalize(vec)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._base_url = base_url.rstrip("/")

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult([], self._model, self.name, self._dimensions)
        payload: dict = {"model": self._model, "input": texts}
        # text-embedding-3-* supports dimensions param
        if self._model.startswith("text-embedding-3"):
            payload["dimensions"] = self._dimensions
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        vectors = [_l2_normalize([float(v) for v in item["embedding"]]) for item in items]
        dims = len(vectors[0]) if vectors else self._dimensions
        return EmbeddingResult(
            vectors=vectors,
            model=self._model,
            provider=self.name,
            dimensions=dims,
        )


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    name = "azure_openai"

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-02-01",
        dimensions: int = 1536,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._deployment = deployment
        self._api_version = api_version
        self._dimensions = dimensions
        self._model = deployment

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult([], self._model, self.name, self._dimensions)
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}/embeddings"
            f"?api-version={self._api_version}"
        )
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                headers={"api-key": self._api_key, "Content-Type": "application/json"},
                json={"input": texts},
            )
            response.raise_for_status()
            data = response.json()
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        vectors = [_l2_normalize([float(v) for v in item["embedding"]]) for item in items]
        dims = len(vectors[0]) if vectors else self._dimensions
        return EmbeddingResult(
            vectors=vectors,
            model=self._model,
            provider=self.name,
            dimensions=dims,
        )


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Resolve provider from settings. Falls back to local when no API key."""
    settings = settings or get_settings()
    provider = (settings.embedding_provider or "local").strip().lower()
    model = settings.embedding_model
    dims = settings.embedding_dimensions

    if provider in {"local", "hash", "fake"}:
        return LocalHashEmbeddingProvider(model=model or "local-hash-v1", dimensions=dims)

    api_key = settings.embedding_api_key or settings.ai_api_key
    if not api_key:
        logger.info("embedding_provider_fallback_local", extra={"requested": provider})
        return LocalHashEmbeddingProvider(
            model=model or "local-hash-v1",
            dimensions=dims if dims <= 256 else 64,
        )

    if provider in {"openai"}:
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=model or "text-embedding-3-small",
            dimensions=dims,
            base_url=settings.embedding_base_url or "https://api.openai.com/v1",
        )

    if provider in {"azure", "azure_openai"}:
        endpoint = settings.embedding_azure_endpoint
        deployment = settings.embedding_azure_deployment or model
        if not endpoint or not deployment:
            logger.warning("azure_embedding_misconfigured_fallback_local")
            return LocalHashEmbeddingProvider(model="local-hash-v1", dimensions=64)
        return AzureOpenAIEmbeddingProvider(
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            api_version=settings.embedding_azure_api_version,
            dimensions=dims,
        )

    logger.warning("unknown_embedding_provider_fallback_local", extra={"provider": provider})
    return LocalHashEmbeddingProvider(model="local-hash-v1", dimensions=64)
