"""Least-privilege role permission cleanup — approved revokes only."""

from __future__ import annotations

import io
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.permissions_config import (
    ACTIONS,
    DEFAULT_ROLE_PERMISSIONS,
    RESOURCES,
    ROLE_PERMISSION_CLEANUP_REVOKES,
)
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.project_cost_service import cost_permissions
from investhome_api.services.project_service import _can_edit_financial

DEMO_PASSWORD = "Demo123!"


def _grants(role_code: str) -> set[tuple[str, str]]:
    return set(DEFAULT_ROLE_PERMISSIONS[role_code])


def test_cleanup_matrix_matches_approved_revokes_and_keeps() -> None:
    partner = _grants("partner")
    executive = _grants("executive")
    finance = _grants("finance")
    operations = _grants("operations")
    construction = _grants("construction")
    marketing = _grants("marketing")
    super_admin = _grants("super_admin")

    assert ("documents", "view_confidential") not in partner
    assert ("documents", "view") in partner
    assert ("documents", "download") in partner

    assert ("security", "view") not in executive
    assert ("crm", "manage_provider_connections") not in executive
    assert ("crm", "manage_settings") not in executive
    assert ("users", "view") in executive

    assert ("documents", "delete") not in finance
    assert ("documents", "archive") in finance
    assert ("documents", "view_confidential") in finance

    assert ("documents", "delete") not in operations
    assert ("projects", "edit_financial") not in operations
    assert ("projects", "manage_budget") in operations
    assert ("projects", "manage_commitments") in operations
    assert ("projects", "manage_project_vendors") in operations

    assert ("projects", "edit_financial") not in construction
    assert ("projects", "view_financial") in construction
    assert ("projects", "manage_commitments") in construction
    assert ("projects", "manage_bills") in construction
    assert ("projects", "manage_project_vendors") in construction

    assert ("marketing", "manage_provider_connections") in marketing

    assert super_admin == {(resource, action) for resource in RESOURCES for action in ACTIONS}
    for role_code, resource, action in ROLE_PERMISSION_CLEANUP_REVOKES:
        assert (resource, action) in super_admin
        assert (resource, action) not in _grants(role_code)


def _permission(db: Session, resource: str, action: str) -> Permission:
    perm = db.scalar(select(Permission).where(Permission.resource == resource, Permission.action == action))
    if perm is None:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        db.flush()
    return perm


def _apply_default_grants(db: Session, role: Role, role_code: str) -> None:
    for resource, action in DEFAULT_ROLE_PERMISSIONS[role_code]:
        perm = _permission(db, resource, action)
        existing = db.scalar(
            select(RolePermission.id).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id,
            )
        )
        if existing is None:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))


def _create_role_user(db: Session, role_code: str) -> str:
    email = f"{role_code}-{uuid4().hex[:8]}@cleanup.example.com"
    role = db.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        role = Role(name=role_code, code=role_code, is_system_role=True)
        db.add(role)
        db.flush()
    _apply_default_grants(db, role, role_code)
    user = User(
        full_name=role_code,
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return email


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _load_user(db: Session, email: str) -> User:
    from investhome_api.services.permission_service import load_user_with_roles

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    loaded = load_user_with_roles(db, user.id)
    assert loaded is not None
    return loaded


def test_partner_cannot_access_confidential_documents(auth_client: TestClient, db: Session) -> None:
    partner_email = _create_role_user(db, "partner")
    _login(auth_client, "admin@example.com")
    upload = auth_client.post(
        "/documents/upload",
        files={"files": ("secret.txt", io.BytesIO(b"secret"), "text/plain")},
        data={"confidentiality_level": "confidential"},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["results"][0]["document"]["id"]

    _login(auth_client, partner_email)
    listed = auth_client.get("/documents")
    assert listed.status_code == 200
    assert all(item["id"] != doc_id for item in listed.json()["items"])
    assert auth_client.get(f"/documents/{doc_id}").status_code == 404
    partner = _load_user(db, partner_email)
    assert user_has_permission(partner, "documents", "view_confidential") is False
    assert user_has_permission(partner, "documents", "view") is True


def test_executive_loses_security_center_and_crm_oauth(auth_client: TestClient, db: Session) -> None:
    email = _create_role_user(db, "executive")
    _login(auth_client, email)
    exec_user = _load_user(db, email)
    assert user_has_permission(exec_user, "users", "view") is True
    assert user_has_permission(exec_user, "security", "view") is False
    assert user_has_permission(exec_user, "crm", "manage_provider_connections") is False
    assert user_has_permission(exec_user, "crm", "manage_settings") is False
    assert auth_client.get("/security/dashboard").status_code == 403
    assert auth_client.get("/security/sessions").status_code == 403
    assert auth_client.get("/security/mfa").status_code == 403
    assert auth_client.get("/security/api-keys").status_code == 403
    assert auth_client.post("/crm/live-communications/ingest", json={"channel": "email"}).status_code == 403
    assert auth_client.post("/crm/settings/communication-accounts/gmail/authorize").status_code == 403


def test_finance_and_operations_cannot_hard_delete_documents(auth_client: TestClient, db: Session) -> None:
    finance_email = _create_role_user(db, "finance")
    ops_email = _create_role_user(db, "operations")
    _login(auth_client, "admin@example.com")
    upload = auth_client.post(
        "/documents/upload",
        files={"files": ("keep.txt", io.BytesIO(b"keep"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["results"][0]["document"]["id"]
    created = auth_client.post(
        "/projects",
        json={
            "project_code": f"OPS-{uuid4().hex[:6]}",
            "project_name": "Cleanup Operations",
            "address": "2 Cleanup Way",
            "city": "Austin",
            "state": "TX",
            "country": "United States",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
        },
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    _login(auth_client, finance_email)
    finance = _load_user(db, finance_email)
    assert user_has_permission(finance, "documents", "delete") is False
    assert user_has_permission(finance, "documents", "archive") is True
    assert auth_client.delete(f"/documents/{doc_id}").status_code == 403

    _login(auth_client, ops_email)
    ops = _load_user(db, ops_email)
    assert user_has_permission(ops, "documents", "delete") is False
    assert user_has_permission(ops, "projects", "edit_financial") is False
    assert user_has_permission(ops, "projects", "manage_budget") is True
    assert user_has_permission(ops, "projects", "manage_commitments") is True
    assert user_has_permission(ops, "projects", "manage_project_vendors") is True
    assert auth_client.delete(f"/documents/{doc_id}").status_code == 403
    perms = cost_permissions(ops)
    assert perms.can_manage_commitments is True
    assert perms.can_manage_vendors is True
    assert perms.can_approve_commitments is False
    assert perms.can_post_payments is False
    assert perms.can_override_budget_control is False
    assert auth_client.get(f"/projects/{project_id}/budgets").status_code == 200
    assert auth_client.get(f"/projects/{project_id}/commitments").status_code == 200
    assert auth_client.get(f"/projects/{project_id}/vendor-bills").status_code == 200
    budget = auth_client.post(f"/projects/{project_id}/budgets", json={"name": "Ops Budget"})
    assert budget.status_code == 201, budget.text


def test_construction_cannot_edit_header_financials_keeps_cost_workflows(
    auth_client: TestClient, db: Session
) -> None:
    construction_email = _create_role_user(db, "construction")
    _login(auth_client, "admin@example.com")
    created = auth_client.post(
        "/projects",
        json={
            "project_code": f"CLN-{uuid4().hex[:6]}",
            "project_name": "Cleanup Construction",
            "address": "1 Cleanup Way",
            "city": "Austin",
            "state": "TX",
            "country": "United States",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
            "construction_budget": "1000000.00",
        },
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    _login(auth_client, construction_email)
    user = _load_user(db, construction_email)
    assert _can_edit_financial(user) is False
    assert user_has_permission(user, "projects", "view_financial") is True
    assert user_has_permission(user, "projects", "manage_commitments") is True
    assert user_has_permission(user, "projects", "manage_bills") is True
    assert user_has_permission(user, "projects", "manage_project_vendors") is True
    denied = auth_client.patch(f"/projects/{project_id}", json={"construction_budget": "2000000.00"})
    assert denied.status_code == 403
    perms = cost_permissions(user)
    assert perms.can_manage_commitments is True
    assert perms.can_manage_bills is True
    assert perms.can_manage_vendors is True
    assert perms.can_post_payments is False
    assert auth_client.get(f"/projects/{project_id}/commitments").status_code == 200
    assert auth_client.get(f"/projects/{project_id}/vendor-bills").status_code == 200
    vendor = auth_client.post(
        "/vendors",
        json={
            "name": "Cleanup Vendor",
            "vendor_code": f"CLV-{uuid4().hex[:6]}",
            "vendor_type": "general_contractor",
            "status": "active",
            "default_currency": "USD",
        },
    )
    assert vendor.status_code == 201, vendor.text


def test_marketing_provider_connections_remain(auth_client: TestClient, db: Session) -> None:
    email = _create_role_user(db, "marketing")
    _login(auth_client, email)
    user = _load_user(db, email)
    assert user_has_permission(user, "marketing", "manage_provider_connections") is True
    response = auth_client.get("/marketing/provider-statuses")
    assert response.status_code == 200


def test_super_admin_still_has_revoked_grants(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "admin@example.com")
    admin = _load_user(db, "admin@example.com")
    assert user_has_permission(admin, "security", "view") is True
    assert user_has_permission(admin, "documents", "view_confidential") is True
    assert user_has_permission(admin, "documents", "delete") is True
    assert user_has_permission(admin, "projects", "edit_financial") is True
    assert user_has_permission(admin, "crm", "manage_provider_connections") is True
    assert auth_client.get("/security/dashboard").status_code == 200
    assert auth_client.get("/marketing/provider-statuses").status_code == 200
