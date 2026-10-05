"""Public WordPress website form receiver — HMAC S2S, no CRM read, no Bitrix."""

from __future__ import annotations

import json
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from investhome_api.core.logging_config import get_logger
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.schemas.website_forms import (
    WEBSITE_FORM_MAX_BODY_BYTES,
    WEBSITE_FORM_RATE_SLUG,
    WebsiteFormSubmit,
    WebsiteFormSubmitResponse,
)
from investhome_api.services.crm.website_form_ingest import (
    WebsiteFormIngestError,
    ingest_website_form,
    website_form_result_from_payload,
    website_form_result_payload,
)
from investhome_api.services.login_rate_limit import resolve_client_ip
from investhome_api.services.public_form_rate_limit import enforce_public_form_rate_limit
from investhome_api.services.website_form_auth import (
    NONCE_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    WebsiteFormAuthError,
    authenticate_website_form_request,
    idempotency_claim,
    idempotency_clear,
    idempotency_lookup,
    idempotency_store,
)

router = APIRouter(prefix="/public/website/forms", tags=["website-public"])
_log = get_logger("investhome.website_form")


def _raise_auth(exc: WebsiteFormAuthError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.public_detail) from exc


def _reject_oversized(raw_body: bytes, content_length: str | None) -> None:
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=413, detail="Payload too large") from exc
        if declared > WEBSITE_FORM_MAX_BODY_BYTES:
            _log.warning("website_form_payload_too_large")
            raise HTTPException(status_code=413, detail="Payload too large")
    if len(raw_body) > WEBSITE_FORM_MAX_BODY_BYTES:
        _log.warning("website_form_payload_too_large")
        raise HTTPException(status_code=413, detail="Payload too large")


@router.post("/submit", response_model=WebsiteFormSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_website_form(
    request: Request,
    db: Session = Depends(get_db),
) -> WebsiteFormSubmitResponse:
    raw_body = await request.body()
    _reject_oversized(raw_body, request.headers.get("content-length"))
    ip = resolve_client_ip(request)
    enforce_public_form_rate_limit(ip=ip, form_slug=WEBSITE_FORM_RATE_SLUG)
    try:
        authenticate_website_form_request(
            raw_body=raw_body,
            timestamp_header=request.headers.get(TIMESTAMP_HEADER),
            nonce_header=request.headers.get(NONCE_HEADER),
            signature_header=request.headers.get(SIGNATURE_HEADER),
        )
    except WebsiteFormAuthError as exc:
        if exc.status_code == 403:
            try:
                from investhome_api.services.security_monitoring import (
                    SecurityEventKind,
                    observe_security_event,
                )

                observe_security_event(
                    SecurityEventKind.WEBHOOK_SIGNATURE_FAILURE,
                    ip=ip,
                )
            except Exception:
                pass
        _raise_auth(exc)

    try:
        payload = WebsiteFormSubmit.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=json.loads(exc.json()),
        ) from exc

    request_id = get_request_id()
    cached = idempotency_lookup(payload.idempotency_key)
    if cached is not None:
        replay = website_form_result_from_payload(cached)
        replay.request_id = request_id
        return replay

    if not idempotency_claim(payload.idempotency_key):
        cached = idempotency_lookup(payload.idempotency_key)
        if cached is not None:
            replay = website_form_result_from_payload(cached)
            replay.request_id = request_id
            return replay
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate request")

    try:
        result = ingest_website_form(db, payload, request_id=request_id)
        stored = website_form_result_payload(result)
        idempotency_store(payload.idempotency_key, stored)
        db.commit()
    except WebsiteFormIngestError as exc:
        db.rollback()
        idempotency_clear(payload.idempotency_key)
        raise HTTPException(status_code=exc.status_code, detail=exc.public_detail) from exc
    except Exception:
        db.rollback()
        idempotency_clear(payload.idempotency_key)
        raise
    return result
