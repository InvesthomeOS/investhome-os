"""WhatsApp marketing provider adapter — honest not-connected implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from investhome_api.services.marketing.providers import MarketingProviderConnectionStatus


class WhatsAppMarketingProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> MarketingProviderConnectionStatus:
        ...

    @abstractmethod
    def get_templates(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def submit_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_test(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def schedule_campaign(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_conversations(self, since: datetime | None = None) -> dict[str, Any]:
        ...


class StubWhatsAppMarketingProviderAdapter(WhatsAppMarketingProviderAdapter):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def get_status(self) -> MarketingProviderConnectionStatus:
        return MarketingProviderConnectionStatus.NOT_CONNECTED

    def get_templates(self) -> dict[str, Any]:
        return {"templates": [], "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def submit_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"submitted": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def send_test(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"sent": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def schedule_campaign(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        return {"scheduled": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def get_conversations(self, since: datetime | None = None) -> dict[str, Any]:
        return {"conversations": [], "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}


WHATSAPP_MARKETING_PROVIDERS: dict[str, WhatsAppMarketingProviderAdapter] = {
    "meta": StubWhatsAppMarketingProviderAdapter("meta"),
    "twilio": StubWhatsAppMarketingProviderAdapter("twilio"),
}


def get_whatsapp_marketing_provider(provider: str = "meta") -> WhatsAppMarketingProviderAdapter:
    return WHATSAPP_MARKETING_PROVIDERS.get(provider, StubWhatsAppMarketingProviderAdapter(provider))
