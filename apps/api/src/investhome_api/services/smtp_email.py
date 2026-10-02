"""Generic SMTP email provider for the notification gateway.

Does not hard-code a vendor. Never logs SMTP passwords, invite tokens, or message bodies.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger
from investhome_api.services.notification_gateway import (
    GatewayMessage,
    GatewayResult,
    NotificationChannel,
    NotificationProvider,
    ProviderReadiness,
)

logger = get_logger("investhome.email.smtp")

PROVIDER_ID = "email_smtp"


def smtp_is_configured() -> bool:
    settings = get_settings()
    host = (settings.smtp_host or "").strip()
    from_email = (settings.smtp_from_email or "").strip()
    if not host or not from_email:
        return False
    _, addr = parseaddr(from_email)
    return "@" in addr


class SmtpEmailProvider(NotificationProvider):
    provider_id = PROVIDER_ID
    channel = NotificationChannel.EMAIL

    def readiness(self) -> ProviderReadiness:
        if smtp_is_configured():
            return ProviderReadiness.CONFIGURED
        return ProviderReadiness.NOT_CONNECTED

    def send(self, message: GatewayMessage) -> GatewayResult:
        if not smtp_is_configured():
            return GatewayResult(
                ok=False,
                provider_id=self.provider_id,
                channel=self.channel,
                status="not_connected",
                detail="SMTP is not configured",
            )
        settings = get_settings()
        try:
            payload = _build_mime_message(message, settings)
            _deliver(payload, settings)
        except Exception as exc:
            logger.warning("smtp_send_failed error_type=%s", type(exc).__name__)
            return GatewayResult(
                ok=False,
                provider_id=self.provider_id,
                channel=self.channel,
                status="failed",
                detail="SMTP send failed",
            )
        logger.info("smtp_send_ok")
        return GatewayResult(
            ok=True,
            provider_id=self.provider_id,
            channel=self.channel,
            status="sent",
        )


def _build_mime_message(message: GatewayMessage, settings) -> MIMEMultipart:
    from_email = (settings.smtp_from_email or "").strip()
    from_name = (settings.smtp_from_name or "InvestHome OS").strip()
    payload = MIMEMultipart("alternative")
    payload["From"] = formataddr((from_name, from_email))
    payload["To"] = message.recipient
    payload["Subject"] = message.subject or from_name
    payload.attach(MIMEText(message.body or "", "plain", "utf-8"))
    html_body = getattr(message, "html_body", None)
    if html_body:
        payload.attach(MIMEText(html_body, "html", "utf-8"))
    return payload


def _smtp_client(settings):
    host = (settings.smtp_host or "").strip()
    port = int(settings.smtp_port)
    timeout = 10
    if port == 465:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    client = smtplib.SMTP(host, port, timeout=timeout)
    if settings.smtp_use_tls:
        client.starttls()
    return client


def _deliver(payload: MIMEMultipart, settings) -> None:
    username = (settings.smtp_username or "").strip()
    password = settings.smtp_password or ""
    client = _smtp_client(settings)
    try:
        if username:
            client.login(username, password)
        refused = client.send_message(payload)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    finally:
        try:
            client.quit()
        except Exception:
            try:
                client.close()
            except Exception:
                pass
