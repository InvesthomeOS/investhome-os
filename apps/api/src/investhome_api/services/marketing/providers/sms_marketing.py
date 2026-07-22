"""SMS marketing provider adapter — honest not-connected implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from investhome_api.services.marketing.providers import MarketingProviderConnectionStatus


class SmsMarketingProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> MarketingProviderConnectionStatus:
        ...

    @abstractmethod
    def validate_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_test_sms(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def schedule_campaign(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_events(self, campaign_id: str) -> dict[str, Any]:
        ...


class StubSmsMarketingProviderAdapter(SmsMarketingProviderAdapter):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def get_status(self) -> MarketingProviderConnectionStatus:
        return MarketingProviderConnectionStatus.NOT_CONNECTED

    def validate_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"valid": True, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def send_test_sms(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"sent": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def schedule_campaign(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        return {"scheduled": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def get_events(self, campaign_id: str) -> dict[str, Any]:
        return {"events": [], "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}


SMS_MARKETING_PROVIDERS: dict[str, SmsMarketingProviderAdapter] = {
    "twilio": StubSmsMarketingProviderAdapter("twilio"),
}


def get_sms_marketing_provider(provider: str = "twilio") -> SmsMarketingProviderAdapter:
    return SMS_MARKETING_PROVIDERS.get(provider, StubSmsMarketingProviderAdapter(provider))
