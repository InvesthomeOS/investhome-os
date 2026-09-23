"""CRM tags live workspace tests."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactTag,
    CrmContactType,
    CrmRecordKind,
    CrmTag,
    CrmTagEvent,
)


def test_crm_tags_create_edit_deactivate_assign(client: TestClient, db: Session) -> None:
    create = client.post(
        "/crm/tags",
        json={"name": "QA Live Tag", "description": "Live verification", "status": "active"},
    )
    assert create.status_code == 201, create.text
    tag = create.json()
    tag_id = UUID(tag["id"])
    assert tag["name"] == "QA Live Tag"
    assert tag["status"] == "active"
    assert tag["usage_count"] == 0

    listed = client.get("/crm/tags")
    assert listed.status_code == 200
    body = listed.json()
    assert "stats" in body
    assert body["stats"]["total_tags"] >= 1
    assert any(item["name"] == "QA Live Tag" for item in body["items"])

    patched = client.patch(f"/crm/tags/{tag['id']}", json={"description": "Updated live tag"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["description"] == "Updated live tag"

    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        record_kind=CrmRecordKind.PERSON,
        display_name="Tag Assign Person",
        status=CrmContactStatus.ACTIVE,
        primary_email="tag.assign@example.com",
    )
    db.add(contact)
    db.commit()

    assigned = client.post(f"/crm/contacts/{contact.id}/tags", json={"tag_id": tag["id"]})
    assert assigned.status_code == 200, assigned.text
    names = [item["name"] for item in assigned.json()]
    assert "QA Live Tag" in names

    duplicate = client.post(f"/crm/contacts/{contact.id}/tags", json={"tag_id": tag["id"]})
    assert duplicate.status_code == 409

    people = client.get(f"/crm/contacts?tag_id={tag['id']}")
    assert people.status_code == 200
    assert any(item["id"] == str(contact.id) for item in people.json()["items"])

    deactivated = client.post(f"/crm/tags/{tag['id']}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["usage_count"] == 1

    still_there = db.get(CrmTag, tag_id)
    assert still_there is not None
    assert still_there.status == "inactive"

    blocked = client.post(f"/crm/contacts/{contact.id}/tags", json={"tag_id": tag["id"]})
    assert blocked.status_code == 409

    removed = client.delete(f"/crm/contacts/{contact.id}/tags/{tag['id']}")
    assert removed.status_code == 200
    assert all(item["id"] != tag["id"] for item in removed.json())

    events = list(db.scalars(select(CrmTagEvent).where(CrmTagEvent.tag_id == tag_id)).all())
    actions = {event.action for event in events}
    assert {"created", "updated", "assigned", "deactivated", "removed"} <= actions


def test_crm_tags_do_not_hard_delete_in_use(client: TestClient, db: Session) -> None:
    tag = CrmTag(name="Keep Used Tag", status="active")
    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        record_kind=CrmRecordKind.PERSON,
        display_name="Used Tag Person",
        status=CrmContactStatus.ACTIVE,
        primary_email="used.tag@example.com",
    )
    db.add_all([tag, contact])
    db.flush()
    db.add(CrmContactTag(contact_id=contact.id, tag_id=tag.id))
    db.commit()

    response = client.post(f"/crm/tags/{tag.id}/deactivate")
    assert response.status_code == 200
    assert db.get(CrmTag, tag.id) is not None
    link = db.scalar(select(CrmContactTag).where(CrmContactTag.tag_id == tag.id))
    assert link is not None
