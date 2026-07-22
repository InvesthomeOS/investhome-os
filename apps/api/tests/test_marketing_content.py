"""Marketing content studio API tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.document import Document, DocumentStatus, DocumentType, StorageProvider
from investhome_api.models.marketing import MarketingApprovalStatus
from investhome_api.models.marketing_content_studio import (
    AssetRightsStatus,
    MarketingAsset,
    MarketingAssetType,
    MarketingContent,
    MarketingContentStatus,
)


def _content_payload(**overrides) -> dict:
    base = {"title": f"Test Content {uuid4().hex[:6]}", "content_type": "blog_post"}
    base.update(overrides)
    return base


def _create_document(db: Session) -> Document:
    doc = Document(
        title="Test Doc",
        original_file_name="test.png",
        stored_file_name=f"{uuid4()}.png",
        file_extension="png",
        mime_type="image/png",
        file_size=1024,
        storage_provider=StorageProvider.LOCAL,
        storage_key=f"test/{uuid4()}.png",
        checksum="abc123",
        document_type=DocumentType.MARKETING_MATERIAL,
        status=DocumentStatus.ACTIVE,
    )
    db.add(doc)
    db.flush()
    return doc


def test_create_content(client: TestClient) -> None:
    response = client.post("/marketing/content", json=_content_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["content"]["status"] == "idea"


def test_invalid_status_transition(client: TestClient) -> None:
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    response = client.post(
        f"/marketing/content/{content_id}/transition",
        json={"target_status": "published"},
    )
    assert response.status_code == 409


def test_valid_status_transition_chain(client: TestClient) -> None:
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    for status in ("requested", "briefing", "draft"):
        resp = client.post(f"/marketing/content/{content_id}/transition", json={"target_status": status})
        assert resp.status_code == 200, resp.text


def test_submit_and_approve_content(client: TestClient) -> None:
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    for status in ("requested", "briefing", "draft", "in_production", "internal_review"):
        client.post(f"/marketing/content/{content_id}/transition", json={"target_status": status})
    submit = client.post(f"/marketing/content/{content_id}/submit-approval")
    assert submit.status_code == 200
    assert submit.json()["content"]["status"] == "pending_approval"
    approve = client.post(f"/marketing/content/{content_id}/approve", json={"notes": "Approved"})
    assert approve.status_code == 200
    assert approve.json()["content"]["status"] == "approved"


def test_publish_blocked_without_approval(client: TestClient) -> None:
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    for status in ("requested", "briefing", "draft", "in_production", "internal_review"):
        client.post(f"/marketing/content/{content_id}/transition", json={"target_status": status})
    publish = client.post(f"/marketing/content/{content_id}/transition", json={"target_status": "published"})
    assert publish.status_code == 409


def test_publishing_readiness(client: TestClient) -> None:
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    readiness = client.get(f"/marketing/content/{content_id}/readiness")
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["state"] in ("ready", "warning", "blocked")


def test_publish_blocked_unknown_asset_rights(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    asset = MarketingAsset(
        name="Unknown Rights Asset",
        asset_type=MarketingAssetType.IMAGE,
        document_id=doc.id,
        file_ref=str(doc.id),
        rights_status=AssetRightsStatus.UNKNOWN,
    )
    db.add(asset)
    db.commit()
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    client.put(f"/marketing/content/{content_id}", json={"asset_ids": [str(asset.id)]})
    for status in (
        "requested", "briefing", "draft", "in_production", "internal_review",
        "pending_approval", "approved",
    ):
        if status == "pending_approval":
            client.post(f"/marketing/content/{content_id}/submit-approval")
            client.post(f"/marketing/content/{content_id}/approve", json={})
        else:
            client.post(f"/marketing/content/{content_id}/transition", json={"target_status": status})
    readiness = client.get(f"/marketing/content/{content_id}/readiness")
    assert readiness.json()["state"] == "blocked"
    assert any("unknown rights" in r.lower() for r in readiness.json()["remediation"])


def test_ai_generation_unavailable(client: TestClient) -> None:
    created = client.post("/marketing/content", json=_content_payload()).json()
    content_id = created["content"]["id"]
    response = client.post(
        f"/marketing/content/{content_id}/ai/generate",
        json={"prompt": "Write a headline"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["auto_publish"] is False
    assert body["requires_review"] is True
    assert body["provider_available"] is False


def test_content_list_and_dashboard(client: TestClient) -> None:
    client.post("/marketing/content", json=_content_payload())
    list_resp = client.get("/marketing/content")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    dash = client.get("/marketing/content/dashboard")
    assert dash.status_code == 200
    assert dash.json()["total"] >= 1
