"""Meta WhatsApp Cloud API text send.

The access token is sent only as an Authorization header. It is never logged
and never placed in the request URL.
"""

from __future__ import annotations

import httpx

from investhome_api.core.logging_config import get_logger
from investhome_api.services.crm.whatsapp_graph_version import (
    WhatsAppGraphVersionError,
    normalize_graph_api_version,
)

logger = get_logger("investhome.whatsapp.cloud")

GRAPH_TIMEOUT_SECONDS = 15.0
# Meta re-engagement codes: free-form text is outside the customer-care window.
_TEMPLATE_WINDOW_CODES = frozenset({"131047", "470"})


class WhatsAppCloudError(Exception):
    def __init__(
        self,
        *,
        http_status: int,
        provider_code: str | None,
        provider_message: str | None,
        template_required: bool,
    ) -> None:
        super().__init__(provider_code or "whatsapp_send_failed")
        self.http_status = http_status
        self.provider_code = provider_code
        self.provider_message = provider_message
        self.template_required = template_required


def _redact(text: str, secret: str) -> str:
    cleaned = " ".join(text.split())
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    lowered = cleaned.lower()
    if "bearer " in lowered:
        cleaned = "bearer [redacted]"
    return cleaned[:240]


def _template_required(code: str | None, message: str | None) -> bool:
    if code in _TEMPLATE_WINDOW_CODES:
        return True
    blob = (message or "").casefold()
    return "re-engagement" in blob or "24 hours have passed" in blob


def _error_parts(payload: object, token: str) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None, None
    raw_code = error.get("code")
    code = str(raw_code).strip() if raw_code is not None else ""
    message = str(error.get("message") or "")
    details = ""
    data = error.get("error_data")
    if isinstance(data, dict):
        details = str(data.get("details") or "")
    combined = _redact(f"{message} {details}".strip(), token)
    return (code or None), (combined or None)


class WhatsAppCloudClient:
    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        graph_api_version: str,
    ) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        try:
            self._graph_api_version = normalize_graph_api_version(graph_api_version)
        except WhatsAppGraphVersionError:
            logger.warning("whatsapp_graph_version_invalid")
            raise

    def send_text(self, *, to: str, body: str) -> str:
        version = self._graph_api_version
        url = f"https://graph.facebook.com/{version}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=GRAPH_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("whatsapp_send_transport_failed error_type=%s", type(exc).__name__)
            raise WhatsAppCloudError(
                http_status=0,
                provider_code=None,
                provider_message=None,
                template_required=False,
            ) from None
        try:
            parsed = response.json()
        except ValueError:
            parsed = None
        if response.status_code >= 400:
            code, message = _error_parts(parsed, self._access_token)
            logger.warning(
                "whatsapp_send_rejected http_status=%s provider_code=%s",
                response.status_code,
                code or "",
            )
            raise WhatsAppCloudError(
                http_status=response.status_code,
                provider_code=code,
                provider_message=message,
                template_required=_template_required(code, message),
            )
        wamid = ""
        if isinstance(parsed, dict):
            messages = parsed.get("messages")
            if isinstance(messages, list) and messages and isinstance(messages[0], dict):
                wamid = str(messages[0].get("id") or "").strip()
        if not wamid:
            logger.warning("whatsapp_send_missing_wamid http_status=%s", response.status_code)
            raise WhatsAppCloudError(
                http_status=response.status_code,
                provider_code="missing_wamid",
                provider_message=None,
                template_required=False,
            )
        logger.info(
            "whatsapp_send_accepted wamid=%s phone_number_id=%s",
            wamid,
            self._phone_number_id,
        )
        return wamid
