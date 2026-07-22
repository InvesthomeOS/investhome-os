# INVESTHOME OS — GitHub Product UI Audit / Phase G1 REPORT

**Date:** 2026-07-20  
**Preview URL:** http://localhost:3000/dashboard/admin/github-ui-preview  
**Pattern matrix:** `docs/ui/github-product-pattern-matrix.md`  
**Technical verdict:** PASS WITH WARNINGS  
**Design acceptance:** **REVISION REQUIRED**

---

## 1. InvestHome frontend audit (Step 1)

| Area | Finding |
|------|---------|
| Framework | Next.js ^15.1 (App Router) |
| React | ^19 |
| TypeScript | ^5.7 |
| Styling | Custom CSS + design tokens (`theme-tokens.css`); **no Tailwind** in `apps/web` |
| Component libs | `@investhome/ui`, local `components/design-system` |
| Router | Next App Router |
| Table / DnD / charts | No dedicated table/DnD libs; HTML5 DnD in sales; custom SVG/CSS charts |
| State | TanStack Query, Zustand, RHF + Zod |
| i18n | next-intl (TR primary) |
| Shell | OsShell + AdminShell |
| Theme | Light-first brand tokens (gold `#9d7b55`, teal `#77bfbb`) |

---

## 2. External repos (Step 2) — license & reuse

| Product | Stack (summary) | License | Reuse | Recommendation |
|---------|-----------------|---------|-------|----------------|
| Twenty | Vite + React 19, Linaria/Mantine, hello-pangea/dnd, Nivo | **AGPL-3.0** | Not safe to copy into proprietary SaaS | **C visual only** |
| Plane | React Router 7, Tailwind, Plane UI, Atlaskit DnD, cmdk | **AGPL-3.0** | Not safe to copy | **C visual only** |
| Dub | Next 15 + React 19, Tailwind, Visx, TanStack Table | **AGPL-3.0-or-later** | Not safe to copy AGPL paths | **C visual only** |
| Cal.com | Next 16 + React 18, Tailwind, Cal UI / Radix | **MIT** | Adapted reuse OK with attribution | **B adapted** |

Clones inspected under `.tmp-github-ui/` (gitignored). **No AGPL source copied into production paths.**

---

## 3. Pattern matrix (Step 3)

Path: `docs/ui/github-product-pattern-matrix.md`

Covers Executive Dashboard, CRM Leads/Contacts, Lead Detail, Sales/Investor Pipeline, Projects, Construction Kanban, Project Detail, Marketing Overview, Campaign Analytics, Calendar, Finance, AI, Notifications, Global Search — with reuse method, license risk, technical risk.

---

## 4. Isolated prototype (Step 4)

| Item | Value |
|------|-------|
| Route | `/dashboard/admin/github-ui-preview` |
| Isolation | `apps/web/src/app/dashboard/admin/github-ui-preview/_preview/` |
| Access | Admin permission gate (same pattern as TailAdmin preview) |
| Data | Demo fixtures only; local DnD state; **no API mutations** |
| Tabs | Satış Pipeline · Proje Operasyonları · Pazarlama Analitiği |
| Labels | Turkish UI; Investhome logo + OS nav names |
| Theme | Light, compact, brand tokens |

---

## 5. Verification (Step 5)

| Check | Result |
|-------|--------|
| Docker web rebuild | Yes (no DB volume delete) |
| Production Next build (in Docker) | Pass |
| Lint (`pnpm lint`) | Pass (unrelated unused-var warning elsewhere) |
| Typecheck | Repo has pre-existing TS errors unrelated to G1; **no errors in github-ui-preview files** |
| Playwright visual QA | Pass — route opened, all tabs + drawer screenshotted |
| Screenshots | `artifacts/github-ui-g1/*.png` (1440 + 1280) |

### Screenshot paths

- `artifacts/github-ui-g1/pipeline.png` / `pipeline-1440.png` / `pipeline-1280.png`
- `artifacts/github-ui-g1/project-operations.png` / `project-operations-1440.png` / `project-operations-1280.png`
- `artifacts/github-ui-g1/marketing-analytics.png` / `marketing-analytics-1440.png` / `marketing-analytics-1280.png`
- `artifacts/github-ui-g1/opportunity-drawer.png` / `opportunity-drawer-1440.png`

---

## 6. Design acceptance (mandatory)

### A. Sales Pipeline (Twenty / Attio bar)

| Criterion | Assessment |
|-----------|------------|
| Comparable to Attio dense CRM? | **Partial.** Cards are information-dense (value, %, bar, avatar, date, type). Missing Attio/Twenty saved views, keyboard stage moves, relationship chips, richer record page. |
| Drag & drop smooth? | HTML5 DnD works; not as polished as `@dnd-kit` / hello-pangea. |
| Cards information-dense? | Yes. |
| Would use every day? | **Not yet** as a daily CRM — strong demo, not Attio-class. |

### B. Project Operations (Plane bar)

| Criterion | Assessment |
|-----------|------------|
| Comparable to Plane? | **Partial.** Project list + kanban + priority/assignee/blockers present. Missing cycles, modules, rich issue thread, Plane command palette. |
| Kanban clean? | Yes after cross-project density fix. |
| Navigation intuitive? | Yes (project list + board). |
| Density appropriate? | Improved with “Tüm projeler”; still thinner than Plane production boards. |

### C. Marketing Analytics (Dub bar)

| Criterion | Assessment |
|-----------|------------|
| Resemble Dub? | **Closest of the three** — compact KPIs, clean chart, attribution bars, campaign table. |
| KPIs understandable? | Yes. |
| Charts clean? | Yes; no oversized donut. |
| Avoid empty giant cards? | Yes. Lead-source table still tends to sit below the fold at 1440. |

### Design verdict

**REVISION REQUIRED**

Do **not** migrate these patterns into production workspaces yet.

Required before READY FOR PHASE 2:

1. **Sales:** Add saved-view chips + denser filter rail; ensure Closing/Won/Lost discoverable without relying on horizontal scroll alone (mini stage scroller / stage summary strip); consider MIT `@dnd-kit` for smoother DnD.
2. **Projects:** Enrich issue drawer (comments/activity, blocker list, project chip); keep Review/Done columns populated in default view.
3. **Marketing:** Fit campaign + lead-source tables into first viewport at 1440 (tighter chart/KPI) so Dub-like “all signal above fold” holds.
4. **Chrome:** When migrating, embed in workspace shells (Sales / Projects / Marketing) — not Admin pill nav — so the composition feels like product, not audit sandbox.

---

## 7. Files changed

- `docs/ui/github-product-pattern-matrix.md` (new)
- `apps/web/src/app/dashboard/admin/github-ui-preview/page.tsx` (new)
- `apps/web/src/app/dashboard/admin/github-ui-preview/_preview/*` (new isolated preview)
- `apps/web/src/app/dashboard/admin/_components/admin-shell.tsx` (nav link)
- `apps/web/messages/tr.json`, `en.json` (`githubUiPreview`)
- `.gitignore` (`.tmp-github-ui/`)
- `.pw-verify/github-ui-g1-qa.mjs` (visual QA)
- `artifacts/github-ui-g1/*` (screenshots + this report)

External clones (not in production tree): `.tmp-github-ui/{twenty,plane,dub,cal.com}`

---

## 8. Final verdicts

| Gate | Result |
|------|--------|
| G1 technical (route + screenshots + matrix + isolation) | **PASS WITH WARNINGS** (repo-wide typecheck pre-existing failures) |
| Design acceptance (Attio/Plane/Dub bar) | **REVISION REQUIRED** |
| Phase 2 migration | **Blocked until revision list above is addressed and re-reviewed** |
