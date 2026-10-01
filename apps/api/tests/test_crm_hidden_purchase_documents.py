"""Hidden purchase documents are not exposed by include_hidden without privileged document access."""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.document import Document, DocumentLink, DocumentType, StorageProvider
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


DEMO_PASSWORD = "Demo123!"
SALES_EMAIL = "sales@example.com"


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _privileged_user(db: Session) -> str:
    role = Role(name="crm_hidden_docs", code=f"crm_hidden_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    for resource, action in (("crm", "read"), ("documents", "view_confidential")):
        perm = db.query(Permission).filter_by(resource=resource, action=action).one()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    email = f"crm.hidden.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="CRM Hidden Docs",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    return email


def _seed_purchase_with_hidden_doc(db: Session) -> tuple[str, str, str]:
    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        record_kind=CrmRecordKind.PERSON,
        display_name=f"Hidden Doc Owner {uuid4().hex[:6]}",
        status=CrmContactStatus.ACTIVE,
        primary_email=f"hidden.doc.{uuid4().hex[:8]}@example.com",
    )
    db.add(contact)
    db.flush()
    agreement = CrmAgreement(
        contact_id=contact.id,
        project_group="1812_h_pl",
        source="bitrix",
        source_external_id=f"bitrix_deal:{uuid4().hex[:8]}",
        unit_number="101",
    )
    db.add(agreement)
    db.flush()

    visible = Document(
        title="visible_offer.pdf",
        original_file_name="visible_offer.pdf",
        stored_file_name=f"{uuid4()}-visible_offer.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_provider=StorageProvider.LOCAL,
        storage_key=f"crm/{uuid4()}/visible_offer.pdf",
        checksum=f"vis-{uuid4().hex}",
        document_type=DocumentType.OTHER,
        notes=json.dumps({"source_type": "deal_uf"}),
    )
    hidden = Document(
        title="hidden_SWIFT_dekont.pdf",
        original_file_name="hidden_SWIFT_dekont.pdf",
        stored_file_name=f"{uuid4()}-hidden_SWIFT_dekont.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=2048,
        storage_provider=StorageProvider.LOCAL,
        storage_key=f"crm/{uuid4()}/hidden_SWIFT_dekont.pdf",
        checksum=f"hid-{uuid4().hex}",
        document_type=DocumentType.RECEIPT,
        notes=json.dumps({"source_type": "deal_uf"}),
    )
    db.add_all([visible, hidden])
    db.flush()
    db.add(DocumentLink(document_id=visible.id, entity_type="crm_agreement", entity_id=agreement.id))
    db.add(
        DocumentLink(
            document_id=hidden.id,
            entity_type="crm_agreement",
            entity_id=agreement.id,
            hidden_from_view=True,
        )
    )
    db.commit()
    return str(agreement.id), str(visible.id), str(hidden.id)


def _card_doc_ids(payload: dict) -> set[str]:
    ids = {item["id"] for item in payload.get("documents") or []}
    ids.update(item["id"] for item in payload.get("person_documents") or [])
    for group in payload.get("document_groups") or []:
        ids.update(item["id"] for item in group.get("documents") or [])
    return ids


def _card_blob(payload: dict) -> str:
    return json.dumps(payload)


def test_default_purchase_card_omits_hidden_documents(auth_client: TestClient, db: Session) -> None:
    agreement_id, visible_id, hidden_id = _seed_purchase_with_hidden_doc(db)
    _login(auth_client, SALES_EMAIL)
    response = auth_client.get(f"/crm/agreements/{agreement_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    ids = _card_doc_ids(body)
    assert visible_id in ids
    assert hidden_id not in ids
    assert "hidden_SWIFT_dekont.pdf" not in _card_blob(body)


def test_crm_read_cannot_expose_hidden_docs_with_include_hidden(auth_client: TestClient, db: Session) -> None:
    agreement_id, visible_id, hidden_id = _seed_purchase_with_hidden_doc(db)
    _login(auth_client, SALES_EMAIL)
    response = auth_client.get(f"/crm/agreements/{agreement_id}", params={"include_hidden": "true"})
    assert response.status_code == 200, response.text
    body = response.json()
    ids = _card_doc_ids(body)
    assert visible_id in ids
    assert hidden_id not in ids
    blob = _card_blob(body)
    assert "hidden_SWIFT_dekont.pdf" not in blob
    assert hidden_id not in blob


def test_privileged_user_can_include_hidden_purchase_documents(auth_client: TestClient, db: Session) -> None:
    agreement_id, visible_id, hidden_id = _seed_purchase_with_hidden_doc(db)
    email = _privileged_user(db)
    db.commit()
    _login(auth_client, email)
    response = auth_client.get(f"/crm/agreements/{agreement_id}", params={"include_hidden": "true"})
    assert response.status_code == 200, response.text
    body = response.json()
    ids = _card_doc_ids(body)
    assert visible_id in ids
    assert hidden_id in ids
    hidden_row = next(item for item in body["documents"] if item["id"] == hidden_id)
    assert hidden_row["hidden_from_view"] is True
    assert hidden_row["original_file_name"] == "hidden_SWIFT_dekont.pdf"

    default = auth_client.get(f"/crm/agreements/{agreement_id}")
    assert hidden_id not in _card_doc_ids(default.json())
