"""CRM Company management API tests."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.crm_company import CrmCompany, CrmCompanyType
from investhome_api.models.crm_contact import CrmContact, CrmContactType, CrmRecordKind
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


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


def _ensure_permission(db: Session, resource: str, action: str) -> Permission:
    perm = db.query(Permission).filter_by(resource=resource, action=action).one_or_none()
    if perm is None:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        db.flush()
    return perm


def _company_user_with(db: Session, extra: list[tuple[str, str]], *, label: str) -> str:
    grants = [("crm", "read"), ("crm", "update"), *extra]
    role = Role(name=label, code=f"{label}_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    for resource, action in grants:
        db.add(RolePermission(role_id=role.id, permission_id=_ensure_permission(db, resource, action).id))
    email = f"{label}.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name=label,
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return email


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _seed_sensitive_company(auth_client: TestClient) -> str:
    suffix = uuid4().hex[:8]
    response = auth_client.post(
        "/crm/companies",
        json=_create_company_payload(
            display_name=f"Sensitive Co {suffix}",
            legal_name=f"Sensitive Co {suffix} LLC",
            primary_email=f"sensitive.{suffix}@co.example",
            domain=f"sensitive-{suffix}.example",
            tax_id=f"TAX{suffix}",
            ein=f"EIN{suffix}",
            registration_number=f"REG{suffix}",
            annual_revenue=1000000,
            financial_profile={"annual_revenue": 1000000, "net_worth": 5000000},
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _reload_company(db: Session, company_id: str) -> CrmCompany:
    db.expire_all()
    company = db.get(CrmCompany, UUID(str(company_id)))
    assert company is not None
    return company


def test_crm_update_can_change_ordinary_company_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    email = _company_user_with(db, [], label="crm_co_update")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"display_name": "Ordinary Co Name", "industry": "Hospitality", "notes": "ok"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "Ordinary Co Name"
    assert body["industry"] == "Hospitality"


def test_crm_update_cannot_change_company_financial_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    email = _company_user_with(db, [], label="crm_co_fin_blocked")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"annual_revenue": 9, "financial_profile": {"net_worth": 1}},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    company = _reload_company(db, company_id)
    assert company.annual_revenue == 1000000
    assert company.financial_profile is not None
    assert company.financial_profile.net_worth == 5000000


def test_crm_update_cannot_change_company_legal_tax_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    original = _reload_company(db, company_id)
    original_tax = original.tax_id
    original_ein = original.ein
    original_reg = original.registration_number
    email = _company_user_with(db, [], label="crm_co_legal_blocked")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"tax_id": "HACKTAX", "ein": "HACKEIN", "registration_number": "HACKREG"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    company = _reload_company(db, company_id)
    assert company.tax_id == original_tax
    assert company.ein == original_ein
    assert company.registration_number == original_reg


def test_crm_view_legal_cannot_update_company_legal_tax_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    original = _reload_company(db, company_id)
    original_tax = original.tax_id
    original_ein = original.ein
    original_reg = original.registration_number
    email = _company_user_with(db, [("crm", "view_legal")], label="crm_co_view_legal")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"tax_id": "HACKTAX", "ein": "HACKEIN", "registration_number": "HACKREG"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    company = _reload_company(db, company_id)
    assert company.tax_id == original_tax
    assert company.ein == original_ein
    assert company.registration_number == original_reg


def test_crm_edit_legal_can_update_company_legal_tax_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    email = _company_user_with(db, [("crm", "edit_legal")], label="crm_co_edit_legal")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"tax_id": "WRITETAX", "ein": "WRITEEIN", "registration_number": "WRITEREG"},
    )
    assert response.status_code == 200, response.text
    company = _reload_company(db, company_id)
    assert company.tax_id == "WRITETAX"
    assert company.ein == "WRITEEIN"
    assert company.registration_number == "WRITEREG"


def test_authorized_user_can_change_company_protected_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    email = _company_user_with(
        db,
        [("crm", "edit_financial"), ("crm", "edit_legal")],
        label="crm_co_sensitive_write",
    )
    _login(auth_client, email)
    financial = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"annual_revenue": 2000000, "financial_profile": {"net_worth": 8000000}},
    )
    assert financial.status_code == 200, financial.text
    legal = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"tax_id": "NEWTAXID", "ein": "NEWEINID", "registration_number": "NEWREGID"},
    )
    assert legal.status_code == 200, legal.text
    company = _reload_company(db, company_id)
    assert company.annual_revenue == 2000000
    assert company.financial_profile is not None
    assert company.financial_profile.net_worth == 8000000
    assert company.tax_id == "NEWTAXID"
    assert company.ein == "NEWEINID"
    assert company.registration_number == "NEWREGID"


def test_super_admin_can_change_company_protected_fields(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    financial = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"annual_revenue": 3000000, "financial_profile": {"net_worth": 9000000}},
    )
    assert financial.status_code == 200, financial.text
    legal = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"tax_id": "ADMINTAX", "ein": "ADMINEIN", "registration_number": "ADMINREG"},
    )
    assert legal.status_code == 200, legal.text
    company = _reload_company(db, company_id)
    assert company.annual_revenue == 3000000
    assert company.financial_profile is not None
    assert company.financial_profile.net_worth == 9000000
    assert company.tax_id == "ADMINTAX"
    assert company.ein == "ADMINEIN"
    assert company.registration_number == "ADMINREG"


def test_mixed_company_payload_cannot_bypass_sensitive_restriction(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    original = _reload_company(db, company_id)
    original_name = original.display_name
    original_tax = original.tax_id
    original_revenue = original.annual_revenue
    email = _company_user_with(db, [], label="crm_co_mixed")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={
            "display_name": "Smuggled Company",
            "annual_revenue": 1,
            "tax_id": "SMUGGLETAX",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    company = _reload_company(db, company_id)
    assert company.display_name == original_name
    assert company.tax_id == original_tax
    assert company.annual_revenue == original_revenue


def test_view_legal_mixed_payload_cannot_bypass_legal_write_restriction(
    auth_client: TestClient, db: Session
) -> None:
    _login(auth_client, "admin@example.com")
    company_id = _seed_sensitive_company(auth_client)
    original = _reload_company(db, company_id)
    original_name = original.display_name
    original_tax = original.tax_id
    email = _company_user_with(db, [("crm", "view_legal")], label="crm_co_view_legal_mixed")
    _login(auth_client, email)
    response = auth_client.put(
        f"/crm/companies/{company_id}",
        json={"display_name": "Smuggled Company", "tax_id": "SMUGGLETAX"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    company = _reload_company(db, company_id)
    assert company.display_name == original_name
    assert company.tax_id == original_tax
