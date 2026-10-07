"""CRM phone lookup uses identity matching; it does not create or merge records."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from investhome_api.services.crm.identity import is_phone_lookup_query, phones_match


DEMO_PASSWORD = "Demo123!"


def _tr_local() -> str:
    return f"532{uuid4().int % 10_000_000:07d}"


def _formats(local: str) -> dict[str, str]:
    return {
        "local": local,
        "zero": f"0{local}",
        "cc": f"90{local}",
        "e164": f"+90{local}",
        "pretty": f"0{local[:3]} {local[3:6]} {local[6:8]} {local[8:]}",
        "intl": f"+90 {local[:3]} {local[3:6]} {local[6:8]} {local[8:]}",
    }


def _create_person(client: TestClient, *, phone: str, name: str | None = None, email: str | None = None) -> dict:
    payload = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": name or f"Phone Lookup {uuid4().hex[:6]}",
        "primary_email": email or f"phone.lookup.{uuid4().hex[:8]}@example.com",
        "primary_phone": phone,
        "lifecycle_stage": "new",
        "priority": "normal",
    }
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["contact"]


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def test_identity_phone_formats_match() -> None:
    formats = _formats("5321234567")
    assert is_phone_lookup_query(formats["pretty"])
    assert is_phone_lookup_query(formats["local"])
    assert is_phone_lookup_query(formats["cc"])
    assert is_phone_lookup_query(formats["intl"])
    assert not is_phone_lookup_query("UniqueAlphaSearchName")
    assert phones_match(formats["pretty"], formats["e164"])
    assert phones_match(formats["local"], formats["intl"])
    assert phones_match(formats["cc"], formats["zero"])


def test_exact_phone_match_finds_contact(client: TestClient) -> None:
    local = _tr_local()
    formats = _formats(local)
    contact = _create_person(client, phone=formats["e164"], name=f"Exact Phone {local}")
    response = client.get("/crm/search/quick", params={"q": formats["e164"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    hit = body["items"][0]
    assert hit["entity_id"] == contact["id"]
    assert hit["title"] == contact["display_name"]
    assert hit["metadata"]["phone_lookup"] is True
    assert hit["metadata"]["open_person_card"] is True
    assert hit["metadata"]["email"] == contact["primary_email"]
    assert hit["metadata"]["display_phone"]
    assert hit["metadata"]["possible_duplicate"] is False


def test_phone_format_variants_resolve_to_same_person(client: TestClient) -> None:
    local = _tr_local()
    formats = _formats(local)
    contact = _create_person(client, phone=formats["pretty"])
    listed = client.get("/crm/contacts", params={"search": formats["intl"]})
    assert listed.status_code == 200
    assert any(item["id"] == contact["id"] for item in listed.json()["items"])
    for query in (formats["pretty"], formats["local"], formats["cc"], formats["intl"], formats["zero"]):
        response = client.get("/crm/search/quick", params={"q": query})
        assert response.status_code == 200, f"{query}: {response.text}"
        body = response.json()
        ids = [item["entity_id"] for item in body["items"]]
        assert contact["id"] in ids, query
        assert body["total"] >= 1


def test_phone_lookup_returns_lead_contact_relationship(client: TestClient) -> None:
    local = _tr_local()
    formats = _formats(local)
    created = client.post(
        "/crm/leads",
        json={
            "full_name": f"Lead Phone {local}",
            "phone": formats["pretty"],
            "email": f"lead.phone.{uuid4().hex[:8]}@example.com",
            "source": "manual",
            "stage": "following",
        },
    )
    assert created.status_code == 201, created.text
    lead = created.json()
    assert lead["contact_id"]
    response = client.get("/crm/search/quick", params={"q": formats["cc"]})
    assert response.status_code == 200, response.text
    body = response.json()
    hit = next(item for item in body["items"] if item["entity_id"] == lead["contact_id"])
    assert hit["metadata"]["lead_id"] == lead["id"]
    assert hit["metadata"]["lead_stage"] == "following"
    assert hit["metadata"]["kanban_stage"] == "following"
    assert hit["entity_type"] == "crm_contact"


def test_phone_lookup_no_match_returns_empty(client: TestClient) -> None:
    query = "+90 532 000 00 99"
    before = client.get("/crm/contacts").json()["total"]
    response = client.get("/crm/search/quick", params={"q": query})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert "Kayıt bulunamadı" in (body["explanation"] or "")
    assert "No matching record found" in (body["explanation"] or "")
    after = client.get("/crm/contacts").json()["total"]
    assert after == before


def test_phone_lookup_does_not_create_or_modify_records(client: TestClient, db: Session) -> None:
    local = _tr_local()
    formats = _formats(local)
    contact = _create_person(client, phone=formats["e164"])
    count_before = db.scalar(select(func.count()).select_from(CrmContact))
    updated_before = db.get(CrmContact, UUID(contact["id"])).updated_at
    client.get("/crm/search/quick", params={"q": formats["pretty"]})
    client.get("/crm/contacts", params={"search": formats["local"]})
    db.expire_all()
    count_after = db.scalar(select(func.count()).select_from(CrmContact))
    updated_after = db.get(CrmContact, UUID(contact["id"])).updated_at
    assert count_after == count_before
    assert updated_after == updated_before


def test_multiple_phone_matches_are_not_merged(client: TestClient) -> None:
    local = _tr_local()
    formats = _formats(local)
    first = _create_person(client, phone=formats["e164"], name=f"Dup A {local}")
    second = _create_person(client, phone=formats["zero"], name=f"Dup B {local}")
    assert first["id"] != second["id"]
    response = client.get("/crm/search/quick", params={"q": formats["intl"]})
    assert response.status_code == 200, response.text
    body = response.json()
    ids = {item["entity_id"] for item in body["items"]}
    assert first["id"] in ids
    assert second["id"] in ids
    assert body["total"] >= 2
    assert all(item["metadata"].get("possible_duplicate") is True for item in body["items"] if item["entity_id"] in ids)


def test_phone_lookup_requires_search_permission(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    local = _tr_local()
    formats = _formats(local)
    contact = _create_person(auth_client, phone=formats["e164"])
    _login(auth_client, "readonly@example.com")
    hidden = auth_client.get("/crm/search/quick", params={"q": formats["pretty"]})
    assert hidden.status_code == 403
    listed = auth_client.get("/crm/contacts", params={"search": formats["local"]})
    assert listed.status_code == 403
    detail = auth_client.get(f"/crm/contacts/{contact['id']}")
    assert detail.status_code == 403


def test_phone_lookup_hides_contacts_without_crm_read(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    local = _tr_local()
    formats = _formats(local)
    contact = _create_person(auth_client, phone=formats["e164"])
    perm = db.query(Permission).filter_by(resource="crm", action="use_global_search").one()
    role = Role(name="crm search only", code=f"crm_search_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    email = f"crm.search.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="CRM Search Only",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    _login(auth_client, email)
    response = auth_client.get("/crm/search/quick", params={"q": formats["pretty"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert all(item["entity_id"] != contact["id"] for item in body["items"])
    assert body["total"] == 0
