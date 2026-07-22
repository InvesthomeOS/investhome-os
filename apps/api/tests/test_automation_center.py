"""Automation Center aggregation API tests."""

from __future__ import annotations


def test_automation_overview_requires_auth(client):
    response = client.get("/automation/overview")
    assert response.status_code in {401, 403}


def test_automation_overview_ok(auth_client):
    response = auth_client.get("/automation/overview")
    assert response.status_code == 200
    data = response.json()
    assert "health" in data
    assert "queue_health" in data
    assert "integrations" in data
    assert data["health"]["availability"] in {"available", "degraded", "unavailable"}
    assert isinstance(data["integrations"], list)
    assert len(data["integrations"]) >= 5


def test_automation_workflows_catalog(auth_client):
    response = auth_client.get("/automation/workflows")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["source"] == "arq_cron" for item in data["items"])
    assert any(item["is_placeholder"] for item in data["items"])
    for item in data["items"]:
        if not item["success_rate_available"]:
            assert item["success_rate"] is None


def test_automation_schedules(auth_client):
    response = auth_client.get("/automation/schedules")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["source"] == "arq_cron" for item in data["items"])


def test_automation_integrations_no_secrets(auth_client):
    response = auth_client.get("/automation/integrations")
    assert response.status_code == 200
    payload = response.text.lower()
    assert "sk-" not in payload
    assert "bearer " not in payload
    data = response.json()
    assert any(item["id"] == "n8n" for item in data["items"])


def test_automation_retry_honest(auth_client):
    response = auth_client.post("/automation/errors/00000000-0000-0000-0000-000000000001/retry")
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert "not available" in data["message"].lower()


def test_automation_workflow_detail_system_job(auth_client):
    response = auth_client.get("/automation/workflows/system:work_due_soon")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "arq_cron"
    assert data["success_rate_available"] is False
