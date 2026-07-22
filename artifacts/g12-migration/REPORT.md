# G12 Controlled Real Data Migration — REPORT

**Date:** 2026-07-20  
**Environment tested:** Local Docker (`API_ENVIRONMENT=development`) — **dry-run only**  
**Real production source files available:** **NO**  
**Go-live recommendation:** **REVISION REQUIRED** (NOT READY FOR REAL GO-LIVE)

---

## Executive verdict

Migration **tooling, mapping templates, runbooks, and demo dry-run** are in place.  
**No real Salesforce/HubSpot/QuickBooks/Drive/Excel business extracts** were found in the repo or provided paths.  
Therefore this phase **cannot** claim production data migration PASS. Demo data remains demo. Financial reconciliation against banks/ledgers is **blocked**.

---

## Imported record counts

| Entity | Imported (real) | In connected DB (demo) | Notes |
|--------|----------------:|-----------------------:|-------|
| Users | 0 | 11 | all demo |
| Leads | 0 | 21 | demo |
| Investors | 0 | 13 | demo |
| CRM contacts | 0 | 25 | demo |
| CRM companies | 0 | 12 | demo |
| Projects | 0 | 14 | demo |
| Buildings / floors / assets | 0 | 6 / 14 / 31 | demo |
| Reservations | 0 | 5 | demo |
| Financial accounts | 0 | 1 | demo balance sum 500000.00 |
| Finance transactions | 0 | 3 | demo |
| Funding commitments | 0 | 0 | — |
| Payment obligations | 0 | 3 | demo |
| Documents | 0 | 7 | demo placeholders |

**Real imported total: 0.**

---

## Rejected records

| Source | Rejected | Reason |
|--------|----------|--------|
| — | 0 | No real source files submitted to dry-run importer |

Template dry-run with empty headers only → `no_source` per entity (`dry-run/import-dry-run.json` after CLI run).

---

## Duplicate report

- Policy: non-financial **suggest_merge**; financial **never_auto_merge**
- Tooling: `investhome-migrate duplicates` → `dry-run/duplicates.json`
- No production duplicate remediation performed (no real import)

---

## Financial reconciliation

| Check | Status |
|-------|--------|
| Demo FK integrity (txn→account, reservation→asset) | PASS (demo only) |
| Bank balance vs statements | **BLOCKED** — no statements |
| Invoices / AP | **BLOCKED** |
| Reservations / deposits | **BLOCKED** |
| Contracts amounts | **BLOCKED** |
| Investor payments / commitments | **BLOCKED** |
| Vendor payments | **BLOCKED** |
| Budgets | **BLOCKED** |
| Cash position | **BLOCKED** |

**Financial recon: INCOMPLETE.**

---

## Document reconciliation

**NOT RUN** — no document export + checksum manifest provided.  
Plan: `06-document-import-plan.md`.

---

## Permission validation

**NOT COMPLETE for real users** — no staff roster.  
Demo RBAC seed exists (11 roles). Procedure: `08-user-onboarding.md`.

---

## User onboarding

**PROCEDURE DOCUMENTED ONLY.**  
Do not onboard `*@investhome.demo` as production. MFA fields exist on `User`; enforce via admin auth settings when real users arrive.

---

## Workflow validation

**DRY-RUN ON DEMO** — chain partially populated in seed; finance/commitment story weak; **not** accepted as production UAT.  
See `09-workflow-validation.md`.

---

## Open issues

1. **Blocker:** All critical source files missing — see `SOURCE_FILES_CHECKLIST.md`
2. **Blocker:** Financial recon cannot complete
3. **Blocker:** Document corpus absent
4. **Blocker:** Real user/role assignments absent
5. Inventory **product** bulk import still deferred — migration templates/CLI are the interim path
6. DOMAIN_MODEL.md still marks some inventory pieces “planned” while code has buildings/floors/assets — doc drift
7. No Salesforce/HubSpot/QB connectors — CSV/manual extracts required
8. Admin migration console UI **not** added (intentionally) to avoid conflicting with launch-health; CLI + artifacts preferred

---

## Migration report (what shipped)

| Deliverable | Path |
|-------------|------|
| Migration package | `apps/api/src/investhome_api/migration/` |
| CLI | `python -m investhome_api.migration.cli` / `investhome-migrate` |
| Runbooks | `docs/ops/migration/` |
| Mapping JSON/MD | `03-field-mapping.json`, `03-field-mapping.md` |
| CSV templates | `templates/*.csv` (headers only) |
| Demo counts / integrity | `dry-run/*.json` |
| Source checklist | `SOURCE_FILES_CHECKLIST.md` |

---

## Operational readiness

| Area | Ready? |
|------|--------|
| Schema / API target | Yes |
| Demo environment for rehearsal | Yes (Docker) |
| Controlled import dry-run tooling | Yes |
| Real data loaded | **No** |
| Finance certified | **No** |
| Production permissions | **No** |
| Demo quarantined after real cutover | **N/A** (cutover not done) |

---

## Go-live recommendation

# REVISION REQUIRED

**NOT READY FOR REAL GO-LIVE.**

**PASS criteria not met:** real production data workflows, financial recon, permissions, document integrity.

**Next approval gate:** Provide files in `SOURCE_FILES_CHECKLIST.md`, re-run dry-run + reconcile, then request G12 re-evaluation. **Do not start the next phase** until this report is approved.

---

## Honesty statement

No fake production dataset was invented or labeled as migrated. Local demo counts are explicitly marked demo / dry-run. Evidence files under `artifacts/g12-migration/` are listed in `evidence/listing.txt`.
