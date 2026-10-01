"""CRM pipeline uses live Lead records — active excludes converted/unqualified."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead, LeadStatus


def test_crm_pipeline_active_counts_exclude_converted_and_unqualified(
    client: TestClient, db: Session
) -> None:
    yeni = client.post(
        "/crm/leads",
        json={"full_name": "Pipeline Yeni", "email": "pipe.yeni@example.com", "source": "website"},
    )
    following = client.post(
        "/crm/leads",
        json={
            "full_name": "Pipeline Takip",
            "email": "pipe.follow@example.com",
            "source": "manual",
            "stage": "following",
        },
    )
    qualified = client.post(
        "/crm/leads",
        json={
            "full_name": "Pipeline Nitelikli",
            "email": "pipe.qual@example.com",
            "source": "google",
            "stage": "qualified",
        },
    )
    convert_src = client.post(
        "/crm/leads",
        json={"full_name": "Pipeline Convert", "email": "pipe.convert@example.com", "source": "manual"},
    )
    lost = client.post(
        "/crm/leads",
        json={"full_name": "Pipeline Lost", "email": "pipe.lost@example.com", "source": "other"},
    )
    assert all(row.status_code == 201 for row in (yeni, following, qualified, convert_src, lost)), lost.text

    moved = client.post(f"/crm/leads/{lost.json()['id']}/stage", json={"stage": "unqualified"})
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"] == "unqualified"

    converted = client.post(f"/crm/leads/{convert_src.json()['id']}/convert")
    assert converted.status_code == 200, converted.text
    assert converted.json()["lead"]["stage"] == "converted"

    listed = client.get("/crm/leads")
    assert listed.status_code == 200
    kpis = listed.json()["kpis"]
    assert kpis["yeni"] >= 1
    assert kpis["following"] >= 1
    assert kpis["qualified"] >= 1
    assert kpis["converted"] >= 1
    assert kpis["unqualified"] >= 1
    assert kpis["active"] == kpis["total"] - kpis["converted"] - kpis["unqualified"]
    assert kpis["active"] >= 3

    default_items = listed.json()["items"]
    converted_id = convert_src.json()["id"]
    lost_id = lost.json()["id"]
    assert any(item["id"] == converted_id for item in default_items)
    converted_only = client.get("/crm/leads", params={"stage": "converted"})
    assert converted_only.status_code == 200
    assert all(item["stage"] == "converted" for item in converted_only.json()["items"])
    assert any(item["id"] == converted_id for item in converted_only.json()["items"])

    lost_only = client.get("/crm/leads", params={"stage": "unqualified"})
    assert lost_only.status_code == 200
    assert any(item["id"] == lost_id for item in lost_only.json()["items"])

    stage_move = client.post(f"/crm/leads/{yeni.json()['id']}/stage", json={"stage": "contacted"})
    assert stage_move.status_code == 200
    assert stage_move.json()["stage"] == "contacted"
    db.expire_all()
    row = db.get(Lead, UUID(yeni.json()["id"]))
    assert row is not None
    assert row.status == LeadStatus.CONTACTED
