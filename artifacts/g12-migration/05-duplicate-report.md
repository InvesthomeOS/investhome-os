# Phase 5 — Duplicate Report & Cleaning Plan

**Policy:** Suggest merges for non-financial entities only. **NEVER auto-merge financials.**

## Actions

| Entity class | Detection | Action |
|--------------|-----------|--------|
| CRM contacts | same `primary_email` | Suggest merge — operator confirms |
| CRM companies | same normalized `name` | Suggest merge |
| Leads / investors | email or name+phone | Suggest link/merge |
| Projects | same `project_code` | Reject duplicate import |
| Inventory assets | project+asset_code | Reject duplicate |
| Finance transactions | date+amount+account+type | **Review only — never auto-merge** |
| Commitments / bills / payments / reservations | external_ref or amount signatures | **Review only — never auto-merge** |

## Demo DB

Run:

```bash
docker compose exec api python -m investhome_api.migration.cli duplicates
```

Output: `dry-run/duplicates.json`.

Any financial groups must remain in a **reject / manual queue**, not an auto-merge pipeline.

## Cleaning steps (when real sources arrive)

1. Normalize emails/phones/codes in staging workbooks
2. Produce merge suggestion CSV for CRM
3. Finance team resolves ledger duplicates offline
4. Re-run dry-run until rejects cleared
5. Import — still no financial auto-merge code paths
