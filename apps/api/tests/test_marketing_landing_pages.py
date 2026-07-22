"""Marketing landing pages API tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import (
    DomainVerificationStatus,
    FormStatus,
    LandingPageDomain,
    LandingPageSection,
    LandingPageStatus,
    MarketingForm,
    MarketingLandingPage,
)


def _create_form(db: Session) -> MarketingForm:
    form = MarketingForm(
        name="Test Form",
        slug=f"test-form-{uuid4().hex[:6]}",
        status=FormStatus.PUBLISHED,
        consent_config_json={"require_explicit_consent": True},
    )
    db.add(form)
    db.flush()
    return form


def test_create_landing_page(client: TestClient) -> None:
    slug = f"lp-{uuid4().hex[:6]}"
    response = client.post("/marketing/landing-pages", json={"name": "Launch Page", "slug": slug})
    assert response.status_code == 201
    assert response.json()["slug"] == slug


def test_slug_uniqueness(client: TestClient) -> None:
    slug = f"dup-{uuid4().hex[:6]}"
    client.post("/marketing/landing-pages", json={"name": "First", "slug": slug})
    response = client.post("/marketing/landing-pages", json={"name": "Second", "slug": slug})
    assert response.status_code == 409


def test_publish_blocked_without_approval(client: TestClient, db: Session) -> None:
    form = _create_form(db)
    page = MarketingLandingPage(
        name="Blocked Page",
        slug=f"blocked-{uuid4().hex[:6]}",
        status=LandingPageStatus.APPROVED,
        form_id=form.id,
        consent_config_json={"channels": ["email"]},
    )
    db.add(page)
    db.flush()
    db.add(
        LandingPageSection(
            landing_page_id=page.id,
            section_type="hero",
            sort_order=0,
            config_json={"headline": "Test"},
        )
    )
    db.add(
        LandingPageDomain(
            landing_page_id=page.id,
            domain="example.com",
            verification_status=DomainVerificationStatus.VERIFIED,
            is_primary=True,
        )
    )
    db.commit()

    readiness = client.get(f"/marketing/landing-pages/{page.id}/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is False
    assert "approval_incomplete" in readiness.json()["blockers"]

    transition = client.post(
        f"/marketing/landing-pages/{page.id}/transition",
        json={"target_status": "published"},
    )
    assert transition.status_code == 422


def test_public_field_allowlist(client: TestClient, db: Session) -> None:
    page = MarketingLandingPage(name="Allowlist", slug=f"allow-{uuid4().hex[:6]}")
    db.add(page)
    db.commit()

    bad = client.post(
        f"/marketing/landing-pages/{page.id}/sections",
        json={
            "section_type": "hero",
            "config_json": {"public_fields": ["project.secret_field"]},
        },
    )
    assert bad.status_code == 400


def test_section_registry(client: TestClient) -> None:
    response = client.get("/marketing/landing-pages/section-registry")
    assert response.status_code == 200
    types = {item["section_type"] for item in response.json()}
    assert "hero" in types
    assert "lead_form" in types
