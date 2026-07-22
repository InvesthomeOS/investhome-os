"""CRM communication center API routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.crm_communication import (
    CrmCommunicationChannel,
    CrmCommunicationDirection,
    CrmCommunicationEntityType,
    CrmCommunicationStatus,
    CrmThreadStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_communications import (
    AnalyticsDashboardResponse,
    CommunicationCreate,
    CommunicationDetail,
    CommunicationListResponse,
    CommunicationMutationResponse,
    CommunicationUpdate,
    PreferenceDetail,
    PreferenceUpsert,
    ProviderStatusListResponse,
    SequenceCreate,
    SequenceDetail,
    SequenceListResponse,
    SequenceUpdate,
    SignatureCreate,
    SignatureDetail,
    SignatureListResponse,
    SignatureUpdate,
    TemplateCreate,
    TemplateDetail,
    TemplateListResponse,
    TemplateUpdate,
    ThreadAssignRequest,
    ThreadDetail,
    ThreadFollowUpRequest,
    ThreadListResponse,
    ThreadMutationResponse,
    ThreadSnoozeRequest,
)
from investhome_api.services.crm.communication_service import (
    archive_communication,
    archive_template,
    archive_thread,
    assign_thread,
    create_communication,
    create_sequence,
    create_signature,
    create_template,
    get_analytics_dashboard,
    get_communication_or_none,
    get_preferences,
    get_provider_statuses,
    get_thread_detail,
    list_communications,
    list_sequences,
    list_signatures,
    list_templates,
    list_threads,
    mark_thread_read,
    mark_thread_unread,
    pin_thread,
    restore_communication,
    set_thread_follow_up,
    snooze_thread,
    update_communication,
    update_sequence,
    update_signature,
    update_template,
    upsert_preferences,
)
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm/communications", tags=["crm-communications"])


def _require_view_communications():
    async def _dependency(user: User = Depends(require_permission("crm", "read"))) -> User:
        if not user_has_permission(user, "crm", "view_communications") and not user_has_permission(
            user, "crm", "read"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dependency


def _require_create_communications():
    return require_permission("crm", "create_communications")


def _require_send_communications():
    return require_permission("crm", "send_communications")


def _require_manage_templates():
    return require_permission("crm", "manage_templates")


@router.get("/threads", response_model=ThreadListResponse)
def get_communication_threads(
    folder: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    channel: CrmCommunicationChannel | None = Query(default=None),
    status_filter: CrmThreadStatus | None = Query(default=None, alias="status"),
    owner_id: UUID | None = Query(default=None),
    assigned_user_id: UUID | None = Query(default=None),
    assigned_team_id: UUID | None = Query(default=None),
    unread_only: bool = Query(default=False),
    follow_up_due: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    entity_type: CrmCommunicationEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    sort_by: str = Query(default="last_communication_at"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> ThreadListResponse:
    items, meta = list_threads(
        db,
        user,
        folder=folder,
        search=search,
        channel=channel,
        status=status_filter,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
        assigned_team_id=assigned_team_id,
        unread_only=unread_only,
        follow_up_due=follow_up_due,
        include_archived=include_archived,
        entity_type=entity_type.value if entity_type else None,
        entity_id=entity_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return ThreadListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
def get_communication_thread_by_id(
    thread_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> ThreadDetail:
    thread = get_thread_detail(db, user, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return thread


@router.post("/threads/{thread_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_thread_read_endpoint(
    thread_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> Response:
    if not mark_thread_read(db, thread_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/threads/{thread_id}/unread", status_code=status.HTTP_204_NO_CONTENT)
def mark_thread_unread_endpoint(
    thread_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> Response:
    if not mark_thread_unread(db, thread_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/threads/{thread_id}/assign", response_model=ThreadMutationResponse)
def assign_thread_endpoint(
    thread_id: UUID,
    payload: ThreadAssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_communications")),
) -> ThreadMutationResponse:
    thread = assign_thread(
        db,
        thread_id,
        assigned_user_id=payload.assigned_user_id,
        assigned_team_id=payload.assigned_team_id,
    )
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return ThreadMutationResponse(thread=thread)


@router.post("/threads/{thread_id}/follow-up", status_code=status.HTTP_204_NO_CONTENT)
def set_thread_follow_up_endpoint(
    thread_id: UUID,
    payload: ThreadFollowUpRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_communications")),
) -> Response:
    if not set_thread_follow_up(db, thread_id, payload.follow_up_date):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/threads/{thread_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
def pin_thread_endpoint(
    thread_id: UUID,
    pinned: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> Response:
    if not pin_thread(db, thread_id, pinned):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/threads/{thread_id}/snooze", status_code=status.HTTP_204_NO_CONTENT)
def snooze_thread_endpoint(
    thread_id: UUID,
    payload: ThreadSnoozeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> Response:
    if not snooze_thread(db, thread_id, payload.snoozed_until):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/threads/{thread_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_thread_endpoint(
    thread_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive_communications")),
) -> Response:
    if not archive_thread(db, thread_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.thread_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=CommunicationListResponse)
def get_communications(
    folder: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    channel: CrmCommunicationChannel | None = Query(default=None),
    direction: CrmCommunicationDirection | None = Query(default=None),
    status_filter: CrmCommunicationStatus | None = Query(default=None, alias="status"),
    thread_id: UUID | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    assigned_user_id: UUID | None = Query(default=None),
    entity_type: CrmCommunicationEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> CommunicationListResponse:
    items, meta = list_communications(
        db,
        user,
        folder=folder,
        search=search,
        channel=channel,
        direction=direction,
        status=status_filter,
        thread_id=thread_id,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
        entity_type=entity_type.value if entity_type else None,
        entity_id=entity_id,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return CommunicationListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/search", response_model=CommunicationListResponse)
def search_communications(
    q: str = Query(min_length=1, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> CommunicationListResponse:
    items, meta = list_communications(db, user, search=q, page=page, page_size=page_size)
    return CommunicationListResponse(items=items, request_id=get_request_id() or "", **meta)


# Templates (static paths before /{communication_id})
@router.get("/templates/list", response_model=TemplateListResponse)
def get_templates(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> TemplateListResponse:
    items, meta = list_templates(db, user, page=page, page_size=page_size, search=search)
    return TemplateListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.post("/templates", response_model=TemplateDetail, status_code=status.HTTP_201_CREATED)
def create_template_endpoint(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_templates()),
) -> TemplateDetail:
    return create_template(db, user, payload)


@router.patch("/templates/{template_id}", response_model=TemplateDetail)
def update_template_endpoint(
    template_id: UUID,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_templates()),
) -> TemplateDetail:
    tpl = update_template(db, template_id, payload)
    if tpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.template_not_found")
    return tpl


@router.post("/templates/{template_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_template_endpoint(
    template_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_manage_templates()),
) -> Response:
    if not archive_template(db, template_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.template_not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/signatures/list", response_model=SignatureListResponse)
def get_signatures(
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> SignatureListResponse:
    return SignatureListResponse(items=list_signatures(db, user), request_id=get_request_id() or "")


@router.post("/signatures", response_model=SignatureDetail, status_code=status.HTTP_201_CREATED)
def create_signature_endpoint(
    payload: SignatureCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_signatures")),
) -> SignatureDetail:
    return create_signature(db, user, payload)


@router.patch("/signatures/{signature_id}", response_model=SignatureDetail)
def update_signature_endpoint(
    signature_id: UUID,
    payload: SignatureUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_signatures")),
) -> SignatureDetail:
    sig = update_signature(db, signature_id, payload)
    if sig is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.signature_not_found")
    return sig


@router.get("/sequences/list", response_model=SequenceListResponse)
def get_sequences(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> SequenceListResponse:
    items, meta = list_sequences(db, page=page, page_size=page_size)
    return SequenceListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.post("/sequences", response_model=SequenceDetail, status_code=status.HTTP_201_CREATED)
def create_sequence_endpoint(
    payload: SequenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_sequences")),
) -> SequenceDetail:
    return create_sequence(db, user, payload)


@router.patch("/sequences/{sequence_id}", response_model=SequenceDetail)
def update_sequence_endpoint(
    sequence_id: UUID,
    payload: SequenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_sequences")),
) -> SequenceDetail:
    seq = update_sequence(db, sequence_id, payload)
    if seq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.sequence_not_found")
    return seq


@router.get("/preferences/{entity_type}/{entity_id}", response_model=PreferenceDetail)
def get_communication_preferences(
    entity_type: CrmCommunicationEntityType,
    entity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> PreferenceDetail:
    pref = get_preferences(db, entity_type.value, entity_id)
    if pref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.preferences_not_found")
    return pref


@router.put("/preferences/{entity_type}/{entity_id}", response_model=PreferenceDetail)
def upsert_communication_preferences(
    entity_type: CrmCommunicationEntityType,
    entity_id: UUID,
    payload: PreferenceUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_communications")),
) -> PreferenceDetail:
    return upsert_preferences(db, user, entity_type.value, entity_id, payload)


@router.get("/analytics/dashboard", response_model=AnalyticsDashboardResponse)
def get_communication_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "view_analytics")),
) -> AnalyticsDashboardResponse:
    result = get_analytics_dashboard(db, user)
    result.request_id = get_request_id() or ""
    return result


@router.get("/providers/status", response_model=ProviderStatusListResponse)
def get_provider_status_endpoint(
    user: User = Depends(_require_view_communications()),
) -> ProviderStatusListResponse:
    return ProviderStatusListResponse(items=get_provider_statuses(), request_id=get_request_id() or "")


@router.get("/calls/list", response_model=CommunicationListResponse)
def get_call_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> CommunicationListResponse:
    items, meta = list_communications(
        db,
        user,
        folder="calls",
        page=page,
        page_size=page_size,
        sort_by="created_at",
        sort_dir="desc",
    )
    return CommunicationListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/meetings/list", response_model=CommunicationListResponse)
def get_meetings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> CommunicationListResponse:
    items, meta = list_communications(
        db,
        user,
        folder="meetings",
        page=page,
        page_size=page_size,
        sort_by="meeting_start_at",
        sort_dir="desc",
    )
    return CommunicationListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/{communication_id}", response_model=CommunicationDetail)
def get_communication_by_id(
    communication_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_view_communications()),
) -> CommunicationDetail:
    from investhome_api.services.crm.communication_service import _serialize_comm_detail

    comm = get_communication_or_none(db, communication_id)
    if comm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.not_found")
    return _serialize_comm_detail(comm)


@router.post("", response_model=CommunicationMutationResponse, status_code=status.HTTP_201_CREATED)
def create_communication_endpoint(
    payload: CommunicationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_create_communications()),
) -> CommunicationMutationResponse:
    if payload.status in {CrmCommunicationStatus.SENT, CrmCommunicationStatus.QUEUED}:
        if not user_has_permission(user, "crm", "send_communications"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to send")
    if payload.status == CrmCommunicationStatus.SCHEDULED:
        if not user_has_permission(user, "crm", "schedule_communications"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to schedule")
    comm, warnings = create_communication(db, user, payload, request=request)
    return CommunicationMutationResponse(communication=comm, warnings=warnings)


@router.patch("/{communication_id}", response_model=CommunicationMutationResponse)
def update_communication_endpoint(
    communication_id: UUID,
    payload: CommunicationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "edit_communications")),
) -> CommunicationMutationResponse:
    comm = update_communication(db, user, communication_id, payload, request=request)
    if comm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.not_found")
    return CommunicationMutationResponse(communication=comm)


@router.post("/{communication_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_communication_endpoint(
    communication_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive_communications")),
) -> Response:
    if not archive_communication(db, user, communication_id, request=request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{communication_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_communication_endpoint(
    communication_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive_communications")),
) -> Response:
    if not restore_communication(db, user, communication_id, request=request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.communications.errors.not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
