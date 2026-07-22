"""CRM global search API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient


def _create_contact(client: TestClient, **overrides) -> dict:
    payload = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": f"Search Test {uuid4().hex[:6]}",
        "primary_email": f"search.{uuid4().hex[:8]}@example.com",
        "lifecycle_stage": "new",
        "priority": "normal",
    }
    payload.update(overrides)
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["contact"]


def test_crm_quick_search_finds_contact(client: TestClient) -> None:
    contact = _create_contact(client, display_name="UniqueAlphaSearchName")
    response = client.get("/crm/search/quick?q=UniqueAlphaSearchName")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert any(item["entity_id"] == contact["id"] for item in body["items"])


def test_crm_global_search_with_entity_filter(client: TestClient) -> None:
    _create_contact(client, display_name="BetaFilterContact")
    response = client.post(
        "/crm/search/global",
        json={"query": "BetaFilterContact", "entity_types": ["crm_contact"], "page_size": 10},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert all(item["entity_type"] == "crm_contact" for item in body["items"])


def test_crm_parse_structured_query(client: TestClient) -> None:
    response = client.post("/crm/search/parse", json={"query": 'type:investor company:"World Bank" status:active'})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "investor" in body["parsed"]["entity_types"]
    assert body["parsed"]["free_text"] == ""


def test_crm_parse_invalid_date_syntax(client: TestClient) -> None:
    response = client.post("/crm/search/parse", json={"query": "last_contact:invalid"})
    assert response.status_code == 200
    assert response.json()["errors"]


def test_crm_recent_searches_crud(client: TestClient) -> None:
    create = client.post(
        "/crm/search/recent",
        json={"query": "test query", "result_count": 3},
    )
    assert create.status_code == 201, create.text
    search_id = create.json()["id"]

    listed = client.get("/crm/search/recent")
    assert listed.status_code == 200
    assert any(item["id"] == search_id for item in listed.json())

    delete_one = client.delete(f"/crm/search/recent/{search_id}")
    assert delete_one.status_code == 204

    client.post("/crm/search/recent", json={"query": "another", "result_count": 0})
    clear = client.delete("/crm/search/recent")
    assert clear.status_code == 204
    assert client.get("/crm/search/recent").json() == []


def test_crm_saved_searches(client: TestClient) -> None:
    listed = client.get("/crm/search/saved")
    assert listed.status_code == 200
    defaults = listed.json()
    assert len(defaults) >= 1

    created = client.post(
        "/crm/search/saved",
        json={"name": "My Custom Search", "query": "type:prospect", "entity_types": ["crm_contact"]},
    )
    assert created.status_code == 201, created.text
    saved_id = created.json()["id"]

    executed = client.post(f"/crm/search/saved/{saved_id}/execute")
    assert executed.status_code == 200

    deleted = client.delete(f"/crm/search/saved/{saved_id}")
    assert deleted.status_code == 204


def test_crm_search_zero_results(client: TestClient) -> None:
    response = client.get("/crm/search/quick?q=zzzznonexistentquery99999")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_crm_entity_picker(client: TestClient) -> None:
    _create_contact(client, display_name="PickerEntityTest")
    response = client.post(
        "/crm/search/entity-picker",
        json={"query": "PickerEntity", "entity_types": ["crm_contact"], "page_size": 10},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 1


def test_crm_natural_language_unavailable(client: TestClient) -> None:
    response = client.post("/crm/search/natural-language", json={"query": "show me active investors"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False


def test_crm_search_suggestions(client: TestClient) -> None:
    _create_contact(client, display_name="SuggestMeNow")
    response = client.get("/crm/search/suggestions?q=Suggest")
    assert response.status_code == 200
    assert len(response.json()["suggestions"]) >= 1
