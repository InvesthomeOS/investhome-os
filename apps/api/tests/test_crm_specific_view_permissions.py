"""crm:read must not bypass specific CRM view permissions."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import CrmContactType
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.schemas.crm_contacts import CrmContactCreate, CrmInvestmentProfileSchema
from investhome_api.services.auth_service import hash_password
from investhome_api.services.crm.contact_service import create_contact


DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _ensure_permission(db: Session, resource: str, action: str) -> Permission:
    perm = db.query(Permission).filter_by(resource=resource, action=action).one_or_none()
    if perm is None:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        db.flush()
    return perm


def _user_with(db: Session, grants: list[tuple[str, str]], *, label: str) -> str:
    role = Role(name=label, code=f"{label}_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    for resource, action in grants:
        db.add(RolePermission(role_id=role.id, permission_id=_ensure_permission(db, resource, action).id))
    email = f"{label}.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name=label,
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return email


def _seed_contact(db: Session):
    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.INVESTOR,
            display_name=f"View Perm Contact {uuid4().hex[:6]}",
            investment_profile=CrmInvestmentProfileSchema(investment_capacity_min=100000),
            compliance_data={"kyc_status": "pending"},
        ),
    )
    db.commit()
    return contact


def test_crm_read_cannot_access_activities_without_view_activities(
    auth_client: TestClient, db: Session
) -> None:
    email = _user_with(db, [("crm", "read")], label="crm_read_no_acts")
    _login(auth_client, email)
    response = auth_client.get("/crm/activities")
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    timeline = auth_client.get("/crm/timeline")
    assert timeline.status_code == 403


def test_crm_read_cannot_access_companies_without_view_companies(
    auth_client: TestClient, db: Session
) -> None:
    email = _user_with(db, [("crm", "read")], label="crm_read_no_cos")
    _login(auth_client, email)
    response = auth_client.get("/crm/companies")
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_view_activities_retains_activity_access(auth_client: TestClient, db: Session) -> None:
    email = _user_with(db, [("crm", "read"), ("crm", "view_activities")], label="crm_view_acts")
    _login(auth_client, email)
    response = auth_client.get("/crm/activities")
    assert response.status_code == 200, response.text


def test_view_companies_retains_company_access(auth_client: TestClient, db: Session) -> None:
    email = _user_with(db, [("crm", "read"), ("crm", "view_companies")], label="crm_view_cos")
    _login(auth_client, email)
    response = auth_client.get("/crm/companies")
    assert response.status_code == 200, response.text


def test_super_admin_retains_activity_and_company_access(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    activities = auth_client.get("/crm/activities")
    companies = auth_client.get("/crm/companies")
    assert activities.status_code == 200, activities.text
    assert companies.status_code == 200, companies.text


def test_crm_read_hides_embedded_activities_and_sensitive_subfields(
    auth_client: TestClient, db: Session
) -> None:
    contact = _seed_contact(db)
    email = _user_with(db, [("crm", "read")], label="crm_read_fields")
    _login(auth_client, email)
    response = auth_client.get(f"/crm/contacts/{contact.id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("crm_activities") == []
    assert body.get("investment_profile") is None
    assert body.get("compliance_data") is None
    timeline = auth_client.get(f"/crm/contacts/{contact.id}/timeline")
    assert timeline.status_code == 403


def test_sales_retains_activity_and_company_access(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    activities = auth_client.get("/crm/activities")
    companies = auth_client.get("/crm/companies")
    assert activities.status_code == 200, activities.text
    assert companies.status_code == 200, companies.text
