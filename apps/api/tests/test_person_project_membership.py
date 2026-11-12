"""Person project membership is shared by the CRM project filter."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.finance import CommitmentStatus, CommitmentType, FundingCommitment
from investhome_api.models.inventory import InventoryAsset, InventoryAssetType, UsageType
from investhome_api.models.inventory_workflows import (
    AcquisitionMethod,
    InventoryOwnership,
    OwnershipRecordStatus,
    OwnershipSource,
    OwnershipType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.services.crm.person_project_membership import person_project_contact_ids
from investhome_api.services.inventory.phase_identity import find_duplicate_phase_units

ROOT = Path(__file__).resolve().parents[1]


def _project(client: TestClient, *, code: str, name: str) -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": name,
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _person(db: Session, name: str) -> CrmContact:
    row = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        status=CrmContactStatus.ACTIVE,
        source="test",
    )
    db.add(row)
    db.flush()
    return row


def test_membership_includes_agreement_and_lead_and_excludes_other_phase(
    client: TestClient, db: Session
) -> None:
    project = _project(client, code="PRJ-MEM-1812", name="1812 H Place NE")
    other = _project(client, code="PRJ-MEM-TEMP", name="The Temple")
    project_id = UUID(project["id"])
    historic = client.post(f"/inventory/projects/{project['id']}/phases", json={"name": "Historic"}).json()
    addition = client.post(
        f"/inventory/projects/{project['id']}/phases",
        json={"name": "Addition", "display_order": 1},
    ).json()
    buyer = _person(db, "Zafer Yıldırım")
    lead_person = _person(db, "Lead Member")
    addition_only = _person(db, "Addition Only")
    stranger = _person(db, "Unrelated Person")
    db.add(
        CrmAgreement(
            contact_id=buyer.id,
            project_id=project_id,
            phase_id=UUID(historic["id"]),
            project_group="1812_h_pl",
            source="test",
            source_external_id="mem-101",
            unit_number="101",
        )
    )
    db.add(
        CrmAgreement(
            contact_id=addition_only.id,
            project_id=project_id,
            phase_id=UUID(addition["id"]),
            project_group="1812_h_pl",
            source="test",
            source_external_id="mem-301",
            unit_number="301",
        )
    )
    db.add(
        Lead(
            full_name="Lead Member",
            status=LeadStatus.NEW,
            source="test",
            ingest_status="ok",
            project_id=project_id,
            phase_id=UUID(historic["id"]),
            converted_contact_id=lead_person.id,
        )
    )
    db.commit()

    listed = client.get("/crm/contacts", params={"agreement_project": "1812_h_pl", "page_size": 100})
    assert listed.status_code == 200, listed.text
    names = {row["display_name"] for row in listed.json()["items"]}
    assert "Zafer Yıldırım" in names
    assert "Lead Member" in names
    assert "Addition Only" in names
    assert "Unrelated Person" not in names

    historic_only = client.get(
        "/crm/contacts",
        params={"project_id": project["id"], "phase_id": historic["id"], "page_size": 100},
    )
    historic_names = {row["display_name"] for row in historic_only.json()["items"]}
    assert "Zafer Yıldırım" in historic_names
    assert "Lead Member" in historic_names
    assert "Addition Only" not in historic_names

    cleared = client.get("/crm/contacts", params={"page_size": 100})
    cleared_names = {row["display_name"] for row in cleared.json()["items"]}
    assert stranger.display_name in cleared_names
    assert other["project_name"] == "The Temple"


def test_migration_chain_restores_0090_and_adds_0092() -> None:
    versions = ROOT / "alembic" / "versions"
    applied = (versions / "0090_project_phases.py").read_text()
    uniqueness = (versions / "0092_inventory_phase_unit_uniqueness.py").read_text()
    audience = (versions / "0093_budget_version_audience.py").read_text()
    profit = (versions / "0094_funding_contracted_profit.py").read_text()
    assert "uq_inventory_assets_project_building_phase_display" in applied
    assert "uq_inventory_assets_project_phase_display" not in applied
    assert 'down_revision: str | None = "0091_lead_phase_links"' in uniqueness
    assert "UNIQUE NULLS NOT DISTINCT (project_id, phase_id, display_id)" in uniqueness
    assert "find_duplicate_phase_units" in uniqueness
    assert "No unit was renamed" in (ROOT / "src/investhome_api/services/inventory/phase_identity.py").read_text()
    assert 'down_revision: str | None = "0092_inventory_phase_unit_uniqueness"' in audience
    assert 'down_revision: str | None = "0093_budget_version_audience"' in profit
    assert find_duplicate_phase_units is not None


def _investor(db: Session, name: str) -> Investor:
    row = Investor(full_name=name)
    db.add(row)
    db.flush()
    return row


def _funding(db: Session, *, project_id: UUID, investor_id: UUID, status: CommitmentStatus) -> None:
    db.add(
        FundingCommitment(
            project_id=project_id,
            investor_id=investor_id,
            commitment_type=CommitmentType.EQUITY,
            committed_amount=Decimal("100000"),
            status=status,
        )
    )


def test_funding_commitment_membership_is_project_level_and_not_duplicated(
    client: TestClient, db: Session
) -> None:
    reit = _project(client, code="PRJ-MEM-REIT", name="REIT Membership")
    other = _project(client, code="PRJ-MEM-OTHER", name="Other Membership")
    reit_id = UUID(reit["id"])
    other_id = UUID(other["id"])
    historic = client.post(f"/inventory/projects/{reit['id']}/phases", json={"name": "Historic"}).json()
    investor = _investor(db, "REIT Investor")
    other_investor = _investor(db, "Other Investor")
    cancelled_investor = _investor(db, "Cancelled Investor")
    person = _person(db, "REIT Investor")
    person.investor_id = investor.id
    other_person = _person(db, "Other Project Investor")
    other_person.investor_id = other_investor.id
    cancelled_person = _person(db, "Cancelled Funding")
    cancelled_person.investor_id = cancelled_investor.id
    phase_buyer = _person(db, "Historic Buyer")
    asset = InventoryAsset(
        project_id=reit_id,
        phase_id=UUID(historic["id"]),
        display_id="201",
        system_code="MEM-REIT-201",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
    )
    db.add(asset)
    db.flush()
    db.add(
        CrmAgreement(
            contact_id=person.id,
            project_id=reit_id,
            phase_id=UUID(historic["id"]),
            project_group="reit",
            source="test",
            source_external_id="mem-reit-201",
            unit_number="201",
        )
    )
    db.add(
        CrmAgreement(
            contact_id=phase_buyer.id,
            project_id=reit_id,
            phase_id=UUID(historic["id"]),
            project_group="reit",
            source="test",
            source_external_id="mem-reit-buyer",
            unit_number="202",
        )
    )
    db.add(
        InventoryOwnership(
            inventory_asset_id=asset.id,
            party_id=investor.id,
            ownership_type=OwnershipType.LEGAL_OWNER,
            ownership_percentage=Decimal("100"),
            effective_from=date(2026, 1, 1),
            status=OwnershipRecordStatus.ACTIVE,
            acquisition_method=AcquisitionMethod.PURCHASE,
            source=OwnershipSource.INITIAL,
        )
    )
    _funding(db, project_id=reit_id, investor_id=investor.id, status=CommitmentStatus.COMMITTED)
    _funding(db, project_id=other_id, investor_id=other_investor.id, status=CommitmentStatus.FULLY_FUNDED)
    _funding(db, project_id=reit_id, investor_id=cancelled_investor.id, status=CommitmentStatus.CANCELLED)
    db.commit()

    members = person_project_contact_ids(db, project_id=reit_id)
    assert members.count(person.id) == 1
    assert person.id in members
    assert other_person.id not in members
    assert cancelled_person.id not in members

    other_members = person_project_contact_ids(db, project_id=other_id)
    assert other_members == [other_person.id]

    historic_members = person_project_contact_ids(db, project_id=reit_id, phase_id=UUID(historic["id"]))
    assert phase_buyer.id in historic_members
    assert person.id in historic_members
    funding_only = _person(db, "Funding Only")
    funding_only_investor = _investor(db, "Funding Only Investor")
    funding_only.investor_id = funding_only_investor.id
    _funding(db, project_id=reit_id, investor_id=funding_only_investor.id, status=CommitmentStatus.PROPOSED)
    db.commit()
    phased = person_project_contact_ids(db, project_id=reit_id, phase_id=UUID(historic["id"]))
    assert funding_only.id not in phased
    assert funding_only.id in person_project_contact_ids(db, project_id=reit_id)


def test_temple_and_uniloft_membership_stay_on_their_own_links(client: TestClient, db: Session) -> None:
    temple = _project(client, code="PRJ-MEM-TEMPLE", name="The Temple")
    uniloft = _project(client, code="PRJ-MEM-UNILOFT", name="UniLoft")
    temple_id = UUID(temple["id"])
    uniloft_id = UUID(uniloft["id"])
    buyer = _person(db, "Temple Buyer")
    investor = _investor(db, "Uniloft Investor")
    investor_contact = _person(db, "Uniloft Investor")
    investor_contact.investor_id = investor.id
    db.add(
        CrmAgreement(
            contact_id=buyer.id,
            project_id=temple_id,
            project_group="the_temple",
            source="test",
            source_external_id="mem-temple-1",
            unit_number="12",
        )
    )
    _funding(db, project_id=uniloft_id, investor_id=investor.id, status=CommitmentStatus.PARTIALLY_FUNDED)
    db.commit()

    temple_members = person_project_contact_ids(db, project_group="the_temple")
    uniloft_members = person_project_contact_ids(db, project_group="uniloft")
    assert buyer.id in temple_members
    assert investor_contact.id not in temple_members
    assert investor_contact.id in uniloft_members
    assert buyer.id not in uniloft_members
