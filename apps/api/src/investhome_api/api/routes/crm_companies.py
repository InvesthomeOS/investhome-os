"""CRM Company API routes — prefix /crm/companies (distinct from org /companies)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_companies import (
    CrmCompanyBulkActionRequest,
    CrmCompanyBulkActionResponse,
    CrmCompanyContactCreate,
    CrmCompanyContactResponse,
    CrmCompanyContactUpdate,
    CrmCompanyCounts,
    CrmCompanyCreate,
    CrmCompanyDetail,
    CrmCompanyDuplicateCandidate,
    CrmCompanyHierarchyResponse,
    CrmCompanyImportResult,
    CrmCompanyListResponse,
    CrmCompanyMergeRequest,
    CrmCompanyMergeResponse,
    CrmCompanyRelationshipCreate,
    CrmCompanyRelationshipResponse,
    CrmCompanySavedViewCreate,
    CrmCompanySavedViewResponse,
    CrmCompanyTimelineEntry,
    CrmCompanyTimelineResponse,
    CrmCompanyTransferOwnershipRequest,
    CrmCompanyUpdate,
)
from investhome_api.services.activity_service import list_activities, snapshot_entity
from investhome_api.services.crm_company_activity import (
    CRM_COMPANY_ACTIVITY_FIELDS,
    record_crm_company_archived,
    record_crm_company_created,
    record_crm_company_deleted,
    record_crm_company_merged,
    record_crm_company_ownership_changed,
    record_crm_company_restored,
    record_crm_company_updated,
)
from investhome_api.services.crm_company_service import (
    add_company_contact,
    add_company_relationship,
    archive_crm_company,
    bulk_action,
    build_hierarchy,
    company_workspace_counts,
    create_crm_company,
    create_saved_view,
    delete_crm_company,
    export_crm_companies_csv,
    find_duplicates,
    get_company_or_404,
    import_crm_companies_csv,
    list_crm_companies,
    list_saved_views,
    merge_crm_companies,
    remove_company_contact,
    restore_crm_company,
    serialize_company_detail,
    update_company_contact,
    update_crm_company,
)
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm/companies", tags=["crm-companies"])


def _require_crm_companies_read():
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not (
            user_has_permission(user, "crm", "view_companies")
            or user_has_permission(user, "crm", "read")
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dependency


@router.get("", response_model=CrmCompanyListResponse)
def list_companies(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    company_type: str | None = Query(default=None),
    lifecycle_stage: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    owner_user_id: UUID | None = Query(default=None),
    country: str | None = Query(default=None),
    relationship_status: str | None = Query(default=None),
    open_relationships: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> CrmCompanyListResponse:
    del user
    return list_crm_companies(
        db,
        search=search,
        status_filter=status_filter,
        company_type=company_type,
        lifecycle_stage=lifecycle_stage,
        industry=industry,
        owner_user_id=owner_user_id,
        country=country,
        relationship_status=relationship_status,
        open_relationships=open_relationships,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/counts", response_model=CrmCompanyCounts)
def get_company_counts(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> CrmCompanyCounts:
    del user
    return company_workspace_counts(db)


@router.post("", response_model=CrmCompanyDetail, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CrmCompanyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmCompanyDetail:
    company = create_crm_company(db, payload, user)
    record_crm_company_created(db, company, user, request)
    db.commit()
    db.refresh(company)
    return serialize_company_detail(db, get_company_or_404(db, company.id), user)


@router.get("/duplicates", response_model=list[CrmCompanyDuplicateCandidate])
def get_duplicates(
    company_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> list[CrmCompanyDuplicateCandidate]:
    del user
    return find_duplicates(db, company_id)


@router.get("/hierarchy", response_model=CrmCompanyHierarchyResponse)
def get_hierarchy(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> CrmCompanyHierarchyResponse:
    del user
    return build_hierarchy(db)


@router.get("/export", response_class=PlainTextResponse)
def export_companies(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("crm", "export")),
) -> PlainTextResponse:
    content = export_crm_companies_csv(db, include_archived=include_archived)
    return PlainTextResponse(content, media_type="text/csv")


@router.post("/import", response_model=CrmCompanyImportResult)
async def import_companies(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "import")),
) -> CrmCompanyImportResult:
    del user
    content = (await file.read()).decode("utf-8-sig")
    result = import_crm_companies_csv(db, content)
    db.commit()
    return result


@router.post("/bulk", response_model=CrmCompanyBulkActionResponse)
def bulk_companies(
    payload: CrmCompanyBulkActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "bulk_actions")),
) -> CrmCompanyBulkActionResponse:
    del request
    result = bulk_action(db, payload.company_ids, payload.action, payload.payload)
    db.commit()
    return result


@router.post("/merge", response_model=CrmCompanyMergeResponse)
def merge_companies(
    payload: CrmCompanyMergeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "merge")),
) -> CrmCompanyMergeResponse:
    target = get_company_or_404(db, payload.target_id)
    result = merge_crm_companies(db, payload.source_id, payload.target_id)
    record_crm_company_merged(db, target, payload.source_id, user, request)
    db.commit()
    return result


@router.get("/saved-views", response_model=list[CrmCompanySavedViewResponse])
def get_saved_views(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> list[CrmCompanySavedViewResponse]:
    return list_saved_views(db, user.id)


@router.post("/saved-views", response_model=CrmCompanySavedViewResponse, status_code=status.HTTP_201_CREATED)
def post_saved_view(
    payload: CrmCompanySavedViewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "create")),
) -> CrmCompanySavedViewResponse:
    view = create_saved_view(db, user.id, payload)
    db.commit()
    db.refresh(view)
    return CrmCompanySavedViewResponse.model_validate(view)


@router.get("/{company_id}", response_model=CrmCompanyDetail)
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> CrmCompanyDetail:
    company = get_company_or_404(db, company_id)
    return serialize_company_detail(db, company, user)


@router.put("/{company_id}", response_model=CrmCompanyDetail)
def update_company(
    company_id: UUID,
    payload: CrmCompanyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmCompanyDetail:
    company = get_company_or_404(db, company_id)
    before = snapshot_entity(company, CRM_COMPANY_ACTIVITY_FIELDS)
    company = update_crm_company(db, company, payload)
    record_crm_company_updated(db, company, user, before, request)
    db.commit()
    return serialize_company_detail(db, get_company_or_404(db, company_id), user)


@router.patch("/{company_id}/archive", response_model=CrmCompanyDetail)
def archive_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "archive")),
) -> CrmCompanyDetail:
    company = get_company_or_404(db, company_id)
    archive_crm_company(db, company)
    record_crm_company_archived(db, company, user, request)
    db.commit()
    return serialize_company_detail(db, get_company_or_404(db, company_id, include_archived=True), user)


@router.patch("/{company_id}/restore", response_model=CrmCompanyDetail)
def restore_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "restore")),
) -> CrmCompanyDetail:
    company = get_company_or_404(db, company_id, include_archived=True)
    restore_crm_company(db, company)
    record_crm_company_restored(db, company, user, request)
    db.commit()
    return serialize_company_detail(db, get_company_or_404(db, company_id), user)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "delete")),
) -> None:
    company = get_company_or_404(db, company_id, include_archived=True)
    display_name = company.display_name
    delete_crm_company(db, company)
    record_crm_company_deleted(db, company_id, display_name, user, request)
    db.commit()


@router.patch("/{company_id}/transfer-ownership", response_model=CrmCompanyDetail)
def transfer_ownership(
    company_id: UUID,
    payload: CrmCompanyTransferOwnershipRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "transfer_ownership")),
) -> CrmCompanyDetail:
    company = get_company_or_404(db, company_id)
    previous_owner = company.owner_user_id
    company.owner_user_id = payload.owner_user_id
    record_crm_company_ownership_changed(db, company, user, previous_owner, request)
    db.commit()
    return serialize_company_detail(db, get_company_or_404(db, company_id), user)


@router.get("/{company_id}/contacts", response_model=list[CrmCompanyContactResponse])
def list_company_contacts(
    company_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> list[CrmCompanyContactResponse]:
    company = get_company_or_404(db, company_id)
    return serialize_company_detail(db, company, user).contacts


@router.post("/{company_id}/contacts", response_model=CrmCompanyContactResponse, status_code=status.HTTP_201_CREATED)
def create_company_contact(
    company_id: UUID,
    payload: CrmCompanyContactCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_company_contacts")),
) -> CrmCompanyContactResponse:
    del user
    company = get_company_or_404(db, company_id)
    link = add_company_contact(db, company, payload)
    db.commit()
    detail = serialize_company_detail(db, get_company_or_404(db, company_id))
    return next(c for c in detail.contacts if c.id == link.id)


@router.put("/{company_id}/contacts/{link_id}", response_model=CrmCompanyContactResponse)
def update_company_contact_route(
    company_id: UUID,
    link_id: UUID,
    payload: CrmCompanyContactUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_company_contacts")),
) -> CrmCompanyContactResponse:
    del user
    company = get_company_or_404(db, company_id)
    link = update_company_contact(db, company, link_id, payload)
    db.commit()
    detail = serialize_company_detail(db, get_company_or_404(db, company_id))
    return next(c for c in detail.contacts if c.id == link.id)


@router.delete("/{company_id}/contacts/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_contact(
    company_id: UUID,
    link_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "manage_company_contacts")),
) -> None:
    del user
    company = get_company_or_404(db, company_id)
    remove_company_contact(db, company, link_id)
    db.commit()


@router.post("/{company_id}/relationships", response_model=CrmCompanyRelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_company_relationship(
    company_id: UUID,
    payload: CrmCompanyRelationshipCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "update")),
) -> CrmCompanyRelationshipResponse:
    del user
    company = get_company_or_404(db, company_id)
    rel = add_company_relationship(db, company, payload)
    db.commit()
    detail = serialize_company_detail(db, get_company_or_404(db, company_id))
    return next(r for r in detail.relationships if r.id == rel.id)


@router.get("/{company_id}/timeline", response_model=CrmCompanyTimelineResponse)
def get_company_timeline(
    company_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_companies_read()),
) -> CrmCompanyTimelineResponse:
    get_company_or_404(db, company_id)
    items, total = list_activities(
        db,
        user,
        entity_type=ActivityEntityType.CRM_COMPANY,
        entity_id=company_id,
        page_size=limit,
    )
    return CrmCompanyTimelineResponse(
        items=[
            CrmCompanyTimelineEntry(
                id=item.id,
                action=item.action.value,
                description_key=item.description_key,
                actor_name=item.actor_name,
                metadata=item.metadata_json,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
    )
