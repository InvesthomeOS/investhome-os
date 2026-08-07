"""Creative Studio foundation API tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import TestingSessionLocal
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.creative_studio import (
    CreativeStudioDocumentStatus,
    CreativeStudioDocumentType,
    CreativeStudioDocumentVersion,
    CreativeStudioProject,
    CreativeStudioProjectStatus,
)
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password


def _login(client: TestClient, email: str = "admin@example.com") -> None:
    response = client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _grant_cs_permissions(auth_client: TestClient, *, actions: list[str] | None = None) -> None:
    db: Session = next(app.dependency_overrides[get_db]())
    grant_actions = actions or [
        "view",
        "create",
        "update",
        "archive",
        "save_draft",
        "save_version",
        "restore",
    ]
    for action in grant_actions:
        perm = db.query(Permission).filter_by(resource="creative_studio", action=action).first()
        if perm is None:
            perm = Permission(resource="creative_studio", action=action)
            db.add(perm)
            db.flush()
        role = db.query(Role).filter_by(code="cs_editor").first()
        if role is None:
            role = Role(name="CS Editor", code="cs_editor", is_system_role=False)
            db.add(role)
            db.flush()
        existing = (
            db.query(RolePermission)
            .filter_by(role_id=role.id, permission_id=perm.id)
            .first()
        )
        if existing is None:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = db.query(User).filter_by(email="cseditor@example.com").first()
    if user is None:
        user = User(
            full_name="CS Editor",
            email="cseditor@example.com",
            hashed_password=hash_password("Demo123!"),
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
        role = db.query(Role).filter_by(code="cs_editor").first()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()


def _create_project(client: TestClient, name: str = "CS Test Project") -> dict:
    response = client.post(
        "/creative-studio/projects",
        json={"name": name, "description": "Foundation test project"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_document(client: TestClient, project_id: str, title: str = "Landing Page") -> dict:
    response = client.post(
        f"/creative-studio/projects/{project_id}/documents",
        json={
            "title": title,
            "document_type": CreativeStudioDocumentType.LANDING.value,
            "draft_body_json": {"blocks": [{"type": "hero", "text": "Hello"}]},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_projects(client: TestClient) -> None:
    created = _create_project(client)
    assert created["name"] == "CS Test Project"
    assert created["status"] == CreativeStudioProjectStatus.ACTIVE.value
    assert created["owner_id"] is not None
    assert created["archived_at"] is None

    listed = client.get("/creative-studio/projects")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 1
    assert any(item["id"] == created["id"] for item in body["items"])


def test_create_list_get_document(client: TestClient) -> None:
    project = _create_project(client)
    document = _create_document(client, project["id"])
    assert document["title"] == "Landing Page"
    assert document["document_type"] == CreativeStudioDocumentType.LANDING.value
    assert document["status"] == CreativeStudioDocumentStatus.DRAFT.value
    assert document["draft_body_json"]["blocks"][0]["text"] == "Hello"
    assert document["current_version_id"] is None

    listed = client.get(f"/creative-studio/projects/{project['id']}/documents")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = client.get(f"/creative-studio/documents/{document['id']}")
    assert detail.status_code == 200
    assert detail.json()["draft_body_json"]["blocks"][0]["text"] == "Hello"


def test_save_draft(client: TestClient) -> None:
    project = _create_project(client)
    document = _create_document(client, project["id"])

    response = client.put(
        f"/creative-studio/documents/{document['id']}/draft",
        json={"draft_body_json": {"blocks": [{"type": "hero", "text": "Updated"}]}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft_body_json"]["blocks"][0]["text"] == "Updated"
    assert body["draft_updated_at"] is not None


def test_draft_save_does_not_create_version(client: TestClient) -> None:
    project = _create_project(client)
    document = _create_document(client, project["id"])

    client.put(
        f"/creative-studio/documents/{document['id']}/draft",
        json={"draft_body_json": {"blocks": [{"type": "cta", "text": "Click"}]}},
    )

    versions = client.get(f"/creative-studio/documents/{document['id']}/versions")
    assert versions.status_code == 200
    assert versions.json()["total"] == 0

    detail = client.get(f"/creative-studio/documents/{document['id']}")
    assert detail.json()["current_version_id"] is None


def test_create_version_increments(client: TestClient) -> None:
    project = _create_project(client)
    document = _create_document(client, project["id"])

    v1 = client.post(
        f"/creative-studio/documents/{document['id']}/versions",
        json={"label": "v1", "summary": "First snapshot"},
    )
    assert v1.status_code == 201
    assert v1.json()["version_number"] == 1
    assert v1.json()["body_json"]["blocks"][0]["text"] == "Hello"

    client.put(
        f"/creative-studio/documents/{document['id']}/draft",
        json={"draft_body_json": {"blocks": [{"type": "hero", "text": "Second"}]}},
    )
    v2 = client.post(
        f"/creative-studio/documents/{document['id']}/versions",
        json={"label": "v2"},
    )
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2

    detail = client.get(f"/creative-studio/documents/{document['id']}")
    assert detail.json()["current_version_id"] == v2.json()["id"]


def test_list_versions_omits_body_by_default(client: TestClient) -> None:
    project = _create_project(client)
    document = _create_document(client, project["id"])
    client.post(f"/creative-studio/documents/{document['id']}/versions", json={"label": "snap"})

    listed = client.get(f"/creative-studio/documents/{document['id']}/versions")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["body_json"] is None
    assert body["items"][0]["version_number"] == 1

    with_body = client.get(f"/creative-studio/documents/{document['id']}/versions?include_body=true")
    assert with_body.json()["items"][0]["body_json"]["blocks"][0]["text"] == "Hello"


def test_restore_preserves_history(client: TestClient) -> None:
    project = _create_project(client)
    document = _create_document(client, project["id"])

    v1 = client.post(
        f"/creative-studio/documents/{document['id']}/versions",
        json={"body_json": {"blocks": [{"type": "hero", "text": "Original"}]}},
    ).json()

    client.put(
        f"/creative-studio/documents/{document['id']}/draft",
        json={"draft_body_json": {"blocks": [{"type": "hero", "text": "Changed"}]}},
    )
    v2 = client.post(
        f"/creative-studio/documents/{document['id']}/versions",
        json={},
    ).json()
    assert v2["version_number"] == 2

    restore = client.post(
        f"/creative-studio/documents/{document['id']}/versions/{v1['id']}/restore",
        json={"create_version": True},
    )
    assert restore.status_code == 200
    result = restore.json()
    assert result["document"]["draft_body_json"]["blocks"][0]["text"] == "Original"
    assert result["new_version"] is not None
    assert result["new_version"]["version_number"] == 3

    versions = client.get(f"/creative-studio/documents/{document['id']}/versions?include_body=true")
    items = versions.json()["items"]
    assert versions.json()["total"] == 3
    # Old versions must remain unchanged
    by_number = {item["version_number"]: item for item in items}
    assert by_number[1]["body_json"]["blocks"][0]["text"] == "Original"
    assert by_number[2]["body_json"]["blocks"][0]["text"] == "Changed"
    assert by_number[3]["body_json"]["blocks"][0]["text"] == "Original"

    # Direct DB check: version 1 row was not mutated
    db: Session = TestingSessionLocal()
    try:
        row = db.get(CreativeStudioDocumentVersion, UUID(v1["id"]))
        assert row is not None
        assert row.version_number == 1
        assert row.body_json["blocks"][0]["text"] == "Original"
    finally:
        db.close()


def test_archived_projects_hidden_by_default(client: TestClient) -> None:
    created = _create_project(client, name=f"Archive Me {uuid4().hex[:6]}")

    db: Session = TestingSessionLocal()
    try:
        project = db.get(CreativeStudioProject, UUID(created["id"]))
        assert project is not None
        project.archived_at = datetime.now(UTC)
        project.status = CreativeStudioProjectStatus.ARCHIVED
        db.commit()
    finally:
        db.close()

    listed = client.get("/creative-studio/projects")
    assert listed.status_code == 200
    assert all(item["id"] != created["id"] for item in listed.json()["items"])

    with_archived = client.get("/creative-studio/projects?include_archived=true")
    assert with_archived.status_code == 200
    assert any(item["id"] == created["id"] for item in with_archived.json()["items"])


def test_unauthenticated_rejected(auth_client: TestClient) -> None:
    response = auth_client.get("/creative-studio/projects")
    assert response.status_code == 401


def test_permission_failures(auth_client: TestClient) -> None:
    _grant_cs_permissions(auth_client, actions=["view", "create"])
    _login(auth_client, "admin@example.com")
    project = _create_project(auth_client)
    document = _create_document(auth_client, project["id"])

    _login(auth_client, "readonly@example.com")
    denied = auth_client.get("/creative-studio/projects")
    assert denied.status_code == 403

    _login(auth_client, "cseditor@example.com")
    allowed = auth_client.get("/creative-studio/projects")
    assert allowed.status_code == 200

    draft_denied = auth_client.put(
        f"/creative-studio/documents/{document['id']}/draft",
        json={"draft_body_json": {"x": 1}},
    )
    assert draft_denied.status_code == 403

    version_denied = auth_client.post(
        f"/creative-studio/documents/{document['id']}/versions",
        json={},
    )
    assert version_denied.status_code == 403

    _grant_cs_permissions(
        auth_client,
        actions=["view", "create", "save_draft", "save_version", "restore"],
    )
    _login(auth_client, "cseditor@example.com")
    draft_ok = auth_client.put(
        f"/creative-studio/documents/{document['id']}/draft",
        json={"draft_body_json": {"x": 1}},
    )
    assert draft_ok.status_code == 200
    version_ok = auth_client.post(
        f"/creative-studio/documents/{document['id']}/versions",
        json={},
    )
    assert version_ok.status_code == 201


def test_invalid_document_type_rejected(client: TestClient) -> None:
    project = _create_project(client)
    response = client.post(
        f"/creative-studio/projects/{project['id']}/documents",
        json={"title": "Bad", "document_type": "not_a_real_type"},
    )
    assert response.status_code == 422
