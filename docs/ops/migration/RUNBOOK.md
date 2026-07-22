# G12 Migration Runbook — Controlled Real Data Cutover

**Status:** Tooling ready · **Real go-live: NOT READY** until source checklist is complete and reconciliation PASSes.

**Safety (non-negotiable):**
1. No blind imports into production.
2. Never invent “production” data.
3. Never auto-merge financial records (payments, contracts, bank balances, commitments, bills).
4. Prefer staging / local Docker dry-run. Local Docker ≠ production go-live.
5. Demo rows stay marked `is_demo` / `integrated_demo_seed` until real import + recon succeeds.
6. Prefer marking demo over destructive wipe if wipe is unsafe.
7. Never print secrets; mask account numbers in logs.

---

## Prerequisites

- Docker stack healthy (`postgres`, `api`) **or** staging API with DB access
- Operator with admin / finance authority
- Completed [SOURCE_FILES_CHECKLIST.md](../../../artifacts/g12-migration/SOURCE_FILES_CHECKLIST.md)
- Backup of target DB taken and verified restorable

## Commands

```bash
# From apps/api (or via docker compose exec api)
python -m investhome_api.migration.cli templates
python -m investhome_api.migration.cli mapping-md
python -m investhome_api.migration.cli inventory --with-db
python -m investhome_api.migration.cli dry-run --sources ../../data/migration-sources
python -m investhome_api.migration.cli duplicates
python -m investhome_api.migration.cli reconcile
```

Console entrypoint (after install): `investhome-migrate <command>`.

## Cutover sequence (when real sources exist)

1. **Inventory** — confirm every source file on checklist; owners sign off quality.
2. **Map** — fill source-specific columns into templates; run `mapping-md` / JSON review.
3. **Quality audit** — duplicates, missing required fields, currency, dates, orphan FKs.
4. **Clean** — merge **non-financial** duplicates only after human approval; queue financials for manual review.
5. **Dry-run import** — `dry-run --sources …` must show `rejected=0` for critical entities.
6. **Staging commit** — import non-financial masters first (users→org→projects→CRM→inventory), then documents, then finance with recon gates.
7. **Financial reconciliation** — bank, invoices, reservations, commitments, obligations, budgets, cash — **zero unexplained diffs**.
8. **Document recon** — checksum + link targets.
9. **User onboarding** — real users only; force password reset; enable MFA if supported.
10. **Workflow UAT** — Lead → Opportunity → Reservation → Contract/docs → Payment → Portal on **real** data.
11. **Go-live gate** — counts, permissions, search, reports, dashboards, AI, exports.
12. **Demo quarantine** — only after PASS: mark or remove demo rows per cleanup policy (`investhome-demo` cleanup is demo-only).

## Abort criteria

- Any financial recon FAIL
- Critical orphan relationships
- Permission gaps for production roles
- Missing bank / AP / commitment source files
- Attempt to treat demo DB as production PASS

## Related artifacts

- `artifacts/g12-migration/REPORT.md` — executive verdict
- `docs/ops/migration/SAFETY_RULES.md`
- `docs/ops/migration/CUTOVER_CHECKLIST.md`
