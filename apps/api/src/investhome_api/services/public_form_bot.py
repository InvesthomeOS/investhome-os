"""Server-side bot checks for public forms (Cloudflare Turnstile-ready)."""

from __future__ import annotations

from collections.abc import Callable

import httpx
from fastapi import HTTPException, status

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger

logger = get_logger("investhome.public_form.bot")

DEV_BYPASS_TOKEN = "dev-bypass"
GENERIC_BOT_REJECT = "Unable to submit form."
GENERIC_UNAVAILABLE = "Form temporarily unavailable. Try again later."

TurnstileVerifier = Callable[[str, str, str], bool]

_verifier_override: TurnstileVerifier | None = None


def reset_turnstile_verifier_for_tests(verifier: TurnstileVerifier | None = None) -> None:
    global _verifier_override
    _verifier_override = verifier


def _siteverify_turnstile(secret: str, token: str, ip: str) -> bool:
    settings = get_settings()
    try:
        response = httpx.post(
            settings.turnstile_siteverify_url,
            data={"secret": secret, "response": token, "remoteip": ip},
            timeout=3.0,
        )
        if response.status_code != 200:
            return False
        payload = response.json()
        return bool(payload.get("success") is True)
    except Exception:
        logger.warning("public_form_turnstile_verify_failed")
        return False


def enforce_public_form_bot(*, token: str | None, ip: str) -> None:
    settings = get_settings()
    is_prod = settings.environment.lower() == "production"
    provided = (token or "").strip()
    secret = (settings.turnstile_secret_key or "").strip()
    required = bool(settings.public_form_bot_verify) or bool(is_prod and secret)

    if not is_prod and provided == DEV_BYPASS_TOKEN:
        logger.info("public_form_bot_dev_bypass")
        return

    if not required:
        return

    if not secret:
        logger.warning("public_form_bot_misconfigured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=GENERIC_UNAVAILABLE,
        )

    if not provided or provided == DEV_BYPASS_TOKEN:
        logger.warning("public_form_bot_rejected reason=missing_or_invalid")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GENERIC_BOT_REJECT)

    verifier = _verifier_override or _siteverify_turnstile
    if not verifier(secret, provided, ip):
        logger.warning("public_form_bot_rejected reason=verify_failed")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GENERIC_BOT_REJECT)
