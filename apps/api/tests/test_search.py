"""Universal global search tests."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.user_auth import Permission, User
from investhome_api.services.search_service import global_search


def _login(auth_client: TestClient, email: str) -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _session(auth_client: TestClient) -> Session:
    from investhome_api.db.session import get_db

    override = auth_client.app.dependency_overrides.get(get_db)
    assert override is not None
    return next(override())


def test_search_requires_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    denied = auth_client.get("/search?q=test")
    assert denied.status_code == 403

    _login(auth_client, "admin@example.com")
    allowed = auth_client.get("/search?q=test")
    assert allowed.status_code == 200


def test_search_finds_lead_by_name(client: TestClient) -> None:
    create = client.post(
        "/leads",
        json={
            "full_name": "Temple District Lead",
            "email": "temple.lead@example.com",
            "status": LeadStatus.NEW.value,
        },
    )
    assert create.status_code == 201

    response = client.get("/search?q=Temple")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    lead_group = next((group for group in payload["groups"] if group["entity_type"] == "lead"), None)
    assert lead_group is not None
    assert any("Temple" in item["title"] for item in lead_group["items"])


def test_search_respects_entity_permissions(auth_client: TestClient) -> None:
    session = _session(auth_client)
    try:
        lead = Lead(full_name="Hidden Search Lead", email="hidden.search@example.com", status=LeadStatus.NEW)
        session.add(lead)
        session.commit()
    finally:
        session.close()

    _login(auth_client, "sales@example.com")
    response = auth_client.get("/search?q=Hidden")
    assert response.status_code == 200
    entity_types = {group["entity_type"] for group in response.json()["groups"]}
    assert "lead" in entity_types
    assert "user" not in entity_types


def test_search_service_highlights_and_groups(auth_client: TestClient) -> None:
    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        lead = Lead(full_name="Albert Levi Prospect", email="albert@example.com", status=LeadStatus.QUALIFIED)
        session.add(lead)
        session.commit()
        result = global_search(session, admin, "Albert")
        assert result.total >= 1
        assert result.groups[0].entity_type == "lead"
        assert result.groups[0].items[0].title == "Albert Levi Prospect"
        assert len(result.groups[0].items[0].highlights) >= 1
    finally:
        session.close()


def test_search_filters_by_entity_type(client: TestClient) -> None:
    client.post(
        "/leads",
        json={
            "full_name": "Numeric Lead 309",
            "email": "309.lead@example.com",
            "status": LeadStatus.NEW.value,
        },
    )
    response = client.get("/search?q=309&entity_types=lead")
    assert response.status_code == 200
    groups = response.json()["groups"]
    assert all(group["entity_type"] == "lead" for group in groups)


def test_search_empty_query_rejected(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    response = auth_client.get("/search?q=%20")
    assert response.status_code == 422


def test_search_excludes_archived_leads(client: TestClient) -> None:
    create = client.post(
        "/leads",
        json={
            "full_name": "Archived Search Lead",
            "email": "archived.search@example.com",
            "status": LeadStatus.NEW.value,
        },
    )
    assert create.status_code == 201
    lead_id = create.json()["id"]

    archive = client.delete(f"/leads/{lead_id}")
    assert archive.status_code == 200

    response = client.get("/search?q=Archived%20Search%20Lead")
    assert response.status_code == 200
    payload = response.json()
    lead_group = next((group for group in payload["groups"] if group["entity_type"] == "lead"), None)
    if lead_group is not None:
        assert all(item["entity_id"] != lead_id for item in lead_group["items"])


def test_sync_system_permissions_adds_search_grants(auth_client: TestClient) -> None:
    from investhome_api.db.auth_seed import sync_system_permissions
    from investhome_api.models.user_auth import Permission

    session = _session(auth_client)
    try:
        before = session.scalar(select(Permission).where(Permission.resource == "search", Permission.action == "view"))
        if before is None:
            synced = sync_system_permissions()
            assert synced >= 1
        else:
            sync_system_permissions()
    finally:
        session.close()

    _login(auth_client, "sales@example.com")
    response = auth_client.get("/search?q=Lead")
    assert response.status_code == 200


def test_search_user_isolated_from_other_recipients(auth_client: TestClient) -> None:
    from investhome_api.models.notification import NotificationPriority, NotificationSource, NotificationType
    from investhome_api.services.notification_service import create_notification

    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        sales = session.scalar(select(User).where(User.email == "sales@example.com"))
        assert admin is not None and sales is not None
        create_notification(
            session,
            recipient_user_id=admin.id,
            type=NotificationType.SYSTEM,
            priority=NotificationPriority.HIGH,
            title_key="notifications.user.deactivated.title",
            message_key="notifications.user.deactivated.message",
            rule_key="user.deactivated",
            related_entity_type="user",
            related_entity_id=admin.id,
            metadata={"related_label": "Secret Admin Alert"},
            source=NotificationSource.ACTIVITY,
            commit=True,
        )
        sales_result = global_search(session, sales, "Secret")
        admin_labels = [
            item.title
            for group in sales_result.groups
            if group.entity_type == "notification"
            for item in group.items
        ]
        assert "Secret Admin Alert" not in admin_labels
    finally:
        session.close()
