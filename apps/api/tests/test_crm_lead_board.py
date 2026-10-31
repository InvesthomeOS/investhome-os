"""Lead list and pipeline totals count the full filtered set, not a 500-row page."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.lead import Lead, LeadStatus


def test_lead_board_counts_more_than_five_hundred_leads(client: TestClient, db: Session) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    rows: list[Lead] = []
    for index in range(501):
        rows.append(
            Lead(
                full_name=f"Scale {index:04d}",
                status=LeadStatus.NEW,
                source="website",
                interested_project="ScaleTower",
                ingest_status="ok",
                is_demo=False,
                created_at=start + timedelta(seconds=index),
                updated_at=start + timedelta(seconds=index),
            )
        )
    follow_start = start + timedelta(days=30)
    for index in range(12):
        rows.append(
            Lead(
                full_name=f"Follow {index:02d}",
                status=LeadStatus.FOLLOW_UP,
                source="referral",
                interested_project="Other",
                ingest_status="ok",
                is_demo=False,
                created_at=follow_start + timedelta(seconds=index),
                updated_at=follow_start + timedelta(seconds=index),
            )
        )
    rows.append(
        Lead(
            full_name="Junked Lead",
            status=LeadStatus.LOST,
            source="website",
            junk_reason="spam",
            ingest_status="ok",
            is_demo=False,
            created_at=start + timedelta(days=40),
            updated_at=start + timedelta(days=40),
        )
    )
    rows.append(
        Lead(
            full_name="Messenger Hidden",
            status=LeadStatus.NEW,
            source="facebook",
            provider="facebook",
            ingest_status="ok",
            is_demo=False,
            created_at=start + timedelta(days=41),
            updated_at=start + timedelta(days=41),
        )
    )
    rows.append(
        Lead(
            full_name="Hidden DM",
            status=LeadStatus.NEW,
            source="website",
            provider="manual",
            metadata_json={"intake": "instagram_dm"},
            ingest_status="failed",
            is_demo=False,
            created_at=start + timedelta(days=42),
            updated_at=start + timedelta(days=42),
        )
    )
    rows.append(
        Lead(
            full_name="Demo Hidden",
            status=LeadStatus.NEW,
            source="website",
            ingest_status="ok",
            is_demo=True,
            created_at=start + timedelta(days=43),
            updated_at=start + timedelta(days=43),
        )
    )
    db.add_all(rows)
    db.commit()

    listed = client.get("/crm/leads", params={"page": 1, "page_size": 100})
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] == 516
    assert body["pages"] == 6
    assert body["kpis"]["total"] == 516
    assert body["kpis"]["yeni"] == 503
    assert body["kpis"]["following"] == 12
    assert body["kpis"]["unqualified"] == 1
    assert body["kpis"]["failed"] == 1
    assert body["kpis"]["active"] == 515
    first_ids = {item["id"] for item in body["items"]}
    assert len(body["items"]) == 100

    second = client.get("/crm/leads", params={"page": 2, "page_size": 100})
    assert second.status_code == 200
    second_ids = {item["id"] for item in second.json()["items"]}
    assert first_ids.isdisjoint(second_ids)

    seen: list[str] = []
    for page in range(1, body["pages"] + 1):
        page_body = client.get("/crm/leads", params={"page": page, "page_size": 100}).json()
        assert page_body["total"] == 516
        seen.extend(item["id"] for item in page_body["items"])
    assert len(seen) == 516
    assert len(set(seen)) == 516

    stage = client.get("/crm/leads", params={"stage": "yeni", "page_size": 50})
    assert stage.status_code == 200
    stage_body = stage.json()
    assert stage_body["total"] == 503
    assert stage_body["kpis"]["yeni"] == 503
    assert stage_body["kpis"]["following"] == 0

    project = client.get("/crm/leads", params={"project": "ScaleTower"})
    assert project.json()["total"] == 501
    assert project.json()["kpis"]["total"] == 501

    search = client.get("/crm/leads", params={"search": "Messenger Hidden"})
    assert search.json()["total"] == 1

    junk = client.get("/crm/leads", params={"junk_reason": "spam"})
    assert junk.json()["total"] == 1
    assert junk.json()["items"][0]["full_name"] == "Junked Lead"

    board = client.get("/crm/leads/board", params={"page_size": 50})
    assert board.status_code == 200, board.text
    columns = {column["stage"]: column for column in board.json()["columns"]}
    assert board.json()["total"] == 516
    assert board.json()["kpis"]["total"] == 516
    assert columns["yeni"]["total"] == 503
    assert columns["following"]["total"] == 12
    assert columns["unqualified"]["total"] == 1
    assert columns["qualified"]["total"] == 0
    assert len(columns["yeni"]["items"]) == 50

    card_ids: list[str] = []
    pages = columns["yeni"]["pages"]
    assert pages == 11
    for page in range(1, pages + 1):
        cards = client.get(
            "/crm/leads/board/cards",
            params={"stage": "yeni", "page": page, "page_size": 50},
        )
        assert cards.status_code == 200, cards.text
        card_body = cards.json()
        assert card_body["total"] == 503
        card_ids.extend(item["id"] for item in card_body["items"])
    assert len(card_ids) == 503
    assert len(set(card_ids)) == 503
    last = client.get(
        "/crm/leads/board/cards",
        params={"stage": "yeni", "page": pages, "page_size": 50},
    ).json()
    assert any(item["full_name"] == "Scale 0000" for item in last["items"])

    pipeline = client.get("/crm/leads/board", params={"surface": "pipeline", "page_size": 50})
    assert pipeline.status_code == 200, pipeline.text
    pipe = pipeline.json()
    assert pipe["total"] == 514
    assert pipe["kpis"]["yeni"] == 501
    pipe_columns = {column["stage"]: column for column in pipe["columns"]}
    assert pipe_columns["yeni"]["total"] == 501
    hidden = client.get("/crm/leads", params={"search": "Hidden DM", "surface": "pipeline"})
    assert hidden.json()["total"] == 0
    visible = client.get("/crm/leads", params={"search": "Hidden DM"})
    assert visible.json()["total"] == 1
