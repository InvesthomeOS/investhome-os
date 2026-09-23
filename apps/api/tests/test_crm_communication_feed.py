"""CRM communication hub feed: Bitrix history, source-id dedupe, unmatched counts."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
)
from investhome_api.models.crm_communication import CrmCommunication, CrmCommunicationMatchStatus
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind


def _contact(db: Session, name: str) -> CrmContact:
    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        status=CrmContactStatus.ACTIVE,
        primary_email=f"{uuid4().hex[:8]}@example.com",
    )
    db.add(contact)
    db.commit()
    return contact


def test_communication_feed_dedupes_source_id_and_opens_stats(client: TestClient, db: Session) -> None:
    person = _contact(db, "Feed Person")
    other = _contact(db, "Co-owner Person")
    shared = {
        "kind": "email",
        "bitrix_record_id": "99123",
        "direction": "outgoing",
    }
    db.add_all(
        [
            CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=person.id,
                activity_type=CrmActivityType.EMAIL,
                activity_category=CrmActivityCategory.COMMUNICATION,
                title="E-posta: Sözleşme",
                description="<p>Ham HTML body</p>",
                status=CrmActivityStatus.COMPLETED,
                metadata_json={"bitrix_history": shared},
            ),
            CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=other.id,
                activity_type=CrmActivityType.EMAIL,
                activity_category=CrmActivityCategory.COMMUNICATION,
                title="E-posta: Sözleşme",
                description="<p>Ham HTML body</p>",
                status=CrmActivityStatus.COMPLETED,
                metadata_json={"bitrix_history": shared},
            ),
            CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=person.id,
                activity_type=CrmActivityType.WHATSAPP,
                activity_category=CrmActivityCategory.COMMUNICATION,
                title="WhatsApp",
                summary="Merhaba, evraklar hazır.",
                status=CrmActivityStatus.COMPLETED,
                metadata_json={
                    "bitrix_history": {
                        "kind": "whatsapp_message",
                        "bitrix_record_id": "wa-1",
                        "chat_id": "chat-9",
                        "direction": "incoming",
                        "author_name": "Feed Person",
                    }
                },
            ),
        ]
    )
    db.add(
        CrmCommunication(
            channel="email",
            direction="inbound",
            source="live_email",
            match_status=CrmCommunicationMatchStatus.UNMATCHED.value,
            sender_identity="unknown@example.com",
            subject="Kim bu",
            preview="Eşleşmedi",
        )
    )
    db.commit()

    listed = client.get("/crm/live-communications/feed?channel=email")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    email_rows = [item for item in body["items"] if item["channel"] == "email" and "99123" in item["source_key"]]
    assert len(email_rows) == 1
    assert "<p>" not in (email_rows[0]["preview"] or "")
    assert body["stats"]["email"] >= 1
    assert body["stats"]["whatsapp"] >= 1
    assert body["stats"]["unmatched"] >= 1

    conversation = client.get(f"/crm/live-communications/conversation?contact_id={person.id}")
    assert conversation.status_code == 200, conversation.text
    messages = conversation.json()["messages"]
    assert any("evraklar" in str(item.get("summary") or "") for item in messages)
    assert all("bitrix_history" in (item.get("metadata") or {}) for item in messages)

    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=person.id,
            activity_type=CrmActivityType.WHATSAPP,
            activity_category=CrmActivityCategory.COMMUNICATION,
            title="WhatsApp",
            summary="Ikinci mesaj ayni sohbet.",
            status=CrmActivityStatus.COMPLETED,
            metadata_json={
                "bitrix_history": {
                    "kind": "whatsapp_message",
                    "bitrix_record_id": "wa-2",
                    "chat_id": "chat-9",
                    "direction": "outgoing",
                    "author_name": "Agent",
                }
            },
        )
    )
    db.commit()
    grouped = client.get("/crm/live-communications/feed?channel=whatsapp")
    assert grouped.status_code == 200, grouped.text
    wa_rows = [item for item in grouped.json()["items"] if item["conversation_key"] == "chat-9"]
    assert len(wa_rows) == 1
