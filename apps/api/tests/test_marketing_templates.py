"""Marketing template API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient


def _template_payload(**overrides) -> dict:
    base = {
        "name": f"Template {uuid4().hex[:4]}",
        "template_type": "email",
        "body_template": "Hello {{name}}, welcome to {{project}}.",
        "placeholders": [
            {"placeholder_key": "name", "label": "Name", "placeholder_type": "text", "required": True},
            {"placeholder_key": "project", "label": "Project", "placeholder_type": "text", "required": True},
        ],
    }
    base.update(overrides)
    return base


def test_create_template(client: TestClient) -> None:
    response = client.post("/marketing/templates", json=_template_payload())
    assert response.status_code == 201, response.text
    assert response.json()["template"]["status"] == "draft"


def test_validate_placeholders_success(client: TestClient) -> None:
    created = client.post("/marketing/templates", json=_template_payload()).json()
    template_id = created["template"]["id"]
    response = client.post(
        f"/marketing/templates/{template_id}/validate",
        json={"values": {"name": "Alice", "project": "Marina Tower"}},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_placeholders_missing_required(client: TestClient) -> None:
    created = client.post("/marketing/templates", json=_template_payload()).json()
    template_id = created["template"]["id"]
    response = client.post(
        f"/marketing/templates/{template_id}/validate",
        json={"values": {"name": "Alice"}},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert any("project" in e for e in response.json()["errors"])


def test_preview_template(client: TestClient) -> None:
    created = client.post("/marketing/templates", json=_template_payload()).json()
    template_id = created["template"]["id"]
    response = client.post(
        f"/marketing/templates/{template_id}/preview",
        json={"values": {"name": "Bob", "project": "Skyline Residences"}},
    )
    assert response.status_code == 200
    assert "Bob" in response.json()["rendered"]
    assert "Skyline Residences" in response.json()["rendered"]


def test_list_templates(client: TestClient) -> None:
    client.post("/marketing/templates", json=_template_payload())
    response = client.get("/marketing/templates")
    assert response.status_code == 200
    assert response.json()["total"] >= 1
