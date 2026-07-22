"""Companies management API tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.company import Company, CompanyEntityType, CompanyStatus


def _create_company_payload(**overrides):
    payload = {
        "company_name": "Acme Holdings",
        "legal_name": "Acme Holdings Ltd",
        "entity_type": CompanyEntityType.CORPORATION.value,
        "registration_number": "REG-1001",
        "tax_id": "1234567890",
        "country": "TR",
        "state": "Istanbul",
        "city": "Istanbul",
        "status": CompanyStatus.ACTIVE.value,
        "industry": "Real Estate",
    }
    payload.update(overrides)
    return payload


def test_create_company(client: TestClient) -> None:
    response = client.post("/companies", json=_create_company_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["company_name"] == "Acme Holdings"
    assert body["legal_name"] == "Acme Holdings Ltd"
    assert body["status"] == CompanyStatus.ACTIVE.value


def test_list_companies_with_search_and_filters(client: TestClient) -> None:
    client.post("/companies", json=_create_company_payload())
    client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Beta Corp",
            legal_name="Beta Corporation",
            registration_number="REG-2002",
            tax_id="98-7654321",
            country="US",
            city="New York",
        ),
    )

    response = client.get("/companies?search=Beta&country=US&status=active")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert any(item["company_name"] == "Beta Corp" for item in body["items"])


def test_get_update_delete_company(client: TestClient) -> None:
    created = client.post("/companies", json=_create_company_payload(registration_number="REG-3003", tax_id="1111111111"))
    company_id = created.json()["id"]

    get_response = client.get(f"/companies/{company_id}")
    assert get_response.status_code == 200

    update_response = client.put(
        f"/companies/{company_id}",
        json={"company_name": "Acme Updated", "industry": "Construction"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["company_name"] == "Acme Updated"

    delete_response = client.delete(f"/companies/{company_id}")
    assert delete_response.status_code == 204


def test_duplicate_legal_name_returns_422(client: TestClient) -> None:
    client.post("/companies", json=_create_company_payload(registration_number="REG-4004", tax_id="2222222222"))
    response = client.post(
        "/companies",
        json=_create_company_payload(registration_number="REG-4005", tax_id="3333333333"),
    )
    assert response.status_code == 422


def test_company_actions(client: TestClient) -> None:
    created = client.post("/companies", json=_create_company_payload(registration_number="REG-5005", tax_id="4444444444"))
    company_id = created.json()["id"]

    archive_response = client.patch(f"/companies/{company_id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == CompanyStatus.ARCHIVED.value

    created2 = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Gamma LLC",
            legal_name="Gamma LLC",
            entity_type=CompanyEntityType.LLC.value,
            registration_number="REG-6006",
            tax_id="5555555555",
        ),
    )
    company_id2 = created2.json()["id"]

    deactivate_response = client.patch(f"/companies/{company_id2}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == CompanyStatus.INACTIVE.value

    duplicate_response = client.post(f"/companies/{company_id2}/duplicate")
    assert duplicate_response.status_code == 201
    assert "(Copy)" in duplicate_response.json()["company"]["company_name"]


def test_export_and_import_companies(client: TestClient) -> None:
    client.post("/companies", json=_create_company_payload(registration_number="REG-7007", tax_id="6666666666"))

    export_response = client.get("/companies/export")
    assert export_response.status_code == 200
    assert "company_name" in export_response.text

    csv_content = "company_name,legal_name,entity_type,registration_number,tax_id,country,status\nImport Co,Import Co LLC,llc,REG-8008,7777777777,TR,draft\n"
    import_response = client.post(
        "/companies/import",
        files={"file": ("companies.csv", csv_content, "text/csv")},
    )
    assert import_response.status_code == 200
    body = import_response.json()
    assert body["imported"] >= 1


def test_company_audit_events(client: TestClient, db: Session) -> None:
    from uuid import UUID

    response = client.post("/companies", json=_create_company_payload(registration_number="REG-9009", tax_id="8888888888"))
    company_id = UUID(response.json()["id"])

    logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.entity_type == ActivityEntityType.COMPANY,
            ActivityLog.entity_id == company_id,
        )
        .all()
    )
    assert len(logs) >= 1
    assert any("activity.company.entity_created" in log.description_key for log in logs)


def test_companies_forbidden_without_permission(auth_client: TestClient) -> None:
    auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
    response = auth_client.post("/companies", json=_create_company_payload())
    assert response.status_code == 403


def test_list_companies_sort_and_pagination(client: TestClient) -> None:
    for index in range(3):
        client.post(
            "/companies",
            json=_create_company_payload(
                company_name=f"Sort Co {index}",
                legal_name=f"Sort Co {index} Ltd",
                registration_number=f"REG-S{index}",
                tax_id=f"999999999{index}",
            ),
        )

    response = client.get("/companies?sort_by=company_name&sort_order=asc&page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["page_size"] == 2
    assert len(body["items"]) <= 2


def test_get_company_not_found(client: TestClient) -> None:
    response = client.get("/companies/00000000-0000-0000-0000-000000000099")
    assert response.status_code == 404


def test_tax_id_valid_tr_and_us(client: TestClient) -> None:
    tr = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Tax TR Co",
            legal_name="Tax TR Co Ltd",
            registration_number="REG-TAX-TR",
            tax_id="12345678901",
            country="TR",
        ),
    )
    assert tr.status_code == 201, tr.text

    us = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Tax US Co",
            legal_name="Tax US Co Inc",
            registration_number="REG-TAX-US",
            tax_id="12-3456789",
            country="US",
            city="New York",
        ),
    )
    assert us.status_code == 201, us.text


def test_tax_id_invalid_rejected(client: TestClient) -> None:
    bad_tr = client.post(
        "/companies",
        json=_create_company_payload(
            registration_number="REG-TAX-BAD-TR",
            tax_id="TAX-INVALID",
            country="TR",
        ),
    )
    assert bad_tr.status_code == 422
    assert "Tax ID format is invalid" in bad_tr.json()["detail"]

    bad_us = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Bad US Tax",
            legal_name="Bad US Tax Inc",
            registration_number="REG-TAX-BAD-US",
            tax_id="123456789",
            country="US",
        ),
    )
    assert bad_us.status_code == 422
    assert "Tax ID format is invalid" in bad_us.json()["detail"]


def test_tax_id_blank_optional_allowed(client: TestClient) -> None:
    response = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="No Tax Co",
            legal_name="No Tax Co Ltd",
            registration_number="REG-TAX-BLANK",
            tax_id="",
            country="TR",
        ),
    )
    assert response.status_code == 201, response.text
    assert response.json().get("tax_id") in (None, "")


def test_tax_id_duplicate_rejected(client: TestClient) -> None:
    first = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Dup Tax A",
            legal_name="Dup Tax A Ltd",
            registration_number="REG-TAX-DUP-A",
            tax_id="1010101010",
        ),
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/companies",
        json=_create_company_payload(
            company_name="Dup Tax B",
            legal_name="Dup Tax B Ltd",
            registration_number="REG-TAX-DUP-B",
            tax_id="1010101010",
        ),
    )
    assert second.status_code == 422
