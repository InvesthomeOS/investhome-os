from fastapi.testclient import TestClient

from investhome_api.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "Investhome OS API"
    assert "timestamp" in payload


def test_live_endpoint() -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready_endpoint() -> None:
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    payload = response.json()
    assert payload["status"] in ("ready", "not_ready")
    assert "database" in payload
