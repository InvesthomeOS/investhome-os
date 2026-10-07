"""Mandatory structured junk reason for Junk Lead (unqualified) transitions."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivityLog
from investhome_api.models.lead import Lead, LeadStatus


def _create_lead(client: TestClient, **overrides: object) -> dict:
    payload = {
        "full_name": "Junk Test Lead",
        "email": "junk.reason@example.com",
        "phone": "+90 555 700 11 01",
        "source": "manual",
        **overrides,
    }
    response = client.post("/crm/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _move(client: TestClient, lead_id: str, stage: str, **extra: object):
    body: dict[str, object] = {"stage": stage, **extra}
    return client.post(f"/crm/leads/{lead_id}/stage", json=body)


def test_move_to_junk_without_reason_is_rejected(client: TestClient, db: Session) -> None:
    lead = _create_lead(client)
    lead_id = lead["id"]
    moved = _move(client, lead_id, "unqualified")
    assert moved.status_code == 422, moved.text
    assert moved.json()["detail"] == "junk_reason_required"
    refreshed = client.get(f"/crm/leads/{lead_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["stage"] == "yeni"
    assert refreshed.json()["junk_reason"] is None
    db.expire_all()
    row = db.get(Lead, UUID(lead_id))
    assert row is not None
    assert row.status == LeadStatus.NEW
    assert row.junk_reason is None


def test_move_to_junk_with_valid_reason_succeeds_and_persists(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, email="junk.valid@example.com", phone="+90 555 700 11 02")
    lead_id = lead["id"]
    moved = _move(client, lead_id, "unqualified", junk_reason="unreachable")
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["stage"] == "unqualified"
    assert body["junk_reason"] == "unreachable"
    assert body["junk_reason_detail"] is None
    assert body["junked_at"]

    refreshed = client.get(f"/crm/leads/{lead_id}")
    assert refreshed.status_code == 200
    detail = refreshed.json()
    assert detail["stage"] == "unqualified"
    assert detail["junk_reason"] == "unreachable"
    assert detail["junked_at"]

    db.expire_all()
    row = db.get(Lead, UUID(lead_id))
    assert row is not None
    assert row.status == LeadStatus.LOST
    assert row.junk_reason == "unreachable"


def test_invalid_junk_reason_is_rejected(client: TestClient) -> None:
    lead = _create_lead(client, email="junk.invalid@example.com", phone="+90 555 700 11 03")
    moved = _move(client, lead["id"], "unqualified", junk_reason="not_a_real_reason")
    assert moved.status_code == 422, moved.text
    assert moved.json()["detail"] == "invalid_junk_reason"
    refreshed = client.get(f"/crm/leads/{lead['id']}")
    assert refreshed.json()["stage"] == "yeni"


def test_patch_and_create_paths_require_junk_reason(client: TestClient) -> None:
    created = client.post(
        "/crm/leads",
        json={
            "full_name": "Create Junk",
            "email": "junk.create@example.com",
            "phone": "+90 555 700 11 04",
            "source": "manual",
            "stage": "unqualified",
        },
    )
    assert created.status_code == 422, created.text
    assert created.json()["detail"] == "junk_reason_required"

    created_ok = client.post(
        "/crm/leads",
        json={
            "full_name": "Create Junk Ok",
            "email": "junk.create.ok@example.com",
            "phone": "+90 555 700 11 05",
            "source": "website",
            "campaign": "spring-form",
            "stage": "unqualified",
            "junk_reason": "spam",
        },
    )
    assert created_ok.status_code == 201, created_ok.text
    assert created_ok.json()["stage"] == "unqualified"
    assert created_ok.json()["junk_reason"] == "spam"

    lead = _create_lead(client, email="junk.patch@example.com", phone="+90 555 700 11 06", full_name="Patch Junk")
    blocked = client.patch(f"/crm/leads/{lead['id']}", json={"stage": "unqualified"})
    assert blocked.status_code == 422, blocked.text
    assert blocked.json()["detail"] == "junk_reason_required"
    patched = client.patch(
        f"/crm/leads/{lead['id']}",
        json={"stage": "unqualified", "junk_reason": "duplicate"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["junk_reason"] == "duplicate"
    assert patched.json()["stage"] == "unqualified"


def test_filter_junk_lead_and_reason(client: TestClient) -> None:
    unreachable = _create_lead(
        client, email="junk.filter.u@example.com", phone="+90 555 700 11 07", full_name="Filter Unreachable"
    )
    budget = _create_lead(
        client, email="junk.filter.b@example.com", phone="+90 555 700 11 08", full_name="Filter Budget"
    )
    active = _create_lead(
        client, email="junk.filter.a@example.com", phone="+90 555 700 11 09", full_name="Filter Active"
    )
    assert _move(client, unreachable["id"], "unqualified", junk_reason="unreachable").status_code == 200
    assert _move(client, budget["id"], "unqualified", junk_reason="insufficient_budget").status_code == 200
    assert _move(client, active["id"], "following").status_code == 200

    junk_only = client.get("/crm/leads", params={"stage": "unqualified"})
    assert junk_only.status_code == 200
    junk_ids = {item["id"] for item in junk_only.json()["items"]}
    assert unreachable["id"] in junk_ids
    assert budget["id"] in junk_ids
    assert active["id"] not in junk_ids

    by_reason = client.get("/crm/leads", params={"stage": "unqualified", "junk_reason": "unreachable"})
    assert by_reason.status_code == 200
    reason_ids = {item["id"] for item in by_reason.json()["items"]}
    assert unreachable["id"] in reason_ids
    assert budget["id"] not in reason_ids
    assert active["id"] not in reason_ids
    assert all(item["junk_reason"] == "unreachable" for item in by_reason.json()["items"])
    assert all(item["stage"] == "unqualified" for item in by_reason.json()["items"])

    code_only = client.get("/crm/leads", params={"junk_reason": "insufficient_budget"})
    assert code_only.status_code == 200
    code_ids = {item["id"] for item in code_only.json()["items"]}
    assert budget["id"] in code_ids
    assert unreachable["id"] not in code_ids
    assert active["id"] not in code_ids


def test_other_stage_moves_do_not_require_junk_reason(client: TestClient) -> None:
    lead = _create_lead(client, email="junk.otherstage@example.com", phone="+90 555 700 11 10")
    moved = _move(client, lead["id"], "following")
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"] == "following"
    assert moved.json()["junk_reason"] is None


def test_leave_junk_preserves_history_and_reenter_requires_new_reason(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, email="junk.reenter@example.com", phone="+90 555 700 11 11")
    lead_id = lead["id"]
    first = _move(client, lead_id, "unqualified", junk_reason="unreachable")
    assert first.status_code == 200
    left = _move(client, lead_id, "following")
    assert left.status_code == 200, left.text
    assert left.json()["stage"] == "following"
    assert left.json()["junk_reason"] == "unreachable"

    db.expire_all()
    row = db.get(Lead, UUID(lead_id))
    assert row is not None
    assert row.status == LeadStatus.FOLLOW_UP
    assert row.junk_reason == "unreachable"

    blocked = _move(client, lead_id, "unqualified")
    assert blocked.status_code == 422
    assert blocked.json()["detail"] == "junk_reason_required"
    assert client.get(f"/crm/leads/{lead_id}").json()["stage"] == "following"

    second = _move(client, lead_id, "unqualified", junk_reason="spam")
    assert second.status_code == 200, second.text
    assert second.json()["junk_reason"] == "spam"
    assert second.json()["stage"] == "unqualified"

    detail = client.get(f"/crm/leads/{lead_id}")
    assert detail.status_code == 200
    activity = detail.json()["activity"]
    junk_events = [
        event
        for event in activity
        if event.get("description") == "crm.leads.stage_changed"
        and (event.get("metadata") or {}).get("to") == "unqualified"
    ]
    assert len(junk_events) >= 2
    reasons = {(event.get("metadata") or {}).get("junk_reason") for event in junk_events}
    assert "unreachable" in reasons
    assert "spam" in reasons
    leave_events = [
        event
        for event in activity
        if event.get("description") == "crm.leads.stage_changed"
        and (event.get("metadata") or {}).get("from") == "unqualified"
        and (event.get("metadata") or {}).get("to") != "unqualified"
    ]
    assert any((event.get("metadata") or {}).get("previous_junk_reason") == "unreachable" for event in leave_events)

    db.expire_all()
    logs = list(
        db.query(ActivityLog).filter(
            ActivityLog.entity_type == ActivityEntityType.LEAD,
            ActivityLog.entity_id == UUID(lead_id),
            ActivityLog.action == ActivityAction.STATUS_CHANGED,
        )
    )
    assert len(logs) >= 3


def test_other_reason_requires_explanation(client: TestClient) -> None:
    lead = _create_lead(client, email="junk.other@example.com", phone="+90 555 700 11 12")
    missing = _move(client, lead["id"], "unqualified", junk_reason="other")
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"] == "junk_reason_detail_required"
    short = _move(client, lead["id"], "unqualified", junk_reason="other", junk_reason_detail="ab")
    assert short.status_code == 422
    assert short.json()["detail"] == "junk_reason_detail_required"
    ok = _move(
        client,
        lead["id"],
        "unqualified",
        junk_reason="other",
        junk_reason_detail="Aile kararı bekleniyor",
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["junk_reason"] == "other"
    assert ok.json()["junk_reason_detail"] == "Aile kararı bekleniyor"
    detail = client.get(f"/crm/leads/{lead['id']}")
    assert detail.json()["junk_reason_detail"] == "Aile kararı bekleniyor"


def test_kanban_non_junk_move_and_tasks_unaffected(client: TestClient) -> None:
    lead = _create_lead(client, email="junk.tasks@example.com", phone="+90 555 700 11 13", full_name="Görev Koruma")
    lead_id = lead["id"]
    contacted = _move(client, lead_id, "contacted")
    assert contacted.status_code == 200, contacted.text
    auto_tasks = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert auto_tasks.status_code == 200
    auto_items = auto_tasks.json()["items"]
    assert len(auto_items) == 1
    auto_id = auto_items[0]["id"]

    manual = client.post(
        "/crm/tasks",
        json={
            "title": "Manuel arama",
            "lead_id": lead_id,
            "due_on": "2026-10-12",
            "due_time": "11:00",
            "timezone": "Europe/Istanbul",
        },
    )
    assert manual.status_code == 201, manual.text
    manual_id = manual.json()["activity"]["id"]

    proposal = _move(client, lead_id, "proposal")
    assert proposal.status_code == 200
    junked = _move(client, lead_id, "unqualified", junk_reason="timing")
    assert junked.status_code == 200, junked.text
    assert junked.json()["junk_reason"] == "timing"

    remaining = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert remaining.status_code == 200
    remaining_ids = {item["id"] for item in remaining.json()["items"]}
    assert auto_id in remaining_ids
    assert manual_id in remaining_ids
    detail = client.get(f"/crm/leads/{lead_id}")
    task_ids = {item["id"] for item in detail.json()["tasks"]}
    assert auto_id in task_ids
    assert manual_id in task_ids
