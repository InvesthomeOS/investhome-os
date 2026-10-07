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

    moved = client.post(
        f"/crm/leads/{lost.json()['id']}/stage",
        json={"stage": "unqualified", "junk_reason": "unreachable"},
    )
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


EXPECTED_STAGES = [
    "yeni",
    "contacted",
    "following",
    "proposal",
    "qualified",
    "negotiation",
    "long_term",
    "unqualified",
    "converted",
]


def test_crm_pipeline_exposes_nine_stages_in_required_order(client: TestClient) -> None:
    listed = client.get("/crm/leads")
    assert listed.status_code == 200
    assert listed.json()["stages"] == EXPECTED_STAGES


def test_crm_pipeline_existing_lead_statuses_map_without_rewrite(client: TestClient, db: Session) -> None:
    mapping = [
        (LeadStatus.NEW, "yeni"),
        (LeadStatus.CONTACTED, "contacted"),
        (LeadStatus.FOLLOW_UP, "following"),
        (LeadStatus.PROPOSAL_SENT, "proposal"),
        (LeadStatus.QUALIFIED, "qualified"),
        (LeadStatus.NEGOTIATION, "negotiation"),
        (LeadStatus.MEETING_SCHEDULED, "long_term"),
        (LeadStatus.LOST, "unqualified"),
        (LeadStatus.WON, "converted"),
    ]
    created_ids: dict[str, str] = {}
    for status, stage in mapping:
        lead = Lead(
            full_name=f"Stage {stage}",
            email=f"{stage}.map@example.com",
            source="manual",
            status=status,
            provider="manual",
            ingest_status="ok",
            is_demo=False,
        )
        db.add(lead)
        db.flush()
        created_ids[stage] = str(lead.id)
    db.commit()

    listed = client.get("/crm/leads")
    assert listed.status_code == 200
    by_id = {item["id"]: item["stage"] for item in listed.json()["items"]}
    for stage, lead_id in created_ids.items():
        assert by_id[lead_id] == stage

    movable = [stage for stage in EXPECTED_STAGES if stage != "converted"]
    source_id = created_ids["yeni"]
    for stage in movable:
        payload: dict[str, str] = {"stage": stage}
        if stage == "unqualified":
            payload["junk_reason"] = "unreachable"
        moved = client.post(f"/crm/leads/{source_id}/stage", json=payload)
        assert moved.status_code == 200, moved.text
        assert moved.json()["stage"] == stage
    blocked = client.post(f"/crm/leads/{source_id}/stage", json={"stage": "converted"})
    assert blocked.status_code == 400
