"""Company workspace API routes — dashboard, activity, search, and management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.config.search_config import DEFAULT_PER_ENTITY_LIMIT, DEFAULT_TOTAL_LIMIT
from investhome_api.db.session import get_db
from investhome_api.models.company import CompanyEntityType, CompanyStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.company_management import (
    CompanyCreate,
    CompanyDuplicateResponse,
    CompanyImportResult,
    CompanyListResponse,
    CompanyResponse,
    CompanyTransferOwnershipRequest,
    CompanyUpdate,
)
from investhome_api.schemas.company_workspace import (
    CompanyActivityItemResponse,
    CompanyDashboardKpisResponse,
    CompanyRecentActivityResponse,
    CompanySearchResponse,
)
from investhome_api.services.company_activity_service import (
    list_recent_company_activity,
    serialize_activity_entry,
)
from investhome_api.services.company_dashboard_service import build_dashboard_kpis
from investhome_api.services.company_management_activity import (
    COMPANY_ACTIVITY_FIELDS,
    record_company_archived,
    record_company_created,
    record_company_ownership_changed,
    record_company_status_changed,
    record_company_updated,
)
from investhome_api.services.company_management_service import (
    archive_company,
    create_company,
    deactivate_company,
    delete_company,
    duplicate_company,
    export_companies_csv,
    get_company_or_404,
    import_companies_csv,
    list_companies,
    serialize_company,
    transfer_ownership,
    update_company,
)
from investhome_api.services.company_search_service import (
    COMPANY_SEARCH_ENTITY_TYPES,
    company_workspace_search,
)
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/companies", tags=["companies"])


def _require_company_read():
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(user, "company", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency


def _parse_entity_types(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {part.strip() for part in raw.split(",") if part.strip()}
    filtered = {value for value in values if value in COMPANY_SEARCH_ENTITY_TYPES}
    return filtered or None


@router.get("/dashboard", response_model=CompanyDashboardKpisResponse)
def get_company_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(_require_company_read()),
) -> CompanyDashboardKpisResponse:
    del user
    return CompanyDashboardKpisResponse(**build_dashboard_kpis(db))


@router.get("/recent-activity", response_model=CompanyRecentActivityResponse)
def get_company_recent_activity(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(_require_company_read()),
) -> CompanyRecentActivityResponse:
    items, total = list_recent_company_activity(db, user, limit=limit)
    return CompanyRecentActivityResponse(
        items=[
            CompanyActivityItemResponse.model_validate(serialize_activity_entry(item))
            for item in items
        ],
        total=total,
    )


@router.get("/search", response_model=CompanySearchResponse)
def search_company_workspace(
    q: str = Query(..., min_length=1, max_length=255),
    entity_types: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=DEFAULT_TOTAL_LIMIT, ge=1, le=100),
    per_entity_limit: int = Query(default=DEFAULT_PER_ENTITY_LIMIT, ge=1, le=25),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "read")),
) -> CompanySearchResponse:
    normalized = q.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query must not be empty")
    result = company_workspace_search(
        db,
        user,
        normalized,
        entity_types=_parse_entity_types(entity_types),
        limit=limit,
        per_entity_limit=per_entity_limit,
    )
    return CompanySearchResponse.model_validate(result.model_dump())


@router.get("/export", response_class=PlainTextResponse)
def export_companies(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("company", "export")),
) -> PlainTextResponse:
    content = export_companies_csv(db, include_archived=include_archived)
    return PlainTextResponse(content, media_type="text/csv")


@router.post("/import", response_model=CompanyImportResult)
async def import_companies(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "create")),
) -> CompanyImportResult:
    del user
    raw = (await file.read()).decode("utf-8-sig")
    result = import_companies_csv(db, raw)
    db.commit()
    return result


@router.get("", response_model=CompanyListResponse)
def list_managed_companies(
    search: str | None = Query(default=None, max_length=255),
    status_filter: CompanyStatus | None = Query(default=None, alias="status"),
    country: str | None = Query(default=None, max_length=100),
    entity_type: CompanyEntityType | None = None,
    owner_user_id: UUID | None = None,
    industry: str | None = Query(default=None, max_length=120),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("company", "read")),
) -> CompanyListResponse:
    return list_companies(
        db,
        search=search,
        status_filter=status_filter,
        country=country,
        entity_type=entity_type,
        owner_user_id=owner_user_id,
        industry=industry,
        created_from=created_from,
        created_to=created_to,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_managed_company(
    payload: CompanyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "create")),
) -> CompanyResponse:
    company = create_company(db, payload)
    record_company_created(db, company, user, request)
    db.commit()
    db.refresh(company)
    return serialize_company(db, get_company_or_404(db, company.id), user=user, include_children=True)  # type: ignore[return-value]


@router.get("/{company_id}", response_model=CompanyResponse)
def get_managed_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "read")),
) -> CompanyResponse:
    company = get_company_or_404(db, company_id)
    return serialize_company(db, company, user=user, include_children=True)  # type: ignore[return-value]


@router.put("/{company_id}", response_model=CompanyResponse)
def update_managed_company(
    company_id: UUID,
    payload: CompanyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "update")),
) -> CompanyResponse:
    company = get_company_or_404(db, company_id)
    before = snapshot_entity(company, COMPANY_ACTIVITY_FIELDS)
    previous_status = company.status
    previous_owner = company.owner_user_id
    company = update_company(db, company, payload)
    record_company_updated(db, company, user, before, request)
    if payload.status is not None and company.status != previous_status:
        record_company_status_changed(db, company, user, previous_status, request)
    if payload.owner_user_id is not None and company.owner_user_id != previous_owner:
        record_company_ownership_changed(db, company, user, previous_owner, request)
    db.commit()
    return serialize_company(db, get_company_or_404(db, company.id), user=user, include_children=True)  # type: ignore[return-value]


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_managed_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "delete")),
) -> None:
    company = get_company_or_404(db, company_id)
    delete_company(db, company)
    record_company_archived(db, company, user, request)
    db.commit()


@router.patch("/{company_id}/archive", response_model=CompanyResponse)
def archive_managed_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "archive")),
) -> CompanyResponse:
    company = get_company_or_404(db, company_id)
    previous_status = company.status
    company = archive_company(db, company)
    record_company_status_changed(db, company, user, previous_status, request)
    record_company_archived(db, company, user, request)
    db.commit()
    return serialize_company(db, get_company_or_404(db, company.id, include_archived=True), user=user, include_children=True)  # type: ignore[return-value]


@router.patch("/{company_id}/deactivate", response_model=CompanyResponse)
def deactivate_managed_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "update")),
) -> CompanyResponse:
    company = get_company_or_404(db, company_id)
    previous_status = company.status
    company = deactivate_company(db, company)
    record_company_status_changed(db, company, user, previous_status, request)
    db.commit()
    return serialize_company(db, get_company_or_404(db, company.id), user=user, include_children=True)  # type: ignore[return-value]


@router.post("/{company_id}/duplicate", response_model=CompanyDuplicateResponse, status_code=status.HTTP_201_CREATED)
def duplicate_managed_company(
    company_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "create")),
) -> CompanyDuplicateResponse:
    source = get_company_or_404(db, company_id)
    clone = duplicate_company(db, source)
    record_company_created(db, clone, user, request)
    db.commit()
    return CompanyDuplicateResponse(
        company=serialize_company(db, get_company_or_404(db, clone.id), user=user, include_children=True)  # type: ignore[arg-type]
    )


@router.patch("/{company_id}/transfer-ownership", response_model=CompanyResponse)
def transfer_managed_company_ownership(
    company_id: UUID,
    payload: CompanyTransferOwnershipRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "update")),
) -> CompanyResponse:
    company = get_company_or_404(db, company_id)
    previous_owner = company.owner_user_id
    company = transfer_ownership(db, company, payload.owner_user_id)
    record_company_ownership_changed(db, company, user, previous_owner, request)
    db.commit()
    return serialize_company(db, get_company_or_404(db, company.id), user=user, include_children=True)  # type: ignore[return-value]
