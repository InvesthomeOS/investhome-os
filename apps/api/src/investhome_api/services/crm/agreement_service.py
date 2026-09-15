"""CRM Agreement list service. Write/import commit is out of scope for Phase 2."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.schemas.crm_agreements import CrmAgreementSummary
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.contact_service import paginate_total_pages
from investhome_api.services.crm.identity import displayable_phone


def serialize_agreement(row: CrmAgreement, *, contact: CrmContact | None = None, contact_name: str | None = None) -> CrmAgreementSummary:
    try:
        group = BitrixProjectGroup(row.project_group)
        label = BITRIX_PROJECT_GROUP_LABELS[group]
    except ValueError:
        label = row.project_group
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    fields = meta.get("agreement_fields") if isinstance(meta.get("agreement_fields"), dict) else {}
    email = None
    phone = None
    if contact is not None:
        email = contact.primary_email
        phone = contact.primary_phone
        contact_name = contact_name or contact.display_name
    email = meta.get("contact_email") or fields.get("email") or email
    phone = displayable_phone(
        phone,
        str(meta.get("contact_phone") or "") or None,
        str(fields.get("phone") or "") or None,
    )
    name = meta.get("source_name") or fields.get("customer_name") or contact_name
    is_reit = row.project_group == BitrixProjectGroup.REIT.value
    unit_number = None if is_reit else (row.unit_number or fields.get("unit_number") or meta.get("unit_number"))
    investment_amount = row.investment_amount or (
        fields.get("payment_amount") if is_reit else None
    ) or (meta.get("investment_amount") if is_reit else None)
    return CrmAgreementSummary(
        id=row.id,
        contact_id=row.contact_id,
        contact_name=name,
        project_id=row.project_id,
        project_group=row.project_group,
        project_group_label=label,
        source=row.source,
        source_external_id=row.source_external_id,
        status=row.status,
        agreement_date=row.agreement_date,
        unit_number=str(unit_number) if unit_number else None,
        investment_amount=str(investment_amount) if investment_amount else None,
        contact_email=str(email) if email else None,
        contact_phone=str(phone) if phone else None,
        review_required=bool(row.review_required or meta.get("review_required")),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_agreements(
    db: Session,
    *,
    project_group: str | None = None,
    status: CrmAgreementStatus | None = None,
    contact_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmAgreementSummary], int]:
    query = select(CrmAgreement)
    if project_group:
        query = query.where(CrmAgreement.project_group == project_group)
    if status is not None:
        query = query.where(CrmAgreement.status == status)
    if contact_id is not None:
        query = query.where(CrmAgreement.contact_id == contact_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(CrmAgreement.agreement_date.desc().nullslast(), CrmAgreement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    contact_ids = {row.contact_id for row in rows}
    contacts: dict[UUID, CrmContact] = {}
    if contact_ids:
        for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all():
            contacts[contact.id] = contact
    items = [
        serialize_agreement(row, contact=contacts.get(row.contact_id), contact_name=(contacts[row.contact_id].display_name if row.contact_id in contacts else None))
        for row in rows
    ]
    return items, int(total)


def agreement_list_meta(*, total: int, page: int, page_size: int) -> dict[str, int]:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": paginate_total_pages(total, page_size),
    }
