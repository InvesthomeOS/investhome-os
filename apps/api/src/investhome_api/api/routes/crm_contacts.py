"""CRM contact management API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.crm_contact import (
    CrmContactPriority,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_contacts import (
    CrmContactAssignOwnerRequest,
    CrmContactBulkUpdateRequest,
    CrmBitrixVerificationSummary,
    CrmContactCreate,
    CrmContactDetail,
    CrmContactImportRequest,
    CrmContactImportResponse,
    CrmContactListResponse,
    CrmContactMergeRequest,
    CrmContactMutationResponse,
    CrmContactRelationshipsResponse,
    CrmContactRelationshipEntry,
    CrmContactSavedViewCreate,
    CrmContactSavedViewResponse,
    CrmContactSavedViewUpdate,
    CrmContactStatusChangeRequest,
    CrmContactTimelineResponse,
    CrmContactUpdate,
    CrmDuplicateCheckRequest,
    CrmDuplicateCheckResponse,
    CrmJunkReasonListResponse,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_created,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity, snapshot_entity
from investhome_api.services.crm.contact_service import (
    CRM_CONTACT_ACTIVITY_FIELDS,
    archive_contact,
    bulk_update_contacts,
    check_duplicates,
    contact_list_meta,
    create_contact,
    create_saved_view,
    delete_contact,
    delete_saved_view,
    export_contacts_csv,
    export_bitrix_verification_csv,
    get_bitrix_verification_summary,
    get_contact_or_none,
    get_contact_relationships,
    assign_contact_owner,
    get_contact_timeline,
    import_contacts,
    list_crm_contacts,
    list_junk_reasons,
    list_saved_views,
    merge_contacts,
    restore_contact,
    serialize_contact_detail,
    update_contact,
    update_saved_view,
    change_contact_status,
)
from investhome_api.services.crm.nedim_purchase_card import resolve_nedim_contact_id
from investhome_api.models.crm_contact import CrmContactSavedView

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])


def _get_contact_or_404(db: Session, contact_id: UUID):
    contact = get_contact_or_none(db, resolve_nedim_contact_id(contact_id))
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.contacts.errors.not_found")
    return contact


def _value_error_http(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=CrmContactListResponse)
def list_contacts(
    search: str | None = Query(default=None, max_length=255),
    contact_type: CrmContactType | None = Query(default=None),
    contact_types: list[CrmContactType] | None = Query(default=None),
    lifecycle_stage: CrmLifecycleStage | None = Query(default=None),
    priority: CrmContactPriority | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    status_filter: CrmContactStatus | None = Query(default=None, alias="status"),
    source_group: str | None = Query(default=None, pattern="^(bitrix|other)$"),
    role_group: str | None = Query(default=None, pattern="^(agent|other)$"),
    category: str | None = Query(default=None, pattern="^(customer|agent|agreement)$"),
    junk_reason: str | None = Query(default=None, max_length=255),
    agreement_project: str | None = Query(default=None, max_length=40),
    bitrix_list: str | None = Query(default=None, pattern="^(current_junk)$"),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at", max_length=40),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmContactListResponse:
    del user
    items, total = list_crm_contacts(
        db,
        search=search,
        contact_type=contact_type,
        contact_types=contact_types,
        lifecycle_stage=lifecycle_stage,
        priority=priority,
        owner_user_id=owner_user_id,
        company_id=company_id,
        status=status_filter,
        source_group=source_group,
        role_group=role_group,
        category=category,
        junk_reason=junk_reason,
        agreement_project=agreement_project,
        bitrix_list=bitrix_list,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    meta = contact_list_meta(total=total, page=page, page_size=page_size)
    return CrmContactListResponse(items=items, request_id=get_request_id() or "", **meta)


@router.get("/export")
def export_contacts(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "export")),
) -> Response:
    del user
    content = export_contacts_csv(db, include_archived=include_archived)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="crm-contacts-export.csv"'},
    )


@router.get("/export/bitrix-verification")
def export_bitrix_contacts_for_verification(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "export")),
) -> Response:
    del user
    content = export_bitrix_verification_csv(db)
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="bitrix-contact-verification.csv"'
        },
    )


@router.get("/bitrix-verification-summary", response_model=CrmBitrixVerificationSummary)
def bitrix_verification_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmBitrixVerificationSummary:
    del user
    return get_bitrix_verification_summary(db)


@router.get("/junk-reasons", response_model=CrmJunkReasonListResponse)
def get_junk_reasons(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmJunkReasonListResponse:
    del user
    items = list_junk_reasons(db)
    return CrmJunkReasonListResponse(items=items, total=len(items))


@router.get("/saved-views", response_model=list[CrmContactSavedViewResponse])
def get_saved_views(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> list[CrmContactSavedViewResponse]:
    return list_saved_views(db, user)


@router.post("/saved-views", response_model=CrmContactSavedViewResponse, status_code=status.HTTP_201_CREATED)
def post_saved_view(
    body: CrmContactSavedViewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmContactSavedViewResponse:
    view = create_saved_view(db, user, body)
    db.commit()
    return CrmContactSavedViewResponse.model_validate(view)


@router.put("/saved-views/{view_id}", response_model=CrmContactSavedViewResponse)
def put_saved_view(
    view_id: UUID,
    body: CrmContactSavedViewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmContactSavedViewResponse:
    view = db.get(CrmContactSavedView, view_id)
    if view is None or (view.owner_user_id != user.id and not view.is_shared):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.contacts.errors.view_not_found")
    view = update_saved_view(db, view, body)
    db.commit()
    return CrmContactSavedViewResponse.model_validate(view)


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_view(
    view_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "delete")),
) -> None:
    view = db.get(CrmContactSavedView, view_id)
    if view is None or view.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="crm.contacts.errors.view_not_found")
    delete_saved_view(db, view)
    db.commit()


@router.post("/check-duplicates", response_model=CrmDuplicateCheckResponse)
def post_check_duplicates(
    body: CrmDuplicateCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmDuplicateCheckResponse:
    del user
    matches = check_duplicates(db, body)
    return CrmDuplicateCheckResponse(matches=matches)


@router.post("/import", response_model=CrmContactImportResponse)
def post_import_contacts(
    body: CrmContactImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "import")),
) -> CrmContactImportResponse:
    result = import_contacts(db, body, actor=user)
    db.commit()
    log_activity(
        db,
        action=ActivityAction.OTHER,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=user.id,
        description_key="activity.crm_contact.imported",
        actor_user=user,
        metadata={"created": result.created, "updated": result.updated, "skipped": result.skipped},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return result


@router.post("/bulk-update")
def post_bulk_update(
    body: CrmContactBulkUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "bulk_actions")),
) -> dict[str, int]:
    count = bulk_update_contacts(db, body)
    db.commit()
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=user.id,
        description_key="activity.crm_contact.bulk_updated",
        actor_user=user,
        metadata={"count": count},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return {"updated": count}


@router.post("/merge", response_model=CrmContactMutationResponse)
def post_merge_contacts(
    body: CrmContactMergeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "merge")),
) -> CrmContactMutationResponse:
    survivor = _get_contact_or_404(db, body.survivor_contact_id)
    merged = _get_contact_or_404(db, body.merged_contact_id)
    try:
        survivor = merge_contacts(db, survivor=survivor, merged=merged, actor=user)
    except ValueError as exc:
        raise _value_error_http(exc) from exc
    db.commit()
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=survivor.id,
        description_key="activity.crm_contact.merged",
        actor_user=user,
        metadata={"merged_contact_id": str(body.merged_contact_id)},
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, survivor, user=user))


@router.get("/{contact_id}", response_model=CrmContactDetail)
def get_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
    project_context: str | None = Query(default=None),
) -> CrmContactDetail:
    contact = _get_contact_or_404(db, contact_id)
    return serialize_contact_detail(db, contact, user=user, project_context=project_context)


@router.post("", response_model=CrmContactMutationResponse, status_code=status.HTTP_201_CREATED)
def create_contact_record(
    body: CrmContactCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmContactMutationResponse:
    try:
        contact = create_contact(db, body, actor=user)
    except ValueError as exc:
        raise _value_error_http(exc) from exc
    after = snapshot_entity(contact, CRM_CONTACT_ACTIVITY_FIELDS)
    log_entity_created(
        db,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="activity.crm_contact.created",
        actor=user,
        metadata=after,
        request=request,
    )
    db.commit()
    contact = _get_contact_or_404(db, contact.id)
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, contact, user=user))


@router.put("/{contact_id}", response_model=CrmContactMutationResponse)
def put_contact(
    contact_id: UUID,
    body: CrmContactUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmContactMutationResponse:
    contact = _get_contact_or_404(db, contact_id)
    before = snapshot_entity(contact, CRM_CONTACT_ACTIVITY_FIELDS)
    try:
        contact = update_contact(db, contact, body, actor=user)
    except ValueError as exc:
        raise _value_error_http(exc) from exc
    after = snapshot_entity(contact, CRM_CONTACT_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="activity.crm_contact.updated",
        actor=user,
        before=before,
        after=after,
        request=request,
    )
    db.commit()
    contact = _get_contact_or_404(db, contact.id)
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, contact, user=user))


@router.patch("/{contact_id}", response_model=CrmContactMutationResponse)
def patch_contact(
    contact_id: UUID,
    body: CrmContactUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmContactMutationResponse:
    return put_contact(contact_id, body, request, db, user)


@router.post("/{contact_id}/archive", response_model=CrmContactMutationResponse)
def post_archive_contact(
    contact_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive")),
) -> CrmContactMutationResponse:
    contact = _get_contact_or_404(db, contact_id)
    archive_contact(db, contact, actor=user)
    log_activity(
        db,
        action=ActivityAction.ARCHIVED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="activity.crm_contact.archived",
        actor_user=user,
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, contact, user=user))


@router.post("/{contact_id}/restore", response_model=CrmContactMutationResponse)
def post_restore_contact(
    contact_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "restore")),
) -> CrmContactMutationResponse:
    contact = _get_contact_or_404(db, contact_id)
    restore_contact(db, contact, actor=user)
    log_activity(
        db,
        action=ActivityAction.RESTORED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="activity.crm_contact.restored",
        actor_user=user,
        request_context=activity_context_from_request(request),
    )
    db.commit()
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, contact, user=user))


@router.post("/{contact_id}/status", response_model=CrmContactMutationResponse)
def post_change_status(
    contact_id: UUID,
    body: CrmContactStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmContactMutationResponse:
    contact = _get_contact_or_404(db, contact_id)
    try:
        change_contact_status(
            db,
            contact,
            status=body.status,
            junk_reason=body.junk_reason,
            next_follow_up_at=body.next_follow_up_at,
            actor=user,
        )
    except ValueError as exc:
        raise _value_error_http(exc) from exc
    log_activity(
        db,
        action=ActivityAction.STATUS_CHANGED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="activity.crm_contact.status_changed",
        actor_user=user,
        request_context=activity_context_from_request(request),
        metadata={"status": body.status.value, "junk_reason": body.junk_reason},
    )
    db.commit()
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, contact, user=user))


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_contact(
    contact_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "delete")),
) -> None:
    contact = _get_contact_or_404(db, contact_id)
    before = snapshot_entity(contact, CRM_CONTACT_ACTIVITY_FIELDS)
    delete_contact(db, contact)
    log_activity(
        db,
        action=ActivityAction.DELETED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact_id,
        description_key="activity.crm_contact.deleted",
        actor_user=user,
        metadata=before,
        request_context=activity_context_from_request(request),
    )
    db.commit()


@router.post("/{contact_id}/assign-owner", response_model=CrmContactMutationResponse)
def post_assign_owner(
    contact_id: UUID,
    body: CrmContactAssignOwnerRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "transfer_ownership")),
) -> CrmContactMutationResponse:
    contact = _get_contact_or_404(db, contact_id)
    before = snapshot_entity(contact, CRM_CONTACT_ACTIVITY_FIELDS)
    assign_contact_owner(db, contact, owner_user_id=body.owner_user_id, actor=user)
    after = snapshot_entity(contact, CRM_CONTACT_ACTIVITY_FIELDS)
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="activity.crm_contact.owner_assigned",
        actor=user,
        before=before,
        after=after,
        request=request,
    )
    db.commit()
    return CrmContactMutationResponse(contact=serialize_contact_detail(db, contact, user=user))


@router.get("/{contact_id}/timeline", response_model=CrmContactTimelineResponse)
def get_timeline(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
    project_context: str | None = Query(default=None),
) -> CrmContactTimelineResponse:
    _get_contact_or_404(db, contact_id)
    items = get_contact_timeline(db, contact_id, user, project_context=project_context)
    return CrmContactTimelineResponse(items=items)


@router.get("/{contact_id}/relationships", response_model=CrmContactRelationshipsResponse)
def get_relationships(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> CrmContactRelationshipsResponse:
    contact = _get_contact_or_404(db, contact_id)
    related = get_contact_relationships(db, contact)
    items = [
        CrmContactRelationshipEntry(
            contact_id=row.id,
            display_name=row.display_name,
            contact_type=row.contact_type,
            relationship_status=row.relationship_status,
            relationship_strength=row.relationship_strength,
        )
        for row in related
    ]
    return CrmContactRelationshipsResponse(items=items)
