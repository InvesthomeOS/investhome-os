"""Marketing segment API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing import MarketingSegment, MarketingSegmentType


def _segment_payload(**overrides) -> dict:
    base = {
        "name": f"Test Segment {uuid4().hex[:6]}",
        "segment_type": "dynamic",
        "rule_groups": [
            {
                "operator": "and",
                "rules": [{"field_key": "contact.country", "operator": "equals", "value": "US"}],
            }
        ],
    }
    base.update(overrides)
    return base


def test_create_segment_with_rules(client: TestClient) -> None:
    response = client.post("/marketing/segments", json=_segment_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["calculation_status"] == "not_calculated"


def test_segment_field_registry(client: TestClient) -> None:
    response = client.get("/marketing/segments/field-registry")
    assert response.status_code == 200
    fields = response.json()["fields"]
    assert any(f["key"] == "contact.email" for f in fields)


def test_segment_preview_not_calculated(client: TestClient) -> None:
    created = client.post("/marketing/segments", json=_segment_payload()).json()
    preview = client.post(f"/marketing/segments/{created['id']}/preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["state"] == "not_calculated"
    assert body["estimated_count"] is None


def test_segment_invalid_field_rejected(client: TestClient) -> None:
    response = client.post(
        "/marketing/segments",
        json=_segment_payload(
            rule_groups=[{"operator": "and", "rules": [{"field_key": "invalid.field", "operator": "equals", "value": "x"}]}]
        ),
    )
    assert response.status_code == 400


def test_circular_segment_dependency(client: TestClient, db: Session) -> None:
    seg_a = MarketingSegment(name="Seg A", segment_type=MarketingSegmentType.DYNAMIC)
    seg_b = MarketingSegment(name="Seg B", segment_type=MarketingSegmentType.DYNAMIC)
    db.add(seg_a)
    db.add(seg_b)
    db.flush()
    seg_a.depends_on_segment_ids = [str(seg_b.id)]
    seg_b.depends_on_segment_ids = [str(seg_a.id)]
    db.commit()

    response = client.get(f"/marketing/segments/{seg_a.id}/dependencies/validate")
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_segment_calculate_honest_count(client: TestClient) -> None:
    created = client.post("/marketing/segments", json=_segment_payload()).json()
    calc = client.post(f"/marketing/segments/{created['id']}/calculate")
    assert calc.status_code == 200
    body = calc.json()
    assert body["member_count"] is None or isinstance(body["member_count"], int)
