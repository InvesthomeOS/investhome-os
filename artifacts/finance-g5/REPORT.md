# INVESTHOME OS — G5 Finance & Treasury Workspace Report

**Date:** 2026-07-20  
**Verdict:** **PASS** (premium treasury UX aligned with CRM G2 / Investors G3 / Projects G4; LIVE APIs preserved; gaps labeled LIVE / PARTIAL / DEMO — not silently mocked as permanent data)

---

## 1. Preview URL

`http://localhost:3000/dashboard/finance`

Demo login: `superadmin@investhome.demo` / `Demo123!`

Query views: `?view=executive|cash|accounts|wires_in|wires_out|investor_payments|vendor_payments|ar|ap|treasury|forecast|budget|approvals|documents|audit`  
Default (no `view`) = Executive Finance Dashboard.

---

## 2. Implemented routes

| Route | View |
|-------|------|
| `/dashboard/finance` | Executive Finance Dashboard (default) |
| `/dashboard/finance?view=cash` | Cash Position |
| `/dashboard/finance?view=accounts` | Bank Accounts |
| `/dashboard/finance?view=wires_in` | Incoming Wires |
| `/dashboard/finance?view=wires_out` | Outgoing Wires |
| `/dashboard/finance?view=investor_payments` | Investor Payments |
| `/dashboard/finance?view=vendor_payments` | Vendor Payments |
| `/dashboard/finance?view=ar` | Accounts Receivable |
| `/dashboard/finance?view=ap` | Accounts Payable |
| `/dashboard/finance?view=treasury` | Treasury |
| `/dashboard/finance?view=forecast` | Forecast (30/60/90/180/365) |
| `/dashboard/finance?view=budget` | Budget |
| `/dashboard/finance?view=approvals` | Approval Center |
| `/dashboard/finance?view=documents` | Financial Documents |
| `/dashboard/finance?view=audit` | Audit Log |

Primary UX: dense treasury shell + horizontal module nav + right **ops drawer** (account / transaction) + DS SVG charts (line + sparklines + compact bars). CRM, Investors, and Projects workspaces were **not** modified.

---

## 3. Data classification

| Surface | Classification | Source |
|---------|----------------|--------|
| Executive KPIs (cash, available, AR/AP totals, budget, burn, runway, net) | **LIVE** (+ PARTIAL sparklines) | `GET /finance/stats`, accounts, budgets, transactions, obligations |
| Cash Position table | **LIVE** | `GET /finance/accounts` |
| Bank Accounts (multi-entity) | **LIVE** | `GET /finance/accounts` (`ownership_entity`) |
| Budget | **LIVE** | `GET /finance/project-budgets` |
| Financial Documents | **LIVE** | `GET /documents` (`folder=finance` / financial types) |
| AI actions | **LIVE** (existing; null when unavailable) | `ContextualAiActions module="finance"` |
| Incoming / Outgoing Wires | **PARTIAL** | Wire `payment_method` on transactions + obligation mapping — no dedicated rails API |
| Investor Payments | **PARTIAL** | Funding commitments + investor-linked transactions |
| Vendor Payments | **PARTIAL** | Payment obligations (`vendor_payment` etc.); retention estimated |
| AR / AP ledgers | **PARTIAL** | Stats + open transactions / obligations (not full GL) |
| Treasury desk | **PARTIAL** | Derived liquidity/debt; credit lines estimated from available balances |
| Forecast horizons | **PARTIAL** | Derived from commitments, obligations, pending inflows |
| Approval Center | **PARTIAL** | `GET /executive/approvals` + pending/scheduled finance transactions |
| Audit Log | **PARTIAL** | Entity activity when present; else recent transaction update trail |
| KPI sparklines / some trend series | **PARTIAL** | Synthesized for Stripe-like density (values remain LIVE) |

No module is silently presented as permanent mock data. DEMO records surface via existing `is_demo` banners only.

---

## 4. Backend gaps

1. **No first-class wires / bank-rail entities** — wires are derived from `payment_method=wire` + obligation status mapping.
2. **No company-wide AR/AP ledger APIs** — workspace uses finance stats + transactions/obligations (project cost APIs exist but are project-scoped).
3. **No dedicated treasury / credit-facility API** — credit lines estimated from operating/reserve available balances.
4. **No finance forecast engine** — horizons computed client-side from live commitments/obligations/pending inflows.
5. **No finance-native approval inbox** — executive approvals reused + pending transaction queue.
6. **Finance audit page is thin** — activity entity support is sparse; UI falls back to transaction update trail.
7. **Bank sync / reconciliation feeds** — missing (`Last Sync` uses `updated_at`).

Existing `/finance/*` CRUD and permissions were **not** replaced or rewritten.

---

## 5. Test results

| Check | Result |
|-------|--------|
| G5 TypeScript (`src/.../finance/_components/g5`) | Clean (repo has pre-existing unrelated `e2e/project-finance.spec.ts` debt) |
| `next build` (Docker web image) | Success |
| Docker `web` rebuild + recreate | Success (no DB volume delete) |
| Critical view navigation (`.pw-verify/verify-finance-g5.mjs`) | **15/15 views passed** (nav click + active state) when stack healthy |
| TR / EN locale | Supported via `investhome.locale` + language select; screenshots `17-turkish.png` (TR) and `18-english.png` (EN) |
| Playwright `e2e/finance-g5.spec.ts` | Spec authored; host verification via `.pw-verify` (same pattern as G3/G4) |

---

## 6. Screenshot paths (verified on disk)

Absolute dir: `C:\Users\eminb\Projects\investhome-os\artifacts\finance-g5`

Independent listing confirmation: **18/18 PNG present, each >10KB** (`sizes-verified.json`).

| # | File | Size (bytes) |
|---|------|-------------:|
| 1 | `artifacts/finance-g5/01-executive-dashboard.png` | 153344 |
| 2 | `artifacts/finance-g5/02-cash-position.png` | 131937 |
| 3 | `artifacts/finance-g5/03-bank-accounts.png` | 133944 |
| 4 | `artifacts/finance-g5/04-incoming-wires.png` | 135709 |
| 5 | `artifacts/finance-g5/05-outgoing-wires.png` | 148106 |
| 6 | `artifacts/finance-g5/06-investor-payments.png` | 135760 |
| 7 | `artifacts/finance-g5/07-vendor-payments.png` | 147825 |
| 8 | `artifacts/finance-g5/08-ar.png` | 130455 |
| 9 | `artifacts/finance-g5/09-ap.png` | 144083 |
| 10 | `artifacts/finance-g5/10-treasury.png` | 144066 |
| 11 | `artifacts/finance-g5/11-forecast.png` | 134575 |
| 12 | `artifacts/finance-g5/12-budget.png` | 127113 |
| 13 | `artifacts/finance-g5/13-approvals.png` | 136973 |
| 14 | `artifacts/finance-g5/14-documents.png` | 124913 |
| 15 | `artifacts/finance-g5/15-audit.png` | 139305 |
| 16 | `artifacts/finance-g5/16-tablet.png` | 129696 |
| 17 | `artifacts/finance-g5/17-turkish.png` | 150773 |
| 18 | `artifacts/finance-g5/18-english.png` | 113866 |

Capture tooling: `.pw-verify/capture-finance-g5.mjs` (+ i18n helper) using absolute paths via `import.meta.url`.

---

## 7. Limitations

- Sparkline / some trend series are synthesized for density; KPI amounts remain LIVE.
- Vendor retention is a UI estimate (5%), not a backend retainage field on finance obligations.
- Horizontal module nav requires scroll on narrower viewports (tablet screenshot covers responsive shell).
- Docker web (no bind mounts) must be rebuilt to pick up source changes; intermittent container flakiness observed under rapid Playwright restarts — unrelated to finance API contracts.
- Chart mix bars can look sparse when collections/burn are zero in seed data.

---

## 8. Verdict

**PASS** — Finance workspace is visually in the same product family as G2–G4 (IBM Plex, warm light surfaces, dense KPI strip, LIVE/PARTIAL tags), uses existing finance APIs without backend rewrites, and ships verified screenshots on disk under `artifacts/finance-g5/`.

**Do not start the next workspace until visual approval of G5.**
