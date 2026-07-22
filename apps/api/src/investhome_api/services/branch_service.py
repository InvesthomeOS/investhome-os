"""Branch management business logic."""

from __future__ import annotations

from math import ceil
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from investhome_api.models.branch import Branch, BranchStatus, BranchWorkingHours
from investhome_api.models.company import Company
from investhome_api.models.user_auth import User
from investhome_api.schemas.branch import (
    BranchCreate,
    BranchDetailResponse,
    BranchSummaryResponse,
    BranchUpdate,
    BranchWorkingHoursBase,
)
from investhome_api.services.permission_service import user_has_permission


SORTABLE_FIELDS = {
    "branch_code": Branch.branch_code,
    "branch_name": Branch.branch_name,
    "city": Branch.city,
    "country": Branch.country,
    "status": Branch.status,
    "created_at": Branch.created_at,
    "updated_at": Branch.updated_at,
}


def can_view_branch_sensitive(user: User | None) -> bool:
    if user is None:
        return False
    return user_has_permission(user, "branch", "update")


def _mask_sensitive_text(value: str | None) -> str | None:
    if not value:
        return value
    return "***"


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _build_maps_link(latitude: float | None, longitude: float | None, link: str | None) -> str | None:
    if link:
        return link
    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps?q={latitude},{longitude}"
    return None


def find_duplicate_address_warnings(db: Session, *, branch: Branch, exclude_id: UUID | None = None) -> list[str]:
    query = select(Branch.id, Branch.branch_code, Branch.branch_name).where(
        Branch.archived_at.is_(None),
        func.lower(Branch.full_address) == branch.full_address.strip().lower(),
        Branch.city == branch.city,
        Branch.country == branch.country,
    )
    if exclude_id:
        query = query.where(Branch.id != exclude_id)
    matches = db.execute(query).all()
    if not matches:
        return []
    labels = ", ".join(f"{row.branch_code} ({row.branch_name})" for row in matches[:3])
    return [f"branch.warnings.duplicate_address:{labels}"]


def compute_employee_count(db: Session, branch_id: UUID) -> int:
    del db, branch_id
    return 0


def _serialize_summary(
    branch: Branch,
    *,
    company_name: str | None = None,
    manager_name: str | None = None,
    employee_count: int = 0,
) -> BranchSummaryResponse:
    return BranchSummaryResponse(
        id=branch.id,
        branch_code=branch.branch_code,
        branch_name=branch.branch_name,
        company_id=branch.company_id,
        company_name=company_name,
        branch_type=branch.branch_type,
        country=branch.country,
        state=branch.state,
        city=branch.city,
        status=branch.status,
        manager_user_id=branch.manager_user_id,
        manager_name=manager_name,
        employee_count=employee_count,
        department_count=branch.department_count,
        opening_date=branch.opening_date,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )


def serialize_branch_detail(
    db: Session,
    branch: Branch,
    *,
    warnings: list[str] | None = None,
    user: User | None = None,
) -> BranchDetailResponse:
    company = db.get(Company, branch.company_id)
    manager_name = None
    if branch.manager_user_id:
        manager = db.get(User, branch.manager_user_id)
        manager_name = manager.full_name if manager else None
    summary = _serialize_summary(
        branch,
        company_name=company.company_name if company else None,
        manager_name=manager_name,
        employee_count=compute_employee_count(db, branch.id),
    )
    return BranchDetailResponse(
        **summary.model_dump(),
        district=branch.district,
        postal_code=branch.postal_code,
        full_address=branch.full_address,
        latitude=float(branch.latitude) if branch.latitude is not None else None,
        longitude=float(branch.longitude) if branch.longitude is not None else None,
        google_maps_link=_build_maps_link(
            float(branch.latitude) if branch.latitude is not None else None,
            float(branch.longitude) if branch.longitude is not None else None,
            branch.google_maps_link,
        ),
        timezone=branch.timezone,
        main_phone=branch.main_phone,
        mobile_phone=branch.mobile_phone,
        email=branch.email,
        website=branch.website,
        emergency_contact=branch.emergency_contact
        if can_view_branch_sensitive(user)
        else _mask_sensitive_text(branch.emergency_contact),
        notes=branch.notes,
        archived_at=branch.archived_at,
        working_hours=branch.working_hours,
        assets=list(branch.assets),
        documents=list(branch.documents),
        warnings=warnings or [],
    )


def _apply_working_hours(db: Session, branch: Branch, payload: BranchWorkingHoursBase | None) -> None:
    if payload is None:
        return
    if branch.working_hours is None:
        branch.working_hours = BranchWorkingHours(branch_id=branch.id)
        db.add(branch.working_hours)
    branch.working_hours.business_days = payload.business_days
    branch.working_hours.open_time = payload.open_time
    branch.working_hours.close_time = payload.close_time
    branch.working_hours.holidays = payload.holidays
    branch.working_hours.special_hours = payload.special_hours


def get_branch_or_none(db: Session, branch_id: UUID) -> Branch | None:
    return db.scalar(
        select(Branch)
        .options(
            joinedload(Branch.working_hours),
            joinedload(Branch.assets),
            joinedload(Branch.documents),
        )
        .where(Branch.id == branch_id)
    )


def list_branches(
    db: Session,
    *,
    search: str | None = None,
    company_id: UUID | None = None,
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    branch_type: str | None = None,
    status: str | None = None,
    manager_user_id: UUID | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[BranchSummaryResponse], int]:
    query = select(Branch, Company.company_name, User.full_name).join(
        Company, Branch.company_id == Company.id
    ).outerjoin(User, Branch.manager_user_id == User.id)

    if not include_archived:
        query = query.where(Branch.archived_at.is_(None))
    if company_id:
        query = query.where(Branch.company_id == company_id)
    if country:
        query = query.where(func.lower(Branch.country) == country.strip().lower())
    if state:
        query = query.where(func.lower(Branch.state) == state.strip().lower())
    if city:
        query = query.where(func.lower(Branch.city) == city.strip().lower())
    if branch_type:
        query = query.where(Branch.branch_type == branch_type)
    if status:
        query = query.where(Branch.status == status)
    if manager_user_id:
        query = query.where(Branch.manager_user_id == manager_user_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Branch.branch_name.ilike(pattern),
                Branch.branch_code.ilike(pattern),
                Branch.city.ilike(pattern),
                Branch.country.ilike(pattern),
                Company.company_name.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    sort_column = SORTABLE_FIELDS.get(sort_by, Branch.updated_at)
    order = desc(sort_column) if sort_dir.lower() == "desc" else asc(sort_column)
    query = query.order_by(order).offset((page - 1) * page_size).limit(page_size)

    items: list[BranchSummaryResponse] = []
    for branch, company_name, manager_name in db.execute(query).all():
        items.append(
            _serialize_summary(
                branch,
                company_name=company_name,
                manager_name=manager_name,
                employee_count=compute_employee_count(db, branch.id),
            )
        )
    return items, total


def create_branch(db: Session, payload: BranchCreate) -> tuple[Branch, list[str]]:
    company = db.get(Company, payload.company_id)
    if company is None:
        raise ValueError("branch.errors.company_not_found")

    existing = db.scalar(select(Branch.id).where(Branch.branch_code == _normalize_code(payload.branch_code)))
    if existing:
        raise ValueError("branch.errors.duplicate_code")

    data = payload.model_dump(exclude={"working_hours"})
    data["branch_code"] = _normalize_code(data["branch_code"])
    if data.get("google_maps_link") is None:
        data["google_maps_link"] = _build_maps_link(data.get("latitude"), data.get("longitude"), None)

    branch = Branch(**data)
    db.add(branch)
    db.flush()
    _apply_working_hours(db, branch, payload.working_hours)
    warnings = find_duplicate_address_warnings(db, branch=branch)
    return branch, warnings


def update_branch(db: Session, branch: Branch, payload: BranchUpdate) -> tuple[Branch, list[str]]:
    data = payload.model_dump(exclude_unset=True, exclude={"working_hours"})
    if "branch_code" in data:
        normalized = _normalize_code(data["branch_code"])
        existing = db.scalar(
            select(Branch.id).where(Branch.branch_code == normalized, Branch.id != branch.id)
        )
        if existing:
            raise ValueError("branch.errors.duplicate_code")
        data["branch_code"] = normalized
    if "company_id" in data and db.get(Company, data["company_id"]) is None:
        raise ValueError("branch.errors.company_not_found")

    for key, value in data.items():
        setattr(branch, key, value)

    if branch.google_maps_link is None and (branch.latitude is not None and branch.longitude is not None):
        branch.google_maps_link = _build_maps_link(
            float(branch.latitude) if branch.latitude is not None else None,
            float(branch.longitude) if branch.longitude is not None else None,
            None,
        )

    _apply_working_hours(db, branch, payload.working_hours)
    warnings = find_duplicate_address_warnings(db, branch=branch, exclude_id=branch.id)
    return branch, warnings


def duplicate_branch(db: Session, branch: Branch) -> Branch:
    suffix = 1
    base_code = branch.branch_code
    while True:
        candidate = f"{base_code}-COPY{suffix if suffix > 1 else ''}"
        if not db.scalar(select(Branch.id).where(Branch.branch_code == candidate)):
            break
        suffix += 1

    clone = Branch(
        branch_code=candidate,
        branch_name=f"{branch.branch_name} (Copy)",
        company_id=branch.company_id,
        branch_type=branch.branch_type,
        country=branch.country,
        state=branch.state,
        city=branch.city,
        district=branch.district,
        postal_code=branch.postal_code,
        full_address=branch.full_address,
        latitude=branch.latitude,
        longitude=branch.longitude,
        google_maps_link=branch.google_maps_link,
        timezone=branch.timezone,
        main_phone=branch.main_phone,
        mobile_phone=branch.mobile_phone,
        email=branch.email,
        website=branch.website,
        emergency_contact=branch.emergency_contact,
        status=BranchStatus.PLANNING.value,
        opening_date=branch.opening_date,
        department_count=branch.department_count,
        notes=branch.notes,
    )
    db.add(clone)
    db.flush()
    if branch.working_hours:
        db.add(
            BranchWorkingHours(
                branch_id=clone.id,
                business_days=branch.working_hours.business_days,
                open_time=branch.working_hours.open_time,
                close_time=branch.working_hours.close_time,
                holidays=branch.working_hours.holidays,
                special_hours=branch.working_hours.special_hours,
            )
        )
    return clone


def paginate_total_pages(total: int, page_size: int) -> int:
    return max(1, ceil(total / page_size))
