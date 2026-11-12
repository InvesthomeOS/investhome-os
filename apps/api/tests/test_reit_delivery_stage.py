"""REIT delivery stage uses the CRM label and does not invent records."""

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.services.crm.agreement_service import agreement_board, format_money, _normalize_agreement_amount

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_reit_delivery_stage.py"
_spec = importlib.util.spec_from_file_location("reconcile_reit_delivery_stage", SCRIPT)
assert _spec is not None and _spec.loader is not None
reit = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = reit
_spec.loader.exec_module(reit)


def _person(db: Session, name: str) -> CrmContact:
    row = CrmContact(
        contact_type=CrmContactType.INVESTOR,
        record_kind=CrmRecordKind.PERSON,
        display_name=name,
        status=CrmContactStatus.ACTIVE,
        source="test",
    )
    db.add(row)
    db.flush()
    return row


def _reit(db: Session, person: CrmContact, *, stage: str, status: CrmAgreementStatus, external: str) -> CrmAgreement:
    row = CrmAgreement(
        contact_id=person.id,
        project_group="reit",
        source="test",
        source_external_id=external,
        status=status,
        investment_amount="500000",
        metadata_json={
            "stage_label": stage,
            "currency": "USD",
            "opportunity": "500000",
            "bitrix_deal_status": "won",
            "bitrix_deal_id": external,
            "bitrix_live": {"stage_label": "Deal won", "deal_id": external},
        },
    )
    db.add(row)
    db.flush()
    return row


def test_crm_stage_label_wins_over_legacy_won(db: Session) -> None:
    person = _person(db, "Göksel Canlılar")
    _reit(db, person, stage="Ev Teslim Süreci", status=CrmAgreementStatus.UNKNOWN, external="reit-won-override")
    db.commit()
    board = agreement_board(db, project_group="reit")
    assert board["kpis"]["won"] == 0
    column = next(item for item in board["columns"] if item["stage"] == "Ev Teslim Süreci")
    assert column["total"] == 1
    assert column["items"][0].stage_label == "Ev Teslim Süreci"
    assert column["items"][0].amount_label == "$500,000"


def test_usd_amount_formats_without_storing_the_symbol() -> None:
    assert format_money("500000", "USD") == "$500,000"
    assert format_money("500000.00", "EUR") == "€500,000"
    assert _normalize_agreement_amount("$500,000") == "500000"


def test_reit_dry_run_matches_existing_agreements_and_skips_cancelled(db: Session) -> None:
    people = {name: _person(db, name) for name in reit.AUTHORITATIVE_MEMBERS}
    people["Hande Erin Suner"].display_name = "Hande Erin suner"
    for index, name in enumerate(reit.AUTHORITATIVE_MEMBERS):
        _reit(
            db,
            people[name],
            stage="Kazanıldı" if index == 0 else "Deal won",
            status=CrmAgreementStatus.UNKNOWN,
            external=f"reit-member-{index}",
        )
    cancelled_person = _person(db, "Bilgehan Eryılmaz")
    _reit(
        db,
        cancelled_person,
        stage="Deal won",
        status=CrmAgreementStatus.CANCELLED,
        external="reit-cancelled",
    )
    db.commit()
    contacts_before = db.scalar(select(func.count()).select_from(CrmContact))
    agreements_before = db.scalar(select(func.count()).select_from(CrmAgreement))
    planned = reit.plan_reit_delivery(db)
    assert len(planned) == 10
    assert {item["action"] for item in planned} == {"READY_FOR_STAGE"}
    assert all(item["target_stage"] == "Ev Teslim Süreci" for item in planned)
    assert all(item["agreement_id"] for item in planned)
    written = reit.apply_reit_delivery(db, planned)
    assert written == 10
    db.commit()
    assert db.scalar(select(func.count()).select_from(CrmContact)) == contacts_before
    assert db.scalar(select(func.count()).select_from(CrmAgreement)) == agreements_before
    saved = db.get(CrmAgreement, planned[0]["agreement"].id)
    assert saved is not None
    assert saved.metadata_json["stage_label"] == "Ev Teslim Süreci"
    assert saved.metadata_json["bitrix_live"]["stage_label"] == "Deal won"
    assert saved.metadata_json["bitrix_deal_id"] == planned[0]["agreement"].metadata_json["bitrix_deal_id"]
    again = reit.plan_reit_delivery(db)
    assert {item["action"] for item in again} == {"ALREADY_AT_TARGET"}
    cancelled = db.scalar(select(CrmAgreement).where(CrmAgreement.source_external_id == "reit-cancelled"))
    assert cancelled is not None
    assert cancelled.status == CrmAgreementStatus.CANCELLED
    assert cancelled.metadata_json["stage_label"] == "Deal won"
