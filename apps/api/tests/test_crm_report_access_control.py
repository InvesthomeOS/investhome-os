"""CRM report owner scope and financial metric access control."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


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


def _user_with(db: Session, grants: list[tuple[str, str]], *, label: str) -> tuple[str, UUID]:
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
    db.refresh(user)
    return email, user.id


def _other_user(db: Session) -> UUID:
    user = User(
        email=f"other.owner.{uuid4().hex[:8]}@example.com",
        full_name="Other Report Owner",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id


def _seed_owned_agreement(
    db: Session,
    owner_id: UUID,
    *,
    amount: str,
    project_group: str,
) -> UUID:
    contact = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name=f"Report Owner {uuid4().hex[:6]}",
        status=CrmContactStatus.ACTIVE,
        owner_user_id=owner_id,
        source="website",
    )
    db.add(contact)
    db.flush()
    db.add(
        CrmAgreement(
            contact_id=contact.id,
            project_group=project_group,
            source="bitrix",
            source_external_id=f"rpt:{uuid4().hex[:10]}",
            investment_amount=amount,
            metadata_json={"opportunity": amount, "currency": "USD"},
        )
    )
    db.commit()
    return contact.id


def _seed_owned_lead(db: Session, owner_id: UUID, name: str) -> None:
    db.add(
        Lead(
            full_name=name,
            source="website",
            status=LeadStatus.NEW,
            interested_project="uniloft",
            is_demo=False,
            assigned_manager_id=owner_id,
        )
    )
    db.commit()


def test_crm_read_cannot_query_another_owner(auth_client: TestClient, db: Session) -> None:
    other_id = _other_user(db)
    email, _uid = _user_with(db, [("crm", "read")], label="crm_read_rpt")
    _login(auth_client, email)
    response = auth_client.get("/crm/reports/workspace", params={"owner_id": str(other_id)})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_self_scoped_report_remains_accessible(auth_client: TestClient, db: Session) -> None:
    other_id = _other_user(db)
    email, user_id = _user_with(db, [("crm", "read")], label="crm_read_self")
    own_marker = f"OwnLead {uuid4().hex[:6]}"
    other_marker = f"OtherLead {uuid4().hex[:6]}"
    _seed_owned_lead(db, user_id, own_marker)
    _seed_owned_lead(db, other_id, other_marker)
    _seed_owned_agreement(db, user_id, amount="12000", project_group="uniloft")
    _seed_owned_agreement(db, other_id, amount="880000", project_group="uniloft")
    _login(auth_client, email)

    unscoped = auth_client.get("/crm/reports/workspace")
    assert unscoped.status_code == 200, unscoped.text
    body = unscoped.json()
    lead_names = [row["name"] for row in body["leads"]["table"]]
    assert own_marker in lead_names
    assert other_marker not in lead_names
    assert body["kpis"]["current_purchases"] >= 1
    for row in body["sales"]["by_project"]:
        assert 880000 not in [item["total"] for item in row["amounts"]]

    self_scoped = auth_client.get("/crm/reports/workspace", params={"owner_id": str(user_id)})
    assert self_scoped.status_code == 200, self_scoped.text
    self_body = self_scoped.json()
    self_names = [row["name"] for row in self_body["leads"]["table"]]
    assert own_marker in self_names
    assert other_marker not in self_names

    summary = auth_client.get("/crm/reports/summary")
    assert summary.status_code == 200, summary.text


def test_financial_metrics_hidden_without_view_financial(auth_client: TestClient, db: Session) -> None:
    email, user_id = _user_with(db, [("crm", "read")], label="crm_read_nofin")
    _seed_owned_agreement(db, user_id, amount="150000", project_group="reit")
    _login(auth_client, email)

    workspace = auth_client.get("/crm/reports/workspace")
    assert workspace.status_code == 200, workspace.text
    body = workspace.json()
    assert body["kpis"]["sales_totals"] == []
    assert body["filter_options"]["currencies"] == []
    for row in body["sales"]["by_project"]:
        assert row["amounts"] == []
    for row in body["investors"]["table"]:
        assert row["amounts"] == []
    assert body["kpis"]["current_purchases"] >= 1

    summary = auth_client.get("/crm/reports/summary")
    assert summary.status_code == 200, summary.text
    reit = summary.json()["reit_investment"]
    assert reit["populated_count"] == 0
    assert reit["total"] is None


def test_view_financial_user_gets_authorized_financial_metrics(auth_client: TestClient, db: Session) -> None:
    other_id = _other_user(db)
    email, user_id = _user_with(
        db,
        [("crm", "read"), ("crm", "view_financial")],
        label="crm_fin_rpt",
    )
    _seed_owned_agreement(db, user_id, amount="75000", project_group="reit")
    _seed_owned_agreement(db, other_id, amount="999999", project_group="reit")
    _login(auth_client, email)

    workspace = auth_client.get("/crm/reports/workspace")
    assert workspace.status_code == 200, workspace.text
    totals = {item["currency"]: item["total"] for item in workspace.json()["kpis"]["sales_totals"]}
    assert totals.get("USD") == 75000
    assert 999999 not in totals.values()

    summary = auth_client.get("/crm/reports/summary")
    assert summary.status_code == 200, summary.text
    reit = summary.json()["reit_investment"]
    assert reit["populated_count"] >= 1
    assert reit["total"] == 75000

    forbidden = auth_client.get("/crm/reports/workspace", params={"owner_id": str(other_id)})
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Insufficient permissions"


def test_super_admin_can_query_broader_scope(auth_client: TestClient, db: Session) -> None:
    other_id = _other_user(db)
    _seed_owned_agreement(db, other_id, amount="64000", project_group="uniloft")
    _login(auth_client, "admin@example.com")

    workspace = auth_client.get("/crm/reports/workspace")
    assert workspace.status_code == 200, workspace.text
    unscoped_purchases = workspace.json()["kpis"]["current_purchases"]
    unscoped_usd = sum(
        item["total"] for item in workspace.json()["kpis"]["sales_totals"] if item["currency"] == "USD"
    )
    assert unscoped_purchases >= 1
    assert unscoped_usd >= 64000

    scoped = auth_client.get("/crm/reports/workspace", params={"owner_id": str(other_id)})
    assert scoped.status_code == 200, scoped.text
    scoped_body = scoped.json()
    assert scoped_body["kpis"]["current_purchases"] == 1
    scoped_usd = {item["currency"]: item["total"] for item in scoped_body["kpis"]["sales_totals"]}
    assert scoped_usd.get("USD") == 64000
    assert unscoped_purchases >= scoped_body["kpis"]["current_purchases"]

    summary = auth_client.get("/crm/reports/summary")
    assert summary.status_code == 200, summary.text
    assert summary.json()["agreements_total"] >= 1


def test_filter_tampering_cannot_bypass_owner_scope(auth_client: TestClient, db: Session) -> None:
    other_id = _other_user(db)
    email, user_id = _user_with(db, [("crm", "read")], label="crm_read_tamp")
    _seed_owned_agreement(db, other_id, amount="777000", project_group="uniloft")
    _login(auth_client, email)

    missing_owner = uuid4()
    for owner in (other_id, missing_owner):
        response = auth_client.get(
            "/crm/reports/workspace",
            params={
                "owner_id": str(owner),
                "project_group": "uniloft",
                "source": "website",
                "currency": "USD",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    allowed = auth_client.get(
        "/crm/reports/workspace",
        params={"owner_id": str(user_id), "project_group": "uniloft"},
    )
    assert allowed.status_code == 200, allowed.text
    totals = [item["total"] for item in allowed.json()["kpis"]["sales_totals"]]
    assert 777000 not in totals
    for row in allowed.json()["sales"]["by_project"]:
        assert 777000 not in [item["total"] for item in row["amounts"]]
