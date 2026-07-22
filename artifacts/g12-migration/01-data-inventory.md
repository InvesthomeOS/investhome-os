# Phase 1 — Data Inventory

**Verdict:** Real external sources **MISSING**. Demo seed + partial CSV import tooling **PRESENT**.

| Source | Owner | Location | Est count | Quality | Duplicates | Risk | Import difficulty | Status |
|--------|-------|----------|-----------|---------|------------|------|-------------------|--------|
| Salesforce / legacy CRM | Sales (TBD) | NOT PROVIDED | unknown | unknown | high | high | medium | MISSING |
| HubSpot / marketing | Marketing (TBD) | NOT PROVIDED | unknown | unknown | high | medium | low (CRM API exists) | MISSING |
| QuickBooks / ledger | Finance (TBD) | NOT PROVIDED | unknown | unknown | critical if merged | **critical** | high | MISSING |
| Bank statements | Controller (TBD) | NOT PROVIDED | unknown | unknown | n/a | **critical** | high | MISSING |
| Drive/SharePoint docs | Ops/Legal (TBD) | NOT PROVIDED | unknown | unknown | medium | high | medium | MISSING |
| Excel unit inventory | Projects (TBD) | NOT PROVIDED | unknown | unknown | high | high | high (bulk import deferred) | MISSING |
| Investor + commitments | IR (TBD) | NOT PROVIDED | unknown | unknown | medium | critical | high | MISSING |
| Vendor + open AP | Finance (TBD) | NOT PROVIDED | unknown | unknown | medium | high | high | MISSING |
| Staff user roster | IT (TBD) | NOT PROVIDED | unknown | unknown | low | high (ACL) | low | MISSING |
| Demo seed | Engineering | `apps/api/.../db/seed*` + `db/demo/*` | see dry-run JSON | synthetic | intentional | must not be production | n/a | PRESENT (DEMO) |
| CSV import APIs | Engineering | CRM/companies/branches/budgets | tooling | production-capable non-ledger | mode-dependent | medium w/o dry-run | low–medium | PRESENT |

## Filesystem scan (2026-07-20)

- `data/` directory: **does not exist**
- `.csv` / `.xlsx` under `data/`, `docs/`, `artifacts/`: **none** (business extracts)
- Templates later written under `artifacts/g12-migration/templates/` are **empty headers**, not data

## Connected DB snapshot (local Docker — DEMO ONLY)

See `dry-run/demo-entity-inventory.json` and `dry-run/demo-counts.json`.

Highlights: users 11 (all demo), leads 21, investors 13, CRM contacts 25, projects 14, inventory 31, financial accounts 1 (balance sum 500000.00 demo), finance transactions 3, documents 7.

**These are not production counts.**
