"""Enterprise architecture foundation verification tests."""

from fastapi.testclient import TestClient

from support.api_helpers import assert_error_envelope, assert_ok_envelope


def test_request_id_header_on_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    request_id = response.headers.get("X-Request-Id")
    assert request_id
    body = response.json()
    assert body.get("request_id") == request_id


def test_health_v2_envelope(client: TestClient) -> None:
    response = client.get("/health/v2")
    payload = assert_ok_envelope(response)
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["meta"]["request_id"]


def test_meta_feature_flags(client: TestClient) -> None:
    response = client.get("/meta")
    payload = assert_ok_envelope(response)
    flags = payload["data"]["feature_flags"]
    assert isinstance(flags, dict)
    assert "company_foundation" in flags


def test_standardized_http_error(client: TestClient) -> None:
    response = client.get("/leads/00000000-0000-0000-0000-000000000099")
    body = assert_error_envelope(response, status_code=404)
    assert body.get("detail") or body.get("error")


def test_validation_error_envelope(client: TestClient) -> None:
    response = client.get("/search", params={"q": ""})
    body = assert_error_envelope(response, status_code=422)
    assert body.get("error", {}).get("code") == "validation_error" or body.get("detail")
