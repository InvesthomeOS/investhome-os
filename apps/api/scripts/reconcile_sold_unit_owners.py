"""Link existing people to sold units. Dry-run unless --apply is passed.

Does not create people, agreements, purchases, or ownership percentages.
--apply only adds a participant on an existing purchase agreement when every
owner is already a unique contact and is not already on that agreement.

--set-delivery-stage plans a move to Ev Teslim Süreci. It still does not write
unless --apply is also passed. It never creates people, agreements, or inventory,
and it never changes a row whose person is missing or ambiguous.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.inventory import InventoryAsset
from investhome_api.models.project import Project
from investhome_api.services.crm.agreement_service import (
    _display_stage,
    canonical_agreement_stage,
    set_agreement_stage,
)
from investhome_api.services.crm.bitrix_project_aliases import fold_alias
from investhome_api.services.crm.unit_change import detached_relationship_clause, is_historical_unit_change

TARGET_STAGE = "Ev Teslim Süreci"
_STAGE_ACTIONS = (
    "READY_FOR_STAGE",
    "ALREADY_AT_TARGET",
    "PERSON_NOT_FOUND",
    "AMBIGUOUS_PERSON",
    "AGREEMENT_NOT_UNIQUE",
    "SKIPPED",
)

# Authoritative labels. Project match is the exact OS project_name, not a substring.
PROJECTS = {
    "1812 H PL": "1812 H Place NE",
    "1313 PENN": "1313",
    "2319 ONTARIO": "2319",
    "1307 K ST": "1307",
}

ROWS: list[tuple[str, str, str]] = [
    ("1812 H PL", "B05", "Ozan / Burcu Savaş"),
    ("1812 H PL", "101", "Zafer Yıldırım"),
    ("1812 H PL", "201", "Ilgaz Uzunca"),
    ("1812 H PL", "204", "Ayşe Çimen"),
    ("1812 H PL", "206", "Oya Nermin Uyan"),
    ("1812 H PL", "207", "Ramazan Dinçer"),
    ("1812 H PL", "208", "Semih Sönmez"),
    ("1812 H PL", "301", "Ümit Çimen"),
    ("1812 H PL", "303", "Engin Uyan"),
    ("1812 H PL", "304", "Berk Çimen"),
    ("1812 H PL", "305", "Lale Şenyol"),
    ("1812 H PL", "306", "Semrin-Gökhan Bülbül"),
    ("1812 H PL", "307", "Semra Arlı"),
    ("1812 H PL", "401", "Mehmet Berke Gür"),
    ("1313 PENN", "101", "Oraj Özgövde"),
    ("1313 PENN", "201", "Oğuz Çetin Başara"),
    ("1313 PENN", "301", "Onat Acet"),
    ("1313 PENN", "302", "Bahar - Gizem Başara"),
    ("2319 ONTARIO", "002", "Bahar Başara"),
    ("2319 ONTARIO", "101", "Murat Zengin"),
    ("2319 ONTARIO", "102", "Alpaslan Özdarendeli"),
    ("2319 ONTARIO", "201", "Bahar-Gizem-Oğuz Başara"),
    ("2319 ONTARIO", "202", "Emrah Gönenç"),
    ("2319 ONTARIO", "301", "Umut Uzuner"),
    ("2319 ONTARIO", "302", "Ceren Gönenç"),
    ("2319 ONTARIO", "401", "Arda Efe"),
    ("2319 ONTARIO", "402", "Can Aydemir"),
    ("2319 ONTARIO", "403", "Nedim Kondu"),
    ("1307 K ST", "002", "Galip - Muhsin Emre"),
    ("1307 K ST", "102", "Çağlar Çağ - Burak Tanrıverdi"),
    ("1307 K ST", "201", "Müjgan Özdarendeli"),
    ("1307 K ST", "202", "Hayati - Eyyub - Göksel Canlılar"),
    ("1307 K ST", "301", "Esra Gonulkırmaz"),
    ("1307 K ST", "302", "Alper Levi"),
    ("1307 K ST", "401", "Bengü Bilgiç"),
]


@dataclass
class PersonHit:
    status: str
    contact: CrmContact | None = None
    detail: str = ""
    evidence: str = ""
    confidence: str = "NOT FOUND"


def split_owners(cell: str) -> list[str]:
    parts = re.split(r"\s*/\s*|\s+-\s+|(?<=\S)-(?=\S)", cell)
    return [part.strip() for part in parts if part.strip()]


def _words(value: str) -> list[str]:
    return [part for part in fold_alias(value).split(" ") if part]


def _is_single_person(name: str) -> bool:
    return len(split_owners(name)) == 1


def _name_forms(contact: CrmContact) -> list[list[str]]:
    forms = [_words(contact.display_name or "")]
    first = contact.first_name or ""
    last = contact.last_name or ""
    if first or last:
        forms.append(_words(f"{first} {last}"))
        forms.append(_words(f"{last} {first}"))
    return [form for form in forms if form]


def _emails(contact: CrmContact) -> set[str]:
    values = [contact.primary_email or ""]
    if contact.secondary_emails:
        values.extend(str(item) for item in contact.secondary_emails)
    return {fold_alias(item) for item in values if fold_alias(item)}


def unit_aliases(unit: str) -> set[str]:
    """Evidence aliases only. Nothing is renamed."""
    return {
        fold_alias(unit),
        fold_alias(f"Unit{unit}"),
        fold_alias(f"Unit {unit}"),
        fold_alias(f"Unit-{unit}"),
    }


def _agreement_evidence(agreement: CrmAgreement) -> str:
    parts = [agreement.unit_number or ""]
    if agreement.metadata_json:
        parts.append(json.dumps(agreement.metadata_json, ensure_ascii=False, default=str))
    return fold_alias(" ".join(parts))


def match_owner(
    contacts: list[CrmContact],
    label: str,
    *,
    agreements: list[CrmAgreement],
    linked_ids: set[UUID],
) -> PersonHit:
    """A name candidate becomes deterministic only with purchase evidence.

    Same-email duplicates collapse to the contact already on the purchase.
    A same-name contact with no unit, deal, email, or phone evidence stays unresolved.
    """
    wanted = _words(label)
    if not wanted:
        return PersonHit("AMBIGUOUS_PERSON", detail=label, confidence="AMBIGUOUS", evidence="empty owner label")
    singles = [row for row in contacts if _is_single_person(row.display_name or "")]
    evidence = " ".join(_agreement_evidence(row) for row in agreements)
    if len(wanted) == 1:
        token = wanted[0]
        if token not in evidence:
            partial = [row for row in singles if token in _words(row.display_name or "")]
            already = [row for row in partial if row.id in linked_ids]
            if len(already) == 1:
                return PersonHit(
                    "FOUND",
                    already[0],
                    confidence="DETERMINISTIC",
                    evidence="this unit purchase already has this contact as an owner",
                )
            if partial:
                return PersonHit(
                    "AMBIGUOUS_PERSON",
                    detail=label,
                    confidence="AMBIGUOUS",
                    evidence="this unit purchase does not name the given name; a same-name contact exists but is not proof",
                )
            return PersonHit("PERSON_NOT_FOUND", detail=label, confidence="NOT FOUND", evidence="no contact and the purchase does not name them")
        named = [
            row
            for row in singles
            if token in _words(row.display_name or "")
            and all(part in evidence for part in _words(row.display_name or ""))
        ]
        contained = named
    else:
        exact = [row for row in singles if wanted in _name_forms(row)]
        contained = exact or [
        row
        for row in singles
        if all(token in _words(row.display_name or "") for token in wanted)
    ]
    if not contained:
        return PersonHit("PERSON_NOT_FOUND", detail=label, confidence="NOT FOUND", evidence="no contact contains every name token")
    evidence = " ".join(_agreement_evidence(row) for row in agreements)
    evidenced = [
        row
        for row in contained
        if row.id in linked_ids or all(token in evidence for token in wanted)
    ]
    if not evidenced:
        names = ", ".join(row.display_name for row in contained[:4])
        return PersonHit(
            "AMBIGUOUS_PERSON",
            detail=label,
            confidence="AMBIGUOUS",
            evidence=f"name candidate exists ({names}) but this unit purchase does not name them",
        )
    if len(evidenced) > 1:
        on_purchase = [row for row in evidenced if row.id in linked_ids]
        if len(on_purchase) == 1:
            others = [row for row in evidenced if row.id != on_purchase[0].id]
            same_email = all(_emails(row) & _emails(on_purchase[0]) for row in others) if others else True
            if same_email or not others:
                chosen = on_purchase[0]
                return PersonHit(
                    "FOUND",
                    chosen,
                    confidence="DETERMINISTIC",
                    evidence="purchase contact; same-email duplicate was not selected",
                )
        emails = {next(iter(_emails(row)), "") for row in evidenced}
        if len(on_purchase) == 1:
            chosen = on_purchase[0]
            return PersonHit(
                "FOUND",
                chosen,
                confidence="DETERMINISTIC",
                evidence="this unit purchase already points at one of the same-name contacts",
            )
        if len(emails) == 1 and len(on_purchase) == 1:
            chosen = on_purchase[0]
            return PersonHit("FOUND", chosen, confidence="DETERMINISTIC", evidence="shared email and purchase contact")
        return PersonHit(
            "AMBIGUOUS_PERSON",
            detail=label,
            confidence="AMBIGUOUS",
            evidence="more than one contact remains after purchase evidence: "
            + ", ".join(row.display_name for row in evidenced[:4]),
        )
    chosen = evidenced[0]
    if chosen.id in linked_ids:
        reason = "existing purchase contact"
    else:
        reason = "purchase or deal text names every token and only one contact matches"
    return PersonHit("FOUND", chosen, confidence="DETERMINISTIC", evidence=reason)


def classify_row(
    db: Session,
    *,
    project_label: str,
    unit: str,
    owners: str,
    contacts: list[CrmContact],
) -> dict[str, object]:
    project_name = PROJECTS[project_label]
    projects = db.scalars(select(Project).where(Project.project_name == project_name)).all()
    if len(projects) != 1:
        return {
            "project": project_label,
            "unit": unit,
            "owners": owners,
            "classification": "CONFLICT",
            "detail": f"project name {project_name} matched {len(projects)} rows",
        }
    project = projects[0]
    assets = db.scalars(
        select(InventoryAsset).where(
            InventoryAsset.project_id == project.id,
            InventoryAsset.display_id == unit,
            InventoryAsset.archived_at.is_(None),
        )
    ).all()
    if len(assets) > 1:
        return {
            "project": project_label,
            "unit": unit,
            "owners": owners,
            "classification": "MULTIPLE_UNIT_MATCHES",
            "detail": str(len(assets)),
        }
    aliases = unit_aliases(unit)
    agreements = [
        row
        for row in db.scalars(
            select(CrmAgreement).where(
                CrmAgreement.project_id == project.id,
                ~detached_relationship_clause(),
            )
        ).all()
        if fold_alias(row.unit_number or "") in aliases
    ]
    linked = _linked_contact_ids(db, agreements)
    hits = [
        match_owner(contacts, label, agreements=agreements, linked_ids=linked)
        for label in split_owners(owners)
    ]
    if any(hit.status == "AMBIGUOUS_PERSON" for hit in hits):
        classification = "AMBIGUOUS_PERSON"
    elif any(hit.status == "PERSON_NOT_FOUND" for hit in hits):
        classification = "PERSON_NOT_FOUND"
    elif len(assets) > 1:
        classification = "MULTIPLE_UNIT_MATCHES"
    elif not agreements and not assets:
        classification = "UNIT_NOT_FOUND"
    elif not agreements:
        classification = "CONFLICT"
    else:
        missing = [hit.contact for hit in hits if hit.contact is not None and hit.contact.id not in linked]
        classification = "ALREADY_LINKED" if not missing else "READY_TO_LINK"
    confidences = {hit.confidence for hit in hits}
    if classification in {"ALREADY_LINKED", "READY_TO_LINK"}:
        confidence = "DETERMINISTIC"
    elif "AMBIGUOUS" in confidences:
        confidence = "AMBIGUOUS"
    else:
        confidence = "NOT FOUND"
    return {
        "project": project_label,
        "unit": unit,
        "owners": owners,
        "classification": classification,
        "confidence": confidence,
        "people": [hit.contact.display_name if hit.contact else hit.detail for hit in hits],
        "evidence": [hit.evidence for hit in hits],
        "agreements": len(agreements),
        "assets": len(assets),
        "stored_units": sorted({row.unit_number or "" for row in agreements}),
        "contact_ids": [str(hit.contact.id) for hit in hits if hit.contact is not None],
        "agreement_ids": [str(row.id) for row in agreements],
    }


def _linked_contact_ids(db: Session, agreements: list[CrmAgreement]) -> set[UUID]:
    linked = {row.contact_id for row in agreements}
    if not agreements:
        return linked
    ids = [row.id for row in agreements]
    participants = db.scalars(
        select(CrmAgreementParticipant.contact_id).where(CrmAgreementParticipant.agreement_id.in_(ids))
    ).all()
    linked.update(participants)
    return linked


def _shown_stage(agreement: CrmAgreement) -> str:
    meta = agreement.metadata_json if isinstance(agreement.metadata_json, dict) else {}
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    return _display_stage(meta, live) or ""


def _already_at_target(stage: str) -> bool:
    text = stage.strip()
    if not text:
        return False
    try:
        return canonical_agreement_stage(text) == TARGET_STAGE
    except ValueError:
        return text == TARGET_STAGE


def current_unit_agreements(db: Session, *, project_label: str, unit: str) -> list[CrmAgreement]:
    """Current, non-detached purchases for one authoritative project and unit."""
    project_name = PROJECTS[project_label]
    projects = db.scalars(select(Project).where(Project.project_name == project_name)).all()
    if len(projects) != 1:
        return []
    aliases = unit_aliases(unit)
    rows = db.scalars(
        select(CrmAgreement).where(
            CrmAgreement.project_id == projects[0].id,
            CrmAgreement.status != CrmAgreementStatus.CANCELLED,
            ~detached_relationship_clause(),
        )
    ).all()
    return [
        row
        for row in rows
        if fold_alias(row.unit_number or "") in aliases and not is_historical_unit_change(row)
    ]


def plan_delivery_stage(db: Session, row: dict[str, object]) -> dict[str, object]:
    """Decide whether one authoritative row may move to Ev Teslim Süreci.

    No people, agreements, or inventory are created. Missing and ambiguous
    people are never selected. A write happens only later, and only for
    READY_FOR_STAGE, through set_agreement_stage().
    """
    classification = str(row.get("classification") or "")
    project = str(row.get("project") or "")
    unit = str(row.get("unit") or "")
    owners = str(row.get("owners") or "")
    agreements = current_unit_agreements(db, project_label=project, unit=unit) if project in PROJECTS else []
    current = _shown_stage(agreements[0]) if len(agreements) == 1 else ""
    contact_ids = [UUID(str(value)) for value in row.get("contact_ids") or []]
    linked = _linked_contact_ids(db, agreements[:1]) if len(agreements) == 1 else set()
    owners_linked = bool(contact_ids) and all(contact_id in linked for contact_id in contact_ids)
    deterministic = row.get("confidence") == "DETERMINISTIC"
    if classification == "AMBIGUOUS_PERSON":
        action = "AMBIGUOUS_PERSON"
    elif classification == "PERSON_NOT_FOUND":
        action = "PERSON_NOT_FOUND"
    elif classification not in {"ALREADY_LINKED", "READY_TO_LINK"} or not deterministic:
        action = "SKIPPED"
    elif len(agreements) != 1:
        action = "AGREEMENT_NOT_UNIQUE"
    elif not owners_linked:
        action = "SKIPPED"
    elif _already_at_target(current):
        action = "ALREADY_AT_TARGET"
    else:
        action = "READY_FOR_STAGE"
    return {
        "action": action,
        "project": project,
        "unit": unit,
        "owners": owners,
        "classification": classification,
        "current_stage": current,
        "target_stage": TARGET_STAGE,
        "stage_change": f"{current or '—'} -> {TARGET_STAGE}",
        "agreement_id": str(agreements[0].id) if action in {"READY_FOR_STAGE", "ALREADY_AT_TARGET"} else "",
    }


def apply_delivery_stage(db: Session, plan: dict[str, object]) -> int:
    """Set stage_label only. Every other metadata key stays as it is."""
    if plan.get("action") != "READY_FOR_STAGE" or not plan.get("agreement_id"):
        return 0
    agreement = db.get(CrmAgreement, UUID(str(plan["agreement_id"])))
    if agreement is None or is_historical_unit_change(agreement):
        return 0
    if agreement.status == CrmAgreementStatus.CANCELLED:
        return 0
    meta = agreement.metadata_json if isinstance(agreement.metadata_json, dict) else {}
    if meta.get("relationship_detached"):
        return 0
    if _already_at_target(_shown_stage(agreement)):
        return 0
    set_agreement_stage(agreement, TARGET_STAGE)
    return 1


def apply_ready(db: Session, row: dict[str, object]) -> int:
    if row["classification"] != "READY_TO_LINK":
        return 0
    agreement_ids = [UUID(value) for value in row["agreement_ids"]]  # type: ignore[index]
    if len(agreement_ids) != 1:
        return 0
    linked = _linked_contact_ids(db, db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(agreement_ids))).all())
    written = 0
    for raw_id in row["contact_ids"]:  # type: ignore[index]
        contact_id = UUID(str(raw_id))
        if contact_id in linked:
            continue
        db.add(
            CrmAgreementParticipant(
                agreement_id=agreement_ids[0],
                contact_id=contact_id,
                role="owner",
                ownership_pct=None,
                is_primary=False,
                source="reconcile_sold_units",
            )
        )
        written += 1
    return written


def run(apply: bool, *, set_delivery_stage: bool = False) -> list[dict[str, object]]:
    db = SessionLocal()
    try:
        contacts = db.scalars(select(CrmContact)).all()
        results = [
            classify_row(db, project_label=project, unit=unit, owners=owners, contacts=list(contacts))
            for project, unit, owners in ROWS
        ]
        if set_delivery_stage:
            planned = [plan_delivery_stage(db, row) for row in results]
            if apply:
                for item in planned:
                    apply_delivery_stage(db, item)
                db.commit()
            else:
                db.rollback()
            return planned
        if apply:
            for row in results:
                apply_ready(db, row)
            db.commit()
        else:
            db.rollback()
        return results
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write. Without this flag the run stays a dry run.")
    parser.add_argument(
        "--set-delivery-stage",
        action="store_true",
        help="Plan Ev Teslim Süreci for already-linked sold units. Writes only with --apply.",
    )
    args = parser.parse_args(argv)
    results = run(apply=args.apply, set_delivery_stage=args.set_delivery_stage)
    counts: dict[str, int] = defaultdict(int)
    if args.set_delivery_stage:
        for row in results:
            counts[str(row["action"])] += 1
            print(
                f"{row['action']}\t{row['project']}\t{row['unit']}\t{row['owners']}\t{row['stage_change']}"
            )
        print("TOTAL", len(results))
        for key in _STAGE_ACTIONS:
            print(f"{key} {counts.get(key, 0)}")
    else:
        for row in results:
            counts[str(row["classification"])] += 1
            print(
                f"{row['classification']}\t{row['confidence']}\t{row['project']}\t{row['unit']}\t{row['owners']}"
                f"\tpeople={row.get('people')}\tids={row.get('contact_ids')}"
                f"\tunits={row.get('stored_units')}\tevidence={row.get('evidence')}"
            )
        print("TOTAL", len(results))
        for key in (
            "READY_TO_LINK",
            "ALREADY_LINKED",
            "PERSON_NOT_FOUND",
            "UNIT_NOT_FOUND",
            "AMBIGUOUS_PERSON",
            "MULTIPLE_UNIT_MATCHES",
            "CONFLICT",
        ):
            print(f"{key} {counts.get(key, 0)}")
    print("APPLY" if args.apply else "DRY_RUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
