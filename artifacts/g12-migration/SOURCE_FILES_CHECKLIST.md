# G12 — Source Files Checklist (REQUIRED for real go-live)

**Current status: INCOMPLETE — no real business extracts found in repo.**

Provide the following under `data/migration-sources/` (gitignored recommended for PII) or a secure share path documented here.

| # | Source file | Format | Owner | Est. rows | Received? | Notes |
|---|-------------|--------|-------|-----------|-----------|-------|
| 1 | CRM contacts export | CSV/XLSX | Sales | | NO | Email required |
| 2 | CRM companies export | CSV/XLSX | Sales | | NO | |
| 3 | Leads / pipeline export | CSV/XLSX | Sales | | NO | Stage mapping needed |
| 4 | Investors roster | CSV/XLSX | IR | | NO | Profile only |
| 5 | Funding commitments | CSV/XLSX | Finance/IR | | NO | FINANCIAL |
| 6 | Projects master | CSV/XLSX | Projects | | NO | Codes unique |
| 7 | Buildings / floors / units | CSV/XLSX | Projects/Sales | | NO | Inventory bulk API deferred — use migration templates |
| 8 | Active reservations + deposits | CSV/XLSX | Sales/Finance | | NO | FINANCIAL |
| 9 | Chart of accounts / bank accounts | CSV + statements | Finance | | NO | Balances must match |
| 10 | General ledger / transactions (QB or bank) | CSV | Finance | | NO | FINANCIAL — never auto-merge |
| 11 | Open AP (vendor bills) | CSV | Finance | | NO | FINANCIAL |
| 12 | Vendor payments | CSV | Finance | | NO | FINANCIAL |
| 13 | Payment obligations / schedules | CSV | Finance | | NO | FINANCIAL |
| 14 | Project budgets workbook | CSV/XLSX | Finance/PM | | NO | Use budget preview/confirm |
| 15 | Document store export + SHA256 manifest | ZIP + CSV | Ops/Legal | | NO | Preserve metadata |
| 16 | Staff users + role assignment | CSV | IT/Admin | | NO | Real emails; MFA plan |
| 17 | Vendor master | CSV | Procurement | | NO | |

## Acceptance of a “received” file

- [ ] Header maps to `artifacts/g12-migration/templates/*.csv` or documented custom map
- [ ] PII handling agreed
- [ ] Row count recorded
- [ ] Sample of 10 rows validated manually
- [ ] Finance files accompanied by independent bank/AP totals for recon

## What exists today (NOT production sources)

| Item | Location | Quality |
|------|----------|---------|
| Demo seed | `apps/api/src/investhome_api/db/**` | Synthetic |
| Empty CSV templates | `artifacts/g12-migration/templates/` | Headers only |
| CRM/company/branch/budget CSV APIs | `apps/api` + web import pages | Tooling |
| Local Docker DB | compose `postgres` | Demo data |

**Until every CRITICAL finance + CRM + inventory + users row above is Received=YES, go-live recommendation remains REVISION REQUIRED.**
