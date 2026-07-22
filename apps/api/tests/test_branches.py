"""Branch management API tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.company import CompanyEntityType, CompanyStatus


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _create_company(client: TestClient) -> str:
    response = client.post(
        "/companies",
        json={
            "company_name": "Branch Test Co",
            "legal_name": "Branch Test Co Ltd",
            "entity_type": CompanyEntityType.CORPORATION.value,
            "registration_number": "BR-REG-001",
            "tax_id": "1010101010",
            "country": "TR",
            "city": "Istanbul",
            "status": CompanyStatus.ACTIVE.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _branch_payload(company_id: str, **overrides):
    payload = {
        "branch_code": "BR-IST-01",
        "branch_name": "Istanbul HQ",
        "company_id": company_id,
        "branch_type": "head_office",
        "country": "Turkey",
        "city": "Istanbul",
        "full_address": "Levent Mah. Buyukdere Cad. No:1",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_create_branch(client: TestClient) -> None:
    company_id = _create_company(client)
    response = client.post("/branches", json=_branch_payload(company_id))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["branch"]["branch_code"] == "BR-IST-01"
    assert body["branch"]["company_id"] == company_id


def test_duplicate_branch_code_rejected(client: TestClient) -> None:
    company_id = _create_company(client)
    client.post("/branches", json=_branch_payload(company_id))
    response = client.post("/branches", json=_branch_payload(company_id, branch_name="Duplicate"))
    assert response.status_code == 422
    assert response.json()["detail"] == "branch.errors.duplicate_code"


def test_list_and_get_branch(client: TestClient) -> None:
    company_id = _create_company(client)
    created = client.post("/branches", json=_branch_payload(company_id, branch_code="BR-ANK-01"))
    branch_id = created.json()["branch"]["id"]

    listing = client.get("/branches?search=ANK&city=Istanbul")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    detail = client.get(f"/branches/{branch_id}")
    assert detail.status_code == 200
    assert detail.json()["branch_name"] == "Istanbul HQ"


def test_update_assign_manager_and_audit(client: TestClient, db: Session) -> None:
    company_id = _create_company(client)
    created = client.post("/branches", json=_branch_payload(company_id, branch_code="BR-IZM-01"))
    branch_id = created.json()["branch"]["id"]

    update = client.put(
        f"/branches/{branch_id}",
        json={"status": "inactive", "notes": "Seasonal closure"},
    )
    assert update.status_code == 200
    assert update.json()["branch"]["status"] == "inactive"

    assign = client.post(
        f"/branches/{branch_id}/assign-manager",
        json={"manager_user_id": None},
    )
    assert assign.status_code == 200

    logs = db.query(ActivityLog).filter(ActivityLog.entity_type == ActivityEntityType.BRANCH).all()
    assert any(entry.description_key == "activity.branch.created" for entry in logs)


def test_branch_permissions_forbidden(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    response = auth_client.post("/branches", json={"branch_code": "X"})
    assert response.status_code == 403


def test_branch_export(client: TestClient) -> None:
    company_id = _create_company(client)
    client.post("/branches", json=_branch_payload(company_id, branch_code="BR-EXP-01"))
    response = client.get("/branches/export")
    assert response.status_code == 200
    assert "branch_code" in response.text


def test_delete_branch(client: TestClient) -> None:
    company_id = _create_company(client)
    created = client.post("/branches", json=_branch_payload(company_id, branch_code="BR-DEL-01"))
    branch_id = created.json()["branch"]["id"]
    response = client.delete(f"/branches/{branch_id}")
    assert response.status_code == 204
    assert client.get(f"/branches/{branch_id}").status_code == 404
