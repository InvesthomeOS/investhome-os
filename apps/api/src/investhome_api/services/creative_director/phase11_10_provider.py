"""Phase 11.10 provider capability audit — already-integrated Images API only."""

from __future__ import annotations

from typing import Any

from investhome_api.services.gpt_image_design.client import edit_image, generate_image
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    EDITS_ENDPOINT_PATH,
    GENERATIONS_ENDPOINT_PATH,
    is_gpt_image_2,
    provider_availability,
)


def provider_capability_audit() -> dict[str, Any]:
    avail = provider_availability()
    model = avail.model or DEFAULT_MODEL
    gpt2 = is_gpt_image_2(model)
    return {
        "schema": "Phase1110ProviderCapabilityAudit",
        "selected_provider": "gpt-image",
        "selected_model": model,
        "available": avail.available,
        "quality": avail.quality,
        "reason": (
            "Strongest already-integrated Images API. Supports POST /v1/images/edits with "
            "source image(s) and an optional PNG mask. No new external dependency."
        ),
        "generations": {
            "endpoint": GENERATIONS_ENDPOINT_PATH,
            "suitable_for_this_proof": False,
            "why": "Text-to-image would invent Temple architecture.",
        },
        "edits": {
            "endpoint": EDITS_ENDPOINT_PATH,
            "function": "edit_image",
            "suitable_for_this_proof": True,
            "multi_image": True,
            "mask": {
                "supported": True,
                "semantics": "transparent = edit, opaque = preserve",
                "used_as_primary_source_preservation": True,
            },
            "input_fidelity_high": (not gpt2),
            "input_fidelity_note": (
                "input_fidelity=high is sent only for pre-gpt-image-2 models. "
                f"Current model is {model}; preservation is mask + prompt, not input_fidelity."
            ),
            "size_4x5": "1088x1360",
        },
        "ideogram": {"selected": False, "role": "POC social — not used"},
        "not_faked": (
            "No regional API beyond the official mask. No ControlNet. No new SDK. "
            "No claim of pixel-lock beyond what /images/edits + mask actually does."
        ),
        "source_preservation_method": (
            "gpt-image-2 /v1/images/edits with IMAGE 1 = real Temple photograph, "
            "IMAGE 2 = real Temple logo, MASK = architecture-preserve (opaque building / transparent field)."
        ),
        "generate_image_symbol": generate_image.__name__,
        "edit_image_symbol": edit_image.__name__,
        "status": "READY" if avail.available else "UNAVAILABLE",
        "reason_unavailable": avail.reason,
    }


def provider_audit_markdown(audit: dict[str, Any] | None = None) -> str:
    a = audit or provider_capability_audit()
    edits = dict(a.get("edits") or {})
    mask = dict(edits.get("mask") or {})
    return "\n".join(
        [
            "# Phase 11.10 — Provider capability audit",
            "",
            "Feasibility proof only. Not a production architecture change.",
            "",
            f"**Selected provider:** {a.get('selected_provider')}",
            f"**Selected model:** {a.get('selected_model')}",
            f"**Available:** {a.get('available')}",
            f"**Quality setting:** {a.get('quality')}",
            "",
            "## Why this provider",
            str(a.get("reason") or ""),
            "",
            "## Generations (`/v1/images/generations`)",
            "Not used for this proof. Text-to-image would invent Temple architecture.",
            "",
            "## Edits (`/v1/images/edits`) — selected",
            f"- Multi-image: {edits.get('multi_image')}",
            f"- Mask supported: {mask.get('supported')}",
            f"- Mask semantics: {mask.get('semantics')}",
            f"- Mask used as primary preservation: {mask.get('used_as_primary_source_preservation')}",
            f"- 4:5 size: {edits.get('size_4x5')}",
            f"- input_fidelity=high: {edits.get('input_fidelity_high')}",
            str(edits.get("input_fidelity_note") or ""),
            "",
            "## Source preservation method actually used",
            str(a.get("source_preservation_method") or ""),
            "",
            "## What is not faked",
            str(a.get("not_faked") or ""),
            "",
            "## Not selected",
            "- Ideogram: POC social route",
            "- New external image APIs",
            "",
        ]
    )
