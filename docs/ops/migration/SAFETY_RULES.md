# G12 Migration — Safety Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Do not invent fake production business data | False go-live confidence |
| 2 | Do not delete demo/production data without validated sources + backup + recon PASS | Irreversible loss |
| 3 | Prefer marking demo (`is_demo`) over wipe when unsafe | Recoverability |
| 4 | Never auto-merge financial records | Ledger integrity |
| 5 | Suggest merges only for non-financial duplicates | Human judgment |
| 6 | No uncontrolled production imports | Blast radius |
| 7 | Local Docker = dry-run environment only | Not production |
| 8 | PASS only with real sources + full recon + workflow UAT | Honest readiness |
| 9 | Mask credentials / account numbers in artifacts | Secret hygiene |
| 10 | Evidence claimed under `artifacts/g12-migration/` must exist on disk | Auditability |

## Financial entities (never auto-merge)

- `financial_accounts`, `finance_transactions`
- `funding_commitments`, `payment_obligations`
- `inventory_reservations` (deposit implications)
- `project_vendor_bills`, `project_payments`
- Budget totals vs workbook (preview/confirm only after recon plan)

## Allowed automated helpers

- CSV dry-run validation
- Duplicate **suggestions**
- FK orphan detection
- Balance **diff reporting** (no auto-adjustment)
