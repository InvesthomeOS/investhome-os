"""STEP 5 person-card editing: canonical Contact / Agreement / Document sources."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _create_person(client: TestClient, **overrides) -> dict:
    payload = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": f"Person Card {uuid4().hex[:6]}",
        "primary_email": f"person.card.{uuid4().hex[:8]}@example.com",
        "lifecycle_stage": "new",
        "priority": "normal",
    }
    payload.update(overrides)
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["contact"]


def test_person_card_patch_identity_and_buyer_budget(client: TestClient) -> None:
    contact = _create_person(client)
    response = client.patch(
        f"/crm/contacts/{contact['id']}",
        json={
            "first_name": "Ayşe",
            "last_name": "Yılmaz",
            "country": "TR",
            "whatsapp": "0532 111 22 33",
            "communication_prefs": {"language": "tr"},
            "buyer_profile": {"budget_min": 150000, "budget_max": 275000},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()["contact"]
    assert body["first_name"] == "Ayşe"
    assert body["last_name"] == "Yılmaz"
    assert body["display_name"] == "Ayşe Yılmaz"
    assert body["country"] == "TR"
    assert body["whatsapp"]
    assert body["communication_prefs"]["language"] == "tr"
    assert float(body["buyer_profile"]["budget_min"]) == 150000
    assert float(body["buyer_profile"]["budget_max"]) == 275000
    assert "investment_amount" not in body or body.get("investment_amount") in (None, "")


def test_purchase_amount_updates_agreement_not_contact(client: TestClient, db: Session) -> None:
    contact = _create_person(client, contact_type="investor")
    agreement = CrmAgreement(
        contact_id=UUID(contact["id"]),
        project_group="uniloft",
        source="os",
        source_external_id=f"step5:{uuid4().hex[:8]}",
        unit_number="12A",
        investment_amount="100000",
        metadata_json={"opportunity": "100000", "purchase_price": "100000", "currency": "USD"},
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)

    patched = client.patch(f"/crm/agreements/{agreement.id}", json={"amount": "180000"})
    assert patched.status_code == 200, patched.text
    card = patched.json()
    assert "180000" in str(card.get("amount") or card.get("amount_label") or card.get("investment_amount") or "")

    db.expire_all()
    row = db.get(CrmAgreement, agreement.id)
    assert row.investment_amount == "180000"
    meta = row.metadata_json or {}
    assert str(meta.get("opportunity")) == "180000"
    assert str(meta.get("purchase_price")) == "180000"

    person = client.get(f"/crm/contacts/{contact['id']}")
    assert person.status_code == 200
    detail = person.json()
    assert detail.get("amount_and_currency_amount") not in {"180000", 180000}
    assert "primary_phone" in detail


def test_empty_agreement_patch_rejected(client: TestClient, db: Session) -> None:
    contact = _create_person(client)
    agreement = CrmAgreement(
        contact_id=UUID(contact["id"]),
        project_group="reit",
        source="os",
        source_external_id=f"step5-empty:{uuid4().hex[:8]}",
        investment_amount="50000",
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
    response = client.patch(f"/crm/agreements/{agreement.id}", json={})
    assert response.status_code == 400


def test_purchase_amount_requires_financial_permission(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    contact = _create_person(auth_client, contact_type="investor")
    agreement = CrmAgreement(
        contact_id=UUID(contact["id"]),
        project_group="uniloft",
        source="os",
        source_external_id=f"step5-fin:{uuid4().hex[:8]}",
        unit_number="8B",
        investment_amount="90000",
        metadata_json={"opportunity": "90000", "purchase_price": "90000"},
    )
    db.add(agreement)
    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one()
    perm_update = db.query(Permission).filter_by(resource="crm", action="update").one()
    role = Role(name="crm update no financial", code=f"crm_upd_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    db.add(RolePermission(role_id=role.id, permission_id=perm_update.id))
    email = f"crm.upd.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="CRM Update No Financial",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(agreement)

    _login(auth_client, email)
    forbidden = auth_client.patch(f"/crm/agreements/{agreement.id}", json={"amount": "120000"})
    assert forbidden.status_code == 403
    db.expire_all()
    assert db.get(CrmAgreement, agreement.id).investment_amount == "90000"


def test_contact_edit_does_not_write_purchase_amount(client: TestClient, db: Session) -> None:
    contact = _create_person(client, contact_type="investor")
    agreement = CrmAgreement(
        contact_id=UUID(contact["id"]),
        project_group="uniloft",
        source="os",
        source_external_id=f"step5-no-copy:{uuid4().hex[:8]}",
        unit_number="3C",
        investment_amount="210000",
        metadata_json={"opportunity": "210000", "purchase_price": "210000"},
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)

    patched = client.patch(
        f"/crm/contacts/{contact['id']}",
        json={"city": "Istanbul", "notes": "Person card note"},
    )
    assert patched.status_code == 200, patched.text
    db.expire_all()
    row = db.get(CrmAgreement, agreement.id)
    assert row.investment_amount == "210000"
    assert (row.metadata_json or {}).get("opportunity") == "210000"
