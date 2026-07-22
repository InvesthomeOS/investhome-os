"""Marketing lead source API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingLeadSource, MarketingLeadSourceType


def _source_payload(**overrides) -> dict:
    base = {
        "name": f"Test Source {uuid4().hex[:6]}",
        "source_type": "paid",
        "tracking_code": f"TRK-{uuid4().hex[:6]}",
        "utm_defaults_json": {"utm_source": "google", "utm_medium": "cpc"},
    }
    base.update(overrides)
    return base


def test_create_lead_source(client: TestClient) -> None:
    response = client.post("/marketing/sources", json=_source_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["normalized_name"] is not None
    assert body["tracking_readiness"] == "ready"


def test_source_hierarchy(client: TestClient, db: Session) -> None:
    parent = MarketingLeadSource(name="Parent Source", source_type=MarketingLeadSourceType.PAID)
    db.add(parent)
    db.flush()
    child_resp = client.post(
        "/marketing/sources",
        json=_source_payload(name="Child Source", parent_id=str(parent.id)),
    )
    assert child_resp.status_code == 201

    hierarchy = client.get("/marketing/sources/hierarchy")
    assert hierarchy.status_code == 200
    assert len(hierarchy.json()["items"]) >= 1


def test_source_normalization(client: TestClient) -> None:
    created = client.post("/marketing/sources", json=_source_payload()).json()
    norm = client.post(
        f"/marketing/sources/{created['id']}/normalize",
        json={"raw_value": "Google Ads Campaign"},
    )
    assert norm.status_code == 200
    body = norm.json()
    assert body["normalized_value"] == "google_ads_campaign"
    assert body["from_cache"] is False

    norm2 = client.post(
        f"/marketing/sources/{created['id']}/normalize",
        json={"raw_value": "Google Ads Campaign"},
    )
    assert norm2.json()["from_cache"] is True


def test_source_mapping(client: TestClient) -> None:
    created = client.post("/marketing/sources", json=_source_payload()).json()
    mapping = client.post(
        f"/marketing/sources/{created['id']}/mappings",
        json={"provider": "google_ads", "external_key": "campaign_123", "mapping_json": {"campaign": "launch"}},
    )
    assert mapping.status_code == 201

    mappings = client.get(f"/marketing/sources/{created['id']}/mappings")
    assert mappings.status_code == 200
    assert len(mappings.json()["items"]) == 1


def test_circular_hierarchy_blocked(client: TestClient, db: Session) -> None:
    source = MarketingLeadSource(name="Self Parent", source_type=MarketingLeadSourceType.ORGANIC)
    db.add(source)
    db.commit()

    update = client.put(
        f"/marketing/sources/{source.id}",
        json={"parent_id": str(source.id)},
    )
    assert update.status_code == 400
