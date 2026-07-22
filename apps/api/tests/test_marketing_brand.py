"""Marketing Brand Center API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient


def test_create_brand_profile(client: TestClient) -> None:
    response = client.post(
        "/marketing/brand/profiles",
        json={"name": f"Brand {uuid4().hex[:4]}", "is_default": True},
    )
    assert response.status_code == 201, response.text
    assert response.json()["profile"]["name"].startswith("Brand")


def test_brand_overview(client: TestClient) -> None:
    client.post("/marketing/brand/profiles", json={"name": "Overview Brand"})
    response = client.get("/marketing/brand")
    assert response.status_code == 200
    assert response.json()["profile_count"] >= 1


def test_terminology_and_claims(client: TestClient) -> None:
    profile = client.post("/marketing/brand/profiles", json={"name": "Claims Brand"}).json()
    profile_id = profile["profile"]["id"]
    term = client.post(
        f"/marketing/brand/profiles/{profile_id}/terminology",
        json={"term": "Investhome", "preferred_usage": "Investhome OS"},
    )
    assert term.status_code == 201
    prohibited = client.post(
        f"/marketing/brand/profiles/{profile_id}/claims/prohibited",
        json={"claim_text": "guaranteed returns", "severity": "error"},
    )
    assert prohibited.status_code == 201
    check = client.post(
        "/marketing/brand/compliance-check",
        json={"brand_profile_id": profile_id, "body_text": "We offer guaranteed returns on all deals."},
    )
    assert check.status_code == 200
    assert check.json()["result"]["status"] == "failed"


def test_compliance_passes_clean_content(client: TestClient) -> None:
    profile = client.post("/marketing/brand/profiles", json={"name": "Clean Brand"}).json()
    profile_id = profile["profile"]["id"]
    check = client.post(
        "/marketing/brand/compliance-check",
        json={"brand_profile_id": profile_id, "body_text": "Discover premium properties in Istanbul."},
    )
    assert check.status_code == 200
    assert check.json()["result"]["status"] == "passed"
