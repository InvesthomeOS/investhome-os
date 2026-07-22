# INVESTHOME OS — G3 Investor Workspace Report

**Date:** 2026-07-20  
**Verdict:** **PASS** (visual + lifecycle + i18n + analytics density meet G3 bar; known backend gaps documented, not silently mocked)

---

## 1. Preview URL

`http://localhost:3000/dashboard/investors`

Demo login: `superadmin@investhome.demo` / `Demo123!`

Query views: `?view=pipeline|list|opportunities|reservations|contracts|payments|closings|portfolio|activity|analytics`

---

## 2. Implemented routes

| Route | View |
|-------|------|
| `/dashboard/investors` | Pipeline (default) |
| `/dashboard/investors?view=list` | Compact list |
| `/dashboard/investors?view=opportunities` | Investment opportunities |
| `/dashboard/investors?view=reservations` | Reservations |
| `/dashboard/investors?view=contracts` | Contracts (stage-derived) |
| `/dashboard/investors?view=payments` | Payments / commitments |
| `/dashboard/investors?view=closings` | Closings |
| `/dashboard/investors?view=portfolio` | Portfolio |
| `/dashboard/investors?view=activity` | Investor activity |
| `/dashboard/investors?view=analytics` | Analytics (full charts) |

Detail UX: right **ops drawer** (not a separate page). CRM routes under `/workspaces/crm` were **not** modified.

---

## 3. Live-data routes

| Surface | Classification | Source |
|---------|----------------|--------|
| Pipeline / List | **LIVE DATA** | `GET/PATCH /investors`, stage via `status` |
| Stats / KPIs (counts, capacity) | **LIVE DATA** | `/investors` + `/investors/stats` |
| Drawer profile fields | **LIVE DATA** | Investor CRUD fields |
| Drawer activity | **LIVE DATA** | `/activity/entity/investor/{id}` |
| Drawer documents | **LIVE DATA** | Entity documents panel |
| Reservations | **LIVE DATA** (when API returns rows) | `/inventory/reservations` |
| Payments | **LIVE DATA** (when API returns rows) | `/finance/funding-commitments`, `/finance/payment-obligations` |
| Opportunities | **LIVE / PARTIAL** | `/sales/opportunities` (prefers `party_type=investor`) |
| AI actions | **LIVE** (existing AI; unavailable state when offline) | Existing Contextual AI |

---

## 4. Demo-data / partial routes

| Surface | Classification | Notes |
|---------|----------------|-------|
| Probability / priority / next action / stage-history notes | **PARTIAL** | localStorage sidecar; gap banner in drawer |
| Contracts | **PARTIAL** | Derived from investor lifecycle stages; no dedicated contracts API |
| Closings | **PARTIAL** | Stage-filtered investors; sales readiness not investor-native |
| Portfolio NAV / yield | **DEMO DATA** | Explicit “demo / labeled” + gap banner; no per-investor portfolio API |
| Analytics trend sparklines | **PARTIAL** | Stage mix & KPIs from live investors; trend series synthesized for density |

---

## 5. Backend gaps

1. **No dedicated probability / expected_investment / priority columns** on Investor — probability persisted client-side; expected close mapped to `next_follow_up_date`; capacity used as investment value.
2. **No investor-native contracts / closings / portfolio holdings APIs** — UI uses stage filters + finance/inventory adjacent APIs.
3. **No structured stage-change note entity** — history in localStorage + OS activity log on status PATCH.
4. **Payment status vocabulary** differs from product enum (Scheduled/Partial/Reconciled) — UI maps finance statuses for display.
5. **Lifecycle enum expanded additively** on VARCHAR status (legacy values retained + mapped). Existing DB rows keep old statuses until updated/reseeded; board maps them.

---

## 6. Test results

| Check | Result |
|-------|--------|
| G3 TypeScript (src investors) | Clean (repo has pre-existing unrelated tsc debt) |
| ESLint G3 files | Pass (warnings cleared) |
| `next build` (host) | Compile OK; standalone symlink EPERM on Windows host |
| Docker `web` + `api` rebuild | Success (no DB volume delete) |
| Playwright `investors-g3.spec.ts` (12 scenarios) | **12/12 passed** |

---

## 7. Screenshot paths

Verified on disk 2026-07-20 (re-captured via `.pw-verify/capture-investors-g3.mjs` against `http://localhost:3000`; all >10KB):

| # | File | Size |
|---|------|------|
| 1 | `artifacts/investors-g3/01-pipeline-desktop.png` | 193,084 bytes |
| 2 | `artifacts/investors-g3/02-list-desktop.png` | 167,105 bytes |
| 3 | `artifacts/investors-g3/03-drawer-open.png` | 214,616 bytes |
| 4 | `artifacts/investors-g3/04-reservations.png` | 116,020 bytes |
| 5 | `artifacts/investors-g3/05-payments.png` | 129,604 bytes |
| 6 | `artifacts/investors-g3/06-portfolio.png` | 130,326 bytes |
| 7 | `artifacts/investors-g3/07-analytics.png` | 142,089 bytes |
| 8 | `artifacts/investors-g3/08-tablet.png` | 130,667 bytes |
| 9 | `artifacts/investors-g3/09-turkish.png` | 193,548 bytes |
| 10 | `artifacts/investors-g3/10-english.png` | 133,589 bytes |

---

## 8. Known limitations

- Probability not server-persisted (clear UI gap).
- Portfolio financials intentionally non-invented.
- 16-column board is dense horizontally (by design; scroll + compact cards).
- English screenshot depends on language control; default locale in Docker is Turkish.
- Host production build may fail on Windows symlink EPERM for standalone output; Docker image build succeeds.

---

## 9. Migration risks

- **Low:** Status stored as VARCHAR (`native_enum=False`); new lifecycle values are additive.
- Legacy statuses (`prospect`, `active`, `invested`, …) remain valid; UI maps them onto board columns.
- Stats endpoint now counts expanded “active” / “invested” stage groups — review any external consumers of those counters.
- Demo seed updated for new stages; existing DBs keep old values until reseed/update (mapping still works).

---

## 10. Final verdict

**PASS**

- Visual language matches approved G1 `github-ui-preview` pipeline quality (IBM Plex, warm surfaces, compact columns/cards, right drawer).
- 16-stage investor lifecycle with DnD optimistic UI + rollback via `PATCH /investors/{id}`.
- Drawer, filters, saved views, TR i18n, compact analytics present.
- CRM workspace untouched.
- Data honesty: LIVE / PARTIAL / DEMO labeled; no silent permanent mocks.

**Do not start next workspace** — awaiting visual approval.
