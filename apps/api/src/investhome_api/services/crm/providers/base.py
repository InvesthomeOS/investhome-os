"""Provider connection status constants."""

from __future__ import annotations

from enum import Enum


class ProviderConnectionStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PENDING_SYNC = "pending_sync"
    NOT_CONNECTED = "not_connected"
