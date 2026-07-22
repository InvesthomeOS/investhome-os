"""Marketing forms API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import FormStatus, MarketingForm, MarketingFormField


def test_create_form(client: TestClient) -> None:
    slug = f"form-{uuid4().hex[:6]}"
    response = client.post("/marketing/forms", json={"name": "Contact Form", "slug": slug})
    assert response.status_code == 201
    assert response.json()["slug"] == slug


def test_publish_blocked_without_fields(client: TestClient, db: Session) -> None:
    form = MarketingForm(
        name="Empty Form",
        slug=f"empty-{uuid4().hex[:6]}",
        consent_config_json={"require_explicit_consent": True},
    )
    db.add(form)
    db.commit()

    readiness = client.get(f"/marketing/forms/{form.id}/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is False
    assert "no_fields" in readiness.json()["blockers"]

    publish = client.post(f"/marketing/forms/{form.id}/publish")
    assert publish.status_code == 422


def test_form_server_validation_fields(client: TestClient, db: Session) -> None:
    form = MarketingForm(name="Valid Form", slug=f"valid-{uuid4().hex[:6]}", status=FormStatus.DRAFT)
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
    db.commit()

    fields = client.get(f"/marketing/forms/{form.id}/fields")
    assert fields.status_code == 200
    assert len(fields.json()) == 1


def test_circular_logic_rejected(client: TestClient, db: Session) -> None:
    form = MarketingForm(name="Logic Form", slug=f"logic-{uuid4().hex[:6]}")
    db.add(form)
    db.flush()
    field = MarketingFormField(form_id=form.id, field_key="email", field_type="email", label="Email")
    db.add(field)
    db.commit()

    response = client.post(
        f"/marketing/forms/{form.id}/logic",
        json={
            "target_field_id": str(field.id),
            "conditions_json": [{"field_id": str(field.id), "condition": "equals", "value": "x"}],
        },
    )
    assert response.status_code == 400


def test_field_registry(client: TestClient) -> None:
    response = client.get("/marketing/forms/field-registry")
    assert response.status_code == 200
    types = {item["field_type"] for item in response.json()}
    assert "email" in types
    assert "consent" in types
