"""Active agreements, cancellation, and legacy unit snapshots stay separate."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.inventory import InventoryAsset
from investhome_api.models.lead import Lead
from investhome_api.services.crm.agreement_service import list_agreements


def _person(db: Session, name: str) -> CrmContact:
    from investhome_api.models.crm_contact import CrmContactStatus, CrmContactType, CrmRecordKind

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


def test_active_list_hides_cancelled_and_keeps_a_unit_snapshot_without_inventory(db: Session) -> None:
    person = _person(db, "Snapshot Buyer")
    active = CrmAgreement(
        contact_id=person.id,
        project_group="1812_h_pl",
        source="test",
        source_external_id="final-active",
        status=CrmAgreementStatus.ACTIVE,
        unit_number="101",
    )
    cancelled = CrmAgreement(
        contact_id=person.id,
        project_group="1313_penn",
        source="test",
        source_external_id="final-cancelled",
        status=CrmAgreementStatus.CANCELLED,
        unit_number="201",
        cancellation_reason="Vazgeçti",
    )
    db.add_all([active, cancelled])
    db.commit()

    shown, _total = list_agreements(db)
    shown_ids = {item.id for item in shown}
    assert active.id in shown_ids
    assert cancelled.id not in shown_ids
    assert shown_ids
    archived, _archived_total = list_agreements(db, status=CrmAgreementStatus.CANCELLED)
    archived_ids = {item.id for item in archived}
    assert cancelled.id in archived_ids
    assert active.id not in archived_ids
    saved = db.get(CrmAgreement, active.id)
    assert saved is not None
    assert saved.unit_number == "101"
    assert saved.inventory_asset_id is None
    assert db.scalar(select(func.count()).select_from(InventoryAsset)) == 0


def test_cancel_keeps_the_lead_out_of_pipeline(client: TestClient, db: Session) -> None:
    created = client.post("/crm/leads", json={"full_name": "İptal Lead", "source": "manual"})
    assert created.status_code == 201, created.text
    body = created.json()
    lead_id = UUID(body["id"])
    contact_id = UUID(body["contact_id"])
    agreement = CrmAgreement(
        contact_id=contact_id,
        project_group="uniloft",
        source="test",
        source_external_id="final-cancel-lead",
        status=CrmAgreementStatus.ACTIVE,
        unit_number="4",
    )
    db.add(agreement)
    db.commit()
    leads_before = db.scalar(select(func.count()).select_from(Lead))
    people_before = db.scalar(select(func.count()).select_from(CrmContact))
    status_before = db.get(Lead, lead_id).status
    response = client.post(
        f"/crm/agreements/{agreement.id}/cancel",
        json={"reason": "Vazgeçti", "note": "Sonra konuşulacak", "cancelled_on": "2026-11-10"},
    )
    assert response.status_code == 200, response.text
    db.expire_all()
    saved = db.get(CrmAgreement, agreement.id)
    assert saved is not None
    assert saved.status == CrmAgreementStatus.CANCELLED
    assert saved.cancellation_reason == "Vazgeçti"
    assert saved.cancellation_note == "Sonra konuşulacak"
    assert saved.pipeline_returned_at is None
    assert db.get(Lead, lead_id).status == status_before
    assert db.scalar(select(func.count()).select_from(Lead)) == leads_before
    assert db.scalar(select(func.count()).select_from(CrmContact)) == people_before
    shown, _total = list_agreements(db)
    assert agreement.id not in {item.id for item in shown}
