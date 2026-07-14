from datetime import UTC, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.models.investor import (
    InvestmentModel,
    Investor,
    InvestorStatus,
    InvestorType,
)
from investhome_api.schemas.investor import (
    InvestorCreate,
    InvestorListResponse,
    InvestorResponse,
    InvestorStatsResponse,
    InvestorUpdate,
)

router = APIRouter(prefix="/investors", tags=["investors"])

SORTABLE_FIELDS = {
    "full_name": Investor.full_name,
    "country": Investor.country,
    "investor_type": Investor.investor_type,
    "status": Investor.status,
    "investment_capacity": Investor.investment_capacity,
    "preferred_investment_model": Investor.preferred_investment_model,
    "assigned_to": Investor.assigned_to,
    "last_contact_date": Investor.last_contact_date,
    "next_follow_up_date": Investor.next_follow_up_date,
    "updated_at": Investor.updated_at,
    "created_at": Investor.created_at,
}


def _get_investor_or_404(
    investor_id: UUID,
    db: Session,
    *,
    include_archived: bool = False,
) -> Investor:
    investor = db.get(Investor, investor_id)
    if investor is None or (investor.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investor not found")
    return investor


def _apply_filters(
    query,
    *,
    search: str | None,
    status_filter: InvestorStatus | None,
    investor_type: InvestorType | None,
    country: str | None,
    investment_model: InvestmentModel | None,
    include_archived: bool,
):
    if not include_archived:
        query = query.where(Investor.archived_at.is_(None))

    if status_filter is not None:
        query = query.where(Investor.status == status_filter)

    if investor_type is not None:
        query = query.where(Investor.investor_type == investor_type)

    if country:
        query = query.where(Investor.country == country)

    if investment_model is not None:
        query = query.where(Investor.preferred_investment_model == investment_model)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Investor.full_name.ilike(pattern),
                Investor.email.ilike(pattern),
                Investor.phone.ilike(pattern),
                Investor.city.ilike(pattern),
                Investor.preferred_markets.ilike(pattern),
                Investor.preferred_projects.ilike(pattern),
            )
        )

    return query


@router.get("/stats", response_model=InvestorStatsResponse)
def get_investor_stats(db: Session = Depends(get_db)) -> InvestorStatsResponse:
    base = select(Investor).where(Investor.archived_at.is_(None))
    investors = db.scalars(base).all()

    total_capacity = sum(
        (inv.investment_capacity or Decimal("0")) for inv in investors
    )

    return InvestorStatsResponse(
        total=len(investors),
        active=sum(1 for inv in investors if inv.status == InvestorStatus.ACTIVE),
        invested=sum(1 for inv in investors if inv.status == InvestorStatus.INVESTED),
        total_investment_capacity=total_capacity,
    )


@router.get("", response_model=InvestorListResponse)
def list_investors(
    search: str | None = Query(default=None, max_length=255),
    status_filter: InvestorStatus | None = Query(default=None, alias="status"),
    investor_type: InvestorType | None = None,
    country: str | None = Query(default=None, max_length=100),
    investment_model: InvestmentModel | None = Query(
        default=None,
        alias="preferred_investment_model",
    ),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> InvestorListResponse:
    sort_column = SORTABLE_FIELDS.get(sort_by, Investor.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(Investor)
    query = _apply_filters(
        query,
        search=search,
        status_filter=status_filter,
        investor_type=investor_type,
        country=country,
        investment_model=investment_model,
        include_archived=include_archived,
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    query = query.order_by(order_fn(sort_column))
    offset = (page - 1) * page_size
    investors = db.scalars(query.offset(offset).limit(page_size)).all()

    pages = ceil(total / page_size) if total else 0

    return InvestorListResponse(
        items=[InvestorResponse.model_validate(investor) for investor in investors],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{investor_id}", response_model=InvestorResponse)
def get_investor(investor_id: UUID, db: Session = Depends(get_db)) -> InvestorResponse:
    investor = _get_investor_or_404(investor_id, db)
    return InvestorResponse.model_validate(investor)


@router.post("", response_model=InvestorResponse, status_code=status.HTTP_201_CREATED)
def create_investor(payload: InvestorCreate, db: Session = Depends(get_db)) -> InvestorResponse:
    investor = Investor(**payload.model_dump())
    db.add(investor)
    db.commit()
    db.refresh(investor)
    return InvestorResponse.model_validate(investor)


@router.patch("/{investor_id}", response_model=InvestorResponse)
def update_investor(
    investor_id: UUID,
    payload: InvestorUpdate,
    db: Session = Depends(get_db),
) -> InvestorResponse:
    investor = _get_investor_or_404(investor_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    for field, value in updates.items():
        setattr(investor, field, value)

    investor.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(investor)
    return InvestorResponse.model_validate(investor)


@router.delete("/{investor_id}", response_model=InvestorResponse)
def archive_investor(investor_id: UUID, db: Session = Depends(get_db)) -> InvestorResponse:
    investor = _get_investor_or_404(investor_id, db)

    if investor.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investor is already archived",
        )

    investor.archived_at = datetime.now(UTC)
    investor.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(investor)
    return InvestorResponse.model_validate(investor)
