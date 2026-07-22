"""Marketing asset library API tests — Sprint 8A2."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.document import Document, DocumentStatus, DocumentType, StorageProvider
from investhome_api.models.marketing import MarketingCampaign
from investhome_api.models.project import Project, ProjectType


def _create_document(db: Session, title: str = "Asset Source") -> Document:
    doc = Document(
        title=title,
        original_file_name="photo.jpg",
        stored_file_name=f"{uuid4()}.jpg",
        file_extension="jpg",
        mime_type="image/jpeg",
        file_size=2048,
        storage_provider=StorageProvider.LOCAL,
        storage_key=f"assets/{uuid4()}.jpg",
        checksum="def456",
        document_type=DocumentType.MARKETING_MATERIAL,
        status=DocumentStatus.ACTIVE,
    )
    db.add(doc)
    db.flush()
    return doc


def _create_campaign(db: Session, name: str = "Spring Launch") -> MarketingCampaign:
    campaign = MarketingCampaign(name=name)
    db.add(campaign)
    db.flush()
    return campaign


def _create_project(db: Session, name: str = "Marina Residences") -> Project:
    project = Project(
        project_code=f"PRJ-{uuid4().hex[:8].upper()}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
    )
    db.add(project)
    db.flush()
    return project


def test_create_asset_from_document(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    response = client.post(
        "/marketing/assets/from-document",
        json={"document_id": str(doc.id), "name": "Hero Image", "asset_type": "image"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["asset"]["document_id"] == str(doc.id)
    assert body["asset"]["title"] == "Hero Image"
    assert body["asset"]["rights_status"] == "unknown"


def test_unknown_rights_blocks_readiness(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    created = client.post(
        "/marketing/assets/from-document",
        json={"document_id": str(doc.id), "asset_type": "image"},
    ).json()
    asset_id = created["asset"]["id"]
    readiness = client.get(f"/marketing/assets/{asset_id}/rights-readiness")
    assert readiness.status_code == 200
    assert readiness.json()["state"] == "blocked"
    assert readiness.json()["rights_status"] == "unknown"


def test_update_rights_to_cleared(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    created = client.post(
        "/marketing/assets/from-document",
        json={"document_id": str(doc.id), "asset_type": "image"},
    ).json()
    asset_id = created["asset"]["id"]
    update = client.put(
        f"/marketing/assets/{asset_id}/rights",
        json={"status": "cleared", "license_type": "owned"},
    )
    assert update.status_code == 200
    assert update.json()["asset"]["rights_status"] == "cleared"
    readiness = client.get(f"/marketing/assets/{asset_id}/rights-readiness")
    assert readiness.json()["state"] == "ready"


def test_duplicate_asset_references_same_document(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    created = client.post(
        "/marketing/assets/from-document",
        json={"document_id": str(doc.id), "name": "Original", "asset_type": "image"},
    ).json()
    asset_id = created["asset"]["id"]
    dup = client.post(f"/marketing/assets/{asset_id}/duplicate")
    assert dup.status_code == 201
    assert dup.json()["asset"]["document_id"] == str(doc.id)
    assert dup.json()["asset"]["id"] != asset_id
    assert dup.json()["asset"]["rights_status"] == "unknown"


def test_list_assets(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    client.post(
        "/marketing/assets/from-document", json={"document_id": str(doc.id), "asset_type": "image"}
    )
    response = client.get("/marketing/assets")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_create_with_folder_tags_ai_prep_and_ready_status(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    response = client.post(
        "/marketing/assets/from-document",
        json={
            "document_id": str(doc.id),
            "title": "Brand Logo Pack",
            "asset_type": "logo",
            "folder": "logos",
            "tags": ["brand", "primary"],
            "status": "ready",
            "notes": "Use on dark backgrounds",
            "ai_prep": {
                "language": "en",
                "audience": "investors",
                "market": "UAE",
                "property_type": "residential",
                "country": "AE",
                "city": "Dubai",
                "keywords": ["logo", "brand"],
            },
        },
    )
    assert response.status_code == 201, response.text
    asset = response.json()["asset"]
    assert asset["title"] == "Brand Logo Pack"
    assert asset["folder"] == "logos"
    assert asset["status"] == "ready"
    assert asset["tags"] == ["brand", "primary"]
    assert asset["ai_prep"]["city"] == "Dubai"
    assert asset["notes"] == "Use on dark backgrounds"


def test_search_by_tag_folder_and_type(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    client.post(
        "/marketing/assets/from-document",
        json={
            "document_id": str(doc.id),
            "name": "Social Carousel",
            "asset_type": "social_post",
            "folder": "social",
            "tags": ["instagram", "q3"],
        },
    )
    by_tag = client.get("/marketing/assets", params={"tag": "instagram"})
    assert by_tag.status_code == 200
    assert by_tag.json()["total"] >= 1
    by_folder = client.get("/marketing/assets", params={"folder": "social"})
    assert by_folder.json()["total"] >= 1
    by_search = client.get("/marketing/assets", params={"search": "carousel"})
    assert by_search.json()["total"] >= 1
    by_type = client.get("/marketing/assets", params={"asset_type": "social_post"})
    assert by_type.json()["total"] >= 1


def test_link_campaign_and_project(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    campaign = _create_campaign(db)
    project = _create_project(db)
    db.commit()
    created = client.post(
        "/marketing/assets/from-document",
        json={
            "document_id": str(doc.id),
            "name": "Campaign Hero",
            "asset_type": "image",
            "folder": "campaigns",
        },
    ).json()
    asset_id = created["asset"]["id"]

    linked_campaign = client.post(
        f"/marketing/assets/{asset_id}/link-campaign",
        json={"campaign_id": str(campaign.id)},
    )
    assert linked_campaign.status_code == 200, linked_campaign.text
    assert linked_campaign.json()["asset"]["campaign_id"] == str(campaign.id)
    assert linked_campaign.json()["asset"]["campaign_name"] == campaign.name

    linked_project = client.post(
        f"/marketing/assets/{asset_id}/link-project",
        json={"project_id": str(project.id)},
    )
    assert linked_project.status_code == 200, linked_project.text
    assert linked_project.json()["asset"]["project_id"] == str(project.id)
    assert linked_project.json()["asset"]["project_name"] == project.project_name

    filtered = client.get("/marketing/assets", params={"campaign_id": str(campaign.id)})
    assert filtered.json()["total"] >= 1
    filtered_project = client.get("/marketing/assets", params={"project_id": str(project.id)})
    assert filtered_project.json()["total"] >= 1

    by_campaign_name = client.get("/marketing/assets", params={"search": "Spring"})
    assert by_campaign_name.json()["total"] >= 1


def test_archive_and_restore(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    created = client.post(
        "/marketing/assets/from-document",
        json={"document_id": str(doc.id), "name": "Temp Asset", "asset_type": "document"},
    ).json()
    asset_id = created["asset"]["id"]
    archived = client.post(f"/marketing/assets/{asset_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["asset"]["status"] == "archived"
    listed = client.get("/marketing/assets")
    assert all(item["id"] != asset_id for item in listed.json()["items"])
    restored = client.post(f"/marketing/assets/{asset_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["asset"]["status"] == "draft"
    listed_again = client.get("/marketing/assets")
    assert any(item["id"] == asset_id for item in listed_again.json()["items"])


def test_summary_metrics_honest_counts(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    client.post(
        "/marketing/assets/from-document",
        json={
            "document_id": str(doc.id),
            "name": "Ready One",
            "asset_type": "image",
            "status": "ready",
        },
    )
    summary = client.get("/marketing/assets/summary")
    assert summary.status_code == 200
    metrics = {item["key"]: item for item in summary.json()["metrics"]}
    assert metrics["total_assets"]["state"] in {"ready", "empty"}
    assert metrics["total_assets"]["value"] >= 1
    assert metrics["ready_assets"]["value"] >= 1
    assert metrics["total_assets"]["evidence"]["source"] == "marketing_assets"


def test_export_csv_metadata_only(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    client.post(
        "/marketing/assets/from-document",
        json={
            "document_id": str(doc.id),
            "name": "Export Me",
            "asset_type": "pdf",
            "tags": ["export"],
        },
    )
    response = client.get("/marketing/assets/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    body = response.text
    assert "title" in body
    assert "Export Me" in body
    assert "document_id" in body
    assert "storage_key" not in body
    assert "checksum" not in body


def test_folders_endpoint(client: TestClient) -> None:
    response = client.get("/marketing/assets/folders")
    assert response.status_code == 200
    assert "logos" in response.json()["items"]
    assert "campaigns" in response.json()["items"]


def test_assets_forbidden_without_permission(auth_client: TestClient) -> None:
    auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
    response = auth_client.get("/marketing/assets")
    assert response.status_code == 403


def test_update_asset_fields(client: TestClient, db: Session) -> None:
    doc = _create_document(db)
    db.commit()
    created = client.post(
        "/marketing/assets/from-document",
        json={"document_id": str(doc.id), "name": "Draft Brochure", "asset_type": "brochure"},
    ).json()
    asset_id = created["asset"]["id"]
    updated = client.put(
        f"/marketing/assets/{asset_id}",
        json={
            "title": "Updated Brochure",
            "status": "ready",
            "folder": "documents",
            "description": "Floor plans pack",
            "tags": ["brochure", "floorplan"],
        },
    )
    assert updated.status_code == 200, updated.text
    asset = updated.json()["asset"]
    assert asset["title"] == "Updated Brochure"
    assert asset["status"] == "ready"
    assert asset["folder"] == "documents"
    assert "floorplan" in asset["tags"]
