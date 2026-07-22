"""Source inventory helpers and DB snapshot for G12."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session


@dataclass
class SourceInventoryRow:
    source_name: str
    owner: str
    location: str
    est_count: str
    quality: str
    duplicates_risk: str
    risk: str
    import_difficulty: str
    status: str


KNOWN_EXTERNAL_SOURCES: list[SourceInventoryRow] = [
    SourceInventoryRow(
        "Salesforce / legacy CRM export",
        "Sales / Ops owner (TBD)",
        "NOT PROVIDED — need .csv/.xlsx export",
        "unknown",
        "unknown",
        "high (email/phone)",
        "high — relationship loss",
        "medium (map stages)",
        "MISSING",
    ),
    SourceInventoryRow(
        "HubSpot / marketing contacts",
        "Marketing owner (TBD)",
        "NOT PROVIDED",
        "unknown",
        "unknown",
        "high",
        "medium",
        "low (CRM import exists)",
        "MISSING",
    ),
    SourceInventoryRow(
        "QuickBooks / accounting ledger",
        "Finance owner (TBD)",
        "NOT PROVIDED — bank + AP/AR exports required",
        "unknown",
        "unknown",
        "critical if merged blindly",
        "critical — financial integrity",
        "high (never auto-merge)",
        "MISSING",
    ),
    SourceInventoryRow(
        "Bank statements / balances",
        "Finance / Controller (TBD)",
        "NOT PROVIDED",
        "unknown",
        "unknown",
        "n/a",
        "critical — recon blocker",
        "high",
        "MISSING",
    ),
    SourceInventoryRow(
        "Google Drive / SharePoint documents",
        "Ops / Legal (TBD)",
        "NOT PROVIDED — need folder export + manifest",
        "unknown",
        "unknown",
        "medium (filename collisions)",
        "high — contract loss",
        "medium",
        "MISSING",
    ),
    SourceInventoryRow(
        "Excel project / unit inventory workbooks",
        "Projects / Sales (TBD)",
        "NOT PROVIDED",
        "unknown",
        "unknown",
        "high (unit codes)",
        "high — sales blockers",
        "high (bulk import deferred in product)",
        "MISSING",
    ),
    SourceInventoryRow(
        "Investor roster + commitments",
        "Investor relations (TBD)",
        "NOT PROVIDED",
        "unknown",
        "unknown",
        "medium",
        "critical for capital",
        "high (financial commitments)",
        "MISSING",
    ),
    SourceInventoryRow(
        "Vendor master + open AP",
        "Finance / Procurement (TBD)",
        "NOT PROVIDED",
        "unknown",
        "unknown",
        "medium",
        "high",
        "high",
        "MISSING",
    ),
    SourceInventoryRow(
        "Staff user roster (HR)",
        "Admin / IT (TBD)",
        "NOT PROVIDED — real emails + roles",
        "unknown",
        "unknown",
        "low",
        "high — access control",
        "low",
        "MISSING",
    ),
    SourceInventoryRow(
        "Investhome OS demo seed (local Docker)",
        "Engineering",
        "apps/api/src/investhome_api/db/seed*.py + db/demo/*",
        "see demo inventory JSON",
        "synthetic demo (is_demo / integrated_demo_seed)",
        "intentional demo overlap possible",
        "must not be treated as production",
        "n/a — already loaded",
        "PRESENT (DEMO ONLY)",
    ),
    SourceInventoryRow(
        "Existing CSV import APIs (CRM/companies/branches/budgets)",
        "Engineering",
        "apps/api services + web import pages",
        "n/a tooling",
        "production-capable for non-ledger CSV",
        "handled by import modes",
        "medium if used without dry-run",
        "low–medium",
        "PRESENT (TOOLING)",
    ),
]


def scan_filesystem_sources(roots: list[Path]) -> dict[str, Any]:
    found: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.csv", "*.xlsx", "*.xls", "*.tsv"):
            for path in root.rglob(pattern):
                # skip node_modules / .git noise
                parts = set(path.parts)
                if "node_modules" in parts or ".git" in parts:
                    continue
                found.append(str(path))
    return {
        "scanned_roots": [str(r) for r in roots],
        "files": found,
        "count": len(found),
        "real_business_extracts_confirmed": False,
        "note": (
            "Any CSV under artifacts/g12-migration/templates are EMPTY HEADER TEMPLATES, "
            "not production data. Do not treat templates as migrated sources."
        ),
    }


def collect_db_snapshot(db: Session) -> dict[str, Any]:
    """Best-effort entity counts for the connected database."""
    from investhome_api.models.crm_activity import CrmActivity
    from investhome_api.models.crm_company import CrmCompany
    from investhome_api.models.crm_contact import CrmContact
    from investhome_api.models.document import Document
    from investhome_api.models.finance import (
        FinanceTransaction,
        FinancialAccount,
        FundingCommitment,
        PaymentObligation,
    )
    from investhome_api.models.inventory import (
        Building,
        Floor,
        InventoryAsset,
        InventoryReservation,
    )
    from investhome_api.models.investor import Investor
    from investhome_api.models.lead import Lead
    from investhome_api.models.project import Project
    from investhome_api.models.sales import SalesOpportunity
    from investhome_api.models.user_auth import User

    def count(model) -> int:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    def count_demo(model) -> int | None:
        if not hasattr(model, "is_demo"):
            return None
        return int(
            db.scalar(select(func.count()).select_from(model).where(model.is_demo.is_(True))) or 0
        )

    entities = {
        "users": User,
        "leads": Lead,
        "investors": Investor,
        "crm_contacts": CrmContact,
        "crm_companies": CrmCompany,
        "crm_activities": CrmActivity,
        "sales_opportunities": SalesOpportunity,
        "projects": Project,
        "buildings": Building,
        "floors": Floor,
        "inventory_assets": InventoryAsset,
        "inventory_reservations": InventoryReservation,
        "financial_accounts": FinancialAccount,
        "finance_transactions": FinanceTransaction,
        "funding_commitments": FundingCommitment,
        "payment_obligations": PaymentObligation,
        "documents": Document,
    }
    snapshot: dict[str, Any] = {}
    for key, model in entities.items():
        demo = count_demo(model)
        entry: dict[str, Any] = {"total": count(model)}
        if demo is not None:
            entry["demo_marked"] = demo
        snapshot[key] = entry

    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "entities": snapshot,
        "warning": (
            "These counts reflect the CONNECTED database (typically local demo). "
            "They are NOT production go-live counts."
        ),
    }


def build_inventory_document(*, fs_scan: dict[str, Any], db_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "phase": 1,
        "title": "DATA INVENTORY",
        "sources": [asdict(s) for s in KNOWN_EXTERNAL_SOURCES],
        "filesystem_scan": fs_scan,
        "connected_db_snapshot": db_snapshot,
        "verdict": (
            "REVISION REQUIRED — no validated real business source extracts located. "
            "Only demo seed + import tooling present."
        ),
    }
