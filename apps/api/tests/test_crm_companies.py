"""CRM Company management API tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.crm_company import CrmCompanyType
from investhome_api.models.crm_contact import CrmContact, CrmContactType, CrmRecordKind


def _create_company_payload(**overrides):
    payload = {
        "display_name": "Acme Capital",
        "legal_name": "Acme Capital LLC",
        "company_type": CrmCompanyType.INVESTMENT_COMPANY.value,
        "primary_email": "info@acmecapital.com",
        "domain": "acmecapital.com",
        "industry": "Real Estate Investment",
    }
    payload.update(overrides)
    return payload


def _create_contact(db: Session) -> str:
    contact = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Jane Investor",
        primary_email="jane@example.com",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return str(contact.id)


def test_create_crm_company(client: TestClient) -> None:
    response = client.post("/crm/companies", json=_create_company_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["display_name"] == "Acme Capital"
    assert body["company_type"] == CrmCompanyType.INVESTMENT_COMPANY.value


def test_list_crm_companies(client: TestClient) -> None:
    client.post("/crm/companies", json=_create_company_payload())
    client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Beta Brokerage",
            legal_name="Beta Brokerage Inc",
            company_type=CrmCompanyType.BROKERAGE.value,
            primary_email="info@beta.com",
            domain="beta.com",
        ),
    )
    response = client.get("/crm/companies?search=Beta&company_type=brokerage")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert any(item["display_name"] == "Beta Brokerage" for item in body["items"])


def test_get_update_delete_crm_company(client: TestClient) -> None:
    created = client.post(
        "/crm/companies",
        json=_create_company_payload(legal_name="Acme Capital II", primary_email="info2@acme.com", domain="acme2.com"),
    )
    company_id = created.json()["id"]

    get_response = client.get(f"/crm/companies/{company_id}")
    assert get_response.status_code == 200

    update_response = client.put(
        f"/crm/companies/{company_id}",
        json={"display_name": "Acme Updated", "industry": "Private Equity"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "Acme Updated"

    delete_response = client.delete(f"/crm/companies/{company_id}")
    assert delete_response.status_code == 204


def test_duplicate_legal_name_returns_422(client: TestClient) -> None:
    client.post("/crm/companies", json=_create_company_payload())
    response = client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Acme Duplicate",
            primary_email="dup@acme.com",
            domain="dup.acme.com",
        ),
    )
    assert response.status_code == 422


def test_hierarchy_circular_prevention(client: TestClient) -> None:
    parent = client.post("/crm/companies", json=_create_company_payload(display_name="Parent Co", legal_name="Parent Co LLC", primary_email="p@co.com", domain="parent.co"))
    child = client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Child Co",
            legal_name="Child Co LLC",
            primary_email="c@co.com",
            domain="child.co",
            parent_company_id=parent.json()["id"],
        ),
    )
    parent_id = parent.json()["id"]
    child_id = child.json()["id"]
    response = client.put(f"/crm/companies/{parent_id}", json={"parent_company_id": child_id})
    assert response.status_code == 422


def test_merge_crm_companies(client: TestClient) -> None:
    source = client.post(
        "/crm/companies",
        json=_create_company_payload(display_name="Source Co", legal_name="Source Co LLC", primary_email="s@co.com", domain="source.co"),
    )
    target = client.post(
        "/crm/companies",
        json=_create_company_payload(display_name="Target Co", legal_name="Target Co LLC", primary_email="t@co.com", domain="target.co"),
    )
    response = client.post(
        "/crm/companies/merge",
        json={"source_id": source.json()["id"], "target_id": target.json()["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["merged_id"] == target.json()["id"]


def test_company_contact_m2m(client: TestClient, db: Session) -> None:
    company = client.post("/crm/companies", json=_create_company_payload()).json()
    contact_id = _create_contact(db)
    link_response = client.post(
        f"/crm/companies/{company['id']}/contacts",
        json={"contact_id": contact_id, "role": "primary", "is_primary": True, "job_title": "Managing Director"},
    )
    assert link_response.status_code == 201, link_response.text
    contacts = client.get(f"/crm/companies/{company['id']}/contacts")
    assert contacts.status_code == 200
    assert len(contacts.json()) == 1
    assert contacts.json()[0]["contact_display_name"] == "Jane Investor"


def test_field_stripping_without_financial_permission(auth_client: TestClient, db: Session) -> None:
    from uuid import uuid4

    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    assert auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"}).status_code == 200
    created = auth_client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Restricted Co",
            legal_name="Restricted Co LLC",
            primary_email="r@co.com",
            domain="restricted.co",
            financial_profile={"annual_revenue": 1000000, "net_worth": 5000000},
        ),
    )
    assert created.status_code == 201, created.text
    company_id = created.json()["id"]

    for resource, action in (("crm", "read"), ("crm", "view_companies")):
        if db.query(Permission).filter_by(resource=resource, action=action).one_or_none() is None:
            db.add(Permission(resource=resource, action=action))
    db.flush()
    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one()
    perm_companies = db.query(Permission).filter_by(resource="crm", action="view_companies").one()
    role = Role(name="crm_co_limited", code=f"crm_co_lim_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    db.add(RolePermission(role_id=role.id, permission_id=perm_companies.id))
    email = f"crm.co.lim.{uuid4().hex[:6]}@example.com"
    limited = User(
        email=email,
        full_name="CRM Co Limited",
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(limited)
    db.flush()
    db.add(UserRole(user_id=limited.id, role_id=role.id))
    db.commit()

    assert auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"}).status_code == 200
    detail = auth_client.get(f"/crm/companies/{company_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body.get("financial_profile") is None
    assert body.get("annual_revenue") is None


def test_crm_company_audit_events(client: TestClient, db: Session) -> None:
    from uuid import UUID

    response = client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Audit Co",
            legal_name="Audit Co LLC",
            primary_email="audit@co.com",
            domain="audit.co",
        ),
    )
    company_id = UUID(response.json()["id"])
    logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.entity_type == ActivityEntityType.CRM_COMPANY,
            ActivityLog.entity_id == company_id,
        )
        .all()
    )
    assert len(logs) >= 1
    assert any("activity.crm_company.entity_created" in log.description_key for log in logs)


def test_import_crm_companies(client: TestClient) -> None:
    csv_content = "display_name,legal_name,company_type,status,primary_email,domain,industry\nImport Co,Import Co LLC,brokerage,active,info@import.co,import.co,Brokerage\n"
    response = client.post(
        "/crm/companies/import",
        files={"file": ("companies.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["imported"] >= 1


def test_crm_companies_forbidden_without_permission(auth_client: TestClient) -> None:
    auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
    response = auth_client.post("/crm/companies", json=_create_company_payload())
    assert response.status_code == 403


def test_company_workspace_counts_and_person_search(client: TestClient, db: Session) -> None:
    client.post("/crm/companies", json=_create_company_payload())
    client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Beta Brokerage",
            legal_name="Beta Brokerage Inc",
            company_type=CrmCompanyType.BROKERAGE.value,
            primary_email="info@beta.com",
            domain="beta-counts.com",
        ),
    )
    partner = client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name="Partner Lojistik",
            legal_name="Partner Lojistik AS",
            company_type=CrmCompanyType.PARTNER.value,
            primary_email="info@partnerlo.com",
            domain="partnerlo.com",
        ),
    )
    contact_id = _create_contact(db)
    client.post(
        f"/crm/companies/{partner.json()['id']}/contacts",
        json={"contact_id": contact_id, "role": "primary", "is_primary": True},
    )

    counts = client.get("/crm/companies/counts")
    assert counts.status_code == 200, counts.text
    body = counts.json()
    assert body["total"] >= 3
    assert body["brokerage"] >= 1
    assert body["partner"] >= 1
    assert body["investor"] >= 1
    assert "open_relationships" in body

    listed = client.get("/crm/companies?search=Jane")
    assert listed.status_code == 200
    assert any(item["display_name"] == "Partner Lojistik" for item in listed.json()["items"])
    found = next(item for item in listed.json()["items"] if item["display_name"] == "Partner Lojistik")
    assert found["contact_count"] >= 1
    assert any(person["display_name"] == "Jane Investor" for person in found["related_people"])
