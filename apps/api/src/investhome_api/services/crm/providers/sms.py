"""SMS provider abstraction — architecture only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from investhome_api.services.crm.providers.base import ProviderConnectionStatus


class SmsProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def get_status(self) -> ProviderConnectionStatus:
        ...

    @abstractmethod
    def connect_sms_provider(self, credentials: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def send_sms(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def schedule_sms(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_sms_delivery_status(self, external_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def sync_sms_messages(self, since: datetime | None = None) -> dict[str, Any]:
        ...


class StubSmsProviderAdapter(SmsProviderAdapter):
    def __init__(self, provider_name: str = "twilio") -> None:
        self.provider_name = provider_name

    def get_status(self) -> ProviderConnectionStatus:
        return ProviderConnectionStatus.NOT_CONNECTED

    def connect_sms_provider(self, credentials: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value}

    def send_sms(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "sent": False}

    def schedule_sms(self, payload: dict[str, Any], scheduled_at: datetime) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "scheduled": False}

    def get_sms_delivery_status(self, external_id: str) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.UNAVAILABLE.value, "delivery": None}

    def sync_sms_messages(self, since: datetime | None = None) -> dict[str, Any]:
        return {"status": ProviderConnectionStatus.NOT_CONNECTED.value, "synced": 0}


SMS_PROVIDER = StubSmsProviderAdapter()


def get_sms_provider_status() -> list[dict[str, Any]]:
    return [
        {
            "provider": SMS_PROVIDER.provider_name,
            "channel": "sms",
            "status": SMS_PROVIDER.get_status().value,
            "message": "SMS provider not configured",
            "last_sync_at": None,
        }
    ]
