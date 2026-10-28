from __future__ import annotations

import re

# WhatsApp Cloud API text-message examples use v25.0. Not a secret.
DEFAULT_GRAPH_API_VERSION = "v25.0"
_GRAPH_VERSION_RE = re.compile(r"^v\d+\.\d+$")


class WhatsAppGraphVersionError(Exception):
    """Raised when WHATSAPP_GRAPH_API_VERSION is not a Graph version token."""

    def __init__(self) -> None:
        super().__init__(
            "WHATSAPP_GRAPH_API_VERSION must match v<major>.<minor>, for example v25.0"
        )


def normalize_graph_api_version(value: str | None) -> str:
    cleaned = (value or "").strip()
    if not _GRAPH_VERSION_RE.fullmatch(cleaned):
        raise WhatsAppGraphVersionError()
    return cleaned
