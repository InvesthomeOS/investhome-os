"""Duplicate detection helpers — suggest merges; never auto-merge financials."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.migration.mapping_registry import CANONICAL_ENTITIES

SuggestAction = Literal["suggest_merge", "review_only", "never_auto_merge"]


@dataclass
class DuplicateGroup:
    entity: str
    match_key: str
    match_type: str
    record_ids: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    action: SuggestAction = "suggest_merge"
    reason: str = ""


def _financial_keys() -> set[str]:
    return {e.key for e in CANONICAL_ENTITIES if e.financial_class == "financial"}


def suggest_contact_duplicates(db: Session) -> list[DuplicateGroup]:
    from collections import defaultdict

    from investhome_api.models.crm_contact import CrmContact

    by_email: dict[str, list] = defaultdict(list)
    for c in db.scalars(select(CrmContact)).all():
        if c.primary_email:
            by_email[c.primary_email.strip().lower()].append(c)

    groups: list[DuplicateGroup] = []
    for email, rows in by_email.items():
        if len(rows) < 2:
            continue
        groups.append(
            DuplicateGroup(
                entity="crm_contacts",
                match_key=email,
                match_type="email",
                record_ids=[str(r.id) for r in rows],
                labels=[r.display_name for r in rows],
                action="suggest_merge",
                reason="Same primary_email — suggest manual merge (non-financial)",
            )
        )
    return groups


def suggest_company_duplicates(db: Session) -> list[DuplicateGroup]:
    from collections import defaultdict

    from investhome_api.models.crm_company import CrmCompany

    by_name: dict[str, list] = defaultdict(list)
    for c in db.scalars(select(CrmCompany)).all():
        name = (c.display_name or "").strip().lower()
        if name:
            by_name[name].append(c)

    groups: list[DuplicateGroup] = []
    for name, rows in by_name.items():
        if len(rows) < 2:
            continue
        groups.append(
            DuplicateGroup(
                entity="crm_companies",
                match_key=name,
                match_type="display_name",
                record_ids=[str(r.id) for r in rows],
                labels=[r.display_name for r in rows],
                action="suggest_merge",
                reason="Same company name — suggest manual merge (non-financial)",
            )
        )
    return groups


def flag_financial_near_duplicates(db: Session) -> list[DuplicateGroup]:
    """Flag potential financial duplicates for human review — NEVER recommend auto-merge."""
    from collections import defaultdict

    from investhome_api.models.finance import FinanceTransaction

    by_sig: dict[str, list] = defaultdict(list)
    for t in db.scalars(select(FinanceTransaction)).all():
        sig = f"{t.transaction_date}|{t.amount}|{t.account_id}|{t.transaction_type}"
        by_sig[sig].append(t)

    groups: list[DuplicateGroup] = []
    for sig, rows in by_sig.items():
        if len(rows) < 2:
            continue
        groups.append(
            DuplicateGroup(
                entity="finance_transactions",
                match_key=sig,
                match_type="date+amount+account+type",
                record_ids=[str(r.id) for r in rows],
                labels=[(r.description or "")[:80] for r in rows],
                action="never_auto_merge",
                reason=(
                    "Possible duplicate ledger lines — MANUAL REVIEW ONLY. "
                    "Do not auto-merge payments/transactions."
                ),
            )
        )
    return groups


def collect_duplicate_report(db: Session) -> dict[str, Any]:
    groups = (
        suggest_contact_duplicates(db)
        + suggest_company_duplicates(db)
        + flag_financial_near_duplicates(db)
    )
    financial = _financial_keys()
    return {
        "policy": {
            "non_financial": "suggest_merge only — operator confirms",
            "financial": "never_auto_merge — review_only",
            "financial_entities": sorted(financial),
        },
        "groups": [asdict(g) for g in groups],
        "counts": {
            "total_groups": len(groups),
            "suggest_merge": sum(1 for g in groups if g.action == "suggest_merge"),
            "never_auto_merge": sum(1 for g in groups if g.action == "never_auto_merge"),
        },
    }
