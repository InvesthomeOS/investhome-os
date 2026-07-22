"""Social media provider adapter — honest not-connected implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from investhome_api.services.marketing.providers import MarketingProviderConnectionStatus


class SocialProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> MarketingProviderConnectionStatus:
        ...

    @abstractmethod
    def validate_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def schedule_post(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        ...

    @abstractmethod
    def publish_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_post_status(self, external_post_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_inbox_items(self, account_id: str, since: datetime | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    def sync_account(self, account_id: str) -> dict[str, Any]:
        ...


class StubSocialProviderAdapter(SocialProviderAdapter):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def get_status(self) -> MarketingProviderConnectionStatus:
        return MarketingProviderConnectionStatus.NOT_CONNECTED

    def validate_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"valid": True, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value, "warnings": []}

    def schedule_post(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        return {"scheduled": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def publish_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"published": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def get_post_status(self, external_post_id: str) -> dict[str, Any]:
        return {"status": MarketingProviderConnectionStatus.UNAVAILABLE.value}

    def get_inbox_items(self, account_id: str, since: datetime | None = None) -> dict[str, Any]:
        return {"items": [], "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}

    def sync_account(self, account_id: str) -> dict[str, Any]:
        return {"synced": False, "status": MarketingProviderConnectionStatus.NOT_CONNECTED.value}


SOCIAL_PROVIDERS: dict[str, SocialProviderAdapter] = {
    "linkedin": StubSocialProviderAdapter("linkedin"),
    "instagram": StubSocialProviderAdapter("instagram"),
    "facebook": StubSocialProviderAdapter("facebook"),
    "x": StubSocialProviderAdapter("x"),
}


def get_social_provider(network: str) -> SocialProviderAdapter:
    return SOCIAL_PROVIDERS.get(network, StubSocialProviderAdapter(network))
