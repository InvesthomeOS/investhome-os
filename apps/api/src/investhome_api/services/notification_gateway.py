"""Shared Notification Gateway abstraction (G15A).

Orchestrates channel delivery without replacing the in-app Notification Center.
Providers are registered honestly — not Available until wired.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class ProviderReadiness(str, Enum):
    AVAILABLE = "available"
    CONFIGURED = "configured"
    PLANNED = "planned"
    PARTIAL = "partial"
    NOT_CONNECTED = "not_connected"
    DISABLED = "disabled"


@dataclass
class GatewayMessage:
    channel: NotificationChannel
    recipient: str
    subject: str | None = None
    body: str = ""
    html_body: str | None = None
    locale: str = "tr"
    metadata: dict[str, Any] = field(default_factory=dict)
    require_human_approval: bool = False


@dataclass
class GatewayResult:
    ok: bool
    provider_id: str
    channel: NotificationChannel
    status: str
    detail: str | None = None
    external_id: str | None = None


class NotificationProvider(ABC):
    provider_id: str
    channel: NotificationChannel

    @abstractmethod
    def readiness(self) -> ProviderReadiness: ...

    @abstractmethod
    def send(self, message: GatewayMessage) -> GatewayResult: ...


class InAppNotificationProvider(NotificationProvider):
    """Delegates to existing notification_service — always available when flag on."""

    provider_id = "in_app"
    channel = NotificationChannel.IN_APP

    def readiness(self) -> ProviderReadiness:
        return ProviderReadiness.AVAILABLE

    def send(self, message: GatewayMessage) -> GatewayResult:
        # Actual persistence happens via notification_service callers.
        # Gateway records intent only for channel routing abstraction.
        return GatewayResult(
            ok=True,
            provider_id=self.provider_id,
            channel=self.channel,
            status="queued_in_app",
            detail="Routed to in-app notification center",
        )


class StubSmsProvider(NotificationProvider):
    provider_id = "sms"
    channel = NotificationChannel.SMS

    def readiness(self) -> ProviderReadiness:
        return ProviderReadiness.PLANNED

    def send(self, message: GatewayMessage) -> GatewayResult:
        return GatewayResult(
            ok=False,
            provider_id=self.provider_id,
            channel=self.channel,
            status="planned",
            detail="SMS channel Planned — not production-ready",
        )


class NotificationGateway:
    """Fan-out abstraction across registered providers."""

    def __init__(self) -> None:
        self._providers: dict[str, NotificationProvider] = {}
        from investhome_api.services.smtp_email import SmtpEmailProvider

        self.register(InAppNotificationProvider())
        self.register(SmtpEmailProvider())
        self.register(StubSmsProvider())

    def register(self, provider: NotificationProvider) -> None:
        self._providers[provider.provider_id] = provider

    def list_providers(self) -> list[dict[str, Any]]:
        items = []
        for p in self._providers.values():
            items.append(
                {
                    "provider_id": p.provider_id,
                    "channel": p.channel.value,
                    "status": p.readiness().value,
                    "message": (
                        "Ready"
                        if p.readiness() in {ProviderReadiness.AVAILABLE, ProviderReadiness.CONFIGURED}
                        else "Not available for production dispatch"
                    ),
                }
            )
        return items

    def dispatch(
        self,
        message: GatewayMessage,
        *,
        provider_id: str | None = None,
    ) -> GatewayResult:
        if message.require_human_approval:
            return GatewayResult(
                ok=False,
                provider_id=provider_id or "gateway",
                channel=message.channel,
                status="awaiting_human_approval",
                detail="Binding/payment/publish notifications require human approval — AI cannot auto-approve",
            )

        if provider_id:
            provider = self._providers.get(provider_id)
            if provider is None:
                return GatewayResult(
                    ok=False,
                    provider_id=provider_id,
                    channel=message.channel,
                    status="unknown_provider",
                    detail=f"Unknown provider: {provider_id}",
                )
            return provider.send(message)

        # Prefer in-app when channel matches or unspecified
        for provider in self._providers.values():
            if provider.channel == message.channel:
                return provider.send(message)

        return GatewayResult(
            ok=False,
            provider_id="gateway",
            channel=message.channel,
            status="no_provider",
            detail=f"No provider for channel {message.channel.value}",
        )


_gateway: NotificationGateway | None = None


def get_notification_gateway() -> NotificationGateway:
    global _gateway
    if _gateway is None:
        _gateway = NotificationGateway()
    return _gateway


def reset_notification_gateway_for_tests() -> None:
    global _gateway
    _gateway = None
