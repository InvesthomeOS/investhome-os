"""Typed adapters for optional Knowledge Hub providers.

Honest unavailable when OCR / vector / malware providers are missing.
AI output is always stored separately and never overwrites original files.
"""

from __future__ import annotations

import os

from investhome_api.config.settings import get_settings
from investhome_api.schemas.knowledge import ProviderCapabilityStatus


def ocr_capability() -> ProviderCapabilityStatus:
    settings = get_settings()
    provider = getattr(settings, "ocr_provider", "local") or "local"
    try:
        from investhome_api.services.document_intelligence.ocr import get_ocr_provider

        ocr = get_ocr_provider()
        available = ocr.is_available() and ocr.name != "dev_fallback"
        reason = None if available else "OCR provider not fully configured (Tesseract/cloud OCR missing)"
        return ProviderCapabilityStatus(
            provider=ocr.name,
            available=available,
            reason=reason,
            required_env=["OCR_PROVIDER", "TESSERACT_CMD (optional)"],
            endpoints=["POST /documents/{id}/reprocess"],
        )
    except Exception:
        return ProviderCapabilityStatus(
            provider=provider,
            available=False,
            reason="OCR adapter failed to initialize",
            required_env=["OCR_PROVIDER"],
            endpoints=["POST /documents/{id}/reprocess"],
        )


def ai_capability() -> ProviderCapabilityStatus:
    settings = get_settings()
    api_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
    provider_name = getattr(settings, "ai_provider", None) or os.getenv("AI_PROVIDER") or "openai"
    if api_key:
        return ProviderCapabilityStatus(
            provider=str(provider_name),
            available=True,
            reason=None,
            required_env=["OPENAI_API_KEY", "AI_PROVIDER"],
            endpoints=[
                "GET /documents/{id}/analysis",
                "POST /documents/{id}/ask",
                "POST /knowledge/ai-search",
            ],
        )
    return ProviderCapabilityStatus(
        provider=str(provider_name),
        available=False,
        reason="AI provider API key not configured — summaries use local fallback when available",
        required_env=["OPENAI_API_KEY", "AI_PROVIDER", "AI_MODEL"],
        endpoints=[
            "GET /documents/{id}/analysis",
            "POST /documents/{id}/ask",
            "POST /knowledge/ai-search",
        ],
    )


def vector_capability() -> ProviderCapabilityStatus:
    """Embedding / vector search — schema exists on DocumentChunk; provider optional."""
    embed_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
    vector_url = os.getenv("VECTOR_STORE_URL")
    if embed_key and vector_url:
        return ProviderCapabilityStatus(
            provider=os.getenv("VECTOR_STORE_PROVIDER", "pgvector"),
            available=True,
            reason=None,
            required_env=["EMBEDDING_API_KEY", "VECTOR_STORE_URL", "VECTOR_STORE_PROVIDER"],
            endpoints=["POST /knowledge/ai-search"],
        )
    return ProviderCapabilityStatus(
        provider=os.getenv("VECTOR_STORE_PROVIDER", "none"),
        available=False,
        reason="Vector store not configured — citation search uses keyword/chunk matching",
        required_env=["EMBEDDING_API_KEY", "VECTOR_STORE_URL", "VECTOR_STORE_PROVIDER"],
        endpoints=["POST /knowledge/ai-search"],
    )


def malware_capability() -> ProviderCapabilityStatus:
    provider = os.getenv("MALWARE_SCAN_PROVIDER")
    endpoint = os.getenv("MALWARE_SCAN_ENDPOINT")
    if provider and endpoint:
        return ProviderCapabilityStatus(
            provider=provider,
            available=True,
            reason=None,
            required_env=["MALWARE_SCAN_PROVIDER", "MALWARE_SCAN_ENDPOINT", "MALWARE_SCAN_API_KEY"],
            endpoints=["POST /documents (upload scan hook)"],
        )
    return ProviderCapabilityStatus(
        provider=provider or "none",
        available=False,
        reason="Malware scanning not configured — status shown as unavailable",
        required_env=["MALWARE_SCAN_PROVIDER", "MALWARE_SCAN_ENDPOINT", "MALWARE_SCAN_API_KEY"],
        endpoints=["POST /documents (upload scan hook)"],
    )


def indexing_capability() -> ProviderCapabilityStatus:
    """Document text indexing uses existing chunk pipeline when processing completes."""
    return ProviderCapabilityStatus(
        provider="document_chunks",
        available=True,
        reason=None,
        required_env=[],
        endpoints=["GET /documents/{id}/processing-status", "POST /documents/{id}/reprocess"],
    )


def all_provider_statuses() -> dict[str, ProviderCapabilityStatus]:
    return {
        "ocr": ocr_capability(),
        "ai": ai_capability(),
        "vector": vector_capability(),
        "malware": malware_capability(),
        "indexing": indexing_capability(),
    }
