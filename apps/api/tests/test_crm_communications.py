"""CRM communication center API tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _create_contact(client: TestClient) -> str:
    payload = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": f"Comm Contact {uuid4().hex[:6]}",
        "primary_email": f"comm.{uuid4().hex[:8]}@example.com",
    }
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["contact"]["id"]


def _communication_payload(contact_id: str, **overrides) -> dict:
    base = {
        "channel": "email",
        "direction": "outbound",
        "status": "draft",
        "subject": f"Test email {uuid4().hex[:6]}",
        "body": "Hello from CRM communication center",
        "recipient_entity_type": "contact",
        "recipient_entity_id": contact_id,
        "visibility": "organization",
    }
    base.update(overrides)
    return base


def test_create_draft_communication(client: TestClient) -> None:
    contact_id = _create_contact(client)
    response = client.post("/crm/communications", json=_communication_payload(contact_id))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["communication"]["status"] == "draft"
    assert body["communication"]["channel"] == "email"


def test_list_communications(client: TestClient) -> None:
    contact_id = _create_contact(client)
    client.post("/crm/communications", json=_communication_payload(contact_id))
    response = client.get("/crm/communications?folder=drafts")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_list_threads(client: TestClient) -> None:
    contact_id = _create_contact(client)
    client.post("/crm/communications", json=_communication_payload(contact_id))
    response = client.get("/crm/communications/threads")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_thread_detail(client: TestClient) -> None:
    contact_id = _create_contact(client)
    created = client.post("/crm/communications", json=_communication_payload(contact_id))
    thread_id = created.json()["communication"]["thread_id"]
    assert thread_id is not None
    response = client.get(f"/crm/communications/threads/{thread_id}")
    assert response.status_code == 200
    assert response.json()["id"] == thread_id


def test_create_call_log(client: TestClient) -> None:
    contact_id = _create_contact(client)
    response = client.post(
        "/crm/communications",
        json=_communication_payload(
            contact_id,
            channel="phone",
            status="sent",
            subject="Follow-up call",
            call_duration_seconds=300,
            call_outcome="connected",
            call_direction="outbound",
        ),
    )
    assert response.status_code == 201, response.text
    assert response.json()["communication"]["channel"] == "phone"


def test_list_call_logs(client: TestClient) -> None:
    contact_id = _create_contact(client)
    client.post(
        "/crm/communications",
        json=_communication_payload(contact_id, channel="phone", status="sent"),
    )
    response = client.get("/crm/communications/calls/list")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_create_template(client: TestClient) -> None:
    response = client.post(
        "/crm/communications/templates",
        json={
            "name": f"Welcome {uuid4().hex[:4]}",
            "template_type": "email",
            "subject": "Welcome",
            "body": "Hello {{first_name}}",
            "variables": ["first_name"],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["template_type"] == "email"


def test_list_templates(client: TestClient) -> None:
    response = client.get("/crm/communications/templates/list")
    assert response.status_code == 200


def test_create_signature(client: TestClient) -> None:
    response = client.post(
        "/crm/communications/signatures",
        json={
            "name": "Default",
            "body_html": "<p>Best regards</p>",
            "scope": "personal",
        },
    )
    assert response.status_code == 201, response.text


def test_create_sequence(client: TestClient) -> None:
    response = client.post(
        "/crm/communications/sequences",
        json={
            "name": f"Onboarding {uuid4().hex[:4]}",
            "enrollment_type": "manual",
            "steps": [
                {"step_order": 0, "step_type": "send_email", "wait_days": 0},
                {"step_order": 1, "step_type": "wait", "wait_days": 3},
                {"step_order": 2, "step_type": "create_follow_up"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["step_count"] == 3
    assert response.json()["is_active"] is False


def test_upsert_preferences(client: TestClient) -> None:
    contact_id = _create_contact(client)
    response = client.put(
        f"/crm/communications/preferences/contact/{contact_id}",
        json={
            "preferred_channel": "email",
            "consent_email": True,
            "do_not_contact": False,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["preferred_channel"] == "email"


def test_analytics_dashboard(client: TestClient) -> None:
    response = client.get("/crm/communications/analytics/dashboard")
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert len(metrics) >= 1
    open_rate = next(m for m in metrics if m["key"] == "open_rate")
    assert open_rate["unavailable"] is True


def test_provider_status(client: TestClient) -> None:
    response = client.get("/crm/communications/providers/status")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert all(item["status"] in {"available", "unavailable", "pending_sync", "not_connected"} for item in items)


def test_mark_thread_read(client: TestClient) -> None:
    contact_id = _create_contact(client)
    created = client.post("/crm/communications", json=_communication_payload(contact_id))
    thread_id = created.json()["communication"]["thread_id"]
    response = client.post(f"/crm/communications/threads/{thread_id}/read")
    assert response.status_code == 204


def test_archive_communication(client: TestClient) -> None:
    contact_id = _create_contact(client)
    created = client.post("/crm/communications", json=_communication_payload(contact_id))
    comm_id = created.json()["communication"]["id"]
    response = client.post(f"/crm/communications/{comm_id}/archive")
    assert response.status_code == 204
