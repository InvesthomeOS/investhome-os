"""CRM Pano live dashboard — current vs historical purchases, no demo metrics."""

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityType,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactDuplicateCandidate,
    CrmContactStatus,
    CrmContactType,
    CrmRecordKind,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.services.crm.unit_change import HISTORICAL_UNIT_CHANGE_SOURCE


def test_dashboard_has_operational_payload(client: TestClient) -> None:
    response = client.get("/crm/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "kpis" in body
    assert "purchase_scope" in body
    assert "charts" in body
    assert "panels" in body
    kpis = body["kpis"]
    for key in (
        "current_purchases",
        "investors",
        "active_tasks",
        "open_leads",
        "documents_review",
        "matches_pending",
    ):
        assert key in kpis
        assert kpis[key] >= 0
    scope = body["purchase_scope"]
    assert scope["current"] + scope["historical"] == scope["total"]
    charts = body["charts"]
    for key in (
        "purchases_by_project",
        "purchases_by_month",
        "task_status",
        "communication_channels",
        "lead_pipeline",
        "document_status",
    ):
        assert isinstance(charts[key], list)
    panels = body["panels"]
    for key in (
        "recent_activities",
        "upcoming_tasks",
        "recent_documents",
        "review_queue",
        "recent_leads",
    ):
        assert isinstance(panels[key], list)


def test_dashboard_current_purchases_exclude_historical_and_dedupe_investors(
    client: TestClient, db: Session
) -> None:
    owner = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Pano Investor",
        status=CrmContactStatus.ACTIVE,
        source="Bitrix",
    )
    other = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Pano Co-owner",
        status=CrmContactStatus.ACTIVE,
        source="Bitrix",
        review_required=True,
        notes="INCELEME_GEREKLI keep separate",
    )
    db.add_all([owner, other])
    db.flush()
    db.add(
        CrmAgreement(
            contact_id=owner.id,
            project_group="1812_h_pl",
            source="bitrix",
            source_external_id="pano:1812-306",
            unit_number="306",
            agreement_date=date(2024, 3, 12),
        )
    )
    db.add(
        CrmAgreement(
            contact_id=owner.id,
            project_group="uniloft",
            source="bitrix",
            source_external_id="pano:uniloft-1",
            unit_number="12",
            agreement_date=date(2024, 4, 1),
        )
    )
    db.add(
        CrmAgreement(
            contact_id=owner.id,
            project_group="1812_h_pl",
            source=HISTORICAL_UNIT_CHANGE_SOURCE,
            source_external_id="pano:1812-hist",
            unit_number="B07",
            metadata_json={"historical_unit_change": True},
        )
    )
    db.add(
        CrmAgreement(
            contact_id=other.id,
            project_group="1812_h_pl",
            source="bitrix",
            source_external_id="pano:1812-co",
            unit_number="208",
            agreement_date=date(2024, 5, 20),
        )
    )
    db.add(
        Lead(
            full_name="Pano Lead",
            status=LeadStatus.NEW,
            source="website",
            is_demo=False,
        )
    )
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=owner.id,
            activity_type=CrmActivityType.TASK,
            activity_category=CrmActivityCategory.TASK,
            title="Pano follow-up",
            task_status=CrmTaskStatus.NOT_STARTED,
            due_date=datetime(2030, 1, 15, tzinfo=UTC),
        )
    )
    left_id, right_id = (owner.id, other.id) if owner.id.hex < other.id.hex else (other.id, owner.id)
    db.add(
        CrmContactDuplicateCandidate(
            contact_id_a=left_id,
            contact_id_b=right_id,
            match_reason="email",
            match_kind="strong",
            match_score=0,
            status="pending",
            source="bitrix",
        )
    )
    db.commit()

    response = client.get("/crm/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()
    kpis = body["kpis"]
    scope = body["purchase_scope"]
    assert kpis["current_purchases"] >= 3
    assert scope["historical"] >= 1
    assert scope["current"] + scope["historical"] == scope["total"]
    assert kpis["current_purchases"] == scope["current"]
    assert kpis["investors"] >= 2
    assert kpis["open_leads"] >= 1
    assert kpis["active_tasks"] >= 1
    assert kpis["matches_pending"] >= 1
    project_chart = {row["key"]: row["count"] for row in body["charts"]["purchases_by_project"]}
    assert project_chart.get("1812_h_pl", 0) >= 2
    month_keys = {row["key"] for row in body["charts"]["purchases_by_month"]}
    assert "2024-03" in month_keys
    pipeline = {row["key"]: row["count"] for row in body["charts"]["lead_pipeline"]}
    assert pipeline.get("yeni", 0) >= 1
    assert any(item["title"] == "Pano Lead" for item in body["panels"]["recent_leads"])
    assert any(item["kind"] in {"match", "contact"} for item in body["panels"]["review_queue"])
    assert "pipelineValue" not in body["kpis"]
    assert "conversion" not in body["charts"]
