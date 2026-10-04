"""Public marketing form abuse protection."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.marketing_landing_conversion import (
    FormStatus,
    MarketingForm,
    MarketingFormField,
    MarketingFormSubmission,
)
from investhome_api.services.public_form_bot import reset_turnstile_verifier_for_tests
from investhome_api.services.public_form_rate_limit import GENERIC_RATE_LIMIT_MESSAGE


def _set_peer_ip(client: TestClient, ip: str) -> None:
    candidates = [
        getattr(client, "_transport", None),
        getattr(client, "transport", None),
    ]
    for transport in candidates:
        if transport is not None and hasattr(transport, "client"):
            transport.client = (ip, 50000)
            return
    raise AssertionError("TestClient transport does not expose ASGI client peer")


def _published_form(db: Session) -> MarketingForm:
    form = MarketingForm(
        name="Abuse Form",
        slug=f"abuse-{uuid4().hex[:8]}",
        status=FormStatus.PUBLISHED,
        consent_config_json={"require_explicit_consent": True, "auto_create_contact": False},
    )
    db.add(form)
    db.flush()
    db.add(
        MarketingFormField(
            form_id=form.id, field_key="email", field_type="email", label="Email", required=True
        )
    )
    db.add(
        MarketingFormField(
            form_id=form.id, field_key="full_name", field_type="text", label="Name", required=True
        )
    )
    db.flush()
    return form


def _payload(email: str | None = None) -> dict:
    return {
        "values": {
            "email": email or f"ok-{uuid4().hex[:8]}@example.com",
            "full_name": "Ok User",
        },
        "consent": {"consent_email": True},
        "idempotency_key": f"idem-{uuid4().hex}",
    }


def _count_subs(db: Session, form_id) -> int:
    return int(
        db.scalar(
            select(func.count()).where(MarketingFormSubmission.form_id == form_id)
        )
        or 0
    )


def test_normal_public_submission_succeeds(client: TestClient, db: Session) -> None:
    form = _published_form(db)
    db.commit()
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=_payload())
    assert response.status_code == 201
    assert _count_subs(db, form.id) == 1


def test_rate_limit_blocks_and_does_not_store(
    client: TestClient, db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("PUBLIC_FORM_BURST_LIMIT", "5")
    get_settings.cache_clear()
    form = _published_form(db)
    db.commit()
    _set_peer_ip(client, "198.51.100.10")
    url = f"/public/marketing/forms/{form.slug}/submit"
    for _ in range(5):
        ok = client.post(url, json=_payload())
        assert ok.status_code == 201, ok.text
    blocked = client.post(url, json=_payload())
    assert blocked.status_code == 429
    assert blocked.headers.get("retry-after")
    assert int(blocked.headers["retry-after"]) >= 1
    body = blocked.json()
    assert body["error"]["code"] == "rate_limited"
    assert GENERIC_RATE_LIMIT_MESSAGE in body["error"]["message"]
    assert _count_subs(db, form.id) == 5


def test_rate_limit_isolated_by_ip(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_FORM_BURST_LIMIT", "5")
    get_settings.cache_clear()
    form = _published_form(db)
    db.commit()
    url = f"/public/marketing/forms/{form.slug}/submit"
    _set_peer_ip(client, "198.51.100.11")
    for _ in range(5):
        assert client.post(url, json=_payload()).status_code == 201
    _set_peer_ip(client, "198.51.100.12")
    other = client.post(url, json=_payload())
    assert other.status_code == 201
    assert _count_subs(db, form.id) == 6


def test_oversized_field_rejected(client: TestClient, db: Session) -> None:
    form = _published_form(db)
    db.commit()
    payload = _payload()
    payload["values"]["full_name"] = "x" * 2001
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 422
    assert _count_subs(db, form.id) == 0


def test_oversized_body_rejected(client: TestClient, db: Session) -> None:
    form = _published_form(db)
    db.commit()
    payload = _payload()
    for index in range(18):
        payload["values"][f"extra_{index:02d}"] = "y" * 2000
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 413
    assert _count_subs(db, form.id) == 0


def test_honeypot_rejected_not_stored(client: TestClient, db: Session) -> None:
    form = _published_form(db)
    db.commit()
    payload = _payload()
    payload["hp_website"] = "http://spam.example"
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 400
    assert _count_subs(db, form.id) == 0


def test_invalid_bot_token_rejected(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_FORM_BOT_VERIFY", "true")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "unit-test-turnstile-secret-not-real")
    get_settings.cache_clear()
    reset_turnstile_verifier_for_tests(lambda _secret, _token, _ip: False)
    form = _published_form(db)
    db.commit()
    payload = _payload()
    payload["cf_turnstile_response"] = "invalid-token"
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 403
    assert _count_subs(db, form.id) == 0


def test_production_bot_misconfig_fails_closed(
    client: TestClient, db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("API_ENVIRONMENT", "production")
    monkeypatch.setenv("PUBLIC_FORM_BOT_VERIFY", "true")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("API_DEBUG", "false")
    monkeypatch.setenv("API_ENABLE_OPENAPI", "false")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://os.investhome.com")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    form = _published_form(db)
    db.commit()
    payload = _payload()
    payload["cf_turnstile_response"] = "dev-bypass"
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 503
    assert _count_subs(db, form.id) == 0


def test_dev_bypass_only_in_development(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setenv("API_ENVIRONMENT", "development")
    monkeypatch.setenv("PUBLIC_FORM_BOT_VERIFY", "true")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    form = _published_form(db)
    db.commit()
    payload = _payload()
    payload["cf_turnstile_response"] = "dev-bypass"
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 201
    assert _count_subs(db, form.id) == 1


def test_valid_turnstile_token_accepted(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_FORM_BOT_VERIFY", "true")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "unit-test-turnstile-secret-not-real")
    get_settings.cache_clear()
    reset_turnstile_verifier_for_tests(lambda _secret, token, _ip: token == "siteverify-ok")
    form = _published_form(db)
    db.commit()
    payload = _payload()
    payload["cf_turnstile_response"] = "siteverify-ok"
    response = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert response.status_code == 201
    assert UUID(response.json()["id"])
