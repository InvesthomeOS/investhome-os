"""CRM Relationship Engine API tests."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.crm_contact import CrmContact, CrmContactType, CrmRecordKind
from investhome_api.models.crm_company import CrmCompany, CrmCompanyType


def _create_contact(db: Session, name: str = "Alice Contact") -> str:
    contact = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        primary_email=f"{name.lower().replace(' ', '.')}@example.com",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return str(contact.id)


def _create_company(db: Session, name: str = "Acme Corp") -> str:
    company = CrmCompany(
        display_name=name,
        legal_name=f"{name} LLC",
        company_type=CrmCompanyType.INVESTMENT_COMPANY,
        primary_email=f"info@{name.lower().replace(' ', '')}.com",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return str(company.id)


def _relationship_payload(source_id: str, target_id: str, **overrides):
    payload = {
        "source_entity_type": "contact",
        "source_entity_id": source_id,
        "target_entity_type": "contact",
        "target_entity_id": target_id,
        "relationship_type": "colleague",
        "strength": "moderate",
    }
    payload.update(overrides)
    return payload


def test_create_and_list_relationship(client: TestClient, db: Session) -> None:
    source_id = _create_contact(db, "Source Person")
    target_id = _create_contact(db, "Target Person")
    response = client.post("/crm/relationships", json=_relationship_payload(source_id, target_id))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["relationship_type"] == "colleague"
    assert body["reciprocal_type"] == "colleague"
    assert body["relationship_score"] >= 0

    list_response = client.get("/crm/relationships")
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1


def test_reciprocal_type_mapping(client: TestClient, db: Session) -> None:
    parent_id = _create_company(db, "Parent Inc")
    child_id = _create_company(db, "Child Inc")
    response = client.post(
        "/crm/relationships",
        json={
            "source_entity_type": "company",
            "source_entity_id": parent_id,
            "target_entity_type": "company",
            "target_entity_id": child_id,
            "relationship_type": "parent",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["reciprocal_type"] == "subsidiary"


def test_duplicate_detection(client: TestClient, db: Session) -> None:
    source_id = _create_contact(db)
    target_id = _create_contact(db, "Other Person")
    payload = _relationship_payload(source_id, target_id)
    client.post("/crm/relationships", json=payload)
    dup_check = client.post("/crm/relationships/check-duplicates", json=payload)
    assert dup_check.status_code == 200
    assert len(dup_check.json()) == 1
    dup_create = client.post("/crm/relationships", json=payload)
    assert dup_create.status_code == 409


def test_hierarchy_cycle_prevention(client: TestClient, db: Session) -> None:
    a_id = _create_company(db, "Company A")
    b_id = _create_company(db, "Company B")
    c_id = _create_company(db, "Company C")
    client.post(
        "/crm/relationships",
        json={
            "source_entity_type": "company",
            "source_entity_id": a_id,
            "target_entity_type": "company",
            "target_entity_id": b_id,
            "relationship_type": "parent",
        },
    )
    client.post(
        "/crm/relationships",
        json={
            "source_entity_type": "company",
            "source_entity_id": b_id,
            "target_entity_type": "company",
            "target_entity_id": c_id,
            "relationship_type": "parent",
        },
    )
    cycle = client.post(
        "/crm/relationships",
        json={
            "source_entity_type": "company",
            "source_entity_id": c_id,
            "target_entity_type": "company",
            "target_entity_id": a_id,
            "relationship_type": "parent",
        },
    )
    assert cycle.status_code == 422


def test_score_calculation(client: TestClient, db: Session) -> None:
    source_id = _create_contact(db, "Score Source")
    target_id = _create_contact(db, "Score Target")
    created = client.post(
        "/crm/relationships",
        json=_relationship_payload(source_id, target_id, strength="strategic", is_verified=True),
    )
    rel_id = created.json()["id"]
    calc = client.get(f"/crm/relationships/scores/calculate?relationship_id={rel_id}")
    assert calc.status_code == 200
    result = calc.json()
    assert result["calculated"] == 1
    assert result["results"][0]["relationship_score"] >= 0


def test_graph_depth_limits(client: TestClient, db: Session) -> None:
    ids = [_create_contact(db, f"Node {i}") for i in range(4)]
    for i in range(3):
        client.post("/crm/relationships", json=_relationship_payload(ids[i], ids[i + 1]))
    graph = client.get(
        f"/crm/relationships/graph?center_entity_type=contact&center_entity_id={ids[0]}&depth=1&limit=10"
    )
    assert graph.status_code == 200
    body = graph.json()
    assert len(body["nodes"]) <= 10
    assert body["depth"] == 1


def test_introduction_path_finding(client: TestClient, db: Session) -> None:
    a = _create_contact(db, "Path A")
    b = _create_contact(db, "Path B")
    c = _create_contact(db, "Path C")
    client.post("/crm/relationships", json=_relationship_payload(a, b, strength="strong"))
    client.post("/crm/relationships", json=_relationship_payload(b, c, strength="strong"))
    paths = client.get(
        f"/crm/relationships/introduction-paths"
        f"?source_entity_type=contact&source_entity_id={a}"
        f"&target_entity_type=contact&target_entity_id={c}"
        f"&strategy=shortest"
    )
    assert paths.status_code == 200
    body = paths.json()
    assert len(body["paths"]) >= 1
    assert body["paths"][0]["total_hops"] == 2


def test_confidential_permission_strip(auth_client: TestClient, db: Session) -> None:
    from uuid import uuid4

    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    source_id = _create_contact(db)
    target_id = _create_contact(db, "Conf Target")

    login = auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
    assert login.status_code == 200
    created = auth_client.post(
        "/crm/relationships",
        json=_relationship_payload(source_id, target_id, is_confidential=True, notes="Secret notes"),
    )
    assert created.status_code == 201, created.text
    rel_id = created.json()["id"]

    full = auth_client.get(f"/crm/relationships/{rel_id}")
    assert full.status_code == 200
    assert full.json()["notes"] == "Secret notes"

    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one()
    role = Role(name="crm_rel_limited", code=f"crm_rel_lim_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    email = f"crm.rel.lim.{uuid4().hex[:6]}@example.com"
    limited = User(
        email=email,
        full_name="CRM Rel Limited",
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(limited)
    db.flush()
    db.add(UserRole(user_id=limited.id, role_id=role.id))
    db.commit()

    assert auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"}).status_code == 200
    readonly = auth_client.get(f"/crm/relationships/{rel_id}")
    assert readonly.status_code == 403


def test_referral_compensation_strip(auth_client: TestClient, db: Session) -> None:
    from uuid import uuid4

    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    referrer = _create_contact(db, "Referrer")
    referred = _create_contact(db, "Referred")

    assert auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"}).status_code == 200
    created = auth_client.post(
        "/crm/relationships/referrals",
        json={
            "referrer_entity_type": "contact",
            "referrer_entity_id": referrer,
            "referred_entity_type": "contact",
            "referred_entity_id": referred,
            "compensation_amount": 5000.0,
            "compensation_currency": "USD",
            "compensation_status": "pending",
        },
    )
    assert created.status_code == 201, created.text

    full = auth_client.get("/crm/relationships/referrals")
    assert full.status_code == 200
    assert full.json()[0]["compensation_amount"] == 5000.0

    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one()
    role = Role(name="crm_ref_limited", code=f"crm_ref_lim_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    email = f"crm.ref.lim.{uuid4().hex[:6]}@example.com"
    limited = User(
        email=email,
        full_name="CRM Ref Limited",
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(limited)
    db.flush()
    db.add(UserRole(user_id=limited.id, role_id=role.id))
    db.commit()

    assert auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"}).status_code == 200
    readonly = auth_client.get("/crm/relationships/referrals")
    assert readonly.status_code == 200
    assert readonly.json()[0]["compensation_amount"] is None


def test_archive_restore_delete(client: TestClient, db: Session) -> None:
    source_id = _create_contact(db)
    target_id = _create_contact(db, "Archive Target")
    created = client.post("/crm/relationships", json=_relationship_payload(source_id, target_id))
    rel_id = created.json()["id"]

    archived = client.post(f"/crm/relationships/{rel_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    restored = client.post(f"/crm/relationships/{rel_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    deleted = client.delete(f"/crm/relationships/{rel_id}")
    assert deleted.status_code == 204


def test_audit_log_on_create(client: TestClient, db: Session) -> None:
    from uuid import UUID

    from sqlalchemy import select

    source_id = _create_contact(db)
    target_id = _create_contact(db, "Audit Target")
    response = client.post("/crm/relationships", json=_relationship_payload(source_id, target_id))
    rel_id = UUID(response.json()["id"])
    logs = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.CRM_RELATIONSHIP,
            ActivityLog.entity_id == rel_id,
        )
    ).all()
    assert len(logs) >= 1


def test_intelligence_dashboard_empty(client: TestClient) -> None:
    response = client.get("/crm/relationships/intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["total_relationships"] == 0


def test_decision_map(client: TestClient, db: Session) -> None:
    company_id = _create_company(db)
    contact_id = _create_contact(db, "Decision Maker")
    response = client.put(
        f"/crm/relationships/company/{company_id}/decision-map",
        json={
            "contact_id": contact_id,
            "role_type": "decision_maker",
            "influence_level": 90,
        },
    )
    assert response.status_code == 200
    dm = client.get(f"/crm/relationships/company/{company_id}/decision-map")
    assert dm.status_code == 200
    assert len(dm.json()["roles"]) == 1


def test_canonical_backfill_replaces_qa_rows_and_is_idempotent(client: TestClient, db: Session) -> None:
    from uuid import UUID

    from investhome_api.models.crm_agreement import CrmAgreement
    from investhome_api.models.crm_company import CrmCompanyContact
    from investhome_api.models.crm_relationship import CrmRelationship
    from investhome_api.models.project import Project
    from investhome_api.services.crm.canonical_relationship_backfill import (
        backfill_canonical_relationships,
        relationship_duplicate_count,
    )

    alpha_id = _create_contact(db, "QA Contact Alpha")
    beta_id = _create_contact(db, "QA Contact Beta")
    real_contact_id = _create_contact(db, "Levi Sunny")
    company_id = _create_company(db, "KW Platin")
    contact_uuid = UUID(real_contact_id)
    company_uuid = UUID(company_id)
    db.add(CrmCompanyContact(company_id=company_uuid, contact_id=contact_uuid))
    project = Project(project_code="P-1812H", project_name="1812 H Place NE")
    db.add(project)
    db.flush()
    db.add(
        CrmAgreement(
            contact_id=contact_uuid,
            project_id=project.id,
            project_group="1812_h_pl",
            source="bitrix",
            source_external_id="1812:canonical-backfill-1",
        )
    )
    db.add(
        CrmAgreement(
            contact_id=contact_uuid,
            project_group="reit",
            source="bitrix",
            source_external_id="reit:canonical-backfill-unlinked",
        )
    )
    db.commit()

    qa = client.post("/crm/relationships", json=_relationship_payload(alpha_id, beta_id))
    assert qa.status_code == 201, qa.text

    first = backfill_canonical_relationships(db)
    db.commit()
    assert first.qa_removed >= 1
    assert first.contact_company_created == 1
    assert first.investor_project_created == 1
    assert first.investor_project_unlinked == 1

    listed = client.get("/crm/relationships?page_size=100")
    assert listed.status_code == 200
    items = listed.json()["items"]
    types = {(row["source_entity_type"], row["target_entity_type"], row["relationship_type"]) for row in items}
    names = {(row["source_display_name"], row["target_display_name"], row["relationship_type"]) for row in items}
    assert ("contact", "company", "contact_company") in types
    assert ("contact", "project", "investor") in types
    assert ("Levi Sunny", "KW Platin", "contact_company") in names
    assert ("Levi Sunny", "1812 H Place NE", "investor") in names
    assert not any(row["source_display_name"] in {"QA Contact Alpha", "QA Contact Beta"} and row["target_display_name"] in {"QA Contact Alpha", "QA Contact Beta"} for row in items)

    second = backfill_canonical_relationships(db)
    db.commit()
    assert second.qa_removed == 0
    assert second.contact_company_created == 0
    assert second.investor_project_created == 0
    assert second.contact_company_skipped >= 1
    assert second.investor_project_skipped >= 1
    assert relationship_duplicate_count(db) == 0
    assert db.query(CrmRelationship).count() >= 2
