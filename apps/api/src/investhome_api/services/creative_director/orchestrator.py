"""Capability-based AI provider registry for Creative Director orchestration.

Business logic maps needs → capabilities. Provider names stay in this registry only.
Missing capabilities are reported — never silently substituted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from investhome_api.config.settings import Settings, get_settings

# Canonical capability keys — extend carefully; do not hardcode providers in callers.
CAPABILITIES: tuple[str, ...] = (
    "text",
    "reasoning",
    "image_generate",
    "image_edit",
    "video_generate",
    "video_edit",
    "architecture_render",
    "voice",
    "music",
    "presentation",
    "document",
)


@dataclass(frozen=True)
class ProviderCapability:
    provider_id: str
    capabilities: tuple[str, ...]
    available: bool
    configured: bool
    reason: str | None = None
    model: str | None = None


@dataclass
class CapabilityAssignment:
    capability: str
    required: bool
    provider_id: str | None
    available: bool
    missing: bool
    reason: str | None = None


@dataclass
class OrchestrationPlan:
    required_capabilities: list[str]
    assignments: list[CapabilityAssignment]
    providers: list[dict[str, Any]] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_capabilities": list(self.required_capabilities),
            "assignments": [asdict(a) for a in self.assignments],
            "providers": list(self.providers),
            "missing_capabilities": list(self.missing_capabilities),
        }


def _llm_provider_status(settings: Settings) -> ProviderCapability:
    provider = (settings.ai_provider or "local").strip().lower()
    model = (settings.ai_model or "").strip() or None
    if provider in {"mock", "local", "fake", "hash", "heuristic"}:
        return ProviderCapability(
            provider_id="openai_gpt",
            capabilities=("text", "reasoning"),
            available=True,
            configured=True,
            reason="local/mock LLM provider active",
            model=model or "local-grounded-v1",
        )
    if provider in {"openai", "azure", "azure_openai"}:
        key = (settings.ai_api_key or "").strip()
        ok = bool(key)
        if provider.startswith("azure"):
            ok = ok and bool((getattr(settings, "ai_azure_endpoint", None) or "").strip())
        return ProviderCapability(
            provider_id="openai_gpt",
            capabilities=("text", "reasoning"),
            available=ok,
            configured=ok,
            reason=None if ok else "AI_API_KEY (or Azure config) missing",
            model=model,
        )
    return ProviderCapability(
        provider_id="openai_gpt",
        capabilities=("text", "reasoning"),
        available=False,
        configured=False,
        reason=f"Unsupported AI_PROVIDER={provider}",
        model=model,
    )


def _gpt_image_status(settings: Settings) -> ProviderCapability:
    from investhome_api.services.gpt_image_design.config import provider_availability

    avail = provider_availability(settings)
    return ProviderCapability(
        provider_id="gpt_image",
        capabilities=("image_generate", "image_edit"),
        available=bool(avail.available),
        configured=bool(avail.configured),
        reason=avail.reason,
        model=avail.model,
    )


def _ideogram_status(settings: Settings) -> ProviderCapability:
    from investhome_api.services.ideogram_design_poc.config import provider_availability

    avail = provider_availability(settings)
    return ProviderCapability(
        provider_id="ideogram",
        capabilities=("image_generate", "image_edit"),
        available=bool(avail.available),
        configured=bool(avail.configured),
        reason=avail.reason,
        model=getattr(avail, "model", None) or settings.ideogram_model,
    )


def _stub(provider_id: str, *capabilities: str, reason: str) -> ProviderCapability:
    return ProviderCapability(
        provider_id=provider_id,
        capabilities=capabilities,
        available=False,
        configured=False,
        reason=reason,
        model=None,
    )


def list_providers(settings: Settings | None = None) -> list[ProviderCapability]:
    s = settings or get_settings()
    return [
        _llm_provider_status(s),
        _gpt_image_status(s),
        _ideogram_status(s),
        _stub("video_stub", "video_generate", "video_edit", reason="Video provider not configured"),
        _stub(
            "architecture_stub",
            "architecture_render",
            reason="Architecture render provider not configured",
        ),
        _stub("voice_stub", "voice", reason="Voice provider not configured"),
        _stub("music_stub", "music", reason="Music provider not configured"),
        _stub("presentation_stub", "presentation", reason="Presentation provider not configured"),
        _stub("document_stub", "document", reason="Document generation provider not configured"),
    ]


def infer_required_capabilities(
    *,
    brief: str,
    mode: str = "project",
    formats: list[str] | None = None,
) -> list[str]:
    """Infer production capabilities from brief language. No generation this sprint."""
    t = (brief or "").lower()
    required: list[str] = ["text", "reasoning"]
    # Project mode still documents image_edit for later real-asset composition;
    # this sprint does NOT call image providers.
    if mode == "project" or any(
        k in t for k in ("görsel", "gorsel", "interior", "image", "visual", "photo", "asset")
    ):
        required.append("image_edit")
    if mode == "general" or any(k in t for k in ("generate from scratch", "ai image", "ideogram", "gpt image")):
        if "image_generate" not in required:
            required.append("image_generate")
    if any(k in t for k in ("video", "reel", "reels", "story video")):
        required.append("video_generate")
    if any(k in t for k in ("architecture", "render", "mimari")):
        required.append("architecture_render")
    if any(k in t for k in ("presentation", "deck", "sunum")):
        required.append("presentation")
    if any(k in t for k in ("brochure", "proposal", "document", "pdf")):
        required.append("document")
    for fmt in formats or []:
        fl = (fmt or "").lower()
        if fl in {"instagram", "social", "story", "feed"} and "image_edit" not in required:
            required.append("image_edit")
        if fl in {"video", "reel"} and "video_generate" not in required:
            required.append("video_generate")
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for cap in required:
        if cap in CAPABILITIES and cap not in seen:
            seen.add(cap)
            out.append(cap)
    return out


def assign_capabilities(
    required: list[str],
    *,
    settings: Settings | None = None,
    prefer_image_provider: str | None = None,
) -> OrchestrationPlan:
    """Map required capabilities → providers. Missing = explicit flag, no silent fallback."""
    providers = list_providers(settings)
    provider_rows = [asdict(p) for p in providers]
    # capability → first available provider (respect prefer_image_provider for image_*)
    by_cap: dict[str, list[ProviderCapability]] = {c: [] for c in CAPABILITIES}
    for p in providers:
        for c in p.capabilities:
            if c in by_cap:
                by_cap[c].append(p)

    assignments: list[CapabilityAssignment] = []
    missing: list[str] = []
    for cap in required:
        candidates = list(by_cap.get(cap) or [])
        if prefer_image_provider and cap in {"image_generate", "image_edit"}:
            preferred = [c for c in candidates if c.provider_id == prefer_image_provider]
            others = [c for c in candidates if c.provider_id != prefer_image_provider]
            candidates = preferred + others
        chosen: ProviderCapability | None = next((c for c in candidates if c.available), None)
        if chosen is None:
            missing.append(cap)
            reason = None
            if candidates:
                reason = candidates[0].reason or f"No available provider for {cap}"
            else:
                reason = f"No provider registered for {cap}"
            assignments.append(
                CapabilityAssignment(
                    capability=cap,
                    required=True,
                    provider_id=candidates[0].provider_id if candidates else None,
                    available=False,
                    missing=True,
                    reason=reason,
                )
            )
        else:
            assignments.append(
                CapabilityAssignment(
                    capability=cap,
                    required=True,
                    provider_id=chosen.provider_id,
                    available=True,
                    missing=False,
                    reason=None,
                )
            )

    return OrchestrationPlan(
        required_capabilities=list(required),
        assignments=assignments,
        providers=provider_rows,
        missing_capabilities=missing,
    )
