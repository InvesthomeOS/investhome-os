"""CRM reports summary API tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact, CrmCompanyType
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.crm_relationship import (
    CrmRelationship,
    CrmRelationshipCategory,
    CrmRelationshipEntityType,
    CrmRelationshipStatus,
)
from investhome_api.services.crm.report_service import _parse_investment_amount, build_crm_reports_summary


def test_parse_investment_amount_only_real_numbers() -> None:
    assert _parse_investment_amount("50000.00") == 50000.0
    assert _parse_investment_amount("100,000") == 100000.0
    assert _parse_investment_amount(" TBD ") is None
    assert _parse_investment_amount(None) is None


def test_reports_summary_counts_existing_rows(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        contact_type=CrmContactType.BROKER,
        record_kind=CrmRecordKind.PERSON,
        display_name="Report Agent",
        status=CrmContactStatus.ACTIVE,
        primary_email="report.agent@example.com",
    )
    company = CrmCompany(display_name="Report Co", company_type=CrmCompanyType.BROKERAGE)
    db.add_all([contact, company])
    db.flush()
    db.add(CrmCompanyContact(company_id=company.id, contact_id=contact.id))
    db.add(
        CrmAgreement(
            contact_id=contact.id,
            project_group="reit",
            source="bitrix",
            source_external_id="reit:report-1",
            investment_amount="150000.00",
        )
    )
    db.add(
        CrmRelationship(
            source_entity_type=CrmRelationshipEntityType.CONTACT,
            source_entity_id=contact.id,
            target_entity_type=CrmRelationshipEntityType.COMPANY,
            target_entity_id=company.id,
            relationship_type="contact_company",
            category=CrmRelationshipCategory.ORGANIZATIONAL,
            status=CrmRelationshipStatus.ACTIVE,
        )
    )
    db.commit()

    summary = build_crm_reports_summary(db)
    assert summary.contacts_total >= 1
    assert summary.contacts_agents >= 1
    assert summary.contacts_agreement >= 1
    assert summary.companies_total >= 1
    assert summary.company_contact_links >= 1
    assert summary.agreements_total >= 1
    assert any(item.key == "reit" for item in summary.agreements_by_project_group)
    assert summary.reit_investment.populated_count >= 1
    assert summary.reit_investment.total is not None
    assert summary.relationships_contact_company >= 1

    response = client.get("/crm/reports/summary")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "contacts_total" in body
    assert "pipeline_by_stage" in body
    assert "activities_by_type" in body
    assert body["companies_total"] >= 1
