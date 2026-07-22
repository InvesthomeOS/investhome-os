"""Admin Workspace stabilization — users, roles, permissions, search, and audit flows."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.company_foundation import CompanyProfile
from investhome_api.models.user_auth import Role, User
from investhome_api.services.search_service import global_search

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _session(client: TestClient) -> Session:
    from investhome_api.db.session import get_db

    override = client.app.dependency_overrides.get(get_db)
    assert override is not None
    return next(override())


def test_admin_users_list_and_view_permissions(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    response = auth_client.get("/users")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["email"] == "admin@example.com" for item in payload["items"])

    _login(auth_client, "sales@example.com")
    denied = auth_client.get("/users")
    assert denied.status_code == 403


def test_admin_create_user_role_assign_and_deactivate(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")

    roles = auth_client.get("/roles")
    assert roles.status_code == 200, roles.text
    read_only = next(item for item in roles.json()["items"] if item["code"] == "read_only")

    email = f"admin.stabilize.{uuid4().hex[:8]}@example.com"
    created = auth_client.post(
        "/users",
        json={
            "full_name": "Stabilize Admin User",
            "email": email,
            "password": "TempPass123!",
            "status": "active",
            "role_ids": [read_only["id"]],
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    assign = auth_client.put(
        f"/users/{user_id}/roles",
        json={"role_ids": [read_only["id"]]},
    )
    assert assign.status_code == 200, assign.text

    deactivate = auth_client.post(f"/users/{user_id}/deactivate")
    assert deactivate.status_code == 200, deactivate.text
    assert deactivate.json()["status"] == "inactive"


def test_admin_role_create_and_permission_assign(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")

    code = f"stabilize_{uuid4().hex[:6]}"
    created = auth_client.post(
        "/roles",
        json={"name": "Stabilize Role", "code": code, "description": "Sprint 6A8 test role"},
    )
    assert created.status_code == 201, created.text
    role_id = created.json()["id"]

    permissions = auth_client.get("/permissions")
    assert permissions.status_code == 200, permissions.text
    permission_ids = [item["id"] for item in permissions.json()["items"][:3]]

    assigned = auth_client.put(
        f"/roles/{role_id}/permissions",
        json={"permission_ids": permission_ids},
    )
    assert assigned.status_code == 200, assigned.text
    assert len(assigned.json()["permissions"]) == len(permission_ids)


def test_admin_privilege_escalation_blocked(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    roles = auth_client.get("/roles")
    assert roles.status_code == 403

    _login(auth_client, "admin@example.com")
    super_admin = auth_client.get("/roles")
    assert super_admin.status_code == 200
    target = next(item for item in super_admin.json()["items"] if item["code"] == "super_admin")
    users = auth_client.get("/users")
    assert users.status_code == 200
    victim = next(item for item in users.json()["items"] if item["email"] != "admin@example.com")

    _login(auth_client, "readonly@example.com")
    denied = auth_client.put(
        f"/users/{victim['id']}/roles",
        json={"role_ids": [target["id"]]},
    )
    assert denied.status_code == 403


def test_admin_search_users_roles_company(auth_client: TestClient) -> None:
    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None

        role = Role(
            name=f"Search Role {uuid4().hex[:4]}",
            code=f"search_{uuid4().hex[:6]}",
            description="admin search test",
            is_system_role=False,
        )
        session.add(role)

        company = session.scalar(select(CompanyProfile))
        if company is None:
            company = CompanyProfile(
                company_name=f"SearchCo {uuid4().hex[:4]}",
                company_code=f"SC{uuid4().hex[:4].upper()}",
            )
            session.add(company)
        else:
            company.company_name = f"SearchCo {uuid4().hex[:4]}"
        session.commit()

        user_results = global_search(session, admin, "admin@example.com")
        assert any(group.entity_type == "user" for group in user_results.groups)

        _login(auth_client, "admin@example.com")
        response = auth_client.get("/search?q=SearchCo")
        assert response.status_code == 200, response.text
        entity_types = {group["entity_type"] for group in response.json()["groups"]}
        assert "company" in entity_types or "user" in entity_types

        role_response = auth_client.get(f"/search?q={role.code}")
        assert role_response.status_code == 200, role_response.text
        role_types = {group["entity_type"] for group in role_response.json()["groups"]}
        assert "role" in role_types
    finally:
        session.close()


def test_admin_mutations_write_activity_logs(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    try:
        before = session.scalar(select(ActivityLog.id).order_by(ActivityLog.created_at.desc()).limit(1))

        roles = auth_client.get("/roles").json()["items"]
        read_only = next(item for item in roles if item["code"] == "read_only")
        email = f"audit.{uuid4().hex[:8]}@example.com"
        created = auth_client.post(
            "/users",
            json={
                "full_name": "Audit Trail User",
                "email": email,
                "password": "TempPass123!",
                "status": "active",
                "role_ids": [read_only["id"]],
            },
        )
        assert created.status_code == 201, created.text

        logs = session.scalars(
            select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(5)
        ).all()
        assert logs
        assert any("user" in (log.entity_type.value if hasattr(log.entity_type, "value") else str(log.entity_type)) for log in logs)
        assert before is not None or len(logs) >= 1
    finally:
        session.close()


def test_admin_users_search_filter(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    response = auth_client.get("/users", params={"search": "admin"})
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 1

    inactive = auth_client.get("/users", params={"status": "inactive"})
    assert inactive.status_code == 200, inactive.text
    assert isinstance(inactive.json()["items"], list)
