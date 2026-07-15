"""Company foundation API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.company_foundation import (
    BrandAsset,
    BrandProfile,
    Department,
    Office,
    Team,
)
from investhome_api.models.document import Document
from investhome_api.models.user_auth import User
from investhome_api.schemas.company_foundation import (
    BrandAssetCreate,
    BrandAssetResponse,
    BrandAssetUpdate,
    BrandProfileCreate,
    BrandProfileResponse,
    BrandProfileUpdate,
    CompanyContextResponse,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    OfficeCreate,
    OfficeResponse,
    OfficeUpdate,
    PreferenceItemResponse,
    ProviderStatusListResponse,
    ProviderStatusResponse,
    PublicBrandResponse,
    SupportedOptionsResponse,
    SystemPreferencesResponse,
    SystemPreferencesUpdate,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
    UserOrganizationAssignment,
)
from investhome_api.models.activity import ActivityEntityType
from investhome_api.services.activity_recorder import log_entity_updated
from investhome_api.services.activity_service import snapshot_entity
from investhome_api.services.company_foundation import activity as cf_activity
from investhome_api.services.company_foundation_service import (
    archive_brand,
    archive_brand_asset,
    archive_office,
    assign_user_organization,
    build_company_context,
    get_all_preferences,
    get_company_profile,
    get_default_brand,
    get_or_create_company_profile,
    get_provider_statuses,
    mask_secret_value,
    set_default_brand,
    supported_options,
    update_preferences,
)
from investhome_api.services.notification_service import create_notification
from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType

router = APIRouter(tags=["company-foundation"])


def _company_or_404(db: Session):
    company = get_or_create_company_profile(db)
    return company


def _office_or_404(db: Session, office_id: UUID) -> Office:
    office = db.get(Office, office_id)
    if office is None or office.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.office_not_found")
    return office


def _brand_or_404(db: Session, brand_id: UUID) -> BrandProfile:
    brand = db.get(BrandProfile, brand_id)
    if brand is None or brand.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.brand_not_found")
    return brand


def _pref_response(pref) -> PreferenceItemResponse:
    raw = pref.value_json.get("value") if pref.value_json else None
    value = mask_secret_value(raw) if pref.is_secret else raw
    return PreferenceItemResponse(
        preference_key=pref.preference_key,
        category=pref.category,
        value=value,
        is_secret=pref.is_secret,
        is_configured=raw is not None,
    )


@router.get("/company/public-brand", response_model=PublicBrandResponse)
def get_public_brand(db: Session = Depends(get_db)) -> PublicBrandResponse:
    """Public branding context without authentication (no secrets)."""
    company = get_or_create_company_profile(db)
    brand = get_default_brand(db, company.id)
    return PublicBrandResponse(
        company_name=company.company_name,
        short_name=company.short_name,
        slogan=company.slogan or (brand.slogan if brand else None),
        primary_color=brand.primary_color if brand else None,
        accent_color=brand.accent_color if brand else None,
        logo_primary_document_id=brand.logo_primary_document_id if brand else None,
    )


@router.get("/company/context", response_model=CompanyContextResponse)
def get_company_context(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("company", "view")),
) -> CompanyContextResponse:
    ctx = build_company_context(db)
    brand = ctx.pop("brand")
    return CompanyContextResponse(
        **ctx,
        brand=BrandProfileResponse.model_validate(brand) if brand else None,
    )


@router.get("/company/profile", response_model=CompanyProfileResponse)
def get_company_profile_route(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("company", "view")),
) -> CompanyProfileResponse:
    return CompanyProfileResponse.model_validate(_company_or_404(db))


@router.patch("/company/profile", response_model=CompanyProfileResponse)
def update_company_profile(
    body: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("company", "update")),
) -> CompanyProfileResponse:
    company = _company_or_404(db)
    update_fields = list(body.model_dump(exclude_unset=True).keys())
    before = snapshot_entity(company, update_fields)
    changed: list[str] = []
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None and getattr(company, field) != value:
            setattr(company, field, value)
            changed.append(field)
    if changed:
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.COMPANY,
            entity_id=company.id,
            description_key="activity.company.profile_updated",
            actor=user,
            before=before,
            after=snapshot_entity(company, update_fields),
            metadata={"company_name": company.company_name},
        )
        db.commit()
        db.refresh(company)
    return CompanyProfileResponse.model_validate(company)


@router.get("/offices", response_model=list[OfficeResponse])
def list_offices(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("offices", "view")),
) -> list[OfficeResponse]:
    company = _company_or_404(db)
    query = select(Office).where(Office.company_id == company.id)
    if not include_archived:
        query = query.where(Office.archived_at.is_(None))
    offices = db.scalars(query.order_by(Office.office_name)).all()
    return [OfficeResponse.model_validate(o) for o in offices]


@router.get("/offices/{office_id}", response_model=OfficeResponse)
def get_office(
    office_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("offices", "view")),
) -> OfficeResponse:
    return OfficeResponse.model_validate(_office_or_404(db, office_id))


@router.post("/offices", response_model=OfficeResponse, status_code=status.HTTP_201_CREATED)
def create_office(
    body: OfficeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("offices", "manage")),
) -> OfficeResponse:
    company = _company_or_404(db)
    if body.is_primary:
        for o in db.scalars(select(Office).where(Office.company_id == company.id)).all():
            o.is_primary = False
    office = Office(company_id=company.id, **body.model_dump())
    db.add(office)
    db.flush()
    cf_activity.record_office_created(db, company, user, office.office_name)
    db.commit()
    db.refresh(office)
    return OfficeResponse.model_validate(office)


@router.patch("/offices/{office_id}", response_model=OfficeResponse)
def update_office(
    office_id: UUID,
    body: OfficeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("offices", "manage")),
) -> OfficeResponse:
    company = _company_or_404(db)
    office = _office_or_404(db, office_id)
    if body.is_primary:
        for o in db.scalars(select(Office).where(Office.company_id == company.id)).all():
            o.is_primary = False
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(office, field, value)
    cf_activity.record_office_updated(db, company, user, office.office_name)
    db.commit()
    db.refresh(office)
    return OfficeResponse.model_validate(office)


@router.post("/offices/{office_id}/archive", response_model=OfficeResponse)
def archive_office_route(
    office_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("offices", "manage")),
) -> OfficeResponse:
    company = _company_or_404(db)
    office = archive_office(db, _office_or_404(db, office_id))
    cf_activity.record_office_archived(db, company, user, office.office_name)
    db.commit()
    db.refresh(office)
    return OfficeResponse.model_validate(office)


@router.get("/brands", response_model=list[BrandProfileResponse])
def list_brands(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("brand", "view")),
) -> list[BrandProfileResponse]:
    company = _company_or_404(db)
    query = select(BrandProfile).where(BrandProfile.company_id == company.id)
    if not include_archived:
        query = query.where(BrandProfile.archived_at.is_(None))
    brands = db.scalars(query.order_by(BrandProfile.brand_name)).all()
    return [BrandProfileResponse.model_validate(b) for b in brands]


@router.get("/brands/{brand_id}", response_model=BrandProfileResponse)
def get_brand(
    brand_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("brand", "view")),
) -> BrandProfileResponse:
    return BrandProfileResponse.model_validate(_brand_or_404(db, brand_id))


@router.post("/brands", response_model=BrandProfileResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    body: BrandProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand", "manage")),
) -> BrandProfileResponse:
    company = _company_or_404(db)
    if body.is_default:
        for b in db.scalars(select(BrandProfile).where(BrandProfile.company_id == company.id)).all():
            b.is_default = False
    brand = BrandProfile(company_id=company.id, **body.model_dump())
    db.add(brand)
    db.flush()
    cf_activity.record_brand_created(db, company, user, brand.brand_name)
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.patch("/brands/{brand_id}", response_model=BrandProfileResponse)
def update_brand(
    brand_id: UUID,
    body: BrandProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand", "manage")),
) -> BrandProfileResponse:
    company = _company_or_404(db)
    brand = _brand_or_404(db, brand_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    cf_activity.record_brand_updated(db, company, user, brand.brand_name)
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.post("/brands/{brand_id}/set-default", response_model=BrandProfileResponse)
def set_default_brand_route(
    brand_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand", "manage")),
) -> BrandProfileResponse:
    company = _company_or_404(db)
    brand = set_default_brand(db, brand_id, company.id)
    cf_activity.record_default_brand_changed(db, company, user, brand.brand_name)
    create_notification(
        db,
        recipient_user_id=user.id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="notifications.company.default_brand_changed.title",
        message_key="notifications.company.default_brand_changed.message",
        rule_key="company.default_brand_changed",
        related_entity_type="brand",
        related_entity_id=brand.id,
        metadata={"brand_name": brand.brand_name},
        source=NotificationSource.USER,
    )
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.post("/brands/{brand_id}/archive", response_model=BrandProfileResponse)
def archive_brand_route(
    brand_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand", "manage")),
) -> BrandProfileResponse:
    brand = archive_brand(db, _brand_or_404(db, brand_id))
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.get("/brands/{brand_id}/assets", response_model=list[BrandAssetResponse])
def list_brand_assets(
    brand_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("brand", "view")),
) -> list[BrandAssetResponse]:
    _brand_or_404(db, brand_id)
    assets = db.scalars(
        select(BrandAsset)
        .where(BrandAsset.brand_profile_id == brand_id, BrandAsset.archived_at.is_(None))
        .order_by(BrandAsset.created_at.desc())
    ).all()
    return [BrandAssetResponse.model_validate(a) for a in assets]


@router.post("/brands/{brand_id}/assets", response_model=BrandAssetResponse, status_code=status.HTTP_201_CREATED)
def link_brand_asset(
    brand_id: UUID,
    body: BrandAssetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand_assets", "manage_assets")),
) -> BrandAssetResponse:
    company = _company_or_404(db)
    brand = _brand_or_404(db, brand_id)
    document = db.get(Document, body.document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documents.errors.not_found")
    ext = document.file_extension.lower().lstrip(".")
    if ext in {"exe", "bat", "cmd", "sh", "ps1", "dll", "msi"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company.errors.executable_asset_forbidden")
    asset = BrandAsset(brand_profile_id=brand.id, **body.model_dump())
    db.add(asset)
    db.flush()
    cf_activity.record_brand_asset_linked(db, company, user, asset.title)
    db.commit()
    db.refresh(asset)
    return BrandAssetResponse.model_validate(asset)


@router.patch("/brand-assets/{asset_id}", response_model=BrandAssetResponse)
def update_brand_asset(
    asset_id: UUID,
    body: BrandAssetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand_assets", "manage_assets")),
) -> BrandAssetResponse:
    asset = db.get(BrandAsset, asset_id)
    if asset is None or asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.asset_not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return BrandAssetResponse.model_validate(asset)


@router.post("/brand-assets/{asset_id}/archive", response_model=BrandAssetResponse)
def archive_brand_asset_route(
    asset_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("brand_assets", "manage_assets")),
) -> BrandAssetResponse:
    asset = db.get(BrandAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.asset_not_found")
    asset = archive_brand_asset(db, asset)
    db.commit()
    db.refresh(asset)
    return BrandAssetResponse.model_validate(asset)


@router.get("/settings/preferences", response_model=SystemPreferencesResponse)
def get_preferences(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("settings", "view")),
) -> SystemPreferencesResponse:
    prefs = get_all_preferences(db)
    items = [_pref_response(p) for p in prefs]
    categories: dict[str, list[PreferenceItemResponse]] = {}
    for item in items:
        categories.setdefault(item.category, []).append(item)
    return SystemPreferencesResponse(items=items, categories=categories)


@router.patch("/settings/preferences", response_model=SystemPreferencesResponse)
def update_preferences_route(
    body: SystemPreferencesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings", "update")),
) -> SystemPreferencesResponse:
    company = _company_or_404(db)
    update_preferences(db, body.preferences)
    cf_activity.record_preferences_updated(db, company, user, list(body.preferences.keys()))
    db.commit()
    prefs = get_all_preferences(db)
    items = [_pref_response(p) for p in prefs]
    categories: dict[str, list[PreferenceItemResponse]] = {}
    for item in items:
        categories.setdefault(item.category, []).append(item)
    return SystemPreferencesResponse(items=items, categories=categories)


@router.get("/settings/supported-options", response_model=SupportedOptionsResponse)
def get_supported_options(
    _user: User = Depends(require_permission("settings", "view")),
) -> SupportedOptionsResponse:
    return SupportedOptionsResponse(**supported_options())


@router.get("/settings/providers", response_model=ProviderStatusListResponse)
def get_provider_status(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("settings", "view")),
) -> ProviderStatusListResponse:
    items = [ProviderStatusResponse(**p) for p in get_provider_statuses()]
    return ProviderStatusListResponse(items=items)


@router.get("/organization/departments", response_model=list[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("organization", "view")),
) -> list[DepartmentResponse]:
    company = _company_or_404(db)
    depts = db.scalars(select(Department).where(Department.company_id == company.id).order_by(Department.name)).all()
    return [DepartmentResponse.model_validate(d) for d in depts]


@router.post("/organization/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("organization", "manage")),
) -> DepartmentResponse:
    company = _company_or_404(db)
    dept = Department(company_id=company.id, **body.model_dump())
    db.add(dept)
    db.flush()
    cf_activity.record_department_created(db, company, user, dept.name)
    db.commit()
    db.refresh(dept)
    return DepartmentResponse.model_validate(dept)


@router.patch("/organization/departments/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: UUID,
    body: DepartmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("organization", "manage")),
) -> DepartmentResponse:
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.department_not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return DepartmentResponse.model_validate(dept)


@router.get("/organization/departments/{department_id}/teams", response_model=list[TeamResponse])
def list_teams(
    department_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("organization", "view")),
) -> list[TeamResponse]:
    teams = db.scalars(select(Team).where(Team.department_id == department_id).order_by(Team.name)).all()
    return [TeamResponse.model_validate(t) for t in teams]


@router.post("/organization/departments/{department_id}/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    department_id: UUID,
    body: TeamCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("organization", "manage")),
) -> TeamResponse:
    company = _company_or_404(db)
    if db.get(Department, department_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.department_not_found")
    team = Team(department_id=department_id, **body.model_dump())
    db.add(team)
    db.flush()
    cf_activity.record_team_created(db, company, user, team.name)
    db.commit()
    db.refresh(team)
    return TeamResponse.model_validate(team)


@router.patch("/organization/teams/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: UUID,
    body: TeamUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("organization", "manage")),
) -> TeamResponse:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company.errors.team_not_found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return TeamResponse.model_validate(team)


@router.post("/organization/users/{user_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
def assign_user_org(
    user_id: UUID,
    body: UserOrganizationAssignment,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("organization", "manage")),
) -> None:
    company = _company_or_404(db)
    assign_user_organization(
        db,
        user_id,
        department_id=body.department_id,
        team_id=body.team_id,
        is_primary_department=body.is_primary_department,
    )
    cf_activity.record_user_org_assignment(db, company, user, user_id)
    db.commit()
