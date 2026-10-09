"""Facebook / Instagram comment inbound, parent context, and OS reply."""

from __future__ import annotations

from time import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import CrmCommunication, CrmCommunicationAuditLog
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.sales import SalesOpportunity
from investhome_api.services.crm import meta_comments, meta_webhook as meta
from investhome_api.services.crm.communication_feed import list_communication_feed
from investhome_api.services.crm.meta_comments import (
    FACEBOOK_ANON_COMMENTER_PREFIX,
    FACEBOOK_COMMENTER_KEY,
    PUBLIC_COMMENT_NOT_CONFIGURED,
    PUBLIC_COMMENT_SEND_FAILED,
    PUBLIC_DELETE_FAILED,
    PUBLIC_LIKE_UNSUPPORTED,
    PUBLIC_PRIVATE_REPLY_ALREADY_SENT,
    PUBLIC_PRIVATE_REPLY_UNAVAILABLE,
    comment_conversation_key,
    extract_facebook_comments,
)
from investhome_api.services.crm.meta_send import FACEBOOK_MESSAGES_URL, instagram_messages_url
from investhome_api.services.crm.meta_webhook import FACEBOOK_PSID_KEY, INSTAGRAM_IGSID_KEY

from test_meta_send import IG_TOKEN, PAGE_TOKEN, SEND_PATH, _DummyResponse, _enable_instagram_send
from test_meta_webhook import (
    APP_SECRET,
    IG_ACCOUNT_ID,
    IG_APP_SECRET,
    IG_WEBHOOK_ACCOUNT_ID,
    PAGE_ID,
    VERIFY_TOKEN,
    _ig_payload,
    _payload,
    _post,
)

GRAPH_VERSION = "v21.0"


@pytest.fixture(autouse=True)
def _meta_comment_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("META_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("META_INSTAGRAM_APP_SECRET", IG_APP_SECRET)
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY_TOKEN)
    monkeypatch.setenv("META_PAGE_ID", PAGE_ID)
    monkeypatch.setenv("META_INSTAGRAM_ACCOUNT_ID", IG_ACCOUNT_ID)
    monkeypatch.setenv("META_INSTAGRAM_WEBHOOK_ACCOUNT_ID", IG_WEBHOOK_ACCOUNT_ID)
    monkeypatch.setattr(meta_comments, "_graph_get", lambda *args, **kwargs: None)
    get_settings.cache_clear()
    meta.reset_meta_idempotency_for_tests()
    yield
    meta.reset_meta_idempotency_for_tests()
    get_settings.cache_clear()


def _fb_comment_payload(
    *,
    comment_id: str,
    sender: str = "1029384756199999",
    text: str = "Fiyat nedir?",
    post_id: str = f"{PAGE_ID}_888111",
    name: str = "Ali Yorum",
    is_published: bool | None = True,
    ad_id: str | None = None,
    ad_title: str | None = None,
    permalink: str | None = "https://www.facebook.com/posts/888111",
    verb: str = "add",
    include_from: bool = True,
    entry_id: str = PAGE_ID,
    photo_id: str | None = None,
    video_id: str | None = None,
    omit_post_id: bool = False,
    omit_verb: bool = False,
) -> dict:
    stamped = int(time())
    post = {"id": post_id, "permalink_url": permalink, "is_published": is_published}
    value = {
        "item": "comment",
        "comment_id": comment_id,
        "created_time": stamped,
        "message": text,
    }
    if not omit_verb:
        value["verb"] = verb
    if include_from:
        value["from"] = {"id": sender, "name": name}
    if omit_post_id:
        if photo_id:
            value["photo_id"] = photo_id
            value["parent_id"] = photo_id
        elif video_id:
            value["video_id"] = video_id
            value["parent_id"] = video_id
        else:
            value["parent_id"] = post_id
    else:
        value["post_id"] = post_id
        value["parent_id"] = post_id
        value["post"] = post
        if photo_id:
            value["photo_id"] = photo_id
        if video_id:
            value["video_id"] = video_id
    if ad_id:
        value["ad_id"] = ad_id
        post["ad_id"] = ad_id
    if ad_title:
        value["ad_title"] = ad_title
        post["ad_title"] = ad_title
    if is_published is False:
        post["promotion_status"] = "active"
    return {"object": "page", "entry": [{"id": entry_id, "time": stamped, "changes": [{"field": "feed", "value": value}]}]}


def _ig_comment_payload(
    *,
    comment_id: str,
    sender: str = "17841400001234567",
    text: str = "Harika reel",
    media_id: str = "17999900001111",
    username: str = "yorumcu",
    media_product_type: str = "FEED",
    original_media_id: str | None = None,
    ad_id: str | None = None,
) -> dict:
    media = {"id": media_id, "media_product_type": media_product_type}
    if original_media_id:
        media["original_media_id"] = original_media_id
    if ad_id:
        media["ad_id"] = ad_id
    stamped = int(time())
    return {
        "object": "instagram",
        "entry": [
            {
                "id": IG_WEBHOOK_ACCOUNT_ID,
                "time": stamped,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": comment_id,
                            "text": text,
                            "timestamp": stamped,
                            "from": {"id": sender, "username": username},
                            "media": media,
                        },
                    }
                ],
            }
        ],
    }


def _comment_row(db: Session, comment_id: str) -> CrmCommunication:
    row = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.external_provider_id == comment_id,
            CrmCommunication.archived_at.is_(None),
        )
    )
    assert row is not None
    return row


def test_facebook_post_comment_inbound(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_cmt_{uuid4().hex[:8]}"
    response, _ = _post(client, _fb_comment_payload(comment_id=comment_id))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = _comment_row(db, comment_id)
    assert row.channel == "facebook"
    assert row.direction == "inbound"
    assert (row.metadata_json or {}).get("kind") == "comment"
    assert row.conversation_key == comment_conversation_key(comment_id)
    context = (row.metadata_json or {}).get("comment_context") or {}
    assert context["platform"] == "facebook"
    assert context["parent_id"] == f"{PAGE_ID}_888111"
    assert context["permalink"]
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    feed = list_communication_feed(db, channel="facebook_comment", page=1, page_size=25)
    assert any(item.preview == "Fiyat nedir?" and item.kind == "comment" for item in feed.items)
    dm_feed = list_communication_feed(db, channel="facebook_dm", page=1, page_size=25)
    assert not any(item.preview == "Fiyat nedir?" for item in dm_feed.items)


def test_facebook_comment_without_from_is_ingested(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_anon_{uuid4().hex[:8]}"
    response, _ = _post(client, _fb_comment_payload(comment_id=comment_id, include_from=False))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = _comment_row(db, comment_id)
    assert row.channel == "facebook"
    assert (row.metadata_json or {}).get("kind") == "comment"
    assert (row.metadata_json or {}).get(FACEBOOK_COMMENTER_KEY) == f"{FACEBOOK_ANON_COMMENTER_PREFIX}{comment_id}"
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    feed = list_communication_feed(db, channel="facebook_comment", page=1, page_size=25)
    assert any(item.preview == "Fiyat nedir?" and item.kind == "comment" for item in feed.items)


def test_facebook_comment_verb_edit_is_ingested(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_edit_{uuid4().hex[:8]}"
    response, _ = _post(client, _fb_comment_payload(comment_id=comment_id, verb="edit", text="Duzenlendi"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = _comment_row(db, comment_id)
    assert row.body_text == "Duzenlendi"
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_facebook_photo_comment_without_post_id_is_ingested(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_photo_{uuid4().hex[:8]}"
    photo_id = f"{PAGE_ID}_pic_77"
    response, _ = _post(
        client,
        _fb_comment_payload(comment_id=comment_id, omit_post_id=True, photo_id=photo_id, text="Foto yorum"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = _comment_row(db, comment_id)
    context = (row.metadata_json or {}).get("comment_context") or {}
    assert context["parent_id"] == photo_id
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_facebook_comment_page_mismatch_is_skipped(client: TestClient, db: Session, caplog: pytest.LogCaptureFixture) -> None:
    comment_id = f"{PAGE_ID}_mismatch_{uuid4().hex[:8]}"
    caplog.set_level("INFO", logger="investhome.meta.comments")
    with caplog.at_level("INFO", logger="investhome.meta.comments"):
        response, _ = _post(
            client,
            _fb_comment_payload(comment_id=comment_id, entry_id="999000111222"),
        )
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == comment_id)) is None
    assert "reason=page_mismatch" in caplog.text
    assert "entry_page_id=999000111222" in caplog.text
    assert f"configured_page_id={PAGE_ID}" in caplog.text
    assert "Fiyat nedir?" not in caplog.text


def test_facebook_page_own_comment_is_skipped(client: TestClient, db: Session, caplog: pytest.LogCaptureFixture) -> None:
    comment_id = f"{PAGE_ID}_own_{uuid4().hex[:8]}"
    caplog.set_level("INFO", logger="investhome.meta.comments")
    with caplog.at_level("INFO", logger="investhome.meta.comments"):
        response, _ = _post(client, _fb_comment_payload(comment_id=comment_id, sender=PAGE_ID))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert "reason=page_own_comment" in caplog.text
    assert db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == comment_id)) is None


def test_facebook_comment_delete_verb_is_skipped(client: TestClient, db: Session, caplog: pytest.LogCaptureFixture) -> None:
    comment_id = f"{PAGE_ID}_delverb_{uuid4().hex[:8]}"
    caplog.set_level("INFO", logger="investhome.meta.comments")
    with caplog.at_level("INFO", logger="investhome.meta.comments"):
        response, _ = _post(client, _fb_comment_payload(comment_id=comment_id, verb="delete"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 0
    assert "reason=unsupported_verb" in caplog.text
    assert "verb=delete" in caplog.text


def test_extract_facebook_comments_real_feed_shapes() -> None:
    comment_id = f"{PAGE_ID}_shape_{uuid4().hex[:8]}"
    missing_from = _fb_comment_payload(comment_id=comment_id, include_from=False, omit_verb=True)
    parsed = extract_facebook_comments(missing_from, page_id=PAGE_ID)
    assert len(parsed) == 1
    assert parsed[0].commenter_id == f"{FACEBOOK_ANON_COMMENTER_PREFIX}{comment_id}"
    assert parsed[0].parent_id == f"{PAGE_ID}_888111"

    photo_id = f"{PAGE_ID}_vid_1"
    video = _fb_comment_payload(
        comment_id=f"{comment_id}_v",
        omit_post_id=True,
        video_id=photo_id,
        verb="edited",
    )
    parsed_video = extract_facebook_comments(video, page_id=PAGE_ID)
    assert len(parsed_video) == 1
    assert parsed_video[0].parent_id == photo_id


def test_facebook_ad_comment_inbound_uses_webhook_context(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_ad_{uuid4().hex[:8]}"
    post_id = f"{PAGE_ID}_dark_99"
    response, _ = _post(
        client,
        _fb_comment_payload(
            comment_id=comment_id,
            post_id=post_id,
            text="Reklam yorumu",
            is_published=False,
            ad_id="120111222333",
            ad_title="Uniloft Kampanya",
            permalink=None,
        ),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = _comment_row(db, comment_id)
    context = (row.metadata_json or {}).get("comment_context") or {}
    assert context["parent_id"] == post_id
    assert context["ad_id"] == "120111222333"
    assert context["ad_name"] == "Uniloft Kampanya"
    assert context.get("is_published") is False
    assert context.get("media_type") == "ad"
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_instagram_comment_inbound(client: TestClient, db: Session) -> None:
    comment_id = f"igcmt_{uuid4().hex[:10]}"
    response, _ = _post(client, _ig_comment_payload(comment_id=comment_id, media_product_type="REELS"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = _comment_row(db, comment_id)
    assert row.channel == "instagram"
    assert (row.metadata_json or {}).get("kind") == "comment"
    context = (row.metadata_json or {}).get("comment_context") or {}
    assert context["platform"] == "instagram"
    assert context["parent_id"] == "17999900001111"
    assert context["media_type"] == "reels"
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    feed = list_communication_feed(db, channel="instagram_comment", page=1, page_size=25)
    assert any(item.kind == "comment" and item.preview == "Harika reel" for item in feed.items)


def test_instagram_ad_comment_keeps_original_media_id(client: TestClient, db: Session) -> None:
    comment_id = f"igad_{uuid4().hex[:10]}"
    response, _ = _post(
        client,
        _ig_comment_payload(
            comment_id=comment_id,
            media_product_type="AD",
            original_media_id="17880001111",
            ad_id="120999888777",
            text="Reklam IG",
        ),
    )
    assert response.status_code == 200
    db.expire_all()
    context = (_comment_row(db, comment_id).metadata_json or {}).get("comment_context") or {}
    assert context["original_media_id"] == "17880001111"
    assert context["ad_id"] == "120999888777"
    assert context["media_type"] == "ad"


def test_duplicate_comment_webhook_does_not_duplicate(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_dup_{uuid4().hex[:8]}"
    payload = _fb_comment_payload(comment_id=comment_id, text="Tekrar")
    first, _ = _post(client, payload)
    second, _ = _post(client, payload)
    assert first.json()["ingested"] == 1
    assert second.json()["ingested"] == 0
    assert second.json()["duplicate"] is True
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication).where(
        CrmCommunication.external_provider_id == comment_id
    )) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_parent_post_context_mapping(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        assert token == PAGE_TOKEN
        if "888111" in url:
            return {
                "id": f"{PAGE_ID}_888111",
                "message": "Uniloft daireleri",
                "permalink_url": "https://www.facebook.com/posts/mapped",
                "created_time": "2026-04-01T12:00:00+0000",
                "full_picture": "https://scontent.xx.fbcdn.net/preview.jpg",
                "status_type": "added_photos",
                "is_published": True,
                "from": {"name": "Investhome", "id": PAGE_ID},
            }
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    comment_id = f"{PAGE_ID}_ctx_{uuid4().hex[:8]}"
    response, _ = _post(client, _fb_comment_payload(comment_id=comment_id))
    assert response.status_code == 200
    db.expire_all()
    context = (_comment_row(db, comment_id).metadata_json or {}).get("comment_context") or {}
    assert context["caption"] == "Uniloft daireleri"
    assert context["permalink"] == "https://www.facebook.com/posts/mapped"
    assert context["preview_url"] == "https://scontent.xx.fbcdn.net/preview.jpg"
    assert context["account_name"] == "Investhome"
    assert context["published_time"]
    feed = list_communication_feed(db, channel="facebook_comment", page=1, page_size=25)
    item = next(row for row in feed.items if row.preview == "Fiyat nedir?")
    assert item.comment_context["caption"] == "Uniloft daireleri"


def test_existing_contact_matching_does_not_create_lead(client: TestClient, db: Session) -> None:
    sender = "1029384756105555"
    message_id = f"mid.{uuid4().hex}"
    dm, _ = _post(client, _payload(message_id=message_id, sender=sender, text="Merhaba DM"))
    assert dm.json()["ingested"] == 1
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    comment_id = f"{PAGE_ID}_match_{uuid4().hex[:8]}"
    comment, _ = _post(client, _fb_comment_payload(comment_id=comment_id, sender=sender, text="Ayni kisi"))
    assert comment.json()["ingested"] == 1
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    meta_json = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
    assert meta_json.get(FACEBOOK_PSID_KEY) == sender
    assert meta_json.get(FACEBOOK_COMMENTER_KEY) == sender
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0


def test_unknown_commenter_does_not_auto_create_lead(client: TestClient, db: Session) -> None:
    comment_id = f"{PAGE_ID}_new_{uuid4().hex[:8]}"
    response, _ = _post(client, _fb_comment_payload(comment_id=comment_id, sender="1029380000000001", text="Yeni kisi"))
    assert response.json()["ingested"] == 1
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    meta_json = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
    assert meta_json.get(FACEBOOK_COMMENTER_KEY) == "1029380000000001"
    assert meta_json.get(FACEBOOK_PSID_KEY) != "1029380000000001"


def test_facebook_comment_reply_success_failure_auth(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"{PAGE_ID}_reply_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_id, sender="1029384756106666", text="Soru"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()
    calls: list[dict] = []

    def _ok(url: str, payload: dict, token: str):
        calls.append({"url": url, "payload": payload, "token": token})
        assert token == PAGE_TOKEN
        assert url == f"https://graph.facebook.com/{GRAPH_VERSION}/{comment_id}/comments"
        assert payload == {"message": "Cevap FB yorum"}
        assert "graph.instagram.com" not in url
        return _DummyResponse(200, {"id": "reply.fb.1"})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _ok)
    first = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Cevap FB yorum",
            "kind": "comment",
        },
    )
    second = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Cevap FB yorum",
            "kind": "comment",
        },
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["provider_message_id"] == "reply.fb.1"
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert PAGE_TOKEN not in first.text
    db.expire_all()
    outgoing = list(
        db.scalars(
            select(CrmCommunication).where(
                CrmCommunication.channel == "facebook",
                CrmCommunication.direction == "outbound",
            )
        ).all()
    )
    assert len(outgoing) == 1
    assert outgoing[0].external_provider_id == "reply.fb.1"
    assert (outgoing[0].metadata_json or {}).get("kind") == "comment"
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0

    def _fail(url: str, payload: dict, token: str):
        return _DummyResponse(400, {"error": {"message": "fail"}})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _fail)
    failed = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Olmasin",
            "kind": "comment",
        },
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == PUBLIC_COMMENT_SEND_FAILED

    monkeypatch.delenv("META_PAGE_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    missing = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Token yok",
            "kind": "comment",
        },
    )
    assert missing.status_code == 503
    assert missing.json()["detail"] == PUBLIC_COMMENT_NOT_CONFIGURED


def test_instagram_comment_reply_success_failure_auth(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igreply_{uuid4().hex[:10]}"
    sender = "17841400003333333"
    _post(client, _ig_comment_payload(comment_id=comment_id, sender=sender, text="IG soru"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    _enable_instagram_send(monkeypatch)

    def _ok(url: str, payload: dict, token: str):
        assert token == IG_TOKEN
        assert token != PAGE_TOKEN
        assert url == f"https://graph.instagram.com/{GRAPH_VERSION}/{comment_id}/replies"
        assert payload == {"message": "Cevap IG yorum"}
        return _DummyResponse(200, {"id": "reply.ig.1"})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _ok)
    ok = client.post(
        SEND_PATH,
        json={
            "channel": "instagram",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Cevap IG yorum",
            "kind": "comment",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["provider_message_id"] == "reply.ig.1"
    assert IG_TOKEN not in ok.text
    db.expire_all()
    outgoing = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.channel == "instagram",
            CrmCommunication.direction == "outbound",
        )
    )
    assert outgoing is not None
    assert (outgoing.metadata_json or {}).get("kind") == "comment"
    assert (outgoing.metadata_json or {}).get("in_reply_to") == comment_id
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0

    def _fail(url: str, payload: dict, token: str):
        return _DummyResponse(500, {"error": {"message": "down"}})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _fail)
    failed = client.post(
        SEND_PATH,
        json={
            "channel": "instagram",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Hata IG yorum",
            "kind": "comment",
        },
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == PUBLIC_COMMENT_SEND_FAILED

    monkeypatch.delenv("META_INSTAGRAM_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    missing = client.post(
        SEND_PATH,
        json={
            "channel": "instagram",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "IG token yok",
            "kind": "comment",
        },
    )
    assert missing.status_code == 503
    assert missing.json()["detail"] == PUBLIC_COMMENT_NOT_CONFIGURED


def test_comment_reply_requires_auth(auth_client: TestClient) -> None:
    response = auth_client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(uuid4()),
            "conversation_key": comment_conversation_key("x"),
            "text": "Nope",
            "kind": "comment",
        },
    )
    assert response.status_code == 401
    assert PAGE_TOKEN not in response.text


def test_facebook_dm_regression_still_creates_lead(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id=message_id, sender="1029384756107777", text="DM kalir"))
    assert response.status_code == 200
    assert response.json()["ingested"] == 1
    db.expire_all()
    row = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == message_id))
    assert row is not None
    assert (row.metadata_json or {}).get("kind") != "comment"
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(SalesOpportunity)) or 0) == 0
    feed = list_communication_feed(db, channel="facebook_dm", page=1, page_size=25)
    assert any(item.preview == "DM kalir" and item.kind == "dm" for item in feed.items)


def test_instagram_dm_regression_still_creates_lead(client: TestClient, db: Session) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, sender="17841400004444444", text="IG DM kalir"))
    assert response.json()["ingested"] == 1
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    row = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == message_id))
    assert row is not None
    assert row.channel == "instagram"
    assert (row.metadata_json or {}).get("kind") != "comment"
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    assert (contact.metadata_json or {}).get(INSTAGRAM_IGSID_KEY) == "17841400004444444"


def test_instagram_incomplete_comments_payload_is_not_ingested(client: TestClient, db: Session) -> None:
    payload = {
        "object": "instagram",
        "entry": [{"id": IG_WEBHOOK_ACCOUNT_ID, "changes": [{"field": "comments", "value": {"text": "yorum"}}]}],
    }
    response, _ = _post(client, payload)
    assert response.status_code == 200
    assert response.json()["ingested"] == 0
    assert int(db.scalar(select(func.count()).select_from(CrmCommunication)) or 0) == 0
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def _conversation(client: TestClient, *, comment_id: str, channel: str, contact_id: str):
    return client.get(
        "/crm/live-communications/conversation",
        params={
            "chat_id": comment_conversation_key(comment_id),
            "channel": channel,
            "contact_id": contact_id,
        },
    )


def test_instagram_comment_parent_context_fetched_on_detail(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igctx_{uuid4().hex[:10]}"
    sender = "17841400001234567"
    _post(client, _ig_comment_payload(comment_id=comment_id, sender=sender, username="c_hasan_acar"))
    db.expire_all()
    row = _comment_row(db, comment_id)
    assert not ((row.metadata_json or {}).get("comment_context") or {}).get("preview_url")
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        assert token == IG_TOKEN
        if comment_id in url:
            return {
                "id": comment_id,
                "username": "c_hasan_acar",
                "from": {"id": sender, "username": "c_hasan_acar"},
                "media": {
                    "id": "17999900001111",
                    "caption": "Uniloft reel",
                    "media_type": "VIDEO",
                    "thumbnail_url": "https://scontent.cdninstagram.com/thumb.jpg",
                    "permalink": "https://www.instagram.com/reel/abc/",
                    "timestamp": "2026-04-01T12:00:00+0000",
                    "username": "investhome",
                },
            }
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    listed = _conversation(client, comment_id=comment_id, channel="instagram", contact_id=str(contact.id))
    assert listed.status_code == 200, listed.text
    body = listed.json()
    context = body["comment_context"]
    assert context["preview_url"] == "https://scontent.cdninstagram.com/thumb.jpg"
    assert context["caption"] == "Uniloft reel"
    assert context["permalink"] == "https://www.instagram.com/reel/abc/"
    assert body["comment_capabilities"]["reply_prefix"] == "@c_hasan_acar "
    assert body["comment_capabilities"]["can_like"] is False
    assert body["comment_capabilities"]["can_delete"] is True
    assert body["comment_capabilities"]["can_private_reply"] is True
    assert any((message.get("summary") or "") == "Harika reel" for message in body["messages"])
    db.expire_all()
    stored = (_comment_row(db, comment_id).metadata_json or {}).get("comment_context") or {}
    assert stored["preview_url"] == context["preview_url"]
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_facebook_comment_parent_context_fetched_on_detail(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"{PAGE_ID}_fbctx_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_id, permalink=None))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        if comment_id in url:
            return {"id": comment_id, "can_reply_privately": True, "user_likes": False, "from": {"name": "Ali Yorum"}}
        if "888111" in url:
            return {
                "id": f"{PAGE_ID}_888111",
                "message": "Uniloft daireleri",
                "permalink_url": "https://www.facebook.com/posts/mapped",
                "full_picture": "https://scontent.xx.fbcdn.net/preview.jpg",
                "created_time": "2026-04-01T12:00:00+0000",
                "from": {"name": "Investhome"},
            }
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    listed = _conversation(client, comment_id=comment_id, channel="facebook", contact_id=str(contact.id))
    assert listed.status_code == 200, listed.text
    context = listed.json()["comment_context"]
    caps = listed.json()["comment_capabilities"]
    assert context["preview_url"].endswith("preview.jpg")
    assert context["caption"] == "Uniloft daireleri"
    assert caps["can_like"] is True
    assert caps["can_delete"] is True
    assert caps["can_private_reply"] is True
    assert caps["reply_prefix"] is None
    assert any((message.get("summary") or "") == "Fiyat nedir?" for message in listed.json()["messages"])


def test_missing_context_fetch_fallback_is_visible(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igmiss_{uuid4().hex[:10]}"
    _post(client, _ig_comment_payload(comment_id=comment_id, text="Bos onizleme"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    get_settings.cache_clear()
    monkeypatch.setattr(meta_comments, "_graph_get", lambda *args, **kwargs: None)
    listed = _conversation(client, comment_id=comment_id, channel="instagram", contact_id=str(contact.id))
    assert listed.status_code == 200
    body = listed.json()
    caps = body["comment_capabilities"]
    assert caps["context_status"] == "unavailable"
    assert caps["context_error"]
    context = body["comment_context"]
    assert context["parent_id"] == "17999900001111"
    assert not context.get("preview_url")
    assert not context.get("caption")
    assert any((message.get("summary") or "") == "Bos onizleme" for message in body["messages"])


def test_instagram_private_reply_from_comment(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    comment_id = f"igpriv_{uuid4().hex[:10]}"
    sender = "17841400003330001"
    _post(client, _ig_comment_payload(comment_id=comment_id, sender=sender, username="c_hasan_acar"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    _enable_instagram_send(monkeypatch)
    calls: list[dict] = []

    def _ok(url: str, payload: dict, token: str):
        calls.append({"url": url, "payload": payload, "token": token})
        assert token == IG_TOKEN
        assert url == instagram_messages_url(IG_ACCOUNT_ID)
        assert payload["recipient"] == {"comment_id": comment_id}
        assert "id" not in payload["recipient"]
        return _DummyResponse(200, {"message_id": "mid.priv.ig.1", "recipient_id": sender})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _ok)
    first = client.post(
        SEND_PATH,
        json={
            "channel": "instagram",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Ozel IG",
            "kind": "private_reply",
        },
    )
    second = client.post(
        SEND_PATH,
        json={
            "channel": "instagram",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Ozel IG 2",
            "kind": "private_reply",
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["provider_message_id"] == "mid.priv.ig.1"
    assert second.status_code == 409
    assert second.json()["detail"] == PUBLIC_PRIVATE_REPLY_ALREADY_SENT
    assert len(calls) == 1
    db.expire_all()
    outgoing = db.scalar(
        select(CrmCommunication).where(
            CrmCommunication.channel == "instagram",
            CrmCommunication.direction == "outbound",
        )
    )
    assert outgoing is not None
    assert (outgoing.metadata_json or {}).get("kind") == "dm"
    assert (outgoing.metadata_json or {}).get("private_reply") is True
    assert outgoing.conversation_key == sender
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_facebook_private_reply_requires_capability(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"{PAGE_ID}_nopriv_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_id))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()
    called = {"n": 0}

    def _fake_post(url: str, payload: dict, token: str):
        called["n"] += 1
        return _DummyResponse(200, {"message_id": "should-not"})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _fake_post)
    denied = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Ozel FB",
            "kind": "private_reply",
        },
    )
    assert denied.status_code == 400
    assert denied.json()["detail"] == PUBLIC_PRIVATE_REPLY_UNAVAILABLE
    assert called["n"] == 0


def test_facebook_private_reply_when_permitted(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"{PAGE_ID}_priv_{uuid4().hex[:8]}"
    sender = "1029384756108888"
    _post(client, _fb_comment_payload(comment_id=comment_id, sender=sender))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        if comment_id in url:
            return {"id": comment_id, "can_reply_privately": True, "user_likes": False}
        return None

    def _ok(url: str, payload: dict, token: str):
        assert url == FACEBOOK_MESSAGES_URL
        assert payload["recipient"] == {"comment_id": comment_id}
        return _DummyResponse(200, {"message_id": "mid.priv.fb.1", "recipient_id": sender})

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    monkeypatch.setattr(meta_comments, "_post_graph_messages", _ok)
    ok = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Ozel FB",
            "kind": "private_reply",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["provider_message_id"] == "mid.priv.fb.1"
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0


def test_facebook_private_reply_graph_error_is_not_fake_success(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"{PAGE_ID}_privfail_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_id, sender="1029384756107771"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        if comment_id in url:
            return {"id": comment_id, "can_reply_privately": True, "user_likes": False}
        return None

    def _fail(url: str, payload: dict, token: str):
        return _DummyResponse(400, {"error": {"message": "window closed"}})

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    monkeypatch.setattr(meta_comments, "_post_graph_messages", _fail)
    failed = client.post(
        SEND_PATH,
        json={
            "channel": "facebook",
            "contact_id": str(contact.id),
            "conversation_key": comment_conversation_key(comment_id),
            "text": "Olmasin",
            "kind": "private_reply",
        },
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == meta_comments.PUBLIC_PRIVATE_REPLY_FAILED
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0
    outbound = list(
        db.scalars(
            select(CrmCommunication).where(
                CrmCommunication.channel == "facebook",
                CrmCommunication.direction == "outbound",
            )
        ).all()
    )
    assert outbound == []


def test_instagram_comment_matches_existing_dm_contact(client: TestClient, db: Session) -> None:
    sender = "17841400005555555"
    dm, _ = _post(client, _ig_payload(message_id=f"mid.{uuid4().hex}", sender=sender, text="Once DM"))
    assert dm.json()["ingested"] == 1
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    comment, _ = _post(
        client, _ig_comment_payload(comment_id=f"igmatch_{uuid4().hex[:10]}", sender=sender, username="c_hasan_acar")
    )
    assert comment.json()["ingested"] == 1
    db.expire_all()
    assert int(db.scalar(select(func.count()).select_from(CrmContact)) or 0) == 1
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 1
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    assert (contact.metadata_json or {}).get(INSTAGRAM_IGSID_KEY) == sender


def test_comment_like_capability_by_platform(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    ig_comment = f"iglike_{uuid4().hex[:10]}"
    fb_comment = f"{PAGE_ID}_like_{uuid4().hex[:8]}"
    _post(client, _ig_comment_payload(comment_id=ig_comment))
    _post(client, _fb_comment_payload(comment_id=fb_comment, sender="1029384756109999"))
    db.expire_all()
    ig_denied = client.post(
        "/crm/live-communications/comment-action",
        json={"channel": "instagram", "conversation_key": comment_conversation_key(ig_comment), "action": "like"},
    )
    assert ig_denied.status_code == 400
    assert ig_denied.json()["detail"] == PUBLIC_LIKE_UNSUPPORTED
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()

    def _ok(url: str, payload: dict, token: str):
        assert url.endswith(f"/{fb_comment}/likes")
        assert token == PAGE_TOKEN
        return _DummyResponse(200, {"success": True})

    monkeypatch.setattr(meta_comments, "_post_graph_messages", _ok)
    liked = client.post(
        "/crm/live-communications/comment-action",
        json={"channel": "facebook", "conversation_key": comment_conversation_key(fb_comment), "action": "like"},
    )
    assert liked.status_code == 200, liked.text
    assert liked.json()["liked"] is True
    assert liked.json()["can_like"] is True
    db.expire_all()
    seed = _comment_row(db, fb_comment)
    assert (seed.metadata_json or {}).get("user_likes") is True


ACTION_PATH = "/crm/live-communications/comment-action"


def test_instagram_image_parent_preview_uses_media_url(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igimg_{uuid4().hex[:10]}"
    media_id = "18011100002222"
    _post(client, _ig_comment_payload(comment_id=comment_id, media_id=media_id, media_product_type="FEED"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        assert token == IG_TOKEN
        if comment_id in url:
            return {
                "id": comment_id,
                "media": {
                    "id": media_id,
                    "caption": "Uniloft daire",
                    "media_type": "IMAGE",
                    "permalink": "https://www.instagram.com/p/abc/",
                    "timestamp": "2026-04-01T12:00:00+0000",
                },
            }
        if media_id in url and "/children" not in url:
            return {
                "id": media_id,
                "caption": "Uniloft daire",
                "media_type": "IMAGE",
                "media_url": "https://scontent.cdninstagram.com/image.jpg",
                "permalink": "https://www.instagram.com/p/abc/",
                "timestamp": "2026-04-01T12:00:00+0000",
                "username": "investhome",
            }
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    listed = _conversation(client, comment_id=comment_id, channel="instagram", contact_id=str(contact.id))
    assert listed.status_code == 200, listed.text
    context = listed.json()["comment_context"]
    assert context["media_type"] == "IMAGE"
    assert context["preview_url"] == "https://scontent.cdninstagram.com/image.jpg"
    assert context["caption"] == "Uniloft daire"


def test_instagram_video_parent_preview_prefers_thumbnail(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igvid_{uuid4().hex[:10]}"
    media_id = "18022200003333"
    _post(client, _ig_comment_payload(comment_id=comment_id, media_id=media_id, media_product_type="REELS"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        if comment_id in url:
            return {
                "id": comment_id,
                "media": {"id": media_id, "caption": "Reel caption", "media_type": "VIDEO"},
            }
        if media_id in url and "/children" not in url:
            return {
                "id": media_id,
                "caption": "Reel caption",
                "media_type": "VIDEO",
                "media_url": "https://scontent.cdninstagram.com/video.mp4",
                "thumbnail_url": "https://scontent.cdninstagram.com/reel-thumb.jpg",
                "permalink": "https://www.instagram.com/reel/xyz/",
            }
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    listed = _conversation(client, comment_id=comment_id, channel="instagram", contact_id=str(contact.id))
    context = listed.json()["comment_context"]
    assert context["preview_url"] == "https://scontent.cdninstagram.com/reel-thumb.jpg"
    assert context["caption"] == "Reel caption"


def test_instagram_carousel_parent_preview_uses_first_child(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igcar_{uuid4().hex[:10]}"
    media_id = "18033300004444"
    child_id = "18033300005555"
    _post(client, _ig_comment_payload(comment_id=comment_id, media_id=media_id))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        if comment_id in url:
            return {
                "id": comment_id,
                "media": {"id": media_id, "caption": "Carousel caption", "media_type": "CAROUSEL_ALBUM"},
            }
        if url.endswith(f"/{media_id}/children") or f"/{media_id}/children?" in url:
            return {
                "data": [
                    {
                        "id": child_id,
                        "media_type": "IMAGE",
                        "media_url": "https://scontent.cdninstagram.com/cover.jpg",
                    }
                ]
            }
        if media_id in url:
            return {"id": media_id, "caption": "Carousel caption", "media_type": "CAROUSEL_ALBUM"}
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    listed = _conversation(client, comment_id=comment_id, channel="instagram", contact_id=str(contact.id))
    context = listed.json()["comment_context"]
    assert context["preview_url"] == "https://scontent.cdninstagram.com/cover.jpg"
    assert context["caption"] == "Carousel caption"


def test_instagram_missing_preview_url_keeps_explicit_fallback(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"ignoprev_{uuid4().hex[:10]}"
    media_id = "18044400006666"
    _post(client, _ig_comment_payload(comment_id=comment_id, media_id=media_id, text="Caption var"))
    db.expire_all()
    contact = db.scalar(select(CrmContact))
    assert contact is not None
    monkeypatch.setenv("META_INSTAGRAM_ACCESS_TOKEN", IG_TOKEN)
    get_settings.cache_clear()

    def _fake_get(url: str, *, token: str, fields: str):
        if comment_id in url or media_id in url:
            return {
                "id": media_id if media_id in url else comment_id,
                "caption": "Caption var",
                "media_type": "IMAGE",
                "permalink": "https://www.instagram.com/p/noimg/",
                "media": {"id": media_id, "caption": "Caption var", "media_type": "IMAGE"},
            }
        return None

    monkeypatch.setattr(meta_comments, "_graph_get", _fake_get)
    listed = _conversation(client, comment_id=comment_id, channel="instagram", contact_id=str(contact.id))
    context = listed.json()["comment_context"]
    assert context["caption"] == "Caption var"
    assert not context.get("preview_url")


def test_facebook_comment_delete_success_failure(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"{PAGE_ID}_del_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_id, text="Silinecek FB"))
    db.expire_all()
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", PAGE_TOKEN)
    get_settings.cache_clear()
    calls: list[str] = []

    def _ok(url: str, *, token: str):
        calls.append(url)
        assert token == PAGE_TOKEN
        assert url == f"https://graph.facebook.com/{GRAPH_VERSION}/{comment_id}"
        assert "/likes" not in url
        return _DummyResponse(200, {"success": True})

    monkeypatch.setattr(meta_comments, "_graph_delete", _ok)
    ok = client.post(
        ACTION_PATH,
        json={"channel": "facebook", "conversation_key": comment_conversation_key(comment_id), "action": "delete"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["deleted"] is True
    assert PAGE_TOKEN not in ok.text
    assert len(calls) == 1
    db.expire_all()
    row = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == comment_id))
    assert row is not None
    assert row.archived_at is not None
    assert (row.metadata_json or {}).get("deleted_on_platform") is True
    assert (row.metadata_json or {}).get("deleted_at")
    assert (row.metadata_json or {}).get("deleted_by")
    feed = list_communication_feed(db, channel="facebook_comment", page=1, page_size=25)
    assert not any(item.preview == "Silinecek FB" for item in feed.items)
    audits = list(
        db.scalars(select(CrmCommunicationAuditLog).where(CrmCommunicationAuditLog.event_type == "communication.deleted")).all()
    )
    assert audits
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0

    comment_fail = f"{PAGE_ID}_delfail_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_fail, text="Silinmesin FB", sender="1029384756107001"))
    monkeypatch.setattr(meta_comments, "_graph_delete", lambda url, *, token: _DummyResponse(400, {"error": {"message": "denied"}}))
    failed = client.post(
        ACTION_PATH,
        json={"channel": "facebook", "conversation_key": comment_conversation_key(comment_fail), "action": "delete"},
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == PUBLIC_DELETE_FAILED
    db.expire_all()
    still = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == comment_fail))
    assert still is not None
    assert still.archived_at is None
    feed_after = list_communication_feed(db, channel="facebook_comment", page=1, page_size=25)
    assert any(item.preview == "Silinmesin FB" for item in feed_after.items)

    monkeypatch.delenv("META_PAGE_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    missing = client.post(
        ACTION_PATH,
        json={"channel": "facebook", "conversation_key": comment_conversation_key(comment_fail), "action": "delete"},
    )
    assert missing.status_code == 503
    assert missing.json()["detail"] == PUBLIC_COMMENT_NOT_CONFIGURED


def test_instagram_comment_delete_success_failure(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    comment_id = f"igdel_{uuid4().hex[:10]}"
    _post(client, _ig_comment_payload(comment_id=comment_id, text="Silinecek IG"))
    db.expire_all()
    _enable_instagram_send(monkeypatch)

    def _ok(url: str, *, token: str):
        assert token == IG_TOKEN
        assert url == f"https://graph.instagram.com/{GRAPH_VERSION}/{comment_id}"
        return _DummyResponse(200, {"success": True})

    monkeypatch.setattr(meta_comments, "_graph_delete", _ok)
    ok = client.post(
        ACTION_PATH,
        json={"channel": "instagram", "conversation_key": comment_conversation_key(comment_id), "action": "delete"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["deleted"] is True
    assert IG_TOKEN not in ok.text
    db.expire_all()
    row = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == comment_id))
    assert row is not None
    assert row.archived_at is not None
    feed = list_communication_feed(db, channel="instagram_comment", page=1, page_size=25)
    assert not any(item.preview == "Silinecek IG" for item in feed.items)
    assert int(db.scalar(select(func.count()).select_from(Lead)) or 0) == 0

    comment_fail = f"igdelfail_{uuid4().hex[:10]}"
    _post(client, _ig_comment_payload(comment_id=comment_fail, text="Silinmesin IG", sender="17841400006660001"))
    monkeypatch.setattr(meta_comments, "_graph_delete", lambda url, *, token: _DummyResponse(500, {"error": {"message": "down"}}))
    failed = client.post(
        ACTION_PATH,
        json={"channel": "instagram", "conversation_key": comment_conversation_key(comment_fail), "action": "delete"},
    )
    assert failed.status_code == 502
    assert failed.json()["detail"] == PUBLIC_DELETE_FAILED
    db.expire_all()
    still = db.scalar(select(CrmCommunication).where(CrmCommunication.external_provider_id == comment_fail))
    assert still is not None and still.archived_at is None

    monkeypatch.delenv("META_INSTAGRAM_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()
    missing = client.post(
        ACTION_PATH,
        json={"channel": "instagram", "conversation_key": comment_conversation_key(comment_fail), "action": "delete"},
    )
    assert missing.status_code == 503
    assert missing.json()["detail"] == PUBLIC_COMMENT_NOT_CONFIGURED


def test_comment_delete_requires_auth(auth_client: TestClient) -> None:
    response = auth_client.post(
        ACTION_PATH,
        json={"channel": "facebook", "conversation_key": comment_conversation_key("x"), "action": "delete"},
    )
    assert response.status_code == 401
    assert PAGE_TOKEN not in response.text
