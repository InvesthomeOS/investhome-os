"""CRM matches review — live evidence, no destructive merge."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.contact_service import create_contact


def _person(db: Session, name: str, **fields: object) -> CrmContact:
    payload = CrmContactCreate(
        display_name=name,
        contact_type="prospect",
        record_kind="person",
        **fields,
    )
    return create_contact(db, payload)


def test_crm_matches_empty_kpis_are_zero(client: TestClient) -> None:
    response = client.get("/crm/matches")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == []
    assert body["kpis"] == {
        "pending": 0,
        "strong": 0,
        "possible": 0,
        "rejected": 0,
        "same_person": 0,
    }


def test_crm_matches_phone_email_name_and_decision_does_not_merge(
    client: TestClient, db: Session
) -> None:
    _person(db, "Ada Phone One", primary_phone="+905551000001", primary_email="ada.one@example.com")
    _person(db, "Ada Phone Two", primary_phone="+90 555 100 00 01", primary_email="ada.two@example.com")
    _person(
        db,
        "Name Only One",
        primary_email="name.one@example.com",
        primary_phone="+905551000111",
    )
    _person(
        db,
        "Name Only One",
        primary_email="name.two@example.com",
        primary_phone="+905551000222",
    )
    db.commit()

    listed = client.get("/crm/matches")
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    kpis = listed.json()["kpis"]
    phone_row = next(item for item in items if "phone" in item["reasons"])
    assert phone_row["match_kind"] == "strong"
    assert phone_row["shared_phone"]
    assert kpis["strong"] >= 1
    name_row = next(item for item in items if item["reasons"] == ["name_review"])
    assert name_row["match_kind"] == "possible"

    accepted = client.post(
        f"/crm/matches/{phone_row['id']}/decision",
        json={"action": "same_person", "notes": "Reviewer decision"},
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "same_person"
    assert body["merge_queued"] is False
    assert body["merge_blocked"] is True
    assert "birleştirilmedi" in body["merge_message"].lower() or "birleştirme" in body["merge_message"].lower()

    db.expire_all()
    left = db.get(CrmContact, UUID(phone_row["person_a_id"]))
    right = db.get(CrmContact, UUID(phone_row["person_b_id"]))
    assert left is not None and right is not None
    assert left.archived_at is None
    assert right.archived_at is None
    assert left.status != CrmContactStatus.ARCHIVED
    assert right.status != CrmContactStatus.ARCHIVED

    rejected = client.post(f"/crm/matches/{name_row['id']}/decision", json={"action": "different"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "different"

    filtered = client.get("/crm/matches", params={"status": "different"})
    assert any(item["id"] == name_row["id"] for item in filtered.json()["items"])
    search = client.get("/crm/matches", params={"search": "Ada Phone"})
    assert search.status_code == 200
    assert any(item["id"] == phone_row["id"] for item in search.json()["items"])


def test_crm_matches_protects_known_identities_and_review_flag(
    client: TestClient, db: Session
) -> None:
    first = _person(
        db,
        "Gökhan Bülbül",
        primary_phone="+905551000301",
        primary_email="gokhan.a@example.com",
    )
    second = _person(
        db,
        "Gökhan Bülbül",
        primary_phone="+905551000302",
        primary_email="gokhan.b@example.com",
    )
    db.add(
        CrmAgreement(
            contact_id=first.id,
            project_group="1812",
            unit_number="306",
            source="bitrix",
            source_external_id="1812-306-a",
        )
    )
    db.add(
        CrmAgreement(
            contact_id=second.id,
            project_group="1812",
            unit_number="H 306",
            source="bitrix",
            source_external_id="1812-306-b",
        )
    )
    selim = _person(
        db,
        "Selim Levi Beceren",
        primary_phone="+905323617374",
        primary_email="sunnylevy@example.com",
    )
    levi = _person(
        db,
        "Levi Sunny",
        primary_phone="+90 532 361 73 74",
        primary_email="sunny.levi@example.com",
    )
    flagged = _person(
        db,
        "Flagged Twin A",
        primary_phone="+905551000401",
        notes="INCELEME_GEREKLI keep separate",
    )
    flagged_b = _person(
        db,
        "Flagged Twin B",
        primary_phone="+905551000401",
    )
    flagged_b.review_required = True
    db.commit()

    listed = client.get("/crm/matches")
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]

    gokhan = next(
        item
        for item in items
        if {item["person_a_id"], item["person_b_id"]} == {str(first.id), str(second.id)}
    )
    assert gokhan["protected"] is True
    assert gokhan["match_kind"] == "possible"
    same = client.post(f"/crm/matches/{gokhan['id']}/decision", json={"action": "same_person"})
    assert same.status_code == 200
    assert same.json()["merge_queued"] is False
    assert same.json()["protected"] is True
    db.expire_all()
    assert db.get(CrmContact, first.id).archived_at is None
    assert db.get(CrmContact, second.id).archived_at is None

    levi_row = next(
        item for item in items if {item["person_a_id"], item["person_b_id"]} == {str(selim.id), str(levi.id)}
    )
    assert levi_row["protected"] is True
    assert "phone" in levi_row["reasons"]
    held = client.post(f"/crm/matches/{levi_row['id']}/decision", json={"action": "in_review"})
    assert held.status_code == 200
    assert held.json()["status"] == "in_review"

    flagged_row = next(
        item
        for item in items
        if {item["person_a_id"], item["person_b_id"]} == {str(flagged.id), str(flagged_b.id)}
    )
    assert flagged_row["protected"] is True

    detail = client.get(f"/crm/matches/{gokhan['id']}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["person_a"]["purchases"]
    assert payload["person_b"]["purchases"]
    assert payload["merge_blocked"] is True
    type_filter = client.get("/crm/matches", params={"match_type": "phone"})
    assert type_filter.status_code == 200
    assert all("phone" in item["reasons"] for item in type_filter.json()["items"])
