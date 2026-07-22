"""Marketing form submission pipeline tests."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import select

from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.marketing_landing_conversion import (
    FormStatus,
    MarketingForm,
    MarketingFormField,
    MarketingFormSubmission,
)


def _published_form_with_email(db: Session, *, auto_create: bool = False) -> MarketingForm:
    form = MarketingForm(
        name="Submit Form",
        slug=f"submit-{uuid4().hex[:6]}",
        status=FormStatus.PUBLISHED,
        consent_config_json={
            "require_explicit_consent": True,
            "auto_create_contact": auto_create,
        },
    )
    db.add(form)
    db.flush()
    db.add(
        MarketingFormField(
            form_id=form.id,
            field_key="email",
            field_type="email",
            label="Email",
            required=True,
        )
    )
    db.add(
        MarketingFormField(
            form_id=form.id,
            field_key="full_name",
            field_type="text",
            label="Name",
            required=True,
        )
    )
    db.flush()
    return form


def test_submission_idempotency(client: TestClient, db: Session) -> None:
    form = _published_form_with_email(db)
    db.commit()
    key = f"idempotency-{uuid4().hex}"
    payload = {
        "values": {"email": f"test-{uuid4().hex[:6]}@example.com", "full_name": "Test User"},
        "consent": {"consent_email": True},
        "idempotency_key": key,
    }
    first = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert first.status_code == 201
    second = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_unknown_consent_blocks_marketing(client: TestClient, db: Session) -> None:
    form = _published_form_with_email(db, auto_create=True)
    db.commit()
    email = f"unknown-{uuid4().hex[:6]}@example.com"
    response = client.post(
        f"/public/marketing/forms/{form.slug}/submit",
        json={
            "values": {"email": email, "full_name": "Unknown Consent"},
            "consent": {},
            "idempotency_key": f"key-{uuid4().hex}",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] in ("pending_review", "lead_context_created")
    sub = db.get(MarketingFormSubmission, UUID(response.json()["id"]))
    assert sub is not None
    if sub.lead_context_id:
        from investhome_api.models.marketing import MarketingLeadContext

        ctx = db.get(MarketingLeadContext, sub.lead_context_id)
        assert ctx.marketing_status == "blocked_consent"


def test_no_silent_contact_creation(client: TestClient, db: Session) -> None:
    form = _published_form_with_email(db, auto_create=False)
    db.commit()
    email = f"silent-{uuid4().hex[:6]}@example.com"
    response = client.post(
        f"/public/marketing/forms/{form.slug}/submit",
        json={
            "values": {"email": email, "full_name": "Silent User"},
            "consent": {"consent_email": True},
            "idempotency_key": f"key-{uuid4().hex}",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"
    assert response.json()["contact_id"] is None
    contact = db.scalar(select(CrmContact).where(CrmContact.primary_email == email))
    assert contact is None


def test_authorized_contact_creation(client: TestClient, db: Session) -> None:
    form = _published_form_with_email(db, auto_create=True)
    db.commit()
    email = f"create-{uuid4().hex[:6]}@example.com"
    response = client.post(
        f"/public/marketing/forms/{form.slug}/submit",
        json={
            "values": {"email": email, "full_name": "Created User"},
            "consent": {"consent_email": True},
            "idempotency_key": f"key-{uuid4().hex}",
        },
    )
    assert response.status_code == 201
    assert response.json()["contact_id"] is not None


def test_server_validation_rejects_unknown_fields(client: TestClient, db: Session) -> None:
    form = _published_form_with_email(db)
    db.commit()
    response = client.post(
        f"/public/marketing/forms/{form.slug}/submit",
        json={
            "values": {"email": "a@b.com", "full_name": "X", "injected_field": "bad"},
            "consent": {"consent_email": True},
            "idempotency_key": f"key-{uuid4().hex}",
        },
    )
    assert response.status_code == 422


def test_duplicate_detection(client: TestClient, db: Session) -> None:
    form = _published_form_with_email(db, auto_create=True)
    db.commit()
    email = f"dup-{uuid4().hex[:6]}@example.com"
    payload = {
        "values": {"email": email, "full_name": "Dup User"},
        "consent": {"consent_email": True},
        "idempotency_key": f"key1-{uuid4().hex}",
    }
    client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    payload["idempotency_key"] = f"key2-{uuid4().hex}"
    second = client.post(f"/public/marketing/forms/{form.slug}/submit", json=payload)
    assert second.status_code == 201
    assert second.json()["status"] == "duplicate_detected"
