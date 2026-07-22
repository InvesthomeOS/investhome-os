"""Provider registry — aggregates all communication provider statuses."""

from __future__ import annotations

from investhome_api.services.crm.providers.email import get_email_provider_status
from investhome_api.services.crm.providers.sms import get_sms_provider_status
from investhome_api.services.crm.providers.whatsapp import get_whatsapp_provider_status


def get_all_provider_statuses() -> list[dict]:
    return [
        *get_email_provider_status(),
        *get_whatsapp_provider_status(),
        *get_sms_provider_status(),
    ]
