"""Bitrix history import and contact timeline tests."""

from __future__ import annotations

import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
)
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType
from investhome_api.services.crm.bitrix_history_import import apply_import, classify_activity, plan_import


def test_classify_activity_uses_provider_not_type_id_six() -> None:
    assert classify_activity({"TYPE_ID": "6", "PROVIDER_ID": "CRM_TASKS_TASK", "SUBJECT": "CRM: takip"}) == "task"
    assert classify_activity({"TYPE_ID": "6", "PROVIDER_ID": "CRM_TODO", "PROVIDER_TYPE_ID": "TODO", "SUBJECT": "Kaan Kalyon Müşteri"}) == "meeting"
    assert classify_activity({"TYPE_ID": "6", "PROVIDER_ID": "CRM_SMS", "PROVIDER_TYPE_ID": "SMS", "SUBJECT": "Gönderilen SMS mesajı"}) == "sms"
    assert classify_activity({"TYPE_ID": "6", "PROVIDER_ID": "IMOPENLINES_SESSION", "SUBJECT": "Open Channel chat WhatsApp"}) == "whatsapp_session"
    assert classify_activity({"TYPE_ID": "4", "PROVIDER_ID": "CRM_EMAIL", "SUBJECT": "Launch"}) == "email"
    assert classify_activity({"TYPE_ID": "6", "PROVIDER_ID": "CRM_WEBFORM", "SUBJECT": "CRM form submitted"}) == "other"


def test_plan_import_matches_canonical_uuid_and_keeps_whatsapp_messages(db: Session, tmp_path: Path) -> None:
    contact = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Kaan Kalyon",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Aktif Musteriler.xls:34456"]}},
    )
    db.add(contact)
    db.flush()
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.COMMENT,
            activity_category=CrmActivityCategory.NOTE,
            title="Imported comment",
            description="same comment body",
            status=CrmActivityStatus.COMPLETED,
            metadata_json={"bitrix_historical_comment": {"import_key": "safe-1", "content_sha256": "x"}},
        )
    )
    db.commit()

    archive = tmp_path / "BITRIX_FINAL_HISTORY_ARCHIVE"
    lead_dir = archive / "raw" / "leads"
    chat_dir = archive / "raw" / "chats" / "live"
    lead_dir.mkdir(parents=True)
    chat_dir.mkdir(parents=True)
    (lead_dir / "34456.json").write_text(
        json.dumps(
            {
                "canonical_crm_contact_id": str(contact.id),
                "person_name": "Kaan Kalyon",
                "bitrix_entity_type": "lead",
                "bitrix_entity_id": "34456",
                "timeline_comments": [
                    {"ID": "1", "COMMENT": "same comment body", "AUTHOR_ID": "92", "CREATED": "2026-01-01T10:00:00+03:00"},
                    {"ID": "2", "COMMENT": "new live comment", "AUTHOR_ID": "92", "CREATED": "2026-01-02T10:00:00+03:00"},
                ],
                "crm_activities": [
                    {"ID": "10", "TYPE_ID": "6", "PROVIDER_ID": "IMOPENLINES_SESSION", "SUBJECT": "Open Channel chat WhatsApp", "CREATED": "2026-01-03T10:00:00+03:00"},
                    {"ID": "11", "TYPE_ID": "6", "PROVIDER_ID": "CRM_SMS", "PROVIDER_TYPE_ID": "SMS", "SUBJECT": "Gönderilen SMS mesajı", "CREATED": "2026-01-04T10:00:00+03:00"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (chat_dir / "lead_34456.json").write_text(
        json.dumps(
            {
                "canonical_crm_contact_id": str(contact.id),
                "person_name": "Kaan Kalyon",
                "bitrix_entity_type": "lead",
                "bitrix_entity_id": "34456",
                "chats": [
                    {
                        "chat_id": "11390",
                        "messages": [
                            {
                                "message_id": "2019566",
                                "chat_id": "11390",
                                "sender_id": "92",
                                "sender_name": "Beyza Karakuş",
                                "direction": "outgoing",
                                "date_time": "2025-12-18T09:26:55+03:00",
                                "message_text": "Merhaba Kaan",
                            },
                            {
                                "message_id": "2019567",
                                "chat_id": "11390",
                                "sender_id": "0",
                                "sender_name": "Kaan Kalyon",
                                "direction": "incoming",
                                "date_time": "2025-12-18T09:27:55+03:00",
                                "message_text": "Merhaba",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    plans, report = plan_import(db, archive)
    kinds = [plan.activity_type.value for plan in plans]
    wa_keys = [plan.import_key for plan in plans if plan.import_key.startswith("bitrix:wa:")]
    assert report.matched_contacts == 1
    assert report.unmatched_contacts == 0
    assert report.whatsapp_messages == 2
    assert wa_keys == ["bitrix:wa:11390:2019566", "bitrix:wa:11390:2019567"]
    assert kinds.count("comment") == 1
    assert kinds.count("sms") == 1
    assert kinds.count("whatsapp") == 3
    assert report.duplicates_skipped == 1

    apply_import(db, plans, actor=None)
    db.commit()
    skipped, third = plan_import(db, archive)
    assert skipped == []
    assert third.new_activities == 0
    assert third.duplicates_skipped >= 5


def test_contact_timeline_uses_bitrix_author_and_whatsapp_metadata(client: TestClient, db: Session) -> None:
    contact = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Timeline WA",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
    )
    db.add(contact)
    db.flush()
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.WHATSAPP,
            activity_category=CrmActivityCategory.COMMUNICATION,
            title="WhatsApp: Merhaba",
            description="Merhaba",
            status=CrmActivityStatus.COMPLETED,
            metadata_json={
                "bitrix_history": {
                    "import_key": "bitrix:wa:11390:1",
                    "kind": "whatsapp_message",
                    "author_name": "Beyza Karakuş",
                    "chat_id": "11390",
                    "message_id": "1",
                    "direction": "outgoing",
                    "source": "bitrix",
                }
            },
        )
    )
    db.commit()
    timeline = client.get(f"/crm/contacts/{contact.id}/timeline")
    assert timeline.status_code == 200
    item = next(row for row in timeline.json()["items"] if row["activity_type"] == "whatsapp")
    assert item["actor_name"] == "Beyza Karakuş"
    assert item["metadata"]["bitrix_history"]["chat_id"] == "11390"
    assert item["summary"] == "Merhaba"
