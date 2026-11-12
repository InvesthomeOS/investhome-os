"""Completion, phased projects, and agreement cancellation stay on existing records."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityReminder, CrmTaskStatus
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.inventory import InventoryAsset, InventoryAssetType, InventorySalesStatus, UsageType
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.services.crm.agreement_service import list_project_unit_catalog
from investhome_api.services.notification_service import dismiss_all
from investhome_api.models.notification import Notification, NotificationPriority, NotificationSource, NotificationStatus, NotificationType
from investhome_api.models.user_auth import User, UserStatus


def test_complete_stores_note_and_drops_future_reminder(client: TestClient, db: Session) -> None:
    lead = client.post("/crm/leads", json={"full_name": "Tamamlanan", "source": "manual"})
    assert lead.status_code == 201, lead.text
    created = client.post(
        "/crm/tasks",
        json={
            "title": "Arama",
            "description": "Orijinal talimat",
            "lead_id": lead.json()["id"],
            "due_on": "2026-12-01",
            "due_time": "15:00",
            "timezone": "Europe/Istanbul",
        },
    )
    assert created.status_code == 201, created.text
    activity_id = created.json()["activity"]["id"]
    done = client.post(f"/crm/tasks/{activity_id}/complete", json={"outcome": "Arama yapıldı. Bir süre düşünecekler."})
    assert done.status_code == 200, done.text
    db.expire_all()
    row = db.get(CrmActivity, UUID(activity_id))
    assert row is not None
    assert row.task_status == CrmTaskStatus.COMPLETED
    assert row.completed_at is not None
    assert row.outcome == "Arama yapıldı. Bir süre düşünecekler."
    assert row.description == "Orijinal talimat"
    pending = db.query(CrmActivityReminder).filter_by(activity_id=row.id, is_sent=False).all()
    assert pending == []


def test_reschedule_replaces_the_ten_minute_reminder(client: TestClient, db: Session) -> None:
    lead = client.post("/crm/leads", json={"full_name": "Ertelenen", "source": "manual"})
    created = client.post(
        "/crm/tasks",
        json={
            "title": "Tekrar ara",
            "lead_id": lead.json()["id"],
            "due_on": "2026-12-02",
            "due_time": "10:00",
            "timezone": "Europe/Istanbul",
        },
    )
    activity_id = created.json()["activity"]["id"]
    moved = client.post(
        f"/crm/tasks/{activity_id}/reschedule",
        json={"due_on": "2026-12-03", "due_time": "11:30", "timezone": "Europe/Istanbul"},
    )
    assert moved.status_code == 200, moved.text
    db.expire_all()
    row = db.get(CrmActivity, UUID(activity_id))
    reminders = db.query(CrmActivityReminder).filter_by(activity_id=row.id, is_sent=False).all()
    assert len(reminders) == 1
    assert reminders[0].offset_minutes == 10
    assert reminders[0].remind_at == row.due_date - timedelta(minutes=10)


def test_phased_project_without_phases_does_not_list_units(db: Session) -> None:
    project = Project(
        project_code="PRJ-PHASE-FLAG",
        project_name="Phased Empty",
        project_type=ProjectType.RESIDENTIAL,
        development_type=DevelopmentType.GROUND_UP,
        project_status=ProjectStatus.CONSTRUCTION,
        uses_phases=True,
    )
    db.add(project)
    db.flush()
    db.add(
        InventoryAsset(
            project_id=project.id,
            display_id="201",
            system_code="PHASE-FLAG-201",
            asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
            usage_type=UsageType.RESIDENTIAL,
            sales_status=InventorySalesStatus.AVAILABLE_FOR_SALE,
        )
    )
    db.commit()
    catalog = list_project_unit_catalog(db, str(project.id))
    assert catalog["uses_phases"] is True
    assert catalog["phase_ready"] is False
    assert catalog["items"] == []


def test_dismiss_all_keeps_the_row(db: Session) -> None:
    user = User(
        full_name="Notify",
        email="notify-dismiss@example.com",
        hashed_password="x",
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    row = Notification(
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.MEDIUM,
        title_key="task",
        message_key="due",
        recipient_user_id=user.id,
        source=NotificationSource.AUTOMATION,
        status=NotificationStatus.UNREAD,
        dedupe_key=f"dismiss-all-{datetime.now(UTC).timestamp()}",
    )
    db.add(row)
    db.commit()
    count = dismiss_all(db, user)
    db.commit()
    assert count >= 1
    db.expire_all()
    saved = db.get(Notification, row.id)
    assert saved is not None
    assert saved.status == NotificationStatus.DISMISSED


def test_cancel_preserves_agreement_and_releases_unit_only_when_clear(client: TestClient, db: Session) -> None:
    project = Project(
        project_code="PRJ-CANCEL",
        project_name="Cancel Tower",
        project_type=ProjectType.RESIDENTIAL,
        development_type=DevelopmentType.GROUND_UP,
        project_status=ProjectStatus.CONSTRUCTION,
        uses_phases=False,
    )
    db.add(project)
    db.flush()
    asset = InventoryAsset(
        project_id=project.id,
        display_id="201",
        system_code="CANCEL-201",
        asset_type=InventoryAssetType.RESIDENTIAL_UNIT,
        usage_type=UsageType.RESIDENTIAL,
        sales_status=InventorySalesStatus.SOLD,
    )
    buyer = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="İptal Müşteri",
        status=CrmContactStatus.ACTIVE,
        source="test",
    )
    other = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name="Diğer Alıcı",
        status=CrmContactStatus.ACTIVE,
        source="test",
    )
    db.add_all([asset, buyer, other])
    db.flush()
    first = CrmAgreement(
        contact_id=buyer.id,
        project_id=project.id,
        inventory_asset_id=asset.id,
        project_group="cancel_tower",
        source="test",
        source_external_id="cancel-1",
        status=CrmAgreementStatus.ACTIVE,
        unit_number="201",
        investment_amount="500000",
    )
    second = CrmAgreement(
        contact_id=other.id,
        project_id=project.id,
        inventory_asset_id=asset.id,
        project_group="cancel_tower",
        source="test",
        source_external_id="cancel-2",
        status=CrmAgreementStatus.ACTIVE,
        unit_number="201",
        investment_amount="500000",
    )
    lead = Lead(
        full_name=buyer.display_name,
        status=LeadStatus.WON,
        source="test",
        ingest_status="ok",
        converted_contact_id=buyer.id,
    )
    db.add_all([first, second, lead])
    db.commit()
    people_before = db.query(CrmContact).count()
    blocked = client.post(
        f"/crm/agreements/{first.id}/cancel",
        json={"reason": "Vazgeçti", "note": "Düşünecek", "cancelled_on": "2026-11-10"},
    )
    assert blocked.status_code == 200, blocked.text
    db.expire_all()
    saved = db.get(CrmAgreement, first.id)
    assert saved is not None
    assert saved.status == CrmAgreementStatus.CANCELLED
    assert saved.cancellation_reason == "Vazgeçti"
    assert saved.cancellation_note == "Düşünecek"
    assert saved.cancelled_by is not None
    assert saved.cancelled_at is not None
    assert saved.unit_number == "201"
    assert saved.investment_amount == "500000"
    assert db.get(InventoryAsset, asset.id).sales_status == InventorySalesStatus.SOLD
    returned = client.post(f"/crm/agreements/{first.id}/return-pipeline", json={"stage": "qualified"})
    assert returned.status_code == 200, returned.text
    db.expire_all()
    assert db.get(Lead, lead.id).status == LeadStatus.QUALIFIED
    assert db.query(CrmContact).count() == people_before
    assert db.get(CrmAgreement, first.id).status == CrmAgreementStatus.CANCELLED
    released = client.post(
        f"/crm/agreements/{second.id}/cancel",
        json={"reason": "İkinci iptal"},
    )
    assert released.status_code == 200, released.text
    db.expire_all()
    assert db.get(InventoryAsset, asset.id).sales_status == InventorySalesStatus.AVAILABLE_FOR_SALE
    assert db.get(CrmAgreement, second.id) is not None
