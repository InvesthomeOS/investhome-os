"""Live communication foundation: accounts, matching, dedupe, unmatched queue."""

import logging
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from investhome_api.models.crm_communication import CrmUserCommunicationAccount
from investhome_api.services.crypto_seal import CURRENT_PREFIX, seal_legacy_v1_for_tests, unseal_secret


def _create_contact(client: TestClient, **overrides) -> dict:
    payload = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": f"Live Contact {uuid4().hex[:6]}",
        "primary_email": f"live.{uuid4().hex[:8]}@example.com",
        **overrides,
    }
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["contact"]


def test_register_communication_account_without_credentials(client: TestClient) -> None:
    identity = f"desk.{uuid4().hex[:6]}@investhome.com.tr"
    response = client.post(
        "/crm/settings/communication-accounts",
        json={
            "channel_type": "email",
            "provider": "m365",
            "identity": identity,
            "account_label": "Sales mailbox",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["identity"] == identity.lower()
    assert body["status"] == "not_connected"
    assert body["has_credentials"] is False
    assert "encrypted_credentials" not in body
    assert "credentials" not in body

    listed = client.get("/crm/settings/communication-accounts")
    assert listed.status_code == 200
    assert any(item["identity"] == identity.lower() for item in listed.json()["items"])


def test_register_account_does_not_echo_secrets(client: TestClient, db, caplog) -> None:
    access = "super-secret-token"
    refresh = "also-secret"
    with caplog.at_level(logging.DEBUG):
        response = client.post(
            "/crm/settings/communication-accounts",
            json={
                "channel_type": "whatsapp",
                "provider": "whatsapp_business",
                "identity": "+905551112233",
                "credentials": {"access_token": access, "refresh_token": refresh},
            },
        )
    assert response.status_code == 201, response.text
    dumped = response.text.lower()
    assert access not in dumped
    assert refresh not in dumped
    assert "encrypted_credentials" not in dumped
    assert "v2:aesgcm:" not in dumped
    body = response.json()
    assert body["has_credentials"] is True

    listed = client.get("/crm/settings/communication-accounts")
    assert listed.status_code == 200
    listed_text = listed.text.lower()
    assert access not in listed_text
    assert refresh not in listed_text
    assert "encrypted_credentials" not in listed_text

    db.expire_all()
    row = db.get(CrmUserCommunicationAccount, UUID(body["id"]))
    assert row is not None
    assert row.encrypted_credentials is not None
    assert row.encrypted_credentials.startswith(CURRENT_PREFIX)
    assert access not in row.encrypted_credentials
    assert refresh not in row.encrypted_credentials
    opened = unseal_secret(row.encrypted_credentials)
    assert opened is not None
    assert opened["access_token"] == access
    assert opened["refresh_token"] == refresh

    logs = caplog.text
    assert access not in logs
    assert refresh not in logs


def test_list_accounts_rewrapped_legacy_hmac_xor_blob(client: TestClient, db) -> None:
    identity = f"legacy.{uuid4().hex[:6]}@investhome.com.tr"
    created = client.post(
        "/crm/settings/communication-accounts",
        json={
            "channel_type": "email",
            "provider": "m365",
            "identity": identity,
        },
    )
    assert created.status_code == 201, created.text
    account_id = UUID(created.json()["id"])
    secrets = {"access_token": "legacy-access", "refresh_token": "legacy-refresh"}
    db.expire_all()
    row = db.get(CrmUserCommunicationAccount, account_id)
    assert row is not None
    row.encrypted_credentials = seal_legacy_v1_for_tests(secrets)
    db.commit()

    listed = client.get("/crm/settings/communication-accounts")
    assert listed.status_code == 200
    assert "legacy-access" not in listed.text
    assert "legacy-refresh" not in listed.text
    item = next(entry for entry in listed.json()["items"] if entry["id"] == str(account_id))
    assert item["has_credentials"] is True

    db.expire_all()
    row = db.get(CrmUserCommunicationAccount, account_id)
    assert row is not None
    assert row.encrypted_credentials is not None
    assert row.encrypted_credentials.startswith(CURRENT_PREFIX)
    assert unseal_secret(row.encrypted_credentials) == secrets


def test_ingest_email_matches_single_contact(client: TestClient) -> None:
    contact = _create_contact(client)
    email = contact["primary_email"]
    payload = {
        "channel": "email",
        "direction": "incoming",
        "source": "live_email",
        "subject": "Tapu süreci",
        "body_html": "<p>Merhaba</p><p>İmza</p>",
        "body_text": "Merhaba İmza",
        "sender": email,
        "recipients": ["desk@investhome.com.tr"],
        "external_provider_id": f"msg-{uuid4().hex}",
        "conversation_id": f"thread-{uuid4().hex[:8]}",
    }
    response = client.post("/crm/live-communications/ingest", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] is True
    assert body["duplicate"] is False
    assert body["match_status"] == "matched"
    assert body["contact_id"] == contact["id"]
    assert body["activity_id"] is not None

    timeline = client.get(f"/crm/contacts/{contact['id']}/timeline")
    assert timeline.status_code == 200
    titles = [item["title"] for item in timeline.json()["items"]]
    assert any("Tapu süreci" in title for title in titles)


def test_ingest_duplicate_external_id_is_idempotent(client: TestClient) -> None:
    contact = _create_contact(client)
    external_id = f"msg-{uuid4().hex}"
    payload = {
        "channel": "email",
        "direction": "incoming",
        "sender": contact["primary_email"],
        "subject": "Same message",
        "body_text": "Hello",
        "external_provider_id": external_id,
    }
    first = client.post("/crm/live-communications/ingest", json=payload)
    second = client.post("/crm/live-communications/ingest", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["duplicate"] is True
    assert first.json()["created"] is True


def test_unmatched_email_goes_to_queue_and_can_be_attached(client: TestClient) -> None:
    contact = _create_contact(client)
    payload = {
        "channel": "email",
        "direction": "incoming",
        "sender": f"unknown.{uuid4().hex[:6]}@gmail.com",
        "subject": "Unknown sender",
        "body_text": "Who is this?",
        "external_provider_id": f"msg-{uuid4().hex}",
    }
    ingested = client.post("/crm/live-communications/ingest", json=payload)
    assert ingested.status_code == 200, ingested.text
    assert ingested.json()["match_status"] == "unmatched"
    assert ingested.json()["contact_id"] is None

    queue = client.get("/crm/live-communications/unmatched")
    assert queue.status_code == 200
    ids = [item["id"] for item in queue.json()["items"]]
    comm_id = ingested.json()["id"]
    assert comm_id in ids

    matched = client.post(
        f"/crm/live-communications/{comm_id}/match",
        json={"contact_id": contact["id"]},
    )
    assert matched.status_code == 200, matched.text
    assert matched.json()["match_status"] == "matched"
    assert matched.json()["activity_id"] is not None

    queue_after = client.get("/crm/live-communications/unmatched")
    assert comm_id not in [item["id"] for item in queue_after.json()["items"]]


def test_ambiguous_email_does_not_guess(client: TestClient) -> None:
    shared = f"shared.{uuid4().hex[:8]}@example.com"
    _create_contact(client, primary_email=shared, display_name="Person One")
    _create_contact(client, primary_email=shared, display_name="Person Two")
    response = client.post(
        "/crm/live-communications/ingest",
        json={
            "channel": "email",
            "direction": "incoming",
            "sender": shared,
            "subject": "Ambiguous",
            "body_text": "Which person?",
            "external_provider_id": f"msg-{uuid4().hex}",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["match_status"] == "ambiguous"
    assert response.json()["contact_id"] is None


def test_whatsapp_matches_normalized_phone(client: TestClient) -> None:
    contact = _create_contact(
        client,
        primary_email=f"wa.{uuid4().hex[:8]}@example.com",
        primary_phone="+90 555 111 22 33",
    )
    response = client.post(
        "/crm/live-communications/ingest",
        json={
            "channel": "whatsapp",
            "direction": "incoming",
            "sender": "05551112233",
            "body_text": "Merhaba, tapu için yazıyorum",
            "external_provider_id": f"wa-{uuid4().hex}",
            "conversation_id": "wa-chat-1",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["match_status"] == "matched"
    assert response.json()["contact_id"] == contact["id"]


def test_secondary_email_matches(client: TestClient) -> None:
    secondary = f"alt.{uuid4().hex[:8]}@example.com"
    contact = _create_contact(
        client,
        primary_email=f"pri.{uuid4().hex[:8]}@example.com",
        secondary_emails=[secondary],
    )
    response = client.post(
        "/crm/live-communications/ingest",
        json={
            "channel": "email",
            "direction": "incoming",
            "sender": secondary,
            "subject": "Secondary inbox",
            "body_text": "From secondary email",
            "external_provider_id": f"msg-{uuid4().hex}",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["match_status"] == "matched"
    assert response.json()["contact_id"] == contact["id"]


def test_unmatched_does_not_appear_on_person_timeline(client: TestClient) -> None:
    contact = _create_contact(client)
    subject = f"Orphan {uuid4().hex[:6]}"
    ingested = client.post(
        "/crm/live-communications/ingest",
        json={
            "channel": "email",
            "direction": "incoming",
            "sender": f"ghost.{uuid4().hex[:6]}@gmail.com",
            "subject": subject,
            "body_text": "Not this person",
            "external_provider_id": f"msg-{uuid4().hex}",
        },
    )
    assert ingested.status_code == 200
    assert ingested.json()["match_status"] == "unmatched"
    timeline = client.get(f"/crm/contacts/{contact['id']}/timeline")
    assert timeline.status_code == 200
    titles = [item["title"] for item in timeline.json()["items"]]
    assert all(subject not in title for title in titles)


def test_content_hash_dedupe_without_external_id(client: TestClient) -> None:
    contact = _create_contact(client)
    payload = {
        "channel": "email",
        "direction": "incoming",
        "sender": contact["primary_email"],
        "subject": "Retry without id",
        "body_text": "Same body twice",
        "occurred_at": "2026-09-22T09:00:00+00:00",
    }
    first = client.post("/crm/live-communications/ingest", json=payload)
    second = client.post("/crm/live-communications/ingest", json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["duplicate"] is True
