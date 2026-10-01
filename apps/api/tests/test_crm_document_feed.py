"""CRM document hub: checksum dedupe, historical units, hide without new links."""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentLink,
    DocumentType,
    DocumentVisibility,
    StorageProvider,
)
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


def _contact(db: Session, name: str) -> CrmContact:
    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        status=CrmContactStatus.ACTIVE,
        primary_email=f"{uuid4().hex[:8]}@example.com",
    )
    db.add(contact)
    db.flush()
    return contact


def _document(
    db: Session,
    *,
    filename: str,
    checksum: str,
    notes: dict,
    mime: str = "application/pdf",
    bitrix_file_id: str | None = None,
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.INTERNAL,
    visibility: DocumentVisibility = DocumentVisibility.ORGANIZATION,
    owner_user_id=None,
    document_type: DocumentType = DocumentType.OTHER,
) -> Document:
    payload = dict(notes)
    if bitrix_file_id:
        payload["bitrix_file_id"] = bitrix_file_id
    doc = Document(
        title=filename,
        original_file_name=filename,
        stored_file_name=f"{uuid4()}-{filename}",
        file_extension=filename.rsplit(".", 1)[-1][:20],
        mime_type=mime,
        file_size=2048,
        storage_provider=StorageProvider.LOCAL,
        storage_key=f"crm/{uuid4()}/{filename}",
        checksum=checksum,
        document_type=document_type,
        confidentiality_level=confidentiality,
        visibility=visibility,
        owner_user_id=owner_user_id,
        notes=json.dumps(payload),
    )
    db.add(doc)
    db.flush()
    return doc


def _link(db: Session, document: Document, entity_type: str, entity_id) -> DocumentLink:
    link = DocumentLink(document_id=document.id, entity_type=entity_type, entity_id=entity_id)
    db.add(link)
    db.flush()
    return link


def test_document_feed_classifies_dedupes_and_protects_historical_units(client: TestClient, db: Session) -> None:
    person = _contact(db, "Semra Feed")
    co_owner = _contact(db, "Co-owner Feed")
    deal_id = uuid4().hex[:10]
    agreement = CrmAgreement(
        contact_id=person.id,
        project_group="1812_h_pl",
        source="bitrix",
        source_external_id=f"bitrix_deal:{deal_id}",
        unit_number="307",
    )
    db.add(agreement)
    db.flush()

    checksum_passport = f"pass-{uuid4().hex}"
    checksum_shared = f"sum-{uuid4().hex}"
    checksum_open = f"open-{uuid4().hex}"
    file_id = f"bx-{uuid4().hex[:8]}"

    passport = _document(db, filename="Semra_pasaport.pdf", checksum=checksum_passport, notes={"source_type": "activity"})
    _link(db, passport, "crm_contact", person.id)
    _link(db, passport, "crm_agreement", agreement.id)

    purchase = _document(
        db,
        filename="1812 H PL B07 SWIFT.pdf",
        checksum=checksum_shared,
        notes={"source_type": "deal_uf", "bitrix_entity_type": "deal", "bitrix_entity_id": deal_id},
        bitrix_file_id=file_id,
    )
    _link(db, purchase, "crm_contact", person.id)
    _link(db, purchase, "crm_agreement", agreement.id)

    duplicate = _document(
        db,
        filename="1812 H PL B07 SWIFT copy.pdf",
        checksum=checksum_shared,
        notes={"source_type": "activity"},
        bitrix_file_id=file_id,
    )
    _link(db, duplicate, "crm_contact", co_owner.id)

    unresolved = _document(
        db,
        filename="1812_H_PL_B08_unknown.pdf",
        checksum=checksum_open,
        notes={"source_type": "activity"},
    )
    _link(db, unresolved, "crm_contact", person.id)
    db.commit()

    body = client.get("/crm/documents/feed?visibility=all&person=Semra%20Feed&page_size=50").json()
    assert client.get("/crm/documents/feed?visibility=all&person=Semra%20Feed").status_code == 200
    passport_row = next(item for item in body["items"] if item["checksum"] == checksum_passport)
    swift = next(item for item in body["items"] if item["checksum"] == checksum_shared)
    open_row = next(item for item in body["items"] if item["checksum"] == checksum_open)

    assert passport_row["scope"] == "person"
    assert passport_row["agreement_id"] is None
    assert passport_row["category"] == "passport"
    assert len([item for item in body["items"] if item["checksum"] == checksum_shared]) == 1
    assert swift["scope"] == "purchase"
    assert swift["historical_unit"] == "B07"
    assert swift["current_unit"] == "307"
    assert swift["unit_number"] == "B07"
    assert swift["agreement_id"] == str(agreement.id)
    assert "307" not in (swift["project_unit"] or "")
    assert open_row["scope"] == "unresolved"
    assert open_row["agreement_id"] is None
    assert open_row["unit_number"] == "B08"
    assert body["stats"]["unresolved"] >= 1
    assert body["stats"]["person"] >= 1
    assert body["stats"]["purchase"] >= 1
    assert body["stats"]["total"] >= 3

    person_only = client.get("/crm/documents/feed?person=Semra%20Feed&visibility=all")
    assert person_only.status_code == 200
    names = {item["contact_name"] for item in person_only.json()["items"]}
    assert "Semra Feed" in names
    assert "Co-owner Feed" not in names

    unresolved_only = client.get("/crm/documents/feed?scope=unresolved&visibility=all&search=1812_H_PL_B08_unknown")
    assert unresolved_only.status_code == 200
    assert any(item["checksum"] == checksum_open for item in unresolved_only.json()["items"])


def test_document_hub_hide_updates_existing_links_only(client: TestClient, db: Session) -> None:
    person = _contact(db, "Hide Person")
    agreement = CrmAgreement(
        contact_id=person.id,
        project_group="1812_h_pl",
        source="bitrix",
        source_external_id=f"bitrix_deal:{uuid4().hex[:8]}",
        unit_number="101",
    )
    db.add(agreement)
    db.flush()
    doc = _document(db, filename="Operating Agreement.pdf", checksum="hide-1", notes={"source_type": "deal_uf"})
    _link(db, doc, "crm_contact", person.id)
    _link(db, doc, "crm_agreement", agreement.id)
    db.commit()

    before = list(db.scalars(select(DocumentLink).where(DocumentLink.document_id == doc.id)).all())
    assert len(before) == 2
    hidden = client.post(f"/crm/documents/{doc.id}/hub-visibility", json={"hidden": True})
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["updated_links"] == 2
    assert hidden.json()["hidden"] is True
    db.expire_all()
    after = list(db.scalars(select(DocumentLink).where(DocumentLink.document_id == doc.id)).all())
    assert len(after) == 2
    assert all(link.hidden_from_view for link in after)

    listed = client.get("/crm/documents/feed?visibility=hidden")
    assert listed.status_code == 200
    assert any(item["id"] == str(doc.id) for item in listed.json()["items"])
    assert listed.json()["stats"]["hidden"] >= 1

    restored = client.post(f"/crm/documents/{doc.id}/hub-visibility", json={"hidden": False})
    assert restored.status_code == 200
    db.expire_all()
    visible = list(db.scalars(select(DocumentLink).where(DocumentLink.document_id == doc.id)).all())
    assert len(visible) == 2
    assert all(not link.hidden_from_view for link in visible)
    assert db.get(Document, doc.id) is not None


DEMO_PASSWORD = "Demo123!"
SALES_EMAIL = "sales@example.com"


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _user_with_permissions(db: Session, pairs: list[tuple[str, str]]) -> str:
    role = Role(name="crm_docs_role", code=f"crm_docs_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    for resource, action in pairs:
        perm = db.query(Permission).filter_by(resource=resource, action=action).one()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    email = f"crm.docs.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="CRM Docs User",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    return email


def _seed_mixed_feed(db: Session) -> dict[str, Document]:
    person = _contact(db, "Feed Privacy Person")
    other_owner = User(
        email=f"doc.owner.{uuid4().hex[:8]}@example.com",
        full_name="Doc Owner",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(other_owner)
    db.flush()
    internal = _document(db, filename="internal_offer.pdf", checksum=f"int-{uuid4().hex}", notes={"source_type": "activity"})
    passport = _document(
        db,
        filename="Feed_pasaport.pdf",
        checksum=f"pass-{uuid4().hex}",
        notes={"source_type": "activity", "bitrix_field_label": "Pasaport"},
        confidentiality=ConfidentialityLevel.HIGHLY_CONFIDENTIAL,
    )
    payment = _document(
        db,
        filename="SWIFT_dekont.pdf",
        checksum=f"pay-{uuid4().hex}",
        notes={"source_type": "deal_uf"},
        confidentiality=ConfidentialityLevel.CONFIDENTIAL,
        document_type=DocumentType.RECEIPT,
    )
    legal = _document(
        db,
        filename="operating_agreement_legal.pdf",
        checksum=f"leg-{uuid4().hex}",
        notes={"source_type": "deal_uf"},
        confidentiality=ConfidentialityLevel.CONFIDENTIAL,
        document_type=DocumentType.LEGAL_DOCUMENT,
    )
    private = _document(
        db,
        filename="private_restricted.pdf",
        checksum=f"priv-{uuid4().hex}",
        notes={"source_type": "activity"},
        visibility=DocumentVisibility.PRIVATE,
        owner_user_id=other_owner.id,
    )
    for doc in (internal, passport, payment, legal, private):
        _link(db, doc, "crm_contact", person.id)
    db.commit()
    return {
        "internal": internal,
        "passport": passport,
        "payment": payment,
        "legal": legal,
        "private": private,
    }


def _feed_payload(client: TestClient) -> dict:
    response = client.get("/crm/documents/feed?visibility=all&page_size=100")
    assert response.status_code == 200, response.text
    return response.json()


def _feed_ids(payload: dict) -> set[str]:
    return {item["id"] for item in payload["items"]}


def _feed_filenames(payload: dict) -> set[str]:
    names = set()
    for item in payload["items"]:
        names.add(item.get("filename") or "")
        names.add(item.get("title") or "")
        names.add(item.get("category") or "")
        names.add(item.get("contact_name") or "")
    return names


def test_crm_read_without_document_view_omits_confidential_feed(auth_client: TestClient, db: Session) -> None:
    seeded = _seed_mixed_feed(db)
    email = _user_with_permissions(db, [("crm", "read")])
    db.commit()
    _login(auth_client, email)

    payload = _feed_payload(auth_client)
    ids = _feed_ids(payload)
    names = _feed_filenames(payload)
    for key in ("internal", "passport", "payment", "legal", "private"):
        assert str(seeded[key].id) not in ids
    assert "Feed_pasaport.pdf" not in names
    assert "SWIFT_dekont.pdf" not in names
    assert "operating_agreement_legal.pdf" not in names
    assert "private_restricted.pdf" not in names
    assert payload["stats"]["total"] == 0


def test_document_viewer_sees_permitted_internal_only(auth_client: TestClient, db: Session) -> None:
    seeded = _seed_mixed_feed(db)
    _login(auth_client, SALES_EMAIL)

    payload = _feed_payload(auth_client)
    ids = _feed_ids(payload)
    names = _feed_filenames(payload)
    assert str(seeded["internal"].id) in ids
    assert str(seeded["passport"].id) not in ids
    assert str(seeded["payment"].id) not in ids
    assert str(seeded["legal"].id) not in ids
    assert str(seeded["private"].id) not in ids
    assert "Feed_pasaport.pdf" not in names
    assert "SWIFT_dekont.pdf" not in names
    assert "passport" not in {item.get("category") for item in payload["items"] if item["id"] == str(seeded["passport"].id)}

    assert auth_client.get(f"/documents/{seeded['internal'].id}").status_code == 200
    assert auth_client.get(f"/documents/{seeded['passport'].id}").status_code == 404
    assert auth_client.get(f"/documents/{seeded['payment'].id}").status_code == 404
    assert auth_client.get(f"/documents/{seeded['legal'].id}").status_code == 404
    assert auth_client.get(f"/documents/{seeded['private'].id}").status_code == 404


def test_confidential_document_user_sees_allowed_feed_entries(auth_client: TestClient, db: Session) -> None:
    seeded = _seed_mixed_feed(db)
    email = _user_with_permissions(
        db,
        [
            ("crm", "read"),
            ("documents", "view"),
            ("documents", "view_confidential"),
            ("documents", "view_highly_confidential"),
        ],
    )
    db.commit()
    _login(auth_client, email)

    payload = _feed_payload(auth_client)
    ids = _feed_ids(payload)
    assert str(seeded["internal"].id) in ids
    assert str(seeded["passport"].id) in ids
    assert str(seeded["payment"].id) in ids
    assert str(seeded["legal"].id) in ids
    assert str(seeded["private"].id) not in ids
    passport_row = next(item for item in payload["items"] if item["id"] == str(seeded["passport"].id))
    payment_row = next(item for item in payload["items"] if item["id"] == str(seeded["payment"].id))
    assert passport_row["filename"] == "Feed_pasaport.pdf"
    assert passport_row["category"] == "passport"
    assert payment_row["filename"] == "SWIFT_dekont.pdf"
    assert payment_row["category"] == "payment"

    assert auth_client.get(f"/documents/{seeded['passport'].id}").status_code == 200
    assert auth_client.get(f"/documents/{seeded['payment'].id}").status_code == 200
    assert auth_client.get(f"/documents/{seeded['private'].id}").status_code == 404
