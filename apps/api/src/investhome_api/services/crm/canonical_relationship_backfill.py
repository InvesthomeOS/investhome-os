"""Idempotent canonical CRM relationship backfill from existing production records.

Derives crm_relationships rows from:
- crm_company_contacts → contact → company (type contact_company)
- crm_agreements with a real project_id → contact → project (type investor)

Does not invent people, companies, projects, or relationship meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.crm_relationship import CrmRelationship, CrmRelationshipEntityType
from investhome_api.models.project import Project
from investhome_api.schemas.crm_relationships import (
    CrmRelationshipCategoryEnum,
    CrmRelationshipCreate,
    CrmRelationshipEntityTypeEnum,
)
from investhome_api.services.crm.reciprocal_mapping_service import seed_type_configs
from investhome_api.services.crm.relationship_service import create_relationship, find_duplicate_candidates

QA_TEST_CONTACT_NAMES = frozenset({"QA Contact Alpha", "QA Contact Beta"})

CONTACT_COMPANY_TYPE = "contact_company"
INVESTOR_PROJECT_TYPE = "investor"


@dataclass(frozen=True)
class CanonicalRelationshipBackfillResult:
    qa_removed: int
    contact_company_created: int
    contact_company_skipped: int
    investor_project_created: int
    investor_project_skipped: int
    investor_project_unlinked: int


def _is_qa_test_contact_name(name: str | None) -> bool:
    return (name or "").strip() in QA_TEST_CONTACT_NAMES


def purge_qa_test_relationships(db: Session) -> int:
    """Delete colleague rows whose both endpoints are the known QA test contacts."""
    qa_contacts = db.scalars(
        select(CrmContact).where(CrmContact.display_name.in_(QA_TEST_CONTACT_NAMES))
    ).all()
    qa_ids = {contact.id for contact in qa_contacts if _is_qa_test_contact_name(contact.display_name)}
    if not qa_ids:
        return 0

    rels = db.scalars(
        select(CrmRelationship).where(
            CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.source_entity_id.in_(qa_ids),
            CrmRelationship.target_entity_id.in_(qa_ids),
        )
    ).all()
    removed = 0
    for rel in rels:
        db.delete(rel)
        removed += 1
    if removed:
        db.flush()
    return removed


def _ensure_relationship(db: Session, payload: CrmRelationshipCreate) -> bool:
    if find_duplicate_candidates(db, payload):
        return False
    create_relationship(db, payload, user=None)
    return True


def _backfill_contact_company(db: Session) -> tuple[int, int]:
    created = 0
    skipped = 0
    links = db.scalars(select(CrmCompanyContact)).all()
    for link in links:
        contact = db.get(CrmContact, link.contact_id)
        company = db.get(CrmCompany, link.company_id)
        if contact is None or company is None:
            skipped += 1
            continue
        payload = CrmRelationshipCreate(
            source_entity_type=CrmRelationshipEntityTypeEnum.CONTACT,
            source_entity_id=link.contact_id,
            target_entity_type=CrmRelationshipEntityTypeEnum.COMPANY,
            target_entity_id=link.company_id,
            relationship_type=CONTACT_COMPANY_TYPE,
            category=CrmRelationshipCategoryEnum.ORGANIZATIONAL,
            is_verified=True,
            metadata_json={
                "origin": "crm_company_contacts",
                "company_contact_id": str(link.id),
            },
        )
        if _ensure_relationship(db, payload):
            created += 1
        else:
            skipped += 1
    return created, skipped


def _backfill_investor_project(db: Session) -> tuple[int, int, int]:
    created = 0
    skipped = 0
    unlinked = 0
    seen: set[tuple[UUID, UUID]] = set()
    agreements = db.scalars(select(CrmAgreement)).all()
    for agreement in agreements:
        if agreement.project_id is None:
            unlinked += 1
            continue
        key = (agreement.contact_id, agreement.project_id)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        contact = db.get(CrmContact, agreement.contact_id)
        project = db.get(Project, agreement.project_id)
        if contact is None or project is None:
            skipped += 1
            continue
        payload = CrmRelationshipCreate(
            source_entity_type=CrmRelationshipEntityTypeEnum.CONTACT,
            source_entity_id=agreement.contact_id,
            target_entity_type=CrmRelationshipEntityTypeEnum.PROJECT,
            target_entity_id=agreement.project_id,
            relationship_type=INVESTOR_PROJECT_TYPE,
            category=CrmRelationshipCategoryEnum.INVESTMENT,
            is_verified=True,
            metadata_json={
                "origin": "crm_agreements",
                "project_group": agreement.project_group,
            },
        )
        if _ensure_relationship(db, payload):
            created += 1
        else:
            skipped += 1
    return created, skipped, unlinked


def backfill_canonical_relationships(db: Session) -> CanonicalRelationshipBackfillResult:
    seed_type_configs(db)
    qa_removed = purge_qa_test_relationships(db)
    company_created, company_skipped = _backfill_contact_company(db)
    investor_created, investor_skipped, investor_unlinked = _backfill_investor_project(db)
    db.flush()
    return CanonicalRelationshipBackfillResult(
        qa_removed=qa_removed,
        contact_company_created=company_created,
        contact_company_skipped=company_skipped,
        investor_project_created=investor_created,
        investor_project_skipped=investor_skipped,
        investor_project_unlinked=investor_unlinked,
    )


def relationship_duplicate_count(db: Session) -> int:
    rows = db.execute(
        select(
            CrmRelationship.source_entity_type,
            CrmRelationship.source_entity_id,
            CrmRelationship.target_entity_type,
            CrmRelationship.target_entity_id,
            CrmRelationship.relationship_type,
        )
    ).all()
    seen: set[tuple] = set()
    duplicates = 0
    for row in rows:
        if row in seen:
            duplicates += 1
        else:
            seen.add(row)
    return duplicates
