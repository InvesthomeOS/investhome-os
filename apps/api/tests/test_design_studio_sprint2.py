"""Visual Design Studio Sprint 2 API tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.design_studio import (
    DesignStatus,
    DesignType,
    FurnitureItem,
    MaterialPackage,
    StylePreset,
)
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from test_design_studio import (
    _create_design_payload,
    _grant_design_permissions,
    _login,
    _seed_project_and_document,
)


def _grant_sprint2_permissions(auth_client: TestClient) -> None:
    _grant_design_permissions(auth_client, include_save=True)
    db: Session = next(app.dependency_overrides[get_db]())
    extra_actions = ["manage_styles", "manage_materials", "manage_furniture", "submit_review"]
    for action in extra_actions:
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
    db.commit()


def test_list_system_style_presets(client: TestClient) -> None:
    from design_studio_seed import seed_design_studio_catalog
    from investhome_api.db.session import get_db

    db = next(app.dependency_overrides[get_db]())
    seed_design_studio_catalog(db)

    response = client.get("/design/style-presets")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 5
    codes = {item["code"] for item in body["items"]}
    for required in ("modern", "luxury", "scandinavian", "industrial", "minimalist"):
        assert required in codes


def test_create_custom_style_preset(auth_client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    response = auth_client.post(
        "/design/style-presets",
        json={
            "name": "Boutique Custom",
            "code": f"boutique_{uuid4().hex[:6]}",
            "description": "Custom test preset",
            "color_palette": {"primary": "#111111"},
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["is_system_preset"] is False


def test_system_style_preset_protected_from_edit(auth_client: TestClient, client: TestClient) -> None:
    from design_studio_seed import seed_design_studio_catalog
    from investhome_api.db.session import get_db

    db = next(app.dependency_overrides[get_db]())
    seed_design_studio_catalog(db)

    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    presets = auth_client.get("/design/style-presets").json()["items"]
    modern = next(p for p in presets if p["code"] == "modern")
    denied = auth_client.patch(f"/design/style-presets/{modern['id']}", json={"name": "Hacked"})
    assert denied.status_code == 403


def test_material_packages_crud(auth_client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    create_response = auth_client.post(
        "/design/material-packages",
        json={
            "name": "Test Package",
            "description": "Sprint 2 test",
            "flooring": "Oak",
            "wall_finish": "White",
            "color_palette": {"primary": "#FFFFFF"},
        },
    )
    assert create_response.status_code == 201
    package_id = create_response.json()["id"]

    list_response = auth_client.get("/design/material-packages")
    assert list_response.status_code == 200
    assert any(item["id"] == package_id for item in list_response.json()["items"])


def test_furniture_catalog_list(client: TestClient) -> None:
    from sqlalchemy import select

    db: Session = next(app.dependency_overrides[get_db]())
    if db.scalar(select(FurnitureItem).limit(1)) is None:
        db.add(
            FurnitureItem(
                name="Test Sofa",
                code=f"test_sofa_{uuid4().hex[:4]}",
                furniture_type="sofa",
                width=200,
                depth=90,
                height=85,
                is_system_item=True,
            )
        )
        db.commit()

    response = client.get("/design/furniture")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_extended_design_version_save(auth_client: TestClient, client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    project, document = _seed_project_and_document(client)
    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    design_id = create_response.json()["id"]

    from design_studio_seed import seed_design_studio_catalog
    from investhome_api.db.session import get_db

    db = next(app.dependency_overrides[get_db]())
    seed_design_studio_catalog(db)

    presets = auth_client.get("/design/style-presets").json()["items"]
    modern = next(p for p in presets if p["code"] == "modern")

    version_response = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={
            "design_parameters": {
                "mode": "basic_overlay",
                "palette": "default",
                "regions": [],
                "backgroundColor": "#FFFFFF",
                "selected_style_preset_id": modern["id"],
                "furniture_items": [],
                "furniture_positions": {},
                "furniture_rotations": {},
                "furniture_dimensions": {},
                "editor_metadata": {},
            }
        },
    )
    assert version_response.status_code == 201
    params = version_response.json()["design_parameters"]
    assert params["selected_style_preset_id"] == modern["id"]


def test_version_increment_and_activity(auth_client: TestClient, client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    project, document = _seed_project_and_document(client)
    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    design_id = create_response.json()["id"]

    from design_studio_seed import seed_design_studio_catalog
    from investhome_api.db.session import get_db

    db = next(app.dependency_overrides[get_db]())
    seed_design_studio_catalog(db)

    presets = auth_client.get("/design/style-presets").json()["items"]
    modern = next(p for p in presets if p["code"] == "modern")
    furniture = auth_client.get("/design/furniture").json()["items"]
    sofa = next(item for item in furniture if item["code"] == "sofa")

    v1 = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={
            "design_parameters": {
                "mode": "basic_overlay",
                "palette": "default",
                "regions": [],
                "backgroundColor": "#FFFFFF",
                "selected_style_preset_id": modern["id"],
            }
        },
    )
    assert v1.status_code == 201
    assert v1.json()["version_number"] == 1

    v2 = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={
            "design_parameters": {
                "mode": "basic_overlay",
                "palette": "default",
                "regions": [],
                "backgroundColor": "#FFFFFF",
                "selected_style_preset_id": modern["id"],
                "furniture_items": [sofa["id"]],
                "furniture_positions": {sofa["id"]: {"x": 100, "y": 120}},
                "furniture_rotations": {sofa["id"]: 0},
            }
        },
    )
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2

    versions = auth_client.get(f"/design/projects/{design_id}/versions").json()["items"]
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2

    activity = auth_client.get(f"/activity/entity/design_project/{design_id}").json()["items"]
    keys = {item["description_key"] for item in activity}
    assert "activity.design.version_saved" in keys
    assert "activity.design.furniture_layout_updated" in keys


def test_compare_design_versions(auth_client: TestClient, client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    project, document = _seed_project_and_document(client)
    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    design_id = create_response.json()["id"]

    base_params = {
        "mode": "basic_overlay",
        "palette": "default",
        "regions": [],
        "backgroundColor": "#FFFFFF",
        "furniture_items": ["item-a"],
        "furniture_positions": {"item-a": {"x": 10, "y": 20}},
    }
    v1 = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={"design_parameters": base_params},
    ).json()

    v2_params = {**base_params, "furniture_items": ["item-a", "item-b"]}
    v2 = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={"design_parameters": v2_params},
    ).json()

    compare_response = auth_client.post(
        f"/design/projects/{design_id}/compare-versions",
        json={"version_a_id": v1["id"], "version_b_id": v2["id"]},
    )
    assert compare_response.status_code == 200
    diff = compare_response.json()["diff"]
    assert diff["furniture_count_a"] == 1
    assert diff["furniture_count_b"] == 2
    assert "item-b" in diff["furniture_added"]


def test_review_workflow(auth_client: TestClient, client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    project, document = _seed_project_and_document(client)
    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    design_id = create_response.json()["id"]

    auth_client.post(
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

    submit_response = auth_client.post(f"/design/projects/{design_id}/submit-review")
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == DesignStatus.READY_FOR_REVIEW.value

    approve_response = auth_client.post(
        f"/design/projects/{design_id}/approve",
        json={"comment": "Looks good"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == DesignStatus.APPROVED.value
    assert approve_response.json()["review_comment"] == "Looks good"


def test_sprint2_search_providers(client: TestClient) -> None:
    from sqlalchemy import select

    db: Session = next(app.dependency_overrides[get_db]())
    if db.scalar(select(StylePreset).where(StylePreset.code == "modern").limit(1)) is None:
        pytest.skip("Style presets not seeded")

    search_response = client.get("/search", params={"q": "modern"})
    assert search_response.status_code == 200
    entity_types = {group["entity_type"] for group in search_response.json()["groups"]}
    assert "style_preset" in entity_types or "design_project" in entity_types


def test_approved_version_immutable(auth_client: TestClient, client: TestClient) -> None:
    _grant_sprint2_permissions(auth_client)
    _login(auth_client)
    project, document = _seed_project_and_document(client)
    create_response = auth_client.post(
        "/design/projects",
        json=_create_design_payload(project["id"], document["id"], document["analysis_id"]),
    )
    design_id = create_response.json()["id"]
    auth_client.post(
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
    auth_client.post(f"/design/projects/{design_id}/submit-review")
    auth_client.post(f"/design/projects/{design_id}/approve")

    denied = auth_client.post(
        f"/design/projects/{design_id}/versions",
        json={
            "design_parameters": {
                "mode": "basic_overlay",
                "palette": "default",
                "regions": [],
                "backgroundColor": "#000000",
            }
        },
    )
    assert denied.status_code == 400
