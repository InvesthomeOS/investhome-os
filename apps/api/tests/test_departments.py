"""Department management API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.company import Company, CompanyEntityType, CompanyStatus
from investhome_api.models.department import DepartmentStatus


def _create_company(client: TestClient) -> str:
    response = client.post(
        "/companies",
        json={
            "company_name": "Dept Test Co",
            "legal_name": "Dept Test Co Ltd",
            "entity_type": CompanyEntityType.CORPORATION.value,
            "registration_number": f"REG-D-{uuid4().hex[:6]}",
            "tax_id": f"{(3030303030 + int(uuid4().hex[:6], 16) % 1000000):010d}",
            "country": "TR",
            "city": "Istanbul",
            "status": CompanyStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_department_payload(company_id: str, **overrides):
    payload = {
        "department_code": f"DEPT-{uuid4().hex[:4].upper()}",
        "department_name": "Finance Department",
        "company_id": company_id,
        "department_type": "finance",
        "status": DepartmentStatus.ACTIVE.value,
    }
    payload.update(overrides)
    return payload


def test_create_department(client: TestClient) -> None:
    company_id = _create_company(client)
    response = client.post("/departments", json=_create_department_payload(company_id))
    assert response.status_code == 201, response.text
    body = response.json()["department"]
    assert body["department_name"] == "Finance Department"
    assert body["company_id"] == company_id
    assert body["status"] == DepartmentStatus.ACTIVE.value


def test_list_departments_with_filters(client: TestClient) -> None:
    company_id = _create_company(client)
    client.post(
        "/departments",
        json=_create_department_payload(company_id, department_name="Engineering", department_type="it"),
    )
    client.post(
        "/departments",
        json=_create_department_payload(
            company_id,
            department_code="HR-001",
            department_name="Human Resources",
            department_type="human_resources",
        ),
    )

    response = client.get(f"/departments?company_id={company_id}&department_type=it")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert all(item["department_type"] == "it" for item in body["items"])


def test_get_update_delete_department(client: TestClient) -> None:
    company_id = _create_company(client)
    created = client.post("/departments", json=_create_department_payload(company_id))
    dept_id = created.json()["department"]["id"]

    get_response = client.get(f"/departments/{dept_id}")
    assert get_response.status_code == 200

    update_response = client.put(
        f"/departments/{dept_id}",
        json={"department_name": "Updated Finance", "cost_center": "CC-100"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["department"]["department_name"] == "Updated Finance"

    delete_response = client.delete(f"/departments/{dept_id}")
    assert delete_response.status_code == 204


def test_duplicate_department_code_returns_422(client: TestClient) -> None:
    company_id = _create_company(client)
    client.post("/departments", json=_create_department_payload(company_id, department_code="FIN-001"))
    response = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="fin-001", department_name="Duplicate"),
    )
    assert response.status_code == 422


def test_department_tree(client: TestClient) -> None:
    company_id = _create_company(client)
    parent = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="EXEC-001", department_name="Executive"),
    ).json()["department"]
    client.post(
        "/departments",
        json=_create_department_payload(
            company_id,
            department_code="FIN-002",
            department_name="Finance",
            parent_department_id=parent["id"],
        ),
    )

    response = client.get(f"/departments/tree?company_id={company_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) >= 1
    root = body["items"][0]
    assert root["department_name"] == "Executive"
    assert len(root["children"]) == 1
    assert root["children"][0]["department_name"] == "Finance"


def test_circular_parent_prevention(client: TestClient) -> None:
    company_id = _create_company(client)
    parent = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="A-001", department_name="Dept A"),
    ).json()["department"]
    child = client.post(
        "/departments",
        json=_create_department_payload(
            company_id,
            department_code="B-001",
            department_name="Dept B",
            parent_department_id=parent["id"],
        ),
    ).json()["department"]

    response = client.put(f"/departments/{parent['id']}", json={"parent_department_id": child["id"]})
    assert response.status_code == 422


def test_self_parent_prevention(client: TestClient) -> None:
    company_id = _create_company(client)
    dept = client.post(
        "/departments",
        json=_create_department_payload(company_id),
    ).json()["department"]

    response = client.put(f"/departments/{dept['id']}", json={"parent_department_id": dept["id"]})
    assert response.status_code == 422


def test_merge_departments(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    source = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="SRC-001", department_name="Source Dept"),
    ).json()["department"]
    target = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="TGT-001", department_name="Target Dept"),
    ).json()["department"]

    response = client.post(
        f"/departments/{source['id']}/merge",
        json={"target_department_id": target["id"], "notes": "Consolidation"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["department"]["id"] == target["id"]

    source_check = client.get(f"/departments/{source['id']}")
    assert source_check.json()["status"] == DepartmentStatus.MERGED.value


def test_move_department(client: TestClient) -> None:
    company_id = _create_company(client)
    parent = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="P-001", department_name="Parent"),
    ).json()["department"]
    child = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="C-001", department_name="Child"),
    ).json()["department"]

    response = client.post(
        f"/departments/{child['id']}/move",
        json={"parent_department_id": parent["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["department"]["parent_department_id"] == parent["id"]


def test_delete_blocked_with_children(client: TestClient) -> None:
    company_id = _create_company(client)
    parent = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="DEL-P", department_name="Parent"),
    ).json()["department"]
    client.post(
        "/departments",
        json=_create_department_payload(
            company_id,
            department_code="DEL-C",
            department_name="Child",
            parent_department_id=parent["id"],
        ),
    )

    response = client.delete(f"/departments/{parent['id']}")
    assert response.status_code == 422


def test_allocation_exceeds_100(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    dept1 = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="AL-001"),
    ).json()["department"]
    dept2 = client.post(
        "/departments",
        json=_create_department_payload(company_id, department_code="AL-002", department_name="Second"),
    ).json()["department"]

    user = db.query(__import__("investhome_api.models.user_auth", fromlist=["User"]).User).first()
    assert user is not None

    client.post(
        f"/departments/{dept1['id']}/assign-employees",
        json={"assignments": [{"user_id": str(user.id), "allocation_percentage": 60}]},
    )
    response = client.post(
        f"/departments/{dept2['id']}/assign-employees",
        json={"assignments": [{"user_id": str(user.id), "allocation_percentage": 50}]},
    )
    assert response.status_code == 422


def test_department_dashboard_metrics(client: TestClient) -> None:
    company_id = _create_company(client)
    client.post("/departments", json=_create_department_payload(company_id))

    response = client.get(f"/departments/dashboard?company_id={company_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_departments"] >= 1


def test_department_audit_events(client: TestClient, db: Session) -> None:
    from uuid import UUID

    company_id = _create_company(client)
    response = client.post("/departments", json=_create_department_payload(company_id))
    dept_id = UUID(response.json()["department"]["id"])

    logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.entity_type == ActivityEntityType.DEPARTMENT,
            ActivityLog.entity_id == dept_id,
        )
        .all()
    )
    assert len(logs) >= 1
    assert any("activity.department.entity_created" in log.description_key for log in logs)


def test_departments_forbidden_without_permission(auth_client: TestClient) -> None:
    auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
    response = auth_client.post(
        "/departments",
        json={
            "department_code": "FORB-001",
            "department_name": "Forbidden",
            "company_id": str(uuid4()),
        },
    )
    assert response.status_code == 403


def test_export_departments(client: TestClient) -> None:
    company_id = _create_company(client)
    client.post("/departments", json=_create_department_payload(company_id))

    response = client.get(f"/departments/export?company_id={company_id}")
    assert response.status_code == 200
    assert "department_code" in response.text
