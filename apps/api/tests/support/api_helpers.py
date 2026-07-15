"""Reusable API test helpers for Investhome OS."""

from __future__ import annotations

from fastapi.testclient import TestClient


def assert_ok_envelope(response, *, expect_request_id: bool = True) -> dict:
    assert response.status_code == 200, response.text
    if expect_request_id:
        assert response.headers.get("X-Request-Id")
    return response.json()


def assert_error_envelope(response, *, status_code: int) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body.get("success") is False or "detail" in body or "error" in body
    assert response.headers.get("X-Request-Id")
    return body


def get_health(client: TestClient) -> dict:
    response = client.get("/health")
    assert response.status_code == 200
    return response.json()
