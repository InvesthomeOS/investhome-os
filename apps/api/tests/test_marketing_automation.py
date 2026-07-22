"""Marketing automation API tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _automation_payload(**overrides) -> dict:
    base = {
        "name": f"Automation {uuid4().hex[:6]}",
        "description": "Test automation workflow",
        "trigger": {"type": "lead_created", "config": {}},
        "conditions": [],
        "actions": [{"type": "notify_team", "config": {}}],
        "is_journey": False,
    }
    base.update(overrides)
    return base


def test_list_automations_empty(client: TestClient) -> None:
    response = client.get("/marketing/automations")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 0
    assert "items" in body


def test_create_automation(client: TestClient) -> None:
    response = client.post("/marketing/automations", json=_automation_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["execution_engine_available"] is False


def test_create_invalid_payload(client: TestClient) -> None:
    response = client.post(
        "/marketing/automations",
        json=_automation_payload(trigger={"type": "invalid_trigger", "config": {}}),
    )
    assert response.status_code == 422


def test_create_missing_actions(client: TestClient) -> None:
    response = client.post(
        "/marketing/automations",
        json=_automation_payload(actions=[]),
    )
    assert response.status_code == 422


def test_get_automation(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    response = client.get(f"/marketing/automations/{automation_id}")
    assert response.status_code == 200
    assert response.json()["id"] == automation_id


def test_update_automation(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    response = client.patch(
        f"/marketing/automations/{automation_id}",
        json={"name": "Updated Automation Name", "change_summary": "Renamed"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Automation Name"
    assert response.json()["version"] == 2


def test_activate_pause_archive_lifecycle(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]

    activate = client.post(f"/marketing/automations/{automation_id}/activate")
    assert activate.status_code == 200, activate.text
    assert activate.json()["status"] == "active"
    assert activate.json()["activated_at"] is not None

    pause = client.post(f"/marketing/automations/{automation_id}/pause")
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    reactivate = client.post(f"/marketing/automations/{automation_id}/activate")
    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "active"

    archive = client.post(f"/marketing/automations/{automation_id}/archive")
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"


def test_invalid_status_transition(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    pause = client.post(f"/marketing/automations/{automation_id}/pause")
    assert pause.status_code == 409


def test_duplicate_automation(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload(name="Original Workflow")).json()
    automation_id = created["id"]
    duplicate = client.post(f"/marketing/automations/{automation_id}/duplicate")
    assert duplicate.status_code == 201, duplicate.text
    body = duplicate.json()
    assert body["status"] == "draft"
    assert "Copy" in body["name"]
    assert body["id"] != automation_id


def test_delete_automation(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    delete = client.delete(f"/marketing/automations/{automation_id}")
    assert delete.status_code == 204
    missing = client.get(f"/marketing/automations/{automation_id}")
    assert missing.status_code == 404


def test_delete_active_automation_blocked(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    client.post(f"/marketing/automations/{automation_id}/activate")
    delete = client.delete(f"/marketing/automations/{automation_id}")
    assert delete.status_code == 409


def test_executions_and_logs(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    client.post(f"/marketing/automations/{automation_id}/activate")

    executions = client.get(f"/marketing/automations/{automation_id}/executions")
    assert executions.status_code == 200
    assert executions.json()["total"] >= 1
    assert executions.json()["items"][0]["status"] == "not_connected"

    logs = client.get(f"/marketing/automations/{automation_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1
    assert logs.json()["items"][0]["level"] in ("info", "warning", "error")


def test_metrics(client: TestClient) -> None:
    created = client.post("/marketing/automations", json=_automation_payload()).json()
    automation_id = created["id"]
    client.post(f"/marketing/automations/{automation_id}/activate")
    metrics = client.get(f"/marketing/automations/{automation_id}/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["execution_engine_available"] is False
    assert body["not_connected_count"] >= 1


def test_automation_not_found(client: TestClient) -> None:
    missing_id = str(uuid4())
    assert client.get(f"/marketing/automations/{missing_id}").status_code == 404
    assert client.patch(f"/marketing/automations/{missing_id}", json={"name": "x"}).status_code == 404


def test_permissions_required(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    from investhome_api.config.settings import get_settings

    get_settings.cache_clear()
    response = client.get("/marketing/automations")
    assert response.status_code in (401, 403)
