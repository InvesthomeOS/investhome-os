"""Visual Design Studio API tests."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.main import app
from conftest import TestingSessionLocal
from investhome_api.models.activity import ActivityLog
from investhome_api.models.design_studio import DesignStatus, DesignType
from investhome_api.models.document import Document, DocumentStatus, DocumentType, StorageProvider
from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingElement
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


def _login(auth_client: TestClient, email: str = "admin@example.com") -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _grant_design_permissions(auth_client: TestClient, *, include_save: bool = True) -> None:
    db: Session = next(app.dependency_overrides[get_db]())
    actions = ["view", "create", "update", "archive", "approve"]
    if include_save:
        actions.append("save_version")
    for action in actions:
        perm = db.query(Permission).filter_by(resource="design", action=action).first()
        if perm is None:
            perm = Permission(resource="design", action=action)
            db.add(perm)
            db.flush()
        role = db.query(Role).filter_by(code="designer").first()
        if role is None:
            role = Role(name="Designer", code="designer", is_system_role=False)
            db.add(role)
            db.flush()
        existing = (
            db.query(RolePermission)
            .filter_by(role_id=role.id, permission_id=perm.id)
            .first()
        )
        if existing is None:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = db.query(User).filter_by(email="designer@example.com").first()
    if user is None:
        user = User(
            full_name="Designer User",
            email="designer@example.com",
            hashed_password=hash_password("Demo123!"),
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
        role = db.query(Role).filter_by(code="designer").first()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()


def _seed_project_and_document(client: TestClient) -> tuple[dict, dict]:
    project_payload = {
        "project_code": f"PRJ-DESIGN-{uuid4().hex[:6]}",
        "project_name": "Design Test Project",
        "project_type": ProjectType.RESIDENTIAL.value,
        "development_type": DevelopmentType.GROUND_UP.value,
        "project_status": ProjectStatus.CONSTRUCTION.value,
    }
    project_response = client.post("/projects", json=project_payload)
    assert project_response.status_code == 201
    project = project_response.json()

    db: Session = next(app.dependency_overrides[get_db]())
    document = Document(
        title="Floor Plan Source",
        original_file_name="floor-plan.svg",
        stored_file_name="floor-plan.svg",
        file_extension="svg",
        mime_type="image/svg+xml",
        file_size=1024,
        storage_provider=StorageProvider.LOCAL,
        storage_key=f"documents/{uuid4()}/floor-plan.svg",
        checksum=uuid4().hex,
        document_type=DocumentType.ARCHITECTURAL_DRAWING,
        status=DocumentStatus.ACTIVE,
        project_id=UUID(project["id"]),
    )
    db.add(document)
    db.flush()

    analysis = DrawingAnalysis(
        document_id=document.id,
        document_version_id=document.id,
        processing_status="completed",
        preview_status="ready",
    )
    db.add(analysis)
    db.flush()

    db.add(
        DrawingElement(
            analysis_id=analysis.id,
            element_type="room",
            label="Living Room",
            confidence="high",
            geometry_json='{"type":"polygon"}',
        )
    )
    db.add(
        DrawingElement(
            analysis_id=analysis.id,
            element_type="room",
            label="Kitchen",
            confidence="high",
        )
    )
    db.commit()

    return project, {"id": str(document.id), "title": document.title, "analysis_id": str(analysis.id)}


def _create_design_payload(project_id: str, document_id: str, analysis_id: str) -> dict:
    return {
        "project_id": project_id,
        "document_id": document_id,
        "drawing_analysis_id": analysis_id,
        "title": "Colored Floor Plan v1",
        "description": "Sprint 1 test design",
        "design_type": DesignType.COLORED_FLOOR_PLAN.value,
    }


def test_create_and_list_design_projects(client: TestClient) -> None:
    project, document = _seed_project_and_document(client)
    payload = _create_design_payload(project["id"], document["id"], document["analysis_id"])

    create_response = client.post("/design/projects", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == payload["title"]
    assert created["status"] == DesignStatus.DRAFT.value
    assert created["project_name"] == project["project_name"]
    assert created["document_title"] == document["title"]

    list_response = client.get("/design/projects")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == created["id"]


def test_save_design_version(client: TestClient) -> None:
    project, document = _seed_project_and_document(client)
    create_response = client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    design_id = create_response.json()["id"]

    regions_response = client.get(f"/design/projects/{design_id}/source-regions")
    assert regions_response.status_code == 200
    regions_body = regions_response.json()
    assert regions_body["mode"] == "room_regions"
    assert len(regions_body["regions"]) == 2

    version_payload = {
        "design_parameters": {
            "mode": "room_regions",
            "palette": "default",
            "regions": [
                {"id": regions_body["regions"][0]["id"], "label": "Living Room", "color": "#E8D5B7"},
                {"id": regions_body["regions"][1]["id"], "label": "Kitchen", "color": "#A8C5DA"},
            ],
            "backgroundColor": "#FFFFFF",
        }
    }
    version_response = client.post(f"/design/projects/{design_id}/versions", json=version_payload)
    assert version_response.status_code == 201
    version = version_response.json()
    assert version["version_number"] == 1
    assert version["design_parameters"]["mode"] == "room_regions"

    versions_response = client.get(f"/design/projects/{design_id}/versions")
    assert versions_response.status_code == 200
    assert versions_response.json()["total"] == 1

    detail_response = client.get(f"/design/projects/{design_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["current_version_number"] == 1
    assert detail_response.json()["status"] == DesignStatus.DRAFT.value


def test_design_permissions_enforced(auth_client: TestClient) -> None:
    _grant_design_permissions(auth_client, include_save=False)
    _login(auth_client, "admin@example.com")
    project, document = _seed_project_and_document(auth_client)

    _login(auth_client, "readonly@example.com")
    denied = auth_client.get("/design/projects")
    assert denied.status_code == 403

    _login(auth_client, "designer@example.com")
    allowed = auth_client.get("/design/projects")
    assert allowed.status_code == 200

    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    assert create_response.status_code == 201
    design_id = create_response.json()["id"]

    save_denied = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={
            "design_parameters": {
                "mode": "basic_overlay",
                "palette": "default",
                "regions": [],
                "backgroundColor": "#FFFFFF",
            }
        },
    )
    assert save_denied.status_code == 403

    _grant_design_permissions(auth_client, include_save=True)
    _login(auth_client, "designer@example.com")
    save_allowed = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={
            "design_parameters": {
                "mode": "basic_overlay",
                "palette": "default",
                "regions": [],
                "backgroundColor": "#FFFFFF",
            }
        },
    )
    assert save_allowed.status_code == 201


def test_design_search_provider(client: TestClient) -> None:
    project, document = _seed_project_and_document(client)
    client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )

    search_response = client.get("/search", params={"q": "Colored Floor"})
    assert search_response.status_code == 200
    groups = search_response.json()["groups"]
    design_group = next((group for group in groups if group["entity_type"] == "design_project"), None)
    assert design_group is not None
    assert design_group["total"] >= 1


def test_design_activity_logged(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    project, document = _seed_project_and_document(auth_client)
    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    assert create_response.status_code == 201
    design_id = create_response.json()["id"]

    with TestingSessionLocal() as db:
        logs = db.query(ActivityLog).filter(ActivityLog.entity_id == UUID(design_id)).all()
        keys = {log.description_key for log in logs}
    assert "activity.design.project_created" in keys
    assert "activity.design.source_plan_selected" in keys
