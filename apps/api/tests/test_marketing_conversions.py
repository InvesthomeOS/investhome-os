"""Marketing conversion and attribution tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import MarketingConversionEvent


def test_conversion_analytics_not_connected(client: TestClient) -> None:
    response = client.get("/marketing/conversions/analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert "not connected" in body["message"].lower()


def test_attribution_shell_honest(client: TestClient) -> None:
    response = client.get("/marketing/attribution")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False


def test_list_conversion_events(client: TestClient, db: Session) -> None:
    db.add(MarketingConversionEvent(event_type="form_submission"))
    db.commit()
    response = client.get("/marketing/conversions/events")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_provider_statuses_honest(client: TestClient) -> None:
    response = client.get("/marketing/conversions/providers")
    assert response.status_code == 200
    for provider in response.json():
        assert provider["connected"] is False
