"""Companies management service — CRUD, validation, import/export."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.company import (
    Company,
    CompanyAddress,
    CompanyBankAccount,
    CompanyContact,
    CompanyDocument,
    CompanyEntityType,
    CompanyRelationship,
    CompanyRelationshipType,
    CompanyStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.company_management import (
    CompanyAddressCreate,
    CompanyBankAccountCreate,
    CompanyContactCreate,
    CompanyCreate,
    CompanyDocumentCreate,
    CompanyImportResult,
    CompanyListItem,
    CompanyListResponse,
    CompanyRelationshipCreate,
    CompanyResponse,
    CompanyUpdate,
)
from investhome_api.services.permission_service import user_has_permission

SORTABLE_FIELDS = {
    "company_name": Company.company_name,
    "legal_name": Company.legal_name,
    "entity_type": Company.entity_type,
    "registration_number": Company.registration_number,
    "tax_id": Company.tax_id,
    "country": Company.country,
    "state": Company.state,
    "city": Company.city,
    "status": Company.status,
    "employee_count": Company.employee_count,
    "branch_count": Company.branch_count,
    "created_at": Company.created_at,
    "updated_at": Company.updated_at,
}

REQUIRED_FIELDS_BY_ENTITY: dict[str, list[str]] = {
    CompanyEntityType.CORPORATION.value: ["legal_name", "registration_number", "country"],
    CompanyEntityType.LLC.value: ["legal_name", "registration_number"],
    CompanyEntityType.TRUST.value: ["legal_name", "country"],
    CompanyEntityType.BRANCH.value: ["country", "city"],
}

COUNTRY_TAX_ID_STUBS: dict[str, str] = {
    "TR": r"^\d{10,11}$",
    "US": r"^\d{2}-\d{7}$",
}


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _check_duplicate(
    db: Session,
    *,
    field: str,
    value: str | None,
    exclude_id: UUID | None = None,
) -> None:
    if not value:
        return
    column = getattr(Company, field)
    query = select(Company.id).where(column == value, Company.archived_at.is_(None))
    if exclude_id:
        query = query.where(Company.id != exclude_id)
    if db.scalar(query):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A company with this {field.replace('_', ' ')} already exists",
        )


def validate_company_fields(
    *,
    entity_type: str,
    legal_name: str | None,
    registration_number: str | None,
    tax_id: str | None,
    country: str | None,
    city: str | None,
) -> None:
    required = REQUIRED_FIELDS_BY_ENTITY.get(entity_type, [])
    values = {
        "legal_name": legal_name,
        "registration_number": registration_number,
        "tax_id": tax_id,
        "country": country,
        "city": city,
    }
    missing = [field for field in required if not values.get(field)]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required fields for entity type: {', '.join(missing)}",
        )

    if country and tax_id and country.upper() in COUNTRY_TAX_ID_STUBS:
        import re

        pattern = COUNTRY_TAX_ID_STUBS[country.upper()]
        if not re.match(pattern, tax_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tax ID format is invalid for country {country}",
            )


def mask_account_number(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 4:
        return "****"
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def can_view_full_bank_details(user: User | None) -> bool:
    if user is None:
        return False
    return user_has_permission(user, "finance", "view") or user_has_permission(user, "company", "update")


def _apply_child_records(
    db: Session,
    company: Company,
    *,
    addresses: list[CompanyAddressCreate] | None = None,
    contacts: list[CompanyContactCreate] | None = None,
    bank_accounts: list[CompanyBankAccountCreate] | None = None,
    documents: list[CompanyDocumentCreate] | None = None,
    relationships: list[CompanyRelationshipCreate] | None = None,
    replace: bool = False,
) -> None:
    if replace:
        company.addresses.clear()
        company.contacts.clear()
        company.bank_accounts.clear()
        company.documents.clear()
        company.relationships_from.clear()
        db.flush()

    if addresses is not None:
        for item in addresses:
            company.addresses.append(
                CompanyAddress(
                    address_type=item.address_type.value,
                    address_line_1=item.address_line_1,
                    address_line_2=item.address_line_2,
                    city=item.city,
                    state=item.state,
                    country=item.country,
                    postal_code=item.postal_code,
                    is_primary=item.is_primary,
                )
            )

    if contacts is not None:
        for item in contacts:
            company.contacts.append(
                CompanyContact(
                    role=item.role.value,
                    full_name=item.full_name,
                    email=item.email,
                    phone=item.phone,
                    is_signatory=item.is_signatory,
                )
            )

    if bank_accounts is not None:
        for item in bank_accounts:
            company.bank_accounts.append(
                CompanyBankAccount(
                    bank_name=item.bank_name,
                    account_name=item.account_name,
                    account_number=item.account_number,
                    iban=item.iban,
                    routing_number=item.routing_number,
                    currency=item.currency,
                    is_primary=item.is_primary,
                )
            )

    if documents is not None:
        for item in documents:
            company.documents.append(
                CompanyDocument(
                    document_id=item.document_id,
                    title=item.title,
                    reference_code=item.reference_code,
                    notes=item.notes,
                )
            )

    if relationships is not None:
        for item in relationships:
            if item.related_company_id == company.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A company cannot relate to itself",
                )
            company.relationships_from.append(
                CompanyRelationship(
                    related_company_id=item.related_company_id,
                    relationship_type=item.relationship_type.value,
                    notes=item.notes,
                )
            )


def _refresh_branch_count(db: Session, company: Company) -> None:
    count = db.scalar(
        select(func.count())
        .select_from(CompanyRelationship)
        .where(
            CompanyRelationship.company_id == company.id,
            CompanyRelationship.relationship_type == CompanyRelationshipType.BRANCH.value,
        )
    )
    company.branch_count = count or 0


def _owner_name(db: Session, owner_user_id: UUID | None) -> str | None:
    if not owner_user_id:
        return None
    user = db.get(User, owner_user_id)
    return user.full_name if user else None


def serialize_company(
    db: Session,
    company: Company,
    *,
    user: User | None = None,
    include_children: bool = False,
) -> CompanyResponse | CompanyListItem:
    owner_name = _owner_name(db, company.owner_user_id)
    base = {
        "id": company.id,
        "logo_document_id": company.logo_document_id,
        "company_name": company.company_name,
        "legal_name": company.legal_name,
        "entity_type": company.entity_type,
        "registration_number": company.registration_number,
        "tax_id": company.tax_id,
        "country": company.country,
        "state": company.state,
        "city": company.city,
        "status": company.status,
        "industry": company.industry,
        "owner_user_id": company.owner_user_id,
        "owner_name": owner_name,
        "employee_count": company.employee_count,
        "branch_count": company.branch_count,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "archived_at": company.archived_at,
    }
    if not include_children:
        return CompanyListItem.model_validate(base)

    show_bank = can_view_full_bank_details(user)
    bank_accounts = []
    for account in company.bank_accounts:
        data = {
            "id": account.id,
            "bank_name": account.bank_name,
            "account_name": account.account_name,
            "account_number": account.account_number if show_bank else mask_account_number(account.account_number),
            "iban": account.iban if show_bank else mask_account_number(account.iban),
            "routing_number": account.routing_number if show_bank else mask_account_number(account.routing_number),
            "currency": account.currency,
            "is_primary": account.is_primary,
            "created_at": account.created_at,
            "updated_at": account.updated_at,
        }
        bank_accounts.append(data)

    relationships = []
    for rel in company.relationships_from:
        related = db.get(Company, rel.related_company_id)
        relationships.append(
            {
                "id": rel.id,
                "related_company_id": rel.related_company_id,
                "related_company_name": related.company_name if related else None,
                "relationship_type": rel.relationship_type,
                "notes": rel.notes,
                "created_at": rel.created_at,
            }
        )

    return CompanyResponse.model_validate(
        {
            **base,
            "notes": company.notes,
            "addresses": company.addresses,
            "contacts": company.contacts,
            "bank_accounts": bank_accounts,
            "documents": company.documents,
            "relationships": relationships,
        }
    )


def get_company_or_404(db: Session, company_id: UUID, *, include_archived: bool = False) -> Company:
    query = (
        select(Company)
        .options(
            selectinload(Company.addresses),
            selectinload(Company.contacts),
            selectinload(Company.bank_accounts),
            selectinload(Company.documents),
            selectinload(Company.relationships_from),
        )
        .where(Company.id == company_id)
    )
    if not include_archived:
        query = query.where(Company.archived_at.is_(None))
    company = db.scalar(query)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def list_companies(
    db: Session,
    *,
    search: str | None = None,
    status_filter: CompanyStatus | None = None,
    country: str | None = None,
    entity_type: CompanyEntityType | None = None,
    owner_user_id: UUID | None = None,
    industry: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> CompanyListResponse:
    query = select(Company)
    if not include_archived:
        query = query.where(Company.archived_at.is_(None))
    if status_filter is not None:
        query = query.where(Company.status == status_filter.value)
    if country:
        query = query.where(Company.country == country)
    if entity_type is not None:
        query = query.where(Company.entity_type == entity_type.value)
    if owner_user_id:
        query = query.where(Company.owner_user_id == owner_user_id)
    if industry:
        query = query.where(Company.industry.ilike(f"%{industry.strip()}%"))
    if created_from:
        query = query.where(Company.created_at >= created_from)
    if created_to:
        query = query.where(Company.created_at <= created_to)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Company.company_name.ilike(pattern),
                Company.legal_name.ilike(pattern),
                Company.registration_number.ilike(pattern),
                Company.tax_id.ilike(pattern),
                Company.city.ilike(pattern),
                Company.country.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    sort_column = SORTABLE_FIELDS.get(sort_by, Company.updated_at)
    order_fn = asc if sort_order == "asc" else desc
    query = query.order_by(order_fn(sort_column))
    offset = (page - 1) * page_size
    companies = db.scalars(query.offset(offset).limit(page_size)).all()

    return CompanyListResponse(
        items=[serialize_company(db, company) for company in companies],  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def create_company(db: Session, payload: CompanyCreate) -> Company:
    legal_name = _normalize(payload.legal_name)
    registration_number = _normalize(payload.registration_number)
    tax_id = _normalize(payload.tax_id)
    country = _normalize(payload.country)
    city = _normalize(payload.city)

    _check_duplicate(db, field="legal_name", value=legal_name)
    _check_duplicate(db, field="registration_number", value=registration_number)
    _check_duplicate(db, field="tax_id", value=tax_id)
    validate_company_fields(
        entity_type=payload.entity_type.value,
        legal_name=legal_name,
        registration_number=registration_number,
        tax_id=tax_id,
        country=country,
        city=city,
    )

    company = Company(
        company_name=payload.company_name.strip(),
        legal_name=legal_name,
        entity_type=payload.entity_type.value,
        registration_number=registration_number,
        tax_id=tax_id,
        country=country,
        state=_normalize(payload.state),
        city=city,
        status=payload.status.value,
        industry=_normalize(payload.industry),
        owner_user_id=payload.owner_user_id,
        logo_document_id=payload.logo_document_id,
        notes=payload.notes,
    )
    db.add(company)
    db.flush()
    _apply_child_records(
        db,
        company,
        addresses=payload.addresses,
        contacts=payload.contacts,
        bank_accounts=payload.bank_accounts,
        documents=payload.documents,
        relationships=payload.relationships,
    )
    _refresh_branch_count(db, company)
    db.flush()
    return company


def update_company(db: Session, company: Company, payload: CompanyUpdate) -> Company:
    legal_name = _normalize(payload.legal_name) if payload.legal_name is not None else company.legal_name
    registration_number = (
        _normalize(payload.registration_number)
        if payload.registration_number is not None
        else company.registration_number
    )
    tax_id = _normalize(payload.tax_id) if payload.tax_id is not None else company.tax_id
    country = _normalize(payload.country) if payload.country is not None else company.country
    city = _normalize(payload.city) if payload.city is not None else company.city
    entity_type = payload.entity_type.value if payload.entity_type is not None else company.entity_type

    _check_duplicate(db, field="legal_name", value=legal_name, exclude_id=company.id)
    _check_duplicate(db, field="registration_number", value=registration_number, exclude_id=company.id)
    _check_duplicate(db, field="tax_id", value=tax_id, exclude_id=company.id)
    validate_company_fields(
        entity_type=entity_type,
        legal_name=legal_name,
        registration_number=registration_number,
        tax_id=tax_id,
        country=country,
        city=city,
    )

    if payload.company_name is not None:
        company.company_name = payload.company_name.strip()
    company.legal_name = legal_name
    company.registration_number = registration_number
    company.tax_id = tax_id
    company.country = country
    company.city = city
    company.entity_type = entity_type
    if payload.state is not None:
        company.state = _normalize(payload.state)
    if payload.status is not None:
        company.status = payload.status.value
    if payload.industry is not None:
        company.industry = _normalize(payload.industry)
    if payload.owner_user_id is not None:
        company.owner_user_id = payload.owner_user_id
    if payload.logo_document_id is not None:
        company.logo_document_id = payload.logo_document_id
    if payload.notes is not None:
        company.notes = payload.notes

    if any(
        value is not None
        for value in (
            payload.addresses,
            payload.contacts,
            payload.bank_accounts,
            payload.documents,
            payload.relationships,
        )
    ):
        _apply_child_records(
            db,
            company,
            addresses=payload.addresses,
            contacts=payload.contacts,
            bank_accounts=payload.bank_accounts,
            documents=payload.documents,
            relationships=payload.relationships,
            replace=True,
        )
    _refresh_branch_count(db, company)
    db.flush()
    return company


def archive_company(db: Session, company: Company) -> Company:
    company.status = CompanyStatus.ARCHIVED.value
    company.archived_at = datetime.now(UTC)
    db.flush()
    return company


def deactivate_company(db: Session, company: Company) -> Company:
    company.status = CompanyStatus.INACTIVE.value
    db.flush()
    return company


def delete_company(db: Session, company: Company) -> None:
    company.archived_at = datetime.now(UTC)
    company.status = CompanyStatus.ARCHIVED.value
    db.flush()


def duplicate_company(db: Session, company: Company) -> Company:
    suffix = " (Copy)"
    clone = Company(
        company_name=f"{company.company_name}{suffix}",
        legal_name=f"{company.legal_name}{suffix}" if company.legal_name else None,
        entity_type=company.entity_type,
        registration_number=None,
        tax_id=None,
        country=company.country,
        state=company.state,
        city=company.city,
        status=CompanyStatus.DRAFT.value,
        industry=company.industry,
        owner_user_id=company.owner_user_id,
        notes=company.notes,
    )
    db.add(clone)
    db.flush()

    for address in company.addresses:
        clone.addresses.append(
            CompanyAddress(
                address_type=address.address_type,
                address_line_1=address.address_line_1,
                address_line_2=address.address_line_2,
                city=address.city,
                state=address.state,
                country=address.country,
                postal_code=address.postal_code,
                is_primary=address.is_primary,
            )
        )
    for contact in company.contacts:
        clone.contacts.append(
            CompanyContact(
                role=contact.role,
                full_name=contact.full_name,
                email=contact.email,
                phone=contact.phone,
                is_signatory=contact.is_signatory,
            )
        )
    db.flush()
    return clone


def transfer_ownership(db: Session, company: Company, owner_user_id: UUID) -> Company:
    owner = db.get(User, owner_user_id)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Owner user not found")
    company.owner_user_id = owner_user_id
    db.flush()
    return company


def export_companies_csv(db: Session, *, include_archived: bool = False) -> str:
    query = select(Company)
    if not include_archived:
        query = query.where(Company.archived_at.is_(None))
    companies = db.scalars(query.order_by(Company.company_name)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "company_name",
            "legal_name",
            "entity_type",
            "registration_number",
            "tax_id",
            "country",
            "state",
            "city",
            "status",
            "industry",
            "employee_count",
            "branch_count",
            "created_at",
        ]
    )
    for company in companies:
        writer.writerow(
            [
                company.company_name,
                company.legal_name or "",
                company.entity_type,
                company.registration_number or "",
                company.tax_id or "",
                company.country or "",
                company.state or "",
                company.city or "",
                company.status,
                company.industry or "",
                company.employee_count,
                company.branch_count,
                company.created_at.isoformat(),
            ]
        )
    return output.getvalue()


def import_companies_csv(db: Session, content: str) -> CompanyImportResult:
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    skipped = 0
    errors: list[str] = []

    for index, row in enumerate(reader, start=2):
        name = (row.get("company_name") or "").strip()
        if not name:
            skipped += 1
            errors.append(f"Row {index}: missing company_name")
            continue
        try:
            payload = CompanyCreate(
                company_name=name,
                legal_name=row.get("legal_name") or None,
                entity_type=CompanyEntityType(row.get("entity_type") or CompanyEntityType.OTHER.value),
                registration_number=row.get("registration_number") or None,
                tax_id=row.get("tax_id") or None,
                country=row.get("country") or None,
                state=row.get("state") or None,
                city=row.get("city") or None,
                status=CompanyStatus(row.get("status") or CompanyStatus.DRAFT.value),
                industry=row.get("industry") or None,
            )
            create_company(db, payload)
            imported += 1
        except HTTPException as exc:
            skipped += 1
            errors.append(f"Row {index}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            errors.append(f"Row {index}: {exc}")

    return CompanyImportResult(imported=imported, skipped=skipped, errors=errors[:20])
