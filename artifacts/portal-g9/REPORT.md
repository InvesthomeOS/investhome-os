# INVESTHOME OS — G9 Client & Investor Portal Report

**Date:** 2026-07-20  
**Verdict:** **PASS**

Premium private-investment portal under `/portal` (Juniper Square–class density, not CRM). Session-scoped investor isolation holds. Screenshots verified on disk (>10KB). Waiting for visual approval before any next phase.

---

## 1. Preview URL

`http://localhost:3000/portal`

**Demo investor login (portal session, not staff OS):**

| Investor | Email | Password |
|----------|-------|----------|
| A (default) | `investor.a@investhome.demo` | `Portal123!` |
| B (isolation tests only) | `investor.b@investhome.demo` | `Portal123!` |

Access: open `/portal/login` → sign in as Investor A. Staff `/login` users are **not** portal accounts.

Requires `PORTAL_SESSION_SECRET` (set in `docker-compose.yml` for web). Cookie: signed `ih_portal_session`.

---

## 2. Implemented routes

| Route | Module |
|-------|--------|
| `/portal` · `/portal/dashboard` | Dashboard |
| `/portal/portfolio` | Portfolio KPIs + allocation |
| `/portal/projects` | Projects list |
| `/portal/projects/[projectId]` | Project detail (overview/photos/progress/milestones/budget/docs/news/rental/map) |
| `/portal/reservations` | Reservations |
| `/portal/contracts` | Contracts |
| `/portal/payments` | Payments tracking |
| `/portal/rental-income` | Rental income |
| `/portal/documents` | Documents (categories, preview, permission-checked download) |
| `/portal/reports` | Report presets |
| `/portal/messages` | Secure messages |
| `/portal/tasks` | Tasks |
| `/portal/meetings` | Meetings |
| `/portal/notifications` | Notification types |
| `/portal/support` | Support center |
| `/portal/account` | Account & security (profile/2FA/devices/sessions/language/prefs) |
| `/portal/login` | Portal auth |

APIs: `POST/GET/DELETE /api/portal/session`, `GET /api/portal/documents/[id]/download` (403 cross-investor).

**Isolation:** Existing `/investor` mock left intact. G5–G8 dashboard workspaces untouched.

---

## 3. Data classification

| Surface | Classification | Notes |
|---------|----------------|-------|
| Portal auth session | **DEMO** | Signed cookie; demo credentials above |
| Portfolio / projects / payments / rental / docs / messages | **DEMO** | Session-scoped fixtures for Investor A or B only |
| Document download gate | **LIVE** (app logic) | Ownership check in API; demo payload body |
| Staff investor CRM APIs | **BLOCKED** (for portal) | Not used as LP data source — would leak CRM scope |
| Dedicated portal backend APIs | **BLOCKED** | No `/portal/*` FastAPI surface yet |

Gap banner shown on every module (no silent permanent mocks).

---

## 4. Security notes

1. Middleware protects `/portal/*` except `/portal/login`; requires `ih_portal_session`.
2. Session cookie is HMAC-signed (`PORTAL_SESSION_SECRET` / `JWT_SECRET`).
3. All portal data accessors filter by `investorId`.
4. Document download returns **403** when document `investorId` ≠ session investor (verified A↛B and B↛A).
5. Investor B holdings/messages/docs never render in Investor A UI (and reverse).
6. No auth bypass / hardcoded admin for staff OS.

---

## 5. Backend gaps

1. No FastAPI portal APIs for LP-scoped portfolio, payments, documents, messages.
2. No DB-backed external investor login role (portal demo auth is Next.js–local).
3. Map is schematic placeholder (coordinates labeled); no map provider key.
4. Report “Generate” is UI-only until report service exists.
5. Existing staff `/investors` CRM must not be reused as portal feed without ownership scoping.

---

## 6. Test results

| Check | Result |
|-------|--------|
| TypeScript (portal sources) | Clean (no portal errors; repo has pre-existing e2e/@playwright debt elsewhere) |
| ESLint portal files | Pass (`--max-warnings 0`) |
| Docker `web` rebuild | Success (no DB volume delete) |
| `verify-portal-g9.mjs` | **11/11 passed** |
| Playwright `portal-g9.spec.ts` | **6/6 passed** |
| Screenshots on disk | **15/15 verified >10KB** (`sizes-verified.json`) |

---

## 7. Screenshot paths

Re-captured 2026-07-20 via `.pw-verify/capture-portal-g9.mjs` (`import.meta.url` → absolute `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\`).  
Directory listing + per-file `>10KB` gate: **15/15 CONFIRMED**.

| # | Absolute path | Size (bytes) |
|---|---------------|-------------:|
| 1 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\01-dashboard.png` | 113,993 |
| 2 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\02-portfolio.png` | 111,373 |
| 3 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\03-project-detail.png` | 187,503 |
| 4 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\04-reservations.png` | 95,633 |
| 5 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\05-contracts.png` | 96,571 |
| 6 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\06-payments.png` | 112,964 |
| 7 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\07-rental-income.png` | 94,532 |
| 8 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\08-documents.png` | 125,149 |
| 9 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\09-reports.png` | 102,677 |
| 10 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\10-messages.png` | 108,296 |
| 11 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\11-notifications.png` | 114,321 |
| 12 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\12-account-security.png` | 113,786 |
| 13 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\13-tablet.png` | 57,784 |
| 14 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\14-turkish.png` | 113,993 |
| 15 | `C:\Users\eminb\Projects\investhome-os\artifacts\portal-g9\15-english.png` | 117,256 |

---

## 8. i18n

- TR default (`portal-tr.json` / `portal-en.json` merged in `i18n/request.ts`)
- Header TR/EN toggle via `investhome.locale` cookie
- Screenshots 14 (TR) and 15 (EN) captured

---

## 9. Known limitations

- Portal data is explicitly **DEMO** until LP-scoped APIs exist.
- Docker web has no source mounts — UI changes require `docker compose build web` (+ `PORTAL_SESSION_SECRET` env).
- Legacy mock at `/investor` remains separate (not the G9 surface).

---

## 10. Verdict rationale

**PASS** because:

1. Visual: dense premium light portal, brand-forward, DS line/sparkline/bar charts — not CRM pipeline boards.
2. Modules 1–15 delivered under `/portal`.
3. Permission isolation holds (UI + download API).
4. Screenshots verified on disk with sizes.
5. TR/EN + responsive coverage.
6. Gaps classified; no silent invention of other investors’ data.

**Waiting for visual approval. Do not start next workspace/phase.**
