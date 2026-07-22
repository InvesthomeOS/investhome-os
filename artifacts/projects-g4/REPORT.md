# INVESTHOME OS — G4 Projects & Construction Workspace Report

**Date:** 2026-07-20  
**Verdict:** **PASS** (portfolio + construction ops + drawer/board + i18n + analytics density meet G4 bar; backend gaps labeled LIVE / PARTIAL / DEMO — not silently mocked as permanent data)

---

## 1. Preview URL

`http://localhost:3000/dashboard/projects`

Demo login: `superadmin@investhome.demo` / `Demo123!`

Query views: `?view=portfolio|board|tasks|timeline|milestones|budget|contractors|permits|inspections|issues|documents|change_orders|analytics|activity`  
Layout: `?layout=grid|list|table` · deep-link: `?id=<projectId>`

---

## 2. Implemented routes

| Route | View |
|-------|------|
| `/dashboard/projects` | Portfolio (default grid) |
| `/dashboard/projects?view=board` | Construction Board (Plane-inspired stages) |
| `/dashboard/projects?view=tasks` | Task list |
| `/dashboard/projects?view=timeline` | Operational timeline |
| `/dashboard/projects?view=milestones` | 20 default + custom milestones |
| `/dashboard/projects?view=budget` | Budget (existing finance/project budget APIs) |
| `/dashboard/projects?view=contractors` | Contractors / commitments |
| `/dashboard/projects?view=permits` | Permits |
| `/dashboard/projects?view=inspections` | Inspections |
| `/dashboard/projects?view=issues` | Issues & risks |
| `/dashboard/projects?view=documents` | Documents |
| `/dashboard/projects?view=change_orders` | Change orders |
| `/dashboard/projects?view=analytics` | Project analytics |
| `/dashboard/projects?view=activity` | Unified activity |
| `/dashboard/projects/[id]/[tab]` | Existing full detail routes preserved |

Primary UX: dense portfolio + right **ops drawer** + construction board/task drawer. CRM (`/workspaces/crm`) and Investors (`/dashboard/investors`) were **not** modified.

---

## 3. Live-data routes

| Surface | Classification | Source |
|---------|----------------|--------|
| Portfolio grid/list/table | **LIVE** | `GET /projects`, stats |
| Project status / portfolio type moves | **LIVE** | `POST /projects/{id}/status` (optimistic + rollback) |
| Timeline (activity + upcoming milestones) | **LIVE** | `/projects/recent-activity`, `/projects/upcoming-milestones` |
| Budget | **LIVE** | `/projects/{id}/budget-summary` (+ categories) |
| Contractors / commitments | **LIVE** | `/projects/{id}/commitments` |
| Documents | **LIVE** | Entity documents panel / project documents |
| Activity feed | **LIVE** | `/projects/recent-activity` |
| Drawer profile fields | **LIVE** | Project CRUD fields |
| Drawer activity / audit | **LIVE** | Entity activity timeline |
| AI actions | **LIVE** (existing AI; unavailable when offline) | `ContextualAiActions module="projects"` |
| Analytics KPI counts / value | **LIVE** | Derived from live project list |

---

## 4. Demo-data / partial routes

| Surface | Classification | Notes |
|---------|----------------|-------|
| Construction Board tasks | **DEMO** | Workspace localStorage store; gap banner; no native task API |
| Task list / task drawer | **DEMO** | Same store; comments/activity tabs show gap |
| Permits | **DEMO** | Seeded workspace records; no permits API |
| Inspections | **DEMO** | Seeded workspace records; no inspections API |
| Issues & risks register | **DEMO** | Workspace store; computed alerts remain live elsewhere |
| Milestones (20 defaults + custom) | **PARTIAL** | Workspace milestone set + live derived milestone dates in timeline |
| Change orders list | **PARTIAL** | Commitment CO API exists; UI shows local rows when empty + commitment CO signal |
| Analytics trend sparklines | **PARTIAL** | Live KPIs; trend series synthesized for Stripe/Linear density |

---

## 5. Backend gaps

1. **No project-native tasks/issues API** — construction board + task drawer use honest DEMO workspace store.
2. **No permits / inspections entity APIs** — document types exist; dedicated registers are DEMO.
3. **No CRUD risk register** — risks computed via alerts; UI register is DEMO.
4. **Milestones are largely derived** (`GET …/milestones`) — no full milestone CRUD entity; G4 adds default set + custom in workspace store.
5. **Change-order API is nested under commitments** — web client helpers still thin; G4 surfaces PARTIAL list + live commitment CO amounts when present.
6. **Portfolio “types”** (Acquisition…Cancelled) are product language mapped onto existing `project_status` (+ development_type hints) — no schema migration.

---

## 6. Test results

| Check | Result |
|-------|--------|
| G4 TypeScript (`src/.../projects/_components/g4`) | Clean (repo has pre-existing unrelated tsc debt) |
| `next build` (Docker web image) | Success |
| Docker `web` rebuild + recreate | Success (no DB volume delete) |
| Critical scenarios 1–15 (`.pw-verify/verify-projects-g4.mjs`) | **15/15 passed** |
| Playwright `e2e/projects-g4.spec.ts` | Spec authored; host `@playwright/test` not installed in web package — verification run via `.pw-verify` Playwright (same pattern as G3 screenshot capture) |

---

## 7. Screenshot paths

Re-captured and verified on disk **2026-07-20** via `.pw-verify/capture-projects-g4.mjs` against `http://localhost:3000`.

Absolute dir: `C:\Users\eminb\Projects\investhome-os\artifacts\projects-g4`

Independent listing confirmation: **15/15 PNG present, each >10KB**.

| # | File | Size (bytes) |
|---|------|-------------:|
| 1 | `artifacts/projects-g4/01-portfolio-desktop.png` | 215397 |
| 2 | `artifacts/projects-g4/02-detail-overview.png` | 200402 |
| 3 | `artifacts/projects-g4/03-construction-board.png` | 178541 |
| 4 | `artifacts/projects-g4/04-task-drawer.png` | 164225 |
| 5 | `artifacts/projects-g4/05-timeline.png` | 114354 |
| 6 | `artifacts/projects-g4/06-milestones.png` | 142509 |
| 7 | `artifacts/projects-g4/07-budget.png` | 130779 |
| 8 | `artifacts/projects-g4/08-contractors.png` | 125123 |
| 9 | `artifacts/projects-g4/09-permits.png` | 113740 |
| 10 | `artifacts/projects-g4/10-inspections.png` | 137641 |
| 11 | `artifacts/projects-g4/11-issues-risks.png` | 130720 |
| 12 | `artifacts/projects-g4/12-analytics.png` | 146450 |
| 13 | `artifacts/projects-g4/13-tablet.png` | 146703 |
| 14 | `artifacts/projects-g4/14-turkish.png` | 212588 |
| 15 | `artifacts/projects-g4/15-english.png` | 126474 |

Also written: `artifacts/projects-g4/sizes-verified.json` (machine-readable sizes from the same listing).

---

## 8. Known limitations

- Construction tasks / permits / inspections / risk register are intentionally DEMO with gap banners (no silent permanent mocks).
- Change-order deep CRUD UI still incomplete vs full cost module; uses commitments + local fallback.
- English screenshot depends on language control; Docker default locale is Turkish.
- Map placeholder omitted — only shown when location data warrants it (addresses exist; no map tile integration added).
- Existing detail tab routes (`/dashboard/projects/[id]/…`) remain for deep finance/units/sales; G4 drawer is the ops-first surface.

---

## 9. Migration risks

- **None for schema** — G4 is frontend + localStorage sidecars only; no destructive migrations.
- Status mapping is additive/display-layer; persist uses existing `ProjectStatus` values via `changeProjectStatus`.
- CRM and Investor workspaces untouched.

---

## 10. i18n & a11y

- Full `projects.g4` catalog in `en.json` + `tr.json` (Turkish default).
- Board cards keyboard-activatable (Enter/Space); drawer focusable; DnD with optimistic update + rollback path.
- Filters + saved views (localStorage `investhome.projects.g4.saved-views.v1`).

---

## 11. Charts & AI

- Design-system SVG charts only (`Sparkline`, `LineChart`, `BarChart`) — no ApexCharts added.
- AI Insights: existing Contextual AI only; proper unavailable messaging; no fake AI payloads.

---

## 12. Final verdict

**PASS**

- Visual language matches approved G1/G2/G3 pipeline quality (IBM Plex, warm surfaces, dense cards, right drawer, construction board).
- Portfolio + Construction Board + Tasks + Timeline + Milestones + Budget + Contractors + Permits + Inspections + Issues + Documents + Change Orders + Analytics + Activity are E2E usable.
- Data honesty: LIVE / PARTIAL / DEMO labeled; backend gaps documented.
- Screenshots on disk under `artifacts/projects-g4/` and size-verified (>10KB each).
- CRM and Investor workspaces not overwritten.

**Do not start Finance Workspace** — awaiting visual approval.
