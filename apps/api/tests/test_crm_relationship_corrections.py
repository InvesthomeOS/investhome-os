"""CRM ownership corrections keep contacts and history, and record old/new values."""

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
)
from investhome_api.models.crm_agreement import (
    CrmAgreement,
    CrmAgreementParticipant,
    CrmAgreementStatus,
)
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmRecordKind,
)
from investhome_api.services.crm.known_crm_corrections import apply_known_crm_corrections

DEMO_PASSWORD = "Demo123!"


def _person(
    db: Session,
    name: str,
    contact_type: CrmContactType = CrmContactType.INVESTOR,
    contact_id: UUID | None = None,
) -> CrmContact:
    contact = CrmContact(
        contact_type=contact_type,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        status=CrmContactStatus.ACTIVE,
    )
    if contact_id is not None:
        contact.id = contact_id
    db.add(contact)
    db.flush()
    return contact


def _agreement(
    db: Session,
    contact: CrmContact,
    *,
    project_group: str,
    unit: str | None,
    amount: str | None = None,
    agreement_id: UUID | None = None,
) -> CrmAgreement:
    row = CrmAgreement(
        id=agreement_id or uuid4(),
        contact_id=contact.id,
        project_group=project_group,
        source="test",
        source_external_id=f"corr:{uuid4().hex[:8]}",
        unit_number=unit,
        investment_amount=amount,
        status=CrmAgreementStatus.ACTIVE,
    )
    db.add(row)
    db.flush()
    return row


def _owner(
    db: Session, agreement: CrmAgreement, contact: CrmContact, pct: str, *, primary: bool = False
) -> None:
    db.add(
        CrmAgreementParticipant(
            agreement_id=agreement.id,
            contact_id=contact.id,
            role="owner",
            ownership_pct=Decimal(pct),
            is_primary=primary,
            source="test",
        )
    )
    db.flush()


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def test_add_remove_and_percentage_rules(client: TestClient, db: Session) -> None:
    keeper = _person(db, "Murat Zengin")
    extra = _person(db, "Yesim Zengin")
    third = _person(db, "Third Owner")
    agreement = _agreement(db, keeper, project_group="2319_ontario", unit="101")
    _owner(db, agreement, keeper, "100.00", primary=True)
    db.commit()

    added = client.post(
        f"/crm/agreements/{agreement.id}/owners",
        json={"contact_id": str(extra.id), "ownership_pct": "40"},
    )
    assert added.status_code == 400, added.text

    shares = client.put(
        f"/crm/agreements/{agreement.id}/owners",
        json={
            "owners": [
                {"contact_id": str(keeper.id), "ownership_pct": "60"},
                {"contact_id": str(extra.id), "ownership_pct": "40"},
            ]
        },
    )
    assert shares.status_code == 200, shares.text
    added = shares
    owners = {item["display_name"]: item["ownership_pct"] for item in added.json()["participants"]}
    assert owners["Murat Zengin"].startswith("60")
    assert owners["Yesim Zengin"].startswith("40")

    invalid = client.put(
        f"/crm/agreements/{agreement.id}/owners",
        json={
            "owners": [
                {"contact_id": str(keeper.id), "ownership_pct": "70"},
                {"contact_id": str(extra.id), "ownership_pct": "50"},
            ]
        },
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "invalid_percentage_total"

    full = client.put(
        f"/crm/agreements/{agreement.id}/owners",
        json={"owners": [{"contact_id": str(keeper.id), "ownership_pct": "100"}]},
    )
    assert full.status_code == 200, full.text
    assert [item["display_name"] for item in full.json()["participants"]] == ["Murat Zengin"]

    again = client.put(
        f"/crm/agreements/{agreement.id}/owners",
        json={
            "owners": [
                {"contact_id": str(keeper.id), "ownership_pct": "50"},
                {"contact_id": str(extra.id), "ownership_pct": "50"},
            ]
        },
    )
    assert again.status_code == 200, again.text
    removed = client.delete(f"/crm/agreements/{agreement.id}/owners/{extra.id}")
    assert removed.status_code == 200, removed.text
    participants = removed.json()["participants"]
    assert [item["display_name"] for item in participants] == ["Murat Zengin"]
    assert participants[0]["ownership_pct"].startswith("100")
    assert db.get(CrmContact, extra.id) is not None

    multiple = client.put(
        f"/crm/agreements/{agreement.id}/owners",
        json={
            "owners": [
                {"contact_id": str(keeper.id), "ownership_pct": "75"},
                {"contact_id": str(third.id), "ownership_pct": "25"},
            ]
        },
    )
    assert multiple.status_code == 200, multiple.text
    both = {item["contact_id"]: item["ownership_pct"] for item in multiple.json()["participants"]}
    assert both[str(keeper.id)].startswith("75")
    assert both[str(third.id)].startswith("25")


def test_unlink_preserves_contact_and_activity(client: TestClient, db: Session) -> None:
    person = _person(db, "Vedat Mizrahi")
    agreement = _agreement(
        db,
        person,
        project_group="uniloft",
        unit="204",
        agreement_id=UUID("b1caae99-c1ab-4840-b9d4-730d406b6ade"),
    )
    _owner(db, agreement, person, "100.00", primary=True)
    activity = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=person.id,
        activity_type=CrmActivityType.NOTE,
        activity_category=CrmActivityCategory.NOTE,
        title="Historical note",
        status=CrmActivityStatus.COMPLETED,
        priority=CrmActivityPriority.MEDIUM,
    )
    db.add(activity)
    db.commit()
    activity_id = activity.id

    response = client.delete(f"/crm/agreements/{agreement.id}/owners/{person.id}")
    assert response.status_code == 200, response.text
    assert response.json()["participants"] == []
    db.expire_all()
    assert db.get(CrmContact, person.id) is not None
    assert db.get(CrmActivity, activity_id) is not None
    assert db.get(CrmActivity, activity_id).title == "Historical note"
    refreshed = db.get(CrmAgreement, agreement.id)
    assert refreshed.metadata_json["relationship_detached"] is True
    assert refreshed.contact_id == person.id
    other = _agreement(db, person, project_group="uniloft", unit="101", amount="50000")
    _owner(db, other, person, "100.00", primary=True)
    refreshed.investment_amount = "200000"
    db.commit()

    listed = client.get("/crm/agreements", params={"contact_id": str(person.id)})
    assert listed.status_code == 200, listed.text
    listed_ids = {item["id"] for item in listed.json()["items"]}
    assert str(agreement.id) not in listed_ids
    assert str(other.id) in listed_ids
    detail = client.get(f"/crm/contacts/{person.id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    purchase_ids = {item["agreement_id"] for item in body["purchases"]}
    assert str(agreement.id) not in purchase_ids
    assert str(other.id) in purchase_ids
    agreement_ids = {item["id"] for item in body["crm_agreements"]}
    assert str(agreement.id) not in agreement_ids
    totals = " ".join(item["total"] for item in body["verified_amount_totals"])
    assert "200000" not in totals
    assert "50000" in totals
    card = client.get(f"/crm/agreements/{agreement.id}")
    assert card.status_code == 200, card.text
    assert card.json()["participants"] == []
    assert card.json()["primary_contact_name"] is None
    assert card.json()["owners_label"] in (None, "")


def test_duplicate_relationship_keeps_contact(client: TestClient, db: Session) -> None:
    primary = _person(db, "Gökhan Bülbül")
    duplicate = _person(db, "Gokhan Bulbul")
    other = _person(db, "Semrin Bülbül")
    agreement = _agreement(
        db,
        primary,
        project_group="1812_h_pl",
        unit="306",
        agreement_id=UUID("7f5aa305-04a4-49f6-923b-4b7a560dbfa4"),
    )
    _owner(db, agreement, primary, "50.00", primary=True)
    _owner(db, agreement, duplicate, "25.00")
    _owner(db, agreement, other, "25.00")
    db.commit()

    response = client.post(f"/crm/agreements/{agreement.id}/owners/duplicates")
    assert response.status_code == 200, response.text
    names = sorted(item["display_name"] for item in response.json()["participants"])
    assert names == ["Gökhan Bülbül", "Semrin Bülbül"]
    assert db.get(CrmContact, duplicate.id) is not None
    assert db.get(CrmContact, duplicate.id).display_name == "Gokhan Bulbul"


def test_archive_and_restore_agent(client: TestClient, db: Session) -> None:
    agent = _person(db, "Kurtuluş Göksu", CrmContactType.BROKER)
    buyer = _person(db, "Not An Agent")
    db.commit()

    denied = client.post(f"/crm/agents/{buyer.id}/archive")
    assert denied.status_code == 400
    assert denied.json()["detail"] == "not_agent"

    archived = client.post(f"/crm/agents/{agent.id}/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    db.expire_all()
    assert db.get(CrmContact, agent.id).status == CrmContactStatus.ARCHIVED
    again = client.post(f"/crm/agents/{agent.id}/archive")
    assert again.json()["status"] == "already_archived"
    active = client.get("/crm/contacts", params={"contact_types": "broker"})
    assert active.status_code == 200, active.text
    assert str(agent.id) not in {item["id"] for item in active.json()["items"]}

    restored = client.post(f"/crm/agents/{agent.id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "restored"
    db.expire_all()
    assert db.get(CrmContact, agent.id).status == CrmContactStatus.ACTIVE
    assert db.get(CrmContact, agent.id).archived_at is None


def test_permission_denied_for_unauthorized_user(auth_client: TestClient, db: Session) -> None:
    keeper = _person(db, "Owner")
    agreement = _agreement(db, keeper, project_group="uniloft", unit="A")
    _owner(db, agreement, keeper, "100.00", primary=True)
    db.commit()
    _login(auth_client, "readonly@example.com")
    response = auth_client.post(
        f"/crm/agreements/{agreement.id}/owners",
        json={"contact_id": str(uuid4()), "ownership_pct": "10"},
    )
    assert response.status_code == 403
    assert auth_client.patch(
        f"/crm/agreements/{agreement.id}/unit",
        json={"unit_number": "B"},
    ).status_code == 403
    assert auth_client.get("/crm/corrections/known/preview").status_code == 403


def test_sales_can_correct_purchases_but_not_known_package(
    auth_client: TestClient, db: Session
) -> None:
    from investhome_api.config.permissions_config import DEFAULT_ROLE_PERMISSIONS

    assert ("crm", "correct_relationships") in DEFAULT_ROLE_PERMISSIONS["executive"]
    assert ("crm", "correct_relationships") in DEFAULT_ROLE_PERMISSIONS["investor_relations"]
    assert ("crm", "correct_relationships") in DEFAULT_ROLE_PERMISSIONS["super_admin"]
    assert ("crm", "correct_relationships") not in DEFAULT_ROLE_PERMISSIONS["sales"]
    assert ("crm", "edit_ownership") in DEFAULT_ROLE_PERMISSIONS["sales"]
    assert ("crm", "update") in DEFAULT_ROLE_PERMISSIONS["sales"]

    person = _person(db, "Ada Buyer")
    extra = _person(db, "Ada Buyer")
    duplicate = _person(db, "Ada Buyer")
    agreement = _agreement(db, person, project_group="uniloft", unit="A")
    _owner(db, agreement, person, "100.00", primary=True)
    note = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=person.id,
        activity_type=CrmActivityType.NOTE,
        activity_category=CrmActivityCategory.NOTE,
        title="Keep after unit change",
        status=CrmActivityStatus.COMPLETED,
        priority=CrmActivityPriority.MEDIUM,
    )
    db.add(note)
    db.commit()
    note_id = note.id

    _login(auth_client, "sales@example.com")
    edited = auth_client.patch(
        f"/crm/contacts/{person.id}",
        json={
            "first_name": "Ada",
            "last_name": "Buyer",
            "display_name": "Ada Buyer Updated",
            "primary_email": "ada.buyer@example.com",
            "primary_phone": "+12025550100",
            "organization_name": "Buyer LLC",
        },
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()["contact"]
    assert body["display_name"] == "Ada Buyer Updated"
    assert body["primary_email"] == "ada.buyer@example.com"
    assert body["organization_name"] == "Buyer LLC"

    moved = auth_client.patch(
        f"/crm/agreements/{agreement.id}/unit",
        json={"unit_number": "B"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["unit_number"] == "B"
    db.expire_all()
    stored = db.get(CrmAgreement, agreement.id)
    assert stored.unit_number == "B"
    assert stored.contact_id == person.id
    assert db.get(CrmContact, person.id) is not None
    assert db.get(CrmActivity, note_id).title == "Keep after unit change"
    unit_log = db.scalar(
        select(ActivityLog).where(
            ActivityLog.entity_id == agreement.id,
            ActivityLog.description_key == "crm.correction.unit_changed",
        )
    )
    assert unit_log is not None
    assert unit_log.previous_values["unit_number"] == "A"
    assert unit_log.new_values["unit_number"] == "B"
    assert unit_log.actor_user_id is not None

    added = auth_client.post(
        f"/crm/agreements/{agreement.id}/owners",
        json={"contact_id": str(extra.id), "ownership_pct": "40"},
    )
    assert added.status_code == 400
    shares = auth_client.put(
        f"/crm/agreements/{agreement.id}/owners",
        json={
            "owners": [
                {"contact_id": str(person.id), "ownership_pct": "60"},
                {"contact_id": str(extra.id), "ownership_pct": "40"},
            ]
        },
    )
    assert shares.status_code == 200, shares.text
    removed = auth_client.delete(f"/crm/agreements/{agreement.id}/owners/{extra.id}")
    assert removed.status_code == 200, removed.text
    assert len(removed.json()["participants"]) == 1

    person.display_name = "Ada Buyer"
    duplicate.display_name = "Ada Buyer"
    _owner(db, agreement, duplicate, "50.00")
    db.commit()
    cleaned = auth_client.post(f"/crm/agreements/{agreement.id}/owners/duplicates")
    assert cleaned.status_code == 200, cleaned.text
    assert db.get(CrmContact, duplicate.id) is not None

    assert auth_client.get("/crm/corrections/known/preview").status_code == 403
    assert auth_client.post("/crm/corrections/known").status_code == 403

    _login(auth_client, "admin@example.com")
    preview = auth_client.get("/crm/corrections/known/preview")
    assert preview.status_code == 200, preview.text
    assert isinstance(preview.json()["results"], list)


def test_audit_records_old_and_new_values(client: TestClient, db: Session) -> None:
    keeper = _person(db, "Bahar Basara")
    extra = _person(db, "Gizem Basara")
    agreement = _agreement(db, keeper, project_group="2319_ontario", unit="002")
    _owner(db, agreement, keeper, "50.00", primary=True)
    _owner(db, agreement, extra, "50.00")
    db.commit()

    response = client.delete(f"/crm/agreements/{agreement.id}/owners/{extra.id}")
    assert response.status_code == 200, response.text
    logs = list(
        db.scalars(
            select(ActivityLog).where(
                ActivityLog.entity_id == agreement.id,
                ActivityLog.description_key == "crm.correction.ownership_removed",
            )
        ).all()
    )
    assert logs
    assert logs[-1].previous_values["display_name"] == "Gizem Basara"
    assert logs[-1].previous_values["ownership_pct"].startswith("50")
    assert logs[-1].new_values["contact_preserved"] is True
    assert logs[-1].metadata_json["correction_action"] == "ownership_removed"


def test_transaction_rollback_keeps_owner(db: Session) -> None:
    keeper = _person(db, "Alper Levi")
    extra = _person(db, "Selim Levi Beceren")
    agreement = _agreement(db, keeper, project_group="1307_k_st", unit="302")
    _owner(db, agreement, keeper, "50.00", primary=True)
    _owner(db, agreement, extra, "50.00")
    db.commit()
    nested = db.begin_nested()
    from investhome_api.services.crm.relationship_corrections import remove_agreement_owner

    remove_agreement_owner(db, agreement.id, extra.id, actor=None)
    assert (
        db.scalar(
            select(CrmAgreementParticipant).where(CrmAgreementParticipant.contact_id == extra.id)
        )
        is None
    )
    nested.rollback()
    assert (
        db.scalar(
            select(CrmAgreementParticipant).where(CrmAgreementParticipant.contact_id == extra.id)
        )
        is not None
    )


def test_known_corrections_are_idempotent_and_skip_ambiguity(db: Session) -> None:
    murat = _person(db, "Murat Zengin")
    yesim = _person(db, "Yeşim Zengin")
    ontario = _agreement(
        db,
        murat,
        project_group="2319_ontario",
        unit="101",
        agreement_id=UUID("db40cd62-2ff1-475f-a603-af9a2a139062"),
    )
    _owner(db, ontario, murat, "50.00", primary=True)
    _owner(db, ontario, yesim, "50.00")

    gokhan = _person(db, "Gökhan Bülbül")
    gokhan_copy = _person(db, "Gokhan Bulbul")
    semrin = _person(db, "Semrin Bülbül")
    place = _agreement(
        db,
        gokhan,
        project_group="1812_h_pl",
        unit="306",
        agreement_id=UUID("7f5aa305-04a4-49f6-923b-4b7a560dbfa4"),
    )
    _owner(db, place, gokhan, "40.00", primary=True)
    _owner(db, place, gokhan_copy, "30.00")
    _owner(db, place, semrin, "30.00")

    vedat = _person(db, "Vedat Mizrahi")
    note = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=vedat.id,
        activity_type=CrmActivityType.EMAIL,
        activity_category=CrmActivityCategory.COMMUNICATION,
        title="Keep this email",
        status=CrmActivityStatus.COMPLETED,
        priority=CrmActivityPriority.MEDIUM,
    )
    db.add(note)
    uniloft = _agreement(
        db,
        vedat,
        project_group="uniloft",
        unit="204",
        agreement_id=UUID("b1caae99-c1ab-4840-b9d4-730d406b6ade"),
    )
    _owner(db, uniloft, vedat, "100.00", primary=True)

    decoy = _person(db, "Musa Cobaner", CrmContactType.REALTOR)
    agent = _person(
        db,
        "Musa Acenta Danışmanı 1",
        CrmContactType.BROKER,
        contact_id=UUID("6f809981-a5a7-4956-a0e8-2f1a7ba4f510"),
    )
    wrong_project = _agreement(
        db,
        murat,
        project_group="uniloft",
        unit="101",
        agreement_id=UUID("1ab68f53-2f72-457b-8ea3-b59572b1d507"),
    )
    _owner(db, wrong_project, murat, "100.00", primary=True)
    db.commit()
    note_id = note.id

    first = {item["key"]: item["status"] for item in apply_known_crm_corrections(db, actor=None)}
    db.commit()
    assert first["2319-unit-101"] == "applied"
    assert first["1812-unit-306"] == "applied"
    assert first["uniloft-unit-204"] == "applied"
    assert first["agent-musa-cobaner"] == "applied"
    assert first["2319-unit-002"] == "ambiguous"
    assert db.get(CrmContact, yesim.id) is not None
    assert db.get(CrmContact, gokhan_copy.id) is not None
    assert db.get(CrmContact, vedat.id) is not None
    assert db.get(CrmActivity, note_id).title == "Keep this email"
    archived = db.get(CrmContact, agent.id)
    assert archived.status == CrmContactStatus.ARCHIVED
    assert archived.display_name == "Musa Acenta Danışmanı 1"
    assert db.get(CrmContact, decoy.id).status == CrmContactStatus.ACTIVE
    murat_row = db.scalar(
        select(CrmAgreementParticipant).where(
            CrmAgreementParticipant.agreement_id == ontario.id,
            CrmAgreementParticipant.contact_id == murat.id,
        )
    )
    assert murat_row.ownership_pct == Decimal("100.00")
    assert (
        db.scalar(
            select(CrmAgreementParticipant).where(
                CrmAgreementParticipant.agreement_id == wrong_project.id
            )
        ).contact_id
        == murat.id
    )

    second = {item["key"]: item["status"] for item in apply_known_crm_corrections(db, actor=None)}
    assert second["2319-unit-101"] == "already_applied"
    assert second["uniloft-unit-204"] == "already_applied"
    assert second["agent-musa-cobaner"] == "already_applied"
    assert second["1812-unit-306"] == "no_duplicate"
    assert second["2319-unit-002"] == "ambiguous"


def test_known_correction_preview_does_not_write(client: TestClient, db: Session) -> None:
    murat = _person(db, "Murat Zengin")
    yesim = _person(db, "Yeşim Zengin")
    ontario = _agreement(
        db,
        murat,
        project_group="2319_ontario",
        unit="101",
        agreement_id=UUID("db40cd62-2ff1-475f-a603-af9a2a139062"),
    )
    _owner(db, ontario, murat, "50.00", primary=True)
    _owner(db, ontario, yesim, "50.00")
    vedat = _person(db, "Vedat Mizrahi")
    uniloft = _agreement(
        db,
        vedat,
        project_group="uniloft",
        unit="204",
        agreement_id=UUID("b1caae99-c1ab-4840-b9d4-730d406b6ade"),
    )
    _owner(db, uniloft, vedat, "100.00", primary=True)
    agent = _person(
        db,
        "Musa Acenta Danışmanı 1",
        CrmContactType.BROKER,
        contact_id=UUID("6f809981-a5a7-4956-a0e8-2f1a7ba4f510"),
    )
    db.commit()
    before = db.scalar(select(func.count()).select_from(ActivityLog)) or 0

    response = client.get("/crm/corrections/known/preview")
    assert response.status_code == 200, response.text
    by_key = {item["key"]: item for item in response.json()["results"]}
    ontario_plan = by_key["2319-unit-101"]
    assert ontario_plan["status"] == "ready"
    assert ontario_plan["agreement_id"] == str(ontario.id)
    assert [item["display_name"] for item in ontario_plan["intended"]["remove"]] == ["Yeşim Zengin"]
    assert ontario_plan["intended"]["keep"][0]["ownership_pct"] == "100.00"
    uniloft_plan = by_key["uniloft-unit-204"]
    assert uniloft_plan["status"] == "ready"
    assert uniloft_plan["contact_id"] == str(vedat.id)
    assert uniloft_plan["intended"]["active_purchaser"] is False
    assert uniloft_plan["intended"]["contact_preserved"] is True
    musa_plan = by_key["agent-musa-cobaner"]
    assert musa_plan["status"] == "ready"
    assert musa_plan["contact_id"] == "6f809981-a5a7-4956-a0e8-2f1a7ba4f510"
    assert musa_plan["contact_id"] == str(agent.id)
    assert musa_plan["current"]["display_name"] == "Musa Acenta Danışmanı 1"
    assert musa_plan["current"]["status"] == "active"
    assert musa_plan["intended"]["action"] == "archive"
    assert by_key["2319-unit-002"]["status"] == "not_found"

    db.expire_all()
    assert db.scalar(select(func.count()).select_from(ActivityLog)) == before
    still = db.scalar(
        select(CrmAgreementParticipant).where(
            CrmAgreementParticipant.agreement_id == ontario.id,
            CrmAgreementParticipant.contact_id == yesim.id,
        )
    )
    assert still is not None
    assert still.ownership_pct == Decimal("50.00")
    assert db.get(CrmContact, agent.id).status == CrmContactStatus.ACTIVE
    assert db.get(CrmAgreement, uniloft.id).status == CrmAgreementStatus.ACTIVE
