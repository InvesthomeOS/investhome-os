"""Email provider abstraction — architecture only, no live integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from investhome_api.services.crm.providers.base import ProviderConnectionStatus


class EmailProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> ProviderConnectionStatus:
        ...

    @abstractmethod
    def connect_email_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def sync_email_threads(self, since: datetime | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def schedule_email(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_email_tracking(self, external_id: str) -> dict[str, Any]:
        ...


class StubEmailProviderAdapter(EmailProviderAdapter):
    """Stub adapter — provider not connected."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def get_status(self) -> ProviderConnectionStatus:
        return ProviderConnectionStatus.NOT_CONNECTED

    def connect_email_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "message": "Provider integration not configured"}

    def sync_email_threads(self, since: datetime | None = None) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "synced": 0}

    def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "sent": False}

    def schedule_email(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "scheduled": False}

    def get_email_tracking(self, external_id: str) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.UNAVAILABLE.value, "tracking": None}


EMAIL_PROVIDERS: dict[str, EmailProviderAdapter] = {
    "gmail": StubEmailProviderAdapter("gmail"),
    "m365": StubEmailProviderAdapter("m365"),
    "smtp": StubEmailProviderAdapter("smtp"),
    "sendgrid": StubEmailProviderAdapter("sendgrid"),
    "postmark": StubEmailProviderAdapter("postmark"),
}


def get_email_provider_status() -> list[dict[str, Any]]:
    return [
        {
            "provider": name,
            "channel": "email",
            "status": adapter.get_status().value,
            "message": "Provider integration not configured",
            "last_sync_at": None,
        }
        for name, adapter in EMAIL_PROVIDERS.items()
    ]


def connect_email_account(provider: str, credentials: dict[str, Any]) -> dict[str, Any]:
    adapter = EMAIL_PROVIDERS.get(provider)
    if adapter is None:
        return {"status": ProviderConnectionStatus.UNAVAILABLE.value, "message": f"Unknown provider: {provider}"}
    return adapter.connect_email_account(credentials)


def send_email_via_provider(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    adapter = EMAIL_PROVIDERS.get(provider)
    if adapter is None:
        return {"status": ProviderConnectionStatus.UNAVAILABLE.value, "sent": False}
    return adapter.send_email(payload)
