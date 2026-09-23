"""CRM reports summary and workspace API tests."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityType,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany, CrmCompanyContact, CrmCompanyType
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.crm_relationship import (
    CrmRelationship,
    CrmRelationshipCategory,
    CrmRelationshipEntityType,
    CrmRelationshipStatus,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.services.crm.report_service import (
    _parse_investment_amount,
    build_crm_reports_summary,
    build_crm_reports_workspace,
)
from investhome_api.services.crm.unit_change import HISTORICAL_UNIT_CHANGE_SOURCE


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
            metadata_json={"opportunity": "150000.00", "currency": "USD"},
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


def test_workspace_excludes_historical_unit_change_from_current_sales(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Semra Report",
        status=CrmContactStatus.ACTIVE,
        source="Bitrix",
    )
    db.add(contact)
    db.flush()
    db.add(
        CrmAgreement(
            contact_id=contact.id,
            project_group="1812_h_pl",
            source="bitrix",
            source_external_id="1812:current-307",
            unit_number="307",
            agreement_date=datetime(2024, 6, 1, tzinfo=UTC).date(),
            metadata_json={"opportunity": "250000", "currency": "USD"},
        )
    )
    db.add(
        CrmAgreement(
            contact_id=contact.id,
            project_group="1812_h_pl",
            source=HISTORICAL_UNIT_CHANGE_SOURCE,
            source_external_id="1812:hist-b07",
            unit_number="B07",
            metadata_json={"opportunity": "999999", "currency": "USD", "historical_unit_change": True},
        )
    )
    db.add(
        CrmAgreement(
            contact_id=contact.id,
            project_group="uniloft",
            source="bitrix",
            source_external_id="uniloft:eur-1",
            unit_number="12",
            metadata_json={"opportunity": "80000", "currency": "EUR"},
        )
    )
    db.add(
        CrmAgreement(
            contact_id=contact.id,
            project_group="reit",
            source="bitrix",
            source_external_id="reit:missing-amount",
            unit_number="REIT-1",
        )
    )
    db.commit()

    workspace = build_crm_reports_workspace(db)
    assert workspace.kpis.current_purchases >= 3
    assert workspace.sales.historical_count >= 1
    usd = next(item for item in workspace.kpis.sales_totals if item.currency == "USD")
    eur = next(item for item in workspace.kpis.sales_totals if item.currency == "EUR")
    assert usd.total == 250000
    assert eur.total == 80000
    assert all(item.currency != "USD+EUR" for item in workspace.kpis.sales_totals)
    assert 999999 not in {item.total for item in workspace.kpis.sales_totals}

    filtered = build_crm_reports_workspace(db, project_group="1812_h_pl")
    assert filtered.kpis.current_purchases == 1
    assert filtered.sales.historical_count == 1
    assert filtered.kpis.sales_totals[0].currency == "USD"
    assert filtered.kpis.sales_totals[0].total == 250000

    response = client.get("/crm/reports/workspace")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "kpis" in body
    assert "sales" in body
    assert "investors" in body
    assert "leads" in body
    assert "communication" in body
    assert "tasks" in body
    assert "documents" in body


def test_workspace_dedupes_communication_source_ids(db: Session) -> None:
    contact = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Co-owner Report",
        status=CrmContactStatus.ACTIVE,
        source="Bitrix",
    )
    other = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Co-owner Copy",
        status=CrmContactStatus.ACTIVE,
        source="Bitrix",
    )
    db.add_all([contact, other])
    db.flush()
    payload = {"bitrix_history": {"kind": "email", "bitrix_record_id": "dup-mail-1"}}
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.EMAIL,
            activity_category=CrmActivityCategory.COMMUNICATION,
            title="Hello",
            summary="Hello",
            metadata_json=payload,
        )
    )
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=other.id,
            activity_type=CrmActivityType.EMAIL,
            activity_category=CrmActivityCategory.COMMUNICATION,
            title="Hello copy",
            summary="Hello copy",
            metadata_json=payload,
        )
    )
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.TASK,
            activity_category=CrmActivityCategory.TASK,
            task_status=CrmTaskStatus.IN_PROGRESS,
            title="Follow up",
            summary="Follow up",
            due_date=datetime.now(tz=UTC) + timedelta(days=2),
        )
    )
    db.add(
        Lead(
            full_name="Website Lead",
            source="website",
            status=LeadStatus.NEW,
            interested_project="uniloft",
            is_demo=False,
        )
    )
    db.commit()

    workspace = build_crm_reports_workspace(db)
    assert workspace.communication.email >= 1
    assert workspace.kpis.open_leads >= 1
    assert any(item.key == "website" for item in workspace.leads.by_source)
    assert all(item.rate is None or item.won + item.lost > 0 for item in workspace.leads.conversion)
    emails = [item for item in workspace.communication.by_channel if item.key == "email"]
    assert emails and emails[0].count >= 1
