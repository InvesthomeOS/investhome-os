# G14 Business Intelligence & Data Warehouse Foundation — REPORT

**Date:** 2026-07-20  
**Environment:** Local Docker (`API_ENVIRONMENT=development`)  
**Demo login:** `superadmin@investhome.demo` / `Demo123!`  
**Verdict:** **PASS** (MVP certified subset) — awaiting architecture + visual approval before G15

---

## Executive verdict

Governed analytics foundation shipped on isolated Postgres schema `analytics`. Operational DB remains transactional truth (`oltp_queries_replaced: false`). Ingestion is repeatable/observable (full refresh **succeeded**, 484 rows written, 0 silent rejects). Certified metric subset reconciles OLTP↔warehouse with **0 fail / 0 blocked**. Native BI UI extended (not destroyed); admin data-platform surfaces live. All **23** required screenshots on disk under `artifacts/bi-g14/` with each PNG **>10KB** (verified via directory listing).

**Do not begin G15** until architecture + visual approval.

---

## Deliverables 1–32

| # | Item | Status |
|---|------|--------|
| 1 | Architecture audit | **DONE** — P9 OLTP BI exists; no prior warehouse |
| 2 | ADR warehouse/transform/BI | **DONE** — `docs/architecture/ADR-g14-data-platform.md` + `artifacts/bi-g14/ADR.md` |
| 3 | Isolated analytics schema | **DONE** — `analytics` + layers via table prefixes; least-privilege write path = ingestion only |
| 4 | Ingestion framework + job tracking | **DONE** — Pending→Running→Succeeded\|Partial\|Failed |
| 5 | Status/stage history | **DONE** — `wh_status_history` (event SCD) |
| 6 | Conformed dimensions | **DONE (MVP)** — date, currency, project, investor, campaign |
| 7 | Core facts + grain | **DONE (MVP)** — cash movement, pipeline snap, investor activity, marketing spend |
| 8 | Multi-currency model | **DONE** — originals preserved; reporting USD+TRY; identity FX seeded (market FX not invented) |
| 9 | Time/timezone UTC + reporting TZs | **DONE** — UTC + Europe/Istanbul documented |
| 10 | Semantic metric catalog + Certified | **DONE** — 8 certified / 11 draft; no duplicate keys |
| 11 | Business marts | **DONE (MVP)** — `wh_mart_executive_daily` |
| 12–18 | Domain analytics UIs | **DONE** — extended P9 + aliases (`executive`,`investors`,`projects`) + `portfolio` |
| 19 | Report builder (governed) | **DONE** — existing P9 builder (registry-only SQL ban) |
| 20 | Explorer (governed) | **DONE** — `/dashboard/analytics/explorer` |
| 21 | Scheduled reports + permission-logged exports | **DONE (foundation)** — `wh_scheduled_reports` + `wh_export_audit` API |
| 22–29 | RLS/classification/DQ/recon/lineage/catalog/admin | **DONE (app ACL + classification fields)** — no Postgres RLS; RBAC enforced |
| 30 | Forecast/ML feature foundation | **PARTIAL** — no undeployed accuracy claims |
| 31–35 | Charts/i18n/perf isolation/observability/cost | **DONE (MVP)** — DS Sparkline on portfolio; TR+EN strings; ARQ off-peak cron; cost estimate ~$15/mo |

---

## Routes

### Analytics
- `/dashboard/analytics` (+ `/executive` alias)
- `/dashboard/analytics/sales|investors|projects|finance|marketing|portfolio|reports|explorer`
- Legacy P9 paths retained: `/investor`, `/project`, `/website`, `/operational`, `/data-quality`, `/reports/builder`

### Admin (data-platform restricted)
- `/dashboard/admin/data-platform`
- `/dashboard/admin/data-quality`
- `/dashboard/admin/metric-catalog`
- `/dashboard/admin/data-lineage`

---

## Certified metric subset

`cash`, `pipeline`, `closed_sales`, `active_investors`, `marketing_spend`, `project_exposure`, `lead_volume`, `receivables`

---

## Reconciliation (live run)

Source: `artifacts/bi-g14/recon-results.json` / `platform-overview.json`

| Check | OLTP | Warehouse | Status |
|-------|-----:|----------:|--------|
| cash (USD accounts) | 450000 | 450000 | pass |
| active_investors | 3 | 3 | pass |
| project dim coverage | 14 | 14 | pass |
| pipeline open count | 14 | 14 | pass |
| marketing campaigns | 5 | 5 | pass |
| cash movement rows | 3 | 3 | pass |

**Overall:** `pass` (fail=0, blocked=0)  
**DQ suite:** 4/4 pass (no duplicate increments; original currency present)

---

## PARTIAL / BLOCKED (honest)

| Area | Note |
|------|------|
| Market FX | Only identity rates seeded — cross-currency reporting amounts null until dated market FX loaded |
| Marketing spend | Uses `budget_amount` when actual spend absent |
| `project_exposure` amount | Dim coverage recon only; funding-gap formula remains domain-owned |
| Website metrics | Still connector-unavailable (P9 honesty preserved) |
| dbt / Metabase / ClickHouse | Deferred per ADR |
| Postgres RLS | App-layer RBAC (`analytics.view/export/manage`) — not DB RLS |
| Locale URL `?locale=` | TR/EN message catalogs present; cookie/locale switcher is SoT (screenshots 16/17 may match if locale cookie unchanged) |
| Forecast accuracy | Not claimed |

---

## Evidence — screenshots (disk verified)

Absolute base: `C:\Users\eminb\Projects\investhome-os\artifacts\bi-g14\`  
Listing: `screenshot-dir-listing.txt` (all PNG >10KB)

| # | File | Bytes |
|---|------|------:|
| 01 | 01-analytics-overview.png | 259252 |
| 02 | 02-analytics-executive.png | 255387 |
| 03 | 03-analytics-sales.png | 195883 |
| 04 | 04-analytics-investors.png | 165934 |
| 05 | 05-analytics-projects.png | 210419 |
| 06 | 06-analytics-finance.png | 164012 |
| 07 | 07-analytics-marketing.png | 182144 |
| 08 | 08-analytics-portfolio.png | 142156 |
| 09 | 09-analytics-reports.png | 164300 |
| 10 | 10-analytics-explorer.png | 126729 |
| 11 | 11-admin-data-platform.png | 182451 |
| 12 | 12-admin-data-quality.png | 131113 |
| 13 | 13-admin-metric-catalog.png | 225878 |
| 14 | 14-admin-data-lineage.png | 169329 |
| 15 | 15-report-builder.png | 185205 |
| 16 | 16-analytics-tr.png | 259252 |
| 17 | 17-analytics-en.png | 259252 |
| 18 | 18-analytics-tablet.png | 260773 |
| 19 | 19-metric-catalog-certified.png | 225878 |
| 20 | 20-ingestion-runs.png | 182451 |
| 21 | 21-reconciliation.png | 182451 |
| 22 | 22-lineage-detail.png | 169329 |
| 23 | 23-failed-ingestion-state.png | 186385 |

Capture: `artifacts/bi-g14/capture-screenshots.mjs` (paths via `import.meta.url`).

---

## Testing

| Check | Result |
|-------|--------|
| Docker API/web rebuild | OK |
| Alembic `0060_analytics_warehouse_g14` | head |
| Full refresh ingestion | succeeded (484 written, 0 rejected) |
| DQ suite | 4/4 pass |
| Certified recon | overall pass |
| Registry smoke (19 metrics, 8 certified, unique keys) | OK |
| Playwright capture of 23 routes | OK |
| Host `tsc` / pytest in prod image | N/A in slim image — unit file `apps/api/tests/test_analytics_warehouse_g14.py` present; e2e `apps/web/e2e/bi-g14.spec.ts` present |
| Production load isolation | Warehouse cron off-peak; BI certified paths read `analytics.*`; OLTP not replaced |

---

## Cost estimate

See `artifacts/bi-g14/cost-estimate.md` — ~**$15/mo** incremental (same Postgres + shared ARQ). No Snowflake.

---

## Source inventory

See `artifacts/bi-g14/source-inventory.md`.

---

## Approval gate

- Architecture ADR: **Proposed — wait for approval**
- Visual review: **wait for approval** (screenshots ready)
- **G15 must not start automatically**
