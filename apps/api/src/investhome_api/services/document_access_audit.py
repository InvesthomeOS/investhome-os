"""Security audit events for document download and preview access.

Does not log file bytes, storage keys, tokens, passwords, or document contents.
Audit persistence failures are swallowed after an internal log — they must not
change download/preview responses or leak document data.
"""

from __future__ import annotations

import logging
from typing import Literal, NoReturn

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.document import Document
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity

logger = logging.getLogger(__name__)

AccessType = Literal["download", "preview"]
AccessOutcome = Literal["allowed", "denied"]

_ALLOWED_DOWNLOAD_KEY = "activity.document.downloaded"
_ALLOWED_PREVIEW_KEY = "activity.document.previewed"
_DENIED_KEY = "activity.document.access_denied"


def _confidentiality_value(document: Document) -> str:
    level = getattr(document, "confidentiality_level", None)
    if level is None:
        return "unknown"
    return level.value if hasattr(level, "value") else str(level)


def record_document_access(
    db: Session,
    *,
    document: Document,
    access_type: AccessType,
    actor: User | None,
    request: Request | None,
    module: str,
    outcome: AccessOutcome = "allowed",
    reason: str | None = None,
    persist: bool = False,
) -> None:
    """Record a document access (or security-relevant denial) audit event."""
    if outcome == "denied":
        action = ActivityAction.OTHER
        description_key = _DENIED_KEY
    elif access_type == "preview":
        action = ActivityAction.VIEWED
        description_key = _ALLOWED_PREVIEW_KEY
    else:
        action = ActivityAction.EXPORTED
        description_key = _ALLOWED_DOWNLOAD_KEY

    metadata: dict[str, str] = {
        "access_type": access_type,
        "document_id": str(document.id),
        "confidentiality_level": _confidentiality_value(document),
        "module": module,
        "outcome": outcome,
    }
    if outcome == "denied" and reason:
        metadata["reason"] = reason

    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.DOCUMENT,
        entity_id=document.id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        request_context=activity_context_from_request(request),
        is_demo=bool(getattr(document, "is_demo", False)),
        commit=persist,
    )


def record_document_access_denied(
    db: Session,
    *,
    document: Document,
    access_type: AccessType,
    actor: User | None,
    request: Request | None,
    module: str,
    reason: str = "forbidden",
) -> None:
    """Persist a denial independently so HTTP 403 rollback/close cannot drop it."""
    try:
        record_document_access(
            db,
            document=document,
            access_type=access_type,
            actor=actor,
            request=request,
            module=module,
            outcome="denied",
            reason=reason,
            persist=True,
        )
        from investhome_api.services.login_rate_limit import resolve_client_ip
        from investhome_api.services.security_monitoring import SecurityEventKind, observe_security_event

        observe_security_event(
            SecurityEventKind.DOCUMENT_ACCESS_DENIED,
            ip=resolve_client_ip(request) if request is not None else None,
            identity=str(actor.id) if actor is not None else None,
            metadata={"reason": reason, "access_type": access_type},
        )
    except Exception:
        logger.exception(
            "Failed to persist document access denial document_id=%s access_type=%s",
            document.id,
            access_type,
        )


def deny_document_access(
    db: Session,
    *,
    document: Document,
    access_type: AccessType,
    actor: User | None,
    request: Request | None,
    module: str,
    status_code: int,
    detail: str,
    reason: str = "forbidden",
) -> NoReturn:
    """Record a denial then raise HTTPException. Never includes document bytes."""
    record_document_access_denied(
        db,
        document=document,
        access_type=access_type,
        actor=actor,
        request=request,
        module=module,
        reason=reason,
    )
    raise HTTPException(status_code=status_code, detail=detail)
