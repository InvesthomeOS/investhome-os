"""Activity log and audit trail tests."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivityLog
from investhome_api.services.activity_service import (
    compute_field_changes,
    log_activity,
    sanitize_payload,
)


def test_sanitize_payload_redacts_sensitive_fields() -> None:
    result = sanitize_payload(
        {
            "password": "secret",
            "hashed_password": "hash",
            "access_token": "token",
            "full_name": "Ada Lovelace",
        }
    )
    assert result is not None
    assert result["password"] == "[REDACTED]"
    assert result["hashed_password"] == "[REDACTED]"
    assert result["access_token"] == "[REDACTED]"
    assert result["full_name"] == "Ada Lovelace"


def test_compute_field_changes_redacts_sensitive_values() -> None:
    changed, previous, new = compute_field_changes(
        {"notes": "before", "password": "old"},
        {"notes": "after", "password": "new"},
    )
    assert "notes" in changed
    assert "password" in changed
    assert previous["password"] == "[REDACTED]"
    assert new["password"] == "[REDACTED]"
    assert previous["notes"] == "before"
    assert new["notes"] == "after"


def test_lead_create_records_activity(client: TestClient) -> None:
    from investhome_api.models.lead import LeadStatus

    create = client.post(
        "/leads",
        json={
            "full_name": "Activity Lead",
            "email": "activity.lead@example.com",
            "status": LeadStatus.NEW.value,
        },
    )
    assert create.status_code == 201
    lead_id = UUID(create.json()["id"])

    from investhome_api.db.session import get_db

    override = client.app.dependency_overrides.get(get_db)
    assert override is not None
    session: Session = next(override())
    try:
        entries = session.scalars(
            select(ActivityLog).where(ActivityLog.entity_id == lead_id)
        ).all()
        assert len(entries) >= 1
        assert any(entry.description_key == "activity.lead.created" for entry in entries)
    finally:
        session.close()


def test_activity_list_requires_permission(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login",
        json={"email": "sales@example.com", "password": "Demo123!"},
    )
    assert login.status_code == 200

    denied = auth_client.get("/activity")
    assert denied.status_code == 403

    admin_login = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "Demo123!"},
    )
    assert admin_login.status_code == 200

    allowed = auth_client.get("/activity")
    assert allowed.status_code == 200
    assert "items" in allowed.json()


def test_entity_activity_respects_resource_permissions(auth_client: TestClient) -> None:
    entity_id = uuid4()
    from investhome_api.db.session import get_db

    override = auth_client.app.dependency_overrides.get(get_db)
    assert override is not None
    session: Session = next(override())
    try:
        log_activity(
            session,
            action=ActivityAction.CREATED,
            entity_type=ActivityEntityType.LEAD,
            entity_id=entity_id,
            description_key="activity.lead.created",
            metadata={"name": "Hidden Lead"},
            commit=True,
        )
    finally:
        session.close()

    auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
    response = auth_client.get(f"/activity/entity/lead/{entity_id}")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    auth_client.post("/auth/login", json={"email": "sales@example.com", "password": "Demo123!"})
    sales_response = auth_client.get(f"/activity/entity/lead/{entity_id}")
    assert sales_response.status_code == 200
    assert sales_response.json()["total"] == 1
