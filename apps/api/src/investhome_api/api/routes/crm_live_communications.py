"""Live communication foundation APIs — accounts, ingest, unmatched queue."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.config.settings import get_settings
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.crm_communication import (
    CrmCommunication,
    CrmCommunicationMatchStatus,
    CrmUserCommunicationAccount,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_live_communications import (
    CommunicationAccountCreate,
    CommunicationAccountListResponse,
    CommunicationAccountOut,
    CommunicationConversationResponse,
    CommunicationFeedResponse,
    ConfirmMatchRequest,
    GmailAuthorizeResponse,
    GmailStatusResponse,
    GmailSyncResponse,
    LiveIngestRequest,
    LiveIngestResponse,
    UnmatchedCommunicationOut,
    UnmatchedListResponse,
)
from investhome_api.services.crm.communication_feed import list_communication_feed, list_whatsapp_conversation
from investhome_api.services.crm.gmail_oauth import (
    complete_authorization,
    connected_gmail_accounts,
    gmail_oauth_configured,
    gmail_redirect_uri,
    start_authorization,
)
from investhome_api.services.crm.gmail_sync import enqueue_gmail_sync, sync_gmail_account
from investhome_api.services.crm.live_accounts import (
    disconnect_account,
    list_accounts,
    register_account,
    serialize_account,
    upgrade_legacy_credentials,
)
from investhome_api.services.crm.live_ingest import confirm_match, ignore_unmatched, ingest_live_message
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(tags=["crm-live-communications"])

_GMAIL_FRONTEND_PATH = "/workspaces/crm/settings/communication-accounts"
_SAFE_OAUTH_ERRORS = frozenset(
    {
        "access_denied",
        "invalid_request",
        "unauthorized_client",
        "unsupported_response_type",
        "invalid_scope",
        "server_error",
        "temporarily_unavailable",
        "invalid_callback",
        "missing_state",
        "missing_code",
        "invalid_state",
        "token_exchange_failed",
        "gmail_not_configured",
        "gmail_pilot_limit",
        "oauth_error",
        "needs_reauth",
    }
)
_SAFE_ERROR_RE = re.compile(r"^[a-z0-9_]{1,64}$")


def _require_view():
    return require_permission("crm", "view_communications")


def _can_manage_accounts(user: User) -> bool:
    return user_has_permission(user, "crm", "manage_provider_connections") or user_has_permission(
        user, "crm", "manage_settings"
    )


def _require_view_accounts(user: User = Depends(require_permission("crm", "read"))) -> User:
    if _can_manage_accounts(user) or user_has_permission(user, "crm", "view_communications"):
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _require_manage_accounts(user: User = Depends(require_permission("crm", "read"))) -> User:
    if _can_manage_accounts(user):
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/crm/settings/communication-accounts", response_model=CommunicationAccountListResponse)
def get_communication_accounts(
    user_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_accounts),
) -> CommunicationAccountListResponse:
    upgraded = upgrade_legacy_credentials(db)
    if upgraded:
        db.commit()
    accounts = list_accounts(db, user, user_id=user_id)
    owner_ids = {item.user_id for item in accounts}
    names: dict[UUID, str] = {}
    if owner_ids:
        owners = list(db.scalars(select(User).where(User.id.in_(owner_ids))).all())
        names = {item.id: item.full_name for item in owners}
    return CommunicationAccountListResponse(
        items=[
            CommunicationAccountOut(**serialize_account(item, owner_name=names.get(item.user_id)))
            for item in accounts
        ],
        request_id=get_request_id() or "",
    )


@router.post(
    "/crm/settings/communication-accounts",
    response_model=CommunicationAccountOut,
    status_code=status.HTTP_201_CREATED,
)
def create_communication_account(
    payload: CommunicationAccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_accounts),
) -> CommunicationAccountOut:
    try:
        account = register_account(
            db,
            actor=user,
            user_id=payload.user_id or user.id,
            channel_type=payload.channel_type,
            provider=payload.provider,
            identity=payload.identity,
            account_label=payload.account_label,
            credentials=payload.credentials,
        )
        db.commit()
        db.refresh(account)
    except ValueError as exc:
        code = str(exc)
        status_code = status.HTTP_409_CONFLICT if code == "identity_taken" else status.HTTP_400_BAD_REQUEST
        if code == "forbidden":
            status_code = status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=code) from exc
    owner = db.get(User, account.user_id)
    return CommunicationAccountOut(**serialize_account(account, owner_name=owner.full_name if owner else None))


@router.post("/crm/settings/communication-accounts/{account_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_communication_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_accounts),
) -> None:
    try:
        disconnect_account(db, account_id, actor=user)
        db.commit()
    except ValueError as exc:
        code = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if code == "not_found" else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.get("/crm/live-communications/feed", response_model=CommunicationFeedResponse)
def get_communication_feed(
    search: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    contact_id: UUID | None = Query(default=None),
    person: str | None = Query(default=None),
    project_group: str | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    direction: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view()),
) -> CommunicationFeedResponse:
    _ = user
    parsed_from = None
    parsed_to = None
    if date_from:
        parsed_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
    if date_to:
        parsed_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
    body = list_communication_feed(
        db,
        search=search,
        channel=channel,
        contact_id=contact_id,
        person=person,
        project_group=project_group,
        owner_id=owner_id,
        direction=direction,
        date_from=parsed_from,
        date_to=parsed_to,
        page=page,
        page_size=page_size,
    )
    body.request_id = get_request_id() or ""
    return body


@router.get("/crm/live-communications/conversation", response_model=CommunicationConversationResponse)
def get_whatsapp_conversation(
    activity_id: UUID | None = Query(default=None),
    contact_id: UUID | None = Query(default=None),
    chat_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view()),
) -> CommunicationConversationResponse:
    _ = user
    body = list_whatsapp_conversation(db, activity_id=activity_id, contact_id=contact_id, chat_id=chat_id)
    body.request_id = get_request_id() or ""
    return body


@router.get("/crm/live-communications/unmatched", response_model=UnmatchedListResponse)
def list_unmatched_communications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view()),
) -> UnmatchedListResponse:
    filters = (
        CrmCommunication.match_status.in_(
            [CrmCommunicationMatchStatus.UNMATCHED.value, CrmCommunicationMatchStatus.AMBIGUOUS.value]
        ),
        CrmCommunication.archived_at.is_(None),
    )
    total = db.scalar(select(func.count()).select_from(CrmCommunication).where(*filters)) or 0
    rows = list(
        db.scalars(
            select(CrmCommunication)
            .where(*filters)
            .order_by(CrmCommunication.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return UnmatchedListResponse(
        items=[
            UnmatchedCommunicationOut(
                id=row.id,
                channel=row.channel,
                direction=row.direction,
                source=row.source,
                sender=row.sender_identity,
                subject=row.subject,
                preview=row.preview,
                occurred_at=row.occurred_at or row.created_at,
                match_status=row.match_status,
                suggested_matches=row.suggested_matches or [],
                account_id=row.account_id,
                conversation_key=row.conversation_key,
            )
            for row in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
        request_id=get_request_id() or "",
    )


@router.post("/crm/live-communications/ingest", response_model=LiveIngestResponse)
def ingest_communication(
    payload: LiveIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_provider_connections")),
) -> LiveIngestResponse:
    try:
        comm, created = ingest_live_message(db, payload.model_dump(), actor=user)
        db.commit()
        db.refresh(comm)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LiveIngestResponse(
        id=comm.id,
        created=created,
        match_status=comm.match_status,
        contact_id=comm.contact_id,
        duplicate=not created,
        activity_id=comm.activity_id,
    )


@router.post("/crm/live-communications/{communication_id}/match", response_model=LiveIngestResponse)
def match_unmatched_communication(
    communication_id: UUID,
    payload: ConfirmMatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_communications")),
) -> LiveIngestResponse:
    try:
        comm = confirm_match(
            db,
            communication_id,
            contact_id=payload.contact_id,
            agreement_id=payload.agreement_id,
            actor=user,
        )
        db.commit()
        db.refresh(comm)
    except ValueError as exc:
        code = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=code) from exc
    return LiveIngestResponse(
        id=comm.id,
        created=True,
        match_status=comm.match_status,
        contact_id=comm.contact_id,
        duplicate=False,
        activity_id=comm.activity_id,
    )


@router.post("/crm/live-communications/{communication_id}/ignore", status_code=status.HTTP_204_NO_CONTENT)
def ignore_unmatched_communication(
    communication_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_communications")),
) -> None:
    try:
        ignore_unmatched(db, communication_id, actor=user)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _frontend_base_url() -> str:
    settings = get_settings()
    origins = settings.cors_origins or ["http://localhost:3000"]
    return str(origins[0]).rstrip("/")


def _sanitize_oauth_error(error: str | None) -> str:
    if not error:
        return "oauth_error"
    normalized = error.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in _SAFE_OAUTH_ERRORS:
        return normalized
    if _SAFE_ERROR_RE.fullmatch(normalized):
        return "oauth_error"
    return "oauth_error"


def _gmail_redirect(query: dict[str, str]) -> RedirectResponse:
    url = f"{_frontend_base_url()}{_GMAIL_FRONTEND_PATH}?{urlencode(query)}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/crm/settings/communication-accounts/gmail/status", response_model=GmailStatusResponse)
def gmail_connection_status(
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_accounts),
) -> GmailStatusResponse:
    _ = user
    return GmailStatusResponse(
        configured=gmail_oauth_configured(),
        redirect_uri=gmail_redirect_uri(),
        connected_count=len(connected_gmail_accounts(db)),
        pilot_limit=1,
        client_reuses_drive_oauth=True,
    )


@router.post(
    "/crm/settings/communication-accounts/gmail/authorize",
    response_model=GmailAuthorizeResponse,
)
def gmail_authorize_start(
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_accounts),
) -> GmailAuthorizeResponse:
    _ = db
    try:
        authorize_url = start_authorization(user_id=str(user.id))
    except ValueError as exc:
        code = str(exc) or "gmail_not_configured"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=code if code in _SAFE_OAUTH_ERRORS else "gmail_not_configured",
        ) from exc
    db.commit()
    return GmailAuthorizeResponse(
        authorize_url=authorize_url,
        redirect_uri=gmail_redirect_uri(),
        configured=True,
    )


@router.get("/crm/settings/communication-accounts/gmail/callback")
def gmail_oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    if error:
        return _gmail_redirect({"gmail": "error", "reason": _sanitize_oauth_error(error)})
    if not code:
        return _gmail_redirect({"gmail": "error", "reason": "missing_code"})
    if not state:
        return _gmail_redirect({"gmail": "error", "reason": "missing_state"})
    try:
        account = complete_authorization(db, code=code, state=state)
        db.commit()
        enqueue_gmail_sync(account.id, force_backfill=True)
    except ValueError as exc:
        db.rollback()
        return _gmail_redirect({"gmail": "error", "reason": _sanitize_oauth_error(str(exc))})
    except Exception:
        db.rollback()
        return _gmail_redirect({"gmail": "error", "reason": "oauth_error"})
    return _gmail_redirect({"gmail": "connected", "account_id": str(account.id)})


@router.post(
    "/crm/settings/communication-accounts/{account_id}/sync",
    response_model=GmailSyncResponse,
)
def sync_communication_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_accounts),
) -> GmailSyncResponse:
    account = db.get(CrmUserCommunicationAccount, account_id)
    if account is None or account.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    if account.provider != "gmail":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not_gmail_account")
    result = sync_gmail_account(db, account, actor=user)
    db.commit()
    return GmailSyncResponse(
        account_id=str(account.id),
        ok=bool(result.get("ok")),
        mode=result.get("mode"),
        ingested=int(result.get("ingested") or 0),
        skipped=int(result.get("skipped") or 0),
        duplicates=int(result.get("duplicates") or 0),
        error=result.get("error"),
    )
