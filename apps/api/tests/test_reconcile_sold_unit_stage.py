"""Sold-unit delivery stage moves only an already-linked current agreement."""

import importlib.util
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.services.crm.unit_change import HISTORICAL_UNIT_CHANGE_SOURCE

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_sold_unit_owners.py"
_spec = importlib.util.spec_from_file_location("reconcile_sold_unit_owners", SCRIPT)
assert _spec is not None and _spec.loader is not None
reconcile = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = reconcile
_spec.loader.exec_module(reconcile)


def _project(db: Session) -> Project:
    row = Project(
        project_code="PRJ-DELIVERY-1812",
        project_name="1812 H Place NE",
        project_type=ProjectType.RESIDENTIAL,
        development_type=DevelopmentType.GROUND_UP,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(row)
    db.flush()
    return row


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


def _agreement(
    db: Session,
    *,
    project: Project,
    contact: CrmContact,
    unit: str,
    stage: str,
    external: str,
    source: str = "bitrix",
    status: CrmAgreementStatus = CrmAgreementStatus.ACTIVE,
    extra: dict | None = None,
) -> CrmAgreement:
    meta = {
        "stage_label": stage,
        "bitrix_deal_id": f"deal-{external}",
        "bitrix_live": {"stage_label": stage, "deal_id": external},
        "original_unit": unit,
    }
    if extra:
        meta.update(extra)
    row = CrmAgreement(
        contact_id=contact.id,
        project_id=project.id,
        project_group="1812_h_pl",
        source=source,
        source_external_id=external,
        status=status,
        unit_number=unit,
        metadata_json=meta,
    )
    db.add(row)
    db.flush()
    return row


def _classified(db: Session, unit: str, owners: str, contacts: list[CrmContact]) -> dict:
    return reconcile.classify_row(
        db,
        project_label="1812 H PL",
        unit=unit,
        owners=owners,
        contacts=contacts,
    )


def test_delivery_stage_updates_only_the_linked_current_agreement(db: Session) -> None:
    project = _project(db)
    zafer = _person(db, "Zafer Yıldırım")
    ilgaz = _person(db, "Ilgaz Uzunca")
    ayse_a = _person(db, "Ayşe Çimen")
    ayse_b = _person(db, "Ayşe Çimen")
    holder = _person(db, "Unrelated Holder")
    ramazan = _person(db, "Ramazan Dinçer")
    semih = _person(db, "Semih Sönmez")
    umit = _person(db, "Ümit Çimen")
    engin = _person(db, "Engin Uyan")
    ready = _agreement(
        db,
        project=project,
        contact=zafer,
        unit="101",
        stage="Para Transferi",
        external="delivery-101",
    )
    already = _agreement(
        db,
        project=project,
        contact=ilgaz,
        unit="201",
        stage="Ev Teslim Süreci",
        external="delivery-201",
    )
    _agreement(
        db,
        project=project,
        contact=holder,
        unit="204",
        stage="Satış Sözleşmesi",
        external="delivery-204",
        extra={"buyer_note": "Ayşe Çimen"},
    )
    first = _agreement(
        db,
        project=project,
        contact=ramazan,
        unit="207",
        stage="Para Transferi",
        external="delivery-207-a",
    )
    _agreement(
        db,
        project=project,
        contact=ramazan,
        unit="207",
        stage="Satış Sözleşmesi",
        external="delivery-207-b",
    )
    _agreement(
        db,
        project=project,
        contact=holder,
        unit="208",
        stage="Kimlik Bilgileri",
        external="delivery-208-old",
        source=HISTORICAL_UNIT_CHANGE_SOURCE,
    )
    historical_current = _agreement(
        db,
        project=project,
        contact=semih,
        unit="208",
        stage="Para Transferi",
        external="delivery-208",
    )
    unlinked = _agreement(
        db,
        project=project,
        contact=holder,
        unit="301",
        stage="Para Transferi",
        external="delivery-301",
        extra={"buyer_note": "Ümit Çimen"},
    )
    cancelled = _agreement(
        db,
        project=project,
        contact=engin,
        unit="303",
        stage="Para Transferi",
        external="delivery-303",
        status=CrmAgreementStatus.CANCELLED,
    )
    before = dict(ready.metadata_json)
    contacts = [zafer, ilgaz, ayse_a, ayse_b, holder, ramazan, semih, umit, engin]
    db.commit()

    plans = {
        row["unit"]: reconcile.plan_delivery_stage(db, _classified(db, row["unit"], row["owners"], contacts))
        for row in (
            {"unit": "101", "owners": "Zafer Yıldırım"},
            {"unit": "201", "owners": "Ilgaz Uzunca"},
            {"unit": "204", "owners": "Ayşe Çimen"},
            {"unit": "206", "owners": "Oya Nermin Uyan"},
            {"unit": "207", "owners": "Ramazan Dinçer"},
            {"unit": "208", "owners": "Semih Sönmez"},
            {"unit": "301", "owners": "Ümit Çimen"},
            {"unit": "303", "owners": "Engin Uyan"},
        )
    }

    assert plans["101"]["action"] == "READY_FOR_STAGE"
    assert plans["101"]["stage_change"] == "Para Transferi -> Ev Teslim Süreci"
    assert plans["201"]["action"] == "ALREADY_AT_TARGET"
    assert plans["201"]["stage_change"] == "Ev Teslim Süreci -> Ev Teslim Süreci"
    assert plans["204"]["action"] == "AMBIGUOUS_PERSON"
    assert plans["206"]["action"] == "PERSON_NOT_FOUND"
    assert plans["207"]["action"] == "AGREEMENT_NOT_UNIQUE"
    assert plans["208"]["action"] == "READY_FOR_STAGE"
    assert plans["208"]["agreement_id"] == str(historical_current.id)
    assert plans["301"]["action"] == "SKIPPED"
    assert plans["303"]["action"] == "AGREEMENT_NOT_UNIQUE"
    assert ready.metadata_json["stage_label"] == "Para Transferi"

    assert reconcile.apply_delivery_stage(db, plans["201"]) == 0
    assert reconcile.apply_delivery_stage(db, plans["204"]) == 0
    assert reconcile.apply_delivery_stage(db, plans["206"]) == 0
    assert reconcile.apply_delivery_stage(db, plans["207"]) == 0
    assert reconcile.apply_delivery_stage(db, plans["301"]) == 0
    assert reconcile.apply_delivery_stage(db, plans["303"]) == 0
    assert reconcile.apply_delivery_stage(db, plans["101"]) == 1
    db.commit()
    db.refresh(ready)
    db.refresh(already)
    db.refresh(unlinked)
    db.refresh(cancelled)
    db.refresh(first)
    assert ready.metadata_json["stage_label"] == "Ev Teslim Süreci"
    assert ready.metadata_json["bitrix_deal_id"] == before["bitrix_deal_id"]
    assert ready.metadata_json["bitrix_live"]["deal_id"] == "delivery-101"
    assert ready.metadata_json["original_unit"] == "101"
    assert already.metadata_json["stage_label"] == "Ev Teslim Süreci"
    assert unlinked.metadata_json["stage_label"] == "Para Transferi"
    assert cancelled.metadata_json["stage_label"] == "Para Transferi"
    assert first.metadata_json["stage_label"] == "Para Transferi"
    assert db.query(CrmAgreementParticipant).count() == 0
    assert db.query(CrmContact).count() == len(contacts)


def test_delivery_cli_stays_dry_run_without_apply(monkeypatch) -> None:
    calls: dict[str, bool] = {}

    def fake_run(apply: bool, *, set_delivery_stage: bool = False):
        calls["apply"] = apply
        calls["set_delivery_stage"] = set_delivery_stage
        if set_delivery_stage:
            return [
                {
                    "action": "READY_FOR_STAGE",
                    "project": "1812 H PL",
                    "unit": "101",
                    "owners": "Zafer Yıldırım",
                    "stage_change": "Para Transferi -> Ev Teslim Süreci",
                }
            ]
        return [
            {
                "classification": "ALREADY_LINKED",
                "confidence": "DETERMINISTIC",
                "project": "1812 H PL",
                "unit": "101",
                "owners": "Zafer Yıldırım",
            }
        ]

    monkeypatch.setattr(reconcile, "run", fake_run)
    assert reconcile.main(["--set-delivery-stage"]) == 0
    assert calls == {"apply": False, "set_delivery_stage": True}
    assert reconcile.main([]) == 0
    assert calls == {"apply": False, "set_delivery_stage": False}
