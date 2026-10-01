"""Public Meta WhatsApp webhook — signature + handshake only. No session auth."""

from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.services.crm.whatsapp_webhook import (
    SIGNATURE_HEADER,
    WhatsAppWebhookRejected,
    handle_verification_challenge,
    process_whatsapp_webhook,
)

router = APIRouter(tags=["whatsapp-webhooks"])


def _raise_rejected(exc: WhatsAppWebhookRejected) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.public_detail) from exc


@router.get("/webhooks/whatsapp")
def whatsapp_webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    try:
        challenge = handle_verification_challenge(
            hub_mode=hub_mode,
            hub_verify_token=hub_verify_token,
            hub_challenge=hub_challenge,
        )
    except WhatsAppWebhookRejected as exc:
        _raise_rejected(exc)
    return PlainTextResponse(content=challenge, status_code=status.HTTP_200_OK)


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook_inbound(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    raw_body = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER)
    try:
        result = process_whatsapp_webhook(db, raw_body=raw_body, signature_header=signature)
        db.commit()
    except WhatsAppWebhookRejected as exc:
        db.rollback()
        if exc.status_code == 403:
            try:
                from investhome_api.services.login_rate_limit import resolve_client_ip
                from investhome_api.services.security_monitoring import (
                    SecurityEventKind,
                    observe_security_event,
                )

                observe_security_event(
                    SecurityEventKind.WEBHOOK_SIGNATURE_FAILURE,
                    ip=resolve_client_ip(request),
                )
            except Exception:
                pass
        _raise_rejected(exc)
    except Exception:
        db.rollback()
        raise
    return result
