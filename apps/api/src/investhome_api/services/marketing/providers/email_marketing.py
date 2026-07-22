"""Email marketing provider adapter — honest not-connected implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from investhome_api.services.marketing.providers import MarketingProviderConnectionStatus


class EmailMarketingProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> MarketingProviderConnectionStatus:
        ...

    @abstractmethod
    def validate_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_test_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def schedule_campaign(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_events(self, campaign_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_suppression(self) -> dict[str, Any]:
        ...


class StubEmailMarketingProviderAdapter(EmailMarketingProviderAdapter):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def get_status(self) -> MarketingProviderConnectionStatus:
        return MarketingProviderConnectionStatus.NOT_CONNECTED

    def validate_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"valid": True, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def send_test_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"sent": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def schedule_campaign(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        return {"scheduled": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def get_events(self, campaign_id: str) -> dict[str, Any]:
        return {"events": [], "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def get_suppression(self) -> dict[str, Any]:
        return {"suppressed": [], "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}


EMAIL_MARKETING_PROVIDERS: dict[str, EmailMarketingProviderAdapter] = {
    "sendgrid": StubEmailMarketingProviderAdapter("sendgrid"),
    "postmark": StubEmailMarketingProviderAdapter("postmark"),
    "smtp": StubEmailMarketingProviderAdapter("smtp"),
}


def get_email_marketing_provider(provider: str = "sendgrid") -> EmailMarketingProviderAdapter:
    return EMAIL_MARKETING_PROVIDERS.get(provider, StubEmailMarketingProviderAdapter(provider))
