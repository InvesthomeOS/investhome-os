"""Marketing channel provider base types."""

from __future__ import annotations

import enum


class MarketingProviderConnectionStatus(str, enum.Enum):
    CONNECTED = "connected"
    NOT_CONNECTED = "not_connected"
    AUTHENTICATION_REQUIRED = "authentication_required"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
