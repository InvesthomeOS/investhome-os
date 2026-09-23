"""CRM Company management service — CRUD, hierarchy, merge, import/export."""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_company import (
    CrmCompany,
    CrmCompanyAddress,
    CrmCompanyBrokerageProfile,
    CrmCompanyContact,
    CrmCompanyFinancialProfile,
    CrmCompanyInvestmentProfile,
    CrmCompanyLawFirmProfile,
    CrmCompanyLenderProfile,
    CrmCompanyPropertyManagementProfile,
    CrmCompanyRelationship,
    CrmCompanyRelationshipLinkStatus,
    CrmCompanySavedView,
    CrmCompanyStatus,
    CrmCompanyType,
    CrmCompanyTypeAssignment,
    CrmCompanyVendorProfile,
)
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_companies import (
    CrmCompanyCounts,
    CrmCompanyAddressCreate,
    CrmCompanyBrokerageProfileSchema,
    CrmCompanyBulkActionResponse,
    CrmCompanyContactCreate,
    CrmCompanyContactUpdate,
    CrmCompanyCreate,
    CrmCompanyDetail,
    CrmCompanyDuplicateCandidate,
    CrmCompanyFinancialProfileSchema,
    CrmCompanyHierarchyNode,
    CrmCompanyHierarchyResponse,
    CrmCompanyImportResult,
    CrmCompanyInvestmentProfileSchema,
    CrmCompanyLawFirmProfileSchema,
    CrmCompanyLenderProfileSchema,
    CrmCompanyListItem,
    CrmCompanyListResponse,
    CrmCompanyRelatedAgreement,
    CrmCompanyRelatedPerson,
    CrmCompanyMergeResponse,
    CrmCompanyPropertyManagementProfileSchema,
    CrmCompanyRelationshipCreate,
    CrmCompanySavedViewCreate,
    CrmCompanySavedViewResponse,
    CrmCompanyStatusEnum,
    CrmCompanyTypeEnum,
    CrmCompanyUpdate,
    CrmCompanyVendorProfileSchema,
)
from investhome_api.services.permission_service import user_has_permission

SORTABLE_FIELDS = {
    "display_name": CrmCompany.display_name,
    "legal_name": CrmCompany.legal_name,
    "company_type": CrmCompany.company_type,
    "status": CrmCompany.status,
    "lifecycle_stage": CrmCompany.lifecycle_stage,
    "industry": CrmCompany.industry,
    "primary_email": CrmCompany.primary_email,
    "created_at": CrmCompany.created_at,
    "updated_at": CrmCompany.updated_at,
}

DUPLICATE_FIELDS = ["legal_name", "ein", "registration_number", "domain", "primary_email"]


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_email(value: str | None) -> str | None:
    normalized = _normalize(value)
    return normalized.lower() if normalized else None


def normalize_domain(value: str | None) -> str | None:
    normalized = _normalize(value)
    if not normalized:
        return None
    normalized = normalized.lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = re.sub(r"^www\.", "", normalized)
    return normalized.split("/")[0] or None


def normalize_phone(value: str | None) -> str | None:
    normalized = _normalize(value)
    if not normalized:
        return None
    return re.sub(r"[^\d+]", "", normalized)


def can_view_legal(user: User | None) -> bool:
    if user is None:
        return True
    return user_has_permission(user, "crm", "view_legal")


def can_view_financial(user: User | None) -> bool:
    if user is None:
        return True
    return user_has_permission(user, "crm", "view_financial")


def can_view_compliance(user: User | None) -> bool:
    if user is None:
        return True
    return user_has_permission(user, "crm", "view_compliance")


def _check_duplicate(
    db: Session,
    *,
    field: str,
    value: str | None,
    exclude_id: UUID | None = None,
) -> None:
    if not value:
        return
    column = getattr(CrmCompany, field)
    query = select(CrmCompany.id).where(column == value, CrmCompany.archived_at.is_(None))
    if exclude_id:
        query = query.where(CrmCompany.id != exclude_id)
    if db.scalar(query):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A CRM company with this {field.replace('_', ' ')} already exists",
        )


def _validate_parent(db: Session, company: CrmCompany, parent_id: UUID | None) -> None:
    if parent_id is None:
        return
    if parent_id == company.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Circular hierarchy")
    parent = db.get(CrmCompany, parent_id)
    if parent is None or parent.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent company not found")
    current_id = parent.parent_company_id
    visited = {parent_id, company.id}
    while current_id:
        if current_id in visited:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Circular hierarchy")
        visited.add(current_id)
        ancestor = db.get(CrmCompany, current_id)
        if ancestor is None:
            break
        current_id = ancestor.parent_company_id


def _apply_type_assignments(
    db: Session,
    company: CrmCompany,
    primary_type: CrmCompanyType,
    company_types: list[CrmCompanyType] | None,
    *,
    replace: bool = False,
) -> None:
    if replace:
        company.type_assignments.clear()
        db.flush()
    types = company_types or [primary_type]
    if primary_type not in types:
        types = [primary_type, *types]
    for idx, ctype in enumerate(types):
        company.type_assignments.append(
            CrmCompanyTypeAssignment(
                company_type=ctype,
                is_primary=(ctype == primary_type),
            )
        )


def _apply_addresses(
    company: CrmCompany,
    addresses: list[CrmCompanyAddressCreate] | None,
    *,
    replace: bool = False,
) -> None:
    if addresses is None:
        return
    if replace:
        company.addresses.clear()
    for item in addresses:
        company.addresses.append(
            CrmCompanyAddress(
                address_type=item.address_type.value,
                address_line1=item.address_line1,
                address_line2=item.address_line2,
                city=item.city,
                state_province=item.state_province,
                postal_code=item.postal_code,
                country=item.country,
                is_primary=item.is_primary,
            )
        )


def _apply_profile(db: Session, company: CrmCompany, payload: CrmCompanyCreate | CrmCompanyUpdate) -> None:
    profile_map = [
        ("financial_profile", CrmCompanyFinancialProfile),
        ("investment_profile", CrmCompanyInvestmentProfile),
        ("brokerage_profile", CrmCompanyBrokerageProfile),
        ("lender_profile", CrmCompanyLenderProfile),
        ("vendor_profile", CrmCompanyVendorProfile),
        ("law_firm_profile", CrmCompanyLawFirmProfile),
        ("property_management_profile", CrmCompanyPropertyManagementProfile),
    ]
    data = payload.model_dump(exclude_unset=isinstance(payload, CrmCompanyUpdate))
    for attr, model_cls in profile_map:
        profile_data = data.get(attr)
        if profile_data is None:
            continue
        existing = getattr(company, attr)
        if existing is None:
            setattr(company, attr, model_cls(company_id=company.id, **profile_data))
        else:
            for key, val in profile_data.items():
                setattr(existing, key, val)


def _company_types(company: CrmCompany) -> list[str]:
    return [a.company_type.value for a in company.type_assignments]


BROKER_CONTACT_TYPES = {CrmContactType.BROKER.value, CrmContactType.REALTOR.value}
OPEN_RELATIONSHIP_STATUSES = {"active", "hot", "warm"}


def _contact_count(db: Session, company_id: UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(CrmCompanyContact).where(CrmCompanyContact.company_id == company_id)
    ) or 0


def _primary_address(company: CrmCompany) -> CrmCompanyAddress | None:
    if not company.addresses:
        return None
    for address in company.addresses:
        if address.is_primary:
            return address
    return company.addresses[0]


def _contact_type_values(contact: CrmContact) -> set[str]:
    values: set[str] = set()
    if contact.contact_type:
        values.add(contact.contact_type.value)
    for assignment in contact.type_assignments or []:
        if assignment.contact_type:
            values.add(assignment.contact_type.value)
    return values


def _related_people(db: Session, company: CrmCompany) -> list[CrmCompanyRelatedPerson]:
    people: list[CrmCompanyRelatedPerson] = []
    for link in company.contact_links:
        contact = db.get(CrmContact, link.contact_id)
        if contact is None:
            continue
        types = _contact_type_values(contact)
        contact_type = contact.contact_type.value if contact.contact_type else None
        people.append(
            CrmCompanyRelatedPerson(
                id=contact.id,
                display_name=contact.display_name,
                contact_type=contact_type,
                is_broker=bool(types & BROKER_CONTACT_TYPES),
            )
        )
    return people


def _related_agreements(db: Session, company: CrmCompany) -> list[CrmCompanyRelatedAgreement]:
    contact_ids = [link.contact_id for link in company.contact_links]
    if not contact_ids:
        return []
    rows = list(
        db.scalars(
            select(CrmAgreement).where(
                or_(
                    CrmAgreement.contact_id.in_(contact_ids),
                    CrmAgreement.id.in_(
                        select(CrmAgreementParticipant.agreement_id).where(
                            CrmAgreementParticipant.contact_id.in_(contact_ids)
                        )
                    ),
                )
            )
        ).all()
    )
    seen: set[UUID] = set()
    items: list[CrmCompanyRelatedAgreement] = []
    for agreement in rows:
        if agreement.id in seen:
            continue
        seen.add(agreement.id)
        contact = db.get(CrmContact, agreement.contact_id)
        items.append(
            CrmCompanyRelatedAgreement(
                id=agreement.id,
                project_group=agreement.project_group,
                unit_number=agreement.unit_number,
                investment_amount=agreement.investment_amount,
                contact_id=agreement.contact_id,
                contact_display_name=contact.display_name if contact else None,
            )
        )
    return items


def _open_relationship_count(db: Session, company_id: UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(CrmCompanyRelationship).where(
            CrmCompanyRelationship.status == CrmCompanyRelationshipLinkStatus.ACTIVE,
            or_(
                CrmCompanyRelationship.source_company_id == company_id,
                CrmCompanyRelationship.target_company_id == company_id,
            ),
        )
    ) or 0


def serialize_company_list_item(db: Session, company: CrmCompany) -> CrmCompanyListItem:
    address = _primary_address(company)
    people = _related_people(db, company)
    owner = db.get(User, company.owner_user_id) if company.owner_user_id else None
    return CrmCompanyListItem(
        id=company.id,
        display_name=company.display_name,
        legal_name=company.legal_name,
        company_type=company.company_type.value,
        company_types=_company_types(company),
        entity_type=company.entity_type.value if company.entity_type else None,
        status=company.status.value,
        lifecycle_stage=company.lifecycle_stage.value,
        primary_email=company.primary_email,
        primary_phone=company.primary_phone,
        domain=company.domain,
        industry=company.industry,
        relationship_status=company.relationship_status.value,
        relationship_strength=company.relationship_strength.value,
        owner_user_id=company.owner_user_id,
        owner_name=owner.full_name if owner else None,
        parent_company_id=company.parent_company_id,
        tags=company.tags,
        is_favorite=company.is_favorite,
        is_pinned=company.is_pinned,
        contact_count=_contact_count(db, company.id),
        city=address.city if address else None,
        country=address.country if address else company.incorporation_country,
        related_people=people,
        open_relationship_count=_open_relationship_count(db, company.id),
        related_agreement_count=len(_related_agreements(db, company)),
        last_activity_at=company.last_contact_at,
        notes=company.notes,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def serialize_company_detail(db: Session, company: CrmCompany, user: User | None = None) -> CrmCompanyDetail:
    base = serialize_company_list_item(db, company).model_dump()
    contacts = []
    for link in company.contact_links:
        contact = db.get(CrmContact, link.contact_id)
        contacts.append(
            {
                "id": link.id,
                "contact_id": link.contact_id,
                "role": link.role.value,
                "job_title": link.job_title,
                "department": link.department,
                "relationship_type": link.relationship_type,
                "ownership_percent": link.ownership_percent,
                "signing_authority": link.signing_authority,
                "is_primary": link.is_primary,
                "start_date": link.start_date,
                "end_date": link.end_date,
                "status": link.status.value,
                "contact_display_name": contact.display_name if contact else None,
            }
        )
    relationships = []
    for rel in company.relationships_from:
        target = db.get(CrmCompany, rel.target_company_id)
        relationships.append(
            {
                "id": rel.id,
                "source_company_id": rel.source_company_id,
                "target_company_id": rel.target_company_id,
                "relationship_type": rel.relationship_type.value,
                "is_reciprocal": rel.is_reciprocal,
                "status": rel.status.value,
                "strength": rel.strength.value,
                "notes": rel.notes,
                "target_display_name": target.display_name if target else None,
            }
        )
    detail_data = {
        **base,
        "trade_name": company.trade_name,
        "registration_number": company.registration_number if can_view_legal(user) else None,
        "tax_id": company.tax_id if can_view_legal(user) else None,
        "ein": company.ein if can_view_legal(user) else None,
        "duns_number": company.duns_number,
        "incorporation_date": company.incorporation_date,
        "incorporation_country": company.incorporation_country,
        "incorporation_state": company.incorporation_state,
        "secondary_emails": company.secondary_emails,
        "secondary_phones": company.secondary_phones,
        "website": company.website,
        "linkedin_url": company.linkedin_url,
        "employee_count": company.employee_count,
        "annual_revenue": company.annual_revenue if can_view_financial(user) else None,
        "description": company.description,
        "relationship_score": company.relationship_score,
        "source": company.source,
        "notes": company.notes,
        "last_contact_at": company.last_contact_at,
        "next_follow_up_at": company.next_follow_up_at,
        "archived_at": company.archived_at,
        "addresses": company.addresses,
        "contacts": contacts,
        "relationships": relationships,
        "related_agreements": _related_agreements(db, company),
        "legal_data": company.legal_data if can_view_legal(user) else None,
        "compliance_data": company.compliance_data if can_view_compliance(user) else None,
    }
    if can_view_financial(user) and company.financial_profile:
        detail_data["financial_profile"] = CrmCompanyFinancialProfileSchema.model_validate(
            company.financial_profile, from_attributes=True
        )
    if company.investment_profile:
        detail_data["investment_profile"] = CrmCompanyInvestmentProfileSchema.model_validate(
            company.investment_profile, from_attributes=True
        )
    if company.brokerage_profile:
        detail_data["brokerage_profile"] = CrmCompanyBrokerageProfileSchema.model_validate(
            company.brokerage_profile, from_attributes=True
        )
    if company.lender_profile:
        detail_data["lender_profile"] = CrmCompanyLenderProfileSchema.model_validate(
            company.lender_profile, from_attributes=True
        )
    if company.vendor_profile:
        detail_data["vendor_profile"] = CrmCompanyVendorProfileSchema.model_validate(
            company.vendor_profile, from_attributes=True
        )
    if company.law_firm_profile:
        detail_data["law_firm_profile"] = CrmCompanyLawFirmProfileSchema.model_validate(
            company.law_firm_profile, from_attributes=True
        )
    if company.property_management_profile:
        detail_data["property_management_profile"] = CrmCompanyPropertyManagementProfileSchema.model_validate(
            company.property_management_profile, from_attributes=True
        )
    return CrmCompanyDetail.model_validate(detail_data)


def get_company_or_404(db: Session, company_id: UUID, *, include_archived: bool = False) -> CrmCompany:
    query = (
        select(CrmCompany)
        .options(
            selectinload(CrmCompany.type_assignments),
            selectinload(CrmCompany.addresses),
            selectinload(CrmCompany.contact_links),
            selectinload(CrmCompany.relationships_from),
            selectinload(CrmCompany.financial_profile),
            selectinload(CrmCompany.investment_profile),
            selectinload(CrmCompany.brokerage_profile),
            selectinload(CrmCompany.lender_profile),
            selectinload(CrmCompany.vendor_profile),
            selectinload(CrmCompany.law_firm_profile),
            selectinload(CrmCompany.property_management_profile),
        )
        .where(CrmCompany.id == company_id)
    )
    if not include_archived:
        query = query.where(CrmCompany.archived_at.is_(None))
    company = db.scalar(query)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CRM company not found")
    return company


def company_workspace_counts(db: Session) -> CrmCompanyCounts:
    active = CrmCompany.archived_at.is_(None)
    total = db.scalar(select(func.count()).select_from(CrmCompany).where(active)) or 0
    brokerage = db.scalar(
        select(func.count()).select_from(CrmCompany).where(active, CrmCompany.company_type == CrmCompanyType.BROKERAGE)
    ) or 0
    partner = db.scalar(
        select(func.count()).select_from(CrmCompany).where(active, CrmCompany.company_type == CrmCompanyType.PARTNER)
    ) or 0
    investor = db.scalar(
        select(func.count()).select_from(CrmCompany).where(
            active, CrmCompany.company_type == CrmCompanyType.INVESTMENT_COMPANY
        )
    ) or 0
    open_company_ids: set[UUID] = set()
    open_company_ids.update(
        row[0]
        for row in db.execute(
            select(CrmCompanyRelationship.source_company_id).where(
                CrmCompanyRelationship.status == CrmCompanyRelationshipLinkStatus.ACTIVE
            )
        )
        if row[0] is not None
    )
    open_company_ids.update(
        row[0]
        for row in db.execute(
            select(CrmCompanyRelationship.target_company_id).where(
                CrmCompanyRelationship.status == CrmCompanyRelationshipLinkStatus.ACTIVE
            )
        )
        if row[0] is not None
    )
    open_company_ids.update(
        row[0]
        for row in db.execute(
            select(CrmCompany.id).where(active, CrmCompany.relationship_status.in_(tuple(OPEN_RELATIONSHIP_STATUSES)))
        )
    )
    return CrmCompanyCounts(
        total=int(total),
        brokerage=int(brokerage),
        partner=int(partner),
        investor=int(investor),
        open_relationships=len(open_company_ids),
    )


def list_crm_companies(
    db: Session,
    *,
    search: str | None = None,
    status_filter: str | None = None,
    company_type: str | None = None,
    lifecycle_stage: str | None = None,
    industry: str | None = None,
    owner_user_id: UUID | None = None,
    country: str | None = None,
    relationship_status: str | None = None,
    open_relationships: bool = False,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> CrmCompanyListResponse:
    query = select(CrmCompany).options(
        selectinload(CrmCompany.type_assignments),
        selectinload(CrmCompany.addresses),
        selectinload(CrmCompany.contact_links),
    )
    if not include_archived:
        query = query.where(CrmCompany.archived_at.is_(None))
    if status_filter:
        query = query.where(CrmCompany.status == status_filter)
    if company_type:
        query = query.where(CrmCompany.company_type == company_type)
    if lifecycle_stage:
        query = query.where(CrmCompany.lifecycle_stage == lifecycle_stage)
    if industry:
        query = query.where(CrmCompany.industry.ilike(f"%{industry.strip()}%"))
    if owner_user_id:
        query = query.where(CrmCompany.owner_user_id == owner_user_id)
    if relationship_status:
        query = query.where(CrmCompany.relationship_status == relationship_status)
    if country:
        query = query.where(
            exists(
                select(CrmCompanyAddress.id).where(
                    CrmCompanyAddress.company_id == CrmCompany.id,
                    CrmCompanyAddress.country.ilike(country.strip()),
                )
            )
        )
    if open_relationships:
        query = query.where(
            or_(
                CrmCompany.relationship_status.in_(tuple(OPEN_RELATIONSHIP_STATUSES)),
                exists(
                    select(CrmCompanyRelationship.id).where(
                        CrmCompanyRelationship.status == CrmCompanyRelationshipLinkStatus.ACTIVE,
                        or_(
                            CrmCompanyRelationship.source_company_id == CrmCompany.id,
                            CrmCompanyRelationship.target_company_id == CrmCompany.id,
                        ),
                    )
                ),
            )
        )
    if search:
        pattern = f"%{search.strip()}%"
        person_match = exists(
            select(CrmCompanyContact.id)
            .join(CrmContact, CrmContact.id == CrmCompanyContact.contact_id)
            .where(
                CrmCompanyContact.company_id == CrmCompany.id,
                or_(
                    CrmContact.display_name.ilike(pattern),
                    CrmContact.primary_email.ilike(pattern),
                    CrmContact.primary_phone.ilike(pattern),
                ),
            )
        )
        query = query.where(
            or_(
                CrmCompany.display_name.ilike(pattern),
                CrmCompany.legal_name.ilike(pattern),
                CrmCompany.primary_email.ilike(pattern),
                CrmCompany.primary_phone.ilike(pattern),
                CrmCompany.domain.ilike(pattern),
                CrmCompany.registration_number.ilike(pattern),
                person_match,
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_column = SORTABLE_FIELDS.get(sort_by, CrmCompany.updated_at)
    order = desc(sort_column) if sort_order == "desc" else asc(sort_column)
    items = db.scalars(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return CrmCompanyListResponse(
        items=[serialize_company_list_item(db, c) for c in items],
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if page_size else 0,
    )


def create_crm_company(db: Session, payload: CrmCompanyCreate, user: User | None = None) -> CrmCompany:
    del user
    legal_name = _normalize(payload.legal_name)
    ein = _normalize(payload.ein)
    reg = _normalize(payload.registration_number)
    domain = normalize_domain(payload.domain or payload.website)
    email = normalize_email(payload.primary_email)
    for field, val in [("legal_name", legal_name), ("ein", ein), ("registration_number", reg), ("domain", domain), ("primary_email", email)]:
        _check_duplicate(db, field=field, value=val)
    company = CrmCompany(
        display_name=payload.display_name.strip(),
        legal_name=legal_name,
        trade_name=_normalize(payload.trade_name),
        company_type=CrmCompanyType(payload.company_type.value),
        entity_type=payload.entity_type.value if payload.entity_type else None,
        status=CrmCompanyStatus(payload.status.value),
        lifecycle_stage=payload.lifecycle_stage.value,
        registration_number=reg,
        tax_id=_normalize(payload.tax_id),
        ein=ein,
        duns_number=_normalize(payload.duns_number),
        incorporation_date=payload.incorporation_date,
        incorporation_country=_normalize(payload.incorporation_country),
        incorporation_state=_normalize(payload.incorporation_state),
        primary_email=email,
        secondary_emails=payload.secondary_emails,
        primary_phone=normalize_phone(payload.primary_phone),
        secondary_phones=payload.secondary_phones,
        website=_normalize(payload.website),
        domain=domain,
        linkedin_url=_normalize(payload.linkedin_url),
        industry=_normalize(payload.industry),
        employee_count=payload.employee_count,
        annual_revenue=payload.annual_revenue,
        description=payload.description,
        source=_normalize(payload.source),
        owner_user_id=payload.owner_user_id,
        parent_company_id=payload.parent_company_id,
        tags=payload.tags,
        notes=payload.notes,
    )
    db.add(company)
    db.flush()
    if payload.parent_company_id:
        _validate_parent(db, company, payload.parent_company_id)
    _apply_type_assignments(db, company, CrmCompanyType(payload.company_type.value), [CrmCompanyType(t.value) for t in payload.company_types] if payload.company_types else None)
    _apply_addresses(company, payload.addresses)
    _apply_profile(db, company, payload)
    db.flush()
    return company


def update_crm_company(db: Session, company: CrmCompany, payload: CrmCompanyUpdate) -> CrmCompany:
    data = payload.model_dump(exclude_unset=True)
    if "legal_name" in data:
        val = _normalize(data["legal_name"])
        _check_duplicate(db, field="legal_name", value=val, exclude_id=company.id)
        company.legal_name = val
    if "ein" in data:
        val = _normalize(data["ein"])
        _check_duplicate(db, field="ein", value=val, exclude_id=company.id)
        company.ein = val
    if "registration_number" in data:
        val = _normalize(data["registration_number"])
        _check_duplicate(db, field="registration_number", value=val, exclude_id=company.id)
        company.registration_number = val
    if "primary_email" in data:
        val = normalize_email(data["primary_email"])
        _check_duplicate(db, field="primary_email", value=val, exclude_id=company.id)
        company.primary_email = val
    if "domain" in data or "website" in data:
        domain = normalize_domain(data.get("domain") or data.get("website") or company.domain)
        _check_duplicate(db, field="domain", value=domain, exclude_id=company.id)
        company.domain = domain
    if "website" in data:
        company.website = _normalize(data["website"])
    if "primary_phone" in data:
        company.primary_phone = normalize_phone(data["primary_phone"])
    if "parent_company_id" in data:
        _validate_parent(db, company, data["parent_company_id"])
        company.parent_company_id = data["parent_company_id"]
    if "display_name" in data:
        company.display_name = data["display_name"].strip()
    if "company_type" in data and data["company_type"]:
        company.company_type = CrmCompanyType(data["company_type"].value if hasattr(data["company_type"], "value") else data["company_type"])
    if "company_types" in data or "company_type" in data:
        primary = company.company_type
        types = [CrmCompanyType(t.value if hasattr(t, "value") else t) for t in data.get("company_types", [])] if data.get("company_types") else None
        _apply_type_assignments(db, company, primary, types, replace=True)
    simple_fields = [
        "trade_name", "entity_type", "status", "lifecycle_stage", "tax_id", "duns_number",
        "incorporation_date", "incorporation_country", "incorporation_state", "secondary_emails",
        "secondary_phones", "linkedin_url", "industry", "employee_count", "annual_revenue",
        "description", "source", "owner_user_id", "tags", "notes",
    ]
    for field in simple_fields:
        if field in data:
            val = data[field]
            if field in ("entity_type", "status", "lifecycle_stage") and val is not None:
                val = val.value if hasattr(val, "value") else val
            if field in ("trade_name", "tax_id", "duns_number", "incorporation_country", "incorporation_state", "linkedin_url", "industry", "source") and val is not None:
                val = _normalize(val)
            setattr(company, field, val)
    if "addresses" in data:
        _apply_addresses(company, payload.addresses, replace=True)
    _apply_profile(db, company, payload)
    db.flush()
    return company


def archive_crm_company(db: Session, company: CrmCompany) -> CrmCompany:
    company.status = CrmCompanyStatus.ARCHIVED
    company.archived_at = datetime.now(UTC)
    db.flush()
    return company


def restore_crm_company(db: Session, company: CrmCompany) -> CrmCompany:
    company.status = CrmCompanyStatus.ACTIVE
    company.archived_at = None
    db.flush()
    return company


def delete_crm_company(db: Session, company: CrmCompany) -> None:
    db.delete(company)


def find_duplicates(db: Session, company_id: UUID | None = None) -> list[CrmCompanyDuplicateCandidate]:
    candidates: list[CrmCompanyDuplicateCandidate] = []
    query = select(CrmCompany).where(CrmCompany.archived_at.is_(None))
    if company_id:
        query = query.where(CrmCompany.id == company_id)
    companies = db.scalars(query).all()
    seen: set[tuple[str, str]] = set()
    for field in DUPLICATE_FIELDS:
        by_value: dict[str, list[CrmCompany]] = {}
        for c in companies:
            val = getattr(c, field)
            if val:
                by_value.setdefault(str(val).lower(), []).append(c)
        for val, group in by_value.items():
            if len(group) < 2:
                continue
            for c in group:
                key = (str(c.id), field)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    CrmCompanyDuplicateCandidate(
                        id=c.id,
                        display_name=c.display_name,
                        legal_name=c.legal_name,
                        match_field=field,
                        match_value=val,
                        confidence=0.9,
                    )
                )
    return candidates


def merge_crm_companies(db: Session, source_id: UUID, target_id: UUID) -> CrmCompanyMergeResponse:
    if source_id == target_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot merge company with itself")
    source = get_company_or_404(db, source_id)
    target = get_company_or_404(db, target_id)
    for link in list(source.contact_links):
        existing = db.scalar(
            select(CrmCompanyContact).where(
                CrmCompanyContact.company_id == target.id,
                CrmCompanyContact.contact_id == link.contact_id,
            )
        )
        if not existing:
            link.company_id = target.id
        else:
            db.delete(link)
    for rel in list(source.relationships_from):
        rel.source_company_id = target.id
    children = db.scalars(select(CrmCompany).where(CrmCompany.parent_company_id == source.id)).all()
    for child in children:
        child.parent_company_id = target.id
    archive_crm_company(db, source)
    db.flush()
    return CrmCompanyMergeResponse(merged_id=target.id, archived_source_id=source.id)


def bulk_action(db: Session, company_ids: list[UUID], action: str, payload: dict | None = None) -> CrmCompanyBulkActionResponse:
    affected = 0
    for cid in company_ids:
        company = get_company_or_404(db, cid, include_archived=True)
        if action == "archive":
            archive_crm_company(db, company)
            affected += 1
        elif action == "restore":
            restore_crm_company(db, company)
            affected += 1
        elif action == "delete":
            delete_crm_company(db, company)
            affected += 1
        elif action == "assign_owner" and payload and payload.get("owner_user_id"):
            company.owner_user_id = UUID(str(payload["owner_user_id"]))
            affected += 1
    db.flush()
    return CrmCompanyBulkActionResponse(affected=affected)


def add_company_contact(db: Session, company: CrmCompany, payload: CrmCompanyContactCreate) -> CrmCompanyContact:
    contact = db.get(CrmContact, payload.contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    existing = db.scalar(
        select(CrmCompanyContact).where(
            CrmCompanyContact.company_id == company.id,
            CrmCompanyContact.contact_id == payload.contact_id,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Contact already linked")
    if payload.is_primary:
        for link in company.contact_links:
            link.is_primary = False
    link = CrmCompanyContact(
        company_id=company.id,
        contact_id=payload.contact_id,
        role=payload.role.value,
        job_title=payload.job_title,
        department=payload.department,
        relationship_type=payload.relationship_type,
        ownership_percent=payload.ownership_percent,
        signing_authority=payload.signing_authority,
        is_primary=payload.is_primary,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status.value,
    )
    db.add(link)
    db.flush()
    return link


def update_company_contact(
    db: Session,
    company: CrmCompany,
    link_id: UUID,
    payload: CrmCompanyContactUpdate,
) -> CrmCompanyContact:
    link = db.scalar(
        select(CrmCompanyContact).where(
            CrmCompanyContact.id == link_id,
            CrmCompanyContact.company_id == company.id,
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company contact link not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_primary"):
        for other in company.contact_links:
            other.is_primary = False
    for key, val in data.items():
        if key == "role" and val:
            val = val.value if hasattr(val, "value") else val
        if key == "status" and val:
            val = val.value if hasattr(val, "value") else val
        setattr(link, key, val)
    db.flush()
    return link


def remove_company_contact(db: Session, company: CrmCompany, link_id: UUID) -> None:
    link = db.scalar(
        select(CrmCompanyContact).where(
            CrmCompanyContact.id == link_id,
            CrmCompanyContact.company_id == company.id,
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company contact link not found")
    db.delete(link)


def add_company_relationship(db: Session, company: CrmCompany, payload: CrmCompanyRelationshipCreate) -> CrmCompanyRelationship:
    if payload.target_company_id == company.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot relate to self")
    target = get_company_or_404(db, payload.target_company_id)
    del target
    rel = CrmCompanyRelationship(
        source_company_id=company.id,
        target_company_id=payload.target_company_id,
        relationship_type=payload.relationship_type.value,
        is_reciprocal=payload.is_reciprocal,
        strength=payload.strength if isinstance(payload.strength, str) else payload.strength,
        notes=payload.notes,
    )
    db.add(rel)
    db.flush()
    return rel


def build_hierarchy(db: Session) -> CrmCompanyHierarchyResponse:
    companies = db.scalars(
        select(CrmCompany).where(CrmCompany.archived_at.is_(None)).order_by(CrmCompany.display_name)
    ).all()
    nodes: dict[UUID, CrmCompanyHierarchyNode] = {}
    for c in companies:
        nodes[c.id] = CrmCompanyHierarchyNode(
            id=c.id,
            display_name=c.display_name,
            company_type=c.company_type.value,
            status=c.status.value,
            parent_company_id=c.parent_company_id,
            children=[],
        )
    roots: list[CrmCompanyHierarchyNode] = []
    for c in companies:
        node = nodes[c.id]
        if c.parent_company_id and c.parent_company_id in nodes:
            nodes[c.parent_company_id].children.append(node)
        else:
            roots.append(node)
    return CrmCompanyHierarchyResponse(roots=roots)


def export_crm_companies_csv(db: Session, *, include_archived: bool = False) -> str:
    result = list_crm_companies(db, include_archived=include_archived, page_size=10000)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["display_name", "legal_name", "company_type", "status", "primary_email", "domain", "industry"],
    )
    writer.writeheader()
    for item in result.items:
        writer.writerow(
            {
                "display_name": item.display_name,
                "legal_name": item.legal_name or "",
                "company_type": item.company_type,
                "status": item.status,
                "primary_email": item.primary_email or "",
                "domain": item.domain or "",
                "industry": item.industry or "",
            }
        )
    return output.getvalue()


def import_crm_companies_csv(db: Session, content: str) -> CrmCompanyImportResult:
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    skipped = 0
    errors: list[str] = []
    for row_num, row in enumerate(reader, start=2):
        display_name = (row.get("display_name") or "").strip()
        if not display_name:
            skipped += 1
            errors.append(f"Row {row_num}: missing display_name")
            continue
        try:
            ctype = CrmCompanyTypeEnum(row.get("company_type") or "other")
            cstatus = CrmCompanyStatusEnum(row.get("status") or "active")
            create_crm_company(
                db,
                CrmCompanyCreate(
                    display_name=display_name,
                    legal_name=row.get("legal_name") or None,
                    company_type=ctype,
                    status=cstatus,
                    primary_email=row.get("primary_email") or None,
                    domain=row.get("domain") or None,
                    industry=row.get("industry") or None,
                ),
            )
            imported += 1
        except HTTPException as exc:
            skipped += 1
            errors.append(f"Row {row_num}: {exc.detail}")
    return CrmCompanyImportResult(imported=imported, skipped=skipped, errors=errors)


def list_saved_views(db: Session, user_id: UUID) -> list[CrmCompanySavedViewResponse]:
    views = db.scalars(
        select(CrmCompanySavedView).where(CrmCompanySavedView.user_id == user_id).order_by(CrmCompanySavedView.name)
    ).all()
    return [CrmCompanySavedViewResponse.model_validate(v) for v in views]


def create_saved_view(db: Session, user_id: UUID, payload: CrmCompanySavedViewCreate) -> CrmCompanySavedView:
    view = CrmCompanySavedView(
        user_id=user_id,
        name=payload.name,
        filters=payload.filters,
        columns=payload.columns,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        is_default=payload.is_default,
    )
    db.add(view)
    db.flush()
    return view
