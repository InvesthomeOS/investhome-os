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


def test_live_facebook_message_is_not_duplicated_with_timeline_activity(
    client: TestClient, db: Session
) -> None:
    person = _contact(db, "Facebook Feed Person")
    mid = f"mid.{uuid4().hex}"
    comm = CrmCommunication(
        channel="facebook",
        direction="inbound",
        source="live_facebook",
        match_status=CrmCommunicationMatchStatus.MATCHED.value,
        contact_id=person.id,
        sender_identity="1029384756",
        preview="Merhaba tek satir",
        body_text="Merhaba tek satir",
        external_provider_id=mid,
        conversation_key="1029384756",
    )
    db.add(comm)
    db.flush()
    activity = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=person.id,
        activity_type=CrmActivityType.FACEBOOK,
        activity_category=CrmActivityCategory.COMMUNICATION,
        title="Facebook: Merhaba tek satir",
        summary="Merhaba tek satir",
        status=CrmActivityStatus.COMPLETED,
        metadata_json={
            "communication_id": str(comm.id),
            "live_communication": True,
            "channel": "facebook",
            "direction": "incoming",
            "live_thread": {
                "kind": "facebook",
                "chat_id": "1029384756",
                "direction": "incoming",
                "source": "live_facebook",
                "message_id": mid,
            },
        },
    )
    db.add(activity)
    db.flush()
    comm.activity_id = activity.id
    db.commit()

    listed = client.get("/crm/live-communications/feed?channel=facebook")
    assert listed.status_code == 200, listed.text
    rows = [
        item
        for item in listed.json()["items"]
        if "Merhaba tek satir" in str(item.get("preview") or item.get("subject") or "")
    ]
    assert len(rows) == 1


def test_whatsapp_conversation_grouping_keeps_one_row_with_live_mirror(
    client: TestClient, db: Session
) -> None:
    person = _contact(db, "WhatsApp Live Person")
    chat = "905551112233"
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=person.id,
            activity_type=CrmActivityType.WHATSAPP,
            activity_category=CrmActivityCategory.COMMUNICATION,
            title="WhatsApp",
            summary="Son mesaj",
            status=CrmActivityStatus.COMPLETED,
            metadata_json={
                "communication_id": str(uuid4()),
                "live_communication": True,
                "channel": "whatsapp",
                "live_thread": {
                    "kind": "whatsapp",
                    "chat_id": chat,
                    "direction": "incoming",
                    "message_id": "wamid.latest",
                },
            },
        )
    )
    db.add(
        CrmCommunication(
            channel="whatsapp",
            direction="inbound",
            source="live_whatsapp",
            match_status=CrmCommunicationMatchStatus.MATCHED.value,
            contact_id=person.id,
            sender_identity=chat,
            preview="Son mesaj",
            body_text="Son mesaj",
            external_provider_id="wamid.latest",
            conversation_key=chat,
        )
    )
    db.commit()

    grouped = client.get("/crm/live-communications/feed?channel=whatsapp")
    assert grouped.status_code == 200, grouped.text
    wa_rows = [item for item in grouped.json()["items"] if item["conversation_key"] == chat]
    assert len(wa_rows) == 1
