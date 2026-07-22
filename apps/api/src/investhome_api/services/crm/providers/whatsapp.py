"""WhatsApp provider abstraction — architecture only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from investhome_api.services.crm.providers.base import ProviderConnectionStatus


class WhatsAppProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> ProviderConnectionStatus:
        ...

    @abstractmethod
    def connect_whatsapp_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def sync_whatsapp_messages(self, since: datetime | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_whatsapp_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_whatsapp_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_whatsapp_delivery_status(self, external_id: str) -> dict[str, Any]:
        ...


class StubWhatsAppProviderAdapter(WhatsAppProviderAdapter):
    def __init__(self, provider_name: str = "whatsapp_business") -> None:
        self.provider_name = provider_name

    def get_status(self) -> ProviderConnectionStatus:
        return ProviderConnectionStatus.NOT_CONNECTED

    def connect_whatsapp_account(self, credentials: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value}

    def sync_whatsapp_messages(self, since: datetime | None = None) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "synced": 0}

    def send_whatsapp_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "sent": False}

    def send_whatsapp_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "sent": False}

    def get_whatsapp_delivery_status(self, external_id: str) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.UNAVAILABLE.value, "delivery": None}


WHATSAPP_PROVIDER = StubWhatsAppProviderAdapter()


def get_whatsapp_provider_status() -> list[dict[str, Any]]:
    return [
        {
            "provider": WHATSAPP_PROVIDER.provider_name,
            "channel": "whatsapp",
            "status": WHATSAPP_PROVIDER.get_status().value,
            "message": "WhatsApp Business API not configured",
            "last_sync_at": None,
        }
    ]
