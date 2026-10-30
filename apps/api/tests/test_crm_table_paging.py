"""Tasks and agreements sort in the query, then page that order."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.services.crm.unit_change import HISTORICAL_UNIT_CHANGE_SOURCE


def _contact(client: TestClient, name: str) -> str:
    response = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": name,
            "primary_email": f"{uuid4().hex[:8]}@example.com",
            "primary_phone": "+15551234567",
            "lifecycle_stage": "new",
            "priority": "normal",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["contact"]["id"]


def _task(client: TestClient, **payload: object) -> dict:
    response = client.post("/crm/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["activity"]


def _ids(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_tasks_sort_before_paging(client: TestClient, db: Session) -> None:
    token = f"page-{uuid4().hex[:8]}"
    early = _task(
        client,
        title=f"{token} Alpha",
        due_on="2026-01-01",
        due_time="09:00",
        priority="low",
        task_status="not_started",
    )
    middle = _task(
        client,
        title=f"{token} Middle",
        due_on="2026-06-01",
        due_time="09:00",
        priority="high",
        task_status="in_progress",
    )
    late = _task(
        client,
        title=f"{token} Zebra",
        due_on="2026-12-01",
        due_time="09:00",
        priority="critical",
        task_status="completed",
    )
    db.expire_all()
    for activity_id, start in (
        (early["id"], datetime(2026, 3, 1, tzinfo=UTC)),
        (middle["id"], datetime(2026, 2, 1, tzinfo=UTC)),
        (late["id"], datetime(2026, 1, 1, tzinfo=UTC)),
    ):
        row = db.get(CrmActivity, UUID(activity_id))
        assert row is not None
        row.start_date = start
    db.commit()

    base = {"search": token, "page_size": 2}
    due = client.get("/crm/tasks", params={**base, "sort_by": "due_date", "sort_dir": "asc"})
    assert _ids(due) == [early["id"], middle["id"]]
    due_page = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "due_date", "sort_dir": "asc", "page": 2, "page_size": 2},
    )
    assert _ids(due_page) == [late["id"]]

    title = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "title", "sort_dir": "desc", "page_size": 1},
    )
    assert _ids(title) == [late["id"]]
    title_page = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "title", "sort_dir": "desc", "page": 2, "page_size": 1},
    )
    assert _ids(title_page) == [middle["id"]]

    start = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "start_date", "sort_dir": "asc", "page_size": 3},
    )
    assert _ids(start) == [late["id"], middle["id"], early["id"]]

    priority = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "priority", "sort_dir": "asc", "page_size": 3},
    )
    assert _ids(priority) == [early["id"], middle["id"], late["id"]]

    status = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "status", "sort_dir": "asc", "page_size": 3},
    )
    assert _ids(status) == [early["id"], middle["id"], late["id"]]

    filtered = client.get(
        "/crm/tasks",
        params={
            "search": token,
            "workspace_status": "active",
            "sort_by": "title",
            "sort_dir": "asc",
            "page": 2,
            "page_size": 1,
        },
    )
    assert filtered.json()["total"] == 2
    assert _ids(filtered) == [middle["id"]]

    unknown = client.get(
        "/crm/tasks",
        params={**base, "sort_by": "person_name", "sort_dir": "desc", "page_size": 3},
    )
    assert _ids(unknown) == [early["id"], middle["id"], late["id"]]


def _agreement(
    db: Session,
    *,
    contact_id: str,
    when: date,
    unit: str,
    hemen: bool,
    status: str = "active",
) -> CrmAgreement:
    row = CrmAgreement(
        contact_id=UUID(contact_id),
        project_group="uniloft",
        source="bitrix",
        source_external_id=f"page-{uuid4().hex}",
        status=status,
        agreement_date=when,
        unit_number=unit,
        hemen_kira=hemen,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_agreements_page_and_sort_on_the_query(client: TestClient, db: Session) -> None:
    buyer = _contact(client, "Pager Buyer")
    other = _contact(client, "Other Buyer")
    oldest = _agreement(db, contact_id=other, when=date(2024, 1, 1), unit="A-1", hemen=False)
    middle = _agreement(db, contact_id=buyer, when=date(2025, 6, 1), unit="B-14", hemen=False)
    newest = _agreement(
        db,
        contact_id=buyer,
        when=date(2026, 3, 1),
        unit="C-2",
        hemen=True,
        status="completed",
    )

    first = client.get(
        "/crm/agreements",
        params={"page": 1, "page_size": 2, "sort_by": "agreement_date"},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert [item["id"] for item in body["items"]] == [str(newest.id), str(middle.id)]

    second = client.get(
        "/crm/agreements",
        params={"page": 2, "page_size": 2, "sort_by": "agreement_date", "sort_dir": "desc"},
    )
    assert [item["id"] for item in second.json()["items"]] == [str(oldest.id)]

    rent = client.get(
        "/crm/agreements",
        params={"sort_by": "hemen_kira", "sort_dir": "asc", "page_size": 2, "page": 2},
    )
    assert [item["id"] for item in rent.json()["items"]] == [str(newest.id)]

    found = client.get(
        "/crm/agreements",
        params={"q": "B-14", "sort_by": "agreement_date", "page_size": 10},
    )
    assert found.json()["total"] == 1
    assert found.json()["items"][0]["id"] == str(middle.id)

    named = client.get(
        "/crm/agreements",
        params={"q": "Pager", "status": "completed", "sort_by": "agreement_date"},
    )
    assert named.json()["total"] == 1
    assert named.json()["items"][0]["id"] == str(newest.id)

    unknown = client.get(
        "/crm/agreements",
        params={"sort_by": "customer_name", "sort_dir": "asc", "page_size": 1},
    )
    assert unknown.json()["items"][0]["id"] == str(newest.id)


def test_agreement_total_counts_visible_rows(client: TestClient, db: Session) -> None:
    buyer = _contact(client, "Visible Buyer")
    visible_new = _agreement(db, contact_id=buyer, when=date(2026, 4, 1), unit="V-1", hemen=False)
    visible_mid = _agreement(db, contact_id=buyer, when=date(2025, 6, 1), unit="V-2", hemen=False)
    visible_old = _agreement(db, contact_id=buyer, when=date(2024, 1, 1), unit="V-3", hemen=False)
    still_visible = _agreement(
        db,
        contact_id=buyer,
        when=date(2025, 1, 1),
        unit="V-4",
        hemen=False,
    )
    still_visible.metadata_json = {"relationship_detached": False}
    detached = _agreement(
        db,
        contact_id=buyer,
        when=date(2026, 5, 1),
        unit="D-1",
        hemen=False,
        status="cancelled",
    )
    detached.metadata_json = {"relationship_detached": True}
    historical_source = _agreement(
        db, contact_id=buyer, when=date(2026, 2, 1), unit="H-1", hemen=False
    )
    historical_source.source = HISTORICAL_UNIT_CHANGE_SOURCE
    historical_flag = _agreement(
        db, contact_id=buyer, when=date(2025, 12, 1), unit="H-2", hemen=False
    )
    historical_flag.metadata_json = {"historical_unit_change": True}
    db.commit()

    hidden = {str(detached.id), str(historical_source.id), str(historical_flag.id)}
    expected = [
        str(visible_new.id),
        str(visible_mid.id),
        str(still_visible.id),
        str(visible_old.id),
    ]
    seen: list[str] = []
    for page in (1, 2):
        response = client.get(
            "/crm/agreements",
            params={"page": page, "page_size": 2, "sort_by": "agreement_date", "sort_dir": "desc"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 4
        assert body["pages"] == 2
        ids = [item["id"] for item in body["items"]]
        assert not hidden.intersection(ids)
        seen.extend(ids)
    assert seen == expected
    assert len(seen) == len(set(seen))

    cancelled = client.get("/crm/agreements", params={"status": "cancelled", "page_size": 10})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["total"] == 1
    assert cancelled.json()["pages"] == 1
    assert cancelled.json()["items"][0]["id"] == str(detached.id)
