"""Company Workspace V1 stabilization — RBAC, search, field security, and CRUD flows."""

from __future__ import annotations

import time
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.company import CompanyEntityType, CompanyStatus
from investhome_api.models.user_auth import User
from investhome_api.services.branch_service import _mask_sensitive_text, can_view_branch_sensitive
from investhome_api.services.company_management_service import can_view_full_bank_details, mask_account_number

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _create_company(client: TestClient, *, name: str = "Stabilize Co") -> str:
    response = client.post(
        "/companies",
        json={
            "company_name": name,
            "legal_name": f"{name} Ltd",
            "entity_type": CompanyEntityType.CORPORATION.value,
            "registration_number": f"REG-{uuid4().hex[:6]}",
            "tax_id": f"{(4040404040 + int(uuid4().hex[:6], 16) % 1000000):010d}",
            "country": "TR",
            "city": "Istanbul",
            "status": CompanyStatus.ACTIVE.value,
            "bank_accounts": [
                {
                    "bank_name": "Test Bank",
                    "account_name": "Ops",
                    "account_number": "1234567890",
                    "iban": "TR123456789012345678901234",
                    "routing_number": "021000021",
                    "currency": "TRY",
                    "is_primary": True,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _branch_payload(company_id: str, **overrides):
    payload = {
        "branch_code": f"BR-{uuid4().hex[:4].upper()}",
        "branch_name": "Stabilize Branch",
        "company_id": company_id,
        "branch_type": "head_office",
        "country": "Turkey",
        "city": "Istanbul",
        "full_address": "Test Address 1",
        "status": "active",
        "emergency_contact": "Emergency Person +90 555 000 0000",
    }
    payload.update(overrides)
    return payload


def test_company_dashboard_and_search(client: TestClient) -> None:
    company_id = _create_company(client, name="Searchable Co")
    client.post("/branches", json=_branch_payload(company_id, branch_name="Search Branch"))

    dashboard = client.get("/companies/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_companies"] >= 1

    search = client.get("/companies/search?q=Search")
    assert search.status_code == 200, search.text
    entity_types = {group["entity_type"] for group in search.json()["groups"]}
    assert "managed_company" in entity_types or "branch" in entity_types


def test_company_search_extended_entities(client: TestClient) -> None:
    company_id = _create_company(client, name="Extended Search Co")
    dept = client.post(
        "/departments",
        json={
            "department_code": f"DEPT-{uuid4().hex[:4].upper()}",
            "department_name": "Extended Search Dept",
            "company_id": company_id,
            "department_type": "finance",
            "status": "active",
        },
    )
    assert dept.status_code == 201, dept.text

    response = client.get(
        "/companies/search",
        params={"q": "Extended", "entity_types": "managed_company,branch,company_department,user,document,project"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 1


def test_company_rbac_forbidden_without_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    assert auth_client.get("/companies/dashboard").status_code == 403
    assert auth_client.get("/companies/search?q=test").status_code == 403
    assert auth_client.get("/departments").status_code == 403
    assert auth_client.get("/branches").status_code == 403


def test_bank_account_masking_helpers() -> None:
    assert mask_account_number("1234567890") == "******7890"
    assert mask_account_number(None) is None
    assert can_view_full_bank_details(None) is False


def test_branch_sensitive_field_helpers(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    user = db.scalar(select(User).where(User.email == "admin@example.com"))
    assert user is not None
    assert can_view_branch_sensitive(user) is True
    assert _mask_sensitive_text("secret contact") == "***"
    assert can_view_branch_sensitive(None) is False


def test_branch_emergency_contact_masked_in_api(auth_client: TestClient, db: Session) -> None:
    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password
    from investhome_api.services.branch_service import get_branch_or_none, serialize_branch_detail

    _login(auth_client, "admin@example.com")
    company_id = _create_company(auth_client)
    created = auth_client.post("/branches", json=_branch_payload(company_id))
    assert created.status_code == 201, created.text
    branch_id = created.json()["branch"]["id"]

    full = auth_client.get(f"/branches/{branch_id}")
    assert full.status_code == 200
    assert full.json()["emergency_contact"] == "Emergency Person +90 555 000 0000"

    # Limited user with branch:read but not branch:update must see masked contact.
    perm = db.query(Permission).filter_by(resource="branch", action="read").one_or_none()
    if perm is None:
        perm = Permission(resource="branch", action="read")
        db.add(perm)
        db.flush()
    role = Role(name="branch_reader", code=f"branch_reader_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    limited = User(
        full_name="Branch Reader",
        email=f"branch.reader.{uuid4().hex[:6]}@example.com",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(limited)
    db.flush()
    db.add(UserRole(user_id=limited.id, role_id=role.id))
    db.commit()

    from investhome_api.services.permission_service import load_user_with_roles

    limited_loaded = load_user_with_roles(db, limited.id)
    assert limited_loaded is not None
    branch = get_branch_or_none(db, UUID(branch_id))
    assert branch is not None
    detail = serialize_branch_detail(db, branch, user=limited_loaded)
    assert detail.emergency_contact == "***"


def test_department_crud_and_audit(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    created = client.post(
        "/departments",
        json={
            "department_code": f"AUD-{uuid4().hex[:4].upper()}",
            "department_name": "Audit Department",
            "company_id": company_id,
            "department_type": "it",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    dept_id = UUID(created.json()["department"]["id"])

    updated = client.put(
        f"/departments/{dept_id}",
        json={"department_name": "Audit Department Updated"},
    )
    assert updated.status_code == 200, updated.text

    logs = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.DEPARTMENT,
            ActivityLog.entity_id == dept_id,
        )
    ).all()
    assert logs


def test_branch_transfer_and_manager_assignment(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    branch_a = client.post("/branches", json=_branch_payload(company_id, branch_code="BR-A-01"))
    branch_b = client.post("/branches", json=_branch_payload(company_id, branch_code="BR-B-01"))
    assert branch_a.status_code == 201 and branch_b.status_code == 201

    manager = db.scalar(select(User).limit(1))
    assert manager is not None
    manager_id = str(manager.id)
    branch_id = branch_a.json()["branch"]["id"]

    assigned = client.post(
        f"/branches/{branch_id}/assign-manager",
        json={"manager_user_id": manager_id},
    )
    assert assigned.status_code == 200, assigned.text

    transfer = client.post(
        f"/branches/{branch_id}/transfer-employees",
        json={"target_branch_id": branch_b.json()["branch"]["id"], "employee_user_ids": []},
    )
    assert transfer.status_code == 200, transfer.text


def test_company_workspace_load_search_latency(client: TestClient) -> None:
    """Pragmatic load check: repeated creates, measure search latency."""
    for index in range(10):
        _create_company(client, name=f"Load Co {index}")

    start = time.perf_counter()
    response = client.get("/companies/search?q=Load")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 1
    assert elapsed_ms < 2000, f"Search latency too high: {elapsed_ms:.1f}ms"
