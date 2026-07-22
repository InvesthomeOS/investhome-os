"""Marketing social channel API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient


def _post_payload(**overrides) -> dict:
    base = {"title": f"Post {uuid4().hex[:6]}", "body_text": "Hello social world"}
    base.update(overrides)
    return base


def test_social_dashboard(client: TestClient) -> None:
    resp = client.get("/marketing/social/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider_status"]["connected"] is False


def test_create_and_list_social_posts(client: TestClient) -> None:
    created = client.post("/marketing/social/posts", json=_post_payload()).json()
    assert created["status"] == "draft"
    listed = client.get("/marketing/social/posts")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


def test_social_publish_not_connected(client: TestClient) -> None:
    post = client.post("/marketing/social/posts", json=_post_payload()).json()
    key = f"idempotency-{uuid4().hex}"
    result = client.post(
        f"/marketing/social/posts/{post['id']}/publish",
        json={"idempotency_key": key},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["idempotent"] is False
    assert body.get("published") is False


def test_social_publish_idempotency(client: TestClient) -> None:
    post = client.post("/marketing/social/posts", json=_post_payload()).json()
    key = f"idempotency-{uuid4().hex}"
    first = client.post(
        f"/marketing/social/posts/{post['id']}/publish",
        json={"idempotency_key": key},
    ).json()
    second = client.post(
        f"/marketing/social/posts/{post['id']}/publish",
        json={"idempotency_key": key},
    ).json()
    assert second["idempotent"] is True
    assert first["operation_id"] == second.get("operation_id") or second["idempotent"]


def test_create_social_account(client: TestClient) -> None:
    resp = client.post(
        "/marketing/social/accounts",
        json={"network": "linkedin", "display_name": "Investhome"},
    )
    assert resp.status_code == 201
    assert resp.json()["connection_status"] == "not_connected"
