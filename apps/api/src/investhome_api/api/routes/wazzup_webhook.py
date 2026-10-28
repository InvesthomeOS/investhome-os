"""Public Wazzup inbound webhook. Query token only. No browser session."""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.services.crm.wazzup_inbound_notify import (
    enqueue_wazzup_inbound_email_notifications,
)
from investhome_api.services.crm.wazzup_webhook import (
    WazzupWebhookRejected,
    process_wazzup_webhook,
)

router = APIRouter(tags=["wazzup-webhooks"])
_db_session = Depends(get_db)


def _raise_rejected(exc: WazzupWebhookRejected) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.public_detail) from exc


@router.post("/webhooks/wazzup")
async def wazzup_webhook_inbound(
    request: Request,
    token: str | None = Query(default=None),
    db: Session = _db_session,
) -> dict[str, Any]:
    raw_body = await request.body()
    created_ids: list[UUID] = []
    try:
        result = process_wazzup_webhook(db, raw_body=raw_body, token=token)
        created_ids = list(result.pop("created_ids", []))
        db.commit()
    except WazzupWebhookRejected as exc:
        db.rollback()
        _raise_rejected(exc)
    except Exception:
        db.rollback()
        raise
    enqueue_wazzup_inbound_email_notifications(created_ids)
    return result
